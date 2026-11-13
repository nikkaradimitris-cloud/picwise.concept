"""What a card says of its price's history: down, up, or the same, and its last 30 nights.

The owner, 2026-11-13: the price's movement on the cards «με κάποιον έξυπνο τρόπο»,
then, to the chips proposed that day (a green ▼ when the price fell, a red ▲ when it rose,
a grey "Same price for N nights", a tap opening the last 30 nights), «Συμφωνώ με το
σχεδιασμό», on every card. The rule, as put to the owner the same day: today's price is
compared with **the last price the shop kept for at least 7 nights** (`MIN_HOLD_NIGHTS`),
so that a price raised for a night or two and brought back down never reads as a
discount (`PROJECT_RULES.md` §4: no fake savings). A change shows from its first night;
a price back where it was shows nothing; a price kept 7 nights or more, with no change
to tell, reads "Same price for N nights".

Every figure comes from the catalogue's memory (`catalogue_memory`): the nights each
product was seen and its price on each. A night the product was not listed is no night
at its price, so a price shown once and hidden is never a "kept" price. A change must be
at least £1 and at least 1% of the price it is compared with (`MIN_CHANGE_PENCE`,
`MIN_CHANGE_PERCENT`): a penny's movement is not news. A change older than the last 30
nights (`WINDOW_NIGHTS`) is not told.

Written each night after the memory, next to the prepared catalogue
(`price_notes.json.gz`, `write_price_notes`), with the prepared catalogue's own time: a
worker of the site shows a note only beside the catalogue of the same preparation
(`notes_for_catalogue`), so a night whose notes failed shows none rather than the night
before's. Each worker loads the file off to the side (`refresh_price_notes`, from the
prepared catalogue's keeper), so no visitor waits for it.
"""
from __future__ import annotations

import gzip
import json
import os
import sqlite3
import threading
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .catalogue_memory import SEEN_NIGHTS_KEPT, history_key

PRICE_NOTES_NAME = "price_notes.json.gz"
PRICE_NOTES_ENV = "PICWISE_PRICE_NOTES_FILE"
_FORMAT = "picwise-price-notes"
_VERSION = 1

# The rule (owner, 2026-11-13).
MIN_HOLD_NIGHTS = 7
WINDOW_NIGHTS = 30
MIN_CHANGE_PENCE = 100
MIN_CHANGE_PERCENT = 1

DOWN, UP, SAME = "down", "up", "same"
_CODES = {"d": DOWN, "u": UP}


@dataclass(frozen=True)
class PriceRun:
    """The nights a product was seen, one after another, at one price."""

    start: date
    end: date
    nights: int
    pence: int
    currency: str


@dataclass(frozen=True)
class PriceNote:
    """What a card says of its price. `runs` are those of the last `WINDOW_NIGHTS`
    nights, oldest first, cut to that window: for a change, every run of the window; for
    the same price, its one run."""

    kind: str
    night: date
    currency: str
    change_pence: int = 0
    since: date | None = None
    nights: int = 0
    runs: tuple[PriceRun, ...] = ()


# ---------------------------------------------------------------------------------------
# The rule, on one product's nights.


def runs_from_memory(
    nights_newest_first: list[str], seen_nights: int, prices: list[tuple[str, int | None, str]]
) -> list[PriceRun]:
    """A product's runs, newest first, from the prepared nights (newest first, the first
    the product's last night seen), the nights it was seen on (`seen_nights`, bit 0 the
    first of those) and its price records (night, pence, currency; oldest first), each
    the price from that night on. A night not seen ends a run; so does a new price."""
    runs: list[PriceRun] = []
    current: list[Any] | None = None  # [start, end, nights, pence, currency]
    index = len(prices) - 1
    for position, night in enumerate(nights_newest_first[:SEEN_NIGHTS_KEPT]):
        if not (seen_nights >> position) & 1:
            if current is not None:
                runs.append(_run(current))
                current = None
            continue
        while index >= 0 and prices[index][0] > night:
            index -= 1
        if index < 0 or prices[index][1] is None:
            break  # no price known from this night back: nothing older is told
        pence, currency = int(prices[index][1]), str(prices[index][2] or "")
        if current is not None and current[3] == pence and current[4] == currency:
            current[0] = night
            current[2] += 1
            continue
        if current is not None:
            runs.append(_run(current))
        current = [night, night, 1, pence, currency]
    if current is not None:
        runs.append(_run(current))
    return runs


def _run(values: list[Any]) -> PriceRun:
    start, end, nights, pence, currency = values
    return PriceRun(date.fromisoformat(start), date.fromisoformat(end), nights, pence, currency)


