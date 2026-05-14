from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any
from urllib.parse import parse_qs, urlparse


AMAZON_ASSOCIATES_TRACKING_ID = "picwise-20"
AMAZON_ASSOCIATES_STORE_ID = "picwise-20"
AMAZON_ASSOCIATE_DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
AMAZON_SAFE_NOTE = (
    "Prices, availability, ratings, reviews, delivery, and seller terms are shown on Amazon and may change. "
    "PicWise does not sell products directly."
)
_ALLOWED_AMAZON_HOSTS = {"amazon.com", "www.amazon.com"}
_ALLOWED_URL_SCHEMES = {"http", "https"}
_ASIN_LENGTH = 10


class AmazonManualAffiliateSource(str, Enum):
    AMAZON_SITESTRIPE_MANUAL = "amazon_sitestripe_manual"


class AmazonManualAffiliateStatus(str, Enum):
    APPROVED = "approved"
    DISABLED = "disabled"
    NEEDS_REVIEW = "needs_review"


class AmazonManualMatchStatus(str, Enum):
    ELIGIBLE = "eligible"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NO_MATCH = "no_match"


@dataclass(frozen=True)
class AmazonAffiliateUrlValidationResult:
    valid: bool
    asin: str | None
    tracking_id: str | None
    normalized_host: str | None
    errors: tuple[str, ...]


@dataclass(frozen=True)
class AmazonManualAffiliateRecord:
    asin: str
    title: str
    category: str
    affiliate_url: str
    tracking_id: str
    source: AmazonManualAffiliateSource
    status: AmazonManualAffiliateStatus
    created_at: str
    notes: str | None = None


@dataclass(frozen=True)
class AmazonManualRecordValidationResult:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class AmazonManualAffiliateSafeResult:
    title: str
    category: str
    asin: str
    affiliate_url: str
    tracking_id: str
    source: str
    status: str
    disclosure: str
    safe_note: str


@dataclass(frozen=True)
class AmazonManualAffiliateMatchResult:
    match_status: AmazonManualMatchStatus
    query: str
    matched_category: str | None
    result: AmazonManualAffiliateSafeResult | None
    reason_codes: tuple[str, ...]


def _extract_asin_from_path(path: str) -> str | None:
    segments = [segment for segment in (path or "").split("/") if segment]
    if not segments:
        return None
    for index, segment in enumerate(segments):
        lowered = segment.lower()
        candidate = None
        if lowered == "dp" and index + 1 < len(segments):
            candidate = segments[index + 1].upper()
        elif lowered == "gp" and index + 2 < len(segments) and segments[index + 1].lower() == "product":
            candidate = segments[index + 2].upper()
        if candidate is None:
            continue
        if len(candidate) != _ASIN_LENGTH:
            continue
        if not candidate.isalnum():
            continue
        return candidate
    return None


def validate_amazon_affiliate_url(
    affiliate_url: str,
    *,
    required_tracking_id: str = AMAZON_ASSOCIATES_TRACKING_ID,
) -> AmazonAffiliateUrlValidationResult:
    safe_url = str(affiliate_url or "").strip()
    if not safe_url:
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=None,
            tracking_id=None,
            normalized_host=None,
            errors=("empty_url",),
        )
    try:
        parsed = urlparse(safe_url)
    except Exception:
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=None,
            tracking_id=None,
            normalized_host=None,
            errors=("malformed_url",),
        )
    host = str(parsed.netloc or "").strip().lower()
    if not parsed.scheme or parsed.scheme.lower() not in _ALLOWED_URL_SCHEMES:
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=None,
            tracking_id=None,
            normalized_host=host or None,
            errors=("invalid_scheme",),
        )
    if host == "amzn.to":
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=None,
            tracking_id=None,
            normalized_host=host,
            errors=("short_links_not_allowed",),
        )
    if host not in _ALLOWED_AMAZON_HOSTS:
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=None,
            tracking_id=None,
            normalized_host=host or None,
            errors=("non_amazon_host",),
        )
    asin = _extract_asin_from_path(parsed.path or "")
    if asin is None:
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=None,
            tracking_id=None,
            normalized_host=host,
            errors=("missing_or_invalid_asin_path",),
        )
    parsed_query = parse_qs(parsed.query or "", keep_blank_values=True)
    tag_value = str((parsed_query.get("tag") or [""])[0]).strip()
    if not tag_value:
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=asin,
            tracking_id=None,
            normalized_host=host,
            errors=("missing_tag",),
        )
    if tag_value != required_tracking_id:
        return AmazonAffiliateUrlValidationResult(
            valid=False,
            asin=asin,
            tracking_id=tag_value,
            normalized_host=host,
            errors=("wrong_tag",),
        )
    return AmazonAffiliateUrlValidationResult(
        valid=True,
        asin=asin,
        tracking_id=tag_value,
        normalized_host=host,
        errors=tuple(),
    )


def validate_manual_amazon_record(record: AmazonManualAffiliateRecord) -> AmazonManualRecordValidationResult:
    errors: list[str] = []
    if record.source != AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL:
        errors.append("unknown_source")
    if record.status not in (
        AmazonManualAffiliateStatus.APPROVED,
        AmazonManualAffiliateStatus.DISABLED,
        AmazonManualAffiliateStatus.NEEDS_REVIEW,
    ):
        errors.append("unknown_status")
    if record.tracking_id != AMAZON_ASSOCIATES_TRACKING_ID:
        errors.append("unexpected_tracking_id")
    url_validation = validate_amazon_affiliate_url(record.affiliate_url)
    if not url_validation.valid:
        errors.extend(url_validation.errors)
    if url_validation.asin and url_validation.asin != record.asin:
        errors.append("asin_mismatch")
    return AmazonManualRecordValidationResult(valid=not errors, errors=tuple(sorted(set(errors))))


