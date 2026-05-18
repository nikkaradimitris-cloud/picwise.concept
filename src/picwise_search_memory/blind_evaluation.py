from __future__ import annotations

from collections import Counter

from picwise_nlu.query_variant_generator import generate_noisy_variants_for_term

from .canonical_registry import build_canonical_vocabulary_registry
from .contracts import CanonicalVocabularyRegistry
from .evaluation_contracts import (
    BlindEvaluationCase,
    BlindEvaluationReport,
    BlindEvaluationResult,
    BlindEvaluationThresholds,
)
from .index_builder import build_offline_search_index
from .index_contracts import SearchIndex, SearchIndexLookupResult
from .index_lookup import lookup_offline_search_index
from .validation import normalize_term

_NEGATIVE_BROAD_TERMS: tuple[str, ...] = (
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
)

_PREFERRED_VARIANT_TYPES: tuple[str, ...] = (
    "joined_words",
    "missing_letter",
    "extra_letter",
    "swapped_adjacent_letters",
    "repeated_letter",
    "vowel_drop",
    "us_uk_spelling",
)


def _is_shared_taxonomy_or_meta_term(term: str) -> bool:
    normalized = normalize_term(term)
    if not normalized:
        return False
    tokens = tuple(token for token in normalized.split() if token)
    if not tokens:
        return False
    meta_tokens = {
        "taxonomy",
        "families",
        "family",
        "source",
        "entry",
        "entries",
        "valid",
        "daily",
        "compatibility",
        "sets",
    }
    shared_marker_count = sum(1 for token in tokens if token in meta_tokens)
    if shared_marker_count >= 1 and len(tokens) <= 2:
        return True
    if len(tokens) == 1 and len(tokens[0]) <= 7:
        return True
    return False


def _shared_term_categories(registry: CanonicalVocabularyRegistry) -> dict[str, set[str]]:
    categories_by_term: dict[str, set[str]] = {}
    for record in registry.records:
        categories_by_term.setdefault(record.normalized_term, set()).add(record.mega_category_id)
    return categories_by_term


def _build_case(
    *,
    case_id: str,
    canonical_id: str,
    canonical_term: str,
    mega_category_id: str,
    query: str,
    expected_normalized_term: str,
    expected_mega_category_id: str,
    variant_type: str,
    source: str,
    should_match: bool,
) -> BlindEvaluationCase:
    return BlindEvaluationCase(
        case_id=case_id,
        canonical_id=canonical_id,
        canonical_term=canonical_term,
        mega_category_id=mega_category_id,
        query=query,
        expected_normalized_term=expected_normalized_term,
        expected_mega_category_id=expected_mega_category_id,
        variant_type=variant_type,
        source=source,
        should_match=should_match,
    )


def _generate_case_variants(record) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = [(record.canonical_term, "exact_canonical")]
    generated = generate_noisy_variants_for_term(record.canonical_term, record.mega_category_id)
    by_type: dict[str, str] = {}
    for row in generated:
        variant = normalize_term(row.get("variant", ""))
        variant_type = str(row.get("variant_type", "")).strip()
        if not variant or not variant_type:
            continue
        if variant_type not in by_type:
            by_type[variant_type] = variant
    for variant_type in _PREFERRED_VARIANT_TYPES:
        variant = by_type.get(variant_type)
        if variant:
            output.append((variant, variant_type))
    return output


