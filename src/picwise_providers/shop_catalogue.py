"""What the shops' own catalogues say, applied to the feed's rows before they are judged.

Owner, 2026-10-26: «Θα κάνεις το 2 και το 3» -- the second being the bot for the shops
whose rows carry no category -- and «Στα θέματα αντιστοίχισης είχες αναφέρει για barcode
... για shopify, φτιάξε τους μηχανισμούς σε αυτή τη βάση και ό,τι έρθει σωστό ήρθε».

The bot (`deployment/bot/shop_catalogue_bot.py`) asks those shops, each night before the
preparation, for their Shopify catalogue, and keeps on the server (never in Supabase)
each product's type and stock under the product's name in its address. Here, for each
row of a shop the file knows:

- its stock: a product the shop's own catalogue says is sold out (all its variants, or
  the one its address names) is held back as out of stock (`SHOP_STOCK_COLUMN`, read by
  `offer_health` with the feed's own columns), while what the bot saw is at most
  `STOCK_DAYS` days old. The shop's word never shows a row the feed calls out of stock.
- its category, only for a row the feed gives none (the owner's rule of 2026-10-26 is
  for rows without a category from the shop; a row with one keeps it): the shop's own
  type becomes the row's type and category, read by the same rules as every other row's
  (`search_selection._product_concepts`), and the row joins only when that reading gives
  a kind the type names by itself; the title may narrow it ("Vacuum Cleaners", "Robot
  Vacuum Cleaner"). A type that names none ("Designer"), an accessory or a doubtful
  reading leaves the row without a category, held as before: no title alone decides
  (owner, 2026-10-26: InStock UK «συμμετέχει μόνο με τα προϊόντα που έχει σωστά»).

Then, for every shop, a row still without a category takes the category of the rows with
the same barcode (the one most of them write), under the same rule: it joins only with a
kind that category names by itself. A barcode written on more than `MAX_BARCODE_ROWS`
rows names no one product.

Without the bot's file (`PICWISE_SHOP_CATALOGUES` unset, or no file there) only the
barcode applies. What was done is counted per shop for the build's public note
(`last_shop_catalogue_note`): counts, shop names and types, never an address.

The file, gzipped JSON, version 1:

    {"version": 1, "written_at": "<UTC time>",
     "shops": {"<shop name as the feed writes it>": {
         "status": "read" | "<why not>", "read_at": "<UTC time>", ...,
         "products": {"<product name in its address>":
                      ["<type>", <1 when any variant is in stock, else 0>,
                       "<YYYY-MM-DD seen>", ["<id of a variant sold out>", ...]]}}}}
"""
from __future__ import annotations

import gzip
import heapq
import json
import os
from collections import Counter
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, unquote, urlsplit

from .contracts import ProviderProduct
from .feed_intake import _barcode, _shop_address
from .normalization import extract_merchant_name

CATALOGUES_ENV = "PICWISE_SHOP_CATALOGUES"
FILE_VERSION = 1
# The column a row's shop-said stock is written in; `offer_health` reads it.
SHOP_STOCK_COLUMN = "shop_stock"
SOLD_OUT = "sold out"
# How old what the bot saw of a product's stock may be for it to count.
STOCK_DAYS = 3
MAX_BARCODE_ROWS = 50
# How many of the types that gave no kind the note lists, the most frequent first.
_TYPES_LISTED = 10
_TYPE_LENGTH = 60

_LAST_NOTE: dict[str, Any] | None = None


def shop_name(raw: Mapping[str, Any]) -> str:
    """A row's shop as the bot's file keys it: its merchant name, spaces aside."""
    return " ".join(str(extract_merchant_name(raw) or "").split())


