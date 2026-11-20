"""Every product of the catalogue given its line of Google's taxonomy by the AI, once.

Owner, 2026-11-20: «Αυτό που πρέπει να κάνουμε είναι να φτιάξουμε μηχανισμούς και κανόνες
σχετικά με το ai που μπορεί να κάνει την ταξινόμηση», then «Θέλω να σκαναριστεί σήμερα όλος
ο κατάλογος... Μετά συντήρηση τα όρια ανα ημέρα θα καθοριστούν μετά». The trial of 1,000
(`measure_shelves.py`, run 44708919103) came first.

Claude Haiku 5.5 reads each product's title, brand, price, the shop's own category words
(`shelves.shop_words`: never the Google line a row carries) and the start of its
description, and answers one line of Google's taxonomy (`picwise_ai.shelves`); the code
checks every answer (`shelves.checked_lines`). The products of one key (`shelves.ask_key`:
a title's own words, the brand and the shop's words) are asked once: a product's sizes and
colours share one answer. The largest keys first, 50 a call, several calls at a time; a
call the API turns away for its rate or its load is asked again later, with fewer at a
time. A product refused or not answered is asked once more in a second round, 25 a call.

The answers kept so far (`--answers`) are read first and never asked again; the answers,
old and new, are written to `--out` (gzip, one JSON a line: {"k": key, "line": "A > B > C",
"" when no line fits, or null when refused twice; "tries"; "at"}), every ten minutes and at
the end. Nothing else is written: the answers name no product, only keys and lines. No rule
of the search reads them yet.

It stops asking before a call would pass `--budget` dollars, after `--stop-after` seconds,
or when the API says the account cannot pay or the key is refused; what it did not ask is
asked by the next run. Printed: counts, the cost, the time, how the AI's lines compare with
the shops' own Google lines (the first link) and with the shelves PicWise guessed (the
second link), and where some words' products went. Titles, brands, shops and categories
are printed, never a link, a description or the key.

    python3 deployment/server/scan_shelves.py CATALOGUE.json.gz --out ANSWERS.jsonl.gz \
        [--answers KEPT.jsonl.gz] [--workers 8] [--budget 40] [--stop-after 18900] \
        [--per-call 50] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import statistics
import sys
import threading
import time
from collections import Counter, deque
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# The second link's own columns: a row carrying one is the second link's.
SECOND_KEYS = ("merchant_id", "aw_product_id")
DESCRIPTION_KEYS = ("description", "product_short_description", "short_description")
# A product refused or not answered is asked this many times in all, then kept as null.
MOST_TRIES = 2
# A call the API turns away for its rate or its load is asked again, at most so often.
MOST_REQUEUES = 6
# After a call turned away for the rate or the load: no new call for so many seconds, and
# one call fewer at a time; one more again after so long without.
PAUSE_SECONDS = 20.0
GROW_AFTER_SECONDS = 180.0
# So many failures in a row of another kind stop the run: something is wrong with every call.
MOST_FAILURES_IN_A_ROW = 12
CHECKPOINT_SECONDS = 600.0
PROGRESS_SECONDS = 120.0
# A note GitHub keeps after the first calls (the pace and the cost), then every so often.
SPEED_CALLS = 24
NOTICE_SECONDS = 2700.0
# The words whose products' lines are printed: the look-alikes the owner saw (20/11).
WORDS = ("boots", "strap", "watch", "kettle", "tyres", "router", "monitor", "cable", "case", "charger")
LISTED = 30
TITLE = 70
_RETRY_ERRORS = ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504", "HTTP 529", "Timeout", "Connection")
_STOP_ERRORS = ("HTTP 401", "HTTP 403")
_NO_CREDIT_RE = re.compile(r"credit balance|billing|purchase credits", re.IGNORECASE)


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _short(text: Any, width: int = TITLE) -> str:
    text = _text(text)
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


class Notices:
    """Lines GitHub keeps as the run's annotations, which its API shows without a login, so
    the scan can be followed while it runs: at most `most` (GitHub keeps ten a step), the
    last `keep` saved for the end. Printed as plain lines too; nothing outside GitHub."""

    def __init__(self, enabled: bool | None = None, most: int = 10, keep: int = 3) -> None:
        self.enabled = os.environ.get("GITHUB_ACTIONS") == "true" if enabled is None else enabled
        self.most = most
        self.keep = keep
        self.used = 0

    def say(self, title: str, text: str, *, final: bool = False) -> None:
        print(f"[{title}] {text}")
        if not self.enabled or self.used >= self.most or (not final and self.used >= self.most - self.keep):
            return
        self.used += 1
        body = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        name = title.replace("%", "%25").replace("\r", " ").replace("\n", " ").replace(":", " ").replace(",", " ")
        print(f"::notice title={name}::{body}")


@dataclass
class Group:
    """The products of one key: what the AI is shown (the first product's), how many they
    are, and what they are read against."""

    key: str
    item: dict[str, Any]
    shop: str
    title: str
    second: bool
    shelf_now: str
    products: int = 0


def groups_of(products: Iterable[Any], lines: Sequence[str]) -> dict[str, Group]:
    """The catalogue's products by key, each key's first product shown to the AI."""
    from picwise_ai.shelves import levels, line_index, shop_words
    from picwise_providers.ai_shelves import key_of
    from picwise_providers.catalogue_cap import shop_of

    index = line_index(lines)
    groups: dict[str, Group] = {}
    for product in products:
        raw = product.raw if hasattr(product.raw, "get") else {}
        words = shop_words(raw)
        # A row given the AI's line keeps the key it was asked by (`ai_shelves`, rule 1).
        key = key_of(product.title, product.brand, raw)
        group = groups.get(key)
        if group is None:
            second = any(_text(raw.get(column)) for column in SECOND_KEYS)
            google = _text(raw.get("google_product_category")) or ("" if not second else _text(product.category_text))
            shelf_now = index.get(" > ".join(levels(google)), google) if google else ""
            description = ""
            for column in DESCRIPTION_KEYS:
                description = _text(raw.get(column))
                if description:
                    break
            group = groups[key] = Group(
                key=key,
                item={
                    "title": product.title,
                    "brand": product.brand,
                    "price": product.price_text,
                    "category": words,
                    "about": description,
                },
                shop=shop_of(product),
                title=_text(product.title),
                second=second,
                shelf_now=shelf_now,
            )
        group.products += 1
    return groups


def read_answers(path: Path | None) -> dict[str, dict[str, Any]]:
    """The answers kept so far, by key; nothing when there is no file. A line that is not
    an answer is passed over."""
    answers: dict[str, dict[str, Any]] = {}
    if path is None or not path.is_file() or path.stat().st_size == 0:
        return answers
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and isinstance(record.get("k"), str) and "line" in record:
                if record["line"] is None or isinstance(record["line"], str):
                    answers[record["k"]] = record
    return answers


def write_answers(path: Path, answers: dict[str, dict[str, Any]]) -> None:
    """All the answers, written whole to a file beside `path` and then put in its place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        for key in sorted(answers):
            handle.write(json.dumps(answers[key], ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def to_ask(groups: dict[str, Group], answers: dict[str, dict[str, Any]]) -> list[str]:
    """The keys still to ask, the most products first: those with no answer, and those
    refused fewer than `MOST_TRIES` times."""
    keys = [
        key
        for key in groups
        if key not in answers or (answers[key].get("line") is None and int(answers[key].get("tries") or 0) < MOST_TRIES)
    ]
    keys.sort(key=lambda key: (-groups[key].products, key))
    return keys


@dataclass
class Call:
    keys: list[str]
    requeues: int = 0


@dataclass
class Totals:
    calls: int = 0
    failed: int = 0
    turned_away: int = 0
    cost: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cache_written: int = 0
    cache_read: int = 0
    answered: int = 0
    no_line: int = 0
    refused: int = 0
    errors: Counter = field(default_factory=Counter)
    seconds: list[float] = field(default_factory=list)
    stopped: str = ""


@dataclass
class Asking:
    """What a run needs: the call to make, the groups, the answers it writes into, and its
    limits."""

    ask_fn: Callable[[dict[str, Any]], tuple[Any, str]]
    groups: dict[str, Group]
    answers: dict[str, dict[str, Any]]
    lines: Sequence[str]
    workers: int
    budget: float
    deadline: float
    out: Path | None = None
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    today: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    totals: Totals = field(default_factory=Totals)
    tries: Counter = field(default_factory=Counter)
    notices: Notices = field(default_factory=lambda: Notices(enabled=False))
    # The request of one call, when not the scan's own (`reask_shelves.py`: more care).
    request_fn: Callable[..., dict[str, Any]] | None = None


def _record(asking: Asking, key: str, line: str | None) -> None:
    asking.answers[key] = {"k": key, "line": line, "tries": asking.tries[key], "at": asking.today}


def _estimate(totals: Totals) -> float:
    """The next call's cost, guessed high: half again the mean so far, two cents before any."""
    return 1.5 * totals.cost / totals.calls if totals.calls else 0.02


def run_round(asking: Asking, keys: Sequence[str], per_call: int, *, label: str) -> list[str]:
    """Ask `keys` in calls of `per_call`, several at a time; the keys refused or not answered
    (each try counted), in order. Keys left unasked by a limit stay unasked."""
    from picwise_ai.shelves import checked_lines, request_kwargs

    totals = asking.totals
    queue: deque[Call] = deque(Call(list(keys[i : i + per_call])) for i in range(0, len(keys), per_call))
    calls_in_round = len(queue)
    failed_keys: list[str] = []
    allowed = max(1, asking.workers)
    pause_until = 0.0
    last_turned_away = asking.clock()
    last_progress = asking.clock()
    last_checkpoint = asking.clock()
    failures_in_a_row = 0
    done_calls = 0
    began = asking.clock()
    last_notice = asking.clock()
    speed_told = False

    def do_call(call: Call) -> tuple[Any, str]:
        build = asking.request_fn or request_kwargs
        request = build([asking.groups[key].item for key in call.keys], asking.lines)
        return asking.ask_fn(request)

    def budget_allows(in_flight: int) -> bool:
        return totals.cost + (in_flight + 1) * _estimate(totals) <= asking.budget

    with ThreadPoolExecutor(max_workers=max(1, asking.workers)) as pool:
        in_flight: dict[Any, Call] = {}
        while queue or in_flight:
            now = asking.clock()
            if not totals.stopped:
                if now >= asking.deadline:
                    totals.stopped = "the time given ran out"
                elif not budget_allows(0):
                    totals.stopped = f"the budget of ${asking.budget:.2f} would be passed"
            while (
                not totals.stopped
                and queue
                and len(in_flight) < allowed
                and now >= pause_until
                and budget_allows(len(in_flight))
            ):
                call = queue.popleft()
                in_flight[pool.submit(do_call, call)] = call
            if not in_flight:
                if totals.stopped or not queue:
                    break
                asking.sleep(max(0.2, min(5.0, pause_until - now)))
                continue
            finished, _ = wait(in_flight, timeout=5.0, return_when=FIRST_COMPLETED)
            for future in finished:
                call = in_flight.pop(future)
                try:
                    asked, message = future.result()
                except Exception as error:  # the call itself broke: its keys are tried again
                    asked, message = None, f"{type(error).__name__}"
                now = asking.clock()
                error = getattr(asked, "error", "") if asked is not None else message
                if asked is not None:
                    totals.calls += 1
                    totals.cost += asked.cost_usd
                    totals.tokens_in += asked.input_tokens
                    totals.tokens_out += asked.output_tokens
                    totals.cache_written += asked.cache_write_tokens
                    totals.cache_read += asked.cache_read_tokens
                    totals.seconds.append(asked.seconds)
                if error and _NO_CREDIT_RE.search(message or ""):
                    totals.errors[error] += 1
                    totals.stopped = "the account has no credit left: " + _short(message, 160)
                    queue.appendleft(call)
                    continue
                if error and any(mark in error for mark in _STOP_ERRORS):
                    totals.errors[error] += 1
                    totals.stopped = "the API refused the key: " + error
                    queue.appendleft(call)
                    continue
                if error and any(mark in error for mark in _RETRY_ERRORS) and call.requeues < MOST_REQUEUES:
                    # Turned away for the rate or the load: asked again later, fewer at a time.
                    totals.turned_away += 1
                    totals.errors[error] += 1
                    call.requeues += 1
                    queue.append(call)
                    allowed = max(1, allowed - 1)
                    pause_until = now + PAUSE_SECONDS
                    last_turned_away = now
                    continue
                found = checked_lines(getattr(asked, "answer", None), len(call.keys), asking.lines)
                if error or getattr(asked, "answer", None) is None:
                    totals.failed += 1
                    totals.errors[error or getattr(asked, "stop_reason", "") or "no answer"] += 1
                    failures_in_a_row += 1
                    if failures_in_a_row >= MOST_FAILURES_IN_A_ROW:
                        totals.stopped = f"{failures_in_a_row} calls in a row failed (the last: {error or 'no answer'})"
                else:
                    failures_in_a_row = 0
                done_calls += 1
                for number, key in enumerate(call.keys, 1):
                    asking.tries[key] += 1
                    line = found.get(number)
                    if line is None:
                        failed_keys.append(key)
                        totals.refused += 1
                        continue
                    _record(asking, key, line)
                    totals.answered += 1
                    if not line:
                        totals.no_line += 1
            if allowed < asking.workers and now - last_turned_away >= GROW_AFTER_SECONDS:
                allowed += 1
                last_turned_away = now
            told = (not speed_told and done_calls >= SPEED_CALLS) or now - last_notice >= NOTICE_SECONDS
            if now - last_progress >= PROGRESS_SECONDS or told:
                last_progress = now
                minutes = max((now - began) / 60.0, 1e-9)
                line = (
                    f"{label}: {done_calls:,} of {calls_in_round:,} calls; {totals.answered:,} keys answered in all, "
                    f"{totals.refused:,} refused; ${totals.cost:.2f}; {done_calls / minutes:.1f} calls a minute, "
                    f"{allowed} at a time; turned away {totals.turned_away:,}"
                )
                if told:
                    speed_told = True
                    last_notice = now
                    left = calls_in_round - done_calls
                    rate = done_calls / minutes
                    each = totals.cost / totals.calls if totals.calls else 0.0
                    line += (
                        f"; about {left / rate:.0f} more minutes and ${left * each:.2f} more at this pace"
                        if rate > 0 else ""
                    )
                    asking.notices.say("progress", line)
                else:
                    print(line)
            if asking.out is not None and now - last_checkpoint >= CHECKPOINT_SECONDS:
                last_checkpoint = now
                write_answers(asking.out, asking.answers)
    return failed_keys


def scan(asking: Asking, keys: Sequence[str], per_call: int) -> list[str]:
    """Two rounds: every key, then those refused or not answered once more, in calls half
    as large. A key refused is kept as null with its tries, and asked again by a later run
    only while it has fewer than `MOST_TRIES`. The keys returned are those left unasked by
    a limit."""
    for key in keys:
        record = asking.answers.get(key)
        if record is not None and record.get("line") is None:
            asking.tries[key] = int(record.get("tries") or 0)
    failed = run_round(asking, keys, per_call, label="round 1")
    again = [key for key in dict.fromkeys(failed) if asking.tries[key] < MOST_TRIES]
    failed_again: list[str] = []
    if again and not asking.totals.stopped:
        failed_again = run_round(asking, again, max(1, per_call // 2), label="round 2")
    for key in dict.fromkeys(failed + failed_again):
        record = asking.answers.get(key)
        if record is None or record.get("line") is None:
            _record(asking, key, None)
    return [key for key in keys if key not in asking.answers]


def _share(part: int, whole: int) -> str:
    return f"{part:,} of {whole:,} ({100 * part / whole:.1f}%)" if whole else f"{part:,} of 0"


def report(groups: dict[str, Group], answers: dict[str, dict[str, Any]]) -> list[str]:
    """How the AI's lines compare with the lines the products have now, by products."""
    from picwise_ai.shelves import levels

    out: list[str] = []
    for second, title in (
        (False, "the first link: the AI's line against the shop's own Google line"),
        (True, "the second link: the AI's line against the shelf PicWise guessed from the shop's words"),
    ):
        tally: Counter[str] = Counter()
        disagreements: list[tuple[int, Group, str]] = []
        for key, group in groups.items():
            if group.second != second:
                continue
            tally["products"] += group.products
            record = answers.get(key)
            if record is None:
                tally["not asked"] += group.products
                continue
            line = record.get("line")
            if line is None:
                tally["refused"] += group.products
                continue
            if not line:
                tally["no line fits"] += group.products
                continue
            tally["a line"] += group.products
            now, ai = levels(group.shelf_now), levels(line)
            if not now:
                tally["no shelf now"] += group.products
                continue
            tally["compared"] += group.products
            if now[0] != ai[0]:
                tally["another department"] += group.products
                disagreements.append((group.products, group, line))
            elif now[:2] == ai[:2]:
                tally["same category"] += group.products
            if now == ai:
                tally["same line"] += group.products
        out.append(f"== {title}")
        out.append(
            f"  products {tally['products']:,}: a line {tally['a line']:,}, no line fits {tally['no line fits']:,}, "
            f"refused {tally['refused']:,}, not asked yet {tally['not asked']:,}"
        )
        compared = tally["compared"]
        out.append(f"  compared {compared:,} (with a shelf now): the same category (two levels) {_share(tally['same category'], compared)}")
        out.append(f"    the same line {_share(tally['same line'], compared)}; another department {_share(tally['another department'], compared)}")
        disagreements.sort(key=lambda found: -found[0])
        out.append(f"  another department, the most products first, {min(LISTED, len(disagreements))} of {len(disagreements):,} keys:")
        for count, group, line in disagreements[:LISTED]:
            out.append(f"    {count:>5} | {_short(group.shop, 22)} | {_short(group.title)}")
            out.append(f"          now: {group.shelf_now}")
            out.append(f"          the AI: {line}")
    return out


def report_words(groups: dict[str, Group], answers: dict[str, dict[str, Any]], words: Sequence[str] = WORDS) -> list[str]:
    """For each word, its products (a title naming it) by the AI's category (two levels)."""
    from picwise_ai.shelves import levels

    out = ["== where the products of some words went (a title naming the word; the AI's category, two levels)"]
    for word in words:
        stem = word[:-1] if word.endswith("s") and not word.endswith("ss") else word
        pattern = re.compile(rf"(?<![\w-]){re.escape(stem)}(?:s|es)?(?![\w-])", re.IGNORECASE)
        tally: Counter[str] = Counter()
        for key, group in groups.items():
            if not pattern.search(group.title):
                continue
            record = answers.get(key)
            line = None if record is None else record.get("line")
            name = "(not asked yet)" if record is None else "(refused)" if line is None else "(no line fits)" if not line else " > ".join(
                part.title() for part in levels(line)[:2]
            )
            tally[name] += group.products
        total = sum(tally.values())
        top = "; ".join(f"{name} {count:,}" for name, count in tally.most_common(5))
        out.append(f"  {word}: {total:,} products: {top}")
    return out


def report_totals(asking: Asking, began: float, unasked: int) -> list[str]:
    totals = asking.totals
    out = [
        f"== {totals.calls:,} calls; keys answered {totals.answered:,} (no line fits {totals.no_line:,}), "
        f"refused or not answered {totals.refused:,} (each try); calls turned away and asked again {totals.turned_away:,}; "
        f"calls failed {totals.failed:,}",
        f"  cost ${totals.cost:.4f}: tokens read {totals.tokens_in:,}, written to the cache {totals.cache_written:,}, "
        f"read from it {totals.cache_read:,}, answered {totals.tokens_out:,}",
        f"  {(time.monotonic() - began) / 60:.1f} minutes in all",
    ]
    if totals.seconds:
        out.append(f"  a call took {statistics.median(totals.seconds):.1f} s in the middle, {max(totals.seconds):.1f} s at most")
    if totals.errors:
        out.append("  errors: " + ", ".join(f"{name} {count}" for name, count in totals.errors.most_common(8)))
    out.append(f"  keys left unasked: {unasked:,}" + (f" (stopped: {totals.stopped})" if totals.stopped else ""))
    return out


class _Recording:
    """The SDK's client, keeping each call's error message for its own thread: `client.ask`
    keeps only the error's name, and the scan must tell an account with no credit from a
    passing error."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._local = threading.local()
        self.messages = self

    def create(self, **request: Any) -> Any:
        self._local.message = ""
        try:
            return self._client.messages.create(**request)
        except Exception as error:
            self._local.message = str(error)[:400]
            raise

    @property
    def message(self) -> str:
        return getattr(self._local, "message", "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--answers", type=Path, default=None, help="the answers kept so far (default: --out)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--budget", type=float, default=40.0)
    parser.add_argument("--stop-after", type=float, default=18900.0, help="seconds")
    parser.add_argument("--per-call", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0, help="ask at most so many keys")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))

    from picwise_ai.shelves import PER_CALL, request_kwargs, taxonomy_lines
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    began = time.monotonic()
    lines = taxonomy_lines()
    if not lines:
        print("no Google taxonomy file: nothing to ask")
        return 1
    prepared = read_prepared_catalogue_to_measure(args.catalogue)
    if prepared is None:
        print("the copy is not a prepared catalogue: nothing to ask")
        return 1
    products = prepared.products
    when = prepared.prepared_at.isoformat()
    groups = groups_of(products, lines)
    del prepared
    answers = read_answers(args.answers if args.answers is not None else args.out)
    keys = to_ask(groups, answers)
    if args.limit:
        keys = keys[: args.limit]
    per_call = args.per_call or PER_CALL
    second = sum(group.products for group in groups.values() if group.second)
    print(
        f"the catalogue prepared at {when}: {len(products):,} products "
        f"({len(products) - second:,} of the first link, {second:,} of the second), read in {time.monotonic() - began:.0f} s"
    )
    notices = Notices()
    notices.say(
        "start",
        f"{len(products):,} products ({second:,} of the second link); keys (sizes and colours together) "
        f"{len(groups):,}; answered before {sum(1 for key in groups if key in answers):,}; to ask now "
        f"{len(keys):,} ({sum(groups[key].products for key in keys):,} products) in about "
        f"{-(-len(keys) // per_call):,} calls; budget ${args.budget:.2f}, {args.workers} at a time",
    )
    if keys:
        sample = request_kwargs([groups[key].item for key in keys[:per_call]], lines)
        print(f"a call: the cached part {sum(len(block['text']) for block in sample['system']):,} characters, its products about {len(sample['messages'][0]['content']):,}")
    if args.dry_run or not os.environ.get("ANTHROPIC_API_KEY") or not keys:
        print("not asked: " + ("--dry-run" if args.dry_run else "nothing to ask" if not keys else "no ANTHROPIC_API_KEY"))
        for line in (*report(groups, answers), *report_words(groups, answers)):
            print(line)
        if not args.dry_run:
            write_answers(args.out, answers)
        return 0

    from picwise_ai.client import ask, make_client

    client = _Recording(make_client(timeout=180.0, max_retries=3))

    def ask_fn(request: dict[str, Any]) -> tuple[Any, str]:
        asked = ask(request, client=client)
        return asked, client.message

    asking = Asking(
        ask_fn=ask_fn,
        groups=groups,
        answers=answers,
        lines=lines,
        workers=max(1, args.workers),
        budget=args.budget,
        deadline=time.monotonic() + args.stop_after,
        out=args.out,
        notices=notices,
    )
    unasked = scan(asking, keys, per_call)
    write_answers(args.out, answers)
    totals_lines = report_totals(asking, began, len(unasked))
    compare_lines = report(groups, answers)
    words_lines = report_words(groups, answers)
    kept = Counter("refused" if record.get("line") is None else "no line fits" if not record.get("line") else "a line" for record in answers.values())
    file_line = f"the answers file: {len(answers):,} keys ({dict(kept)}), {args.out.stat().st_size / 1048576:.1f} MB"
    notices.say("done", "\n".join([*totals_lines, file_line]), final=True)
    notices.say("compared", "\n".join(compare_lines), final=True)
    notices.say("words", "\n".join(words_lines), final=True)
    for line in (*compare_lines, *words_lines):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
