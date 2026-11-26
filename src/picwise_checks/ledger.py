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
import html
import json
import os
import unicodedata
import tempfile
from collections import Counter, defaultdict
from dataclasses import astuple, dataclass, field, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Collection, Iterable, Mapping, Sequence

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
# 9.1 and 9.3. The first round ends after 3 days at most (owner, 2026-11-22: «15 μέρες θα
# βλέπουνε οι χρήστες σαββούρα είναι πάρα πολύ!», then «Σε 3 μέρες»): a product not checked
# by then is not shown, as a shop that cannot be checked leaves on its day 4.
PASS_VALID_NIGHTS = 30
FIRST_ROUND_NIGHTS = 4
# 19.3.1: with the rule of how many of a shop's products pass (its switch on), a pass counts
# for three nights (owner, 2026-11-22: «Και 3 βράδια μπορούμε... Αν υπάρξει κάποια έπιπλοκή
# κρατάμε τα προϊόντα ασκανάριστα μέχρι 3 μέρες»): a product passed on a night is shown that
# night and the two after, then waits until it passes again. The reason it waits by.
PASS_NIGHTS_SCANNED = 3
NOT_PASSED_IN_THREE = "not passed in 3 nights"
# 21 (owner, 2026-11-25: «24 ώρες είναι το σκανάρισμα και ότι προλάβει να σκανάρει.... Εάν το
# σύστημα κολλήσει και δεν κάνεις κανάρισμα την επόμενη μέρα τα προϊόντα μένουν όπως έχουν πρέπει
# μετά την τρίτη ή την τέταρτη να σβηστούν», then «Ναι συμφωνώ» to the rule put to him): with the
# rule of how many of a shop's products pass, a pass counts for the day it was made. A product
# not passed tonight waits once its shop's asking was whole on a night after its pass
# (`Shop.complete_on`: the bot asked the shop all day, or all it had, and nothing stopped it);
# while it was not (the server or the bot stuck, the shop stopped answering) the product stays
# as it was, up to the three nights of 19.3.1 after its pass.
PASS_NIGHTS_DAY = 1
NOT_PASSED_TODAY = "not passed in the last 24 hours"
NOT_PASSED_IN_THIRTY = "not passed in 30 nights"
# 5.6.2: a shop that cannot be checked leaves on its day 4, after 3 days (owner, 2026-11-22:
# «Σε 3 μέρες», instead of the 14 of 21/11).
OUT_ON_DAY = 4
FRESH_AFTER_CHECKED = 7
# 5.2: a reading of the shop's own site decides stock for 3 days.
STOCK_DAYS = 3
# 5.6.2: a shop out because it could not be checked is asked each night by up to 5 pages.
RETRY_PAGES = 5
# 10.4 and 10.5.
CHEAPEST_FIRST = 24
OLD_PASS_FIRST = 14
# 23 (owner, 2026-11-26: «Αρχείο ελέγχων: να σβήνονται τα προϊόντα που λείπουν από το feed πάνω από 7
# μέρες»; «όποιο προϊόν δεν πληροί τις προϋποθέσεις σβήνεται αμέσως και δεν μένει να πιάνει μνήμη»):
# a product the bot has not been given for over 7 nights (not shown, no candidate, no cut product
# the feed still lists) is let go from the ledger; one short line of it is kept (the night, its last
# state and reason) for `GONE_KEPT_NIGHTS`, so that what was let go can be counted and told.
FORGET_AFTER_NIGHTS = 7
GONE_KEPT_NIGHTS = 30


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
    # The product's options in stock on its shop's own page (`page_reader.options_in_stock`)
    # and the night read: the card names them (owner, 2026-11-24: «Μόνο τα διαθέσιμα»).
    options: str = ""
    options_on: str = ""


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
    # 21: the last night the shop's asking was whole (the bot asked it all day, or all it
    # had, and nothing stopped it); "" until the first such night, which keeps the three
    # nights of 19.3.1 for every product of the shop.
    complete_on: str = ""


