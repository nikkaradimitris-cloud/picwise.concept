"""Which kinds a title alone reads right at least 99% of the time, and how many of the
rows held for want of a category those kinds would bring in: measured only.

    python3 deployment/server/print_title_safety.py FEED [SHOP_CATALOGUES]

Owner, 2026-10-31: «Ναι, κάνε τη μέτρηση». About 500,000 of the feed's rows are held
because their shop sends no category (`missing_category_text`), and a search shows a
product only as the kind asked for (`PROJECT_RULES.md` §4). The owner's direction of
26/10 shows only what is mapped safely, and stopped showing such rows by their title;
put to them since, waiting for their word: "safe" as a number, a title's kind alone only
for the kinds it reads right 99% of the time on the rows that have a shelf. So, from
the feed the server prepared from and the bot's file of the shops' catalogues, judged
as the nightly preparation judges them (`state.resolve_provider_feed_pipeline`):

- per kind the title alone gives (its narrowest), on the rows a card can show whose
  type and shelf alone give a kind: how often the title agrees with the shelf (the same
  kind, a broader or a narrower one, as `kind_check.measure_title_alone` counts);
- of the rows held for want of a category alone, which a card could show by their title
  (`feed_intake`: every other check passed), the kind their title alone gives;
- the kinds at or over `SAFE` with at least `ENOUGH_ROWS` rows to tell by, what they would
  bring in and from which shops, the kinds under it, the kinds with too few rows to tell,
  and how many kinds would then have products from at least 3 shops.

Run by .github/workflows/server-cap.yml on GitHub's runner; nothing on the server or
shown changes. Counts, kinds, shop names and titles only, never a link. Always exits 0.
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path

# The owner's "safe", put to them on 26/10: right at least this often.
SAFE = 0.99
# Rows with a shelf a kind needs before its share is trusted.
ENOUGH_ROWS = 100
# Shops a kind needs to count as covered (owner, 2026-10-26).
COVERED = 3
LISTED = 25
TITLE_LENGTH = 70


def _cut(text: str) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= TITLE_LENGTH else text[: TITLE_LENGTH - 3] + "..."


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: print_title_safety.py FEED [SHOP_CATALOGUES]")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    # The feed and the shops' types as the preparation reads them, never a prepared file.
    os.environ["AWIN_FEED_FILE"] = str(Path(argv[1]).resolve())
    os.environ.pop("PICWISE_PREPARED_CATALOGUE_FILE", None)
    if len(argv) == 3 and Path(argv[2]).is_file():
        os.environ["PICWISE_SHOP_CATALOGUES"] = str(Path(argv[2]).resolve())
    try:
        from picwise_nlu.concept_understanding import annotate_product_concepts
        from picwise_providers.awin_adapter import awin_feed_config_from_env
        from picwise_providers.catalogue_balance import NO_SHOP, _narrowest_kind
        from picwise_providers.feed_intake import _FEED_GATE_HOLDS, _hold_reasons, _way_without_category
        from picwise_providers.kind_check import _related
        from picwise_providers.normalization import extract_merchant_name
        from picwise_providers.search_selection import _product_concepts, _product_search_fields
        from picwise_providers.state import resolve_provider_feed_pipeline

        pipeline = resolve_provider_feed_pipeline(awin_feed_config_from_env(), include_graph_projection=False)
        if pipeline.feed_status.status != "provider_feed_ready":
            print(f"the feed could not be read: {pipeline.feed_status.status}")
            return 0

        def shop_of(product) -> str:
            raw = product.raw if isinstance(product.raw, Mapping) else {}
            return " ".join(str(extract_merchant_name(raw) or "").split()) or NO_SHOP

        def title_kind(product) -> tuple[str, frozenset[str]]:
            kinds = annotate_product_concepts("", "", str(product.title or ""))
            return _narrowest_kind(kinds), kinds

        rows = 0
        shown = 0
        # Per kind the title gives: rows with a shelf to tell by, and those agreeing.
        told: Counter = Counter()
        right: Counter = Counter()
        wrong_shelves: dict[str, Counter] = defaultdict(Counter)
        wrong_titles: dict[str, list[str]] = defaultdict(list)
        shown_shops: dict[str, set[str]] = defaultdict(set)
        held_buckets: Counter = Counter()
        held: Counter = Counter()
        held_shops: dict[str, Counter] = defaultdict(Counter)
        held_titles: dict[str, list[str]] = defaultdict(list)
        for row in pipeline.eligibility_results:
            rows += 1
            product = row.product
            raw = product.raw if isinstance(product.raw, Mapping) else {}
            if not _hold_reasons(row):
                shown += 1
                fields = _product_search_fields(product)
                kind = _narrowest_kind(_product_concepts(product, fields))
                if kind:
                    shown_shops[kind].add(shop_of(product))
                by_shelf = [
                    found
                    for found in annotate_product_concepts(fields["product_type"], fields["category"], "")
                    if not found.startswith("__")
                ]
                if not by_shelf:
                    continue
                said, kinds = title_kind(product)
                if not said:
                    continue
                told[said] += 1
                if _related(by_shelf, [found for found in kinds if not found.startswith("__")]):
                    right[said] += 1
                else:
                    wrong_shelves[said][_narrowest_kind(by_shelf)] += 1
                    if len(wrong_titles[said]) < 2:
                        wrong_titles[said].append(_cut(product.title))
                continue
            gate = {code for code in row.reason_codes if code in _FEED_GATE_HOLDS}
            if gate != {"missing_category_text"}:
                continue
            if _way_without_category(row, " ".join(str(raw.get("product_type") or "").split())) != "title":
                continue
            said, kinds = title_kind(product)
            if said:
                held_buckets["kind"] += 1
                held[said] += 1
                held_shops[said][shop_of(product)] += 1
                if len(held_titles[said]) < 2:
                    held_titles[said].append(_cut(product.title))
            elif "__accessory__" in kinds:
                held_buckets["accessory"] += 1
            elif any(found.startswith("__") for found in kinds):
                held_buckets["doubtful"] += 1
            else:
                held_buckets["none"] += 1
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the title's safety could not be measured: {type(error).__name__}")
        return 0

    def share(kind: str) -> float:
        return right[kind] / told[kind] if told[kind] else 0.0

    safe = sorted(
        (kind for kind in held if told[kind] >= ENOUGH_ROWS and share(kind) >= SAFE),
        key=lambda kind: (-held[kind], kind),
    )
    unsafe = sorted(
        (kind for kind in held if told[kind] >= ENOUGH_ROWS and share(kind) < SAFE),
        key=lambda kind: (-held[kind], kind),
    )
    untold = sorted((kind for kind in held if told[kind] < ENOUGH_ROWS), key=lambda kind: (-held[kind], kind))
    all_told = sum(told.values())
    print(
        f"the feed: {rows:,} rows, {shown:,} a card can show; held for want of a category alone and"
        f" showable by their title: {sum(held_buckets.values()):,} (the title gives a kind to"
        f" {held_buckets['kind']:,}, an accessory {held_buckets['accessory']:,}, doubtful"
        f" {held_buckets['doubtful']:,}, nothing {held_buckets['none']:,})"
    )
    print(
        f"the title alone against the shelf, on the rows shown with one: the title gives a kind to {all_told:,},"
        f" agreeing with the shelf for {sum(right.values()):,}"
        f" ({100 * sum(right.values()) / all_told:.1f}%)" if all_told else "no row shown with a shelf"
    )
    brought = sum(held[kind] for kind in safe)
    print(
        f"kinds the title alone reads right at least {SAFE:.0%} of the time, with at least {ENOUGH_ROWS} rows to"
        f" tell by: {len(safe):,}; they would bring in {brought:,} of the {held_buckets['kind']:,} held rows"
        " whose title gives a kind"
    )
    by_shop: Counter = Counter()
    for kind in safe:
        by_shop.update(held_shops[kind])
    if by_shop:
        print("  by shop: " + "; ".join(f"{shop} {count:,}" for shop, count in by_shop.most_common(10)))
    for kind in safe[:LISTED]:
        shops = ", ".join(f"{shop} {count:,}" for shop, count in held_shops[kind].most_common(3))
        print(
            f"  {kind}: right {100 * share(kind):.1f}% of {told[kind]:,}; brings in {held[kind]:,} ({shops});"
            f" e.g. {' | '.join(held_titles[kind])}"
        )
    print(f"kinds under {SAFE:.0%}: {len(unsafe):,}, holding {sum(held[kind] for kind in unsafe):,} held rows; the most first")
    for kind in unsafe[:LISTED]:
        errs = ", ".join(f"{shelf or '?'} {count:,}" for shelf, count in wrong_shelves[kind].most_common(2))
        print(
            f"  {kind}: right {100 * share(kind):.1f}% of {told[kind]:,}; held {held[kind]:,}; the shelf said"
            f" instead: {errs}; e.g. {' | '.join(wrong_titles[kind])}"
        )
    print(
        f"kinds with fewer than {ENOUGH_ROWS} rows to tell by: {len(untold):,}, holding"
        f" {sum(held[kind] for kind in untold):,} held rows; the most first: "
        + "; ".join(f"{kind} {held[kind]:,} ({told[kind]:,})" for kind in untold[:LISTED])
    )
    before = sum(1 for kind, shops in shown_shops.items() if len(shops) >= COVERED)
    after_shops = {kind: set(shops) for kind, shops in shown_shops.items()}
    for kind in safe:
        after_shops.setdefault(kind, set()).update(held_shops[kind])
    after = sum(1 for shops in after_shops.values() if len(shops) >= COVERED)
    print(
        f"kinds with products from at least {COVERED} shops: {before:,} today, {after:,} with the kinds at"
        f" {SAFE:.0%} brought in"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
