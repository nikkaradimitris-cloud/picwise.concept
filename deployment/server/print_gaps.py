"""Which of PicWise's kinds have products from too few shops, and which have none: where
more shops, of Awin or of another network, would fill the catalogue.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_gaps.py catalogue.json.gz

Owner, 2026-10-31: «Ναι, κάνε τη μέτρηση», so that they know which shops to look for
(Awin's programmes that accept at once, then Webgains). Counted as the nightly note
counts "enough" (`picwise_providers.catalogue_balance`: each product a card can show
under its narrowest real kind, its shop by the merchant's name; at least 3 shops, the
owner's "enough" of 26/10), and set against every kind PicWise defines, by its
mega-category (`picwise_nlu.product_concepts`). Run by .github/workflows/server-cap.yml
on GitHub's runner from a copy of the server's file; nothing on the server or shown
changes. Counts and names only, never a link. Always exits 0.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path

# The shops a kind needs to count as covered (owner, 2026-10-26).
ENOUGH = 3
# Kinds found in the file that the concept table does not hold.
OTHER = "(kinds outside the concept table)"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_gaps.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_nlu.product_concepts import get_product_concepts
        from picwise_providers.catalogue_balance import NO_SHOP, _narrowest_kind
        from picwise_providers.normalization import extract_merchant_name
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]))
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        concepts = get_product_concepts()
        products: Counter = Counter()
        shops: dict[str, Counter] = defaultdict(Counter)
        every_shop: set[str] = set()
        for product, product_kinds in zip(prepared.products, prepared.kinds):
            raw = product.raw if isinstance(product.raw, Mapping) else {}
            shop = " ".join(str(extract_merchant_name(raw) or "").split()) or NO_SHOP
            every_shop.add(shop)
            kind = _narrowest_kind(product_kinds)
            if kind:
                products[kind] += 1
                shops[kind][shop] += 1
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the gaps could not be measured: {type(error).__name__}")
        return 0

    mega_of = {concept.concept_id: concept.mega_category_id for concept in concepts}
    name_of = {concept.concept_id: concept.primary_english or concept.concept_id for concept in concepts}
    kinds_by_mega: dict[str, list[str]] = defaultdict(list)
    for concept in concepts:
        kinds_by_mega[concept.mega_category_id].append(concept.concept_id)
    for kind in sorted(set(products) - set(mega_of)):
        kinds_by_mega[OTHER].append(kind)
        name_of[kind] = kind

    def spread(kind: str) -> int:
        return len(shops.get(kind, ()))

    with_kind = sum(products.values())
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products a card"
        f" can show, from {len(every_shop):,} shops; {with_kind:,} of them with a kind; PicWise defines"
        f" {len(concepts):,} kinds"
    )
    every_kind = [kind for kinds in kinds_by_mega.values() for kind in kinds]
    tally = Counter(min(spread(kind), ENOUGH) for kind in every_kind)
    print(
        f"kinds with products from at least {ENOUGH} shops: {tally[ENOUGH]:,}; from two: {tally[2]:,};"
        f" from one: {tally[1]:,}; with none: {tally[0]:,}"
    )
    # The mega-categories with the most kinds short of shops first.
    order = sorted(
        kinds_by_mega,
        key=lambda mega: (-sum(1 for kind in kinds_by_mega[mega] if spread(kind) < ENOUGH), mega),
    )
    print(f"by mega-category: kinds defined; from {ENOUGH}+ shops / two / one / none; products; shops")
    for mega in order:
        kinds = kinds_by_mega[mega]
        counted = Counter(min(spread(kind), ENOUGH) for kind in kinds)
        mega_shops = set().union(*(shops.get(kind, Counter()).keys() for kind in kinds))
        print(
            f"  {mega}: {len(kinds):,}; {counted[ENOUGH]:,} / {counted[2]:,} / {counted[1]:,} / {counted[0]:,};"
            f" {sum(products[kind] for kind in kinds):,}; {len(mega_shops):,}"
        )
    print(f"the kinds with products from fewer than {ENOUGH} shops, the most products first (products: shops)")
    for mega in order:
        short = [kind for kind in kinds_by_mega[mega] if 0 < spread(kind) < ENOUGH]
        if not short:
            continue
        print(f"  {mega}:")
        for kind in sorted(short, key=lambda kind: (-products[kind], name_of[kind])):
            named = ", ".join(f"{shop} {count:,}" for shop, count in shops[kind].most_common())
            print(f"    {name_of[kind]}: {products[kind]:,}: {named}")
    print("the kinds with no product")
    for mega in order:
        empty = sorted(name_of[kind] for kind in kinds_by_mega[mega] if spread(kind) == 0)
        if empty:
            print(f"  {mega} ({len(empty):,}): {', '.join(empty)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
