from .contracts import (
    ExternalOffer,
    ExternalOfferSource,
    ExternalOfferSourceType,
    ExternalOfferStatus,
    ExternalOfferValidationResult,
    OfferCandidate,
    OfferIntakeResult,
    ProductSourceRecord,
    ProductSourceStatus,
    SourceTrustLevel,
)
from .eligibility import CandidateEligibilityDecision, EligibilityGateResult, EligibilityStatus, run_product_eligibility_gate
from .fixture_adapter import LocalFixtureOfferSourceAdapter
from .affiliate_feed_adapter import (
    AffiliateFeedBatchResult,
    AffiliateFeedRowResult,
    AffiliateFeedRowStatus,
    adapt_affiliate_feed_rows,
)
from .import_adapter import import_offer_candidates_from_csv_text, import_offer_candidates_from_json_text
from .ranking import (
    OfferRankingInput,
    OfferRankingReason,
    OfferRankingResult,
    OfferRankingStatus,
    RankedOffer,
    rank_external_offers,
)
from .recommendation_engine import (
    PickWiseRecommendationSet,
    ProductDisplaySlot,
    RecommendationReason,
    RecommendationStatus,
    WiseRecommendedProduct,
    build_pickwise_recommendation_set,
)
from .redirect import (
    RedirectProofInput,
    RedirectProofResult,
    RedirectStatus,
    RedirectTrackingPayload,
    build_redirect_proof,
)
from .source_intake import OfferIntakeRequest, build_default_product_source, intake_offer_candidates
from .validation import validate_external_offer

__all__ = [
    "ExternalOffer",
    "ExternalOfferSource",
    "ExternalOfferSourceType",
    "ExternalOfferStatus",
    "ExternalOfferValidationResult",
    "OfferCandidate",
    "OfferIntakeResult",
    "SourceTrustLevel",
    "ProductSourceStatus",
    "ProductSourceRecord",
    "EligibilityStatus",
    "CandidateEligibilityDecision",
    "EligibilityGateResult",
    "run_product_eligibility_gate",
    "LocalFixtureOfferSourceAdapter",
    "AffiliateFeedRowStatus",
    "AffiliateFeedRowResult",
    "AffiliateFeedBatchResult",
    "adapt_affiliate_feed_rows",
    "OfferIntakeRequest",
    "build_default_product_source",
    "intake_offer_candidates",
    "import_offer_candidates_from_json_text",
    "import_offer_candidates_from_csv_text",
    "OfferRankingInput",
    "OfferRankingReason",
    "OfferRankingResult",
    "OfferRankingStatus",
    "RankedOffer",
    "PickWiseRecommendationSet",
    "ProductDisplaySlot",
    "WiseRecommendedProduct",
    "RecommendationReason",
    "RecommendationStatus",
    "build_pickwise_recommendation_set",
    "RedirectProofInput",
    "RedirectProofResult",
    "RedirectStatus",
    "RedirectTrackingPayload",
    "build_redirect_proof",
    "rank_external_offers",
    "validate_external_offer",
]
