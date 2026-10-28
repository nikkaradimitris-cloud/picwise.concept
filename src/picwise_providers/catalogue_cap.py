"""Which products a capped catalogue keeps: no category over a share of all products.

Owner, 2026-10-27: no category of like products may hold more than 15% of all the
products shown, so that no shop makes the site look like one kind of shop to Google
(«ρολογάδικο»), the server's room spreads over more categories little by little, and
each search looks complete; «πρώτα από όλα να έχει καθαρή και ποιοτική πληροφορία», a
satisfying volume rather than a huge one. Counted per category, the first two levels of
the product's shelf when it is one of Google's, as `catalogue_balance` reads them
("apparel & accessories > jewelry", where watches are too); the shops' own categories
are one group. Then:

- the size: each category keeps at most the same number C, the largest C such that no
  category keeps more than the share of what all keep (`catalogue_balance.capped_size`),
  worked out each night from every product a card can show, never from the previous
  night's cut: with more products C grows, with fewer it shrinks in proportion;
- which ones: the ones kept the night before first, as long as a card can still show
  them (owner: «κοιτώντας πάντα το χθεσινό σαν αφετηρία»); the places left go to the
  others, and when there are fewer places than those, the ones that stay are chosen as
  below, so they keep their spread;
- inside a category, its places are shared fairly over its kinds (a product without
  one under its narrowest shelf, or under the kind that shelf names: "... > rings" with
  "ring", so rings never take two shares; an accessory stays on its shelf, as earring
  backs on a shelf of earrings are none): a kind with fewer products than an equal
  share keeps them all and leaves the rest to the others, so a search for earrings on a
  shelf full of rings still finds earrings;
- inside a kind, the clean ones first (a barcode, or a brand and a part number; an
  image; a stock state that varies across the feed), among them those sold by more than
  one shop first, and each such tier spread over its price range from the cheapest to
  the dearest, so every search keeps cheap, middle and dear choices; ties go by the
  row's id, so the same ones come each night.

Nothing is deleted: a product left out is not shown, and comes back when there is room.
Measured first (`deployment/server/print_cap.py`): nothing shown changes.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Collection, Mapping, Sequence

from picwise_nlu.concept_understanding import ACCESSORY_MARKER

from .catalogue_balance import CAP_SHARE, NO_SHOP, _narrowest_kind, _shelf_groups, capped_size
from .contracts import FeedAvailabilityContext, ProviderProduct
from .decision_labels import parse_price_amount
from .normalization import extract_merchant_name
from .offer_health import interpret_availability_state
from .search_selection import _product_identity_key

# What a product lacks of the three signs of clean information, worst last.
CLEAN_SIGNS = ("an identity", "an image", "a stock state that varies")


@dataclass(frozen=True)
class CapResult:
    """What a cap keeps (`cap_catalogue`)."""

    share: float
    # The most products a category keeps; None when too few categories for the share to
    # hold, and then nothing is left out.
    size: int | None
    # Per product, in the order given: kept or not.
    keep: tuple[bool, ...]
    # The kept products' row keys (`row_key`), the next night's starting point.
    kept_keys: frozenset[str]
    # Per category: products before and kept.
    by_category: dict[str, tuple[int, int]] = field(default_factory=dict)
    # Per category over the cap, per kind or shelf inside it: products before and kept.
    inside: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)
    # Per shop: products before and kept.
    by_shop: dict[str, tuple[int, int]] = field(default_factory=dict)
    # In the categories over the cap, the kept ones by how many clean signs they lack,
    # how many of them more than one shop sells, and how many were kept the night before.
    kept_by_missing_signs: dict[int, int] = field(default_factory=dict)
    kept_in_several_shops: int = 0
    kept_from_before: int = 0
    # Per category over the cap: the lowest, the middle and the highest price, of all
    # its products and of those kept.
    prices: dict[str, dict[str, tuple[float, float, float] | None]] = field(default_factory=dict)

    @property
    def kept(self) -> int:
        return sum(self.keep)


def row_key(product: ProviderProduct) -> str:
    """The feed row's own id, the same from one night to the next."""
    own = str(product.provider_product_id or "").strip() or str(product.product_url or "").strip()
    return f"{product.provider_key}:{own}"


def shop_of(product: ProviderProduct) -> str:
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    return " ".join(str(extract_merchant_name(raw) or "").split()) or NO_SHOP


def _shelf(category: str) -> str:
    return " > ".join(part.strip().lower() for part in str(category or "").split(">") if part.strip())


