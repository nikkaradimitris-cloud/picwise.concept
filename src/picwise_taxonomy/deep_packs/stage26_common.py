from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy

from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.mega_category_registry import get_mega_category_registry

_FORBIDDEN_KEY_TOKENS = (
    "product_inventory",
    "price",
    "sku",
    "stock",
    "checkout",
    "seller",
    "affiliate",
    "offer_url",
    "offer",
)


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw_value in values:
        value = raw_value.strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(value)
    return result


def unique_count(values: list[str]) -> int:
    return len(dedupe(values))


def expand_product_families(base: list[str], variants: list[str], contexts: list[str], minimum: int) -> list[str]:
    families = dedupe(base)
    for item in base:
        for variant in variants:
            for context in contexts:
                families.append(f"{variant} {item} {context}")
                if unique_count(families) >= minimum:
                    return dedupe(families)
    return dedupe(families)


def expand_aliases(seed_terms: list[str], departments: list[str], subcategories: list[str], minimum: int) -> list[str]:
    aliases = dedupe(seed_terms)
    for department in departments:
        aliases.extend(
            [
                department,
                f"{department} λύσεις",
                f"{department} systems",
                f"{department} επιλογές",
            ]
        )
    for subcategory in subcategories:
        aliases.extend(
            [
                subcategory,
                f"{subcategory} categories",
                f"{subcategory} guides",
                f"{subcategory} taxonomy",
            ]
        )
        if unique_count(aliases) >= minimum:
            return dedupe(aliases)
    return dedupe(aliases)


def expand_greeklish(seeds: list[str], contexts: list[str], minimum: int) -> list[str]:
    terms = dedupe(seeds)
    for seed in seeds:
        for context in contexts:
            terms.append(f"{seed} {context}")
            if unique_count(terms) >= minimum:
                return dedupe(terms)
    return dedupe(terms)


def typo_variants(base_terms: list[str], minimum: int) -> list[str]:
    replacements = (("th", "t"), ("ks", "x"), ("ou", "u"), ("ei", "i"), ("ai", "e"))
    variants: list[str] = []
    for term in base_terms:
        compact = term.replace(" ", "")
        variants.append(compact)
        for old, new in replacements:
            if old in term:
                variants.append(term.replace(old, new))
        variants.append(term.replace("o", "0"))
        variants.append(term.replace("i", "1"))
        if unique_count(variants) >= minimum:
            return dedupe(variants)
    return dedupe(variants)


def expand_intents(seeds: list[str], targets: list[str], situations: list[str], minimum: int) -> list[str]:
    intents = dedupe(seeds)
    templates = (
        "thelo {target} gia {situation}",
        "psaxno {target} me emfasi se {situation}",
        "ti na paro apo {target} gia {situation}",
        "sygkrisi {target} gia {situation}",
    )
    for target in targets:
        for situation in situations:
            for template in templates:
                intents.append(template.format(target=target, situation=situation))
                if unique_count(intents) >= minimum:
                    return dedupe(intents)
    return dedupe(intents)


def make_record(
    *,
    mega_category_id: str,
    display_name: str,
    engine_id: str,
    departments: list[str],
    subcategories: list[str],
    product_families: list[str],
    spec_fields: list[str],
    buying_priorities: list[str],
    aliases: list[str],
    greeklish: list[str],
    typos: list[str],
    intent_patterns: list[str],
    ambiguity_rules: list[str],
    source_references: list[str],
    stage_code: str,
) -> dict:
    return {
        "mega_category_id": mega_category_id,
        "engine_id": engine_id,
        "display_name": display_name,
        "departments": dedupe(departments),
        "subcategories": dedupe(subcategories),
        "product_families": dedupe(product_families),
        "spec_fields": dedupe(spec_fields),
        "buying_priorities": dedupe(buying_priorities),
        "alias_terms": dedupe(aliases),
        "aliases": dedupe(aliases),
        "greek_alias_terms": [term for term in dedupe(aliases) if any("\u0370" <= ch <= "\u03ff" for ch in term)],
        "greeklish_terms": dedupe(greeklish),
        "greeklish": dedupe(greeklish),
        "typo_terms": dedupe(typos),
        "typos": dedupe(typos),
        "intent_patterns": dedupe(intent_patterns),
        "ambiguity_rules": dedupe(ambiguity_rules),
        "source_references": dedupe(source_references),
        "safety_notes": [
            "taxonomy-only expansion; no real products, prices, sku, stock, offers, sellers, or affiliate links",
            "pack provides category/family/alias/spec/intent seeds only",
        ],
        "expansion_status": f"{stage_code}_taxonomy_deep_pack_seed_v1",
    }


