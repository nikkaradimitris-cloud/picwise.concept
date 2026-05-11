from __future__ import annotations

import hashlib

from picwise_taxonomy.workbench.gap_registry import build_gap_record

from .contracts import MappingStatus, TaxonomyMappingResult


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
    return "Add deterministic taxonomy seed coverage and remap."


def route_mapping_result_to_gap(
    mapping_result: TaxonomyMappingResult,
    source_item: dict,
) -> dict | None:
    if mapping_result.status == MappingStatus.MAPPED:
        return None

    source_item_id = str(source_item.get("source_item_id", "")).strip()
    source_name = str(source_item.get("source_name", "")).strip()
    raw_path = str(source_item.get("raw_path", "")).strip()
    raw_label = str(source_item.get("raw_label", "")).strip()
    raw_parent_label = str(source_item.get("raw_parent_label", "")).strip()
    reason_code = mapping_result.gap_reason.value if mapping_result.gap_reason else "no_mega_category_match"

    base_gap = build_gap_record(
        gap_id=_stable_gap_id(source_item_id or mapping_result.source_item_id, reason_code),
        raw_term=raw_label or source_item_id,
        normalized_term=mapping_result.normalized_label,
        suggested_engine_id=mapping_result.suggested_engine_id,
        suggested_mega_category_id=mapping_result.suggested_mega_category_id,
        suggested_department=(mapping_result.target.department if mapping_result.target else ""),
        suggested_subcategory=(mapping_result.target.subcategory if mapping_result.target else ""),
        suggested_product_family=(mapping_result.target.product_family if mapping_result.target else ""),
        related_terms=[term for term in [raw_parent_label, raw_path] if term],
        greeklish_terms=[],
        typo_terms=[],
        reason=reason_code,
        severity="high" if mapping_result.status == MappingStatus.INVALID_SOURCE else "medium",
        status="needs_mapping" if mapping_result.status != MappingStatus.NEEDS_REVIEW else "new_gap",
        source="mapping_layer",
        notes="deterministic_mapping_gap",
        schema_version="24B.0",
    )
    base_gap["source_item_id"] = source_item_id or mapping_result.source_item_id
    base_gap["source_name"] = source_name
    base_gap["original_source_name_path"] = {
        "source_name": source_name,
        "raw_path": raw_path,
        "raw_label": raw_label,
    }
    base_gap["attempted_normalized"] = {
        "normalized_label": mapping_result.normalized_label,
        "normalized_path": mapping_result.normalized_path,
    }
    base_gap["reason_code"] = reason_code
    base_gap["confidence"] = mapping_result.confidence.value
    base_gap["operator_action_hint"] = mapping_result.operator_action_hint or _build_operator_hint(
        mapping_result.status, reason_code
    )
    return base_gap
