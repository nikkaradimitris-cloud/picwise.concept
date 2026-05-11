from .contracts import (
    CanonicalSourceReference,
    CanonicalTaxonomyBuildInput,
    CanonicalTaxonomyBuildResult,
    CanonicalTaxonomyRecord,
    CanonicalTaxonomyStatus,
)
from .coverage_matrix import (
    CoverageMatrixInput,
    CoverageMatrixResult,
    CoverageMatrixRow,
    CoverageStrength,
    build_canonical_coverage_matrix,
)
from .deduplication import (
    DeduplicationInput,
    DeduplicationResult,
    MergeCandidate,
    MergeDecision,
    MergeReason,
    MergeStatus,
    build_taxonomy_deduplication,
)
from .registry_builder import build_canonical_taxonomy_registry
from .validation import (
    CanonicalRegistryCatalog,
    build_canonical_registry_catalog,
    validate_canonical_record,
    validate_canonical_records,
)

__all__ = [
    "CanonicalSourceReference",
    "CanonicalTaxonomyBuildInput",
    "CanonicalTaxonomyBuildResult",
    "CanonicalTaxonomyRecord",
    "CanonicalTaxonomyStatus",
    "CoverageMatrixInput",
    "CoverageMatrixResult",
    "CoverageMatrixRow",
    "CoverageStrength",
    "DeduplicationInput",
    "DeduplicationResult",
    "MergeCandidate",
    "MergeDecision",
    "MergeReason",
    "MergeStatus",
    "CanonicalRegistryCatalog",
    "build_canonical_registry_catalog",
    "validate_canonical_record",
    "validate_canonical_records",
    "build_canonical_taxonomy_registry",
    "build_canonical_coverage_matrix",
    "build_taxonomy_deduplication",
]
