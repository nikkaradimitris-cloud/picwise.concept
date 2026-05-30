from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from .contracts import ProviderProduct

_HTTP_URL_RE = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)

_TITLE_KEYS = ("title", "product_name", "name", "product_title")
_BRAND_KEYS = ("brand", "manufacturer", "merchant_brand", "brand_name")
_CATEGORY_KEYS = ("category", "category_name", "product_category", "merchant_category")
_URL_KEYS = ("product_url", "url", "deeplink", "aw_deep_link", "merchant_deep_link", "link")
_IMAGE_KEYS = ("image_url", "image", "aw_image_url", "merchant_image_url", "image_link")
_PRICE_KEYS = ("price", "current_price", "search_price", "sale_price", "price_text")
_AVAILABILITY_KEYS = ("availability", "in_stock", "stock_status", "availability_text")
_CURRENCY_KEYS = ("currency", "currency_code")
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


def derive_stable_provider_product_id(*, product_url: str, title: str, raw: Mapping[str, Any]) -> str:
    explicit = _first_non_empty(raw, _PRODUCT_ID_KEYS)
    if explicit:
        return explicit
    seed = f"{product_url.strip().lower()}|{title.strip().lower()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"derived_{digest}"


def is_valid_http_url(value: str) -> bool:
    safe = str(value or "").strip()
    if not safe:
        return False
    return bool(_HTTP_URL_RE.match(safe))


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

    return ProviderProduct(
        provider_key=str(provider_key or "").strip(),
        provider_product_id=provider_product_id,
        title=title,
        brand=_first_non_empty(payload, _BRAND_KEYS),
        category_text=_first_non_empty(payload, _CATEGORY_KEYS),
        product_url=product_url,
        image_url=_first_non_empty(payload, _IMAGE_KEYS),
        price_text=_first_non_empty(payload, _PRICE_KEYS),
        availability_text=_first_non_empty(payload, _AVAILABILITY_KEYS),
        currency=_first_non_empty(payload, _CURRENCY_KEYS),
        raw=payload,
    )
