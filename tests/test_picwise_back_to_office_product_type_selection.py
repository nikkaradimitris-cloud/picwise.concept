from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.normalization import normalize_feed_row_to_provider_product  # noqa: E402
from picwise_providers.state import (  # noqa: E402
    load_eligible_provider_feed_products,
    resolve_search_provider_feed_product_selection,
)

_BTO_FEED_ENV = "AWIN_FEED_FILE"
_BTO_FEED_DEFAULT = Path(
    r"C:\Users\User\Desktop\picwise-private-feeds\back_to_office_clean_full_columns.csv.gz"
)

_BLOCKED_LAPTOP_TYPES = (
    "Laptop Stands",
    "Straps",
    "Laptop Cases",
    "Power Adapters & Inverters",
    "Mobile Device Chargers",
)
_BLOCKED_MOUSE_TYPES = ("Mouse Pads", "Wrist Rests")
_BLOCKED_HEADPHONE_TYPES = ("Mobile Device Chargers",)
_BLOCKED_MONITOR_TYPES = ("Display Privacy Filters",)
_BLOCKED_CHAIR_TYPES = (
    "Chair Back Supports",
    "Video Game Chairs",
    "Seat Cushions",
    "Backrests",
)


def _bto_feed_path() -> Path:
    return Path(os.environ.get(_BTO_FEED_ENV, str(_BTO_FEED_DEFAULT)))


def _bto_feed_config() -> ProviderFeedConfig:
    return ProviderFeedConfig(provider_key="awin", feed_file=str(_bto_feed_path()))


def _product_types(products: tuple) -> tuple[str, ...]:
    types: list[str] = []
    for product in products:
        raw = product.raw if isinstance(product.raw, dict) else {}
        types.append(str(raw.get("product_type") or "").strip())
    return tuple(types)


class BackToOfficeProductTypeSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_feed_file = os.environ.get(_BTO_FEED_ENV)
        feed_path = _bto_feed_path()
        if feed_path.is_file():
            os.environ[_BTO_FEED_ENV] = str(feed_path)

    def tearDown(self) -> None:
        if self._saved_feed_file is None:
            os.environ.pop(_BTO_FEED_ENV, None)
        else:
            os.environ[_BTO_FEED_ENV] = self._saved_feed_file

    def _require_bto_feed(self) -> ProviderFeedConfig:
        feed_path = _bto_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"Back to the Office feed not present at {feed_path}")
        return _bto_feed_config()

    def _assert_selected_types(
        self,
        query: str,
        *,
        allowed_types: tuple[str, ...],
        blocked_types: tuple[str, ...] = (),
        min_count: int = 4,
    ) -> None:
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query=query,
            feed_config=config,
        )
        self.assertEqual(selection.status, "selected")
        self.assertGreaterEqual(len(selection.selected_products), min_count)
        types = _product_types(selection.selected_products)
        for product_type in types:
            self.assertIn(product_type, allowed_types)
            self.assertNotIn(product_type, blocked_types)

    def test_laptop_prefers_actual_laptops(self) -> None:
        self._assert_selected_types(
            "laptop",
            allowed_types=("Laptops",),
            blocked_types=_BLOCKED_LAPTOP_TYPES,
        )

    def test_dell_laptop_prefers_dell_laptops(self) -> None:
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="dell laptop",
            feed_config=config,
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual(len(selection.selected_products), 4)
        for product in selection.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Laptops")
            brand_blob = f"{product.brand} {product.title}".lower()
            self.assertIn("dell", brand_blob)

    def test_monitor_queries_prefer_computer_monitors(self) -> None:
        for query in ("monitor", "27 inch monitor", "computer monitor"):
            with self.subTest(query=query):
                self._assert_selected_types(
                    query,
                    allowed_types=("Computer Monitors", "Not Categorized"),
                    blocked_types=_BLOCKED_MONITOR_TYPES,
                )

    def test_mouse_prefers_mice_not_pads(self) -> None:
        self._assert_selected_types(
            "mouse",
            allowed_types=("Mice",),
            blocked_types=_BLOCKED_MOUSE_TYPES,
        )

    def test_headphones_prefers_headsets_not_chargers(self) -> None:
        self._assert_selected_types(
            "headphones",
            allowed_types=("Headphones & Headsets",),
            blocked_types=_BLOCKED_HEADPHONE_TYPES,
        )

    def test_webcam_and_logitech_webcam(self) -> None:
        self._assert_selected_types("webcam", allowed_types=("Webcams",))
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="logitech webcam",
            feed_config=config,
        )
        self.assertEqual(selection.status, "selected")
        for product in selection.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Webcams")
            brand_blob = f"{product.brand} {product.title}".lower()
            self.assertIn("logitech", brand_blob)

    def test_keyboard_queries(self) -> None:
        self._assert_selected_types("wireless keyboard", allowed_types=("Keyboards",))
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="logitech keyboard",
            feed_config=config,
        )
        self.assertEqual(selection.status, "selected")
        for product in selection.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Keyboards")
            brand_blob = f"{product.brand} {product.title}".lower()
            self.assertIn("logitech", brand_blob)

    def test_docking_station_prefers_docks(self) -> None:
        self._assert_selected_types(
            "docking station",
            allowed_types=("Laptop Docks & Port Replicators",),
        )

    def test_toner_and_ink_cartridge_queries(self) -> None:
        self._assert_selected_types(
            "toner cartridge",
            allowed_types=("Toner Cartridges",),
        )
        config = self._require_bto_feed()
        hp_toner = resolve_search_provider_feed_product_selection(
            query="hp toner",
            feed_config=config,
        )
        self.assertEqual(hp_toner.status, "selected")
        for product in hp_toner.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Toner Cartridges")
        self._assert_selected_types(
            "ink cartridge",
            allowed_types=("Ink Cartridges",),
        )

    def test_office_chair_does_not_fake_chairs_when_feed_lacks_real_office_chairs(self) -> None:
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="office chair",
            feed_config=config,
        )
        self.assertEqual(selection.status, "insufficient_relevant_products")
        self.assertEqual(len(selection.selected_products), 0)
        self.assertLess(selection.matched_count, 4)

    def test_brand_name_maps_from_official_feed_field(self) -> None:
        config = self._require_bto_feed()
        products = load_eligible_provider_feed_products(feed_config=config)
        branded = [product for product in products if str(product.brand or "").strip()]
        self.assertGreater(len(branded), 100)
        sample = branded[0]
        raw = sample.raw if isinstance(sample.raw, dict) else {}
        self.assertEqual(str(raw.get("brand_name") or "").strip(), sample.brand)

    def test_brand_name_not_inferred_from_title_only_rows(self) -> None:
        product = normalize_feed_row_to_provider_product(
            {
                "product_name": "Logitech MX Keys Keyboard",
                "product_type": "Keyboards",
                "category_name": "Computers",
                "aw_deep_link": "https://merchant.example/products/logi-kb",
            },
            provider_key="awin",
        )
        assert product is not None
        self.assertEqual(product.brand, "")


if __name__ == "__main__":
    unittest.main()
