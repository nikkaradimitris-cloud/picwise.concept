"""The AI's shelves read by the catalogue: the same two rules for both Awin links.

Owner, 2026-11-20: the search fell after the second link («ότι κανόνες ισχύουν για το ένα
feed πρέπει να ισχύουν και για το καινούργιο»), and not product by product: «Αυτό που πρέπει
να κάνουμε είναι να φτιάξουμε μηχανισμούς και κανόνες σχετικά με το ai που μπορεί να κάνει
την ταξινόμηση». A first-link row carries two words of its shop that check each other: its
own category (`product_type`) and a line of Google's taxonomy (`google_product_category`).
A second-link row carries only the first; PicWise guessed the second from the same words
(`awin_categories`), so it checked nothing: a cable shop's "RJ45 Boots" went to the shoes.
Claude Haiku 5.5 now gives every product a line of Google's taxonomy, read from its title,
brand, price and the shop's words (`deployment/server/scan_shelves.py`, every product once:
`picwise_ai.shelves.ask_key`), kept in the file `PICWISE_AI_SHELVES_FILE` names (on the
server `/srv/picwise/assist/shelves/answers.jsonl.gz`). Without the file, nothing changes.

1. A second-link row's Google line is the AI's (`second_link_answer`), in place of the one
   guessed: the rules that read a shelf (the kind's aisle, the cap) read it as a first-link
   row's. Its own category stays its type, and its Awin category columns leave the row, as
   a first-link row has none: the search read them as a shelf of their own, before the
   Google line ("RJ45 Boots" kept a cable boot among the boots). The key it was asked by
   stays in the row (`AI_KEY_COLUMN`).
2. Every product, of either link (owner, 2026-11-20, 19:00: «ένα προϊόν εμφανίζεται σε ένα
   είδος μόνο αν η κατηγορία που του έδωσε το AI είναι στη λίστα του είδους. Ο ίδιος κανόνας
   και για τα δύο feeds»): each kind of the site has its own lines of Google's taxonomy,
   written once by the AI and checked (`picwise_ai.kind_lines`, kept in
   `data/kind_lines/google_lines_by_kind.json`); a kind's list holds its narrower kinds'
   lines too; a line the AI chose holds the lines under it, a line its check added (where
   the products read as the kind really are, judged the kind itself) only itself. A product keeps a kind its type, shelf
   and title give only when the AI's line for it is on that kind's list (`checked_kinds`);
   a product left with none of its kinds is doubtful (`UNCERTAIN_MARKER`): it is found by
   its words, never by its kind ("watches" shows watches; "garmin strap" still finds the
   strap). No line from the AI (not asked yet, refused, "no line fits", or one of the
   tree's first lines, which it gave when it slipped: `SLIP_LINES`), or a kind with no
   list, changes nothing. Until 20/11 19:00 the AI's line was read through the kind reader
   (rule 2 of 16:40), which read "Hardware Accessories > Washers" as a washing machine.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

AI_SHELVES_FILE_ENV = "PICWISE_AI_SHELVES_FILE"
# A second-link row given the AI's line keeps the key it was asked by here: its own Awin
# category columns, which the key is made of, leave the row (rule 1).
AI_KEY_COLUMN = "ai_shelf_key"

_LOCK = threading.Lock()
_LOADED: dict[str, Any] = {}
# The file is looked at again at most so often: a preparation asks for each product.
_RECHECK_SECONDS = 60.0


def _configured_path() -> Path | None:
    configured = str(os.environ.get(AI_SHELVES_FILE_ENV) or "").strip()
    return Path(configured) if configured else None


# A product the AI refused or did not answer is asked so many times in all
# (`deployment/server/scan_shelves.py`, `MOST_TRIES`); then it is refused for good: no line,
# which the checks read as no category (the checks' rules, 5.5).
MOST_TRIES = 2


def _read_file(path: Path) -> tuple[dict[str, str], frozenset[str]]:
    found: dict[str, str] = {}
    refused: set[str] = set()
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for text in handle:
                try:
                    record = json.loads(text)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                key, line = record.get("k"), record.get("line")
                if isinstance(key, str) and isinstance(line, str):
                    found[key] = sys.intern(line)
                elif isinstance(key, str) and line is None and "line" in record:
                    try:
                        tries = int(record.get("tries") or 0)
                    except (TypeError, ValueError):
                        tries = 0
                    if tries >= MOST_TRIES:
                        refused.add(key)
    except (OSError, EOFError, gzip.BadGzipFile):
        return {}, frozenset()
    return found, frozenset(refused)


def read_answers(path: Path) -> dict[str, str]:
    """The AI's lines by key, from the scan's answers file: only the lines given ("" for
    "no line fits", refusals and lines that are not answers left out). Empty when the
    file cannot be read: the catalogue is then prepared as without it."""
    return _read_file(path)[0]


def read_refused(path: Path) -> frozenset[str]:
    """The keys the AI refused, or did not answer, `MOST_TRIES` times: asked no more."""
    return _read_file(path)[1]


def answers() -> dict[str, str]:
    """The answers of the configured file, read once a process (again when the file or its
    time changes); empty with no file."""
    path = _configured_path()
    if path is None:
        return {}
    now = time.monotonic()
    with _LOCK:
        if _LOADED.get("path") == str(path) and now - _LOADED.get("checked", -1e18) < _RECHECK_SECONDS:
            return _LOADED["answers"]
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            stamp = None
        if _LOADED.get("path") != str(path) or _LOADED.get("stamp") != stamp:
            _LOADED["answers"], _LOADED["refused"] = _read_file(path) if stamp is not None else ({}, frozenset())
            _LOADED["stamp"] = stamp
            _LOADED["path"] = str(path)
        _LOADED["checked"] = now
        return _LOADED["answers"]


def refused_keys() -> frozenset[str]:
    """The configured file's keys refused for good (`read_refused`), read with `answers`."""
    answers()
    with _LOCK:
        return _LOADED.get("refused") or frozenset()


