from __future__ import annotations

from collections import Counter, defaultdict

from picwise_search_memory.blind_evaluation import (
    evaluate_blind_cases,
    generate_blind_evaluation_cases,
)
from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry
from picwise_search_memory.index_builder import build_offline_search_index
from picwise_search_memory.index_contracts import SearchIndexLookupResult
from picwise_search_memory.index_lookup import lookup_offline_search_index
from picwise_search_memory.validation import normalize_term

from .stage7b_contracts import SearchLearningCase
from .stage7b_contracts import SearchLearningReport
from .stage7b_contracts import SearchLearningResult
from .stage7b_contracts import SearchLearningSuggestion

_BROAD_NEGATIVE_TERMS = {
    "bank",
    "charger",
    "apple",
    "nike",
    "bosch",
    "insurance",
    "loan",
    "erp",
    "crm",
    "accounting software",
}

_CONNECTED_PROVIDER_CATEGORIES = {"power_banks"}
_CONNECTED_PROVIDER_MEGA_CATEGORIES = {"phones_mobile_accessories"}


def _to_case(
    query: str,
    lookup_result: SearchIndexLookupResult,
    source: str,
    expected_behavior: str = "",
) -> SearchLearningCase:
    return SearchLearningCase(
        query=query,
        normalized_query=lookup_result.normalized_query or normalize_term(query),
        observed_status=lookup_result.status,
        expected_behavior=expected_behavior,
        matched_canonical_id=lookup_result.matched_entry.canonical_id if lookup_result.matched_entry else "",
        matched_mega_category_id=lookup_result.matched_entry.mega_category_id if lookup_result.matched_entry else "",
        confidence=lookup_result.score,
        reason_codes=tuple(sorted(set(lookup_result.reason_codes))),
        source=source,
        review_status="pending_human_review",
    )


def classify_search_learning_case(case: SearchLearningCase) -> str:
    reasons = set(case.reason_codes)
    if case.normalized_query in _BROAD_NEGATIVE_TERMS:
        return "broad_negative_safe"
    if case.observed_status != "match":
        if "ambiguous_top_candidates" in reasons or "ambiguous_exact_collision" in reasons:
            return "ambiguous"
        if "cross_category_exact_collision" in reasons:
            return "false_positive_risk"
        if case.confidence > 0.0:
            return "low_confidence"
        return "not_understood"

    if case.expected_behavior == "provider_connected":
        if (
            case.matched_canonical_id in _CONNECTED_PROVIDER_CATEGORIES
            or case.matched_mega_category_id in _CONNECTED_PROVIDER_MEGA_CATEGORIES
        ):
            return "connected_provider_result"
        return "wrong_category"

    if case.expected_behavior == "provider_not_connected":
        return "provider_not_connected"
    if case.expected_behavior == "broad_negative":
        return "broad_negative_safe"
    if case.expected_behavior == "unknown":
        return "false_positive_risk"

    if case.confidence < 0.84:
        return "low_confidence"
    return "no_action_needed"


def collect_search_learning_signals(cases: tuple[SearchLearningCase, ...]) -> tuple[SearchLearningResult, ...]:
    results: list[SearchLearningResult] = []
    for case in cases:
        classification = classify_search_learning_case(case)
        requires_review = classification in {
            "not_understood",
            "low_confidence",
            "ambiguous",
            "wrong_category",
            "provider_not_connected",
            "false_positive_risk",
        }
        results.append(
            SearchLearningResult(
                case=case,
                classification=classification,
                requires_review=requires_review,
            )
        )
    return tuple(results)


def _looks_like_typo(normalized_query: str) -> bool:
    return normalized_query not in _BROAD_NEGATIVE_TERMS and any(
        token for token in normalized_query.split() if len(token) >= 5 and token.count(token[0]) >= 3
    )


