"""What the checks remember from night to night, and what the preparation reads.

The ledger (rules 11) is kept on the server beside the catalogue's memory, never in the
repo or in a public place: per product (its shop and id, `catalogue_memory.product_key`)
its page's verdict, when it was asked, how many nights it has failed, when it is due
again, the site's price and stock read; per shop its reader and whether it is proven,
whether it can be checked and its day, Awin's word, its feed's last import; per night
what each brake held.

`record_night` takes one night's readings, applies the rules in their order (the shops,
Awin, the products, the brakes, the first rounds) and returns the night's note: counts
and shop names only. `decisions` is what the preparation reads
(`picwise_providers.checks_applied`); `asking_order` is the order the bot asks in
(rules 10). Each step is pinned by a test named after its section
(`tests/test_picwise_checks_ledger.py`).
"""
from __future__ import annotations

import gzip
import json
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import astuple, dataclass, field, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Collection, Iterable, Mapping

from . import brakes
from .verdicts import ANOTHER_PRODUCT, FAILED, GONE, PASSED, Row, ShopNight, Verdict, awin_out, feed_is_old
from .verdicts import far_apart, same_price, shop_checkable

FORMAT = "picwise-checks-ledger"
VERSION = 1
DECISIONS_FORMAT = "picwise-checks-decisions"
LEDGER_NAME = "ledger.json.gz"
DECISIONS_NAME = "decisions.json.gz"
CANDIDATES_NAME = "candidates.json.gz"
NIGHTS_KEPT = 30
RATIOS_KEPT = 60

# A product's state in the ledger.
HELD = "held"
# Which brake holds a product.
BY_SHOP = "shop"
BY_OWNER = "owner"
BY_KIND = "kind"
BY_NIGHT = "night"
BY_STOP = "stopped"

# 8.1: asked again the next night and the two after, then every 7 nights; gone and
# another product after 7 nights, then every 30.
AGAIN_NIGHTS = 3
AGAIN_EVERY = 7
GONE_FIRST = 7
GONE_EVERY = 30
# 8.2: a product that passes again within 7 nights of its cut keeps its place.
KEEPS_PLACE_NIGHTS = 7
# 9.1 and 9.3.
PASS_VALID_NIGHTS = 30
FIRST_ROUND_NIGHTS = 14
# 5.6.2.
OUT_ON_DAY = 15
FRESH_AFTER_CHECKED = 7
# 5.2: a reading of the shop's own site decides stock for 3 days.
STOCK_DAYS = 3
# 10.4 and 10.5.
CHEAPEST_FIRST = 24
OLD_PASS_FIRST = 14


def _day(value: str) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _iso(value: date) -> str:
    return value.isoformat()


@dataclass(slots=True)
class Product:
    """One product's checks (rules 11). Dates are the nights, "YYYY-MM-DD"."""

    shop: str
    state: str = ""
    reason: str = ""
    asked: str = ""
    fails: int = 0
    due: str = ""
    by: str = ""
    passed_on: str = ""
    cut_on: str = ""
    held: str = ""
    site_price: str = ""
    feed_price: str = ""
    price_on: str = ""
    tie: str = ""
    stock: str = ""
    stock_on: str = ""
    sig: str = ""


@dataclass(slots=True)
class Shop:
    """One shop's checks (rules 11)."""

    reader: str = ""
    passes: int = 0
    proof: list = field(default_factory=list)
    stock_proof: list = field(default_factory=list)
    ratios: list = field(default_factory=list)
    days: int = 0
    streak: int = 0
    why: str = ""
    out: str = ""
    awin: str = ""
    link: str = ""
    feed_import: str = ""
    first_night: str = ""
    round_over: str = ""
    owner_hold: bool = False


_PRODUCT_FIELDS = tuple(item.name for item in fields(Product))
_SHOP_FIELDS = tuple(item.name for item in fields(Shop))


@dataclass
class Ledger:
    products: dict[str, Product] = field(default_factory=dict)
    shops: dict[str, Shop] = field(default_factory=dict)
    nights: list[dict[str, Any]] = field(default_factory=list)

    def shop(self, name: str) -> Shop:
        entry = self.shops.get(name)
        if entry is None:
            entry = self.shops[name] = Shop()
        return entry


