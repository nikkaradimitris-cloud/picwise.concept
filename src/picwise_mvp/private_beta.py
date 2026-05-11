from __future__ import annotations

from dataclasses import dataclass
import re

from picwise_nlu import build_local_nlu_intent
from picwise_offers import (
    EligibilityGateResult,
    LocalFixtureOfferSourceAdapter,
    OfferIntakeRequest,
    OfferIntakeResult,
    PickWiseRecommendationSet,
    RecommendationStatus,
    build_default_product_source,
    build_pickwise_recommendation_set,
    intake_offer_candidates,
    run_product_eligibility_gate,
)
from picwise_search import SearchDecision, route_search_query

_URL_REGEX = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)


@dataclass(frozen=True)
class OutboundLinkContract:
    status: str
    target_url: str | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class PickWiseMVPSearchFlow:
    query: str
    search_decision: SearchDecision
    local_nlu_intent: dict[str, object]
    expected_vertical: str
    intake_result: OfferIntakeResult
    eligibility_result: EligibilityGateResult
    recommendation_set: PickWiseRecommendationSet
    outbound_link_contract: OutboundLinkContract
    state: str
    reason_codes: tuple[str, ...]


def _is_valid_url(value: str | None) -> bool:
    if not value:
        return False
    return bool(_URL_REGEX.match(value.strip()))


def _resolve_expected_vertical(query: str, local_nlu_intent: dict[str, object]) -> str:
    lowered_query = query.lower()
    category = str(local_nlu_intent.get("category") or "").lower()
    if any(token in lowered_query for token in ("finance", "insurance", "loan", "credit")):
        return "finance_insurance_business_finance"
    if any(token in lowered_query for token in ("saas", "erp", "software")) or category in {"saas", "software", "erp"}:
        return "software_saas_erp"
    return "retail_physical_products"


def _build_outbound_link_contract(recommendation_set: PickWiseRecommendationSet) -> OutboundLinkContract:
    wise = recommendation_set.wise_recommended_product
    if wise is None:
        return OutboundLinkContract(
            status="not_available",
            target_url=None,
            reason_codes=("wise_recommendation_not_safe",),
        )
    slot_map = {slot.candidate_id: slot for slot in recommendation_set.display_slots}
    slot = slot_map.get(wise.candidate_id)
    if slot is None:
        return OutboundLinkContract(
            status="blocked",
            target_url=None,
            reason_codes=("recommended_slot_missing",),
        )
    target_url = slot.affiliate_url or slot.outbound_url
    if not _is_valid_url(target_url):
        return OutboundLinkContract(
            status="blocked",
            target_url=None,
            reason_codes=("invalid_outbound_contract_url",),
        )
    return OutboundLinkContract(
        status="ready",
        target_url=target_url,
        reason_codes=("outbound_contract_ready",),
    )


def run_pickwise_mvp_search_flow(query: str) -> PickWiseMVPSearchFlow:
    raw_query = str(query or "").strip()
    decision = route_search_query(raw_query)
    local_nlu_intent = build_local_nlu_intent(raw_query)
    expected_vertical = _resolve_expected_vertical(raw_query, local_nlu_intent)
    source = build_default_product_source()
    intake_result = intake_offer_candidates(
        OfferIntakeRequest(
            query=raw_query,
            search_decision=decision.to_dict(),
            local_nlu_intent=local_nlu_intent,
            source=source,
        ),
        adapter=LocalFixtureOfferSourceAdapter(),
    )

    eligibility_result = run_product_eligibility_gate(
        intake_result.candidates,
        expected_vertical=expected_vertical,
        source_trust_level=source.trust_level,
        source_connected=intake_result.status.value == "connected",
        image_required=expected_vertical == "retail_physical_products",
    )
    recommendation_set = build_pickwise_recommendation_set(
        query=raw_query,
        eligible_candidates=eligibility_result.eligible_candidates,
    )
    outbound_contract = _build_outbound_link_contract(recommendation_set)

    reason_codes: list[str] = []
    state = "ready"
    if intake_result.status.value != "connected":
        state = "not_connected"
        reason_codes.extend(intake_result.reason_codes)
    elif recommendation_set.status == RecommendationStatus.NO_VALID_CANDIDATES:
        state = "no_result"
        reason_codes.append("no_eligible_candidates_after_gate")
    elif recommendation_set.status == RecommendationStatus.NOT_ENOUGH_VALID_CANDIDATES:
        state = "needs_data"
        reason_codes.append("not_enough_valid_candidates")
    if expected_vertical == "finance_insurance_business_finance":
        state = "manual_review"
        reason_codes.append("finance_vertical_manual_review_only")
    if decision.route_type in {"ambiguous_query", "no_safe_result"}:
        state = "needs_data" if decision.route_type == "no_safe_result" else "manual_review"
        reason_codes.append(decision.route_type)

    return PickWiseMVPSearchFlow(
        query=raw_query,
        search_decision=decision,
        local_nlu_intent=local_nlu_intent,
        expected_vertical=expected_vertical,
        intake_result=intake_result,
        eligibility_result=eligibility_result,
        recommendation_set=recommendation_set,
        outbound_link_contract=outbound_contract,
        state=state,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )
