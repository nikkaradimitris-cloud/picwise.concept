"""The answers to the question "is it the kind itself", read by the night's preparation.

`docs/PICWISE_KIND_ITSELF_RULES.md` (task 6 of the work split by model; the owner's plan of
21/11, step 8: a question to the AI for every product, «είναι το ίδιο το προϊόν ή αξεσουάρ,
ανταλλακτικό ή αναλώσιμο;»). The order is cheapest first, and the cheapest products the
rules read as a kind are what is filed beside it: a printer's rollers, a tablet's cases, a
TV's unit. The question is asked of the AI for the kind the site would show a product as
(`picwise_ai.itself`), twice where it matters: a first reading of every question, a second,
by a stronger model, of what the first would move and of each kind's first cards. Here the
preparation reads the answers, behind one switch (`data/kind_itself_switch.json`, frozen
with the code: turning it prepares the catalogue again):

- **only a second reading moves a product** (the rules' section 5): not itself, and the
  product leaves the kind (an accessory, a part, a consumable or a set leaves its broader
  kinds too; another thing leaves the kind, and its broader kinds are asked in turn); itself,
  for a kind the lists (`ai_shelves.checked_kinds`) took from it, and the product is of that
  kind again; unsure, or no second reading, and nothing changes;
- a product left with none of its kinds is doubtful, as when the lists leave it none: found
  by its words, never by its kind;
- **an answer stands until another takes its place** (4.7): one asked under other words of
  the kind (`picwise_ai.itself.kind_version`) is read as before and named to be asked again;
- **the brakes** (section 7) hold against what the catalogue showed the night before
  (`Shown`, kept beside the prepared file): the readings that came since the owner's last
  look (`looked_until`, beside the switch) are not applied to the products shown then where
  they would change, of one kind, more than a fifth of its products with a second reading,
  and at least 20; nor to any on a night they would change more than 5% of all such
  products. What a brake holds stays held, night after night, until the owner's word. A
  product not shown the night before is no change: its answers are read;
- **a new product waits for its answers** (section 6): the cap lets a product not shown the
  night before take a place only when no question of its own waits for a reading
  (`may_enter`); a product already shown stays as the lists read it until answered;
- **what is asked next** (section 8.2): the questions with no first reading, those that
  wait for a second, those to ask again, of the products the cap keeps or would take next,
  and the first cards of each kind (`job_items`, written for `picwise-itself.service`).

With the switch off, no answers file (`PICWISE_KIND_ITSELF_FILE` unset or nothing there), or
one that cannot be read, nothing is read and nothing waits: the catalogue is as the lists
read it. What was done is counted for the night's public note (`last_note`): counts and
kinds' names only, never a title or an id.

The answers file names no product: one record a question, by the question's key
(`ai_shelves.key_of`: a title's own words, the brand, the shop's category words) and the
kind.
"""
from __future__ import annotations

import gzip
import json
import os
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picwise_nlu.concept_understanding import UNCERTAIN_MARKER
from picwise_nlu.product_concepts import broader_concepts, get_product_concepts_by_id

from .contracts import ProviderProduct
from .normalization import extract_merchant_name

ANSWERS_FILE_ENV = "PICWISE_KIND_ITSELF_FILE"
SWITCH_FILE = Path(__file__).resolve().parents[2] / "data" / "kind_itself_switch.json"
JOBS_ENV = "PICWISE_ITSELF_JOBS"
JOBS_NAME = "itself.jsonl.gz"
# What the catalogue showed, kept beside the prepared file for the next night's brakes.
SHOWN_NAME = "kind_itself_shown.json.gz"
SHOWN_FORMAT = 1

ITSELF = "itself"
UNSURE = "unsure"
OTHER = "other"
# Not the kind itself, and nothing of its broader kinds either: it goes with the thing.
GOES_WITH = frozenset({"accessory", "part", "consumable", "set"})
NOT_ITSELF = GOES_WITH | {OTHER}
ANSWERS = frozenset(NOT_ITSELF | {ITSELF, UNSURE})
# A question with no answer is asked so many times in all, then left.
MOST_TRIES = 2
# A kind's first cards: so many of a search for its name, and its Recommended (the rules' 3).
FRONT = 24
# The brakes (the rules' 7.3 and 7.4).
KIND_BRAKE_SHARE = 0.20
KIND_BRAKE_MIN = 20
NIGHT_BRAKE_SHARE = 0.05
_KINDS_LISTED = 12
_DESCRIPTION_KEYS = ("description", "product_short_description", "short_description")
_ABOUT_CHARS = 400