def product_address_name(url: str) -> tuple[str, str]:
    """The product's name in its shop's own address, Shopify's ".../products/<name>",
    and the variant the address names ("?variant=<id>"), each "" when there is none.
    An Awin link is read as text for the address it carries, never opened."""
    address = urlsplit(_shop_address(url))
    segments = [unquote(segment) for segment in address.path.split("/") if segment]
    name = ""
    for index in range(len(segments) - 2, -1, -1):
        if segments[index].lower() == "products":
            name = segments[index + 1].strip().lower()
            break
    variant = next(iter(parse_qs(address.query).get("variant", ())), "").strip()
    return name, variant if variant.isdigit() else ""


def load_shop_catalogues(path: str | os.PathLike[str] | None = None) -> tuple[dict[str, Any] | None, str]:
    """The bot's file and how it was read: "read", "none" (not configured or not
    there) or "unreadable"."""
    where = path if path is not None else os.environ.get(CATALOGUES_ENV, "").strip()
    if not where or not Path(where).is_file():
        return None, "none"
    try:
        with gzip.open(where, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, EOFError):
        return None, "unreadable"
    if not isinstance(data, dict) or data.get("version") != FILE_VERSION or not isinstance(data.get("shops"), dict):
        return None, "unreadable"
    return data, "read"


def last_shop_catalogue_note() -> dict[str, Any] | None:
    """What the last `apply_shop_catalogues` did, for the build's public note."""
    return _LAST_NOTE


def _has_kind(product: ProviderProduct) -> bool:
    """Whether the row, read as every row is, is a kind its type or category names by
    themselves: the title may narrow that kind ("Vacuum Cleaners", "Robot Vacuum
    Cleaner"), never give one alone ("Designer", "Gifts")."""
    from picwise_nlu.concept_understanding import annotate_product_concepts

    from .search_selection import _product_concepts, _product_search_fields, product_kind_key

    fields = _product_search_fields(product)
    read = {kind for kind in _product_concepts(product, fields) if not kind.startswith("__")}
    if not read:
        return False
    product_type, category, _title = product_kind_key(product, fields)
    return bool(read & {kind for kind in annotate_product_concepts(product_type, category, "") if not kind.startswith("__")})


def _with_category(product: ProviderProduct, category: str, product_type: str) -> ProviderProduct:
    raw = dict(product.raw or {})
    if product_type:
        raw["product_type"] = product_type
    return replace(product, category_text=category, raw=raw)


