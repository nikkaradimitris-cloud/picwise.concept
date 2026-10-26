"""What each shop's feed brings in, and why the rest is held back: measured, not a rule.

Owner, 2026-10-18: first many more shops, "with whatever each one's feed sends"; then
a check of each shop. Shops differ in what they send (one sends no category, another
no image, another no description), and the rules that keep a product off the page
apply to all of them alike. Before many shops come in, this says per shop how many of
its rows a search can show, how many only when the buyer asks for a used or
refurbished one, and why each of the others is held back, so the choice of shops (and
of any rule) rests on counts.

The deployment's build writes it into its public note (`tools/prepare_catalogue.py
--static-dir`), which holds counts and shop names, never the feed's link. Nothing
shown changes.

Owner, 2026-10-23: also, per shop, how many rows write something in `product_type`,
with a few of its values. Back to the Office sends 93,726 of its 95,161 live rows
without `google_product_category`, so they are held; whether its `product_type` names
their category is the question before any rule reads it. Measured only: no search reads
it from here.

Owner, 2026-10-25, with every Google-format shop on the server: about 532,000 of its
1,123,857 rows have no category, so «να μη χάνουμε τόσο μεγάλο όγκο». Per shop, of the
rows the feed gate holds for that alone, how many a search could show if their category
came from elsewhere, today's other checks passed (in stock, a price, an image): from the
shop's own `product_type`, or, with none, from the title alone; and what a search would
read them as, a kind, an accessory, doubtful or nothing, with a few of their types and
titles. Measured only: whether a feed tells the truth about stock is the shop checks' to
say.

Owner, 2026-10-26: «Ο στόχος είναι να λύσεις αυτό το πρόβλημα», without the shops' help
(«δεν στηρίζομαι σε αυτούς»). So, of those rows a search could show by their title, the
note also says where else a category may hide: which columns the rows fill, the most
frequent values of the columns named like a label, a category, a type, a department, a
section, a collection or a tag, and what the shop's own address of the product names
before the product (`/kitchen/kettles/...`), read as a shelf, and whether it agrees with
the title. An Awin link is read as text for the address it carries, never opened.
"""
from __future__ import annotations

import heapq
import re
from collections import Counter
from typing import Any, Callable, Collection, Mapping, Sequence
from urllib.parse import parse_qs, unquote, urlsplit

from picwise_nlu.concept_understanding import (
    ACCESSORY_MARKER,
    UNCERTAIN_MARKER,
    annotate_product_concepts,
)
from picwise_nlu.product_concepts import broader_concepts

from .contracts import ProviderEligibilityResult, ProviderProduct
from .kind_check import description_lead
from .normalization import extract_merchant_name

# The feed gate (`eligibility.py`) holds a row back for these; its other codes only
# describe the row ("category_text_present").
_FEED_GATE_HOLDS = frozenset(
    {
        "missing_provider_key",
        "missing_title",
        "missing_product_url",
        "invalid_product_url",
        "missing_provider_product_id",
        "missing_category_text",
        "missing_image_url",
        "missing_price_text",
        "missing_availability_text",
    }
)


# How many of a shop's `product_type` values the note shows, the most frequent first,
# and how long each may be.
_PRODUCT_TYPE_EXAMPLES = 5
_PRODUCT_TYPE_EXAMPLE_LENGTH = 100
# Of a shop's rows held only for having no category and shown otherwise, how many of
# their product types the note shows, and how many titles read as a kind without one.
_WITHOUT_CATEGORY_TYPES = 3
_WITHOUT_CATEGORY_TITLES = 3
_TITLE_EXAMPLE_LENGTH = 70
# What a search would read a product as.
_KIND_BUCKETS = ("kind", "accessory", "doubtful", "none")
# Where else a row without a category may name one: columns named like these, and the
# shop's own address. How many columns, values and address shelves the note shows.
_HINT_COLUMN_RE = re.compile(r"label|categ|type|department|section|collection|tag", flags=re.IGNORECASE)
_COLUMNS_LISTED = 15
_HINT_COLUMNS = 6
_HINT_VALUES = 3
_HINT_VALUE_LENGTH = 60
_ADDRESS_PATHS = 5
# The columns a feed writes a product's barcode in.
_BARCODE_COLUMNS = ("gtin", "ean", "upc", "barcode", "isbn")


def _shop_name(raw: Mapping[str, Any]) -> str:
    return " ".join(str(extract_merchant_name(raw) or "?").split())