FIRST = "first"
SECOND = "second"


@dataclass(frozen=True)
class Reading:
    """One model's answer to a question: what the product is to the kind, what it is in a
    few words, the model and the day."""

    said: str
    what: str = ""
    by: str = ""
    at: str = ""


@dataclass
class Record:
    """One question as the answers file keeps it: its key, its kind, the version its
    readings were asked under, the readings, and the tries of a reading asked for that came
    with no answer, with the version they were made under (0 again once a reading is kept)."""

    key: str
    kind: str
    version: str = ""
    first: Reading | None = None
    second: Reading | None = None
    tries: int = 0
    tried: str = ""

    def to_json(self) -> dict[str, Any]:
        document: dict[str, Any] = {"k": self.key, "kind": self.kind, "v": self.version}
        for name, reading in ((FIRST, self.first), (SECOND, self.second)):
            if reading is not None:
                document[name] = {"is": reading.said, "what": reading.what, "by": reading.by, "at": reading.at}
        if self.tries:
            document["tries"] = self.tries
            document["tried"] = self.tried
        return document

    def no_answer(self, version: str) -> None:
        """A reading asked for under `version` came with no answer."""
        self.tries = self.tries + 1 if self.tried == version else 1
        self.tried = version

    def tries_under(self, version: str) -> int:
        return self.tries if self.tried == version else 0


def _reading(document: Any) -> Reading | None:
    if not isinstance(document, Mapping) or document.get("is") not in ANSWERS:
        return None
    return Reading(
        said=str(document["is"]),
        what=" ".join(str(document.get("what") or "").split()),
        by=str(document.get("by") or ""),
        at=str(document.get("at") or ""),
    )


def read_answers(path: str | os.PathLike[str] | None) -> dict[tuple[str, str], Record]:
    """The questions kept, by (key, kind); none when the file is not there or cannot be
    read. A line that is no record is passed over; of two records of one question, the
    later stands."""
    found: dict[tuple[str, str], Record] = {}
    if not path:
        return found
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for text in handle:
                try:
                    document = json.loads(text)
                except ValueError:
                    continue
                if not isinstance(document, Mapping):
                    continue
                key, kind = document.get("k"), document.get("kind")
                if not isinstance(key, str) or not isinstance(kind, str) or not key or not kind:
                    continue
                try:
                    tries = int(document.get("tries") or 0)
                except (TypeError, ValueError):
                    tries = 0
                found[(key, kind)] = Record(
                    key=key, kind=kind, version=str(document.get("v") or ""),
                    first=_reading(document.get(FIRST)), second=_reading(document.get(SECOND)), tries=max(0, tries),
                    tried=str(document.get("tried") or "") if tries > 0 else "",
                )
    except (OSError, EOFError, UnicodeDecodeError, gzip.BadGzipFile):
        return {}
    return found


def answers_readable(path: str | os.PathLike[str]) -> bool:
    """Can the answers file be written over: not there yet, or read through to its end? A
    file that is there and cannot be read is kept as it is, for a person to look at."""
    if not Path(path).exists():
        return True
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for _text in handle:
                pass
    except (OSError, EOFError, UnicodeDecodeError, gzip.BadGzipFile):
        return False
    return True


def write_answers(path: str | os.PathLike[str], records: Mapping[tuple[str, str], Record]) -> None:
    """Every question, written whole to a file beside `path` and then put in its place."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        for key in sorted(records):
            handle.write(json.dumps(records[key].to_json(), ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, target)


def read_switch(path: Path = SWITCH_FILE) -> tuple[bool, str]:
    """The switch of the rules' 7.6 and the day of the last look (7.5): (the answers are
    read, the day up to which they were looked at)."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, ""
    if not isinstance(document, Mapping):
        return False, ""
    return document.get("gate") is True, str(document.get("looked_until") or "")


def real_kinds(kinds: Iterable[str]) -> frozenset[str]:
    return frozenset(kind for kind in kinds if not kind.startswith("__"))


@dataclass(frozen=True)
class Shown:
    """What a catalogue showed, for the next night's brakes (the rules' 7.2 to 7.4): each
    product that has a question, by its feed row (`catalogue_cap.row_key`), with the kinds
    it was shown as; and what a brake held that night, with the night it first held."""

    rows: Mapping[str, frozenset[str]]
    held: Mapping[str, str] = field(default_factory=dict)
    night_held: str = ""
    night: str = ""


def shown_path(prepared_path: Path) -> Path:
    """Where what a catalogue showed is kept, for a prepared file written at `prepared_path`."""
    return Path(prepared_path).parent / SHOWN_NAME


