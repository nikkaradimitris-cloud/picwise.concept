"""How the products a search can show spread over departments, aisles, shops and kinds,
and what a cap on each one's share would cut: measured only, nothing shown changes.

Owner, 2026-10-26: a shop of 100,000 watches added to 200,000 products makes PicWise
look like a watch site, so no kind should hold more than about 15% («για παράδειγμα και
όχι περιοριστικά 15%») of all products, «έτσι ώστε να έχουμε μία ωραία κατανομή ειδών»,
which also helps the checks; then «Ναι» to measuring it first. Finediam (jewellery) held
70% of the server's 518,041 shown products, and most jewellery has no PicWise kind
("ring" gives none), so the share is measured on several groupings:

- the department and the aisle: the top and the first two levels of the product's shelf
  when it is one of Google's taxonomy (British names read as the US ones, as the aisle
  rule reads them), else one group for the shops' own categories;
- the shop;
- the kind, each product under its narrowest real kind, of the products with one.

For each, the largest groups and their shares, and what a cap of `CAP_SHARE` of the
total would keep: each group keeps at most the same number C, the largest C such that
no group keeps more than that share of what all keep, which needs at least 1/share
groups (7 for 15%); with fewer, no C holds and the note says so. Also the owner's
"enough" put to them on 26/10: how many kinds have products from at least 3 shops.
Counts and names only; the note never holds a link.
"""
from __future__ import annotations

import heapq
from collections import Counter
from functools import lru_cache
from typing import Any, Collection, Mapping, Sequence

from picwise_nlu.concept_understanding import _BREADCRUMB_SPLIT_RE, _BRITISH_AISLE_NAMES, _aisle_departments
from picwise_nlu.product_concepts import broader_concepts

from .contracts import ProviderProduct
from .normalization import extract_merchant_name

CAP_SHARE = 0.15
# How many of the largest groups, and of the groups a cap cuts most, the note lists.
_LISTED = 10
OWN_CATEGORIES = "(the shops' own categories)"
NO_SHOP = "(no shop named)"


def capped_size(sizes: Sequence[int], share: float = CAP_SHARE) -> int | None:
    """The most products a group may keep so that, each group keeping at most that many,
    none keeps more than `share` of what all keep; the sizes themselves' largest when no
    group is over; None when no size above 0 holds (too few groups)."""
    ordered = sorted((size for size in sizes if size > 0), reverse=True)
    total = sum(ordered)
    if not ordered:
        return 0
    if ordered[0] <= share * total:
        return ordered[0]
    # The k largest groups capped at C, the others whole: C = share * (k * C + rest).
    rest = total
    for k in range(1, len(ordered) + 1):
        rest -= ordered[k - 1]
        if share * k >= 1:
            return None
        cap = share * rest / (1 - share * k)
        below = ordered[k] if k < len(ordered) else 0
        if below <= cap <= ordered[k - 1]:
            # Below one product a group, only cutting everything would hold.
            return int(cap) if cap >= 1 else None
    return None


def _view(counts: Counter, share: float) -> dict[str, Any]:
    total = sum(counts.values())
    cap = capped_size(list(counts.values()), share)
    largest = heapq.nsmallest(_LISTED, counts.items(), key=lambda item: (-item[1], item[0]))
    view: dict[str, Any] = {
        "groups": len(counts),
        "products": total,
        "largest": [
            {"name": name, "products": size, "share": round(size / total, 4) if total else 0.0}
            for name, size in largest
        ],
        "over": sum(1 for size in counts.values() if total and size > share * total),
        "cap": cap,
    }
    if cap is None:
        view.update(kept=None, cut=None, cut_by_group=[])
        return view
    cut = {name: size - cap for name, size in counts.items() if size > cap}
    kept = total - sum(cut.values())
    view.update(
        kept=kept,
        cut=total - kept,
        cut_by_group=[
            {"name": name, "cut": size, "kept": counts[name] - size}
            for name, size in heapq.nsmallest(_LISTED, cut.items(), key=lambda item: (-item[1], item[0]))
        ],
    )
    return view


def _shelf_groups(category: str) -> tuple[str, str]:
    """The department and the aisle of a product's shelf, when it is one of Google's."""
    names = [
        _BRITISH_AISLE_NAMES.get(name, name)
        for name in (" ".join(segment.lower().split()) for segment in _BREADCRUMB_SPLIT_RE.split(str(category or "")))
        if name
    ]
    if not names or names[0] not in _aisle_departments():
        return OWN_CATEGORIES, OWN_CATEGORIES
    return names[0], " > ".join(names[:2])


@lru_cache(maxsize=None)
def _depth(kind: str) -> int:
    return len(broader_concepts(kind))


def _narrowest_kind(kinds: Collection[str]) -> str:
    real = [kind for kind in kinds if not kind.startswith("__")]
    if not real:
        return ""
    return max(real, key=lambda kind: (_depth(kind), kind))


def measure_catalogue_balance(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    *,
    share: float = CAP_SHARE,
) -> dict[str, Any]:
    """The shares of the shown products and what a cap would cut (module docstring).
    `kinds` holds each product's kinds, as the prepared catalogue reads them."""
    departments: Counter = Counter()
    aisles: Counter = Counter()
    shops: Counter = Counter()
    by_kind: Counter = Counter()
    shops_by_kind: dict[str, set[str]] = {}
    for product, product_kinds in zip(products, kinds):
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        department, aisle = _shelf_groups(product.category_text)
        departments[department] += 1
        aisles[aisle] += 1
        shop = " ".join(str(extract_merchant_name(raw) or "").split()) or NO_SHOP
        shops[shop] += 1
        kind = _narrowest_kind(product_kinds)
        if kind:
            by_kind[kind] += 1
            shops_by_kind.setdefault(kind, set()).add(shop)
    spread = Counter(len(found) for found in shops_by_kind.values())
    return {
        "share": share,
        "products": len(products),
        "department": _view(departments, share),
        "aisle": _view(aisles, share),
        "shop": _view(shops, share),
        "kind": _view(by_kind, share),
        "no_kind": len(products) - sum(by_kind.values()),
        "kinds_by_shops": {
            "kinds": len(shops_by_kind),
            "one_shop": spread.get(1, 0),
            "two_shops": spread.get(2, 0),
            "three_or_more": sum(count for shops_count, count in spread.items() if shops_count >= 3),
        },
    }
