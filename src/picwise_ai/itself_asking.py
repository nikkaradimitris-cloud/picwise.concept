"""The asking of the question "is it the kind itself": the readings a list of questions
waits for, asked of the two models and kept (`docs/PICWISE_KIND_ITSELF_RULES.md`, 4.4, 4.7
and 8).

The night's preparation names the questions (`picwise_providers.kind_itself.job_items`: one
item a question, with what the model reads of a product); this asks them and keeps the
answers in the records the preparation reads. Used by the service of every morning
(`deployment/server/itself_service.py`) and by the first asking of a whole catalogue
(`deployment/server/ask_itself.py`). No SDK here: the caller gives the function that sends
one request (`picwise_ai.client.ask` with its client).

- **The first reading** (`itself.MODEL`) of every question that has none, or whose answer
  was asked under other words of its kind.
- **The second reading** (`itself.SECOND_MODEL`), in the same run: of a question that has a
  first reading and no second (the preparation names only those that call for one); and of
  each first reading just made that calls for one: not itself (or unsure) for a kind the
  product has, itself for a kind the lists took from it, any answer for a first card, any
  answer where the answer it replaces had a second.
- **An answer stands until another takes its place**: a question asked again keeps its old
  record until the new one is whole (its first reading, and its second where one is called
  for).
- A reading asked for that the model gave no answer to (a product's number left out, an
  answer that does not check out, a refusal) is counted in the record; after
  `kind_itself.MOST_TRIES` the question is left, here and by the preparation. A call the API
  itself failed (no answer within the time, too many requests, an error of the network) counts
  against no question: its products are left for the next run, after a pause.
- A call holds products of one kind, `itself.PER_CALL` at most; each kind's first call goes
  before any kind's second, so that a run stopped by its limit or its time has served every
  kind's cheapest products (the questions come cheapest first). The run stops before a call
  would pass its budget, and at its deadline; what it did not ask stays for the next run.
"""
from __future__ import annotations

import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from picwise_providers.kind_itself import FIRST, ITSELF, MOST_TRIES, SECOND, Reading, Record

from . import itself
from .client import Budget

# A call's cost guessed before any call of its reading has come back: high, so that the
# budget stops early rather than late (the trials of 22/11: a Haiku call of 40 products
# $0.0015, a Sonnet one $0.023).
FIRST_GUESS_USD = {itself.MODEL: 0.004, itself.SECOND_MODEL: 0.06}
DEAREST_GUESS_USD = 0.12
# The answers are written to their file after so many calls, and at the end.
SAVE_EVERY = 40
WORKERS = 4
# Seconds a worker waits after a call the API failed, before its next one.
PAUSE_AFTER_A_FAILURE = 15.0


@dataclass
class Totals:
    """What one run did, by reading ("first", "second")."""

    questions: int = 0
    # Named with nothing to ask: both readings kept, a kind the site does not have, a
    # question left after its tries.
    nothing_to_ask: int = 0
    calls: Counter = field(default_factory=Counter)
    failed_calls: Counter = field(default_factory=Counter)
    asked: Counter = field(default_factory=Counter)
    answered: Counter = field(default_factory=Counter)
    not_asked: Counter = field(default_factory=Counter)
    said: dict[str, Counter] = field(default_factory=lambda: {FIRST: Counter(), SECOND: Counter()})
    cost: dict[str, float] = field(default_factory=lambda: {FIRST: 0.0, SECOND: 0.0})
    # Of the questions asked again, those whose new answer took the old one's place.
    replaced: int = 0
    errors: Counter = field(default_factory=Counter)
    stopped: str = ""

    def cost_usd(self) -> float:
        return sum(self.cost.values())

    def left(self) -> int:
        """The readings named that the run did not get: not asked, or asked with no answer."""
        return sum(self.not_asked.values()) + sum(self.asked.values()) - sum(self.answered.values())

    def note(self) -> dict[str, Any]:
        """Counts and the cost, never a product."""
        return {
            "questions": self.questions,
            "nothing_to_ask": self.nothing_to_ask,
            **{reading: {
                "calls": self.calls[reading], "failed_calls": self.failed_calls[reading], "asked": self.asked[reading],
                "answered": self.answered[reading], "not_asked": self.not_asked[reading],
                "said": dict(sorted(self.said[reading].items())), "cost_usd": round(self.cost[reading], 4),
            } for reading in (FIRST, SECOND)},
            "asked_again_and_replaced": self.replaced,
            "left": self.left(),
            "cost_usd": round(self.cost_usd(), 4),
            "stopped": self.stopped,
        }


