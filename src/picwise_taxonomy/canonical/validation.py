from __future__ import annotations

from dataclasses import dataclass

from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.mega_category_registry import get_mega_category_registry

from .contracts import CanonicalTaxonomyRecord, CanonicalTaxonomyStatus


@dataclass(frozen=True)
class CanonicalRegistryCatalog:
    engine_ids: set[str]
    mega_to_engine: dict[str, str]


def build_canonical_registry_catalog() -> CanonicalRegistryCatalog:
    engines = get_engine_registry()
    mega_categories = get_mega_category_registry()
    return CanonicalRegistryCatalog(
        engine_ids={entry["engine_id"] for entry in engines},
        mega_to_engine={entry["mega_category_id"]: entry["engine_id"] for entry in mega_categories},
    )


def validate_canonical_record(record: CanonicalTaxonomyRecord, catalog: CanonicalRegistryCatalog) -> dict:
    engine_exists = record.engine_id in catalog.engine_ids if record.engine_id else False
    mega_exists = record.mega_category_id in catalog.mega_to_engine if record.mega_category_id else False
    mega_belongs_to_engine = bool(
        engine_exists
        and mega_exists
        and catalog.mega_to_engine.get(record.mega_category_id) == record.engine_id
    )
    active_has_registry_fields = bool(record.engine_id and record.mega_category_id)
    active_is_registry_valid = (
        record.status != CanonicalTaxonomyStatus.ACTIVE
        or (active_has_registry_fields and engine_exists and mega_exists and mega_belongs_to_engine)
    )
    return {
        "valid": bool(record.status != CanonicalTaxonomyStatus.ACTIVE or active_is_registry_valid),
        "engine_exists": engine_exists,
        "mega_exists": mega_exists,
        "mega_belongs_to_engine": mega_belongs_to_engine,
        "active_has_registry_fields": active_has_registry_fields,
        "active_is_registry_valid": active_is_registry_valid,
    }


def validate_canonical_records(records: list[CanonicalTaxonomyRecord]) -> dict:
    catalog = build_canonical_registry_catalog()
    failures: list[str] = []
    for record in records:
        check = validate_canonical_record(record, catalog)
        if check["valid"]:
            continue
        failures.append(
            f"Record {record.record_id} is active but failed registry validation "
            f"(engine_exists={check['engine_exists']}, mega_exists={check['mega_exists']}, "
            f"mega_belongs_to_engine={check['mega_belongs_to_engine']})."
        )
    return {
        "valid": not failures,
        "failure_count": len(failures),
        "reasons": tuple(failures),
    }
