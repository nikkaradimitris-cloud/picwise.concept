from __future__ import annotations

from .awin_adapter import load_awin_provider_feed
from .contracts import (
    AVAILABILITY_STATES,
    PROVIDER_ELIGIBILITY_STATUSES,
    PROVIDER_FEED_STATUSES,
    FeedAvailabilityContext,
    OfferHealth,
    ProductEligibility,
    ProviderEligibilityResult,
    ProviderFeedConfig,
    ProviderFeedStatus,
    ProviderGraphProjectionResult,
    ProviderParseResult,
    ProviderProduct,
    PurchasabilityVerification,
    RECOMMENDATION_CONFIDENCE_LEVELS,
)
from .eligibility import evaluate_provider_product_eligibility
from .graph_projection import project_provider_products_to_graph
from .normalization import normalize_feed_row_to_provider_product
from .offer_health import (
    build_feed_availability_context,
    evaluate_offer_health,
    evaluate_product_eligibility,
    evaluate_purchasability_state,
    evaluate_recommendation_confidence,
    extract_purchasability_verification,
    interpret_availability_state,
)
from .state import resolve_provider_feed_pipeline

__all__ = (
    "AVAILABILITY_STATES",
    "PROVIDER_ELIGIBILITY_STATUSES",
    "PROVIDER_FEED_STATUSES",
    "FeedAvailabilityContext",
    "OfferHealth",
    "ProductEligibility",
    "ProviderEligibilityResult",
    "ProviderFeedConfig",
    "ProviderFeedStatus",
    "ProviderGraphProjectionResult",
    "ProviderParseResult",
    "ProviderProduct",
    "PurchasabilityVerification",
    "RECOMMENDATION_CONFIDENCE_LEVELS",
    "build_feed_availability_context",
    "evaluate_offer_health",
    "evaluate_product_eligibility",
    "evaluate_provider_product_eligibility",
    "evaluate_purchasability_state",
    "evaluate_recommendation_confidence",
    "extract_purchasability_verification",
    "interpret_availability_state",
    "load_awin_provider_feed",
    "normalize_feed_row_to_provider_product",
    "project_provider_products_to_graph",
    "resolve_provider_feed_pipeline",
)
