from __future__ import annotations

from typing import Any

from picwise_nlu.output_builder import build_local_nlu_intent

from .stage30_config import Stage30ShadowConfig, build_default_stage30_config
from .stage30_decision_comparison import compare_runtime_vs_shadow
from .stage30_shadow_records import build_shadow_record
from .stage30_validation import validate_shadow_record


def _infer_runtime_target(runtime_decision: dict[str, Any]) -> str:
    target = str(runtime_decision.get("existing_runtime_target") or "").strip()
    if target:
        return target
    target = str(runtime_decision.get("category") or "").strip()
    if target:
        return target
    route_type = str(runtime_decision.get("route_type") or "").strip()
    if route_type in {"ambiguous_query", "no_safe_result"}:
        return "unknown"
    return "unknown"


def _infer_runtime_vertical(runtime_decision: dict[str, Any]) -> str:
    explicit = str(runtime_decision.get("existing_runtime_vertical") or runtime_decision.get("vertical") or "").strip()
    if explicit:
        return explicit
    route_type = str(runtime_decision.get("route_type") or "").strip()
    if route_type in {"specific_product", "general_intent", "ambiguous_query", "no_safe_result"}:
        return "retail_physical_products"
    return "unknown"


def _infer_shadow_vertical(shadow_intent: dict[str, Any], runtime_vertical: str) -> str:
    query_type = str(shadow_intent.get("query_type") or "").strip()
    if query_type in {"specific_product", "general_intent", "ambiguous_query"}:
        return "retail_physical_products"
    if runtime_vertical:
        return runtime_vertical
    return "unknown"


class Stage30ShadowRunner:
    def __init__(self, config: Stage30ShadowConfig | None = None) -> None:
        self._config = config or build_default_stage30_config()

    def run_shadow(
        self,
        *,
        runtime_query: str,
        runtime_decision: dict[str, Any],
        source_surface: str | None = None,
        source_route: str | None = None,
        timestamp: str | None = None,
    ):
        runtime_target = _infer_runtime_target(runtime_decision)
        runtime_vertical = _infer_runtime_vertical(runtime_decision)

        try:
            shadow_intent = build_local_nlu_intent(runtime_query)
        except Exception as error:  # pragma: no cover - defensive runtime safety.
            shadow_intent = {
                "status": "not_available",
                "needs_review": True,
                "query_type": "unknown",
                "category": "unknown",
                "confidence": 0.0,
                "reason_codes": ["shadow_probe_error"],
                "error_type": error.__class__.__name__,
            }

        shadow_target = str(shadow_intent.get("category") or "unknown")
        shadow_vertical = _infer_shadow_vertical(shadow_intent, runtime_vertical)
        comparison = compare_runtime_vs_shadow(
            runtime_target=runtime_target,
            runtime_vertical=runtime_vertical,
            runtime_decision=str(runtime_decision.get("status") or runtime_decision.get("existing_runtime_decision") or ""),
            shadow_target=shadow_target,
            shadow_vertical=shadow_vertical,
            shadow_status=str(shadow_intent.get("status") or ""),
            shadow_needs_review=bool(shadow_intent.get("needs_review", False)),
            config=self._config,
        )
        record = build_shadow_record(
            runtime_query=runtime_query,
            normalized_query=str(runtime_decision.get("normalized_query") or "").strip(),
            source_surface=source_surface or self._config.source_surface_default,
            source_route=source_route or self._config.source_route_default,
            existing_runtime_decision=str(runtime_decision.get("status") or runtime_decision.get("existing_runtime_decision") or "unknown"),
            existing_runtime_target=runtime_target,
            existing_runtime_vertical=runtime_vertical,
            shadow_nlu_target=shadow_target,
            shadow_vertical=shadow_vertical,
            shadow_confidence=float(shadow_intent.get("confidence", 0.0) or 0.0),
            comparison_status=comparison.comparison_status,
            failure_type=comparison.failure_type,
            expected_learning_action=comparison.expected_learning_action,
            vertical=comparison.vertical,
            metadata={
                "shadow_query_type": str(shadow_intent.get("query_type") or ""),
                "shadow_status": str(shadow_intent.get("status") or ""),
                "shadow_reason_codes": list(shadow_intent.get("reason_codes", [])),
                "manual_review": comparison.manual_review,
            },
            timestamp=timestamp,
        )
        report = validate_shadow_record(record)
        if not report["valid"]:
            raise ValueError(f"Invalid Stage 30 shadow record: {report['errors']}")
        return record
