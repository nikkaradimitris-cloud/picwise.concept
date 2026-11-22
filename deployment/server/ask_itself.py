"""Task 6's first asking: the question "is it the kind itself" asked for every product of a
catalogue (`docs/PICWISE_KIND_ITSELF_RULES.md`, 8.1; the owner's plan of 21/11, step 8: a
question to the AI for every product, the cheapest of each kind first, about $25 once).

On a copy of the server's prepared catalogue, with the AI's shelves beside it, the nights
are lived one after another without waiting for them: each round names what the night's
preparation would name (`picwise_providers.kind_itself.job_items`: the questions with no
first reading, those that wait for a second, each kind's first cards as the answers so far
leave them, the broader kind of what was read as another thing) and asks it as the morning's
service would (`picwise_ai.itself_asking.run`: the first reading by Claude Haiku 5.5, the
second by Claude Sonnet 5.5), until a round names nothing, or the rounds, the budget or the
time end. The answers are written to `--out` along the way; with `--answers`, the answers
kept so far are read first and nothing they hold is asked again.

Then it says what the answers would do, were the switch turned: how many products would
leave a kind, by answer, how many would come back, and the kinds that would lose and gain
the most. Nothing on the server or the site changes: no rule reads the answers until
`data/kind_itself_switch.json` is turned, on the owner's word, after a look.

    python3 deployment/server/ask_itself.py CATALOGUE.json.gz --out ANSWERS.jsonl.gz \
        [--answers KEPT.jsonl.gz] [--shelves SHELF_ANSWERS.jsonl.gz] [--budget 20] \
        [--stop-after 6000] [--workers 8] [--rounds 6] [--dry-run]

Without `ANTHROPIC_API_KEY`, or with `--dry-run`, nothing is asked: the run says what the
first round would ask and what it would cost. Counts, kinds' names and the cost are
printed, never a link, an id or the key. Exits 0, also when the catalogue cannot be read
(a count only); 1 when the answers kept cannot be read (they are never written over).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

BUDGET_USD = 20.0
STOP_AFTER_SECONDS = 6000.0
WORKERS = 8
ROUNDS = 6
# What a thousand readings cost in the trials of 22/11, and the share of the first readings
# that called for a second: for a dry run's estimate only.
FIRST_PER_THOUSAND = 0.037
SECOND_PER_THOUSAND = 0.58
SECOND_SHARE = (0.10, 0.16)
# A day no reading is younger than: the rounds are lived with no brake, which are for the
# nights after the owner's look.
NO_BRAKE = "9999-12-31"
KINDS_LISTED = 15

Read = Callable[[int], tuple[frozenset[str], frozenset[str], str]]


def read_kinds(prepared: Any) -> tuple[Read, dict[str, int]]:
    """Each product's own kinds, the kinds the lists leave it and its question's key, read
    once (`search_selection.kinds_read`); and how the copy's products count: those with a
    question, those the lists took out of a kind, and those whose kinds read here are not
    the prepared file's (other rules, or other shelves, than the server's)."""
    from picwise_providers.kind_itself import real_kinds
    from picwise_providers.search_selection import kinds_read

    found = [kinds_read(product, fields) for product, fields in zip(prepared.products, prepared.search_fields)]
    counts = {
        "products": len(found),
        "with_a_question": sum(1 for _before, _after, key in found if key),
        "taken_out_by_the_lists": sum(1 for before, after, key in found if key and real_kinds(before) - real_kinds(after)),
        "read_otherwise_here": sum(1 for (_before, after, _key), kinds in zip(found, prepared.kinds) if after != kinds),
    }
    return found.__getitem__, counts


def name_round(records: dict, products: Any, read: Read, today: str) -> tuple[list[dict[str, Any]], Any, list[frozenset[str]]]:
    """What a night's preparation would name with the answers kept so far, every product
    kept; that night, for its count of what the answers do; and every product's kinds."""
    from picwise_providers import kind_itself

    night = kind_itself.Night(records=records, looked_until=NO_BRAKE, today=today)
    kinds: list[frozenset[str]] = []
    for place in range(len(products)):
        before, after, key = read(place)
        kinds.append(night.settle(place, before, after, key) if key else after)
    kinds = night.finish(kinds)
    items = kind_itself.job_items(night, products, range(len(products)), read, kept=products, kept_kinds=kinds)
    return items, night, kinds