def generate_search_learning_suggestions(
    results: tuple[SearchLearningResult, ...],
) -> tuple[SearchLearningSuggestion, ...]:
    by_bucket: dict[tuple[str, str], list[SearchLearningResult]] = defaultdict(list)
    for row in results:
        category_key = row.case.matched_mega_category_id or "unknown_category"
        by_bucket[(row.classification, category_key)].append(row)

    suggestions: list[SearchLearningSuggestion] = []
    for (classification, category), bucket in sorted(by_bucket.items(), key=lambda item: (item[0][0], item[0][1])):
        evidence = tuple(sorted({f"{row.case.query}|{row.case.observed_status}|{row.case.confidence:.4f}" for row in bucket}))
        suggestion_id = f"stage7b_{classification}_{category}_{len(bucket)}"
        if classification == "provider_not_connected":
            suggestions.append(
                SearchLearningSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type="provider needed for category",
                    proposed_action="track provider integration priority for category",
                    target_layer="provider_connectivity_planning",
                    affected_category=category,
                    evidence=evidence,
                    risk_level="medium",
                    requires_human_approval=True,
                    can_auto_apply=False,
                )
            )
            continue
        if classification == "broad_negative_safe":
            suggestions.append(
                SearchLearningSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type="keep broad negative blocked",
                    proposed_action="preserve broad negative blocking behavior",
                    target_layer="search_safety_review",
                    affected_category=category,
                    evidence=evidence,
                    risk_level="low",
                    requires_human_approval=True,
                    can_auto_apply=False,
                )
            )
            continue
        if classification == "not_understood":
            clean_candidates = [
                row.case.normalized_query
                for row in bucket
                if row.case.normalized_query
                and len(row.case.normalized_query.split()) >= 2
                and not _looks_like_typo(row.case.normalized_query)
            ]
            if clean_candidates:
                suggestions.append(
                    SearchLearningSuggestion(
                        suggestion_id=suggestion_id,
                        suggestion_type="add clean canonical vocabulary term",
                        proposed_action="review clean unknown terms for canonical vocabulary inclusion",
                        target_layer="canonical_vocabulary_registry",
                        affected_category=category,
                        evidence=tuple(sorted(set(clean_candidates)))[:10],
                        risk_level="medium",
                        requires_human_approval=True,
                        can_auto_apply=False,
                    )
                )
            else:
                suggestions.append(
                    SearchLearningSuggestion(
                        suggestion_id=suggestion_id,
                        suggestion_type="review ambiguous term",
                        proposed_action="manual linguistic review for unknown/unclear queries",
                        target_layer="offline_learning_review",
                        affected_category=category,
                        evidence=evidence,
                        risk_level="high",
                        requires_human_approval=True,
                        can_auto_apply=False,
                    )
                )
            continue
        if classification in {"low_confidence", "ambiguous", "false_positive_risk"}:
            suggestion_type = "improve generic variant generation" if classification == "low_confidence" else "review ambiguous term"
            target_layer = "query_variant_generator_generic" if classification == "low_confidence" else "offline_learning_review"
            suggestions.append(
                SearchLearningSuggestion(
                    suggestion_id=suggestion_id,
                    suggestion_type=suggestion_type,
                    proposed_action="manual review and offline improvement proposal only",
                    target_layer=target_layer,
                    affected_category=category,
                    evidence=evidence,
                    risk_level="high" if classification != "low_confidence" else "medium",
                    requires_human_approval=True,
                    can_auto_apply=False,
                )
            )
            continue
        suggestions.append(
            SearchLearningSuggestion(
                suggestion_id=suggestion_id,
                suggestion_type="no action needed",
                proposed_action="no learning update required",
                target_layer="offline_learning_review",
                affected_category=category,
                evidence=evidence,
                risk_level="low",
                requires_human_approval=True,
                can_auto_apply=False,
            )
        )

    return tuple(suggestions)


