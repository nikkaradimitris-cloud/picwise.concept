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


class AmazonManualAffiliateQualityStatus(str, Enum):
    ACTIVE = "active"
    UNAVAILABLE_MANUAL = "unavailable_manual"
    WEAK_MATCH = "weak_match"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


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
    slot_label: str
    affiliate_url: str
    tracking_id: str
    source: AmazonManualAffiliateSource
    status: AmazonManualAffiliateStatus
    quality_status: AmazonManualAffiliateQualityStatus
    quality_note: str | None
    last_manual_reviewed_at: str | None
    operator_note: str | None
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
    slot_label: str
    asin: str
    affiliate_url: str
    tracking_id: str
    source: str
    status: str
    quality_status: str
    disclosure: str
    safe_note: str


@dataclass(frozen=True)
class AmazonManualAffiliateMatchResult:
    match_status: AmazonManualMatchStatus
    query: str
    matched_category: str | None
    result: AmazonManualAffiliateSafeResult | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class AmazonManualAffiliateMultiMatchResult:
    match_status: AmazonManualMatchStatus
    query: str
    matched_category: str | None
    results: tuple[AmazonManualAffiliateSafeResult, ...]
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
    if record.quality_status not in (
        AmazonManualAffiliateQualityStatus.ACTIVE,
        AmazonManualAffiliateQualityStatus.UNAVAILABLE_MANUAL,
        AmazonManualAffiliateQualityStatus.WEAK_MATCH,
        AmazonManualAffiliateQualityStatus.NEEDS_MANUAL_REVIEW,
    ):
        errors.append("unknown_quality_status")
    if record.status == AmazonManualAffiliateStatus.APPROVED:
        if record.quality_status != AmazonManualAffiliateQualityStatus.ACTIVE:
            errors.append("approved_record_must_be_active_quality")
    if record.status == AmazonManualAffiliateStatus.DISABLED:
        if record.quality_status == AmazonManualAffiliateQualityStatus.ACTIVE:
            errors.append("disabled_record_cannot_be_active_quality")
    if record.status == AmazonManualAffiliateStatus.NEEDS_REVIEW:
        if record.quality_status == AmazonManualAffiliateQualityStatus.ACTIVE:
            errors.append("needs_review_record_cannot_be_active_quality")
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
    slot_label: str,
    affiliate_url: str,
    tracking_id: str,
    source: AmazonManualAffiliateSource,
    status: AmazonManualAffiliateStatus,
    quality_status: AmazonManualAffiliateQualityStatus,
    quality_note: str | None,
    last_manual_reviewed_at: str | None,
    operator_note: str | None,
    created_at: str,
    notes: str | None = None,
) -> AmazonManualAffiliateRecord:
    return AmazonManualAffiliateRecord(
        asin=asin,
        title=title,
        category=category,
        slot_label=slot_label,
        affiliate_url=affiliate_url,
        tracking_id=tracking_id,
        source=source,
        status=status,
        quality_status=quality_status,
        quality_note=quality_note,
        last_manual_reviewed_at=last_manual_reviewed_at,
        operator_note=operator_note,
        created_at=created_at,
        notes=notes,
    )


