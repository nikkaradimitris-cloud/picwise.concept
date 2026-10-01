"""Check a real Awin product feed before (or after) pointing the site at it.

    python tools/check_awin_feed.py --url "<Awin Create-a-Feed download link>"
    python tools/check_awin_feed.py --file feed.csv.gz
    python tools/check_awin_feed.py            # uses AWIN_FEED_URL / AWIN_FEED_FILE

Reports what the site will actually be able to do with the feed:

- how many rows parse, how many products are card-eligible (in stock, priced, linked)
- which of Awin's columns are present, and which useful ones are missing
- merchants and currencies in the feed
- how many products PicWise recognises as a known kind of product, and the feed
  product types it does not recognise -- each one is a lexicon gap to review
- for the most common kinds, whether a search actually renders four choices

The download link contains the account's API key. It is never printed.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (SRC, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_USEFUL_COLUMNS = (
    "aw_product_id", "product_name", "aw_deep_link", "merchant_image_url", "search_price",
    "currency", "merchant_name", "brand_name", "category_name", "merchant_category",
    "product_type", "in_stock", "stock_status", "description", "keywords", "last_updated",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check an Awin product feed")
    parser.add_argument("--url", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--samples", type=int, default=15)
    args = parser.parse_args()
    if args.file:
        os.environ["AWIN_FEED_FILE"] = args.file
        os.environ.pop("AWIN_FEED_URL", None)
    elif args.url:
        os.environ["AWIN_FEED_URL"] = args.url
        os.environ.pop("AWIN_FEED_FILE", None)
    if not (os.environ.get("AWIN_FEED_FILE") or os.environ.get("AWIN_FEED_URL")):
        sys.exit("No feed: pass --url or --file, or set AWIN_FEED_URL / AWIN_FEED_FILE.")
    logging.disable(logging.WARNING)

    from picwise_nlu.concept_understanding import annotate_product_concepts
    from picwise_nlu.product_concepts import get_product_concepts_by_id
    from picwise_providers.awin_adapter import awin_feed_config_from_env, load_awin_provider_feed
    from picwise_providers.state import load_eligible_provider_feed_products
    from picwise_search.live_search_resolver import resolve_live_search
    from picwise_surface import provider_feed_cards_will_render

    started = time.perf_counter()
    config = awin_feed_config_from_env()
    parsed = load_awin_provider_feed(config)
    load_seconds = time.perf_counter() - started
    print(f"Feed status: {parsed.status}  ({load_seconds:.1f}s to download and parse)")
    if parsed.status != "provider_feed_loaded":
        print("  reasons:", ", ".join(parsed.reason_codes))
        sys.exit(1)
    if config.feed_file and os.path.exists(config.feed_file):
        print(f"  size on disk: {os.path.getsize(config.feed_file) / 1e6:.1f} MB")

    products = parsed.products
    columns: Counter[str] = Counter()
    for product in products[:500]:
        columns.update(key for key, value in (product.raw or {}).items() if str(value or "").strip())
    print(f"Rows parsed into products: {len(products)}")
    present = [name for name in _USEFUL_COLUMNS if columns.get(name)]
    missing = [name for name in _USEFUL_COLUMNS if not columns.get(name)]
    print("  useful columns present:", ", ".join(present) or "-")
    print("  useful columns missing:", ", ".join(missing) or "-")

    eligible = load_eligible_provider_feed_products(config)
    print(f"Card-eligible products: {len(eligible)} of {len(products)}")

    merchants = Counter(str((p.raw or {}).get("merchant_name") or "?") for p in products)
    currencies = Counter(str(p.currency or "?") for p in products)
    print("Merchants:", ", ".join(f"{name} ({count})" for name, count in merchants.most_common(10)))
    print("Currencies:", ", ".join(f"{name} ({count})" for name, count in currencies.most_common()))

    concept_counts: Counter[str] = Counter()
    unknown_types: Counter[str] = Counter()
    for product in eligible:
        raw = product.raw or {}
        product_type = str(raw.get("product_type") or "")
        category = str(raw.get("merchant_category") or raw.get("category_name") or product.category_text or "")
        concepts = annotate_product_concepts(product_type, category, str(product.title or ""))
        if concepts:
            concept_counts.update(concepts)
        else:
            unknown_types[(product_type or category or "(no type or category)").strip()] += 1
    recognised = len(eligible) - sum(unknown_types.values())
    share = recognised / len(eligible) * 100 if eligible else 0.0
    print(f"Recognised kind of product: {recognised} of {len(eligible)} eligible ({share:.0f}%)")
    print("  most common kinds:", ", ".join(f"{c} ({n})" for c, n in concept_counts.most_common(15)))
    if unknown_types:
        print("  feed types PicWise does not recognise (lexicon gaps to review):")
        for name, count in unknown_types.most_common(25):
            print(f"    {count:6d}  {name}")

    by_id = get_product_concepts_by_id()
    print(f"\nSample searches (most common kinds, one Greek and one English name each):")
    for concept_id, _count in concept_counts.most_common(args.samples):
        concept = by_id.get(concept_id)
        if concept is None:
            continue
        for query in (concept.greek[0] if concept.greek else "", concept.primary_english):
            if not query:
                continue
            started = time.perf_counter()
            resolution = resolve_live_search(query)
            elapsed = (time.perf_counter() - started) * 1000
            rendered = provider_feed_cards_will_render(resolution)
            note = "4 choices" if rendered else (resolution.provider_feed_selection_status or resolution.resolver_state)
            print(f"  {query!r:32s} -> {note}  ({elapsed:.0f} ms)")


if __name__ == "__main__":
    main()