@dataclass(frozen=True)
class Reading:
    """One product asked tonight: its page's verdict and what was read on it."""

    page: Verdict
    site_price: float | None = None
    tie: str = ""
    stock: str = ""


def row_signature(row: Row) -> str:
    """What changes in a feed row that makes its checks old (8.1, 10.2): its price, its
    address, its photo's address."""
    price = "" if row.price is None else f"{row.price:.2f}"
    return f"{price}|{row.address}|{row.photo}"


# ---- reading and writing -----------------------------------------------------------


def load(path: Path) -> Ledger:
    """The ledger at `path`; an empty one when there is none yet. A file that cannot be
    read raises: the night stops rather than start from nothing."""
    if not path.exists():
        return Ledger()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("format") != FORMAT or payload.get("version") != VERSION:
        raise ValueError("not a ledger of this version")
    return Ledger(
        products={key: Product(*values) for key, values in payload.get("products", {}).items()},
        shops={name: Shop(**{k: v for k, v in values.items() if k in _SHOP_FIELDS})
               for name, values in payload.get("shops", {}).items()},
        nights=list(payload.get("nights", [])),
    )


def _write_gzip_json(document: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False)
    try:
        with gzip.open(handle, "wt", encoding="utf-8") as zipped:
            json.dump(document, zipped, separators=(",", ":"), sort_keys=True)
        handle.close()
        os.replace(handle.name, path)
    except BaseException:
        handle.close()
        os.unlink(handle.name)
        raise


def save(ledger: Ledger, path: Path) -> None:
    """Written whole, replaced at once."""
    _write_gzip_json(
        {
            "format": FORMAT,
            "version": VERSION,
            "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "products": {key: list(astuple(product)) for key, product in ledger.products.items()},
            "shops": {name: {k: getattr(shop, k) for k in _SHOP_FIELDS} for name, shop in ledger.shops.items()},
            "nights": ledger.nights[-NIGHTS_KEPT:],
        },
        path,
    )


# ---- coming back (8) --------------------------------------------------------------


def due_after(reason: str, fails: int, night: date) -> date:
    """8.1: when a failed product is asked again."""
    if reason in (GONE, ANOTHER_PRODUCT):
        return night + timedelta(days=GONE_FIRST if fails <= 1 else GONE_EVERY)
    return night + timedelta(days=1 if fails <= AGAIN_NIGHTS else AGAIN_EVERY)


# ---- the night (5, 7, 8, 9) -------------------------------------------------------


def _shop_night(ledger: Ledger, name: str, night: date, tonight: ShopNight) -> tuple[bool, str]:
    """5.6.2: a shop's day while it cannot be checked; out on day 15; back the first
    night a product is read on it; the count afresh only after 7 nights checked in a
    row, a shop that falls back sooner going on from the day it had reached."""
    shop = ledger.shop(name)
    shop.first_night = shop.first_night or _iso(night)
    checkable, why = shop_checkable(tonight)
    if checkable:
        shop.streak += 1
        if shop.streak >= FRESH_AFTER_CHECKED:
            shop.days, shop.why = 0, ""
        if shop.out.startswith("cannot be checked"):
            shop.out = ""
        if tonight.catalogue_read:
            shop.reader = "shopify"
        elif tonight.pages_read:
            shop.reader = "page"
    else:
        shop.streak = 0
        shop.days += 1
        shop.why = why
        if shop.days >= OUT_ON_DAY and not shop.out:
            shop.out = f"cannot be checked: {why}"
    return checkable, why


def _awin(ledger: Ledger, awin: Mapping[str, tuple[str | None, str]], shown_by_shop: Mapping[str, int],
          shown: int, owner_awin_word: bool) -> dict[str, Any]:
    """5.6.3: Awin's reading put on each shop of the catalogue; a reading that would put
    out many shops at once waits for the owner's word."""
    newly: dict[str, str] = {}
    for name in shown_by_shop:
        relationship, link = awin.get(name, (None, ""))
        shop = ledger.shop(name)
        shop.awin, shop.link = relationship or "", link or ""
        reason = awin_out(relationship, link)
        if reason and not shop.out:
            newly[name] = reason
        elif not reason and shop.out.startswith("Awin"):
            shop.out = ""
    products_out = sum(shown_by_shop.get(name, 0) for name in newly)
    waits = bool(newly) and brakes.awin_waits(len(newly), products_out, shown) and not owner_awin_word
    if not waits:
        for name, reason in newly.items():
            ledger.shop(name).out = reason
    return {"newly_out": sorted(newly), "products": products_out, "waits": waits}


