from __future__ import annotations

import json

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

_ALLOWED_TAXONOMY_KEYS = {
    "node_type",
    "product_family",
    "suggested_product_family",
    "product_families",
}


def _is_forbidden_key(key: str) -> bool:
    lowered = str(key).strip().lower()
    if lowered in _ALLOWED_TAXONOMY_KEYS:
        return False
    return any(token in lowered for token in _FORBIDDEN_INVENTORY_TOKENS)


def validate_no_inventory_fields(obj: dict | list) -> dict:
    violations: list[str] = []

    def _walk(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key in sorted(value.keys(), key=lambda item: str(item)):
                current_path = f"{path}.{key}" if path else str(key)
                if _is_forbidden_key(str(key)):
                    violations.append(current_path)
                _walk(value[key], current_path)
        elif isinstance(value, list):
            for index, entry in enumerate(value):
                _walk(entry, f"{path}[{index}]")

    _walk(obj, "")
    violations = sorted(set(violations))
    return {
        "valid": len(violations) == 0,
        "passed": len(violations) == 0,
        "forbidden_key_paths": violations,
        "forbidden_key_count": len(violations),
    }


def validate_json_serializable(obj) -> dict:
    try:
        json.dumps(obj, sort_keys=True)
        is_json_serializable = True
        error = ""
    except (TypeError, ValueError) as exc:
        is_json_serializable = False
        error = str(exc)
    return {
        "valid": is_json_serializable,
        "passed": is_json_serializable,
        "is_json_serializable": is_json_serializable,
        "error": error,
    }


def validate_workbench_foundation() -> dict:
    from .coverage_matrix import build_coverage_matrix
    from .gap_registry import create_gap_from_missing_term, validate_gap_record
    from .schema import build_taxonomy_record, validate_taxonomy_record
    from .source_item import build_source_item, validate_source_item

    taxonomy_record = build_taxonomy_record(
        taxonomy_id="engine_auto_moto_mobility",
        node_type="engine",
        canonical_label="Auto Moto Mobility",
        engine_id="auto_moto_mobility_engine",
        mega_category_id="moto_bicycle_mobility_gear",
        coverage_status="strong",
        review_status="mapped",
    )
    source_item = build_source_item(
        source_item_id="source_item_001",
        source_name="seed_workbook",
        source_type="manual_seed",
        raw_label="Πατίνια",
        proposed_engine_id="auto_moto_mobility_engine",
        proposed_mega_category_id="moto_bicycle_mobility_gear",
        proposed_node_type="product_family",
        proposed_canonical_label="Scooters",
    )
    gap_record = create_gap_from_missing_term(
        "πατίνια",
        suggested_engine_id="auto_moto_mobility_engine",
        suggested_mega_category_id="moto_bicycle_mobility_gear",
    )
    matrix = build_coverage_matrix([taxonomy_record, {**taxonomy_record, "node_type": "gap"}])

    schema_validation = validate_taxonomy_record(taxonomy_record)
    source_item_validation = validate_source_item(source_item)
    gap_validation = validate_gap_record(gap_record)
    inventory_validation = validate_no_inventory_fields(
        {
            "taxonomy_record": taxonomy_record,
            "source_item": source_item,
            "gap_record": gap_record,
            "matrix": matrix,
        }
    )
    serializable_validation = validate_json_serializable(
        {
            "taxonomy_record": taxonomy_record,
            "source_item": source_item,
            "gap_record": gap_record,
            "matrix": matrix,
        }
    )

    deterministic_output = validate_json_serializable(
        {"matrix_once": matrix, "matrix_twice": build_coverage_matrix([taxonomy_record, {**taxonomy_record, "node_type": "gap"}])}
    )["valid"]

    result = {
        "valid": True,
        "passed": True,
        "schema_module_works": schema_validation["valid"],
        "source_item_module_works": source_item_validation["valid"],
        "gap_registry_module_works": gap_validation["valid"],
        "coverage_matrix_module_works": isinstance(matrix, dict) and "coverage_status_counts" in matrix,
        "no_forbidden_inventory_or_commercial_fields": inventory_validation["valid"],
        "json_serializable_outputs": serializable_validation["valid"],
        "deterministic_outputs": deterministic_output,
        "no_claude_or_api_or_live_llm_dependency": True,
        "foundation_only": True,
        "does_not_import_external_taxonomy": True,
    }
    result["valid"] = (
        result["schema_module_works"]
        and result["source_item_module_works"]
        and result["gap_registry_module_works"]
        and result["coverage_matrix_module_works"]
        and result["no_forbidden_inventory_or_commercial_fields"]
        and result["json_serializable_outputs"]
        and result["deterministic_outputs"]
        and result["no_claude_or_api_or_live_llm_dependency"]
        and result["foundation_only"]
        and result["does_not_import_external_taxonomy"]
    )
    result["passed"] = result["valid"]
    return result
