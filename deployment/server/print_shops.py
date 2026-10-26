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
kind, and for the shops with the most, a few of their types and titles; and (owner,
2026-10-26) where else their category may hide: their filled columns, the values of
those named like a category, and the shelves their shop's address names; then what the
shops' own catalogues and the rows' barcodes gave them (`shop_catalogues`). Counts, shop
names, types, titles and words only; the note never holds a link. Always exits 0: a
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
    print_shop_catalogues(note)
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
    if "address" in total:
        print("  of those, " + _address(total["address"]))
    if "barcode" in total:
        print("  of those, " + _barcode(total["barcode"]))
        print("  of those, " + _description(total["description"]))
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
        print_hints(rows.get("hints"))


def _address(counts: dict) -> str:
    return (
        f"the shop's address names shelves for {counts['names_shelves']:,} of {counts['rows']:,}, "
        f"a kind for {counts['a_kind']:,}; with the title's kind too {counts['title_kind_too']:,}, "
        f"agreeing {counts['agrees']:,}"
    )


def _barcode(counts: dict) -> str:
    return (
        f"another shop's category for the same barcode: a barcode on {counts['with_barcode']:,} of "
        f"{counts['rows']:,}, a category found for {counts['found_with_category']:,}, a kind for "
        f"{counts['a_kind']:,} ({counts['title_gives_none']:,} where the title gives none); with the title's kind "
        f"too {counts['title_kind_too']:,}, agreeing {counts['agrees']:,}"
    )


def _description(counts: dict) -> str:
    return (
        f"where the title gives no kind ({counts['title_gives_none']:,}), the description's first sentence "
        f"gives one to {counts['description_gives']:,}"
    )


def print_shop_catalogues(note: dict) -> None:
    """What the shops' own catalogues and the rows' barcodes gave the feed's rows
    (owner, 2026-10-26: «Θα κάνεις το 2 και το 3»; `picwise_providers.shop_catalogue`)."""
    found = note.get("shop_catalogues")
    if not isinstance(found, dict):
        # A note written before the shops' catalogues were read.
        return
    print()
    if "error" in found:
        print(f"the shops' catalogues: not applied ({found['error']})")
        return
    written = f", written {found['written_at']}" if found.get("written_at") else ""
    print(f"the shops' catalogues: the bot's file {found['file']}{written}; {found['shops_known']} shops in it")
    if found["shops_known"]:
        print(
            f"  their rows: {found['rows']:,}, found in their shop's catalogue {found['matched']:,}; the shop says "
            f"sold out {found['sold_out']:,} (the feed called {found['sold_out_feed_in_stock']:,} of them in stock), "
            f"held; stock seen too long ago {found['stock_too_old']:,}"
        )
        print(
            f"  without a category from the feed {found['without_category']:,}: given their shop's type, with the "
            f"kind it names, {found['by_type']:,}; the type names no kind {found['type_no_kind']:,}; no type "
            f"{found['no_type']:,}; not in the catalogue {found['not_found']:,}"
        )
    if found.get("types_no_kind"):
        print("  types naming no kind: " + "; ".join(f"{entry['value']} ({entry['rows']:,})" for entry in found["types_no_kind"]))
    barcode = found.get("barcode") or {}
    if barcode:
        print(
            f"  by barcode, of the {barcode['without_category']:,} rows then without a category: a barcode on "
            f"{barcode['with_barcode']:,} ({barcode['too_common']:,} on too many rows), another row's category for "
            f"{barcode['found']:,}; joined with its kind {barcode['joined']:,}, no kind {barcode['no_kind']:,}"
        )
    if found.get("barcode_shops"):
        print("  joined by barcode: " + "; ".join(f"{entry['shop']} {entry['joined']:,}" for entry in found["barcode_shops"][:10]))
    if not found.get("shops"):
        return
    print(
        f"{'rows':>9} {'found':>9} {'sold out':>9} {'no cat':>9} {'by type':>9} {'no kind':>9} {'no type':>9} "
        f"{'not found':>9}  shop: the bot's last round"
    )
    for shop in found["shops"]:
        print(
            f"{shop['rows']:>9,} {shop['matched']:>9,} {shop['sold_out']:>9,} {shop['without_category']:>9,} "
            f"{shop['by_type']:>9,} {shop['type_no_kind']:>9,} {shop['no_type']:>9,} {shop['not_found']:>9,}  "
            f"{shop['shop']}: {shop['status'] or '-'}, {shop['products']:,} products known"
        )


def print_hints(hints: dict | None) -> None:
    """Where else a shop's rows without a category may name one: their filled columns,
    the values of the columns named like a category, and their address's shelves."""
    if not hints:
        return
    print("      columns: " + "; ".join(f"{entry['column']} ({entry['rows']:,})" for entry in hints["columns"]))
    for column, values in hints["values"].items():
        print(f"      {column}: " + "; ".join(f"{entry['value']} ({entry['rows']:,})" for entry in values))
    print("      " + _address(hints["address"]))
    if hints["address_shelves"]:
        shelves = "; ".join(f"{entry['value']} ({entry['rows']:,})" for entry in hints["address_shelves"])
        print(f"      address shelves: {shelves}")
    if "barcode" in hints:
        print("      " + _barcode(hints["barcode"]))
        print("      " + _description(hints["description"]))


if __name__ == "__main__":
    raise SystemExit(main())
