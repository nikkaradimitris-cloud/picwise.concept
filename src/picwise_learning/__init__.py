"""Stage 29 offline NLU learning package."""

from .stage29_approval_gate import filter_approved_suggestions, set_approval_status
from .stage29_config import Stage29GenerationConfig, build_default_stage29_config
from .stage29_contracts import (
    STAGE29_ID,
    Stage29EvaluationRecord,
    Stage29FailureRecord,
    Stage29GeneratedQueryRecord,
    Stage29LearningSuggestion,
    Stage29RegressionCase,
    Stage29RegressionPack,
    Stage29SeedRecord,
    Stage29UpdatePack,
)
from .stage29_evaluation import evaluate_generated_queries
from .stage29_failure_analysis import analyze_failures
from .stage29_query_generator import chunk_generated_queries, generate_queries_stream
from .stage29_regression_pack import build_regression_pack
from .stage29_seed_builder import build_stage29_seeds
from .stage29_suggestions import build_learning_suggestions
from .stage29_update_pack import build_update_pack
from .stage29_validation import (
    validate_generated_query_record,
    validate_learning_suggestion,
    validate_seed_record,
)
from .stage30_config import Stage30ShadowConfig, build_default_stage30_config
from .stage30_contracts import (
    STAGE30_ID,
    Stage30FailureCandidate,
    Stage30ShadowRecord,
    Stage30ShadowSummary,
)
from .stage30_failure_bridge import build_failure_candidate, build_failure_candidates
from .stage30_runtime_probe import Stage30RuntimeProbe, build_default_stage30_runtime_probe
from .stage30_shadow_runner import Stage30ShadowRunner
from .stage30_summary import build_shadow_summary
from .stage30_validation import validate_shadow_record

__all__ = [
    "STAGE29_ID",
    "Stage29GenerationConfig",
    "build_default_stage29_config",
    "Stage29SeedRecord",
    "Stage29GeneratedQueryRecord",
    "Stage29EvaluationRecord",
    "Stage29FailureRecord",
    "Stage29LearningSuggestion",
    "Stage29UpdatePack",
    "Stage29RegressionCase",
    "Stage29RegressionPack",
    "build_stage29_seeds",
    "generate_queries_stream",
    "chunk_generated_queries",
    "evaluate_generated_queries",
    "analyze_failures",
    "build_learning_suggestions",
    "set_approval_status",
    "filter_approved_suggestions",
    "build_update_pack",
    "build_regression_pack",
    "validate_seed_record",
    "validate_generated_query_record",
    "validate_learning_suggestion",
    "STAGE30_ID",
    "Stage30ShadowConfig",
    "build_default_stage30_config",
    "Stage30ShadowRecord",
    "Stage30FailureCandidate",
    "Stage30ShadowSummary",
    "Stage30ShadowRunner",
    "Stage30RuntimeProbe",
    "build_default_stage30_runtime_probe",
    "build_failure_candidate",
    "build_failure_candidates",
    "build_shadow_summary",
    "validate_shadow_record",
]
