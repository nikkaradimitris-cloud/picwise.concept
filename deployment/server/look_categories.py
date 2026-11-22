"""A look at the category (the checks' rules 5.5; owner, 2026-11-21: «Όποιο προϊόν δεν μπαίνει
σε κατηγορία βγαίνει»): of the products the site shows now, how many the AI gave a line of
Google's taxonomy, how many it gave none ("no line fits", refused twice, a slip) and would
be cut once the checks are on, and how many it was never asked. Counts and shop names only.

    ssh picwise 'sudo systemd-run ... /usr/bin/python3 -' < deployment/server/look_categories.py

Run once by .github/workflows/server-look-categories.yml, on the server, as the site's user,
with the release in use; it changes nothing and asks nothing of anyone.
"""
from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path

PREPARED = "/srv/picwise/shared/prepared/catalogue.json.gz"
ANSWERS = "/srv/picwise/assist/shelves/answers.jsonl.gz"
MOST_TRIES = 2
SHOPS_LISTED = 25


def main() -> int:
    from picwise_providers.ai_shelves import is_slip, key_of
    from picwise_providers.catalogue_cap import shop_of
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    lines: dict[str, str] = {}
    refused: set[str] = set()
    once: set[str] = set()
    with gzip.open(ANSWERS, "rt", encoding="utf-8") as handle:
        for text in handle:
            try:
                record = json.loads(text)
            except ValueError:
                continue
            key, line = record.get("k"), record.get("line")
            if isinstance(key, str) and isinstance(line, str):
                lines[key] = line
            elif isinstance(key, str) and line is None:
                (refused if int(record.get("tries") or 0) >= MOST_TRIES else once).add(key)
    print(f"the answers: {len(lines):,} keys with an answer, {len(refused):,} refused twice, {len(once):,} refused once")
    prepared = read_prepared_catalogue_to_measure(Path(PREPARED))
    states: Counter = Counter()
    none_by_shop: Counter = Counter()
    unasked_by_shop: Counter = Counter()
    shown_by_shop: Counter = Counter()
    for product in prepared.products:
        raw = product.raw if hasattr(product.raw, "get") else {}
        key = key_of(product.title, product.brand, raw)
        shop = shop_of(product)
        shown_by_shop[shop] += 1
        line = lines.get(key)
        if line is None:
            state = "refused twice" if key in refused else "not asked yet"
        elif not line:
            state = "no line fits"
        elif is_slip(line):
            state = "a slip"
        else:
            state = "a line"
        states[state] += 1
        if state in ("refused twice", "no line fits", "a slip"):
            none_by_shop[shop] += 1
        elif state == "not asked yet":
            unasked_by_shop[shop] += 1
    total = sum(states.values())
    print(f"the products the site shows (prepared {prepared.prepared_at:%Y-%m-%d %H:%M} UTC): {total:,}")
    for state, count in states.most_common():
        print(f"  {state}: {count:,} ({100 * count / max(1, total):.1f}%)")
    cut = sum(none_by_shop.values())
    print(f"would be cut as 'no category': {cut:,} ({100 * cut / max(1, total):.1f}%; the brake holds over 10%)")
    print("the shops with the most products with no category (of their shown):")
    for shop, count in none_by_shop.most_common(SHOPS_LISTED):
        print(f"  {shop}: {count:,} of {shown_by_shop[shop]:,}")
    print("the shops with the most products not asked yet (asked the morning after the deployment):")
    for shop, count in unasked_by_shop.most_common(10):
        print(f"  {shop}: {count:,} of {shown_by_shop[shop]:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
