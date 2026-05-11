from __future__ import annotations

import json

from .manifest import get_finance_insurance_taxonomy_manifest

_REQUIRED_BUCKET_IDS = {
    "banking_accounts_cards",
    "loans_mortgages_leasing",
    "insurance_protection",
    "payments_pos_merchant_services",
    "investing_trading_platforms",
    "business_finance_accounting_tools",
    "tax_legal_compliance_finance_support",
    "financial_education_comparison",
}

_REQUIRED_FIELDS = {
    "fees",
    "interest_rate_type",
    "apr_apy_markers",
    "eligibility_requirements",
    "term_length",
    "coverage_type",
    "deductible_excess",
    "risk_level",
    "country_availability",
    "provider_trust",
    "regulatory_disclaimer_required",
    "manual_review_required",
}

_REQUIRED_INTENTS = {
    "compare_cards",
    "compare_loans",
    "compare_insurance",
    "low_fee_account",
    "business_pos_payment_provider",
    "small_business_finance",
    "car_insurance",
    "health_insurance",
    "mortgage_comparison",
    "investment_platform_comparison",
    "eligibility_question",
    "risk_safety_question",
}

_REQUIRED_SAFETY_STATUSES = {
    "comparison_allowed",
    "review_required",
    "regulated_advice_blocked",
    "quote_application_blocked",
    "eligibility_decision_blocked",
}

_REQUIRED_RETAIL_ENGINE_IDS = {
    "home_living_appliances_engine",
    "tech_electronics_office_engine",
    "auto_moto_mobility_engine",
    "tools_diy_garden_repair_engine",
    "health_beauty_family_lifestyle_engine",
    "fashion_footwear_jewelry_accessories_engine",
}


def validate_finance_insurance_taxonomy_manifest() -> dict:
    """Validate Stage 28F finance/insurance taxonomy contract and boundaries."""
    manifest = get_finance_insurance_taxonomy_manifest()
    buckets = manifest["category_buckets"]
    bucket_ids = {bucket["bucket_id"] for bucket in buckets}
    manifest_intent_ids = {intent["pattern_id"] for intent in manifest["intent_patterns"]}

    all_buckets_have_families = all(bucket["example_product_service_families"] for bucket in buckets)
    all_buckets_have_intents = all(bucket["intent_examples"] for bucket in buckets)
    all_buckets_have_fields = all(
        _REQUIRED_FIELDS.issubset({field["field_id"] for field in bucket["field_definitions"]})
        for bucket in buckets
    )
    all_buckets_have_safety_requirements = all(
        _REQUIRED_SAFETY_STATUSES.issubset({item["safety_status"] for item in bucket["safety_requirements"]})
        for bucket in buckets
    )
    ranking_contract_only = all(
        dimension["contract_only"] and not dimension["scoring_implemented"]
        for bucket in buckets
        for dimension in bucket["ranking_dimensions"]
    ) and all(
        dimension["contract_only"] and not dimension["scoring_implemented"]
        for dimension in manifest["ranking_dimensions"]
    )

    result = {
        "valid": True,
        "passed": True,
        "is_json_serializable": True,
        "stage_title_exact": manifest["stage_title"] == "Stage 28F — Finance / Insurance Taxonomy Contract",
        "vertical_id_exact": manifest["vertical_id"] == "finance_insurance_business_finance",
        "references_stage_28d_market_scope": (
            manifest["stage_28d_market_scope_reference"] == "Stage 28D — PickWise Market Scope Expansion"
        ),
        "separate_from_retail_physical_products": "retail_physical_products"
        in set(manifest["separate_from_vertical_ids"]),
        "separate_from_software_saas_erp": "software_saas_erp" in set(manifest["separate_from_vertical_ids"]),
        "not_forced_into_any_retail_engine": set(manifest["not_forced_into_retail_engines"])
        == _REQUIRED_RETAIL_ENGINE_IDS,
        "google_taxonomy_not_main_backbone": manifest["avoids_google_product_taxonomy_backbone"],
        "future_sources_declared_without_live_import": set(manifest["future_source_plans"])
        == {
            "regulated_provider_category_lists",
            "bank_card_loan_insurance_category_references",
            "public_comparison_category_structures",
            "manual_structured_source_lists",
        },
        "all_required_buckets_exist": _REQUIRED_BUCKET_IDS.issubset(bucket_ids),
        "each_bucket_has_product_service_families": all_buckets_have_families,
        "each_bucket_has_finance_fields": all_buckets_have_fields,
        "each_bucket_has_intent_patterns": all_buckets_have_intents,
        "manifest_has_required_intent_patterns": _REQUIRED_INTENTS.issubset(manifest_intent_ids),
        "each_bucket_has_safety_requirements": all_buckets_have_safety_requirements,
        "ranking_dimensions_contract_only_not_implemented": ranking_contract_only,
        "regulated_advice_blocked": manifest["non_goals"]["regulated_financial_advice_logic"],
        "quote_application_blocked": manifest["non_goals"]["quote_or_application_logic"],
        "eligibility_approval_decision_blocked": manifest["non_goals"]["approval_or_eligibility_decision_logic"],
        "no_runtime_dependency_required": not manifest["dependency_boundaries"]["runtime_dependency_required"],
        "no_local_nlu_runtime_dependency_required": not manifest["dependency_boundaries"][
            "local_nlu_runtime_dependency_required"
        ],
        "no_live_api_or_scraping_dependency_required": not manifest["dependency_boundaries"][
            "network_or_external_api_calls_required"
        ],
        "no_checkout_cart_payment_billing_implementation": manifest["non_goals"][
            "checkout_cart_payment_billing"
        ],
        "no_owned_provider_marketplace_inventory": manifest["non_goals"][
            "owned_provider_marketplace_inventory"
        ],
        "all_bucket_source_statuses_present": all(bool(bucket["source_status"]) for bucket in buckets),
        "all_bucket_readiness_statuses_present": all(bool(bucket["readiness_status"]) for bucket in buckets),
    }

    try:
        json.dumps(manifest, sort_keys=True)
    except (TypeError, ValueError):
        result["is_json_serializable"] = False

    result["valid"] = all(result.values())
    result["passed"] = result["valid"]
    return result