def note_from_runs(runs: list[PriceRun], night: date) -> PriceNote | None:
    """The note of a product seen tonight (`night`), from its runs, newest first; None
    when there is nothing true and worth telling yet."""
    if not runs or runs[0].end != night:
        return None
    current = runs[0]
    window_start = night - timedelta(days=WINDOW_NIGHTS - 1)
    for position in range(1, len(runs)):
        reference = runs[position]
        if reference.nights < MIN_HOLD_NIGHTS:
            continue
        since = runs[position - 1].start
        change = current.pence - reference.pence
        if (
            since >= window_start
            and reference.currency == current.currency
            and abs(change) >= MIN_CHANGE_PENCE
            and abs(change) * 100 >= MIN_CHANGE_PERCENT * reference.pence
        ):
            return PriceNote(
                kind=DOWN if change < 0 else UP,
                night=night,
                currency=current.currency,
                change_pence=abs(change),
                since=since,
                runs=tuple(reversed(_within(runs, window_start))),
            )
        break
    if current.nights >= MIN_HOLD_NIGHTS:
        return PriceNote(
            kind=SAME,
            night=night,
            currency=current.currency,
            nights=min(current.nights, WINDOW_NIGHTS),
            runs=tuple(_within([current], window_start)),
        )
    return None


def _within(runs: list[PriceRun], window_start: date) -> list[PriceRun]:
    kept = []
    for run in runs:
        if run.end < window_start:
            break
        if run.start < window_start:
            run = PriceRun(window_start, run.end, (run.end - window_start).days + 1, run.pence, run.currency)
        kept.append(run)
    return kept


# ---------------------------------------------------------------------------------------
# The night's file.


def price_notes_path() -> Path | None:
    """`PICWISE_PRICE_NOTES_FILE`, else the file beside the prepared catalogue the site
    reads; None where neither is configured (Vercel's backup keeps no memory)."""
    configured = str(os.environ.get(PRICE_NOTES_ENV) or "").strip()
    if configured:
        return Path(configured)
    from .prepared_catalogue import prepared_catalogue_path

    prepared = prepared_catalogue_path()
    return prepared.parent / PRICE_NOTES_NAME if prepared is not None else None


