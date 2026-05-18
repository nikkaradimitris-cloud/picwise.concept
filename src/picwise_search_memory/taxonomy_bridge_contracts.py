from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaxonomySearchMemoryConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    MISSING = "missing"
    NOT_EXPORTABLE = "not_exportable"


@dataclass(frozen=True)
class TaxonomySearchMemorySource:
    source_stage: str
    source_file: str
    source_path_or_key: str
    connection_status: TaxonomySearchMemoryConnectionStatus
    live_used_status: str
    offline_used_status: str
    can_feed_search_memory: bool
    records_inspected: int = 0
    records_exported: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaxonomySearchMemoryTerm:
    canonical_term: str
    normalized_term: str
    mega_category_id: str
    source_stage: str
    source_file: str
    source_path_or_key: str
    product_family: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)
    language: str = "english"
    status: str = "offline_source_only"
    quality_flags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaxonomySearchMemoryGap:
    source_stage: str
    source_file: str
    source_path_or_key: str
    connection_status: TaxonomySearchMemoryConnectionStatus
    reason: str
    warning: str = ""


@dataclass(frozen=True)
class TaxonomySearchMemoryBridgeReport:
    stages_inspected: tuple[str, ...]
    files_found: tuple[str, ...]
    files_missing: tuple[str, ...]
    usable_source_records: int
    source_records_skipped: int
    records_exported_to_search_memory: int
    records_consumed_by_canonical_registry: int
    records_consumed_by_search_index: int
    gaps_found: tuple[TaxonomySearchMemoryGap, ...]
    counts_by_source_stage: dict[str, int]
    counts_by_mega_category_id: dict[str, int]
    disconnected_assets: tuple[str, ...]
    live_used_status: str
    offline_used_status: str
    can_feed_search_memory: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    sources: tuple[TaxonomySearchMemorySource, ...] = field(default_factory=tuple)
