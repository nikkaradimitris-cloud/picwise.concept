"""The night's note says which shops' feeds shrank, and which kinds few shops sell (the
audit, 2026-11-10; owner, the same day: «Ζητώ διόρθωση και βελτίωση ... το μηχανισμό», and
«Θα προσθέσουμε καταστήματα ... στις κατηγορίες που λείπουν»).

The audit found one shop holding 61% of the site's products and nothing telling when a
shop's feed came short or empty: the catalogue is built from the night's feed alone, so
the site would simply be that much smaller in the morning. And of 265 kinds, 99 came from
one shop and 76 from two, with no list of which. Pinned here:

- the preparation compares each shop's rows with the note of the preparation before
  (`tools/prepare_catalogue.py`, `_intake_change`): fewer than half is "shrunk", none is
  "gone", a shop it did not have is "new"; a small shop's ups and downs are not named;
- it says so in its output, where the server's journal and a deployment's run show it,
  and the server's report prints it (`deployment/server/print_shops.py`);
- with no note before, or one that prepared nothing, it compares with nothing;
- measured and said only: the catalogue is still tonight's feed;
- the note names the kinds only one or two shops sell, the largest first, with the
  shops' names (`catalogue_balance.measure_catalogue_balance`), and the report prints the
  largest of them.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.catalogue_balance import measure_catalogue_balance  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "description",
)


def _load_tool():
    spec = importlib.util.spec_from_file_location("prepare_catalogue_shrink_tool", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _note(shops: dict[str, int], *, prepared: bool = True, at: str = "2026-11-09T04:24:00+00:00") -> dict:
    return {
        "prepared": prepared,
        "prepared_at": at,
        "intake": {"rows": sum(shops.values()), "shops": [{"shop": name, "rows": rows} for name, rows in shops.items()]},
    }


class IntakeChangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = _load_tool()

    def _change(self, before: dict | None, now: dict[str, int]) -> dict:
        return self.tool._intake_change(before, _note(now)["intake"])

    def test_a_feed_with_fewer_than_half_its_rows_is_named(self) -> None:
        change = self._change(
            _note({"Big Shop": 1000, "Steady Shop": 400, "Lost Shop": 300, "Halved Shop": 200}),
            {"Big Shop": 120, "Steady Shop": 390, "Halved Shop": 100, "New Shop": 50},
        )
        self.assertEqual(change["compared_with"], "2026-11-09T04:24:00+00:00")
        self.assertEqual(change["shrunk"], [{"shop": "Big Shop", "rows_before": 1000, "rows": 120}])
        self.assertEqual(change["gone"], [{"shop": "Lost Shop", "rows_before": 300, "rows": 0}])
        self.assertEqual(change["new"], ["New Shop"])
        # Exactly half is not fewer than half; a little fewer is a shop's ordinary night.
        self.assertNotIn("Halved Shop", json.dumps(change["shrunk"]))
        self.assertNotIn("Steady Shop", json.dumps(change))

    def test_the_largest_first_and_a_small_shop_not_named(self) -> None:
        change = self._change(
            _note({"A": 60, "B": 5000, "C": 49, "D": 700}), {"A": 10, "B": 100, "C": 1, "D": 0}
        )
        self.assertEqual([entry["shop"] for entry in change["shrunk"]], ["B", "A"])
        self.assertEqual([entry["shop"] for entry in change["gone"]], ["D"])
        # 49 rows the night before: under what is called a shop's feed here.
        self.assertNotIn("C", [entry["shop"] for entry in change["shrunk"] + change["gone"]])
        self.assertEqual(self.tool.SHRUNK_FROM_ROWS, 50)
        self.assertEqual(self.tool.SHRUNK_SHARE, 0.5)

    def test_with_nothing_to_compare_with_nothing_is_compared(self) -> None:
        now = {"Big Shop": 10}
        self.assertEqual(self._change(None, now), {"compared_with": None})
        self.assertEqual(self._change(_note({"Big Shop": 1000}, prepared=False), now), {"compared_with": None})
        self.assertEqual(self._change({"prepared": True, "intake": {"error": "x"}}, now), {"compared_with": None})
        self.assertEqual(self.tool._intake_change(_note({"Big Shop": 1000}), {"error": "x"}), {"compared_with": None})

    def test_every_feed_as_large_as_before_names_no_shop(self) -> None:
        change = self._change(_note({"A": 100, "B": 200}), {"A": 100, "B": 260})
        self.assertEqual((change["shrunk"], change["gone"], change["new"]), ([], [], []))


class TheToolSaysSoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.static = self.folder / "public"
        saved = {name: os.environ.get(name) for name in ("AWIN_FEED_FILE", "AWIN_FEED_URL")}

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def _feed(self, name: str, shops: dict[str, int]) -> Path:
        path = self.folder / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for shop, rows in shops.items():
                for number in range(rows):
                    pid = f"{shop.split()[0].lower()}-{number}"
                    writer.writerow([
                        pid, f"Fixturon Electric Kettle {number} 1.7L", "Fixturon", "Kettles", "Kitchen Appliances",
                        f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                        f"{10 + number % 40}.00", "GBP", "1", shop, fixture_description(),
                    ])
        return path

    def _prepare(self, feed: Path) -> tuple[str, dict]:
        tool = _load_tool()
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        printed = io.StringIO()
        with redirect_stdout(printed):
            code = tool.main([
                "--feed-file", str(feed), "--out", str(self.folder / "catalogue.json.gz"),
                "--static-dir", str(self.static),
            ])
        self.assertEqual(code, 0, printed.getvalue())
        return printed.getvalue(), json.loads((self.static / "prepared.json").read_text(encoding="utf-8"))

    def test_the_preparation_names_the_shops_whose_feed_shrank_and_goes_on(self) -> None:
        said, first = self._prepare(self._feed("first.csv", {"Alpha Shop": 80, "Beta Shop": 60, "Gamma Shop": 55}))
        self.assertEqual(first["intake_change"], {"compared_with": None})
        self.assertNotIn("fewer than half", said)

        said, second = self._prepare(self._feed("second.csv", {"Alpha Shop": 12, "Beta Shop": 61, "Delta Shop": 5}))
        change = second["intake_change"]
        self.assertEqual(change["compared_with"], first["prepared_at"])
        self.assertEqual(change["shrunk"], [{"shop": "Alpha Shop", "rows_before": 80, "rows": 12}])
        self.assertEqual(change["gone"], [{"shop": "Gamma Shop", "rows_before": 55, "rows": 0}])
        self.assertEqual(change["new"], ["Delta Shop"])
        self.assertIn(
            "prepare_catalogue: fewer than half of the night before's rows from Gamma Shop (55 -> 0); "
            "Alpha Shop (80 -> 12)",
            said,
        )
        # Measured and said only: the catalogue is tonight's feed.
        self.assertEqual(second["products"], 12 + 61 + 5)
        # Names and counts, never an address.
        self.assertNotIn("fixture.example.invalid", json.dumps(change))

        report = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "print_shops.py")],
            input=json.dumps(second), capture_output=True, text=True, check=True,
        ).stdout
        self.assertIn(f"since the preparation of {first['prepared_at']}:", report)
        self.assertIn("  no rows now: Gamma Shop (55 -> 0)", report)
        self.assertIn("  fewer than half the rows: Alpha Shop (80 -> 12)", report)
        self.assertIn("  new shops: Delta Shop", report)

        said, third = self._prepare(self._feed("third.csv", {"Alpha Shop": 12, "Beta Shop": 70, "Delta Shop": 5}))
        self.assertEqual(
            (third["intake_change"]["shrunk"], third["intake_change"]["gone"], third["intake_change"]["new"]),
            ([], [], []),
        )
        self.assertNotIn("fewer than half", said)
        report = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "print_shops.py")],
            input=json.dumps(third), capture_output=True, text=True, check=True,
        ).stdout
        self.assertIn("  every shop's feed came as large as before or larger; no new shop", report)


def _product(pid: str, shop: str, category: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon {pid}", brand="Fixturon",
        category_text=category, product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg", price_text="10.00",
        availability_text="in stock", currency="GBP", raw={"merchant_name": shop},
    )


class KindsFromFewShopsTests(unittest.TestCase):
    def test_the_kinds_one_or_two_shops_sell_with_the_shops_names(self) -> None:
        kitchen = "Home & Garden > Kitchen & Dining"
        products = (
            [_product(f"k{n}", f"Kettle Shop {n % 3}", kitchen) for n in range(9)]      # three shops
            + [_product(f"t{n}", f"Toaster Shop {n % 2}", kitchen) for n in range(6)]  # two shops
            + [_product(f"b{n}", "Blender Shop", kitchen) for n in range(8)]           # one shop
            + [_product(f"m{n}", "Mixer Shop", kitchen) for n in range(2)]             # one shop
            + [_product("x1", "Other Shop", kitchen)]                                  # no kind
        )
        kinds = (
            [frozenset({"kettle"})] * 9 + [frozenset({"toaster"})] * 6 + [frozenset({"blender"})] * 8
            + [frozenset({"mixer"})] * 2 + [frozenset()]
        )
        note = measure_catalogue_balance(products, kinds)
        self.assertEqual(note["kinds_by_shops"], {"kinds": 4, "one_shop": 2, "two_shops": 1, "three_or_more": 1})
        # The largest first; a kind three shops sell is not among them; nor a product with no kind.
        self.assertEqual(
            note["kinds_from_few_shops"],
            [
                {"kind": "blender", "products": 8, "shops": ["Blender Shop"]},
                {"kind": "toaster", "products": 6, "shops": ["Toaster Shop 0", "Toaster Shop 1"]},
                {"kind": "mixer", "products": 2, "shops": ["Mixer Shop"]},
            ],
        )

    def test_the_report_prints_the_largest_of_them(self) -> None:
        view = {"groups": 1, "products": 1, "largest": [{"name": "x", "products": 1, "share": 1.0}], "over": 0,
                "cap": None, "kept": None, "cut": None, "cut_by_group": []}
        note = {
            "prepared": True,
            "intake": {"rows": 1, "shown": 1, "not_new": 0, "held": 0, "shops": []},
            "balance": {
                "share": 0.15, "products": 1, "department": view, "aisle": view, "shop": view, "kind": view,
                "no_kind": 0, "kinds_by_shops": {"kinds": 2, "one_shop": 1, "two_shops": 1, "three_or_more": 0},
                "kinds_from_few_shops": [
                    {"kind": "blender", "products": 1234, "shops": ["Blender Shop"]},
                    {"kind": "toaster", "products": 6, "shops": ["Toaster Shop 0", "Toaster Shop 1"]},
                ],
            },
        }
        report = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "print_shops.py")],
            input=json.dumps(note), capture_output=True, text=True, check=True,
        ).stdout
        self.assertIn(
            "  the largest kinds from one or two shops: blender 1,234 (Blender Shop); "
            "toaster 6 (Toaster Shop 0, Toaster Shop 1)",
            report,
        )


if __name__ == "__main__":
    unittest.main()