@dataclass
class Night:
    """What `record_night` gives back: the night's note (counts and shop names only)
    and the products that passed again within 7 nights of their cut (8.2)."""

    note: dict[str, Any]
    came_back: list[str] = field(default_factory=list)


def record_night(
    ledger: Ledger,
    night: date,
    rows: Mapping[str, Row],
    readings: Mapping[str, Reading],
    shop_nights: Mapping[str, ShopNight],
    *,
    shown: Collection[str],
    parts: Mapping[str, str] | None = None,
    awin: Mapping[str, tuple[str | None, str]] | None = None,
    feeds: Mapping[str, date | None] | None = None,
    owner_cut_shops: Collection[str] = (),
    owner_awin_word: bool = False,
) -> Night:
    """One night's readings into the ledger, by the rules' order.

    `rows`: the feed's rows the bot knew tonight (the shown ones, the cap's candidates,
    the cut ones the feed still lists); `readings`: the products asked; `shop_nights`:
    what asking each shop gave; `shown`: the keys the site shows (the prepared
    catalogue); `parts`: each shown key's kind as the cap reads it
    (`catalogue_cap.part_of`); `awin`: Awin's relationship and link status per shop,
    None when its API did not answer; `feeds`: each shop's feed's last import;
    `owner_cut_shops`: the shops whose products held for the owner he said to cut
    («κόψε»); `owner_awin_word`: his word on a reading of Awin that waits."""
    tonight = _iso(night)
    parts = parts or {}
    shown = frozenset(shown)
    shown_by_shop: Counter = Counter(rows[key].shop for key in shown if key in rows)
    note: dict[str, Any] = {"night": tonight, "shops_asked": len(shop_nights)}

    # 7.1: a round most shops did not answer is ours, and records nothing.
    answered = sum(1 for item in shop_nights.values() if item.catalogue_read or item.requests > item.refused)
    if brakes.round_is_ours(len(shop_nights), answered):
        note["ours"] = True
        ledger.nights.append({"night": tonight, "ours": True, "night_brake": False})
        ledger.nights = ledger.nights[-NIGHTS_KEPT:]
        return Night(note)

    # The shops (5.6.2), Awin (5.6.3), the feeds' ages (5.6.4).
    cannot = {}
    for name, item in shop_nights.items():
        checkable, why = _shop_night(ledger, name, night, item)
        if not checkable:
            cannot[name] = why
    note["cannot_be_checked"] = {name: [why, ledger.shop(name).days] for name, why in sorted(cannot.items())}
    if awin is not None:
        note["awin"] = _awin(ledger, awin, shown_by_shop, len(shown), owner_awin_word)
    for name, imported in (feeds or {}).items():
        ledger.shop(name).feed_import = _iso(imported) if imported else ""

    # The products (5, 8).
    decided: Counter = Counter()
    new_failures: dict[str, list[str]] = defaultdict(list)
    owner_repeats: list[str] = []
    came_back: list[str] = []
    passed_now: Counter = Counter()
    failed_by_reason: Counter = Counter()
    proof_tonight: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    stock_tonight: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for key, reading in readings.items():
        row = rows.get(key)
        if row is None:
            continue
        product = ledger.products.get(key)
        if product is None:
            product = ledger.products[key] = Product(shop=row.shop)
        product.asked = tonight
        product.sig = row_signature(row)
        verdict = reading.page
        if reading.site_price is not None and row.price:
            if verdict.state == PASSED and far_apart(reading.site_price, row.price):
                verdict = Verdict(FAILED, "price far apart")
            product.site_price = f"{reading.site_price:.2f}"
            product.feed_price = f"{row.price:.2f}"
            product.price_on, product.tie = tonight, reading.tie
            proof_tonight[row.shop][0] += 1
            proof_tonight[row.shop][1] += same_price(reading.site_price, row.price)
            shop = ledger.shop(row.shop)
            shop.ratios = (shop.ratios + [[reading.site_price, row.price]])[-RATIOS_KEPT:]
        if reading.stock:
            product.stock, product.stock_on = reading.stock, tonight
            if row.feed_stock:
                stock_tonight[row.shop][0] += 1
                stock_tonight[row.shop][1] += reading.stock == row.feed_stock
        if verdict.state == PASSED:
            decided[row.shop] += 1
            passed_now[row.shop] += 1
            cut = _day(product.cut_on)
            if cut is not None and (night - cut).days <= KEEPS_PLACE_NIGHTS:
                came_back.append(key)
            product.state, product.reason, product.fails, product.due = PASSED, "", 0, ""
            product.by, product.passed_on, product.held, product.cut_on = verdict.by, tonight, "", ""
        elif verdict.state == FAILED:
            decided[row.shop] += 1
            failed_by_reason[verdict.reason] += 1
            was_state, was_held = product.state, product.held
            product.fails += 1
            product.reason = verdict.reason
            product.due = _iso(due_after(verdict.reason, product.fails, night))
            product.state, product.held = FAILED, ""
            if was_state == HELD and was_held == BY_OWNER:
                owner_repeats.append(key)
            elif was_state not in (FAILED, HELD):
                new_failures[row.shop].append(key)
    for name, (tied, same) in proof_tonight.items():
        shop = ledger.shop(name)
        shop.proof = (shop.proof + [[tonight, tied, same]])[-brakes.PROOF_NIGHTS:]
    for name, (tied, same) in stock_tonight.items():
        shop = ledger.shop(name)
        shop.stock_proof = (shop.stock_proof + [[tonight, tied, same]])[-brakes.PROOF_NIGHTS:]
    for name, passes in passed_now.items():
        ledger.shop(name).passes += passes

    # The brakes (7.2, 7.3, 7.4): a held product is kept as it was and asked first.
    held: Counter = Counter()
    braked_shops = []
    for name, keys in new_failures.items():
        brake = brakes.shop_brake(decided[name], len(keys), ledger.shop(name).passes)
        if brake:
            braked_shops.append(name)
            by = BY_SHOP if brake == brakes.HOLD else BY_OWNER
            if by == BY_OWNER:
                ledger.shop(name).owner_hold = True
            for key in keys:
                _hold(ledger.products[key], by, night)
                held[by] += 1
    # A product held for the owner stays so, failing again, until his word (7.2).
    cut_words = frozenset(owner_cut_shops)
    for key in owner_repeats:
        product = ledger.products[key]
        if product.shop not in cut_words:
            _hold(product, BY_OWNER, night)
            held[BY_OWNER] += 1
    for name in cut_words:
        if name in ledger.shops:
            ledger.shops[name].owner_hold = False

    cuts = [key for key in shown
            if key in ledger.products and ledger.products[key].state == FAILED and not ledger.products[key].cut_on]
    by_part: dict[str, list[str]] = defaultdict(list)
    for key in cuts:
        by_part[parts.get(key, "")].append(key)
    shown_parts: Counter = Counter(parts.get(key, "") for key in shown)
    for part, keys in by_part.items():
        if part and brakes.kind_brake(shown_parts[part], len(keys)):
            for key in keys:
                _hold(ledger.products[key], BY_KIND, night)
                held[BY_KIND] += 1
    cuts = [key for key in cuts if ledger.products[key].state == FAILED]
    # A shop that leaves whole under 5.6 is not counted by the night's brake (7.4).
    shops_decided = sum(1 for name, count in decided.items() if count and not ledger.shop(name).out)
    braked_in = [name for name in braked_shops if not ledger.shop(name).out]
    night_brake = brakes.night_brake(shops_decided, len(braked_in), len(cuts), len(shown))
    stopped = brakes.cutting_stopped([entry.get("night_brake", False) for entry in ledger.nights] + [night_brake])
    if night_brake or stopped:
        for key in cuts:
            _hold(ledger.products[key], BY_STOP if stopped else BY_NIGHT, night)
            held[BY_STOP if stopped else BY_NIGHT] += 1
        cuts = []
    for key in cuts:
        ledger.products[key].cut_on = tonight
    # A failed product not shown (a candidate, one cut before) has nothing to be cut from.
    for key in readings:
        product = ledger.products.get(key)
        if product is not None and product.state == FAILED and not product.cut_on:
            product.cut_on = tonight

    # The first rounds (9.3).
    keys_by_shop: dict[str, list[str]] = defaultdict(list)
    for key in shown:
        if key in rows:
            keys_by_shop[rows[key].shop].append(key)
    for name, keys in keys_by_shop.items():
        shop = ledger.shop(name)
        if shop.round_over or not shop.first_night:
            continue
        started = _day(shop.first_night)
        everyone_asked = all(key in ledger.products and ledger.products[key].asked for key in keys)
        if everyone_asked or (started is not None and (night - started).days + 1 >= FIRST_ROUND_NIGHTS):
            shop.round_over = tonight

    ledger.nights.append({"night": tonight, "ours": False, "night_brake": night_brake, "stopped": stopped,
                          "braked_shops": sorted(braked_shops), "held": dict(held)})
    ledger.nights = ledger.nights[-NIGHTS_KEPT:]
    note.update({
        "decided": sum(decided.values()),
        "passed": sum(passed_now.values()),
        "failed": dict(sorted(failed_by_reason.items())),
        "cut_tonight": len(cuts),
        "back_tonight": len(came_back),
        "held": dict(sorted(held.items())),
        "braked_shops": sorted(braked_shops),
        "night_brake": night_brake,
        "stopped": stopped,
        "prices_tied": {name: values for name, values in sorted(proof_tonight.items())},
    })
    return Night(note, came_back)


