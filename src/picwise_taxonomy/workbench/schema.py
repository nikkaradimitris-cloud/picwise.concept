from __future__ import annotations

from copy import deepcopy

from .validation import validate_json_serializable, validate_no_inventory_fields

_ALLOWED_NODE_TYPES = {
    "engine",
    "mega_category",
    "department",
    "subcategory",
    "product_family",
    "intent_family",
    "alias",
    "spec_field",
    "priority",
    "ambiguity_rule",
    "source_reference",
    "gap",
}

_ALLOWED_COVERAGE_STATUS = {
    "not_started",
    "weak",
    "partial",
    "strong",
    "deep",
    "blocked",
    "needs_review",
}

_ALLOWED_REVIEW_STATUS = {
    "draft",
    "needs_mapping",
    "mapped",
    "needs_review",
    "approved",
    "rejected",
    "deprecated",
}

_REQUIRED_LIST_FIELDS = (
    "labels",
    "aliases",
    "greek_aliases",
    "greeklish_aliases",
    "typo_aliases",
    "spec_fields",
    "priority_terms",
    "intent_patterns",
    "ambiguity_rules",
    "source_references",
)

_FORBIDDEN_INVENTORY_TOKENS = (
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "affiliate",
    "commission",
    "seller",
    "store",
    "sku",
    "inventory",
)


def is_forbidden_inventory_field(key: str) -> bool:
    lowered = str(key).strip().lower()
    return any(token in lowered for token in _FORBIDDEN_INVENTORY_TOKENS)


def _normalize_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        values = []
    cleaned = sorted({_normalize_string(value) for value in values if _normalize_string(value)})
    return cleaned


def build_taxonomy_record(
    taxonomy_id: str,
    node_type: str,
    canonical_label: str,
    parent_id: str | None = None,
    engine_id: str | None = None,
    mega_category_id: str | None = None,
    display_label: str | None = None,
    labels: list[str] | None = None,
    aliases: list[str] | None = None,
    greek_aliases: list[str] | None = None,
    greeklish_aliases: list[str] | None = None,
    typo_aliases: list[str] | None = None,
    spec_fields: list[str] | None = None,
    priority_terms: list[str] | None = None,
    intent_patterns: list[str] | None = None,
    ambiguity_rules: list[str] | None = None,
    source_references: list[dict] | None = None,
    coverage_status: str = "not_started",
    review_status: str = "draft",
    confidence: float = 0.0,
    notes: str = "",
    schema_version: str = "24A.1",
) -> dict:
    record = {
        "taxonomy_id": taxonomy_id,
        "parent_id": parent_id or "",
        "engine_id": engine_id or "",
        "mega_category_id": mega_category_id or "",
        "node_type": node_type,
        "canonical_label": canonical_label,
        "display_label": display_label or canonical_label,
        "labels": labels or [canonical_label],
        "aliases": aliases or [],
        "greek_aliases": greek_aliases or [],
        "greeklish_aliases": greeklish_aliases or [],
        "typo_aliases": typo_aliases or [],
        "spec_fields": spec_fields or [],
        "priority_terms": priority_terms or [],
        "intent_patterns": intent_patterns or [],
        "ambiguity_rules": ambiguity_rules or [],
        "source_references": source_references or [],
        "coverage_status": coverage_status,
        "review_status": review_status,
        "confidence": float(confidence),
        "notes": notes,
        "schema_version": schema_version,
    }
    return normalize_taxonomy_record(record)


def normalize_taxonomy_record(record: dict) -> dict:
    normalized = deepcopy(record)
    normalized["taxonomy_id"] = _normalize_string(normalized.get("taxonomy_id"))
    normalized["parent_id"] = _normalize_string(normalized.get("parent_id"))
    normalized["engine_id"] = _normalize_string(normalized.get("engine_id"))
    normalized["mega_category_id"] = _normalize_string(normalized.get("mega_category_id"))
    normalized["node_type"] = _normalize_string(normalized.get("node_type"))
    normalized["canonical_label"] = _normalize_string(normalized.get("canonical_label"))
    normalized["display_label"] = _normalize_string(
        normalized.get("display_label") or normalized["canonical_label"]
    )
    normalized["coverage_status"] = _normalize_string(
        normalized.get("coverage_status") or "not_started"
    )
    normalized["review_status"] = _normalize_string(normalized.get("review_status") or "draft")
    normalized["notes"] = _normalize_string(normalized.get("notes"))
    normalized["schema_version"] = _normalize_string(normalized.get("schema_version") or "24A.1")
    normalized["confidence"] = float(normalized.get("confidence", 0.0))

    for field in _REQUIRED_LIST_FIELDS:
        normalized[field] = _normalize_string_list(normalized.get(field, []))

    source_references = normalized.get("source_references", [])
    if not isinstance(source_references, list):
        source_references = []
    cleaned_source_references: list[dict] = []
    for entry in source_references:
        if not isinstance(entry, dict):
            continue
        clean_entry = {
            "source_name": _normalize_string(entry.get("source_name")),
            "source_type": _normalize_string(entry.get("source_type")),
            "source_item_id": _normalize_string(entry.get("source_item_id")),
            "notes": _normalize_string(entry.get("notes")),
        }
        cleaned_source_references.append(clean_entry)
    normalized["source_references"] = sorted(
        cleaned_source_references,
        key=lambda item: (
            item["source_name"],
            item["source_type"],
            item["source_item_id"],
            item["notes"],
        ),
    )
    return normalized


def validate_taxonomy_record(record: dict) -> dict:
    normalized = normalize_taxonomy_record(record)
    inventory_validation = validate_no_inventory_fields(normalized)
    serializable_validation = validate_json_serializable(normalized)

    missing_required_fields = [
        key
        for key in (
            "taxonomy_id",
            "parent_id",
            "engine_id",
            "mega_category_id",
            "node_type",
            "canonical_label",
            "display_label",
            "labels",
            "aliases",
            "greek_aliases",
            "greeklish_aliases",
            "typo_aliases",
            "spec_fields",
            "priority_terms",
            "intent_patterns",
            "ambiguity_rules",
            "source_references",
            "coverage_status",
            "review_status",
            "confidence",
            "notes",
            "schema_version",
        )
        if key not in normalized
    ]
    list_fields_valid = all(isinstance(normalized.get(field), list) for field in _REQUIRED_LIST_FIELDS)
    node_type_valid = normalized["node_type"] in _ALLOWED_NODE_TYPES
    coverage_status_valid = normalized["coverage_status"] in _ALLOWED_COVERAGE_STATUS
    review_status_valid = normalized["review_status"] in _ALLOWED_REVIEW_STATUS

    result = {
        "valid": True,
        "passed": True,
        "record": normalized,
        "missing_required_fields": missing_required_fields,
        "node_type_valid": node_type_valid,
        "coverage_status_valid": coverage_status_valid,
        "review_status_valid": review_status_valid,
        "list_fields_valid": list_fields_valid,
        "no_forbidden_inventory_fields": inventory_validation["valid"],
        "inventory_validation": inventory_validation,
        "is_json_serializable": serializable_validation["valid"],
    }
    result["valid"] = (
        not result["missing_required_fields"]
        and result["node_type_valid"]
        and result["coverage_status_valid"]
        and result["review_status_valid"]
        and result["list_fields_valid"]
        and result["no_forbidden_inventory_fields"]
        and result["is_json_serializable"]
    )
    result["passed"] = result["valid"]
    return result
