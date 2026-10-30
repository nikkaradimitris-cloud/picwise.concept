"""How the shown products spread, and what a cap on a share would cut: measured only.

`src/picwise_providers/catalogue_balance.py`. Owner, 2026-10-26: a shop of 100,000 watches
added to 200,000 products makes PicWise look like a watch site, so no kind should hold
more than about 15% of all products, «έτσι ώστε να έχουμε μία ωραία κατανομή ειδών»;
then «Ναι» to measuring it first. Pinned here: the cap's arithmetic (each group keeps at
most C, the largest C with no group over the share of what all keep; none with too few
groups), the department and aisle read off Google's shelves in British or US names, the
shop, each product under its narrowest kind, and how many kinds have products from at
least 3 shops.

Every product is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.catalogue_balance import (  # noqa: E402
    OWN_CATEGORIES,
    capped_size,
    measure_catalogue_balance,
)
from picwise_providers.contracts import ProviderProduct  # noqa: E402


def _product(pid: str, shop: str, category: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon Thing {pid}", brand="Fixturon",
        category_text=category, product_url=f"https://shop.example.invalid/p/{pid}",
        image_url=f"https://shop.example.invalid/i/{pid}.jpg", price_text="20.00", availability_text="in stock",
        currency="GBP", raw={"merchant_name": shop},
    )


class CapTests(unittest.TestCase):
    def test_the_largest_size_with_no_group_over_the_share(self) -> None:
        sizes = [360_000] + [30_000] * 5 + [10_000] * 10
        cap = capped_size(sizes)
        kept = sum(min(size, cap) for size in sizes)
        self.assertEqual(cap, 44_117)
        self.assertLessEqual(cap, 0.15 * kept)
        self.assertGreater(cap + 1, 0.15 * (kept + sum(1 for size in sizes if size > cap)))
        # Nothing over the share: nothing is cut.
        self.assertEqual(capped_size([10] * 10), 10)
        self.assertEqual(capped_size([100, 1, 1, 1, 1, 1, 1, 1]), 1)
        self.assertEqual(capped_size([]), 0)

    def test_too_few_groups_cannot_hold(self) -> None:
        # Six groups of 15% are 90%: no size above 0 holds.
        self.assertIsNone(capped_size([70, 10, 10, 10]))
        self.assertIsNone(capped_size([5]))
        self.assertIsNone(capped_size([10] * 6))
        self.assertEqual(capped_size([10] * 7), 10)


class MeasureTests(unittest.TestCase):
    def setUp(self) -> None:
        rings = [_product(f"r{n}", "Fixture Jewels", "Clothing & Accessories > Jewellery & Watches > Rings")
                 for n in range(70)]
        kettles = [_product(f"k{n}", f"Fixture Kitchen {n % 3}", "Home & Garden > Kitchen & Dining > Kettles")
                   for n in range(20)]
        vacuums = [_product(f"v{n}", "Fixture Cleaning", "Home & Garden > Household Appliances > Vacuums")
                   for n in range(8)]
        own = [_product("o1", "Fixture Office", "Windows Laptops"), _product("o2", "Fixture Office", "Windows Laptops")]
        self.products = rings + kettles + vacuums + own
        self.kinds = (
            [frozenset()] * 70
            + [frozenset({"kettle"})] * 20
            + [frozenset({"robot_vacuum", "vacuum_cleaner"})] * 8
            + [frozenset({"laptop"}), frozenset({"__uncertain_kind__"})]
        )
        self.note = measure_catalogue_balance(self.products, self.kinds)

    def test_departments_and_aisles_from_googles_shelves(self) -> None:
        department = self.note["department"]
        self.assertEqual(
            [(entry["name"], entry["products"]) for entry in department["largest"]],
            [("apparel & accessories", 70), ("home & garden", 28), (OWN_CATEGORIES, 2)],
        )
        self.assertEqual(department["over"], 2)
        # Three groups: a cap of 15% cannot hold.
        self.assertIsNone(department["cap"])
        aisles = {entry["name"]: entry["products"] for entry in self.note["aisle"]["largest"]}
        self.assertEqual(aisles["apparel & accessories > jewelry"], 70)
        self.assertEqual(aisles["home & garden > kitchen & dining"], 20)
        self.assertEqual(aisles["home & garden > household appliances"], 8)

    def test_shops_kinds_and_kinds_from_three_shops(self) -> None:
        shops = {entry["name"]: entry["products"] for entry in self.note["shop"]["largest"]}
        self.assertEqual(shops["Fixture Jewels"], 70)
        self.assertEqual(self.note["shop"]["groups"], 6)
        kinds = {entry["name"]: entry["products"] for entry in self.note["kind"]["largest"]}
        # Each product under its narrowest kind; a doubtful one has none.
        self.assertEqual(kinds, {"kettle": 20, "robot_vacuum": 8, "laptop": 1})
        self.assertEqual(self.note["no_kind"], 71)
        self.assertEqual(self.note["kinds_by_shops"], {"kinds": 3, "one_shop": 2, "two_shops": 0, "three_or_more": 1})

    def test_a_cap_that_holds_cuts_the_largest_groups_only(self) -> None:
        products = [_product(f"p{n}", f"Shop {n % 10}", "Home & Garden") for n in range(100)]
        products += [_product(f"j{n}", "Shop Big", "Home & Garden") for n in range(100)]
        note = measure_catalogue_balance(products, [frozenset()] * len(products))
        shop = note["shop"]
        self.assertEqual(shop["groups"], 11)
        # Ten shops of 10 and one of 100: capped at 17, 117 are kept.
        self.assertEqual((shop["cap"], shop["kept"], shop["cut"]), (17, 117, 83))
        self.assertEqual(shop["cut_by_group"], [{"name": "Shop Big", "cut": 83, "kept": 17}])


if __name__ == "__main__":
    unittest.main()
