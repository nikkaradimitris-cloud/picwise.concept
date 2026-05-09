from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .slugging import normalize_keyword_text, slugify_keyword

PRICE_BAND_MIN_EUR = 80.0
PRICE_BAND_MAX_EUR = 250.0


class BuyingPageValidationError(ValueError):
    """Raised when BuyingPage data violates the Stage 1 contract."""


class IndexStatus(str, Enum):
    NOINDEX = "noindex"
    INDEXABLE = "indexable"
    SUBMITTED = "submitted"
    INDEXED = "indexed"
    DEINDEXED = "deindexed"


class RefreshStatus(str, Enum):
    FRESH = "fresh"
    REFRESH_DUE = "refresh_due"
    REFRESH_FAILED = "refresh_failed"
    MANUAL_REQUIRED = "manual_required"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"


@dataclass(frozen=True)
class FAQItem:
    question: str
    answer: str

    def __post_init__(self) -> None:
        if not str(self.question).strip() or not str(self.answer).strip():
            raise BuyingPageValidationError("FAQ items require non-empty question and answer.")


@dataclass(frozen=True)
class RefreshMetadata:
    refresh_status: RefreshStatus
    refresh_interval_hours: int
    next_refresh_at: datetime | None
    last_refresh_at: datetime | None
    refresh_reason: str

    def __post_init__(self) -> None:
        try:
            status = (
                self.refresh_status
                if isinstance(self.refresh_status, RefreshStatus)
                else RefreshStatus(str(self.refresh_status))
            )
        except ValueError as exc:
            raise BuyingPageValidationError("refresh_status is invalid.") from exc
        object.__setattr__(self, "refresh_status", status)

        if int(self.refresh_interval_hours) <= 0:
            raise BuyingPageValidationError("refresh_interval_hours must be > 0.")
        if not str(self.refresh_reason).strip():
            raise BuyingPageValidationError("refresh_reason is required.")


@dataclass(frozen=True)
class ProductSlot:
    product_id: str
    title: str
    brand: str | None
    price: float
    currency: str
    image_url: str
    product_url: str
    affiliate_url: str | None
    rating: float | None
    reviews_count: int | None
    availability: str
    reason_summary: str
    buying_reason: str

    def __post_init__(self) -> None:
        if not str(self.product_id).strip():
            raise BuyingPageValidationError("ProductSlot.product_id is required.")
        if not str(self.title).strip():
            raise BuyingPageValidationError("ProductSlot.title is required.")
        if float(self.price) < 0:
            raise BuyingPageValidationError("ProductSlot.price must be >= 0.")
        if not str(self.currency).strip():
            raise BuyingPageValidationError("ProductSlot.currency is required.")
        if not str(self.image_url).strip():
            raise BuyingPageValidationError("ProductSlot.image_url is required.")
        if not str(self.product_url).strip():
            raise BuyingPageValidationError("ProductSlot.product_url is required.")
        if self.rating is not None and not (0 <= float(self.rating) <= 5):
            raise BuyingPageValidationError("ProductSlot.rating must be between 0 and 5.")
        if self.reviews_count is not None and int(self.reviews_count) < 0:
            raise BuyingPageValidationError("ProductSlot.reviews_count must be >= 0.")
        if not str(self.availability).strip():
            raise BuyingPageValidationError("ProductSlot.availability is required.")
        if not str(self.reason_summary).strip() or not str(self.buying_reason).strip():
            raise BuyingPageValidationError(
                "ProductSlot.reason_summary and buying_reason are required."
            )


@dataclass(frozen=True)
class BuyingPage:
    slug: str
    main_keyword: str
    keyword_aliases: tuple[str, ...]
    category: str
    products: tuple[ProductSlot, ...]
    recommended_product_id: str
    faq_items: tuple[FAQItem, ...]
    related_searches: tuple[str, ...]
    index_status: IndexStatus
    last_updated: datetime
    refresh_metadata: RefreshMetadata
    price_band_applicable: bool
    target_price_min_eur: float | None = None
    target_price_max_eur: float | None = None
    approval_status: ApprovalStatus = ApprovalStatus.APPROVED

    def __post_init__(self) -> None:
        canonical_slug = slugify_keyword(self.main_keyword)
        if self.slug != canonical_slug:
            raise BuyingPageValidationError(
                f"slug must be canonical for main_keyword. Expected '{canonical_slug}'."
            )

        aliases = tuple(str(alias).strip() for alias in self.keyword_aliases if str(alias).strip())
        if len(aliases) > 10:
            raise BuyingPageValidationError("keyword_aliases cannot exceed 10 entries.")
        object.__setattr__(self, "keyword_aliases", aliases)

        normalized_aliases = [normalize_keyword_text(alias) for alias in aliases]
        if any(not alias for alias in normalized_aliases):
            raise BuyingPageValidationError("keyword_aliases contain invalid normalized values.")
        if len(set(normalized_aliases)) != len(normalized_aliases):
            raise BuyingPageValidationError(
                "keyword_aliases contain duplicates after normalization."
            )

        if len(self.products) != 4:
            raise BuyingPageValidationError("BuyingPage must include exactly 4 products.")
        product_ids = {product.product_id for product in self.products}
        if self.recommended_product_id not in product_ids:
            raise BuyingPageValidationError(
                "recommended_product_id must exist in the 4 configured products."
            )

        try:
            status = (
                self.index_status
                if isinstance(self.index_status, IndexStatus)
                else IndexStatus(str(self.index_status))
            )
        except ValueError as exc:
            raise BuyingPageValidationError("index_status is invalid.") from exc
        object.__setattr__(self, "index_status", status)

        try:
            approval = (
                self.approval_status
                if isinstance(self.approval_status, ApprovalStatus)
                else ApprovalStatus(str(self.approval_status))
            )
        except ValueError as exc:
            raise BuyingPageValidationError("approval_status is invalid.") from exc
        object.__setattr__(self, "approval_status", approval)

        if self.price_band_applicable:
            if self.target_price_min_eur is None or self.target_price_max_eur is None:
                raise BuyingPageValidationError(
                    "target_price_min_eur and target_price_max_eur are required when "
                    "price_band_applicable is true."
                )
            if (
                float(self.target_price_min_eur) != PRICE_BAND_MIN_EUR
                or float(self.target_price_max_eur) != PRICE_BAND_MAX_EUR
            ):
                raise BuyingPageValidationError("Target price band must be 80-250 EUR.")

            for product in self.products:
                if product.currency.upper() != "EUR":
                    raise BuyingPageValidationError(
                        "All products must be priced in EUR when price band applies."
                    )
                if not (PRICE_BAND_MIN_EUR <= float(product.price) <= PRICE_BAND_MAX_EUR):
                    raise BuyingPageValidationError(
                        "Product prices must be within the 80-250 EUR target band."
                    )