def _build_learning_report(
    results: tuple[SearchLearningResult, ...],
    suggestions: tuple[SearchLearningSuggestion, ...],
    sources: tuple[str, ...],
) -> SearchLearningReport:
    counts = Counter(row.classification for row in results)
    suggestion_counts = Counter(row.suggestion_type for row in suggestions)
    return SearchLearningReport(
        total_cases=len(results),
        not_understood_count=counts.get("not_understood", 0),
        low_confidence_count=counts.get("low_confidence", 0),
        ambiguous_count=counts.get("ambiguous", 0),
        wrong_category_count=counts.get("wrong_category", 0),
        provider_not_connected_count=counts.get("provider_not_connected", 0),
        broad_negative_safe_count=counts.get("broad_negative_safe", 0),
        connected_provider_result_count=counts.get("connected_provider_result", 0),
        false_positive_risk_count=counts.get("false_positive_risk", 0),
        suggestions_by_type=dict(sorted(suggestion_counts.items())),
        suggestions_requiring_approval=sum(1 for row in suggestions if row.requires_human_approval),
        can_auto_apply_anything=False,
        results=results,
        suggestions=suggestions,
        sources=sources,
    )


def run_controlled_search_learning_review(
    query_batch: tuple[dict[str, str], ...] | None = None,
) -> SearchLearningReport:
    registry = build_canonical_vocabulary_registry()
    index = build_offline_search_index(registry=registry)
    blind_cases = generate_blind_evaluation_cases(registry, include_negative_terms=True)
    blind_results = evaluate_blind_cases(blind_cases, index)
    _ = blind_results

    default_batch = (
        {"query": "washing machine", "expected_behavior": "provider_not_connected"},
        {"query": "coffee grinder", "expected_behavior": "provider_not_connected"},
        {"query": "office chair", "expected_behavior": "provider_not_connected"},
        {"query": "usb cable", "expected_behavior": "provider_not_connected"},
        {"query": "gaming mouse", "expected_behavior": "provider_not_connected"},
        {"query": "bluetooth speaker", "expected_behavior": "provider_not_connected"},
        {"query": "car battery", "expected_behavior": "provider_not_connected"},
        {"query": "car tyre", "expected_behavior": "provider_not_connected"},
        {"query": "bike helmet", "expected_behavior": "provider_not_connected"},
        {"query": "cordless drill", "expected_behavior": "provider_not_connected"},
        {"query": "screwdriver set", "expected_behavior": "provider_not_connected"},
        {"query": "garden shears", "expected_behavior": "provider_not_connected"},
        {"query": "blood pressure monitor", "expected_behavior": "provider_not_connected"},
        {"query": "beard trimmer", "expected_behavior": "provider_not_connected"},
        {"query": "baby car seat", "expected_behavior": "provider_not_connected"},
        {"query": "winter jacket", "expected_behavior": "provider_not_connected"},
        {"query": "running shoes", "expected_behavior": "provider_not_connected"},
        {"query": "wrist watch", "expected_behavior": "provider_not_connected"},
        {"query": "bank", "expected_behavior": "broad_negative"},
        {"query": "insurance", "expected_behavior": "broad_negative"},
        {"query": "power bank", "expected_behavior": "provider_connected"},
        {"query": "xqzv lmnqpt", "expected_behavior": "unknown"},
    )
    input_batch = query_batch or default_batch

    cases: list[SearchLearningCase] = []
    for row in input_batch:
        query = row.get("query", "")
        expected_behavior = row.get("expected_behavior", "")
        lookup_result = lookup_offline_search_index(query, index)
        cases.append(
            _to_case(
                query=query,
                lookup_result=lookup_result,
                source="stage7b_acceptance_batch",
                expected_behavior=expected_behavior,
            )
        )

    results = collect_search_learning_signals(tuple(cases))
    suggestions = generate_search_learning_suggestions(results)
    return _build_learning_report(
        results=results,
        suggestions=suggestions,
        sources=("stage6a_generated_blind_evaluation", "stage7b_acceptance_batch"),
    )

