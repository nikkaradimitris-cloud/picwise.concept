"""The checks' decisions, applied to the feed's rows before they are judged.

The checks' rules (`docs/PICWISE_CHECKS_RULES.md`, sections 6 and 9; owner, 2026-11-21:
«Ποιότητα πάνω από ποσότητα. Όποιο προϊόν δεν περνά τον έλεγχο κόβεται...»). Each night
the checks' bot (`deployment/bot/shop_checks_bot.py`) writes what the rules decided
(`picwise_checks.ledger.decisions`); here the preparation applies it, behind the one
switch of the rules' 7.7 (`data/checks_switch.json`, frozen with the code: turning it
prepares the catalogue again, so the whole catalogue is back within one preparation):

- a product cut, or of a shop out, is marked (`CHECKS_COLUMN`, with its reason), which
  `offer_health.evaluate_product_eligibility` reads as no product a card can show;
- a product a proven page reader read sold out or in stock in the last 3 days takes that
  word in `shop_stock`, as a Shopify catalogue's reading does (owner, 2026-11-12);
- a product whose shop's own page states another price, tied to its row, in a shop
  whose reader is proven, shows the page's price (owner, 2026-11-21: «Δείχνουμε την τιμή
  της σελίδας»): the shop's own price, nothing worked out; marked as the shop site's
  (`PRICE_SOURCE_COLUMN`, which starts its price's history again, `catalogue_memory`),
  its feed's sale columns let go, since the page's price is the price in force;
- the cap lets a product not shown the night before take a place only when its checks
  passed (`may_enter`), counts a product back within 7 nights as kept the night before
  (`returning_row_keys`), and names the next ones for the bot (`candidates` written by
  `tools/prepare_catalogue.py`).

With the switch off, no decisions file (`PICWISE_CHECKS_DECISIONS` unset or nothing
there), or one more than 2 nights old, nothing is applied and nothing gated: the
catalogue is as it was before the checks. What was applied is counted for the night's
public note (`last_checks_note`): counts and shop names only, never an id or an address.
"""
from __future__ import annotations

import gzip
import json
import os
from collections import Counter
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Collection, Mapping, Sequence

from .contracts import ProviderProduct
from .normalization import extract_merchant_name

CHECKS_COLUMN = "checks_cut"
PRICE_SOURCE_COLUMN = "price_source"
SHOP_SITE = "shop site"
DECISIONS_ENV = "PICWISE_CHECKS_DECISIONS"
DECISIONS_FORMAT = "picwise-checks-decisions"
SWITCH_FILE = Path(__file__).resolve().parents[2] / "data" / "checks_switch.json"
MAX_AGE_NIGHTS = 2
_SALE_COLUMNS = ("sale_price", "sale_price_effective_date")
_SHOPS_LISTED = 30
# A shop out is asked again each night by a few of its pages (rules 5.6.2): the rows of
# it the preparation names for the bot.
ROWS_OF_A_SHOP_OUT = 20

_ACTIVE: dict[str, Any] | None = None
_LAST_NOTE: dict[str, Any] | None = None
_LAST_CUT: list[ProviderProduct] = []


def checks_switch_on(path: Path = SWITCH_FILE) -> bool:
    """The switch of the rules' 7.7: true when the checks' cuts are applied."""
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("cut") is True
    except (OSError, ValueError, AttributeError):
        return False


_PRODUCT_KEY: Any = None


def _key(product: ProviderProduct) -> str:
    global _PRODUCT_KEY
    if _PRODUCT_KEY is None:
        from .catalogue_memory import product_key

        _PRODUCT_KEY = product_key
    return _PRODUCT_KEY(product)


def _shop(product: ProviderProduct) -> str:
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    return " ".join(str(extract_merchant_name(raw) or "").split())


def load_decisions(path: str | os.PathLike[str] | None = None, *, today: date | None = None,
                   ) -> tuple[dict[str, Any] | None, str]:
    """The night's decisions, or None and why not."""
    configured = path if path is not None else str(os.environ.get(DECISIONS_ENV) or "").strip()
    if not configured:
        return None, "no decisions file named"
    target = Path(configured)
    if not target.exists():
        return None, "no decisions yet"
    try:
        with gzip.open(target, "rt", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, EOFError, ValueError):
        return None, "the decisions file cannot be read"
    if not isinstance(document, dict) or document.get("format") != DECISIONS_FORMAT:
        return None, "not a decisions file"
    try:
        night = date.fromisoformat(str(document.get("night")))
    except ValueError:
        return None, "the decisions name no night"
    today = today or datetime.now(timezone.utc).date()
    if (today - night).days > MAX_AGE_NIGHTS:
        return None, f"the decisions are of {night}: too old"
    return document, "read"


