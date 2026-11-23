"""Which categories of Google's taxonomy the site shows: a switch for each category and
subcategory (`docs/PICWISE_CATEGORY_SWITCHES.md`).

The owner, 2026-11-22, on problem categories («Τι θα έλεγες άμα κάναμε λίγο πιο
συγκεκριμένες τις κατηγορίες ... αυτές που είναι που προβληματικές τώρα ... να της
αφαιρούσαμε τελείως»), and which stay: «Σπίτι κήπος ...τεχνολογία ..ένδυση υπόδηση.. κρατάμε και τα
δαχτυλίδια ρολόγια αξεσουάρ», toys too; «Όλο το παιχνίδι είναι στις υπό κατηγορίες», the
ones of products of little value or hard to identify out; «Και τα είδη pet shop έξω.. όπως
και τα είδη καλλωπισμού»; «Καλώδια αντάπτορες φορτιστές προστατευτικά οθόνες θήκες κινητών
τηλεχειριστήρια μπαταρίες ραντάρ ... έξω»; «κρατάμε τα αρώματα». 2026-11-23, asked of what
had not been talked over: bedding, pools and hot tubs, fireplaces and smoke alarms out, ink
and toner out, video games, television mounts and hats, scarves and gloves in; no lowest
price at this step («Κανένα όριο σε αυτό το επίπεδο»); and how: «Να δημιουργήσεις έναν
διακόπτη για κάθε μία κατηγορία και υποκατηγορία αυτής έτσι ώστε όταν φτιάξουμε το
διαχειριστικό να μπορεί ένας άνθρωπος με το χέρι να ανοίγει να κλείνει μία κατηγορία ...
χωρίς πολλά μπερδέματα ή κώδικες».

The list (`data/category_switches.json`): one line a category or subcategory of Google's
taxonomy (`google`, read by the program), its name for the owner (`name`), open or closed
(`on`); a line may carry `site`, the words a visitor is told PicWise covers. A product is
shown only when the line the AI gave it (`ai_shelves`) is under a top line of the list and
every line of the list above it, its own included, is open: closing a category closes all
under it. A level the list does not name takes its parent's word. A product the AI has
given no line yet, or a slip (`ai_shelves.SLIP_LINES`), is not decided here: the checks
hold a new one until it has its line and cut one with none (their rules 5.5). With no
answers of the AI at all, nothing is decided.

The whole rule stands behind the list's own switch (its top `on`), false until the owner's
«ανέβασε»: with it false nothing is closed and the night only counts what each line holds,
for the night's note (`last_note`) and the dashboard to come. Applied in the preparation
before anything counts products (`state.prepare_feed_catalogue`): the answers to the
question "is it the kind itself", how many of a shop's products pass, the cap of a
category, the bot's candidates and the AI's next questions all see only what the list
lets through. Read with the code (`prepared_catalogue._FROZEN_FILES`): a change to the list
prepares the catalogue again.
"""
from __future__ import annotations

import json
import threading
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import ai_shelves
from .contracts import ProviderProduct

_REPO_ROOT = Path(__file__).resolve().parents[2]
SWITCHES_FILE = _REPO_ROOT / "data" / "category_switches.json"
# How many shops the night's note names, those the list closes most products of first.
SHOPS_LISTED = 40

_LOCK = threading.Lock()
_READ: dict[str, Any] = {}
_LAST_NOTE: dict[str, Any] | None = None


def levels_of(line: str) -> tuple[str, ...]:
    """A line of Google's taxonomy as its levels, as the AI's lines are read
    (`ai_shelves._levels`: spaces and case do not count)."""
    return tuple(" ".join(part.split()).casefold() for part in str(line or "").split(">") if part.strip())


@dataclass(frozen=True)
class Line:
    """A line of the list."""

    google: str
    levels: tuple[str, ...]
    name: str
    on: bool
    site: str = ""