_PRODUCT_FIELDS = tuple(item.name for item in fields(Product))
_SHOP_FIELDS = tuple(item.name for item in fields(Shop))


@dataclass
class Ledger:
    products: dict[str, Product] = field(default_factory=dict)
    shops: dict[str, Shop] = field(default_factory=dict)
    nights: list[dict[str, Any]] = field(default_factory=list)
    # 23: the last night each product was given to the bot, and the short lines of those let go
    # (`forget_unseen`). Kept beside the products in the file, where a ledger written before
    # them has none and an older bot reads none.
    seen: dict[str, str] = field(default_factory=dict)
    gone: dict[str, list] = field(default_factory=dict)

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
    # Its options in stock, as JSON (`page_reader.options_in_stock`); "" when none were read.
    options: str = ""


def row_signature(row: Row) -> str:
    """What changes in a feed row that makes its checks old (8.1, 10.2): its price, its
    address, its photo's address."""
    price = "" if row.price is None else f"{row.price:.2f}"
    return f"{price}|{row.address}|{row.photo}"


# ---- reading and writing -----------------------------------------------------------


def load(path: Path, *, shops: Collection[str] | None = None) -> Ledger:
    """The ledger at `path`; an empty one when there is none yet. A file that cannot be
    read raises: the night stops rather than start from nothing. `shops`: only these shops'
    products and entries (a bot of its own, which asks only its shops and records nothing, 23);
    without the last nights seen and the lines of those let go, which only the recording keeps."""
    if not path.exists():
        return Ledger()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("format") != FORMAT or payload.get("version") != VERSION:
        raise ValueError("not a ledger of this version")
    wanted = frozenset(shops) if shops is not None else None
    products = payload.pop("products", {})
    kept = {key: Product(*values) for key, values in products.items() if wanted is None or values[0] in wanted}
    del products
    return Ledger(
        products=kept,
        shops={name: Shop(**{k: v for k, v in values.items() if k in _SHOP_FIELDS})
               for name, values in payload.get("shops", {}).items() if wanted is None or name in wanted},
        nights=list(payload.get("nights", [])),
        seen=dict(payload.get("seen") or {}) if wanted is None else {},
        gone=dict(payload.get("gone") or {}) if wanted is None else {},
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
            "seen": ledger.seen,
            "gone": ledger.gone,
        },
        path,
    )


# ---- what is let go (23) ----------------------------------------------------------


def forget_unseen(ledger: Ledger, night: date, given: Collection[str]) -> dict[str, Any]:
    """23: tonight's products given to the bot (`given`: the shown, the candidates, the cut ones the
    feed still lists) are seen tonight; a product of the ledger not given for over
    `FORGET_AFTER_NIGHTS` nights is let go, its short line kept in `gone` (the night, its last state
    and reason) for `GONE_KEPT_NIGHTS`; one given again leaves `gone`. A product the ledger holds
    with no night seen (a ledger written before 26/11) is counted seen tonight: the first nights
    let nothing go. What it did, counted."""
    tonight = _iso(night)
    given = frozenset(given)
    for key in given:
        if key in ledger.products:
            ledger.seen[key] = tonight
        ledger.gone.pop(key, None)
    limit = _iso(night - timedelta(days=FORGET_AFTER_NIGHTS))
    let_go: Counter = Counter()
    for key in [key for key in ledger.products if key not in given]:
        last = ledger.seen.get(key)
        if not last:
            ledger.seen[key] = tonight
            continue
        if last < limit:
            product = ledger.products.pop(key)
            ledger.seen.pop(key, None)
            ledger.gone[key] = [tonight, product.state or "never decided", product.reason]
            let_go[product.state or "never decided"] += 1
    for key in [key for key in ledger.seen if key not in ledger.products]:
        ledger.seen.pop(key, None)
    kept_from = _iso(night - timedelta(days=GONE_KEPT_NIGHTS))
    for key in [key for key, line in ledger.gone.items() if not line or str(line[0]) < kept_from]:
        ledger.gone.pop(key, None)
    return {"let_go": sum(let_go.values()), "let_go_by_state": dict(sorted(let_go.items())),
            "products": len(ledger.products), "gone_kept": len(ledger.gone)}


