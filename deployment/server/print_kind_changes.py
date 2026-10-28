"""Print which products of the server's prepared catalogue this checkout reads as another kind.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_kind_changes.py catalogue.json.gz

Owner, 2026-10-27: «Διόρθω τους κανόνες και άντε να δούμε πού θα καταλήξουμε τελικά»,
after the check of far prices (`print_prices.py`) listed products read as the wrong kind.
Each product is read again as the preparation reads it (`annotate_product_concepts` of
its type, its categories and its title) with this checkout's rules, and its narrowest
kind set against the one the server stored: how many are read as another kind, from which
to which, with the shops and the cheapest titles of each change (price first puts the
cheapest at the top of a page), and the kinds whose counts change; then the check of far
prices again (`print_prices.print_far`), with the kinds read so: where it ends. Run by
.github/workflows/server-cap.yml on GitHub's runner, from a copy of the server's file;
nothing on the server or shown changes until a deployment. Counts, names, titles and
prices only; the file's links are never printed. Always exits 0.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

CHANGES = 20
SHOPS = 4
EXAMPLES = 5
LISTED = 20


def _short(text: str, width: int = 70) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _label(kinds, narrowest) -> str:
    """A product's kind as the cap and the price check name it: its narrowest kind, or
    what its markers say."""
    if "__accessory__" in kinds:
        return "(accessory)"
    if "__uncertain_kind__" in kinds:
        return "(doubtful)"
    return narrowest(kinds) or "(no kind)"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_kind_changes.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_nlu.concept_understanding import annotate_product_concepts
        from picwise_providers.catalogue_balance import _narrowest_kind
        from picwise_providers.catalogue_cap import shop_of
        from picwise_providers.decision_labels import parse_price_amount
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
        from picwise_providers.search_selection import _product_search_fields, product_kind_key
        from print_prices import print_far, rows_of

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]))
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        # The fields the preparation read each kind from, when the file holds them.
        fields = prepared.search_fields
        if not fields or "category" not in fields[0]:
            fields = tuple(_product_search_fields(product) for product in prepared.products)
        changes: dict[tuple[str, str], list] = defaultdict(list)
        before: Counter = Counter()
        after: Counter = Counter()
        widened = 0
        kinds_now = []
        for product, stored, product_fields in zip(prepared.products, prepared.kinds, fields):
            now = annotate_product_concepts(*product_kind_key(product, product_fields))
            kinds_now.append(now)
            old, new = _label(stored, _narrowest_kind), _label(now, _narrowest_kind)
            before[old] += 1
            after[new] += 1
            if old != new:
                changes[(old, new)].append(product)
            elif set(stored) != set(now):
                widened += 1
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the kinds could not be read again: {type(error).__name__}")
        return 0

    total = len(prepared.products)
    changed = sum(len(products) for products in changes.values())
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {total:,} products a card can show;"
        f" read again with this checkout's rules, {changed:,} are read as another kind"
        f" ({100 * changed / max(total, 1):.2f}%); {widened:,} keep their kind and gain or lose a broader one"
    )
    print("from -> to, the most first, with their shops and the cheapest titles (price | shop | title):")
    for (old, new), products in sorted(changes.items(), key=lambda item: (-len(item[1]), item[0]))[:CHANGES]:
        print(f"  {len(products):>9,}  {old} -> {new}")
        shops = Counter(shop_of(product) for product in products)
        print("             shops: " + ", ".join(f"{shop} {count:,}" for shop, count in shops.most_common(SHOPS)))
        priced = sorted(
            products,
            key=lambda product: (parse_price_amount(product.price_text) is None, parse_price_amount(product.price_text) or 0, str(product.title)),
        )
        for product in priced[:EXAMPLES]:
            price = parse_price_amount(product.price_text)
            shown = f"{price:,.2f} {str(product.currency or '').strip().upper()}" if price is not None else "no price"
            print(f"             {shown:>14} | {shop_of(product)} | {_short(product.title)}")
    moved = sorted(
        (name for name in set(before) | set(after) if before[name] != after[name]),
        key=lambda name: (-abs(after[name] - before[name]), name),
    )
    print(f"the kinds whose counts change, the most first: {len(moved):,}")
    for name in moved[:LISTED]:
        print(f"  {before[name]:>9,} -> {after[name]:>9,}  {name}")
    print("the check of far prices again, with the kinds this checkout's rules read:")
    try:
        print_far([row for row in rows_of(prepared, kinds_now) if row[0] is not None])
    except Exception as error:  # a measure only
        print(f"the far prices could not be measured again: {type(error).__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
