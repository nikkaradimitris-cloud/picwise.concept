"""How many of a shop's products pass to the site (`picwise_providers.shop_cap`; the checks'
rules, section 19; owner, 2026-11-22: what the bot scans of a shop passes, 20,000 the most,
in the order «Με τις 3 αλλαγές»).

Pinned: the order's spread, its fair shares over the parts and the passed before the never
asked inside a step (19.4 d, f); a shop at or under the most keeps every product; a capped
shop keeps the most, the thin kinds first, then what it sells cheapest of the offers the site
keeps, then the products with a kind before those with none, a product a cheaper shop keeps
last (19.4 a to c); two shops of one catalogue show two halves of it (19.4 b); the night
before's first, a kept product a cheaper shop keeps giving its place to one that passed
(19.4 e); the checks' gate and the candidates, one and a quarter times the places open
(19.6.2); the bot's order of a shop's shown products (19.3.2); the switch (19.7.2). And, from
the look of 23/11: a cheaper row of a shop that is not capped counts as a cheaper offer only
when the site may show it (shown the night before, or let in by the checks' gate).

Every row is local test data: fictional shops and brands, `.invalid` hosts.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import shop_cap  # noqa: E402
from picwise_providers.catalogue_cap import row_key  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

KETTLE = frozenset({"kettle"})
TOASTER = frozenset({"toaster"})


def _product(number: int, *, shop: str = "Big", price: float | None = None, gtin: str = "",
             kinds_hint: str = "", image: bool = True) -> ProviderProduct:
    raw = {"merchant_name": shop, "availability": "in stock"}
    if gtin:
        raw["ean"] = gtin
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"{shop.lower()}-{number}", title=f"Zentra thing {number} {kinds_hint}",
        brand="Zentra", category_text="Home & Garden > Kitchen", product_url=f"https://{shop.lower()}.invalid/p/{number}",
        image_url=f"https://{shop.lower()}.invalid/i/{number}.jpg" if image else "",
        price_text=f"{(price if price is not None else 10 + number):.2f}", availability_text="in stock", currency="GBP",
        raw=raw,
    )


def _gtin(number: int) -> str:
    """A valid EAN-13 for `number`."""
    body = f"501234{number:06d}"
    total = sum(int(digit) * (3 if index % 2 else 1) for index, digit in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _numbers(products, keep) -> list[str]:
    return [product.provider_product_id for product, kept in zip(products, keep) if kept]


class TheOrderTests(unittest.TestCase):
    def test_spread_positions_are_every_position_the_middle_first_and_each_first_part_spread(self) -> None:
        for count in (1, 2, 3, 7, 10, 64, 101):
            order = shop_cap.spread_positions(count)
            self.assertEqual(sorted(order), list(range(count)))
        self.assertEqual(shop_cap.spread_positions(8)[:3], [4, 2, 6])
        # Any first part of a hundred covers cheap, middle and dear.
        first = sorted(shop_cap.spread_positions(100)[:4])
        self.assertLess(first[0], 25)
        self.assertGreaterEqual(first[-1], 75)

    def test_by_step_the_passed_first_fair_over_the_parts_clean_first(self) -> None:
        members = list(range(12))
        step = {index: (0 if index < 2 else 2) for index in members}
        waits = {index: index in (0, 5, 6, 7, 8) for index in members}
        part = {index: ("a" if index % 2 else "b") for index in members}
        rank = {index: ((1, 1) if index == 3 else (0, 1)) for index in members}
        order = shop_cap.ordered(members, step=step.__getitem__, waits=waits.__getitem__, part=part.__getitem__,
                                 rank=rank.__getitem__, price=lambda index: (False, float(index), str(index)))
        self.assertEqual(sorted(order), members)
        # Step 0 first, its passed product before the one not.
        self.assertEqual(order[:2], [1, 0])
        rest = order[2:]
        passed = [index for index in rest if not waits[index]]
        self.assertEqual(set(rest[:len(passed)]), set(passed))
        # Inside the passed of step 2: the parts take turns, and the unclean 3 is its part's last.
        first_passed = rest[:len(passed)]
        self.assertEqual([part[index] for index in first_passed[:4]], ["a", "b", "a", "b"] if part[first_passed[0]] == "a"
                         else ["b", "a", "b", "a"])
        self.assertEqual([index for index in first_passed if part[index] == "a"][-1], 3)


class CapShopsTests(unittest.TestCase):
    def test_a_shop_at_or_under_the_most_keeps_every_product(self) -> None:
        products = [_product(number) for number in range(5)]
        result = shop_cap.cap_shops(products, [KETTLE] * 5, limit=5)
        self.assertEqual((result.keep, result.candidates, result.shops), ((True,) * 5, (), {}))

    def test_a_capped_shop_keeps_the_most_thin_kinds_first_a_cheaper_shops_last(self) -> None:
        # Big: 10 kettles (one sold cheaper by Small), 1 toaster (a thin kind), 2 with no kind.
        big = [_product(number, kinds_hint="kettle") for number in range(10)]
        big[0] = _product(0, gtin=_gtin(1), price=50.0)
        toaster = _product(20, kinds_hint="toaster")
        loose = [_product(30), _product(31)]
        small = [_product(1, shop="Small", gtin=_gtin(1), price=40.0)]
        products = big + [toaster] + loose + small
        kinds = [KETTLE] * 10 + [TOASTER] + [frozenset()] * 2 + [KETTLE]
        result = shop_cap.cap_shops(products, kinds, limit=9, thin=2)
        kept = _numbers(products, result.keep)
        self.assertEqual(len([number for number in kept if number.startswith("big")]), 9)
        self.assertIn("big-20", kept)            # (a) the thin kind first
        self.assertNotIn("big-0", kept)          # last: Small keeps it cheaper
        self.assertNotIn("big-30", kept)         # (c) a kind before none
        self.assertNotIn("big-31", kept)
        self.assertIn("small-1", kept)           # a shop under the most is not touched
        note = result.shops["Big"]
        self.assertEqual((note["products"], note["kept"], note["cut"]), (13, 9, 4))
        self.assertEqual(note["kept_by_step"]["thin kinds"], 1)
        self.assertEqual(note["kept_by_step"]["a cheaper shop's"], 0)

    def test_two_shops_of_one_catalogue_show_two_halves_of_it(self) -> None:
        # GamingKit and PCHUB.UK's case (19.2): one catalogue, Alpha the cheaper on all.
        alpha = [_product(number, shop="Alpha", gtin=_gtin(number), price=10.0 + number) for number in range(8)]
        beta = [_product(number, shop="Beta", gtin=_gtin(number), price=11.0 + number) for number in range(8)]
        products = alpha + beta
        result = shop_cap.cap_shops(products, [KETTLE] * 16, limit=4, thin=1)
        alpha_codes = {product.raw["ean"] for product, kept in zip(alpha, result.keep[:8]) if kept}
        beta_codes = {product.raw["ean"] for product, kept in zip(beta, result.keep[8:]) if kept}
        self.assertEqual((len(alpha_codes), len(beta_codes)), (4, 4))
        # Beta keeps the products Alpha's cap left out: no place shows a dearer copy.
        self.assertFalse(alpha_codes & beta_codes)
        self.assertEqual(result.shops["Beta"]["kept_by_step"]["cheapest kept"], 4)

    def test_the_night_before_first_and_a_cheaper_shops_gives_its_place_to_one_that_passed(self) -> None:
        big = [_product(number, kinds_hint="kettle") for number in range(6)]
        big[0] = _product(0, gtin=_gtin(1), price=50.0)
        small = [_product(1, shop="Small", gtin=_gtin(1), price=40.0)]
        products = big + small
        kinds = [KETTLE] * 7
        before = {row_key(product) for product in big[:3]} | {row_key(small[0])}
        # Only big-4 passed its checks and may enter; big-3 and big-5 wait.
        gate = {row_key(big[4])}
        result = shop_cap.cap_shops(products, kinds, kept_before=before, limit=3,
                                    may_enter=lambda product: row_key(product) in gate)
        kept = _numbers(products, result.keep)
        self.assertEqual([number for number in kept if number.startswith("big")], ["big-1", "big-2", "big-4"])
        self.assertEqual(result.candidates, ())
        # With nothing that passed waiting, the kept product a cheaper shop keeps stays.
        again = shop_cap.cap_shops(products, kinds, kept_before=before, limit=3, may_enter=lambda product: False)
        self.assertEqual([number for number in _numbers(products, again.keep) if number.startswith("big")],
                         ["big-0", "big-1", "big-2"])

    def test_a_cheaper_row_that_waits_at_the_gate_is_no_cheaper_offer_yet(self) -> None:
        # The look of 23/11: half the rows of the shops that are not capped wait at the gate.
        # Small sells big-0 cheaper, but the site did not show its row the night before and
        # it has not passed its check: nothing of it is shown, so big-0 is the cheapest offer
        # the site keeps, and Big's to keep as that (19.4 b). The night Small's row is shown,
        # or passes and may enter, big-0 is last.
        big = [_product(number, kinds_hint="kettle") for number in range(6)]
        big[0] = _product(0, gtin=_gtin(1), price=50.0)
        small = [_product(1, shop="Small", gtin=_gtin(1), price=40.0)]
        products = big + small
        kinds = [KETTLE] * 7
        before = {row_key(product) for product in big[:3]}
        waits = shop_cap.cap_shops(products, kinds, kept_before=before, limit=3, thin=1, may_enter=lambda product: False)
        self.assertEqual([number for number in _numbers(products, waits.keep) if number.startswith("big")],
                         ["big-0", "big-1", "big-2"])
        self.assertEqual((waits.shops["Big"]["kept_by_step"]["cheapest kept"],
                          waits.shops["Big"]["kept_by_step"]["a cheaper shop's"]), (1, 0))
        shown = shop_cap.cap_shops(products, kinds, kept_before=before | {row_key(small[0])}, limit=3, thin=1,
                                   may_enter=lambda product: False)
        self.assertEqual((shown.shops["Big"]["kept_by_step"]["cheapest kept"],
                          shown.shops["Big"]["kept_by_step"]["a cheaper shop's"]), (0, 1))
        passed = shop_cap.cap_shops(products, kinds, kept_before=before, limit=3, thin=1,
                                    may_enter=lambda product: row_key(product) == row_key(small[0]))
        self.assertEqual(passed.shops["Big"]["kept_by_step"]["a cheaper shop's"], 1)
        # With the checks not applied, every row is an offer the site keeps, as before.
        free = shop_cap.cap_shops(products, kinds, limit=3, thin=1)
        self.assertNotIn("big-0", _numbers(products, free.keep))

    def test_the_gate_and_one_and_a_quarter_candidates_for_the_places_open(self) -> None:
        big = [_product(number, kinds_hint="kettle") for number in range(20)]
        before = {row_key(product) for product in big[:4]}
        result = shop_cap.cap_shops(big, [KETTLE] * 20, kept_before=before, limit=8, may_enter=lambda product: False)
        self.assertEqual(sum(result.keep), 4)
        self.assertEqual(len(result.candidates), 5)
        self.assertFalse(set(result.candidates) & set(range(4)))
        self.assertEqual(result.shops["Big"]["waiting_at_the_gate"], 16)
        self.assertEqual(shop_cap.candidates_for(4), 5)
        self.assertEqual(shop_cap.candidates_for(0), 0)

    def test_no_shop_keeps_a_copy_of_what_a_cheaper_shop_keeps_whatever_the_order_they_are_settled_in(self) -> None:
        # The look of 22/11 (two shops with one catalogue: 8,962 of one's 20,000 were copies of
        # what the other kept cheaper). Alpha is never the cheapest; Papa sells the same forty
        # cheaper; India sells twenty of them cheaper still, and keeps only some. Papa's choice
        # changes once India has chosen, after Alpha chose against Papa's first one: settled once
        # each, Alpha kept six copies of what Papa keeps, and its note called them its cheapest.
        alpha = [_product(number, shop="Alpha", price=20.0 + number, gtin=_gtin(number)) for number in range(1, 41)]
        papa = [_product(number, shop="Papa", price=10.0 + number, gtin=_gtin(number)) for number in range(1, 41)]
        india = [_product(number, shop="India", price=5.0 + number, gtin=_gtin(number)) for number in range(1, 21)] \
            + [_product(100 + number, shop="India", price=50.0 + number) for number in range(40)]
        products = alpha + papa + india
        before = {row_key(product) for product in products}
        result = shop_cap.cap_shops(products, [KETTLE] * len(products), kept_before=before, limit=10)
        kept = [product for product, keep in zip(products, result.keep) if keep]
        self.assertEqual({shop: sum(1 for product in kept if product.raw["merchant_name"] == shop)
                          for shop in ("Alpha", "India", "Papa")}, {"Alpha": 10, "India": 10, "Papa": 10})
        low: dict[str, float] = {}
        for product in kept:
            low[product.raw["ean"]] = min(low.get(product.raw["ean"], float("inf")), float(product.price_text)) \
                if product.raw.get("ean") else 0.0
        copies = [product.provider_product_id for product in kept
                  if product.raw.get("ean") and low[product.raw["ean"]] < float(product.price_text)]
        self.assertEqual(copies, [])
        # Thirty different products, and each shop's note says what its places hold.
        self.assertEqual(len({product.raw["ean"] for product in kept if product.raw.get("ean")}), 30)
        for shop in ("Alpha", "India", "Papa"):
            self.assertEqual(result.shops[shop]["kept_by_step"]["a cheaper shop's"], 0, shop)

    def test_the_shops_are_settled_a_few_times_at_most(self) -> None:
        self.assertEqual(shop_cap.SETTLE_ROUNDS, 5)
        # With one round, as it was built: the copies are there. The rounds are what takes them out.
        alpha = [_product(number, shop="Alpha", price=20.0 + number, gtin=_gtin(number)) for number in range(1, 41)]
        papa = [_product(number, shop="Papa", price=10.0 + number, gtin=_gtin(number)) for number in range(1, 41)]
        india = [_product(number, shop="India", price=5.0 + number, gtin=_gtin(number)) for number in range(1, 21)] \
            + [_product(100 + number, shop="India", price=50.0 + number) for number in range(40)]
        products = alpha + papa + india
        before = {row_key(product) for product in products}
        real = shop_cap.SETTLE_ROUNDS
        shop_cap.SETTLE_ROUNDS = 1
        try:
            once = shop_cap.cap_shops(products, [KETTLE] * len(products), kept_before=before, limit=10)
        finally:
            shop_cap.SETTLE_ROUNDS = real
        kept = [product for product, keep in zip(products, once.keep) if keep]
        low: dict[str, float] = {}
        for product in kept:
            if product.raw.get("ean"):
                low[product.raw["ean"]] = min(low.get(product.raw["ean"], float("inf")), float(product.price_text))
        self.assertGreater(sum(1 for product in kept if product.raw.get("ean") and low[product.raw["ean"]] < float(product.price_text)), 0)

    def test_what_waits_at_the_gate_is_kept_for_the_cap_of_a_category_to_name_among(self) -> None:
        big = [_product(number, kinds_hint="kettle") for number in range(20)]
        before = {row_key(product) for product in big[:4]}
        result = shop_cap.cap_shops(big, [KETTLE] * 20, kept_before=before, limit=8, may_enter=lambda product: False)
        # Every product of the shop that waits, in its order; the candidates it named itself are the first of them.
        self.assertEqual(sorted(result.waiting["Big"]), list(range(4, 20)))
        self.assertEqual(result.waiting["Big"][:5], result.candidates)
        self.assertEqual(result.allowed, {"Big": 5})
        # A shop with no place open, or with none that waits, gives nothing to name among.
        full = shop_cap.cap_shops(big, [KETTLE] * 20, kept_before={row_key(product) for product in big[:8]}, limit=8,
                                  may_enter=lambda product: False)
        self.assertEqual((full.waiting, full.allowed, full.candidates), ({}, {}, ()))
        ungated = shop_cap.cap_shops(big, [KETTLE] * 20, kept_before=before, limit=8)
        self.assertEqual((ungated.waiting, ungated.allowed, ungated.candidates), ({}, {}, ()))

    def test_a_shops_candidates_are_only_those_the_cap_of_a_category_names_too(self) -> None:
        # The look of 22/11: a shop's place open is no place open in a category at its size.
        big = [_product(number, kinds_hint="kettle") for number in range(20)]
        before = {row_key(product) for product in big[:4]}
        result = shop_cap.cap_shops(big, [KETTLE] * 20, kept_before=before, limit=8, may_enter=lambda product: False)
        waiting = result.waiting["Big"]
        # The category has a place for three of them, far down the shop's order: those three, in its order.
        named = {waiting[9], waiting[12], waiting[15]}
        some = shop_cap.vetted(result, named)
        self.assertEqual(some.candidates, (waiting[9], waiting[12], waiting[15]))
        self.assertEqual(some.shops["Big"]["candidates"], 3)
        self.assertEqual((some.keep, some.shops["Big"]["waiting_at_the_gate"]), (result.keep, 16))
        # For none of them: the shop names none, and no product is asked for nothing.
        none = shop_cap.vetted(result, ())
        self.assertEqual((none.candidates, none.shops["Big"]["candidates"]), ((), 0))
        # For every one: the first by its order, as many as it may name and no more.
        every = shop_cap.vetted(result, waiting)
        self.assertEqual(every.candidates, result.candidates)
        self.assertEqual(len(every.candidates), 5)
        # What it was given is as it was.
        self.assertEqual((len(result.candidates), result.shops["Big"]["candidates"]), (5, 5))

    def test_the_first_night_the_passed_come_before_the_never_asked(self) -> None:
        big = [_product(number, kinds_hint="kettle") for number in range(10)]
        before = {row_key(product) for product in big}
        passed = {row_key(big[number]) for number in (7, 8, 9)}
        result = shop_cap.cap_shops(big, [KETTLE] * 10, kept_before=before, limit=4,
                                    passed=lambda product: row_key(product) in passed)
        kept = _numbers(big, result.keep)
        self.assertTrue({"big-7", "big-8", "big-9"} <= set(kept))
        self.assertEqual(result.shops["Big"]["kept_passed"], 3)

    def test_a_kind_is_thin_by_what_the_night_before_kept(self) -> None:
        # 5 toasters are offered, but the site showed 1 of them last night (and 3 kettles): thin under 3.
        big = [_product(number, kinds_hint="kettle") for number in range(10)]
        toasters = [_product(100 + number, shop="Other", kinds_hint="toaster") for number in range(4)]
        mine = _product(50, kinds_hint="toaster")
        products = big + [mine] + toasters
        kinds = [KETTLE] * 10 + [TOASTER] * 5
        before = {row_key(product) for product in big[:3]} | {row_key(toasters[0])}
        result = shop_cap.cap_shops(products, kinds, kept_before=before, limit=5, thin=3)
        self.assertIn("big-50", _numbers(products, result.keep))
        self.assertEqual(result.shops["Big"]["kept_by_step"]["thin kinds"], 1)
        self.assertEqual(result.shops["Big"]["kept_from_before"], 3)
        # With no memory of the night before, by every product given: 5 toasters are no thin kind.
        fresh = shop_cap.cap_shops(products, kinds, limit=5, thin=3)
        self.assertEqual(fresh.shops["Big"]["kept_by_step"]["thin kinds"], 0)


class ShopOrderTests(unittest.TestCase):
    def test_a_product_another_shop_shows_cheaper_is_asked_last(self) -> None:
        big = [_product(number, kinds_hint="kettle") for number in range(5)]
        big[2] = _product(2, gtin=_gtin(2), price=60.0)
        small = [_product(2, shop="Small", gtin=_gtin(2), price=30.0)]
        products = big + small
        order = shop_cap.shop_order(products, [KETTLE] * 6)
        self.assertEqual(order["Big"][-1], 2)
        self.assertEqual(sorted(order["Big"]), [0, 1, 2, 3, 4])
        self.assertEqual(order["Small"], [5])


class SwitchTests(unittest.TestCase):
    def test_the_switch_is_off_in_the_repo_and_read_strictly(self) -> None:
        self.assertFalse(shop_cap.shop_cap_on())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "switch.json"
            self.assertFalse(shop_cap.shop_cap_on(path))
            for text in ("{", '{"cap": "true"}', "[]"):
                path.write_text(text, encoding="utf-8")
                self.assertFalse(shop_cap.shop_cap_on(path), text)
            path.write_text(json.dumps({"cap": True}), encoding="utf-8")
            self.assertTrue(shop_cap.shop_cap_on(path))

    def test_the_switch_is_frozen_with_the_code(self) -> None:
        from picwise_providers.prepared_catalogue import _FROZEN_FILES

        self.assertIn("data/shop_cap_switch.json", _FROZEN_FILES)


if __name__ == "__main__":
    unittest.main()