def apply_checks(
    products: Sequence[ProviderProduct],
    *,
    decisions: Mapping[str, Any] | None = None,
    switch: bool | None = None,
    today: date | None = None,
) -> tuple[ProviderProduct, ...]:
    """The rows with the checks' decisions applied (module docstring)."""
    global _ACTIVE, _LAST_NOTE, _LAST_CUT
    switch = checks_switch_on() if switch is None else switch
    status = "given"
    if decisions is None and switch:
        decisions, status = load_decisions(today=today)
    if not switch or decisions is None:
        _ACTIVE, _LAST_CUT = None, []
        _LAST_NOTE = {"applied": False, "why": "the switch is off" if not switch else status}
        return tuple(products)
    shops_out: Mapping[str, str] = decisions.get("shops_out") or {}
    cut: Mapping[str, str] = decisions.get("cut") or {}
    stock: Mapping[str, list] = decisions.get("stock") or {}
    prices: Mapping[str, list] = decisions.get("prices") or {}
    counts: Counter = Counter()
    cut_by_shop: Counter = Counter()
    reasons: Counter = Counter()
    result = list(products)
    marked: list[ProviderProduct] = []
    named_of_shop: Counter = Counter()
    for index, product in enumerate(result):
        raw = dict(product.raw) if isinstance(product.raw, Mapping) else {}
        shop = _shop(product)
        if shop in shops_out:
            raw[CHECKS_COLUMN] = f"shop out: {shops_out[shop]}"
            counts["shop_out"] += 1
            named_of_shop[shop] += 1
            if named_of_shop[shop] <= ROWS_OF_A_SHOP_OUT:
                result[index] = replace(product, raw=raw)
                marked.append(result[index])
                continue
        else:
            key = _key(product)
            if key in cut:
                raw[CHECKS_COLUMN] = str(cut[key] or "failed")
                counts["cut"] += 1
                cut_by_shop[shop] += 1
                reasons[str(cut[key] or "failed")] += 1
            else:
                if key in stock:
                    raw["shop_stock"] = str(stock[key][0])
                    counts["stock_" + str(stock[key][0]).replace(" ", "_")] += 1
                if key in prices:
                    for column in _SALE_COLUMNS:
                        raw.pop(column, None)
                    raw[PRICE_SOURCE_COLUMN] = SHOP_SITE
                    result[index] = replace(product, price_text=str(prices[key][0]), raw=raw)
                    counts["price_from_site"] += 1
                    continue
                if key not in stock:
                    continue
        result[index] = replace(product, raw=raw)
        if CHECKS_COLUMN in raw:
            marked.append(result[index])
    _ACTIVE = {"enter": frozenset(decisions.get("enter") or ()), "returning": frozenset(decisions.get("returning") or ())}
    _LAST_CUT = marked
    _LAST_NOTE = {
        "applied": True,
        "night": str(decisions.get("night") or ""),
        "shops_out": dict(sorted(shops_out.items())),
        "products_of_shops_out": counts["shop_out"],
        "cut": counts["cut"],
        "cut_by_reason": dict(sorted(reasons.items())),
        "cut_by_shop": [{"shop": name, "cut": count} for name, count in cut_by_shop.most_common(_SHOPS_LISTED)],
        "price_from_site": counts["price_from_site"],
        "stock_from_page": {name[6:]: count for name, count in counts.items() if name.startswith("stock_")},
    }
    return tuple(result)


def gate_on() -> bool:
    """Whether the last `apply_checks` applied decisions, so the cap's gate is on."""
    return _ACTIVE is not None


def may_enter(product: ProviderProduct) -> bool:
    """9.4: a product not shown the night before may take a place only when its checks
    passed; every product may while the gate is off."""
    return _ACTIVE is None or _key(product) in _ACTIVE["enter"]


def returning_row_keys(products: Sequence[ProviderProduct], row_key: Any) -> frozenset[str]:
    """8.2: the cap's keys (`row_key`) of the products back within 7 nights of their cut."""
    if _ACTIVE is None or not _ACTIVE["returning"]:
        return frozenset()
    return frozenset(row_key(product) for product in products if _key(product) in _ACTIVE["returning"])


def take_cut_products() -> list[ProviderProduct]:
    """The rows the last `apply_checks` marked as cut (of a shop out, a few): the feed
    still lists them, so the bot asks them again on their schedule (rules 8.1, 5.6.2).
    Taken once, so that they are not kept in memory past the cap."""
    global _LAST_CUT
    taken, _LAST_CUT = _LAST_CUT, []
    return taken


def last_checks_note() -> dict[str, Any] | None:
    return dict(_LAST_NOTE) if _LAST_NOTE is not None else None


def reset_for_tests() -> None:
    global _ACTIVE, _LAST_NOTE, _LAST_CUT
    _ACTIVE, _LAST_NOTE, _LAST_CUT = None, None, []


def candidates_document(candidates: Collection[ProviderProduct], cut: Collection[ProviderProduct],
                        row_record: Any, row_of: Any) -> dict[str, Any]:
    """What the preparation writes for the bot (`candidates.json.gz`): the rows of the
    cap's candidates and of the cut products the feed still lists."""
    rows: dict[str, list] = {}
    for product in list(candidates) + list(cut):
        row = row_of(product)
        rows.setdefault(row.key, row_record(row))
    return {
        "format": "picwise-checks-candidates",
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidates": sorted({row_of(product).key for product in candidates}),
        "rows": [rows[key] for key in sorted(rows)],
    }
