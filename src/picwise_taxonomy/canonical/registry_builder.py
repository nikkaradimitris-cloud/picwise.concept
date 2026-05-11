from __future__ import annotations

import re
from collections import Counter

from .contracts import (
    CanonicalSourceReference,
    CanonicalTaxonomyBuildInput,
    CanonicalTaxonomyBuildResult,
    CanonicalTaxonomyRecord,
    CanonicalTaxonomyStatus,
)
from .validation import build_canonical_registry_catalog, validate_canonical_record, validate_canonical_records

_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
_ACTIVE_CONFIDENCE = {"exact", "strong_alias", "path_match"}
_BLOCKED_GAP_REASONS = {
    "invalid_source_item",
    "forbidden_inventory_field",
    "no_engine_match",
    "no_mega_category_match",
    "unsupported_google_path",
}


def _normalize_text(value: object) -> str:
    lowered = str(value or "").strip().lower()
    return _NORMALIZE_PATTERN.sub("_", lowered).strip("_")


def _normalize_list(values: object) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    cleaned = sorted({_normalize_text(value) for value in values if _normalize_text(value)})
    return tuple(cleaned)


def _build_source_reference(source_item: dict, mapping_payload: dict) -> CanonicalSourceReference:
    return CanonicalSourceReference(
        source_item_id=str(mapping_payload.get("source_item_id", "")).strip(),
        source_name=str(source_item.get("source_name", "")).strip(),
        source_type=str(source_item.get("source_type", "")).strip(),
        mapping_status=str(mapping_payload.get("status", "")).strip(),
        mapping_confidence=str(mapping_payload.get("confidence", "")).strip(),
        mapping_gap_reason=str(mapping_payload.get("gap_reason", "")).strip(),
    )


def _record_id(
    *,
    status: CanonicalTaxonomyStatus,
    source_item_id: str,
    engine_id: str,
    mega_category_id: str,
    department: str,
    subcategory: str,
    product_family: str,
) -> str:
    parts = [
        status.value,
        _normalize_text(source_item_id),
        _normalize_text(engine_id),
        _normalize_text(mega_category_id),
        _normalize_text(department),
        _normalize_text(subcategory),
        _normalize_text(product_family),
    ]
    return "__".join(part or "na" for part in parts)


def _status_for_mapping(mapping_payload: dict, *, target_valid: bool) -> CanonicalTaxonomyStatus:
    mapping_status = str(mapping_payload.get("status", "")).strip()
    mapping_confidence = str(mapping_payload.get("confidence", "")).strip()
    gap_reason = str(mapping_payload.get("gap_reason", "")).strip()
    if mapping_status == "mapped" and mapping_confidence in _ACTIVE_CONFIDENCE and target_valid:
        return CanonicalTaxonomyStatus.ACTIVE
    if gap_reason in _BLOCKED_GAP_REASONS or mapping_status in {"unmapped", "invalid_source"}:
        return CanonicalTaxonomyStatus.BLOCKED_GAP
    return CanonicalTaxonomyStatus.REVIEW_ONLY


def _extract_aliases(source_item: dict) -> tuple[str, ...]:
    aliases = []
    aliases.extend(source_item.get("proposed_aliases", []) if isinstance(source_item, dict) else [])
    metadata = source_item.get("raw_metadata", {}) if isinstance(source_item, dict) else {}
    if isinstance(metadata, dict):
        metadata_aliases = metadata.get("aliases", [])
        if isinstance(metadata_aliases, list):
            aliases.extend(metadata_aliases)
    return _normalize_list(aliases)


def _extract_spec_fields(source_item: dict) -> tuple[str, ...]:
    fields = []
    fields.extend(source_item.get("proposed_spec_fields", []) if isinstance(source_item, dict) else [])
    metadata = source_item.get("raw_metadata", {}) if isinstance(source_item, dict) else {}
    if isinstance(metadata, dict):
        metadata_specs = metadata.get("spec_fields", [])
        if isinstance(metadata_specs, list):
            fields.extend(metadata_specs)
    return _normalize_list(fields)


def _extract_intent_patterns(source_item: dict) -> tuple[str, ...]:
    patterns = []
    patterns.extend(source_item.get("proposed_intent_patterns", []) if isinstance(source_item, dict) else [])
    metadata = source_item.get("raw_metadata", {}) if isinstance(source_item, dict) else {}
    if isinstance(metadata, dict):
        metadata_patterns = metadata.get("intent_patterns", [])
        if isinstance(metadata_patterns, list):
            patterns.extend(metadata_patterns)
    return _normalize_list(patterns)


