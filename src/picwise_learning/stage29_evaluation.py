from __future__ import annotations

from collections.abc import Callable, Iterable

from picwise_nlu.output_builder import build_local_nlu_intent

from .stage29_contracts import Stage29EvaluationRecord, Stage29GeneratedQueryRecord


def _default_local_nlu_evaluator(query: str) -> dict:
    return build_local_nlu_intent(query)


def _resolve_actual_target(result: dict) -> str:
    category = str(result.get("category") or "").strip()
    if category:
        return category
    query_type = str(result.get("query_type", "")).strip()
    if query_type in {"unknown", "ambiguous_query"}:
        return "unavailable:not_supported"
    return "unavailable:not_connected"


def _resolve_status(expected_target: str, actual_target: str, result: dict) -> tuple[str, str | None]:
    status = str(result.get("status", "")).strip()
    confidence = float(result.get("confidence", 0.0) or 0.0)
    if actual_target.startswith("unavailable:"):
        return "unknown", "unsupported_interface"
    if bool(result.get("needs_review")):
        return "manual_review", "unknown_intent"
    if expected_target == actual_target:
        if confidence >= 0.7:
            return "passed", None
        return "manual_review", "unknown_intent"
    if status in {"specific_product_resolved", "general_intent_resolved", "intent_resolved"}:
        return "failed", "wrong_category"
    return "unknown", "unsupported_interface"


def evaluate_generated_queries(
    generated_records: Iterable[Stage29GeneratedQueryRecord],
    evaluator: Callable[[str], dict] | None = None,
) -> list[Stage29EvaluationRecord]:
    local_evaluator = evaluator or _default_local_nlu_evaluator
    rows: list[Stage29EvaluationRecord] = []
    for record in generated_records:
        result = local_evaluator(record.generated_query)
        actual_target = _resolve_actual_target(result)
        eval_status, failure_type = _resolve_status(record.expected_nlu_target, actual_target, result)
        confidence = result.get("confidence", "unavailable:not_supported")
        actual_vertical = "retail_physical_products" if actual_target and not actual_target.startswith("unavailable:") else "unavailable:not_supported"
        if record.vertical != "retail_physical_products":
            actual_vertical = "unavailable:not_supported"
        if eval_status == "passed" and record.expected_intent == "manual_review_expected":
            eval_status, failure_type = "unsafe_pass", "unsafe_pass"
        rows.append(
            Stage29EvaluationRecord(
                generated_query_record_id=record.record_id,
                generated_query=record.generated_query,
                expected_nlu_target=record.expected_nlu_target,
                actual_nlu_target=actual_target,
                expected_vertical=record.vertical,
                actual_vertical=actual_vertical,
                status=eval_status,
                failure_type=failure_type,
                confidence=confidence,
                notes=f"local_nlu_status:{result.get('status', 'unavailable:not_supported')}",
            )
        )
    return rows
