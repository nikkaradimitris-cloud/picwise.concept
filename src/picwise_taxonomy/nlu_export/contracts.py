from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaxonomyNLUExportStatus(str, Enum):
    ACTIVE = "active"
    REVIEW_ONLY = "review_only"
    DISABLED_GAP = "disabled_gap"


@dataclass(frozen=True)
class TaxonomyNLUSignalSet:
    aliases: tuple[str, ...] = field(default_factory=tuple)
    greek_aliases: tuple[str, ...] = field(default_factory=tuple)
    greeklish_aliases: tuple[str, ...] = field(default_factory=tuple)
    typo_variants: tuple[str, ...] = field(default_factory=tuple)
    spec_fields: tuple[str, ...] = field(default_factory=tuple)
    intent_patterns: tuple[str, ...] = field(default_factory=tuple)
    priority_terms: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaxonomyNLUExportRecord:
    export_id: str
    status: TaxonomyNLUExportStatus
    engine_id: str
    mega_category_id: str
    department: str = ""
    subcategory: str = ""
    product_family: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)
    greek_aliases: tuple[str, ...] = field(default_factory=tuple)
    greeklish_aliases: tuple[str, ...] = field(default_factory=tuple)
    typo_variants: tuple[str, ...] = field(default_factory=tuple)
    spec_fields: tuple[str, ...] = field(default_factory=tuple)
    intent_patterns: tuple[str, ...] = field(default_factory=tuple)
    priority_terms: tuple[str, ...] = field(default_factory=tuple)
    source_stage_refs: tuple[str, ...] = field(default_factory=tuple)
    validation_warnings: tuple[str, ...] = field(default_factory=tuple)
    signals: TaxonomyNLUSignalSet = field(default_factory=TaxonomyNLUSignalSet)


@dataclass(frozen=True)
class TaxonomyNLUExportInput:
    source_packs: tuple[dict, ...] = field(default_factory=tuple)
    include_review_items: bool = True
    include_disabled_gap_items: bool = True
    stage_title: str = "Stage 27A — Taxonomy → Local NLU Export"
    stage_ref: str = "stage_27a_taxonomy_to_local_nlu_export"


@dataclass(frozen=True)
class TaxonomyNLUExportResult:
    records: tuple[TaxonomyNLUExportRecord, ...]
    total_records: int
    active_records: int
    review_only_records: int
    disabled_gap_records: int
    counts_by_engine: dict[str, int]
    counts_by_mega_category: dict[str, int]
    total_aliases: int
    total_greek_aliases: int
    total_greeklish_aliases: int
    total_typo_variants: int
    total_spec_fields: int
    total_intent_patterns: int
    total_priority_terms: int
    valid: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    stage_title: str = "Stage 27A — Taxonomy → Local NLU Export"

