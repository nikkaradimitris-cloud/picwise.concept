"""The trial of the AI's shelves: 1,000 products of a copy of the server's catalogue.

Owner, 2026-11-19: «Μπλέξουμε και το ai για να ταξινομήσουμε όλο τον κατάλογο»; 20/11,
«Ναι κάνε καί τά 2»: a trial on 1,000 products, under $1, before the whole catalogue.
Claude Haiku 5.5 gives each product one line of Google's taxonomy (`picwise_ai.shelves`);
the code checks every answer against the taxonomy. Two halves:

- A: products of the first link whose shop gave a Google line three levels deep or more.
  The AI is shown the title, brand, price and the start of the description, never the
  shop's line nor its category words: the shop's line is the answer the AI's is read
  against (a product with no category at all, as the first link's ~900,000 rows held
  for none, gives the AI no more than this);
- B: products of the second link whose shelf was read from broad category words
  (Tooled Up's «DIY»): the AI is shown the shop's category words too, and its line is
  printed beside the shelf the product has now, to be read by hand.

Printed: the products asked, answered, "no line fits" and refused; the cost, the tokens and
the time; for A, how often the AI's line agrees with the shop's, level by level, and the
disagreements; for B, how often the AI's line is deeper or in another department, and a
sample; the whole catalogue's cost at this price. Nothing on the server or the site
changes.

    python3 deployment/server/measure_shelves.py CATALOGUE.json.gz [--products 1000] \
        [--per-call 50] [--budget 1.00] [--seed 20261120] [--dry-run]

The AI is asked only with `ANTHROPIC_API_KEY` set and without `--dry-run`. It stops asking
before a call would pass `--budget` dollars. The repository and its logs are public:
titles, brands, shops and categories are printed, never a link, a description or the key.
"""
from __future__ import annotations

import argparse
import os
import random
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The second link's own columns (Awin's format), and those the shelf was read from when
# it was broad: `awin_adapter._with_aisle` drops them when the shelf it read is precise.
SECOND_KEYS = ("merchant_id", "aw_product_id")
AWIN_CATEGORY_COLUMNS = (
    "merchant_product_category_path",
    "merchant_product_second_category",
    "merchant_product_third_category",
    "merchant_category",
    "category_name",
)
DESCRIPTION_KEYS = ("description", "product_short_description", "short_description")
# One shop never fills a half: at most this many products of a shop in each.
PER_SHOP = {"A": 15, "B": 60}
DEEP_ENOUGH = 3
LISTED = {"A": 40, "B": 60}
TITLE = 70


@dataclass
class Picked:
    half: str
    shop: str
    title: str
    item: dict[str, Any]
    shelf_now: str
    shop_words: str = ""


@dataclass
class Answered:
    picked: Picked
    line: str | None  # None: refused or not answered; "": no line fits


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _short(text: Any, width: int = TITLE) -> str:
    text = _text(text)
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def _first(raw: Any, keys: Sequence[str]) -> str:
    for key in keys:
        value = _text(raw.get(key))
        if value:
            return value
    return ""


def shop_words(raw: Any) -> str:
    """The second link's category words, each once, in the columns' order."""
    words: list[str] = []
    for key in AWIN_CATEGORY_COLUMNS:
        value = _text(raw.get(key))
        if value and value.casefold() not in (word.casefold() for word in words):
            words.append(value)
    return " / ".join(words)