@dataclass
class _Pending:
    """One question on its way: its item, the kind's version of today, the record it would
    replace when it is asked again (None for a question with no answer yet), and the first
    reading in hand."""

    item: Mapping[str, Any]
    version: str
    old: Record | None = None
    first: Reading | None = None

    @property
    def place(self) -> tuple[str, str]:
        return str(self.item["k"]), str(self.item["kind"])


def calls_for_second(item: Mapping[str, Any], said: str) -> bool:
    """Does a first reading call for a second (the rules' 4.4)? What it would move: not
    itself, or unsure, for a kind the product has; itself for a kind the lists took from
    it. And every first card."""
    why = str(item.get("why") or "")
    if why == "taken":
        return said == ITSELF
    return said != ITSELF or why == "first card"


def in_turn(calls: Sequence[tuple[str, list[Any]]]) -> list[tuple[str, list[Any]]]:
    """A kind's calls in their order, each kind's first before any kind's second."""
    by_kind: dict[str, list[list[Any]]] = {}
    for kind, batch in calls:
        by_kind.setdefault(kind, []).append(batch)
    ordered: list[tuple[str, list[Any]]] = []
    rank = 0
    while True:
        row = [(kind, batches[rank]) for kind, batches in by_kind.items() if rank < len(batches)]
        if not row:
            return ordered
        ordered.extend(row)
        rank += 1