# ---- coming back (8) --------------------------------------------------------------


def due_after(reason: str, fails: int, night: date) -> date:
    """8.1: when a failed product is asked again."""
    if reason in (GONE, ANOTHER_PRODUCT):
        return night + timedelta(days=GONE_FIRST if fails <= 1 else GONE_EVERY)
    return night + timedelta(days=1 if fails <= AGAIN_NIGHTS else AGAIN_EVERY)


# ---- the night (5, 7, 8, 9) -------------------------------------------------------


def _shop_night(ledger: Ledger, name: str, night: date, tonight: ShopNight) -> tuple[bool, str]:
    """5.6.2: a shop's day while it cannot be checked; out on day 4 (`OUT_ON_DAY`; owner,
    2026-11-22: «Σε 3 μέρες»); back the first night a product is read on it; the count
    afresh only after 7 nights checked in a row, a shop that falls back sooner going on
    from the day it had reached."""
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


def shop_name_key(name: str) -> str:
    """A shop's name as two sources may write it differently ("&amp;", an accent, case,
    spaces): the key both are matched by."""
    return " ".join(unicodedata.normalize("NFKC", html.unescape(str(name or ""))).casefold().split())


def _awin(ledger: Ledger, awin: Mapping[str, tuple[str | None, str]], shown_by_shop: Mapping[str, int],
          shown: int, owner_awin_word: bool, closed_out: bool = False) -> dict[str, Any]:
    """5.6.3: Awin's reading put on each shop of the catalogue; a reading that would put
    out many shops at once waits for the owner's word. A shop of the catalogue whose name
    the reading does not hold is not judged by it (built 21/11, after the look on the
    server, where two names written otherwise read as "in no list"): only a shop Awin's
    reading names, in none of its lists, is. `closed_out`: the Proposed part of the rule
    (a shop suspended, in no list or offline is out too), only on the owner's yes; without
    it only a rejection puts a shop out («Βγαίνουν»), and the others are named in the note."""
    by_key = {shop_name_key(name): value for name, value in awin.items()}
    newly: dict[str, str] = {}
    proposed: dict[str, str] = {}
    unmatched = []
    for name in shown_by_shop:
        if shop_name_key(name) not in by_key:
            unmatched.append(name)
            continue
        relationship, link = by_key[shop_name_key(name)]
        shop = ledger.shop(name)
        shop.awin, shop.link = relationship or "", link or ""
        reason = awin_out(relationship, link, closed_too=closed_out)
        would = "" if reason else awin_out(relationship, link)
        if would:
            proposed[name] = would
        if reason and not shop.out:
            newly[name] = reason
        elif not reason and shop.out.startswith("Awin"):
            shop.out = ""
    products_out = sum(shown_by_shop.get(name, 0) for name in newly)
    waits = bool(newly) and brakes.awin_waits(len(newly), products_out, shown) and not owner_awin_word
    if not waits:
        for name, reason in newly.items():
            ledger.shop(name).out = reason
    return {"newly_out": [[name, newly[name]] for name in sorted(newly)], "products": products_out, "waits": waits,
            "names_not_matched": sorted(unmatched),
            # What the Proposed rule would put out, while it waits for the owner's yes.
            "would_be_out_if_proposed": [[name, proposed[name], shown_by_shop.get(name, 0)] for name in sorted(proposed)]}


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
    awin_closed_out: bool = False,
    complete: Collection[str] = (),
) -> Night:
    """One night's readings into the ledger, by the rules' order.

    `rows`: the feed's rows the bot knew tonight (the shown ones, the cap's candidates,
    the cut ones the feed still lists); `readings`: the products asked; `shop_nights`:
    what asking each shop gave; `shown`: the keys the site shows (the prepared
    catalogue); `parts`: each shown key's kind as the cap reads it
    (`catalogue_cap.part_of`); `awin`: Awin's relationship and link status per shop,
    None when its API did not answer; `feeds`: each shop's feed's last import;
    `owner_cut_shops`: the shops whose products held for the owner he said to cut
    («κόψε»); `owner_awin_word`: his word on a reading of Awin that waits;
    `awin_closed_out`: his yes to the Proposed part of 5.6.3 (a shop suspended, in no list
    or offline at Awin is out), off until he gives it; `complete`: the shops whose asking
    was whole tonight (21), each one that could be checked marked so (`Shop.complete_on`).
    A round that is ours (7.1) marks none: every product stays as it was."""
    tonight = _iso(night)
    parts = parts or {}
    shown = frozenset(shown)
    shown_by_shop: Counter = Counter(rows[key].shop for key in shown if key in rows)
    note: dict[str, Any] = {"night": tonight, "shops_asked": len(shop_nights)}

    # 7.1: a round most shops did not answer is ours, and records nothing.
    answered = sum(1 for item in shop_nights.values() if item.catalogue_read or item.answers)
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
    # 21: the shops asked whole tonight; a shop that could not be checked was not.
    whole = sorted(name for name in complete if name in shop_nights and name not in cannot)
    for name in whole:
        ledger.shop(name).complete_on = tonight
    note["asked_whole"] = len(whole)
    if awin is not None:
        note["awin"] = _awin(ledger, awin, shown_by_shop, len(shown), owner_awin_word, awin_closed_out)
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
    # What was read first: the prices and the stock, and with them each shop's proof (7.5).
    for key, reading in readings.items():
        row = rows.get(key)
        if row is None:
            continue
        product = ledger.products.get(key)
        if product is None:
            product = ledger.products[key] = Product(shop=row.shop)
        product.asked = tonight
        product.sig = row_signature(row)
        if reading.site_price is not None and row.price:
            product.site_price = f"{reading.site_price:.2f}"
            product.feed_price = f"{row.price:.2f}"
            product.price_on, product.tie = tonight, reading.tie
            proof_tonight[row.shop][0] += 1
            proof_tonight[row.shop][1] += same_price(reading.site_price, row.price)
            shop = ledger.shop(row.shop)
            shop.ratios = (shop.ratios + [[reading.site_price, row.price]])[-RATIOS_KEPT:]
        if reading.page.state == PASSED:
            # Read tonight: the options in stock now, none when the page names none.
            product.options, product.options_on = reading.options, tonight
        if reading.stock:
            product.stock, product.stock_on = reading.stock, tonight
            if row.feed_stock:
                stock_tonight[row.shop][0] += 1
                stock_tonight[row.shop][1] += reading.stock == row.feed_stock
    for name, (tied, same) in proof_tonight.items():
        shop = ledger.shop(name)
        shop.proof = (shop.proof + [[tonight, tied, same]])[-brakes.PROOF_NIGHTS:]
    for name, (tied, same) in stock_tonight.items():
        shop = ledger.shop(name)
        shop.stock_proof = (shop.stock_proof + [[tonight, tied, same]])[-brakes.PROOF_NIGHTS:]

    # Then the verdicts. A price far apart fails its product only where the shop's reader
    # of prices is proven (7.5: a reader's word changes the site only once proven; built
    # 21/11 after the look on the server, where a shop's catalogue gave its prices in
    # another currency than the feed's).
    for key, reading in readings.items():
        row = rows.get(key)
        if row is None:
            continue
        product = ledger.products[key]
        verdict = reading.page
        if verdict.state == PASSED and reading.site_price is not None and row.price \
                and far_apart(reading.site_price, row.price) and proven(ledger.shop(row.shop)):
            verdict = Verdict(FAILED, "price far apart")
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
        # Asked means decided once, passed or failed: a product the shop refused was not
        # checked, so a shop that refuses keeps the 3 days the owner gave it (5.6.2;
        # built 21/11 after the look, where a shop of 4 products all refused ended its round
        # on its first night).
        everyone_asked = all(key in ledger.products and _decided_once(ledger.products[key]) for key in keys)
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