def front(products: Any, read: Read, kinds: list[frozenset[str]], clock: Callable[[], float] = time.monotonic) -> str:
    """Each kind's first cards as the kinds stand, counted: for a dry run, beside the look's
    own count of them (22/11: 5,731 cards in 293 kinds, 5,633 questions), and how long the
    night's preparation would take to work them out."""
    from picwise_providers import kind_itself

    began = clock()
    cards = kind_itself.first_cards(products, kinds)
    seconds = clock() - began
    questions = {(read(place)[2], kind) for kind, places in cards.items() for place in places}
    return (f"each kind's first cards (the first {kind_itself.FRONT} and the Recommended): "
            f"{sum(len(places) for places in cards.values()):,} cards in {len(cards):,} kinds, {len(questions):,} questions;"
            f" worked out in {seconds:.1f} s")


def named(items: list[dict[str, Any]]) -> str:
    wants = Counter(str(item.get("want")) for item in items)
    whys = Counter(str(item.get("why")) for item in items)
    return (f"{len(items):,} questions in {len({item['kind'] for item in items}):,} kinds: {wants['first']:,} for a first"
            f" reading, {wants['second']:,} for a second ({whys['kind']:,} of a kind the product has, {whys['taken']:,} of"
            f" a kind the lists took, {whys['first card']:,} first cards"
            + (f"; {sum(1 for item in items if item.get('again')):,} asked again" if any(item.get("again") for item in items) else "")
            + ")")


def estimate(items: list[dict[str, Any]]) -> str:
    """A dry run's guess of the whole asking's cost, from the first round's questions."""
    firsts = sum(1 for item in items if item.get("want") == "first")
    seconds = sum(1 for item in items if item.get("want") == "second")
    low, high = (seconds + share * firsts for share in SECOND_SHARE)
    return (f"by the trials of 22/11: the first readings about ${firsts * FIRST_PER_THOUSAND / 1000:.2f}; the second,"
            f" {low:,.0f} to {high:,.0f} before the first cards are read again, ${low * SECOND_PER_THOUSAND / 1000:.2f} to"
            f" ${high * SECOND_PER_THOUSAND / 1000:.2f}; the first cards themselves come in the rounds after")


def effect(night: Any) -> list[str]:
    """What the answers kept would do, were the switch turned: counts and kinds' names."""
    note = night.note()
    left = ", ".join(f"{name} {count:,}" for name, count in note["left_by_answer"].items()) or "none"

    def listed(rows: list[dict[str, Any]]) -> str:
        return ", ".join(f"{row['kind']} {row['products']:,}" for row in rows[:KINDS_LISTED]) or "none"

    return [
        f"{note['questions_kept']:,} questions kept; {note['products_with_a_second_reading']:,} products with a second reading",
        f"would leave a kind: {note['left_a_kind']:,} products ({left}); would come back: {note['came_back']:,}",
        f"the kinds that would lose the most: {listed(note['kinds_that_lost_the_most'])}",
        f"the kinds that would gain the most: {listed(note['kinds_that_gained_the_most'])}",
        f"still waiting for a reading: {note['products_with_a_question_waiting']:,} products",
    ]


