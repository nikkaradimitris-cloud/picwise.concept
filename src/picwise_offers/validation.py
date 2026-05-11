from __future__ import annotations

import re
from typing import Any

from .contracts import (
    ExternalOffer,
    ExternalOfferSource,
    ExternalOfferSourceType,
    ExternalOfferStatus,
    ExternalOfferValidationResult,
)

_REQUIRED_FIELDS: tuple[str, ...] = (
    "external_product_title",
    "external_store",
    "external_url",
    "price",
    "availability",
    "delivery",
    "returns",
    "review_score",
    "affiliate_url",
    "data_source",
)
_SAFE_URL_REGEX = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)
_SAFE_TEST_DOMAINS = ("example.com", "example.invalid")
_LOCAL_ONLY_SOURCE_TYPES: tuple[ExternalOfferSourceType, ...] = (
    ExternalOfferSourceType.FIXTURE,
    ExternalOfferSourceType.MANUAL_IMPORT,
)
_UNAVAILABLE_VALUES = {"unavailable", "out_of_stock", "not_available"}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _is_safe_url(url: str) -> bool:
    normalized = _normalize_text(url)
    if not normalized or not _SAFE_URL_REGEX.match(normalized):
        return False
    lowered = normalized.lower()
    return any(f"://{domain}" in lowered or f".{domain}/" in lowered for domain in _SAFE_TEST_DOMAINS)


def _has_missing_required_fields(payload: dict[str, Any]) -> tuple[str, ...]:
    missing = []
    for field_name in _REQUIRED_FIELDS:
        value = payload.get(field_name)
        if value is None:
            missing.append(field_name)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field_name)
    return tuple(sorted(set(missing)))


def validate_external_offer(
    payload: dict[str, Any], source: ExternalOfferSource | None = None
) -> ExternalOfferValidationResult:
    safe_payload = payload if isinstance(payload, dict) else {}
    resolved_source_type = source.source_type if source is not None else ExternalOfferSourceType.FIXTURE
    errors: list[str] = []

    if safe_payload.get("is_external_offer") is False:
        errors.append("is_external_offer_false")
    if bool(safe_payload.get("pickwise_owned_inventory")):
        errors.append("pickwise_owned_inventory_not_allowed")
    if bool(safe_payload.get("stock_management")):
        errors.append("stock_management_not_allowed")
    if bool(safe_payload.get("checkout_enabled")):
        errors.append("checkout_not_allowed")
    if resolved_source_type not in _LOCAL_ONLY_SOURCE_TYPES:
        errors.append("non_local_source_type_blocked_for_stage_28a")

    if errors:
        return ExternalOfferValidationResult(
            valid=False,
            status=ExternalOfferStatus.BLOCKED_NOT_EXTERNAL,
            errors=tuple(sorted(errors)),
            offer=None,
        )

    missing_fields = _has_missing_required_fields(safe_payload)
    if missing_fields:
        return ExternalOfferValidationResult(
            valid=False,
            status=ExternalOfferStatus.BLOCKED_MISSING_REQUIRED_FIELDS,
            errors=missing_fields,
            offer=None,
        )

    external_url = _normalize_text(safe_payload.get("external_url"))
    affiliate_url = _normalize_text(safe_payload.get("affiliate_url"))
    if not _is_safe_url(external_url) or not _is_safe_url(affiliate_url):
        return ExternalOfferValidationResult(
            valid=False,
            status=ExternalOfferStatus.BLOCKED_INVALID_URL,
            errors=("invalid_external_or_affiliate_url",),
            offer=None,
        )

    availability = _normalize_text(safe_payload.get("availability")).lower()
    status = ExternalOfferStatus.VALID_EXTERNAL_OFFER
    valid = True
    if availability in _UNAVAILABLE_VALUES:
        status = ExternalOfferStatus.UNAVAILABLE
        valid = False

    review_score_raw = safe_payload.get("review_score", 0.0)
    try:
        review_score = float(review_score_raw)
    except (TypeError, ValueError):
        review_score = -1.0
    if review_score < 0.0 or review_score > 5.0:
        status = ExternalOfferStatus.REVIEW_REQUIRED
        valid = False

    try:
        price_value = float(safe_payload.get("price", 0.0))
    except (TypeError, ValueError):
        price_value = -1.0
    if price_value <= 0:
        status = ExternalOfferStatus.INVALID_EXTERNAL_OFFER
        valid = False

    offer = ExternalOffer(
        offer_id=_normalize_text(safe_payload.get("offer_id") or "external-offer"),
        external_product_title=_normalize_text(safe_payload.get("external_product_title")),
        external_store=_normalize_text(safe_payload.get("external_store")),
        external_url=external_url,
        price=round(price_value, 2),
        availability=_normalize_text(safe_payload.get("availability")),
        delivery=_normalize_text(safe_payload.get("delivery")),
        returns=_normalize_text(safe_payload.get("returns")),
        review_score=round(max(0.0, min(review_score, 5.0)), 2),
        affiliate_url=affiliate_url,
        data_source=_normalize_text(safe_payload.get("data_source")),
        source_type=resolved_source_type,
        status=status,
        is_external_temporary_data=True,
        pickwise_owned_inventory=False,
    )
    return ExternalOfferValidationResult(
        valid=valid,
        status=status,
        errors=tuple(),
        offer=offer,
    )
