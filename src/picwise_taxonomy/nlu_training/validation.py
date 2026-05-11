from __future__ import annotations

from dataclasses import dataclass

from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.mega_category_registry import get_mega_category_registry

from .contracts import NLUTrainingExample, NLUTrainingPackBuildResult

_ALLOWED_SAFETY_STATUSES = frozenset({"safe_training_example", "review_only", "disabled_gap"})


@dataclass(frozen=True)
class NLUTrainingCatalog:
    valid_engine_ids: frozenset[str]
    valid_mega_ids: frozenset[str]
    engine_to_mega_ids: dict[str, tuple[str, ...]]
    mega_to_engine_id: dict[str, str]


def build_training_catalog() -> NLUTrainingCatalog:
    engines = get_engine_registry()
    mega_categories = get_mega_category_registry()
    engine_to_mega_ids = {
        str(engine.get("engine_id", "")).strip(): tuple(str(item).strip() for item in engine.get("mega_category_ids", []))
        for engine in engines
        if str(engine.get("engine_id", "")).strip()
    }
    mega_to_engine = {
        str(entry.get("mega_category_id", "")).strip(): str(entry.get("engine_id", "")).strip()
        for entry in mega_categories
        if str(entry.get("mega_category_id", "")).strip()
    }
    return NLUTrainingCatalog(
        valid_engine_ids=frozenset(engine_to_mega_ids.keys()),
        valid_mega_ids=frozenset(mega_to_engine.keys()),
        engine_to_mega_ids=dict(sorted(engine_to_mega_ids.items())),
        mega_to_engine_id=dict(sorted(mega_to_engine.items())),
    )


def validate_training_example(example: NLUTrainingExample, catalog: NLUTrainingCatalog | None = None) -> dict:
    active_catalog = catalog or build_training_catalog()
    engine_exists = example.expected_engine_id in active_catalog.valid_engine_ids
    mega_exists = example.expected_mega_category_id in active_catalog.valid_mega_ids
    mega_belongs_to_engine = (
        engine_exists
        and mega_exists
        and example.expected_mega_category_id in set(active_catalog.engine_to_mega_ids.get(example.expected_engine_id, ()))
        and active_catalog.mega_to_engine_id.get(example.expected_mega_category_id) == example.expected_engine_id
    )
    required_shape_ok = bool(example.example_id and example.query_text and example.normalized_query and example.source_taxonomy_refs)
    safety_status_ok = example.safety_status in _ALLOWED_SAFETY_STATUSES
    valid = required_shape_ok and engine_exists and mega_exists and mega_belongs_to_engine and safety_status_ok
    reasons: list[str] = []
    if not required_shape_ok:
        reasons.append("example_shape_incomplete")
    if not engine_exists:
        reasons.append("unknown_engine_id")
    if not mega_exists:
        reasons.append("unknown_mega_category_id")
    if engine_exists and mega_exists and not mega_belongs_to_engine:
        reasons.append("mega_category_not_owned_by_engine")
    if not safety_status_ok:
        reasons.append("invalid_safety_status")
    return {
        "valid": valid,
        "engine_exists": engine_exists,
        "mega_exists": mega_exists,
        "mega_belongs_to_engine": mega_belongs_to_engine,
        "required_shape_ok": required_shape_ok,
        "safety_status_ok": safety_status_ok,
        "reasons": tuple(reasons),
    }


def validate_training_pack_result(result: NLUTrainingPackBuildResult) -> dict:
    catalog = build_training_catalog()
    checks = [
        validate_training_example(example, catalog)
        for pack in result.packs
        for example in pack.examples
    ]
    examples_valid = all(check["valid"] for check in checks)
    summary_total_matches = result.total_examples == sum(result.examples_by_mega_category.values())
    all_megas_present = len(result.examples_by_mega_category.keys()) == len(catalog.valid_mega_ids)
    reasons = sorted({reason for check in checks for reason in check["reasons"]})
    if not summary_total_matches:
        reasons.append("summary_total_examples_mismatch")
    if not all_megas_present:
        reasons.append("missing_mega_category_pack")
    valid = examples_valid and summary_total_matches and all_megas_present
    return {"valid": valid, "reasons": tuple(sorted(set(reasons)))}
