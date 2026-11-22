"""The service `picwise-meter`: each day, the first cards of fixed searches judged by a model
that has no part in what it measures (`docs/PICWISE_KIND_ITSELF_RULES.md`, section 9; the
owner's plan of 21/11, step 9: «μετρητής ποιότητας», the same 40 searches each day; step 12:
a daily email with the quality).

Run by `picwise-meter.service` each morning after the night's preparation and the AI's
askings, under the AI layer's own user and key. It asks the site on the server itself for
each search's page, as a page is asked (`/search?q=…&shown=12`: no script runs, so no
visitor's search is logged and nothing is sent to the AI by the site), reads the cards a
visitor would see (title, shop, price; never a link or an id), and has Claude Opus 5.5 say
for each whether it is what the buyer asked for (`picwise_ai.meter`).

- **Every day**: the first 12 cards of the measure after's 40 searches, the same every day,
  so that one day can be read against another.
- **A seventh of the kinds a day**: the first 12 cards of each kind's first name; every kind
  within a week.
- **A card is judged once**: its verdict is kept by the search's words and the card's title,
  shop and price; a day pays only for the cards it has not seen. Stopped before $2 a day; what
  it did not judge is counted as not judged, and waits for the next day.

It keeps the verdicts (`verdicts.jsonl.gz`), the day's note (`day.json`: the cards right of
those judged, beside the day before; the wrong cards by title and shop; the cost) and one
line a day (`days.jsonl`). The morning's health run reads the note and tells a fall of more
than 3 points as a limit. Its verdicts decide nothing: nothing shown changes by them.

    meter_service.py --dir /srv/picwise/assist/meter [--site http://127.0.0.1:8016] [--budget 2]
"""
from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

VERDICTS_NAME = "verdicts.jsonl.gz"
NOTE_NAME = "day.json"
DAYS_NAME = "days.jsonl"
SITE = "http://127.0.0.1:8016"
BUDGET_USD = 2.0
WORKERS = 4
# Seconds between two pages asked of the site.
PAUSE = 0.3
# A verdict whose card no page has shown for so many days is dropped.
KEPT_DAYS = 35
# The wrong cards the note names, at most.
WRONG_LISTED = 60
# The days of `days.jsonl` kept.
DAYS_KEPT = 120
# A fall of more than so many points from the day before is told as a limit.
FALL_POINTS = 3.0
# A call's cost guessed before any has come back: high, so that the budget stops early.
FIRST_GUESS_USD = 0.05
# With the prompt's fingerprint: a verdict kept under other instructions is not counted.
VERSION = 1

_ARTICLE = re.compile(r'<article class="pw-card[^"]*" data-choice-id="[^"]*">(.*?)</article>', re.DOTALL)


def _text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _first(pattern: str, block: str) -> str:
    match = re.search(pattern, block, re.DOTALL)
    return html.unescape(match.group(1)) if match else ""


def read_cards(page: str, limit: int) -> list[dict[str, str]]:
    """The first cards of a search's page, as a visitor sees them: title, shop and price."""
    cards = []
    for block in _ARTICLE.findall(page)[:limit]:
        card = {
            "title": _text(_first(r'<h2 title="([^"]*)" class="pw-card-title"', block)),
            "shop": _text(_first(r'<p class="pw-card-shop">(.*?)</p>', block)),
            "price": _text(_first(r'<p class="pw-price">(.*?)</p>', block)),
        }
        if card["title"]:
            cards.append(card)
    return cards


def version() -> str:
    from picwise_ai import meter

    return f"{VERSION}.{meter.prompt_fingerprint()}"


def kinds_of_the_day(day: date) -> list[tuple[str, str]]:
    """The day's seventh of the kinds, each with its first name: every kind within a week."""
    from picwise_nlu.product_concepts import get_product_concepts

    named = sorted((concept.concept_id, concept.english[0]) for concept in get_product_concepts() if concept.english)
    return [(kind, name) for place, (kind, name) in enumerate(named) if place % 7 == day.toordinal() % 7]


def read_verdicts(path: Path) -> dict[str, dict[str, Any]]:
    """The verdicts kept, by card key; none when the file is not there or cannot be read."""
    found: dict[str, dict[str, Any]] = {}
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for text in handle:
                try:
                    entry = json.loads(text)
                except ValueError:
                    continue
                if isinstance(entry, dict) and isinstance(entry.get("c"), str) and entry.get("is") in ("yes", "no", "unsure"):
                    found[entry["c"]] = entry
    except (OSError, EOFError, UnicodeDecodeError, gzip.BadGzipFile):
        return {}
    return found


