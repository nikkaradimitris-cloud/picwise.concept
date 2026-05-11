from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CanonicalTaxonomyStatus(str, Enum):
    ACTIVE = "active"
    REVIEW_ONLY = "review_only"
    BLOCKED_GAP = "blocked_gap"


@dataclass(frozen=True)
class CanonicalSourceReference:
    source_item_id: str
    source_name: str
    source_type: str
    mapping_status: str
    mapping_confidence: str
    mapping_gap_reason: str = ""
    stage: str = "Stage 25A — Canonical Taxonomy Registry Builder"


@dataclass(frozen=True)
class CanonicalTaxonomyRecord:
    record_id: str
    status: CanonicalTaxonomyStatus
    engine_id: str
    mega_category_id: str
    department: str = ""
    subcategory: str = ""
    product_family: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)
    spec_fields: tuple[str, ...] = field(default_factory=tuple)
    intent_patterns: tuple[str, ...] = field(default_factory=tuple)
    source_references: tuple[CanonicalSourceReference, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CanonicalTaxonomyBuildInput:
    source_items: tuple[dict, ...] = field(default_factory=tuple)
    mapped_results: tuple[dict, ...] = field(default_factory=tuple)
    gap_records: tuple[dict, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CanonicalTaxonomyBuildResult:
    records: tuple[CanonicalTaxonomyRecord, ...]
    total_records: int
    active_records: int
    review_only_records: int
    blocked_gap_records: int
    counts_by_engine: dict[str, int]
    counts_by_mega_category: dict[str, int]
    source_count: int
    gap_count: int
    valid: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    stage: str = "Stage 25A — Canonical Taxonomy Registry Builder"
    coverage_matrix_created: bool = False
    dedup_rules_created: bool = False
    canonical_registry_created: bool = True

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "records": [
                {
                    "record_id": record.record_id,
                    "status": record.status.value,
                    "engine_id": record.engine_id,
                    "mega_category_id": record.mega_category_id,
                    "department": record.department,
                    "subcategory": record.subcategory,
                    "product_family": record.product_family,
                    "aliases": list(record.aliases),
                    "spec_fields": list(record.spec_fields),
                    "intent_patterns": list(record.intent_patterns),
                    "provenance": list(record.provenance),
                    "source_references": [
                        {
                            "source_item_id": reference.source_item_id,
                            "source_name": reference.source_name,
                            "source_type": reference.source_type,
                            "mapping_status": reference.mapping_status,
                            "mapping_confidence": reference.mapping_confidence,
                            "mapping_gap_reason": reference.mapping_gap_reason,
                            "stage": reference.stage,
                        }
                        for reference in record.source_references
                    ],
                }
                for record in self.records
            ],
            "summary": {
                "total_records": self.total_records,
                "active_records": self.active_records,
                "review_only_records": self.review_only_records,
                "blocked_gap_records": self.blocked_gap_records,
                "counts_by_engine": dict(sorted(self.counts_by_engine.items())),
                "counts_by_mega_category": dict(sorted(self.counts_by_mega_category.items())),
                "source_count": self.source_count,
                "gap_count": self.gap_count,
                "valid": self.valid,
                "reasons": list(self.reasons),
                "warnings": list(self.warnings),
            },
            "coverage_matrix_created": self.coverage_matrix_created,
            "dedup_rules_created": self.dedup_rules_created,
            "canonical_registry_created": self.canonical_registry_created,
        }