def _decided_once(product: Product) -> bool:
    return bool(product.passed_on) or product.fails > 0 or product.state in (FAILED, HELD)


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


def not_shown_until_checked(product: Product | None, shop: Shop, night: date, *, old_feed_rule: bool = False,
                            pass_nights: int = PASS_VALID_NIGHTS) -> str:
    """9.3 (and 5.6.4, Proposed): why a product may not be shown until the bot has asked
    it, or "": never asked; not passed in 30 nights, or in `pass_nights` when fewer (19.3.1:
    3, the rule of how many of a shop's products pass; 21: `PASS_NIGHTS_DAY`, a pass counts
    for the day, three nights while its shop's asking was not whole on a night after it);
    with `old_feed_rule`, of a feed over 7 days old with no reading of its shop's own site of
    the last 3 nights. No check failed: the product waits at the cap's gate as a new one
    does (9.4)."""
    if product is None or not _decided_once(product):
        return "never checked"
    passed = _day(product.passed_on)
    if passed is None or (night - passed).days >= PASS_VALID_NIGHTS:
        return NOT_PASSED_IN_THIRTY
    if (night - passed).days >= pass_nights:
        if pass_nights != PASS_NIGHTS_DAY:
            return NOT_PASSED_IN_THREE if pass_nights == PASS_NIGHTS_SCANNED else f"not passed in {pass_nights} nights"
        if (night - passed).days >= PASS_NIGHTS_SCANNED:
            return NOT_PASSED_IN_THREE
        if shop.complete_on and shop.complete_on > product.passed_on:
            return NOT_PASSED_TODAY
    if old_feed_rule and feed_is_old(_day(shop.feed_import), night):
        # The latest of its two readings, the price's and the stock's (until 22/11 the price's
        # stood before the stock's, so a fresh reading of stock beside an older one of price
        # counted as old).
        read = max((day for day in (_day(product.price_on), _day(product.stock_on)) if day is not None), default=None)
        if read is None or (night - read).days >= STOCK_DAYS:
            return "old feed, no fresh reading"
    return ""


