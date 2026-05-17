from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchIndexEntry:
    index_key: str
    variant: str
    normalized_variant: str
    canonical_id: str
    canonical_term: str
    normalized_term: str
    mega_category_id: str
    variant_type: str
    source: str
    generator_version: str
    schema_version: str
    token_count: int
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "index_key": self.index_key,
            "variant": self.variant,
            "normalized_variant": self.normalized_variant,
            "canonical_id": self.canonical_id,
            "canonical_term": self.canonical_term,
            "normalized_term": self.normalized_term,
            "mega_category_id": self.mega_category_id,
            "variant_type": self.variant_type,
            "source": self.source,
            "generator_version": self.generator_version,
            "schema_version": self.schema_version,
            "token_count": self.token_count,
            "quality_flags": list(self.quality_flags),
        }


@dataclass(frozen=True)
class SearchIndexBuildReport:
    total_canonical_records: int
    total_generated_variants: int
    total_index_entries: int
    duplicates_removed: int
    rejected_count: int
    counts_by_mega_category_id: dict[str, int]
    counts_by_variant_type: dict[str, int]
    schema_version: str
    source: str

    def to_dict(self) -> dict:
        return {
            "total_canonical_records": self.total_canonical_records,
            "total_generated_variants": self.total_generated_variants,
            "total_index_entries": self.total_index_entries,
            "duplicates_removed": self.duplicates_removed,
            "rejected_count": self.rejected_count,
            "counts_by_mega_category_id": dict(sorted(self.counts_by_mega_category_id.items())),
            "counts_by_variant_type": dict(sorted(self.counts_by_variant_type.items())),
            "schema_version": self.schema_version,
            "source": self.source,
        }


@dataclass(frozen=True)
class SearchIndex:
    entries: tuple[SearchIndexEntry, ...]
    report: SearchIndexBuildReport
    schema_version: str
    source: str

    def to_dict(self) -> dict:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "report": self.report.to_dict(),
            "schema_version": self.schema_version,
            "source": self.source,
        }


@dataclass(frozen=True)
class SearchIndexLookupResult:
    query: str
    normalized_query: str
    status: str
    score: float
    confidence: str
    matched_entry: SearchIndexEntry | None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "status": self.status,
            "score": self.score,
            "confidence": self.confidence,
            "matched_entry": self.matched_entry.to_dict() if self.matched_entry else None,
            "reason_codes": list(self.reason_codes),
        }
