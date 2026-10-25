"""Print each shop of the server's prepared catalogue: its rows, what is shown, why the
rest is held back.

    ssh picwise 'sudo cat /srv/picwise/shared/public/prepared.json' | python3 deployment/server/print_shops.py

Run by .github/workflows/server-deploy.yml after a deployment. Reads the build's public
note (`tools/prepare_catalogue.py --static-dir`) on stdin: its `intake`, what each
shop's feed brings in (`picwise_providers.feed_intake`), which names every shop of the
feed, also one whose rows are all held back. So the log says which shops the feed link
carries, not only how many. Counts and shop names only; the note never holds the feed's
link. Always exits 0: a deployment never fails because of this list.
"""
from __future__ import annotations

import json
import sys

# How many of a shop's reasons for holding rows back are printed, the most frequent first.
REASONS = 3


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
