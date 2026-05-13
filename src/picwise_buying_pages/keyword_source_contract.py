from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from picwise_offers.locale_logic import DEFAULT_LOCALE_RULESET, TargetMarket


class KeywordVolumeBucket(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class KeywordIntentType(str, Enum):
    BUYER_INTENT = "buyer_intent"
    COMPARISON_INTENT = "comparison_intent"
    PRODUCT_SPECIFIC = "product_specific"
    CATEGORY_RESEARCH = "category_research"
    INFORMATIONAL_ONLY = "informational_only"
    AMBIGUOUS = "ambiguous"


class KeywordVariantType(str, Enum):
    MAIN = "main"
    MEDIUM_HIGH_SUPPORT = "medium_high_support"
    LOW_VOLUME_LONG_TAIL = "low_volume_long_tail"
    LANGUAGE_VARIANT = "language_variant"
    TYPO_VARIANT = "typo_variant"
    SPEC_VARIANT = "spec_variant"
    BRAND_MODEL_VARIANT = "brand_model_variant"


class KeywordSourceType(str, Enum):
    LOCAL_FIXTURE = "local_fixture"
    PROVIDER_FEED = "provider_feed"
    GOOGLE_KEYWORD_PLANNER_EXPORT = "google_keyword_planner_export"
    SEARCH_CONSOLE_EXPORT = "search_console_export"
    TAXONOMY_GENERATED = "taxonomy_generated"
    NLU_GENERATED = "nlu_generated"
    MANUAL_REVIEW = "manual_review"


class KeywordClusterStatus(str, Enum):
    PAGE_READY = "page_ready"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class KeywordVariant:
    keyword: str
    variant_type: KeywordVariantType

    def __post_init__(self) -> None:
        text = _normalize_text(self.keyword)
        if not text:
            raise ValueError("KeywordVariant.keyword is required.")
        object.__setattr__(self, "keyword", text)
        variant = _coerce_enum(self.variant_type, KeywordVariantType, KeywordVariantType.LANGUAGE_VARIANT)
        object.__setattr__(self, "variant_type", variant)


@dataclass(frozen=True)
class KeywordCluster:
    cluster_id: str
    locale: str
    market: str
    target_category: str
    buyer_intent: bool
    intent_type: KeywordIntentType
    main_keyword: str
    support_keywords: tuple[str, ...]
    long_tail_keywords: tuple[str, ...]
    variants: tuple[KeywordVariant, ...]
    product_spec_signals: tuple[str, ...]
    brand_model_signals: tuple[str, ...]
    source_type: KeywordSourceType
    volume_bucket_by_keyword: dict[str, KeywordVolumeBucket]
    confidence_score: float
    review_required: bool
    rejection_reasons: tuple[str, ...]
    blocker_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cluster_id", _normalize_text(self.cluster_id) or "keyword-cluster-unknown")
        object.__setattr__(self, "locale", _normalize_text(self.locale) or "")
        object.__setattr__(self, "market", (_normalize_text(self.market) or "").upper())
        object.__setattr__(self, "target_category", _normalize_text(self.target_category) or "")
        object.__setattr__(self, "buyer_intent", bool(self.buyer_intent))
        intent = _coerce_enum(self.intent_type, KeywordIntentType, KeywordIntentType.AMBIGUOUS)
        object.__setattr__(self, "intent_type", intent)
        object.__setattr__(self, "main_keyword", _normalize_text(self.main_keyword) or "")
        object.__setattr__(self, "support_keywords", _normalize_keyword_sequence(self.support_keywords))
        object.__setattr__(self, "long_tail_keywords", _normalize_keyword_sequence(self.long_tail_keywords))

        normalized_variants: list[KeywordVariant] = []
        for item in self.variants:
            if isinstance(item, KeywordVariant):
                normalized_variants.append(item)
                continue
            if isinstance(item, Mapping):
                normalized_variants.append(
                    KeywordVariant(
                        keyword=str(item.get("keyword", "")).strip(),
                        variant_type=str(item.get("variant_type", KeywordVariantType.LANGUAGE_VARIANT.value)).strip(),
                    )
                )
        object.__setattr__(self, "variants", tuple(normalized_variants))

        object.__setattr__(self, "product_spec_signals", _normalize_keyword_sequence(self.product_spec_signals))
        object.__setattr__(self, "brand_model_signals", _normalize_keyword_sequence(self.brand_model_signals))
        source = _coerce_enum(self.source_type, KeywordSourceType, KeywordSourceType.LOCAL_FIXTURE)
        object.__setattr__(self, "source_type", source)
        object.__setattr__(self, "volume_bucket_by_keyword", _normalize_volume_bucket_map(self.volume_bucket_by_keyword))

        score = float(self.confidence_score)
        if score < 0:
            score = 0.0
        if score > 1:
            score = 1.0
        object.__setattr__(self, "confidence_score", score)

        object.__setattr__(self, "review_required", bool(self.review_required))
        object.__setattr__(self, "rejection_reasons", _normalize_keyword_sequence(self.rejection_reasons))
        object.__setattr__(self, "blocker_reasons", _normalize_keyword_sequence(self.blocker_reasons))


@dataclass(frozen=True)
class KeywordClusterValidationResult:
    cluster_id: str
    status: KeywordClusterStatus
    is_page_ready: bool
    review_required: bool
    blocked: bool
    missing_main_keyword: bool
    insufficient_long_tail: bool
    ambiguous_intent: bool
    informational_only: bool
    duplicate_keywords: tuple[str, ...]
    locale_market_issue: bool
    blocker_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    warning_reasons: tuple[str, ...]
    is_public_index_ready: bool


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_keyword(value: Any) -> str:
    text = _normalize_text(value) or ""
    return " ".join(text.lower().split())


def _normalize_keyword_sequence(values: Iterable[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        text = _normalize_keyword(value)
        if text:
            normalized.append(text)
    return tuple(normalized)


def _coerce_enum(value: Any, enum_cls: type[Enum], default: Enum) -> Enum:
    if isinstance(value, enum_cls):
        return value
    raw = _normalize_text(value)
    if raw is None:
        return default
    try:
        return enum_cls(raw)
    except ValueError:
        return default


def _normalize_volume_bucket_map(
    mapping: Mapping[str, Any] | None,
) -> dict[str, KeywordVolumeBucket]:
    if not isinstance(mapping, Mapping):
        return {}
    normalized: dict[str, KeywordVolumeBucket] = {}
    for raw_keyword, raw_bucket in mapping.items():
        keyword = _normalize_keyword(raw_keyword)
        if not keyword:
            continue
        bucket = _coerce_enum(raw_bucket, KeywordVolumeBucket, KeywordVolumeBucket.UNKNOWN)
        normalized[keyword] = bucket
    return dict(sorted(normalized.items()))


def _extract_keyword_groups(local_input: Mapping[str, Any]) -> tuple[str, tuple[str, ...], tuple[str, ...], int]:
    main_candidates: list[str] = []
    raw_main = local_input.get("main_keyword")
    if isinstance(raw_main, list):
        main_candidates.extend(_normalize_keyword(item) for item in raw_main)
    elif raw_main is not None:
        main_candidates.append(_normalize_keyword(raw_main))

    alternate_main = local_input.get("main_keywords")
    if isinstance(alternate_main, list):
        main_candidates.extend(_normalize_keyword(item) for item in alternate_main)

    clean_main = [item for item in main_candidates if item]
    support = _normalize_keyword_sequence(local_input.get("support_keywords", []))
    long_tail = _normalize_keyword_sequence(local_input.get("long_tail_keywords", []))
    return (clean_main[0] if clean_main else "", support, long_tail, len(clean_main))


def _collect_duplicates(
    main_keyword: str,
    support_keywords: tuple[str, ...],
    long_tail_keywords: tuple[str, ...],
    variants: tuple[KeywordVariant, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    occurrences: dict[str, int] = {}
    for keyword in (main_keyword, *support_keywords, *long_tail_keywords, *(item.keyword for item in variants)):
        if not keyword:
            continue
        occurrences[keyword] = occurrences.get(keyword, 0) + 1

    duplicate_set = {keyword for keyword, count in occurrences.items() if count > 1}
    seen_support: set[str] = set()
    deduped_support_list: list[str] = []
    for item in support_keywords:
        if item == main_keyword:
            continue
        if item in seen_support:
            duplicate_set.add(item)
            continue
        seen_support.add(item)
        deduped_support_list.append(item)

    seen_long_tail: set[str] = set()
    deduped_long_tail_list: list[str] = []
    for item in long_tail_keywords:
        if item == main_keyword:
            continue
        if item in seen_long_tail:
            duplicate_set.add(item)
            continue
        seen_long_tail.add(item)
        deduped_long_tail_list.append(item)

    seen_variant_pairs: set[tuple[str, KeywordVariantType]] = set()
    deduped_variants: list[KeywordVariant] = []
    for item in variants:
        pair = (item.keyword, item.variant_type)
        if pair in seen_variant_pairs:
            duplicate_set.add(item.keyword)
            continue
        seen_variant_pairs.add(pair)
        deduped_variants.append(item)

    return (
        tuple(sorted(duplicate_set)),
        tuple(deduped_support_list),
        tuple(deduped_long_tail_list),
        tuple(deduped_variants),
        tuple(sorted(occurrences.keys())),
    )


def _locale_market_issue(locale: str, market: str) -> bool:
    allowed_markets = {item.value for item in TargetMarket}
    if market not in allowed_markets:
        return True
    if not locale:
        return True
    locale_region = locale.replace("_", "-").split("-")[-1].upper()
    region_for_market = {"US": "US", "UK": "GB", "DE": "DE", "GR": "GR"}
    expected_region = region_for_market.get(market)
    if expected_region and locale_region != expected_region:
        return True
    return False


def _has_category_linkage(cluster: KeywordCluster, all_keywords: tuple[str, ...]) -> bool:
    category_parts = [part for part in cluster.target_category.replace("/", " ").split() if part]
    if not category_parts:
        return False
    combined = " ".join(all_keywords)
    if any(part.lower() in combined for part in category_parts):
        return True
    if cluster.product_spec_signals or cluster.brand_model_signals:
        return True
    return False


def _is_keyword_stuffing(total_before_dedupe: int, deduped_keyword_total: int) -> bool:
    if total_before_dedupe >= 80:
        return True
    if total_before_dedupe and deduped_keyword_total / total_before_dedupe < 0.55:
        return True
    return False


def _validate_keyword_cluster(
    cluster: KeywordCluster,
    *,
    main_keyword_candidate_count: int | None = None,
) -> KeywordClusterValidationResult:
    blocker_reasons = list(cluster.blocker_reasons)
    review_reasons: list[str] = []
    warning_reasons: list[str] = []

    if main_keyword_candidate_count is not None and main_keyword_candidate_count != 1:
        blocker_reasons.append("invalid_main_keyword_count")

    missing_main_keyword = not cluster.main_keyword
    if missing_main_keyword:
        blocker_reasons.append("missing_main_keyword")

    support_count = len(cluster.support_keywords)
    if support_count < 3 or support_count > 5:
        warning_reasons.append("support_keywords_outside_preferred_range")

    insufficient_long_tail = len(cluster.long_tail_keywords) < 10
    long_tail_overflow = len(cluster.long_tail_keywords) > 30
    if insufficient_long_tail:
        blocker_reasons.append("insufficient_long_tail_keywords_for_page_ready")
    if long_tail_overflow:
        blocker_reasons.append("long_tail_keywords_exceed_page_ready_limit")

    if not cluster.buyer_intent:
        blocker_reasons.append("buyer_intent_not_clear")

    informational_only = cluster.intent_type == KeywordIntentType.INFORMATIONAL_ONLY
    if informational_only:
        blocker_reasons.append("informational_only_cluster_not_page_ready")

    ambiguous_intent = cluster.intent_type == KeywordIntentType.AMBIGUOUS
    if ambiguous_intent:
        review_reasons.append("ambiguous_intent_requires_review")

    locale_market_issue = _locale_market_issue(cluster.locale, cluster.market)
    if locale_market_issue:
        blocker_reasons.append("locale_market_mismatch_or_unsupported")

    all_keywords = (
        (cluster.main_keyword,) if cluster.main_keyword else tuple()
    ) + cluster.support_keywords + cluster.long_tail_keywords + tuple(item.keyword for item in cluster.variants)
    if not _has_category_linkage(cluster, all_keywords):
        blocker_reasons.append("missing_product_category_intent_linkage")

    duplicate_keywords, deduped_support, deduped_long_tail, deduped_variants, deduped_keyword_pool = _collect_duplicates(
        cluster.main_keyword,
        cluster.support_keywords,
        cluster.long_tail_keywords,
        cluster.variants,
    )
    if duplicate_keywords:
        review_reasons.append("duplicate_keywords_detected")

    total_before_dedupe = 1 + len(cluster.support_keywords) + len(cluster.long_tail_keywords) + len(cluster.variants)
    if _is_keyword_stuffing(total_before_dedupe, len(deduped_keyword_pool)):
        blocker_reasons.append("keyword_stuffing_detected")

    explicit_volume_map = cluster.volume_bucket_by_keyword
    if any(not isinstance(item, KeywordVolumeBucket) for item in explicit_volume_map.values()):
        blocker_reasons.append("invalid_volume_bucket_value")

    review_required = cluster.review_required or bool(review_reasons)
    deduped_blockers = tuple(sorted(dict.fromkeys(blocker_reasons)))
    deduped_review = tuple(sorted(dict.fromkeys(review_reasons)))
    deduped_warning = tuple(sorted(dict.fromkeys(warning_reasons)))
    blocked = bool(deduped_blockers)
    is_page_ready = not blocked and not review_required and not missing_main_keyword and not insufficient_long_tail
    status = (
        KeywordClusterStatus.BLOCKED
        if blocked
        else (KeywordClusterStatus.REVIEW_REQUIRED if review_required else KeywordClusterStatus.PAGE_READY)
    )

    _ = deduped_support, deduped_long_tail, deduped_variants
    return KeywordClusterValidationResult(
        cluster_id=cluster.cluster_id,
        status=status,
        is_page_ready=is_page_ready,
        review_required=review_required,
        blocked=blocked,
        missing_main_keyword=missing_main_keyword,
        insufficient_long_tail=insufficient_long_tail or long_tail_overflow,
        ambiguous_intent=ambiguous_intent,
        informational_only=informational_only,
        duplicate_keywords=duplicate_keywords,
        locale_market_issue=locale_market_issue,
        blocker_reasons=deduped_blockers,
        review_reasons=deduped_review,
        warning_reasons=deduped_warning,
        is_public_index_ready=False,
    )


def build_keyword_cluster_from_local_input(
    local_input: Mapping[str, Any],
) -> tuple[KeywordCluster, KeywordClusterValidationResult]:
    main_keyword, support_keywords, long_tail_keywords, main_count = _extract_keyword_groups(local_input)
    variants = tuple(
        KeywordVariant(
            keyword=str(item.get("keyword", "")).strip(),
            variant_type=str(item.get("variant_type", KeywordVariantType.LANGUAGE_VARIANT.value)).strip(),
        )
        for item in local_input.get("variants", [])
        if isinstance(item, Mapping)
    )
    cluster = KeywordCluster(
        cluster_id=str(local_input.get("cluster_id", "keyword-cluster-local")).strip(),
        locale=str(local_input.get("locale", "")).strip(),
        market=str(local_input.get("market", "")).strip().upper(),
        target_category=str(local_input.get("target_category", "")).strip(),
        buyer_intent=bool(local_input.get("buyer_intent", False)),
        intent_type=str(local_input.get("intent_type", KeywordIntentType.AMBIGUOUS.value)).strip(),
        main_keyword=main_keyword,
        support_keywords=support_keywords,
        long_tail_keywords=long_tail_keywords,
        variants=variants,
        product_spec_signals=tuple(local_input.get("product_spec_signals", [])),
        brand_model_signals=tuple(local_input.get("brand_model_signals", [])),
        source_type=str(local_input.get("source_type", KeywordSourceType.LOCAL_FIXTURE.value)).strip(),
        volume_bucket_by_keyword=dict(local_input.get("volume_bucket_by_keyword", {})),
        confidence_score=float(local_input.get("confidence_score", 0.0)),
        review_required=bool(local_input.get("review_required", False)),
        rejection_reasons=tuple(local_input.get("rejection_reasons", [])),
        blocker_reasons=tuple(local_input.get("blocker_reasons", [])),
    )
    validation = _validate_keyword_cluster(cluster, main_keyword_candidate_count=main_count)
    return cluster, validation


def validate_keyword_cluster_batch(
    clusters_or_inputs: Iterable[KeywordCluster | Mapping[str, Any]],
    *,
    review_rate_threshold: float | None = None,
) -> dict[str, Any]:
    decisions: list[KeywordClusterValidationResult] = []
    for item in clusters_or_inputs:
        if isinstance(item, KeywordCluster):
            decisions.append(_validate_keyword_cluster(item))
        else:
            _cluster, validation = build_keyword_cluster_from_local_input(item)
            decisions.append(validation)

    total_clusters = len(decisions)
    status_counts: dict[str, int] = {}
    blocker_counts: dict[str, int] = {}
    for result in decisions:
        key = result.status.value
        status_counts[key] = status_counts.get(key, 0) + 1
        for reason in result.blocker_reasons:
            blocker_counts[reason] = blocker_counts.get(reason, 0) + 1

    page_ready_count = status_counts.get(KeywordClusterStatus.PAGE_READY.value, 0)
    review_required_count = status_counts.get(KeywordClusterStatus.REVIEW_REQUIRED.value, 0)
    blocked_count = status_counts.get(KeywordClusterStatus.BLOCKED.value, 0)
    missing_main_keyword_count = sum(1 for result in decisions if result.missing_main_keyword)
    insufficient_long_tail_count = sum(1 for result in decisions if result.insufficient_long_tail)
    ambiguous_intent_count = sum(1 for result in decisions if result.ambiguous_intent)
    informational_only_count = sum(1 for result in decisions if result.informational_only)
    duplicate_keyword_count = sum(1 for result in decisions if bool(result.duplicate_keywords))
    locale_market_issue_count = sum(1 for result in decisions if result.locale_market_issue)

    if review_rate_threshold is None:
        review_rate_threshold = DEFAULT_LOCALE_RULESET.review_rate_threshold_for_step4
    review_rate = (review_required_count / total_clusters) if total_clusters else 0.0
    can_move_to_step5 = bool(total_clusters > 0 and blocked_count == 0 and review_rate <= review_rate_threshold)

    return {
        "total_clusters": total_clusters,
        "page_ready_count": page_ready_count,
        "review_required_count": review_required_count,
        "blocked_count": blocked_count,
        "missing_main_keyword_count": missing_main_keyword_count,
        "insufficient_long_tail_count": insufficient_long_tail_count,
        "ambiguous_intent_count": ambiguous_intent_count,
        "informational_only_count": informational_only_count,
        "duplicate_keyword_count": duplicate_keyword_count,
        "locale_market_issue_count": locale_market_issue_count,
        "status_counts": dict(sorted(status_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "can_move_to_step5": can_move_to_step5,
    }
