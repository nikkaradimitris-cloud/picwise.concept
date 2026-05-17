from .canonical_registry import build_canonical_vocabulary_registry
from .contracts import (
    CanonicalVocabularyBuildReport,
    CanonicalVocabularyRecord,
    CanonicalVocabularyRegistry,
)
from .index_builder import build_offline_search_index
from .index_contracts import SearchIndex, SearchIndexBuildReport, SearchIndexEntry, SearchIndexLookupResult
from .index_lookup import lookup_offline_search_index
from .validation import known_mega_category_ids, normalize_term, stable_canonical_id, validate_record, validate_registry

__all__ = [
    "CanonicalVocabularyRecord",
    "CanonicalVocabularyRegistry",
    "CanonicalVocabularyBuildReport",
    "SearchIndexEntry",
    "SearchIndex",
    "SearchIndexBuildReport",
    "SearchIndexLookupResult",
    "build_canonical_vocabulary_registry",
    "build_offline_search_index",
    "lookup_offline_search_index",
    "known_mega_category_ids",
    "normalize_term",
    "stable_canonical_id",
    "validate_record",
    "validate_registry",
]