def category_of(product: ProviderProduct) -> str:
    """The category a cap counts a product in: the first two levels of its shelf."""
    return _shelf_groups(product.category_text)[1]


def part_of(product: ProviderProduct, kinds: Collection[str]) -> str:
    """Where inside its category a product's place is shared: its kind, else its shelf."""
    kind = _narrowest_kind(kinds)
    return kind if kind else f"shelf: {_shelf(product.category_text) or '(none)'}"


def _leaf_names(part: str) -> tuple[str, ...]:
    leaf = part.rsplit(">", 1)[-1].strip().replace(" ", "_").replace("-", "_")
    names = [leaf]
    if leaf.endswith("es"):
        names.append(leaf[:-2])
    if leaf.endswith("s"):
        names.append(leaf[:-1])
    return tuple(names)


def joined_parts(
    categories: Sequence[str], parts: Sequence[str], accessories: Sequence[bool] = ()
) -> list[str]:
    """`parts` with a shelf whose last level names a kind of the same category put under
    that kind (a "... > rings" shelf with "ring"), so that one kind never takes two
    shares: the kind reading leaves many rings on a shelf of rings without a kind. A
    product read as an accessory (`accessories`, in order) stays on its shelf: earring
    backs on a shelf of earrings are none (owner, 2026-10-27)."""
    kinds_in: dict[str, set[str]] = defaultdict(set)
    for category, part in zip(categories, parts):
        if not part.startswith("shelf: "):
            kinds_in[category].add(part)
    joined: list[str] = []
    for index, (category, part) in enumerate(zip(categories, parts)):
        if part.startswith("shelf: ") and not (accessories and accessories[index]):
            part = next((name for name in _leaf_names(part) if name in kinds_in[category]), part)
        joined.append(part)
    return joined


def fair_quotas(sizes: Mapping[str, int], places: int) -> dict[str, int]:
    """Each part's share of `places`: equal shares, a part smaller than its share keeping
    all it has and leaving the rest to the others; the places an equal split leaves over
    go to the largest parts first, then by name."""
    quotas: dict[str, int] = {}
    remaining = max(0, places)
    pending = sorted(sizes.items(), key=lambda item: (item[1], item[0]))
    while pending:
        equal = remaining // len(pending)
        name, size = pending[0]
        if size <= equal:
            quotas[name] = size
            remaining -= size
            pending.pop(0)
            continue
        extra = remaining - equal * len(pending)
        for rank, (name, _size) in enumerate(sorted(pending, key=lambda item: (-item[1], item[0]))):
            quotas[name] = equal + (1 if rank < extra else 0)
        break
    return quotas


