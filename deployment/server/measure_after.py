"""The measure after the AI's shelves: the first 12 cards of fixed searches, judged.

Owner, 2026-11-20: «Δεν με ενδιαφέρει η μέτρηση πριν και μετά το ai με ενδιαφέρει η μέτρηση
μόνο μετά». A catalogue prepared with the AI's shelves (`picwise_providers.ai_shelves`, its
answers in `PICWISE_AI_SHELVES_FILE`) is answered as the site answers it: the prepared
file and its kinds, the gone photos, the offers and the families' answers when given. Each
search's first 12 cards are judged by Claude Haiku 5.5 (`audit_search.KIND_PROMPT`: is it
the thing the buyer asked for, not a part, an accessory or something else) for the kind
the search is read as. Printed, and kept as GitHub's notes (`scan_shelves.Notices`): the
cards right and wrong in all, by link (first, second) and by shop; then each search, its
wrong cards named. Nothing on the server or the site changes.

    python3 deployment/server/measure_after.py CATALOGUE.json.gz [--gone GONE.json] \
        [--offers OFFERS.json] [--families FAMILIES.json] [--budget 0.50] [--dry-run]

Titles, shops and prices are printed, never a link or the key. Always exits 0.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# The searches measured: the look-alikes the owner saw on 20/11 first, then the kinds most
# asked for in the UK, a few of each department.
SEARCHES = (
    "boots", "watches", "smartwatch", "kettle", "router", "car tyres", "monitor", "tv",
    "laptop", "tablet", "headphones", "speaker", "keyboard", "mouse", "printer", "camera",
    "phone charger", "smartphone", "toaster", "air fryer", "microwave", "washing machine",
    "vacuum cleaner", "drill", "sofa", "office chair", "desk", "mattress", "trainers",
    "jacket", "dress", "perfume", "shampoo", "dog bed", "lego", "backpack", "suitcase",
    "sunglasses", "earrings", "necklace",
)
CARDS = 12
SECOND_KEYS = ("merchant_id", "aw_product_id")
TITLE = 70
# What the kinds' lists took away: the kinds that lost the most, and the AI's lines named.
TAKEN_KINDS = 15
TAKEN_LINES = 2
# The products judged to see whether real ones are hidden: so many of each of the kinds
# that lost the most, and so many from the other kinds together.
SAMPLE_KINDS = 30
SAMPLE_A_KIND = 10
SAMPLE_REST = 60
HIDDEN_EXAMPLES = 12


def _short(text: Any, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


@dataclass
class Card:
    product_id: str
    title: str
    shop: str
    price: str
    second: bool
    verdict: str = ""


@dataclass
class Searched:
    query: str
    kind: str
    total: int
    cards: list[Card] = field(default_factory=list)
    error: str = ""


def _setup(catalogue: Path, gone: str, offers: str, families: str) -> None:
    """The site's settings, as `picwise-web.service` sets them, for this process."""
    for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "AWIN_FEED_URL_AWIN", "AWIN_FEED_FILE_AWIN",
                 "PICWISE_PURCHASABILITY_CACHE_FILE", "PICWISE_GONE_PHOTOS_FILE", "PICWISE_OFFERS_FILE",
                 "PICWISE_FAMILIES_FILE"):
        os.environ.pop(name, None)
    os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(catalogue.resolve())
    os.environ["PICWISE_PREPARED_MAX_AGE_HOURS"] = "100000"
    for option, name in ((gone, "PICWISE_GONE_PHOTOS_FILE"), (offers, "PICWISE_OFFERS_FILE"),
                         (families, "PICWISE_FAMILIES_FILE")):
        if option and Path(option).is_file() and Path(option).stat().st_size:
            os.environ[name] = str(Path(option).resolve())


def search_all(queries: Sequence[str]) -> tuple[list[Searched], Any]:
    """Each search answered as the site answers it, its first cards; and the catalogue the
    site read, for the cards' titles and shops."""
    from picwise_nlu.concept_understanding import understand_product_query
    from picwise_providers import state
    from picwise_providers.catalogue_cap import shop_of
    from picwise_search import resolve_live_search

    found: list[Searched] = []
    by_id: dict[str, Any] = {}
    prepared = None
    for query in queries:
        kind = str(understand_product_query(query).concept_id or "")
        try:
            resolution = resolve_live_search(query, shown=CARDS)
        except Exception as error:  # a measure only
            found.append(Searched(query, kind, 0, error=type(error).__name__))
            continue
        if prepared is None:
            prepared = state._PREPARED_STATE.get("prepared")
            if prepared is not None:
                by_id = {str(product.provider_product_id): product for product in prepared.products}
        products = list(resolution.provider_feed_selected_products) + list(resolution.provider_feed_more_products)
        searched = Searched(query, kind, int(resolution.provider_feed_total_count or len(products)))
        for shown in products[:CARDS]:
            product_id = str(shown.get("provider_product_id") or "")
            product = by_id.get(product_id)
            raw = product.raw if product is not None and hasattr(product.raw, "get") else {}
            searched.cards.append(
                Card(
                    product_id=product_id,
                    title=str(getattr(product, "title", "") or shown.get("title") or ""),
                    shop=shop_of(product) if product is not None else "",
                    price=str(getattr(product, "price_text", "") or ""),
                    second=any(str(raw.get(key) or "").strip() for key in SECOND_KEYS),
                )
            )
        found.append(searched)
    return found, prepared


