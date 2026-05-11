from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from picwise_taxonomy.nlu_export import TaxonomyNLUExportRecord


class NLUTrainingPackStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"
    NEEDS_REVIEW = "needs_review"


class QueryVariantType(str, Enum):
    ALIAS = "alias"
    GREEK_ALIAS = "greek_alias"
    GREEKLISH_ALIAS = "greeklish_alias"
    TYPO_VARIANT = "typo_variant"
    SPEC_INTENT = "spec_intent"
    PRIORITY_TERM = "priority_term"
    MIXED_INTENT = "mixed_intent"


@dataclass(frozen=True)
class NLUTrainingExample:
    example_id: str
    query_text: str
    normalized_query: str
    expected_engine_id: str
    expected_mega_category_id: str
    expected_department: str = ""
    expected_subcategory: str = ""
    expected_product_family: str = ""
    language_script: str = "english"
    intent_label: str = ""
    variant_type: QueryVariantType = QueryVariantType.ALIAS
    source_taxonomy_refs: tuple[str, ...] = field(default_factory=tuple)
    safety_status: str = "safe_training_example"


@dataclass(frozen=True)
class MegaCategoryTrainingPack:
    pack_id: str
    engine_id: str
    mega_category_id: str
    status: NLUTrainingPackStatus
    examples: tuple[NLUTrainingExample, ...]
    source_record_ids: tuple[str, ...] = field(default_factory=tuple)
    signal_counts: dict[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NLUTrainingPackBuildInput:
    export_records: tuple[TaxonomyNLUExportRecord, ...] = field(default_factory=tuple)
    min_examples_for_ready: int = 100
    max_examples_per_pack: int = 180
    stage_title: str = "Stage 27B — NLU Training Packs per Mega-Category"


@dataclass(frozen=True)
class NLUTrainingPackBuildResult:
    packs: tuple[MegaCategoryTrainingPack, ...]
    total_packs: int
    ready_packs: int
    partial_packs: int
    insufficient_data_packs: int
    needs_review_packs: int
    total_examples: int
    examples_by_mega_category: dict[str, int]
    examples_by_engine: dict[str, int]
    examples_by_variant_type: dict[str, int]
    examples_by_language_script: dict[str, int]
    valid: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    stage_title: str = "Stage 27B — NLU Training Packs per Mega-Category"
