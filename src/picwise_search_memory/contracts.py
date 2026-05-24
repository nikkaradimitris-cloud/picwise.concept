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

    @classmethod
    def from_dict(cls, data: dict) -> CanonicalVocabularyRecord:
        return cls(
            canonical_id=str(data["canonical_id"]),
            canonical_term=str(data["canonical_term"]),
            normalized_term=str(data["normalized_term"]),
            mega_category_id=str(data["mega_category_id"]),
            source=str(data["source"]),
            source_file=str(data["source_file"]),
            language=str(data["language"]),
            status=str(data["status"]),
            schema_version=str(data["schema_version"]),
            token_count=int(data["token_count"]),
            quality_flags=tuple(str(flag) for flag in data.get("quality_flags") or ()),
            aliases=tuple(str(alias) for alias in data.get("aliases") or ()),
            product_family=str(data.get("product_family") or ""),
            source_path=str(data.get("source_path") or ""),
            confidence_weight=float(data.get("confidence_weight") or 1.0),
        )


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

    @classmethod
    def from_dict(cls, data: dict) -> CanonicalVocabularyBuildReport:
        return cls(
            total_input_terms=int(data["total_input_terms"]),
            total_records=int(data["total_records"]),
            rejected_terms=int(data["rejected_terms"]),
            duplicate_terms=int(data["duplicate_terms"]),
            rejected_by_reason={str(key): int(value) for key, value in (data.get("rejected_by_reason") or {}).items()},
            counts_by_mega_category={
                str(key): int(value) for key, value in (data.get("counts_by_mega_category") or {}).items()
            },
            source=str(data["source"]),
            schema_version=str(data["schema_version"]),
            language=str(data["language"]),
            status=str(data["status"]),
        )


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

    @classmethod
    def from_dict(cls, data: dict) -> CanonicalVocabularyRegistry:
        return cls(
            records=tuple(CanonicalVocabularyRecord.from_dict(record) for record in data.get("records") or ()),
            report=CanonicalVocabularyBuildReport.from_dict(data["report"]),
            source=str(data["source"]),
            schema_version=str(data["schema_version"]),
        )