def read_shown(path: str | os.PathLike[str] | None) -> Shown | None:
    """What the catalogue of the night before showed; None when nothing is kept or it
    cannot be read, and then the brakes have nothing to hold against."""
    if not path:
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, EOFError, ValueError, gzip.BadGzipFile):
        return None
    if not isinstance(document, Mapping) or document.get("v") != SHOWN_FORMAT or not isinstance(document.get("rows"), Mapping):
        return None
    held = document.get("held")
    return Shown(
        rows={str(row): frozenset(str(kinds or "").split()) for row, kinds in document["rows"].items()},
        held={str(kind): str(since) for kind, since in held.items() if since} if isinstance(held, Mapping) else {},
        night_held=str(document.get("night_held") or ""),
        night=str(document.get("night") or ""),
    )


def write_shown(path: str | os.PathLike[str], rows: Mapping[str, str], *, held: Mapping[str, str] | None = None,
                night_held: str = "", night: str = "") -> int:
    """What tonight's catalogue shows (`shown_rows`) and what its brakes hold, written whole
    and then put in place; the rows written."""
    target = Path(path)
    temporary = target.with_name(target.name + ".part")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump({"v": SHOWN_FORMAT, "night": night, "held": dict(held or {}), "night_held": night_held,
                   "rows": dict(rows)}, handle, ensure_ascii=False, separators=(",", ":"))
    os.replace(temporary, target)
    return len(rows)


def narrowest(kinds: Iterable[str]) -> tuple[str, ...]:
    """The kinds that are no broader kind of another of them, in a steady order."""
    kinds = frozenset(kinds)
    broad = {wide for kind in kinds for wide in broader_concepts(kind)[1:]}
    return tuple(sorted(kind for kind in kinds if kind not in broad)) or tuple(sorted(kinds))


def _parents(kind: str) -> tuple[str, ...]:
    concept = get_product_concepts_by_id().get(kind)
    return tuple(concept.broader) if concept is not None else ()


def _held_by_another(kind: str, kinds: Iterable[str], but: Iterable[str]) -> bool:
    """Is `kind` the broader kind of another of `kinds`, those of `but` apart?"""
    apart = set(but) | {kind}
    return any(kind in broader_concepts(other)[1:] for other in kinds if other not in apart)


@dataclass(frozen=True)
class Settled:
    """One product's kinds after its answers (the rules' section 5)."""

    kinds: frozenset[str]
    # What left a kind, as (kind, answer, the day of the reading); what came back, as (kind, day).
    out: tuple[tuple[str, str, str], ...] = ()
    back: tuple[tuple[str, str], ...] = ()
    # The questions that wait: for a first reading, for a second.
    want_first: tuple[str, ...] = ()
    want_second: tuple[str, ...] = ()
    # The kinds with a second reading in force, whatever it said.
    read_twice: tuple[str, ...] = ()
    # Every kind whose question was looked up.
    consulted: tuple[str, ...] = ()


