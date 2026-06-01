from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .contracts import PurchasabilityVerification
from .normalization import is_valid_http_url

DEFAULT_TIMEOUT_SECONDS = 12.0
DEFAULT_MAX_BYTES = 512_000
DEFAULT_USER_AGENT = (
    "PicWise-PageVerifier/1.0 (audit-only; lightweight HTML check; no headless browser)"
)

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")

_BUY_SIGNALS = (
    "add to basket",
    "add to cart",
    "buy now",
    "checkout",
)
_OUT_OF_STOCK_SIGNALS = (
    "out of stock",
    "sold out",
    "temporarily unavailable",
    "currently unavailable",
    "unavailable",
)
_DISCONTINUED_SIGNALS = (
    "discontinued",
    "no longer available",
)
_AMBIGUOUS_SIGNALS = (
    "check availability",
    "notify me when",
    "coming soon",
    "email for price",
)

_REDIRECT_SUSPECT_PATH_MARKERS = (
    "/search",
    "/category",
    "/categories",
    "/catalog",
    "/browse",
    "/collections",
    "/shop",
    "/store",
    "/home",
    "/index",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def html_to_visible_text(html: str) -> str:
    without_blocks = _SCRIPT_STYLE_RE.sub(" ", str(html or ""))
    without_tags = _TAG_RE.sub(" ", without_blocks)
    return " ".join(without_tags.split()).lower()


def _path_is_redirect_suspect(path: str) -> bool:
    normalized = str(path or "").strip().lower() or "/"
    if normalized in {"/", ""}:
        return True
    for marker in _REDIRECT_SUSPECT_PATH_MARKERS:
        if marker in normalized:
            return True
    return False


def is_redirect_suspect(*, original_url: str, final_url: str) -> bool:
    final = str(final_url or "").strip()
    if not final or not is_valid_http_url(final):
        return True
    original = urlparse(str(original_url or "").strip())
    resolved = urlparse(final)
    if not resolved.scheme or not resolved.netloc:
        return True
    if _path_is_redirect_suspect(resolved.path):
        return True
    original_host = (original.netloc or "").lower()
    final_host = (resolved.netloc or "").lower()
    if original_host and final_host and original_host != final_host:
        original_path = (original.path or "").lower()
        final_path = (resolved.path or "").lower()
        if original_path and final_path and original_path != final_path:
            if _path_is_redirect_suspect(final_path):
                return True
    return False


def detect_page_purchasability_signals(page_text: str) -> dict[str, bool]:
    normalized = str(page_text or "").lower()
    return {
        "buy_button_seen": any(signal in normalized for signal in _BUY_SIGNALS),
        "out_of_stock_seen": any(signal in normalized for signal in _OUT_OF_STOCK_SIGNALS),
        "discontinued_seen": any(signal in normalized for signal in _DISCONTINUED_SIGNALS),
    }


def analyze_product_page_content(
    *,
    url: str,
    html: str,
    http_status: int | None,
    final_url: str,
    checked_at: str | None = None,
) -> PurchasabilityVerification:
    timestamp = checked_at or _utc_now_iso()
    source = "page_verifier"

    if not is_valid_http_url(url):
        return PurchasabilityVerification(
            purchasability_state="invalid_page",
            buy_button_seen=False,
            out_of_stock_seen=None,
            final_url=final_url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence="unknown",
        )

    status = http_status if http_status is not None else 0
    if status < 200 or status >= 400:
        return PurchasabilityVerification(
            purchasability_state="invalid_page",
            buy_button_seen=False,
            out_of_stock_seen=None,
            final_url=final_url or url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence="unknown",
        )

    if is_redirect_suspect(original_url=url, final_url=final_url):
        return PurchasabilityVerification(
            purchasability_state="redirect_suspect",
            buy_button_seen=None,
            out_of_stock_seen=None,
            final_url=final_url or url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence="weak",
        )

    signals = detect_page_purchasability_signals(html_to_visible_text(html))
    buy_seen = signals["buy_button_seen"]
    oos_seen = signals["out_of_stock_seen"]
    discontinued_seen = signals["discontinued_seen"]

    if discontinued_seen:
        return PurchasabilityVerification(
            purchasability_state="discontinued",
            buy_button_seen=buy_seen if buy_seen else False,
            out_of_stock_seen=oos_seen if oos_seen else None,
            final_url=final_url or url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence="verified",
        )

    if oos_seen:
        return PurchasabilityVerification(
            purchasability_state="out_of_stock",
            buy_button_seen=buy_seen if buy_seen else False,
            out_of_stock_seen=True,
            final_url=final_url or url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence="verified",
        )

    if buy_seen:
        confidence = "verified"
        if oos_seen or discontinued_seen:
            confidence = "limited"
        return PurchasabilityVerification(
            purchasability_state="purchasable",
            buy_button_seen=True,
            out_of_stock_seen=False,
            final_url=final_url or url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence=confidence,
        )

    page_text = html_to_visible_text(html)
    if any(marker in page_text for marker in _AMBIGUOUS_SIGNALS):
        return PurchasabilityVerification(
            purchasability_state="purchasability_unknown",
            buy_button_seen=False,
            out_of_stock_seen=False,
            final_url=final_url or url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence="weak",
        )

    if not page_text.strip():
        return PurchasabilityVerification(
            purchasability_state="purchasability_unknown",
            buy_button_seen=False,
            out_of_stock_seen=False,
            final_url=final_url or url,
            http_status=http_status,
            last_checked_at=timestamp,
            verification_source=source,
            verification_confidence="unknown",
        )

    return PurchasabilityVerification(
        purchasability_state="missing_buy_button",
        buy_button_seen=False,
        out_of_stock_seen=False,
        final_url=final_url or url,
        http_status=http_status,
        last_checked_at=timestamp,
        verification_source=source,
        verification_confidence="limited",
    )


def _fetch_page_bytes(
    url: str,
    *,
    timeout_seconds: float,
    user_agent: str,
    max_bytes: int,
    opener: Callable[..., Any] | None = None,
) -> tuple[bytes, int | None, str]:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    open_fn = opener or urlopen
    with open_fn(request, timeout=timeout_seconds) as response:
        status = getattr(response, "status", None)
        if status is None and hasattr(response, "getcode"):
            status = response.getcode()
        final_url = getattr(response, "geturl", lambda: url)()
        chunks: list[bytes] = []
        total = 0
        while True:
            block = response.read(min(65536, max(1, max_bytes - total)))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total >= max_bytes:
                break
        return b"".join(chunks), status, str(final_url or url)


def verify_product_page_purchasability(
    url: str,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    opener: Callable[..., Any] | None = None,
) -> PurchasabilityVerification:
    safe_url = str(url or "").strip()
    timestamp = _utc_now_iso()

    if not is_valid_http_url(safe_url):
        return PurchasabilityVerification(
            purchasability_state="invalid_page",
            buy_button_seen=False,
            out_of_stock_seen=None,
            final_url="",
            http_status=None,
            last_checked_at=timestamp,
            verification_source="page_verifier",
            verification_confidence="unknown",
        )

    try:
        body, http_status, final_url = _fetch_page_bytes(
            safe_url,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            max_bytes=max_bytes,
            opener=opener,
        )
    except HTTPError as exc:
        headers = getattr(exc, "headers", None)
        location = ""
        if headers is not None:
            location = str(headers.get("Location") or headers.get("location") or "")
        return analyze_product_page_content(
            url=safe_url,
            html="",
            http_status=exc.code,
            final_url=location or safe_url,
            checked_at=timestamp,
        )
    except (URLError, TimeoutError, OSError, ValueError):
        return PurchasabilityVerification(
            purchasability_state="invalid_page",
            buy_button_seen=False,
            out_of_stock_seen=None,
            final_url=safe_url,
            http_status=None,
            last_checked_at=timestamp,
            verification_source="page_verifier",
            verification_confidence="unknown",
        )

    charset = "utf-8"
    html = body.decode(charset, errors="replace")
    return analyze_product_page_content(
        url=safe_url,
        html=html,
        http_status=http_status,
        final_url=final_url,
        checked_at=timestamp,
    )


def purchasability_verification_to_raw(
    verification: PurchasabilityVerification,
) -> dict[str, Any]:
    return verification.to_dict()


def merge_verification_into_product_raw(
    raw: Mapping[str, Any],
    verification: PurchasabilityVerification,
) -> dict[str, Any]:
    merged = dict(raw) if isinstance(raw, Mapping) else {}
    merged.update(purchasability_verification_to_raw(verification))
    return merged
