"""Task 6's trial: the question "is it the kind itself" asked of several models about the
same products, before its rules are written.

The look (`look_itself.py`) counted what the question would be asked about; this asks it
(`picwise_ai.itself`), on a copy of the server's prepared catalogue, about two small sets:

A. the first cards of the measure after's 40 searches, as the site answers them
   (`measure_after.SEARCHES`), each for the kind its search is read as;
B. a sample of the products the kinds' lists took out of a kind
   (`ai_shelves.checked_kinds`), each for the kind it lost: the products the question
   could bring back.

Each model named is asked the same questions: set A every model, set B the first two. The
run says, per model, the answers, the cost and what a thousand questions cost; how often
two models agree; every product two models read differently; and every answer, so that
the question's wording can be judged by reading. Nothing on the server or the site
changes, and no answer is kept anywhere.

    python3 deployment/server/try_itself.py CATALOGUE.json.gz [--shelves ANSWERS.jsonl.gz] \
        [--gone GONE.json] [--offers OFFERS.json] [--families FAMILIES.json] \
        [--models claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5] [--cards 12] \
        [--taken-kinds 20] [--taken-each 8] [--budget 1.50] [--dry-run]

It stops asking before a call would pass `--budget` dollars in all. Without
`ANTHROPIC_API_KEY`, or with `--dry-run`, nothing is asked: the run says what would be.
Titles, shops, prices and categories are printed, never a link, an id or the key. Always
exits 0.
"""
from __future__ import annotations

import argparse
import os
import random
import statistics
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")
CARDS = 12
TAKEN_KINDS = 20
TAKEN_EACH = 8
BUDGET_USD = 1.50
WORKERS = 4
SEED = 20261122
ABOUT_CHARS = 400
DESCRIPTION_KEYS = ("description", "product_short_description", "short_description")
# A call's cost guessed before any of a model's calls has come back: high, so that the
# budget stops early rather than late.
FIRST_GUESS_USD = {"claude-haiku-5-5": 0.004, "claude-sonnet-5-5": 0.06, "claude-opus-5-5": 0.12}
TITLE = 70