@dataclass(frozen=True)
class Switches:
    """The list as read: its own switch and its lines, in the file's order."""

    on: bool
    lines: tuple[Line, ...]
    by_levels: Mapping[tuple[str, ...], Line]

    def closing(self, levels: Sequence[str]) -> Line | None:
        """The line of the list that closes a product of these levels, the highest first;
        None when it is open."""
        for depth in range(1, len(levels) + 1):
            line = self.by_levels.get(tuple(levels[:depth]))
            if line is not None and not line.on:
                return line
        return None

    def is_open(self, levels: Sequence[str]) -> bool:
        """Whether a product of these levels is shown: its top line is on the list, and no
        line of the list above it, its own included, is closed."""
        levels = tuple(levels)
        if not levels or levels[:1] not in self.by_levels:
            return False
        return self.closing(levels) is None

    def line_open(self, line: Line) -> bool:
        """Whether a line of the list is open with every line above it."""
        return self.is_open(line.levels)


def _parse(payload: Any) -> Switches:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("lines"), list):
        raise ValueError("no list of lines")
    lines: list[Line] = []
    by_levels: dict[tuple[str, ...], Line] = {}
    for entry in payload["lines"]:
        if not isinstance(entry, Mapping):
            raise ValueError("a line that is not an object")
        google = str(entry.get("google") or "").strip()
        levels = levels_of(google)
        if not levels:
            raise ValueError("a line with no category")
        if levels in by_levels:
            raise ValueError(f"a category twice: {google}")
        if not isinstance(entry.get("on"), bool):
            raise ValueError(f"no true or false for {google}")
        line = Line(google=google, levels=levels, name=str(entry.get("name") or "").strip() or google,
                    on=entry["on"], site=str(entry.get("site") or "").strip())
        lines.append(line)
        by_levels[levels] = line
    return Switches(on=payload.get("on") is True, lines=tuple(lines), by_levels=by_levels)


