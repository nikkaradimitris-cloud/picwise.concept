from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .slugging import normalize_keyword_text


class CandidateIndexDecisionStatus(str, Enum):
    index_candidate = "index_candidate"
    noindex_candidate = "noindex_candidate"
    hold_manual_review = "hold_manual_review"
    rejected = "rejected"
    duplicate_canonical_required = "duplicate_canonical_required"


@dataclass(frozen=True)
class CandidateIndexGatePolicy:
    min_products_required: int = 4
    missing_four_products_outcome: CandidateIndexDecisionStatus = CandidateIndexDecisionStatus.rejected
    thin_content_outcome: CandidateIndexDecisionStatus = CandidateIndexDecisionStatus.noindex_candidate
    duplicate_slug_outcome: CandidateIndexDecisionStatus = CandidateIndexDecisionStatus.duplicate_canonical_required
    require_affiliate_for_monetized: bool = True
    supported_locales: tuple[str, ...] = ("en-US", "en-GB", "de-DE", "el-GR")
    supported_markets: tuple[str, ...] = ("US", "UK", "DE", "GR")
    supported_currencies: tuple[str, ...] = ("USD", "GBP", "EUR")
    keyword_stuffing_ratio_max: float = 0.32
    similarity_threshold: float = 0.9
    min_content_words: int = 450
    min_evidence_confidence: float = 0.7


@dataclass(frozen=True)
class CandidateIndexDecision:
    candidate_page_id: str
    slug: str
    status: CandidateIndexDecisionStatus
    is_public: bool
    is_indexable: bool
    sitemap_allowed: bool
    canonical_required: bool
    canonical_target_slug: str | None
    quality_score: float
    product_quality_score: float
    keyword_quality_score: float
    locale_quality_score: float
    duplicate_risk_score: float
    blocker_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    evidence_summary: Mapping[str, Any]


@dataclass(frozen=True)
class CandidateIndexBatchResult:
    total_candidates: int
    index_candidate_count: int
    noindex_candidate_count: int
    hold_manual_review_count: int
    rejected_count: int
    duplicate_canonical_required_count: int
    sitemap_allowed_candidate_count: int
    status_counts: dict[str, int]
    blocker_counts: dict[str, int]
    review_counts: dict[str, int]
    decisions: tuple[CandidateIndexDecision, ...]
    can_move_to_step7: bool


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm_text(value).lower()


def _norm_upper(value: Any) -> str:
    return _norm_text(value).upper()


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = _norm_lower(value)
    if normalized in {"1", "true", "yes", "y", "ready", "pass", "passed"}:
        return True
    if normalized in {"0", "false", "no", "n", "blocked", "fail", "failed"}:
        return False
    return default


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_id_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        cleaned = [_norm_text(item) for item in value if _norm_text(item)]
        return tuple(dict.fromkeys(cleaned))
    return tuple()


