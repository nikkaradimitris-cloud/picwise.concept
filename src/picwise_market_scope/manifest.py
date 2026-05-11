from __future__ import annotations

import json
from copy import deepcopy

_VERTICALS = {
    "retail_physical_products": {
        "vertical_id": "retail_physical_products",
        "scope_type": "physical_goods_discovery",
        "taxonomy_contract": "google_product_taxonomy_backbone",
        "ranking_dimensions": [
            "product_relevance",
            "spec_match_quality",
            "merchant_trust_signals",
            "price_value_alignment",
            "availability_freshness",
        ],
        "uses_existing_pickwise_6_engines": True,
        "notes": (
            "Current PickWise six engines represent retail hypermarket domains only. "
            "The 18 buckets are category and subcategory partitions under those six "
            "retail engines, not 18 independent market verticals."
        ),
    },
    "software_saas_erp": {
        "vertical_id": "software_saas_erp",
        "scope_type": "software_service_discovery",
        "taxonomy_contract": "saas_erp_domain_contract_required",
        "ranking_dimensions": [
            "feature_fit",
            "integration_compatibility",
            "deployment_model_fit",
            "pricing_model_transparency",
            "vendor_reliability",
        ],
        "must_not_be_forced_into_retail_tech_electronics_office": True,
        "notes": (
            "SaaS and ERP search intent is contractual and workflow-oriented. "
            "It must remain a separate vertical and cannot be collapsed into "
            "retail Tech/Electronics/Office category logic."
        ),
    },
    "finance_insurance_business_finance": {
        "vertical_id": "finance_insurance_business_finance",
        "scope_type": "financial_product_service_discovery",
        "taxonomy_contract": "finance_insurance_domain_contract_required",
        "ranking_dimensions": [
            "eligibility_fit",
            "risk_profile_alignment",
            "regulatory_clarity",
            "fee_transparency",
            "institution_reliability",
        ],
        "must_not_be_forced_into_retail": True,
        "notes": (
            "Finance and insurance intent uses eligibility, regulatory, and risk "
            "constraints. It must stay separate from retail taxonomy structures."
        ),
    },
}

_MANIFEST = {
    "stage_id": "28D",
    "stage_name": "pickwise_market_scope_expansion",
    "purpose": "Declare market-scope vertical contract boundaries only",
    "verticals": _VERTICALS,
    "clarifications": {
        "existing_6_engines_are_retail_hypermarkets_only": True,
        "existing_18_buckets_are_category_subcategory_under_6_retail_engines": True,
        "existing_18_buckets_are_not_18_independent_hypermarkets": True,
        "google_taxonomy_is_deep_backbone_for_physical_retail_products": True,
        "saas_erp_is_separate_from_retail_tech_electronics_office": True,
        "finance_insurance_is_separate_from_retail": True,
        "each_vertical_requires_distinct_taxonomy_contract": True,
        "each_vertical_requires_distinct_ranking_dimensions": True,
    },
    "non_goals": {
        "app_router_runtime_changes": True,
        "search_runtime_changes": True,
        "local_nlu_runtime_changes": True,
        "stage_28e_work": True,
        "stage_28f_work": True,
        "stage_29a_work": True,
        "external_scraping_or_api_live_calls": True,
        "owned_inventory_checkout_cart_warehouse_marketplace_logic": True,
    },
}


def get_market_scope_manifest() -> dict:
    """Return deterministic Stage 28D market scope manifest."""
    return deepcopy(_MANIFEST)


def validate_market_scope_manifest() -> dict:
    """Validate Stage 28D market scope coverage and strict boundaries."""
    manifest = get_market_scope_manifest()
    verticals = manifest["verticals"]
    retail_vertical = verticals["retail_physical_products"]
    saas_vertical = verticals["software_saas_erp"]
    finance_vertical = verticals["finance_insurance_business_finance"]

    expected_vertical_keys = sorted(
        [
            "retail_physical_products",
            "software_saas_erp",
            "finance_insurance_business_finance",
        ]
    )

    result = {
        "passed": True,
        "valid": True,
        "is_json_serializable": True,
        "stage_id_is_28d": manifest["stage_id"] == "28D",
        "has_exact_three_required_verticals": sorted(verticals.keys()) == expected_vertical_keys,
        "retail_vertical_uses_google_product_taxonomy_backbone": (
            retail_vertical["taxonomy_contract"] == "google_product_taxonomy_backbone"
        ),
        "retail_vertical_explicitly_scoped_to_existing_6_engines": retail_vertical[
            "uses_existing_pickwise_6_engines"
        ],
        "saas_vertical_is_not_forced_into_retail_tech_electronics_office": saas_vertical[
            "must_not_be_forced_into_retail_tech_electronics_office"
        ],
        "finance_vertical_is_not_forced_into_retail": finance_vertical[
            "must_not_be_forced_into_retail"
        ],
        "all_verticals_have_taxonomy_contract": all(
            bool(payload.get("taxonomy_contract")) for payload in verticals.values()
        ),
        "all_verticals_have_distinct_taxonomy_contracts": len(
            {payload["taxonomy_contract"] for payload in verticals.values()}
        )
        == 3,
        "all_verticals_have_ranking_dimensions": all(
            bool(payload.get("ranking_dimensions")) for payload in verticals.values()
        ),
        "all_verticals_have_distinct_ranking_dimensions": len(
            {tuple(payload["ranking_dimensions"]) for payload in verticals.values()}
        )
        == 3,
        "clarification_flags_all_true": all(manifest["clarifications"].values()),
        "non_goal_flags_all_true": all(manifest["non_goals"].values()),
    }

    try:
        json.dumps(manifest, sort_keys=True)
    except (TypeError, ValueError):
        result["is_json_serializable"] = False

    result["valid"] = (
        result["is_json_serializable"]
        and result["stage_id_is_28d"]
        and result["has_exact_three_required_verticals"]
        and result["retail_vertical_uses_google_product_taxonomy_backbone"]
        and result["retail_vertical_explicitly_scoped_to_existing_6_engines"]
        and result["saas_vertical_is_not_forced_into_retail_tech_electronics_office"]
        and result["finance_vertical_is_not_forced_into_retail"]
        and result["all_verticals_have_taxonomy_contract"]
        and result["all_verticals_have_distinct_taxonomy_contracts"]
        and result["all_verticals_have_ranking_dimensions"]
        and result["all_verticals_have_distinct_ranking_dimensions"]
        and result["clarification_flags_all_true"]
        and result["non_goal_flags_all_true"]
    )
    result["passed"] = result["valid"]
    return result
