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


def _product(pid: str, shop: str, *, ean: str = "", shelf: str = KITCHEN, column: str = "ean") -> ProviderProduct:
    raw = {"merchant_name": shop}
    if ean:
        raw[column] = ean
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon Item {pid}", brand="Fixturon",
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


class SharedProductsReportTests(unittest.TestCase):
    _VIEW = {"groups": 1, "products": 1, "largest": [{"name": "x", "products": 1, "share": 1.0}], "over": 0,
             "cap": None, "kept": None, "cut": None, "cut_by_group": []}

    def _report(self, balance_extra: dict) -> str:
        note = {
            "prepared": True,
            "intake": {"rows": 1, "shown": 1, "not_new": 0, "held": 0, "shops": []},
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
        self.assertNotIn("two or more shops sell", self._report({}))


if __name__ == "__main__":
    unittest.main()