def _short(text: Any, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


@dataclass(frozen=True)
class Question:
    """One product asked for one kind: where it came from (a search, or "taken"), its place
    in the catalogue and what the model reads of it."""

    source: str
    kind: str
    place: int
    item: dict[str, str]
    shop: str


def item_of(product: Any) -> dict[str, str]:
    """A product as the model reads it (`picwise_ai.itself.item_line`)."""
    from picwise_ai.shelves import shop_words

    raw = product.raw if hasattr(product.raw, "get") else {}
    about = next((" ".join(str(raw.get(name)).split()) for name in DESCRIPTION_KEYS if str(raw.get(name) or "").strip()), "")
    return {
        "title": " ".join(str(product.title or "").split()),
        "brand": str(product.brand or ""),
        "category": shop_words(raw),
        "price": f"{product.price_text} {product.currency}".strip(),
        "about": about[:ABOUT_CHARS],
    }


def card_questions(prepared: Any, index: dict[str, int], cards: int) -> list[Question]:
    """Set A: each of the 40 searches' first cards, for the kind the search is read as."""
    import look_itself
    from measure_after import SEARCHES
    from picwise_providers.catalogue_cap import shop_of

    questions: list[Question] = []
    for query in SEARCHES:
        found = look_itself.searched(query, cards)
        if not found["kind"]:
            continue
        for product_id in found["cards"]:
            place = index.get(product_id)
            if place is None:
                continue
            product = prepared.products[place]
            questions.append(Question(query, found["kind"], place, item_of(product), shop_of(product)))
    return questions


def taken_questions(prepared: Any, kinds: int, each: int, seed: int = SEED) -> list[Question]:
    """Set B: of the kinds the lists took the most products out of, a sample of those
    products, each for the narrowest kind it lost."""
    import look_itself
    from picwise_providers.ai_shelves import key_of
    from picwise_providers.catalogue_cap import shop_of
    from picwise_providers.search_selection import kinds_before_the_kind_lists

    by_kind: dict[str, dict[str, int]] = defaultdict(dict)
    for place, (product, fields, after) in enumerate(zip(prepared.products, prepared.search_fields, prepared.kinds)):
        lost = look_itself.real_kinds(kinds_before_the_kind_lists(product, fields)) - look_itself.real_kinds(after)
        if not lost:
            continue
        key = key_of(product.title, product.brand, product.raw)
        for kind in look_itself.narrowest(frozenset(lost)):
            by_kind[kind].setdefault(key, place)
    chooser = random.Random(seed)
    questions: list[Question] = []
    for kind, places in sorted(by_kind.items(), key=lambda item: (-len(item[1]), item[0]))[:kinds]:
        chosen = sorted(chooser.sample(sorted(places.values()), min(each, len(places))))
        for place in chosen:
            product = prepared.products[place]
            questions.append(Question("taken", kind, place, item_of(product), shop_of(product)))
    return questions


@dataclass
class Asked:
    """What one model answered: per question (its place in the list asked), the answer and
    the few words; and what its calls cost."""

    model: str
    answers: dict[int, tuple[str, str]] = field(default_factory=dict)
    calls: int = 0
    failed: int = 0
    cost: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    seconds: list[float] = field(default_factory=list)
    errors: Counter = field(default_factory=Counter)
    not_asked: int = 0


class Budget:
    """The dollars every model's calls may cost together. A call is let through only when
    its guessed cost fits beside what is spent and what the calls still out are guessed at."""

    def __init__(self, limit: float) -> None:
        self.limit = limit
        self.spent = 0.0
        self.held = 0.0
        self.lock = threading.Lock()

    def reserve(self, guess: float) -> bool:
        with self.lock:
            if self.spent + self.held + guess > self.limit:
                return False
            self.held += guess
            return True

    def settle(self, guess: float, cost: float) -> None:
        with self.lock:
            self.held = max(0.0, self.held - guess)
            self.spent += cost


def ask_model(
    model: str,
    questions: list[Question],
    ask: Callable[[dict[str, Any]], Any] | None,
    budget: Budget,
    *,
    effort: str = "low",
    workers: int = WORKERS,
) -> Asked:
    """Every question asked of one model, a kind's products together, several calls at a
    time; a call not made for the budget leaves its questions not asked."""
    from picwise_ai import itself

    asked = Asked(model)
    order = sorted(range(len(questions)), key=lambda number: (questions[number].kind, number))
    calls = itself.batches([(questions[number].kind, number) for number in order])
    lock = threading.Lock()

    def one(call: list[tuple[str, list[int]]]) -> None:
        numbers = [number for _kind, group in call for number in group]
        with lock:
            guess = 1.5 * asked.cost / asked.calls if asked.calls else FIRST_GUESS_USD.get(model, 0.12)
        if ask is None or not budget.reserve(guess):
            with lock:
                asked.not_asked += len(numbers)
            return
        request = itself.request_kwargs(
            [(kind, [questions[number].item for number in group]) for kind, group in call], model=model, effort=effort
        )
        cost = 0.0
        try:
            answer = ask(request)
            cost = float(getattr(answer, "cost_usd", 0.0) or 0.0)
        finally:
            budget.settle(guess, cost)
        found = itself.checked_answers(getattr(answer, "answer", None), len(numbers))
        with lock:
            asked.calls += 1
            asked.cost += cost
            asked.tokens_in += int(getattr(answer, "input_tokens", 0) or 0) + int(getattr(answer, "cache_read_tokens", 0) or 0) \
                + int(getattr(answer, "cache_write_tokens", 0) or 0)
            asked.tokens_out += int(getattr(answer, "output_tokens", 0) or 0)
            asked.seconds.append(float(getattr(answer, "seconds", 0.0) or 0.0))
            error = str(getattr(answer, "error", "") or "")
            if error or getattr(answer, "answer", None) is None:
                asked.failed += 1
                asked.errors[error or str(getattr(answer, "stop_reason", "") or "no answer")] += 1
            for position, number in enumerate(numbers, 1):
                if position in found:
                    asked.answers[number] = found[position]

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, calls))
    return asked


def _side(answer: str) -> str:
    from picwise_ai import itself

    return "itself" if answer == itself.ITSELF else "not" if answer in itself.NOT_ITSELF else "unsure"