def generate_blind_evaluation_cases(
    registry: CanonicalVocabularyRegistry,
    *,
    include_negative_terms: bool = True,
) -> tuple[BlindEvaluationCase, ...]:
    cases: list[BlindEvaluationCase] = []
    case_index = 1
    categories_by_term = _shared_term_categories(registry)

    for record in sorted(registry.records, key=lambda row: (row.mega_category_id, row.normalized_term, row.canonical_id)):
        variants = _generate_case_variants(record)
        shared_category_count = len(categories_by_term.get(record.normalized_term, {record.mega_category_id}))
        shared_term_negative = shared_category_count >= 3 and _is_shared_taxonomy_or_meta_term(record.normalized_term)
        for query, variant_type in variants:
            should_match = not shared_term_negative
            expected_normalized_term = record.normalized_term if should_match else ""
            expected_mega_category_id = record.mega_category_id if should_match else ""
            expected_canonical_id = record.canonical_id if should_match else ""
            case_variant_type = "shared_term_negative" if shared_term_negative else variant_type
            source = (
                "shared_taxonomy_term_safety_set"
                if shared_term_negative
                else f"{record.source}+stage3_variant_generator"
            )
            cases.append(
                _build_case(
                    case_id=f"blind_{case_index:06d}",
                    canonical_id=expected_canonical_id,
                    canonical_term=record.canonical_term,
                    mega_category_id=record.mega_category_id,
                    query=query,
                    expected_normalized_term=expected_normalized_term,
                    expected_mega_category_id=expected_mega_category_id,
                    variant_type=case_variant_type,
                    source=source,
                    should_match=should_match,
                )
            )
            case_index += 1

    if include_negative_terms:
        for broad_term in _NEGATIVE_BROAD_TERMS:
            normalized = normalize_term(broad_term)
            cases.append(
                _build_case(
                    case_id=f"blind_{case_index:06d}",
                    canonical_id="",
                    canonical_term="",
                    mega_category_id="",
                    query=normalized,
                    expected_normalized_term="",
                    expected_mega_category_id="",
                    variant_type="broad_term_negative",
                    source="broad_term_safety_set",
                    should_match=False,
                )
            )
            case_index += 1

    return tuple(cases)


def _evaluate_case(case: BlindEvaluationCase, lookup_result: SearchIndexLookupResult) -> BlindEvaluationResult:
    matched_canonical_id = lookup_result.matched_entry.canonical_id if lookup_result.matched_entry else ""
    matched_mega_category_id = lookup_result.matched_entry.mega_category_id if lookup_result.matched_entry else ""

    if case.should_match:
        passed = (
            lookup_result.status == "match"
            and matched_canonical_id == case.canonical_id
            and matched_mega_category_id == case.expected_mega_category_id
        )
    else:
        passed = lookup_result.status != "match"

    return BlindEvaluationResult(
        case_id=case.case_id,
        query=case.query,
        expected_canonical_id=case.canonical_id,
        expected_mega_category_id=case.expected_mega_category_id,
        matched_canonical_id=matched_canonical_id,
        matched_mega_category_id=matched_mega_category_id,
        status=lookup_result.status,
        score=lookup_result.score,
        passed=passed,
        reason_codes=tuple(sorted(set(lookup_result.reason_codes))),
    )


def evaluate_blind_cases(cases: tuple[BlindEvaluationCase, ...], index: SearchIndex) -> tuple[BlindEvaluationResult, ...]:
    results: list[BlindEvaluationResult] = []
    for case in cases:
        lookup_result = lookup_offline_search_index(case.query, index)
        results.append(_evaluate_case(case, lookup_result))
    return tuple(results)