def pick(products: Sequence[Any], lines: Sequence[str], *, total: int, seed: int) -> list[Picked]:
    """Half of `total` from each of A and B (the other half takes what one lacks), the
    products shuffled with `seed` and at most `PER_SHOP` of a shop in a half."""
    from picwise_ai.shelves import levels, line_index
    from picwise_providers.catalogue_cap import shop_of

    index = line_index(lines)
    candidates: dict[str, list[Picked]] = {"A": [], "B": []}
    for product in products:
        raw = product.raw if hasattr(product.raw, "get") else {}
        item = {
            "title": product.title,
            "brand": product.brand,
            "price": product.price_text,
            "about": _first(raw, DESCRIPTION_KEYS),
        }
        shop = shop_of(product)
        if any(_text(raw.get(key)) for key in SECOND_KEYS):
            words = shop_words(raw)
            if not words:
                continue
            item["category"] = words
            shelf = _text(raw.get("google_product_category")) or _text(product.category_text)
            candidates["B"].append(Picked("B", shop, product.title, item, shelf, words))
        elif _text(raw.get("advertiser_id")):
            line = index.get(" > ".join(levels(_text(raw.get("google_product_category")))))
            if line and len(levels(line)) >= DEEP_ENOUGH:
                candidates["A"].append(Picked("A", shop, product.title, item, line))
    chosen: list[Picked] = []
    wanted = {"A": total // 2, "B": total - total // 2}
    if len(candidates["B"]) < wanted["B"]:
        wanted = {"A": total - len(candidates["B"]), "B": len(candidates["B"])}
    elif len(candidates["A"]) < wanted["A"]:
        wanted = {"A": len(candidates["A"]), "B": total - len(candidates["A"])}
    shuffler = random.Random(seed)
    for half in ("A", "B"):
        pool = candidates[half]
        shuffler.shuffle(pool)
        per_shop: Counter[str] = Counter()
        taken = 0
        for found in pool:
            if taken >= wanted[half]:
                break
            if per_shop[found.shop] >= PER_SHOP[half]:
                continue
            per_shop[found.shop] += 1
            chosen.append(found)
            taken += 1
    return chosen


def batches(chosen: Sequence[Picked], per_call: int) -> list[list[Picked]]:
    """Calls of one half each, A and B in turn, so a budget that stops early leaves both."""
    by_half = {half: [found for found in chosen if found.half == half] for half in ("A", "B")}
    calls = {half: [items[i : i + per_call] for i in range(0, len(items), per_call)] for half, items in by_half.items()}
    ordered: list[list[Picked]] = []
    for position in range(max(len(calls["A"]), len(calls["B"]), 0)):
        for half in ("A", "B"):
            if position < len(calls[half]):
                ordered.append(calls[half][position])
    return ordered


@dataclass
class Totals:
    calls: int = 0
    failed: int = 0
    cost: float = 0.0
    most: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cache_written: int = 0
    cache_read: int = 0
    models: Counter = field(default_factory=Counter)
    errors: Counter = field(default_factory=Counter)
    seconds: list[float] = field(default_factory=list)


def run(
    calls: Sequence[Sequence[Picked]],
    lines: Sequence[str],
    *,
    ask_fn: Callable[[dict[str, Any]], Any],
    budget: float,
) -> tuple[list[Answered], Totals, int]:
    """Ask each call while the budget allows the next; the answers, the totals and how many
    calls were left unasked."""
    from picwise_ai.shelves import checked_lines, request_kwargs

    answered: list[Answered] = []
    totals = Totals()
    for position, items in enumerate(calls):
        # The next call's cost, guessed high: half again the dearest so far (the first
        # writes the tree to the cache), and before any answer two cents.
        if totals.cost + (1.5 * totals.most if totals.calls else 0.02) > budget:
            return answered, totals, len(calls) - position
        asked = ask_fn(request_kwargs([found.item for found in items], lines))
        totals.calls += 1
        totals.cost += asked.cost_usd
        totals.most = max(totals.most, asked.cost_usd, 0.002)
        totals.tokens_in += asked.input_tokens
        totals.tokens_out += asked.output_tokens
        totals.cache_written += asked.cache_write_tokens
        totals.cache_read += asked.cache_read_tokens
        totals.seconds.append(asked.seconds)
        if asked.model:
            totals.models[asked.model] += 1
        if asked.error or asked.answer is None:
            totals.failed += 1
            totals.errors[asked.error or asked.stop_reason or "no answer"] += 1
        found = checked_lines(asked.answer, len(items), lines)
        for number, picked in enumerate(items, 1):
            answered.append(Answered(picked, found.get(number)))
        print(
            f"call {totals.calls}: {items[0].half}, {len(found)} of {len(items)} answered"
            + (f" ({asked.error})" if asked.error else "")
            + f"; {asked.seconds:.1f} s; ${asked.cost_usd:.5f}; cache read {asked.cache_read_tokens:,}, "
            f"written {asked.cache_write_tokens:,}; ${totals.cost:.4f} in all"
        )
    return answered, totals, 0


def _share(part: int, whole: int) -> str:
    return f"{part:,} of {whole:,} ({100 * part / whole:.1f}%)" if whole else f"{part:,} of 0"


def report_a(answered: Sequence[Answered]) -> list[str]:
    """The AI's line against the shop's own, level by level."""
    from picwise_ai.shelves import levels

    lines_out = ["== A: the AI's line against the shop's own Google line (hidden from the AI)"]
    rows = [found for found in answered if found.picked.half == "A"]
    given = [found for found in rows if found.line]
    lines_out.append(
        f"  asked {len(rows):,}: a line {len(given):,}, 'no line fits' {sum(1 for f in rows if f.line == ''):,}, "
        f"refused or not answered {sum(1 for f in rows if f.line is None):,}"
    )
    if not given:
        return lines_out
    same = Counter()
    by_department: dict[str, Counter] = {}
    disagreements = []
    for found in given:
        shop, ai = levels(found.picked.shelf_now), levels(found.line or "")
        department = found.picked.shelf_now.split(" > ")[0]
        tally = by_department.setdefault(department, Counter())
        tally["asked"] += 1
        for depth in (1, 2, 3):
            if shop[:depth] == ai[:depth] and len(shop) >= depth and len(ai) >= depth:
                same[depth] += 1
        if shop[:2] == ai[:2]:
            tally["same category"] += 1
        else:
            disagreements.append(found)
        if shop == ai:
            same["line"] += 1
        elif shop[: len(ai)] == ai:
            same["shallower"] += 1
        elif ai[: len(shop)] == shop:
            same["deeper"] += 1
    total = len(given)
    lines_out += [
        f"  the same department (first level): {_share(same[1], total)}",
        f"  the same category (first two levels, the cap's): {_share(same[2], total)}",
        f"  the same three levels: {_share(same[3], total)}",
        f"  the same line: {_share(same['line'], total)}",
        f"  on the shop's path, shallower: {same['shallower']:,}; deeper: {same['deeper']:,}",
        "  each department, the same category:",
    ]
    for department, tally in sorted(by_department.items(), key=lambda item: -item[1]["asked"]):
        lines_out.append(f"    {_share(tally['same category'], tally['asked'])}  {department}")
    lines_out.append(f"  another category than the shop's, {min(len(disagreements), LISTED['A'])} of {len(disagreements)}:")
    for found in disagreements[: LISTED["A"]]:
        lines_out.append(f"    {_short(found.picked.shop, 24)} | {_short(found.picked.title)}")
        lines_out.append(f"        the shop: {found.picked.shelf_now}")
        lines_out.append(f"        the AI:   {found.line}")
    return lines_out


def report_b(answered: Sequence[Answered]) -> list[str]:
    """The AI's line against the shelf the second link's product has now."""
    from picwise_ai.shelves import levels

    lines_out = ["== B: the second link's products on a broad shelf: the shelf now and the AI's line"]
    rows = [found for found in answered if found.picked.half == "B"]
    given = [found for found in rows if found.line]
    lines_out.append(
        f"  asked {len(rows):,}: a line {len(given):,}, 'no line fits' {sum(1 for f in rows if f.line == ''):,}, "
        f"refused or not answered {sum(1 for f in rows if f.line is None):,}"
    )
    if not given:
        return lines_out
    tally: Counter[str] = Counter()
    for found in given:
        now, ai = levels(found.picked.shelf_now), levels(found.line or "")
        if not now or now[0] != ai[0]:
            tally["other department"] += 1
        elif ai == now:
            tally["same"] += 1
        elif ai[: len(now)] == now:
            tally["deeper"] += 1
        elif now[: len(ai)] == ai:
            tally["shallower"] += 1
        else:
            tally["same department, another branch"] += 1
    depth_now = statistics.mean(len(levels(found.picked.shelf_now)) for found in given)
    depth_ai = statistics.mean(len(levels(found.line or "")) for found in given)
    shops = Counter(found.picked.shop for found in rows)
    lines_out += [
        f"  deeper on the same path: {_share(tally['deeper'], len(given))}",
        f"  the same line: {_share(tally['same'], len(given))}",
        f"  shallower on the same path: {_share(tally['shallower'], len(given))}",
        f"  the same department, another branch: {_share(tally['same department, another branch'], len(given))}",
        f"  another department (or none now): {_share(tally['other department'], len(given))}",
        f"  levels: now {depth_now:.1f} on average, the AI's {depth_ai:.1f}",
        f"  shops: {len(shops)}; the most products: " + ", ".join(f"{name} {count}" for name, count in shops.most_common(5)),
        f"  a sample, {min(len(given), LISTED['B'])} of {len(given)}:",
    ]
    for found in given[: LISTED["B"]]:
        lines_out.append(f"    {_short(found.picked.shop, 24)} | {_short(found.picked.title)}")
        lines_out.append(f"        the shop's words: {_short(found.picked.shop_words, 100)}")
        lines_out.append(f"        now: {found.picked.shelf_now or '(none)'}")
        lines_out.append(f"        the AI: {found.line}")
    return lines_out


def report_totals(totals: Totals, answered: Sequence[Answered], unasked: int, catalogue_size: int) -> list[str]:
    asked = len(answered)
    out = [
        f"== {asked:,} products asked in {totals.calls} calls ({unasked} calls left unasked by the budget); "
        f"calls with no answer: {totals.failed}" + (f" ({dict(totals.errors)})" if totals.errors else ""),
        f"  the model: {dict(totals.models)}",
        f"  cost ${totals.cost:.4f}: tokens read {totals.tokens_in:,}, written to the cache {totals.cache_written:,}, "
        f"read from it {totals.cache_read:,}, answered {totals.tokens_out:,}",
    ]
    if totals.seconds:
        out.append(f"  a call took {statistics.median(totals.seconds):.1f} s in the middle, {max(totals.seconds):.1f} s at most")
    if asked:
        each = totals.cost / asked
        out.append(f"  ${each:.6f} a product, ${1000 * each:.3f} for 1,000")
        out.append(
            f"  the catalogue's {catalogue_size:,} products at this price: about ${catalogue_size * each:,.2f}; "
            f"through the Batch API, half that: about ${catalogue_size * each / 2:,.2f}"
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue")
    parser.add_argument("--products", type=int, default=1000)
    parser.add_argument("--per-call", type=int, default=0)
    parser.add_argument("--budget", type=float, default=1.00)
    parser.add_argument("--seed", type=int, default=20261120)
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

    lines = taxonomy_lines()
    if not lines:
        print("no Google taxonomy file: nothing to ask")
        return 1
    began = time.monotonic()
    prepared = read_prepared_catalogue_to_measure(Path(args.catalogue))
    if prepared is None:
        print("the copy is not a prepared catalogue: nothing to ask")
        return 1
    products = prepared.products
    print(f"the catalogue prepared at {prepared.prepared_at.isoformat()}: {len(products):,} products, read in {time.monotonic() - began:.0f} s")
    chosen = pick(products, lines, total=args.products, seed=args.seed)
    halves = Counter(found.half for found in chosen)
    print(f"picked: A {halves['A']:,} (the first link, the shop's line hidden), B {halves['B']:,} (the second link, a broad shelf)")
    for half in ("A", "B"):
        for found in [found for found in chosen if found.half == half][:3]:
            print(f"  {half} | {_short(found.shop, 24)} | {_short(found.title)} | {found.shelf_now or '(none)'}")
    calls = batches(chosen, args.per_call or PER_CALL)
    sample = request_kwargs([found.item for found in calls[0]] if calls else [], lines)
    print(
        f"{len(calls)} calls; the cached part {sum(len(block['text']) for block in sample['system']):,} characters, "
        f"a call's products about {len(sample['messages'][0]['content']):,}"
    )
    if args.dry_run or not os.environ.get("ANTHROPIC_API_KEY"):
        print("not asked: " + ("--dry-run" if args.dry_run else "no ANTHROPIC_API_KEY"))
        return 0

    from picwise_ai.client import ask, make_client

    client = make_client(timeout=120.0, max_retries=2)
    answered, totals, unasked = run(calls, lines, ask_fn=lambda request: ask(request, client=client), budget=args.budget)
    for line in (*report_totals(totals, answered, unasked, len(products)), *report_a(answered), *report_b(answered)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
