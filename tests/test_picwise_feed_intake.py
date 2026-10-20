"""What each shop's feed brings in, measured for the deployment's public note.

`src/picwise_providers/feed_intake.py`. Owner, 2026-10-18: first many more shops,
"with whatever each one's feed sends". Shops differ in what they send, and the rules
that keep a product off the page apply to all alike, so the build says per shop how
many rows a search can show, how many only when asked for, and why the others are held
back. Pinned here: the counts per shop and in all, every reason counted, and that the
note carries them without anything of the feed's link.

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
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    measure_configured_feed_intake,
)

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "stock_status", "merchant_name",
    "condition",
)


def _row(pid: str, shop: str, *, category: str = "Kettles", image: bool = True, url: str = "",
         stock: str = "", condition: str = "", price: str = "20.00") -> list[str]:
    return [
        pid, f"Fixturon Electric Kettle {pid}", "Fixturon", category,
        url or f"https://fixture.example.invalid/out/{pid}",
        f"https://fixture.example.invalid/img/{pid}.jpg" if image else "",
        price, "GBP", "1", stock, shop, condition,
    ]


class FeedIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = Path(tempfile.mkdtemp())
        self.feed = folder / "feed.csv"
        rows = [
            _row("a1", "Fixture Store One"),
            _row("a2", "Fixture Store One"),
            _row("a3", "Fixture Store One", condition="Refurbished"),
            _row("a4", "Fixture Store One", stock="Out of stock"),
            _row("b1", "Fixture Store Two", category=""),
            _row("b2", "Fixture Store Two", category=""),
            _row("b3", "Fixture Store Two", image=False),
            _row("b4", "Fixture Store Two", url="not-a-link"),
            _row("b5", "Fixture Store Two", category="", image=False),
            _row("b6", "Fixture Store Two"),
        ]
        with self.feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            writer.writerows(rows)
        saved = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(self.feed)
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

    def test_each_shop_says_what_it_brings_and_why_the_rest_is_held(self) -> None:
        intake = measure_configured_feed_intake()
        one, two = intake["shops"][1], intake["shops"][0]
        self.assertEqual((two["shop"], one["shop"]), ("Fixture Store Two", "Fixture Store One"))
        self.assertEqual(
            {key: one[key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 4, "shown": 2, "not_new": 1, "held": 1},
        )
        # The reasons are the card gate's own codes, as it gives them.
        self.assertEqual(
            one["held_reasons"], {"availability_out_of_stock": 1, "purchasability_out_of_stock": 1}
        )
        self.assertEqual(
            {key: two[key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 6, "shown": 1, "not_new": 0, "held": 5},
        )
        # A shop that sends no category loses those rows at the feed gate; a row held
        # back for two reasons counts under both.
        self.assertEqual(
            two["held_reasons"],
            {"missing_category_text": 3, "missing_image_url": 2, "invalid_product_url": 1},
        )

    def test_the_totals_add_up(self) -> None:
        intake = measure_configured_feed_intake()
        self.assertEqual(
            {key: intake[key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 10, "shown": 3, "not_new": 1, "held": 6},
        )
        self.assertEqual(intake["shown"] + intake["not_new"] + intake["held"], intake["rows"])
        for shop in intake["shops"]:
            self.assertEqual(shop["shown"] + shop["not_new"] + shop["held"], shop["rows"])
        self.assertEqual(intake["held_reasons"]["missing_category_text"], 3)
        self.assertNotIn("fixture.example.invalid", repr(intake))

    def test_no_feed_no_intake(self) -> None:
        os.environ["AWIN_FEED_FILE"] = str(self.feed.parent / "no-such-feed.csv")
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        self.assertIsNone(measure_configured_feed_intake())


if __name__ == "__main__":
    unittest.main()
