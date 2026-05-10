from __future__ import annotations

import json
from collections import Counter

from .engine_registry import get_engine_registry
from .mega_category_registry import get_mega_category_registry

_FORBIDDEN_KEY_TOKENS = ("product", "offer", "price", "affiliate")
_FASHION_ENGINE_ID = "fashion_footwear_jewelry_accessories_engine"


def get_search_engines() -> list[dict]:
    """Public accessor for the deterministic search-engine registry."""
    return get_engine_registry()


def get_mega_categories() -> list[dict]:
    """Public accessor for the deterministic mega-category registry."""
    return get_mega_category_registry()


def _contains_forbidden_field(data: list[dict]) -> bool:
    for entry in data:
        for key in entry.keys():
            key_lower = key.lower()
            if any(token in key_lower for token in _FORBIDDEN_KEY_TOKENS):
                return True
    return False


def _is_json_serializable(payload: dict) -> bool:
    try:
        json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


def validate_engine_registry() -> dict:
    engines = get_search_engines()
    engine_ids = [engine["engine_id"] for engine in engines]
    per_engine_mega_counts = {
        engine["engine_id"]: len(engine.get("mega_category_ids", [])) for engine in engines
    }

    result = {
        "valid": True,
        "engine_count": len(engines),
        "expected_engine_count": 6,
        "unique_engine_ids": len(set(engine_ids)) == len(engine_ids),
        "engine_has_three_mega_categories_each": all(
            count == 3 for count in per_engine_mega_counts.values()
        ),
        "fashion_engine_exists": _FASHION_ENGINE_ID in engine_ids,
        "forbidden_fields_present": _contains_forbidden_field(engines),
        "per_engine_mega_category_counts": per_engine_mega_counts,
        "is_json_serializable": _is_json_serializable({"engines": engines}),
    }
    result["valid"] = (
        result["engine_count"] == result["expected_engine_count"]
        and result["unique_engine_ids"]
        and result["engine_has_three_mega_categories_each"]
        and result["fashion_engine_exists"]
        and not result["forbidden_fields_present"]
        and result["is_json_serializable"]
    )
    return result


def validate_mega_category_registry() -> dict:
    engines = get_search_engines()
    mega_categories = get_mega_categories()
    valid_engine_ids = {engine["engine_id"] for engine in engines}
    mega_category_ids = [entry["mega_category_id"] for entry in mega_categories]
    per_engine_counts = Counter(entry["engine_id"] for entry in mega_categories)
    fashion_count = per_engine_counts.get(_FASHION_ENGINE_ID, 0)

    result = {
        "valid": True,
        "mega_category_count": len(mega_categories),
        "expected_mega_category_count": 18,
        "unique_mega_category_ids": len(set(mega_category_ids)) == len(mega_category_ids),
        "all_engine_references_valid": all(
            entry["engine_id"] in valid_engine_ids for entry in mega_categories
        ),
        "every_engine_has_three_mega_categories": all(
            per_engine_counts.get(engine_id, 0) == 3 for engine_id in sorted(valid_engine_ids)
        ),
        "fashion_engine_has_three_mega_categories": fashion_count == 3,
        "forbidden_fields_present": _contains_forbidden_field(mega_categories),
        "is_json_serializable": _is_json_serializable({"mega_categories": mega_categories}),
        "per_engine_mega_category_counts": dict(sorted(per_engine_counts.items())),
    }
    result["valid"] = (
        result["mega_category_count"] == result["expected_mega_category_count"]
        and result["unique_mega_category_ids"]
        and result["all_engine_references_valid"]
        and result["every_engine_has_three_mega_categories"]
        and result["fashion_engine_has_three_mega_categories"]
        and not result["forbidden_fields_present"]
        and result["is_json_serializable"]
    )
    return result


def validate_taxonomy_lock() -> dict:
    engine_validation = validate_engine_registry()
    mega_category_validation = validate_mega_category_registry()
    engines = get_search_engines()
    mega_categories = get_mega_categories()

    result = {
        "valid": engine_validation["valid"] and mega_category_validation["valid"],
        "engine_validation": engine_validation,
        "mega_category_validation": mega_category_validation,
        "engine_count": len(engines),
        "mega_category_count": len(mega_categories),
        "deterministic_ordering": True,
        "is_json_serializable": _is_json_serializable(
            {
                "engines": engines,
                "mega_categories": mega_categories,
                "validation": {
                    "engine_validation": engine_validation,
                    "mega_category_validation": mega_category_validation,
                },
            }
        ),
    }
    result["valid"] = result["valid"] and result["is_json_serializable"]
    return result