def _product_type(raw: Mapping[str, Any]) -> str:
    return " ".join(str(raw.get("product_type") or "").split())


def _product_type_note(values: Counter, without_category: int) -> dict[str, Any]:
    """How many rows write a `product_type`, how many of them have no category, and
    the most frequent values."""
    examples = heapq.nsmallest(_PRODUCT_TYPE_EXAMPLES, values.items(), key=lambda item: (-item[1], item[0]))
    return {
        "filled": sum(values.values()),
        "filled_without_category": without_category,
        "examples": [
            {
                "value": value
                if len(value) <= _PRODUCT_TYPE_EXAMPLE_LENGTH
                else value[: _PRODUCT_TYPE_EXAMPLE_LENGTH - 3] + "...",
                "rows": count,
            }
            for value, count in examples
        ],
    }


def _cut(text: str, length: int) -> str:
    return text if len(text) <= length else text[: length - 3] + "..."


def _top_values(values: Counter, count: int, length: int) -> list[dict[str, Any]]:
    return [
        {"value": _cut(value, length), "rows": rows}
        for value, rows in heapq.nsmallest(count, values.items(), key=lambda item: (-item[1], item[0]))
    ]


def _kind_bucket(kinds: Collection[str]) -> str:
    if any(not kind.startswith("__") for kind in kinds):
        return "kind"
    if ACCESSORY_MARKER in kinds:
        return "accessory"
    if UNCERTAIN_MARKER in kinds:
        return "doubtful"
    return "none"


def _buckets(counts: Counter | None) -> dict[str, int] | None:
    return None if counts is None else {bucket: counts.get(bucket, 0) for bucket in _KIND_BUCKETS}


def _way_without_category(row: ProviderEligibilityResult, product_type: str) -> str:
    """For a row held only for having no category: "type" when the card gate passes it on
    its product type, "title" when it has none and the card gate holds it for that alone,
    or "" when another reason would hold it anyway."""
    card = row.product_eligibility
    if card is None:
        return ""
    if product_type:
        return "type" if card.card_eligible else ""
    return "title" if set(card.reason_codes) == {"missing_product_type_or_category_evidence"} else ""


def _shop_address(url: str) -> str:
    """The shop's own address of a product: the link itself, or the address an Awin link
    carries in its query ("ued", "p"), read as text; "" when it carries none ("pclick.php")."""
    parts = urlsplit(str(url or "").strip())
    if "awin1.com" not in parts.netloc.lower():
        return str(url or "").strip()
    query = parse_qs(parts.query)
    for key in ("ued", "p"):
        for value in query.get(key, ()):
            if value.lower().startswith("http"):
                return value
    return ""


def _address_shelves(url: str) -> str:
    """The shelves a shop's address names before its product, as a breadcrumb: ".../
    kitchen/kettles/fixturon-glass-kettle" is "kitchen > kettles"; "" when it names
    none. Words only, never the address: the note holds no link."""
    address = _shop_address(url)
    if not address:
        return ""
    segments = [segment for segment in urlsplit(address).path.lower().split("/") if segment]
    shelves = [" ".join(re.split(r"[-_+]+", unquote(segment))).strip() for segment in segments[:-1]]
    return " > ".join(shelf for shelf in shelves if shelf)


def _barcode(raw: Mapping[str, Any]) -> str:
    """A row's barcode as digits without leading zeros, so a GTIN-14 meets its GTIN-13;
    "" when it writes none of at least 8 digits."""
    for column in _BARCODE_COLUMNS:
        digits = re.sub(r"\D", "", str(raw.get(column) or ""))
        if len(digits) >= 8:
            return digits.lstrip("0")
    return ""


def _related(left: Collection[str], right: Collection[str]) -> bool:
    return any(a == b or a in broader_concepts(b) or b in broader_concepts(a) for a in left for b in right)


def _hint_note(hints: dict[str, Any]) -> dict[str, Any]:
    columns = hints["columns"]
    named = sorted((column for column in columns if _HINT_COLUMN_RE.search(column)), key=lambda c: (-columns[c], c))
    return {
        "columns": [
            {"column": column, "rows": rows}
            for column, rows in heapq.nsmallest(_COLUMNS_LISTED, columns.items(), key=lambda item: (-item[1], item[0]))
        ],
        "values": {
            column: _top_values(hints["values"][column], _HINT_VALUES, _HINT_VALUE_LENGTH)
            for column in named[:_HINT_COLUMNS]
            if column in hints["values"]
        },
        "address": dict(hints["address"]),
        "address_shelves": _top_values(hints["paths"], _ADDRESS_PATHS, _HINT_VALUE_LENGTH),
        "barcode": dict(hints["barcode"]),
        "description": dict(hints["description"]),
    }


