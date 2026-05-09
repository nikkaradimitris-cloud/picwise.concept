from __future__ import annotations

from dataclasses import dataclass

from .models import (
    BuyingPage,
    IndexStatus,
    PRICE_BAND_MAX_EUR,
    PRICE_BAND_MIN_EUR,
    ProductSlot,
    SellerReliabilityStatus,
    is_price_band_exempt_category,
)
from .slugging import normalize_keyword_text, slugify_keyword


@dataclass(frozen=True)
class IndexGateResult:
    indexable: bool
    reasons: tuple[str, ...]

    @property
    def robots_meta_value(self) -> str:
        return "index,follow" if self.indexable else "noindex,follow"


_PUBLIC_AVAILABILITY_OK = frozenset({"in stock", "active", "available", "preorder", "limited"})
_PUBLIC_AVAILABILITY_FAIL = frozenset(
    {"out of stock", "unavailable", "inactive", "discontinued", "fake", "placeholder"}
)
_SELLER_PASS = frozenset(
    {SellerReliabilityStatus.TRUSTED, SellerReliabilityStatus.ACCEPTABLE}
)
_SELLER_REVIEW_REQUIRED = frozenset(
    {
        SellerReliabilityStatus.UNKNOWN,
        SellerReliabilityStatus.NOT_CONNECTED,
        SellerReliabilityStatus.DATA_NOT_YET,
    }
)
_SELLER_FAIL = frozenset({SellerReliabilityStatus.UNRELIABLE, SellerReliabilityStatus.BLOCKED})
_SCAM_MARKERS = ("scam", "counterfeit", "blocked", "fake", "fraud")


def _is_useful_specs(specs: tuple[str, ...]) -> bool:
    if len(specs) < 2:
        return False
    return any(len(normalize_keyword_text(spec).split()) >= 2 for spec in specs)


def _is_suspicious_pricing_or_data(product: ProductSlot) -> bool:
    text_haystack = " ".join(
        (
            product.title,
            product.reason_summary,
            product.buying_reason,
            product.short_description or "",
            " ".join(product.specifications),
            " ".join(product.suspicious_markers),
            str(product.availability),
        )
    ).lower()
    if any(marker in text_haystack for marker in _SCAM_MARKERS):
        return True
    if product.rating is not None and (product.reviews_count in (None, 0)):
        return True
    if product.seller_rating is not None and (product.seller_reviews_count in (None, 0)):
        return True
    return False


