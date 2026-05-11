from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

REQUIRED_STATUSES: Tuple[str, ...] = (
    "contract_defined",
    "planned_source_import",
    "needs_taxonomy_expansion",
    "blocked_until_future_stage",
)

REQUIRED_SAFETY_STATUSES: Tuple[str, ...] = (
    "comparison_allowed",
    "review_required",
    "regulated_advice_blocked",
    "quote_application_blocked",
    "eligibility_decision_blocked",
)


@dataclass(frozen=True)
class FinanceInsuranceProductFamily:
    family_id: str
    display_name: str
    description: str


@dataclass(frozen=True)
class FinanceInsuranceFieldDefinition:
    field_id: str
    display_name: str
    description: str
    expected_values: Tuple[str, ...]
    required_for_contract: bool = True


@dataclass(frozen=True)
class FinanceInsuranceIntentPattern:
    pattern_id: str
    display_name: str
    query_examples: Tuple[str, ...]
    description: str


@dataclass(frozen=True)
class FinanceInsuranceRankingDimension:
    dimension_id: str
    display_name: str
    description: str
    contract_only: bool = True
    scoring_implemented: bool = False


@dataclass(frozen=True)
class FinanceInsuranceSafetyRequirement:
    requirement_id: str
    display_name: str
    description: str
    safety_status: str


@dataclass(frozen=True)
class FinanceInsuranceCategoryBucket:
    bucket_id: str
    display_name: str
    description: str
    example_product_service_families: Tuple[FinanceInsuranceProductFamily, ...]
    relevant_user_business_profiles: Tuple[str, ...]
    intent_examples: Tuple[FinanceInsuranceIntentPattern, ...]
    field_definitions: Tuple[FinanceInsuranceFieldDefinition, ...]
    ranking_dimensions: Tuple[FinanceInsuranceRankingDimension, ...]
    safety_requirements: Tuple[FinanceInsuranceSafetyRequirement, ...]
    source_status: str
    readiness_status: str


@dataclass(frozen=True)
class FinanceInsuranceVerticalReadiness:
    vertical_id: str
    current_status: str
    readiness_reason: str
    next_stage_dependency: str


@dataclass(frozen=True)
class FinanceInsuranceTaxonomyManifest:
    stage_id: str
    stage_title: str
    vertical_id: str
    stage_28d_market_scope_reference: str
    separate_from_vertical_ids: Tuple[str, ...]
    not_forced_into_retail_engines: Tuple[str, ...]
    avoids_google_product_taxonomy_backbone: bool
    future_source_plans: Tuple[str, ...]
    category_buckets: Tuple[FinanceInsuranceCategoryBucket, ...]
    intent_patterns: Tuple[FinanceInsuranceIntentPattern, ...]
    ranking_dimensions: Tuple[FinanceInsuranceRankingDimension, ...]
    safety_status_catalog: Tuple[str, ...]
    status_catalog: Tuple[str, ...]
    dependency_boundaries: dict
    non_goals: dict
    vertical_readiness: FinanceInsuranceVerticalReadiness
