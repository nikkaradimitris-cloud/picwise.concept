from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from picwise_nlu import (
    adapt_local_nlu_intent_for_router,
    build_local_nlu_intent,
    detect_category,
    normalize_greeklish_and_typos,
    normalize_query,
)
from picwise_nlu.concept_understanding import suggest_product_names, understand_product_query
from picwise_nlu.product_concepts import get_product_concepts_by_id
from picwise_search_memory.canonical_registry import get_cached_canonical_vocabulary_registry
from picwise_search_memory.broad_query_suggestions import (
    BroadQuerySuggestion,
    build_broad_query_suggestions,
    is_unsafe_broad_query,
    should_offer_broad_query_suggestions,
)
from picwise_search_memory.index_lookup import lookup_offline_search_index

from picwise_providers.search_selection import (
    is_strong_feed_opportunity_selection,
    provider_product_to_backend_dict,
)
from picwise_providers.state import (
    resolve_search_provider_feed_metadata,
    resolve_search_provider_feed_product_selection,
    resolve_search_provider_feed_recommendation_decision,
)

from .index_resolver_adapter import get_cached_offline_search_index, resolve_query_with_search_index


# Categories served by a manually connected provider instead of the provider feed.
# Amazon is no longer part of the product, so this is empty: every purchase-intent
# query, power banks included, now resolves through the same provider-feed engine as
# every other product type. The mapping is kept rather than deleted so a future
# manually connected provider has a place to register, and so the generic gates below
# keep their shape.
_CONNECTED_PROVIDER_BY_CATEGORY: dict[str, str] = {}

_CONNECTED_STATUSES = {
    "intent_resolved",
    "specific_product_resolved",
    "general_intent_resolved",
}

_INDEX_CATEGORY_OVERRIDE_MIN_CONFIDENCE = 0.84
_INDEX_CATEGORY_OVERRIDE_MIN_SCORE = 0.84
_HIGHLY_AMBIGUOUS_BROAD_SUGGESTION_COUNT = 5


def _vocabulary_registry():
    return get_cached_canonical_vocabulary_registry()