def _keyword_token_set(candidate_page: Mapping[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for raw in (
        candidate_page.get("main_keyword"),
        *(candidate_page.get("support_keywords") or ()),
        *(candidate_page.get("long_tail_keywords") or ()),
    ):
        normalized = normalize_keyword_text(_norm_text(raw))
        if not normalized:
            continue
        for token in normalized.split():
            if token:
                tokens.add(token)
    return tokens


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    if union == 0:
        return 0.0
    return intersection / union


def _bucket_status(
    *,
    has_rejected_reason: bool,
    has_noindex_reason: bool,
    has_hold_reason: bool,
    duplicate_required: bool,
) -> CandidateIndexDecisionStatus:
    if duplicate_required:
        return CandidateIndexDecisionStatus.duplicate_canonical_required
    if has_rejected_reason:
        return CandidateIndexDecisionStatus.rejected
    if has_hold_reason:
        return CandidateIndexDecisionStatus.hold_manual_review
    if has_noindex_reason:
        return CandidateIndexDecisionStatus.noindex_candidate
    return CandidateIndexDecisionStatus.index_candidate


def _convert_decision_to_payload(decision: CandidateIndexDecision) -> dict[str, Any]:
    payload = asdict(decision)
    payload["status"] = decision.status.value
    return payload


def _derive_quality_scores(
    *,
    product_penalty: float,
    keyword_penalty: float,
    locale_penalty: float,
    duplicate_penalty: float,
) -> tuple[float, float, float, float, float]:
    product_quality = max(0.0, 100.0 - product_penalty)
    keyword_quality = max(0.0, 100.0 - keyword_penalty)
    locale_quality = max(0.0, 100.0 - locale_penalty)
    duplicate_risk = max(0.0, 100.0 - duplicate_penalty)
    quality_score = round(
        ((product_quality * 0.35) + (keyword_quality * 0.30) + (locale_quality * 0.20) + (duplicate_risk * 0.15)),
        2,
    )
    return (
        quality_score,
        round(product_quality, 2),
        round(keyword_quality, 2),
        round(locale_quality, 2),
        round(duplicate_risk, 2),
    )


def _policy_from_input(policy: CandidateIndexGatePolicy | None) -> CandidateIndexGatePolicy:
    return policy if policy is not None else CandidateIndexGatePolicy()


def evaluate_candidate_index_eligibility(
    candidate_page: Mapping[str, Any],
    supporting_evidence: Mapping[str, Any] | None = None,
    policy: CandidateIndexGatePolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    evidence = dict(supporting_evidence or {})
    candidate = dict(candidate_page)

    candidate_page_id = _norm_text(candidate.get("candidate_page_id") or "candidate-page-unknown")
    slug = _norm_text(candidate.get("slug"))
    selected_product_ids = _coerce_id_tuple(candidate.get("selected_product_ids"))
    product_count = int(candidate.get("product_count") or len(selected_product_ids))
    recommended_product_id = _norm_text(candidate.get("recommended_product_id"))
    is_public_input = _as_bool(candidate.get("is_public"), default=False)
    locale = _norm_text(candidate.get("locale"))
    market = _norm_upper(candidate.get("market"))

    evidence_selected_products = _coerce_id_tuple(evidence.get("selected_product_ids"))
    if evidence_selected_products:
        selected_product_ids = evidence_selected_products
        product_count = len(selected_product_ids)

    provider_ready = _as_bool(evidence.get("provider_ready"), default=True)
    locale_ready = _as_bool(evidence.get("locale_ready"), default=True)
    keyword_cluster_ready = _as_bool(
        evidence.get("keyword_cluster_ready"),
        default=_norm_lower(candidate.get("status")) == "candidate_ready",
    )
    page_ready_keyword_evidence = _as_bool(evidence.get("page_ready_keyword_evidence"), default=keyword_cluster_ready)
    monetized = _as_bool(evidence.get("is_monetized"), default=True)
    affiliate_coverage = _as_float(evidence.get("affiliate_coverage"), default=1.0)
    missing_affiliate_links = _coerce_id_tuple(evidence.get("missing_affiliate_product_ids"))
    title_meta_intent_ready = _as_bool(evidence.get("title_meta_intent_ready"), default=True)
    keyword_stuffing_ratio = _as_float(evidence.get("keyword_stuffing_ratio"), default=0.0)
    thin_content = _as_bool(evidence.get("thin_content"), default=False)
    content_word_count = int(evidence.get("content_word_count") or 0)
    unsupported_locale_currency = _as_bool(evidence.get("unsupported_locale_currency"), default=False)
    currency = _norm_upper(evidence.get("currency"))
    fake_or_filler_products = _as_bool(evidence.get("fake_or_filler_products"), default=False)
    duplicate_slug_detected = _as_bool(evidence.get("duplicate_slug_detected"), default=False)
    similarity_score = _as_float(evidence.get("similarity_score"), default=0.0)
    similar_to_slug = _norm_text(evidence.get("similar_to_slug"))
    uncertain_evidence = _as_bool(evidence.get("uncertain_evidence"), default=False)
    evidence_confidence = _as_float(evidence.get("evidence_confidence"), default=1.0)

    rejected_reasons: list[str] = []
    noindex_reasons: list[str] = []
    review_reasons: list[str] = []
    duplicate_reasons: list[str] = []

    product_penalty = 0.0
    keyword_penalty = 0.0
    locale_penalty = 0.0
    duplicate_penalty = 0.0

    if is_public_input:
        rejected_reasons.append("candidate_must_be_non_public")
        product_penalty += 20

    if product_count < resolved_policy.min_products_required:
        if resolved_policy.missing_four_products_outcome == CandidateIndexDecisionStatus.rejected:
            rejected_reasons.append("requires_exactly_four_products")
        elif resolved_policy.missing_four_products_outcome == CandidateIndexDecisionStatus.noindex_candidate:
            noindex_reasons.append("requires_exactly_four_products")
        else:
            review_reasons.append("requires_exactly_four_products")
        product_penalty += 40

    if recommended_product_id and recommended_product_id not in selected_product_ids:
        rejected_reasons.append("recommended_product_not_in_selected_products")
        product_penalty += 25
    if not recommended_product_id:
        review_reasons.append("recommended_product_evidence_missing")
        product_penalty += 8

    if not page_ready_keyword_evidence:
        rejected_reasons.append("missing_page_ready_keyword_cluster_evidence")
        keyword_penalty += 25
    if not locale_ready:
        rejected_reasons.append("missing_locale_ready_product_evidence")
        locale_penalty += 25
    if not provider_ready:
        rejected_reasons.append("missing_provider_ready_product_evidence")
        product_penalty += 25

    if fake_or_filler_products:
        rejected_reasons.append("fake_or_filler_products_detected")
        product_penalty += 35

    if monetized and resolved_policy.require_affiliate_for_monetized:
        if affiliate_coverage < 1.0 or bool(missing_affiliate_links):
            rejected_reasons.append("missing_affiliate_links_for_monetized_page")
            product_penalty += 20

    if not title_meta_intent_ready:
        rejected_reasons.append("missing_title_meta_intent_evidence")
        keyword_penalty += 20

    if keyword_stuffing_ratio > resolved_policy.keyword_stuffing_ratio_max:
        rejected_reasons.append("keyword_stuffing_detected")
        keyword_penalty += 30

    if unsupported_locale_currency:
        rejected_reasons.append("unsupported_locale_market_currency")
        locale_penalty += 45
    if locale and locale not in resolved_policy.supported_locales:
        rejected_reasons.append("unsupported_locale_market_currency")
        locale_penalty += 45
    if market and market not in resolved_policy.supported_markets:
        rejected_reasons.append("unsupported_locale_market_currency")
        locale_penalty += 45
    if currency and currency not in resolved_policy.supported_currencies:
        rejected_reasons.append("unsupported_locale_market_currency")
        locale_penalty += 45

    if thin_content or (content_word_count > 0 and content_word_count < resolved_policy.min_content_words):
        if resolved_policy.thin_content_outcome == CandidateIndexDecisionStatus.rejected:
            rejected_reasons.append("thin_content_indicators_detected")
        elif resolved_policy.thin_content_outcome == CandidateIndexDecisionStatus.hold_manual_review:
            review_reasons.append("thin_content_indicators_detected")
        else:
            noindex_reasons.append("thin_content_indicators_detected")
        keyword_penalty += 25

    canonical_target_slug: str | None = None
    canonical_required = False
    if duplicate_slug_detected:
        duplicate_penalty += 60
        if resolved_policy.duplicate_slug_outcome == CandidateIndexDecisionStatus.rejected:
            rejected_reasons.append("duplicate_slug_detected")
        else:
            duplicate_reasons.append("duplicate_slug_detected")
            canonical_required = True
            canonical_target_slug = _norm_text(evidence.get("canonical_target_slug")) or None
    elif similarity_score >= resolved_policy.similarity_threshold and similar_to_slug:
        duplicate_reasons.append("near_duplicate_candidate_requires_canonical")
        duplicate_penalty += 45
        canonical_required = True
        canonical_target_slug = similar_to_slug

    if uncertain_evidence or evidence_confidence < resolved_policy.min_evidence_confidence:
        review_reasons.append("uncertain_supporting_evidence")
        keyword_penalty += 8
        locale_penalty += 8

    rejected_reasons = list(dict.fromkeys(rejected_reasons))
    noindex_reasons = list(dict.fromkeys(noindex_reasons))
    review_reasons = list(dict.fromkeys(review_reasons))
    duplicate_reasons = list(dict.fromkeys(duplicate_reasons))

    status = _bucket_status(
        has_rejected_reason=bool(rejected_reasons),
        has_noindex_reason=bool(noindex_reasons),
        has_hold_reason=bool(review_reasons),
        duplicate_required=bool(duplicate_reasons),
    )

    quality_score, product_quality, keyword_quality, locale_quality, duplicate_risk = _derive_quality_scores(
        product_penalty=product_penalty,
        keyword_penalty=keyword_penalty,
        locale_penalty=locale_penalty,
        duplicate_penalty=duplicate_penalty,
    )

    blocker_reasons = tuple(
        sorted(dict.fromkeys([*rejected_reasons, *noindex_reasons, *duplicate_reasons]))
    )
    review_reason_codes = tuple(sorted(review_reasons))
    is_indexable = status == CandidateIndexDecisionStatus.index_candidate
    decision = CandidateIndexDecision(
        candidate_page_id=candidate_page_id,
        slug=slug,
        status=status,
        is_public=False,
        is_indexable=is_indexable,
        sitemap_allowed=is_indexable,
        canonical_required=canonical_required,
        canonical_target_slug=canonical_target_slug,
        quality_score=quality_score,
        product_quality_score=product_quality,
        keyword_quality_score=keyword_quality,
        locale_quality_score=locale_quality,
        duplicate_risk_score=duplicate_risk,
        blocker_reasons=blocker_reasons,
        review_reasons=review_reason_codes,
        evidence_summary={
            "selected_product_count": product_count,
            "recommended_product_in_selected": bool(
                recommended_product_id and recommended_product_id in selected_product_ids
            ),
            "keyword_cluster_ready": page_ready_keyword_evidence,
            "locale_ready": locale_ready,
            "provider_ready": provider_ready,
            "affiliate_coverage": affiliate_coverage,
            "title_meta_intent_ready": title_meta_intent_ready,
            "keyword_stuffing_ratio": round(keyword_stuffing_ratio, 3),
            "thin_content": thin_content,
            "content_word_count": content_word_count,
            "unsupported_locale_currency": unsupported_locale_currency,
            "duplicate_slug_detected": duplicate_slug_detected,
            "similarity_score": round(similarity_score, 3),
            "similar_to_slug": similar_to_slug or None,
            "uncertain_evidence": uncertain_evidence,
            "evidence_confidence": round(evidence_confidence, 3),
        },
    )
    return _convert_decision_to_payload(decision)


def _count_by_status(decisions: Iterable[CandidateIndexDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = decision.status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_reasons(decisions: Iterable[CandidateIndexDecision], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        reasons = getattr(decision, attr)
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def evaluate_candidate_index_batch(
    candidate_pages: Iterable[Mapping[str, Any]],
    supporting_evidence: Mapping[str, Any] | None = None,
    policy: CandidateIndexGatePolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    pages = [dict(page) for page in candidate_pages]
    by_candidate_id: dict[str, dict[str, Any]] = {}
    for page in pages:
        candidate_page_id = _norm_text(page.get("candidate_page_id") or f"candidate-page-{len(by_candidate_id)+1}")
        by_candidate_id[candidate_page_id] = page

    ordered_pages = sorted(
        by_candidate_id.values(),
        key=lambda item: (_norm_text(item.get("candidate_page_id")), _norm_text(item.get("slug"))),
    )
    resolved_evidence_root = dict(supporting_evidence or {})
    root_candidate_evidence = dict(resolved_evidence_root.get("candidate_evidence") or {})

    slug_to_candidate_ids: dict[str, list[str]] = {}
    token_sets: dict[str, set[str]] = {}
    for page in ordered_pages:
        candidate_page_id = _norm_text(page.get("candidate_page_id"))
        slug = _norm_text(page.get("slug"))
        if slug:
            slug_to_candidate_ids.setdefault(slug, []).append(candidate_page_id)
        token_sets[candidate_page_id] = _keyword_token_set(page)

    duplicate_slug_ids: set[str] = set()
    for candidate_ids in slug_to_candidate_ids.values():
        if len(candidate_ids) > 1:
            duplicate_slug_ids.update(candidate_ids)

    pairwise_similar_duplicates: dict[str, tuple[str, float]] = {}
    ordered_candidates = [(_norm_text(page.get("candidate_page_id")), _norm_text(page.get("slug"))) for page in ordered_pages]
    for left_index, (left_id, left_slug) in enumerate(ordered_candidates):
        for right_id, right_slug in ordered_candidates[left_index + 1 :]:
            if not left_slug or not right_slug or left_slug == right_slug:
                continue
            score = _jaccard_similarity(token_sets[left_id], token_sets[right_id])
            if score < resolved_policy.similarity_threshold:
                continue
            canonical_slug = min(left_slug, right_slug)
            duplicate_slug = max(left_slug, right_slug)
            duplicate_id = left_id if left_slug == duplicate_slug else right_id
            existing = pairwise_similar_duplicates.get(duplicate_id)
            if existing is None or score > existing[1]:
                pairwise_similar_duplicates[duplicate_id] = (canonical_slug, score)

    decisions: list[CandidateIndexDecision] = []
    for page in ordered_pages:
        candidate_page_id = _norm_text(page.get("candidate_page_id"))
        slug = _norm_text(page.get("slug"))
        page_evidence = dict(root_candidate_evidence.get(candidate_page_id) or root_candidate_evidence.get(slug) or {})
        if candidate_page_id in duplicate_slug_ids:
            page_evidence.setdefault("duplicate_slug_detected", True)
        if candidate_page_id in pairwise_similar_duplicates and candidate_page_id not in duplicate_slug_ids:
            canonical_slug, similarity = pairwise_similar_duplicates[candidate_page_id]
            page_evidence.setdefault("similar_to_slug", canonical_slug)
            page_evidence.setdefault("similarity_score", similarity)
        payload = evaluate_candidate_index_eligibility(
            page,
            supporting_evidence=page_evidence,
            policy=resolved_policy,
        )
        decisions.append(
            CandidateIndexDecision(
                candidate_page_id=payload["candidate_page_id"],
                slug=payload["slug"],
                status=CandidateIndexDecisionStatus(payload["status"]),
                is_public=bool(payload["is_public"]),
                is_indexable=bool(payload["is_indexable"]),
                sitemap_allowed=bool(payload["sitemap_allowed"]),
                canonical_required=bool(payload["canonical_required"]),
                canonical_target_slug=payload["canonical_target_slug"],
                quality_score=float(payload["quality_score"]),
                product_quality_score=float(payload["product_quality_score"]),
                keyword_quality_score=float(payload["keyword_quality_score"]),
                locale_quality_score=float(payload["locale_quality_score"]),
                duplicate_risk_score=float(payload["duplicate_risk_score"]),
                blocker_reasons=tuple(payload["blocker_reasons"]),
                review_reasons=tuple(payload["review_reasons"]),
                evidence_summary=dict(payload["evidence_summary"]),
            )
        )

    status_counts = _count_by_status(decisions)
    blocker_counts = _count_reasons(decisions, "blocker_reasons")
    review_counts = _count_reasons(decisions, "review_reasons")

    index_count = status_counts.get(CandidateIndexDecisionStatus.index_candidate.value, 0)
    noindex_count = status_counts.get(CandidateIndexDecisionStatus.noindex_candidate.value, 0)
    hold_count = status_counts.get(CandidateIndexDecisionStatus.hold_manual_review.value, 0)
    rejected_count = status_counts.get(CandidateIndexDecisionStatus.rejected.value, 0)
    duplicate_count = status_counts.get(CandidateIndexDecisionStatus.duplicate_canonical_required.value, 0)
    sitemap_allowed_count = sum(1 for item in decisions if item.sitemap_allowed)
    total_candidates = len(decisions)
    can_move_to_step7 = bool(
        total_candidates > 0
        and index_count == total_candidates
        and rejected_count == 0
        and hold_count == 0
        and duplicate_count == 0
        and noindex_count == 0
    )

    result = CandidateIndexBatchResult(
        total_candidates=total_candidates,
        index_candidate_count=index_count,
        noindex_candidate_count=noindex_count,
        hold_manual_review_count=hold_count,
        rejected_count=rejected_count,
        duplicate_canonical_required_count=duplicate_count,
        sitemap_allowed_candidate_count=sitemap_allowed_count,
        status_counts=status_counts,
        blocker_counts=blocker_counts,
        review_counts=review_counts,
        decisions=tuple(decisions),
        can_move_to_step7=can_move_to_step7,
    )
    payload = asdict(result)
    payload["decisions"] = [_convert_decision_to_payload(item) for item in result.decisions]
    return payload