def _hold_reasons(row: ProviderEligibilityResult) -> tuple[str, ...]:
    """Why a search cannot show this row, or () when it can."""
    if row.status != "eligible":
        held = tuple(code for code in row.reason_codes if code in _FEED_GATE_HOLDS)
        return held or (f"feed_{row.status}",)
    card = row.product_eligibility
    if card is None or card.card_eligible:
        return ()
    return tuple(card.reason_codes) or ("not_card_eligible",)


# What each other place a category may hide in gave, per row a search could show by its
# title: the shop's address, another row's category for the same barcode, the
# description's first sentence where the title gives no kind.
_ADDRESS_KEYS = ("rows", "names_shelves", "a_kind", "title_kind_too", "agrees")
_BARCODE_KEYS = ("rows", "with_barcode", "found_with_category", "a_kind", "title_kind_too", "agrees", "title_gives_none")
_DESCRIPTION_KEYS = ("title_gives_none", "description_gives")


def _empty_hint_counts() -> dict[str, dict[str, int]]:
    return {
        "address": dict.fromkeys(_ADDRESS_KEYS, 0),
        "barcode": dict.fromkeys(_BARCODE_KEYS, 0),
        "description": dict.fromkeys(_DESCRIPTION_KEYS, 0),
    }


def _real(kinds: Collection[str]) -> list[str]:
    return [kind for kind in kinds if not kind.startswith("__")]


def _count_hints(
    hints: dict[str, Any],
    totals: dict[str, dict[str, int]],
    raw: Mapping[str, Any],
    product: ProviderProduct,
    title_kinds: Collection[str],
    categories_by_barcode: Mapping[str, str],
) -> None:
    """Where else a row a search could show by its title may name its category: its
    filled columns, the values of those named like a category, its shop's address, the
    category another row with its barcode has, and its description's first sentence."""
    for column, value in raw.items():
        text = " ".join(str(value or "").split())
        if not text:
            continue
        hints["columns"][column] += 1
        if _HINT_COLUMN_RE.search(str(column)) and "://" not in text and not text.lower().startswith("www."):
            hints["values"].setdefault(column, Counter())[text] += 1

    def count(place: str, key: str) -> None:
        for counts in (hints[place], totals[place]):
            counts[key] += 1

    by_title = _real(title_kinds)

    def count_kinds(place: str, kinds: list[str]) -> None:
        if not kinds:
            return
        count(place, "a_kind")
        if by_title:
            count(place, "title_kind_too")
            if _related(kinds, by_title):
                count(place, "agrees")
        elif place == "barcode":
            count(place, "title_gives_none")

    count("address", "rows")
    shelves = _address_shelves(product.product_url)
    if shelves:
        hints["paths"][shelves] += 1
        count("address", "names_shelves")
        count_kinds("address", _real(annotate_product_concepts("", shelves, "")))
    count("barcode", "rows")
    barcode = _barcode(raw)
    if barcode:
        count("barcode", "with_barcode")
        borrowed = categories_by_barcode.get(barcode, "")
        if borrowed:
            count("barcode", "found_with_category")
            count_kinds("barcode", _real(annotate_product_concepts("", borrowed.lower(), str(product.title or ""))))
    if not by_title:
        count("description", "title_gives_none")
        if _real(annotate_product_concepts("", "", description_lead(str(raw.get("description") or "")))):
            count("description", "description_gives")


