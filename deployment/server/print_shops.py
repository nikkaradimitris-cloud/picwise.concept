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
shops' own catalogues and the rows' barcodes gave them (`shop_catalogues`); and how many
products, by barcode, two or more shops sell, in all and per category
(`balance.shared_products`; 2026-11-11), and by brand and part number
(`balance.shared_by_brand_and_part`), and how each shop was taken in: its products the
site answers from, with a kind, with a barcode, sold by another shop too
(`balance.by_shop`; 2026-11-12). Counts, shop
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
# How many of the largest kinds only one or two shops sell are printed.
FEW_SHOPS_LISTED = 25
# How many categories are printed with the products two or more shops sell, the most first.
SHARED_LISTED = 10
# How many of the shops' types that name no kind are printed, the most first.
WORDS_LISTED = 30


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
    print_silent_shops(shops)
    print()
    print_memory(note)
    print_intake_change(note)
    print_without_category(intake)
    print_shop_catalogues(note)
    print_balance(note)
    return 0


def print_silent_shops(shops: list[dict]) -> None:
    """The shops in the feed that give no product, each with every reason its rows are
    held: the feed's, and behind a missing category the card's own
    (`feed_intake._held_behind_category`; the audit's fixes, 2026-11-12: five shops the
    owner had joined gave none, and the note said only "no category"). Nothing when
    every shop gives a product."""
    silent = [shop for shop in shops if shop["rows"] and not shop["shown"] and not shop["not_new"]]
    if not silent:
        return
    print(f"shops that give no product: {len(silent)}")
    for shop in sorted(silent, key=lambda shop: (-shop["rows"], shop["shop"])):
        held = ", ".join(f"{reason} {count:,}" for reason, count in shop["held_reasons"].items())
        behind = (shop.get("without_category") or {}).get("also_held_for") or {}
        said = (shop.get("without_category") or {}).get("out_of_stock_by") or {}
        line = f"  {shop['rows']:>7,} rows  {shop['shop']}: {held or 'none held'}"
        if behind:
            line += "; behind the missing category: " + ", ".join(f"{reason} {count:,}" for reason, count in behind.items())
        if said:
            line += "; out of stock by " + ", ".join(f"{value} ({count:,})" for value, count in said.items())
        print(line)


def print_memory(note: dict) -> None:
    """What the catalogue's memory says after the night (`catalogue_memory`, 2026-11-12);
    nothing for a note without it."""
    memory = note.get("memory")
    if not isinstance(memory, dict):
        return
    if "error" in memory:
        print(f"the catalogue's memory: not written ({memory['error']})")
        print()
        return
    line = (
        f"the catalogue's memory: {memory['products_known']:,} products over {memory['nights']} nights; "
        f"the night of {memory['night']}: {memory['seen_tonight']:,} seen, {memory['new_tonight']:,} new, "
        f"{memory['price_changed_tonight']:,} with a new price"
    )
    if memory.get("compared_with"):
        line += f", {memory['gone_since']:,} seen on {memory['compared_with']} and not since"
    print(line)
    print()


