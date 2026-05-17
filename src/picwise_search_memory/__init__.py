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
from .blind_evaluation import (
    build_blind_evaluation_report,
    evaluate_blind_cases,
    generate_blind_evaluation_cases,
    run_offline_blind_index_evaluation,
)
from .evaluation_contracts import (
    BlindEvaluationCase,
    BlindEvaluationReport,
    BlindEvaluationResult,
    BlindEvaluationThresholds,
)

__all__ = [
    "CanonicalVocabularyRecord",
    "CanonicalVocabularyRegistry",
    "CanonicalVocabularyBuildReport",
    "SearchIndexEntry",
    "SearchIndex",
    "SearchIndexBuildReport",
    "SearchIndexLookupResult",
    "BlindEvaluationCase",
    "BlindEvaluationResult",
    "BlindEvaluationReport",
    "BlindEvaluationThresholds",
    "build_canonical_vocabulary_registry",
    "build_offline_search_index",
    "lookup_offline_search_index",
    "generate_blind_evaluation_cases",
    "evaluate_blind_cases",
    "build_blind_evaluation_report",
    "run_offline_blind_index_evaluation",
    "known_mega_category_ids",
    "normalize_term",
    "stable_canonical_id",
    "validate_record",
    "validate_registry",
]