def decisions(ledger: Ledger, night: date, rows: Mapping[str, Row], *, shown: Collection[str],
              candidates: Collection[str] = (), came_back: Iterable[str] = (),
              old_feed_rule: bool = False, pass_nights: int = PASS_VALID_NIGHTS,
              passed_over: int = 0) -> dict[str, Any]:
    """What the preparation reads (`picwise_providers.checks_applied`), rules 6 and 9:

    - `shops_out`: the shops out, and why (5.6);
    - `cut`: the products a card may not show, and why: a failed check (5);
    - `wait`: the shown products that are not shown until they are checked (9.3), once
      their shop's first round is over: never asked, or not passed in 30 nights; and, with
      `old_feed_rule` (5.6.4, Proposed: only on the owner's yes), one of an old feed with no
      reading of its shop's site of the last 3 nights. No check of theirs failed, so they
      are not cut: they leave the cap's memory of the night before and wait at its gate,
      where the cap names the next ones as candidates and the bot asks those the next
      night (9.4). Until 22/11 they were marked cut like a failed product, so that the cap
      never saw them: the night after, the bot did not ask them, and a place of theirs
      went to another product before they could be named for it (the look of task 7);
    - `enter`: the cap's candidates whose checks passed, the only products not shown
      last night that may take a place (9.4);
    - `prices`: the shop's own page's price, tied to its row, where the shop's reader is
      proven and the reading is of the row's present price (5.3, 7.5);
    - `stock`: what a page reader read of stock, where it is proven, for 3 days (5.2);
    - `returning`: products that passed again within 7 nights of their cut (8.2);
    - `passed`, with `passed_over`: of the shops that show more than `passed_over` products,
      the shown ones that passed and may be shown, so that a shop over the most it passes
      keeps those before the ones never asked (19.4 f; `picwise_providers.shop_cap`);
    - `passed_on`, with the day's rule (21): the night of the pass of each product shown or
      entering on a pass, by night, so that on a morning with no newer night (the bot
      stuck) the preparation lets a pass count three nights and no more
      (`picwise_providers.checks_applied.expire`).

    `pass_nights`: how many nights a pass counts for (9.1: 30; 19.3.1: 3, the rule of how
    many of a shop's products pass, its switch on; 21: `PASS_NIGHTS_DAY`)."""
    shown = frozenset(shown)
    candidates = frozenset(candidates)
    shown_by_shop: Counter = Counter(rows[key].shop for key in shown if key in rows) if passed_over > 0 else Counter()
    passed: list[str] = []
    cut: dict[str, str] = {}
    wait: dict[str, str] = {}
    prices: dict[str, list[str]] = {}
    stock: dict[str, list[str]] = {}
    options: dict[str, list[str]] = {}
    enter: list[str] = []
    day_rule = pass_nights == PASS_NIGHTS_DAY
    passed_on: dict[str, list[str]] = defaultdict(list)
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
            why = not_shown_until_checked(product, shop, night, old_feed_rule=old_feed_rule, pass_nights=pass_nights)
            if why:
                wait[key] = why
                continue
        entering = key in candidates and key not in shown and product is not None and product.state == PASSED \
            and not not_shown_until_checked(product, shop, night, old_feed_rule=old_feed_rule, pass_nights=pass_nights)
        if entering:
            enter.append(key)
        if product is None:
            continue
        if day_rule and product.state == PASSED and product.passed_on and (key in shown or entering):
            passed_on[product.passed_on].append(key)
        if key in shown and shown_by_shop[row.shop] > passed_over > 0 and product.state == PASSED \
                and not not_shown_until_checked(product, shop, night, old_feed_rule=old_feed_rule, pass_nights=pass_nights):
            passed.append(key)
        if proven(shop) and product.site_price and product.feed_price and row.price is not None \
                and product.feed_price == f"{row.price:.2f}" and product.site_price != product.feed_price:
            prices[key] = [product.site_price, product.price_on]
        read = _day(product.stock_on)
        if shop.reader == "page" and stock_proven(shop) and product.stock and read is not None \
                and (night - read).days <= STOCK_DAYS:
            stock[key] = [product.stock, product.stock_on]
        read_options = _day(product.options_on)
        if product.options and read_options is not None and (night - read_options).days <= STOCK_DAYS:
            options[key] = [product.options, product.options_on]
    shops_out = {name: shop.out for name, shop in sorted(ledger.shops.items()) if shop.out}
    return {
        "format": DECISIONS_FORMAT,
        "version": VERSION,
        "night": _iso(night),
        "shops_out": shops_out,
        "cut": dict(sorted(cut.items())),
        "wait": dict(sorted(wait.items())),
        "enter": sorted(enter),
        "prices": dict(sorted(prices.items())),
        "stock": dict(sorted(stock.items())),
        "options": dict(sorted(options.items())),
        "returning": sorted(came_back),
        **({"passed": sorted(passed)} if passed_over > 0 else {}),
        **({"passed_on": {day: sorted(keys) for day, keys in sorted(passed_on.items())}} if day_rule else {}),
    }