def print_intake_change(note: dict) -> None:
    """The shops whose feed shrank or vanished since the preparation before, and the new
    ones (`tools/prepare_catalogue.py`, `_intake_change`); nothing for a note without it."""
    change = note.get("intake_change")
    if not isinstance(change, dict) or not change.get("compared_with"):
        return
    print(f"since the preparation of {change['compared_with']}:")
    for label, key in (("no rows now", "gone"), ("fewer than half the rows", "shrunk")):
        entries = change.get(key) or []
        if entries:
            print(
                f"  {label}: "
                + "; ".join(f"{entry['shop']} ({entry['rows_before']:,} -> {entry['rows']:,})" for entry in entries)
            )
    if change.get("new"):
        print("  new shops: " + ", ".join(change["new"]))
    if not (change.get("gone") or change.get("shrunk") or change.get("new")):
        print("  every shop's feed came as large as before or larger; no new shop")
    print()


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
    if total.get("also_held_for"):
        print(
            "  held for something else too, behind the missing category: "
            + ", ".join(f"{reason} {count:,}" for reason, count in total["also_held_for"].items())
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
        if rows.get("also_held_for"):
            print("      also held for: " + ", ".join(f"{reason} {count:,}" for reason, count in rows["also_held_for"].items()))
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


# How many of the largest groups, and of those a cap cuts most, are printed per grouping.
BALANCE_LISTED = 5


def print_balance(note: dict) -> None:
    """How the shown products spread over departments, aisles, shops and kinds, and what
    a cap on a share would cut, measured only (owner, 2026-10-26: no kind over about 15%;
    «Ναι» to measuring it first; `picwise_providers.catalogue_balance`)."""
    found = note.get("balance")
    if not isinstance(found, dict):
        # A note written before the shares were measured.
        return
    print()
    if "error" in found:
        print(f"the shares of the shown products: not measured ({found['error']})")
        return
    share = f"{100 * found['share']:g}%"
    print(
        f"the shares of the {found['products']:,} products shown, and a cap of {share} on each "
        f"(measured only; nothing shown changes):"
    )
    for key, label in (("department", "department"), ("aisle", "aisle"), ("shop", "shop"), ("kind", "kind")):
        view = found[key]
        named = "; ".join(
            f"{entry['name']} {entry['products']:,} ({100 * entry['share']:.1f}%)"
            for entry in view["largest"][:BALANCE_LISTED]
        )
        extra = f", of the {view['products']:,} with a kind" if key == "kind" else ""
        print(f"  by {label}: {view['groups']:,} groups{extra}, {view['over']:,} over {share}; the largest: {named}")
        if view["cap"] is None:
            print(f"    a cap of {share} cannot hold: too few groups of products")
            continue
        cuts = "; ".join(f"{entry['name']} -{entry['cut']:,}" for entry in view["cut_by_group"][:BALANCE_LISTED])
        print(
            f"    capped at {view['cap']:,} a group: {view['kept']:,} kept, {view['cut']:,} cut"
            + (f": {cuts}" if cuts else "")
        )
    spread = found["kinds_by_shops"]
    print(
        f"  kinds with products from at least 3 shops: {spread['three_or_more']:,} of {spread['kinds']:,} "
        f"(from one shop {spread['one_shop']:,}, from two {spread['two_shops']:,}); shown with no kind "
        f"{found['no_kind']:,}"
    )
    few = found.get("kinds_from_few_shops") or []
    if few:
        # Where a shop added counts most: the largest kinds only one or two shops sell.
        print(
            "  the largest kinds from one or two shops: "
            + "; ".join(
                f"{entry['kind']} {entry['products']:,} ({', '.join(entry['shops'])})"
                for entry in few[:FEW_SHOPS_LISTED]
            )
        )
    words = found.get("words_to_learn")
    if words:
        print(
            "  the shops' own types of the products kept with no kind, to review (shop_words.py), the most first: "
            + "; ".join(f"{entry['type']} ({entry['shop']}) {entry['products']:,}" for entry in words[:WORDS_LISTED])
        )
    shared = found.get("shared_products")
    if isinstance(shared, dict):
        # The products the pages for Google start from (docs/PICWISE_AUDIT_FIXES.md, 4.A.2).
        print(
            f"  products two or more shops sell, by barcode: {shared['two_or_more_shops']:,} of the "
            f"{shared['barcodes']:,} with a barcode"
            + (
                "; by category: "
                + "; ".join(
                    f"{entry['category']} {entry['two_or_more_shops']:,} of {entry['barcodes']:,}"
                    for entry in shared["by_category"][:SHARED_LISTED]
                )
                if shared["by_category"]
                else ""
            )
        )
    parts = found.get("shared_by_brand_and_part")
    if isinstance(parts, dict):
        print(
            f"  products two or more shops sell, by brand and part number: {parts['two_or_more_shops']:,} of the "
            f"{parts['products']:,} with both; {parts['not_joined_by_barcode']:,} of them no barcode joins"
        )
    print_by_shop(found.get("by_shop"), note.get("intake"))


def print_by_shop(by_shop: object, intake: object) -> None:
    """How each shop was taken in: of the rows its feed brought, the products a card can
    show, those the site answers from (after the cap), and of these how many have a kind,
    a barcode, and are sold by another shop too (docs/PICWISE_AUDIT_FIXES.md, 4.E.12)."""
    if not isinstance(by_shop, list) or not by_shop:
        # A note written before it was measured.
        return
    fed = {
        shop.get("shop"): shop
        for shop in (intake.get("shops") if isinstance(intake, dict) else None) or []
        if isinstance(shop, dict)
    }
    print()
    print("how each shop was taken in (the site answers from 'kept'; the rest are counts of the kept):")
    print(f"{'rows':>9} {'shown':>9} {'kept':>8} {'a kind':>8} {'barcode':>8} {'2+ shops':>8}  shop")
    for entry in by_shop:
        # The feed's list names a shop with no name "?", the shares "(no shop named)".
        feed = fed.get(entry["shop"]) or (fed.get("?") if entry["shop"] == "(no shop named)" else None) or {}
        rows, shown = feed.get("rows"), feed.get("shown")
        print(
            f"{(format(rows, ',') if isinstance(rows, int) else '?'):>9} "
            f"{(format(shown, ',') if isinstance(shown, int) else '?'):>9} "
            f"{entry['products']:>8,} {entry['with_kind']:>8,} {entry['with_barcode']:>8,} "
            f"{entry['another_shop_too']:>8,}  {entry['shop']}"
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
