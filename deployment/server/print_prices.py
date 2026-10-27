"""Print the prices at the ends of the server's prepared catalogue, and far from their kind's.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_prices.py catalogue.json.gz

Owner, 2026-10-27, on the cap of 15% a category: products at 99 pence may be poor, or
sold by the piece of a pack, and one at about 100,000 is too much; «Κάνε τη μέτρηση»
(measure first, never by the commission a product leaves). Prints how many products
cost under 1 and 2 and 10,000 and 50,000 or more, each in its own currency, by category
and shop with the cheapest and dearest titles; how many cheap ones name a pack, a set or
a number of pieces in their title; how many are under a tenth or over ten times the
middle price of their kind; and, in the categories over the cap, the prices below and
above which the cheapest and dearest 2% of each kind lie. Run by
.github/workflows/server-cap.yml on GitHub's runner, from a copy of the server's file;
nothing on the server or shown changes. Counts, names, titles and prices only; the
file's links are never printed. Always exits 0.
"""
from __future__ import annotations

import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

LISTED = 8
EXAMPLES = 10
# Kinds with fewer products have no middle price worth comparing with.
MIN_KIND = 20
TRIM = 0.02
PACK = re.compile(
    r"\b(?:pack|packs|multipack|multi-pack|set of|sets of|bundle|pcs|pieces|pairs?)\b"
    r"|\b\d+\s*(?:x|pk|pcs|pack)\b|\bx\s*\d+\b",
    re.IGNORECASE,
)


def _short(text: str, width: int = 70) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _count_lines(counts: Counter, total: int) -> list[str]:
    return [
        f"    {count:>9,}  {100 * count / total:5.1f}%  {name}"
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:LISTED]
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_prices.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_providers.catalogue_balance import CAP_SHARE, capped_size
        from picwise_providers.catalogue_cap import category_of, part_of, shop_of
        from picwise_providers.decision_labels import parse_price_amount
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]))
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        rows = []
        for product, kinds in zip(prepared.products, prepared.kinds):
            rows.append(
                (
                    parse_price_amount(product.price_text),
                    str(product.currency or "").strip().upper() or "?",
                    category_of(product),
                    part_of(product, kinds),
                    shop_of(product),
                    _short(product.title),
                )
            )
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the prices could not be measured: {type(error).__name__}")
        return 0

    total = len(rows)
    currencies = Counter(currency for _price, currency, *_rest in rows)
    print(
        f"prices of the {total:,} products a card can show (catalogue of {prepared.prepared_at.isoformat()}): "
        + "; ".join(f"{currency} {count:,}" for currency, count in currencies.most_common())
        + " (the bands below are in each product's own currency)"
    )
    priced = [row for row in rows if row[0] is not None]
    print(f"no price read: {total - len(priced):,}")
    bands = (
        ("under 1.00", lambda price: price < 1),
        ("1.00 to under 2.00", lambda price: 1 <= price < 2),
        ("10,000 and over", lambda price: price >= 10_000),
        ("50,000 and over", lambda price: price >= 50_000),
    )
    print(
        "; ".join(
            f"{name}: {sum(1 for row in priced if test(row[0])):,} ({100 * sum(1 for row in priced if test(row[0])) / max(total, 1):.2f}%)"
            for name, test in bands
        )
    )
    for name, test in bands:
        found = [row for row in priced if test(row[0])]
        if not found or name == "50,000 and over":
            continue
        dear = name.startswith("10,000")
        print(f"== {name}: {len(found):,}")
        print("  by category:")
        for line in _count_lines(Counter(row[2] for row in found), len(found)):
            print(line)
        print("  by shop:")
        for line in _count_lines(Counter(row[4] for row in found), len(found)):
            print(line)
        if not dear:
            packs = sum(1 for row in found if PACK.search(row[5]))
            print(f"  their title names a pack, a set or a number of pieces: {packs:,} (by the words in the title)")
        ordered = sorted(found, key=lambda row: (-row[0], row[5]) if dear else (row[0], row[5]))
        print(f"  the {'dearest' if dear else 'cheapest'} {min(EXAMPLES, len(found))}:")
        for price, currency, category, _part, shop, title in ordered[:EXAMPLES]:
            print(f"    {_money(price):>12} {currency} | {shop} | {title} | {category}")

    by_part: dict[str, list[float]] = defaultdict(list)
    for price, _currency, _category, part, _shop, _title in priced:
        by_part[part].append(price)
    middles = {part: statistics.median(prices) for part, prices in by_part.items() if len(prices) >= MIN_KIND}
    low = [(row[0] / middles[row[3]], row) for row in priced if row[3] in middles and row[0] < middles[row[3]] / 10]
    high = [(row[0] / middles[row[3]], row) for row in priced if row[3] in middles and row[0] > middles[row[3]] * 10]
    print(f"== far from the middle price of their kind (or shelf), of the {len(middles):,} with at least {MIN_KIND} products:")
    for label, found, furthest_first in (
        ("under a tenth of it", low, lambda item: (item[0], item[1][5])),
        ("over ten times it", high, lambda item: (-item[0], item[1][5])),
    ):
        print(f"  {label}: {len(found):,}")
        for _ratio, (price, currency, category, part, shop, title) in sorted(found, key=furthest_first)[:LISTED]:
            print(f"    {_money(price):>12} {currency} (middle {_money(middles[part])}) | {part} | {shop} | {title}")

    sizes = Counter(row[2] for row in rows)
    cap = capped_size(list(sizes.values()), CAP_SHARE)
    over = sorted((name for name, count in sizes.items() if cap is not None and count > cap), key=lambda name: -sizes[name])
    print(f"== the cheapest and dearest {TRIM:.0%} of each kind (or shelf), in the categories over the cap:")
    if not over:
        print("  no category is over the cap")
    for category in over:
        parts: dict[str, list[float]] = defaultdict(list)
        for price, _currency, row_category, part, _shop, _title in priced:
            if row_category == category:
                parts[part].append(price)
        print(f"  {category}:")
        for part, prices in sorted(parts.items(), key=lambda item: (-len(item[1]), item[0]))[:LISTED]:
            prices.sort()
            last = len(prices) - 1
            below, above = prices[int(TRIM * last)], prices[int((1 - TRIM) * last)]
            print(
                f"    {len(prices):>9,}  cheapest {TRIM:.0%} up to {_money(below)}, dearest {TRIM:.0%} from {_money(above)}"
                f" (all {_money(prices[0])} to {_money(prices[-1])})  {part}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
