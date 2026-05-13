from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .candidate_index_gate import CandidateIndexDecisionStatus


class LiveMVPExposureStatus(str, Enum):
    live_mvp_ready = "live_mvp_ready"
    hold_manual_review = "hold_manual_review"
    blocked = "blocked"


@dataclass(frozen=True)
class LiveMVPGatePolicy:
    max_live_mvp_ready: int = 25
    min_selected_products_required: int = 4
    allow_public_exposure: bool = False
    allow_sitemap_candidate_flag: bool = True
    preview_enabled_for_manual_review: bool = True
    public_exposure_candidate_page_ids: tuple[str, ...] = ()
    sitemap_candidate_page_ids: tuple[str, ...] = ()
    preview_tracking_event_name: str = "live_mvp_preview_rendered"
    outbound_click_tracking_event_name: str = "live_mvp_outbound_click"


@dataclass(frozen=True)
class LiveMVPPageRecord:
    candidate_page_id: str
    slug: str
    source_index_decision_status: str
    locale: str
    market: str
    main_keyword: str
    selected_product_ids: tuple[str, ...]
    recommended_product_id: str
    exposure_status: LiveMVPExposureStatus
    can_render_preview: bool
    can_collect_outbound_click: bool
    can_be_publicly_exposed: bool
    can_be_sitemap_candidate: bool
    is_mass_publish: bool
    blocker_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    tracking_event_names: tuple[str, ...]


@dataclass(frozen=True)
class LiveMVPBatchResult:
    total_candidates: int
    live_mvp_ready_count: int
    hold_manual_review_count: int
    blocked_count: int
    preview_ready_count: int
    outbound_tracking_ready_count: int
    sitemap_candidate_count: int
    status_counts: dict[str, int]
    blocker_counts: dict[str, int]
    can_move_to_step8: bool
    records: tuple[LiveMVPPageRecord, ...]


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _norm_upper(value: Any) -> str:
    return _norm_text(value).upper()


def _coerce_id_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        cleaned = [_norm_text(item) for item in value if _norm_text(item)]
        return tuple(dict.fromkeys(cleaned))
    return tuple()


def _policy_from_input(policy: LiveMVPGatePolicy | None) -> LiveMVPGatePolicy:
    return policy if policy is not None else LiveMVPGatePolicy()


