from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .contracts import (
    REQUIRED_STATUSES,
    SaaSERPCategoryBucket,
    SaaSERPFieldDefinition,
    SaaSERPIntentPattern,
    SaaSERPRankingDimension,
    SaaSERPSoftwareFamily,
    SaaSERPTaxonomyManifest,
    SaaSERPVerticalReadiness,
)

_COMMON_FIELDS = (
    SaaSERPFieldDefinition("pricing_model", "Pricing Model", "Commercial structure.", ("subscription", "usage_based", "hybrid", "one_time_license")),
    SaaSERPFieldDefinition("monthly_cost_range", "Monthly Cost Range", "Expected monthly cost interval.", ("free", "under_50", "50_to_200", "200_to_1000", "1000_plus")),
    SaaSERPFieldDefinition("users_or_seats", "Users or Seats", "Seat capacity assumptions.", ("solo", "small_team", "department", "enterprise_multi_team")),
    SaaSERPFieldDefinition("deployment_type", "Deployment Type", "Delivery model.", ("cloud", "on_premise", "hybrid")),
    SaaSERPFieldDefinition("integrations", "Integrations", "Integration requirements.", ("native_integrations", "connector_marketplace", "custom_webhooks", "none")),
    SaaSERPFieldDefinition("support_level", "Support Level", "Support coverage.", ("community", "business_hours", "priority", "dedicated_success_manager")),
    SaaSERPFieldDefinition("api_availability", "API Availability", "API coverage assumptions.", ("none", "limited_api", "full_rest_api", "full_graphql_api")),
    SaaSERPFieldDefinition("security_compliance", "Security and Compliance", "Security and regulatory assurances.", ("basic_controls", "gdpr_ready", "soc2", "iso27001", "industry_specific")),
    SaaSERPFieldDefinition("trial_demo_availability", "Trial or Demo Availability", "Trial or demo availability.", ("none", "self_serve_trial", "sales_demo", "sandbox_environment")),
    SaaSERPFieldDefinition("business_size_fit", "Business Size Fit", "Company size fit.", ("micro", "smb", "mid_market", "enterprise")),
    SaaSERPFieldDefinition("industry_fit", "Industry Fit", "Industry targeting fit.", ("horizontal", "vertical_specific", "regulated_verticals")),
)

_INTENT_PATTERNS = (
    SaaSERPIntentPattern("compare_software", "Compare Software", ("compare crm software", "erp software comparison"), "Compare alternatives by fit."),
    SaaSERPIntentPattern("find_alternative", "Find Alternative", ("alternative to salesforce", "xero alternative for smb"), "Seek substitutes for known vendors."),
    SaaSERPIntentPattern("best_for_small_business", "Best for Small Business", ("best payroll software for small business",), "Find tools suited for small teams."),
    SaaSERPIntentPattern("best_for_industry_workflow", "Best for Industry Workflow", ("best taxi dispatch software", "best fleet management platform"), "Find software by industry use-case."),
    SaaSERPIntentPattern("cheap_free_trial", "Cheap, Free, or Trial", ("free invoicing software", "cheap project management saas"), "Budget and trial intent."),
    SaaSERPIntentPattern("cloud_vs_on_premise", "Cloud vs On-premise", ("on premise erp vs cloud erp",), "Evaluate deployment constraints."),
    SaaSERPIntentPattern("integration_needed", "Integration Needed", ("crm with quickbooks integration", "pos software with api"), "Require stack compatibility."),
    SaaSERPIntentPattern("gdpr_security_compliance_need", "GDPR, Security, Compliance Need", ("gdpr compliant booking software", "soc2 project management tool"), "Need compliance and security assurances."),
)

_RANKING_DIMENSIONS = (
    SaaSERPRankingDimension("workflow_fit", "Workflow Fit", "Match to intended business workflows."),
    SaaSERPRankingDimension("total_cost_clarity", "Total Cost Clarity", "Pricing transparency across seats and usage."),
    SaaSERPRankingDimension("integration_strength", "Integration Strength", "Coverage and reliability of integrations."),
    SaaSERPRankingDimension("deployment_compatibility", "Deployment Compatibility", "Fit with infra and deployment constraints."),
    SaaSERPRankingDimension("vendor_reliability", "Vendor Reliability", "Operational trust and support consistency."),
    SaaSERPRankingDimension("security_compliance_fit", "Security and Compliance Fit", "Alignment with security/compliance needs."),
)


