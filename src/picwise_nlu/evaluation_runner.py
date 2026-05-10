from __future__ import annotations

from typing import Any

from .expected_dataset import get_expected_intent_cases
from .output_builder import build_local_nlu_intent

_RESOLVED_STATUSES = {
    "intent_resolved",
    "specific_product_resolved",
    "general_intent_resolved",
}


def _contains_all_strings(actual: Any, expected: list[Any]) -> bool:
    if not isinstance(actual, list):
        return False
    actual_lc = [str(item).lower() for item in actual]
    for item in expected:
        if str(item).lower() not in actual_lc:
            return False
    return True


def _dict_contains(actual: Any, expected: dict[str, Any]) -> bool:
    if not isinstance(actual, dict):
        return False
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if isinstance(expected_value, dict):
            if not _dict_contains(actual_value, expected_value):
                return False
        elif isinstance(expected_value, list):
            if not _contains_all_strings(actual_value, expected_value):
                return False
        else:
            if actual_value != expected_value:
                return False
    return True


def _expected_needs_review(expected: dict[str, Any]) -> bool:
    expected_status = str(expected.get("status", "")).strip()
    if expected.get("needs_review") is True:
        return True
    return expected_status in {
        "ambiguous_needs_review",
        "manual_review_required",
        "insufficient_data",
        "no_safe_result",
        "invalid_intent",
    }


def evaluate_single_case(case: dict) -> dict:
    payload = dict(case or {})
    case_id = str(payload.get("case_id", "unknown_case"))
    user_input = str(payload.get("input", ""))
    expected = payload.get("expected", {})
    expected = expected if isinstance(expected, dict) else {}

    actual = build_local_nlu_intent(user_input)
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if isinstance(expected_value, dict):
            if not _dict_contains(actual_value, expected_value):
                mismatches.append(key)
        elif isinstance(expected_value, list):
            if not _contains_all_strings(actual_value, expected_value):
                mismatches.append(key)
        elif actual_value != expected_value:
            mismatches.append(key)

    expected_review = _expected_needs_review(expected)
    actual_status = str(actual.get("status", ""))
    actual_confidence = float(actual.get("confidence", 0.0))
    unsafe_pass = bool(
        expected_review
        and actual_status in _RESOLVED_STATUSES
        and actual_confidence >= 0.7
    )
    passed = not mismatches and not unsafe_pass

    return {
        "case_id": case_id,
        "input": user_input,
        "expected": expected,
        "actual": actual,
        "mismatch_fields": mismatches,
        "unsafe_pass": unsafe_pass,
        "passed": passed,
        "reason": "unsafe_pass" if unsafe_pass else ("field_mismatch" if mismatches else "ok"),
    }


def evaluate_local_nlu_cases(cases: list[dict] | None = None) -> dict:
    case_list = cases if isinstance(cases, list) and cases else get_expected_intent_cases()
    results = [evaluate_single_case(case) for case in case_list]
    total = len(results)
    passed = sum(1 for row in results if row.get("passed"))
    failed = total - passed
    unsafe_passes = sum(1 for row in results if row.get("unsafe_pass"))
    manual_review_count = sum(
        1 for row in results if isinstance(row.get("actual"), dict) and row["actual"].get("needs_review")
    )
    failures = [row for row in results if not row.get("passed")]
    accuracy = round((passed / total), 4) if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "accuracy": accuracy,
        "unsafe_passes": unsafe_passes,
        "manual_review_count": manual_review_count,
        "failures": failures,
        "results": results,
    }
