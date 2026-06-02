from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse, urlunparse

from .contracts import ProviderProduct, PurchasabilityVerification
from .purchasability_verifier import merge_verification_into_product_raw

CACHE_ENV_VAR = "PICWISE_PURCHASABILITY_CACHE_FILE"
_CACHE_VERSION = 1

_OPTIONAL_ENTRY_BOOL_KEYS = (
    "discontinued_seen",
    "missing_buy_button",
    "redirect_suspect",
    "invalid_page",
)

_active_cache: PurchasabilityCache | None = None
_active_cache_path: str | None = None


def normalize_product_url_key(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        return text.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            parsed.query,
            "",
        )
    )
    return normalized


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


def _verified_purchasable_from_entry(entry: Mapping[str, Any]) -> bool:
    state = str(entry.get("purchasability_state") or "").strip().lower()
    if state != "purchasable":
        return False
    confidence = str(entry.get("verification_confidence") or "").strip().lower()
    return confidence in {"high", "strong", "verified"}


def verification_from_cache_entry(entry: Mapping[str, Any]) -> PurchasabilityVerification:
    payload = entry if isinstance(entry, Mapping) else {}
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
    return PurchasabilityVerification(
        purchasability_state=state,
        buy_button_seen=_parse_bool(payload.get("buy_button_seen")),
        out_of_stock_seen=_parse_bool(payload.get("out_of_stock_seen")),
        final_url=str(payload.get("final_url") or "").strip(),
        http_status=_parse_int(payload.get("http_status")),
        last_checked_at=str(payload.get("checked_at") or payload.get("last_checked_at") or "").strip(),
        verification_source=str(payload.get("verification_source") or "").strip(),
        verification_confidence=str(payload.get("verification_confidence") or "").strip().lower(),
    )


def cache_entry_from_verification(
    verification: PurchasabilityVerification,
    *,
    product_url: str = "",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entry = verification.to_dict()
    key = normalize_product_url_key(product_url)
    if key:
        entry["cache_key"] = key
        entry["product_url"] = key
    entry.setdefault("verification_source", "page_verifier")
    checked_at = str(entry.get("last_checked_at") or "").strip()
    if checked_at:
        entry["checked_at"] = checked_at
    entry["verified_purchasable"] = _verified_purchasable_from_entry(entry)
    if extra:
        for field, value in extra.items():
            if value is not None:
                entry[str(field)] = value
    state = str(entry.get("purchasability_state") or "")
    if state == "discontinued":
        entry.setdefault("discontinued_seen", True)
    if state == "missing_buy_button":
        entry["missing_buy_button"] = True
    if state == "redirect_suspect":
        entry["redirect_suspect"] = True
    if state == "invalid_page":
        entry["invalid_page"] = True
    return entry


def merge_cache_entry_into_product_raw(
    raw: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    verification = verification_from_cache_entry(entry)
    merged = merge_verification_into_product_raw(raw, verification)
    for key in _OPTIONAL_ENTRY_BOOL_KEYS:
        if key in entry:
            merged[key] = entry[key]
    return merged


@dataclass
class PurchasabilityCache:
    entries: dict[str, dict[str, Any]]
    version: int = _CACHE_VERSION

    @classmethod
    def empty(cls) -> PurchasabilityCache:
        return PurchasabilityCache(entries={})

    @classmethod
    def load(cls, path: str) -> PurchasabilityCache:
        safe_path = str(path or "").strip()
        if not safe_path:
            return cls.empty()
        try:
            with open(safe_path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return cls.empty()
        if not isinstance(payload, dict):
            return cls.empty()
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, dict):
            return cls.empty()
        entries: dict[str, dict[str, Any]] = {}
        for key, value in raw_entries.items():
            norm_key = normalize_product_url_key(str(key))
            if norm_key and isinstance(value, dict):
                row = dict(value)
                row.setdefault("cache_key", norm_key)
                entries[norm_key] = row
        version = payload.get("version", _CACHE_VERSION)
        try:
            version_int = int(version)
        except (TypeError, ValueError):
            version_int = _CACHE_VERSION
        return PurchasabilityCache(entries=entries, version=version_int)

    def save(self, path: str) -> None:
        safe_path = str(path or "").strip()
        if not safe_path:
            return
        parent = os.path.dirname(safe_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {
            "version": self.version,
            "entries": self.entries,
        }
        with open(safe_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    def get(self, product_url: str) -> dict[str, Any] | None:
        key = normalize_product_url_key(product_url)
        if not key:
            return None
        entry = self.entries.get(key)
        if not isinstance(entry, dict):
            return None
        return dict(entry)

    def set(
        self,
        product_url: str,
        verification: PurchasabilityVerification,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> str:
        key = normalize_product_url_key(product_url)
        if not key:
            return ""
        self.entries[key] = cache_entry_from_verification(
            verification,
            product_url=key,
            extra=extra,
        )
        return key

    def has(self, product_url: str) -> bool:
        return self.get(product_url) is not None


def configure_purchasability_cache(path: str | None) -> PurchasabilityCache | None:
    global _active_cache, _active_cache_path
    safe_path = str(path or "").strip()
    if not safe_path:
        _active_cache = None
        _active_cache_path = None
        return None
    _active_cache_path = safe_path
    _active_cache = PurchasabilityCache.load(safe_path)
    return _active_cache


def clear_purchasability_cache_configuration() -> None:
    configure_purchasability_cache(None)


def resolve_purchasability_cache() -> PurchasabilityCache | None:
    if _active_cache is not None:
        return _active_cache
    env_path = str(os.environ.get(CACHE_ENV_VAR) or "").strip()
    if not env_path:
        return None
    return PurchasabilityCache.load(env_path)


def resolve_purchasability_cache_path() -> str | None:
    if _active_cache_path:
        return _active_cache_path
    env_path = str(os.environ.get(CACHE_ENV_VAR) or "").strip()
    return env_path or None


def enrich_provider_product_with_cache(
    product: ProviderProduct,
    cache: PurchasabilityCache,
) -> tuple[ProviderProduct, bool]:
    entry = cache.get(product.product_url)
    if entry is None:
        return product, False
    raw = product.raw if isinstance(product.raw, dict) else {}
    merged_raw = merge_cache_entry_into_product_raw(raw, entry)
    enriched = ProviderProduct(
        provider_key=product.provider_key,
        provider_product_id=product.provider_product_id,
        title=product.title,
        brand=product.brand,
        category_text=product.category_text,
        product_url=product.product_url,
        image_url=product.image_url,
        price_text=product.price_text,
        availability_text=product.availability_text,
        currency=product.currency,
        raw=merged_raw,
    )
    return enriched, True


def enrich_provider_products_with_cache(
    products: tuple[ProviderProduct, ...],
    cache: PurchasabilityCache | None = None,
) -> tuple[ProviderProduct, ...]:
    active = cache if cache is not None else resolve_purchasability_cache()
    if active is None:
        return products
    enriched: list[ProviderProduct] = []
    for product in products:
        row, _hit = enrich_provider_product_with_cache(product, active)
        enriched.append(row)
    return tuple(enriched)


def blocked_reason_from_eligibility(reason_codes: tuple[str, ...]) -> str | None:
    for code in reason_codes:
        if code.startswith("purchasability_"):
            return code
    for code in reason_codes:
        if code.startswith("availability_"):
            return code
    return None
