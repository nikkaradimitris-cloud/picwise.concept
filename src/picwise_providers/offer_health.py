from __future__ import annotations

import re
from typing import Any, Mapping

from .contracts import (
    FeedAvailabilityContext,
    OfferHealth,
    ProductEligibility,
    ProviderProduct,
    PurchasabilityVerification,
    RECOMMENDATION_CONFIDENCE_LEVELS,
)
from .normalization import is_valid_http_url

_AFFILIATE_URL_KEYS = (
    "affiliate_url",
    "aw_deep_link",
    "merchant_deep_link",
    "deeplink",
    "link",
)
_VERIFICATION_STATE_KEYS = ("purchasability_state",)
_VERIFICATION_BOOL_KEYS = ("buy_button_seen", "out_of_stock_seen")
_VERIFICATION_TEXT_KEYS = (
    ("final_url", "final_url"),
    ("last_checked_at", "last_checked_at"),
    ("verification_source", "verification_source"),
    ("verification_confidence", "verification_confidence"),
)
_VERIFICATION_INT_KEYS = (("http_status", "http_status"),)

_AVAILABILITY_RAW_KEYS = (
    "availability",
    "in_stock",
    "stock_status",
    "availability_text",
)

_OUT_OF_STOCK_VALUES = frozenset(
    {
        "out_of_stock",
        "out of stock",
        "out-of-stock",
        "sold out",
        "sold_out",
        "not available",
        "not_available",
        "unavailable",
        "no stock",
        "0",
        "false",
    }
)
_DISCONTINUED_VALUES = frozenset(
    {
        "discontinued",
        "no longer available",
        "no_longer_available",
        "end of life",
        "end_of_life",
        "eol",
    }
)
_IN_STOCK_VALUES = frozenset(
    {
        "in stock",
        "in_stock",
        "in-stock",
        "available",
        "yes",
        "true",
        "1",
    }
)

_WEAK_PRODUCT_TYPE_VALUES = frozenset(
    {
        "not categorized",
        "uncategorized",
        "other",
        "general",
        "misc",
        "miscellaneous",
    }
)
_GENERIC_CATEGORY_VALUES = frozenset(
    {
        "computers",
        "computer",
        "electronics",
        "electronic",
        "general",
        "other",
        "misc",
        "miscellaneous",
        "default",
        "uncategorized",
        "not categorized",
    }
)

def _normalize_availability_token(value: object) -> str:
    collapsed = " ".join(str(value or "").split()).strip().lower()
    if not collapsed:
        return ""
    return collapsed.replace("-", " ").replace("_", " ")


def _collect_product_availability_values(product: ProviderProduct) -> tuple[str, str]:
    raw = product.raw if isinstance(product.raw, dict) else {}
    for key in _AVAILABILITY_RAW_KEYS:
        token = _normalize_availability_token(raw.get(key))
        if token:
            return token, key
    token = _normalize_availability_token(product.availability_text)
    if token:
        return token, "availability_text"
    return "", ""


def build_feed_availability_context(
    products: tuple[ProviderProduct, ...],
) -> FeedAvailabilityContext:
    normalized_values: list[str] = []
    for product in products:
        token, _field = _collect_product_availability_values(product)
        if token:
            normalized_values.append(token)

    distinct = tuple(dict.fromkeys(normalized_values))
    has_variation = len(distinct) > 1
    return FeedAvailabilityContext(
        has_meaningful_variation=has_variation,
        distinct_normalized_values=distinct,
        product_count_with_signal=len(normalized_values),
    )


def _availability_state_for_token(
    token: str,
    *,
    feed_ctx: FeedAvailabilityContext,
) -> tuple[str, str]:
    if not token:
        return "unknown", "missing_availability_signal"
    if not feed_ctx.product_count_with_signal:
        return "unknown", "feed_availability_missing"
    if not feed_ctx.has_meaningful_variation:
        if token in _DISCONTINUED_VALUES:
            return "weak", "constant_feed_discontinued_signal"
        if token in _OUT_OF_STOCK_VALUES:
            return "weak", "constant_feed_out_of_stock_signal"
        return "weak", "constant_feed_availability"
    if token in _DISCONTINUED_VALUES:
        return "discontinued", "explicit_discontinued"
    if token in _OUT_OF_STOCK_VALUES:
        return "out_of_stock", "explicit_out_of_stock"
    return "trusted", "varied_feed_availability"


def interpret_availability_state(
    product: ProviderProduct,
    *,
    feed_ctx: FeedAvailabilityContext,
) -> tuple[str, str, str]:
    token, source_field = _collect_product_availability_values(product)
    state, signal = _availability_state_for_token(token, feed_ctx=feed_ctx)
    return state, source_field, signal