def _bucket(
    bucket_id: str,
    display_name: str,
    description: str,
    families: tuple[SaaSERPSoftwareFamily, ...],
    sizes: tuple[str, ...],
    intent_ids: tuple[int, ...],
    readiness_status: str,
) -> SaaSERPCategoryBucket:
    return SaaSERPCategoryBucket(
        bucket_id=bucket_id,
        display_name=display_name,
        description=description,
        example_software_families=families,
        relevant_business_sizes=sizes,
        intent_examples=tuple(_INTENT_PATTERNS[i] for i in intent_ids),
        field_definitions=_COMMON_FIELDS,
        ranking_dimensions=_RANKING_DIMENSIONS,
        source_status="planned_source_import",
        readiness_status=readiness_status,
    )


_BUCKETS = (
    _bucket(
        "erp_business_management",
        "ERP / Business Management",
        "Core ERP suites for finance and operations.",
        (
            SaaSERPSoftwareFamily("erp_core_suites", "ERP Core Suites", "Unified resource planning suites."),
            SaaSERPSoftwareFamily("operations_management", "Operations Management", "Operations planning and execution systems."),
        ),
        ("smb", "mid_market", "enterprise"),
        (0, 2, 5, 7),
        "contract_defined",
    ),
    _bucket(
        "crm_sales_marketing",
        "CRM / Sales / Marketing",
        "Lead management, CRM, and marketing automation software.",
        (
            SaaSERPSoftwareFamily("crm_platforms", "CRM Platforms", "Customer lifecycle and pipeline tooling."),
            SaaSERPSoftwareFamily("marketing_automation", "Marketing Automation", "Campaign and nurture orchestration."),
        ),
        ("micro", "smb", "mid_market", "enterprise"),
        (0, 1, 2, 6),
        "contract_defined",
    ),
    _bucket(
        "accounting_invoicing_payroll",
        "Accounting / Invoicing / Payroll",
        "Bookkeeping, invoicing, payroll, and financial ops software.",
        (
            SaaSERPSoftwareFamily("accounting_software", "Accounting Software", "General ledger and reporting products."),
            SaaSERPSoftwareFamily("payroll_systems", "Payroll Systems", "Salary and tax workflow software."),
        ),
        ("micro", "smb", "mid_market"),
        (0, 2, 4, 7),
        "needs_taxonomy_expansion",
    ),
    _bucket(
        "hr_workforce_scheduling",
        "HR / Workforce / Scheduling",
        "HRIS and workforce scheduling systems.",
        (
            SaaSERPSoftwareFamily("hris_platforms", "HRIS Platforms", "HR records and onboarding workflows."),
            SaaSERPSoftwareFamily("workforce_scheduling", "Workforce Scheduling", "Shift and attendance management."),
        ),
        ("smb", "mid_market", "enterprise"),
        (0, 2, 4, 6),
        "needs_taxonomy_expansion",
    ),
    _bucket(
        "project_management_collaboration",
        "Project Management / Collaboration",
        "Task planning and team collaboration software.",
        (
            SaaSERPSoftwareFamily("project_management_tools", "Project Management Tools", "Task planning and delivery tracking."),
            SaaSERPSoftwareFamily("team_collaboration_suites", "Team Collaboration Suites", "Team communication and collaboration hubs."),
        ),
        ("micro", "smb", "mid_market", "enterprise"),
        (0, 1, 4, 6),
        "contract_defined",
    ),
    _bucket(
        "ecommerce_booking_pos_software",
        "E-commerce / Booking / POS Software",
        "E-commerce enablement, booking systems, and POS operations software.",
        (
            SaaSERPSoftwareFamily("ecommerce_platform_software", "E-commerce Platform Software", "Catalog and order workflow software."),
            SaaSERPSoftwareFamily("booking_and_pos_systems", "Booking and POS Systems", "Appointment and point-of-sale management."),
        ),
        ("smb", "mid_market", "enterprise"),
        (0, 2, 3, 6),
        "needs_taxonomy_expansion",
    ),
    _bucket(
        "cybersecurity_cloud_hosting",
        "Cybersecurity / Cloud / Hosting",
        "Security operations, cloud ops, and hosting management software.",
        (
            SaaSERPSoftwareFamily("security_platforms", "Security Platforms", "Threat protection and monitoring products."),
            SaaSERPSoftwareFamily("cloud_hosting_management", "Cloud Hosting Management", "Cloud deployment and hosting software."),
        ),
        ("smb", "mid_market", "enterprise"),
        (0, 5, 6, 7),
        "blocked_until_future_stage",
    ),
    _bucket(
        "industry_specific_software",
        "Industry-specific Software",
        "Vertical workflow software for distinct industries.",
        (
            SaaSERPSoftwareFamily("taxi_dispatch", "Taxi Dispatch", "Ride assignment and dispatch systems."),
            SaaSERPSoftwareFamily("fleet_management", "Fleet Management", "Fleet routing and maintenance systems."),
            SaaSERPSoftwareFamily("restaurant_systems", "Restaurant Systems", "Restaurant POS and ordering systems."),
            SaaSERPSoftwareFamily("hotel_property_management", "Hotel and Property Management", "Hospitality and property operations systems."),
            SaaSERPSoftwareFamily("field_service", "Field Service", "Work-order and field scheduling systems."),
            SaaSERPSoftwareFamily("warehouse_wms", "Warehouse and WMS", "Warehouse management systems."),
            SaaSERPSoftwareFamily("retail_pos", "Retail POS", "Point-of-sale operations software."),
            SaaSERPSoftwareFamily("service_booking_systems", "Service Booking Systems", "Booking and appointment software."),
            SaaSERPSoftwareFamily("ai_tools_automation_tools", "AI and Automation Tools", "AI-assisted and automation workflow software."),
        ),
        ("micro", "smb", "mid_market", "enterprise"),
        (0, 2, 3, 4),
        "needs_taxonomy_expansion",
    ),
)