def measure_feed_intake(
    rows: Sequence[ProviderEligibilityResult],
    *,
    not_new_products: Collection[int] = (),
    read_kinds: Callable[[ProviderProduct], Collection[str]] | None = None,
) -> dict[str, Any]:
    """Per shop: rows in the feed, shown, shown only when asked for, and held back, and
    what its `product_type` column carries; and of its rows without a category, how many
    could be shown by their product type or by their title, read as what.

    `rows` is every row of the feed as the pipeline judged it. `not_new_products` holds
    the `id()` of the products a card can show that the feed calls not new: they are
    shown only when the buyer asks for that condition. A row held back for two reasons
    counts under both. `read_kinds` reads a product's kinds as the search does; without
    it, no kind is counted.
    """
    shops: dict[str, dict[str, Any]] = {}
    totals = {"rows": 0, "shown": 0, "not_new": 0, "held": 0}
    held_reasons: Counter = Counter()
    without_totals = {"rows": 0, "only_this": 0, "with_product_type": 0, "shown_by_type": 0, "shown_by_title": 0}
    kinds_totals = {"type": Counter(), "title": Counter()}
    hint_totals = _empty_hint_counts()
    # Another row's category for the same barcode: the first category written for it.
    categories_by_barcode: dict[str, str] = {}
    for row in rows:
        category = str(row.product.category_text or "").strip()
        barcode = _barcode(row.product.raw) if category and isinstance(row.product.raw, Mapping) else ""
        if barcode:
            categories_by_barcode.setdefault(barcode, category)
    for row in rows:
        raw = row.product.raw if isinstance(row.product.raw, Mapping) else {}
        shop = shops.setdefault(
            _shop_name(raw),
            {
                "rows": 0, "shown": 0, "not_new": 0, "held": 0, "reasons": Counter(),
                "product_types": Counter(), "product_type_without_category": 0,
                "without_category": {key: 0 for key in without_totals},
                "kinds": {"type": Counter(), "title": Counter()}, "types_shown": Counter(), "titles": [],
                "hints": {"columns": Counter(), "values": {}, "paths": Counter(), **_empty_hint_counts()},
            },
        )
        shop["rows"] += 1
        totals["rows"] += 1
        product_type = _product_type(raw)
        if product_type:
            shop["product_types"][product_type] += 1
            if "missing_category_text" in row.reason_codes:
                shop["product_type_without_category"] += 1
        if "missing_category_text" in row.reason_codes:
            without = shop["without_category"]
            for bucket in (without, without_totals):
                bucket["rows"] += 1
            if {code for code in row.reason_codes if code in _FEED_GATE_HOLDS} == {"missing_category_text"}:
                for bucket in (without, without_totals):
                    bucket["only_this"] += 1
                    if product_type:
                        bucket["with_product_type"] += 1
                way = _way_without_category(row, product_type)
                if way:
                    for bucket in (without, without_totals):
                        bucket[f"shown_by_{way}"] += 1
                    if way == "type":
                        shop["types_shown"][product_type] += 1
                    kinds: Collection[str] = ()
                    if read_kinds is not None:
                        kinds = read_kinds(row.product)
                        kind = _kind_bucket(kinds)
                        shop["kinds"][way][kind] += 1
                        kinds_totals[way][kind] += 1
                        if way == "title" and kind == "kind" and len(shop["titles"]) < _WITHOUT_CATEGORY_TITLES:
                            named = ", ".join(sorted(k for k in kinds if not k.startswith("__")))
                            shop["titles"].append(
                                f"{_cut(' '.join(str(row.product.title or '').split()), _TITLE_EXAMPLE_LENGTH)}"
                                f" -> {named}"
                            )
                    if way == "title":
                        _count_hints(shop["hints"], hint_totals, raw, row.product, kinds, categories_by_barcode)
        reasons = _hold_reasons(row)
        if reasons:
            for bucket in (shop, totals):
                bucket["held"] += 1
            shop["reasons"].update(reasons)
            held_reasons.update(reasons)
        elif id(row.product) in not_new_products:
            shop["not_new"] += 1
            totals["not_new"] += 1
        else:
            shop["shown"] += 1
            totals["shown"] += 1
    read = read_kinds is not None
    return {
        **totals,
        "held_reasons": dict(held_reasons.most_common()),
        "without_category": {
            **without_totals,
            "kinds_by_type": _buckets(kinds_totals["type"] if read else None),
            "kinds_by_title": _buckets(kinds_totals["title"] if read else None),
            **hint_totals,
        },
        "shops": [
            {
                "shop": name,
                "rows": shop["rows"],
                "shown": shop["shown"],
                "not_new": shop["not_new"],
                "held": shop["held"],
                "held_reasons": dict(shop["reasons"].most_common()),
                "product_type": _product_type_note(
                    shop["product_types"], shop["product_type_without_category"]
                ),
                "without_category": {
                    **shop["without_category"],
                    "kinds_by_type": _buckets(shop["kinds"]["type"] if read else None),
                    "kinds_by_title": _buckets(shop["kinds"]["title"] if read else None),
                    "types": _top_values(shop["types_shown"], _WITHOUT_CATEGORY_TYPES, _PRODUCT_TYPE_EXAMPLE_LENGTH),
                    "titles": shop["titles"],
                    "hints": _hint_note(shop["hints"]),
                },
            }
            for name, shop in sorted(shops.items(), key=lambda item: (-item[1]["rows"], item[0]))
        ],
    }