def settle(
    before: frozenset[str],
    after: frozenset[str],
    lookup: Callable[[str], Record | None],
) -> Settled:
    """A product's kinds from its own kinds (`before`), the kinds the lists leave it
    (`after`) and the records of its questions (`lookup`, by kind; None for a question
    never asked)."""
    own = real_kinds(before)
    if not own:
        return Settled(after)
    left = set(real_kinds(after))
    taken = set(own - left)
    final = set(left)
    out: list[tuple[str, str, str]] = []
    back: list[tuple[str, str]] = []
    want_first: list[str] = []
    want_second: list[str] = []
    read_twice: list[str] = []
    consulted: list[str] = []

    def readings(kind: str) -> tuple[str | None, Reading | None, bool]:
        """The first reading's answer (None: none yet, the question waiting when it may
        still be asked), the second reading, and whether a second may still be asked (a
        reading with no answer is asked `MOST_TRIES` times, then left)."""
        consulted.append(kind)
        record = lookup(kind)
        if record is None or record.first is None:
            if record is None or record.tries < MOST_TRIES:
                want_first.append(kind)
            return None, None, False
        if record.second is not None:
            read_twice.append(kind)
        return record.first.said, record.second, record.tries < MOST_TRIES

    # The kinds the lists leave it: a second reading that is not itself takes it out.
    todo = list(narrowest(left))
    asked: set[str] = set()
    while todo:
        kind = todo.pop(0)
        if kind in asked or kind not in final:
            continue
        asked.add(kind)
        first, second, may_ask = readings(kind)
        if first is None:
            continue
        if second is None:
            if first != ITSELF and may_ask:
                want_second.append(kind)
            continue
        if second.said in GOES_WITH:
            gone = {kind} | {wide for wide in broader_concepts(kind)[1:] if wide in final}
            gone = {one for one in gone if one == kind or not _held_by_another(one, final, gone)}
            final -= gone
            out.append((kind, second.said, second.at))
        elif second.said == OTHER:
            final.discard(kind)
            out.append((kind, second.said, second.at))
            todo.extend(parent for parent in _parents(kind) if parent in final and not _held_by_another(parent, final, ()))
    # The kinds the lists took from it: a second reading that is itself brings it back.
    todo = list(narrowest(taken))
    asked = set()
    while todo:
        kind = todo.pop(0)
        if kind in asked or kind not in taken:
            continue
        asked.add(kind)
        first, second, may_ask = readings(kind)
        if first is None:
            continue
        if first == OTHER and second is None:
            todo.extend(parent for parent in _parents(kind) if parent in taken)
            continue
        if second is None:
            if first == ITSELF and may_ask:
                want_second.append(kind)
            continue
        if second.said == ITSELF:
            final |= {kind} | {wide for wide in broader_concepts(kind)[1:] if wide in taken}
            back.append((kind, second.at))
        elif second.said == OTHER:
            todo.extend(parent for parent in _parents(kind) if parent in taken)
    if final == left:
        kinds = after
    elif not final:
        kinds = frozenset({UNCERTAIN_MARKER})
    else:
        # The context a product carries (a pet's, a camping product's) stays with it.
        markers = (after if left else before) - real_kinds(after if left else before) - {UNCERTAIN_MARKER}
        kinds = frozenset(final) | markers
    return Settled(kinds, tuple(out), tuple(back), tuple(want_first), tuple(want_second), tuple(read_twice),
                   tuple(consulted))


# --------------------------------------------------------------------------------------
# The night: every product settled, the brakes, what waits
# --------------------------------------------------------------------------------------


def _shop(product: ProviderProduct) -> str:
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    return " ".join(str(extract_merchant_name(raw) or "").split())


@dataclass
class _Moved:
    """A product whose kinds a second reading changed, kept so that a brake can put it back."""

    before: frozenset[str]
    after: frozenset[str]
    key: str
    young: frozenset[str]


# A product's flags, one byte a place: a question of it waits for a reading; a question of
# it is to be asked again; it has a question at all.
_WAITS, _AGAIN, _ASKED = 1, 2, 4


