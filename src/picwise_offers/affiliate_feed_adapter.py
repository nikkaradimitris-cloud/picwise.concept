from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .contracts import OfferCandidate

_HTTP_URL_REGEX = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)
_NUMERIC_REGEX = re.compile(r"-?\d+(?:[.,]\d+)?")


class AffiliateFeedRowStatus(str, Enum):
    MAPPED = "mapped"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


@dataclass(frozen=True)
class AffiliateFeedRowResult:
    row_index: int
    status: AffiliateFeedRowStatus
    reason_codes: tuple[str, ...]
    candidate: OfferCandidate | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class AffiliateFeedBatchResult:
    row_results: tuple[AffiliateFeedRowResult, ...]
    mapped_candidates: tuple[OfferCandidate, ...]
    status_counts: dict[str, int]


def _first_non_empty(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if not lowered:
        return None
    if lowered in {"1", "true", "yes", "y", "available"}:
        return True
    if lowered in {"0", "false", "no", "n", "none", "not_available"}:
        return False
    return None


def _normalize_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    match = _NUMERIC_REGEX.search(text)
    if not match:
        return None
    number = match.group(0).replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def _normalize_specifications(value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        cleaned = tuple(str(item).strip() for item in value if str(item).strip())
        return cleaned or None
    text = str(value).strip()
    if not text:
        return None
    parts = tuple(item.strip() for item in text.split("|") if item.strip())
    return parts or (text,)


def _is_valid_http_url(value: str | None) -> bool:
    if not value:
        return False
    return bool(_HTTP_URL_REGEX.match(value.strip()))


def _canonical_seller_reliability_status(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_")
    mapping = {
        "trusted": "trusted",
        "acceptable": "acceptable",
        "partner_verified": "acceptable",
        "unknown": "unknown",
        "unreliable": "unreliable",
        "blocked": "blocked",
    }
    return mapping.get(normalized, "unknown")


def _resolve_seller_reliability(
    *,
    seller_name: str | None,
    trusted_seller_status_by_name: Mapping[str, str] | None,
) -> str:
    if not seller_name or not trusted_seller_status_by_name:
        return "unknown"
    for key, status in trusted_seller_status_by_name.items():
        if str(key).strip().lower() == seller_name.strip().lower():
            return _canonical_seller_reliability_status(status)
    return "unknown"


def adapt_affiliate_feed_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_id: str,
    source_type: str = "affiliate_feed",
    trusted_seller_status_by_name: Mapping[str, str] | None = None,
) -> AffiliateFeedBatchResult:
    normalized_source_id = str(source_id or "").strip()
    normalized_source_type = str(source_type or "affiliate_feed").strip() or "affiliate_feed"
    if not normalized_source_id:
        raise ValueError("source_id is required for affiliate feed adaptation.")

    row_results: list[AffiliateFeedRowResult] = []
    mapped_candidates: list[OfferCandidate] = []

    for row_index, raw_row in enumerate(rows):
        reasons: list[str] = []
        if not isinstance(raw_row, Mapping):
            row_results.append(
                AffiliateFeedRowResult(
                    row_index=row_index,
                    status=AffiliateFeedRowStatus.REJECTED,
                    reason_codes=("invalid_row_type",),
                    candidate=None,
                    metadata={"adapter": "affiliate_feed_adapter_v1"},
                )
            )
            continue

        payload = dict(raw_row)
        candidate_id = _first_non_empty(payload, ("candidate_id", "offer_id", "product_id", "id", "sku", "item_id"))
        title = _first_non_empty(payload, ("title", "product_title", "name"))
        seller_name = _first_non_empty(payload, ("seller_name", "seller", "merchant", "store", "vendor"))
        outbound_url = _first_non_empty(payload, ("outbound_url", "product_url", "url", "landing_page_url", "link"))
        affiliate_url = _first_non_empty(payload, ("affiliate_url", "tracking_url", "deeplink", "affiliate_link"))
        image_url = _first_non_empty(payload, ("image_url", "image", "image_link", "thumbnail_url"))
        currency = _first_non_empty(payload, ("currency", "currency_code"))
        availability = _first_non_empty(payload, ("availability", "availability_status", "stock_status"))
        brand = _first_non_empty(payload, ("brand", "manufacturer"))
        model = _first_non_empty(payload, ("model", "model_code"))
        category = _first_non_empty(payload, ("category", "product_category"))
        vertical = _first_non_empty(payload, ("vertical",))
        engine = _first_non_empty(payload, ("engine",))
        category_bucket = _first_non_empty(payload, ("category_bucket", "taxonomy_bucket", "category_slug"))
        google_taxonomy_path = _first_non_empty(
            payload,
            ("google_taxonomy_path", "google_product_category", "taxonomy_path"),
        )
        seller_url = _first_non_empty(payload, ("seller_url", "merchant_url", "store_url", "vendor_url"))
        source_updated_at = _first_non_empty(payload, ("source_updated_at", "updated_at", "last_updated"))
        short_description = _first_non_empty(payload, ("short_description", "description", "product_description"))
        specifications = _normalize_specifications(payload.get("specifications", payload.get("specs")))
        locale = _first_non_empty(payload, ("locale", "language_locale"))
        market = _first_non_empty(payload, ("market", "country", "region"))
        shipping_info_available = _normalize_bool(payload.get("shipping_info_available"))
        return_policy_available = _normalize_bool(payload.get("return_policy_available"))
        price = _normalize_price(payload.get("price", payload.get("sale_price", payload.get("amount"))))

        if not candidate_id:
            reasons.append("missing_candidate_id")
        if not title:
            reasons.append("missing_title")
        if not seller_name:
            reasons.append("missing_seller_name")
        if not outbound_url and not affiliate_url:
            reasons.append("missing_outbound_and_affiliate_url")
        if outbound_url and not _is_valid_http_url(outbound_url):
            reasons.append("invalid_outbound_url")
        if affiliate_url and not _is_valid_http_url(affiliate_url):
            reasons.append("invalid_affiliate_url")
        if seller_url and not _is_valid_http_url(seller_url):
            reasons.append("invalid_seller_url")

        seller_reliability_status = _resolve_seller_reliability(
            seller_name=seller_name,
            trusted_seller_status_by_name=trusted_seller_status_by_name,
        )
        if seller_reliability_status == "unknown":
            reasons.append("seller_reliability_unknown")

        metadata: dict[str, Any] = {
            "adapter": "affiliate_feed_adapter_v1",
            "feed_row_index": row_index,
            "enrichment": {
                "seller_reliability_status": seller_reliability_status,
                "shipping_info_available": shipping_info_available,
                "return_policy_available": return_policy_available,
                "has_short_description": bool(short_description),
                "has_specifications": bool(specifications),
                "has_taxonomy_linkage": bool(category_bucket or google_taxonomy_path or category),
            },
        }
        if short_description:
            metadata["short_description"] = short_description
        if specifications:
            metadata["specifications"] = specifications
        if locale or market:
            metadata["locale_market"] = {"locale": locale, "market": market}

        deduped_reasons = tuple(dict.fromkeys(reasons))
        has_rejection = any(code in {"missing_candidate_id", "invalid_outbound_url"} for code in deduped_reasons)

        if has_rejection:
            row_results.append(
                AffiliateFeedRowResult(
                    row_index=row_index,
                    status=AffiliateFeedRowStatus.REJECTED,
                    reason_codes=deduped_reasons,
                    candidate=None,
                    metadata=metadata,
                )
            )
            continue

        status = AffiliateFeedRowStatus.MAPPED if not deduped_reasons else AffiliateFeedRowStatus.REVIEW_REQUIRED
        candidate = OfferCandidate(
            candidate_id=candidate_id,
            source_id=normalized_source_id,
            source_type=normalized_source_type,
            title=title,
            brand=brand,
            model=model,
            image_url=image_url,
            price=price,
            currency=currency,
            seller_name=seller_name,
            seller_url=seller_url,
            availability_status=availability,
            outbound_url=outbound_url,
            affiliate_url=affiliate_url,
            category=category,
            vertical=vertical,
            engine=engine,
            category_bucket=category_bucket,
            google_taxonomy_path=google_taxonomy_path,
            saas_erp_contract_ref=_first_non_empty(payload, ("saas_erp_contract_ref",)),
            finance_insurance_contract_ref=_first_non_empty(payload, ("finance_insurance_contract_ref",)),
            source_updated_at=source_updated_at,
            metadata=metadata,
        )
        row_results.append(
            AffiliateFeedRowResult(
                row_index=row_index,
                status=status,
                reason_codes=deduped_reasons,
                candidate=candidate,
                metadata=metadata,
            )
        )
        mapped_candidates.append(candidate)

    status_counts: dict[str, int] = {}
    for row_result in row_results:
        key = row_result.status.value
        status_counts[key] = status_counts.get(key, 0) + 1

    return AffiliateFeedBatchResult(
        row_results=tuple(row_results),
        mapped_candidates=tuple(mapped_candidates),
        status_counts=status_counts,
    )