def _count_by_status(records: Iterable[LiveMVPPageRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = record.exposure_status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_blockers(records: Iterable[LiveMVPPageRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for reason in record.blocker_reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _to_record_payload(record: LiveMVPPageRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["exposure_status"] = record.exposure_status.value
    return payload


def build_live_mvp_batch(
    candidate_pages: Iterable[Mapping[str, Any]],
    index_decisions: Iterable[Mapping[str, Any]],
    policy: LiveMVPGatePolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)

    pages_by_id: dict[str, dict[str, Any]] = {}
    for page in candidate_pages:
        normalized_page = dict(page)
        candidate_page_id = _norm_text(normalized_page.get("candidate_page_id"))
        if candidate_page_id:
            pages_by_id[candidate_page_id] = normalized_page

    decisions_by_id: dict[str, dict[str, Any]] = {}
    for decision in index_decisions:
        normalized_decision = dict(decision)
        candidate_page_id = _norm_text(normalized_decision.get("candidate_page_id"))
        if candidate_page_id:
            decisions_by_id[candidate_page_id] = normalized_decision

    ordered_ids = sorted(set(pages_by_id.keys()) | set(decisions_by_id.keys()))
    ordered_ids_for_ready = sorted(
        ordered_ids,
        key=lambda item: (
            _norm_text(pages_by_id.get(item, {}).get("candidate_page_id") or item),
            _norm_text(pages_by_id.get(item, {}).get("slug")),
        ),
    )
    ready_allowed_ids = set(ordered_ids_for_ready[: max(0, resolved_policy.max_live_mvp_ready)])

    allowed_public_ids = set(resolved_policy.public_exposure_candidate_page_ids)
    allowed_sitemap_ids = set(resolved_policy.sitemap_candidate_page_ids)

    records: list[LiveMVPPageRecord] = []
    for candidate_page_id in ordered_ids:
        page = pages_by_id.get(candidate_page_id, {})
        decision = decisions_by_id.get(candidate_page_id, {})
        slug = _norm_text(page.get("slug") or decision.get("slug"))
        source_status = _norm_text(
            decision.get("status") or CandidateIndexDecisionStatus.hold_manual_review.value
        )
        selected_product_ids = _coerce_id_tuple(page.get("selected_product_ids"))
        recommended_product_id = _norm_text(page.get("recommended_product_id"))
        evidence_summary = decision.get("evidence_summary")
        evidence = dict(evidence_summary) if isinstance(evidence_summary, Mapping) else {}

        blocker_reasons: list[str] = list(_coerce_id_tuple(decision.get("blocker_reasons")))
        review_reasons: list[str] = list(_coerce_id_tuple(decision.get("review_reasons")))

        exposure_status = LiveMVPExposureStatus.blocked
        if source_status == CandidateIndexDecisionStatus.index_candidate.value:
            if candidate_page_id not in ready_allowed_ids:
                exposure_status = LiveMVPExposureStatus.hold_manual_review
                review_reasons.append("outside_controlled_live_mvp_batch_limit")
            elif len(selected_product_ids) < resolved_policy.min_selected_products_required:
                exposure_status = LiveMVPExposureStatus.blocked
                blocker_reasons.append("requires_exactly_four_products")
            else:
                recommended_in_selected = bool(
                    recommended_product_id and recommended_product_id in selected_product_ids
                )
                if "recommended_product_in_selected" in evidence:
                    recommended_in_selected = bool(evidence.get("recommended_product_in_selected"))
                if not recommended_in_selected:
                    exposure_status = LiveMVPExposureStatus.hold_manual_review
                    review_reasons.append("recommended_product_evidence_missing")
                else:
                    exposure_status = LiveMVPExposureStatus.live_mvp_ready
        elif source_status == CandidateIndexDecisionStatus.hold_manual_review.value:
            exposure_status = LiveMVPExposureStatus.hold_manual_review
            review_reasons.append("source_index_decision_hold_manual_review")
        else:
            exposure_status = LiveMVPExposureStatus.blocked
            blocker_reasons.append(f"source_index_decision_{source_status}")

        blocker_reasons = list(dict.fromkeys(_coerce_id_tuple(blocker_reasons)))
        review_reasons = list(dict.fromkeys(_coerce_id_tuple(review_reasons)))

        can_render_preview = exposure_status in {
            LiveMVPExposureStatus.live_mvp_ready,
            LiveMVPExposureStatus.hold_manual_review,
        }
        if exposure_status == LiveMVPExposureStatus.hold_manual_review and not resolved_policy.preview_enabled_for_manual_review:
            can_render_preview = False
        can_collect_outbound_click = exposure_status == LiveMVPExposureStatus.live_mvp_ready
        can_be_publicly_exposed = bool(
            resolved_policy.allow_public_exposure
            and exposure_status == LiveMVPExposureStatus.live_mvp_ready
            and candidate_page_id in allowed_public_ids
        )
        can_be_sitemap_candidate = bool(
            resolved_policy.allow_sitemap_candidate_flag
            and exposure_status == LiveMVPExposureStatus.live_mvp_ready
            and candidate_page_id in allowed_sitemap_ids
        )

        tracking_event_names: list[str] = []
        if can_render_preview:
            tracking_event_names.append(resolved_policy.preview_tracking_event_name)
        if can_collect_outbound_click:
            tracking_event_names.append(resolved_policy.outbound_click_tracking_event_name)

        records.append(
            LiveMVPPageRecord(
                candidate_page_id=candidate_page_id,
                slug=slug,
                source_index_decision_status=source_status,
                locale=_norm_text(page.get("locale")),
                market=_norm_upper(page.get("market")),
                main_keyword=_norm_text(page.get("main_keyword")),
                selected_product_ids=selected_product_ids,
                recommended_product_id=recommended_product_id,
                exposure_status=exposure_status,
                can_render_preview=can_render_preview,
                can_collect_outbound_click=can_collect_outbound_click,
                can_be_publicly_exposed=can_be_publicly_exposed,
                can_be_sitemap_candidate=can_be_sitemap_candidate,
                is_mass_publish=False,
                blocker_reasons=tuple(blocker_reasons),
                review_reasons=tuple(review_reasons),
                tracking_event_names=tuple(dict.fromkeys(_coerce_id_tuple(tracking_event_names))),
            )
        )

    ordered_records = tuple(
        sorted(
            records,
            key=lambda item: (item.candidate_page_id, item.slug),
        )
    )
    status_counts = _count_by_status(ordered_records)
    blocker_counts = _count_blockers(ordered_records)

    live_ready = status_counts.get(LiveMVPExposureStatus.live_mvp_ready.value, 0)
    hold = status_counts.get(LiveMVPExposureStatus.hold_manual_review.value, 0)
    blocked = status_counts.get(LiveMVPExposureStatus.blocked.value, 0)
    preview_ready_count = sum(1 for item in ordered_records if item.can_render_preview)
    outbound_tracking_ready_count = sum(1 for item in ordered_records if item.can_collect_outbound_click)
    sitemap_candidate_count = sum(1 for item in ordered_records if item.can_be_sitemap_candidate)
    total_candidates = len(ordered_records)
    can_move_to_step8 = bool(
        total_candidates > 0
        and live_ready == total_candidates
        and hold == 0
        and blocked == 0
        and outbound_tracking_ready_count == live_ready
        and all(not item.is_mass_publish for item in ordered_records)
    )

    result = LiveMVPBatchResult(
        total_candidates=total_candidates,
        live_mvp_ready_count=live_ready,
        hold_manual_review_count=hold,
        blocked_count=blocked,
        preview_ready_count=preview_ready_count,
        outbound_tracking_ready_count=outbound_tracking_ready_count,
        sitemap_candidate_count=sitemap_candidate_count,
        status_counts=status_counts,
        blocker_counts=blocker_counts,
        can_move_to_step8=can_move_to_step8,
        records=ordered_records,
    )
    payload = asdict(result)
    payload["records"] = [_to_record_payload(item) for item in result.records]
    return payload
