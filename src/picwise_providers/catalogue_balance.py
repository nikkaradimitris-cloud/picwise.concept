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
"enough" put to them on 26/10: how many kinds have products from at least 3 shops, and
(2026-11-10) which kinds only one or two shops sell, with those shops' names.

Also how many products two or more shops sell (`shared_products`; the audit's fixes,
2026-11-11, `docs/PICWISE_AUDIT_FIXES.md` 4.A.2: the product pages for Google start
from those products, and nobody knew how many there are). A product is a barcode whose
check digit agrees (`product_identity.valid_gtin`, padded to 14 digits so the UPC-12 and
EAN-13 forms of one code agree), counted once however many shops and rows carry it; it
is sold by two or more shops when two shop names or more carry it, so one shop listing
it twice does not make it so, and a row with no barcode never counts. Per category, the
category being the first two levels of the shop's Google shelf as the cap reads it
(`catalogue_cap`; "aisle" above), each barcode counted once, under the category most of
its rows name (ties by name), so the categories add up to the whole.

Also, per shop, how it was taken in (`by_shop`; 2026-11-12, the mechanism's step 12,
`docs/PICWISE_AUDIT_FIXES.md` 4.E): of its products the site answers from, how many
have a kind, how many a barcode, and how many another shop sells too, by barcode; so
the morning after a shop is added says how much of it a visitor can find. And how many
products two or more shops sell by brand and manufacturer's part number
(`shared_by_brand_and_part`; step 15), read from every product whether or not it has a
barcode, as `product_identity.same_product_key` reads them (the MPN columns only, a
value that looks like a code, with a brand), and how many of those no barcode already
joins: the overlap a barcode alone does not show.
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
from .product_identity import BRAND_KEYS, MPN_KEYS, same_product_key, valid_gtin

CAP_SHARE = 0.15
# How many of the largest groups, and of the groups a cap cuts most, the note lists.
_LISTED = 10
# How many of the kinds only one or two shops sell the note names, the largest first.
_FEW_SHOPS_LISTED = 200
# How many categories the count of products two or more shops sell lists, the most first.
_SHARED_LISTED = 200
# How many of the shops' types that name no kind the note lists, the most first, and how
# many titles of each (`shop_words`; 2026-11-12).
_WORDS_LISTED = 100
# A type written on fewer products is a product's own description, not a shop's word
# (the first night's list, 12/11, was a camera shop's one-product paths).
_WORDS_MIN_PRODUCTS = 2
_WORD_TITLES = 2
_WORD_TITLE_LENGTH = 90
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


def _shared_products(barcodes: Mapping[str, tuple[set[str], Counter]]) -> dict[str, Any]:
    """How many products, by barcode, two or more shops sell, in all and per category
    (module docstring). `barcodes` maps each barcode to the shops and the categories of
    its rows."""
    by_category: dict[str, list[int]] = {}
    shared = 0
    for shops, categories in barcodes.values():
        category = min(categories.items(), key=lambda item: (-item[1], item[0]))[0]
        counts = by_category.setdefault(category, [0, 0])
        counts[0] += 1
        if len(shops) >= 2:
            counts[1] += 1
            shared += 1
    listed = sorted(by_category.items(), key=lambda item: (-item[1][1], -item[1][0], item[0]))
    return {
        "barcodes": len(barcodes),
        "two_or_more_shops": shared,
        "categories": len(by_category),
        "by_category": [
            {"category": name, "barcodes": counts[0], "two_or_more_shops": counts[1]}
            for name, counts in listed[:_SHARED_LISTED]
        ],
    }


def _brand_and_part(raw: Mapping[str, Any], brand: str) -> str:
    """The product's brand and part number key, whether or not it has a barcode: the key
    `same_product_key` gives a row without one."""
    return same_product_key({key: raw.get(key) for key in MPN_KEYS + BRAND_KEYS}, brand=brand)


def _shared_by_brand_and_part(parts: Mapping[str, tuple[set[str], set[str]]],
                              barcodes: Mapping[str, tuple[set[str], Counter]]) -> dict[str, Any]:
    """How many products, by brand and part number, two or more shops sell, and how many
    of those no barcode of theirs already joins across shops (module docstring). `parts`
    maps each key to its shops and its rows' barcodes."""
    shared = [codes for shops, codes in parts.values() if len(shops) >= 2]
    return {
        "products": len(parts),
        "two_or_more_shops": len(shared),
        "not_joined_by_barcode": sum(
            1 for codes in shared if not any(len(barcodes[code][0]) >= 2 for code in codes)
        ),
    }