def _safe_divide(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def build_blind_evaluation_report(
    cases: tuple[BlindEvaluationCase, ...],
    results: tuple[BlindEvaluationResult, ...],
    thresholds: BlindEvaluationThresholds | None = None,
) -> BlindEvaluationReport:
    threshold_config = thresholds or BlindEvaluationThresholds()
    case_by_id = {case.case_id: case for case in cases}
    total_cases = len(cases)
    passed_total = sum(1 for row in results if row.passed)
    failed_total = total_cases - passed_total

    positive_cases = [case for case in cases if case.should_match]
    negative_cases = [case for case in cases if not case.should_match]
    positive_case_ids = {case.case_id for case in positive_cases}
    negative_case_ids = {case.case_id for case in negative_cases}
    broad_case_ids = {case.case_id for case in cases if case.variant_type == "broad_term_negative"}

    canonical_correct = 0
    category_correct = 0
    no_match_count = 0
    wrong_category_count = 0
    false_positive_count = 0
    broad_safety_pass = 0

    for result in results:
        if result.status != "match":
            no_match_count += 1
        if result.case_id in positive_case_ids:
            if result.matched_canonical_id == result.expected_canonical_id and result.status == "match":
                canonical_correct += 1
            if result.matched_mega_category_id == result.expected_mega_category_id and result.status == "match":
                category_correct += 1
            if result.status == "match" and result.expected_mega_category_id and (
                result.matched_mega_category_id != result.expected_mega_category_id
            ):
                wrong_category_count += 1
        elif result.case_id in negative_case_ids and result.status == "match":
            false_positive_count += 1
        if result.case_id in broad_case_ids and result.status != "match":
            broad_safety_pass += 1

    accuracy = _safe_divide(passed_total, total_cases)
    canonical_accuracy = _safe_divide(canonical_correct, len(positive_cases))
    mega_category_accuracy = _safe_divide(category_correct, len(positive_cases))
    no_match_rate = _safe_divide(no_match_count, total_cases)
    wrong_category_rate = _safe_divide(wrong_category_count, len(positive_cases))
    false_positive_rate = _safe_divide(false_positive_count, len(negative_cases))
    broad_term_safety_rate = _safe_divide(broad_safety_pass, len(broad_case_ids))

    counts_by_mega_category: Counter[str] = Counter()
    counts_by_variant_type: Counter[str] = Counter()
    for case in cases:
        mega = case.expected_mega_category_id if case.expected_mega_category_id else "__broad_or_negative__"
        counts_by_mega_category[mega] += 1
        counts_by_variant_type[case.variant_type] += 1

    threshold_status = {
        "mega_category_accuracy": mega_category_accuracy >= threshold_config.mega_category_accuracy_min,
        "canonical_accuracy": canonical_accuracy >= threshold_config.canonical_accuracy_min,
        "wrong_category_rate": wrong_category_rate <= threshold_config.wrong_category_rate_max,
        "false_positive_rate": false_positive_rate <= threshold_config.false_positive_rate_max,
        "broad_term_safety_rate": broad_term_safety_rate >= threshold_config.broad_term_safety_rate_min,
    }
    can_proceed_to_stage5 = all(threshold_status.values())

    failed_cases = tuple(row for row in results if not row.passed)
    return BlindEvaluationReport(
        total_cases=total_cases,
        passed=passed_total,
        failed=failed_total,
        accuracy=round(accuracy, 4),
        canonical_accuracy=round(canonical_accuracy, 4),
        mega_category_accuracy=round(mega_category_accuracy, 4),
        no_match_rate=round(no_match_rate, 4),
        wrong_category_rate=round(wrong_category_rate, 4),
        false_positive_rate=round(false_positive_rate, 4),
        broad_term_safety_rate=round(broad_term_safety_rate, 4),
        counts_by_mega_category_id=dict(sorted(counts_by_mega_category.items())),
        counts_by_variant_type=dict(sorted(counts_by_variant_type.items())),
        failed_cases=failed_cases,
        threshold_status=threshold_status,
        can_proceed_to_stage5=can_proceed_to_stage5,
    )


def run_offline_blind_index_evaluation(
    *,
    thresholds: BlindEvaluationThresholds | None = None,
    include_negative_terms: bool = True,
) -> BlindEvaluationReport:
    registry = build_canonical_vocabulary_registry()
    index = build_offline_search_index(registry=registry)
    cases = generate_blind_evaluation_cases(registry, include_negative_terms=include_negative_terms)
    results = evaluate_blind_cases(cases, index)
    return build_blind_evaluation_report(cases, results, thresholds=thresholds)
