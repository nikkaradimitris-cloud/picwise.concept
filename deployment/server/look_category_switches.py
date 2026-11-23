"""The look before the «ανέβασε» of the categories' list (`docs/PICWISE_CATEGORY_SWITCHES.md`,
`picwise_providers.category_scope`, `data/category_switches.json`; the owner, 22/11 and 23/11).

Read-only, on GitHub's runner, beside the look of the shops' rule (`look_shop_rule.py`, which
prepares the catalogue twice from the copies of what the server prepared from: the list's
switch off, as the site runs, and on). This script adds what that look does not count:

    python3 deployment/server/look_category_switches.py note RUN/prepared.json --out categories-on.json
    python3 deployment/server/look_category_switches.py shown RUN --out shown-off.json
    python3 deployment/server/look_category_switches.py print --note categories-on.json --shown shown-off.json

`note` keeps the preparation's own note of the list (`categories` in `prepared.json`): what
each line holds of the products a card can show, what the list closed, and of which shops.
`shown` reads a catalogue prepared with the switch off (what the site shows today) and counts,
with the list read as if its switch were on, how many of the products shown it would close,
by the line that closes them, by top line and by shop. `print` writes both out.

Written and printed: counts, shops' names and the list's lines; never a link, an id or a key.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

CATALOGUE_NAME = "catalogue.json.gz"
# How many lines of a list are printed.
LISTED = 40


def note(path: Path) -> dict[str, Any]:
    """The preparation's note of the list, with the night's product count."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"products_shown": payload.get("products"), "categories": payload.get("categories")}


def shown(folder: Path) -> dict[str, Any]:
    """Of the products a catalogue shows, those the list, read as if on, would close."""
    from picwise_providers import ai_shelves, category_scope
    from picwise_providers.catalogue_cap import shop_of
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    switches = category_scope.read_switches()
    if switches is None:
        return {"error": "the list cannot be read"}
    switches = dataclasses.replace(switches, on=True)
    table = ai_shelves.answers()
    if not table:
        return {"error": "no answers of the AI's categories"}
    prepared = read_prepared_catalogue_to_measure(folder / CATALOGUE_NAME)
    if prepared is None:
        return {"error": "the catalogue cannot be read"}
    by_line: Counter = Counter()
    by_top: Counter = Counter()
    open_by_top: Counter = Counter()
    by_shop: Counter = Counter()
    open_by_shop: Counter = Counter()
    undecided = 0
    for product in prepared.products:
        levels = category_scope.product_levels(product, table)
        if levels is None:
            undecided += 1
            continue
        top = switches.by_levels.get(levels[:1])
        top_name = top.name if top is not None else f"(not on the list) {levels[0]}"
        if switches.is_open(levels):
            open_by_top[top_name] += 1
            open_by_shop[shop_of(product)] += 1
            continue
        line = switches.closing(levels)
        by_line[f"{line.name} ({line.google})" if line is not None else top_name] += 1
        by_top[top_name] += 1
        by_shop[shop_of(product)] += 1
    return {
        "products": len(prepared.products),
        "closed": sum(by_line.values()),
        "open": sum(open_by_top.values()),
        "undecided": undecided,
        "closed_by_line": by_line.most_common(),
        "closed_by_top": by_top.most_common(),
        "open_by_top": open_by_top.most_common(),
        "closed_by_shop": [[shop, count, open_by_shop.get(shop, 0)] for shop, count in by_shop.most_common()],
    }


def print_all(categories: Mapping[str, Any] | None, today: Mapping[str, Any] | None, say: Any = print) -> None:
    if today:
        if today.get("error"):
            say(f"today's catalogue: {today['error']}")
        else:
            say(f"of the {today['products']:,} products the site shows today (the switch off), the list would close "
                f"{today['closed']:,}, keep {today['open']:,}; {today['undecided']:,} have no category from the AI")
            say("closed, by top line: " + "; ".join(f"{name} {count:,}" for name, count in today["closed_by_top"]))
            say("open, by top line: " + "; ".join(f"{name} {count:,}" for name, count in today["open_by_top"]))
            say("closed, by the line that closes them (the most first):")
            for name, count in today["closed_by_line"][:LISTED * 2]:
                say(f"  {count:>7,}  {name}")
            say("closed, by shop (closed, kept):")
            for shop, count, kept in today["closed_by_shop"][:LISTED]:
                say(f"  {count:>7,}  {kept:>7,}  {shop}")
    note = (categories or {}).get("categories") or {}
    if not note:
        say("the list's note: none")
        return
    if note.get("products") is None:
        say(f"the list's note: it decided nothing ({note.get('why') or note.get('error')})")
        return
    say(f"the night with the switch on: of {note['products']:,} products a card can show (before the shops' rule and "
        f"the cap of a category), {note['closed']:,} closed, {note['open']:,} open, {note['undecided']:,} with no "
        f"category from the AI ({note.get('not_listed', 0):,} of the closed on a top line not on the list); the site then "
        f"shows {int((categories or {}).get('products_shown') or 0):,}")
    say("each line of the list: products a card can show under it, open or closed")
    for line in note.get("lines") or []:
        depth = str(line.get("google") or "").count(">")
        mark = "open  " if line.get("open") else ("CLOSED" if not line.get("on") else "closed above")
        say(f"  {'  ' * depth}{int(line.get('products') or 0):>9,}  {mark}  {line.get('name')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("note")
    one.add_argument("path", type=Path)
    one.add_argument("--out", type=Path, required=True)
    two = sub.add_parser("shown")
    two.add_argument("folder", type=Path)
    two.add_argument("--out", type=Path, required=True)
    three = sub.add_parser("print")
    three.add_argument("--note", type=Path)
    three.add_argument("--shown", type=Path)
    args = parser.parse_args(argv)
    if args.command == "note":
        args.out.write_text(json.dumps(note(args.path), ensure_ascii=False), encoding="utf-8")
        return 0
    if args.command == "shown":
        args.out.write_text(json.dumps(shown(args.folder), ensure_ascii=False), encoding="utf-8")
        return 0

    def read(path: Path | None) -> dict[str, Any] | None:
        if path is None or not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    print_all(read(args.note), read(args.shown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
