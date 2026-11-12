"""How many products two or more shops sell, counted by barcode (the audit's fixes,
2026-11-11, `docs/PICWISE_AUDIT_FIXES.md` 4.A.2).

The product pages for Google start from the products several shops sell, and nobody knew
how many there are. The night's note now says it (`catalogue_balance.measure_catalogue_balance`,
`shared_products`, under `balance` in `prepared.json`), and the server's report prints it
(`deployment/server/print_shops.py`). Pinned here:

- a barcode two shops carry counts once, however many rows carry it;
- one shop's twice-listed barcode does not make a product sold by two shops;
- no barcode, or one whose check digit does not agree, never counts;
- the UPC-12 and EAN-13 forms of one code are one product;
- per category (the first two levels of the shop's Google shelf, as the cap reads it),
  each barcode once, under the category most of its rows name, so the categories add up
  to the whole;
- the report prints it, and a note written before it prints nothing about it.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.catalogue_balance import measure_catalogue_balance  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

KITCHEN = "Home & Garden > Kitchen & Dining > Kitchen Appliances"
AUDIO = "Electronics > Audio > Headphones"


def _ean13(base12: str) -> str:
    total = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


def _product(pid: str, shop: str, *, ean: str = "", shelf: str = KITCHEN, column: str = "ean",
             mpn: str = "", brand: str = "Fixturon") -> ProviderProduct:
    raw = {"merchant_name": shop}
    if ean:
        raw[column] = ean
    if mpn:
        raw["mpn"] = mpn
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon Item {pid}", brand=brand,
        category_text=shelf, product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg", price_text="10.00",
        availability_text="in stock", currency="GBP", raw=raw,
    )


def _shared(products: list[ProviderProduct]) -> dict:
    return measure_catalogue_balance(products, [frozenset()] * len(products))["shared_products"]


class SharedProductsTests(unittest.TestCase):
    def test_a_barcode_two_shops_carry_counts_once(self) -> None:
        code = _ean13("501234500001")
        shared = _shared([
            _product("a1", "Shop One", ean=code),
            _product("a2", "Shop Two", ean=code),
            _product("a3", "Shop Two", ean=code),
        ])
        self.assertEqual(shared["barcodes"], 1)
        self.assertEqual(shared["two_or_more_shops"], 1)

    def test_one_shops_twice_listed_barcode_does_not_count(self) -> None:
        code = _ean13("501234500002")
        shared = _shared([_product("b1", "Shop One", ean=code), _product("b2", "Shop One", ean=code)])
        self.assertEqual(shared["barcodes"], 1)
        self.assertEqual(shared["two_or_more_shops"], 0)

    def test_no_barcode_or_a_wrong_check_digit_never_counts(self) -> None:
        good = _ean13("501234500003")
        wrong = good[:-1] + str((int(good[-1]) + 1) % 10)
        shared = _shared([
            _product("c1", "Shop One"),
            _product("c2", "Shop Two"),
            _product("c3", "Shop One", ean=wrong),
            _product("c4", "Shop Two", ean=wrong),
        ])
        self.assertEqual(shared, {"barcodes": 0, "two_or_more_shops": 0, "categories": 0, "by_category": []})

    def test_the_upc_and_ean_forms_of_one_code_are_one_product(self) -> None:
        shared = _shared([
            _product("d1", "Shop One", ean="036000291452"),
            _product("d2", "Shop Two", ean="0036000291452", column="product_GTIN"),
        ])
        self.assertEqual(shared["barcodes"], 1)
        self.assertEqual(shared["two_or_more_shops"], 1)

    def test_per_category_each_barcode_once_under_the_category_most_rows_name(self) -> None:
        kettle = _ean13("501234500010")   # two kitchen rows, one audio row: kitchen
        toaster = _ean13("501234500011")  # one shop only
        headset = _ean13("501234500012")  # one row each: the tie goes by name
        speaker = _ean13("501234500013")
        products = [
            _product("e1", "Shop One", ean=kettle),
            _product("e2", "Shop Two", ean=kettle),
            _product("e3", "Shop Three", ean=kettle, shelf=AUDIO),
            _product("e4", "Shop One", ean=toaster),
            _product("e5", "Shop One", ean=headset, shelf=AUDIO),
            _product("e6", "Shop Two", ean=headset),
            _product("e7", "Shop One", ean=speaker, shelf=AUDIO),
            _product("e8", "Shop Two", ean=speaker, shelf=AUDIO),
            _product("e9", "Shop Three", ean=speaker, shelf="My Shop > Speakers"),
            _product("e10", "Shop Two"),
        ]
        shared = _shared(products)
        self.assertEqual(shared["barcodes"], 4)
        self.assertEqual(shared["two_or_more_shops"], 3)
        self.assertEqual(shared["categories"], 2)
        self.assertEqual(
            shared["by_category"],
            [
                {"category": "electronics > audio", "barcodes": 2, "two_or_more_shops": 2},
                {"category": "home & garden > kitchen & dining", "barcodes": 2, "two_or_more_shops": 1},
            ],
        )
        self.assertEqual(sum(entry["barcodes"] for entry in shared["by_category"]), shared["barcodes"])
        self.assertEqual(
            sum(entry["two_or_more_shops"] for entry in shared["by_category"]), shared["two_or_more_shops"]
        )

    def test_the_note_holds_no_barcode_nor_link(self) -> None:
        code = _ean13("501234500020")
        text = json.dumps(_shared([_product("f1", "Shop One", ean=code), _product("f2", "Shop Two", ean=code)]))
        self.assertNotIn(code, text)
        self.assertNotIn("http", text)


class SharedByBrandAndPartTests(unittest.TestCase):
    """The mechanism's step 15 (docs/PICWISE_AUDIT_FIXES.md, 4.E): the overlap a barcode
    alone does not show."""

    def _parts(self, products: list[ProviderProduct]) -> dict:
        return measure_catalogue_balance(products, [frozenset()] * len(products))["shared_by_brand_and_part"]

    def test_two_shops_with_one_brand_and_part_number_and_no_barcode(self) -> None:
        parts = self._parts([
            _product("g1", "Shop One", mpn="FX-100"),
            _product("g2", "Shop Two", mpn="fx-100"),
            _product("g3", "Shop Two", mpn="FX-200"),
        ])
        self.assertEqual(parts, {"products": 2, "two_or_more_shops": 1, "not_joined_by_barcode": 1})

    def test_a_pair_a_barcode_already_joins_is_not_new(self) -> None:
        code = _ean13("501234500030")
        parts = self._parts([
            _product("h1", "Shop One", mpn="FX-300", ean=code),
            _product("h2", "Shop Two", mpn="FX-300", ean=code),
        ])
        self.assertEqual(parts, {"products": 1, "two_or_more_shops": 1, "not_joined_by_barcode": 0})

    def test_one_shop_with_a_barcode_and_one_without_are_joined_by_the_part_number_only(self) -> None:
        parts = self._parts([
            _product("i1", "Shop One", mpn="FX-400", ean=_ean13("501234500031")),
            _product("i2", "Shop Two", mpn="FX-400"),
        ])
        self.assertEqual(parts, {"products": 1, "two_or_more_shops": 1, "not_joined_by_barcode": 1})

    def test_another_brand_a_plain_word_or_one_shop_twice_never_joins(self) -> None:
        parts = self._parts([
            _product("j1", "Shop One", mpn="FX-500"),
            _product("j2", "Shop Two", mpn="FX-500", brand="Otheron"),
            _product("j3", "Shop One", mpn="Black"),
            _product("j4", "Shop Two", mpn="Black"),
            _product("j5", "Shop One", mpn="FX-600"),
            _product("j6", "Shop One", mpn="FX-600"),
            _product("j7", "Shop Two", mpn="FX-700", brand=""),
        ])
        self.assertEqual(parts, {"products": 3, "two_or_more_shops": 0, "not_joined_by_barcode": 0})


class ByShopTests(unittest.TestCase):
    """The mechanism's step 12: how each shop was taken in."""

    def test_per_shop_its_products_with_a_kind_a_barcode_and_another_shop_too(self) -> None:
        both, alone, twice = _ean13("501234500040"), _ean13("501234500041"), _ean13("501234500042")
        products = [
            _product("k1", "Shop Big", ean=both),
            _product("k2", "Shop Big", ean=alone),
            _product("k3", "Shop Big", ean=twice),
            _product("k4", "Shop Big", ean=twice),
            _product("k5", "Shop Big"),
            _product("k6", "Shop Small", ean=both),
            _product("k7", "Shop Small"),
            _product("k8", "Shop Bare"),
        ]
        kinds = [frozenset({"kettle"}), frozenset(), frozenset({"kettle"}), frozenset({"__uncertain_kind__"}),
                 frozenset(), frozenset({"toaster"}), frozenset(), frozenset()]
        note = measure_catalogue_balance(products, kinds)
        self.assertEqual(
            note["by_shop"],
            [
                {"shop": "Shop Big", "products": 5, "with_kind": 2, "with_barcode": 4, "another_shop_too": 1},
                {"shop": "Shop Small", "products": 2, "with_kind": 1, "with_barcode": 1, "another_shop_too": 1},
                {"shop": "Shop Bare", "products": 1, "with_kind": 0, "with_barcode": 0, "another_shop_too": 0},
            ],
        )
        # Every shop is listed, and the shops add up to the whole.
        self.assertEqual(sum(entry["products"] for entry in note["by_shop"]), note["products"])
        self.assertEqual(sum(entry["with_kind"] for entry in note["by_shop"]), note["products"] - note["no_kind"])
        text = json.dumps([note["by_shop"], note["shared_by_brand_and_part"]])
        self.assertNotIn(both, text)
        self.assertNotIn("http", text)


