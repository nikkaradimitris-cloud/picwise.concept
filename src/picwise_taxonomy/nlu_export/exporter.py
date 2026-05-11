from __future__ import annotations

import re
from collections import Counter

from picwise_taxonomy.deep_packs import (
    get_auto_moto_mobility_pack,
    get_fashion_footwear_jewelry_accessories_pack,
    get_health_beauty_family_lifestyle_pack,
    get_home_living_appliances_pack,
    get_tech_electronics_office_pack,
    get_tools_diy_garden_repair_pack,
)

from .contracts import (
    TaxonomyNLUExportInput,
    TaxonomyNLUExportRecord,
    TaxonomyNLUExportResult,
    TaxonomyNLUExportStatus,
    TaxonomyNLUSignalSet,
)
from .validation import build_taxonomy_nlu_export_catalog, validate_export_record, validate_export_records

_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
_GREEK_CHAR_PATTERN = re.compile(r"[\u0370-\u03ff]")
_PACK_LOADERS = (
    get_auto_moto_mobility_pack,
    get_home_living_appliances_pack,
    get_tech_electronics_office_pack,
    get_health_beauty_family_lifestyle_pack,
    get_tools_diy_garden_repair_pack,
    get_fashion_footwear_jewelry_accessories_pack,
)


def _normalize_text(value: object) -> str:
    lowered = str(value or "").strip().lower()
    return _NORMALIZE_PATTERN.sub("_", lowered).strip("_")


def _stable_unique(values: object) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    cleaned = {
        str(raw_value).strip()
        for raw_value in values
        if isinstance(raw_value, str) and str(raw_value).strip()
    }
    return tuple(sorted(cleaned, key=lambda item: item.lower()))


def _extract_greek_aliases(aliases: tuple[str, ...], payload: dict) -> tuple[str, ...]:
    direct = _stable_unique(payload.get("greek_alias_terms", []))
    if direct:
        return direct
    return tuple(alias for alias in aliases if _GREEK_CHAR_PATTERN.search(alias))


def _build_signal_set(payload: dict) -> TaxonomyNLUSignalSet:
    aliases = _stable_unique(payload.get("alias_terms", payload.get("aliases", [])))
    greeklish_aliases = _stable_unique(payload.get("greeklish_terms", payload.get("greeklish", [])))
    typo_variants = _stable_unique(payload.get("typo_terms", payload.get("typos", [])))
    spec_fields = _stable_unique(payload.get("spec_fields", []))
    intent_patterns = _stable_unique(payload.get("intent_patterns", []))
    priority_terms = _stable_unique(payload.get("buying_priorities", []))
    return TaxonomyNLUSignalSet(
        aliases=aliases,
        greek_aliases=_extract_greek_aliases(aliases, payload),
        greeklish_aliases=greeklish_aliases,
        typo_variants=typo_variants,
        spec_fields=spec_fields,
        intent_patterns=intent_patterns,
        priority_terms=priority_terms,
    )


def _record_status(
    provisional_record: TaxonomyNLUExportRecord,
    signal_set: TaxonomyNLUSignalSet,
) -> tuple[TaxonomyNLUExportStatus, tuple[str, ...]]:
    warnings: list[str] = []
    validation = validate_export_record(provisional_record)
    if not validation["engine_exists"] or not validation["mega_exists"] or not validation["mega_belongs_to_engine"]:
        warnings.extend(validation["reasons"])
        return TaxonomyNLUExportStatus.DISABLED_GAP, tuple(sorted(set(warnings)))
    if not (
        signal_set.aliases
        and signal_set.greeklish_aliases
        and signal_set.typo_variants
        and signal_set.spec_fields
        and signal_set.intent_patterns
        and signal_set.priority_terms
    ):
        warnings.append("weak_signal_set_requires_review")
        return TaxonomyNLUExportStatus.REVIEW_ONLY, tuple(sorted(set(warnings)))
    return TaxonomyNLUExportStatus.ACTIVE, tuple(sorted(set(warnings)))


def _export_id(
    *,
    status: TaxonomyNLUExportStatus,
    engine_id: str,
    mega_category_id: str,
    department: str,
    subcategory: str,
    product_family: str,
) -> str:
    parts = (
        status.value,
        _normalize_text(engine_id),
        _normalize_text(mega_category_id),
        _normalize_text(department),
        _normalize_text(subcategory),
        _normalize_text(product_family),
    )
    return "__".join(part or "na" for part in parts)


def _source_refs(input_ref: str, pack: dict, record: dict) -> tuple[str, ...]:
    refs = set(_stable_unique(record.get("source_references", [])))
    if isinstance(pack.get("source"), str) and pack.get("source", "").strip():
        refs.add(f"deep_pack_source:{pack['source']}")
    if isinstance(pack.get("stage_title"), str) and pack.get("stage_title", "").strip():
        refs.add(pack["stage_title"])
    if isinstance(record.get("expansion_status"), str) and record.get("expansion_status", "").strip():
        refs.add(f"deep_pack_expansion:{record['expansion_status']}")
    refs.add("Stage 25A — Canonical Taxonomy Registry Builder")
    refs.add("Stage 27A — Taxonomy → Local NLU Export")
    refs.add(input_ref)
    return tuple(sorted(refs, key=lambda item: item.lower()))