_VERTICAL_READINESS = SaaSERPVerticalReadiness(
    vertical_id="software_saas_erp",
    current_status="contract_defined",
    readiness_reason="Taxonomy contract is defined; scoring and ingestion are future-stage responsibilities.",
    next_stage_dependency="blocked_until_future_stage",
)

_MANIFEST_OBJECT = SaaSERPTaxonomyManifest(
    stage_id="28E",
    stage_title="Stage 28E — SaaS / ERP Taxonomy Contract",
    vertical_id="software_saas_erp",
    stage_28d_market_scope_reference="Stage 28D — PickWise Market Scope Expansion",
    separate_from_vertical_id="retail_physical_products",
    not_forced_into_retail_engine="tech_electronics_office",
    avoids_google_product_taxonomy_backbone=True,
    future_source_plans=(
        "saas_category_lists",
        "software_directories",
        "erp_crm_pos_category_references",
        "manual_structured_source_lists",
    ),
    category_buckets=_BUCKETS,
    intent_patterns=_INTENT_PATTERNS,
    ranking_dimensions=_RANKING_DIMENSIONS,
    status_catalog=REQUIRED_STATUSES,
    dependency_boundaries={
        "runtime_dependency_required": False,
        "local_nlu_runtime_dependency_required": False,
        "network_or_external_api_calls_required": False,
    },
    non_goals={
        "ranking_implementation": True,
        "external_saas_offers_or_affiliate_logic": True,
        "app_router_search_runtime_changes": True,
        "local_nlu_runtime_changes": True,
        "stage_28f_work": True,
        "stage_29a_work": True,
        "live_scraping_or_live_api_ingestion": True,
        "checkout_cart_payment_subscription_billing": True,
        "owned_marketplace_inventory_storage": True,
    },
    vertical_readiness=_VERTICAL_READINESS,
)

_MANIFEST = asdict(_MANIFEST_OBJECT)


def get_saas_erp_taxonomy_manifest() -> dict:
    """Return deterministic Stage 28E SaaS / ERP taxonomy contract manifest."""
    return deepcopy(_MANIFEST)