def write_price_notes(memory_path: Path, out_path: Path, *, prepared_at: datetime) -> dict[str, Any]:
    """Tonight's notes, from the memory at `memory_path`, written to `out_path` in one
    step; how many of each, for the night's public note."""
    prepared_at = prepared_at.astimezone(timezone.utc)
    night = prepared_at.date().isoformat()
    tonight = date.fromisoformat(night)
    notes: dict[str, Any] = {}
    counts = {DOWN: 0, UP: 0, SAME: 0}
    with closing(sqlite3.connect(f"file:{Path(memory_path)}?mode=ro", uri=True, timeout=60)) as db:
        nights = [
            row[0]
            for row in db.execute(
                "SELECT night FROM nights WHERE night <= ? ORDER BY night DESC LIMIT ?", (night, SEEN_NIGHTS_KEPT)
            )
        ]
        if nights and nights[0] == night:
            products = db.execute(
                "SELECT key, seen_nights, price_pence, currency FROM products WHERE last_seen = ? ORDER BY key",
                (night,),
            ).fetchall()
            changed = {
                row[0]
                for row in db.execute(
                    """SELECT prices.key FROM prices JOIN products USING (key)
                       WHERE products.last_seen = ? GROUP BY prices.key HAVING COUNT(*) > 1""",
                    (night,),
                )
            }
            records: dict[str, list[tuple[str, int | None, str]]] = {}
            if changed:
                for key, price_night, pence, currency in db.execute(
                    """SELECT prices.key, prices.night, prices.price_pence, prices.currency
                       FROM prices JOIN products USING (key)
                       WHERE products.last_seen = ? ORDER BY prices.key, prices.night""",
                    (night,),
                ):
                    if key in changed:
                        records.setdefault(key, []).append((price_night, pence, currency))
            for key, seen_nights, pence, currency in products:
                if pence is None:
                    continue
                bits = int(seen_nights or 1)
                if key in records:
                    note = note_from_runs(runs_from_memory(nights, bits, records[key]), tonight)
                else:
                    # One price ever: how many nights in a row, to tonight, it was seen.
                    in_a_row = min((~bits & (bits + 1)).bit_length() - 1, len(nights))
                    note = (
                        PriceNote(kind=SAME, night=tonight, currency=str(currency or ""),
                                  nights=min(in_a_row, WINDOW_NIGHTS))
                        if in_a_row >= MIN_HOLD_NIGHTS
                        else None
                    )
                if note is None:
                    continue
                notes[key] = _encode(note)
                counts[note.kind] += 1
    payload = {
        "format": _FORMAT,
        "version": _VERSION,
        # As the prepared catalogue writes its own (`prepared_catalogue`), to the
        # microsecond: the site matches the two exactly.
        "prepared_at": prepared_at.isoformat(),
        "night": night,
        "min_hold_nights": MIN_HOLD_NIGHTS,
        "window_nights": WINDOW_NIGHTS,
        "notes": notes,
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial = out_path.with_name(out_path.name + ".partial")
    with gzip.open(partial, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, separators=(",", ":"))
    os.replace(partial, out_path)
    return {"file": out_path.name, "night": night, "notes": len(notes), **counts}


def _encode(note: PriceNote) -> Any:
    """A same-price note is its nights alone (most notes, kept small in each worker); a
    change is [d|u, change, days since, currency, [[days ago from, to, pence], ...]]."""
    if note.kind == SAME:
        return int(note.nights)
    return [
        "d" if note.kind == DOWN else "u",
        note.change_pence,
        (note.night - note.since).days if note.since else 0,
        note.currency,
        [[(note.night - run.start).days, (note.night - run.end).days, run.pence] for run in note.runs],
    ]


# ---------------------------------------------------------------------------------------
# The site's side.


class PriceNotes:
    """One night's notes, as a worker of the site holds them."""

    def __init__(self, prepared_at: datetime, night: date, notes: dict[str, Any]) -> None:
        self.prepared_at = prepared_at
        self.night = night
        self._notes = notes

    def __len__(self) -> int:
        return len(self._notes)

    def note(self, shop: object, product_id: object, *, currency: str = "") -> PriceNote | None:
        """The note of the product a shop (as its feed row names it) lists under
        `product_id`, or None. A same-price note takes the card's currency."""
        value = self._notes.get(history_key(shop, product_id))
        if value is None:
            return None
        if isinstance(value, int):
            run_start = self.night - timedelta(days=value - 1)
            return PriceNote(
                kind=SAME, night=self.night, currency=currency, nights=value,
                runs=(PriceRun(run_start, self.night, value, 0, currency),),
            )
        try:
            code, change, since_days, note_currency, runs = value
            return PriceNote(
                kind=_CODES[code],
                night=self.night,
                currency=str(note_currency),
                change_pence=int(change),
                since=self.night - timedelta(days=int(since_days)),
                runs=tuple(
                    PriceRun(
                        self.night - timedelta(days=int(start)),
                        self.night - timedelta(days=int(end)),
                        int(start) - int(end) + 1,
                        int(pence),
                        str(note_currency),
                    )
                    for start, end, pence in runs
                ),
            )
        except (KeyError, TypeError, ValueError):
            return None


def read_price_notes(path: Path) -> PriceNotes | None:
    """The notes in `path`, or None when it is missing, unreadable or of another format."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, Mapping) or payload.get("format") != _FORMAT or payload.get("version") != _VERSION:
            return None
        notes = payload.get("notes")
        prepared_at = datetime.fromisoformat(str(payload["prepared_at"]))
        if prepared_at.tzinfo is None:
            return None
        return PriceNotes(
            prepared_at.astimezone(timezone.utc),
            date.fromisoformat(str(payload["night"])),
            dict(notes) if isinstance(notes, Mapping) else {},
        )
    except (OSError, ValueError, KeyError, TypeError, EOFError):
        return None


_STATE: dict[str, Any] = {}
_LOCK = threading.Lock()


def refresh_price_notes(*, kept: bool = True) -> str:
    """Load the night's notes when the file changed, off to the side, then put them in
    place in one step: "loaded", "current", "none" (no file) or "refused". The
    prepared catalogue's keeper calls it every few seconds (`kept`): from then on no
    request loads the file itself."""
    if kept:
        _STATE["kept"] = True
    path = price_notes_path()
    if path is None:
        return "none"
    try:
        stat = path.stat()
    except OSError:
        _STATE.pop("notes", None)
        _STATE.pop("file_key", None)
        return "none"
    file_key = (str(path), stat.st_mtime_ns, stat.st_size)
    if _STATE.get("file_key") == file_key:
        return "current"
    with _LOCK:
        if _STATE.get("file_key") == file_key:
            return "current"
        notes = read_price_notes(path)
        _STATE["file_key"] = file_key
        _STATE["notes"] = notes
    return "loaded" if notes is not None else "refused"


def notes_for_catalogue(prepared_at: datetime | None) -> PriceNotes | None:
    """The notes written with the prepared catalogue of `prepared_at`, or None: a card
    tells a price's history only beside the catalogue the same night's preparation
    wrote. Where no keeper runs (a local run, a test), the file is loaded here."""
    if prepared_at is None:
        return None
    if not _STATE.get("kept"):
        refresh_price_notes(kept=False)
    notes = _STATE.get("notes")
    if notes is None or notes.prepared_at != prepared_at.astimezone(timezone.utc):
        return None
    return notes


def _reset_price_notes_for_tests() -> None:
    _STATE.clear()