@dataclass
class Night:
    """One preparation's reading of the answers."""

    records: Mapping[tuple[str, str], Record]
    looked_until: str = ""
    versions: Callable[[str], str] | None = None
    # What the catalogue of the night before showed (None: nothing kept), and tonight's day.
    shown: Shown | None = None
    today: str = ""
    moved: dict[int, _Moved] = field(default_factory=dict)
    # Per place, the flags above: flags only, since most products a feed lists are never
    # shown and never asked (1.6 million rows on 22/11).
    flags: bytearray = field(default_factory=bytearray)
    products_waiting: int = 0
    products_to_ask_again: int = 0
    # The places with a second reading in force, with its kinds.
    twice: list[tuple[int, tuple[str, ...]]] = field(default_factory=list)
    out: Counter = field(default_factory=Counter)
    out_by_kind: Counter = field(default_factory=Counter)
    back_by_kind: Counter = field(default_factory=Counter)
    # The brakes (`finish`): whether they had the night before to hold against; the
    # products shown then that the readings since the last look would change; what is held.
    brakes_stand: bool = False
    changed_of_shown: int = 0
    products_held: int = 0
    held_kinds: dict[str, int] = field(default_factory=dict)
    held_since: dict[str, str] = field(default_factory=dict)
    night_held_since: str = ""
    _version_cache: dict[str, str] = field(default_factory=dict)

    def version(self, kind: str) -> str:
        found = self._version_cache.get(kind)
        if found is None:
            if self.versions is not None:
                found = self.versions(kind)
            else:
                from picwise_ai.itself import kind_version

                found = kind_version(kind)
            self._version_cache[kind] = found
        return found

    def lookup(self, key: str, hidden: Callable[[str, Record], bool] | None = None) -> Callable[[str], Record | None]:
        """The records of one product's questions, by kind. An answer asked under other
        words of the kind stands until another takes its place (the rules' 4.7); the tries
        count only under today's words. `hidden` leaves out a record's second reading (a
        brake)."""

        def find(kind: str) -> Record | None:
            record = self.records.get((key, kind))
            if record is None:
                return None
            second = record.second
            if hidden is not None and second is not None and hidden(kind, record):
                second = None
            tries = record.tries_under(self.version(kind))
            if second is record.second and tries == record.tries:
                return record
            return Record(record.key, record.kind, record.version, record.first, second, tries, record.tried)

        return find

    def again(self, key: str, kind: str) -> bool:
        """Is the question's answer one to ask again: kept, asked under other words of the
        kind than today's, and not already asked again in vain `MOST_TRIES` times?"""
        record = self.records.get((key, kind))
        if record is None or record.first is None:
            return False
        version = self.version(kind)
        return bool(version) and record.version != version and record.tries_under(version) < MOST_TRIES

    def young(self, day: str) -> bool:
        """Did a reading come since the owner's last look (the rules' 7.5)?"""
        return bool(day) and day > self.looked_until

    def _flag(self, place: int, flags: int) -> None:
        if place >= len(self.flags):
            self.flags.extend(bytes(place + 1 - len(self.flags)))
        self.flags[place] |= flags

    def settle(self, place: int, before: frozenset[str], after: frozenset[str], key: str) -> frozenset[str]:
        """One product's kinds after its answers; what moved, waits or was read is counted."""
        settled = settle(before, after, self.lookup(key))
        flags = _ASKED
        if settled.want_first or settled.want_second:
            flags |= _WAITS
            self.products_waiting += 1
        if any(self.again(key, kind) for kind in settled.consulted):
            flags |= _AGAIN
            self.products_to_ask_again += 1
        self._flag(place, flags)
        if settled.read_twice:
            self.twice.append((place, settled.read_twice))
        if settled.out or settled.back:
            young = {kind for kind, _said, day in settled.out if self.young(day)}
            young |= {kind for kind, day in settled.back if self.young(day)}
            self.moved[place] = _Moved(before, after, key, frozenset(young))
        return settled.kinds

    def _has(self, place: int, flag: int) -> bool:
        return place < len(self.flags) and bool(self.flags[place] & flag)

    def waits(self, place: int) -> bool:
        return self._has(place, _WAITS)

    def to_ask(self, place: int) -> bool:
        return self._has(place, _WAITS | _AGAIN)

    def asked(self, place: int) -> bool:
        return self._has(place, _ASKED)

    def finish(self, kinds: list[frozenset[str]], row: Callable[[int], str] | None = None) -> list[frozenset[str]]:
        """The brakes (the rules' 7.3 and 7.4), then the count of what moved. `kinds` are
        every product's kinds as `settle` gave them, in order; `row` gives a place's feed
        row, to find it in what the night before showed. A product shown then, that the
        readings since the last look would change, is put back as it was shown when a brake
        holds: its kind's, or the whole night's."""
        shown = self.shown
        self.brakes_stand = shown is not None and row is not None
        changed_at: dict[int, frozenset[str]] = {}
        if shown is not None and row is not None:
            held_before = {kind: since for kind, since in shown.held.items() if since > self.looked_until}
            night_before = shown.night_held if shown.night_held > self.looked_until else ""
            twice_shown: Counter = Counter()
            products_twice_shown = 0
            for place, read_kinds in self.twice:
                if row(place) in shown.rows:
                    products_twice_shown += 1
                    twice_shown.update(read_kinds)
            changes: Counter = Counter()
            for place, moved in self.moved.items():
                if not moved.young:
                    continue
                was = shown.rows.get(row(place))
                if was is None:
                    continue  # not shown the night before: a new product, no change
                now = real_kinds(kinds[place])
                changed = frozenset(kind for kind in moved.young if (kind in was) != (kind in now))
                if not changed:
                    continue  # read on an earlier night, and shown so since
                changed_at[place] = changed
                changes.update(changed)
            self.changed_of_shown = len(changed_at)
            # A kind's night (7.3): the kinds held before stay held; a kind is held from
            # tonight when the readings would change too many of its products.
            self.held_since = dict(held_before)
            for kind, count in changes.items():
                if kind not in self.held_since and count >= KIND_BRAKE_MIN \
                        and count > KIND_BRAKE_SHARE * max(1, twice_shown[kind]):
                    self.held_since[kind] = self.today
            self.held_kinds = {kind: changes[kind] for kind in self.held_since}
            # The whole night (7.4): what no kind's brake holds, counted over every kind.
            loose = sum(1 for changed in changed_at.values() if changed - self.held_since.keys())
            night_trips = loose >= KIND_BRAKE_MIN and loose > NIGHT_BRAKE_SHARE * max(1, products_twice_shown)
            self.night_held_since = night_before or (self.today if night_trips else "")
        for place, moved in self.moved.items():
            changed = changed_at.get(place, frozenset())
            held = changed if self.night_held_since else changed & self.held_since.keys()
            if held:
                settled = settle(moved.before, moved.after, self.lookup(
                    moved.key, lambda kind, record, held=held: kind in held and self.young(record.second.at)))
                kinds[place] = settled.kinds
                self.products_held += 1
            else:
                settled = settle(moved.before, moved.after, self.lookup(moved.key))
            for kind, said, _day in settled.out:
                self.out[said] += 1
                self.out_by_kind[kind] += 1
            for kind, _day in settled.back:
                self.back_by_kind[kind] += 1
        return kinds

    def note(self) -> dict[str, Any]:
        def listed(counter: Counter) -> list[dict[str, Any]]:
            return [{"kind": kind, "products": count} for kind, count in counter.most_common(_KINDS_LISTED)]

        return {
            "applied": True,
            "looked_until": self.looked_until,
            "questions_kept": len(self.records),
            "products_with_a_second_reading": len(self.twice),
            "left_a_kind": sum(self.out_by_kind.values()),
            "left_by_answer": dict(sorted(self.out.items())),
            "came_back": sum(self.back_by_kind.values()),
            "kinds_that_lost_the_most": listed(self.out_by_kind),
            "kinds_that_gained_the_most": listed(self.back_by_kind),
            "brakes": "stood" if self.brakes_stand else "no memory of the night before: nothing to hold against",
            "changed_of_what_was_shown": self.changed_of_shown,
            "held_as_shown": self.products_held,
            "held_by_a_kinds_brake": [{"kind": kind, "products": self.held_kinds.get(kind, 0), "since": since}
                                      for kind, since in sorted(self.held_since.items())],
            "held_by_the_nights_brake": self.night_held_since,
            "products_with_a_question_waiting": self.products_waiting,
            "products_to_ask_again": self.products_to_ask_again,
        }


