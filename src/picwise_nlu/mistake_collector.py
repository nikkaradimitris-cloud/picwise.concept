from __future__ import annotations

from typing import Any


def collect_mistakes(evaluation_report: dict) -> list[dict]:
    report = dict(evaluation_report or {})
    failures = report.get("failures", [])
    if not isinstance(failures, list):
        return []

    mistakes: list[dict] = []
    for failure in failures:
        row = dict(failure or {})
        mistakes.append(
            {
                "case_id": str(row.get("case_id", "")),
                "input": str(row.get("input", "")),
                "expected": row.get("expected", {}) if isinstance(row.get("expected"), dict) else {},
                "actual": row.get("actual", {}) if isinstance(row.get("actual"), dict) else {},
                "mismatch_fields": list(row.get("mismatch_fields", []))
                if isinstance(row.get("mismatch_fields"), list)
                else [],
                "reason": str(row.get("reason", "field_mismatch")),
            }
        )
    return mistakes


def summarize_mistakes(mistakes: list[dict]) -> dict:
    safe_mistakes = mistakes if isinstance(mistakes, list) else []
    mismatch_counter: dict[str, int] = {}
    reason_counter: dict[str, int] = {}

    for row in safe_mistakes:
        payload = dict(row or {})
        for field in payload.get("mismatch_fields", []):
            key = str(field).strip()
            if key:
                mismatch_counter[key] = mismatch_counter.get(key, 0) + 1
        reason = str(payload.get("reason", "")).strip() or "field_mismatch"
        reason_counter[reason] = reason_counter.get(reason, 0) + 1

    return {
        "total_mistakes": len(safe_mistakes),
        "mismatch_field_counts": mismatch_counter,
        "reason_counts": reason_counter,
    }
