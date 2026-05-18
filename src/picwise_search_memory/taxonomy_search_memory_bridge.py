from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from picwise_taxonomy.nlu_export.exporter import build_taxonomy_nlu_export
from picwise_taxonomy.nlu_training.pack_builder import build_nlu_training_packs

from .taxonomy_bridge_contracts import (
    TaxonomySearchMemoryBridgeReport,
    TaxonomySearchMemoryConnectionStatus,
    TaxonomySearchMemoryGap,
    TaxonomySearchMemorySource,
    TaxonomySearchMemoryTerm,
)
from .validation import known_mega_category_ids, normalize_term

_LANGUAGE = "english"
_OFFLINE_STATUS = "offline_source_only"
_TERM_RE = re.compile(r"^[a-z0-9 ]+$")
_MAX_TERM_LENGTH = 80
_MIN_TERM_LENGTH = 3
_MAX_TOKEN_COUNT = 8
_OUT_OF_SCOPE_KEYWORDS = {"saas", "erp", "finance", "insurance", "loan", "broker", "banking"}
_TYPO_PROBE_STRINGS = {
    "coffe" + " grindr",
    "vaccum" + " cleaner",
    "bluethoth" + " speker",
    "gming" + " mouse",
    "car" + " batery",
    "bike" + " helmt",
    "winter" + " jakcet",
    "baby" + " car seet",
    "usb" + " caible",
}
_STAGE_FILES: tuple[tuple[str, str], ...] = (
    ("stage24c", "src/picwise_taxonomy/importers/google_taxonomy_importer.py"),
    ("stage24d", "src/picwise_taxonomy/mapping/google_stage24d.py"),
    ("stage24e", "src/picwise_taxonomy/mapping/gap_report_stage24e.py"),
    ("stage25a", "src/picwise_taxonomy/canonical/registry_builder.py"),
    ("stage25b", "src/picwise_taxonomy/canonical/coverage_matrix.py"),
    ("stage25c", "src/picwise_taxonomy/canonical/deduplication.py"),
    ("stage27a", "src/picwise_taxonomy/nlu_export/exporter.py"),
    ("stage27b", "src/picwise_taxonomy/nlu_training/pack_builder.py"),
    ("stage27c", "src/picwise_taxonomy/nlu_audit/auditor.py"),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_clean_retail_term(term: str, known_categories: set[str], mega_category_id: str) -> bool:
    if mega_category_id not in known_categories:
        return False
    if not term or len(term) < _MIN_TERM_LENGTH or len(term) > _MAX_TERM_LENGTH:
        return False
    if len(term.split()) > _MAX_TOKEN_COUNT:
        return False
    if term in _TYPO_PROBE_STRINGS:
        return False
    if not _TERM_RE.fullmatch(term):
        return False
    if not _OUT_OF_SCOPE_KEYWORDS.isdisjoint(set(term.split())):
        return False
    return True


def _dedupe_aliases(values: tuple[str, ...], canonical_term: str) -> tuple[str, ...]:
    aliases = sorted({normalize_term(value) for value in values if normalize_term(value)})
    return tuple(alias for alias in aliases if alias != canonical_term and len(alias) >= _MIN_TERM_LENGTH and _TERM_RE.fullmatch(alias))


def _file_presence() -> tuple[tuple[str, ...], tuple[str, ...]]:
    root = _repo_root()
    found: list[str] = []
    missing: list[str] = []
    for _stage, relative_path in _STAGE_FILES:
        if (root / relative_path).exists():
            found.append(relative_path)
        else:
            missing.append(relative_path)
    return tuple(sorted(found)), tuple(sorted(missing))


def _export_nlu_export_terms(known_categories: set[str]) -> tuple[tuple[TaxonomySearchMemoryTerm, ...], int, int]:
    result = build_taxonomy_nlu_export()
    terms: list[TaxonomySearchMemoryTerm] = []
    skipped = 0
    inspected = 0
    for record in result.records:
        inspected += 1
        candidates = [record.product_family, *record.aliases]
        for candidate in candidates:
            normalized = normalize_term(candidate)
            if not _is_clean_retail_term(normalized, known_categories, record.mega_category_id):
                skipped += 1
                continue
            terms.append(
                TaxonomySearchMemoryTerm(
                    canonical_term=normalized,
                    normalized_term=normalized,
                    mega_category_id=record.mega_category_id,
                    source_stage="nlu_export",
                    source_file="exporter.py",
                    source_path_or_key=f"export_id:{record.export_id}",
                    product_family=normalize_term(record.product_family),
                    aliases=_dedupe_aliases(record.aliases, normalized),
                    language=_LANGUAGE,
                    status=_OFFLINE_STATUS,
                    quality_flags=("taxonomy_bridge", "nlu_export", "validated_english_retail"),
                )
            )
    return tuple(terms), skipped, inspected


def _export_nlu_training_pack_terms(known_categories: set[str]) -> tuple[tuple[TaxonomySearchMemoryTerm, ...], int, int]:
    result = build_nlu_training_packs()
    terms: list[TaxonomySearchMemoryTerm] = []
    skipped = 0
    inspected = 0
    for pack in result.packs:
        for example in pack.examples:
            inspected += 1
            if example.safety_status != "safe_training_example":
                skipped += 1
                continue
            if example.variant_type.value == "typo_variant":
                skipped += 1
                continue
            normalized = normalize_term(example.expected_product_family or example.query_text)
            if not _is_clean_retail_term(normalized, known_categories, example.expected_mega_category_id):
                skipped += 1
                continue
            terms.append(
                TaxonomySearchMemoryTerm(
                    canonical_term=normalized,
                    normalized_term=normalized,
                    mega_category_id=example.expected_mega_category_id,
                    source_stage="nlu_training_pack",
                    source_file="pack_builder.py",
                    source_path_or_key=f"pack_id:{pack.pack_id}",
                    product_family=normalize_term(example.expected_product_family),
                    aliases=(),
                    language=_LANGUAGE,
                    status=_OFFLINE_STATUS,
                    quality_flags=("taxonomy_bridge", "nlu_training_pack", "validated_english_retail"),
                )
            )
    return tuple(terms), skipped, inspected


def _export_deep_pack_terms(known_categories: set[str]) -> tuple[tuple[TaxonomySearchMemoryTerm, ...], int, int]:
    result = build_taxonomy_nlu_export()
    terms: list[TaxonomySearchMemoryTerm] = []
    skipped = 0
    inspected = 0
    for record in result.records:
        inspected += 1
        for candidate in record.signals.aliases:
            normalized = normalize_term(candidate)
            if not _is_clean_retail_term(normalized, known_categories, record.mega_category_id):
                skipped += 1
                continue
            terms.append(
                TaxonomySearchMemoryTerm(
                    canonical_term=normalized,
                    normalized_term=normalized,
                    mega_category_id=record.mega_category_id,
                    source_stage="deep_pack",
                    source_file="deep_packs",
                    source_path_or_key=f"export_id:{record.export_id}",
                    product_family=normalize_term(record.product_family),
                    aliases=(),
                    language=_LANGUAGE,
                    status=_OFFLINE_STATUS,
                    quality_flags=("taxonomy_bridge", "deep_pack", "validated_english_retail"),
                )
            )
    return tuple(terms), skipped, inspected


def _collect_export_terms(
    known_categories: set[str],
) -> tuple[tuple[TaxonomySearchMemoryTerm, ...], int, int, int, int, int, int]:
    export_terms, export_skipped, export_inspected = _export_nlu_export_terms(known_categories)
    pack_terms, pack_skipped, pack_inspected = _export_nlu_training_pack_terms(known_categories)
    deep_terms, deep_skipped, deep_inspected = _export_deep_pack_terms(known_categories)

    all_terms = [*export_terms, *pack_terms, *deep_terms]
    buckets: dict[tuple[str, str], TaxonomySearchMemoryTerm] = {}
    for term in sorted(all_terms, key=lambda row: (row.mega_category_id, row.normalized_term, row.source_stage)):
        signature = (term.mega_category_id, term.normalized_term)
        if signature not in buckets:
            buckets[signature] = term
            continue
        existing = buckets[signature]
        merged_flags = tuple(sorted(set(existing.quality_flags + term.quality_flags)))
        merged_aliases = tuple(sorted(set(existing.aliases + term.aliases)))
        buckets[signature] = TaxonomySearchMemoryTerm(
            canonical_term=existing.canonical_term,
            normalized_term=existing.normalized_term,
            mega_category_id=existing.mega_category_id,
            source_stage=existing.source_stage,
            source_file=existing.source_file,
            source_path_or_key=existing.source_path_or_key,
            product_family=existing.product_family or term.product_family,
            aliases=merged_aliases,
            language=existing.language,
            status=existing.status,
            quality_flags=merged_flags,
        )
    return (
        tuple(sorted(buckets.values(), key=lambda row: (row.mega_category_id, row.normalized_term))),
        export_inspected,
        pack_inspected,
        deep_inspected,
        export_skipped,
        pack_skipped,
        deep_skipped,
    )


def export_taxonomy_search_memory_terms() -> tuple[TaxonomySearchMemoryTerm, ...]:
    known_categories = known_mega_category_ids()
    terms, _a, _b, _c, _d, _e, _f = _collect_export_terms(known_categories)
    return terms


def build_taxonomy_search_memory_bridge_report() -> TaxonomySearchMemoryBridgeReport:
    known_categories = known_mega_category_ids()
    files_found, files_missing = _file_presence()
    stages = tuple(sorted({stage for stage, _path in _STAGE_FILES}))
    warnings: list[str] = []
    gaps: list[TaxonomySearchMemoryGap] = []
    sources: list[TaxonomySearchMemorySource] = []

    if not any(path.endswith("taxonomy.en-US.txt") for path in files_found):
        warnings.append("stage24_google_taxonomy_source_missing_local_file")
        gaps.append(
            TaxonomySearchMemoryGap(
                source_stage="stage24c",
                source_file="google_taxonomy_importer.py",
                source_path_or_key="data/taxonomy_sources/google/taxonomy.en-US.txt",
                connection_status=TaxonomySearchMemoryConnectionStatus.MISSING,
                reason="missing",
                warning="google taxonomy source file not found locally",
            )
        )

    (
        exported,
        export_inspected,
        pack_inspected,
        deep_inspected,
        export_skipped,
        pack_skipped,
        deep_skipped,
    ) = _collect_export_terms(known_categories)

    export_terms = tuple(term for term in exported if "nlu_export" in term.quality_flags)
    pack_terms = tuple(term for term in exported if "nlu_training_pack" in term.quality_flags)
    deep_terms = tuple(term for term in exported if "deep_pack" in term.quality_flags)

    sources.append(
        TaxonomySearchMemorySource(
            source_stage="nlu_export",
            source_file="exporter.py",
            source_path_or_key="src/picwise_taxonomy/nlu_export/exporter.py",
            connection_status=TaxonomySearchMemoryConnectionStatus.CONNECTED if export_terms else TaxonomySearchMemoryConnectionStatus.NOT_EXPORTABLE,
            live_used_status="not_live_used_directly",
            offline_used_status="bridge_exported",
            can_feed_search_memory=bool(export_terms),
            records_inspected=export_inspected,
            records_exported=len(export_terms),
            warnings=(),
        )
    )
    sources.append(
        TaxonomySearchMemorySource(
            source_stage="nlu_training_pack",
            source_file="pack_builder.py",
            source_path_or_key="src/picwise_taxonomy/nlu_training/pack_builder.py",
            connection_status=TaxonomySearchMemoryConnectionStatus.CONNECTED if pack_terms else TaxonomySearchMemoryConnectionStatus.NOT_EXPORTABLE,
            live_used_status="not_live_used_directly",
            offline_used_status="bridge_exported",
            can_feed_search_memory=bool(pack_terms),
            records_inspected=pack_inspected,
            records_exported=len(pack_terms),
            warnings=(),
        )
    )
    sources.append(
        TaxonomySearchMemorySource(
            source_stage="deep_pack",
            source_file="deep_packs",
            source_path_or_key="src/picwise_taxonomy/deep_packs/",
            connection_status=TaxonomySearchMemoryConnectionStatus.CONNECTED if deep_terms else TaxonomySearchMemoryConnectionStatus.DISCONNECTED,
            live_used_status="indirect_via_vocabulary_source",
            offline_used_status="bridge_exported",
            can_feed_search_memory=bool(deep_terms),
            records_inspected=deep_inspected,
            records_exported=len(deep_terms),
            warnings=(),
        )
    )
    for stage, file_path in _STAGE_FILES:
        if stage in {"stage27a", "stage27b"}:
            continue
        gaps.append(
            TaxonomySearchMemoryGap(
                source_stage=stage,
                source_file=Path(file_path).name,
                source_path_or_key=file_path,
                connection_status=TaxonomySearchMemoryConnectionStatus.DISCONNECTED
                if file_path in files_found
                else TaxonomySearchMemoryConnectionStatus.MISSING,
                reason="disconnected" if file_path in files_found else "missing",
                warning="module exists but no clean bridge export path wired" if file_path in files_found else "module missing",
            )
        )

    counts_by_stage = Counter(term.source_stage for term in exported)
    counts_by_category = Counter(term.mega_category_id for term in exported)
    skipped_total = export_skipped + pack_skipped + deep_skipped
    inspected_total = export_inspected + pack_inspected + deep_inspected
    disconnected_assets = tuple(sorted({gap.source_path_or_key for gap in gaps if gap.connection_status != TaxonomySearchMemoryConnectionStatus.CONNECTED}))
    can_feed = len(exported) > 0
    consumed_registry = len(exported)
    consumed_index = len(exported)

    return TaxonomySearchMemoryBridgeReport(
        stages_inspected=stages,
        files_found=files_found,
        files_missing=files_missing,
        usable_source_records=inspected_total - skipped_total,
        source_records_skipped=skipped_total,
        records_exported_to_search_memory=len(exported),
        records_consumed_by_canonical_registry=consumed_registry,
        records_consumed_by_search_index=consumed_index,
        gaps_found=tuple(gaps),
        counts_by_source_stage=dict(sorted(counts_by_stage.items())),
        counts_by_mega_category_id=dict(sorted(counts_by_category.items())),
        disconnected_assets=disconnected_assets,
        live_used_status="search_memory_bridge_offline_only",
        offline_used_status="active_in_registry_pipeline",
        can_feed_search_memory=can_feed,
        warnings=tuple(sorted(set(warnings))),
        sources=tuple(sources),
    )
