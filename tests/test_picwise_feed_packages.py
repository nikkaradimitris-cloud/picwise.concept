"""The feed judged in packages gives the same catalogue and the same notes as the whole feed
(`picwise_providers.feed_packages`; owner, 2026-11-25: «Το αρχείο κατεβαίνει ολόκληρο και
αποθηκεύεται στο σκληρό δίσκο ... προώθηση άλλα 500.000 ...»; `docs/PICWISE_PACKAGES_PLAN.md`).

Pinned, on a feed of both links with what every cross-row rule reads (shops interleaved, rows
never shown, rows without a category that take their barcode's, availability that varies, a
second link whose shops and ids the first has, the checks' decisions with a shop out, cuts,
waits, the page's price and stock, the AI's categories with the category's cut or its brake,
a shop's own catalogue), prepared whole and in packages of a few rows: the same products in
the same order, the same kinds, fields, suggestions, choices, status and availability context;
the same notes of the shops' catalogues, the checks (and the gate's sets, the rows for the
bot) and the intake. And where the feed cannot be judged so, the whole feed is read.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers import ai_shelves, checks_applied, feed_packages, shop_catalogue, state  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.catalogue_memory import product_key  # noqa: E402
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.normalization import normalize_feed_row_to_provider_product  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_ENV = ("AWIN_FEED_FILE", "AWIN_FEED_URL", "AWIN_FEED_FILE_AWIN", "AWIN_FEED_URL_AWIN", "PICWISE_CHECKS_DECISIONS",
        "PICWISE_AI_SHELVES_FILE", "PICWISE_SHOP_CATALOGUES", feed_packages.PACKAGES_ENV)
_FIRST = ("aw_product_id", "product_name", "brand_name", "product_type", "merchant_category", "aw_deep_link",
          "aw_image_url", "search_price", "currency", "in_stock", "stock_status", "merchant_name", "merchant_id", "ean",
          "description")
_SECOND = ("aw_product_id", "product_name", "brand_name", "merchant_product_category_path", "aw_deep_link", "aw_image_url",
           "search_price", "currency", "in_stock", "merchant_name", "merchant_id", "merchant_deep_link", "description")
_SHOPS = (("Alpha Shop", "101"), ("Beta Shop", "102"), ("Gamma Shop", "103"), ("Delta Shop", "104"),
          ("Epsilon Shop", "105"))
_LINE = "Home & Garden > Kitchen & Dining > Kitchen Appliances"


def _fresh() -> None:
    clear_awin_feed_parse_cache()
    clear_provider_feed_pipeline_cache()
    state._CATALOGUE_CACHE.clear()
    ai_shelves.reset()
    checks_applied.reset_for_tests()


def _model(number: int) -> str:
    return "Model" + "".join(chr(ord("a") + (number // 26 ** place) % 26) for place in range(2))


def _first_rows() -> list[dict[str, str]]:
    rows = []
    for number in range(150):
        shop, shop_id = _SHOPS[number % len(_SHOPS)]
        pid = f"{shop.split()[0].lower()}-{number}"
        kettle = number % 2 == 0
        without_category = number % 7 == 3
        address = (f"https://beta-shop.example.invalid/products/item-{number}" if shop == "Beta Shop"
                   else f"https://fixture.example.invalid/out/{pid}")
        rows.append({
            "aw_product_id": pid,
            # A model's own word in each title: the AI is asked one question a title's words
            # (`picwise_ai.shelves.ask_key`, numbers and sizes left out).
            "product_name": f"Fixturon {'Electric Kettle' if kettle else 'Toaster'} {_model(number)} "
                            f"{'1.7L' if kettle else '2 Slice'}",
            "brand_name": "Fixturon",
            "product_type": "" if without_category else ("Kettles" if kettle else "Toasters"),
            "merchant_category": "" if without_category else "Kitchen Appliances",
            "aw_deep_link": address,
            "aw_image_url": "" if number % 11 == 5 else f"https://fixture.example.invalid/img/{pid}.jpg",
            "search_price": "" if number % 13 == 6 else f"{10 + number}.00",
            "currency": "GBP",
            "in_stock": "0" if number % 9 == 4 else "1",
            "stock_status": "out of stock" if number % 17 == 2 else "in stock",
            "merchant_name": shop,
            "merchant_id": shop_id,
            "ean": f"50{number % 10:011d}",
            "description": fixture_description(),
        })
    return rows


def _second_rows() -> list[dict[str, str]]:
    rows = []
    for number in range(36):
        shop, shop_id = ("Alpha Shop", "101") if number % 6 == 5 else ("Zeta Shop", "201")
        pid = "alpha-0" if number == 4 else f"zeta-{number}"
        rows.append({
            "aw_product_id": pid,
            "product_name": f"Zentrix Electric Kettle {number} 1.5L",
            "brand_name": "Zentrix",
            "merchant_product_category_path": "Home & Garden > Kitchen > Kettles",
            "aw_deep_link": f"https://www.awin1.invalid/pclick.php?p={number}",
            "aw_image_url": f"https://zeta.example.invalid/img/{number}.jpg",
            "search_price": f"{20 + number}.50",
            "currency": "GBP",
            "in_stock": "0" if number % 8 == 3 else "1",
            "merchant_name": shop,
            "merchant_id": shop_id,
            "merchant_deep_link": f"https://zeta-shop.example.invalid/p/{number}",
            "description": fixture_description(),
        })
    return rows


def _write_csv(path: Path, columns, rows, *, gzipped: bool = False, encoding: str = "utf-8") -> None:
    opener = (lambda: gzip.open(path, "wt", newline="", encoding=encoding)) if gzipped else \
        (lambda: path.open("w", newline="", encoding=encoding))
    with opener() as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _key(row: dict[str, str]) -> str:
    product = normalize_feed_row_to_provider_product(row, provider_key="awin")
    assert product is not None
    return product_key(product)


class FeedInPackagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        saved = {name: os.environ.get(name) for name in _ENV}

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            state._LAST_INTAKE = None
            state._LAST_PACKAGES = None
            _fresh()

        self.addCleanup(restore)
        for name in _ENV:
            os.environ.pop(name, None)
        self.first = _first_rows()
        self.second = _second_rows()
        self.first_path = self.folder / "first.csv"
        self.second_path = self.folder / "second.csv.gz"
        _write_csv(self.first_path, _FIRST, self.first)
        _write_csv(self.second_path, _SECOND, self.second, gzipped=True)
        os.environ["AWIN_FEED_FILE_AWIN"] = str(self.second_path)
        self.config = ProviderFeedConfig(provider_key="awin", feed_file=str(self.first_path))
        self.today = datetime.now(timezone.utc).date().isoformat()
        self.packages = self.folder / "packages"
        _fresh()

    # ---- the files the night reads beside the feed -------------------------------------

    def _decisions(self) -> None:
        by_pid = {row["aw_product_id"]: row for row in self.first}
        decisions = {
            "format": checks_applied.DECISIONS_FORMAT, "version": 1, "night": self.today,
            "shops_out": {"Delta Shop": "cannot be checked: refuses the bot"},
            "cut": {_key(by_pid["epsilon-4"]): "gone", _key(by_pid["gamma-7"]): "price far apart"},
            "wait": {_key(by_pid["beta-11"]): "never checked"},
            "enter": [], "returning": [], "passed": [],
            "prices": {_key(by_pid["alpha-10"]): ["9.50", self.today]},
            "stock": {_key(by_pid["epsilon-14"]): ["sold out", self.today]},
            "options": {},
        }
        path = self.folder / "decisions.json.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(decisions, handle)
        os.environ["PICWISE_CHECKS_DECISIONS"] = str(path)

    def _answers(self, *, none: int, line: int) -> None:
        """The AI's categories: `none` rows "no line fits", `line` rows a line; the rest unasked."""
        with_category = [row for row in self.first if row["product_type"] and row["merchant_name"] != "Delta Shop"]
        path = self.folder / "shelves.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for place, row in enumerate(with_category[: none + line]):
                product = normalize_feed_row_to_provider_product(row, provider_key="awin")
                key = ai_shelves.key_of(product.title, product.brand, product.raw)
                handle.write(json.dumps({"k": key, "line": "" if place < none else _LINE}) + "\n")
        os.environ["PICWISE_AI_SHELVES_FILE"] = str(path)

    def _catalogues(self) -> None:
        products = {}
        for row in self.first:
            if row["merchant_name"] != "Beta Shop":
                continue
            number = int(row["aw_product_id"].split("-")[1])
            products[f"item-{number}"] = ["Kettles" if number % 2 == 0 else "Toasters", 0 if number % 4 == 1 else 1,
                                          self.today, []]
        path = self.folder / "catalogues.json.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump({"version": 1, "written_at": self.today, "shops": {"Beta Shop": {"status": "read",
                                                                                       "products": products}}}, handle)
        os.environ["PICWISE_SHOP_CATALOGUES"] = str(path)

    # ---- the two ways ------------------------------------------------------------------

    def _prepare(self, *, packages: bool, rows: int = 23):
        _fresh()
        state._LAST_INTAKE = None
        with patch.object(feed_packages, "PACKAGE_ROWS", rows):
            prepared = state.prepare_feed_catalogue(self.config, measure_intake=True,
                                                    packages=self.packages if packages else None)
        return {
            "prepared": prepared,
            "intake": state.last_prepared_intake(),
            "catalogues": shop_catalogue.last_shop_catalogue_note(),
            "checks": checks_applied.last_checks_note(),
            "active": checks_applied._ACTIVE,
            "cut_rows": list(checks_applied._LAST_CUT),
            "packages": state.last_packages(),
        }

    def assertSame(self, whole: dict, packaged: dict) -> None:
        before, after = whole["prepared"], packaged["prepared"]
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        self.assertEqual([p.provider_product_id for p in after.products], [p.provider_product_id for p in before.products])
        self.assertEqual(after.products, before.products)
        self.assertEqual(after.kinds, before.kinds)
        self.assertEqual(after.non_new, before.non_new)
        self.assertEqual(after.search_fields, before.search_fields)
        self.assertEqual((after.eligible_count, after.shop_count), (before.eligible_count, before.shop_count))
        self.assertEqual(after.suggestions, before.suggestions)
        self.assertEqual(after.choices, before.choices)
        self.assertEqual(after.brands, before.brands)
        self.assertEqual(after.feed_status, before.feed_status)
        self.assertEqual(after.availability_context, before.availability_context)
        self.assertEqual(packaged["intake"], whole["intake"])
        self.assertEqual(packaged["catalogues"], whole["catalogues"])
        self.assertEqual(packaged["checks"], whole["checks"])
        self.assertEqual(packaged["active"], whole["active"])
        self.assertEqual(packaged["cut_rows"], whole["cut_rows"])
        self.assertIsNone(whole["packages"])
        self.assertTrue(packaged["packages"]["used"], packaged["packages"])
        self.assertGreater(packaged["packages"]["packages"], 1)

    def test_the_same_catalogue_and_notes_from_a_plain_night(self) -> None:
        self.assertSame(self._prepare(packages=False), self._prepare(packages=True))

    def test_the_same_with_the_checks_a_shops_catalogue_and_the_categorys_cut(self) -> None:
        self._decisions()
        self._catalogues()
        self._answers(none=2, line=40)
        whole = self._prepare(packages=False)
        self.assertEqual(whole["checks"]["category"]["no_category"], 2)
        self.assertFalse(whole["checks"]["category"]["held_by_its_brake"])
        self.assertTrue(whole["cut_rows"])
        self.assertTrue(whole["catalogues"]["sold_out"])
        self.assertTrue(whole["catalogues"]["barcode"]["joined"])
        self.assertSame(whole, self._prepare(packages=True))

    def test_the_same_with_the_categorys_brake_holding(self) -> None:
        self._decisions()
        self._answers(none=12, line=20)
        whole = self._prepare(packages=False)
        self.assertTrue(whole["checks"]["category"]["held_by_its_brake"])
        self.assertSame(whole, self._prepare(packages=True))

    def test_the_same_with_one_package_or_one_bucket_a_package(self) -> None:
        self._decisions()
        whole = self._prepare(packages=False)
        packaged = self._prepare(packages=True, rows=10_000)
        self.assertEqual(packaged["packages"]["packages"], 1)
        packaged["packages"]["packages"] = 2  # one package is still the same, only bigger
        self.assertSame(whole, packaged)
        self.assertSame(whole, self._prepare(packages=True, rows=1))

    def test_a_first_link_not_utf8_is_read_again_as_latin1_the_same(self) -> None:
        self.first[17]["description"] = fixture_description("Caf\xe9 grade steel.")
        _write_csv(self.first_path, _FIRST, self.first, encoding="latin-1")
        self.assertSame(self._prepare(packages=False), self._prepare(packages=True))

    def test_where_it_cannot_be_judged_so_the_whole_feed_is_read(self) -> None:
        missing = ProviderFeedConfig(provider_key="awin", feed_file=str(self.folder / "no-such-feed.csv"))
        _fresh()
        self.assertIsNone(state.prepare_feed_catalogue(missing, packages=self.packages))
        self.assertEqual(state.last_packages(), {"used": False, "why": "the first link cannot be read"})
        # A second link that breaks after some of its rows: the whole feed, as before.
        self.second[20]["description"] = "\xe9t\xe9"
        _write_csv(self.second_path, _SECOND, self.second, gzipped=True, encoding="latin-1")
        whole = self._prepare(packages=False)
        packaged = self._prepare(packages=True)
        self.assertEqual(packaged["packages"], {"used": False, "why": "the second link is not UTF-8"})
        self.assertEqual(packaged["prepared"].products, whole["prepared"].products)

    def test_the_packages_folder_is_left_empty(self) -> None:
        self._prepare(packages=True)
        self.assertEqual(list(self.packages.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
