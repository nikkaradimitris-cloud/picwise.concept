"""The trial of the manufacturers' file: 200 brands of a copy of the server's catalogue.

Owner, 2026-11-20: the manufacturers' file must hold many thousands of manufacturers and
what each makes, so that the search suggests («για τον κάθε ένα πρέπει να ξέρουμε τι
κατασκευάζει έτσι ώστε να προτείνουμε»); asked how, «Από το AI, με δοκιμή πρώτα»: a trial
on 200 brands, under $1, its accuracy and cost shown to the owner before the whole.
Claude Haiku 5.5 says of each brand whether it is a maker's, a shop's own name or unknown,
the kinds of PicWise's list it makes, and up to five products the list has no kind for
(`picwise_ai.manufacturers`); the code checks every answer against the list.

The brands: the owner's examples first (Dyson, Samsung...), then the largest of the
catalogue, then brands spread over the rest by size, each with up to three of its
products' titles. Printed: the cost, the tokens and the time, and what 10,000 brands would
cost; how many were makers, shops and unknown; how often the AI's kinds hold the kind the
catalogue sells most of the brand (the AI's kinds may be more: a maker makes what our shops
do not sell); the brands the catalogue finds to be a shop's own name, and what the AI says
of them; the owner's examples whole, and a sample. Nothing on the server or the site
changes.

    python3 deployment/server/measure_manufacturers.py CATALOGUE.json.gz [--brands 200] \
        [--per-call 40] [--budget 1.00] [--dry-run]

The AI is asked only with `ANTHROPIC_API_KEY` set and without `--dry-run`. It stops asking
before a call would pass `--budget` dollars. The repository and its logs are public: brands,
kinds and titles are printed, never a link, a description or the key.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The owner's examples, and brands a buyer would type, first; asked whether the catalogue
# holds them or not (the file is to hold makers our shops do not sell: «No Dyson vacuum
# cleaner in our shops right now»).
EXAMPLES = (
    "Dyson", "Samsung", "Apple", "Nike", "Bosch", "Canon", "HP", "LEGO", "Philips", "Sony",
    "Miele", "Shark", "Ninja", "Nespresso", "Le Creuset",
)
# The largest of the catalogue, after the examples; then the rest spread by size.
LARGEST = 100
TITLE = 70
LISTED = 40


@dataclass
class Asked:
    key: str
    name: str
    products: int
    # The catalogue's kinds of it, the most first (`brand_list.CatalogueBrand.kinds`).
    kinds: tuple[tuple[str, int], ...]
    titles: tuple[str, ...]
    # Most of its products sold by a shop of its own name.
    shops_own: bool
    status: str = ""
    ai_kinds: tuple[str, ...] = ()
    others: tuple[str, ...] = ()


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


def _short(text: Any, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def pick(prepared: Any, total: int) -> list[Asked]:
    """`total` brands (module docstring): the examples, the catalogue's largest, then its
    others spread by size; each with up to three titles of its products, of different kinds
    where it has them, its main products' before its parts and accessories'. An example the
    catalogue does not hold is asked by its name alone."""
    from picwise_ai.manufacturers import TITLES
    from picwise_nlu.concept_understanding import ACCESSORY_MARKER, UNCERTAIN_MARKER
    from picwise_providers.brand_list import brand_key, build_brand_list, mend_letters
    from picwise_providers.catalogue_balance import _narrowest_kind
    from picwise_providers.normalization import extract_merchant_name

    brands = build_brand_list(prepared.products, prepared.kinds)
    by_key = {brand.key: brand for brand in brands}
    examples = {brand_key(name): name for name in EXAMPLES}
    order: list[str] = list(examples)
    for brand in brands[:LARGEST]:
        if brand.key not in order:
            order.append(brand.key)
    rest = [brand.key for brand in brands if brand.key not in order]
    room = max(0, total - len(order))
    if rest and room:
        step = max(1, len(rest) // room)
        order.extend(rest[::step][:room])
    order = order[:total]
    chosen = set(order)
    # A few of each brand's products, (title, kind): its main ones, its parts and accessories.
    found: dict[str, tuple[list[tuple[str, str]], list[tuple[str, str]]]] = {key: ([], []) for key in order}
    own_shop: Counter = Counter()
    keys: dict[str, str] = {}
    shop_keys: dict[str, str] = {}
    for product, kinds in zip(prepared.products, prepared.kinds):
        written = " ".join(str(product.brand or "").split())
        if not written:
            continue
        key = keys.get(written)
        if key is None:
            key = keys[written] = brand_key(mend_letters(written))
        if key not in chosen:
            continue
        raw = product.raw if hasattr(product.raw, "get") else {}
        shop = " ".join(str(extract_merchant_name(raw) or "").split())
        shop_key = shop_keys.get(shop)
        if shop_key is None:
            shop_key = shop_keys[shop] = brand_key(mend_letters(shop))
        if shop_key == key:
            own_shop[key] += 1
        main, parts = found[key]
        kinds = frozenset(kinds)
        side, most = (parts, TITLES) if kinds & {ACCESSORY_MARKER, UNCERTAIN_MARKER} else (main, 4 * TITLES)
        if len(side) < most:
            side.append((_short(product.title, 90), _narrowest_kind(kinds) or "-"))
    asked: list[Asked] = []
    for key in order:
        brand = by_key.get(key)
        main, parts = found[key]
        asked.append(
            Asked(
                key=key,
                name=brand.name if brand else examples.get(key, key),
                products=brand.products if brand else 0,
                kinds=brand.kinds if brand else (),
                titles=shown_titles(main, parts, TITLES),
                shops_own=bool(brand) and own_shop[key] * 2 > brand.products,
            )
        )
    return asked


def shown_titles(main: Sequence[tuple[str, str]], parts: Sequence[tuple[str, str]], most: int) -> tuple[str, ...]:
    """The titles the AI reads of a brand: its main products of different kinds first, then
    its other main products, then its parts and accessories."""
    titles: list[str] = []
    seen: set[str] = set()
    for title, kind in main:
        if kind not in seen:
            seen.add(kind)
            titles.append(title)
    for title, _kind in (*main, *parts):
        if title not in titles:
            titles.append(title)
    return tuple(titles[:most])


def run(
    chosen: Sequence[Asked], *, per_call: int, ask_fn: Callable[[dict[str, Any]], Any], budget: float
) -> tuple[Totals, int]:
    """Ask each call while the budget allows the next; the answers are written into the
    brands. The totals, and how many calls were left unasked."""
    from picwise_ai.manufacturers import checked_brands, kinds_list, request_kwargs

    kinds = kinds_list()
    calls = [list(chosen[i : i + per_call]) for i in range(0, len(chosen), per_call)]
    totals = Totals()
    for position, items in enumerate(calls):
        # The next call's cost, guessed high: half again the dearest so far, before any
        # answer two cents.
        if totals.cost + (1.5 * totals.most if totals.calls else 0.02) > budget:
            return totals, len(calls) - position
        asked = ask_fn(request_kwargs([{"name": item.name, "titles": item.titles} for item in items], kinds))
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
        found = checked_brands(asked.answer, len(items), kinds)
        for number, item in enumerate(items, 1):
            if number in found:
                item.status, item.ai_kinds, item.others = found[number]
        print(
            f"call {totals.calls}: {len(found)} of {len(items)} answered"
            + (f" ({asked.error})" if asked.error else "")
            + f"; {asked.seconds:.1f} s; ${asked.cost_usd:.5f}; ${totals.cost:.4f} in all"
        )
    return totals, 0


def _share(part: int, whole: int) -> str:
    return f"{part:,} of {whole:,} ({100 * part / whole:.1f}%)" if whole else f"{part:,} of 0"


def _names(kinds: Sequence[str], most: int = 6) -> str:
    from picwise_nlu.product_concepts import get_product_concepts_by_id

    by_id = get_product_concepts_by_id()
    shown = [by_id[kind].primary_english if kind in by_id else kind for kind in kinds[:most]]
    if len(kinds) > most:
        shown.append(f"+{len(kinds) - most} more")
    return ", ".join(shown) or "none"


def _related(left: str, right: str) -> bool:
    from picwise_nlu.product_concepts import broader_concepts

    return left == right or left in broader_concepts(right) or right in broader_concepts(left)


def report(chosen: Sequence[Asked], totals: Totals, unasked: int) -> list[str]:
    answered = [item for item in chosen if item.status]
    out = [
        f"== {len(chosen):,} brands, {len(answered):,} answered in {totals.calls} calls "
        f"({unasked} calls left unasked by the budget); calls with no answer: {totals.failed}"
        + (f" ({dict(totals.errors)})" if totals.errors else ""),
        f"  the model: {dict(totals.models)}",
        f"  cost ${totals.cost:.4f}: tokens read {totals.tokens_in:,}, written to the cache {totals.cache_written:,}, "
        f"read from it {totals.cache_read:,}, answered {totals.tokens_out:,}",
    ]
    if totals.seconds:
        out.append(f"  a call took {statistics.median(totals.seconds):.1f} s in the middle, {max(totals.seconds):.1f} s at most")
    if answered:
        each = totals.cost / len(answered)
        out.append(
            f"  ${each:.5f} a brand: 10,000 brands about ${10_000 * each:,.2f}; through the Batch API, half that"
        )
    statuses = Counter(item.status for item in answered)
    out.append(
        f"== what the AI says they are: maker {statuses['maker']:,}, a shop's own name {statuses['shop']:,}, "
        f"unknown {statuses['unknown']:,}"
    )
    makers = [item for item in answered if item.status == "maker"]
    if makers:
        kinds_each = [len(item.ai_kinds) for item in makers]
        out.append(
            f"  a maker's kinds: {statistics.median(kinds_each):.0f} in the middle, {max(kinds_each)} at most; "
            f"with products the list has no kind for: {sum(1 for item in makers if item.others):,}"
        )
    # Against the catalogue: the kind it sells most of the brand.
    with_kind = [item for item in makers if item.kinds and item.kinds[0][1] >= 3]
    holding = [item for item in with_kind if any(_related(kind, item.kinds[0][0]) for kind in item.ai_kinds)]
    out.append(
        "== against the catalogue: of the makers whose largest kind here is of 3 products or more, "
        f"the AI's kinds hold it (or a broader or narrower kind) for {_share(len(holding), len(with_kind))}"
    )
    missing = [item for item in with_kind if item not in holding]
    if missing:
        out.append(f"  not held, the {min(LISTED, len(missing))} largest:")
        for item in sorted(missing, key=lambda each: -each.products)[:LISTED]:
            ours = ", ".join(f"{kind} {count}" for kind, count in item.kinds[:3])
            out.append(f"    {_short(item.name, 30)} ({item.products:,}): here {ours} | AI {_names(item.ai_kinds)}")
    shops = [item for item in answered if item.shops_own]
    if shops:
        said = Counter(item.status for item in shops)
        out.append(
            f"== the brands the catalogue finds to be a shop's own name (most of its products from a shop of that "
            f"name): {len(shops):,}; the AI: maker {said['maker']}, shop {said['shop']}, unknown {said['unknown']}"
        )
    unknown = [item for item in answered if item.status == "unknown"]
    if unknown:
        out.append(f"== unknown to the AI: {len(unknown):,}; the largest: "
                   + ", ".join(f"{_short(item.name, 30)} ({item.products:,})" for item in unknown[:20]))
    out.append("== the owner's examples and brands a buyer would type (0 here: not in our shops)")
    from picwise_providers.brand_list import brand_key

    examples = {brand_key(name) for name in EXAMPLES}
    for item in chosen:
        if item.key in examples:
            out.append(
                f"  {item.name} ({item.products:,} here: {', '.join(f'{kind} {count}' for kind, count in item.kinds[:3]) or 'no kind'}): "
                f"{item.status or 'not answered'}; makes {_names(item.ai_kinds, 12)}"
                + (f"; and {', '.join(item.others)}" if item.others else "")
            )
    out.append(f"== a sample of {min(LISTED, len(answered))}, spread over the brands asked")
    step = max(1, len(answered) // LISTED)
    for item in answered[::step][:LISTED]:
        ours = ", ".join(f"{kind} {count}" for kind, count in item.kinds[:2]) or "no kind"
        out.append(
            f"  {_short(item.name, 28)} ({item.products:,}; here {ours}): {item.status}; {_names(item.ai_kinds, 5)}"
            + (f" | others: {', '.join(item.others[:3])}" if item.others else "")
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue")
    parser.add_argument("--brands", type=int, default=200)
    parser.add_argument("--per-call", type=int, default=0)
    parser.add_argument("--budget", type=float, default=1.00)
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

    from picwise_ai.manufacturers import PER_CALL, kinds_list, request_kwargs
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    began = time.monotonic()
    prepared = read_prepared_catalogue_to_measure(Path(args.catalogue))
    if prepared is None:
        print("the copy is not a prepared catalogue: nothing to ask")
        return 1
    print(
        f"the catalogue prepared at {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products, "
        f"read in {time.monotonic() - began:.0f} s"
    )
    chosen = pick(prepared, args.brands)
    print(f"picked {len(chosen):,} brands; PicWise's kinds: {len(kinds_list())}")
    for item in chosen[:5]:
        print(f"  {_short(item.name, 30)} ({item.products:,}) | {' ; '.join(item.titles)}")
    per_call = args.per_call or PER_CALL
    sample = request_kwargs([{"name": item.name, "titles": item.titles} for item in chosen[:per_call]])
    print(
        f"{-(-len(chosen) // per_call)} calls; the cached part {sum(len(block['text']) for block in sample['system']):,} "
        f"characters, a call's brands about {len(sample['messages'][0]['content']):,}"
    )
    if args.dry_run or not os.environ.get("ANTHROPIC_API_KEY"):
        print("not asked: " + ("--dry-run" if args.dry_run else "no ANTHROPIC_API_KEY"))
        return 0

    from picwise_ai.client import ask, make_client

    client = make_client(timeout=120.0, max_retries=2)
    totals, unasked = run(
        chosen, per_call=per_call, ask_fn=lambda request: ask(request, client=client), budget=args.budget
    )
    for line in report(chosen, totals, unasked):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