def _spread(indices: Sequence[int], count: int, order: Sequence[tuple[bool, float, str]]) -> list[int]:
    """`count` of `indices`, evenly over their price order."""
    if count >= len(indices):
        return list(indices)
    if count <= 0:
        return []
    ordered = sorted(indices, key=order.__getitem__)
    total = len(ordered)
    return [ordered[(2 * step + 1) * total // (2 * count)] for step in range(count)]


def _pick(
    indices: Sequence[int],
    count: int,
    rank: Sequence[tuple[int, int]],
    order: Sequence[tuple[bool, float, str]],
) -> list[int]:
    """`count` of `indices`: the best ranked first, each rank spread over its prices."""
    by_rank: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index in indices:
        by_rank[rank[index]].append(index)
    chosen: list[int] = []
    for place in sorted(by_rank):
        left = count - len(chosen)
        if left <= 0:
            break
        chosen.extend(_spread(by_rank[place], left, order))
    return chosen


def _price_summary(values: Sequence[float]) -> tuple[float, float, float] | None:
    if not values:
        return None
    return (min(values), statistics.median(values), max(values))


def cap_catalogue(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    *,
    feed_ctx: FeedAvailabilityContext,
    kept_before: Collection[str] = frozenset(),
    share: float = CAP_SHARE,
) -> CapResult:
    """Which of `products` (those a card can show, `kinds` each one's kinds) a cap of
    `share` a category keeps (module docstring); `kept_before` holds the row keys the
    previous night kept."""
    keys = [row_key(product) for product in products]
    categories = [category_of(product) for product in products]
    parts = joined_parts(
        categories,
        [part_of(product, product_kinds) for product, product_kinds in zip(products, kinds)],
        [ACCESSORY_MARKER in product_kinds for product_kinds in kinds],
    )
    sizes = Counter(categories)
    size = capped_size(list(sizes.values()), share)
    shops = [shop_of(product) for product in products]
    keep = [True] * len(products)
    over = {name for name, count in sizes.items() if size is not None and count > size}

    inside: dict[str, dict[str, tuple[int, int]]] = {}
    missing_signs: Counter = Counter()
    several_shops = 0
    from_before = 0
    prices: dict[str, dict[str, tuple[float, float, float] | None]] = {}
    if over:
        members: dict[str, list[int]] = defaultdict(list)
        for index, category in enumerate(categories):
            if category in over:
                members[category].append(index)
        # Who sells each identified product, over every product a card can show.
        sellers: dict[str, set[str]] = defaultdict(set)
        identities = ["" for _product in products]
        for index, product in enumerate(products):
            identity = _product_identity_key(product)
            if identity:
                identities[index] = identity
                sellers[identity].add(shops[index])
        amounts: list[float | None] = [None] * len(products)
        lacking = [0] * len(products)
        for indices in members.values():
            for index in indices:
                product = products[index]
                amounts[index] = parse_price_amount(product.price_text)
                state, _source, _signal = interpret_availability_state(product, feed_ctx=feed_ctx)
                lacking[index] = (
                    (0 if identities[index] else 1)
                    + (0 if str(product.image_url or "").strip() else 1)
                    + (0 if state == "trusted" else 1)
                )
        rank = [
            (lacking[index], 0 if len(sellers.get(identities[index], ())) > 1 else 1)
            for index in range(len(products))
        ]
        order = [
            (amount is None, amount if amount is not None else 0.0, keys[index])
            for index, amount in enumerate(amounts)
        ]
        before = frozenset(kept_before)
        for category, indices in sorted(members.items()):
            by_part: dict[str, list[int]] = defaultdict(list)
            for index in indices:
                by_part[parts[index]].append(index)
            quotas = fair_quotas({part: len(found) for part, found in by_part.items()}, size or 0)
            chosen: set[int] = set()
            for part, found in by_part.items():
                quota = quotas.get(part, 0)
                earlier = [index for index in found if keys[index] in before]
                if len(earlier) >= quota:
                    picked = _pick(earlier, quota, rank, order)
                else:
                    later = [index for index in found if keys[index] not in before]
                    picked = earlier + _pick(later, quota - len(earlier), rank, order)
                chosen.update(picked)
            for index in indices:
                keep[index] = index in chosen
            inside[category] = {
                part: (len(found), sum(1 for index in found if keep[index])) for part, found in by_part.items()
            }
            for index in chosen:
                missing_signs[lacking[index]] += 1
                several_shops += rank[index][1] == 0
                from_before += keys[index] in before
            prices[category] = {
                "all": _price_summary([amounts[index] for index in indices if amounts[index] is not None]),
                "kept": _price_summary([amounts[index] for index in chosen if amounts[index] is not None]),
            }

    by_category = {name: (count, 0) for name, count in sizes.items()}
    by_shop: dict[str, tuple[int, int]] = {}
    for index, category in enumerate(categories):
        before_count, kept_count = by_category[category]
        by_category[category] = (before_count, kept_count + keep[index])
        shop_before, shop_kept = by_shop.get(shops[index], (0, 0))
        by_shop[shops[index]] = (shop_before + 1, shop_kept + keep[index])
    return CapResult(
        share=share,
        size=size,
        keep=tuple(keep),
        kept_keys=frozenset(key for key, kept in zip(keys, keep) if kept),
        by_category=by_category,
        inside=inside,
        by_shop=by_shop,
        kept_by_missing_signs=dict(sorted(missing_signs.items())),
        kept_in_several_shops=several_shops,
        kept_from_before=from_before,
        prices=prices,
    )


def cap_summary(result: CapResult, *, listed: int = 10) -> dict[str, Any]:
    """The cap's numbers for a note or a log: counts and names only."""

    def largest(counts: Mapping[str, tuple[int, int]], by: int) -> list[dict[str, Any]]:
        ordered = sorted(counts.items(), key=lambda item: (-item[1][by], item[0]))[:listed]
        return [{"name": name, "products": before, "kept": kept} for name, (before, kept) in ordered]

    return {
        "share": result.share,
        "size": result.size,
        "products": len(result.keep),
        "kept": result.kept,
        "over": sorted(result.inside),
        "categories": largest(result.by_category, 1),
        "inside": {name: largest(parts, 0) for name, parts in sorted(result.inside.items())},
        "shops": largest(result.by_shop, 0),
        "kept_by_missing_signs": result.kept_by_missing_signs,
        "kept_in_several_shops": result.kept_in_several_shops,
        "kept_from_before": result.kept_from_before,
        "prices": result.prices,
    }