def judge(found: list[Searched], prepared: Any, ask: Callable[[dict[str, Any]], Any] | None, budget: float) -> float:
    """Each search's cards judged for the kind it is read as; the cost."""
    import audit_search
    from picwise_nlu.product_concepts import get_product_concepts

    names = {concept.concept_id: (concept.english[0] if concept.english else concept.concept_id)
             for concept in get_product_concepts()}
    index = {str(product.provider_product_id): i for i, product in enumerate(prepared.products)} if prepared else {}
    fields = prepared.search_fields if prepared is not None else ()
    spent = [0.0]

    def one(searched: Searched) -> None:
        rows = []
        for card in searched.cards:
            i = index.get(card.product_id)
            if i is None:
                continue
            rows.append((card, prepared.products[i], fields[i] if fields else {}))
        if not rows or ask is None or spent[0] >= budget:
            return
        name = names.get(searched.kind, searched.kind.replace("_", " ")) or searched.query
        asked_for = f'"{searched.query}" (a {name})' if name.lower() != searched.query.lower() else f"a {name}"
        request = audit_search.kind_request(asked_for, [(product, product_fields) for _card, product, product_fields in rows])
        asked = ask(request)
        spent[0] += float(getattr(asked, "cost_usd", 0.0) or 0.0)
        for (card, _product, _fields), said in zip(rows, audit_search._answers(getattr(asked, "answer", None), len(rows), "answer")):
            card.verdict = said

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, found))
    return spent[0]


@dataclass
class Taken:
    """What the kinds' lists took away (`ai_shelves.checked_kinds`): per kind, the places of
    the products its type, shelf and title give it that the AI's line keeps out of it."""

    by_kind: dict[str, list[int]] = field(default_factory=dict)
    lines: dict[int, str] = field(default_factory=dict)
    products: int = 0
    left_with_none: int = 0
    with_kind: int = 0
    # Products whose AI line is one the model gave when it slipped (`ai_shelves.SLIP_LINES`).
    slips: int = 0


def taken_away(prepared: Any) -> Taken:
    from picwise_providers.ai_shelves import is_slip, line_of
    from picwise_providers.search_selection import kinds_before_the_kind_lists

    taken = Taken()
    for place, (product, fields, kinds) in enumerate(zip(prepared.products, prepared.search_fields, prepared.kinds)):
        taken.slips += is_slip(line_of(str(product.title or ""), str(product.brand or ""), product.raw))
        after = {kind for kind in kinds if not kind.startswith("__")}
        taken.with_kind += bool(after)
        before = {kind for kind in kinds_before_the_kind_lists(product, fields) if not kind.startswith("__")}
        lost = before - after
        if not lost:
            continue
        taken.products += 1
        taken.left_with_none += not after
        taken.lines[place] = str(line_of(str(product.title or ""), str(product.brand or ""), product.raw) or "")
        for kind in lost:
            taken.by_kind.setdefault(kind, []).append(place)
    return taken


def _last(line: str) -> str:
    return line.split(">")[-1].strip() or "(no line)"


def report_taken(prepared: Any, taken: Taken, top: int = TAKEN_KINDS) -> list[str]:
    """How many products the lists took out of a kind, and from which kinds the most, with
    the AI's lines they carry."""
    out = [
        f"products with a kind {taken.with_kind:,}; taken out of a kind by the lists {taken.products:,}"
        f" (left with no kind, so doubtful: {taken.left_with_none:,}); products whose AI line is one of the"
        f" tree's first five, given when the model slipped, read as no answer: {taken.slips:,}",
    ]
    ranked = sorted(taken.by_kind.items(), key=lambda item: -len(item[1]))
    rows = []
    for kind, places in ranked[:top]:
        lines = Counter(_last(taken.lines.get(place, "")) for place in places)
        example = _short(prepared.products[places[0]].title, 40)
        rows.append(
            f"{kind} {len(places):,} ("
            + ", ".join(f"{name} {count:,}" for name, count in lines.most_common(TAKEN_LINES))
            + f"; e.g. {example})"
        )
    out.append("the kinds that lost the most: " + "; ".join(rows))
    return out