def _seen(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _shop_note(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": str(entry.get("status") or ""),
        "read_at": str(entry.get("read_at") or ""),
        "products": len(entry.get("products") or {}),
        "rows": 0, "matched": 0, "sold_out": 0, "sold_out_feed_in_stock": 0, "stock_too_old": 0,
        "without_category": 0, "by_type": 0, "type_no_kind": 0, "no_type": 0, "not_found": 0,
    }


_FEED_IN_STOCK = frozenset({"in stock", "instock", "in_stock", "1", "yes", "true", "available"})


def apply_shop_catalogues(
    products: Sequence[ProviderProduct],
    *,
    catalogues: Mapping[str, Any] | None = None,
    file_status: str | None = None,
    today: date | None = None,
) -> tuple[ProviderProduct, ...]:
    """The rows with what their shops' catalogues and their barcodes say (module
    docstring); the note of it is kept for `last_shop_catalogue_note`."""
    global _LAST_NOTE
    if catalogues is None and file_status is None:
        catalogues, file_status = load_shop_catalogues()
    today = today or datetime.now(timezone.utc).date()
    shops = (catalogues or {}).get("shops") or {}
    notes = {name: _shop_note(entry) for name, entry in shops.items() if isinstance(entry, Mapping)}
    types_no_kind: Counter = Counter()
    result = list(products)
    for index, product in enumerate(result):
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        name = shop_name(raw)
        entry = shops.get(name)
        if not isinstance(entry, Mapping):
            continue
        note = notes[name]
        note["rows"] += 1
        without_category = not " ".join(str(product.category_text or "").split())
        if without_category:
            note["without_category"] += 1
        handle, variant = product_address_name(product.product_url)
        known = (entry.get("products") or {}).get(handle) if handle else None
        if not isinstance(known, list) or len(known) < 4:
            if without_category:
                note["not_found"] += 1
            continue
        note["matched"] += 1
        product_type = " ".join(str(known[0] or "").split())
        seen = _seen(known[2])
        if seen is not None and (today - seen).days <= STOCK_DAYS:
            if not known[1] or (variant and variant in {str(value) for value in known[3] or ()}):
                note["sold_out"] += 1
                availability = " ".join(str(product.availability_text or "").lower().split())
                if availability in _FEED_IN_STOCK:
                    note["sold_out_feed_in_stock"] += 1
                product = replace(product, raw={**dict(raw), SHOP_STOCK_COLUMN: SOLD_OUT})
                result[index] = product
        else:
            note["stock_too_old"] += 1
        if not without_category:
            continue
        if not product_type:
            note["no_type"] += 1
            continue
        candidate = _with_category(product, product_type, product_type)
        if _has_kind(candidate):
            note["by_type"] += 1
            result[index] = candidate
        else:
            note["type_no_kind"] += 1
            types_no_kind[product_type] += 1
    barcode_note, barcode_shops = _apply_barcodes(result)
    _LAST_NOTE = {
        "file": file_status or ("read" if catalogues is not None else "none"),
        "written_at": str((catalogues or {}).get("written_at") or ""),
        "shops_known": len(notes),
        **{
            key: sum(note[key] for note in notes.values())
            for key in ("rows", "matched", "sold_out", "sold_out_feed_in_stock", "stock_too_old",
                        "without_category", "by_type", "type_no_kind", "no_type", "not_found")
        },
        "types_no_kind": [
            {"value": value if len(value) <= _TYPE_LENGTH else value[: _TYPE_LENGTH - 3] + "...", "rows": rows}
            for value, rows in heapq.nsmallest(_TYPES_LISTED, types_no_kind.items(), key=lambda item: (-item[1], item[0]))
        ],
        "barcode": barcode_note,
        "barcode_shops": barcode_shops,
        "shops": [
            {"shop": name, **note}
            for name, note in sorted(notes.items(), key=lambda item: (-item[1]["without_category"], item[0]))
        ],
    }
    return tuple(result)


def _apply_barcodes(result: list[ProviderProduct]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """A row without a category takes the category most rows with its barcode write,
    and joins only when its reading gives a kind; in place. Returns the counts, in all
    and per shop (the shops it gave a row to, the most first)."""
    rows_by_barcode: Counter = Counter()
    categories: dict[str, Counter] = {}
    barcodes: list[str] = []
    for product in result:
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        barcode = _barcode(raw)
        barcodes.append(barcode)
        if not barcode:
            continue
        rows_by_barcode[barcode] += 1
        category = " ".join(str(product.category_text or "").split())
        if category:
            product_type = " ".join(str(raw.get("product_type") or "").split())
            categories.setdefault(barcode, Counter())[(category, product_type)] += 1
    note = {"without_category": 0, "with_barcode": 0, "too_common": 0, "found": 0, "joined": 0, "no_kind": 0}
    joined_by_shop: Counter = Counter()
    for index, product in enumerate(result):
        if " ".join(str(product.category_text or "").split()):
            continue
        note["without_category"] += 1
        barcode = barcodes[index]
        if not barcode:
            continue
        note["with_barcode"] += 1
        if rows_by_barcode[barcode] > MAX_BARCODE_ROWS:
            note["too_common"] += 1
            continue
        found = categories.get(barcode)
        if not found:
            continue
        note["found"] += 1
        (category, product_type), _count = min(found.items(), key=lambda item: (-item[1], item[0]))
        candidate = _with_category(product, category, product_type)
        if _has_kind(candidate):
            note["joined"] += 1
            joined_by_shop[shop_name(product.raw if isinstance(product.raw, Mapping) else {})] += 1
            result[index] = candidate
        else:
            note["no_kind"] += 1
    shops = [{"shop": name, "joined": count} for name, count in sorted(joined_by_shop.items(), key=lambda item: (-item[1], item[0]))]
    return note, shops
