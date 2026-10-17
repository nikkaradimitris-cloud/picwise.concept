"""Run 118 buyer searches through the real search on one Awin feed file.

The searches are in `tools/price_first_eval_cases.py`. For each, it says what the page
shows and how long it took.

    python -I tools/price_first_eval.py <feed.csv.gz> <out.json>
    python -I tools/price_first_eval.py <feed.csv.gz> <out.json> --cards
    python -I tools/price_first_eval.py <feed.csv.gz> <out.json> --compare <earlier.json>

Read-only: it reads the file and changes nothing. The feed is a file the owner downloads
from Awin and uploads; never its link, which holds the account's API key.

`--cards` prints the cards each page shows. `--compare` reads an earlier run and lists
the searches whose page changed (cards, prices, count) and the time per search before
and after: run it before a change that should only be faster, then after, on the same file.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import runpy
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_FILE = Path(__file__).resolve().with_name("price_first_eval_cases.py")


def _run(feed: Path) -> list[dict]:
    os.environ["AWIN_FEED_FILE"] = str(feed)
    os.environ.pop("AWIN_FEED_URL", None)
    for path in (str(ROOT), str(ROOT / "src")):
        if path not in sys.path:
            sys.path.insert(0, path)
    logging.disable(logging.WARNING)

    from picwise_providers.awin_adapter import awin_feed_config_from_env, load_awin_provider_feed
    from picwise_providers.search_selection import _product_concepts, _product_search_fields
    from picwise_search.live_search_resolver import resolve_live_search
    from picwise_surface import provider_feed_cards_will_render

    cases = runpy.run_path(str(CASES_FILE))["CASES"]
    by_id = {p.provider_product_id: p for p in load_awin_provider_feed(awin_feed_config_from_env()).products}
    rows = []
    for query, expected, style in cases:
        started = time.perf_counter()
        r = resolve_live_search(query)
        ms = (time.perf_counter() - started) * 1000
        rendered = bool(provider_feed_cards_will_render(r))
        cheapest = set(r.provider_feed_cheapest_product_ids or ())
        places = dict(r.provider_feed_price_ranks or ())
        shops = dict(r.provider_feed_shop_counts or ())
        shown = []
        for card in r.provider_feed_selected_products if rendered else ():
            product_id = card.get("provider_product_id")
            product = by_id.get(product_id)
            kinds = sorted(_product_concepts(product, _product_search_fields(product))) if product else []
            shown.append({
                "title": str(card.get("title", ""))[:90],
                "price": card.get("price_text"),
                "shop": card.get("merchant_name"),
                "kinds": kinds,
                "place": places.get(product_id),
                "shops": shops.get(product_id, 1),
                "recommended": product_id == r.provider_feed_recommended_product_id,
                "lowest": product_id in cheapest,
            })
        rows.append({
            "query": query, "expected": expected, "style": style, "ms": round(ms),
            "understood": r.understood_concept_id, "understood_name": r.understood_concept_name,
            "by_correction": r.understood_by_correction, "did_you_mean": list(r.did_you_mean),
            "state": r.resolver_state, "selection": r.provider_feed_selection_status,
            "price_first": r.provider_feed_price_first, "total": r.provider_feed_total_count,
            "decision": r.provider_feed_decision_status,
            "unmatched": list(r.provider_feed_unmatched_query_terms),
            "partial": [list(terms) for terms in r.provider_feed_partially_matched_terms],
            "rendered": rendered, "shown": shown,
        })
        page = f"{len(shown)} of {r.provider_feed_total_count}" if rendered else (
            r.provider_feed_selection_status or r.resolver_state)
        print(f"{ms:7.0f} ms  {query!r:40} -> {r.understood_concept_id} {page}", flush=True)
    return rows


def _print_cards(row: dict) -> None:
    for card in row["shown"]:
        mark = "R" if card["recommended"] else ("L" if card["lowest"] else " ")
        print(f"     {mark} {card['price']:>10}  {card['title'][:70]}  ({card['shop']})")


def _summary(rows: list[dict]) -> None:
    rendered = [row for row in rows if row["rendered"]]
    recommended = [row for row in rendered if any(card["recommended"] for card in row["shown"])]
    times = [row["ms"] for row in rows[1:]] or [row["ms"] for row in rows]
    print(f"\n{len(rows)} searches: {len(rendered)} pages with products "
          f"({sum(1 for row in rendered if row['price_first'])} price first), "
          f"{len(recommended)} with a Recommended, {len(rows) - len(rendered)} without products")
    print(f"time per search: first {rows[0]['ms'] if rows else 0} ms (loads the feed), "
          f"then median {statistics.median(times) if times else 0:.0f} ms, max {max(times, default=0)} ms")
    empty = [row["query"] for row in rows if not row["rendered"]]
    if empty:
        print("without products:", ", ".join(repr(query) for query in empty))


def _page(row: dict) -> tuple:
    return (row["total"], tuple((card["title"], card["price"], card["recommended"]) for card in row["shown"]))


def _compare(rows: list[dict], earlier_path: Path) -> None:
    earlier = {row["query"]: row for row in json.loads(earlier_path.read_text(encoding="utf-8"))}
    changed = [row for row in rows if row["query"] in earlier and _page(row) != _page(earlier[row["query"]])]
    print(f"\ncompared with {earlier_path}: {len(changed)} of {len(rows)} pages changed")
    for row in changed:
        before = earlier[row["query"]]
        print(f"\n  {row['query']!r}: {before['total']} -> {row['total']} products")
        print("   before:")
        _print_cards(before)
        print("   after:")
        _print_cards(row)
    before_times = [earlier[row["query"]]["ms"] for row in rows[1:] if row["query"] in earlier]
    after_times = [row["ms"] for row in rows[1:] if row["query"] in earlier]
    if before_times and after_times:
        print(f"\nmedian time per search: before {statistics.median(before_times):.0f} ms, "
              f"after {statistics.median(after_times):.0f} ms")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("feed", type=Path, help="the Awin feed file (.csv.gz)")
    parser.add_argument("out", type=Path, help="where to write what each search showed (JSON)")
    parser.add_argument("--cards", action="store_true", help="print the cards each page shows")
    parser.add_argument("--compare", type=Path, help="an earlier out.json to compare with")
    args = parser.parse_args(argv)
    if not args.feed.is_file():
        parser.error(f"no feed file at {args.feed}")

    rows = _run(args.feed.resolve())
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.cards:
        for row in rows:
            print(f"\n{row['query']!r} -> {row['understood']} ({row['total']} products)")
            _print_cards(row)
    _summary(rows)
    if args.compare:
        _compare(rows, args.compare)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