def _record_from_deep_pack(input_ref: str, pack: dict, payload: dict) -> TaxonomyNLUExportRecord:
    signal_set = _build_signal_set(payload)
    engine_id = str(payload.get("engine_id", "")).strip()
    mega_category_id = str(payload.get("mega_category_id", "")).strip()
    department = next(iter(_stable_unique(payload.get("departments", []))), "")
    subcategory = next(iter(_stable_unique(payload.get("subcategories", []))), "")
    product_family = next(iter(_stable_unique(payload.get("product_families", []))), "")
    provisional = TaxonomyNLUExportRecord(
        export_id="",
        status=TaxonomyNLUExportStatus.REVIEW_ONLY,
        engine_id=engine_id,
        mega_category_id=mega_category_id,
        department=department,
        subcategory=subcategory,
        product_family=product_family,
        aliases=signal_set.aliases,
        greek_aliases=signal_set.greek_aliases,
        greeklish_aliases=signal_set.greeklish_aliases,
        typo_variants=signal_set.typo_variants,
        spec_fields=signal_set.spec_fields,
        intent_patterns=signal_set.intent_patterns,
        priority_terms=signal_set.priority_terms,
        source_stage_refs=_source_refs(input_ref, pack, payload),
        signals=signal_set,
    )
    status, warnings = _record_status(provisional, signal_set)
    return TaxonomyNLUExportRecord(
        export_id=_export_id(
            status=status,
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
        aliases=signal_set.aliases,
        greek_aliases=signal_set.greek_aliases,
        greeklish_aliases=signal_set.greeklish_aliases,
        typo_variants=signal_set.typo_variants,
        spec_fields=signal_set.spec_fields,
        intent_patterns=signal_set.intent_patterns,
        priority_terms=signal_set.priority_terms,
        source_stage_refs=provisional.source_stage_refs,
        validation_warnings=warnings,
        signals=signal_set,
    )


def get_default_source_packs() -> tuple[dict, ...]:
    return tuple(loader() for loader in _PACK_LOADERS)


def build_taxonomy_nlu_export(
    export_input: TaxonomyNLUExportInput | None = None,
) -> TaxonomyNLUExportResult:
    active_input = export_input or TaxonomyNLUExportInput(source_packs=get_default_source_packs())
    source_packs = tuple(active_input.source_packs or get_default_source_packs())
    catalog = build_taxonomy_nlu_export_catalog()
    records = [
        _record_from_deep_pack(active_input.stage_ref, pack, item)
        for pack in source_packs
        for item in sorted(
            pack.get("mega_categories", []),
            key=lambda payload: (
                str(payload.get("engine_id", "")).strip(),
                str(payload.get("mega_category_id", "")).strip(),
            ),
        )
    ]
    scoped_records = [
        item
        for item in records
        if (active_input.include_review_items or item.status != TaxonomyNLUExportStatus.REVIEW_ONLY)
        and (active_input.include_disabled_gap_items or item.status != TaxonomyNLUExportStatus.DISABLED_GAP)
    ]
    ordered_records = tuple(
        sorted(
            scoped_records,
            key=lambda item: (item.status.value, item.engine_id, item.mega_category_id, item.export_id),
        )
    )
    status_counts = Counter(record.status.value for record in ordered_records)
    engine_counts = Counter(record.engine_id for record in ordered_records if record.engine_id in catalog.valid_engine_ids)
    mega_counts = Counter(
        record.mega_category_id for record in ordered_records if record.mega_category_id in catalog.valid_mega_ids
    )
    validation = validate_export_records(ordered_records)
    warnings = list(validation["reasons"])
    if status_counts.get(TaxonomyNLUExportStatus.REVIEW_ONLY.value, 0):
        warnings.append("Review-only records are present and intentionally not active.")
    if status_counts.get(TaxonomyNLUExportStatus.DISABLED_GAP.value, 0):
        warnings.append("Disabled gap records are present and excluded from active routing.")
    return TaxonomyNLUExportResult(
        records=ordered_records,
        total_records=len(ordered_records),
        active_records=status_counts.get(TaxonomyNLUExportStatus.ACTIVE.value, 0),
        review_only_records=status_counts.get(TaxonomyNLUExportStatus.REVIEW_ONLY.value, 0),
        disabled_gap_records=status_counts.get(TaxonomyNLUExportStatus.DISABLED_GAP.value, 0),
        counts_by_engine=dict(sorted(engine_counts.items())),
        counts_by_mega_category=dict(sorted(mega_counts.items())),
        total_aliases=sum(len(record.aliases) for record in ordered_records),
        total_greek_aliases=sum(len(record.greek_aliases) for record in ordered_records),
        total_greeklish_aliases=sum(len(record.greeklish_aliases) for record in ordered_records),
        total_typo_variants=sum(len(record.typo_variants) for record in ordered_records),
        total_spec_fields=sum(len(record.spec_fields) for record in ordered_records),
        total_intent_patterns=sum(len(record.intent_patterns) for record in ordered_records),
        total_priority_terms=sum(len(record.priority_terms) for record in ordered_records),
        valid=validation["valid"],
        warnings=tuple(sorted(set(warnings))),
        stage_title=active_input.stage_title,
    )

