"""How fresh a feed's listings are: measured, not yet a rule.

Owner, 2026-10-18: most products the live site shows are out of stock on the shop's own
page, at prices that give them away as old listings -- "we show ghosts". The feed's
`in_stock` says yes on every row, so it says nothing, and price first brings the
cheapest forward, which is often a listing a shop forgot. Two columns an Awin feed can
carry speak to it, and PicWise reads neither yet:

- `last_updated`: when the shop last updated the listing;
- `stock_quantity`: how many it has, where 0 means none.

Before either becomes a rule (the owner's decision: which age is too old), this
measures what each would remove on the real feed. The deployment's build writes it
into its public note (`tools/prepare_catalogue.py --static-dir`), which the owner can
open; it holds counts, dates and shop names, never the feed's link.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from statistics import median
from typing import Any, Mapping, Sequence

from .contracts import ProviderProduct
from .normalization import extract_merchant_name

AGE_THRESHOLDS_DAYS = (7, 30, 90, 180, 365)
_DATE_RE = re.compile(r"\s*(\d{4})-(\d{2})-(\d{2})")
_QUANTITY_RE = re.compile(r"\s*(-?\d+(?:\.\d+)?)\s*$")
_EXAMPLES = 3
_TOP_VALUES = 5


def _listing_date(value: object) -> date | None:
    match = _DATE_RE.match(str(value or ""))
    if match is None:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _quantity(value: object) -> float | None:
    match = _QUANTITY_RE.match(str(value or ""))
    return float(match.group(1)) if match else None


def _top_values(values: Counter) -> list[list[Any]]:
    return [[value, count] for value, count in values.most_common(_TOP_VALUES)]


def measure_feed_freshness(products: Sequence[ProviderProduct], *, today: date) -> dict[str, Any]:
    """What `last_updated` and `stock_quantity` say about these products, in counts.

    Ages are whole days before `today`; a date after it counts as 0 days old.
    """
    ages: list[int] = []
    no_date = 0
    unreadable_dates: Counter = Counter()
    quantities = Counter()
    stock_values: dict[str, Counter] = {"in_stock": Counter(), "stock_status": Counter()}
    shops: dict[str, dict[str, Any]] = {}
    for product in products:
        raw: Mapping[str, Any] = product.raw if isinstance(product.raw, Mapping) else {}
        shop_name = " ".join(str(extract_merchant_name(raw) or "?").split())
        shop = shops.setdefault(shop_name, {"products": 0, "ages": [], "stock_quantity_zero": 0, "stock_status_filled": 0})
        shop["products"] += 1

        text = str(raw.get("last_updated") or "").strip()
        listed = _listing_date(text) if text else None
        if not text:
            no_date += 1
        elif listed is None:
            unreadable_dates[text[:25]] += 1
        else:
            age = max(0, (today - listed).days)
            ages.append(age)
            shop["ages"].append(age)

        quantity_text = str(raw.get("stock_quantity") or "").strip()
        if quantity_text:
            quantity = _quantity(quantity_text)
            if quantity is None:
                quantities["unreadable"] += 1
            elif quantity <= 0:
                quantities["zero_or_less"] += 1
                shop["stock_quantity_zero"] += 1
            else:
                quantities["positive"] += 1

        for column, values in stock_values.items():
            value = " ".join(str(raw.get(column) or "").lower().split())
            if value:
                values[value] += 1
                if column == "stock_status":
                    shop["stock_status_filled"] += 1

    return {
        "products": len(products),
        "last_updated": {
            "dated": len(ages),
            "no_date": no_date,
            "unreadable": sum(unreadable_dates.values()),
            "unreadable_examples": [value for value, _count in unreadable_dates.most_common(_EXAMPLES)],
            "median_age_days": median(ages) if ages else None,
            "older_than_days": {
                str(days): sum(1 for age in ages if age > days) for days in AGE_THRESHOLDS_DAYS
            },
        },
        "stock_quantity": {
            "filled": sum(quantities.values()),
            "zero_or_less": quantities["zero_or_less"],
            "positive": quantities["positive"],
            "unreadable": quantities["unreadable"],
        },
        "stock_values": {column: _top_values(values) for column, values in stock_values.items()},
        "shops": [
            {
                "shop": name,
                "products": shop["products"],
                "dated": len(shop["ages"]),
                "median_age_days": median(shop["ages"]) if shop["ages"] else None,
                "older_than_90_days": sum(1 for age in shop["ages"] if age > 90),
                "stock_quantity_zero": shop["stock_quantity_zero"],
                "stock_status_filled": shop["stock_status_filled"],
            }
            for name, shop in sorted(shops.items(), key=lambda item: -item[1]["products"])
        ],
    }
