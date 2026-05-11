from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

REQUIRED_STATUSES: Tuple[str, ...] = (
    "contract_defined",
    "planned_source_import",
    "needs_taxonomy_expansion",
    "blocked_until_future_stage",
)


@dataclass(frozen=True)
class SaaSERPSoftwareFamily:
    family_id: str
    display_name: str
    description: str


@dataclass(frozen=True)
class SaaSERPFieldDefinition:
    field_id: str
    display_name: str
    description: str
    expected_values: Tuple[str, ...]
    required_for_contract: bool = True


@dataclass(frozen=True)
class SaaSERPIntentPattern:
    pattern_id: str
    display_name: str
    query_examples: Tuple[str, ...]
    description: str


@dataclass(frozen=True)
class SaaSERPRankingDimension:
    dimension_id: str
    display_name: str
    description: str
    contract_only: bool = True
    scoring_implemented: bool = False


@dataclass(frozen=True)
class SaaSERPCategoryBucket:
    bucket_id: str
    display_name: str
    description: str
    example_software_families: Tuple[SaaSERPSoftwareFamily, ...]
    relevant_business_sizes: Tuple[str, ...]
    intent_examples: Tuple[SaaSERPIntentPattern, ...]
    field_definitions: Tuple[SaaSERPFieldDefinition, ...]
    ranking_dimensions: Tuple[SaaSERPRankingDimension, ...]
    source_status: str
    readiness_status: str


@dataclass(frozen=True)
class SaaSERPVerticalReadiness:
    vertical_id: str
    current_status: str
    readiness_reason: str
    next_stage_dependency: str


@dataclass(frozen=True)
class SaaSERPTaxonomyManifest:
    stage_id: str
    stage_title: str
    vertical_id: str
    stage_28d_market_scope_reference: str
    separate_from_vertical_id: str
    not_forced_into_retail_engine: str
    avoids_google_product_taxonomy_backbone: bool
    future_source_plans: Tuple[str, ...]
    category_buckets: Tuple[SaaSERPCategoryBucket, ...]
    intent_patterns: Tuple[SaaSERPIntentPattern, ...]
    ranking_dimensions: Tuple[SaaSERPRankingDimension, ...]
    status_catalog: Tuple[str, ...]
    dependency_boundaries: dict
    non_goals: dict
    vertical_readiness: SaaSERPVerticalReadiness