def write_decisions(document: Mapping[str, Any], path: Path) -> None:
    _write_gzip_json(document, path)


# ---- the order of asking (10) -----------------------------------------------------


def asking_order(ledger: Ledger, night: date, rows: Mapping[str, Row], *, shown: Collection[str],
                 candidates: Collection[str] = (), parts: Mapping[str, str] | None = None,
                 scanned: bool = False, shown_order: Mapping[str, Sequence[str]] | None = None,
                 dearer: Collection[str] = (), limit: int = 0) -> dict[str, list[str]]:
    """Per shop, its products in the order they are asked tonight (rules 10): (1) the
    held and the failed that are due; (2) the shown whose row changed its price, address
    or photo since their check, and the sold-out readings about to lapse; (3) the cap's
    candidates; (4) the shown never asked, of each kind the 24 cheapest and the middle
    price first, then the rest, the cheapest first; (5) the shown whose last pass is over
    14 nights old, then the rest, asked longest ago first. A failed product not due is
    not asked; `rows` may hold cut products the feed still lists.

    `scanned`: the rule of how many of a shop's products pass (the checks' rules 19.3, its
    switch on). Each day the bot asks a shop's shown products again first, after (1) and
    (2), in the order of 19.4 (`shown_order`, per shop its keys, worked out from the
    prepared catalogue by `picwise_providers.shop_cap.shop_order`), and new ones only in
    the time left: the cap's candidates in the order the caps named them, then the shown
    never asked (19.3.2); so a shop settles at what it lets the bot scan in a day and its
    products do not take turns. `dearer`: of the shown, those a cheaper shop shows (the last
    of each shop's order, `shop_cap.shop_order`). They show nothing, so with the rule on they
    are asked again after the cap's candidates, not before (the mend of 20.7.4: a shop the bot
    cannot scan whole in a day never reached its candidates). `limit`: past (1), at most this
    many of a shop (19.3.3: its first 20,000)."""
    parts = parts or {}
    shown = frozenset(shown)
    dearer = frozenset(dearer) if scanned else frozenset()
    named = {key: place for place, key in enumerate(dict.fromkeys(candidates))}
    candidates = frozenset(named)
    places = {key: place for keys in (shown_order or {}).values() for place, key in enumerate(keys)} if scanned else {}
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
            elif scanned:
                # 19.3.2: asked again first, in the order of 19.4; a product the order does not
                # name (the catalogue read without it), after, the cheapest first.
                place = places.get(key)
                rank = (0, place, 0.0) if place is not None else (1, 0, row.price or 0.0)
                shop_tiers[4 if key in dearer else 2].append(((rank, key), key))
            else:
                passed = _day(product.passed_on)
                old = passed is None or (night - passed).days > OLD_PASS_FIRST
                shop_tiers[4 if old else 5].append(((product.asked, key), key))
        elif key in candidates:
            shop_tiers[3 if scanned else 2].append((((0, named[key]) if scanned else (0, key)), key))
        elif (ledger.shops.get(row.shop) or Shop()).out.startswith("cannot be checked"):
            # A shop out because it could not be checked is asked again each night by a
            # few of its pages (5.6.2).
            tier = shop_tiers[3 if scanned else 2]
            if sum(1 for rank, _asked in tier if rank[0] == 1) < RETRY_PAGES:
                tier.append(((1, key), key))
    for (shop_name, _part), keys in sorted(never.items()):
        priced = sorted(keys, key=lambda key: (rows[key].price is None, rows[key].price or 0.0, key))
        first = priced[:CHEAPEST_FIRST]
        middle = priced[len(priced) // 2] if priced else None
        if middle is not None and middle not in first:
            first.append(middle)
        chosen = set(first)
        never_tier = tiers[shop_name][5 if scanned else 3]
        never_tier.extend(((0, rows[key].price or 0.0, key), key) for key in first)
        never_tier.extend(((1, rows[key].price or 0.0, key), key) for key in priced if key not in chosen)
    order: dict[str, list[str]] = {}
    for shop_name, shop_tiers in tiers.items():
        keys = [key for _rank, key in sorted(shop_tiers[0])]
        rest: list[str] = []
        for tier in shop_tiers[1:]:
            rest.extend(key for _rank, key in sorted(tier))
        keys.extend(rest[:limit] if limit > 0 else rest)
        if keys:
            order[shop_name] = keys
    return order
