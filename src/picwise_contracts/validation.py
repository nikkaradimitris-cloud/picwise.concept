from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .enums import DecisionDepth, MissingDataState, ProductBrain, ProductChoiceRole


class ContractValidationError(ValueError):
    """Raised when a contract payload violates Picwise schema rules."""


FORBIDDEN_FAKE_KEYWORDS = (
    "fake_review",
    "fake_reviews",
    "fake_rating",
    "fake_ratings",
    "fake_revenue",
    "fake_saving",
    "fake_savings",
    "fake_urgency",
    "fake_confidence",
    "fake_ai_confidence",
)

FORBIDDEN_COMMISSION_RANKING_KEYWORDS = (
    "commission_rank",
    "commission_score",
    "rank_by_commission",
    "recommend_by_commission",
    "recommended_by_commission",
    "affiliate_weight",
)

ALLOWED_MISSING_DATA_STATES = {state.value for state in MissingDataState}

COMMON_ROLES = {
    ProductChoiceRole.BUDGET,
    ProductChoiceRole.VALUE,
    ProductChoiceRole.BEST_OVERALL,
    ProductChoiceRole.PREMIUM,
}

BRAIN_SPECIFIC_ROLES: dict[ProductBrain, set[ProductChoiceRole]] = {
    ProductBrain.SOFTWARE_PROGRAMS_SAAS: {
        ProductChoiceRole.BASIC,
        ProductChoiceRole.BEST_FOR_SMALL_BUSINESS,
    },
    ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS: {
        ProductChoiceRole.LOWEST_MONTHLY_COST,
        ProductChoiceRole.STABLE_PRICE,
        ProductChoiceRole.FLEXIBLE_PLAN,
    },
    ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS: {
        ProductChoiceRole.SAFE_BUDGET,
        ProductChoiceRole.BEST_SAFETY,
        ProductChoiceRole.BEST_COMFORT,
        ProductChoiceRole.PREMIUM_ISOFIX,
    },
    # TODO: Expand role taxonomy by category once dedicated role specs are added.
}

CTA_BY_BRAIN: dict[ProductBrain, set[str]] = {
    ProductBrain.TECH_SPECS_ELECTRONICS: {
        "View in Store",
        "Go to Store",
        "View Details and Buy",
    },
    ProductBrain.PHYSICAL_PRODUCTS_HOME_MACHINES: {
        "View in Store",
        "Go to Store",
        "View Details and Buy",
    },
    ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS: {
        "View in Store",
        "Go to Store",
        "View Details and Buy",
    },
    ProductBrain.SOFTWARE_PROGRAMS_SAAS: {
        "View Plan",
        "View Pricing",
        "View Details",
    },
    ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS: {
        "View Offer",
        "Compare Terms",
        "Estimate Cost",
        "Continue to Provider",
        "Request Offer",
    },
}


@dataclass(frozen=True)
class ValidationWarning:
    code: str
    message: str


def validate_missing_data_states(states: Sequence[str]) -> None:
    unknown_states = set(states) - ALLOWED_MISSING_DATA_STATES
    if unknown_states:
        raise ContractValidationError(
            f"Invalid missing_data_states: {sorted(unknown_states)}"
        )


def _scan_for_forbidden_keywords(payload: Any, keywords: tuple[str, ...]) -> list[str]:
    found: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, Mapping):
            for key, value in obj.items():
                key_str = str(key).lower()
                for keyword in keywords:
                    if keyword in key_str:
                        found.append(str(key))
                walk(value)
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            for item in obj:
                walk(item)

    walk(payload)
    return found


def validate_no_fake_data(payload: Any) -> None:
    offending_keys = _scan_for_forbidden_keywords(payload, FORBIDDEN_FAKE_KEYWORDS)
    if offending_keys:
        raise ContractValidationError(
            f"Forbidden fake-data markers present: {sorted(set(offending_keys))}"
        )


def validate_no_commission_ranking_fields(payload: Any) -> None:
    offending_keys = _scan_for_forbidden_keywords(
        payload, FORBIDDEN_COMMISSION_RANKING_KEYWORDS
    )
    if offending_keys:
        raise ContractValidationError(
            "Commission ranking fields are forbidden: "
            f"{sorted(set(offending_keys))}"
        )


def validate_choice_role(role: ProductChoiceRole, brain: ProductBrain) -> None:
    allowed = set(COMMON_ROLES)
    allowed.update(BRAIN_SPECIFIC_ROLES.get(brain, set()))
    if role not in allowed:
        raise ContractValidationError(
            f"Role '{role.value}' is not allowed for brain '{brain.value}'."
        )


def validate_cta_label(cta_label: str, brain: ProductBrain) -> list[ValidationWarning]:
    allowed_labels = CTA_BY_BRAIN.get(brain, set())
    if cta_label in allowed_labels:
        return []
    return [
        ValidationWarning(
            code="cta_label_non_standard",
            message=(
                f"CTA '{cta_label}' is not in the canonical list for brain "
                f"'{brain.value}'."
            ),
        )
    ]


def validate_financial_utility_choice_requirements(risks_or_limitations: str) -> None:
    lowered = risks_or_limitations.lower()
    required_terms = ("term", "risk", "unknown", "condition", "fee", "charge", "cancel")
    if not any(marker in lowered for marker in required_terms):
        raise ContractValidationError(
            "Financial/utility choice must include terms, risks, or unknowns."
        )


def validate_primary_choice_count(choices_count: int) -> None:
    if choices_count != 4:
        raise ContractValidationError(
            f"DecisionOutput must contain exactly 4 primary choices, got {choices_count}."
        )


def validate_recommended_count(recommended_count: int) -> None:
    if recommended_count != 1:
        raise ContractValidationError(
            "DecisionOutput must contain exactly 1 recommended choice, "
            f"got {recommended_count}."
        )
