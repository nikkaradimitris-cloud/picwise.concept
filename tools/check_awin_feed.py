"""Check a real Awin product feed before (or after) pointing the site at it.

    python tools/check_awin_feed.py --url "<Awin Create-a-Feed download link>"
    python tools/check_awin_feed.py --file feed.csv.gz
    python tools/check_awin_feed.py            # uses AWIN_FEED_URL / AWIN_FEED_FILE

Reports what the site will actually be able to do with the feed:

- how many rows parse, how many products are card-eligible (in stock, priced, linked)
  and which merchants send no description, so are shown with a note saying so
- what each shop actually fills in, which is the choice the feed leaves its owner:
  Awin passes a merchant's own upload through, so a shop that sends no description or
  no specifications cannot be made to by any feed setting -- only by dropping it
- how many of its products can be found in a product database at all (a valid GTIN, or
  a brand with a real part code), which is the one column that decides whether a shop
  can ever be ranked on more than its price
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

# Every column PicWise reads, so a feed built without one is reported rather than
# quietly losing the check that needs it: `condition` decides whether a product is
# shown at all before the buyer asks for a non-new one, `ean`/`product_GTIN`/`mpn`
# make the same product from several merchants one product, and `is_for_sale`,
# `pre_order`, `valid_from`/`valid_to` keep offers that cannot be bought out.
_USEFUL_COLUMNS = (
    "aw_product_id", "product_name", "aw_deep_link", "merchant_image_url", "aw_image_url",
    "search_price", "currency", "merchant_name", "brand_name", "category_name",
    "merchant_category", "product_type", "in_stock", "stock_status", "description",
    "keywords", "last_updated", "condition", "ean", "product_GTIN", "mpn", "is_for_sale",
    "pre_order", "valid_from", "valid_to",
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
    from picwise_providers.product_condition import NEW_CONDITION_VALUES, stated_condition
    from picwise_providers.product_identity import read_product_identity
    from picwise_providers.product_description import (
        DESCRIPTION_MIN_CHARS,
        has_sufficient_description,
    )
    from picwise_providers.search_selection import product_non_new_condition
    from picwise_providers.offer_health import evaluate_product_eligibility
    from picwise_providers.state import (
        build_feed_availability_context,
        load_eligible_provider_feed_products,
    )
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

    # Two gates, and the tool used to report the first under the second's name. The
    # feed gate (`picwise_providers.eligibility`) decides whether a row became a
    # usable product at all; the card gate (`evaluate_product_eligibility`) decides
    # whether a search may show it, and it is the one that answers "what will the site
    # do with this feed". Everything below is counted over the products that can
    # actually be shown.
    feed_eligible = load_eligible_provider_feed_products(config)
    feed_ctx = build_feed_availability_context(feed_eligible)
    card_results = [
        (product, evaluate_product_eligibility(product, feed_ctx=feed_ctx))
        for product in feed_eligible
    ]
    eligible = [product for product, result in card_results if result.card_eligible]
    print(f"Feed-eligible products: {len(feed_eligible)} of {len(products)} rows")
    print(f"Card-eligible products (a search may show these): {len(eligible)}")
    blocked = Counter(
        code for _product, result in card_results if not result.card_eligible
        for code in result.reason_codes
    )
    for code, count in blocked.most_common(8):
        print(f"    {count:6d}  {code}")

    # Products without a description are shown with a note saying so (owner,
    # 2026-10-18; until then they were hidden). Reported per merchant because that is
    # the level the owner can act on -- a shop that describes nothing can be asked to
    # fill the column, or dropped from the feed.
    thin = Counter()
    per_merchant = Counter()
    for product in feed_eligible:
        merchant = " ".join(str((product.raw or {}).get("merchant_name") or "?").split())
        per_merchant[merchant] += 1
        if not has_sufficient_description(product.raw or {}, title=product.title):
            thin[merchant] += 1
    total_thin = sum(thin.values())
    print(
        f"No usable description (shown with a note, {DESCRIPTION_MIN_CHARS}+ characters count as one): "
        f"{total_thin} of {len(feed_eligible)} feed-eligible products"
    )
    for merchant, count in thin.most_common(8):
        share = count * 100 // max(1, per_merchant[merchant])
        note = " -- this shop describes nothing" if share == 100 else ""
        print(f"    {count:6d}  {merchant} ({share}% of its {per_merchant[merchant]} rows){note}")

    # Data quality per shop. Measured on 2026-10-12 after the owner asked whether the
    # thin feed was a Create-a-Feed setting: it is not. All 149 Awin columns were
    # present and `specifications` was filled by three shops (one at 100%), so the
    # columns a feed arrives with are a merchant's own upload, not a checkbox. Which
    # makes this table the decision the owner actually has: which shops to keep.
    # Owner decision, 2026-10-12: the feed is an offer source, not a product source,
    # so the question that decides whether a shop is usable is whether its products
    # can be found in a product database at all. A shop at 0% "known" can never be
    # enriched and so can never be ranked on anything but its price, whatever else it
    # sends -- which makes this column, not the description one, the shop-selection
    # criterion. "known" is a valid GTIN, or a brand with a real part code.
    quality_keys = (
        ("known", "__identity__"),
        ("desc", "description"),
        ("specs", "specifications"),
        ("type", "product_type"),
        ("brand", "brand_name"),
        ("gtin", "__gtin__"),
        ("rating", "average_rating"),
    )
    filled: dict[str, Counter] = {}
    for product in feed_eligible:
        raw = product.raw if isinstance(product.raw, dict) else {}
        merchant = " ".join(str(raw.get("merchant_name") or "?").split())
        counts = filled.setdefault(merchant, Counter())
        counts["rows"] += 1
        identity = read_product_identity(raw, brand=product.brand)
        counts["__identity__"] += identity.matchable
        counts["__gtin__"] += bool(identity.gtin)
        if has_sufficient_description(raw, title=product.title):
            counts["description"] += 1
        for _label, column in quality_keys:
            # `description` is counted above by the rule, not by the column being
            # filled, and the `__` keys are counted from the identity above.
            if column.startswith("__") or column == "description":
                continue
            value = " ".join(str(raw.get(column) or "").split())
            if value and not (column == "average_rating" and value in {"0", "0.0"}):
                counts[column] += 1
    known = sum(counts["__identity__"] for counts in filled.values())
    print(
        f"\nFindable in a product database (valid GTIN, or brand + part code): "
        f"{known} of {len(feed_eligible)} feed-eligible products"
    )
    print("What each shop actually sends (share of its own rows):")
    print(f"    {'shop':<26}{'rows':>6}" + "".join(f"{label:>8}" for label, _c in quality_keys))
    for merchant, counts in sorted(filled.items(), key=lambda item: -item[1]["rows"])[:15]:
        rows = counts["rows"]
        line = f"    {merchant[:25]:<26}{rows:>6}"
        line += "".join(f"{counts[column] * 100 // rows:>7}%" for _label, column in quality_keys)
        if not counts["__identity__"]:
            line += "  <- no identifier at all: can never be enriched"
        print(line)

    # Non-new stock, which is hidden unless a buyer asks for that condition (owner
    # decision, 2026-10-10). Worth knowing how much of the feed that is.
    non_new = Counter(
        words for words in (product_non_new_condition(product) for product in eligible) if words
    )
    total_non_new = sum(non_new.values())
    print(
        f"Not new (shown only when asked for): {total_non_new} of {len(eligible)} eligible"
    )
    if total_non_new:
        print(
            "  as the feed words it:",
            ", ".join(f"{words} ({count})" for words, count in non_new.most_common(10)),
        )
    # Condition values PicWise could read as neither "new" nor "not new". These are
    # shown as if new, so if any of them means used, the word belongs in
    # `picwise_providers.product_condition`.
    unread = Counter()
    for product in eligible:
        value = stated_condition(product.raw if isinstance(product.raw, dict) else {})
        comparable = " ".join(value.lower().replace("-", " ").replace("_", " ").split())
        if value and not product_non_new_condition(product) and comparable not in NEW_CONDITION_VALUES:
            unread[value] += 1
    if unread:
        print(
            "  condition values PicWise cannot read (shown as if new, report them):",
            ", ".join(f"{value} ({count})" for value, count in unread.most_common(10)),
        )

    # Ratings. The owner decided on 2026-10-11 that the recommendation should rest on
    # real ratings rather than price, which needs a feed that carries them: the first
    # one did not (127 rows of "0" out of 11,573, and a `reviews` column full of
    # colours). This is the line that says whether a new feed can carry that decision.
    rated = Counter()
    rating_rows = 0
    for product in eligible:
        raw = product.raw if isinstance(product.raw, dict) else {}
        for key in ("rating", "average_rating", "product_rating"):
            try:
                value = float(str(raw.get(key) or "").strip().replace(",", "."))
            except ValueError:
                continue
            if value > 0:
                rating_rows += 1
                rated[str(raw.get("merchant_name") or "?")] += 1
                break
    print(f"Products with a real rating: {rating_rows} of {len(eligible)} eligible")
    if rated:
        print(
            "  merchants that provide ratings:",
            ", ".join(f"{name} ({count})" for name, count in rated.most_common(10)),
        )
    else:
        print("  no merchant in this feed provides a usable rating (0 and empty do not count)")

    # The verdict, so a feed is judged in one glance rather than read as a table. The
    # criteria are the owner's, taken on 2026-10-12: a shop whose products cannot be
    # found in a product database can never be enriched and so can never be ranked on
    # anything but price, and is rejected until its data changes; and the decisive
    # question for the whole project is whether any shop sends a real rating at all.
    print("\nVERDICT")
    if rating_rows:
        shops_with_ratings = len(rated)
        print(
            f"  RATINGS FOUND: {rating_rows} products from {shops_with_ratings} shop(s). "
            "This feed can rank on the owner's first criterion."
        )
    else:
        print(
            "  NO RATINGS. No shop in this feed sends one, so nothing here can be "
            "ranked on the product's rating -- the owner's first criterion."
        )
    # A shop is kept when its products can be judged, by either route: it sends the
    # specifications itself, or it sends an identifier so a product database can. The
    # first draft of this rule failed 4x4 Predator for being only 42% findable while
    # it sends specifications on 79% of its rows -- a shop that already carries what
    # the database would have supplied does not need the database.
    keep, reject = [], []
    for merchant, counts in filled.items():
        rows = counts["rows"]
        findable = counts["__identity__"] * 100 // rows
        described = counts["description"] * 100 // rows
        specified = counts["specifications"] * 100 // rows
        judgeable = findable >= 50 or specified >= 50
        (keep if judgeable and described >= 50 else reject).append(
            (merchant, rows, findable, described, specified)
        )
    for label, rows_of in (("KEEP", keep), ("REJECT (temporarily)", reject)):
        rows_of.sort(key=lambda row: -row[1])
        total = sum(row[1] for row in rows_of)
        print(f"  {label}: {len(rows_of)} shops, {total} products")
        for merchant, rows, findable, described, specified in rows_of[:12]:
            why = []
            if findable < 50 and specified < 50:
                why.append(
                    f"{findable}% findable in a product database and {specified}% "
                    "send their own specifications"
                )
            if described < 50:
                why.append(f"only {described}% described")
            note = f"  -- {', '.join(why)}" if why else ""
            print(f"      {rows:6d}  {merchant[:34]}{note}")

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