def write_verdicts(path: Path, verdicts: dict[str, dict[str, Any]], day: date) -> None:
    """The verdicts whose card a page showed in the last `KEPT_DAYS`, written whole and then
    put in place."""
    oldest = (day - timedelta(days=KEPT_DAYS)).isoformat()
    temporary = path.with_name(path.name + ".part")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        for key in sorted(verdicts):
            if str(verdicts[key].get("seen") or "") >= oldest:
                handle.write(json.dumps(verdicts[key], ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def read_days(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    days = []
    for text in lines:
        try:
            entry = json.loads(text)
        except ValueError:
            continue
        if isinstance(entry, dict) and isinstance(entry.get("day"), str):
            days.append(entry)
    return days


def write_json(path: Path, document: Any) -> None:
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def counted(sets: list[tuple[str, list[dict[str, str]] | None]], verdicts: dict[str, dict[str, Any]], kept: str) -> dict[str, Any]:
    """One part's count: the cards right of those judged (`yes` of `yes` and `no`)."""
    from picwise_ai import meter

    count = {"searches": len(sets), "pages_failed": 0, "with_no_card": 0, "cards": 0, "yes": 0, "no": 0, "unsure": 0,
             "not_judged": 0}
    for search, cards in sets:
        if cards is None:
            count["pages_failed"] += 1
            continue
        if not cards:
            count["with_no_card"] += 1
        for card in cards:
            count["cards"] += 1
            verdict = verdicts.get(meter.card_key(search, card))
            count[verdict["is"] if verdict is not None and verdict.get("v") == kept else "not_judged"] += 1
    judged = count["yes"] + count["no"]
    count["share"] = round(count["yes"] / judged, 4) if judged else None
    return count


def run(
    directory: Path,
    *,
    get: Callable[[str], str],
    ask_fn: Callable[[dict[str, Any]], Any] | None,
    day: date | None = None,
    site: str = SITE,
    budget: float = BUDGET_USD,
    workers: int = WORKERS,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """One day's measure; its note (also written as `NOTE_NAME`). With no `ask_fn` nothing
    is judged: the pages are read and the cards counted against the verdicts kept."""
    from measure_after import SEARCHES
    from picwise_ai import meter
    from picwise_ai.client import Budget

    day = day or datetime.now(timezone.utc).date()
    today = day.isoformat()
    kept = version()
    verdicts_path = directory / VERDICTS_NAME
    verdicts = read_verdicts(verdicts_path)
    kinds = kinds_of_the_day(day)
    pages: dict[str, list[dict[str, str]] | None] = {}
    for search in [*SEARCHES, *(name for _kind, name in kinds)]:
        if search in pages:
            continue
        try:
            pages[search] = read_cards(get(f"{site}/search?q={quote(search)}&shown={meter.CARDS}"), meter.CARDS)
        except Exception:  # a page that did not answer is counted, never guessed
            pages[search] = None
        sleep(PAUSE)
    # A card seen today keeps its verdict; one not judged yet, or judged under other
    # instructions, is asked.
    to_ask: list[tuple[str, list[dict[str, str]]]] = []
    for search, cards in pages.items():
        fresh = []
        for card in cards or ():
            verdict = verdicts.get(meter.card_key(search, card))
            if verdict is not None and verdict.get("v") == kept:
                verdict["seen"] = today
            else:
                fresh.append(card)
        if fresh:
            to_ask.append((search, fresh))
    spend = Budget(budget)
    lock = threading.Lock()
    state = {"calls": 0, "failed": 0, "cost": 0.0, "stopped": "", "judged": 0}

    def one(call: tuple[str, list[dict[str, str]]]) -> None:
        search, cards = call
        with lock:
            if state["stopped"]:
                return
            guess = 1.5 * state["cost"] / state["calls"] if state["calls"] else FIRST_GUESS_USD
        if not spend.reserve(guess):
            with lock:
                state["stopped"] = state["stopped"] or f"its limit of ${budget:.2f}"
            return
        answer, cost = None, 0.0
        try:
            answer = ask_fn(meter.request_kwargs(search, cards))
            cost = float(getattr(answer, "cost_usd", 0.0) or 0.0)
        except Exception:  # a call that failed is a call with no verdict
            answer = None
        finally:
            spend.settle(guess, cost)
        found = meter.checked_verdicts(getattr(answer, "answer", None), len(cards))
        with lock:
            state["calls"] += 1
            state["cost"] += cost
            state["failed"] += not found
            for number, card in enumerate(cards, 1):
                if number in found:
                    state["judged"] += 1
                    verdicts[meter.card_key(search, card)] = {
                        "c": meter.card_key(search, card), "is": found[number][0], "why": found[number][1], "v": kept,
                        "at": today, "seen": today, "q": search, **card,
                    }

    if ask_fn is not None and to_ask:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            list(pool.map(one, to_ask))
    searches = counted([(search, pages[search]) for search in SEARCHES], verdicts, kept)
    kinds_part = counted([(name, pages[name]) for _kind, name in kinds], verdicts, kept)
    wrong = []
    for part, names in (("search", list(SEARCHES)), ("kind", [name for _kind, name in kinds if name not in SEARCHES])):
        for search in names:
            for card in pages.get(search) or ():
                verdict = verdicts.get(meter.card_key(search, card))
                if verdict is not None and verdict.get("v") == kept and verdict["is"] == "no":
                    wrong.append({"part": part, "q": search, **card, "why": str(verdict.get("why") or "")})
    days = [entry for entry in read_days(directory / DAYS_NAME) if entry["day"] != today]
    before = max((entry for entry in days if entry["day"] < today and entry.get("share") is not None),
                 key=lambda entry: entry["day"], default=None)
    week = [entry for entry in days if (day - timedelta(days=6)).isoformat() <= entry["day"] < today]
    week_yes = kinds_part["yes"] + sum(int(entry.get("kinds_yes") or 0) for entry in week)
    week_no = kinds_part["no"] + sum(int(entry.get("kinds_no") or 0) for entry in week)
    fell = None
    if before is not None and searches["share"] is not None:
        fell = round(100 * (float(before["share"]) - searches["share"]), 1)
    note = {
        "day": today,
        "version": kept,
        "searches": searches,
        "kinds": {**kinds_part, "of_the_day": len(kinds)},
        "kinds_week": {"days": len(week) + 1, "yes": week_yes, "no": week_no,
                       "share": round(week_yes / (week_yes + week_no), 4) if week_yes + week_no else None},
        "before": {"day": before["day"], "share": before["share"]} if before is not None else None,
        "fell_points": fell,
        "fell": bool(fell is not None and fell > FALL_POINTS),
        "wrong": wrong[:WRONG_LISTED],
        "wrong_in_all": len(wrong),
        "judged_today": state["judged"],
        "calls": state["calls"],
        "failed_calls": state["failed"],
        "cost_usd": round(state["cost"], 4),
        "stopped": state["stopped"],
        "asked": ask_fn is not None,
    }
    write_verdicts(verdicts_path, verdicts, day)
    write_json(directory / NOTE_NAME, note)
    days.append({"day": today, "share": searches["share"], "yes": searches["yes"], "no": searches["no"],
                 "unsure": searches["unsure"], "not_judged": searches["not_judged"], "kinds_yes": kinds_part["yes"],
                 "kinds_no": kinds_part["no"], "cost_usd": note["cost_usd"]})
    days.sort(key=lambda entry: entry["day"])
    (directory / (DAYS_NAME + ".part")).write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in days[-DAYS_KEPT:]), encoding="utf-8")
    os.replace(directory / (DAYS_NAME + ".part"), directory / DAYS_NAME)
    for line in report(note):
        print(line)
    return note


def _share(share: float | None) -> str:
    return f"{100 * share:.1f}%" if share is not None else "none judged"


def report(note: dict[str, Any]) -> list[str]:
    """The day's measure in lines: counts, the wrong cards by title and shop, the cost."""
    searches, kinds, week = note["searches"], note["kinds"], note["kinds_week"]
    before = note.get("before")
    lines = [
        f"quality on {note['day']}, the 40 searches: {searches['yes']:,} of {searches['yes'] + searches['no']:,} cards right"
        f" ({_share(searches['share'])}); {searches['unsure']:,} cannot be told, {searches['not_judged']:,} not judged,"
        f" {searches['pages_failed']} pages failed"
        + (f"; the day before ({before['day']}) {_share(before['share'])}" if before else "; no day before"),
        f"quality, the day's {kinds['of_the_day']} kinds: {kinds['yes']:,} of {kinds['yes'] + kinds['no']:,} cards right"
        f" ({_share(kinds['share'])}); the last {week['days']} days' kinds {week['yes']:,} of {week['yes'] + week['no']:,}"
        f" ({_share(week['share'])})",
        f"quality: {note['judged_today']:,} cards judged today in {note['calls']} calls ({note['failed_calls']} failed);"
        f" ${note['cost_usd']:.4f}" + (f"; stopped at {note['stopped']}" if note["stopped"] else "")
        + ("" if note["asked"] else "; the AI not asked"),
    ]
    for card in note["wrong"]:
        lines.append(f"quality, wrong for \"{card['q']}\": {card['title'][:90]} ({card['shop']}, {card['price']}): {card['why']}")
    if note["wrong_in_all"] > len(note["wrong"]):
        lines.append(f"quality: {note['wrong_in_all'] - len(note['wrong']):,} more wrong cards not listed")
    return lines


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "PicWise meter, reading its own pages"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=60) as answer:
        return answer.read().decode("utf-8", "replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Judge the first cards of fixed searches, once a day.")
    parser.add_argument("--dir", type=Path, required=True, help="where the verdicts and the day's note are kept")
    parser.add_argument("--site", default=SITE, help="the site, asked on the server itself")
    parser.add_argument("--budget", type=float, default=BUDGET_USD)
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("no key in the environment: nothing is judged")
        return 0

    from picwise_ai.client import ask, make_client

    client = make_client(timeout=120.0, max_retries=3)
    run(args.dir, get=_get, ask_fn=lambda request: ask(request, client=client), site=args.site.rstrip("/"),
        budget=args.budget, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