def _share(part: int, whole: int) -> str:
    return f"{part:,} of {whole:,} ({100 * part / whole:.1f}%)" if whole else f"{part:,} of 0"


def report_model(asked: Asked, questions: list[Question]) -> list[str]:
    answers = Counter(said for said, _what in asked.answers.values())
    lines = [
        f"{asked.model}: {len(asked.answers):,} of {len(questions):,} questions answered in {asked.calls} calls"
        f" ({asked.failed} failed, {asked.not_asked} questions not asked for the budget); ${asked.cost:.4f}"
        + (f", ${1000 * asked.cost / len(asked.answers):.3f} a thousand questions" if asked.answers else "")
        + f"; tokens read {asked.tokens_in:,}, answered {asked.tokens_out:,}"
        + (f"; a call {statistics.median(asked.seconds):.1f} s in the middle" if asked.seconds else ""),
        "  answers: " + ", ".join(f"{name} {count}" for name, count in answers.most_common()),
    ]
    if asked.errors:
        lines.append("  errors: " + ", ".join(f"{name} {count}" for name, count in asked.errors.most_common(5)))
    return lines


def report_agreement(first: Asked, second: Asked, questions: list[Question]) -> list[str]:
    """How often two models agree, on the side (itself, not, unsure) and on the very answer;
    and every question they read differently."""
    both = sorted(set(first.answers) & set(second.answers))
    same_side = [number for number in both if _side(first.answers[number][0]) == _side(second.answers[number][0])]
    same = [number for number in both if first.answers[number][0] == second.answers[number][0]]
    table: Counter[tuple[str, str]] = Counter(
        (_side(first.answers[number][0]), _side(second.answers[number][0])) for number in both
    )
    lines = [
        f"{first.model} and {second.model}: both answered {len(both):,}; the same side {_share(len(same_side), len(both))};"
        f" the very same answer {_share(len(same), len(both))}",
        "  " + "; ".join(f"{a} / {b}: {count}" for (a, b), count in sorted(table.items(), key=lambda item: -item[1])),
    ]
    for number in both:
        if number in same_side:
            continue
        question = questions[number]
        lines.append(
            f"  [{question.source} -> {question.kind}] {_short(question.item['title'])} | {question.item['price']}"
            f" | {_short(question.shop, 16)}: {first.answers[number][0]} ({first.answers[number][1]})"
            f" / {second.answers[number][0]} ({second.answers[number][1]})"
        )
    return lines


def report_searches(asked: list[Asked], questions: list[Question]) -> list[str]:
    """Per search of set A, how many of its cards each model reads as the kind itself."""
    by_source: dict[str, list[int]] = defaultdict(list)
    for number, question in enumerate(questions):
        if question.source != "taken":
            by_source[question.source].append(number)
    lines = ["search (kind): cards; itself by " + ", ".join(model.model.split("-")[1] for model in asked)]
    totals = [Counter() for _model in asked]
    for source, numbers in by_source.items():
        counts = []
        for position, model in enumerate(asked):
            sides = Counter(_side(model.answers[number][0]) for number in numbers if number in model.answers)
            totals[position].update(sides)
            counts.append(f"{sides['itself']}" + (f" (+{sides['unsure']} unsure)" if sides["unsure"] else ""))
        lines.append(f'  "{source}" ({questions[numbers[0]].kind}): {len(numbers)}; ' + ", ".join(counts))
    lines.append("in all: " + "; ".join(
        f"{model.model.split('-')[1]} itself {_share(total['itself'], sum(total.values()))}, unsure {total['unsure']}"
        for model, total in zip(asked, totals)
    ))
    return lines


def report_taken(asked: list[Asked], questions: list[Question]) -> list[str]:
    """Per kind of set B, how many of its sampled products each model reads as the kind itself."""
    by_kind: dict[str, list[int]] = defaultdict(list)
    for number, question in enumerate(questions):
        if question.source == "taken":
            by_kind[question.kind].append(number)
    lines = ["kind: sampled; itself by " + ", ".join(model.model.split("-")[1] for model in asked)]
    totals = [Counter() for _model in asked]
    for kind, numbers in by_kind.items():
        counts = []
        for position, model in enumerate(asked):
            sides = Counter(_side(model.answers[number][0]) for number in numbers if number in model.answers)
            totals[position].update(sides)
            counts.append(f"{sides['itself']}" if sides else "-")
        lines.append(f"  {kind}: {len(numbers)}; " + ", ".join(counts))
    lines.append("in all: " + "; ".join(
        f"{model.model.split('-')[1]} itself {_share(total['itself'], sum(total.values()))}"
        for model, total in zip(asked, totals) if total
    ))
    return lines