def read_switches(path: Path | None = None) -> Switches | None:
    """The list, read again only when its file changes; None when it cannot be read (then
    nothing is closed, and the night's note says why)."""
    path = SWITCHES_FILE if path is None else path
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return None
    key = str(path)
    with _LOCK:
        cached = _READ.get(key)
        if cached is not None and cached[0] == stamp:
            return cached[1]
    try:
        switches = _parse(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        switches = None
    with _LOCK:
        _READ[key] = (stamp, switches)
    return switches


def scope_on(path: Path | None = None) -> bool:
    """The whole rule's switch: true when the list closes what it says."""
    switches = read_switches(path)
    return switches is not None and switches.on


def product_levels(product: ProviderProduct, table: Mapping[str, str] | None = None) -> tuple[str, ...] | None:
    """The levels of the line the AI gave a product; None when it has none yet, none fits,
    or it slipped (the checks decide those: their rules 5.5)."""
    line = ai_shelves.line_of(product.title, product.brand, product.raw, table)
    if not line or ai_shelves.is_slip(line):
        return None
    return levels_of(line) or None


def closes(product: ProviderProduct, *, switches: Switches | None = None,
           table: Mapping[str, str] | None = None) -> bool:
    """Whether the list, its switch on, leaves this product out."""
    switches = read_switches() if switches is None else switches
    if switches is None or not switches.on:
        return False
    table = ai_shelves.answers() if table is None else table
    if not table:
        return False
    levels = product_levels(product, table)
    return levels is not None and not switches.is_open(levels)


def passing(products: Iterable[ProviderProduct]) -> list[ProviderProduct]:
    """The products the list lets through (all of them with its switch off, and all of them
    should reading it fail: the list never stops the night's preparation)."""
    products = list(products)
    try:
        switches = read_switches()
        if switches is None or not switches.on:
            return products
        table = ai_shelves.answers()
        if not table:
            return products
        return [product for product in products if not closes(product, switches=switches, table=table)]
    except Exception:
        return products


def settle(
    products: Sequence[ProviderProduct],
    *,
    switches: Switches | None = None,
    table: Mapping[str, str] | None = None,
) -> list[bool] | None:
    """For each product, whether the list lets it through; None when every product passes
    (the switch off, the list or the AI's answers missing, or nothing closed). The night's
    note (`last_note`) is kept whenever the list and the answers can be read: what each line
    holds of these products, and what the list closes or would close."""
    global _LAST_NOTE
    switches = read_switches() if switches is None else switches
    if switches is None:
        _LAST_NOTE = {"applied": False, "why": "the list cannot be read"}
        return None
    table = ai_shelves.answers() if table is None else table
    if not table:
        _LAST_NOTE = {"applied": False, "why": "no answers of the AI's categories: nothing is decided"}
        return None
    from .catalogue_cap import shop_of

    keep: list[bool] = []
    held: Counter = Counter()
    open_count = closed_count = undecided = 0
    closed_by_shop: Counter = Counter()
    open_by_shop: Counter = Counter()
    closed_by_line: Counter = Counter()
    for product in products:
        levels = product_levels(product, table)
        if levels is None:
            undecided += 1
            keep.append(True)
            continue
        for depth in range(1, len(levels) + 1):
            if levels[:depth] in switches.by_levels:
                held[levels[:depth]] += 1
        if switches.is_open(levels):
            open_count += 1
            open_by_shop[shop_of(product)] += 1
            keep.append(True)
            continue
        closed_count += 1
        closed_by_shop[shop_of(product)] += 1
        line = switches.closing(levels)
        closed_by_line[line.levels if line is not None else levels[:1]] += 1
        keep.append(False)
    note: dict[str, Any] = {
        "applied": switches.on,
        "products": len(products),
        "open": open_count,
        "closed": closed_count,
        "undecided": undecided,
        "not_listed": sum(count for levels, count in closed_by_line.items() if levels not in switches.by_levels),
        "lines": [
            {"google": line.google, "name": line.name, "on": line.on, "open": switches.line_open(line),
             "products": held.get(line.levels, 0)}
            for line in switches.lines
        ],
        "closed_by_shop": [
            {"shop": shop, "closed": count, "open": open_by_shop.get(shop, 0)}
            for shop, count in closed_by_shop.most_common(SHOPS_LISTED)
        ],
    }
    if not switches.on:
        note["why"] = "the switch is off: what the list would close is counted, nothing is closed"
    _LAST_NOTE = note
    if not switches.on or not closed_count:
        return None
    return keep


def settle_or_keep(products: Sequence[ProviderProduct]) -> list[bool] | None:
    """`settle`, but a failure keeps every product and is only noted (its kind, never its text,
    which could quote a row): the list never stops the night's preparation."""
    global _LAST_NOTE
    try:
        return settle(products)
    except Exception as error:
        _LAST_NOTE = {"applied": False, "error": f"the list failed ({type(error).__name__}): every product kept"}
        return None


def last_note() -> dict[str, Any] | None:
    """The note of the last `settle`: what each line of the list holds, and what it closes."""
    return dict(_LAST_NOTE) if _LAST_NOTE is not None else None


def site_words(path: Path | None = None) -> str:
    """What a visitor is told PicWise covers, under "No products found", with the list's
    switch on ("" with it off): the `site` words of the open lines, a line's left out when a
    line above it already says it, in the list's order."""
    switches = read_switches(path)
    if switches is None or not switches.on:
        return ""
    said: list[Line] = []
    for line in switches.lines:
        if not line.site or not switches.line_open(line):
            continue
        if any(line.levels[:len(other.levels)] == other.levels for other in said):
            continue
        said.append(line)
    words = [line.site for line in said]
    if not words:
        return ""
    listed = words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    return f"PicWise covers {listed}."


def reset_for_tests() -> None:
    global _LAST_NOTE
    with _LOCK:
        _READ.clear()
    _LAST_NOTE = None
