"""The feed prepared once a day (step 5 of the price-first plan).

A server that reads a real feed for the first time downloads it, parses every row,
judges whether a card can show each product and reads what kind each one is: about 25
seconds on the third feed (42,076 rows), and the first buyer after a quiet spell waits
through them. Prepared once a day, the same result loads in a few seconds.

The file holds what a search, the cards, the suggestions and the outbound redirect read,
judged by the code that wrote it:

- the products a card can show, each as the feed gave it less its empty fields (no
  rule reads an empty field differently from a missing one, and on the third feed 72%
  of the fields are empty), with what the feed says to call it not new and what kind
  it is;
- the feed-wide availability context those judgements were made against;
- the feed's status, the counts the scanning screen names, and the search suggestions.

It never holds the feed's link, which carries the account's API key.

A file is not used, and the server reads the feed itself as before, when it was written
by other code (a change to any rule it froze), in another format, or longer ago than its
age limit (`PICWISE_PREPARED_MAX_AGE_HOURS`, 30 by default).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contracts import FeedAvailabilityContext, ProviderFeedStatus, ProviderProduct
from .suggestions import SearchSuggestion

PREPARED_CATALOGUE_ENV = "PICWISE_PREPARED_CATALOGUE_FILE"
PREPARED_MAX_AGE_ENV = "PICWISE_PREPARED_MAX_AGE_HOURS"
DEFAULT_MAX_AGE_HOURS = 30.0
# Where a deployment's build writes the file (`tools/prepare_catalogue.py`). It is
# read from there only on Vercel, so a file prepared on a laptop never stands in for
# the feed a local run or a test is given.
DEFAULT_PREPARED_PATH = Path("prepared") / "catalogue.json.gz"

_FORMAT = "picwise-prepared-catalogue"
_VERSION = 1
_REPO_ROOT = Path(__file__).resolve().parents[2]
# The packages whose rules the file freezes: reading the feed, judging a product,
# reading its kind, the suggestions. A change to any of their files makes a file
# written before it stale.
_FROZEN_PACKAGES = ("src/picwise_providers", "src/picwise_nlu")


@dataclass(frozen=True)
class PreparedCatalogue:
    prepared_at: datetime
    feed_status: ProviderFeedStatus
    availability_context: FeedAvailabilityContext
    # Card-eligible products, in feed order, and for each the not-new condition the
    # feed states ("" for new) and the kinds it was read as.
    products: tuple[ProviderProduct, ...]
    non_new: tuple[str, ...]
    kinds: tuple[frozenset[str], ...]
    # What the scanning screen names: the feed's eligible products and their shops.
    eligible_count: int
    shop_count: int
    suggestions: tuple[SearchSuggestion, ...]


def code_fingerprint(*, repo_root: Path | None = None) -> str:
    """One digest over every source file whose rules a prepared file freezes."""
    root = repo_root or _REPO_ROOT
    digest = hashlib.sha256(f"{_FORMAT}:{_VERSION}".encode())
    for package in _FROZEN_PACKAGES:
        for path in sorted((root / package).rglob("*.py")):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def prepared_catalogue_path() -> Path | None:
    """The prepared file this server reads, when one is configured or built in."""
    configured = str(os.environ.get(PREPARED_CATALOGUE_ENV) or "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else _REPO_ROOT / path
    if os.environ.get("VERCEL"):
        built = _REPO_ROOT / DEFAULT_PREPARED_PATH
        return built if built.is_file() else None
    return None


def prepared_catalogue_age_limit() -> timedelta:
    """How old a prepared file may be and still stand in for the feed."""
    try:
        hours = float(str(os.environ.get(PREPARED_MAX_AGE_ENV) or DEFAULT_MAX_AGE_HOURS))
    except ValueError:
        hours = DEFAULT_MAX_AGE_HOURS
    return timedelta(hours=max(0.0, hours))


def write_prepared_catalogue(prepared: PreparedCatalogue, path: Path) -> int:
    """Write the file, whole or not at all, and return its size in bytes.

    Products are stored as lists, and the names of their filled fields once for every
    product that has the same ones: a feed's column names repeated for 40,000 products
    would double the file.
    """
    columns: dict[tuple[str, ...], int] = {}
    rows = []
    for product, non_new, kinds in zip(prepared.products, prepared.non_new, prepared.kinds):
        raw = {
            key: value for key, value in (product.raw or {}).items() if value is not None and value != ""
        }
        keys = tuple(raw)
        index = columns.setdefault(keys, len(columns))
        rows.append(
            [
                product.provider_key,
                product.provider_product_id,
                product.title,
                product.brand,
                product.category_text,
                product.product_url,
                product.image_url,
                product.price_text,
                product.availability_text,
                product.currency,
                index,
                [raw[key] for key in keys],
                non_new,
                sorted(kinds),
            ]
        )
    payload = {
        "format": _FORMAT,
        "version": _VERSION,
        "code": code_fingerprint(),
        "prepared_at": prepared.prepared_at.astimezone(timezone.utc).isoformat(),
        "feed_status": prepared.feed_status.to_dict(),
        "availability_context": prepared.availability_context.to_dict(),
        "eligible_count": prepared.eligible_count,
        "shop_count": prepared.shop_count,
        "suggestions": [[row.text, row.products] for row in prepared.suggestions],
        "raw_columns": [list(keys) for keys in columns],
        "products": rows,
    }
    data = gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"), 6)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, partial = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".partial")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(partial, path)
    except BaseException:
        if os.path.exists(partial):
            os.unlink(partial)
        raise
    return len(data)


@dataclass(frozen=True)
class PreparedFileCheck:
    """A prepared file as read, and why it can or cannot stand in for the feed.

    `state` is "fresh", "too_old", "other_code" (written by other code), "other_format"
    or "unreadable"; only a fresh file carries its catalogue.
    """

    state: str
    catalogue: PreparedCatalogue | None = None
    prepared_at: datetime | None = None


def check_prepared_catalogue(path: Path, *, now: datetime | None = None) -> PreparedFileCheck:
    """The prepared file at `path`, read and checked."""
    try:
        payload = json.loads(gzip.decompress(path.read_bytes()))
    except (OSError, EOFError, ValueError):
        return PreparedFileCheck("unreadable")
    if not isinstance(payload, dict):
        return PreparedFileCheck("unreadable")
    if payload.get("format") != _FORMAT or payload.get("version") != _VERSION:
        return PreparedFileCheck("other_format")
    if payload.get("code") != code_fingerprint():
        return PreparedFileCheck("other_code")
    try:
        prepared_at = datetime.fromisoformat(str(payload["prepared_at"]))
        if prepared_at.tzinfo is None:
            return PreparedFileCheck("unreadable")
        if (now or datetime.now(timezone.utc)) - prepared_at > prepared_catalogue_age_limit():
            return PreparedFileCheck("too_old", prepared_at=prepared_at)
        return PreparedFileCheck("fresh", _catalogue_from_payload(payload, prepared_at), prepared_at)
    except (KeyError, TypeError, ValueError, IndexError):
        return PreparedFileCheck("unreadable")


def read_prepared_catalogue(path: Path, *, now: datetime | None = None) -> PreparedCatalogue | None:
    """The prepared file at `path`, or None when it cannot stand in for the feed."""
    return check_prepared_catalogue(path, now=now).catalogue


def _catalogue_from_payload(payload: dict[str, Any], prepared_at: datetime) -> PreparedCatalogue:
    status = payload["feed_status"]
    context = payload["availability_context"]
    columns = [tuple(keys) for keys in payload["raw_columns"]]
    products = []
    non_new = []
    kinds = []
    for row in payload["products"]:
        (
            provider_key, product_id, title, brand, category_text, product_url,
            image_url, price_text, availability_text, currency, index, values,
            condition, row_kinds,
        ) = row
        products.append(
            ProviderProduct(
                provider_key=provider_key,
                provider_product_id=product_id,
                title=title,
                brand=brand,
                category_text=category_text,
                product_url=product_url,
                image_url=image_url,
                price_text=price_text,
                availability_text=availability_text,
                currency=currency,
                raw=dict(zip(columns[index], values)),
            )
        )
        non_new.append(str(condition))
        kinds.append(frozenset(row_kinds))
    return PreparedCatalogue(
        prepared_at=prepared_at,
        feed_status=ProviderFeedStatus(
            status=str(status["status"]),
            provider_key=str(status["provider_key"]),
            reason_codes=tuple(status.get("reason_codes") or ()),
            product_count=int(status.get("product_count") or 0),
            eligible_count=int(status.get("eligible_count") or 0),
            review_count=int(status.get("review_count") or 0),
            blocked_count=int(status.get("blocked_count") or 0),
        ),
        availability_context=FeedAvailabilityContext(
            has_meaningful_variation=bool(context["has_meaningful_variation"]),
            distinct_normalized_values=tuple(context.get("distinct_normalized_values") or ()),
            product_count_with_signal=int(context.get("product_count_with_signal") or 0),
            informative_fields=tuple(context.get("informative_fields") or ()),
        ),
        products=tuple(products),
        non_new=tuple(non_new),
        kinds=tuple(kinds),
        eligible_count=int(payload["eligible_count"]),
        shop_count=int(payload["shop_count"]),
        suggestions=tuple(
            SearchSuggestion(text=str(text), products=int(count))
            for text, count in payload["suggestions"]
        ),
    )
