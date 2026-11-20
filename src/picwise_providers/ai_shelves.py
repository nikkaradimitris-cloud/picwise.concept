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
2. Every product, of either link: the kinds its type, shelf and title give are read against
   the kinds the AI's line gives with the same title (`checked_kinds`). The AI's line
   giving none of them -- an accessory (a strap the shop filed under "Watches"), or another
   kind -- makes the product doubtful (`UNCERTAIN_MARKER`): it is found by its words, never
   by its kind ("watches" shows watches; "garmin strap" still finds the strap). A line that
   names no kind PicWise knows doubts a kind only from another department than the row's
   own line. No line from the AI (not asked yet, refused, "no line fits") changes nothing.
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


def read_answers(path: Path) -> dict[str, str]:
    """The AI's lines by key, from the scan's answers file: only the lines given ("" for
    "no line fits", refusals and lines that are not answers left out). Empty when the
    file cannot be read: the catalogue is then prepared as without it."""
    found: dict[str, str] = {}
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
    except (OSError, EOFError, gzip.BadGzipFile):
        return {}
    return found


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
            _LOADED["answers"] = read_answers(path) if stamp is not None else {}
            _LOADED["stamp"] = stamp
            _LOADED["path"] = str(path)
        _LOADED["checked"] = now
        return _LOADED["answers"]


def reset() -> None:
    """Forget the answers read (tests)."""
    with _LOCK:
        _LOADED.clear()


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
    return (line, key) if line else ("", "")


# Google's taxonomy in British English names one department otherwise: a shop of the first
# link writes "Clothing & Accessories > Shoes" where the AI, given the American list, writes
# "Apparel & Accessories > Shoes" (the scan of 20/11: most of its "another department").
_SAME_DEPARTMENT = {"clothing & accessories": "apparel & accessories"}


def _department(line: str) -> str:
    name = " ".join(str(line or "").split(">")[0].split()).casefold()
    return _SAME_DEPARTMENT.get(name, name)


def checked_kinds(
    kinds: frozenset[str],
    *,
    title: str,
    brand: str,
    raw: Any,
    table: Mapping[str, str] | None = None,
) -> frozenset[str]:
    """Rule 2: the kinds a product is read as, kept when the AI's line agrees, else the
    product doubtful."""
    table = answers() if table is None else table
    if not table or not kinds:
        return kinds
    real = {kind for kind in kinds if not kind.startswith("__")}
    if not real:
        return kinds
    line = line_of(title, brand, raw, table)
    if not line:
        return kinds
    from picwise_nlu.concept_understanding import ACCESSORY_MARKER, UNCERTAIN_MARKER, annotate_product_concepts

    by_ai = annotate_product_concepts("", line, str(title or ""))
    by_ai_real = {kind for kind in by_ai if not kind.startswith("__")}
    if real & by_ai_real:
        return kinds
    if ACCESSORY_MARKER in by_ai or by_ai_real:
        return frozenset({UNCERTAIN_MARKER})
    get = getattr(raw, "get", None)
    own_line = str(get("google_product_category") or "") if get is not None else ""
    if own_line and _department(own_line) != _department(line):
        return frozenset({UNCERTAIN_MARKER})
    return kinds
