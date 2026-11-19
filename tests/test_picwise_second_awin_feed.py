"""The second Awin link, in Awin's own feed format, read beside the first (owner,
2026-11-19: «εφόσον το σετ μπορεί να υποστηρίξει την υποδομή της awin προχωράμε»). Pinned:
unset, nothing changes; set, its products come after the first link's; a shop in both is
read from the first alone, by Awin's advertiser id across the two formats; an id the first
uses is not taken twice; a second link that fails leaves the first as it is.
Every row is local test data: fictional shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers import awin_adapter  # noqa: E402
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402

GOOGLE = ["id", "title", "advertiser_id", "advertiser_name", "price", "link", "aw_deep_link", "image_link",
          "availability", "google_product_category", "brand"]
AWIN = ["aw_product_id", "product_name", "merchant_id", "merchant_name", "search_price", "currency",
        "merchant_deep_link", "aw_deep_link", "merchant_image_url", "in_stock", "merchant_category", "brand_name"]


def _write(path: Path, header: list[str], rows: list[list[str]]) -> str:
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(header)
    writer.writerows(rows)
    path.write_text(text.getvalue(), encoding="utf-8")
    return str(path)


def _google_row(ident: str, shop_id: str, shop: str) -> list[str]:
    return [ident, f"Fictional kettle {ident}", shop_id, shop, "19.99 GBP", f"https://shop{shop_id}.invalid/{ident}",
            f"https://awin.invalid/{ident}", f"https://img.invalid/{ident}.jpg", "in_stock",
            "Home & Garden > Kitchen & Dining > Kitchen Appliances", "Fictional"]


def _awin_row(ident: str, shop_id: str, shop: str) -> list[str]:
    return [ident, f"Fictional laptop {ident}", shop_id, shop, "499.00", "GBP", f"https://shop{shop_id}.invalid/{ident}",
            f"https://awin.invalid/{ident}", f"https://img.invalid/{ident}.jpg", "1", "Laptops", "Fictional"]


class SecondFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.first = _write(self.folder / "google.csv", GOOGLE, [_google_row("g1", "101", "Kitchen Shop"),
                                                                 _google_row("g2", "102", "Home Shop")])
        awin_adapter.clear_awin_feed_parse_cache()
        self.addCleanup(awin_adapter.clear_awin_feed_parse_cache)
        env = {k: v for k, v in os.environ.items() if not k.startswith("AWIN_FEED_")}
        patch = mock.patch.dict(os.environ, env, clear=True)
        patch.start()
        self.addCleanup(patch.stop)

    def load(self):
        return awin_adapter.load_awin_provider_feed(ProviderFeedConfig(provider_key="awin", feed_file=self.first))

    def test_unset_nothing_changes(self) -> None:
        result = self.load()
        self.assertEqual([p.provider_product_id for p in result.products], ["g1", "g2"])

    def test_set_its_new_shops_come_after_and_a_shop_in_both_is_read_once(self) -> None:
        second = _write(self.folder / "awin.csv", AWIN, [
            _awin_row("a1", "201", "Laptop Shop"),
            _awin_row("a2", "101", "Kitchen Shop"),   # in the first link already, by its id
            _awin_row("g1", "202", "Other Shop"),     # an id the first link uses
            _awin_row("a3", "201", "Laptop Shop"),
        ])
        os.environ["AWIN_FEED_FILE_AWIN"] = second
        result = self.load()
        self.assertEqual(result.status, "provider_feed_loaded")
        self.assertEqual([p.provider_product_id for p in result.products], ["g1", "g2", "a1", "a3"])
        self.assertIn("second_feed_loaded", result.reason_codes)

    def test_a_second_link_that_fails_leaves_the_first(self) -> None:
        os.environ["AWIN_FEED_FILE_AWIN"] = str(self.folder / "missing.csv")
        result = self.load()
        self.assertEqual([p.provider_product_id for p in result.products], ["g1", "g2"])


if __name__ == "__main__":
    unittest.main()


class AisleTests(unittest.TestCase):
    def test_awin_names_find_their_aisle_and_phrases_hold_whole(self) -> None:
        from picwise_providers.awin_categories import aisle_for, row_aisle

        self.assertEqual(aisle_for("Laptops"), "Electronics > Computers")
        self.assertEqual(aisle_for("Laptop Bags"), "Electronics > Electronics Accessories")
        self.assertEqual(aisle_for("Handbags"), "Apparel & Accessories > Handbags, Wallets & Cases")
        self.assertEqual(aisle_for("Tyres"), "Vehicles & Parts > Vehicle Parts & Accessories")
        self.assertEqual(aisle_for("Power Tools"), "Hardware > Tools")
        self.assertEqual(aisle_for("Experiences"), "")
        # The most specific column first; a Google shelf left as it is.
        self.assertEqual(row_aisle({"merchant_product_category_path": "Monitors > 27 inch", "category_name": "Computers"}),
                         "Electronics > Video")
        self.assertEqual(row_aisle({"google_product_category": "Media > Books", "category_name": "Laptops"}), "")

    def test_the_second_link_s_rows_carry_their_aisle(self) -> None:
        folder = Path(tempfile.mkdtemp())
        first = _write(folder / "google.csv", GOOGLE, [_google_row("g1", "101", "Kitchen Shop")])
        second = _write(folder / "awin.csv", AWIN, [_awin_row("a1", "201", "Laptop Shop")])
        awin_adapter.clear_awin_feed_parse_cache()
        with mock.patch.dict(os.environ, {"AWIN_FEED_FILE_AWIN": second}):
            result = awin_adapter.load_awin_provider_feed(ProviderFeedConfig(provider_key="awin", feed_file=first))
        awin_adapter.clear_awin_feed_parse_cache()
        by_id = {p.provider_product_id: p for p in result.products}
        self.assertEqual(by_id["a1"].category_text, "Electronics > Computers > Laptops")
        self.assertEqual(by_id["g1"].category_text, "Home & Garden > Kitchen & Dining > Kitchen Appliances")


class SecondRowKeepTests(unittest.TestCase):
    def test_rows_that_can_never_show_are_not_read(self) -> None:
        folder = Path(tempfile.mkdtemp())
        first = _write(folder / "google.csv", GOOGLE, [_google_row("g1", "101", "Kitchen Shop")])
        rows = [_awin_row(f"a{i}", "201", "Laptop Shop") for i in range(6)]
        rows[1][5] = "EUR"            # another currency
        rows[2][4] = "0"              # no price
        rows[3][9] = "0"              # out of stock
        rows[4][10] = ""              # no category words
        rows[5][2] = "101"            # a shop the first link has
        second = _write(folder / "awin.csv", AWIN, rows)
        awin_adapter.clear_awin_feed_parse_cache()
        with mock.patch.dict(os.environ, {"AWIN_FEED_FILE_AWIN": second}):
            result = awin_adapter.load_awin_provider_feed(ProviderFeedConfig(provider_key="awin", feed_file=first))
        awin_adapter.clear_awin_feed_parse_cache()
        self.assertEqual([p.provider_product_id for p in result.products], ["g1", "a0"])
