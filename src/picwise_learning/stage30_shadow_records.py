from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from .stage30_contracts import STAGE30_ID, Stage30ShadowRecord


def _detect_language(query: str) -> str:
    text = str(query or "")
    if any("\u0370" <= char <= "\u03ff" for char in text):
        return "el"
    return "en"


def _detect_noise_signals(query: str) -> tuple[str, ...]:
    raw = str(query or "")
    signals: list[str] = []
    if "  " in raw:
        signals.append("double_spaces")
    if "??" in raw or "!!" in raw:
        signals.append("punctuation_noise")
    if any(char.isalpha() for char in raw):
        lowered = raw.lower()
        uppered = raw.upper()
        if raw != lowered and raw != uppered:
            signals.append("case_mix")
    if not signals:
        signals.append("clean")
    return tuple(signals)


def build_shadow_record(
    *,
    runtime_query: str,
    normalized_query: str,
    source_surface: str,
    source_route: str,
    existing_runtime_decision: str,
    existing_runtime_target: str | None,
    existing_runtime_vertical: str | None,
    shadow_nlu_target: str,
    shadow_vertical: str,
    shadow_confidence: float | str,
    comparison_status: str,
    failure_type: str | None,
    expected_learning_action: str,
    vertical: str,
    metadata: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> Stage30ShadowRecord:
    resolved_timestamp = timestamp or datetime.now(UTC).isoformat()
    payload = "|".join(
        [
            str(runtime_query or "").strip().lower(),
            str(resolved_timestamp),
            str(existing_runtime_target or "").strip().lower(),
            str(shadow_nlu_target or "").strip().lower(),
        ]
    )
    record_id = "s30_shadow_" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return Stage30ShadowRecord(
        shadow_record_id=record_id,
        stage=STAGE30_ID,
        runtime_query=str(runtime_query or ""),
        normalized_query=str(normalized_query or ""),
        timestamp=resolved_timestamp,
        source_surface=str(source_surface or ""),
        source_route=str(source_route or ""),
        existing_runtime_decision=str(existing_runtime_decision or ""),
        existing_runtime_target=existing_runtime_target,
        existing_runtime_vertical=existing_runtime_vertical,
        shadow_nlu_target=str(shadow_nlu_target or "unknown"),
        shadow_vertical=str(shadow_vertical or "unknown"),
        shadow_confidence=shadow_confidence,
        comparison_status=str(comparison_status or "manual_review"),
        failure_type=failure_type,
        vertical=str(vertical or "unknown"),
        language=_detect_language(runtime_query),
        noise_signals=_detect_noise_signals(runtime_query),
        expected_learning_action=str(expected_learning_action or "none"),
        did_affect_runtime=False,
        metadata=metadata or {},
    )
