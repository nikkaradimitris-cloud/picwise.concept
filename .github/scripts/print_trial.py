"""The trial preparation's two notes side by side: the first link alone, and both links.

    python3 .github/scripts/print_trial.py one/ both/

Each folder holds a trial's prepared catalogue (`catalogue.json.gz`) and its note
(`prepared.json`).

Run by `.github/workflows/trial-prepare.yml` (owner, 2026-11-19). Printed: products and
shops each kept; the cap's share, its most a category and the size it worked out; every
category (Google's first two levels) with its products in each, the largest first; the
categories under 500 products ("thin", the next shops to look for); the shops the second
link adds and what each keeps. Counts and names only.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

THIN = 500


def _note(path: str) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _counts(folder: str) -> tuple[Counter, Counter]:
    """Products per category (the cap's) and per shop in a trial's prepared catalogue."""
    from picwise_providers.catalogue_cap import category_of, shop_of
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    prepared = read_prepared_catalogue_to_measure(Path(folder) / "catalogue.json.gz")
    aisles, shops = Counter(), Counter()
    if prepared is None:
        return aisles, shops
    for product in prepared.products:
        aisles[category_of(product)] += 1
        shops[shop_of(product)] += 1
    return aisles, shops


def main(argv: list[str]) -> int:
    one, both = _note(str(Path(argv[1]) / "prepared.json")), _note(str(Path(argv[2]) / "prepared.json"))
    for label, note in (("first link alone", one), ("both links", both)):
        if not note:
            print(f"{label}: no note (the preparation failed)")
            continue
        pool = note.get("google_pool") or {}
        print(
            f"{label}: prepared {note.get('prepared')}, {note.get('products')} products from {note.get('shops')} shops; "
            f"the cap: share {pool.get('share')}, most a category {pool.get('category_max')}, size {pool.get('size')}, "
            f"{pool.get('kept')} kept of {pool.get('products')}"
        )
    a, sa = _counts(argv[1])
    b, sb = _counts(argv[2])
    print("each category, products: first link alone -> both links (the largest first)")
    for name in sorted(set(a) | set(b), key=lambda name: (-b.get(name, 0), name)):
        print(f"  {a.get(name, 0):>8,} -> {b.get(name, 0):>8,}  {name}")
    thin = [name for name in b if b[name] < THIN]
    print(f"categories under {THIN} products with both links: {len(thin)} of {len(b)} listed")
    added = {name: count for name, count in sb.items() if name not in sa}
    print(f"shops the second link adds: {len(added)}")
    for name, count in sorted(added.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {count:>8,}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
