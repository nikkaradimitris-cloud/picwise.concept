from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import sys
import tempfile
import time
import zlib
from typing import IO, Any, Mapping
from urllib.error import URLError
from urllib.request import urlopen

from .contracts import PROVIDER_FEED_STATUSES, ProviderFeedConfig, ProviderParseResult, ProviderProduct
from .normalization import normalize_feed_row_to_provider_product

_AWIN_PROVIDER_KEY = "awin"
# Parsed-feed cache. PROJECT_RULES section 9 caps click-to-redirect at 300ms, but a
# real provider feed costs hundreds of milliseconds to read, decompress and
# normalize, and the outbound redirect route has to resolve one product from it on
# every click. Cache the parse against the file's identity (path, mtime, size) so
# only a changed file is re-read. Feed URLs are never cached: remote content can
# change with no local signal. This caches parsing only and changes no decision,
# eligibility or truth logic.
_PARSE_CACHE: dict[tuple[str, int, int], ProviderParseResult] = {}
_PARSE_CACHE_MAX_ENTRIES = 4
_AWIN_FEED_FILE_ENV = "AWIN_FEED_FILE"
_AWIN_FEED_URL_ENV = "AWIN_FEED_URL"
# The second Awin link, in Awin's own feed format (owner, 2026-11-19: «εφόσον το σετ μπορεί
# να υποστηρίξει την υποδομή της awin προχωράμε»): Awin keeps its two formats in separate
# links, so the shops whose feeds are in Awin's format come in this one. Read beside the
# first wherever it is set; unset, nothing changes. A shop in both is read from the first
# alone (the rule of 2026-10-22: one shop, its products once), known by Awin's advertiser
# id, else its name.
SECOND_FEED_FILE_ENV = "AWIN_FEED_FILE_AWIN"
SECOND_FEED_URL_ENV = "AWIN_FEED_URL_AWIN"
_SHOP_ID_KEYS = ("advertiser_id", "merchant_id")
_GZIP_MAGIC = b"\x1f\x8b"
# A value this short or shorter is held once for all the rows that give it.
_SHARED_VALUE_CHARS = 64

# A feed URL (Awin's Create-a-Feed download link) is downloaded to a local file and
# reused, instead of being fetched on every search: a real feed is tens of megabytes
# and the PROJECT_RULES section 9 render budget is 1.5 seconds. Awin regenerates feeds
# daily, so a few hours of reuse loses nothing.
_FEED_CACHE_TTL_ENV = "AWIN_FEED_CACHE_TTL_SECONDS"
_FEED_MAX_STALE_ENV = "AWIN_FEED_MAX_STALE_SECONDS"
_FEED_CACHE_DIR_ENV = "AWIN_FEED_CACHE_DIR"
_FEED_MAX_BYTES_ENV = "AWIN_FEED_MAX_BYTES"
_DEFAULT_FEED_CACHE_TTL_SECONDS = 6 * 3600
# When a refresh fails, the last good copy is served for at most this long. Past it
# the feed is reported unavailable: prices and stock a day old are acceptable, older
# ones risk showing offers that no longer exist.
_DEFAULT_FEED_MAX_STALE_SECONDS = 24 * 3600
_DEFAULT_FEED_MAX_BYTES = 300 * 1024 * 1024
_FAILED_FETCH_RETRY_SECONDS = 60
_FAILED_FETCHES: dict[str, float] = {}


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(str(os.environ.get(name) or "").strip()))
    except ValueError:
        return default


def _feed_cache_path(feed_url: str) -> str:
    # The URL carries the account's API key, so it is hashed, never written out.
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:20]
    directory = str(os.environ.get(_FEED_CACHE_DIR_ENV) or "").strip() or tempfile.gettempdir()
    return os.path.join(directory, f"picwise_awin_feed_{digest}.bin")