@dataclass(frozen=True)
class LiveSearchResolution:
    raw_query: str
    display_query: str
    normalized_query: str
    canonical_query: str
    canonical_category: str | None
    mega_category_id: str | None
    display_name: str | None
    lower_level_provider_category: str | None
    intent: str
    query_type: str
    confidence: float
    status: str
    needs_review: bool
    provider_key: str
    provider_status: str
    result_allowed: bool
    resolver_state: str
    reason_codes: tuple[str, ...]
    suggestions: tuple[BroadQuerySuggestion, ...] = field(default_factory=tuple)
    # The product concept understood from the query, when there was one.
    understood_concept_id: str | None = None
    understood_concept_name: str | None = None
    # True when understanding needed a typo correction rather than an exact (or
    # exact-by-sound) match. The page then states what it understood.
    understood_by_correction: bool = False
    understood_specs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    # Product names to ask about when nothing was understood ("dsk" -> desk).
    did_you_mean: tuple[str, ...] = field(default_factory=tuple)
    provider_feed_status: str | None = None
    provider_feed_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    provider_feed_eligible_count: int = 0
    provider_feed_selection_status: str | None = None
    provider_feed_selection_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    provider_feed_unmatched_query_terms: tuple[str, ...] = field(default_factory=tuple)
    provider_feed_partially_matched_terms: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    provider_feed_ambiguous_product_families: tuple[str, ...] = field(default_factory=tuple)
    provider_feed_matched_count: int = 0
    provider_feed_selected_count: int = 0
    provider_feed_selected_products: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    provider_feed_decision_status: str | None = None
    provider_feed_recommended_product_id: str | None = None
    provider_feed_recommendation_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    provider_feed_recommendation_confidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "understood_concept_id": self.understood_concept_id,
            "understood_concept_name": self.understood_concept_name,
            "understood_by_correction": self.understood_by_correction,
            "understood_specs": list(self.understood_specs),
            "did_you_mean": list(self.did_you_mean),
            "raw_query": self.raw_query,
            "display_query": self.display_query,
            "normalized_query": self.normalized_query,
            "canonical_query": self.canonical_query,
            "canonical_category": self.canonical_category,
            "mega_category_id": self.mega_category_id,
            "display_name": self.display_name,
            "lower_level_provider_category": self.lower_level_provider_category,
            "intent": self.intent,
            "query_type": self.query_type,
            "confidence": self.confidence,
            "status": self.status,
            "needs_review": self.needs_review,
            "provider_key": self.provider_key,
            "provider_status": self.provider_status,
            "result_allowed": self.result_allowed,
            "resolver_state": self.resolver_state,
            "reason_codes": list(self.reason_codes),
            "suggestions": [row.to_dict() for row in self.suggestions],
        }
        if self.provider_feed_status is not None:
            payload["provider_feed_status"] = self.provider_feed_status
            payload["provider_feed_reason_codes"] = list(self.provider_feed_reason_codes)
            payload["provider_feed_eligible_count"] = self.provider_feed_eligible_count
        if self.provider_feed_selection_status is not None:
            payload["provider_feed_selection_status"] = self.provider_feed_selection_status
            payload["provider_feed_selection_reason_codes"] = list(
                self.provider_feed_selection_reason_codes
            )
            payload["provider_feed_unmatched_query_terms"] = list(
                self.provider_feed_unmatched_query_terms
            )
            payload["provider_feed_partially_matched_terms"] = [
                list(row) for row in self.provider_feed_partially_matched_terms
            ]
            payload["provider_feed_ambiguous_product_families"] = list(
                self.provider_feed_ambiguous_product_families
            )
            payload["provider_feed_matched_count"] = self.provider_feed_matched_count
            payload["provider_feed_selected_count"] = self.provider_feed_selected_count
            payload["provider_feed_selected_products"] = list(self.provider_feed_selected_products)
            if self.provider_feed_decision_status is not None:
                payload["provider_feed_decision_status"] = self.provider_feed_decision_status
                payload["provider_feed_recommended_product_id"] = self.provider_feed_recommended_product_id
                payload["provider_feed_recommendation_reason_codes"] = list(
                    self.provider_feed_recommendation_reason_codes
                )
                if self.provider_feed_recommendation_confidence is not None:
                    payload["provider_feed_recommendation_confidence"] = (
                        self.provider_feed_recommendation_confidence
                    )
        return payload


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def is_empty_search_query(query: str) -> bool:
    return not _normalized_text(query)


def empty_landing_search_resolution(query: str = "") -> LiveSearchResolution:
    raw_query = str(query or "")
    return LiveSearchResolution(
        raw_query=raw_query,
        display_query=raw_query,
        normalized_query="",
        canonical_query="",
        canonical_category=None,
        mega_category_id=None,
        display_name=None,
        lower_level_provider_category=None,
        intent="unknown",
        query_type="unknown",
        confidence=0.0,
        status="invalid_intent",
        needs_review=True,
        provider_key="not_connected",
        provider_status="not_connected",
        result_allowed=False,
        resolver_state="blocked_or_unsafe",
        reason_codes=("empty_query",),
    )


def _safe_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return round(score, 2)


def _index_reason_codes_block_feed_opportunity(reason_codes: tuple[str, ...]) -> bool:
    blocked_markers = ("homograph", "unsafe", "blocked")
    for code in reason_codes:
        lowered = str(code).lower()
        if any(marker in lowered for marker in blocked_markers):
            return True
    return False


def _query_eligible_for_feed_opportunity_attempt(
    *,
    canonicalized_query: str,
    offer_broad_suggestions: bool,
    broad_suggestions: tuple[BroadQuerySuggestion, ...],
    blocked_or_unsafe: bool,
    index_reason_codes: tuple[str, ...],
) -> bool:
    if blocked_or_unsafe:
        return False
    if is_unsafe_broad_query(canonicalized_query):
        return False
    if _index_reason_codes_block_feed_opportunity(index_reason_codes):
        return False
    if offer_broad_suggestions and len(broad_suggestions) >= _HIGHLY_AMBIGUOUS_BROAD_SUGGESTION_COUNT:
        return False
    return True


