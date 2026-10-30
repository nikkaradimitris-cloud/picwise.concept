"""Print what a cap of 15% a category would keep of the server's prepared catalogue.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_cap.py catalogue.json.gz

Owner, 2026-10-27: no category of like products over 15% of all products, counted per
category of the shop's shelf, yesterday's kept ones the next night's starting point,
clean information first (`picwise_providers.catalogue_cap`). Measured first: run by
.github/workflows/server-cap.yml on GitHub's runner, from a copy of the server's file,
with this checkout's code; nothing on the server or shown changes. Counts, names and
prices only; the file's links are never printed. Always exits 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

# How many categories, kinds and shops each list prints.
LISTED = 12


def _share(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "-"


def _money(value: float) -> str:
    return f"{value:,.2f}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_cap.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_providers.catalogue_cap import CLEAN_SIGNS, cap_catalogue
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]))
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        result = cap_catalogue(prepared.products, prepared.kinds, feed_ctx=prepared.availability_context)
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the cap could not be measured: {type(error).__name__}")
        return 0

    total = len(result.keep)
    kept = result.kept
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {total:,} products a card can show,"
        f" in {len(result.by_category):,} categories"
    )
    if result.size is None:
        print(f"a cap of {result.share:.0%} a category cannot hold with so few categories: nothing would be left out")
        return 0
    print(
        f"a cap of {result.share:.0%} a category: at most {result.size:,} a category;"
        f" {kept:,} kept, {total - kept:,} left out (no list of the night before: chosen as on a first night)"
    )
    over = sorted(result.inside, key=lambda name: (-result.by_category[name][0], name))
    print("categories over the cap:" if over else "no category is over the cap")
    for name in over:
        before, after = result.by_category[name]
        print(f"  {before:>9,} -> {after:>7,}  {name}")
    print("the largest categories after the cap, and their share of what is kept:")
    largest = sorted(result.by_category.items(), key=lambda item: (-item[1][1], item[0]))[:LISTED]
    for name, (_before, after) in largest:
        print(f"  {after:>9,}  {_share(after, kept):>6}  {name}")
    for name in over:
        parts = result.inside[name]
        print(f"inside {name}, by kind (by shelf when a product has none): {len(parts):,} of them")
        for part, (before, after) in sorted(parts.items(), key=lambda item: (-item[1][0], item[0]))[:LISTED]:
            print(f"  {before:>9,} -> {after:>7,}  {part}")
        summary = result.prices.get(name) or {}
        everything, chosen = summary.get("all"), summary.get("kept")
        if everything and chosen:
            print(
                "  prices, lowest / middle / highest: all "
                + " / ".join(_money(value) for value in everything)
                + "; kept "
                + " / ".join(_money(value) for value in chosen)
            )
    print("by shop, the most products first:")
    for shop, (before, after) in sorted(result.by_shop.items(), key=lambda item: (-item[1][0], item[0]))[:LISTED]:
        print(f"  {before:>9,} -> {after:>7,}  {_share(after, kept):>6}  {shop}")
    in_over = sum(result.kept_by_missing_signs.values())
    if in_over:
        lacking = ", ".join(
            f"{count:,} lacking {('one', 'two', 'all three')[missing - 1]}"
            for missing, count in result.kept_by_missing_signs.items()
            if missing
        )
        print(
            f"of the {in_over:,} kept in the categories over the cap:"
            f" {result.kept_by_missing_signs.get(0, 0):,} with all of {', '.join(CLEAN_SIGNS)}"
            + (f"; {lacking} of them" if lacking else "")
            + f"; {result.kept_in_several_shops:,} sold by more than one shop"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