def _hold(product: Product, by: str, night: date) -> None:
    product.state, product.held = HELD, by
    product.due = _iso(night + timedelta(days=1))


# ---- what the preparation reads ---------------------------------------------------


def proven(shop: Shop) -> bool:
    """7.5: the shop's reader of prices is proven."""
    return brakes.reader_proven((tied, same) for _night, tied, same in shop.proof)


def stock_proven(shop: Shop) -> bool:
    """7.5: the shop's page reader of stock is proven."""
    return brakes.reader_proven((tied, same) for _night, tied, same in shop.stock_proof)


def decisions(ledger: Ledger, night: date, rows: Mapping[str, Row], *, shown: Collection[str],
              candidates: Collection[str] = (), came_back: Iterable[str] = ()) -> dict[str, Any]:
    """What the preparation reads (`picwise_providers.checks_applied`), rules 6 and 9:

    - `shops_out`: the shops out, and why (5.6);
    - `cut`: the products a card may not show, and why: a failed check (5); once its
      shop's first round is over, a shown product never asked or not passed in 30
      nights (9.3), and one of an old feed with no reading of its shop's site of the last
      3 nights (5.6.4);
    - `enter`: the cap's candidates whose checks passed, the only products not shown
      last night that may take a place (9.4);
    - `prices`: the shop's own page's price, tied to its row, where the shop's reader is
      proven and the reading is of the row's present price (5.3, 7.5);
    - `stock`: what a page reader read of stock, where it is proven, for 3 days (5.2);
    - `returning`: products that passed again within 7 nights of their cut (8.2)."""
    shown = frozenset(shown)
    candidates = frozenset(candidates)
    cut: dict[str, str] = {}
    prices: dict[str, list[str]] = {}
    stock: dict[str, list[str]] = {}
    enter: list[str] = []
    for key in shown | candidates:
        row = rows.get(key)
        if row is None:
            continue
        product = ledger.products.get(key)
        shop = ledger.shops.get(row.shop) or Shop()
        if product is not None and product.state == FAILED:
            cut[key] = product.reason
            continue
        if key in shown and shop.round_over and (product is None or product.state != HELD):
            passed = _day(product.passed_on) if product is not None else None
            if product is None or not product.asked:
                cut[key] = "never asked"
                continue
            if passed is None or (night - passed).days >= PASS_VALID_NIGHTS:
                cut[key] = "not passed in 30 nights"
                continue
            if feed_is_old(_day(shop.feed_import), night):
                read = _day(product.price_on) or _day(product.stock_on)
                if read is None or (night - read).days >= STOCK_DAYS:
                    cut[key] = "old feed, no fresh reading"
                    continue
        if key in candidates and key not in shown and product is not None and product.state == PASSED:
            passed = _day(product.passed_on)
            if passed is not None and (night - passed).days < PASS_VALID_NIGHTS:
                enter.append(key)
        if product is None:
            continue
        if proven(shop) and product.site_price and product.feed_price and row.price is not None \
                and product.feed_price == f"{row.price:.2f}" and product.site_price != product.feed_price:
            prices[key] = [product.site_price, product.price_on]
        read = _day(product.stock_on)
        if shop.reader == "page" and stock_proven(shop) and product.stock and read is not None \
                and (night - read).days <= STOCK_DAYS:
            stock[key] = [product.stock, product.stock_on]
    shops_out = {name: shop.out for name, shop in sorted(ledger.shops.items()) if shop.out}
    return {
        "format": DECISIONS_FORMAT,
        "version": VERSION,
        "night": _iso(night),
        "shops_out": shops_out,
        "cut": dict(sorted(cut.items())),
        "enter": sorted(enter),
        "prices": dict(sorted(prices.items())),
        "stock": dict(sorted(stock.items())),
        "returning": sorted(came_back),
    }


