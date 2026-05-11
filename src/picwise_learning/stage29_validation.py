from __future__ import annotations

from .stage29_contracts import (
    STAGE29_ID,
    RISK_LEVELS,
    SUGGESTION_APPROVAL_STATUSES,
    Stage29GeneratedQueryRecord,
    Stage29LearningSuggestion,
    Stage29SeedRecord,
)

_FINANCE_BLOCKED_HINTS = ("advice", "quote", "eligibility", "approval", "application", "provider")


def _require(value: str | None, name: str, errors: list[str]) -> None:
    if not str(value or "").strip():
        errors.append(f"missing:{name}")


def validate_seed_record(seed: Stage29SeedRecord) -> dict:
    errors: list[str] = []
    _require(seed.seed_id, "seed_id", errors)
    _require(seed.expected_nlu_target, "expected_nlu_target", errors)
    if seed.vertical == "retail_physical_products":
        _require(seed.retail_engine, "retail_engine", errors)
        _require(seed.mega_category, "mega_category", errors)
    if seed.vertical == "software_saas_erp" and seed.retail_engine:
        errors.append("saas_must_not_have_retail_engine")
    if seed.vertical == "finance_insurance_business_finance":
        if seed.retail_engine:
            errors.append("finance_must_not_have_retail_engine")
        text = seed.canonical_query.lower()
        if any(term in text for term in _FINANCE_BLOCKED_HINTS):
            errors.append("finance_query_contains_blocked_intent")
    return {"valid": not errors, "errors": errors}


def validate_generated_query_record(record: Stage29GeneratedQueryRecord) -> dict:
    errors: list[str] = []
    _require(record.record_id, "record_id", errors)
    _require(record.generated_query, "generated_query", errors)
    _require(record.canonical_query, "canonical_query", errors)
    _require(record.source_seed_id, "source_seed_id", errors)
    _require(record.expected_nlu_target, "expected_nlu_target", errors)
    if record.stage != STAGE29_ID:
        errors.append("stage_must_be_29")
    if record.vertical == "retail_physical_products":
        _require(record.retail_engine, "retail_engine", errors)
        if not record.mega_category:
            errors.append("retail_requires_mega_category")
    if record.vertical == "software_saas_erp" and record.retail_engine:
        errors.append("saas_must_not_have_retail_engine")
    if record.vertical == "finance_insurance_business_finance" and record.retail_engine:
        errors.append("finance_must_not_have_retail_engine")
    if not record.offline_only:
        errors.append("offline_only_required")
    return {"valid": not errors, "errors": errors}


def validate_learning_suggestion(suggestion: Stage29LearningSuggestion) -> dict:
    errors: list[str] = []
    _require(suggestion.suggestion_id, "suggestion_id", errors)
    _require(suggestion.suggested_target, "suggested_target", errors)
    if suggestion.approval_status not in SUGGESTION_APPROVAL_STATUSES:
        errors.append("invalid_approval_status")
    if suggestion.risk_level not in RISK_LEVELS:
        errors.append("invalid_risk_level")
    if not suggestion.source_failure_ids:
        errors.append("missing_source_failure_ids")
    if not suggestion.offline_only:
        errors.append("offline_only_required")
    return {"valid": not errors, "errors": errors}
