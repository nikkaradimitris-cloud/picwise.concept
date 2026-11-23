"""The cap of 15% a category: which products a capped catalogue keeps.

`picwise_providers.catalogue_cap`. Owner, 2026-10-27: no category of like products over
15% of all products, so that no shop makes the site one kind of shop to Google, the
server's room spreads over more categories, and each search looks complete, clean
information first; yesterday's kept ones the next night's starting point, more products
a larger cap and fewer a smaller one in proportion. Pinned here: the cap is 15% of what
is kept, worked out at once (no category over it, the next number up would be), and a
category under it keeps all; inside a category the places are shared fairly over its
kinds, a shelf naming a kind joining it (an accessory marked so stays on its shelf, as
the check of far prices asks); inside a kind the clean ones first, those sold by more
than one shop first among them, spread over the price range; the night before's kept
ones stay while they fit, and when there are fewer places the ones that stay keep their
spread; the same input gives the same choice; too few categories cut nothing. And the
pool Google may be given from (owner, 2026-10-30: every product stays in the search):
kept beside the prepared file and read back as written, the next night's starting
point; no file, or a broken one, starts afresh. And the products offered for the cap to
name its candidates among (the checks' rules 19.6.2; the look of 23/11): they count for no
category's size and no kind's share, none is kept, and they are named only where a place
is open for them.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.catalogue_balance import capped_size  # noqa: E402
from picwise_providers.catalogue_cap import (  # noqa: E402
    cap_catalogue,
    fair_quotas,
    google_pool_path,
    joined_parts,
    read_google_pool,
    row_key,
    write_google_pool,
)
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402

JEWELLERY = "Apparel & Accessories > Jewelry > Rings"
SMALL = [f"Home & Garden > Decor {number} > Vases" for number in range(10)]


def _product(
    number: int,
    category: str,
    *,
    price: float = 10.0,
    shop: str = "Fictional Shop",
    gtin: str = "",
    image: bool = True,
    stock: str = "in stock",
) -> ProviderProduct:
    raw = {"merchant_name": shop, "availability": stock, "data_provenance": "local_test_fixture"}
    if gtin:
        raw["ean"] = gtin
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=f"Fictional product {number}",
        brand="Fictbrand",
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg" if image else "",
        price_text=f"{price:.2f}",
        availability_text=stock,
        currency="GBP",
        raw=raw,
    )


def _gtin(number: int) -> str:
    return f"{5_000_000_000_000 + number:013d}"


def _context(products: list[ProviderProduct]):
    # One sold-out row elsewhere in the feed, so the stock column varies and an
    # "in stock" in it is a stock state that varies.
    sold_out = _product(999_999, "Home & Garden > Elsewhere", stock="out of stock")
    return build_feed_availability_context(tuple(products) + (sold_out,))


def _catalogue(sizes: dict[str, int], *, start: int = 0) -> list[ProviderProduct]:
    products = []
    number = start
    for category, count in sizes.items():
        for _ in range(count):
            products.append(_product(number, category, price=1.0 + number, gtin=_gtin(number)))
            number += 1
    return products


class CapSizeTests(unittest.TestCase):
    def test_the_cap_is_fifteen_percent_of_what_is_kept(self) -> None:
        sizes = {JEWELLERY: 300, "Apparel & Accessories > Clothing > Shirts": 40, **{name: 20 for name in SMALL}}
        products = _catalogue(sizes)
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        self.assertEqual(result.size, capped_size(list(sizes.values())))
        kept = result.kept
        largest = max(after for _before, after in result.by_category.values())
        self.assertLessEqual(largest, 0.15 * kept)
        # One more product a category would break the share: the cap is the largest that holds.
        self.assertGreater(result.size + 1, 0.15 * (kept + 2))
        for name in SMALL:
            self.assertEqual(result.by_category[f"home & garden > decor {SMALL.index(name)}"], (20, 20))
        self.assertEqual(result.by_category["apparel & accessories > jewelry"][1], result.size)

    def test_a_category_keeps_no_more_than_its_most_whatever_the_share(self) -> None:
        # Owner, 2026-11-19: «μέγιστο όριο ανά κατηγορία», set on the server.
        sizes = {JEWELLERY: 300, "Apparel & Accessories > Clothing > Shirts": 40, **{name: 20 for name in SMALL}}
        products = _catalogue(sizes)
        free = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        held = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products), category_max=25)
        self.assertGreater(free.size, 25)
        self.assertEqual(held.size, 25)
        self.assertEqual(held.category_max, 25)
        self.assertEqual(held.by_category["apparel & accessories > jewelry"], (300, 25))
        self.assertEqual(held.by_category["apparel & accessories > clothing"], (40, 25))
        for name in SMALL:
            self.assertEqual(held.by_category[f"home & garden > decor {SMALL.index(name)}"], (20, 20))
        too_few = _catalogue({JEWELLERY: 50})
        alone = cap_catalogue(too_few, [frozenset()] * len(too_few), feed_ctx=_context(too_few), category_max=30)
        self.assertEqual(alone.by_category["apparel & accessories > jewelry"], (50, 30))

    def test_more_products_elsewhere_raise_the_cap_and_fewer_lower_it(self) -> None:
        base = {JEWELLERY: 300, **{name: 20 for name in SMALL}}
        more = {JEWELLERY: 300, **{name: 30 for name in SMALL}}
        fewer = {JEWELLERY: 300, **{name: 10 for name in SMALL}}
        sizes = []
        for shape in (base, more, fewer):
            products = _catalogue(shape)
            sizes.append(cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products)).size)
        self.assertLess(sizes[0], sizes[1])
        self.assertGreater(sizes[0], sizes[2])

    def test_too_few_categories_cut_nothing(self) -> None:
        products = _catalogue({JEWELLERY: 50, "Home & Garden > Decor > Vases": 5})
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        self.assertIsNone(result.size)
        self.assertEqual(result.kept, len(products))


class FairShareTests(unittest.TestCase):
    def test_a_small_kind_keeps_all_and_the_rest_is_shared(self) -> None:
        quotas = fair_quotas({"ring": 80, "earrings": 15, "necklace": 5}, 30)
        self.assertEqual(quotas, {"necklace": 5, "ring": 13, "earrings": 12})
        self.assertEqual(sum(quotas.values()), 30)

    def test_a_shelf_naming_a_kind_of_its_category_joins_that_kind(self) -> None:
        categories = ["apparel & accessories > jewelry"] * 4 + ["apparel & accessories > clothing"] * 2 + ["home & garden > decor"]
        parts = [
            "ring",
            "watch",
            "shelf: clothing & accessories > jewellery & watches > rings",
            "shelf: clothing & accessories > jewellery & watches > watches",
            "t_shirt",
            "shelf: clothing & accessories > clothing > t-shirts",
            "shelf: home & garden > decor > rings",
        ]
        self.assertEqual(
            joined_parts(categories, parts),
            ["ring", "watch", "ring", "watch", "t_shirt", "t_shirt", "shelf: home & garden > decor > rings"],
        )

    def test_a_marked_accessory_stays_on_its_shelf(self) -> None:
        # Earring backs on a shelf of earrings are no earrings: the check of far prices
        # leaves them there (2026-10-28). The cap still joins them, as chosen.
        shelf = "shelf: clothing & accessories > jewellery & watches > earrings"
        self.assertEqual(
            joined_parts(["apparel & accessories > jewelry"] * 3, ["earrings", shelf, shelf], [False, False, True]),
            ["earrings", "earrings", shelf],
        )
        earrings = "Apparel & Accessories > Jewelry > Earrings"
        products = [_product(index, earrings, gtin=_gtin(index)) for index in range(60)]
        products += [_product(10_000 + index, name, gtin=_gtin(10_000 + index)) for index, name in enumerate(SMALL * 20)]
        kinds = [frozenset({"earrings"})] * 40 + [frozenset()] * 10 + [frozenset({"__accessory__"})] * 10
        kinds += [frozenset()] * (len(products) - 60)
        inside = cap_catalogue(products, kinds, feed_ctx=_context(products)).inside["apparel & accessories > jewelry"]
        self.assertEqual(set(inside), {"earrings"})
        self.assertEqual(inside["earrings"][0], 60)

    def test_rings_on_a_shelf_of_rings_take_no_second_share(self) -> None:
        rings = [_product(index, JEWELLERY, gtin=_gtin(index)) for index in range(300)]
        products = rings + [
            _product(10_000 + index, name, gtin=_gtin(10_000 + index)) for index, name in enumerate(SMALL * 20)
        ]
        kinds = [frozenset({"ring"}) if index < 150 else frozenset() for index in range(len(products))]
        result = cap_catalogue(products, kinds, feed_ctx=_context(products))
        self.assertEqual(result.inside["apparel & accessories > jewelry"], {"ring": (300, result.size)})

    def test_inside_a_category_its_kinds_share_its_places(self) -> None:
        products = _catalogue({JEWELLERY: 300, **{name: 20 for name in SMALL}})
        kinds = [frozenset({"ring"}) if index < 270 else frozenset({"earrings"}) for index in range(300)]
        kinds += [frozenset()] * (len(products) - 300)
        result = cap_catalogue(products, kinds, feed_ctx=_context(products))
        inside = result.inside["apparel & accessories > jewelry"]
        self.assertEqual(inside["earrings"], (30, min(30, result.size // 2)))
        self.assertEqual(inside["ring"][1] + inside["earrings"][1], result.size)


class WhichOnesStayTests(unittest.TestCase):
    def _over(self, products: list[ProviderProduct]) -> list[ProviderProduct]:
        # Ten small categories of 20 make the cap about 35 a category.
        number = 10_000
        for name in SMALL:
            for _ in range(20):
                products.append(_product(number, name, gtin=_gtin(number)))
                number += 1
        return products

    def test_clean_ones_first(self) -> None:
        clean = [_product(index, JEWELLERY, price=10.0 + index, gtin=_gtin(index)) for index in range(40)]
        bare = [_product(100 + index, JEWELLERY, price=10.0 + index, image=False) for index in range(200)]
        products = self._over(clean + bare)
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        kept_clean = sum(result.keep[: len(clean)])
        self.assertEqual(kept_clean, min(len(clean), result.size))
        self.assertEqual(result.kept_by_missing_signs.get(0), kept_clean)

    def test_sold_by_more_than_one_shop_first_among_the_clean(self) -> None:
        shared = [_product(index, JEWELLERY, gtin=_gtin(index), shop="Fictional Shop") for index in range(20)]
        elsewhere = [_product(500 + index, "Home & Garden > Elsewhere > Vases", gtin=_gtin(index), shop="Other Shop") for index in range(20)]
        alone = [_product(1_000 + index, JEWELLERY, gtin=_gtin(1_000 + index)) for index in range(200)]
        products = self._over(shared + alone) + elsewhere
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        self.assertEqual(sum(result.keep[:20]), 20)
        self.assertGreaterEqual(result.kept_in_several_shops, 20)

    def test_spread_over_the_price_range(self) -> None:
        rings = [_product(index, JEWELLERY, price=1.0 + index, gtin=_gtin(index)) for index in range(300)]
        products = self._over(rings)
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        prices = result.prices["apparel & accessories > jewelry"]
        everything, kept = prices["all"], prices["kept"]
        # Cheap, middle and dear all stay: the kept ones' range covers most of the whole range.
        self.assertLess(kept[0], everything[0] + 10)
        self.assertGreater(kept[2], everything[2] - 10)
        self.assertAlmostEqual(kept[1], everything[1], delta=10)

    def test_the_same_input_gives_the_same_choice(self) -> None:
        products = self._over([_product(index, JEWELLERY, gtin=_gtin(index)) for index in range(300)])
        first = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        second = cap_catalogue(list(products), [frozenset()] * len(products), feed_ctx=_context(products))
        self.assertEqual(first.keep, second.keep)


class NightBeforeTests(unittest.TestCase):
    def _night(self, rings: int, others: int, kept_before=frozenset()):
        products = [_product(index, JEWELLERY, price=1.0 + index, gtin=_gtin(index)) for index in range(rings)]
        number = 10_000
        for name in SMALL:
            for _ in range(others):
                products.append(_product(number, name, gtin=_gtin(number)))
                number += 1
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products), kept_before=kept_before)
        rings_kept = {row_key(product) for product, kept in zip(products[:rings], result.keep) if kept}
        return result, rings_kept

    def test_yesterdays_kept_ones_stay_and_new_places_go_to_others(self) -> None:
        _yesterday, kept_yesterday = self._night(300, 20)
        # Today the other categories grow: the cap rises, yesterday's rings all stay.
        today, kept_today = self._night(300, 30, kept_before=frozenset(kept_yesterday))
        self.assertTrue(kept_yesterday <= kept_today)
        self.assertGreater(len(kept_today), len(kept_yesterday))
        # Counted in the categories over the cap only: yesterday's rings, all of them.
        self.assertEqual(today.kept_from_before, len(kept_yesterday))

    def test_fewer_places_keep_a_spread_of_yesterdays(self) -> None:
        _yesterday, kept_yesterday = self._night(300, 30)
        today, kept_today = self._night(300, 10, kept_before=frozenset(kept_yesterday))
        self.assertLess(len(kept_today), len(kept_yesterday))
        self.assertTrue(kept_today <= kept_yesterday)
        prices = today.prices["apparel & accessories > jewelry"]["kept"]
        self.assertLess(prices[0], 30)
        self.assertGreater(prices[2], 270)

    def test_a_kept_product_no_longer_shown_is_simply_gone(self) -> None:
        _yesterday, kept_yesterday = self._night(300, 20)
        gone = sorted(kept_yesterday)[0]
        products_today, kept_today = self._night(300, 20, kept_before=frozenset(kept_yesterday))
        self.assertIn(gone, kept_today)
        # Drop that row from today's products: it cannot be kept, another takes its place.
        products = [_product(index, JEWELLERY, price=1.0 + index, gtin=_gtin(index)) for index in range(300)]
        products = [product for product in products if row_key(product) != gone]
        number = 10_000
        for name in SMALL:
            for _ in range(20):
                products.append(_product(number, name, gtin=_gtin(number)))
                number += 1
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products), kept_before=frozenset(kept_yesterday))
        kept_rings = {row_key(product) for product, kept in zip(products, result.keep) if kept and "Jewelry" in product.category_text}
        self.assertNotIn(gone, kept_rings)
        self.assertEqual(len(kept_rings), result.size)
        self.assertEqual(products_today.size, result.size)


class OfferedTests(unittest.TestCase):
    """The products of a shop over the most a shop passes that wait at the gate, given for
    the cap to name its candidates among (`offered`; the checks' rules 19.6.2 and 20.7).
    The look of 23/11: counted like the rest, the waiting rows of a shop with one place open
    moved every kind's share in its categories from one night to the next."""

    NECKLACES = "Apparel & Accessories > Jewelry > Necklaces"

    def _others(self, count: int = 20) -> list[ProviderProduct]:
        products = []
        number = 10_000
        for name in SMALL:
            for _ in range(count):
                products.append(_product(number, name, gtin=_gtin(number)))
                number += 1
        return products

    def test_they_count_for_no_categorys_size_and_no_share_and_none_is_kept(self) -> None:
        products = [_product(index, JEWELLERY, price=1.0 + index, gtin=_gtin(index)) for index in range(300)] + self._others()
        offered = [_product(20_000 + index, JEWELLERY, price=2.0 + index, shop="Big Shop", gtin=_gtin(20_000 + index))
                   for index in range(600)]
        offered += [_product(30_000 + index, SMALL[0], shop="Big Shop", gtin=_gtin(30_000 + index)) for index in range(50)]
        given = products + offered
        context = _context(given)
        kinds = [frozenset()] * len(given)
        night_before = cap_catalogue(products, kinds[: len(products)], feed_ctx=context)
        self.assertEqual(night_before.size, 35)

        def nothing_new(_product_: ProviderProduct) -> bool:
            return False

        plain = cap_catalogue(products, kinds[: len(products)], feed_ctx=context, kept_before=night_before.kept_keys,
                              may_enter=nothing_new)
        result = cap_catalogue(given, kinds, feed_ctx=context, kept_before=night_before.kept_keys, may_enter=nothing_new,
                               offered=range(len(products), len(given)))
        self.assertEqual((result.size, plain.size), (35, 35))
        self.assertEqual(result.keep[: len(products)], plain.keep)
        self.assertFalse(any(result.keep[len(products):]))
        self.assertEqual((result.by_category, result.by_shop, result.inside), (plain.by_category, plain.by_shop, plain.inside))
        self.assertEqual(result.kept_keys, plain.kept_keys)
        # Counted like the rest, as they were, they move the size of every category (and with
        # it each kind's share: the walk of nights in `test_picwise_checks_walk`).
        counted = cap_catalogue(given, kinds, feed_ctx=context, kept_before=night_before.kept_keys, may_enter=nothing_new)
        self.assertEqual(counted.size, 38)

    def test_in_a_category_over_its_size_they_are_named_only_for_the_places_their_kind_has_open(self) -> None:
        # Seventeen clean rings, the ones the cap keeps; the other rings have no image. The
        # necklaces fill their share. Five kept rings then leave the feed: the rings have five
        # places open, the necklaces none.
        rings = [_product(index, JEWELLERY, price=1.0 + index, gtin=_gtin(index), image=index < 17) for index in range(300)]
        necklaces = [_product(1_000 + index, self.NECKLACES, price=1.0 + index, gtin=_gtin(1_000 + index)) for index in range(300)]
        others = self._others()
        first = rings + necklaces + others
        offered = [_product(20_000 + index, JEWELLERY, price=5.0 + index, shop="Big Shop", gtin=_gtin(20_000 + index))
                   for index in range(40)]
        offered += [_product(21_000 + index, self.NECKLACES, price=5.0 + index, shop="Big Shop", gtin=_gtin(21_000 + index))
                    for index in range(40)]
        context = _context(first + offered)
        night_before = cap_catalogue(first, [frozenset()] * len(first), feed_ctx=context)
        kept_rings = [product for product, kept in zip(rings, night_before.keep) if kept]
        self.assertEqual((night_before.size, len(kept_rings)), (35, 17))
        gone = {row_key(product) for product in kept_rings[:5]}
        today = [product for product in first if row_key(product) not in gone]
        given = today + offered
        result = cap_catalogue(given, [frozenset()] * len(given), feed_ctx=context, kept_before=night_before.kept_keys,
                               may_enter=lambda _product_: False, offered=range(len(today), len(given)))
        self.assertFalse(any(result.keep[len(today):]))
        named = [given[index] for index in result.candidates if "Jewelry" in given[index].category_text]
        # One and a quarter times the five places, the clean ones first: the offered rings, which
        # have an image. No necklace is named, offered or not: their kind has no place open.
        self.assertEqual(len(named), 7)
        self.assertTrue(all(product.category_text == JEWELLERY and product.raw["merchant_name"] == "Big Shop" for product in named))
        # With no place open in any kind, none is named.
        full = cap_catalogue(first + offered, [frozenset()] * len(first + offered), feed_ctx=context,
                             kept_before=night_before.kept_keys, may_enter=lambda _product_: False,
                             offered=range(len(first), len(first + offered)))
        self.assertEqual([index for index in full.candidates if index >= len(first)], [])

    def test_in_a_category_under_its_size_as_many_are_named_as_it_has_places_for(self) -> None:
        products = [_product(index, JEWELLERY, price=1.0 + index, gtin=_gtin(index)) for index in range(300)] + self._others()
        # Thirty the most a category keeps: the first small one has 20, so ten places; a
        # category the shops keep nothing of has thirty; the one over its size has none.
        dolls = "Toys & Games > Toys > Dolls"
        offered = [_product(30_000 + index, SMALL[0], price=1.0 + index, shop="Big Shop", gtin=_gtin(30_000 + index))
                   for index in range(100)]
        offered += [_product(40_000 + index, dolls, price=1.0 + index, shop="Big Shop", gtin=_gtin(40_000 + index))
                    for index in range(60)]
        given = products + offered
        context = _context(given)
        night_before = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=context, category_max=30)
        self.assertEqual(night_before.size, 30)
        result = cap_catalogue(given, [frozenset()] * len(given), feed_ctx=context, kept_before=night_before.kept_keys,
                               category_max=30, may_enter=lambda _product_: False, offered=range(len(products), len(given)))
        self.assertEqual(result.size, 30)
        named = [given[index] for index in result.candidates if index >= len(products)]
        by_category = {}
        for product in named:
            by_category[product.category_text] = by_category.get(product.category_text, 0) + 1
        self.assertEqual(by_category, {SMALL[0]: 13, dolls: 38})
        # Spread over their prices, not the cheapest alone.
        prices = sorted(float(product.price_text) for product in named if product.category_text == SMALL[0])
        self.assertLess(prices[0], 10)
        self.assertGreater(prices[-1], 90)