def resolve_live_search(query: str) -> LiveSearchResolution:
    raw_query = str(query or "")
    display_query = raw_query
    normalized_query = normalize_query(raw_query)
    canonicalized_query = normalize_greeklish_and_typos(normalized_query)

    intent = build_local_nlu_intent(raw_query)
    # Which product the buyer means, however it was spelled: Greek, greeklish, the
    # wrong keyboard layout, or English with typos.
    concept_reading = understand_product_query(raw_query)
    adapter = adapt_local_nlu_intent_for_router(intent)
    category_probe = detect_category(canonicalized_query)
    index_result = resolve_query_with_search_index(canonicalized_query)
    raw_index_lookup = lookup_offline_search_index(canonicalized_query, get_cached_offline_search_index())
    broad_suggestions = build_broad_query_suggestions(_vocabulary_registry(), canonicalized_query)
    offer_broad_suggestions = should_offer_broad_query_suggestions(
        normalized_query=canonicalized_query,
        lookup_result=raw_index_lookup,
        suggestions=broad_suggestions,
    )

    canonical_category = intent.get("category") or category_probe.get("category")
    if not canonical_category and index_result.status == "matched" and index_result.canonical_term:
        canonical_category = str(index_result.canonical_term)

    index_high_confidence_category = (
        index_result.status in {"matched", "low_confidence"}
        and bool(index_result.mega_category_id)
        and index_result.confidence >= _INDEX_CATEGORY_OVERRIDE_MIN_CONFIDENCE
        and index_result.score >= _INDEX_CATEGORY_OVERRIDE_MIN_SCORE
    )
    if index_high_confidence_category:
        mega_category_id = index_result.mega_category_id
        if index_result.canonical_term:
            provider_category = category_probe.get("category") or intent.get("category")
            if provider_category in _CONNECTED_PROVIDER_BY_CATEGORY:
                canonical_category = str(provider_category)
            else:
                canonical_category = str(index_result.canonical_term)
    else:
        mega_category_id = (
            intent.get("mega_category_id")
            or category_probe.get("mega_category_id")
            or (index_result.mega_category_id if index_result.status == "matched" else None)
            or (
                canonical_category
                if canonical_category and canonical_category != "power_banks"
                else None
            )
        )
    lower_level_provider_category = category_probe.get("lower_level_provider_category")
    if canonical_category in _CONNECTED_PROVIDER_BY_CATEGORY:
        lower_level_provider_category = canonical_category
    query_type = str(intent.get("query_type") or "unknown")
    confidence = max(
        _safe_confidence(intent.get("confidence")),
        _safe_confidence(category_probe.get("confidence")),
        _safe_confidence(index_result.confidence),
    )
    status = str(intent.get("status") or "manual_review_required")
    needs_review = bool(intent.get("needs_review", True))
    is_ambiguous_or_invalid = status in {"ambiguous_needs_review", "invalid_intent"} or query_type == "ambiguous_query"
    if (
        status not in _CONNECTED_STATUSES
        and index_high_confidence_category
        and canonical_category not in _CONNECTED_PROVIDER_BY_CATEGORY
    ):
        status = "general_intent_resolved"
        needs_review = False

    intent_blocked = status == "invalid_intent" or any(
        marker in str(code).lower()
        for code in intent.get("reason_codes", [])
        for marker in ("unsafe", "blocked")
    )
    concept_understood = concept_reading.understood and not intent_blocked
    if concept_understood:
        # The product concept is understood even where the word-level NLU and the
        # English search index are not ("ψιγείο", "plintirio", "cygeio"). Its mega
        # category is the taxonomy category whose product rules apply.
        if not mega_category_id:
            mega_category_id = concept_reading.mega_category_id
        if not canonical_category:
            canonical_category = concept_reading.concept_id
        if status not in _CONNECTED_STATUSES:
            status = "general_intent_resolved"
        needs_review = False
        is_ambiguous_or_invalid = False
        # A query the index judges too broad ("charger": phone, laptop or car?) keeps
        # its suggestions. Understanding the word does not settle which product.

    # No per-category query rewriting: collapsing "power bank 20000mah for iphone" to
    # "power bank" existed only so the manual Amazon matcher would hit, and it threw away
    # the tokens the feed selection needs to tell the four choices apart.
    canonical_query = (
        index_result.canonical_term
        or canonicalized_query
        or normalized_query
        or _normalized_text(raw_query).lower()
    )

    provider_lookup_key = str(lower_level_provider_category or canonical_category or "")
    provider_key = _CONNECTED_PROVIDER_BY_CATEGORY.get(provider_lookup_key, "not_connected")
    provider_status = "connected" if provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY else "not_connected"

    connected_category_safe_gate = bool(
        provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY
        and provider_status == "connected"
        and _normalized_text(raw_query)
        and not is_ambiguous_or_invalid
        and confidence >= 0.2
    )
    if connected_category_safe_gate and status not in _CONNECTED_STATUSES:
        status = "general_intent_resolved"
        needs_review = False

    result_allowed = bool(
        provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY
        and provider_status == "connected"
        and status in _CONNECTED_STATUSES
        and confidence >= 0.2
    )

    resolver_state = "not_understood"
    blocked_or_unsafe = status == "invalid_intent" or any(
        marker in str(code).lower()
        for code in intent.get("reason_codes", [])
        for marker in ("unsafe", "blocked")
    )
    if result_allowed:
        resolver_state = "connected_provider_results"
    elif offer_broad_suggestions:
        resolver_state = "broad_query_suggestions"
        mega_category_id = None
        canonical_category = None
        needs_review = False
        status = "general_intent_resolved"
    elif blocked_or_unsafe:
        resolver_state = "blocked_or_unsafe"
    elif mega_category_id and provider_status != "connected":
        resolver_state = "understood_provider_not_connected"
    elif provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY and (needs_review or confidence < 0.2):
        resolver_state = "low_confidence_manual_review"
    elif not mega_category_id and not canonical_category:
        resolver_state = "not_understood"
    else:
        # Unsupported or weakly resolved categories remain safely un-understood.
        resolver_state = "not_understood"

    reason_codes: list[str] = [str(code) for code in intent.get("reason_codes", []) if str(code).strip()]
    reason_codes.extend(f"index_{code}" for code in index_result.reason_codes)
    reason_codes.append(f"index_status_{index_result.status}")
    if not _normalized_text(raw_query):
        reason_codes.append("empty_query")
    if not mega_category_id and not canonical_category:
        reason_codes.append("no_canonical_category")
    if mega_category_id and provider_status != "connected":
        reason_codes.append("provider_not_connected")
    if needs_review:
        reason_codes.append("manual_review_required")
    if provider_status == "connected":
        reason_codes.append("provider_connected")
    if offer_broad_suggestions:
        reason_codes.append("broad_query_suggestions")
    reason_codes.append(f"resolver_state_{resolver_state}")
    reason_codes.append(f"adapter_{adapter.get('adapter_decision', 'safe_review_only')}")

    provider_feed_status: str | None = None
    provider_feed_reason_codes: tuple[str, ...] = ()
    provider_feed_eligible_count = 0
    provider_feed_selection_status: str | None = None
    provider_feed_selection_reason_codes: tuple[str, ...] = ()
    provider_feed_unmatched_query_terms: tuple[str, ...] = ()
    provider_feed_partially_matched_terms: tuple[tuple[str, int], ...] = ()
    provider_feed_ambiguous_product_families: tuple[str, ...] = ()
    provider_feed_matched_count = 0
    provider_feed_selected_count = 0
    provider_feed_selected_products: tuple[dict[str, Any], ...] = ()
    provider_feed_decision_status: str | None = None
    provider_feed_recommended_product_id: str | None = None
    provider_feed_recommendation_reason_codes: tuple[str, ...] = ()
    provider_feed_recommendation_confidence: str | None = None
    selection_query = canonicalized_query or normalized_query or raw_query
    standard_provider_feed_path = bool(
        mega_category_id
        and provider_lookup_key not in _CONNECTED_PROVIDER_BY_CATEGORY
        and not offer_broad_suggestions
        and resolver_state != "blocked_or_unsafe"
    )
    feed_opportunity_attempt = _query_eligible_for_feed_opportunity_attempt(
        canonicalized_query=canonicalized_query,
        offer_broad_suggestions=offer_broad_suggestions,
        broad_suggestions=broad_suggestions,
        blocked_or_unsafe=blocked_or_unsafe,
        index_reason_codes=index_result.reason_codes,
    )
    should_check_provider_feed = bool(
        provider_lookup_key not in _CONNECTED_PROVIDER_BY_CATEGORY
        and resolver_state != "blocked_or_unsafe"
        and (standard_provider_feed_path or feed_opportunity_attempt)
    )
    if should_check_provider_feed:
        feed_metadata = resolve_search_provider_feed_metadata(
            mega_category_id=str(mega_category_id) if mega_category_id else None,
            manual_provider_connected=provider_status == "connected",
            allow_without_mega_category=feed_opportunity_attempt,
        )
        if feed_metadata is not None:
            provider_feed_status = feed_metadata.provider_feed_status
            provider_feed_reason_codes = feed_metadata.provider_feed_reason_codes
            provider_feed_eligible_count = feed_metadata.provider_feed_eligible_count
            reason_codes.append(f"provider_feed_status_{provider_feed_status}")

            recognized_product_search = bool(
                mega_category_id
                and status in _CONNECTED_STATUSES
                and not is_ambiguous_or_invalid
            )
            feed_opportunity_search = bool(
                feed_opportunity_attempt
                and not recognized_product_search
                and provider_feed_status == "provider_feed_ready"
            )
            if (
                provider_feed_status == "provider_feed_ready"
                and (recognized_product_search or feed_opportunity_search)
            ):
                selection = resolve_search_provider_feed_product_selection(
                    query=selection_query,
                    reading=concept_reading,
                )
                expose_selection = recognized_product_search or is_strong_feed_opportunity_selection(
                    selection
                )
                report_feed_opportunity_selection = bool(
                    feed_opportunity_search
                    and selection.status in {"selected", "insufficient_relevant_products"}
                )
                if expose_selection or report_feed_opportunity_selection:
                    provider_feed_selection_status = selection.status
                    provider_feed_selection_reason_codes = selection.reason_codes
                    provider_feed_unmatched_query_terms = selection.unmatched_query_terms
                    provider_feed_partially_matched_terms = selection.partially_matched_terms
                    provider_feed_ambiguous_product_families = (
                        selection.ambiguous_product_families
                    )
                    provider_feed_matched_count = selection.matched_count
                    provider_feed_selected_count = len(selection.selected_products)
                    recommendation = resolve_search_provider_feed_recommendation_decision(
                        query=selection_query,
                        selection=selection,
                    )
                    provider_feed_recommendation_reason_codes = recommendation.recommendation_reason_codes
                    provider_feed_recommendation_confidence = recommendation.recommendation_confidence
                    products_exposed = bool(
                        expose_selection and selection.status == "selected"
                    )
                    if products_exposed:
                        provider_feed_selected_products = tuple(
                            provider_product_to_backend_dict(product)
                            for product in selection.selected_products
                        )
                    if recommendation.decision_status == "recommended" and not products_exposed:
                        # A weak feed-opportunity selection is reported but not exposed.
                        # Claiming "recommended" with zero exposed products contradicts
                        # itself and breaks the runtime truth rules, which forbid
                        # overclaiming a recommendation without the evidence behind it.
                        provider_feed_decision_status = (
                            "recommendation_withheld_weak_feed_opportunity"
                        )
                        provider_feed_recommendation_confidence = "unknown"
                        reason_codes.append("provider_feed_recommendation_withheld")
                    else:
                        provider_feed_decision_status = recommendation.decision_status
                        if recommendation.decision_status == "recommended":
                            provider_feed_recommended_product_id = (
                                recommendation.recommended_product_id
                            )
                    reason_codes.append(
                        f"provider_feed_selection_status_{provider_feed_selection_status}"
                    )
                    reason_codes.extend(
                        f"provider_feed_selection_{code}" for code in selection.reason_codes
                    )
                    reason_codes.append(
                        f"provider_feed_decision_status_{provider_feed_decision_status}"
                    )
                    reason_codes.extend(
                        f"provider_feed_recommendation_{code}"
                        for code in provider_feed_recommendation_reason_codes
                    )
                    if feed_opportunity_search and expose_selection:
                        reason_codes.append("provider_feed_opportunity_gate")

    did_you_mean: tuple[str, ...] = ()
    if (
        not concept_understood
        and not provider_feed_selected_products
        and not offer_broad_suggestions
        and resolver_state != "blocked_or_unsafe"
        and _normalized_text(raw_query)
    ):
        did_you_mean = suggest_product_names(raw_query)
    understood_concept_name = None
    if concept_understood:
        concept = get_product_concepts_by_id().get(str(concept_reading.concept_id))
        if concept is not None:
            greek_query = concept_reading.head_language == "el"
            understood_concept_name = (
                concept.greek[0] if greek_query and concept.greek else concept.primary_english
            )
    return LiveSearchResolution(
        did_you_mean=did_you_mean,
        understood_concept_id=concept_reading.concept_id if concept_understood else None,
        understood_concept_name=understood_concept_name,
        understood_by_correction=bool(concept_understood and not concept_reading.exact),
        understood_specs=tuple(
            {
                "value": spec.token,
                "unit": spec.unit,
                "spec_field": spec.spec_field or "not_applicable",
                "typed": spec.source,
            }
            for spec in (concept_reading.specs if concept_understood else ())
        ),
        raw_query=raw_query,
        display_query=display_query,
        normalized_query=normalized_query,
        canonical_query=canonical_query,
        canonical_category=str(canonical_category) if canonical_category else None,
        mega_category_id=str(mega_category_id) if mega_category_id else None,
        display_name=str(category_probe.get("display_name") or "") or None,
        lower_level_provider_category=str(lower_level_provider_category) if lower_level_provider_category else None,
        intent=str(canonical_category or "unknown"),
        query_type=query_type,
        confidence=confidence,
        status=status,
        needs_review=needs_review,
        provider_key=provider_key,
        provider_status=provider_status,
        result_allowed=result_allowed,
        resolver_state=resolver_state,
        reason_codes=tuple(sorted(set(reason_codes))),
        suggestions=broad_suggestions if offer_broad_suggestions else (),
        provider_feed_status=provider_feed_status,
        provider_feed_reason_codes=provider_feed_reason_codes,
        provider_feed_eligible_count=provider_feed_eligible_count,
        provider_feed_selection_status=provider_feed_selection_status,
        provider_feed_selection_reason_codes=provider_feed_selection_reason_codes,
        provider_feed_unmatched_query_terms=provider_feed_unmatched_query_terms,
        provider_feed_partially_matched_terms=provider_feed_partially_matched_terms,
        provider_feed_ambiguous_product_families=provider_feed_ambiguous_product_families,
        provider_feed_matched_count=provider_feed_matched_count,
        provider_feed_selected_count=provider_feed_selected_count,
        provider_feed_selected_products=provider_feed_selected_products,
        provider_feed_decision_status=provider_feed_decision_status,
        provider_feed_recommended_product_id=provider_feed_recommended_product_id,
        provider_feed_recommendation_reason_codes=provider_feed_recommendation_reason_codes,
        provider_feed_recommendation_confidence=provider_feed_recommendation_confidence,
    )
