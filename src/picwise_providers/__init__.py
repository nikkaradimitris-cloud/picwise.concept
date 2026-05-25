from __future__ import annotations

from .awin_adapter import load_awin_provider_feed
from .contracts import (
    PROVIDER_ELIGIBILITY_STATUSES,
    PROVIDER_FEED_STATUSES,
    ProviderEligibilityResult,
    ProviderFeedConfig,
    ProviderFeedStatus,
    ProviderGraphProjectionResult,
    ProviderParseResult,
    ProviderProduct,
)
from .eligibility import evaluate_provider_product_eligibility
from .graph_projection import project_provider_products_to_graph
from .normalization import normalize_feed_row_to_provider_product
from .state import resolve_provider_feed_pipeline

__all__ = (
    "PROVIDER_ELIGIBILITY_STATUSES",
    "PROVIDER_FEED_STATUSES",
    "ProviderEligibilityResult",
    "ProviderFeedConfig",
    "ProviderFeedStatus",
    "ProviderGraphProjectionResult",
    "ProviderParseResult",
    "ProviderProduct",
    "evaluate_provider_product_eligibility",
    "load_awin_provider_feed",
    "normalize_feed_row_to_provider_product",
    "project_provider_products_to_graph",
    "resolve_provider_feed_pipeline",
)
