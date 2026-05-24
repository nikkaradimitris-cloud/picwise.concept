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
    canonical_source: str = ""
    canonical_status: str = ""

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
            "canonical_source": self.canonical_source,
            "canonical_status": self.canonical_status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchIndexEntry:
        return cls(
            index_key=str(data["index_key"]),
            variant=str(data["variant"]),
            normalized_variant=str(data["normalized_variant"]),
            canonical_id=str(data["canonical_id"]),
            canonical_term=str(data["canonical_term"]),
            normalized_term=str(data["normalized_term"]),
            mega_category_id=str(data["mega_category_id"]),
            variant_type=str(data["variant_type"]),
            source=str(data["source"]),
            generator_version=str(data["generator_version"]),
            schema_version=str(data["schema_version"]),
            token_count=int(data["token_count"]),
            quality_flags=tuple(str(flag) for flag in data.get("quality_flags") or ()),
            canonical_source=str(data.get("canonical_source") or ""),
            canonical_status=str(data.get("canonical_status") or ""),
        )


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
    total_collision_keys: int = 0
    collision_entries_count: int = 0
    collision_keys_by_variant_type: dict[str, int] = field(default_factory=dict)
    collision_entries_by_variant_type: dict[str, int] = field(default_factory=dict)
    collision_entries_by_mega_category_id: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_canonical_records": self.total_canonical_records,
            "total_generated_variants": self.total_generated_variants,
            "total_index_entries": self.total_index_entries,
            "duplicates_removed": self.duplicates_removed,
            "rejected_count": self.rejected_count,
            "counts_by_mega_category_id": dict(sorted(self.counts_by_mega_category_id.items())),
            "counts_by_variant_type": dict(sorted(self.counts_by_variant_type.items())),
            "total_collision_keys": self.total_collision_keys,
            "collision_entries_count": self.collision_entries_count,
            "collision_keys_by_variant_type": dict(sorted(self.collision_keys_by_variant_type.items())),
            "collision_entries_by_variant_type": dict(sorted(self.collision_entries_by_variant_type.items())),
            "collision_entries_by_mega_category_id": dict(sorted(self.collision_entries_by_mega_category_id.items())),
            "schema_version": self.schema_version,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchIndexBuildReport:
        return cls(
            total_canonical_records=int(data["total_canonical_records"]),
            total_generated_variants=int(data["total_generated_variants"]),
            total_index_entries=int(data["total_index_entries"]),
            duplicates_removed=int(data["duplicates_removed"]),
            rejected_count=int(data["rejected_count"]),
            counts_by_mega_category_id={
                str(key): int(value) for key, value in (data.get("counts_by_mega_category_id") or {}).items()
            },
            counts_by_variant_type={
                str(key): int(value) for key, value in (data.get("counts_by_variant_type") or {}).items()
            },
            schema_version=str(data["schema_version"]),
            source=str(data["source"]),
            total_collision_keys=int(data.get("total_collision_keys") or 0),
            collision_entries_count=int(data.get("collision_entries_count") or 0),
            collision_keys_by_variant_type={
                str(key): int(value) for key, value in (data.get("collision_keys_by_variant_type") or {}).items()
            },
            collision_entries_by_variant_type={
                str(key): int(value) for key, value in (data.get("collision_entries_by_variant_type") or {}).items()
            },
            collision_entries_by_mega_category_id={
                str(key): int(value) for key, value in (data.get("collision_entries_by_mega_category_id") or {}).items()
            },
        )


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

    @classmethod
    def from_dict(cls, data: dict) -> SearchIndex:
        return cls(
            entries=tuple(SearchIndexEntry.from_dict(entry) for entry in data.get("entries") or ()),
            report=SearchIndexBuildReport.from_dict(data["report"]),
            schema_version=str(data["schema_version"]),
            source=str(data["source"]),
        )


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