def hidden_sample(taken: Taken, seed: int = 20261120) -> dict[str, list[int]]:
    """The products judged, per kind: up to `SAMPLE_A_KIND` of each kind that lost the most,
    and `SAMPLE_REST` from the other kinds together."""
    import random

    chooser = random.Random(seed)
    ranked = sorted(taken.by_kind.items(), key=lambda item: (-len(item[1]), item[0]))
    sample: dict[str, list[int]] = {}
    for kind, places in ranked[:SAMPLE_KINDS]:
        sample[kind] = sorted(chooser.sample(places, min(SAMPLE_A_KIND, len(places))))
    rest = [(kind, place) for kind, places in ranked[SAMPLE_KINDS:] for place in places]
    for kind, place in chooser.sample(rest, min(SAMPLE_REST, len(rest))):
        sample.setdefault(kind, []).append(place)
    return sample


def _spread(keys: list[tuple[str, int]], most: int, a_kind: int = 2) -> list[tuple[str, int]]:
    """At most `a_kind` of each kind, `most` in all."""
    counted: Counter[str] = Counter()
    found = []
    for kind, place in keys:
        if counted[kind] < a_kind and len(found) < most:
            counted[kind] += 1
            found.append((kind, place))
    return found


def hidden_check(
    prepared: Any, taken: Taken, ask: Callable[[dict[str, Any]], Any] | None, budget: float
) -> tuple[list[str], float]:
    """Whether real products are hidden: a sample of the products the lists took out of a
    kind, each judged by Claude Haiku 5.5 for that kind (`audit_search.KIND_PROMPT`); the
    share that is the kind itself, by kind, and over all the products taken, estimated
    kind by kind from the sample."""
    import audit_search
    from picwise_nlu.product_concepts import get_product_concepts

    if ask is None or not taken.products:
        return [f"not judged ({'no AI' if ask is None else 'nothing taken'})"], 0.0
    names = {concept.concept_id: (concept.english[0] if concept.english else concept.concept_id)
             for concept in get_product_concepts()}
    sample = hidden_sample(taken)
    fields = prepared.search_fields
    spent = [0.0]
    verdicts: dict[tuple[str, int], str] = {}

    def one(job: tuple[str, list[int]]) -> None:
        kind, places = job
        if spent[0] >= budget:
            return
        rows = [(prepared.products[place], fields[place]) for place in places]
        request = audit_search.kind_request(f"a {names.get(kind, kind.replace('_', ' '))}", rows)
        asked = ask(request)
        spent[0] += float(getattr(asked, "cost_usd", 0.0) or 0.0)
        for place, said in zip(places, audit_search._answers(getattr(asked, "answer", None), len(rows), "answer")):
            verdicts[(kind, place)] = said

    jobs = [(kind, places[start:start + 20]) for kind, places in sample.items() for start in range(0, len(places), 20)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, jobs))
    judged = {key: said for key, said in verdicts.items() if said in ("yes", "no")}
    real = [key for key, said in judged.items() if said == "yes"]
    # The kinds that lost the most, each by its own sample; the others by their sample together.
    ranked = sorted(taken.by_kind.items(), key=lambda item: (-len(item[1]), item[0]))
    largest = {kind for kind, _places in ranked[:SAMPLE_KINDS]}
    estimate = 0.0
    per_kind = []
    rest_said: list[str] = []
    rest_count = 0
    for kind, places in ranked:
        said = [judged[(kind, place)] for place in sample.get(kind, ()) if (kind, place) in judged]
        if kind in largest:
            if said:
                estimate += said.count("yes") / len(said) * len(places)
                per_kind.append(f"{kind} {said.count('yes')}/{len(said)}")
        else:
            rest_said += said
            rest_count += len(places)
    if rest_said:
        estimate += rest_said.count("yes") / len(rest_said) * rest_count
        per_kind.append(f"the other kinds together {rest_said.count('yes')}/{len(rest_said)}")
    total = sum(len(places) for places in taken.by_kind.values())
    out = [
        f"judged {len(judged):,} of the products the lists took out of a kind (a sample; unsure {len(verdicts) - len(judged)}):"
        f" really that kind {_share(len(real), len(judged))}",
        f"estimated over all {total:,} (product, kind) taken: about {estimate:,.0f} real ones hidden"
        f" ({100 * estimate / total:.1f}%)" if total else "nothing taken",
        "by kind (real of judged): " + "; ".join(per_kind),
        "real ones hidden, e.g.: " + "; ".join(
            f"{_short(prepared.products[place].title, 45)} ({kind}; {_last(taken.lines.get(place, ''))})"
            for kind, place in _spread(real, HIDDEN_EXAMPLES)
        ),
    ]
    return out, spent[0]


