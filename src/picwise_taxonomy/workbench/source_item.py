from __future__ import annotations

from copy import deepcopy

from .validation import validate_json_serializable, validate_no_inventory_fields

_ALLOWED_SOURCE_TYPES = {
    "manual_seed",
    "csv_import",
    "json_import",
    "yaml_import",
    "feed_category_export",
    "marketplace_category_reference",
    "public_taxonomy_reference",
    "operator_gap_report",
}


def _normalize_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        values = []
    cleaned = sorted({_normalize_string(value) for value in values if _normalize_string(value)})
    return cleaned


def _normalize_string_dict(values: object) -> dict:
    if not isinstance(values, dict):
        return {}
    normalized: dict[str, str] = {}
    for key in sorted(values.keys(), key=lambda item: str(item)):
        normalized[_normalize_string(key)] = _normalize_string(values[key])
    return normalized


def build_source_item(
    source_item_id: str,
    source_name: str,
    source_type: str,
    raw_label: str,
    raw_parent_label: str = "",
    raw_path: str = "",
    raw_metadata: dict | None = None,
    proposed_engine_id: str = "",
    proposed_mega_category_id: str = "",
    proposed_node_type: str = "",
    proposed_canonical_label: str = "",
    proposed_aliases: list[str] | None = None,
    proposed_spec_fields: list[str] | None = None,
    proposed_intent_patterns: list[str] | None = None,
    confidence: float = 0.0,
    status: str = "draft",
    notes: str = "",
) -> dict:
    item = {
        "source_item_id": source_item_id,
        "source_name": source_name,
        "source_type": source_type,
        "raw_label": raw_label,
        "raw_parent_label": raw_parent_label,
        "raw_path": raw_path,
        "raw_metadata": raw_metadata or {},
        "proposed_engine_id": proposed_engine_id,
        "proposed_mega_category_id": proposed_mega_category_id,
        "proposed_node_type": proposed_node_type,
        "proposed_canonical_label": proposed_canonical_label,
        "proposed_aliases": proposed_aliases or [],
        "proposed_spec_fields": proposed_spec_fields or [],
        "proposed_intent_patterns": proposed_intent_patterns or [],
        "confidence": float(confidence),
        "status": status,
        "notes": notes,
    }
    return normalize_source_item(item)


def normalize_source_item(item: dict) -> dict:
    normalized = deepcopy(item)
    for field in (
        "source_item_id",
        "source_name",
        "source_type",
        "raw_label",
        "raw_parent_label",
        "raw_path",
        "proposed_engine_id",
        "proposed_mega_category_id",
        "proposed_node_type",
        "proposed_canonical_label",
        "status",
        "notes",
    ):
        normalized[field] = _normalize_string(normalized.get(field))

    normalized["raw_metadata"] = _normalize_string_dict(normalized.get("raw_metadata"))
    normalized["proposed_aliases"] = _normalize_string_list(normalized.get("proposed_aliases"))
    normalized["proposed_spec_fields"] = _normalize_string_list(normalized.get("proposed_spec_fields"))
    normalized["proposed_intent_patterns"] = _normalize_string_list(
        normalized.get("proposed_intent_patterns")
    )
    normalized["confidence"] = float(normalized.get("confidence", 0.0))
    return normalized


def validate_source_item(item: dict) -> dict:
    normalized = normalize_source_item(item)
    inventory_validation = validate_no_inventory_fields(normalized)
    serializable_validation = validate_json_serializable(normalized)

    required_fields = (
        "source_item_id",
        "source_name",
        "source_type",
        "raw_label",
        "raw_parent_label",
        "raw_path",
        "raw_metadata",
        "proposed_engine_id",
        "proposed_mega_category_id",
        "proposed_node_type",
        "proposed_canonical_label",
        "proposed_aliases",
        "proposed_spec_fields",
        "proposed_intent_patterns",
        "confidence",
        "status",
        "notes",
    )
    missing_required_fields = [key for key in required_fields if key not in normalized]
    source_type_valid = normalized["source_type"] in _ALLOWED_SOURCE_TYPES

    result = {
        "valid": True,
        "passed": True,
        "item": normalized,
        "missing_required_fields": missing_required_fields,
        "source_type_valid": source_type_valid,
        "no_forbidden_inventory_fields": inventory_validation["valid"],
        "inventory_validation": inventory_validation,
        "is_json_serializable": serializable_validation["valid"],
        "is_foundation_only": True,
        "has_external_fetch_behavior": False,
    }
    result["valid"] = (
        not result["missing_required_fields"]
        and result["source_type_valid"]
        and result["no_forbidden_inventory_fields"]
        and result["is_json_serializable"]
        and result["is_foundation_only"]
        and not result["has_external_fetch_behavior"]
    )
    result["passed"] = result["valid"]
    return result
