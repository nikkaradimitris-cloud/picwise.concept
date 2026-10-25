"""Print the shown products of the server's prepared catalogue whose kind may be wrong.

    ssh picwise 'sudo cat /srv/picwise/shared/public/prepared.json' | python3 deployment/server/print_kinds.py

Run by .github/workflows/server-deploy.yml after a deployment. Reads the build's public
note's `kinds` (`picwise_providers.kind_check`) on stdin: per kind, how many of its shown
products have a title naming none of the kind's nouns, and how many have a title naming
it while neither their product type nor their shelf does (owner, 2026-10-25: "Colleen
Hoover" books answering "vacuum cleaner"), with the cheapest three of each (price, shop,
title, shelf), since price first puts the cheapest at the top of a page. Suspects, not
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
    print(
        f"{kinds['products']:,} products shown as a kind; the title names none of its kinds: "
        f"{kinds['title_names_no_kind']:,}; only the title names one: "
        f"{'not measured' if only_title is None else format(only_title, ',')}"
    )
    print_list("the title names none of the kind's words", kinds["by_kind"], "title_without_kind")
    if "by_kind_only_title" in kinds:
        print_list(
            "only the title names the kind, neither the type nor the shelf",
            kinds["by_kind_only_title"],
            "only_title_names_it",
        )
    return 0


def print_list(heading: str, entries: list[dict], count: str) -> None:
    print()
    print(f"== {heading}: the kinds with the most, each with its cheapest (price | shop | title | shelf)")
    for entry in entries:
        print(f"{entry['kind']}: {entry[count]:,} of {entry['products']:,}")
        for example in entry["cheapest"]:
            print(f"    {example}")


if __name__ == "__main__":
    raise SystemExit(main())
