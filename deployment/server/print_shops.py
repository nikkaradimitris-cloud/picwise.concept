"""Print each shop of the server's prepared catalogue: its rows, what is shown, why the
rest is held back; then its rows without a category, and how many could be shown.

    ssh picwise 'sudo cat /srv/picwise/shared/public/prepared.json' | python3 deployment/server/print_shops.py

Run by .github/workflows/server-deploy.yml after a deployment. Reads the build's public
note (`tools/prepare_catalogue.py --static-dir`) on stdin: its `intake`, what each
shop's feed brings in (`picwise_providers.feed_intake`), which names every shop of the
feed, also one whose rows are all held back. So the log says which shops the feed link
carries, not only how many. Then, per shop, its rows the feed gate holds for having no
category (owner, 2026-10-25: about 532,000 of 1,123,857): how many for that alone, how
many could be shown by the shop's own product type or by the title alone, read as a
kind, and for the shops with the most, a few of their types and titles. Counts, shop
names, types and titles only; the note never holds the feed's link. Always exits 0: a
deployment never fails because of this list.
"""
from __future__ import annotations

import json
import sys

# How many of a shop's reasons for holding rows back are printed, the most frequent first.
REASONS = 3
# How many shops, those with the most rows without a category, show their types and titles.
DETAILED = 15


def main() -> int:
    try:
        note = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("no prepared note on the server")
        return 0
    if not note.get("prepared"):
        print(f"nothing prepared: {note.get('reason')}")
        return 0
    intake = note.get("intake")
    if not isinstance(intake, dict) or "shops" not in intake:
        print(f"no shop list in the note: {intake}")
        return 0
    shops = intake["shops"]
    # The note's own `shops` counts the shops with a row past the feed's checks, also one
    # whose rows are all out of stock; this counts the shops a search can show.
    showing = sum(1 for shop in shops if shop["shown"] or shop["not_new"])
    print(
        f"{len(shops)} shops in the feed, {showing} with a product shown; {intake['rows']:,} rows: "
        f"shown {intake['shown']:,}, only when asked for {intake['not_new']:,}, held {intake['held']:,}"
    )
    print(f"{'rows':>9} {'shown':>9} {'asked':>7} {'held':>9}  shop: why held (rows)")
    for shop in shops:
        reasons = ", ".join(
            f"{reason} {count:,}" for reason, count in list(shop["held_reasons"].items())[:REASONS]
        )
        print(
            f"{shop['rows']:>9,} {shop['shown']:>9,} {shop['not_new']:>7,} {shop['held']:>9,}  "
            f"{shop['shop']}{': ' + reasons if reasons else ''}"
        )
    print()
    print_without_category(intake)
    return 0


def _kinds(buckets: dict | None) -> str:
    if buckets is None:
        return "kinds not read"
    return ", ".join(f"{name} {count:,}" for name, count in buckets.items())


def _kind_count(buckets: dict | None) -> str:
    return "-" if buckets is None else f"{buckets['kind']:,}"


def print_without_category(intake: dict) -> None:
    total = intake.get("without_category")
    if not isinstance(total, dict):
        print("no count of the rows without a category in the note")
        return
    print(
        f"rows without a category: {total['rows']:,}; held for that alone {total['only_this']:,}, "
        f"{total['with_product_type']:,} of them with the shop's own type"
    )
    print(f"  could be shown by their own type: {total['shown_by_type']:,} ({_kinds(total['kinds_by_type'])})")
    print(
        f"  could be shown by their title alone: {total['shown_by_title']:,} "
        f"({_kinds(total['kinds_by_title'])})"
    )
    print(
        f"{'no cat':>9} {'alone':>9} {'own type':>9} {'by type':>9} {'a kind':>9} {'by title':>9} "
        f"{'a kind':>9}  shop"
    )
    shops = sorted(
        (shop for shop in intake["shops"] if (shop.get("without_category") or {}).get("rows")),
        key=lambda shop: (-shop["without_category"]["rows"], shop["shop"]),
    )
    for index, shop in enumerate(shops):
        rows = shop["without_category"]
        print(
            f"{rows['rows']:>9,} {rows['only_this']:>9,} {rows['with_product_type']:>9,} "
            f"{rows['shown_by_type']:>9,} {_kind_count(rows['kinds_by_type']):>9} "
            f"{rows['shown_by_title']:>9,} {_kind_count(rows['kinds_by_title']):>9}  {shop['shop']}"
        )
        if index >= DETAILED:
            continue
        if rows["types"]:
            print("      types: " + "; ".join(f"{entry['value']} ({entry['rows']:,})" for entry in rows["types"]))
        if rows["titles"]:
            print("      titles: " + "; ".join(rows["titles"]))


if __name__ == "__main__":
    raise SystemExit(main())
