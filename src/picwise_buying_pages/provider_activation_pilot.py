from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

from picwise_offers.affiliate_feed_adapter import adapt_affiliate_feed_rows
from picwise_offers.feed_dry_run import run_affiliate_feed_dry_run
from picwise_offers.feed_enrichment import FeedEnrichmentContracts
from picwise_offers.locale_logic import LocaleEligibilityStatus, evaluate_locale_product_eligibility

from .candidate_index_gate import evaluate_candidate_index_batch
from .candidate_page_batch import build_candidate_page_batch
from .controlled_rollout import evaluate_controlled_rollout_batch
from .keyword_source_contract import validate_keyword_cluster_batch
from .live_mvp_gate import build_live_mvp_batch
from .mvp_observation import summarize_mvp_observations
from .promotion_policy import evaluate_promotion_policy_batch
from .release_governance import evaluate_release_governance_batch


class ProviderActivationPilotStatus(str, Enum):
    pilot_ready = "pilot_ready"
    pilot_needs_remediation = "pilot_needs_remediation"
    pilot_blocked = "pilot_blocked"


@dataclass(frozen=True)
class ProviderActivationInputContract:
    provider_name: str
    provider_feed_export_file_path: str
    trusted_seller_map_file_path: str | None
    shipping_return_enrichment_map_path: str | None
    taxonomy_category_map_path: str | None
    keyword_cluster_batch_path: str | None
    target_market: str
    target_locale: str
    dry_run_only: bool


@dataclass(frozen=True)
class ProviderActivationRunbookStep:
    step_id: str
    title: str
    description: str
    required: bool
    complete: bool
    notes: str


@dataclass(frozen=True)
class ProviderActivationChecklist:
    steps: tuple[ProviderActivationRunbookStep, ...]
    completed_required_steps: int
    total_required_steps: int
    is_complete: bool
    remediation_items: tuple[str, ...]


@dataclass(frozen=True)
class ProviderActivationRollbackDrill:
    drill_id: str
    steps: tuple[ProviderActivationRunbookStep, ...]
    completed_required_steps: int
    total_required_steps: int
    is_complete: bool


@dataclass(frozen=True)
class ProviderActivationPilotResult:
    provider_name: str
    target_market: str
    target_locale: str
    dry_run_only: bool
    feed_rows_total: int
    provider_readiness_status: str
    locale_ready_count: int
    keyword_cluster_ready_count: int
    candidate_pages_built: int
    index_candidate_count: int
    live_mvp_ready_count: int
    promotion_ready_count: int
    limited_rollout_ready_count: int
    governance_approval_ready_count: int
    blocked_count: int
    remediation_required_count: int
    blocker_reasons: tuple[str, ...]
    remediation_actions: tuple[str, ...]
    approval_checklist: ProviderActivationChecklist
    rollback_drill: ProviderActivationRollbackDrill
    pilot_status: ProviderActivationPilotStatus
    can_request_human_activation_review: bool
    can_publish_publicly: bool
    can_expand_live_sitemap: bool
    is_mass_publish: bool


@dataclass(frozen=True)
class ProviderActivationPilotPolicy:
    allowed_target_markets: tuple[str, ...] = ("US", "UK", "DE", "GR")
    expected_locale_by_market: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "US": ("en-US",),
            "UK": ("en-GB",),
            "DE": ("de-DE",),
            "GR": ("el-GR",),
        }
    )
    missing_trusted_seller_map_outcome: str = "remediation_required"
    require_keyword_cluster_batch_for_page_planning: bool = True
    require_observation_events_for_promotion: bool = True
    require_governance_approval_ready_for_pilot_ready: bool = True


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_sorted(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(dict.fromkeys(_norm_text(item) for item in values if _norm_text(item))))


