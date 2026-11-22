"""A look before the rule of a cap per shop is written: what it would keep and cut.

Owner, 2026-11-22 (15:51 to 16:03 Athens): each shop, and every shop that comes in, keeps at
most what the bot can check in one day at that shop's own pace, and never more than 20,000;
kept first, the products the shop sells cheapest of all (the same product, by its code);
then the products of the site's kinds with the fewest products; then the rest, a share of
each kind over its prices, the most complete first. Not yet in the rules, not built.

On a copy of the server's prepared catalogue, with no AI and nothing written anywhere:

1. each shop's products as the catalogue shows them, and its cap: 20,000, or a day of the
   bot's 21.6 hours at the pace the look of 22/11 measured for it, where that is less
   (`PACE_SECONDS`; the bot's own nights will measure every shop from 23/11);
2. for the shops over their cap: how many of their products carry a code another shop's
   product carries too (`product_identity.same_product_key`), and of those where this shop
   is the cheapest, tied or dearer; how many are of a kind the whole catalogue holds few of;
   how many have no kind of the site's at all;
3. the three steps tried in the owner's order, each step's products chosen, when it holds
   more than the places left, as the category cap chooses (`catalogue_cap.fair_quotas` over
   the kinds, each spread over its prices): how many each step keeps, how many are cut;
4. what that leaves of the catalogue: its products, each kind's products before and after,
   the kinds left with none, with fewer than 4, with fewer than 24; and the kinds that lose
   the most.

    python3 deployment/server/look_shop_cap.py CATALOGUE.json.gz [--cap 20000] [--thin 100]

Counts, shops' and kinds' names only, never a link or an id. Always exits 0.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

CAP = 20000
# The bot's day (the checks' rules 4.7): 05:30 to 03:05 UTC.
DAY_SECONDS = 21 * 3600 + 35 * 60
# Seconds a request, each shop asked alone (the looks of 22/11, the checks' rules 17).
PACE_SECONDS = {"InStock UK": 3.3, "Tyres UK": 3.3, "Tooled Up": 4.1, "GamingKit": 4.3, "PCHUB.UK": 6.4, "Tirendo UK": 10.0}
# A kind the whole catalogue holds fewer products of than this is "thin".
THIN = 100
SHOPS_LISTED = 25
KINDS_LISTED = 20


def cap_of(shop: str, cap: int = CAP) -> int:
    pace = PACE_SECONDS.get(shop)
    return min(cap, int(DAY_SECONDS // pace)) if pace else cap


def _price(product: Any) -> float:
    from picwise_providers.decision_labels import parse_price_amount

    amount = parse_price_amount(product.price_text)
    return float(amount) if amount is not None else float("inf")


def measure(prepared: Any, cap: int = CAP, thin: int = THIN) -> dict[str, Any]:
    """Everything the look says, as numbers."""
    from picwise_providers.catalogue_cap import _spread, fair_quotas, part_of, row_key, shop_of
    from picwise_providers.kind_itself import narrowest, real_kinds
    from picwise_providers.product_identity import same_product_key

    products, kinds = prepared.products, prepared.kinds
    count = len(products)
    shops = [shop_of(product) for product in products]
    prices = [_price(product) for product in products]
    codes = [same_product_key(product.raw if isinstance(product.raw, dict) else {}, brand=str(product.brand or ""))
             for product in products]
    own = [real_kinds(found) for found in kinds]
    parts = [part_of(product, found) for product, found in zip(products, kinds)]
    by_shop: dict[str, list[int]] = defaultdict(list)
    for place, shop in enumerate(shops):
        by_shop[shop].append(place)
    kind_size: Counter = Counter(kind for found in own for kind in found)
    # The cheapest price each code is sold at, and by how many shops.
    cheapest: dict[str, float] = {}
    sellers: dict[str, set[str]] = defaultdict(set)
    for place, code in enumerate(codes):
        if code:
            sellers[code].add(shops[place])
            if prices[place] < cheapest.get(code, float("inf")):
                cheapest[code] = prices[place]
    order = [(prices[place] == float("inf"), prices[place], row_key(products[place])) for place in range(count)]

    def choose(places: list[int], room: int) -> list[int]:
        """`room` of `places`, as the category cap chooses inside a category: fair shares
        over the parts (a kind, else a shelf), each part spread over its prices."""
        if room >= len(places):
            return list(places)
        by_part: dict[str, list[int]] = defaultdict(list)
        for place in places:
            by_part[parts[place]].append(place)
        quotas = fair_quotas({part: len(found) for part, found in by_part.items()}, room)
        chosen: list[int] = []
        for part, found in by_part.items():
            chosen.extend(_spread(found, quotas.get(part, 0), order))
        return chosen

    keep = [True] * count
    rows = []
    for shop, places in sorted(by_shop.items(), key=lambda item: -len(item[1])):
        limit = cap_of(shop, cap)
        coded = [place for place in places if codes[place]]
        shared = [place for place in coded if len(sellers[codes[place]]) > 1]
        cheapest_here = [place for place in shared if prices[place] <= cheapest[codes[place]]]
        with_kind = [place for place in places if own[place]]
        in_thin = [place for place in with_kind if min(kind_size[kind] for kind in narrowest(own[place])) < thin]
        row = {"shop": shop, "products": len(places), "cap": limit, "over": max(0, len(places) - limit),
               "with_a_code": len(coded), "shared": len(shared), "cheapest_here": len(cheapest_here),
               "dearer_here": len(shared) - len(cheapest_here), "with_a_kind": len(with_kind), "in_thin_kinds": len(in_thin)}
        if len(places) > limit:
            taken: set[int] = set()
            steps = []
            for step in (cheapest_here, in_thin, places):
                left = [place for place in step if place not in taken]
                chosen = choose(left, limit - len(taken))
                taken.update(chosen)
                steps.append(len(chosen))
            row["kept_by_step"] = steps
            for place in places:
                if place not in taken:
                    keep[place] = False
        rows.append(row)
    after: Counter = Counter(kind for place, found in enumerate(own) if keep[place] for kind in found)
    lost = sorted(((kind_size[kind] - after[kind], kind_size[kind], kind) for kind in kind_size), reverse=True)
    return {
        "products": count, "shops": len(by_shop), "kept": sum(keep), "cut": count - sum(keep),
        "with_a_kind": sum(1 for found in own if found),
        "with_a_kind_kept": sum(1 for place, found in enumerate(own) if found and keep[place]),
        "rows": rows,
        "kinds": len(kind_size),
        "kinds_under": {limit: [sum(1 for kind in kind_size if kind_size[kind] < limit),
                                sum(1 for kind in kind_size if after[kind] < limit)] for limit in (1, 4, 24, thin)},
        "lost_most": [{"kind": kind, "before": before, "after": before - gone} for gone, before, kind in lost[:KINDS_LISTED]],
        "halved": sum(1 for gone, before, _kind in lost if before and gone * 2 > before),
    }


def ties(prepared: Any) -> Counter:
    """Per shop, its products at their code's cheapest price that another shop sells at
    that same price."""
    from picwise_providers.catalogue_cap import shop_of
    from picwise_providers.product_identity import same_product_key

    at: dict[str, dict[str, float]] = defaultdict(dict)
    for product in prepared.products:
        code = same_product_key(product.raw if isinstance(product.raw, dict) else {}, brand=str(product.brand or ""))
        if code:
            shop, price = shop_of(product), _price(product)
            at[code][shop] = min(price, at[code].get(shop, float("inf")))
    tied: Counter = Counter()
    for found in at.values():
        if len(found) < 2:
            continue
        low = min(found.values())
        level = [shop for shop, price in found.items() if price == low]
        if len(level) > 1:
            tied.update(level)
    return tied


def report(numbers: dict[str, Any], tied: Counter, thin: int = THIN) -> list[str]:
    lines = [
        f"the catalogue: {numbers['products']:,} products of {numbers['shops']} shops, {numbers['with_a_kind']:,} with a kind;"
        f" a cap per shop would keep {numbers['kept']:,} and cut {numbers['cut']:,}"
        f" ({numbers['with_a_kind_kept']:,} with a kind kept)",
        "== each shop: products shown, its cap, over it; with a code; a code another shop sells too: cheapest here"
        " (of them at the same price as another shop), dearer here; with a kind; of a thin kind"
        f" (under {thin} products in the whole catalogue); kept by step 1, 2, 3",
    ]
    for row in numbers["rows"][:SHOPS_LISTED]:
        steps = row.get("kept_by_step")
        lines.append(
            f"{row['shop']}: {row['products']:,}, cap {row['cap']:,}, over {row['over']:,}; with a code {row['with_a_code']:,};"
            f" shared {row['shared']:,}: cheapest here {row['cheapest_here']:,} ({tied.get(row['shop'], 0):,} tied),"
            f" dearer here {row['dearer_here']:,}; with a kind {row['with_a_kind']:,}; thin {row['in_thin_kinds']:,}"
            + (f"; kept {steps[0]:,} + {steps[1]:,} + {steps[2]:,}" if steps else "")
        )
    over = [row for row in numbers["rows"] if row["over"]]
    lines.append(f"shops over their cap: {len(over)}: " + ", ".join(f"{row['shop']} {row['over']:,}" for row in over))
    under = numbers["kinds_under"]
    lines.append(
        f"== the kinds ({numbers['kinds']}), before and after: with no product {under[1][0]} and {under[1][1]};"
        f" under 4 products {under[4][0]} and {under[4][1]}; under 24 {under[24][0]} and {under[24][1]};"
        f" under {thin} {under[thin][0]} and {under[thin][1]}; that lose over half {numbers['halved']}"
    )
    lines.append("the kinds that lose the most: " + ", ".join(
        f"{entry['kind']} {entry['before']:,} to {entry['after']:,}" for entry in numbers["lost_most"]))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--cap", type=int, default=CAP)
    parser.add_argument("--thin", type=int, default=THIN)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    import look_itself

    began = time.monotonic()
    try:
        prepared = look_itself._load(args.catalogue, gone="", offers="", families="")
    except Exception as error:  # a look only
        print(f"the catalogue could not be read: {type(error).__name__}: {error}")
        return 0
    if prepared is None:
        print("the copy is not a prepared catalogue")
        return 0
    print(f"the catalogue of {prepared.prepared_at.isoformat()}, read in {time.monotonic() - began:.0f} s")
    for line in report(measure(prepared, args.cap, args.thin), ties(prepared), args.thin):
        print(line)
    print(f"in {time.monotonic() - began:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
