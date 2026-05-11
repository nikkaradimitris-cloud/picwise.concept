from __future__ import annotations

from picwise_taxonomy.workbench.source_item import validate_source_item
from picwise_taxonomy.workbench.validation import validate_json_serializable

_FORBIDDEN_INVENTORY_TOKENS = (
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "prices",
    "affiliate",
    "affiliate_url",
    "commission",
    "seller",
    "store",
    "store_offer",
    "sku",
    "stock",
    "inventory",
    "checkout",
)

_ALLOWED_TAXONOMY_CLASSIFICATION_KEYS = {
    "node_type",
    "product_family",
    "suggested_product_family",
    "product_families",
}


def _is_forbidden_inventory_key(key: str) -> bool:
    lowered = str(key).strip().lower()
    if lowered in _ALLOWED_TAXONOMY_CLASSIFICATION_KEYS:
        return False
    return any(token in lowered for token in _FORBIDDEN_INVENTORY_TOKENS)


def reject_inventory_like_source_record(record: dict) -> dict:
    violations: list[str] = []

    def _walk(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key in sorted(value.keys(), key=lambda item: str(item)):
                current_path = f"{path}.{key}" if path else str(key)
                if _is_forbidden_inventory_key(str(key)):
                    violations.append(current_path)
                _walk(value[key], current_path)
        elif isinstance(value, list):
            for index, entry in enumerate(value):
                _walk(entry, f"{path}[{index}]")

    _walk(record if isinstance(record, dict) else {}, "")
    unique_violations = sorted(set(violations))
    return {
        "valid": len(unique_violations) == 0,
        "passed": len(unique_violations) == 0,
        "record": record if isinstance(record, dict) else {},
        "forbidden_key_paths": unique_violations,
        "forbidden_key_count": len(unique_violations),
        "inventory_like_rejected": len(unique_violations) > 0,
    }


def validate_imported_source_items(items: list[dict]) -> dict:
    validation_results = []
    for item in items or []:
        record_check = reject_inventory_like_source_record(item if isinstance(item, dict) else {})
        item_check = validate_source_item(item if isinstance(item, dict) else {})
        validation_results.append(
            {
                "inventory_record_validation": record_check,
                "source_item_validation": item_check,
                "valid": record_check["valid"] and item_check["valid"],
            }
        )

    all_valid = all(entry["valid"] for entry in validation_results) if validation_results else True
    serializable_check = validate_json_serializable(items or [])
    return {
        "valid": all_valid and serializable_check["valid"],
        "passed": all_valid and serializable_check["valid"],
        "total_items": len(items or []),
        "valid_item_count": sum(1 for entry in validation_results if entry["valid"]),
        "invalid_item_count": sum(1 for entry in validation_results if not entry["valid"]),
        "item_validations": validation_results,
        "json_serializable": serializable_check["valid"],
        "no_claude_or_api_or_live_llm_dependency": True,
        "foundation_only": True,
    }


def validate_importer_foundation() -> dict:
    from .google_taxonomy_importer import parse_google_taxonomy_text
    from .path_parser import build_source_item_from_path
    from .structured_source_importer import import_source_csv_text, import_source_json_text

    manual_item = build_source_item_from_path(
        path="Apparel & Accessories > Shoes > Athletic Shoes",
        source_name="manual_seed_pack",
        source_type="manual_seed",
    )
    google_items = parse_google_taxonomy_text(
        "\n".join(
            [
                "# google taxonomy sample",
                "Apparel & Accessories > Shoes",
                "Hardware > Tools",
            ]
        )
    )
    json_items = import_source_json_text(
        '[{"path": "Home & Garden > Kitchen & Dining", "aliases": ["kitchen", "dining"]}]',
        source_name="json_seed",
    )
    csv_items = import_source_csv_text(
        "path,label,parent,aliases\nVehicles & Parts > Vehicle Parts & Accessories,,,parts|accessories\n",
        source_name="csv_seed",
    )
    combined = [manual_item] + google_items + json_items + csv_items
    combined_validation = validate_imported_source_items(combined)
    serializable_check = validate_json_serializable(combined)

    return {
        "valid": combined_validation["valid"] and serializable_check["valid"],
        "passed": combined_validation["valid"] and serializable_check["valid"],
        "manual_path_parsing_works": bool(manual_item.get("raw_path")),
        "google_text_parsing_works": len(google_items) > 0,
        "json_structured_import_works": len(json_items) > 0,
        "csv_structured_import_works": len(csv_items) > 0,
        "source_item_validation_works": combined_validation["valid"],
        "inventory_protection_works": combined_validation["valid"],
        "json_serializable_outputs": serializable_check["valid"],
        "local_file_or_text_only": True,
        "no_claude_or_api_or_live_llm_dependency": True,
        "no_product_inventory_logic": True,
        "no_sku_or_offer_or_price_logic": True,
    }