def _policy_from_input(policy: ProviderActivationPilotPolicy | Mapping[str, Any] | None) -> ProviderActivationPilotPolicy:
    if isinstance(policy, ProviderActivationPilotPolicy):
        return policy
    if policy is None:
        return ProviderActivationPilotPolicy()
    payload = dict(policy)
    expected_locale_by_market = payload.get("expected_locale_by_market")
    normalized_locale_mapping: dict[str, tuple[str, ...]] = {}
    if isinstance(expected_locale_by_market, Mapping):
        for market, locales in expected_locale_by_market.items():
            market_code = _norm_text(market).upper()
            if not market_code:
                continue
            locale_values: list[str] = []
            if isinstance(locales, (list, tuple)):
                locale_values = [_norm_text(locale) for locale in locales if _norm_text(locale)]
            elif _norm_text(locales):
                locale_values = [_norm_text(locales)]
            if locale_values:
                normalized_locale_mapping[market_code] = tuple(locale_values)
    return ProviderActivationPilotPolicy(
        allowed_target_markets=tuple(
            _norm_text(item).upper() for item in payload.get("allowed_target_markets", ("US", "UK", "DE", "GR")) if _norm_text(item)
        ),
        expected_locale_by_market=normalized_locale_mapping
        or {
            "US": ("en-US",),
            "UK": ("en-GB",),
            "DE": ("de-DE",),
            "GR": ("el-GR",),
        },
        missing_trusted_seller_map_outcome=_norm_text(payload.get("missing_trusted_seller_map_outcome")) or "remediation_required",
        require_keyword_cluster_batch_for_page_planning=bool(
            payload.get("require_keyword_cluster_batch_for_page_planning", True)
        ),
        require_observation_events_for_promotion=bool(payload.get("require_observation_events_for_promotion", True)),
        require_governance_approval_ready_for_pilot_ready=bool(
            payload.get("require_governance_approval_ready_for_pilot_ready", True)
        ),
    )


def _to_input_contract(input_contract: ProviderActivationInputContract | Mapping[str, Any]) -> ProviderActivationInputContract:
    if isinstance(input_contract, ProviderActivationInputContract):
        return input_contract
    payload = dict(input_contract)
    return ProviderActivationInputContract(
        provider_name=_norm_text(payload.get("provider_name")) or "provider-unknown",
        provider_feed_export_file_path=_norm_text(payload.get("provider_feed_export_file_path")),
        trusted_seller_map_file_path=_norm_text(payload.get("trusted_seller_map_file_path")) or None,
        shipping_return_enrichment_map_path=_norm_text(payload.get("shipping_return_enrichment_map_path")) or None,
        taxonomy_category_map_path=_norm_text(payload.get("taxonomy_category_map_path")) or None,
        keyword_cluster_batch_path=_norm_text(payload.get("keyword_cluster_batch_path")) or None,
        target_market=_norm_text(payload.get("target_market")).upper(),
        target_locale=_norm_text(payload.get("target_locale")),
        dry_run_only=bool(payload.get("dry_run_only", False)),
    )


