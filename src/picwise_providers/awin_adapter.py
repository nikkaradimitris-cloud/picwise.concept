from __future__ import annotations

import csv
import io
import json
import os
from typing import Any, Mapping
from urllib.error import URLError
from urllib.request import urlopen

from .contracts import PROVIDER_FEED_STATUSES, ProviderFeedConfig, ProviderParseResult, ProviderProduct
from .normalization import normalize_feed_row_to_provider_product

_AWIN_PROVIDER_KEY = "awin"
_AWIN_FEED_FILE_ENV = "AWIN_FEED_FILE"
_AWIN_FEED_URL_ENV = "AWIN_FEED_URL"


def awin_feed_config_from_env() -> ProviderFeedConfig:
    return ProviderFeedConfig(
        provider_key=_AWIN_PROVIDER_KEY,
        feed_file=os.environ.get(_AWIN_FEED_FILE_ENV),
        feed_url=os.environ.get(_AWIN_FEED_URL_ENV),
    )


def _load_feed_bytes(*, feed_file: str | None, feed_url: str | None) -> tuple[bytes | None, tuple[str, ...]]:
    errors: list[str] = []
    file_path = str(feed_file or "").strip()
    if file_path:
        try:
            with open(file_path, "rb") as handle:
                return handle.read(), tuple()
        except OSError as exc:
            errors.append(f"feed_file_read_failed:{exc.__class__.__name__}")
            return None, tuple(errors)

    url = str(feed_url or "").strip()
    if url:
        try:
            with urlopen(url, timeout=30) as response:
                return response.read(), tuple()
        except (URLError, OSError, ValueError) as exc:
            errors.append(f"feed_url_fetch_failed:{exc.__class__.__name__}")
            return None, tuple(errors)

    return None, tuple(errors)


def _decode_feed_payload(payload: bytes) -> tuple[str | None, tuple[str, ...]]:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return payload.decode(encoding), tuple()
        except UnicodeDecodeError:
            continue
    return None, ("feed_decode_failed",)


def _parse_csv_rows(text: str) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], ("csv_missing_header",)
    rows: list[dict[str, Any]] = []
    for row in reader:
        rows.append({str(key): value for key, value in row.items() if key is not None})
    return rows, tuple()


def _parse_json_rows(text: str) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [], ("json_decode_failed",)

    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, Mapping)]
        if not rows and payload:
            return [], ("json_rows_not_objects",)
        return [dict(item) for item in rows], tuple()

    if isinstance(payload, Mapping):
        for key in ("products", "items", "rows", "data"):
            nested = payload.get(key)
            if isinstance(nested, list):
                rows = [item for item in nested if isinstance(item, Mapping)]
                return [dict(item) for item in rows], tuple()
        return [dict(payload)], tuple()

    return [], ("json_unsupported_shape",)


def _parse_feed_text(text: str) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    stripped = text.lstrip()
    if not stripped:
        return [], ("feed_empty",)
    if stripped.startswith("{") or stripped.startswith("["):
        return _parse_json_rows(text)
    return _parse_csv_rows(text)


def load_awin_provider_feed(
    config: ProviderFeedConfig | None = None,
) -> ProviderParseResult:
    resolved = config or awin_feed_config_from_env()
    if not resolved.is_configured():
        return ProviderParseResult(
            status="provider_feed_not_configured",
            reason_codes=("no_feed_file_or_url",),
        )

    payload, load_errors = _load_feed_bytes(
        feed_file=resolved.feed_file,
        feed_url=resolved.feed_url,
    )
    if payload is None:
        return ProviderParseResult(
            status="provider_feed_parse_failed",
            reason_codes=tuple(load_errors or ("feed_load_failed",)),
            parse_errors=tuple(load_errors or ("feed_load_failed",)),
        )

    text, decode_errors = _decode_feed_payload(payload)
    if text is None:
        return ProviderParseResult(
            status="provider_feed_parse_failed",
            reason_codes=decode_errors,
            parse_errors=decode_errors,
        )

    rows, parse_errors = _parse_feed_text(text)
    if parse_errors:
        return ProviderParseResult(
            status="provider_feed_parse_failed",
            reason_codes=parse_errors,
            parse_errors=parse_errors,
        )

    products: list[ProviderProduct] = []
    for row in rows:
        normalized = normalize_feed_row_to_provider_product(row, provider_key=resolved.provider_key)
        if normalized is not None:
            products.append(normalized)

    if not products:
        return ProviderParseResult(
            status="provider_feed_empty",
            reason_codes=("no_products_after_normalization",),
        )

    return ProviderParseResult(
        status="provider_feed_loaded",
        products=tuple(products),
        reason_codes=("feed_loaded",),
    )


def resolve_awin_feed_status(config: ProviderFeedConfig | None = None) -> str:
    parse_result = load_awin_provider_feed(config)
    if parse_result.status in {
        "provider_feed_not_configured",
        "provider_feed_parse_failed",
        "provider_feed_empty",
    }:
        return parse_result.status
    return parse_result.status