def _build_record(source_item: dict, mapping_payload: dict, catalog) -> CanonicalTaxonomyRecord:
    target = mapping_payload.get("target") or {}
    engine_id = str(target.get("engine_id", "")).strip()
    mega_category_id = str(target.get("mega_category_id", "")).strip()
    department = str(target.get("department", "")).strip()
    subcategory = str(target.get("subcategory", "")).strip()
    product_family = str(target.get("product_family", "")).strip()

    provisional = CanonicalTaxonomyRecord(
        record_id="",
        status=CanonicalTaxonomyStatus.REVIEW_ONLY,
        engine_id=engine_id,
        mega_category_id=mega_category_id,
        department=department,
        subcategory=subcategory,
        product_family=product_family,
        aliases=_extract_aliases(source_item),
        spec_fields=_extract_spec_fields(source_item),
        intent_patterns=_extract_intent_patterns(source_item),
        source_references=(_build_source_reference(source_item, mapping_payload),),
        provenance=tuple(
            sorted(
                {
                    "stage24c_imported_source_item",
                    "stage24d_validated_mapping",
                    "stage25a_canonical_registry_builder",
                }
            )
        ),
    )

    target_check = validate_canonical_record(provisional, catalog)
    status = _status_for_mapping(mapping_payload, target_valid=target_check["active_is_registry_valid"])

    source_item_id = str(mapping_payload.get("source_item_id", "")).strip()
    return CanonicalTaxonomyRecord(
        record_id=_record_id(
            status=status,
            source_item_id=source_item_id,
            engine_id=engine_id,
            mega_category_id=mega_category_id,
            department=department,
            subcategory=subcategory,
            product_family=product_family,
        ),
        status=status,
        engine_id=engine_id,
        mega_category_id=mega_category_id,
        department=department,
        subcategory=subcategory,
        product_family=product_family,
        aliases=provisional.aliases,
        spec_fields=provisional.spec_fields,
        intent_patterns=provisional.intent_patterns,
        source_references=provisional.source_references,
        provenance=provisional.provenance,
    )


def build_canonical_taxonomy_registry(build_input: CanonicalTaxonomyBuildInput) -> CanonicalTaxonomyBuildResult:
    source_items = list(build_input.source_items or ())
    mapped_results = list(build_input.mapped_results or ())
    gap_records = list(build_input.gap_records or ())
    source_items_by_id = {
        str(item.get("source_item_id", "")).strip(): item for item in source_items if str(item.get("source_item_id", "")).strip()
    }
    catalog = build_canonical_registry_catalog()

    records = [
        _build_record(source_items_by_id.get(str(mapping_payload.get("source_item_id", "")).strip(), {}), mapping_payload, catalog)
        for mapping_payload in sorted(
            mapped_results,
            key=lambda payload: (
                str(payload.get("source_item_id", "")).strip(),
                str(payload.get("status", "")).strip(),
                str(payload.get("confidence", "")).strip(),
            ),
        )
    ]
    ordered_records = sorted(records, key=lambda item: (item.status.value, item.record_id))

    status_counts = Counter(record.status.value for record in ordered_records)
    engine_counts = Counter(record.engine_id for record in ordered_records if record.engine_id)
    mega_counts = Counter(record.mega_category_id for record in ordered_records if record.mega_category_id)
    validation = validate_canonical_records(ordered_records)

    warnings: list[str] = []
    if any(record.status == CanonicalTaxonomyStatus.BLOCKED_GAP for record in ordered_records):
        warnings.append("Blocked gap records present; operator review is required before activation.")
    if any(record.status == CanonicalTaxonomyStatus.REVIEW_ONLY for record in ordered_records):
        warnings.append("Review-only records present; no full taxonomy coverage is claimed.")

    return CanonicalTaxonomyBuildResult(
        records=tuple(ordered_records),
        total_records=len(ordered_records),
        active_records=status_counts.get(CanonicalTaxonomyStatus.ACTIVE.value, 0),
        review_only_records=status_counts.get(CanonicalTaxonomyStatus.REVIEW_ONLY.value, 0),
        blocked_gap_records=status_counts.get(CanonicalTaxonomyStatus.BLOCKED_GAP.value, 0),
        counts_by_engine=dict(sorted(engine_counts.items())),
        counts_by_mega_category=dict(sorted(mega_counts.items())),
        source_count=len(source_items_by_id),
        gap_count=len(gap_records),
        valid=validation["valid"],
        reasons=tuple(validation["reasons"]),
        warnings=tuple(warnings),
    )
