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
"""
from __future__ import annotations

import heapq
from collections import Counter
from typing import Any, Callable, Collection, Mapping, Sequence

from picwise_nlu.concept_understanding import ACCESSORY_MARKER, UNCERTAIN_MARKER

from .contracts import ProviderEligibilityResult, ProviderProduct
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


def _hold_reasons(row: ProviderEligibilityResult) -> tuple[str, ...]:
    """Why a search cannot show this row, or () when it can."""
    if row.status != "eligible":
        held = tuple(code for code in row.reason_codes if code in _FEED_GATE_HOLDS)
        return held or (f"feed_{row.status}",)
    card = row.product_eligibility
    if card is None or card.card_eligible:
        return ()
    return tuple(card.reason_codes) or ("not_card_eligible",)


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
    for row in rows:
        raw = row.product.raw if isinstance(row.product.raw, Mapping) else {}
        shop = shops.setdefault(
            _shop_name(raw),
            {
                "rows": 0, "shown": 0, "not_new": 0, "held": 0, "reasons": Counter(),
                "product_types": Counter(), "product_type_without_category": 0,
                "without_category": {key: 0 for key in without_totals},
                "kinds": {"type": Counter(), "title": Counter()}, "types_shown": Counter(), "titles": [],
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
                },
            }
            for name, shop in sorted(shops.items(), key=lambda item: (-item[1]["rows"], item[0]))
        ],
    }