def collect_product_slot_public_reasons(
    page: BuyingPage,
    product: ProductSlot,
    *,
    require_affiliate_url: bool = True,
    require_image: bool = True,
    require_price: bool = True,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not str(product.title).strip():
        reasons.append("missing_title")
    normalized_availability = normalize_keyword_text(product.availability)
    if not normalized_availability or normalized_availability in _PUBLIC_AVAILABILITY_FAIL:
        reasons.append("missing_or_invalid_availability")
    elif normalized_availability not in _PUBLIC_AVAILABILITY_OK:
        reasons.append("availability_not_public_safe")
    if require_image and not str(product.image_url).strip():
        reasons.append("missing_image")
    if require_price:
        if float(product.price) <= 0:
            reasons.append("missing_or_invalid_price")
        if not str(product.currency).strip():
            reasons.append("missing_currency")
    if require_affiliate_url and not str(product.affiliate_url or "").strip():
        reasons.append("missing_affiliate_url")
    if not str(product.reason_summary).strip() or not str(product.buying_reason).strip():
        reasons.append("missing_short_product_text")
    if not _is_useful_specs(product.specifications):
        reasons.append("missing_useful_specs")
    if not (str(product.short_description or "").strip()):
        reasons.append("missing_short_description")

    if _is_suspicious_pricing_or_data(product):
        reasons.append("fake_or_suspicious_product_data")

    if page.price_band_applicable and str(product.currency).upper() != "EUR":
        reasons.append("price_band_currency_mismatch")

    seller_status = product.seller_reliability_status
    if seller_status in _SELLER_FAIL:
        reasons.append("seller_unreliable_or_blocked")
    elif seller_status in _SELLER_REVIEW_REQUIRED:
        reasons.append("seller_manual_review_required")
    elif seller_status not in _SELLER_PASS:
        reasons.append("seller_status_unknown")

    seller_identity_exists = bool(str(product.seller_name or "").strip() or str(product.seller_id or "").strip())
    if not seller_identity_exists:
        reasons.append("missing_seller_identity")
    if not bool(product.return_policy_available):
        reasons.append("missing_return_policy_signal")
    if not bool(product.shipping_info_available):
        reasons.append("missing_shipping_info_signal")

    return tuple(reasons)


def is_product_slot_publicly_valid(page: BuyingPage, product: ProductSlot) -> bool:
    return not collect_product_slot_public_reasons(page, product)


def _is_near_duplicate_title(left: str, right: str) -> bool:
    left_tokens = [token for token in normalize_keyword_text(left).split() if token]
    right_tokens = [token for token in normalize_keyword_text(right).split() if token]
    if not left_tokens or not right_tokens:
        return False
    if left_tokens == right_tokens:
        return True
    left_set = set(left_tokens)
    right_set = set(right_tokens)
    overlap = len(left_set & right_set)
    return overlap >= min(len(left_set), len(right_set), 3)


def _is_useful_same_family_variant(product: ProductSlot, anchor_products: tuple[ProductSlot, ...]) -> bool:
    if not product.comparison_useful:
        return False
    family = str(product.comparison_family or "").strip().lower()
    for anchor in anchor_products:
        anchor_family = str(anchor.comparison_family or "").strip().lower()
        if family and anchor_family and family == anchor_family:
            return True
        same_brand = bool(
            str(product.brand or "").strip()
            and str(anchor.brand or "").strip()
            and normalize_keyword_text(product.brand or "") == normalize_keyword_text(anchor.brand or "")
        )
        if same_brand and _is_near_duplicate_title(product.title, anchor.title):
            return True
    return False


def evaluate_index_gate(page: BuyingPage) -> IndexGateResult:
    reasons: list[str] = []

    if page.index_status != IndexStatus.INDEXABLE:
        reasons.append("index_status_not_indexable")

    if not page.main_keyword.strip():
        reasons.append("missing_main_keyword")

    if page.slug != slugify_keyword(page.main_keyword):
        reasons.append("invalid_slug")
    if not page.slug.strip() or "--" in page.slug:
        reasons.append("obvious_duplicate_or_invalid_slug")

    if len(page.products) != 4:
        reasons.append("invalid_product_count")

    product_ids = {product.product_id for product in page.products}
    if page.recommended_product_id not in product_ids:
        reasons.append("invalid_recommended_product")

    if not page.keyword_aliases:
        reasons.append("missing_aliases")
    if len(page.keyword_aliases) > 10:
        reasons.append("too_many_aliases")

    if not page.faq_items:
        reasons.append("missing_faq")

    if not page.related_searches:
        reasons.append("missing_related_searches")

    for idx, product in enumerate(page.products, start=1):
        if not product.product_url.strip():
            reasons.append("missing_product_url")
            break
        product_reasons = collect_product_slot_public_reasons(page, product)
        reasons.extend(f"product_{idx}:{reason}" for reason in product_reasons)

    unique_product_ids = {product.product_id for product in page.products}
    if len(unique_product_ids) != len(page.products):
        reasons.append("duplicate_product_id")

    normalized_titles = [normalize_keyword_text(product.title) for product in page.products]
    if len({title for title in normalized_titles if title}) < 3:
        reasons.append("weak_comparison_value")
    for i, left in enumerate(page.products):
        for right in page.products[i + 1 :]:
            if _is_near_duplicate_title(left.title, right.title):
                reasons.append("duplicate_or_near_duplicate_products")
                break
        if "duplicate_or_near_duplicate_products" in reasons:
            break

    if not all(product.comparison_useful for product in page.products):
        reasons.append("contains_non_useful_filler")

    if page.price_band_applicable:
        if (
            page.target_price_min_eur is None
            or page.target_price_max_eur is None
            or float(page.target_price_min_eur) != PRICE_BAND_MIN_EUR
            or float(page.target_price_max_eur) != PRICE_BAND_MAX_EUR
        ):
            reasons.append("price_band_target_mismatch")
        anchor_products = tuple(
            product
            for product in page.products
            if PRICE_BAND_MIN_EUR <= float(product.price) <= PRICE_BAND_MAX_EUR
        )
        if not anchor_products:
            reasons.append("missing_in_band_anchor_product")
        for product in page.products:
            if product.currency.upper() != "EUR":
                reasons.append("price_band_currency_mismatch")
                break
            if PRICE_BAND_MIN_EUR <= float(product.price) <= PRICE_BAND_MAX_EUR:
                continue
            if not _is_useful_same_family_variant(product, anchor_products):
                reasons.append("price_variant_not_same_family_or_useful")
                break
    elif not is_price_band_exempt_category(page.category):
        reasons.append("price_band_bypass_for_physical_category")

    valid_product_ids = {
        product.product_id for product in page.products if is_product_slot_publicly_valid(page, product)
    }
    if page.recommended_product_id not in valid_product_ids:
        reasons.append("recommended_product_not_publicly_valid")

    return IndexGateResult(indexable=not reasons, reasons=tuple(reasons))