def report_every(asked: list[Asked], questions: list[Question]) -> list[str]:
    """Every question with each model's answer, to judge the wording by reading."""
    lines = []
    last = None
    for number, question in enumerate(questions):
        head = (question.source, question.kind)
        if head != last:
            lines.append(f'"{question.source}" for {question.kind}:')
            last = head
        said = " / ".join(
            (f"{model.answers[number][0]} ({model.answers[number][1]})" if number in model.answers else "-") for model in asked
        )
        lines.append(f"  {question.item['price']} | {_short(question.item['title'])} | {_short(question.shop, 16)} : {said}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--shelves", default="")
    parser.add_argument("--gone", default="")
    parser.add_argument("--offers", default="")
    parser.add_argument("--families", default="")
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--cards", type=int, default=CARDS)
    parser.add_argument("--taken-kinds", type=int, default=TAKEN_KINDS)
    parser.add_argument("--taken-each", type=int, default=TAKEN_EACH)
    parser.add_argument("--budget", type=float, default=BUDGET_USD)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    import look_itself
    from scan_shelves import Notices

    notices = Notices()
    began = time.monotonic()
    if args.shelves and Path(args.shelves).is_file() and Path(args.shelves).stat().st_size:
        os.environ["PICWISE_AI_SHELVES_FILE"] = str(Path(args.shelves).resolve())
    try:
        prepared = look_itself._load(args.catalogue, gone=args.gone, offers=args.offers, families=args.families)
    except Exception as error:  # a trial only
        notices.say("trial: failed", f"the catalogue could not be read: {type(error).__name__}: {error}", final=True)
        return 0
    if prepared is None:
        notices.say("trial: failed", "the copy is not a prepared catalogue", final=True)
        return 0
    index = {str(product.provider_product_id): place for place, product in enumerate(prepared.products)}
    cards = card_questions(prepared, index, args.cards)
    taken = taken_questions(prepared, args.taken_kinds, args.taken_each)
    print(f"the catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products; set A {len(cards)} "
          f"questions (the first {args.cards} cards of the searches), set B {len(taken)} (taken out of a kind by the lists);"
          f" read in {time.monotonic() - began:.0f} s")
    models = [name.strip() for name in args.models.split(",") if name.strip()]
    ask = None
    if not args.dry_run and os.environ.get("ANTHROPIC_API_KEY"):
        from picwise_ai.client import ask as ask_one, make_client

        client = make_client(timeout=120.0, max_retries=3)
        ask = lambda request: ask_one(request, client=client)  # noqa: E731
    else:
        print("the AI: not asked (a dry run, or no key)")
    budget = Budget(args.budget)
    questions = cards + taken
    asked: list[Asked] = []
    for position, model in enumerate(models):
        # Set B only of the first two models: the dearest reads the cards alone.
        asked_of = questions if position < 2 else cards
        found = ask_model(model, asked_of, ask, budget)
        asked.append(found)
        notices.say(f"trial: {model}", "\n".join(report_model(found, asked_of)), final=True)
    notices.say("trial: the cost", f"${budget.spent:.4f} of ${args.budget:.2f} in all", final=True)
    for first in range(len(asked)):
        for second in range(first + 1, len(asked)):
            lines = report_agreement(asked[first], asked[second], questions)
            notices.say(f"trial: {asked[first].model.split('-')[1]} and {asked[second].model.split('-')[1]}",
                        "\n".join(lines[:2]), final=True)
            for line in lines:
                print(line)
    for title, lines in (
        ("trial: the searches' cards", report_searches(asked, questions)),
        ("trial: taken out of a kind", report_taken(asked[:2], questions)),
    ):
        notices.say(title, "\n".join(lines)[:3800], final=True)
        for line in lines:
            print(line)
    print("== every question, each model's answer (" + " / ".join(model.model for model in asked) + ")")
    for line in report_every(asked, questions):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
