from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .contracts import (
    REQUIRED_SAFETY_STATUSES,
    REQUIRED_STATUSES,
    FinanceInsuranceCategoryBucket,
    FinanceInsuranceFieldDefinition,
    FinanceInsuranceIntentPattern,
    FinanceInsuranceProductFamily,
    FinanceInsuranceRankingDimension,
    FinanceInsuranceSafetyRequirement,
    FinanceInsuranceTaxonomyManifest,
    FinanceInsuranceVerticalReadiness,
)

_COMMON_FIELDS = (
    FinanceInsuranceFieldDefinition(
        "fees",
        "Fees",
        "Fee structure and recurring or one-time fee expectations.",
        ("none", "flat_fee", "percentage_fee", "mixed_fee", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "interest_rate_type",
        "Interest Rate Type",
        "Whether the product uses fixed, variable, or mixed rates where relevant.",
        ("not_applicable", "fixed", "variable", "mixed", "promotional_then_variable"),
    ),
    FinanceInsuranceFieldDefinition(
        "apr_apy_markers",
        "APR/APY Markers",
        "APR/APY disclosure markers where products require rate transparency.",
        ("not_applicable", "apr_disclosed", "apy_disclosed", "both_disclosed", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "eligibility_requirements",
        "Eligibility Requirements",
        "Contract-level eligibility constraints for category-level matching.",
        ("age", "residency", "income", "business_registration", "credit_profile", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "term_length",
        "Term Length",
        "Contract term horizon where applicable.",
        ("on_demand", "monthly", "annual", "multi_year", "custom_term", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "coverage_type",
        "Coverage Type",
        "Coverage type for protection and insurance categories.",
        ("not_applicable", "liability", "comprehensive", "health", "life", "business", "mixed"),
    ),
    FinanceInsuranceFieldDefinition(
        "deductible_excess",
        "Deductible / Excess",
        "Deductible or excess obligations when policy contracts include them.",
        ("not_applicable", "zero", "low", "medium", "high", "custom", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "risk_level",
        "Risk Level",
        "Risk profile needed for advisory-safe ranking contracts.",
        ("low", "moderate", "high", "speculative", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "country_availability",
        "Country Availability",
        "Country and jurisdiction availability constraints.",
        ("single_country", "multi_country_region", "global", "restricted", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "provider_trust",
        "Provider Trust",
        "Provider reliability and trust marker at contract level.",
        ("regulated_entity", "licensed_partner", "verified_provider", "unknown"),
    ),
    FinanceInsuranceFieldDefinition(
        "regulatory_disclaimer_required",
        "Regulatory Disclaimer Required",
        "Whether regulated disclaimers are mandatory.",
        ("yes", "no", "depends_on_jurisdiction"),
    ),
    FinanceInsuranceFieldDefinition(
        "manual_review_required",
        "Manual Review Required",
        "Whether manual review is required before any sensitive output.",
        ("yes", "no", "conditional"),
    ),
)

_INTENT_PATTERNS = (
    FinanceInsuranceIntentPattern(
        "compare_cards",
        "Compare Cards",
        ("compare cashback cards", "best travel card comparison"),
        "User wants side-by-side card comparison without application actions.",
    ),
    FinanceInsuranceIntentPattern(
        "compare_loans",
        "Compare Loans",
        ("compare personal loans", "loan options for small business"),
        "User seeks comparative loan options and terms only.",
    ),
    FinanceInsuranceIntentPattern(
        "compare_insurance",
        "Compare Insurance",
        ("compare home insurance", "insurance plans comparison"),
        "User seeks policy comparison without quote submission.",
    ),
    FinanceInsuranceIntentPattern(
        "low_fee_account",
        "Low-fee Account",
        ("low fee business bank account", "account with minimal monthly fee"),
        "Fee-sensitive account discovery intent.",
    ),
    FinanceInsuranceIntentPattern(
        "business_pos_payment_provider",
        "Business POS / Payment Provider",
        ("best POS payment provider for cafe", "merchant services comparison"),
        "Business payment acceptance provider comparison intent.",
    ),
    FinanceInsuranceIntentPattern(
        "small_business_finance",
        "Small Business Finance",
        ("small business financing options", "working capital financing comparison"),
        "SMB-oriented financing and support exploration intent.",
    ),
    FinanceInsuranceIntentPattern(
        "car_insurance",
        "Car Insurance",
        ("best car insurance coverage", "compare car insurance deductible"),
        "Motor insurance coverage comparison intent.",
    ),
    FinanceInsuranceIntentPattern(
        "health_insurance",
        "Health Insurance",
        ("health insurance policy comparison", "family health insurance plans"),
        "Health protection comparison and understanding intent.",
    ),
    FinanceInsuranceIntentPattern(
        "mortgage_comparison",
        "Mortgage Comparison",
        ("mortgage comparison fixed vs variable", "first home mortgage options"),
        "Mortgage comparison intent without advice or approval decisions.",
    ),
    FinanceInsuranceIntentPattern(
        "investment_platform_comparison",
        "Investment Platform Comparison",
        ("compare investment trading platforms", "low fee trading platform"),
        "Platform and feature comparison for self-directed investing.",
    ),
    FinanceInsuranceIntentPattern(
        "eligibility_question",
        "Eligibility Question",
        ("am I eligible for this card category", "loan eligibility requirements"),
        "User asks eligibility questions; contract stays informational only.",
    ),
    FinanceInsuranceIntentPattern(
        "risk_safety_question",
        "Risk / Safety Question",
        ("is this investment platform risky", "insurance coverage risk level"),
        "User asks about risk and safety framing.",
    ),
)

_RANKING_DIMENSIONS = (
    FinanceInsuranceRankingDimension(
        "fee_transparency",
        "Fee Transparency",
        "Visibility and comparability of all fee components.",
    ),
    FinanceInsuranceRankingDimension(
        "rate_clarity",
        "Rate Clarity",
        "APR/APY or interest-rate disclosure clarity.",
    ),
    FinanceInsuranceRankingDimension(
        "eligibility_clarity",
        "Eligibility Clarity",
        "Clarity of non-decision eligibility requirements.",
    ),
    FinanceInsuranceRankingDimension(
        "coverage_fit",
        "Coverage Fit",
        "Coverage suitability to declared protection needs.",
    ),
    FinanceInsuranceRankingDimension(
        "risk_alignment",
        "Risk Alignment",
        "Alignment with user-declared risk tolerance bands.",
    ),
    FinanceInsuranceRankingDimension(
        "provider_trustworthiness",
        "Provider Trustworthiness",
        "Provider trust, licensing, and disclosure quality signals.",
    ),
    FinanceInsuranceRankingDimension(
        "jurisdiction_fit",
        "Jurisdiction Fit",
        "Country availability and jurisdiction fit for category visibility.",
    ),
)

_SAFETY_REQUIREMENTS = (
    FinanceInsuranceSafetyRequirement(
        "comparison_allowed",
        "Comparison Allowed",
        "Comparison and educational content is allowed at taxonomy contract level.",
        "comparison_allowed",
    ),
    FinanceInsuranceSafetyRequirement(
        "review_required",
        "Review Required",
        "Sensitive financial/insurance surfaces require manual review gating.",
        "review_required",
    ),
    FinanceInsuranceSafetyRequirement(
        "regulated_advice_blocked",
        "Regulated Advice Blocked",
        "Regulated financial advice output is blocked in this stage.",
        "regulated_advice_blocked",
    ),
    FinanceInsuranceSafetyRequirement(
        "quote_application_blocked",
        "Quote / Application Blocked",
        "Quote flows and application flows are blocked in this stage.",
        "quote_application_blocked",
    ),
    FinanceInsuranceSafetyRequirement(
        "eligibility_decision_blocked",
        "Eligibility Decision Blocked",
        "Eligibility and approval decisions are blocked in this stage.",
        "eligibility_decision_blocked",
    ),
)


def _bucket(
    bucket_id: str,
    display_name: str,
    description: str,
    families: tuple[FinanceInsuranceProductFamily, ...],
    profiles: tuple[str, ...],
    intent_ids: tuple[int, ...],
    readiness_status: str,
) -> FinanceInsuranceCategoryBucket:
    return FinanceInsuranceCategoryBucket(
        bucket_id=bucket_id,
        display_name=display_name,
        description=description,
        example_product_service_families=families,
        relevant_user_business_profiles=profiles,
        intent_examples=tuple(_INTENT_PATTERNS[i] for i in intent_ids),
        field_definitions=_COMMON_FIELDS,
        ranking_dimensions=_RANKING_DIMENSIONS,
        safety_requirements=_SAFETY_REQUIREMENTS,
        source_status="planned_source_import",
        readiness_status=readiness_status,
    )


_BUCKETS = (
    _bucket(
        "banking_accounts_cards",
        "Banking / Accounts / Cards",
        "Consumer and business banking accounts, payment cards, and account bundles.",
        (
            FinanceInsuranceProductFamily("checking_accounts", "Checking Accounts", "Day-to-day banking accounts."),
            FinanceInsuranceProductFamily("savings_accounts", "Savings Accounts", "Interest-bearing deposit accounts."),
            FinanceInsuranceProductFamily("credit_cards", "Credit Cards", "Consumer and business credit card products."),
            FinanceInsuranceProductFamily("debit_prepaid_cards", "Debit / Prepaid Cards", "Debit and prepaid card products."),
        ),
        ("individual_consumer", "student", "freelancer", "small_business_owner"),
        (0, 3, 10, 11),
        "contract_defined",
    ),
    _bucket(
        "loans_mortgages_leasing",
        "Loans / Mortgages / Leasing",
        "Financing products including personal loans, business loans, mortgages, and leasing.",
        (
            FinanceInsuranceProductFamily("personal_loans", "Personal Loans", "General-purpose unsecured lending."),
            FinanceInsuranceProductFamily("business_loans", "Business Loans", "Business term loan facilities."),
            FinanceInsuranceProductFamily("mortgages", "Mortgages", "Residential and commercial mortgage products."),
            FinanceInsuranceProductFamily("asset_leasing", "Asset Leasing", "Leasing for vehicles or equipment."),
        ),
        ("individual_consumer", "first_time_buyer", "small_business_owner", "enterprise_finance_team"),
        (1, 8, 10, 11),
        "needs_taxonomy_expansion",
    ),
    _bucket(
        "insurance_protection",
        "Insurance / Protection",
        "Protection products across auto, health, home, life, and business risk lines.",
        (
            FinanceInsuranceProductFamily("car_insurance", "Car Insurance", "Auto liability and comprehensive policies."),
            FinanceInsuranceProductFamily("health_insurance", "Health Insurance", "Individual and family health policies."),
            FinanceInsuranceProductFamily("property_insurance", "Property Insurance", "Home and property protection products."),
            FinanceInsuranceProductFamily("business_insurance", "Business Insurance", "Business liability and interruption coverage."),
        ),
        ("individual_consumer", "family_household", "small_business_owner", "risk_manager"),
        (2, 6, 7, 11),
        "contract_defined",
    ),
    _bucket(
        "payments_pos_merchant_services",
        "Payments / POS / Merchant Services",
        "Merchant acceptance, POS processing, and payment service providers.",
        (
            FinanceInsuranceProductFamily("merchant_accounts", "Merchant Accounts", "Card acceptance account products."),
            FinanceInsuranceProductFamily("payment_gateways", "Payment Gateways", "Gateway and transaction routing services."),
            FinanceInsuranceProductFamily("point_of_sale", "Point of Sale", "POS acceptance and settlement software services."),
            FinanceInsuranceProductFamily("cross_border_payments", "Cross-border Payments", "International settlement solutions."),
        ),
        ("small_business_owner", "merchant_operator", "ecommerce_operator", "finance_operations_team"),
        (4, 5, 10, 11),
        "contract_defined",
    ),
    _bucket(
        "investing_trading_platforms",
        "Investing / Trading Platforms",
        "Investment and trading access platforms for retail and business users.",
        (
            FinanceInsuranceProductFamily("brokerage_platforms", "Brokerage Platforms", "Brokerage execution and custody platforms."),
            FinanceInsuranceProductFamily("robo_advisor_platforms", "Robo-advisor Platforms", "Automated portfolio management services."),
            FinanceInsuranceProductFamily("retirement_investing", "Retirement Investing", "Retirement-focused investment accounts."),
            FinanceInsuranceProductFamily("education_sandboxes", "Education Sandboxes", "Paper trading and simulation environments."),
        ),
        ("individual_consumer", "active_trader", "long_term_investor", "small_business_treasury"),
        (9, 11, 10, 2),
        "needs_taxonomy_expansion",
    ),
    _bucket(
        "business_finance_accounting_tools",
        "Business Finance / Accounting Finance Tools",
        "Business cashflow, treasury, accounting finance, and spend control tooling.",
        (
            FinanceInsuranceProductFamily("cashflow_management", "Cashflow Management", "Cashflow forecasting and liquidity tooling."),
            FinanceInsuranceProductFamily("expense_management", "Expense Management", "Spend controls and reimbursement services."),
            FinanceInsuranceProductFamily("invoice_finance", "Invoice Finance", "Factoring and invoice-backed financing services."),
            FinanceInsuranceProductFamily("treasury_tools", "Treasury Tools", "Working capital and treasury optimization tools."),
        ),
        ("small_business_owner", "cfo_office", "finance_operations_team", "enterprise_procurement"),
        (5, 4, 1, 10),
        "contract_defined",
    ),
    _bucket(
        "tax_legal_compliance_finance_support",
        "Tax / Legal / Compliance Finance Support",
        "Tax, legal, and compliance support services related to finance operations.",
        (
            FinanceInsuranceProductFamily("tax_preparation_support", "Tax Preparation Support", "Tax filing support categories."),
            FinanceInsuranceProductFamily("regulatory_compliance_tools", "Regulatory Compliance Tools", "Compliance monitoring support."),
            FinanceInsuranceProductFamily("legal_document_support", "Legal Document Support", "Contract and legal document support."),
            FinanceInsuranceProductFamily("audit_readiness_support", "Audit Readiness Support", "Audit prep and record readiness support."),
        ),
        ("small_business_owner", "compliance_officer", "legal_operations", "finance_operations_team"),
        (10, 11, 2, 5),
        "planned_source_import",
    ),
    _bucket(
        "financial_education_comparison",
        "Financial Education / Comparison / Advisory-safe Content",
        "Educational and comparison-focused financial content without regulated advice actions.",
        (
            FinanceInsuranceProductFamily("financial_guides", "Financial Guides", "Educational guides and explainers."),
            FinanceInsuranceProductFamily("comparison_tables", "Comparison Tables", "Structured feature comparison tables."),
            FinanceInsuranceProductFamily("risk_literacy_content", "Risk Literacy Content", "Risk literacy and safety explainers."),
            FinanceInsuranceProductFamily("glossary_resources", "Glossary Resources", "Financial terminology resources."),
        ),
        ("new_to_finance_user", "individual_consumer", "small_business_owner", "student"),
        (2, 8, 9, 11),
        "contract_defined",
    ),
)

_VERTICAL_READINESS = FinanceInsuranceVerticalReadiness(
    vertical_id="finance_insurance_business_finance",
    current_status="contract_defined",
    readiness_reason=(
        "Taxonomy contract is defined for finance/insurance/business finance; "
        "source imports and scoring stay blocked for later stages."
    ),
    next_stage_dependency="blocked_until_future_stage",
)

_MANIFEST_OBJECT = FinanceInsuranceTaxonomyManifest(
    stage_id="28F",
    stage_title="Stage 28F — Finance / Insurance Taxonomy Contract",
    vertical_id="finance_insurance_business_finance",
    stage_28d_market_scope_reference="Stage 28D — PickWise Market Scope Expansion",
    separate_from_vertical_ids=("retail_physical_products", "software_saas_erp"),
    not_forced_into_retail_engines=(
        "home_living_appliances_engine",
        "tech_electronics_office_engine",
        "auto_moto_mobility_engine",
        "tools_diy_garden_repair_engine",
        "health_beauty_family_lifestyle_engine",
        "fashion_footwear_jewelry_accessories_engine",
    ),
    avoids_google_product_taxonomy_backbone=True,
    future_source_plans=(
        "regulated_provider_category_lists",
        "bank_card_loan_insurance_category_references",
        "public_comparison_category_structures",
        "manual_structured_source_lists",
    ),
    category_buckets=_BUCKETS,
    intent_patterns=_INTENT_PATTERNS,
    ranking_dimensions=_RANKING_DIMENSIONS,
    safety_status_catalog=REQUIRED_SAFETY_STATUSES,
    status_catalog=REQUIRED_STATUSES,
    dependency_boundaries={
        "runtime_dependency_required": False,
        "local_nlu_runtime_dependency_required": False,
        "network_or_external_api_calls_required": False,
    },
    non_goals={
        "ranking_implementation": True,
        "finance_or_saas_ranking_implementation": True,
        "regulated_financial_advice_logic": True,
        "quote_or_application_logic": True,
        "approval_or_eligibility_decision_logic": True,
        "app_router_search_runtime_changes": True,
        "local_nlu_runtime_changes": True,
        "stage_29a_massive_multilingual_noisy_query_generator": True,
        "live_scraping_or_live_api_ingestion": True,
        "checkout_cart_payment_billing": True,
        "owned_provider_marketplace_inventory": True,
    },
    vertical_readiness=_VERTICAL_READINESS,
)

_MANIFEST = asdict(_MANIFEST_OBJECT)


def get_finance_insurance_taxonomy_manifest() -> dict:
    """Return deterministic Stage 28F finance/insurance taxonomy contract manifest."""
    return deepcopy(_MANIFEST)
