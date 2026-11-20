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


def doubted(prepared: Any, top: int = 15) -> list[str]:
    """What rule 2 took away (`ai_shelves.checked_kinds`): the products the catalogue holds
    as doubtful that the kind reader alone reads as a kind, by that kind. To see that the
    AI's line hides look-alikes, not the things themselves."""
    from picwise_nlu.concept_understanding import UNCERTAIN_MARKER, annotate_product_concepts
    from picwise_providers.search_selection import product_kind_key

    fields = prepared.search_fields
    if not fields or not prepared.kinds:
        return ["rule 2: the catalogue keeps no kinds or fields to read"]
    lost: Counter[str] = Counter()
    titles: dict[str, list[str]] = {}
    doubtful = with_kind = 0
    for product, product_fields, kinds in zip(prepared.products, fields, prepared.kinds):
        if kinds == frozenset({UNCERTAIN_MARKER}):
            doubtful += 1
            alone = annotate_product_concepts(*product_kind_key(product, product_fields))
            real = sorted(kind for kind in alone if not kind.startswith("__"))
            if real:
                head = real[0] if len(real) == 1 else min(real, key=len)
                lost[head] += 1
                titles.setdefault(head, [])
                if len(titles[head]) < 2:
                    titles[head].append(_short(product.title, 45))
        elif any(not kind.startswith("__") for kind in kinds):
            with_kind += 1
    out = [
        f"products with a kind {with_kind:,}; doubtful {doubtful:,}, of which the AI's line made doubtful "
        f"{sum(lost.values()):,} (read as a kind without it)",
        "the kinds that lost the most: " + "; ".join(
            f"{kind} {count:,} (e.g. {' / '.join(titles.get(kind, []))})" for kind, count in lost.most_common(top)
        ),
    ]
    return out


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
        notices.say("after: what the AI's line made doubtful", "\n".join(doubted(prepared)), final=True)
    except Exception as error:  # a measure only
        print(f"rule 2's count failed: {type(error).__name__}")
    totals, each = report(found)
    totals.append(f"the judging cost ${cost:.4f}")
    notices.say("after: in all", "\n".join(totals), final=True)
    half = (len(each) + 1) // 2
    notices.say("after: each search (1)", "\n".join(each[:half]), final=True)
    notices.say("after: each search (2)", "\n".join(each[half:]), final=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
