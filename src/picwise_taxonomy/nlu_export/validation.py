from __future__ import annotations

from dataclasses import dataclass

from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.mega_category_registry import get_mega_category_registry

from .contracts import TaxonomyNLUExportRecord, TaxonomyNLUExportStatus


@dataclass(frozen=True)
class TaxonomyNLUExportCatalog:
    valid_engine_ids: frozenset[str]
    valid_mega_ids: frozenset[str]
    engine_to_mega_ids: dict[str, tuple[str, ...]]
    mega_to_engine_id: dict[str, str]


def build_taxonomy_nlu_export_catalog() -> TaxonomyNLUExportCatalog:
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
    return TaxonomyNLUExportCatalog(
        valid_engine_ids=frozenset(engine_to_mega_ids.keys()),
        valid_mega_ids=frozenset(mega_to_engine.keys()),
        engine_to_mega_ids=dict(sorted(engine_to_mega_ids.items())),
        mega_to_engine_id=dict(sorted(mega_to_engine.items())),
    )


def validate_export_record(
    record: TaxonomyNLUExportRecord,
    catalog: TaxonomyNLUExportCatalog | None = None,
) -> dict:
    active_catalog = catalog or build_taxonomy_nlu_export_catalog()
    engine_exists = record.engine_id in active_catalog.valid_engine_ids
    mega_exists = record.mega_category_id in active_catalog.valid_mega_ids
    mega_belongs_to_engine = (
        engine_exists
        and mega_exists
        and record.mega_category_id in set(active_catalog.engine_to_mega_ids.get(record.engine_id, ()))
        and active_catalog.mega_to_engine_id.get(record.mega_category_id) == record.engine_id
    )
    required_shape_ok = bool(record.export_id and record.aliases and record.spec_fields and record.intent_patterns)
    active_is_registry_valid = (
        record.status != TaxonomyNLUExportStatus.ACTIVE or (engine_exists and mega_exists and mega_belongs_to_engine)
    )
    valid = required_shape_ok and engine_exists and mega_exists and mega_belongs_to_engine and active_is_registry_valid
    reasons: list[str] = []
    if not required_shape_ok:
        reasons.append("record_shape_incomplete")
    if not engine_exists:
        reasons.append("unknown_engine_id")
    if not mega_exists:
        reasons.append("unknown_mega_category_id")
    if engine_exists and mega_exists and not mega_belongs_to_engine:
        reasons.append("mega_category_not_owned_by_engine")
    if not active_is_registry_valid:
        reasons.append("active_record_failed_registry_validation")
    return {
        "valid": valid,
        "engine_exists": engine_exists,
        "mega_exists": mega_exists,
        "mega_belongs_to_engine": mega_belongs_to_engine,
        "required_shape_ok": required_shape_ok,
        "active_is_registry_valid": active_is_registry_valid,
        "reasons": tuple(reasons),
    }


def validate_export_records(records: tuple[TaxonomyNLUExportRecord, ...]) -> dict:
    catalog = build_taxonomy_nlu_export_catalog()
    checks = [validate_export_record(record, catalog) for record in records]
    valid = all(check["valid"] for check in checks)
    reasons = sorted({reason for check in checks for reason in check["reasons"]})
    return {"valid": valid, "reasons": tuple(reasons)}