def run(
    items: Sequence[Mapping[str, Any]],
    records: dict[tuple[str, str], Record],
    *,
    ask_fn: Callable[[dict[str, Any]], Any],
    budget: Budget,
    today: str,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    workers: int = WORKERS,
    save: Callable[[], None] | None = None,
    save_every: int = SAVE_EVERY,
    first: tuple[str, str] = (itself.MODEL, itself.EFFORT),
    second: tuple[str, str] = (itself.SECOND_MODEL, itself.SECOND_EFFORT),
    versions: Callable[[str], str] = itself.kind_version,
    sleep: Callable[[float], None] = time.sleep,
) -> Totals:
    """Ask what `items` wait for and keep the answers in `records` (changed in place).
    `ask_fn` sends one request and gives an answer as `client.ask` does (its `answer`,
    `cost_usd` and `error`); `save` writes the records to their file."""
    totals = Totals(questions=len(items))
    lock = threading.Lock()
    firsts: list[_Pending] = []
    seconds: list[_Pending] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key, kind = str(item.get("k") or ""), str(item.get("kind") or "")
        version = versions(kind) if key and kind else ""
        if not version or (key, kind) in seen:
            totals.nothing_to_ask += 1
            continue
        seen.add((key, kind))
        record = records.get((key, kind))
        if record is not None and record.tries_under(version) >= MOST_TRIES:
            totals.nothing_to_ask += 1
        elif record is None or record.first is None:
            firsts.append(_Pending(item, version))
        elif record.version != version:
            firsts.append(_Pending(item, version, old=record))
        elif record.second is None:
            seconds.append(_Pending(item, version, first=record.first))
        else:
            totals.nothing_to_ask += 1

    def keep_first(pending: _Pending, got: tuple[str, str] | None, model: str, follow: list[_Pending]) -> None:
        place = pending.place
        if got is None:
            record = pending.old or records.get(place) or Record(place[0], place[1], pending.version)
            record.no_answer(pending.version)
            records[place] = record
            return
        pending.first = Reading(got[0], got[1], model, today)
        again = pending.old is not None
        wants_second = calls_for_second(pending.item, got[0]) or (again and pending.old.second is not None)
        if wants_second:
            follow.append(pending)
        if again and wants_second:
            return  # the old answer stands until the second reading comes
        records[place] = Record(place[0], place[1], pending.version, pending.first)
        if again:
            totals.replaced += 1

    def keep_second(pending: _Pending, got: tuple[str, str] | None, model: str, _follow: list[_Pending]) -> None:
        place = pending.place
        if got is None:
            (pending.old or records[place]).no_answer(pending.version)
            return
        records[place] = Record(place[0], place[1], pending.version, pending.first, Reading(got[0], got[1], model, today))
        if pending.old is not None:
            totals.replaced += 1

    def ask_round(reading: str, pendings: list[_Pending], model: str, effort: str,
                  keep: Callable[[_Pending, tuple[str, str] | None, str, list[_Pending]], None]) -> list[_Pending]:
        follow: list[_Pending] = []
        calls = in_turn(itself.batches([(str(pending.item["kind"]), pending) for pending in pendings]))

        def one(call: tuple[str, list[_Pending]]) -> None:
            kind, batch = call
            with lock:
                if not totals.stopped and deadline is not None and clock() >= deadline:
                    totals.stopped = "its time"
                if totals.stopped:
                    totals.not_asked[reading] += len(batch)
                    return
                made = totals.calls[reading]
                guess = 1.5 * totals.cost[reading] / made if made else FIRST_GUESS_USD.get(model, DEAREST_GUESS_USD)
            if not budget.reserve(guess):
                with lock:
                    totals.stopped = totals.stopped or f"its limit of ${budget.limit:.2f}"
                    totals.not_asked[reading] += len(batch)
                return
            answer, cost, failure = None, 0.0, ""
            try:
                answer = ask_fn(itself.request_kwargs(kind, [pending.item for pending in batch], model=model, effort=effort))
                cost = float(getattr(answer, "cost_usd", 0.0) or 0.0)
            except Exception as error:  # a call that failed is a call with no answer
                failure = type(error).__name__
            finally:
                budget.settle(guess, cost)
            # The API's own failure (nothing came back: no stop reason) is not the model's
            # answer to these products: nothing is counted against their questions.
            api_failed = answer is None or (getattr(answer, "answer", None) is None
                                            and not str(getattr(answer, "stop_reason", "") or ""))
            found = {} if api_failed else itself.checked_answers(getattr(answer, "answer", None), len(batch))
            with lock:
                totals.calls[reading] += 1
                totals.cost[reading] += cost
                if not found:
                    totals.failed_calls[reading] += 1
                    totals.errors[failure or str(getattr(answer, "error", "") or "")
                                  or str(getattr(answer, "stop_reason", "") or "") or "no answer"] += 1
                if api_failed:
                    totals.not_asked[reading] += len(batch)
                else:
                    totals.asked[reading] += len(batch)
                    for position, pending in enumerate(batch, 1):
                        got = found.get(position)
                        if got is not None:
                            totals.answered[reading] += 1
                            totals.said[reading][got[0]] += 1
                        keep(pending, got, model, follow)
                if save is not None and save_every > 0 and sum(totals.calls.values()) % save_every == 0:
                    save()
            if api_failed:
                sleep(PAUSE_AFTER_A_FAILURE)

        if calls:
            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                list(pool.map(one, calls))
        return follow

    follow = ask_round(FIRST, firsts, first[0], first[1], keep_first)
    ask_round(SECOND, seconds + follow, second[0], second[1], keep_second)
    if save is not None:
        save()
    return totals


def report(totals: Totals) -> list[str]:
    """What a run did, in lines: counts and the cost only."""
    lines = []
    for reading, model in ((FIRST, itself.MODEL), (SECOND, itself.SECOND_MODEL)):
        asked = totals.asked[reading]
        said = ", ".join(f"{name} {count:,}" for name, count in totals.said[reading].most_common())
        lines.append(
            f"the {reading} reading ({model}): {asked:,} asked in {totals.calls[reading]:,} calls"
            f" ({totals.failed_calls[reading]:,} failed), {totals.answered[reading]:,} answered"
            + (f" ({said})" if said else "")
            + f", {totals.not_asked[reading]:,} not asked; ${totals.cost[reading]:.4f}"
            + (f", ${1000 * totals.cost[reading] / totals.answered[reading]:.3f} a thousand"
               if totals.answered[reading] else "")
        )
    if totals.errors:
        lines.append("calls with no answer: " + ", ".join(f"{name} {count}" for name, count in totals.errors.most_common(6)))
    lines.append(
        f"in all: {totals.questions:,} questions named, {totals.nothing_to_ask:,} with nothing to ask,"
        f" {totals.replaced:,} asked again and replaced, {totals.left():,} readings left; ${totals.cost_usd():.4f}"
        + (f"; stopped at {totals.stopped}" if totals.stopped else "")
    )
    return lines
