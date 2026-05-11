from __future__ import annotations

import hashlib

from picwise_taxonomy.workbench.gap_registry import build_gap_record

from .contracts import MappingStatus, TaxonomyMappingResult

_STAGE_24E_TITLE = "Stage 24E — Unmapped / Gap Report"
_SAFE_SUGGESTION_REASON_CODES = {
    "no_engine_match",
    "unknown_department",
    "unknown_subcategory",
    "unknown_product_family",
}


def _stable_gap_id(source_item_id: str, reason_code: str) -> str:
    digest = hashlib.sha1(f"{source_item_id}|{reason_code}".encode("utf-8")).hexdigest()
    return f"gap_map_{digest[:16]}"


def _build_operator_hint(status: MappingStatus, reason_code: str) -> str:
    if status == MappingStatus.INVALID_SOURCE:
        return "Fix invalid source schema/fields and re-import."
    if reason_code == "weak_match_needs_review":
        return "Review weak match and confirm safe taxonomy node."
    if "ambiguous" in reason_code:
        return "Resolve ambiguity with explicit engine/mega/department context."
    if "unknown_" in reason_code:
        return "Extend curated seeds or coverage structure and remap."
    if reason_code == "unsupported_google_path":
        return "Google path is outside supported mapping scope; route to operator backlog for explicit coverage."
    return "Add deterministic taxonomy seed coverage and remap."


def _safe_suggestions(
    reason_code: str,
    suggested_engine_id: str,
    suggested_mega_category_id: str,
) -> tuple[str, str]:
    if reason_code in _SAFE_SUGGESTION_REASON_CODES:
        return suggested_engine_id, suggested_mega_category_id
    return "", ""


def _status_or_default(status: str) -> MappingStatus:
    try:
        return MappingStatus(status)
    except ValueError:
        return MappingStatus.UNMAPPED


def _route_to_gap(
    *,
    source_item_id: str,
    source_name: str,
    source_type: str,
    raw_path: str,
    raw_label: str,
    normalized_label: str,
    normalized_path: str,
    status: str,
    confidence: str,
    reason_code: str,
    operator_action_hint: str,
    suggested_engine_id: str,
    suggested_mega_category_id: str,
) -> dict | None:
    if status == MappingStatus.MAPPED.value:
        return None

    safe_engine, safe_mega = _safe_suggestions(reason_code, suggested_engine_id, suggested_mega_category_id)

    base_gap = build_gap_record(
        gap_id=_stable_gap_id(source_item_id, reason_code),
        raw_term=raw_label or source_item_id,
        normalized_term=normalized_label,
        suggested_engine_id=safe_engine,
        suggested_mega_category_id=safe_mega,
        suggested_department="",
        suggested_subcategory="",
        suggested_product_family="",
        related_terms=[term for term in [raw_path] if term],
        greeklish_terms=[],
        typo_terms=[],
        reason=reason_code,
        severity="high" if status == MappingStatus.INVALID_SOURCE.value else "medium",
        status="needs_mapping" if status != MappingStatus.NEEDS_REVIEW.value else "new_gap",
        source="mapping_layer",
        notes="deterministic_mapping_gap",
        schema_version="24B.0",
    )
    base_gap["source_item_id"] = source_item_id
    base_gap["source_id"] = source_item_id
    base_gap["source_name"] = source_name
    base_gap["source_type"] = source_type
    base_gap["original_path"] = raw_path
    base_gap["original_name"] = raw_label
    base_gap["normalized_path"] = normalized_path
    base_gap["normalized_name"] = normalized_label
    base_gap["original_source_name_path"] = {
        "source_name": source_name,
        "raw_path": raw_path,
        "raw_label": raw_label,
    }
    base_gap["attempted_normalized"] = {
        "normalized_label": normalized_label,
        "normalized_path": normalized_path,
    }
    base_gap["reason_code"] = reason_code
    base_gap["confidence"] = confidence
    base_gap["mapping_status"] = status
    base_gap["operator_action_hint"] = operator_action_hint or _build_operator_hint(_status_or_default(status), reason_code)
    base_gap["stage"] = _STAGE_24E_TITLE
    if not safe_engine:
        base_gap["suggested_engine_id"] = ""
    if not safe_mega:
        base_gap["suggested_mega_category_id"] = ""
    return base_gap


def route_mapping_result_to_gap(
    mapping_result: TaxonomyMappingResult,
    source_item: dict,
    *,
    reason_code_override: str = "",
) -> dict | None:
    source_item_id = str(source_item.get("source_item_id", "")).strip() or mapping_result.source_item_id
    source_name = str(source_item.get("source_name", "")).strip()
    source_type = str(source_item.get("source_type", "")).strip()
    raw_path = str(source_item.get("raw_path", "")).strip()
    raw_label = str(source_item.get("raw_label", "")).strip()
    reason_code = reason_code_override or (
        mapping_result.gap_reason.value if mapping_result.gap_reason else "no_mega_category_match"
    )
    return _route_to_gap(
        source_item_id=source_item_id,
        source_name=source_name,
        source_type=source_type,
        raw_path=raw_path,
        raw_label=raw_label,
        normalized_label=mapping_result.normalized_label,
        normalized_path=mapping_result.normalized_path,
        status=mapping_result.status.value,
        confidence=mapping_result.confidence.value,
        reason_code=reason_code,
        operator_action_hint=mapping_result.operator_action_hint,
        suggested_engine_id=mapping_result.suggested_engine_id,
        suggested_mega_category_id=mapping_result.suggested_mega_category_id,
    )


def route_mapping_payload_to_gap(
    mapping_payload: dict,
    source_item: dict,
    *,
    reason_code_override: str = "",
) -> dict | None:
    source_item_id = str(source_item.get("source_item_id", "")).strip() or str(
        mapping_payload.get("source_item_id", "")
    ).strip()
    source_name = str(source_item.get("source_name", "")).strip()
    source_type = str(source_item.get("source_type", "")).strip()
    raw_path = str(source_item.get("raw_path", "")).strip()
    raw_label = str(source_item.get("raw_label", "")).strip()
    status = str(mapping_payload.get("status", "")).strip()
    reason_code = reason_code_override or str(mapping_payload.get("gap_reason", "")).strip() or "no_mega_category_match"
    return _route_to_gap(
        source_item_id=source_item_id,
        source_name=source_name,
        source_type=source_type,
        raw_path=raw_path,
        raw_label=raw_label,
        normalized_label=str(mapping_payload.get("normalized_label", "")).strip(),
        normalized_path=str(mapping_payload.get("normalized_path", "")).strip(),
        status=status,
        confidence=str(mapping_payload.get("confidence", "")).strip(),
        reason_code=reason_code,
        operator_action_hint=str(mapping_payload.get("operator_action_hint", "")).strip(),
        suggested_engine_id=str(mapping_payload.get("suggested_engine_id", "")).strip(),
        suggested_mega_category_id=str(mapping_payload.get("suggested_mega_category_id", "")).strip(),
    )
