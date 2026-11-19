from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .contracts import ProviderProduct
from .decision_labels import parse_price_amount

_HTTP_URL_RE = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)

_TITLE_KEYS = ("title", "product_name", "name", "product_title")
_BRAND_KEYS = ("brand", "manufacturer", "merchant_brand", "brand_name")
# `google_product_category` is the category column of a Google-format feed (Awin's
# "Enhanced" feeds; owner, 2026-10-20: PicWise reads Google-format feeds). Last, so an
# Awin-format row reads its category as before.
_CATEGORY_KEYS = (
    "category", "category_name", "product_category", "merchant_category", "google_product_category"
)
_URL_KEYS = ("product_url", "url", "deeplink", "aw_deep_link", "merchant_deep_link", "link")
_IMAGE_KEYS = ("image_url", "image", "aw_image_url", "merchant_image_url", "image_link")
# The shop's usual price: the first of these the row fills. Its sale price is read on its
# own (`sale_price_in_force`).
_PRICE_KEYS = ("price", "current_price", "search_price", "price_text")
# The shop's own sale price (owner, 2026-11-19: «Θα ήθελα να αποφύγουμε τους υπολογισμούς
# τιμής», then «Στην έκπτωση τραβά στην τιμή της έκπτωσης»). Google's format, the feed the
# server reads, gives a product on sale two prices: `price`, the shop's usual one, and
# `sale_price`, its price during the sale, with the sale's dates in
# `sale_price_effective_date` ("start/end", ISO 8601) where the shop gives them. The sale
# price is the shop's, never one PicWise works out.
_SALE_PRICE_KEY = "sale_price"
_SALE_DATES_KEY = "sale_price_effective_date"
# A sale ending within this long leaves the usual price: the catalogue is read once a
# night, and a price must not stand on the site after the shop has ended it.
SALE_MUST_LAST = timedelta(hours=24)
_AVAILABILITY_KEYS = ("availability", "in_stock", "stock_status", "availability_text")
_CURRENCY_KEYS = ("currency", "currency_code")
# A Google-format feed has no currency column: its price carries the currency, "39.99
# GBP" (Google's own form; "GBP 39.99" read too). Only a three-letter code standing
# apart from the amount is taken.
_PRICE_WITH_CODE_RE = re.compile(r"^(?:([A-Z]{3})\s+(\S+)|(\S+)\s+([A-Z]{3}))$")
_MERCHANT_KEYS = (
    "merchant_name",
    "merchant",
    "advertiser_name",
    "advertiser",
    "retailer_name",
    "retailer",
    "store_name",
    "store",
    "seller_name",
    "seller",
    "vendor",
)
_PRODUCT_ID_KEYS = (
    "provider_product_id",
    "product_id",
    "aw_product_id",
    "merchant_product_id",
    "sku",
    "id",
    "item_id",
)


