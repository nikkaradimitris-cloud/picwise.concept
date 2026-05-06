from __future__ import annotations

from enum import Enum


class MissingDataState(str, Enum):
    NOT_CONNECTED = "not_connected"
    DATA_NOT_YET = "data_not_yet"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ProductBrain(str, Enum):
    TECH_SPECS_ELECTRONICS = "tech_specs_electronics"
    SOFTWARE_PROGRAMS_SAAS = "software_programs_saas"
    PHYSICAL_PRODUCTS_HOME_MACHINES = "physical_products_home_machines"
    FINANCIAL_UTILITY_CONTRACT_PRODUCTS = "financial_utility_contract_products"
    HIGH_TRUST_RISK_SENSITIVE_DECISIONS = "high_trust_risk_sensitive_decisions"


class DecisionDepth(str, Enum):
    FAST_DECISION = "fast_decision"
    CONSIDERED_PURCHASE = "considered_purchase"
    HIGH_STAKES_HIGH_TRUST = "high_stakes_high_trust"


class ProductChoiceRole(str, Enum):
    BUDGET = "budget"
    VALUE = "value"
    BEST_OVERALL = "best_overall"
    PREMIUM = "premium"

    SAFE_BUDGET = "safe_budget"
    BEST_SAFETY = "best_safety"
    BEST_COMFORT = "best_comfort"
    PREMIUM_ISOFIX = "premium_isofix"
    BASIC = "basic"
    BEST_FOR_SMALL_BUSINESS = "best_for_small_business"
    LOWEST_MONTHLY_COST = "lowest_monthly_cost"
    STABLE_PRICE = "stable_price"
    FLEXIBLE_PLAN = "flexible_plan"


class TrackingEventType(str, Enum):
    PAGE_IMPRESSION = "page_impression"
    QUERY_SERVED = "query_served"
    CARDS_SHOWN = "cards_shown"
    RECOMMENDED_SHOWN = "recommended_shown"
    CTA_CLICK = "cta_click"
    RECOMMENDED_CLICK = "recommended_click"
    NON_RECOMMENDED_CLICK = "non_recommended_click"
    MORE_CLICK = "more_click"
    REDIRECT_ATTEMPT = "redirect_attempt"
    REDIRECT_SUCCESS = "redirect_success"
    REDIRECT_FAILURE = "redirect_failure"
