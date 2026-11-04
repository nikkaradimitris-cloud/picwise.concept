"""A shop the owner left out shows nothing, and the note says why.

`src/picwise_providers/eligibility.py` (`LEFT_OUT_SHOPS`). Owner, 2026-10-26: «Θα κάνεις
το 2 και το 3», the third being "So Divine out": it sells adult products, the server
showed 72 of its 81 rows, and the site has no rule for them. Pinned here: every row of
the shop is held at the feed gate whatever its name's spaces and case, with its own
reason in the per-shop note; another shop's rows are judged as before.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.eligibility import evaluate_provider_product_eligibility  # noqa: E402
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    load_eligible_provider_feed_products,
    measure_configured_feed_intake,
)

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
)


def _row(pid: str, shop: str) -> list[str]:
    return [
        pid, f"Fixturon Electric Kettle {pid}", "Fixturon", "Kettles",
        f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
        "20.00", "GBP", "1", shop,
    ]


def _product(shop: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id="p1", title="Fixturon Electric Kettle",
        brand="Fixturon", category_text="Kettles", product_url="https://fixture.example.invalid/out/p1",
        image_url="https://fixture.example.invalid/img/p1.jpg", price_text="20.00",
        availability_text="in stock", currency="GBP", raw={"merchant_name": shop},
    )


class LeftOutShopTests(unittest.TestCase):
    def test_the_feed_gate_holds_every_row_of_a_left_out_shop(self) -> None:
        for shop in ("So Divine", "so divine", "  So   DIVINE "):
            with self.subTest(shop=shop):
                result = evaluate_provider_product_eligibility(_product(shop))
                self.assertEqual(result.status, "blocked")
                self.assertIn("shop_left_out", result.reason_codes)

    def test_another_shop_is_judged_as_before(self) -> None:
        for shop in ("So Divine Candles", "Divine", "Fixture Kitchen Shop"):
            with self.subTest(shop=shop):
                result = evaluate_provider_product_eligibility(_product(shop))
                self.assertEqual(result.status, "eligible")
                self.assertNotIn("shop_left_out", result.reason_codes)

    def test_the_note_names_the_reason_and_no_product_of_it_is_shown(self) -> None:
        feed = Path(tempfile.mkdtemp()) / "feed.csv"
        with feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            writer.writerows([_row("a1", "So Divine"), _row("a2", "So Divine"), _row("b1", "Fixture Kitchen Shop")])
        saved = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(feed)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if saved is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = saved
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

        shown = load_eligible_provider_feed_products()
        self.assertEqual([product.provider_product_id for product in shown], ["b1"])
        note = measure_configured_feed_intake()
        shops = {shop["shop"]: shop for shop in note["shops"]}
        self.assertEqual(shops["So Divine"]["shown"], 0)
        self.assertEqual(shops["So Divine"]["held"], 2)
        self.assertEqual(shops["So Divine"]["held_reasons"], {"shop_left_out": 2})
        self.assertEqual(note["held_reasons"].get("shop_left_out"), 2)
        self.assertEqual(shops["Fixture Kitchen Shop"]["shown"], 1)


if __name__ == "__main__":
    unittest.main()
