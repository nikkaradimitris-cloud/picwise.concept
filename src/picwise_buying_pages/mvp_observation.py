from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping


class MVPObservationEventType(str, Enum):
    preview_rendered = "preview_rendered"
    outbound_click = "outbound_click"
    preview_error = "preview_error"
    outbound_error = "outbound_error"
    manual_review_opened = "manual_review_opened"
    blocker_detected = "blocker_detected"


class MVPObservationStatus(str, Enum):
    observation_ready = "observation_ready"
    needs_more_data = "needs_more_data"
    hold_manual_review = "hold_manual_review"
    blocked = "blocked"


@dataclass(frozen=True)
class MVPObservationEvent:
    event_id: str
    candidate_page_id: str
    slug: str
    event_type: MVPObservationEventType
    timestamp: str
    source: str
    test_mode: bool
    operator_generated: bool
    locale: str
    market: str
    product_id: str | None
    outbound_url: str | None
    metadata: Mapping[str, Any]
    rejected_reason: str | None = None


@dataclass(frozen=True)
class MVPPageObservationSummary:
    candidate_page_id: str
    slug: str
    locale: str
    market: str
    is_live_mvp_ready: bool
    controlled_and_reversible: bool
    total_events: int
    preview_render_count: int
    outbound_click_count: int
    preview_error_count: int
    outbound_error_count: int
    manual_review_count: int
    blocker_event_count: int
    rejected_event_count: int
    status: MVPObservationStatus
    promotion_ready: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class MVPObservationBatchResult:
    total_events: int
    accepted_events: int
    rejected_events: int
    preview_render_count: int
    outbound_click_count: int
    preview_error_count: int
    outbound_error_count: int
    manual_review_count: int
    blocker_event_count: int
    unique_candidate_pages_observed: int
    page_summaries: tuple[MVPPageObservationSummary, ...]
    status_counts: dict[str, int]
    rejected_reason_counts: dict[str, int]
    promotion_ready_count: int
    hold_manual_review_count: int
    blocked_count: int
    can_move_to_step9: bool


@dataclass(frozen=True)
class MVPPromotionPolicy:
    min_preview_events_required: int = 1
    min_outbound_click_events_required: int = 1
    min_observation_events_coverage: int = 2
    max_outbound_error_events_allowed: int = 0
    max_preview_error_events_allowed: int = 0
    allow_coverage_without_outbound_click: bool = True
    require_controlled_reversible: bool = True


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _norm_upper(value: Any) -> str:
    return _norm_text(value).upper()