_NIGHT: Night | None = None
_LAST_NOTE: dict[str, Any] | None = None
_SHOWN_FILE: Path | None = None


def remember_at(path: str | os.PathLike[str] | None) -> None:
    """Where what a catalogue showed is kept (`shown_path`), named by the preparation's tool
    before the night begins; None forgets it."""
    global _SHOWN_FILE
    _SHOWN_FILE = Path(path) if path else None


def begin_night(*, switch: tuple[bool, str] | None = None, path: str | os.PathLike[str] | None = None,
                versions: Callable[[str], str] | None = None, shown: Shown | None = None,
                today: str | None = None) -> Night | None:
    """The night's reading of the answers, or None (and why, in the note) when nothing is
    read: the switch off, no answers file named, none there, or none in it."""
    global _NIGHT, _LAST_NOTE
    _NIGHT = None
    gate, looked_until = read_switch() if switch is None else switch
    if not gate:
        _LAST_NOTE = {"applied": False, "why": "the switch is off"}
        return None
    configured = path if path is not None else str(os.environ.get(ANSWERS_FILE_ENV) or "").strip()
    if not configured:
        _LAST_NOTE = {"applied": False, "why": "no answers file named"}
        return None
    if not Path(configured).exists():
        _LAST_NOTE = {"applied": False, "why": "no answers yet"}
        return None
    records = read_answers(configured)
    if not records:
        _LAST_NOTE = {"applied": False, "why": "the answers file cannot be read, or holds no answer"}
        return None
    _NIGHT = Night(
        records=records, looked_until=looked_until, versions=versions,
        shown=shown if shown is not None else read_shown(_SHOWN_FILE),
        today=today or datetime.now(timezone.utc).date().isoformat(),
    )
    return _NIGHT


def settle_catalogue(
    night: Night,
    count: int,
    read: Callable[[int], tuple[frozenset[str], frozenset[str], str]],
    row: Callable[[int], str] | None = None,
) -> tuple[frozenset[str], ...]:
    """Every product's kinds after its answers and the brakes. `read` gives, for each of the
    `count` places, the product's own kinds, the kinds the lists leave it, and its question
    key ("" for a product with no kind of its own, which has no question); `row`, a place's
    feed row (`catalogue_cap.row_key`), for the brakes."""
    global _LAST_NOTE
    kinds: list[frozenset[str]] = []
    for place in range(count):
        before, after, key = read(place)
        kinds.append(night.settle(place, before, after, key) if key else after)
    kinds = night.finish(kinds, row)
    _LAST_NOTE = night.note()
    return tuple(kinds)