MANUAL_AMAZON_AFFILIATE_REGISTRY: tuple[AmazonManualAffiliateRecord, ...] = (
    _record(
        asin="B08K7GHZ3V",
        title="INIU Portable Charger 10500mAh Fast Charging Power Bank",
        category="power_banks",
        slot_label="Everyday portable",
        affiliate_url=(
            "https://www.amazon.com/INIU-Portable-Charger-10500mAh-Charging/dp/B08K7GHZ3V"
            "?crid=167FD632I01EF&dib=eyJ2IjoiMSJ9.vveHnzS65ZgXb2UfnvBQmQ9bt0Y5VqU045bi_7dC0g98_B_yplGmgBeLX9pyRIDIkQk3qJGmoKYyW67ys8YETW0WJFBtgyLHAowwDriIgS9hAA4sobvEg-VmEsx3qgIjpS0xPRSYMy2vuWU5pJHRV0cWJQ7XU6eAZvWOvcIk7V7SWpkws95R_XISBp9l7c0cr4_W2PoXLzhZQlafsb1LiJp9zsPQOxeYYf0UpIPnnfc.4n4VK-OC-3wrBqMPipk1SCSXGKLYddx9BGt9B1MwF_A"
            "&dib_tag=se&keywords=powerbank+fast+charging&qid=1778792963&sprefix=Powerban%2Caps%2C264"
            "&sr=8-1&linkCode=ll2&tag=picwise-20&linkId=fd52291bc856330b8545dc8851549c81&language=en_US"
            "&ref_=as_li_ss_tl"
        ),
        tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
        source=AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL,
        status=AmazonManualAffiliateStatus.DISABLED,
        quality_status=AmazonManualAffiliateQualityStatus.UNAVAILABLE_MANUAL,
        quality_note="Disabled after manual review: Amazon listing showed 'Currently unavailable'.",
        last_manual_reviewed_at="2026-05-15T14:00:00Z",
        operator_note="Keep for audit history; exclude from public results and outbound redirect.",
        created_at="2026-05-15T00:00:00Z",
        notes="Stage 1 approved SiteStripe proof link.",
    ),
    _record(
        asin="B0FQJH2XSY",
        title="Portable Charger 5000mAh Compact Power Bank",
        category="power_banks",
        slot_label="Compact carry",
        affiliate_url=(
            "https://www.amazon.com/Portable-Charger-5000mAh-Display-Compatible/dp/B0FQJH2XSY"
            "?crid=VQNXR1L41CLV&dib=eyJ2IjoiMSJ9.D6kMgaHqNvKJ1cw7QsBiwGTBHFj3-3SIJ7itcuMWUi0yWbWhNl8tec5aNQ3ivYbkVdKqha1czJa7hASapCVU8Mvnp8UHnRiXsTlHDP8b32Lyt517sLGP_MPSLd2K88yjUYZuVY0CYNDeGgYQvWak52elggEW4HLFOhnqAem_z62JK4pr5AhPTOwSR8KO9o2E6wTJcM4-1Cov5MmZVABm1hDV3tc8sdClCah3K4r9pc8.B1Df7z0nGidAEChCFM56a1cXgZtkHwfPfJGEbedGgyU"
            "&dib_tag=se&keywords=compact%2Bpower%2Bbank&qid=1778847524&sprefix=compact%2Bpower%2Bbank%2Caps%2C384"
            "&sr=8-7&th=1&linkCode=ll2&tag=picwise-20&linkId=2b8cf97d0ba667e96fd60b75b4115bba&language=en_US"
            "&ref_=as_li_ss_tl"
        ),
        tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
        source=AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL,
        status=AmazonManualAffiliateStatus.APPROVED,
        quality_status=AmazonManualAffiliateQualityStatus.ACTIVE,
        quality_note="Manually reviewed and active for public display.",
        last_manual_reviewed_at="2026-05-15T14:00:00Z",
        operator_note="Approved for controlled public result set.",
        created_at="2026-05-15T00:00:00Z",
        notes="Stage 4 approved SiteStripe compact option.",
    ),
    _record(
        asin="B0GR1257LT",
        title="Geavonyg PowerBanks 20000mAh Portable Charger",
        category="power_banks",
        slot_label="20000mAh capacity",
        affiliate_url=(
            "https://www.amazon.com/Geavonyg-PowerBanks-20000mAh-Chargers-Removable/dp/B0GR1257LT"
            "?crid=3GI30IGT370S9&dib=eyJ2IjoiMSJ9.fk1ZUR1sWfdGCr5G7EP_b-vE5wnA6VuUwnD9mRBufoBcA0f7rK0VmsEqoTeg3Pj_-ka11lU_F-hH14V7wFHaDiq-qMlYTK5X-EAEnlF8M9Jyq8mf_Txyh6Qc7HS5y5n5RNI3PUmAdWBLIoUVcp3uswPQ5M6J-NVgHwwlVMALZHw0AXNxIdefZZAFPAD_sAT7iAMiMVT7aVTGMHOkXicaj84dMsgkyZQbadvbQCdtiVE.PrzwVH197TX0Mepuhg-UGOY5rfCjz1N9MgFjp81qBuI"
            "&dib_tag=se&keywords=20%2C000mAh%2Bpower%2Bbank&qid=1778846386&sprefix=20%2C000mah%2Bpower%2Bbank%2Caps%2C255"
            "&sr=8-3&th=1&linkCode=ll2&tag=picwise-20&linkId=9e405083aac7309eb218473fbbff562f&language=en_US"
            "&ref_=as_li_ss_tl"
        ),
        tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
        source=AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL,
        status=AmazonManualAffiliateStatus.APPROVED,
        quality_status=AmazonManualAffiliateQualityStatus.ACTIVE,
        quality_note="Manually reviewed and active for public display.",
        last_manual_reviewed_at="2026-05-15T14:00:00Z",
        operator_note="Approved for controlled public result set.",
        created_at="2026-05-15T00:00:00Z",
        notes="Stage 4 approved SiteStripe 20000mAh option.",
    ),
    _record(
        asin="B0GH75LWKN",
        title="Portable Charger 40000mAh Fast Charging Power Bank",
        category="power_banks",
        slot_label="High capacity",
        affiliate_url=(
            "https://www.amazon.com/Portable-Charger-40000mah-Charging-Battery/dp/B0GH75LWKN"
            "?crid=27EOP8ZRI2PVJ&dib=eyJ2IjoiMSJ9.tCTJHxhWimVpL8HIyv_29RC_hYmRe4-IiKu9MJwkdv66oGoty47P6HM7d_Pzo5YtfQtoPGn1G_u0u6swe39GHPzSoS_4diKuo6aSirkCfjZW6MCRaCA0clx_NZ-At0uyu5wjpgyCH4gkb_Q1iiID2VOX9p3K0BBoNtWpB3HzCjVC3HMQJYdHy0ZseYpzLtPWhQatflWBjbctyn6YjrpzH_aJ6-KT7jokxDqxxf0Hya8.rqLiVaosoy2HgV2BiLlWmZzf-0QxN6C0eyRThE8aqAY"
            "&dib_tag=se&keywords=Fast%2Bcharging%2BUSB-C%2BPD%2Bpower%2Bbank&qid=1778846446&sprefix=fast%2Bcharging%2Busb-c%2Bpd%2Bpower%2Bbank%2Caps%2C247"
            "&sr=8-3&th=1&linkCode=ll2&tag=picwise-20&linkId=d99ec02821dbb297449344f74c98d28c&language=en_US"
            "&ref_=as_li_ss_tl"
        ),
        tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
        source=AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL,
        status=AmazonManualAffiliateStatus.APPROVED,
        quality_status=AmazonManualAffiliateQualityStatus.ACTIVE,
        quality_note="Manually reviewed and active for public display.",
        last_manual_reviewed_at="2026-05-15T14:00:00Z",
        operator_note="Approved for controlled public result set.",
        created_at="2026-05-15T00:00:00Z",
        notes="Stage 4 approved SiteStripe high-capacity option.",
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
        "5000mah",
        "20000mah",
        "20,000mah",
        "40000mah",
        "charger 10500mah",
        "compact power bank",
        "fast charging",
    )
    if any(signal in normalized for signal in power_bank_signals):
        return "power_banks"
    return None


def _build_safe_result(record: AmazonManualAffiliateRecord) -> AmazonManualAffiliateSafeResult:
    return AmazonManualAffiliateSafeResult(
        title=record.title,
        category=record.category,
        slot_label=record.slot_label,
        asin=record.asin,
        affiliate_url=record.affiliate_url,
        tracking_id=record.tracking_id,
        source=record.source.value,
        status=record.status.value,
        quality_status=record.quality_status.value,
        disclosure=AMAZON_ASSOCIATE_DISCLOSURE,
        safe_note=AMAZON_SAFE_NOTE,
    )


def _find_records_for_category(category: str) -> tuple[AmazonManualAffiliateRecord, ...]:
    return tuple(record for record in MANUAL_AMAZON_AFFILIATE_REGISTRY if record.category == category)


def is_public_eligible_manual_amazon_record(record: AmazonManualAffiliateRecord) -> bool:
    if record.status != AmazonManualAffiliateStatus.APPROVED:
        return False
    if record.quality_status != AmazonManualAffiliateQualityStatus.ACTIVE:
        return False
    if not validate_manual_amazon_record(record).valid:
        return False
    return True


def match_manual_amazon_affiliates(query: str) -> AmazonManualAffiliateMultiMatchResult:
    category = _match_category(query)
    if category is None:
        return AmazonManualAffiliateMultiMatchResult(
            match_status=AmazonManualMatchStatus.NO_MATCH,
            query=str(query or ""),
            matched_category=None,
            results=tuple(),
            reason_codes=("no_manual_category_match",),
        )
    records = _find_records_for_category(category)
    if not records:
        return AmazonManualAffiliateMultiMatchResult(
            match_status=AmazonManualMatchStatus.NEEDS_REVIEW,
            query=str(query or ""),
            matched_category=category,
            results=tuple(),
            reason_codes=("missing_registry_record",),
        )
    safe_results: list[AmazonManualAffiliateSafeResult] = []
    invalid_reason_codes: list[str] = []
    disabled_count = 0
    needs_review_count = 0
    for record in records:
        record_validation = validate_manual_amazon_record(record)
        if not record_validation.valid:
            invalid_reason_codes.extend(record_validation.errors)
            continue
        if record.status == AmazonManualAffiliateStatus.DISABLED:
            disabled_count += 1
            continue
        if record.status == AmazonManualAffiliateStatus.NEEDS_REVIEW:
            needs_review_count += 1
            continue
        if record.quality_status != AmazonManualAffiliateQualityStatus.ACTIVE:
            needs_review_count += 1
            continue
        safe_results.append(_build_safe_result(record))
    if invalid_reason_codes:
        return AmazonManualAffiliateMultiMatchResult(
            match_status=AmazonManualMatchStatus.BLOCKED,
            query=str(query or ""),
            matched_category=category,
            results=tuple(),
            reason_codes=("invalid_manual_record",) + tuple(sorted(set(invalid_reason_codes))),
        )
    if safe_results:
        return AmazonManualAffiliateMultiMatchResult(
            match_status=AmazonManualMatchStatus.ELIGIBLE,
            query=str(query or ""),
            matched_category=category,
            results=tuple(safe_results),
            reason_codes=("eligible_manual_amazon_links",),
        )
    if needs_review_count > 0:
        return AmazonManualAffiliateMultiMatchResult(
            match_status=AmazonManualMatchStatus.NEEDS_REVIEW,
            query=str(query or ""),
            matched_category=category,
            results=tuple(),
            reason_codes=("record_needs_review",),
        )
    if disabled_count > 0:
        return AmazonManualAffiliateMultiMatchResult(
            match_status=AmazonManualMatchStatus.BLOCKED,
            query=str(query or ""),
            matched_category=category,
            results=tuple(),
            reason_codes=("record_disabled",),
        )
    return AmazonManualAffiliateMultiMatchResult(
        match_status=AmazonManualMatchStatus.NEEDS_REVIEW,
        query=str(query or ""),
        matched_category=category,
        results=tuple(),
        reason_codes=("no_approved_record",),
    )


def match_manual_amazon_affiliate(query: str) -> AmazonManualAffiliateMatchResult:
    multi_result = match_manual_amazon_affiliates(query)
    first_result = multi_result.results[0] if multi_result.results else None
    return AmazonManualAffiliateMatchResult(
        match_status=multi_result.match_status,
        query=multi_result.query,
        matched_category=multi_result.matched_category,
        result=first_result,
        reason_codes=multi_result.reason_codes,
    )


def _normalize_asin(value: str) -> str | None:
    normalized = str(value or "").strip().upper()
    if len(normalized) != _ASIN_LENGTH:
        return None
    if not normalized.isalnum():
        return None
    return normalized


def get_approved_manual_amazon_record_by_asin(asin: str) -> AmazonManualAffiliateRecord | None:
    normalized_asin = _normalize_asin(asin)
    if normalized_asin is None:
        return None
    for record in MANUAL_AMAZON_AFFILIATE_REGISTRY:
        if record.asin != normalized_asin:
            continue
        if is_public_eligible_manual_amazon_record(record):
            return record
    return None


def get_manual_amazon_record_by_asin(asin: str) -> AmazonManualAffiliateRecord | None:
    normalized_asin = _normalize_asin(asin)
    if normalized_asin is None:
        return None
    for record in MANUAL_AMAZON_AFFILIATE_REGISTRY:
        if record.asin == normalized_asin:
            return record
    return None


def manual_affiliate_registry_as_dicts() -> tuple[dict[str, Any], ...]:
    return tuple(asdict(record) for record in MANUAL_AMAZON_AFFILIATE_REGISTRY)