class SharedProductsReportTests(unittest.TestCase):
    _VIEW = {"groups": 1, "products": 1, "largest": [{"name": "x", "products": 1, "share": 1.0}], "over": 0,
             "cap": None, "kept": None, "cut": None, "cut_by_group": []}

    def _report(self, balance_extra: dict, shops: list | None = None) -> str:
        note = {
            "prepared": True,
            "intake": {"rows": 1, "shown": 1, "not_new": 0, "held": 0, "shops": shops or []},
            "balance": {
                "share": 0.15, "products": 1, "department": self._VIEW, "aisle": self._VIEW, "shop": self._VIEW,
                "kind": self._VIEW, "no_kind": 0,
                "kinds_by_shops": {"kinds": 0, "one_shop": 0, "two_shops": 0, "three_or_more": 0},
                "kinds_from_few_shops": [],
                **balance_extra,
            },
        }
        return subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "print_shops.py")],
            input=json.dumps(note), capture_output=True, text=True, check=True,
        ).stdout

    def test_the_report_prints_it_in_all_and_per_category(self) -> None:
        report = self._report({
            "shared_products": {
                "barcodes": 12345, "two_or_more_shops": 1234, "categories": 2,
                "by_category": [
                    {"category": "electronics > audio", "barcodes": 2000, "two_or_more_shops": 1000},
                    {"category": "home & garden > kitchen & dining", "barcodes": 10345, "two_or_more_shops": 234},
                ],
            },
        })
        self.assertIn(
            "  products two or more shops sell, by barcode: 1,234 of the 12,345 with a barcode; by category: "
            "electronics > audio 1,000 of 2,000; home & garden > kitchen & dining 234 of 10,345",
            report,
        )

    def test_a_note_written_before_it_prints_nothing_about_it(self) -> None:
        report = self._report({})
        self.assertNotIn("two or more shops sell", report)
        self.assertNotIn("how each shop was taken in", report)

    def test_the_report_prints_the_overlap_by_brand_and_part_number(self) -> None:
        report = self._report({
            "shared_by_brand_and_part": {"products": 54321, "two_or_more_shops": 2345, "not_joined_by_barcode": 1900},
        })
        self.assertIn(
            "  products two or more shops sell, by brand and part number: 2,345 of the 54,321 with both; "
            "1,900 of them no barcode joins",
            report,
        )

    def test_the_report_prints_how_each_shop_was_taken_in_beside_its_feed(self) -> None:
        feed = {"not_new": 0, "held": 0, "held_reasons": {}}
        report = self._report(
            {
                "by_shop": [
                    {"shop": "Shop Big", "products": 14869, "with_kind": 5000, "with_barcode": 12000,
                     "another_shop_too": 150},
                    {"shop": "Shop Unfed", "products": 3, "with_kind": 0, "with_barcode": 0, "another_shop_too": 0},
                ],
            },
            shops=[{"shop": "Shop Big", "rows": 1033769, "shown": 154853, **feed}],
        )
        lines = report.splitlines()
        start = lines.index(
            "how each shop was taken in (the site answers from 'kept'; the rest are counts of the kept):"
        )
        self.assertEqual(lines[start + 2].split(), ["1,033,769", "154,853", "14,869", "5,000", "12,000", "150",
                                                    "Shop", "Big"])
        # A shop the feed's list does not name is still printed, its feed unknown.
        self.assertEqual(lines[start + 3].split(), ["?", "?", "3", "0", "0", "0", "Shop", "Unfed"])


if __name__ == "__main__":
    unittest.main()