def shown_rows(night: Night, products: Sequence[ProviderProduct], kinds: Sequence[frozenset[str]],
               places: Iterable[int]) -> dict[str, str]:
    """What tonight's catalogue shows, for the next night's brakes: of the products at
    `places` (those the cap keeps), each that has a question, by its feed row, with the
    kinds it is shown as."""
    from .catalogue_cap import row_key

    return {row_key(products[place]): " ".join(sorted(real_kinds(kinds[place])))
            for place in places if night.asked(place)}


def gate_on() -> bool:
    """Whether the last preparation read the answers, so that a new product waits for its own."""
    return _NIGHT is not None


def tonight() -> Night | None:
    """The night the last preparation read, for the preparation's tool."""
    return _NIGHT


def may_enter(product: ProviderProduct) -> bool:
    """The rules' section 6: a product not shown the night before takes a place only when
    no question of its own waits for a reading; every product may while nothing is read.
    Worked out for the one product (its kinds read again): the cap asks it only of the few
    products whose checks passed (`checks_applied.may_enter` first)."""
    if _NIGHT is None:
        return True
    from .search_selection import _product_search_fields, kinds_read

    before, after, key = kinds_read(product, _product_search_fields(product))
    if not key:
        return True
    settled = settle(before, after, _NIGHT.lookup(key))
    return not settled.want_first and not settled.want_second


def last_note() -> dict[str, Any] | None:
    return dict(_LAST_NOTE) if _LAST_NOTE is not None else None


def reset_for_tests() -> None:
    global _NIGHT, _LAST_NOTE, _SHOWN_FILE
    _NIGHT, _LAST_NOTE, _SHOWN_FILE = None, None, None


# --------------------------------------------------------------------------------------
# What is asked next
# --------------------------------------------------------------------------------------


def item_of(product: ProviderProduct) -> dict[str, str]:
    """A product as the model reads it (`picwise_ai.itself.item_line`)."""
    from picwise_ai.shelves import shop_words

    raw = product.raw if isinstance(product.raw, Mapping) else {}
    about = next((" ".join(str(raw.get(name)).split()) for name in _DESCRIPTION_KEYS if str(raw.get(name) or "").strip()), "")
    return {
        "title": " ".join(str(product.title or "").split()),
        "brand": str(product.brand or ""),
        "category": shop_words(raw),
        "price": f"{product.price_text} {product.currency}".strip(),
        "about": about[:_ABOUT_CHARS],
    }


def _price(product: ProviderProduct) -> float:
    from .decision_labels import parse_price_amount

    amount = parse_price_amount(product.price_text)
    return float(amount) if amount is not None else float("inf")


def first_cards(
    products: Sequence[ProviderProduct], kinds: Sequence[frozenset[str]], cards: int | None = None
) -> dict[str, list[int]]:
    """Per kind, the places (in `products`) of its first cards: a search for the kind's name
    as the site orders it (`search_selection._price_first_products`: one card a product, the
    cheapest first), its first `cards` and its Recommended. Of the new products only, and
    not a pet's or a camping product where the plain search leaves them out."""
    from .search_selection import (
        _context_allows_member,
        _median_recommendation,
        _price_first_products,
        product_non_new_condition,
    )

    cards = FRONT if cards is None else cards
    members: dict[str, list[int]] = {}
    for place, (product, product_kinds) in enumerate(zip(products, kinds)):
        for kind in product_kinds:
            if kind.startswith("__"):
                continue
            if product_non_new_condition(product) or not _context_allows_member(product_kinds, kind, ()):
                continue
            members.setdefault(kind, []).append(place)
    place_of = {id(product): place for place, product in enumerate(products)}
    front: dict[str, list[int]] = {}
    for kind, places in members.items():
        ordered = _price_first_products([products[place] for place in places])
        chosen = [place_of[id(entry.product)] for entry in ordered[:cards]]
        recommended, _status = _median_recommendation(ordered)
        if recommended is not None:
            place = place_of[id(ordered[recommended].product)]
            if place not in chosen:
                chosen.append(place)
        front[kind] = chosen
    return front