def rounds(
    products: Any,
    read: Read,
    records: dict,
    *,
    ask_fn: Callable[[dict[str, Any]], Any] | None,
    budget: Any,
    today: str,
    deadline: float | None = None,
    workers: int = WORKERS,
    most: int = ROUNDS,
    save: Callable[[], None] | None = None,
    say: Callable[[str], None] = print,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[list[Any], Any]:
    """The rounds, until one names nothing; each round's totals, and the night as the last
    answers leave it. With no `ask_fn` (a dry run), the first round is named and counted."""
    from picwise_ai import itself_asking

    done: list[Any] = []
    for number in range(1, most + 1):
        began = clock()
        items, night, kinds = name_round(records, products, read, today)
        say(f"round {number}: {named(items)}; named in {clock() - began:.0f} s")
        if not items:
            return done, night
        if ask_fn is None:
            say(estimate(items))
            say(front(products, read, kinds, clock))
            return done, night
        totals = itself_asking.run(items, records, ask_fn=ask_fn, budget=budget, today=today, deadline=deadline,
                                   clock=clock, workers=workers, save=save)
        done.append(totals)
        for line in itself_asking.report(totals):
            say(f"round {number}: {line}")
        if totals.stopped:
            break
        if not sum(totals.answered.values()):
            say(f"round {number}: no reading came back: stopping")
            break
    _items, night, _kinds = name_round(records, products, read, today)
    return done, night


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="the answers, written here")
    parser.add_argument("--answers", default="", help="the answers kept so far, read first")
    parser.add_argument("--shelves", default="", help="the AI's shelves, as the server's preparation reads them")
    parser.add_argument("--budget", type=float, default=BUDGET_USD)
    parser.add_argument("--stop-after", type=float, default=STOP_AFTER_SECONDS, help="seconds of asking")
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    import look_itself
    from picwise_ai.client import Budget
    from picwise_providers import kind_itself
    from scan_shelves import Notices

    notices = Notices()
    began = time.monotonic()
    if args.shelves and Path(args.shelves).is_file() and Path(args.shelves).stat().st_size:
        os.environ["PICWISE_AI_SHELVES_FILE"] = str(Path(args.shelves).resolve())
    else:
        print("no AI's shelves given: the kinds are read without the lists")
    try:
        prepared = look_itself._load(args.catalogue, gone="", offers="", families="")
    except Exception as error:  # a count only
        notices.say("the first asking: failed", f"the catalogue could not be read: {type(error).__name__}: {error}", final=True)
        return 0
    if prepared is None:
        notices.say("the first asking: failed", "the copy is not a prepared catalogue", final=True)
        return 0
    records: dict = {}
    kept = Path(args.answers) if args.answers else None
    if kept is not None and kept.is_file() and kept.stat().st_size:
        if not kind_itself.answers_readable(kept):
            notices.say("the first asking: failed", "the answers kept cannot be read: nothing asked, nothing written", final=True)
            return 1
        records = kind_itself.read_answers(kept)
    read, counts = read_kinds(prepared)
    print(f"the catalogue of {prepared.prepared_at.isoformat()}: {counts['products']:,} products,"
          f" {counts['with_a_question']:,} with a question, {counts['taken_out_by_the_lists']:,} taken out of a kind by the"
          f" lists; {counts['read_otherwise_here']:,} whose kinds read here are not the prepared file's;"
          f" {len(records):,} questions kept so far; read in {time.monotonic() - began:.0f} s")
    ask_fn = None
    if not args.dry_run and os.environ.get("ANTHROPIC_API_KEY"):
        from picwise_ai.client import ask as ask_one, make_client

        client = make_client(timeout=180.0, max_retries=3)
        ask_fn = lambda request: ask_one(request, client=client)  # noqa: E731
    else:
        print("the AI: not asked (a dry run, or no key)")
    budget = Budget(args.budget)
    today = datetime.now(timezone.utc).date().isoformat()
    done, night = rounds(
        prepared.products, read, records, ask_fn=ask_fn, budget=budget, today=today,
        deadline=time.monotonic() + args.stop_after, workers=max(1, args.workers), most=max(1, args.rounds),
        save=lambda: kind_itself.write_answers(args.out, records),
    )
    if ask_fn is not None:
        kind_itself.write_answers(args.out, records)
    stopped = next((totals.stopped for totals in done if totals.stopped), "")
    summary = [
        f"{len(done)} rounds; {sum(sum(totals.answered.values()) for totals in done):,} readings kept;"
        f" ${budget.spent:.4f} of ${args.budget:.2f}" + (f"; stopped at {stopped}" if stopped else ""),
        *effect(night),
    ]
    notices.say("the first asking", "\n".join(summary), final=True)
    for line in summary:
        print(line)
    print(f"in {time.monotonic() - began:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