def _is_explicit_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _parse_timestamp(value: Any) -> str | None:
    raw = _norm_text(value)
    if not raw:
        return None
    normalized = raw
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_counts(summaries: Iterable[MVPPageObservationSummary]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for summary in summaries:
        key = summary.status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_rejections(events: Iterable[MVPObservationEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        reason = _norm_text(event.rejected_reason)
        if reason:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _event_to_payload(event: MVPObservationEvent) -> dict[str, Any]:
    payload = asdict(event)
    payload["event_type"] = event.event_type.value
    payload["metadata"] = dict(event.metadata)
    return payload


def _summary_to_payload(summary: MVPPageObservationSummary) -> dict[str, Any]:
    payload = asdict(summary)
    payload["status"] = summary.status.value
    return payload


def _policy_from_input(policy: MVPPromotionPolicy | None) -> MVPPromotionPolicy:
    return policy if policy is not None else MVPPromotionPolicy()


def _contains_fabricated_metrics(payload: Mapping[str, Any]) -> bool:
    forbidden_keys = {
        "revenue",
        "revenues",
        "conversion",
        "conversions",
        "impressions",
        "search_volume",
    }
    for key in payload.keys():
        if _norm_text(key).lower() in forbidden_keys:
            return True
    return False


def validate_mvp_observation_event(event_input: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(event_input or {})
    event_type_raw = _norm_text(payload.get("event_type"))
    timestamp = _parse_timestamp(payload.get("timestamp"))
    candidate_page_id = _norm_text(payload.get("candidate_page_id"))
    slug = _norm_text(payload.get("slug"))
    test_mode = payload.get("test_mode")
    operator_generated = payload.get("operator_generated")
    metadata = payload.get("metadata")
    metadata_map = dict(metadata) if isinstance(metadata, Mapping) else {}

    rejected_reason: str | None = None

    if not candidate_page_id:
        rejected_reason = "missing_candidate_page_id"
    elif not slug:
        rejected_reason = "missing_slug"
    elif not event_type_raw:
        rejected_reason = "missing_event_type"
    elif event_type_raw not in {item.value for item in MVPObservationEventType}:
        rejected_reason = "invalid_event_type"
    elif not timestamp:
        rejected_reason = "invalid_timestamp"
    elif not _is_explicit_bool(test_mode):
        rejected_reason = "test_mode_flag_must_be_explicit_boolean"
    elif not _is_explicit_bool(operator_generated):
        rejected_reason = "operator_generated_flag_must_be_explicit_boolean"
    elif _contains_fabricated_metrics(payload) or _contains_fabricated_metrics(metadata_map):
        rejected_reason = "fabricated_revenue_or_conversion_metrics_not_allowed"
    elif event_type_raw == MVPObservationEventType.outbound_click.value:
        if not _norm_text(payload.get("product_id")):
            rejected_reason = "outbound_click_missing_product_id"
        elif not _norm_text(payload.get("outbound_url")):
            rejected_reason = "outbound_click_missing_outbound_url"

    event = MVPObservationEvent(
        event_id=_norm_text(payload.get("event_id")) or "event-id-missing",
        candidate_page_id=candidate_page_id,
        slug=slug,
        event_type=MVPObservationEventType(event_type_raw)
        if event_type_raw in {item.value for item in MVPObservationEventType}
        else MVPObservationEventType.preview_error,
        timestamp=timestamp or "1970-01-01T00:00:00Z",
        source=_norm_text(payload.get("source")) or "local_observation",
        test_mode=bool(test_mode) if isinstance(test_mode, bool) else False,
        operator_generated=bool(operator_generated) if isinstance(operator_generated, bool) else False,
        locale=_norm_text(payload.get("locale")),
        market=_norm_upper(payload.get("market")),
        product_id=_norm_text(payload.get("product_id")) or None,
        outbound_url=_norm_text(payload.get("outbound_url")) or None,
        metadata=metadata_map,
        rejected_reason=rejected_reason,
    )
    accepted = rejected_reason is None
    return {
        "accepted": accepted,
        "rejected_reason": rejected_reason,
        "event": _event_to_payload(event),
    }


def evaluate_mvp_promotion_readiness(
    page_summary: Mapping[str, Any],
    policy: MVPPromotionPolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    summary = dict(page_summary or {})

    is_live_mvp_ready = bool(summary.get("is_live_mvp_ready"))
    controlled_and_reversible = bool(summary.get("controlled_and_reversible", True))
    preview_render_count = int(summary.get("preview_render_count") or 0)
    outbound_click_count = int(summary.get("outbound_click_count") or 0)
    total_events = int(summary.get("total_events") or 0)
    outbound_error_count = int(summary.get("outbound_error_count") or 0)
    preview_error_count = int(summary.get("preview_error_count") or 0)
    blocker_event_count = int(summary.get("blocker_event_count") or 0)
    manual_review_count = int(summary.get("manual_review_count") or 0)

    reasons: list[str] = []
    status = MVPObservationStatus.needs_more_data
    promotion_ready = False

    if not is_live_mvp_ready:
        status = MVPObservationStatus.blocked
        reasons.append("not_live_mvp_ready")
    elif resolved_policy.require_controlled_reversible and not controlled_and_reversible:
        status = MVPObservationStatus.blocked
        reasons.append("must_remain_controlled_and_reversible")
    elif blocker_event_count > 0:
        status = MVPObservationStatus.blocked
        reasons.append("blocker_events_present")
    elif outbound_error_count > resolved_policy.max_outbound_error_events_allowed:
        status = MVPObservationStatus.hold_manual_review
        reasons.append("outbound_error_threshold_exceeded")
    elif manual_review_count > 0:
        status = MVPObservationStatus.hold_manual_review
        reasons.append("manual_review_opened")
    elif preview_error_count > resolved_policy.max_preview_error_events_allowed:
        status = MVPObservationStatus.hold_manual_review
        reasons.append("preview_error_threshold_exceeded")
    else:
        has_preview_evidence = preview_render_count >= resolved_policy.min_preview_events_required
        has_outbound_evidence = outbound_click_count >= resolved_policy.min_outbound_click_events_required
        has_coverage = total_events >= resolved_policy.min_observation_events_coverage

        if not has_preview_evidence:
            status = MVPObservationStatus.needs_more_data
            reasons.append("preview_evidence_missing")
        elif not has_outbound_evidence and not (
            resolved_policy.allow_coverage_without_outbound_click and has_coverage
        ):
            status = MVPObservationStatus.needs_more_data
            reasons.append("outbound_or_coverage_evidence_missing")
        else:
            status = MVPObservationStatus.observation_ready
            promotion_ready = True
            reasons.append("promotion_readiness_contract_satisfied")

    return {
        "status": status.value,
        "promotion_ready": promotion_ready,
        "reasons": tuple(reasons),
    }


def summarize_mvp_observations(
    events: Iterable[Mapping[str, Any]],
    live_mvp_records: Iterable[Mapping[str, Any]] | None = None,
    policy: MVPPromotionPolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    event_inputs = [dict(event) for event in events]
    validated_events = [validate_mvp_observation_event(item) for item in event_inputs]

    accepted_events = [
        MVPObservationEvent(
            event_id=item["event"]["event_id"],
            candidate_page_id=item["event"]["candidate_page_id"],
            slug=item["event"]["slug"],
            event_type=MVPObservationEventType(item["event"]["event_type"]),
            timestamp=item["event"]["timestamp"],
            source=item["event"]["source"],
            test_mode=bool(item["event"]["test_mode"]),
            operator_generated=bool(item["event"]["operator_generated"]),
            locale=item["event"]["locale"],
            market=item["event"]["market"],
            product_id=item["event"]["product_id"],
            outbound_url=item["event"]["outbound_url"],
            metadata=dict(item["event"]["metadata"]),
            rejected_reason=item["event"]["rejected_reason"],
        )
        for item in validated_events
        if item["accepted"]
    ]
    rejected_events = [
        MVPObservationEvent(
            event_id=item["event"]["event_id"],
            candidate_page_id=item["event"]["candidate_page_id"],
            slug=item["event"]["slug"],
            event_type=MVPObservationEventType(item["event"]["event_type"]),
            timestamp=item["event"]["timestamp"],
            source=item["event"]["source"],
            test_mode=bool(item["event"]["test_mode"]),
            operator_generated=bool(item["event"]["operator_generated"]),
            locale=item["event"]["locale"],
            market=item["event"]["market"],
            product_id=item["event"]["product_id"],
            outbound_url=item["event"]["outbound_url"],
            metadata=dict(item["event"]["metadata"]),
            rejected_reason=item["event"]["rejected_reason"],
        )
        for item in validated_events
        if not item["accepted"]
    ]

    live_records = [dict(record) for record in (live_mvp_records or ())]
    live_records_by_id: dict[str, dict[str, Any]] = {}
    for record in live_records:
        candidate_page_id = _norm_text(record.get("candidate_page_id"))
        if candidate_page_id:
            live_records_by_id[candidate_page_id] = record

    accepted_by_page: dict[str, list[MVPObservationEvent]] = {}
    for event in accepted_events:
        accepted_by_page.setdefault(event.candidate_page_id, []).append(event)

    rejected_by_page: dict[str, list[MVPObservationEvent]] = {}
    for event in rejected_events:
        candidate_page_id = _norm_text(event.candidate_page_id)
        if candidate_page_id:
            rejected_by_page.setdefault(candidate_page_id, []).append(event)

    page_ids = sorted(set(accepted_by_page.keys()) | set(live_records_by_id.keys()))
    page_summaries: list[MVPPageObservationSummary] = []
    for candidate_page_id in page_ids:
        accepted_for_page = accepted_by_page.get(candidate_page_id, [])
        rejected_for_page = rejected_by_page.get(candidate_page_id, [])
        live_record = live_records_by_id.get(candidate_page_id, {})
        slug = _norm_text(live_record.get("slug"))
        locale = _norm_text(live_record.get("locale"))
        market = _norm_upper(live_record.get("market"))
        if accepted_for_page and not slug:
            slug = accepted_for_page[0].slug
        if accepted_for_page and not locale:
            locale = accepted_for_page[0].locale
        if accepted_for_page and not market:
            market = accepted_for_page[0].market

        counts = {
            MVPObservationEventType.preview_rendered.value: 0,
            MVPObservationEventType.outbound_click.value: 0,
            MVPObservationEventType.preview_error.value: 0,
            MVPObservationEventType.outbound_error.value: 0,
            MVPObservationEventType.manual_review_opened.value: 0,
            MVPObservationEventType.blocker_detected.value: 0,
        }
        for event in accepted_for_page:
            counts[event.event_type.value] = counts.get(event.event_type.value, 0) + 1

        is_live_mvp_ready = _norm_text(live_record.get("exposure_status")) == "live_mvp_ready"
        readiness = evaluate_mvp_promotion_readiness(
            {
                "is_live_mvp_ready": is_live_mvp_ready,
                "controlled_and_reversible": True,
                "total_events": len(accepted_for_page),
                "preview_render_count": counts[MVPObservationEventType.preview_rendered.value],
                "outbound_click_count": counts[MVPObservationEventType.outbound_click.value],
                "preview_error_count": counts[MVPObservationEventType.preview_error.value],
                "outbound_error_count": counts[MVPObservationEventType.outbound_error.value],
                "manual_review_count": counts[MVPObservationEventType.manual_review_opened.value],
                "blocker_event_count": counts[MVPObservationEventType.blocker_detected.value],
            },
            policy=resolved_policy,
        )
        page_summaries.append(
            MVPPageObservationSummary(
                candidate_page_id=candidate_page_id,
                slug=slug,
                locale=locale,
                market=market,
                is_live_mvp_ready=is_live_mvp_ready,
                controlled_and_reversible=True,
                total_events=len(accepted_for_page),
                preview_render_count=counts[MVPObservationEventType.preview_rendered.value],
                outbound_click_count=counts[MVPObservationEventType.outbound_click.value],
                preview_error_count=counts[MVPObservationEventType.preview_error.value],
                outbound_error_count=counts[MVPObservationEventType.outbound_error.value],
                manual_review_count=counts[MVPObservationEventType.manual_review_opened.value],
                blocker_event_count=counts[MVPObservationEventType.blocker_detected.value],
                rejected_event_count=len(rejected_for_page),
                status=MVPObservationStatus(readiness["status"]),
                promotion_ready=bool(readiness["promotion_ready"]),
                reasons=tuple(readiness["reasons"]),
            )
        )

    ordered_summaries = tuple(sorted(page_summaries, key=lambda item: (item.candidate_page_id, item.slug)))
    status_counts = _status_counts(ordered_summaries)
    rejected_reason_counts = _count_rejections(rejected_events)

    accepted_count = len(accepted_events)
    rejected_count = len(rejected_events)
    preview_render_count = sum(1 for item in accepted_events if item.event_type == MVPObservationEventType.preview_rendered)
    outbound_click_count = sum(1 for item in accepted_events if item.event_type == MVPObservationEventType.outbound_click)
    preview_error_count = sum(1 for item in accepted_events if item.event_type == MVPObservationEventType.preview_error)
    outbound_error_count = sum(1 for item in accepted_events if item.event_type == MVPObservationEventType.outbound_error)
    manual_review_count = sum(1 for item in accepted_events if item.event_type == MVPObservationEventType.manual_review_opened)
    blocker_event_count = sum(1 for item in accepted_events if item.event_type == MVPObservationEventType.blocker_detected)

    promotion_ready_count = sum(1 for item in ordered_summaries if item.promotion_ready)
    hold_manual_review_count = status_counts.get(MVPObservationStatus.hold_manual_review.value, 0)
    blocked_count = status_counts.get(MVPObservationStatus.blocked.value, 0)
    needs_more_data_count = status_counts.get(MVPObservationStatus.needs_more_data.value, 0)

    can_move_to_step9 = bool(
        ordered_summaries
        and rejected_count == 0
        and blocked_count == 0
        and hold_manual_review_count == 0
        and needs_more_data_count == 0
        and promotion_ready_count == len(ordered_summaries)
    )

    result = MVPObservationBatchResult(
        total_events=len(event_inputs),
        accepted_events=accepted_count,
        rejected_events=rejected_count,
        preview_render_count=preview_render_count,
        outbound_click_count=outbound_click_count,
        preview_error_count=preview_error_count,
        outbound_error_count=outbound_error_count,
        manual_review_count=manual_review_count,
        blocker_event_count=blocker_event_count,
        unique_candidate_pages_observed=len(page_ids),
        page_summaries=ordered_summaries,
        status_counts=status_counts,
        rejected_reason_counts=rejected_reason_counts,
        promotion_ready_count=promotion_ready_count,
        hold_manual_review_count=hold_manual_review_count,
        blocked_count=blocked_count,
        can_move_to_step9=can_move_to_step9,
    )
    result_payload = asdict(result)
    result_payload["page_summaries"] = [_summary_to_payload(item) for item in result.page_summaries]
    return result_payload