def category_state(title: str, brand: str, raw: Any) -> str:
    """The checks' rules, 5.5: "line" (the AI gave a line of Google's taxonomy that is no
    slip), "none" ("no line fits", refused for good, or a slip: no category), "unasked"
    (no answer yet, or refused fewer than `MOST_TRIES` times), or "" with no answers file
    at all, which decides nothing."""
    table = answers()
    if not table:
        return ""
    key = key_of(title, brand, raw)
    line = table.get(key)
    if line is None:
        return "none" if key in refused_keys() else "unasked"
    return "line" if line and not is_slip(line) else "none"


def reset() -> None:
    """Forget the answers and the kinds' lists read (tests)."""
    with _LOCK:
        _LOADED.clear()
        _LISTS.clear()


def key_of(title: str, brand: str, raw: Any) -> str:
    """The key a product was asked by (`picwise_ai.shelves.ask_key`), the one a row keeps
    when it has one."""
    get = getattr(raw, "get", None)
    kept = str(get(AI_KEY_COLUMN) or "") if get is not None else ""
    if kept:
        return kept
    from picwise_ai.shelves import ask_key, shop_words

    return ask_key(title, brand, shop_words(raw))


def line_of(title: str, brand: str, raw: Any, table: Mapping[str, str] | None = None) -> str | None:
    """The AI's line for a product (None: no answer; "": no line fits)."""
    table = answers() if table is None else table
    if not table:
        return None
    return table.get(key_of(title, brand, raw))


# The first five lines of Google's tree, which the model gave products of every kind when it
# slipped (the check of 20/11: "Animals & Pet Supplies" on products read as 162 kinds,
# watches, kettles, televisions...): a line among them says nothing of the product, and is
# read as no answer by both rules.
SLIP_LINES = frozenset({
    "animals & pet supplies",
    "animals & pet supplies > live animals",
    "animals & pet supplies > pet supplies",
    "animals & pet supplies > pet supplies > bird supplies",
    "animals & pet supplies > pet supplies > bird supplies > bird cage accessories",
})


def is_slip(line: str | None) -> bool:
    """A line the model gave when it slipped (`SLIP_LINES`)."""
    return " > ".join(" ".join(part.split()).casefold() for part in str(line or "").split(">") if part.strip()) in SLIP_LINES


