from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


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


class SourceTrustLevel(str, Enum):
    TRUSTED = "trusted"
    PARTNER_VERIFIED = "partner_verified"
    UNKNOWN = "unknown"
    UNSAFE = "unsafe"


class ProductSourceStatus(str, Enum):
    CONNECTED = "connected"
    NOT_CONNECTED = "not_connected"
    NEEDS_DATA = "needs_data"
    MANUAL_REVIEW = "manual_review"
    NOT_READY = "not_ready"


@dataclass(frozen=True)
class ProductSourceRecord:
    source_id: str
    source_type: str
    source_label: str
    status: ProductSourceStatus
    trust_level: SourceTrustLevel
    verticals: tuple[str, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class OfferCandidate:
    candidate_id: str
    source_id: str
    source_type: str
    title: str | None
    brand: str | None
    model: str | None
    image_url: str | None
    price: float | None
    currency: str | None
    seller_name: str | None
    seller_url: str | None
    availability_status: str | None
    outbound_url: str | None
    affiliate_url: str | None
    category: str | None
    vertical: str | None
    engine: str | None
    category_bucket: str | None
    google_taxonomy_path: str | None
    saas_erp_contract_ref: str | None
    finance_insurance_contract_ref: str | None
    source_updated_at: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class OfferIntakeResult:
    source: ProductSourceRecord
    status: ProductSourceStatus
    candidates: tuple[OfferCandidate, ...]
    reason_codes: tuple[str, ...]
    metadata: dict[str, Any]