def _parse_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _parse_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def extract_purchasability_verification(raw: Mapping[str, Any]) -> PurchasabilityVerification:
    payload = raw if isinstance(raw, Mapping) else {}
    state = str(payload.get("purchasability_state") or "").strip().lower()
    if state not in {
        "purchasable",
        "purchasability_unknown",
        "missing_buy_button",
        "out_of_stock",
        "discontinued",
        "invalid_page",
        "redirect_suspect",
    }:
        state = "purchasability_unknown"

    text_fields = {key: str(payload.get(source) or "").strip() for key, source in _VERIFICATION_TEXT_KEYS}
    return PurchasabilityVerification(
        purchasability_state=state,
        buy_button_seen=_parse_bool(payload.get("buy_button_seen")),
        out_of_stock_seen=_parse_bool(payload.get("out_of_stock_seen")),
        final_url=text_fields["final_url"],
        http_status=_parse_int(payload.get("http_status")),
        last_checked_at=text_fields["last_checked_at"],
        verification_source=text_fields["verification_source"],
        verification_confidence=str(payload.get("verification_confidence") or "").strip().lower(),
    )


def evaluate_purchasability_state(
    product: ProviderProduct,
    *,
    availability_state: str,
) -> PurchasabilityVerification:
    raw = product.raw if isinstance(product.raw, dict) else {}
    verification = extract_purchasability_verification(raw)

    explicit_state = verification.purchasability_state
    if explicit_state != "purchasability_unknown":
        return verification

    if availability_state == "discontinued":
        return PurchasabilityVerification(
            purchasability_state="discontinued",
            buy_button_seen=verification.buy_button_seen,
            out_of_stock_seen=verification.out_of_stock_seen,
            final_url=verification.final_url,
            http_status=verification.http_status,
            last_checked_at=verification.last_checked_at,
            verification_source=verification.verification_source or "feed_availability",
            verification_confidence=verification.verification_confidence,
        )
    if availability_state == "out_of_stock":
        return PurchasabilityVerification(
            purchasability_state="out_of_stock",
            buy_button_seen=verification.buy_button_seen,
            out_of_stock_seen=True if verification.out_of_stock_seen is None else verification.out_of_stock_seen,
            final_url=verification.final_url,
            http_status=verification.http_status,
            last_checked_at=verification.last_checked_at,
            verification_source=verification.verification_source or "feed_availability",
            verification_confidence=verification.verification_confidence,
        )
    if verification.buy_button_seen is False:
        return PurchasabilityVerification(
            purchasability_state="missing_buy_button",
            buy_button_seen=False,
            out_of_stock_seen=verification.out_of_stock_seen,
            final_url=verification.final_url,
            http_status=verification.http_status,
            last_checked_at=verification.last_checked_at,
            verification_source=verification.verification_source or "page_verification",
            verification_confidence=verification.verification_confidence,
        )
    if verification.buy_button_seen is True:
        return PurchasabilityVerification(
            purchasability_state="purchasable",
            buy_button_seen=True,
            out_of_stock_seen=verification.out_of_stock_seen,
            final_url=verification.final_url,
            http_status=verification.http_status,
            last_checked_at=verification.last_checked_at,
            verification_source=verification.verification_source or "page_verification",
            verification_confidence=verification.verification_confidence,
        )
    return verification


def _parse_price_text(price_text: str) -> float | None:
    cleaned = str(price_text or "").strip().replace(",", "")
    if not cleaned:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _has_product_url(product: ProviderProduct) -> bool:
    if is_valid_http_url(product.product_url):
        return True
    raw = product.raw if isinstance(product.raw, dict) else {}
    for key in _AFFILIATE_URL_KEYS:
        if is_valid_http_url(str(raw.get(key) or "")):
            return True
    return False


def _has_product_type_or_category_evidence(product: ProviderProduct) -> bool:
    raw = product.raw if isinstance(product.raw, dict) else {}
    product_type = " ".join(str(raw.get("product_type") or "").split()).strip().lower()
    if product_type and product_type not in _WEAK_PRODUCT_TYPE_VALUES:
        return True
    category_text = " ".join(str(product.category_text or "").split()).strip().lower()
    if category_text and category_text not in _GENERIC_CATEGORY_VALUES:
        return True
    for key in ("merchant_product_category_path", "merchant_category", "category_name"):
        value = " ".join(str(raw.get(key) or "").split()).strip().lower()
        if value and value not in _GENERIC_CATEGORY_VALUES:
            return True
    return False