def second_link_answer(
    title: str, brand: str, raw: Any, table: Mapping[str, str] | None = None
) -> tuple[str, str]:
    """Rule 1: the Google line a second-link row is given, the AI's, with the key it was
    asked by; ("", "") to keep the line guessed from the shop's words."""
    table = answers() if table is None else table
    if not table:
        return "", ""
    key = key_of(title, brand, raw)
    line = table.get(key) or ""
    return (line, key) if line and not is_slip(line) else ("", "")


KIND_LINES_FILE_ENV = "PICWISE_KIND_LINES_FILE"
_LISTS: dict[str, Any] = {}


def _levels(line: str) -> tuple[str, ...]:
    return tuple(" ".join(part.split()).casefold() for part in str(line or "").split(">") if part.strip())


def kind_lists(path: Path | None = None) -> dict[str, tuple[tuple[tuple[str, ...], bool], ...]]:
    """Each kind's lines as kept in the repository, as levels, each kind's own with its
    narrower kinds' (a robot vacuum is a vacuum cleaner), read once a process: the lines the
    AI chose with the lines under them; the lines its check added (`exact`) alone. A kind
    with no line is left out: no rule can be read for it."""
    if path is None:
        configured = str(os.environ.get(KIND_LINES_FILE_ENV) or "").strip()
        from picwise_ai.kind_lines import KIND_LINES_PATH

        path = Path(configured) if configured else KIND_LINES_PATH
    with _LOCK:
        if _LISTS.get("path") == str(path):
            return _LISTS["lists"]
    from picwise_ai.kind_lines import read
    from picwise_nlu.product_concepts import get_product_concepts

    own = read(path)
    exact = read(path, "exact")
    narrower: dict[str, set[str]] = {}
    for concept in get_product_concepts():
        for wide in concept.broader:
            narrower.setdefault(wide, set()).add(concept.concept_id)

    def under(kind: str, seen: frozenset[str] = frozenset()) -> set[str]:
        found = {kind}
        for narrow in narrower.get(kind, ()):
            if narrow not in seen:
                found |= under(narrow, seen | {kind})
        return found

    lists: dict[str, tuple[tuple[tuple[str, ...], bool], ...]] = {}
    for kind in set(own) | set(exact):
        parts = under(kind)
        entries = {(_levels(line), False) for part in parts for line in own.get(part, ())}
        entries |= {(_levels(line), True) for part in parts for line in exact.get(part, ())}
        entries = {entry for entry in entries if entry[0]}
        if entries:
            lists[kind] = tuple(sorted(entries))
    with _LOCK:
        _LISTS["path"] = str(path)
        _LISTS["lists"] = lists
    return lists


def on_list(line: str, allowed: tuple[tuple[tuple[str, ...], bool], ...]) -> bool:
    """A line is on a list when it is one of its lines or under one the AI chose (a line
    its check added holds no line under it)."""
    levels = _levels(line)
    return any(levels == part if alone else levels[: len(part)] == part for part, alone in allowed)


def checked_kinds(
    kinds: frozenset[str],
    *,
    title: str,
    brand: str,
    raw: Any,
    table: Mapping[str, str] | None = None,
    lists: Mapping[str, tuple[tuple[tuple[str, ...], bool], ...]] | None = None,
) -> frozenset[str]:
    """Rule 2: the kinds a product is read as, each kept only when the AI's line for the
    product is on the kind's list; none kept, the product doubtful."""
    table = answers() if table is None else table
    if not table or not kinds:
        return kinds
    real = {kind for kind in kinds if not kind.startswith("__")}
    if not real:
        return kinds
    line = line_of(title, brand, raw, table)
    if not line or is_slip(line):
        return kinds
    lists = kind_lists() if lists is None else lists
    left = {kind for kind in real if kind in lists and not on_list(line, lists[kind])}
    if not left:
        return kinds
    if left == real:
        from picwise_nlu.concept_understanding import UNCERTAIN_MARKER

        return frozenset({UNCERTAIN_MARKER})
    return frozenset(kinds - left)