def _by_shop(shops: Counter, with_kind: Counter, with_barcode: Counter,
             sold: Sequence[tuple[str, str]], barcodes: Mapping[str, tuple[set[str], Counter]]) -> list[dict[str, Any]]:
    """Per shop, how it was taken in (module docstring), the shop with the most first."""
    shared: Counter = Counter(shop for shop, code in sold if len(barcodes[code][0]) >= 2)
    return [
        {
            "shop": shop,
            "products": count,
            "with_kind": with_kind.get(shop, 0),
            "with_barcode": with_barcode.get(shop, 0),
            "another_shop_too": shared.get(shop, 0),
        }
        for shop, count in sorted(shops.items(), key=lambda item: (-item[1], item[0]))
    ]


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
    barcodes: dict[str, tuple[set[str], Counter]] = {}
    words: dict[tuple[str, str], list] = {}
    with_kind: Counter = Counter()
    with_barcode: Counter = Counter()
    sold: list[tuple[str, str]] = []
    parts: dict[str, tuple[set[str], set[str]]] = {}
    for product, product_kinds in zip(products, kinds):
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        department, aisle = _shelf_groups(product.category_text)
        departments[department] += 1
        aisles[aisle] += 1
        shop = " ".join(str(extract_merchant_name(raw) or "").split()) or NO_SHOP
        shops[shop] += 1
        gtin = valid_gtin(raw)
        if gtin:
            sellers, shelves = barcodes.setdefault(gtin.zfill(14), (set(), Counter()))
            sellers.add(shop)
            shelves[aisle] += 1
            with_barcode[shop] += 1
            sold.append((shop, gtin.zfill(14)))
        part = _brand_and_part(raw, str(product.brand or ""))
        if part:
            part_shops, part_codes = parts.setdefault(part, (set(), set()))
            part_shops.add(shop)
            if gtin:
                part_codes.add(gtin.zfill(14))
        kind = _narrowest_kind(product_kinds)
        product_type = " ".join(str(raw.get("product_type") or "").split())
        if not kind and product_type:
            entry = words.setdefault((shop, product_type), [0, []])
            entry[0] += 1
            if len(entry[1]) < _WORD_TITLES:
                entry[1].append(" ".join(str(product.title or "").split())[:_WORD_TITLE_LENGTH])
        if kind:
            by_kind[kind] += 1
            with_kind[shop] += 1
            shops_by_kind.setdefault(kind, set()).add(shop)
    spread = Counter(len(found) for found in shops_by_kind.values())
    # The kinds only one or two shops sell, the largest first: where a page of four has
    # nothing to compare between shops, and so where a shop added counts most (the audit,
    # 2026-11-10: of 265 kinds, 99 came from one shop and 76 from two; owner, the same
    # day: «Θα προσθέσουμε καταστήματα ... στις κατηγορίες που λείπουν»).
    few_shops = sorted(
        (
            {"kind": kind, "products": by_kind[kind], "shops": sorted(found)}
            for kind, found in shops_by_kind.items()
            if len(found) <= 2
        ),
        key=lambda entry: (-entry["products"], entry["kind"]),
    )
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
        "kinds_from_few_shops": few_shops[:_FEW_SHOPS_LISTED],
        "shared_products": _shared_products(barcodes),
        "shared_by_brand_and_part": _shared_by_brand_and_part(parts, barcodes),
        "by_shop": _by_shop(shops, with_kind, with_barcode, sold, barcodes),
        # The shops' own types of the products kept with no kind: what to review for
        # `shop_words.LEARNED_TYPES` or for the lexicon, the most first.
        "words_to_learn": [
            {"shop": shop, "type": product_type, "products": count, "titles": titles}
            for (shop, product_type), (count, titles) in sorted(
                ((key, value) for key, value in words.items() if value[0] >= _WORDS_MIN_PRODUCTS),
                key=lambda item: (-item[1][0], item[0]),
            )[:_WORDS_LISTED]
        ],
    }
