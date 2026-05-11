from __future__ import annotations

from copy import deepcopy

from .validation import validate_json_serializable, validate_no_inventory_fields

_ALLOWED_SEVERITY = {"low", "medium", "high", "critical"}
_ALLOWED_STATUS = {
    "new_gap",
    "needs_mapping",
    "mapped",
    "needs_deep_pack",
    "covered",
    "rejected",
}


def _normalize_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        values = []
    return sorted({_normalize_string(value) for value in values if _normalize_string(value)})


def _slugify(raw: str) -> str:
    cleaned = "".join(character if character.isalnum() else "_" for character in raw.lower())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "gap"


def build_gap_record(
    gap_id: str,
    raw_term: str,
    normalized_term: str,
    suggested_engine_id: str = "",
    suggested_mega_category_id: str = "",
    suggested_department: str = "",
    suggested_subcategory: str = "",
    suggested_product_family: str = "",
    related_terms: list[str] | None = None,
    greeklish_terms: list[str] | None = None,
    typo_terms: list[str] | None = None,
    reason: str = "",
    severity: str = "medium",
    status: str = "new_gap",
    source: str = "operator_gap_report",
    notes: str = "",
    schema_version: str = "24A.1",
) -> dict:
    record = {
        "gap_id": gap_id,
        "raw_term": raw_term,
        "normalized_term": normalized_term,
        "suggested_engine_id": suggested_engine_id,
        "suggested_mega_category_id": suggested_mega_category_id,
        "suggested_department": suggested_department,
        "suggested_subcategory": suggested_subcategory,
        "suggested_product_family": suggested_product_family,
        "related_terms": related_terms or [],
        "greeklish_terms": greeklish_terms or [],
        "typo_terms": typo_terms or [],
        "reason": reason,
        "severity": severity,
        "status": status,
        "source": source,
        "notes": notes,
        "schema_version": schema_version,
    }
    return normalize_gap_record(record)


def normalize_gap_record(record: dict) -> dict:
    normalized = deepcopy(record)
    for field in (
        "gap_id",
        "raw_term",
        "normalized_term",
        "suggested_engine_id",
        "suggested_mega_category_id",
        "suggested_department",
        "suggested_subcategory",
        "suggested_product_family",
        "reason",
        "severity",
        "status",
        "source",
        "notes",
        "schema_version",
    ):
        normalized[field] = _normalize_string(normalized.get(field))

    normalized["related_terms"] = _normalize_string_list(normalized.get("related_terms"))
    normalized["greeklish_terms"] = _normalize_string_list(normalized.get("greeklish_terms"))
    normalized["typo_terms"] = _normalize_string_list(normalized.get("typo_terms"))
    return normalized


def validate_gap_record(record: dict) -> dict:
    normalized = normalize_gap_record(record)
    inventory_validation = validate_no_inventory_fields(normalized)
    serializable_validation = validate_json_serializable(normalized)
    severity_valid = normalized["severity"] in _ALLOWED_SEVERITY
    status_valid = normalized["status"] in _ALLOWED_STATUS

    required_fields = (
        "gap_id",
        "raw_term",
        "normalized_term",
        "suggested_engine_id",
        "suggested_mega_category_id",
        "suggested_department",
        "suggested_subcategory",
        "suggested_product_family",
        "related_terms",
        "greeklish_terms",
        "typo_terms",
        "reason",
        "severity",
        "status",
        "source",
        "notes",
        "schema_version",
    )
    missing_required_fields = [key for key in required_fields if key not in normalized]
    result = {
        "valid": True,
        "passed": True,
        "record": normalized,
        "missing_required_fields": missing_required_fields,
        "severity_valid": severity_valid,
        "status_valid": status_valid,
        "no_forbidden_inventory_fields": inventory_validation["valid"],
        "inventory_validation": inventory_validation,
        "is_json_serializable": serializable_validation["valid"],
    }
    result["valid"] = (
        not result["missing_required_fields"]
        and result["severity_valid"]
        and result["status_valid"]
        and result["no_forbidden_inventory_fields"]
        and result["is_json_serializable"]
    )
    result["passed"] = result["valid"]
    return result


def create_gap_from_missing_term(
    raw_term: str,
    suggested_engine_id: str | None = None,
    suggested_mega_category_id: str | None = None,
) -> dict:
    term = _normalize_string(raw_term)
    normalized_term = term.lower()
    engine_id = _normalize_string(suggested_engine_id)
    mega_category_id = _normalize_string(suggested_mega_category_id)

    auto_engine = "auto_moto_mobility_engine"
    auto_mega = "moto_bicycle_mobility_gear"
    if term == "πατίνια":
        if not engine_id:
            engine_id = auto_engine
        if not mega_category_id:
            mega_category_id = auto_mega

    status = "mapped" if engine_id and mega_category_id else "needs_mapping"
    gap_id = f"gap_{_slugify(normalized_term)}"
    return build_gap_record(
        gap_id=gap_id,
        raw_term=term,
        normalized_term=normalized_term,
        suggested_engine_id=engine_id,
        suggested_mega_category_id=mega_category_id,
        suggested_department="",
        suggested_subcategory="",
        suggested_product_family="",
        related_terms=[],
        greeklish_terms=[],
        typo_terms=[],
        reason="missing_term_detected",
        severity="medium",
        status=status,
        source="operator_gap_report",
        notes="created_from_missing_term",
        schema_version="24A.1",
    )