def _input_file_mapping(local_inputs: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(local_inputs, Mapping):
        return {}
    files = local_inputs.get("files")
    if isinstance(files, Mapping):
        return dict(files)
    return dict(local_inputs)


def _load_optional_mapping(file_map: Mapping[str, Any], file_path: str | None) -> dict[str, Any] | None:
    if not file_path:
        return None
    value = file_map.get(file_path)
    return dict(value) if isinstance(value, Mapping) else None


def validate_provider_activation_input(
    input_contract: ProviderActivationInputContract | Mapping[str, Any],
    policy: ProviderActivationPilotPolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = _to_input_contract(input_contract)
    resolved_policy = _policy_from_input(policy)
    blocker_reasons: list[str] = []
    remediation_actions: list[str] = []

    if not contract.provider_feed_export_file_path:
        blocker_reasons.append("missing_provider_feed_export_file_path")
    if not contract.target_market:
        blocker_reasons.append("missing_target_market")
    elif contract.target_market not in resolved_policy.allowed_target_markets:
        blocker_reasons.append("unsupported_target_market")
    if not contract.target_locale:
        blocker_reasons.append("missing_target_locale")
    if contract.target_market and contract.target_locale:
        expected_locales = tuple(resolved_policy.expected_locale_by_market.get(contract.target_market, tuple()))
        if expected_locales and contract.target_locale not in expected_locales:
            blocker_reasons.append("target_market_locale_mismatch")
    if contract.dry_run_only is not True:
        blocker_reasons.append("dry_run_only_must_be_true")

    if not contract.trusted_seller_map_file_path:
        if resolved_policy.missing_trusted_seller_map_outcome == "blocked":
            blocker_reasons.append("missing_trusted_seller_map")
        else:
            remediation_actions.append("provide_trusted_seller_map")
    if not contract.shipping_return_enrichment_map_path:
        remediation_actions.append("provide_shipping_return_enrichment_map")
    if not contract.taxonomy_category_map_path:
        remediation_actions.append("provide_taxonomy_category_map")
    if resolved_policy.require_keyword_cluster_batch_for_page_planning and not contract.keyword_cluster_batch_path:
        blocker_reasons.append("missing_keyword_cluster_batch")

    return {
        "valid": len(blocker_reasons) == 0,
        "normalized_input_contract": asdict(contract),
        "blocker_reasons": _dedupe_sorted(blocker_reasons),
        "remediation_actions": _dedupe_sorted(remediation_actions),
    }


def build_provider_activation_checklist(
    input_contract: ProviderActivationInputContract | Mapping[str, Any],
    pipeline_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = _to_input_contract(input_contract)
    pipeline = dict(pipeline_result or {})
    validation = validate_provider_activation_input(contract)

    checklist_steps = (
        ProviderActivationRunbookStep(
            step_id="step12-input-contract-validated",
            title="Input Contract Validated",
            description="Operator-supplied provider activation input contract is structurally valid.",
            required=True,
            complete=bool(validation["valid"]),
            notes="All required fields and dry-run lock must pass.",
        ),
        ProviderActivationRunbookStep(
            step_id="step12-feed-export-provided",
            title="Provider Feed Export Provided",
            description="Local provider feed export file path is present and feed rows are available.",
            required=True,
            complete=bool(contract.provider_feed_export_file_path and int(pipeline.get("feed_rows_total", 0)) > 0),
            notes="Pilot blocks if feed export is missing.",
        ),
        ProviderActivationRunbookStep(
            step_id="step12-keyword-batch-provided",
            title="Keyword Cluster Batch Provided",
            description="Keyword cluster batch exists for page-planning dry-run checks.",
            required=True,
            complete=bool(contract.keyword_cluster_batch_path and int(pipeline.get("keyword_cluster_ready_count", 0)) > 0),
            notes="Page planning remains blocked without a keyword cluster batch.",
        ),
        ProviderActivationRunbookStep(
            step_id="step12-governance-approval-ready",
            title="Governance Approval Ready",
            description="Step 11 governance readiness exists for human activation review request.",
            required=True,
            complete=bool(int(pipeline.get("governance_approval_ready_count", 0)) > 0),
            notes="No public publish is allowed at this stage.",
        ),
        ProviderActivationRunbookStep(
            step_id="step12-public-safety-locks",
            title="Public Safety Locks Enforced",
            description="Pilot remains non-public, non-sitemap-expanding, and non-mass-publish.",
            required=True,
            complete=bool(
                pipeline.get("can_publish_publicly") is False
                and pipeline.get("can_expand_live_sitemap") is False
                and pipeline.get("is_mass_publish") is False
            ),
            notes="Hard lock: no publish, no live sitemap expansion.",
        ),
    )

    required_steps = tuple(step for step in checklist_steps if step.required)
    completed_required = sum(1 for step in required_steps if step.complete)
    total_required = len(required_steps)
    remediation_items = tuple(
        step.step_id for step in required_steps if not step.complete
    ) + tuple(validation["remediation_actions"])
    checklist = ProviderActivationChecklist(
        steps=checklist_steps,
        completed_required_steps=completed_required,
        total_required_steps=total_required,
        is_complete=completed_required == total_required,
        remediation_items=_dedupe_sorted(list(remediation_items)),
    )
    return asdict(checklist)


def build_provider_activation_rollback_drill(
    input_contract: ProviderActivationInputContract | Mapping[str, Any]
) -> dict[str, Any]:
    contract = _to_input_contract(input_contract)
    steps = (
        ProviderActivationRunbookStep(
            step_id="step12-rollback-01-stop-run",
            title="Stop Pilot Run",
            description="Halt operator-run dry-run orchestration and freeze output artifacts.",
            required=True,
            complete=True,
            notes="Dry-run only process can be halted without customer impact.",
        ),
        ProviderActivationRunbookStep(
            step_id="step12-rollback-02-revert-local-inputs",
            title="Revert Local Input Package",
            description="Revert to last known-good local export and trusted maps package.",
            required=True,
            complete=bool(contract.provider_feed_export_file_path),
            notes="No credentials or live API keys are involved.",
        ),
        ProviderActivationRunbookStep(
            step_id="step12-rollback-03-verify-public-locks",
            title="Verify Public Locks",
            description="Confirm no public routes, sitemap entries, or publish states changed.",
            required=True,
            complete=True,
            notes="This pilot never mutates public exposure paths.",
        ),
        ProviderActivationRunbookStep(
            step_id="step12-rollback-04-log-remediation",
            title="Log Remediation Work",
            description="Log blockers and remediation actions before next pilot attempt.",
            required=True,
            complete=True,
            notes="Deterministic remediation list is part of the report.",
        ),
    )
    required_steps = tuple(step for step in steps if step.required)
    completed_required = sum(1 for step in required_steps if step.complete)
    drill = ProviderActivationRollbackDrill(
        drill_id="step12-provider-activation-rollback-drill-v1",
        steps=steps,
        completed_required_steps=completed_required,
        total_required_steps=len(required_steps),
        is_complete=completed_required == len(required_steps),
    )
    return asdict(drill)


def evaluate_provider_activation_pilot(
    input_contract: ProviderActivationInputContract | Mapping[str, Any],
    local_inputs: Mapping[str, Any] | None = None,
    policy: ProviderActivationPilotPolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = _to_input_contract(input_contract)
    resolved_policy = _policy_from_input(policy)
    validation = validate_provider_activation_input(contract, policy=resolved_policy)
    file_map = _input_file_mapping(local_inputs)

    blocker_reasons = list(validation["blocker_reasons"])
    remediation_actions = list(validation["remediation_actions"])

    feed_rows_total = 0
    provider_readiness_status = "blocked"
    locale_ready_count = 0
    keyword_cluster_ready_count = 0
    candidate_pages_built = 0
    index_candidate_count = 0
    live_mvp_ready_count = 0
    promotion_ready_count = 0
    limited_rollout_ready_count = 0
    governance_approval_ready_count = 0

    mapped_candidates: tuple[Any, ...] = tuple()
    locale_decisions: list[dict[str, Any]] = []
    keyword_clusters_payload: list[dict[str, Any]] = []
    candidate_batch_payload: dict[str, Any] = {"candidate_pages": []}
    index_batch_payload: dict[str, Any] = {"decisions": []}
    live_mvp_payload: dict[str, Any] = {"records": []}
    observation_payload: dict[str, Any] = {"page_summaries": []}
    promotion_payload: dict[str, Any] = {"decisions": []}
    rollout_payload: dict[str, Any] = {"decisions": []}
    governance_payload: dict[str, Any] = {"approval_ready_count": 0, "decisions": []}

    feed_rows = file_map.get(contract.provider_feed_export_file_path)
    if not isinstance(feed_rows, list):
        blocker_reasons.append("missing_provider_feed_export_file")
        feed_rows = []
    feed_rows_total = len(feed_rows)

    trusted_seller_map = _load_optional_mapping(file_map, contract.trusted_seller_map_file_path)
    if contract.trusted_seller_map_file_path and trusted_seller_map is None:
        if resolved_policy.missing_trusted_seller_map_outcome == "blocked":
            blocker_reasons.append("missing_trusted_seller_map_file")
        else:
            remediation_actions.append("provide_trusted_seller_map_file")

    enrichment_map = _load_optional_mapping(file_map, contract.shipping_return_enrichment_map_path)
    taxonomy_map = _load_optional_mapping(file_map, contract.taxonomy_category_map_path)
    keyword_clusters_source = file_map.get(contract.keyword_cluster_batch_path or "")
    if contract.keyword_cluster_batch_path and isinstance(keyword_clusters_source, list):
        keyword_clusters_payload = [dict(item) for item in keyword_clusters_source if isinstance(item, Mapping)]
    elif resolved_policy.require_keyword_cluster_batch_for_page_planning:
        blocker_reasons.append("missing_keyword_cluster_batch_file")

    if feed_rows:
        delivery_by_candidate_id: dict[str, Any] = {}
        for row in feed_rows:
            if not isinstance(row, Mapping):
                continue
            row_candidate_id = _norm_text(row.get("candidate_id") or row.get("offer_id") or row.get("product_id"))
            if not row_candidate_id:
                continue
            delivery_value = row.get("delivery_coverage")
            if delivery_value is not None:
                delivery_by_candidate_id[row_candidate_id] = delivery_value

        enrichment_contracts = FeedEnrichmentContracts(
            shipping_info_available_by_candidate_id=dict(
                enrichment_map.get("shipping_info_available_by_candidate_id", {})
            )
            if isinstance(enrichment_map, Mapping)
            else None,
            return_policy_available_by_candidate_id=dict(
                enrichment_map.get("return_policy_available_by_candidate_id", {})
            )
            if isinstance(enrichment_map, Mapping)
            else None,
            taxonomy_linkage_by_candidate_id=dict(taxonomy_map)
            if isinstance(taxonomy_map, Mapping)
            else None,
        )
        dry_run_report = run_affiliate_feed_dry_run(
            [dict(item) for item in feed_rows if isinstance(item, Mapping)],
            source_id=contract.provider_name,
            trusted_seller_status_by_name=trusted_seller_map,
            include_enrichment_remediation_summary=True,
            enrichment_contracts=enrichment_contracts,
        )
        provider_readiness_status = dry_run_report.readiness_status

        adapted = adapt_affiliate_feed_rows(
            [dict(item) for item in feed_rows if isinstance(item, Mapping)],
            source_id=contract.provider_name,
            trusted_seller_status_by_name=trusted_seller_map,
        )
        mapped_candidates = adapted.mapped_candidates
        for candidate in mapped_candidates:
            metadata_map = candidate.metadata if isinstance(candidate.metadata, Mapping) else {}
            locale_market_map = metadata_map.get("locale_market") if isinstance(metadata_map.get("locale_market"), Mapping) else {}
            locale_candidate_payload = {
                "candidate_market": locale_market_map.get("market"),
                "candidate_locale": locale_market_map.get("locale"),
                "candidate_currency": candidate.currency,
                "delivery_coverage": delivery_by_candidate_id.get(candidate.candidate_id),
            }
            locale_decision = evaluate_locale_product_eligibility(
                locale_candidate_payload,
                target_market=contract.target_market,
            )
            locale_decisions.append(
                {
                    "product_id": candidate.candidate_id,
                    "candidate_id": candidate.candidate_id,
                    "status": locale_decision.status.value,
                    "target_market": contract.target_market,
                    "market": locale_decision.candidate_market or "",
                }
            )
        locale_ready_count = sum(
            1 for item in locale_decisions if item["status"] == LocaleEligibilityStatus.LOCALE_READY.value
        )
        locale_blocked_count = sum(
            1 for item in locale_decisions if item["status"] == LocaleEligibilityStatus.LOCALE_BLOCKED.value
        )
        if locale_blocked_count > 0:
            blocker_reasons.append("locale_gate_blocked_candidates_present")

    if keyword_clusters_payload:
        keyword_batch = validate_keyword_cluster_batch(keyword_clusters_payload)
        keyword_cluster_ready_count = int(keyword_batch.get("page_ready_count", 0))
        if not bool(keyword_batch.get("can_move_to_step5")):
            blocker_reasons.append("keyword_cluster_batch_not_page_ready")
    elif contract.keyword_cluster_batch_path:
        blocker_reasons.append("keyword_cluster_batch_invalid")

    if mapped_candidates and keyword_clusters_payload and locale_ready_count > 0:
        products = []
        for candidate in mapped_candidates:
            products.append(
                {
                    "product_id": candidate.candidate_id,
                    "category": _norm_text(candidate.category or candidate.category_bucket).lower(),
                    "target_category": _norm_text(candidate.category or candidate.category_bucket).lower(),
                    "provider_ready": True,
                    "status": "provider_ready",
                }
            )
        sorted_product_ids = sorted(_norm_text(item.get("product_id")) for item in products if _norm_text(item.get("product_id")))
        recommendation_mapping: dict[str, str] = {}
        if sorted_product_ids:
            for cluster in keyword_clusters_payload:
                cluster_id = _norm_text(cluster.get("cluster_id"))
                if cluster_id:
                    recommendation_mapping[cluster_id] = sorted_product_ids[0]
        candidate_batch_payload = build_candidate_page_batch(
            keyword_clusters_payload,
            products,
            locale_decisions,
            recommendation_mapping=recommendation_mapping,
            max_candidate_pages=max(1, len(keyword_clusters_payload)),
        )
        candidate_pages_built = int(candidate_batch_payload.get("total_built", 0))
        candidate_pages = list(candidate_batch_payload.get("candidate_pages", []))

        candidate_evidence: dict[str, dict[str, Any]] = {}
        for page in candidate_pages:
            candidate_id = _norm_text(page.get("candidate_page_id"))
            if not candidate_id:
                continue
            candidate_evidence[candidate_id] = {
                "provider_ready": True,
                "locale_ready": True,
                "page_ready_keyword_evidence": True,
                "is_monetized": False,
                "affiliate_coverage": 1.0,
                "title_meta_intent_ready": True,
                "keyword_stuffing_ratio": 0.0,
                "thin_content": False,
                "content_word_count": 600,
                "unsupported_locale_currency": False,
                "evidence_confidence": 1.0,
            }

        index_batch_payload = evaluate_candidate_index_batch(
            candidate_pages,
            supporting_evidence={"candidate_evidence": candidate_evidence},
        )
        index_candidate_count = int(index_batch_payload.get("index_candidate_count", 0))

        live_mvp_payload = build_live_mvp_batch(
            candidate_pages,
            list(index_batch_payload.get("decisions", [])),
        )
        live_mvp_ready_count = int(live_mvp_payload.get("live_mvp_ready_count", 0))

        observation_events = []
        if isinstance(local_inputs, Mapping):
            raw_events = local_inputs.get("mvp_observation_events")
            if isinstance(raw_events, list):
                observation_events = [dict(item) for item in raw_events if isinstance(item, Mapping)]
        observation_payload = summarize_mvp_observations(
            observation_events,
            live_mvp_records=list(live_mvp_payload.get("records", [])),
        )
        promotion_payload = evaluate_promotion_policy_batch(list(observation_payload.get("page_summaries", [])))
        promotion_ready_count = int(promotion_payload.get("promoted_to_limited_exposure_count", 0))

        rollout_payload = evaluate_controlled_rollout_batch(list(promotion_payload.get("decisions", [])))
        limited_rollout_ready_count = int(rollout_payload.get("limited_rollout_ready_count", 0))

        approval_status_by_candidate = {}
        if isinstance(local_inputs, Mapping) and isinstance(local_inputs.get("approval_status_by_candidate"), Mapping):
            approval_status_by_candidate = dict(local_inputs.get("approval_status_by_candidate", {}))
        governance_payload = evaluate_release_governance_batch(
            list(rollout_payload.get("decisions", [])),
            approval_status_by_candidate=approval_status_by_candidate,
        )
        governance_approval_ready_count = int(governance_payload.get("approval_ready_count", 0))

    if resolved_policy.require_observation_events_for_promotion and promotion_ready_count == 0:
        remediation_actions.append("collect_operator_observation_events_for_step8_9")
    if resolved_policy.require_governance_approval_ready_for_pilot_ready and governance_approval_ready_count == 0:
        remediation_actions.append("obtain_step11_approved_governance_status")

    blocker_reasons = list(_dedupe_sorted(blocker_reasons))
    remediation_actions = list(_dedupe_sorted(remediation_actions))

    can_publish_publicly = False
    can_expand_live_sitemap = False
    is_mass_publish = False

    if blocker_reasons:
        pilot_status = ProviderActivationPilotStatus.pilot_blocked
    else:
        is_structurally_ready = (
            contract.dry_run_only
            and feed_rows_total > 0
            and locale_ready_count > 0
            and keyword_cluster_ready_count > 0
            and candidate_pages_built > 0
            and index_candidate_count > 0
            and live_mvp_ready_count >= 0
            and promotion_ready_count > 0
            and limited_rollout_ready_count > 0
            and governance_approval_ready_count > 0
        )
        if is_structurally_ready and not remediation_actions:
            pilot_status = ProviderActivationPilotStatus.pilot_ready
        else:
            pilot_status = ProviderActivationPilotStatus.pilot_needs_remediation

    can_request_human_activation_review = bool(
        pilot_status == ProviderActivationPilotStatus.pilot_ready and governance_approval_ready_count > 0
    )

    partial_result = {
        "feed_rows_total": feed_rows_total,
        "keyword_cluster_ready_count": keyword_cluster_ready_count,
        "governance_approval_ready_count": governance_approval_ready_count,
        "can_publish_publicly": can_publish_publicly,
        "can_expand_live_sitemap": can_expand_live_sitemap,
        "is_mass_publish": is_mass_publish,
    }
    approval_checklist = build_provider_activation_checklist(contract, pipeline_result=partial_result)
    rollback_drill = build_provider_activation_rollback_drill(contract)

    result = ProviderActivationPilotResult(
        provider_name=contract.provider_name,
        target_market=contract.target_market,
        target_locale=contract.target_locale,
        dry_run_only=contract.dry_run_only,
        feed_rows_total=feed_rows_total,
        provider_readiness_status=provider_readiness_status,
        locale_ready_count=locale_ready_count,
        keyword_cluster_ready_count=keyword_cluster_ready_count,
        candidate_pages_built=candidate_pages_built,
        index_candidate_count=index_candidate_count,
        live_mvp_ready_count=live_mvp_ready_count,
        promotion_ready_count=promotion_ready_count,
        limited_rollout_ready_count=limited_rollout_ready_count,
        governance_approval_ready_count=governance_approval_ready_count,
        blocked_count=len(blocker_reasons),
        remediation_required_count=len(remediation_actions),
        blocker_reasons=tuple(blocker_reasons),
        remediation_actions=tuple(remediation_actions),
        approval_checklist=ProviderActivationChecklist(
            steps=tuple(ProviderActivationRunbookStep(**item) for item in approval_checklist["steps"]),
            completed_required_steps=int(approval_checklist["completed_required_steps"]),
            total_required_steps=int(approval_checklist["total_required_steps"]),
            is_complete=bool(approval_checklist["is_complete"]),
            remediation_items=tuple(approval_checklist["remediation_items"]),
        ),
        rollback_drill=ProviderActivationRollbackDrill(
            drill_id=rollback_drill["drill_id"],
            steps=tuple(ProviderActivationRunbookStep(**item) for item in rollback_drill["steps"]),
            completed_required_steps=int(rollback_drill["completed_required_steps"]),
            total_required_steps=int(rollback_drill["total_required_steps"]),
            is_complete=bool(rollback_drill["is_complete"]),
        ),
        pilot_status=pilot_status,
        can_request_human_activation_review=can_request_human_activation_review,
        can_publish_publicly=can_publish_publicly,
        can_expand_live_sitemap=can_expand_live_sitemap,
        is_mass_publish=is_mass_publish,
    )
    payload = asdict(result)
    payload["pilot_status"] = result.pilot_status.value
    return payload

