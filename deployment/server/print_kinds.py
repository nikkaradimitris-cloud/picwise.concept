"""Print the shown products of the server's prepared catalogue whose kind may be wrong.

    ssh picwise 'sudo cat /srv/picwise/shared/public/prepared.json' | python3 deployment/server/print_kinds.py

Run by .github/workflows/server-deploy.yml after a deployment. Reads the build's public
note's `kinds` (`picwise_providers.kind_check`) on stdin: per kind, how many of its shown
products have a title naming none of the kind's nouns, and how many have a title naming
it while neither their product type nor their shelf does (owner, 2026-10-25: "Colleen
Hoover" books answering "vacuum cleaner"), with the cheapest three of each (price, shop,
title, shelf), since price first puts the cheapest at the top of a page, and the
shelves they most often sit on, whole, as the kind reader saw them; then the products a
title's kind on another department's aisle made doubtful, per kind they were read as
before; and how often a title alone gives the kind the shelf gives (`title_alone`, owner,
2026-10-25: before any row without a category is shown by its title). Suspects, not
mistakes. The note holds no link. Always exits 0: a deployment never fails because of
this list.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        note = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("no prepared note on the server")
        return 0
    if not note.get("prepared"):
        print(f"nothing prepared: {note.get('reason')}")
        return 0
    kinds = note.get("kinds")
    if not isinstance(kinds, dict) or "by_kind" not in kinds:
        print(f"no kinds in the note: {kinds}")
        return 0
    only_title = kinds.get("only_title_names_kind")
    doubted = kinds.get("doubted_by_aisle")
    print(
        f"{kinds['products']:,} products shown as a kind; the title names none of its kinds: "
        f"{kinds['title_names_no_kind']:,}; only the title names one: {_count(only_title)}; "
        f"made doubtful by their aisle: {_count(doubted)}"
    )
    print_list("the title names none of the kind's words", kinds["by_kind"], "title_without_kind")
    if "by_kind_only_title" in kinds:
        print_list(
            "only the title names the kind, neither the type nor the shelf",
            kinds["by_kind_only_title"],
            "only_title_names_it",
        )
    if doubted is not None:
        print_list(
            "made doubtful by their aisle, per kind they were read as before",
            kinds.get("by_kind_doubted_by_aisle") or [],
            "doubted_by_its_aisle",
            of="doubted; still of the kind:",
        )
    print_title_alone(note.get("title_alone"))
    return 0


def _share(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "-"


def print_title_alone(title_alone: object) -> None:
    """How often a title alone gives the kind the shelf gives: in all, per shop, and the
    most frequent pairs of the shelf's kind and the title's other kind."""
    print()
    if not isinstance(title_alone, dict) or "products" not in title_alone:
        print(f"== the title alone against the shelf: not measured ({title_alone})")
        return
    gives = title_alone["agrees"] + title_alone["differs"]
    print(
        f"== the title alone against the shelf: {title_alone['products']:,} products with a kind from their "
        f"shelf; the title alone gives one to {gives:,} ({_share(gives, title_alone['products'])}), "
        f"the shelf's {title_alone['agrees']:,} ({_share(title_alone['agrees'], gives)} of those), another "
        f"{title_alone['differs']:,}; none: an accessory {title_alone['accessory']:,}, doubtful "
        f"{title_alone['doubtful']:,}, nothing {title_alone['none']:,}"
    )
    print(f"{'products':>9} {'a kind':>7} {'agrees':>7}  shop")
    for shop in title_alone["by_shop"]:
        shop_gives = shop["agrees"] + shop["differs"]
        print(
            f"{shop['products']:>9,} {_share(shop_gives, shop['products']):>7} "
            f"{_share(shop['agrees'], shop_gives):>7}  {shop['shop']}"
        )
    print("-- the shelf's kind -> the title's other kind, the most frequent, each with its cheapest")
    for pair in title_alone["differs_by_pair"]:
        print(f"{pair['shelf_kind']} -> {pair['title_kind']}: {pair['products']:,}")
        for example in pair["cheapest"]:
            print(f"    {example}")


def _count(value: int | None) -> str:
    return "not measured" if value is None else format(value, ",")


def print_list(heading: str, entries: list[dict], count: str, of: str = "of") -> None:
    print()
    print(f"== {heading}: the kinds with the most, each with its cheapest (price | shop | title | shelf)")
    for entry in entries:
        print(f"{entry['kind']}: {entry[count]:,} {of} {entry['products']:,}")
        for example in entry["cheapest"]:
            print(f"    {example}")
        # The shelves its suspects most often sit on, whole, as the kind reader saw them.
        if entry.get("shelves"):
            shelves = "; ".join(f"{shelf['shelf']} ({shelf['products']:,})" for shelf in entry["shelves"])
            print(f"    shelves: {shelves}")


if __name__ == "__main__":
    raise SystemExit(main())