def evaluate_offer_health(
    product: ProviderProduct,
    *,
    feed_ctx: FeedAvailabilityContext,
) -> OfferHealth:
    availability_state, source_field, feed_signal = interpret_availability_state(
        product,
        feed_ctx=feed_ctx,
    )
    purchasability = evaluate_purchasability_state(
        product,
        availability_state=availability_state,
    )
    return OfferHealth(
        availability_state=availability_state,
        purchasability=purchasability,
        availability_source_field=source_field,
        feed_availability_signal=feed_signal,
    )


def evaluate_recommendation_confidence(
    *,
    card_eligible: bool,
    offer_health: OfferHealth,
    has_strong_feed_evidence: bool,
) -> str:
    if not card_eligible:
        return "unknown"

    purch_state = offer_health.purchasability.purchasability_state
    if purch_state in {
        "missing_buy_button",
        "out_of_stock",
        "discontinued",
        "invalid_page",
        "redirect_suspect",
    }:
        return "unknown"

    confidence = "weak"
    if has_strong_feed_evidence:
        confidence = "limited"

    if (
        purch_state == "purchasable"
        and offer_health.availability_state == "trusted"
        and has_strong_feed_evidence
        and offer_health.purchasability.verification_confidence in {"high", "strong", "verified"}
    ):
        confidence = "strong"

    if purch_state == "purchasability_unknown" and confidence == "strong":
        confidence = "limited"

    if offer_health.availability_state in {"weak", "unknown"} and confidence == "strong":
        confidence = "limited"

    if confidence not in RECOMMENDATION_CONFIDENCE_LEVELS:
        return "unknown"
    return confidence


def evaluate_product_eligibility(
    product: ProviderProduct,
    *,
    feed_ctx: FeedAvailabilityContext,
) -> ProductEligibility:
    reason_codes: list[str] = []
    offer_health = evaluate_offer_health(product, feed_ctx=feed_ctx)

    if not str(product.title or "").strip():
        reason_codes.append("missing_title")
    if not _has_product_url(product):
        reason_codes.append("missing_product_url")
    if not str(product.image_url or "").strip() or not is_valid_http_url(product.image_url):
        reason_codes.append("missing_image_url")
    if _parse_price_text(product.price_text) is None:
        reason_codes.append("missing_or_unparseable_price")
    if not str(product.currency or "").strip():
        reason_codes.append("missing_currency")
    if not _has_product_type_or_category_evidence(product):
        reason_codes.append("missing_product_type_or_category_evidence")

    if offer_health.availability_state == "out_of_stock":
        reason_codes.append("availability_out_of_stock")
    elif offer_health.availability_state == "discontinued":
        reason_codes.append("availability_discontinued")

    purch_state = offer_health.purchasability.purchasability_state
    if purch_state == "missing_buy_button":
        reason_codes.append("purchasability_missing_buy_button")
    elif purch_state == "out_of_stock":
        reason_codes.append("purchasability_out_of_stock")
    elif purch_state == "discontinued":
        reason_codes.append("purchasability_discontinued")
    elif purch_state == "invalid_page":
        reason_codes.append("purchasability_invalid_page")
    elif purch_state == "redirect_suspect":
        reason_codes.append("purchasability_redirect_suspect")

    has_strong_feed_evidence = not any(
        code
        in {
            "missing_title",
            "missing_product_url",
            "missing_image_url",
            "missing_or_unparseable_price",
            "missing_currency",
            "missing_product_type_or_category_evidence",
            "availability_out_of_stock",
            "availability_discontinued",
            "purchasability_missing_buy_button",
            "purchasability_out_of_stock",
            "purchasability_discontinued",
            "purchasability_invalid_page",
            "purchasability_redirect_suspect",
        }
        for code in reason_codes
    )

    card_eligible = not reason_codes
    confidence_ceiling = evaluate_recommendation_confidence(
        card_eligible=card_eligible,
        offer_health=offer_health,
        has_strong_feed_evidence=has_strong_feed_evidence,
    )

    return ProductEligibility(
        card_eligible=card_eligible,
        reason_codes=tuple(sorted(set(reason_codes))),
        offer_health=offer_health,
        recommendation_confidence_ceiling=confidence_ceiling,
    )


def offer_health_blocks_card_eligibility(offer_health: OfferHealth) -> tuple[str, ...]:
    blocked: list[str] = []
    if offer_health.availability_state in {"out_of_stock", "discontinued"}:
        blocked.append(f"availability_{offer_health.availability_state}")
    purch_state = offer_health.purchasability.purchasability_state
    if purch_state in {
        "missing_buy_button",
        "out_of_stock",
        "discontinued",
        "invalid_page",
        "redirect_suspect",
    }:
        blocked.append(f"purchasability_{purch_state}")
    return tuple(blocked)