class GooglePoolFileTests(unittest.TestCase):
    """The pool Google may be given from, kept from one night to the next (owner,
    2026-10-30: every product stays in the search; the cap chooses only that pool)."""

    def test_the_night_before_s_pool_is_read_back_as_written(self) -> None:
        products = _catalogue({JEWELLERY: 300, **{name: 20 for name in SMALL}})
        result = cap_catalogue(products, [frozenset()] * len(products), feed_ctx=_context(products))
        with tempfile.TemporaryDirectory() as folder:
            path = google_pool_path(Path(folder) / "prepared" / "catalogue.json.gz")
            self.assertEqual(path.name, "google_pool.json.gz")
            self.assertGreater(write_google_pool(result, path, prepared_at=datetime(2026, 10, 30, 4, 21, tzinfo=timezone.utc)), 0)
            self.assertEqual(read_google_pool(path), result.kept_keys)
            self.assertEqual(len(result.kept_keys), result.kept)
            # The next night on the same products keeps the same pool, all of it from before.
            again = cap_catalogue(
                products, [frozenset()] * len(products), feed_ctx=_context(products), kept_before=read_google_pool(path)
            )
            self.assertEqual(again.kept_keys, result.kept_keys)
            self.assertEqual(again.kept_from_before, result.by_category["apparel & accessories > jewelry"][1])

    def test_no_file_or_a_broken_one_starts_afresh(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "google_pool.json.gz"
            self.assertEqual(read_google_pool(path), frozenset())
            path.write_bytes(b"not a pool")
            self.assertEqual(read_google_pool(path), frozenset())


if __name__ == "__main__":
    unittest.main()
