"""The feed prepared once a day (step 5 of the price-first plan).

A server that reads a real feed for the first time downloads it, parses every row,
judges whether a card can show each product and reads what kind each one is: about 25
seconds on the third feed (42,076 rows), and the first buyer after a quiet spell waits
through them. Prepared once a day, the same result loads in a few seconds.

The file holds what a search, the cards, the suggestions and the outbound redirect read,
judged by the code that wrote it:

- the products a card can show, each as the feed gave it less its empty fields (no
  rule reads an empty field differently from a missing one, and on the third feed 72%
  of the fields are empty) and less the Awin columns no rule reads
  (`LEFT_OUT_COLUMNS`), with what the feed says to call it not new and what kind it
  is;
- the feed-wide availability context those judgements were made against;
- the feed's status, the counts the scanning screen names, and the search suggestions.

It never holds the feed's link, which carries the account's API key.

Its size is what a server holds in memory, and Vercel's free plan gives a server 2 GB
(owner, 2026-10-18: many shops first). So a text is written once: one that occurs more
than once in the file goes into a table of texts, and a product's own fields (its
title, link, price...) point at the feed column they were read from.

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
from collections import Counter
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
_VERSION = 2
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Awin columns no rule of PicWise reads, left out of the file: Awin's own ids and
# bookkeeping, the prices other than the one compared, delivery (left out of the price
# by the owner), the extra images and links (a card shows one image and links through
# `aw_deep_link`), and the free columns. On the fictional Awin-shaped feed of the
# measurement of 2026-10-20 they were 14 of a row's 35 filled fields, most of their
# text long links. A rule that comes to read one takes it off this list;
# `tests/test_picwise_prepared_catalogue.py` fails while a listed column is named
# anywhere a feed product is read.
LEFT_OUT_COLUMNS = frozenset(
    {
        "category_id", "brand_id", "data_feed_id", "commission_group", "language",
        "store_price", "display_price", "rrp_price", "saving", "savings_percent",
        "base_price", "base_price_amount", "base_price_text", "product_price_old",
        "delivery_cost", "delivery_restrictions", "delivery_weight", "delivery_time",
        "terms_of_contract", "web_offer", "size_stock_status", "size_stock_amount",
        "number_available", "parent_product_id", "dimensions", "promotional_text",
        "warranty", "colour",
        "merchant_thumb_url", "aw_thumb_url", "large_image", "alternate_image",
        "alternate_image_two", "alternate_image_three", "alternate_image_four", "basket_link",
        "custom_1", "custom_2", "custom_3", "custom_4", "custom_5", "custom_6", "custom_7",
        "custom_8", "custom_9",
        "Fashion:suitable_for", "Fashion:category", "Fashion:size", "Fashion:material",
        "Fashion:pattern", "Fashion:swatch",
    }
)
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
    # Each product's search fields as the search reads them (`_product_search_fields`),
    # so a server loading the file does not work them out again for every product.
    # Empty when not given; the search then works them out itself.
    search_fields: tuple[dict[str, str], ...] = ()


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


def _product_fields(product: ProviderProduct) -> tuple[Any, ...]:
    return (
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
    )


def _kept_raw(product: ProviderProduct) -> dict[str, Any]:
    return {
        key: value
        for key, value in (product.raw or {}).items()
        if value is not None and value != "" and key not in LEFT_OUT_COLUMNS
    }


def write_prepared_catalogue(prepared: PreparedCatalogue, path: Path) -> int:
    """Write the file, whole or not at all, and return its size in bytes.

    Products are stored as lists, and the names of their filled fields once for every
    product that has the same ones: a feed's column names repeated for 40,000 products
    would double the file. Each text is written once. In a product's row a text is the
    text itself when it occurs only there; a number from 0 up when it is in the file's
    table of texts (`strings`); and, for the product's own fields, a number below 0
    when it is the row's own column value at that place (-1 the first). A value that is
    not text, which only a JSON feed can carry, is written inside a list of one.
    """
    raws = [_kept_raw(product) for product in prepared.products]
    search_fields = prepared.search_fields or tuple({} for _product in prepared.products)
    field_names = tuple(search_fields[0]) if search_fields else ()
    if any(tuple(fields) != field_names for fields in search_fields):
        raise ValueError("search fields differ between products")
    counts: Counter = Counter()
    for product, raw, non_new, kinds, fields in zip(
        prepared.products, raws, prepared.non_new, prepared.kinds, search_fields
    ):
        texts = [value for value in raw.values() if isinstance(value, str)]
        own = set(texts)
        counts.update(texts)
        counts.update(
            value
            for value in (*_product_fields(product), *fields.values())
            if isinstance(value, str) and value not in own
        )
        counts.update(sorted(kinds))
        counts[non_new] += 1
    table: dict[str, int] = {}
    for text, count in counts.items():
        # The empty text stays itself: read back, it is the one empty text anyway.
        if count > 1 and text:
            table[text] = len(table)

    def slot(value: Any) -> Any:
        if not isinstance(value, str):
            return [value]
        return table.get(value, value)

    columns: dict[tuple[str, ...], int] = {}
    rows = []
    for product, raw, non_new, kinds, fields in zip(
        prepared.products, raws, prepared.non_new, prepared.kinds, search_fields
    ):
        keys = tuple(raw)
        index = columns.setdefault(keys, len(columns))
        values = [raw[key] for key in keys]
        place: dict[str, int] = {}
        for position, value in enumerate(values):
            if isinstance(value, str):
                place.setdefault(value, -1 - position)

        def own_or_slot(value: Any) -> Any:
            return place[value] if isinstance(value, str) and value in place else slot(value)

        rows.append(
            [
                *(own_or_slot(value) for value in _product_fields(product)),
                index,
                [slot(value) for value in values],
                slot(non_new),
                [slot(kind) for kind in sorted(kinds)],
                [own_or_slot(fields[name]) for name in field_names],
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
        "strings": list(table),
        "search_fields": list(field_names),
        "raw_columns": [list(keys) for keys in columns],
        "products": rows,
    }
    # ASCII text: read back, a text holding one character beyond Latin-1 ("€", "’")
    # takes two or four bytes for every character, and the file is read whole.
    data = gzip.compress(json.dumps(payload, ensure_ascii=True).encode("ascii"), 6)
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
        payload = _read_payload(path)
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


def _read_payload(path: Path) -> Any:
    # One copy of the file at a time: the compressed bytes go once decompressed, those
    # once decoded, and the text once read.
    text = gzip.decompress(path.read_bytes()).decode("utf-8")
    return json.loads(text)


def read_prepared_catalogue(path: Path, *, now: datetime | None = None) -> PreparedCatalogue | None:
    """The prepared file at `path`, or None when it cannot stand in for the feed."""
    return check_prepared_catalogue(path, now=now).catalogue


def read_prepared_catalogue_to_measure(path: Path) -> PreparedCatalogue | None:
    """The prepared file at `path` whatever code wrote it and however old, or None when
    it is not one: for a measure taken from the server's file with other code
    (`deployment/server/print_cap.py`), never to stand in for the feed."""
    try:
        payload = _read_payload(path)
        if not isinstance(payload, dict) or payload.get("format") != _FORMAT or payload.get("version") != _VERSION:
            return None
        prepared_at = datetime.fromisoformat(str(payload["prepared_at"]))
        return _catalogue_from_payload(payload, prepared_at)
    except (OSError, EOFError, ValueError, KeyError, TypeError, IndexError):
        return None


def _catalogue_from_payload(payload: dict[str, Any], prepared_at: datetime) -> PreparedCatalogue:
    status = payload["feed_status"]
    context = payload["availability_context"]
    columns = [tuple(keys) for keys in payload["raw_columns"]]
    strings = payload["strings"]
    products = []
    non_new = []
    kinds = []
    # Products of one kind share one set of kinds.
    kind_sets: dict[tuple[str, ...], frozenset[str]] = {}

    def resolve(slot: Any, values: list[Any]) -> Any:
        if slot.__class__ is str:
            return slot
        if slot.__class__ is int:
            return values[-1 - slot] if slot < 0 else strings[slot]
        return slot[0]

    field_names = tuple(payload["search_fields"])
    search_fields = []
    # Each row is let go once read, so the file's rows and the products made from them
    # are not all held at once.
    rows = payload.pop("products")
    rows.reverse()
    while rows:
        row = rows.pop()
        index, row_values, condition, row_kinds, row_fields = row[10:]
        values = [
            value if value.__class__ is str else (strings[value] if value.__class__ is int else value[0])
            for value in row_values
        ]
        fields = [resolve(slot, values) for slot in row[:10]]
        products.append(
            ProviderProduct(
                provider_key=fields[0],
                provider_product_id=fields[1],
                title=fields[2],
                brand=fields[3],
                category_text=fields[4],
                product_url=fields[5],
                image_url=fields[6],
                price_text=fields[7],
                availability_text=fields[8],
                currency=fields[9],
                raw=dict(zip(columns[index], values)),
            )
        )
        non_new.append(str(resolve(condition, values)))
        names = tuple(resolve(slot, values) for slot in row_kinds)
        kind_set = kind_sets.get(names)
        if kind_set is None:
            kind_set = kind_sets[names] = frozenset(names)
        kinds.append(kind_set)
        if field_names:
            search_fields.append(dict(zip(field_names, (resolve(slot, values) for slot in row_fields))))
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
        search_fields=tuple(search_fields),
    )
