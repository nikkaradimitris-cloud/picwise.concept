from __future__ import annotations

import json

from .manifest import get_saas_erp_taxonomy_manifest

_REQUIRED_BUCKET_IDS = {
    "erp_business_management",
    "crm_sales_marketing",
    "accounting_invoicing_payroll",
    "hr_workforce_scheduling",
    "project_management_collaboration",
    "ecommerce_booking_pos_software",
    "cybersecurity_cloud_hosting",
    "industry_specific_software",
}

_REQUIRED_FIELDS = {
    "pricing_model",
    "monthly_cost_range",
    "users_or_seats",
    "deployment_type",
    "integrations",
    "support_level",
    "api_availability",
    "security_compliance",
    "trial_demo_availability",
    "business_size_fit",
    "industry_fit",
}


def validate_saas_erp_taxonomy_manifest() -> dict:
    """Validate Stage 28E contract structure and strict boundaries."""
    manifest = get_saas_erp_taxonomy_manifest()
    buckets = manifest["category_buckets"]
    bucket_ids = {bucket["bucket_id"] for bucket in buckets}

    all_buckets_have_families = all(bucket["example_software_families"] for bucket in buckets)
    all_buckets_have_intents = all(bucket["intent_examples"] for bucket in buckets)
    all_buckets_have_required_fields = all(
        _REQUIRED_FIELDS.issubset({field["field_id"] for field in bucket["field_definitions"]})
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
        "stage_title_exact": manifest["stage_title"] == "Stage 28E — SaaS / ERP Taxonomy Contract",
        "vertical_id_is_software_saas_erp": manifest["vertical_id"] == "software_saas_erp",
        "separate_from_retail_physical_products": (
            manifest["separate_from_vertical_id"] == "retail_physical_products"
        ),
        "not_forced_into_tech_electronics_office": (
            manifest["not_forced_into_retail_engine"] == "tech_electronics_office"
        ),
        "google_taxonomy_not_main_backbone": manifest["avoids_google_product_taxonomy_backbone"],
        "all_required_buckets_exist": _REQUIRED_BUCKET_IDS.issubset(bucket_ids),
        "each_bucket_has_software_families": all_buckets_have_families,
        "each_bucket_has_software_specific_fields": all_buckets_have_required_fields,
        "each_bucket_has_intent_patterns": all_buckets_have_intents,
        "ranking_is_contract_only_not_implemented": ranking_contract_only,
        "no_runtime_dependency_required": not manifest["dependency_boundaries"][
            "runtime_dependency_required"
        ],
        "no_local_nlu_runtime_dependency_required": not manifest["dependency_boundaries"][
            "local_nlu_runtime_dependency_required"
        ],
        "no_live_api_or_scraping_dependency_required": not manifest["dependency_boundaries"][
            "network_or_external_api_calls_required"
        ],
        "no_checkout_cart_payment_subscription_billing_implementation": manifest["non_goals"][
            "checkout_cart_payment_subscription_billing"
        ],
        "no_owned_marketplace_inventory": manifest["non_goals"][
            "owned_marketplace_inventory_storage"
        ],
    }

    try:
        json.dumps(manifest, sort_keys=True)
    except (TypeError, ValueError):
        result["is_json_serializable"] = False

    result["valid"] = (
        result["is_json_serializable"]
        and result["stage_title_exact"]
        and result["vertical_id_is_software_saas_erp"]
        and result["separate_from_retail_physical_products"]
        and result["not_forced_into_tech_electronics_office"]
        and result["google_taxonomy_not_main_backbone"]
        and result["all_required_buckets_exist"]
        and result["each_bucket_has_software_families"]
        and result["each_bucket_has_software_specific_fields"]
        and result["each_bucket_has_intent_patterns"]
        and result["ranking_is_contract_only_not_implemented"]
        and result["no_runtime_dependency_required"]
        and result["no_local_nlu_runtime_dependency_required"]
        and result["no_live_api_or_scraping_dependency_required"]
        and result["no_checkout_cart_payment_subscription_billing_implementation"]
        and result["no_owned_marketplace_inventory"]
    )
    result["passed"] = result["valid"]
    return result

