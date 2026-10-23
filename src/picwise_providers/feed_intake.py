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
"""
from __future__ import annotations

import heapq
from collections import Counter
from typing import Any, Collection, Mapping, Sequence

from .contracts import ProviderEligibilityResult
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
) -> dict[str, Any]:
    """Per shop: rows in the feed, shown, shown only when asked for, and held back, and
    what its `product_type` column carries.

    `rows` is every row of the feed as the pipeline judged it. `not_new_products` holds
    the `id()` of the products a card can show that the feed calls not new: they are
    shown only when the buyer asks for that condition. A row held back for two reasons
    counts under both.
    """
    shops: dict[str, dict[str, Any]] = {}
    totals = {"rows": 0, "shown": 0, "not_new": 0, "held": 0}
    held_reasons: Counter = Counter()
    for row in rows:
        raw = row.product.raw if isinstance(row.product.raw, Mapping) else {}
        shop = shops.setdefault(
            _shop_name(raw),
            {
                "rows": 0, "shown": 0, "not_new": 0, "held": 0, "reasons": Counter(),
                "product_types": Counter(), "product_type_without_category": 0,
            },
        )
        shop["rows"] += 1
        totals["rows"] += 1
        product_type = _product_type(raw)
        if product_type:
            shop["product_types"][product_type] += 1
            if "missing_category_text" in row.reason_codes:
                shop["product_type_without_category"] += 1
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
    return {
        **totals,
        "held_reasons": dict(held_reasons.most_common()),
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
            }
            for name, shop in sorted(shops.items(), key=lambda item: (-item[1]["rows"], item[0]))
        ],
    }
