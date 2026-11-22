"""A look before the rule of a cap per shop is written: what it would keep and cut.

Owner, 2026-11-22: a shop keeps at most 20,000 products, one cap for every shop (17:08
Athens: «το πλαφόν είναι ένα και είναι 20.000 προϊόντα.. δεν μπαίνει πλαφόν για το κάθε
κατάστημα.. μπαίνει κανόνας μόνο όσα έχουν σκανναριστεί περνάνε»: what a shop's pace allows
shows by itself, since only the products the bot has checked are shown). Kept first (16:03,
and 17:15 with three changes): the products of the kinds with the fewest products; what the
shop sells cheapest of the offers the site keeps (the same product, by its code); the rest,
the products with a kind before those with none, a share of each kind over its prices.

On a copy of the server's prepared catalogue, with no AI and nothing written anywhere:

1. each shop's products as the catalogue shows them, and its cap: 20,000 for every shop
   (with `--by-pace`, as the rule was first read: a day of the bot's 21.6 hours at the pace
   the look of 22/11 measured for the shop, where that is less, `PACE_SECONDS`);
2. for the shops over their cap: how many of their products carry a code another shop's
   product carries too (`product_identity.same_product_key`), and of those where this shop
   is the cheapest, tied or dearer; how many are of a kind the whole catalogue holds few of;
   how many have no kind of the site's at all;
3. the three steps tried in the owner's order, each step's products chosen, when it holds
   more than the places left, as the category cap chooses (`catalogue_cap.fair_quotas` over
   the kinds, each spread over its prices): how many each step keeps, how many are cut;
   and tried again refined (`measure`, `tried`): a product a cheaper shop keeps is kept last
   of all, a product whose cheaper offers were all cut counts as cheapest for the next shop,
   and the products with a kind of the site's go before those with none;
4. what each way leaves of the catalogue: its products, the products a cheaper shop keeps
   too, each kind's products before and after, the kinds left with none, with fewer than 4,
   with fewer than 24; and the kinds that lose the most.

    python3 deployment/server/look_shop_cap.py CATALOGUE.json.gz [--cap 20000] [--thin 100] [--by-pace]

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


# Whether a shop's cap is also held to a day of the bot at its pace: not the owner's rule
# (22/11, 17:08: one cap for every shop), kept to compare with the first reading of it.
BY_PACE = False


def cap_of(shop: str, cap: int = CAP, by_pace: bool | None = None) -> int:
    pace = PACE_SECONDS.get(shop) if (BY_PACE if by_pace is None else by_pace) else None
    return min(cap, int(DAY_SECONDS // pace)) if pace else cap


def _price(product: Any) -> float:
    from picwise_providers.decision_labels import parse_price_amount

    amount = parse_price_amount(product.price_text)
    return float(amount) if amount is not None else float("inf")


def measure(prepared: Any, cap: int = CAP, thin: int = THIN) -> dict[str, Any]:
    """Everything the look says, as numbers: the catalogue, each shop, and the three steps
    tried two ways (`_tried`)."""
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
    shared = [bool(code) and len(sellers[code]) > 1 for code in codes]
    cheapest_here = [shared[place] and prices[place] <= cheapest[codes[place]] for place in range(count)]
    in_thin = [bool(own[place]) and min(kind_size[kind] for kind in narrowest(own[place])) < thin for place in range(count)]

    def choose(places: list[int], room: int) -> list[int]:
        """`room` of `places`, as the category cap chooses inside a category: fair shares
        over the parts (a kind, else a shelf), each part spread over its prices."""
        if room >= len(places):
            return list(places)
        if room <= 0:
            return []
        by_part: dict[str, list[int]] = defaultdict(list)
        for place in places:
            by_part[parts[place]].append(place)
        quotas = fair_quotas({part: len(found) for part, found in by_part.items()}, room)
        chosen: list[int] = []
        for part, found in by_part.items():
            chosen.extend(_spread(found, quotas.get(part, 0), order))
        return chosen

    capped = sorted((shop for shop, places in by_shop.items() if len(places) > cap_of(shop, cap)),
                    key=lambda shop: (cap_of(shop, cap), shop))

    def tried(refined: bool) -> dict[str, Any]:
        """The three steps tried. As recorded: (1) what the shop sells cheapest of all the
        shops that sell it, (2) the thin kinds, (3) the rest, a share of each part. Refined
        (proposed): a product a cheaper shop keeps is kept last of all; a product whose
        cheaper offers were all cut counts as cheapest for the next shop (the shops settled
        the smallest cap first, after a first pass in which each keeps what it sells cheapest
        of all); and in step 3 the products with a kind of the site's go before those with
        none."""
        keep = [True] * count
        for shop in capped:
            for place in by_shop[shop]:
                keep[place] = False
        steps: dict[str, list[int]] = {shop: [0, 0, 0, 0] for shop in capped}
        taken: dict[str, set[int]] = {shop: set() for shop in capped}

        def take(shop: str, places: list[int], step: int) -> None:
            left = [place for place in places if place not in taken[shop]]
            chosen = choose(left, cap_of(shop, cap) - len(taken[shop]))
            taken[shop].update(chosen)
            steps[shop][step] += len(chosen)
            for place in chosen:
                keep[place] = True

        for shop in capped:
            take(shop, [place for place in by_shop[shop] if cheapest_here[place]], 0)
        for shop in capped:
            places = by_shop[shop]
            if not refined:
                take(shop, [place for place in places if in_thin[place]], 1)
                take(shop, places, 2)
                continue
            # The cheapest price each code is kept at by another shop, as things stand.
            kept_at: dict[str, float] = {}
            wanted = {codes[place] for place in places if shared[place]}
            for place, code in enumerate(codes):
                if code in wanted and keep[place] and shops[place] != shop and prices[place] < kept_at.get(code, float("inf")):
                    kept_at[code] = prices[place]
            dearer = {place for place in places if shared[place] and kept_at.get(codes[place], float("inf")) < prices[place]}
            rest = [place for place in places if place not in dearer]
            take(shop, [place for place in rest if shared[place]], 0)
            take(shop, [place for place in rest if in_thin[place]], 1)
            take(shop, [place for place in rest if own[place]], 2)
            take(shop, rest, 2)
            take(shop, sorted(dearer), 3)
        after: Counter = Counter(kind for place, found in enumerate(own) if keep[place] for kind in found)
        lost = sorted(((kind_size[kind] - after[kind], kind_size[kind], kind) for kind in kind_size), reverse=True)
        # Of what the capped shops keep: the products a cheaper shop keeps too, and how many
        # different products (codes, or rows with none) they show.
        kept_low: dict[str, float] = {}
        for place, code in enumerate(codes):
            if code and keep[place] and prices[place] < kept_low.get(code, float("inf")):
                kept_low[code] = prices[place]
        of_capped = [place for shop in capped for place in by_shop[shop] if keep[place]]
        return {
            "kept": sum(keep), "cut": count - sum(keep),
            "with_a_kind_kept": sum(1 for place, found in enumerate(own) if found and keep[place]),
            "steps": steps,
            "dearer_duplicates_kept": sum(1 for place in of_capped if codes[place] and kept_low[codes[place]] < prices[place]),
            "different_products_of_the_capped": len({codes[place] or f"row:{place}" for place in of_capped}),
            "kinds_under": {limit: sum(1 for kind in kind_size if after[kind] < limit) for limit in (1, 4, 24, thin)},
            "lost_most": [{"kind": kind, "before": before, "after": before - gone} for gone, before, kind in lost[:KINDS_LISTED]],
            "halved": sum(1 for gone, before, _kind in lost if before and gone * 2 > before),
        }

    rows = []
    for shop, places in sorted(by_shop.items(), key=lambda item: -len(item[1])):
        limit = cap_of(shop, cap)
        rows.append({
            "shop": shop, "products": len(places), "cap": limit, "over": max(0, len(places) - limit),
            "with_a_code": sum(1 for place in places if codes[place]), "shared": sum(1 for place in places if shared[place]),
            "cheapest_here": sum(1 for place in places if cheapest_here[place]),
            "dearer_here": sum(1 for place in places if shared[place] and not cheapest_here[place]),
            "with_a_kind": sum(1 for place in places if own[place]), "in_thin_kinds": sum(1 for place in places if in_thin[place]),
        })
    return {
        "products": count, "shops": len(by_shop), "with_a_kind": sum(1 for found in own if found), "rows": rows,
        "kinds": len(kind_size),
        "kinds_under_before": {limit: sum(1 for kind in kind_size if kind_size[kind] < limit) for limit in (1, 4, 24, thin)},
        "as_recorded": tried(False), "refined": tried(True),
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
        f"the catalogue: {numbers['products']:,} products of {numbers['shops']} shops, {numbers['with_a_kind']:,} with a kind",
        "== each shop: products shown, its cap, over it; with a code; a code another shop sells too: cheapest here"
        " (of them at the same price as another shop), dearer here; with a kind; of a thin kind"
        f" (under {thin} products in the whole catalogue)",
    ]
    for row in numbers["rows"][:SHOPS_LISTED]:
        lines.append(
            f"{row['shop']}: {row['products']:,}, cap {row['cap']:,}, over {row['over']:,}; with a code {row['with_a_code']:,};"
            f" shared {row['shared']:,}: cheapest here {row['cheapest_here']:,} ({tied.get(row['shop'], 0):,} tied),"
            f" dearer here {row['dearer_here']:,}; with a kind {row['with_a_kind']:,}; thin {row['in_thin_kinds']:,}"
        )
    over = [row for row in numbers["rows"] if row["over"]]
    lines.append(f"shops over their cap: {len(over)}: " + ", ".join(f"{row['shop']} {row['over']:,}" for row in over))
    before = numbers["kinds_under_before"]
    for title, name in (("the steps as recorded", "as_recorded"), ("the steps refined (proposed)", "refined")):
        found = numbers[name]
        under = found["kinds_under"]
        lines.append(
            f"== {title}: kept {found['kept']:,}, cut {found['cut']:,}; with a kind kept {found['with_a_kind_kept']:,} of"
            f" {numbers['with_a_kind']:,}; of what the capped shops keep, {found['dearer_duplicates_kept']:,} are sold cheaper by"
            f" a shop that keeps them too, and they show {found['different_products_of_the_capped']:,} different products"
        )
        lines.append("kept by step (cheapest shown, thin kinds, the rest, a cheaper shop's too): " + "; ".join(
            f"{shop} {' + '.join(f'{step:,}' for step in steps)}" for shop, steps in found["steps"].items()))
        lines.append(
            f"the kinds ({numbers['kinds']}), before and after: with no product {before[1]} and {under[1]}; under 4 products"
            f" {before[4]} and {under[4]}; under 24 {before[24]} and {under[24]}; under {thin} {before[thin]} and {under[thin]};"
            f" that lose over half {found['halved']}"
        )
        lines.append("the kinds that lose the most: " + ", ".join(
            f"{entry['kind']} {entry['before']:,} to {entry['after']:,}" for entry in found["lost_most"]))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--cap", type=int, default=CAP)
    parser.add_argument("--thin", type=int, default=THIN)
    parser.add_argument("--by-pace", action="store_true", help="hold a shop's cap to a day of the bot at its pace too")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    global BY_PACE
    BY_PACE = bool(args.by_pace)
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
