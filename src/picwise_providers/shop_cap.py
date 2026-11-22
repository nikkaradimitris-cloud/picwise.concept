"""How many of a shop's products pass to the site: what the bot scans, 20,000 the most.

The checks' rules, section 19 (`docs/PICWISE_CHECKS_RULES.md`). Owner, 2026-11-22: «Το
πλαφόνι είναι 20.000 προϊόντα ... δεν μπαίνει πλαφών για το κάθε κατάστημα.. μπαίνει κανόνας
μόνο όσα έχουν σκανναριστεί περνάνε», and «μπορεί να σκανάρει 15.000 προϊόντα σε ένα άλλο 20
και σε ένα άλλο 5 αυτά περνάνε στο site μέγιστο όριο ... είναι τα 20.000»; a pass counts for
three nights («κρατάμε τα προϊόντα ασκανάριστα μέχρι 3 μέρες», 19.3.1); the order a shop keeps
its products by, «Με τις 3 αλλαγές» (19.4).

What a shop lets the bot scan shows by itself: a pass counts for three nights
(`picwise_checks.ledger`, `PASS_NIGHTS_SCANNED`) and the bot asks a shop's shown products again
first (`ledger.asking_order`, `scanned`), so a shop settles at what the bot scans of it in a
day. This module is the other half: no shop passes more than `SHOP_LIMIT` products, and the
order of 19.4 decides which (`cap_shops`, worked out by the preparation before the cap of 15%
a category, 19.6.1) and in what order the bot asks a shop's shown products (`shop_order`,
worked out by the bot from the prepared catalogue, 19.3.2).

The order of 19.4, for one shop's products:

a. the products of the thin kinds (a kind the catalogue holds fewer than `THIN` of);
b. what it sells cheapest of the offers the site keeps (the same product by its code,
   `product_identity.same_product_key`);
c. the rest, the products with a kind of the site's before those with none;
last, a product a cheaper shop keeps (it shows nothing: one product is shown once, from the
cheapest, owner 16/10). A product belongs to the first of these that fits it, but a product a
cheaper shop keeps is last whatever its kind.

Inside a step (d, e, f): the products that passed their checks before the others (f); fair
shares over the parts (a kind, else the shop's shelf: `catalogue_cap.part_of`), the largest
part first in each round, as `catalogue_cap.fair_quotas` gives the places left over to the
largest; inside a part the clean ones first (an identity, an image, a stock state that
varies), among them those more than one shop sells; each tier spread over its prices, so
that any first part of the order holds cheap, middle and dear products; ties by the row's
id, so the same ones come each night. The order is one list, so the first N of it are what a
shop keeps with N places, and the bot asks in the same order (built 22/11: the category cap
picks a number per part and spreads it; a list whose every first part is fair and spread
serves the cap, its candidates and the bot alike).

A capped shop (more products a card can show than `SHOP_LIMIT`) keeps, in this order: the
products it kept the night before that a cheaper shop does not keep (e); then those that
passed their checks and may enter (the checks' gate, 19.6.2); then the ones it kept the
night before that a cheaper shop keeps; then those that may enter and a cheaper shop keeps
(e: "a kept product that became a cheaper shop's too gives its place to a product that
waits, checked and passed"). With places still open, the next ones by the order that wait at
the gate are its candidates, one and a quarter times the places open: the bot asks them.
The shops are settled by name after a first pass in which each takes what it sells cheapest
of every shop that sells it (b); in the second pass "cheapest" is read among the offers the
other shops keep, so a product whose cheaper offers were all left out by their own shops is
the next shop's to keep.

Behind one switch (`data/shop_cap_switch.json`, frozen with the code, 19.7.2): false, no
shop is capped and the bot asks as before.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Collection, Iterable, Mapping, Sequence

from .catalogue_cap import part_of, row_key, shop_of
from .contracts import FeedAvailabilityContext, ProviderProduct
from .decision_labels import parse_price_amount
from .product_identity import same_product_key

# Owner, 2026-11-22 (17:08, 17:21): the most a shop passes to the site.
SHOP_LIMIT = 20_000
# Proposed (19.4 a, 19.8.1): a kind the catalogue holds fewer products of is thin.
THIN = 100
SWITCH_FILE = Path(__file__).resolve().parents[2] / "data" / "shop_cap_switch.json"

# The steps of 19.4, in order; a product's step is the first that fits it.
THIN_STEP, CHEAPEST_STEP, KIND_STEP, REST_STEP, DEARER_STEP = range(5)
STEPS = ("thin kinds", "cheapest kept", "with a kind", "the rest", "a cheaper shop's")
_INFINITY = float("inf")


def shop_cap_on(path: Path = SWITCH_FILE) -> bool:
    """The switch of 19.7.2: true when a shop passes at most what the bot scanned of it."""
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("cap") is True
    except (OSError, ValueError, AttributeError):
        return False


def candidates_for(open_places: int) -> int:
    """19.6.2: how many candidates a shop with `open_places` names, one and a quarter times."""
    return -(-5 * open_places // 4) if open_places > 0 else 0


def spread_positions(count: int) -> list[int]:
    """The positions 0..count-1 in an order whose every first part is spread evenly: the
    middle first, then the quarters, the eighths... (the points `catalogue_cap._spread`
    takes, (2k+1)/2^(L+1) of the way along), then any left."""
    seen = bytearray(count)
    order: list[int] = []
    level = 0
    while len(order) < count and (1 << level) <= 2 * count:
        denominator = 1 << (level + 1)
        for step in range(1 << level):
            place = (2 * step + 1) * count // denominator
            if not seen[place]:
                seen[place] = 1
                order.append(place)
        level += 1
    order.extend(place for place in range(count) if not seen[place])
    return order


def ordered(
    members: Iterable[int],
    *,
    step: Callable[[int], int],
    waits: Callable[[int], bool],
    part: Callable[[int], str],
    rank: Callable[[int], tuple[int, int]],
    price: Callable[[int], tuple[bool, float, str]],
) -> list[int]:
    """`members` in the order of 19.4 (module docstring): by step; inside a step the ones
    that passed (`waits` false) first; then fair shares over the parts, round by round, the
    largest part first; inside a part the clean ones first (`rank`), each rank spread over
    its prices (`price`, ties by the row's id)."""
    groups: dict[tuple[int, bool], dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for member in members:
        groups[(step(member), waits(member))][part(member)].append(member)
    result: list[int] = []
    for group in sorted(groups):
        sequences: dict[str, list[int]] = {}
        for name, found in groups[group].items():
            by_rank: dict[tuple[int, int], list[int]] = defaultdict(list)
            for member in found:
                by_rank[rank(member)].append(member)
            sequence: list[int] = []
            for tier in sorted(by_rank):
                by_price = sorted(by_rank[tier], key=price)
                sequence.extend(by_price[place] for place in spread_positions(len(by_price)))
            sequences[name] = sequence
        names = sorted(sequences, key=lambda name: (-len(sequences[name]), name))
        depth = 0
        while names:
            still = []
            for name in names:
                sequence = sequences[name]
                result.append(sequence[depth])
                if depth + 1 < len(sequence):
                    still.append(name)
            names = still
            depth += 1
    return result


@dataclass
class _Facts:
    """What the order reads of each product it orders (by position in `members`)."""

    members: list[int]
    keys: list[str]
    codes: list[str]
    prices: list[float]
    parts: list[str]
    thin: list[bool]
    has_kind: list[bool]
    lacking: list[int]


def _facts(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    members: list[int],
    kind_size: Mapping[str, int],
    thin: int,
    feed_ctx: FeedAvailabilityContext | None,
) -> _Facts:
    from .kind_itself import narrowest, real_kinds
    from .offer_health import interpret_availability_state

    facts = _Facts(members, [], [], [], [], [], [], [])
    for index in members:
        product = products[index]
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        code = same_product_key(raw, brand=str(product.brand or ""))
        amount = parse_price_amount(product.price_text)
        own = real_kinds(kinds[index])
        facts.keys.append(row_key(product))
        facts.codes.append(code)
        facts.prices.append(float(amount) if amount is not None else _INFINITY)
        facts.parts.append(part_of(product, kinds[index]))
        facts.has_kind.append(bool(own))
        facts.thin.append(bool(own) and min(kind_size.get(kind, 0) for kind in narrowest(own)) < thin)
        stock_varies = True
        if feed_ctx is not None:
            state, _source, _signal = interpret_availability_state(product, feed_ctx=feed_ctx)
            stock_varies = state == "trusted"
        facts.lacking.append((0 if code else 1) + (0 if str(product.image_url or "").strip() else 1)
                             + (0 if stock_varies else 1))
    return facts


def _kind_sizes(kinds: Iterable[Collection[str]]) -> Counter:
    from .kind_itself import real_kinds

    sizes: Counter = Counter()
    for found in kinds:
        sizes.update(real_kinds(found))
    return sizes


def _intern(products: Sequence[ProviderProduct]) -> list[str]:
    names: dict[str, str] = {}
    return [names.setdefault(name, name) for name in map(shop_of, products)]


@dataclass(frozen=True)
class ShopCapResult:
    """What the rule of 19.3 keeps (`cap_shops`)."""

    limit: int
    thin: int
    # Per product, in the order given: kept or not. A shop at or under the limit keeps all.
    keep: tuple[bool, ...]
    # The capped shops' candidates for the bot (indices into the products), in their order.
    candidates: tuple[int, ...] = ()
    # Per capped shop (19.7.3): its products a card can show, kept, by step, from the night
    # before, waiting at the gate, candidates named.
    shops: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def kept(self) -> int:
        return sum(self.keep)


def cap_shops(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    *,
    feed_ctx: FeedAvailabilityContext | None = None,
    kept_before: Collection[str] = frozenset(),
    may_enter: Callable[[ProviderProduct], bool] | None = None,
    passed: Callable[[ProviderProduct], bool] | None = None,
    limit: int = SHOP_LIMIT,
    thin: int = THIN,
) -> ShopCapResult:
    """Which of `products` (those a card can show, `kinds` each one's kinds) the shops keep
    (module docstring). `kept_before`: the row keys (`catalogue_cap.row_key`) the site kept
    the night before (the category cap's pool); a kind is thin by what it kept, or by every
    product given on a night with no such memory. `may_enter`: the checks' gate (a product
    not kept the night before takes a place only when it says so); `passed`: whether a
    product passed its checks (19.4 f); both None when the checks are not applied."""
    count = len(products)
    shops = _intern(products)
    sizes = Counter(shops)
    capped = sorted(name for name, size in sizes.items() if size > limit)
    if not capped:
        return ShopCapResult(limit=limit, thin=thin, keep=(True,) * count)
    capped_set = frozenset(capped)
    before = frozenset(kept_before)
    remembered = [index for index in range(count) if before and row_key(products[index]) in before]
    kind_size = _kind_sizes(kinds[index] for index in remembered) if remembered else _kind_sizes(kinds)
    del remembered
    members = [index for index in range(count) if shops[index] in capped_set]
    facts = _facts(products, kinds, members, kind_size, thin, feed_ctx)
    positions = range(len(members))
    in_before = [facts.keys[place] in before for place in positions]
    enters = [may_enter is None or in_before[place] or bool(may_enter(products[members[place]])) for place in positions]
    has_passed = [passed is not None and bool(passed(products[members[place]])) for place in positions]

    # Who sells each of the capped shops' codes, and at what price: the cheapest of all,
    # and the cheapest among the shops that are not capped (they keep every product).
    wanted = {code for code in facts.codes if code}
    cheapest_all: dict[str, float] = {}
    sellers: dict[str, set[str]] = defaultdict(set)
    uncapped_low: dict[str, float] = {}
    for place, code in enumerate(facts.codes):
        if code:
            sellers[code].add(shops[members[place]])
            cheapest_all[code] = min(cheapest_all.get(code, _INFINITY), facts.prices[place])
    for index, product in enumerate(products):
        if shops[index] in capped_set:
            continue
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        code = same_product_key(raw, brand=str(product.brand or ""))
        if code not in wanted:
            continue
        amount = parse_price_amount(product.price_text)
        price = float(amount) if amount is not None else _INFINITY
        sellers[code].add(shops[index])
        cheapest_all[code] = min(cheapest_all.get(code, _INFINITY), price)
        uncapped_low[code] = min(uncapped_low.get(code, _INFINITY), price)
    shared = [bool(code) and len(sellers[code]) > 1 for code in facts.codes]
    by_shop: dict[str, list[int]] = defaultdict(list)
    for place in positions:
        by_shop[shops[members[place]]].append(place)

    def rank(place: int) -> tuple[int, int]:
        return (facts.lacking[place], 0 if shared[place] else 1)

    def price(place: int) -> tuple[bool, float, str]:
        value = facts.prices[place]
        return (value == _INFINITY, value if value != _INFINITY else 0.0, facts.keys[place])

    def step_of(place: int, dearer: bool) -> int:
        if dearer:
            return DEARER_STEP
        if facts.thin[place]:
            return THIN_STEP
        if shared[place]:
            return CHEAPEST_STEP
        return KIND_STEP if facts.has_kind[place] else REST_STEP

    taken: dict[str, list[int]] = {}
    steps: dict[str, list[int]] = {}
    orders: dict[str, list[int]] = {}

    def settle(shop: str, dearer: Callable[[int], bool]) -> None:
        mine = by_shop[shop]
        step = {place: step_of(place, dearer(place)) for place in mine}
        order = ordered(mine, step=step.__getitem__, waits=lambda place: not has_passed[place], part=facts.parts.__getitem__,
                        rank=rank, price=price)
        last = [place for place in order if step[place] == DEARER_STEP]
        first = [place for place in order if step[place] != DEARER_STEP]
        chosen = ([place for place in first if in_before[place]] + [place for place in first if not in_before[place] and enters[place]]
                  + [place for place in last if in_before[place]] + [place for place in last if not in_before[place] and enters[place]])
        taken[shop] = chosen[:limit]
        steps[shop] = [step[place] for place in taken[shop]]
        orders[shop] = order

    def low_of(shop: str) -> dict[str, float]:
        found: dict[str, float] = {}
        for place in taken[shop]:
            code = facts.codes[place]
            if code:
                found[code] = min(found.get(code, _INFINITY), facts.prices[place])
        return found

    # The first pass: each takes what it sells cheapest of every shop that sells it (19.4 b).
    for shop in capped:
        settle(shop, lambda place: shared[place] and facts.prices[place] > cheapest_all[facts.codes[place]])
    # Then shop by shop, "cheapest" read among the offers the other shops keep.
    lows = {shop: low_of(shop) for shop in capped}
    for shop in capped:
        def kept_elsewhere(code: str, _shop: str = shop) -> float:
            return min([uncapped_low.get(code, _INFINITY)] + [lows[other].get(code, _INFINITY) for other in capped if other != _shop])

        settle(shop, lambda place: shared[place] and kept_elsewhere(facts.codes[place]) < facts.prices[place])
        lows[shop] = low_of(shop)

    keep = [True] * count
    for index in members:
        keep[index] = False
    candidates: list[int] = []
    notes: dict[str, dict[str, Any]] = {}
    for shop in capped:
        chosen = taken[shop]
        for place in chosen:
            keep[members[place]] = True
        open_places = limit - len(chosen)
        waiting = [place for place in orders[shop] if not in_before[place] and not enters[place]]
        named = waiting[:candidates_for(open_places)]
        candidates.extend(members[place] for place in named)
        by_step = Counter(steps[shop])
        notes[shop] = {
            "products": sizes[shop],
            "kept": len(chosen),
            "cut": sizes[shop] - len(chosen),
            "kept_by_step": {STEPS[number]: by_step.get(number, 0) for number in range(len(STEPS))},
            "kept_from_before": sum(1 for place in chosen if in_before[place]),
            "kept_passed": sum(1 for place in chosen if has_passed[place]),
            "waiting_at_the_gate": len(waiting),
            "candidates": len(named),
        }
    return ShopCapResult(limit=limit, thin=thin, keep=tuple(keep), candidates=tuple(candidates), shops=notes)


def shop_order(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    *,
    feed_ctx: FeedAvailabilityContext | None = None,
    thin: int = THIN,
) -> dict[str, list[int]]:
    """Per shop, its products (indices) in the order of 19.4, read among the products given
    (the catalogue the site shows): what the bot asks a shop's shown products again in
    (19.3.2). Every product given is kept, so a product another shop shows cheaper is last,
    and a kind is thin by what the catalogue shows."""
    shops = _intern(products)
    members = list(range(len(products)))
    facts = _facts(products, kinds, members, _kind_sizes(kinds), thin, feed_ctx)
    low: dict[str, float] = {}
    sellers: dict[str, set[str]] = defaultdict(set)
    for place, code in enumerate(facts.codes):
        if code:
            sellers[code].add(shops[place])
            low[code] = min(low.get(code, _INFINITY), facts.prices[place])
    by_shop: dict[str, list[int]] = defaultdict(list)
    for place in members:
        by_shop[shops[place]].append(place)

    def step(place: int) -> int:
        code = facts.codes[place]
        shared = bool(code) and len(sellers[code]) > 1
        if shared and low[code] < facts.prices[place]:
            return DEARER_STEP
        if facts.thin[place]:
            return THIN_STEP
        if shared:
            return CHEAPEST_STEP
        return KIND_STEP if facts.has_kind[place] else REST_STEP

    def rank(place: int) -> tuple[int, int]:
        code = facts.codes[place]
        return (facts.lacking[place], 0 if code and len(sellers[code]) > 1 else 1)

    def price(place: int) -> tuple[bool, float, str]:
        value = facts.prices[place]
        return (value == _INFINITY, value if value != _INFINITY else 0.0, facts.keys[place])

    return {shop: ordered(found, step=step, waits=lambda _place: False, part=facts.parts.__getitem__, rank=rank, price=price)
            for shop, found in by_shop.items()}


def shop_cap_summary(result: ShopCapResult | None, *, listed: int = 20) -> dict[str, Any]:
    """The rule's numbers for the night's note (19.7.3): counts and shop names only."""
    if result is None:
        return {"applied": False}
    shops = sorted(result.shops.items(), key=lambda item: (-item[1]["products"], item[0]))[:listed]
    return {
        "applied": True,
        "limit": result.limit,
        "thin": result.thin,
        "products": len(result.keep),
        "kept": result.kept,
        "capped_shops": len(result.shops),
        "cut": sum(entry["cut"] for entry in result.shops.values()),
        "candidates": len(result.candidates),
        "shops": [{"shop": name, **entry} for name, entry in shops],
    }