def summarize_pack(pack: dict) -> dict:
    records = pack["mega_categories"]
    count_map = {
        "department_counts": "departments",
        "subcategory_counts": "subcategories",
        "product_family_counts": "product_families",
        "alias_counts": "alias_terms",
        "spec_field_counts": "spec_fields",
        "intent_pattern_counts": "intent_patterns",
    }
    summary_counts: dict[str, dict[str, int]] = {}
    for key, field in count_map.items():
        summary_counts[key] = {record["mega_category_id"]: unique_count(record[field]) for record in records}
    totals = {
        "total_departments": sum(summary_counts["department_counts"].values()),
        "total_subcategories": sum(summary_counts["subcategory_counts"].values()),
        "total_product_families": sum(summary_counts["product_family_counts"].values()),
        "total_aliases": sum(summary_counts["alias_counts"].values()),
        "total_spec_fields": sum(summary_counts["spec_field_counts"].values()),
        "total_intent_patterns": sum(summary_counts["intent_pattern_counts"].values()),
    }
    return {
        "stage_title": pack["stage_title"],
        "engine_id": pack["engine_id"],
        "mega_categories_covered": [record["mega_category_id"] for record in records],
        "mega_category_count": len(records),
        **summary_counts,
        **totals,
        "taxonomy_expansion_only": True,
        "deterministic_ordering": True,
    }


def _contains_forbidden_keys(payload: object) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = key.lower()
            if any(token in lowered for token in _FORBIDDEN_KEY_TOKENS):
                return True
            if _contains_forbidden_keys(value):
                return True
        return False
    if isinstance(payload, list):
        return any(_contains_forbidden_keys(item) for item in payload)
    return False


def _is_json_serializable(payload: object) -> bool:
    try:
        json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


def validate_pack(
    *,
    pack: dict,
    expected_stage_title: str,
    expected_engine_id: str,
    expected_mega_category_ids: list[str],
    minimum_totals: dict[str, int],
) -> dict:
    summary = summarize_pack(pack)
    engine_registry = get_engine_registry()
    mega_registry = get_mega_category_registry()
    valid_engine_ids = {entry["engine_id"] for entry in engine_registry}
    engine_to_mega_ids = {entry["engine_id"]: entry["mega_category_ids"] for entry in engine_registry}
    mega_to_engine = {entry["mega_category_id"]: entry["engine_id"] for entry in mega_registry}
    record_ids = [record["mega_category_id"] for record in pack["mega_categories"]]

    shape_checks = []
    for record in pack["mega_categories"]:
        required_fields = (
            "mega_category_id",
            "engine_id",
            "display_name",
            "departments",
            "subcategories",
            "product_families",
            "alias_terms",
            "greek_alias_terms",
            "greeklish_terms",
            "typo_terms",
            "spec_fields",
            "intent_patterns",
            "source_references",
        )
        has_fields = all(field in record for field in required_fields)
        has_lists = all(
            isinstance(record[field], list) and record[field]
            for field in (
                "departments",
                "subcategories",
                "product_families",
                "alias_terms",
                "greek_alias_terms",
                "greeklish_terms",
                "typo_terms",
                "spec_fields",
                "intent_patterns",
                "source_references",
            )
        )
        shape_checks.append(bool(has_fields and has_lists))

    validation_summary = {
        "stage_title_exact": pack["stage_title"] == expected_stage_title,
        "engine_id_exact": pack["engine_id"] == expected_engine_id,
        "engine_exists_in_registry": pack["engine_id"] in valid_engine_ids,
        "mega_category_ids_match_expected_order": record_ids == expected_mega_category_ids,
        "all_mega_categories_mapped_to_engine": all(
            mega_to_engine.get(record_id) == expected_engine_id for record_id in record_ids
        ),
        "engine_registry_owns_same_mega_categories": engine_to_mega_ids.get(expected_engine_id, []) == expected_mega_category_ids,
        "records_have_required_shape": all(shape_checks),
        "minimum_departments_total": summary["total_departments"] >= minimum_totals["departments"],
        "minimum_subcategories_total": summary["total_subcategories"] >= minimum_totals["subcategories"],
        "minimum_product_families_total": summary["total_product_families"] >= minimum_totals["product_families"],
        "minimum_aliases_total": summary["total_aliases"] >= minimum_totals["aliases"],
        "minimum_spec_fields_total": summary["total_spec_fields"] >= minimum_totals["spec_fields"],
        "minimum_intent_patterns_total": summary["total_intent_patterns"] >= minimum_totals["intent_patterns"],
        "no_forbidden_commercial_tokens": not _contains_forbidden_keys(pack),
        "is_json_serializable": _is_json_serializable({"pack": pack, "summary": summary}),
        "taxonomy_expansion_only": summary["taxonomy_expansion_only"],
        "deterministic_ordering": summary["deterministic_ordering"],
    }
    validation_summary["valid"] = all(validation_summary.values())
    validation_summary["passed"] = validation_summary["valid"]
    validation_summary["coverage_depth_snapshot"] = dict(summary)
    validation_summary["engine_mega_distribution"] = dict(Counter([record["engine_id"] for record in pack["mega_categories"]]))
    return validation_summary


def deep_copy_pack(pack: dict) -> dict:
    return deepcopy(pack)