def write_decisions(document: Mapping[str, Any], path: Path) -> None:
    _write_gzip_json(document, path)


# ---- the order of asking (10) -----------------------------------------------------


def asking_order(ledger: Ledger, night: date, rows: Mapping[str, Row], *, shown: Collection[str],
                 candidates: Collection[str] = (), parts: Mapping[str, str] | None = None,
                 ) -> dict[str, list[str]]:
    """Per shop, its products in the order they are asked tonight (rules 10): (1) the
    held and the failed that are due; (2) the shown whose row changed its price, address
    or photo since their check, and the sold-out readings about to lapse; (3) the cap's
    candidates; (4) the shown never asked, of each kind the 24 cheapest and the middle
    price first, then the rest, the cheapest first; (5) the shown whose last pass is over
    14 nights old, then the rest, asked longest ago first. A failed product not due is
    not asked; `rows` may hold cut products the feed still lists."""
    parts = parts or {}
    shown = frozenset(shown)
    candidates = frozenset(candidates)
    today = _iso(night)
    tiers: dict[str, list[list[tuple[Any, str]]]] = defaultdict(lambda: [[], [], [], [], [], []])
    never: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key in sorted(rows):
        row = rows[key]
        product = ledger.products.get(key)
        shop_tiers = tiers[row.shop]
        if product is not None and product.state in (FAILED, HELD):
            if product.state == HELD or (product.due and product.due <= today):
                shop_tiers[0].append(((product.due, key), key))
            continue
        if key in shown:
            if product is not None and product.asked and product.sig != row_signature(row):
                shop_tiers[1].append(((product.asked, key), key))
            elif product is not None and product.stock == "sold out" and product.stock_on \
                    and (night - (_day(product.stock_on) or night)).days >= STOCK_DAYS - 1:
                shop_tiers[1].append(((product.stock_on, key), key))
            elif product is None or not product.asked:
                never[(row.shop, parts.get(key, ""))].append(key)
            else:
                passed = _day(product.passed_on)
                old = passed is None or (night - passed).days > OLD_PASS_FIRST
                shop_tiers[4 if old else 5].append(((product.asked, key), key))
        elif key in candidates:
            shop_tiers[2].append(((0, key), key))
    for (shop_name, _part), keys in sorted(never.items()):
        priced = sorted(keys, key=lambda key: (rows[key].price is None, rows[key].price or 0.0, key))
        first = priced[:CHEAPEST_FIRST]
        middle = priced[len(priced) // 2] if priced else None
        if middle is not None and middle not in first:
            first.append(middle)
        chosen = set(first)
        tiers[shop_name][3].extend(((0, rows[key].price or 0.0, key), key) for key in first)
        tiers[shop_name][3].extend(((1, rows[key].price or 0.0, key), key) for key in priced if key not in chosen)
    order: dict[str, list[str]] = {}
    for shop_name, shop_tiers in tiers.items():
        keys: list[str] = []
        for tier in shop_tiers:
            keys.extend(key for _rank, key in sorted(tier))
        if keys:
            order[shop_name] = keys
    return order