def _share(part: int, whole: int) -> str:
    return f"{part:,} of {whole:,} ({100 * part / whole:.1f}%)" if whole else f"{part:,} of 0"


def report(found: list[Searched]) -> tuple[list[str], list[str]]:
    """The totals, and each search with its wrong cards."""
    cards = [card for searched in found for card in searched.cards]
    judged = [card for card in cards if card.verdict in ("yes", "no")]
    wrong = [card for card in judged if card.verdict == "no"]
    by_link = {
        "first link": [card for card in judged if not card.second],
        "second link": [card for card in judged if card.second],
    }
    shops = Counter(card.shop or "(no shop)" for card in wrong)
    totals = [
        f"{len(found)} searches, {len(cards):,} cards (the first {CARDS} of each); judged {len(judged):,}"
        f" (unsure or not judged {len(cards) - len(judged):,})",
        f"right {_share(len(judged) - len(wrong), len(judged))}; wrong {len(wrong):,}",
        f"searches with no wrong card: {sum(1 for s in found if s.cards and not any(c.verdict == 'no' for c in s.cards))}"
        f" of {len(found)}; with no card: {sum(1 for s in found if not s.cards)}",
    ]
    for link, rows in by_link.items():
        bad = sum(1 for card in rows if card.verdict == "no")
        totals.append(f"{link}: {len(rows):,} cards judged, wrong {_share(bad, len(rows))}")
    if shops:
        totals.append("the most wrong cards: " + "; ".join(f"{shop} {count}" for shop, count in shops.most_common(8)))
    each = []
    for searched in found:
        if searched.error:
            each.append(f'"{searched.query}": the search failed ({searched.error})')
            continue
        bad = [card for card in searched.cards if card.verdict == "no"]
        right = sum(1 for card in searched.cards if card.verdict == "yes")
        line = f'"{searched.query}" ({searched.kind or "no kind"}, {searched.total:,} products): {right} right, {len(bad)} wrong of {len(searched.cards)}'
        if bad:
            line += " -- " + "; ".join(
                f"{_short(card.title, 55)} ({card.shop}, {'2nd' if card.second else '1st'})" for card in bad[:4]
            )
        each.append(line)
    return totals, each


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--gone", default="")
    parser.add_argument("--offers", default="")
    parser.add_argument("--families", default="")
    parser.add_argument("--budget", type=float, default=0.50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    for folder in (ROOT, ROOT / "src", HERE):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    from scan_shelves import Notices

    notices = Notices()
    began = time.monotonic()
    _setup(args.catalogue, args.gone, args.offers, args.families)
    try:
        found, prepared = search_all(SEARCHES)
    except Exception as error:  # a measure only
        notices.say("measure", f"the searches could not be run: {type(error).__name__}: {error}", final=True)
        return 0
    if prepared is None:
        notices.say("measure", "the site's catalogue was not read from the file (another code, or not a prepared file)", final=True)
        return 0
    print(f"the catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products; "
          f"{len(found)} searches in {time.monotonic() - began:.0f} s")
    ask = None
    if not args.dry_run and os.environ.get("ANTHROPIC_API_KEY"):
        from picwise_ai.client import ask as ask_one, make_client

        client = make_client(timeout=60.0, max_retries=4)
        ask = lambda request: ask_one(request, client=client)  # noqa: E731
    else:
        print("the AI: not asked (a dry run, or no key)")
    cost = judge(found, prepared, ask, args.budget)
    try:
        taken = taken_away(prepared)
        notices.say("after: what the kinds' lists took away", "\n".join(report_taken(prepared, taken)), final=True)
        hidden, hidden_cost = hidden_check(prepared, taken, ask, args.budget)
        cost += hidden_cost
        notices.say("after: real products hidden?", "\n".join(hidden), final=True)
    except Exception as error:  # a measure only
        print(f"the lists' count failed: {type(error).__name__}: {error}")
    totals, each = report(found)
    totals.append(f"the judging cost ${cost:.4f}")
    notices.say("after: in all", "\n".join(totals), final=True)
    half = (len(each) + 1) // 2
    notices.say("after: each search (1)", "\n".join(each[:half]), final=True)
    notices.say("after: each search (2)", "\n".join(each[half:]), final=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
