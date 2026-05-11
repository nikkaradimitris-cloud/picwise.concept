from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExternalOfferStatus(str, Enum):
    VALID_EXTERNAL_OFFER = "valid_external_offer"
    INVALID_EXTERNAL_OFFER = "invalid_external_offer"
    UNAVAILABLE = "unavailable"
    BLOCKED_MISSING_REQUIRED_FIELDS = "blocked_missing_required_fields"
    BLOCKED_INVALID_URL = "blocked_invalid_url"
    BLOCKED_NOT_EXTERNAL = "blocked_not_external"
    REVIEW_REQUIRED = "review_required"


class ExternalOfferSourceType(str, Enum):
    FIXTURE = "fixture"
    MANUAL_IMPORT = "manual_import"
    AFFILIATE_FEED = "affiliate_feed"
    MERCHANT_FEED = "merchant_feed"
    EXTERNAL_API_PLACEHOLDER = "external_api_placeholder"


@dataclass(frozen=True)
class ExternalOfferSource:
    source_id: str
    source_type: ExternalOfferSourceType
    source_label: str
    is_temporary_external_input: bool = True
    allows_live_calls: bool = False


@dataclass(frozen=True)
class ExternalOffer:
    offer_id: str
    external_product_title: str
    external_store: str
    external_url: str
    price: float
    availability: str
    delivery: str
    returns: str
    review_score: float
    affiliate_url: str
    data_source: str
    source_type: ExternalOfferSourceType = ExternalOfferSourceType.FIXTURE
    status: ExternalOfferStatus = ExternalOfferStatus.VALID_EXTERNAL_OFFER
    is_external_temporary_data: bool = True
    pickwise_owned_inventory: bool = False


@dataclass(frozen=True)
class ExternalOfferValidationResult:
    valid: bool
    status: ExternalOfferStatus
    errors: tuple[str, ...]
    offer: ExternalOffer | None = None
