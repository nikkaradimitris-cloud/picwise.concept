from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CanonicalVocabularyRecord:
    canonical_id: str
    canonical_term: str
    normalized_term: str
    mega_category_id: str
    source: str
    source_file: str
    language: str
    status: str
    schema_version: str
    token_count: int
    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    product_family: str = ""
    source_path: str = ""
    confidence_weight: float = 1.0

    def to_dict(self) -> dict:
        return {
            "canonical_id": self.canonical_id,
            "canonical_term": self.canonical_term,
            "normalized_term": self.normalized_term,
            "mega_category_id": self.mega_category_id,
            "source": self.source,
            "source_file": self.source_file,
            "language": self.language,
            "status": self.status,
            "schema_version": self.schema_version,
            "token_count": self.token_count,
            "quality_flags": list(self.quality_flags),
            "aliases": list(self.aliases),
            "product_family": self.product_family,
            "source_path": self.source_path,
            "confidence_weight": self.confidence_weight,
        }


@dataclass(frozen=True)
class CanonicalVocabularyBuildReport:
    total_input_terms: int
    total_records: int
    rejected_terms: int
    duplicate_terms: int
    rejected_by_reason: dict[str, int]
    counts_by_mega_category: dict[str, int]
    source: str
    schema_version: str
    language: str
    status: str

    def to_dict(self) -> dict:
        return {
            "total_input_terms": self.total_input_terms,
            "total_records": self.total_records,
            "rejected_terms": self.rejected_terms,
            "duplicate_terms": self.duplicate_terms,
            "rejected_by_reason": dict(sorted(self.rejected_by_reason.items())),
            "counts_by_mega_category": dict(sorted(self.counts_by_mega_category.items())),
            "source": self.source,
            "schema_version": self.schema_version,
            "language": self.language,
            "status": self.status,
        }


@dataclass(frozen=True)
class CanonicalVocabularyRegistry:
    records: tuple[CanonicalVocabularyRecord, ...]
    report: CanonicalVocabularyBuildReport
    source: str
    schema_version: str

    def to_dict(self) -> dict:
        return {
            "records": [record.to_dict() for record in self.records],
            "report": self.report.to_dict(),
            "source": self.source,
            "schema_version": self.schema_version,
        }