def _download_feed(feed_url: str, destination: str) -> tuple[bool, tuple[str, ...]]:
    limit = _int_env(_FEED_MAX_BYTES_ENV, _DEFAULT_FEED_MAX_BYTES) or _DEFAULT_FEED_MAX_BYTES
    partial = f"{destination}.part{os.getpid()}"
    try:
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
        written = 0
        with urlopen(feed_url, timeout=60) as response, open(partial, "wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit:
                    raise ValueError("feed_too_large")
                handle.write(chunk)
        if written == 0:
            raise ValueError("feed_download_empty")
        os.replace(partial, destination)
        return True, tuple()
    except (URLError, OSError, ValueError) as exc:
        detail = str(exc) if isinstance(exc, ValueError) and str(exc).startswith("feed_") else exc.__class__.__name__
        return False, (f"feed_url_fetch_failed:{detail}",)
    finally:
        if os.path.exists(partial):
            try:
                os.remove(partial)
            except OSError:
                pass


def materialize_feed_url(feed_url: str, *, now: float | None = None) -> tuple[str | None, tuple[str, ...]]:
    """Return a local file holding the feed at `feed_url`, downloading when stale.

    Fresh copy (younger than the TTL): used as is. Older: re-downloaded. If the
    download fails, the previous copy keeps serving until it is older than the
    maximum staleness, and a failed URL is not retried for a minute so a broken feed
    does not cost every request a timeout.
    """
    url = str(feed_url or "").strip()
    if not url:
        return None, ("no_feed_url",)
    current = time.time() if now is None else now
    path = _feed_cache_path(url)
    ttl = _int_env(_FEED_CACHE_TTL_ENV, _DEFAULT_FEED_CACHE_TTL_SECONDS)
    max_stale = _int_env(_FEED_MAX_STALE_ENV, _DEFAULT_FEED_MAX_STALE_SECONDS)
    try:
        age: float | None = current - os.stat(path).st_mtime
    except OSError:
        age = None
    if age is not None and age < ttl:
        return path, tuple()

    last_failure = _FAILED_FETCHES.get(path)
    if last_failure is not None and current - last_failure < _FAILED_FETCH_RETRY_SECONDS:
        errors: tuple[str, ...] = ("feed_url_fetch_failed:recently",)
    else:
        ok, errors = _download_feed(url, path)
        if ok:
            _FAILED_FETCHES.pop(path, None)
            return path, tuple()
        _FAILED_FETCHES[path] = current
    if age is not None and age < max_stale:
        return path, errors + ("serving_previous_feed_copy",)
    return None, errors


def awin_feed_config_from_env() -> ProviderFeedConfig:
    feed_file = str(os.environ.get(_AWIN_FEED_FILE_ENV) or "").strip() or None
    feed_url = str(os.environ.get(_AWIN_FEED_URL_ENV) or "").strip() or None
    if feed_file is None and feed_url is not None:
        # Hand the rest of the pipeline a file, so the parse, pipeline and redirect
        # caches -- all keyed on file identity -- work for URL feeds too.
        cached, _errors = materialize_feed_url(feed_url)
        if cached is not None:
            return ProviderFeedConfig(provider_key=_AWIN_PROVIDER_KEY, feed_file=cached)
    return ProviderFeedConfig(
        provider_key=_AWIN_PROVIDER_KEY,
        feed_file=feed_file,
        feed_url=feed_url,
    )


def _feed_path(*, feed_file: str | None, feed_url: str | None) -> tuple[str | None, tuple[str, ...]]:
    """The local file holding the feed: the one configured, or the link's download."""
    file_path = str(feed_file or "").strip()
    if not file_path:
        url = str(feed_url or "").strip()
        if not url:
            return None, tuple()
        cached, fetch_errors = materialize_feed_url(url)
        if cached is None:
            return None, tuple(fetch_errors or ("feed_url_fetch_failed",))
        file_path = cached
    try:
        with open(file_path, "rb"):
            pass
    except OSError as exc:
        return None, (f"feed_file_read_failed:{exc.__class__.__name__}",)
    return file_path, tuple()


def _is_gzip_file(path: str) -> bool:
    if path.strip().lower().endswith(".gz"):
        return True
    with open(path, "rb") as handle:
        return handle.read(2) == _GZIP_MAGIC


# A feed is read as a stream, row by row, and never held whole. Held whole, a feed of
# many shops costs its compressed bytes, its decompressed bytes, its text and every
# row with all 149 columns at once (owner, 2026-10-18: many shops first): about 21 KB a
# row on a fictional Awin-shaped feed (2026-10-20), so the 8 GB of a Vercel build would
# run out near 380,000 rows. A row keeps only its filled columns: no rule reads an
# empty column differently from a missing one, and a row of a real feed leaves about
# 70% of its columns empty.
_PEEK_CHARS = 4096


def _open_feed_text(path: str, *, gzipped: bool, encoding: str) -> IO[str]:
    binary = gzip.open(path, "rb") if gzipped else open(path, "rb")
    # newline="\n": lines end at "\n" only and keep their endings, as the whole text
    # read through `io.StringIO` did; the csv reader takes the "\r\n" itself.
    return io.TextIOWrapper(binary, encoding=encoding, newline="\n")


def _read_feed_rows(path: str, keep=None) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    try:
        gzipped = _is_gzip_file(path)
    except OSError as exc:
        return [], (f"feed_file_read_failed:{exc.__class__.__name__}",)
    # UTF-8 first, else the whole feed as Latin-1, which decodes any bytes.
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with _open_feed_text(path, gzipped=gzipped, encoding=encoding) as text:
                head = text.read(_PEEK_CHARS)
                while head and not head.strip():
                    more = text.read(_PEEK_CHARS)
                    if not more:
                        break
                    head += more
            if not head.strip():
                return [], ("feed_empty",)
            with _open_feed_text(path, gzipped=gzipped, encoding=encoding) as text:
                if head.lstrip()[0] in "{[":
                    return _parse_json_rows(text.read())
                return _parse_csv_stream(text, keep)
        except UnicodeDecodeError:
            continue
        except (OSError, EOFError, zlib.error) as exc:
            reason = "gzip_decompress_failed" if gzipped else "feed_file_read_failed"
            return [], (f"{reason}:{exc.__class__.__name__}",)
        except Exception as exc:
            return [], (f"feed_parse_failed:{exc.__class__.__name__}",)
    return [], ("feed_decode_failed",)


def _parse_csv_stream(text: IO[str], keep=None) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    # Read as `csv.DictReader` reads it -- blank lines skipped, a repeated column name
    # taking its last value -- with only the filled fields kept, and each row made in one
    # step. A row with a filled field beyond the header's columns is left out whole: its
    # fields no longer stand under their names, so its price could be another column's
    # text or number (2026-11-19: 201 of InStock UK's rows, their sale prices reading
    # "Union Jack" and pieces of JSON; `feed-compare.yml` counts them). Empty fields past
    # the header, a trailing comma, change nothing and are dropped as before.
    try:
        reader = csv.reader(text)
        header = next(reader, None)
        if header is None:
            return [], ("csv_missing_header",)
        repeated_names = len(set(header)) != len(header)
        rows: list[dict[str, Any]] = []
        width = len(header)
        # The columns no rule reads (`prepared_catalogue.LEFT_OUT_COLUMNS`, which a test keeps
        # true) are never kept, and a short value is shared by every row that gives it
        # (`sys.intern`): a shop's name, a currency, a category, a brand once in memory,
        # not once a row (2026-11-19: the two Awin links passed the server's memory).
        from .prepared_catalogue import LEFT_OUT_COLUMNS

        read = [name not in LEFT_OUT_COLUMNS for name in header]
        header = [sys.intern(name) for name in header]
        for row in reader:
            if not row:
                continue
            if len(row) > width and any(field.strip() for field in row[width:]):
                continue
            if repeated_names:
                record = {
                    key: (sys.intern(value) if len(value) <= _SHARED_VALUE_CHARS else value)
                    for key, value in dict(
                        (name, field) for name, field, wanted in zip(header, row, read) if wanted
                    ).items()
                    if value
                }
            else:
                record = {
                    key: (sys.intern(value) if len(value) <= _SHARED_VALUE_CHARS else value)
                    for key, value, wanted in zip(header, row, read)
                    if wanted and value
                }
            # A row that can never show is left here, before it costs memory (`keep`).
            if keep is None or keep(record):
                rows.append(record)
        return rows, tuple()
    except csv.Error as exc:
        return [], (f"csv_parse_failed:{exc.__class__.__name__}",)


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


def feed_file_cache_key(feed_file: str | None) -> tuple[str, int, int] | None:
    path = str(feed_file or "").strip()
    if not path:
        return None
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (os.path.abspath(path), stat.st_mtime_ns, stat.st_size)


def clear_awin_feed_parse_cache() -> None:
    """Drop the parsed-feed cache. For tests and for forcing a re-read."""
    _PARSE_CACHE.clear()


def second_feed_config_from_env() -> ProviderFeedConfig | None:
    """The second Awin link (`SECOND_FEED_URL_ENV`), or a local file of it, when set."""
    feed_file = str(os.environ.get(SECOND_FEED_FILE_ENV) or "").strip() or None
    feed_url = str(os.environ.get(SECOND_FEED_URL_ENV) or "").strip() or None
    if feed_file is None and feed_url is None:
        return None
    if feed_file is None and feed_url is not None:
        cached, _errors = materialize_feed_url(feed_url)
        if cached is not None:
            return ProviderFeedConfig(provider_key=_AWIN_PROVIDER_KEY, feed_file=cached)
    return ProviderFeedConfig(provider_key=_AWIN_PROVIDER_KEY, feed_file=feed_file, feed_url=feed_url)


def shop_key(product: ProviderProduct) -> str:
    """The shop a product is from, as two Awin links name it alike: the advertiser's id."""
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    for key in _SHOP_ID_KEYS:
        value = str(raw.get(key) or "").strip()
        if value:
            return f"id:{value}"
    from .normalization import extract_merchant_name

    name = " ".join(str(extract_merchant_name(raw) or "").split()).casefold()
    return f"name:{name}" if name else ""


def _with_aisle(product: ProviderProduct) -> ProviderProduct:
    """An Awin-format row given the aisle of Google's taxonomy its words fit, ahead of its
    own category (`awin_categories`), so the cap counts it in its own category."""
    from dataclasses import replace

    from .awin_categories import row_aisle

    raw = product.raw if isinstance(product.raw, Mapping) else {}
    aisle = row_aisle(raw)
    if not aisle:
        return product
    own = " ".join(str(product.category_text or "").split())
    return replace(product, category_text=f"{aisle} > {own}" if own else aisle)


_OUT_OF_STOCK = {"0", "no", "n", "false", "out of stock", "out_of_stock", "outofstock", "sold out"}


def second_row_keep(first: ProviderParseResult):
    """Which of the second link's rows are read at all (2026-11-19: both links together
    passed the preparation's memory on the server): only rows that could show, in pounds,
    with a price, in stock or saying nothing, with category words, from a shop the first
    link does not have. The rest never become products, and cost nothing."""
    shops = {shop_key(product) for product in first.products} if first.status == "provider_feed_loaded" else set()
    shops.discard("")

    def keep(row: Mapping[str, Any]) -> bool:
        currency = str(row.get("currency") or "").strip().upper()
        if currency and currency != "GBP":
            return False
        price = str(row.get("search_price") or row.get("price") or "").strip()
        try:
            if float(price.replace(",", "").split()[0]) <= 0:
                return False
        except (ValueError, IndexError):
            return False
        stock = str(row.get("in_stock") or row.get("stock_status") or "").strip().lower()
        if stock in _OUT_OF_STOCK:
            return False
        if not any(str(row.get(column) or "").strip() for column in
                   ("merchant_product_category_path", "category_name", "merchant_category")):
            return False
        for key in _SHOP_ID_KEYS:
            value = str(row.get(key) or "").strip()
            if value:
                return f"id:{value}" not in shops
        return True

    return keep


def merge_feeds(first: ProviderParseResult, second: ProviderParseResult) -> ProviderParseResult:
    """The first link's products, then the second's from shops the first does not have
    and with ids the first does not use. The first decides when the second fails."""
    if second.status != "provider_feed_loaded" or not second.products:
        return first
    if first.status != "provider_feed_loaded":
        return first
    shops = {shop_key(product) for product in first.products}
    shops.discard("")
    ids = {str(product.provider_product_id or "").strip() for product in first.products}
    added = [
        _with_aisle(product)
        for product in second.products
        if shop_key(product) not in shops and str(product.provider_product_id or "").strip() not in ids
    ]
    if not added:
        return first
    return ProviderParseResult(
        status=first.status,
        products=tuple(first.products) + tuple(added),
        reason_codes=tuple(first.reason_codes) + ("second_feed_loaded",),
        parse_errors=tuple(first.parse_errors),
    )


def load_awin_provider_feed(
    config: ProviderFeedConfig | None = None,
) -> ProviderParseResult:
    resolved = config or awin_feed_config_from_env()
    second = second_feed_config_from_env()
    cache_key = feed_file_cache_key(resolved.feed_file)
    if cache_key is not None and second is not None:
        cache_key = cache_key + (feed_file_cache_key(second.feed_file) or (str(second.feed_url or ""), 0, 0))
    if cache_key is not None:
        cached = _PARSE_CACHE.get(cache_key)
        if cached is not None:
            return cached
    parsed = _load_awin_provider_feed_uncached(resolved)
    if second is not None:
        parsed = merge_feeds(parsed, _load_awin_provider_feed_uncached(second, keep=second_row_keep(parsed)))
    if cache_key is not None and parsed.status == "provider_feed_loaded":
        if len(_PARSE_CACHE) >= _PARSE_CACHE_MAX_ENTRIES:
            _PARSE_CACHE.clear()
        _PARSE_CACHE[cache_key] = parsed
    return parsed


def _load_awin_provider_feed_uncached(resolved: ProviderFeedConfig, keep=None) -> ProviderParseResult:
    if not resolved.is_configured():
        return ProviderParseResult(
            status="provider_feed_not_configured",
            reason_codes=("no_feed_file_or_url",),
        )

    path, load_errors = _feed_path(
        feed_file=resolved.feed_file,
        feed_url=resolved.feed_url,
    )
    if path is None:
        return ProviderParseResult(
            status="provider_feed_parse_failed",
            reason_codes=tuple(load_errors or ("feed_load_failed",)),
            parse_errors=tuple(load_errors or ("feed_load_failed",)),
        )

    rows, parse_errors = _read_feed_rows(path, keep)
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