def _first_non_empty(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _split_currency(price_text: str) -> tuple[str, str]:
    """A price and the currency code written with it: "39.99 GBP" is ("39.99", "GBP"); a
    price without one stays as the feed wrote it, with ""."""
    match = _PRICE_WITH_CODE_RE.match(price_text)
    if match is None:
        return price_text, ""
    code_first, amount_after, amount_first, code_after = match.groups()
    if code_first:
        return amount_after, code_first
    return amount_first, code_after


def _sale_moment(text: str) -> datetime | None:
    """One end of a sale's dates as a moment ("2026-11-30T23:59-0800", "...Z", "+01:00"),
    or None when it cannot be read. A moment with no offset is read as UTC."""
    value = str(text or "").strip()
    if not value:
        return None
    if value[-1:] in ("Z", "z"):
        value = value[:-1] + "+00:00"
    value = re.sub(r"(T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?[+-]\d{2})(\d{2})$", r"\1:\2", value)
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


# Why a row's sale price is not its price tonight (`sale_price_left_because`), for the
# measure that counts them (`.github/scripts/compare_feeds.py`); "" is a sale price in
# force, "none" a row without one.
SALE_NONE = "none"
SALE_UNREADABLE = "sale price unreadable"
SALE_NOT_LOWER = "not lower than the usual price"
SALE_OTHER_CURRENCY = "another currency"
SALE_DATES_UNREADABLE = "dates unreadable"
SALE_NOT_STARTED = "not started"
SALE_ENDING = "ended or ending within 24 h"


def sale_price_left_because(payload: Mapping[str, Any], *, now: datetime | None = None) -> str:
    """Why the row's sale price is not the shop's price now: one of the `SALE_*` reasons,
    `SALE_NONE` for a row with no sale price, "" when it is in force
    (`sale_price_in_force`, whose rule this is)."""
    if not isinstance(payload, Mapping):
        return SALE_NONE
    sale_text = _normalize_text(payload.get(_SALE_PRICE_KEY))
    if not sale_text:
        return SALE_NONE
    sale_amount, sale_code = _split_currency(sale_text)
    sale = parse_price_amount(sale_amount)
    if sale is None or sale <= 0:
        return SALE_UNREADABLE
    usual_amount, usual_code = _split_currency(_first_non_empty(payload, _PRICE_KEYS))
    usual = parse_price_amount(usual_amount)
    if usual is not None:
        if sale >= usual:
            return SALE_NOT_LOWER
        if sale_code and usual_code and sale_code.upper() != usual_code.upper():
            return SALE_OTHER_CURRENCY
    dates = _normalize_text(payload.get(_SALE_DATES_KEY))
    if dates:
        ends = [part for part in dates.split("/") if part.strip()]
        if len(ends) != 2:
            return SALE_DATES_UNREADABLE
        start, end = _sale_moment(ends[0]), _sale_moment(ends[1])
        if start is None or end is None or end <= start:
            return SALE_DATES_UNREADABLE
        moment = now if now is not None else datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        if moment < start:
            return SALE_NOT_STARTED
        if moment + SALE_MUST_LAST > end:
            return SALE_ENDING
    return ""


def sale_price_in_force(payload: Mapping[str, Any], *, now: datetime | None = None) -> str:
    """The row's sale price as the feed wrote it ("29.99 GBP") when it is the shop's price
    now, else "" (owner, 2026-11-19: «Στην έκπτωση τραβά στην τιμή της έκπτωσης»).

    The sale price counts only when it is lower than the shop's usual price, in the same
    currency, and live now by its dates (`sale_price_effective_date`), not ending within
    `SALE_MUST_LAST`. Dates that cannot be read leave the usual price: no price is shown
    that the shop may have ended. A row with no usual price PicWise can read takes a sale
    price live by its dates. Nothing here is worked out: the price is the shop's. Why a
    sale price is left: `sale_price_left_because`.
    """
    if sale_price_left_because(payload, now=now):
        return ""
    return _normalize_text(payload.get(_SALE_PRICE_KEY))


def _price_and_currency(payload: Mapping[str, Any]) -> tuple[str, str]:
    """The row's price and currency: the shop's sale price when it is in force
    (`sale_price_in_force`), else its usual price. Without a currency column, a code
    written with the price is split off it, so a Google-format row reads as an Awin row
    does ("39.99", "GBP"); a price without one stays as the feed wrote it. A sale price
    written without a code is in the usual price's currency (the same row's)."""
    usual_text = _first_non_empty(payload, _PRICE_KEYS)
    sale_text = sale_price_in_force(payload)
    currency = _first_non_empty(payload, _CURRENCY_KEYS)
    if currency:
        return sale_text or usual_text, currency
    usual_amount, usual_code = _split_currency(usual_text)
    if not sale_text:
        return usual_amount, usual_code
    sale_amount, sale_code = _split_currency(sale_text)
    return sale_amount, sale_code or usual_code


def derive_stable_provider_product_id(*, product_url: str, title: str, raw: Mapping[str, Any]) -> str:
    explicit = _first_non_empty(raw, _PRODUCT_ID_KEYS)
    if explicit:
        return explicit
    seed = f"{product_url.strip().lower()}|{title.strip().lower()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"derived_{digest}"


def extract_merchant_name(raw: Mapping[str, Any]) -> str:
    """Return the selling merchant named by the feed row, or "" when absent.

    A provider key such as "awin" identifies the affiliate network, not the shop.
    An Awin feed carries thousands of merchants, so the merchant must come from
    the row itself. Never substitute a guess: an empty result means the feed did
    not say, and the surface must present that as unknown.
    """
    if not isinstance(raw, Mapping):
        return ""
    return _normalize_text(_first_non_empty(dict(raw), _MERCHANT_KEYS))


def is_valid_http_url(value: str) -> bool:
    safe = str(value or "").strip()
    if not safe:
        return False
    return bool(_HTTP_URL_RE.match(safe))


# A shop's further photos of a product (owner, 2026-11-15: the photo grows at a tap, and
# «όποιος στέλνει επιπλέον φωτογραφίες ... εμφανίζουμε έως 4»): Google's format, the feed
# the server reads, lists them in `additional_image_link`, commas between them. (Awin's own
# format's `alternate_image` columns stay left out of the prepared catalogue,
# `prepared_catalogue.LEFT_OUT_COLUMNS`.) At most `MAX_EXTRA_IMAGES` beside the main
# photo, none twice.
_EXTRA_IMAGE_KEYS = ("additional_image_link",)
MAX_EXTRA_IMAGES = 3


def extra_image_urls(raw: Mapping[str, Any] | None, main_url: str = "") -> tuple[str, ...]:
    """The product's further photos the shop sends, at most `MAX_EXTRA_IMAGES`, each a
    web address and none the main photo's."""
    if not isinstance(raw, Mapping):
        return ()
    seen = {str(main_url or "").strip()}
    found: list[str] = []
    for key in _EXTRA_IMAGE_KEYS:
        value = raw.get(key)
        if isinstance(value, (list, tuple)):
            candidates = [str(item) for item in value]
        else:
            candidates = re.split(r",\s*(?=https?://)", str(value or ""))
        for candidate in candidates:
            url = candidate.strip()
            if not url or url in seen or any(char.isspace() for char in url) or not is_valid_http_url(url):
                continue
            seen.add(url)
            found.append(url)
            if len(found) >= MAX_EXTRA_IMAGES:
                return tuple(found)
    return tuple(found)


def normalize_feed_row_to_provider_product(
    row: Mapping[str, Any],
    *,
    provider_key: str,
) -> ProviderProduct | None:
    if not isinstance(row, Mapping):
        return None

    payload = dict(row)
    title = _first_non_empty(payload, _TITLE_KEYS)
    product_url = _first_non_empty(payload, _URL_KEYS)
    provider_product_id = derive_stable_provider_product_id(
        product_url=product_url,
        title=title,
        raw=payload,
    )
    price_text, currency = _price_and_currency(payload)

    return ProviderProduct(
        provider_key=str(provider_key or "").strip(),
        provider_product_id=provider_product_id,
        title=title,
        brand=_first_non_empty(payload, _BRAND_KEYS),
        category_text=_first_non_empty(payload, _CATEGORY_KEYS),
        product_url=product_url,
        image_url=_first_non_empty(payload, _IMAGE_KEYS),
        price_text=price_text,
        availability_text=_first_non_empty(payload, _AVAILABILITY_KEYS),
        currency=currency,
        raw=payload,
    )
