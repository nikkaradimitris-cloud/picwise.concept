from __future__ import annotations

import re
from dataclasses import dataclass

from picwise_taxonomy.coverage_plan import get_mega_category_coverage_plan
from picwise_taxonomy.deep_packs import (
    get_fashion_footwear_jewelry_accessories_pack,
    get_tools_diy_garden_repair_pack,
)
from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.importers.import_validation import reject_inventory_like_source_record
from picwise_taxonomy.mega_category_registry import get_mega_category_registry
from picwise_taxonomy.workbench.source_item import normalize_source_item, validate_source_item

from .contracts import MappingTarget

_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_text(value: str) -> str:
    lowered = str(value or "").strip().lower()
    return _NORMALIZE_PATTERN.sub(" ", lowered).strip()


def split_normalized_tokens(value: str) -> set[str]:
    normalized = normalize_text(value)
    if not normalized:
        return set()
    return {token for token in normalized.split(" ") if token}


def normalize_path_segments(path: str) -> list[str]:
    segments = [normalize_text(segment) for segment in str(path or "").split(">")]
    return [segment for segment in segments if segment]


@dataclass(frozen=True)
class MegaTaxonomySeeds:
    mega_category_id: str
    engine_id: str
    display_name: str
    department_labels: set[str]
    subcategory_labels: set[str]
    product_family_labels: set[str]
    mega_alias_labels: set[str]


@dataclass(frozen=True)
class MappingCatalog:
    valid_engine_ids: set[str]
    engine_to_megas: dict[str, set[str]]
    mega_to_engine: dict[str, str]
    mega_seeds: dict[str, MegaTaxonomySeeds]
    engine_labels: dict[str, set[str]]
    mega_labels: dict[str, set[str]]


def _build_engine_labels() -> dict[str, set[str]]:
    labels: dict[str, set[str]] = {}
    for engine in get_engine_registry():
        engine_id = engine["engine_id"]
        labels[engine_id] = {
            normalize_text(engine_id),
            normalize_text(engine.get("display_name", "")),
        }
    return labels


def _deep_pack_map() -> dict[str, dict]:
    records = {}
    for record in get_tools_diy_garden_repair_pack()["mega_categories"]:
        records[record["mega_category_id"]] = record
    for record in get_fashion_footwear_jewelry_accessories_pack()["mega_categories"]:
        records[record["mega_category_id"]] = record
    return records


def _merge_labels(values: list[str] | set[str]) -> set[str]:
    return {normalize_text(value) for value in values if normalize_text(value)}


def build_mapping_catalog() -> MappingCatalog:
    engines = get_engine_registry()
    mega_records = get_mega_category_registry()
    coverage_records = {record["mega_category_id"]: record for record in get_mega_category_coverage_plan()}
    deep_pack_records = _deep_pack_map()

    valid_engine_ids = {engine["engine_id"] for engine in engines}
    engine_to_megas: dict[str, set[str]] = {
        engine["engine_id"]: set(engine.get("mega_category_ids", [])) for engine in engines
    }
    mega_to_engine: dict[str, str] = {
        mega["mega_category_id"]: mega["engine_id"] for mega in mega_records
    }
    engine_labels = _build_engine_labels()

    mega_seeds: dict[str, MegaTaxonomySeeds] = {}
    mega_labels: dict[str, set[str]] = {}
    for mega in mega_records:
        mega_id = mega["mega_category_id"]
        coverage = coverage_records.get(mega_id, {})
        deep_pack = deep_pack_records.get(mega_id, {})
        department_labels = _merge_labels(
            list(coverage.get("department_seed_examples", [])) + list(deep_pack.get("departments", []))
        )
        subcategory_labels = _merge_labels(
            list(coverage.get("subcategory_seed_examples", [])) + list(deep_pack.get("subcategories", []))
        )
        product_family_labels = _merge_labels(
            list(coverage.get("product_family_seed_examples", []))
            + list(deep_pack.get("product_families", []))
        )
        mega_alias_labels = _merge_labels(
            list(coverage.get("alias_seed_examples", []))
            + list(deep_pack.get("alias_terms", []))
            + [mega.get("display_name", ""), mega_id]
        )
        mega_seeds[mega_id] = MegaTaxonomySeeds(
            mega_category_id=mega_id,
            engine_id=mega["engine_id"],
            display_name=mega.get("display_name", ""),
            department_labels=department_labels,
            subcategory_labels=subcategory_labels,
            product_family_labels=product_family_labels,
            mega_alias_labels=mega_alias_labels,
        )
        mega_labels[mega_id] = set(mega_alias_labels)

    return MappingCatalog(
        valid_engine_ids=valid_engine_ids,
        engine_to_megas=engine_to_megas,
        mega_to_engine=mega_to_engine,
        mega_seeds=mega_seeds,
        engine_labels=engine_labels,
        mega_labels=mega_labels,
    )


def validate_mapping_input(source_item: dict) -> dict:
    source_validation = validate_source_item(source_item)
    inventory_validation = reject_inventory_like_source_record(source_item)
    normalized_item = normalize_source_item(source_item if isinstance(source_item, dict) else {})
    return {
        "valid": source_validation["valid"] and inventory_validation["valid"],
        "source_validation": source_validation,
        "inventory_validation": inventory_validation,
        "normalized_item": normalized_item,
    }


def validate_mapping_target(target: MappingTarget, catalog: MappingCatalog) -> dict:
    engine_exists = target.engine_id in catalog.valid_engine_ids
    mega_exists = target.mega_category_id in catalog.mega_to_engine
    mega_belongs_to_engine = mega_exists and catalog.mega_to_engine[target.mega_category_id] == target.engine_id
    seeds = catalog.mega_seeds.get(target.mega_category_id)
    department_ok = (not target.department) or bool(seeds and normalize_text(target.department) in seeds.department_labels)
    subcategory_ok = (not target.subcategory) or bool(
        seeds and normalize_text(target.subcategory) in seeds.subcategory_labels
    )
    product_family_ok = (not target.product_family) or bool(
        seeds and normalize_text(target.product_family) in seeds.product_family_labels
    )
    return {
        "valid": engine_exists
        and mega_exists
        and mega_belongs_to_engine
        and department_ok
        and subcategory_ok
        and product_family_ok,
        "engine_exists": engine_exists,
        "mega_exists": mega_exists,
        "mega_belongs_to_engine": mega_belongs_to_engine,
        "department_ok": department_ok,
        "subcategory_ok": subcategory_ok,
        "product_family_ok": product_family_ok,
    }