def job_items(
    night: Night,
    products: Sequence[ProviderProduct],
    places: Iterable[int],
    read: Callable[[int], tuple[frozenset[str], frozenset[str], str]],
    kept: Sequence[ProviderProduct] = (),
    kept_kinds: Sequence[frozenset[str]] = (),
) -> list[dict[str, Any]]:
    """What the AI is asked next (the rules' 8.2), one item a question: of the products at
    `places` (those the cap keeps and the next ones it would take), the questions that wait
    for a first reading or a second, and those to ask again, their answers asked under other
    words of the kind (`read`, as `settle_catalogue` takes it, reads again the kinds of the
    few named); and, of the products the cap keeps (`kept`, with their kinds), each kind's
    first cards whose first reading is itself and that have no second. A question with no
    first reading whose product is cheaper than its kind's last first card is named as a
    first card too, so that its two readings come the same morning. Each kind's cheapest
    first, the kinds in turn."""
    from .ai_shelves import key_of

    items: dict[tuple[str, str], dict[str, Any]] = {}
    fronts = first_cards(kept, kept_kinds) if kept else {}
    # The price of each kind's last first card (none: the kind has fewer cards than a front).
    last = {kind: _price(kept[cards[FRONT - 1]]) for kind, cards in fronts.items() if len(cards) >= FRONT}

    def why_of(product: ProviderProduct, kind: str, taken: frozenset[str]) -> str:
        if kind in taken:
            return "taken"
        if kept and any(_price(product) <= last.get(wide, float("inf")) for wide in broader_concepts(kind)):
            return "first card"
        return "kind"

    def add(product: ProviderProduct, key: str, kind: str, want: str, why: str, again: bool = False) -> None:
        item = items.get((key, kind))
        if item is None:
            item = items[(key, kind)] = {"k": key, "kind": kind, "want": want, "why": why, **item_of(product),
                                         "shop": _shop(product), "products": 0, "_price": _price(product)}
        else:
            if want == FIRST:
                item["want"] = FIRST
            if why == "first card":
                item["why"] = why
        if again:
            item["again"] = True
        item["products"] += 1
        item["_price"] = min(item["_price"], _price(product))

    for place in places:
        if not night.to_ask(place):
            continue
        before, after, key = read(place)
        if not key:
            continue
        settled = settle(before, after, night.lookup(key))
        taken = real_kinds(before) - real_kinds(after)
        for kind in settled.want_first:
            add(products[place], key, kind, FIRST, why_of(products[place], kind, taken))
        for kind in settled.want_second:
            add(products[place], key, kind, SECOND, "taken" if kind in taken else "kind")
        for kind in settled.consulted:
            if night.again(key, kind):
                add(products[place], key, kind, FIRST, why_of(products[place], kind, taken), again=True)
    if kept:
        for kind, front in fronts.items():
            for place in front:
                product = kept[place]
                raw = product.raw if isinstance(product.raw, Mapping) else {}
                key = key_of(str(product.title or ""), str(product.brand or ""), raw)
                # The question a first card answers for is its narrowest kind's.
                for asked_kind in narrowest(real_kinds(k for k in kept_kinds[place] if kind in broader_concepts(k))):
                    record = night.lookup(key)(asked_kind)
                    if record is None or record.first is None or record.first.said != ITSELF or record.second is not None:
                        continue
                    if night.again(key, asked_kind):
                        add(product, key, asked_kind, FIRST, "first card", again=True)
                    elif record.tries < MOST_TRIES:
                        add(product, key, asked_kind, SECOND, "first card")
    # Each kind's cheapest first, the kinds in turn: a run stopped by its limit has served
    # every kind's first cards.
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for item in items.values():
        by_kind.setdefault(item["kind"], []).append(item)
    for rows in by_kind.values():
        rows.sort(key=lambda item: (item["_price"], item["k"]))
    ordered: list[dict[str, Any]] = []
    rank = 0
    while True:
        row = [rows[rank] for _kind, rows in sorted(by_kind.items()) if rank < len(rows)]
        if not row:
            break
        ordered.extend(row)
        rank += 1
    for item in ordered:
        del item["_price"]
    return ordered


def write_job(items: Sequence[Mapping[str, Any]], folder: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    """The questions the AI is asked next (`job_items`), one JSON a line, written whole and
    then put in place, in the folder `JOBS_ENV` names (shared with picwise-itself); None
    with no folder named."""
    configured = folder if folder is not None else str(os.environ.get(JOBS_ENV) or "").strip()
    if not configured:
        return None
    target = Path(configured) / JOBS_NAME
    temporary = target.with_name(target.name + ".part")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, target)
    wants = Counter(str(item.get("want") or "") for item in items)
    return {"questions": len(items), "first": wants[FIRST], "second": wants[SECOND],
            "again": sum(1 for item in items if item.get("again"))}