def _record(
    *,
    asin: str,
    title: str,
    category: str,
    affiliate_url: str,
    tracking_id: str,
    source: AmazonManualAffiliateSource,
    status: AmazonManualAffiliateStatus,
    created_at: str,
    notes: str | None = None,
) -> AmazonManualAffiliateRecord:
    return AmazonManualAffiliateRecord(
        asin=asin,
        title=title,
        category=category,
        affiliate_url=affiliate_url,
        tracking_id=tracking_id,
        source=source,
        status=status,
        created_at=created_at,
        notes=notes,
    )


MANUAL_AMAZON_AFFILIATE_REGISTRY: tuple[AmazonManualAffiliateRecord, ...] = (
    _record(
        asin="B08K7GHZ3V",
        title="INIU Portable Charger 10500mAh Fast Charging Power Bank",
        category="power_banks",
        affiliate_url=(
            "https://www.amazon.com/INIU-Portable-Charger-10500mAh-Charging/dp/B08K7GHZ3V"
            "?crid=167FD632I01EF&dib=eyJ2IjoiMSJ9.vveHnzS65ZgXb2UfnvBQmQ9bt0Y5VqU045bi_7dC0g98_B_yplGmgBeLX9pyRIDIkQk3qJGmoKYyW67ys8YETW0WJFBtgyLHAowwDriIgS9hAA4sobvEg-VmEsx3qgIjpS0xPRSYMy2vuWU5pJHRV0cWJQ7XU6eAZvWOvcIk7V7SWpkws95R_XISBp9l7c0cr4_W2PoXLzhZQlafsb1LiJp9zsPQOxeYYf0UpIPnnfc.4n4VK-OC-3wrBqMPipk1SCSXGKLYddx9BGt9B1MwF_A"
            "&dib_tag=se&keywords=powerbank+fast+charging&qid=1778792963&sprefix=Powerban%2Caps%2C264"
            "&sr=8-1&linkCode=ll2&tag=picwise-20&linkId=fd52291bc856330b8545dc8851549c81&language=en_US"
            "&ref_=as_li_ss_tl"
        ),
        tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
        source=AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL,
        status=AmazonManualAffiliateStatus.APPROVED,
        created_at="2026-05-15T00:00:00Z",
        notes="Stage 1 approved SiteStripe proof link.",
    ),
)


def _normalize_query(query: str) -> str:
    lowered = str(query or "").lower().strip()
    compact = " ".join(lowered.replace("_", " ").replace("-", " ").split())
    return compact


def _match_category(query: str) -> str | None:
    normalized = _normalize_query(query)
    if not normalized:
        return None
    power_bank_signals = (
        "power bank",
        "powerbank",
        "portable charger",
        "10500mah",
        "charger 10500mah",
        "fast charging",
    )
    if any(signal in normalized for signal in power_bank_signals):
        return "power_banks"
    return None


def _build_safe_result(record: AmazonManualAffiliateRecord) -> AmazonManualAffiliateSafeResult:
    return AmazonManualAffiliateSafeResult(
        title=record.title,
        category=record.category,
        asin=record.asin,
        affiliate_url=record.affiliate_url,
        tracking_id=record.tracking_id,
        source=record.source.value,
        status=record.status.value,
        disclosure=AMAZON_ASSOCIATE_DISCLOSURE,
        safe_note=AMAZON_SAFE_NOTE,
    )


def _find_record_for_category(category: str) -> AmazonManualAffiliateRecord | None:
    for record in MANUAL_AMAZON_AFFILIATE_REGISTRY:
        if record.category == category:
            return record
    return None


def match_manual_amazon_affiliate(query: str) -> AmazonManualAffiliateMatchResult:
    category = _match_category(query)
    if category is None:
        return AmazonManualAffiliateMatchResult(
            match_status=AmazonManualMatchStatus.NO_MATCH,
            query=str(query or ""),
            matched_category=None,
            result=None,
            reason_codes=("no_manual_category_match",),
        )
    record = _find_record_for_category(category)
    if record is None:
        return AmazonManualAffiliateMatchResult(
            match_status=AmazonManualMatchStatus.NEEDS_REVIEW,
            query=str(query or ""),
            matched_category=category,
            result=None,
            reason_codes=("missing_registry_record",),
        )
    record_validation = validate_manual_amazon_record(record)
    if not record_validation.valid:
        return AmazonManualAffiliateMatchResult(
            match_status=AmazonManualMatchStatus.BLOCKED,
            query=str(query or ""),
            matched_category=category,
            result=None,
            reason_codes=("invalid_manual_record",) + record_validation.errors,
        )
    if record.status == AmazonManualAffiliateStatus.DISABLED:
        return AmazonManualAffiliateMatchResult(
            match_status=AmazonManualMatchStatus.BLOCKED,
            query=str(query or ""),
            matched_category=category,
            result=None,
            reason_codes=("record_disabled",),
        )
    if record.status == AmazonManualAffiliateStatus.NEEDS_REVIEW:
        return AmazonManualAffiliateMatchResult(
            match_status=AmazonManualMatchStatus.NEEDS_REVIEW,
            query=str(query or ""),
            matched_category=category,
            result=None,
            reason_codes=("record_needs_review",),
        )
    return AmazonManualAffiliateMatchResult(
        match_status=AmazonManualMatchStatus.ELIGIBLE,
        query=str(query or ""),
        matched_category=category,
        result=_build_safe_result(record),
        reason_codes=("eligible_manual_amazon_link",),
    )


def manual_affiliate_registry_as_dicts() -> tuple[dict[str, Any], ...]:
    return tuple(asdict(record) for record in MANUAL_AMAZON_AFFILIATE_REGISTRY)
