"""Print the prices at the ends of the server's prepared catalogue, and far from their kind's.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_prices.py catalogue.json.gz

Owner, 2026-10-27, on the cap of 15% a category: products at 99 pence may be poor, or
sold by the piece of a pack, and one at about 100,000 is too much; «Κάνε τη μέτρηση»
(measure first, never by the commission a product leaves). Prints how many products
cost under 1 and 2 and 10,000 and 50,000 or more, each in its own currency, by category
and shop with the cheapest and dearest titles; and how many cheap ones name a pack, a
set or a number of pieces in their title. Measured: the ends are few and real, so no
price rule and no trim of each kind's ends (owner's «Ναι», 2026-10-27). Then, as a check
the owner said yes to, the products priced far outside the usual prices of their kind
(a shelf naming a kind joins it, as in the cap) and of their own shop's for that kind,
by kind and by shop and kind: most often products read as the wrong kind; a list to
read, nothing hidden. Run by .github/workflows/server-cap.yml on
GitHub's runner, from a copy of the server's file; nothing on the server or shown
changes. Counts, names, titles and prices only; the file's links are never printed.
Always exits 0.
"""
from __future__ import annotations

import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

LISTED = 8
EXAMPLES = 10
# Kinds with fewer products have no usual prices worth comparing with.
MIN_KIND = 20
# A shop's own usual prices for a kind count from this many of its products of it.
MIN_SHOP = 10
# Outside the usual prices: beyond the middle half's spread taken this many times, on a
# ratio scale, and this many times off the middle price besides.
FENCE = 1.5
FAR = 10
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


def _usual(prices: list[float]) -> tuple[float, float, float]:
    """The usual prices of a group: the bounds beyond which a price is far (FENCE times
    the middle half's spread, on a ratio scale), and the middle price."""
    logs = sorted(math.log10(price) for price in prices)
    last = len(logs) - 1
    low, high = logs[last // 4], logs[(3 * last) // 4]
    spread = high - low
    return 10 ** (low - FENCE * spread), 10 ** (high + FENCE * spread), statistics.median(prices)


def _distance(price: float, usual: tuple[float, float, float]) -> float:
    """How far, on a ratio scale, `price` lies outside `usual` and FAR times off its
    middle besides; 0 when it does not."""
    bottom, top, middle = usual
    if price < bottom and price < middle / FAR:
        return math.log10(bottom / price)
    if price > top and price > middle * FAR:
        return math.log10(price / top)
    return 0.0


def rows_of(prepared, kinds) -> list[tuple]:
    """Per product: its price (None when unread), currency, category, kind or shelf (a
    shelf naming a kind joins it, as in the cap), shop and short title. `kinds` are the
    stored ones, or those this checkout reads (`print_kind_changes.py`)."""
    from picwise_providers.catalogue_cap import category_of, joined_parts, part_of, shop_of
    from picwise_providers.decision_labels import parse_price_amount

    categories = [category_of(product) for product in prepared.products]
    parts = joined_parts(categories, [part_of(product, product_kinds) for product, product_kinds in zip(prepared.products, kinds)])
    return [
        (
            parse_price_amount(product.price_text),
            str(product.currency or "").strip().upper() or "?",
            category,
            part,
            shop_of(product),
            _short(product.title),
        )
        for product, category, part in zip(prepared.products, categories, parts)
    ]


def print_far(priced: list[tuple]) -> None:
    """Print the products priced far outside the usual prices of their kind and of their
    own shop's for it, from `rows_of`'s rows that have a price."""
    # Far outside the usual prices of their kind: beyond the middle half's spread, taken
    # FENCE times on a ratio scale, and FAR times off the middle price besides; and far
    # outside its own shop's usual prices for that kind too, when the shop has MIN_SHOP
    # or more of it, so a shop's cheap rings are not doubted because another sells
    # diamonds (owner, 2026-10-27: «Ναι» to using it as a check, then to comparing within
    # the shop). Such a price is most often a product read as the wrong kind, sometimes a
    # pack or a luxury piece: a list to read, nothing hidden.
    by_part: dict[str, list[float]] = defaultdict(list)
    by_shop_part: dict[tuple[str, str], list[float]] = defaultdict(list)
    for price, _currency, _category, part, shop, _title in priced:
        if price > 0:
            by_part[part].append(price)
            by_shop_part[(shop, part)].append(price)
    usual = {part: _usual(prices) for part, prices in by_part.items() if len(prices) >= MIN_KIND}
    own_usual = {key: _usual(prices) for key, prices in by_shop_part.items() if len(prices) >= MIN_SHOP}
    far = []
    for row in priced:
        price, part, shop = row[0], row[3], row[4]
        if part not in usual or price <= 0:
            continue
        distance = _distance(price, usual[part])
        own = own_usual.get((shop, part))
        if distance and (own is None or _distance(price, own)):
            far.append((distance, row))
    flagged = Counter(row[3] for _distance_, row in far)
    print(
        f"== priced far outside the usual prices of their kind (or shelf), and of their own shop's for it when it"
        f" has {MIN_SHOP} or more: {len(far):,}, in {len(flagged):,} of the {len(usual):,} with at least {MIN_KIND}"
        " products; a list to find products read as the wrong kind"
    )
    for part, count in sorted(flagged.items(), key=lambda item: (-item[1], item[0]))[: 2 * LISTED]:
        bottom, top, middle = usual[part]
        print(
            f"    {count:>7,} of {len(by_part[part]):>7,} (usual {_money(bottom)} to {_money(top)}, middle {_money(middle)})  {part}"
        )
    groups: dict[tuple[str, str], list[tuple[float, tuple]]] = defaultdict(list)
    for item in far:
        groups[(item[1][4], item[1][3])].append(item)
    print("  by shop and kind, the most first, each with its furthest:")
    for (shop, part), items in sorted(groups.items(), key=lambda entry: (-len(entry[1]), entry[0]))[: 2 * LISTED]:
        _distance_, (price, currency, _category, _part, _shop, title) = max(items, key=lambda item: (item[0], item[1][5]))
        print(f"    {len(items):>7,}  {shop} | {part} | e.g. {_money(price)} {currency} {title}")
    print(f"  the furthest {min(2 * EXAMPLES, len(far))}:")
    for _distance_, (price, currency, category, part, shop, title) in sorted(far, key=lambda item: (-item[0], item[1][5]))[: 2 * EXAMPLES]:
        print(f"    {_money(price):>12} {currency} | {part} (middle {_money(usual[part][2])}) | {shop} | {title} | {category}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_prices.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]))
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        rows = rows_of(prepared, prepared.kinds)
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

    print_far(priced)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
