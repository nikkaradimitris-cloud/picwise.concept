from __future__ import annotations

from pathlib import Path

from picwise_taxonomy.importers.google_taxonomy_importer import import_google_taxonomy_local_file

from .batch_mapper import map_source_items_batch
from .mapper import map_source_item_to_taxonomy
from .validation import build_mapping_catalog, normalize_path_segments

_GOOGLE_DEFAULT_LOCAL_TAXONOMY_PATH = Path("data/taxonomy_sources/google/taxonomy.en-US.txt")


def _path_segments(source_item: dict) -> list[str]:
    metadata = source_item.get("raw_metadata", {})
    if isinstance(metadata, dict):
        raw_segments = metadata.get("path_segments")
        if isinstance(raw_segments, list) and raw_segments:
            return [str(segment).strip() for segment in raw_segments if str(segment).strip()]
    return [segment.strip() for segment in str(source_item.get("raw_path", "")).split(">") if segment.strip()]


def _normalized_segments(source_item: dict) -> list[str]:
    return [segment for segment in normalize_path_segments(" > ".join(_path_segments(source_item))) if segment]


def _contains_any(haystack: list[str], needles: tuple[str, ...]) -> bool:
    return any(needle in segment for segment in haystack for needle in needles)


def _google_mapping_hint_for_item(source_item: dict) -> dict:
    normalized_segments = _normalized_segments(source_item)
    if not normalized_segments:
        return {}
    top_level = normalized_segments[0]

    if top_level == "apparel accessories":
        if _contains_any(normalized_segments, ("shoe", "shoes", "footwear", "sneaker", "boot")):
            return {
                "proposed_engine_id": "fashion_footwear_jewelry_accessories_engine",
                "proposed_mega_category_id": "footwear_shoes_sneakers_boots",
            }

    if top_level == "vehicles parts":
        if _contains_any(normalized_segments, ("vehicle parts", "vehicle accessories", "car parts", "auto parts")):
            return {
                "proposed_engine_id": "auto_moto_mobility_engine",
                "proposed_mega_category_id": "car_parts_service_maintenance",
            }

    if top_level == "electronics":
        if _contains_any(normalized_segments, ("mobile phones", "telephony", "communications", "smartphones")):
            return {
                "proposed_engine_id": "tech_electronics_office_engine",
                "proposed_mega_category_id": "phones_mobile_accessories",
            }

    if top_level == "home garden":
        if _contains_any(normalized_segments, ("kitchen", "dining", "cookware", "tableware")):
            return {
                "proposed_engine_id": "home_living_appliances_engine",
                "proposed_mega_category_id": "kitchen_cooking_household",
            }

    return {}


def apply_google_stage24d_mapping_hints(source_item: dict) -> dict:
    hinted_item = dict(source_item or {})
    hint = _google_mapping_hint_for_item(hinted_item)
    if not hint:
        return hinted_item
    hinted_item["proposed_engine_id"] = hint["proposed_engine_id"]
    hinted_item["proposed_mega_category_id"] = hint["proposed_mega_category_id"]
    return hinted_item


def map_google_source_item_stage24d(source_item: dict):
    hinted_item = apply_google_stage24d_mapping_hints(source_item)
    return map_source_item_to_taxonomy(hinted_item)


def map_google_source_items_stage24d(source_items: list[dict]) -> dict:
    hinted_items = [apply_google_stage24d_mapping_hints(item) for item in source_items or []]
    batch_result = map_source_items_batch(hinted_items)
    catalog = build_mapping_catalog()
    mapped_results = [
        result for result in batch_result.get("mapped_results", []) if str(result.get("status", "")).strip() == "mapped"
    ]
    invalid_target_count = sum(
        1
        for result in mapped_results
        if (result.get("target") or {}).get("mega_category_id") not in catalog.mega_to_engine
        or catalog.mega_to_engine[(result.get("target") or {}).get("mega_category_id")]
        != (result.get("target") or {}).get("engine_id")
    )
    batch_result["stage24d"] = {
        "source_name": "google_product_taxonomy",
        "hinted_item_count": len(hinted_items),
        "mapped_item_count": len(mapped_results),
        "mapped_targets_valid": invalid_target_count == 0,
        "invalid_mapped_target_count": invalid_target_count,
        "stage24e_gap_report_created": False,
        "canonical_registry_created": False,
    }
    return batch_result


def load_google_source_items_from_local_import_path(file_path: str | Path | None = None) -> dict:
    local_path = Path(file_path) if file_path else _GOOGLE_DEFAULT_LOCAL_TAXONOMY_PATH
    import_report = import_google_taxonomy_local_file(str(local_path))
    return {
        "file_path": str(local_path),
        "items": import_report.get("items", []),
        "import_report": import_report,
    }


def map_google_taxonomy_local_file_stage24d(file_path: str | Path | None = None) -> dict:
    loaded = load_google_source_items_from_local_import_path(file_path=file_path)
    batch_result = map_google_source_items_stage24d(loaded["items"])
    return {
        "file_path": loaded["file_path"],
        "import_report": loaded["import_report"],
        "mapping_batch": batch_result,
        "stage24e_gap_report_created": False,
        "canonical_registry_created": False,
    }
