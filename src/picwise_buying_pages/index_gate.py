from __future__ import annotations

from dataclasses import dataclass

from .models import BuyingPage, IndexStatus, PRICE_BAND_MAX_EUR, PRICE_BAND_MIN_EUR
from .slugging import slugify_keyword


@dataclass(frozen=True)
class IndexGateResult:
    indexable: bool
    reasons: tuple[str, ...]

    @property
    def robots_meta_value(self) -> str:
        return "index,follow" if self.indexable else "noindex,follow"


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

    for product in page.products:
        if not product.product_url.strip():
            reasons.append("missing_product_url")
            break
        if not (product.affiliate_url or "").strip():
            reasons.append("missing_affiliate_url")
            break

    if page.price_band_applicable:
        for product in page.products:
            if product.currency.upper() != "EUR":
                reasons.append("price_band_currency_mismatch")
                break
            if not (PRICE_BAND_MIN_EUR <= float(product.price) <= PRICE_BAND_MAX_EUR):
                reasons.append("price_band_out_of_range")
                break

    return IndexGateResult(indexable=not reasons, reasons=tuple(reasons))
