"""The look before the rule of a cap per shop is written (`deployment/server/look_shop_cap.py`;
owner, 2026-11-22: each shop keeps at most what the bot can check in a day, never over 20,000;
kept first what it sells cheapest of all, then the kinds with the fewest products, then a
share of each kind over its prices).

Pinned here, on a prepared catalogue of the test's own: a shop's cap is 20,000 or a day of the
bot at its measured pace; a shop over its cap keeps its cap and no more, by the three steps in
their order; a shop under it keeps everything; what is said holds counts and names only.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import look_itself  # noqa: E402
import look_shop_cap  # noqa: E402
from test_picwise_look_itself import _write  # noqa: E402


class TheCapOfAShop(unittest.TestCase):
    def test_twenty_thousand_or_a_day_of_the_bot_at_its_pace(self) -> None:
        self.assertEqual(look_shop_cap.DAY_SECONDS, 77700)
        self.assertEqual(look_shop_cap.cap_of("A Shop Never Measured"), 20000)
        self.assertEqual(look_shop_cap.cap_of("InStock UK"), 20000)
        self.assertEqual(look_shop_cap.cap_of("Tooled Up"), 18951)
        self.assertEqual(look_shop_cap.cap_of("GamingKit"), 18069)
        self.assertEqual(look_shop_cap.cap_of("PCHUB.UK"), 12140)
        self.assertEqual(look_shop_cap.cap_of("Tirendo UK"), 7770)
        self.assertEqual(look_shop_cap.cap_of("Tirendo UK", 5000), 5000)


class OnACatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        _write(Path(cls.folder.name) / "catalogue.json.gz")
        cls.prepared = look_itself._load(Path(cls.folder.name) / "catalogue.json.gz", gone="", offers="", families="")

    @classmethod
    def tearDownClass(cls) -> None:
        from picwise_providers import state

        state._PREPARED_STATE.clear()
        state.remember_product_kinds({})
        cls.folder.cleanup()

    def test_a_shop_under_its_cap_keeps_everything(self) -> None:
        numbers = look_shop_cap.measure(self.prepared)
        self.assertEqual((numbers["kept"], numbers["cut"]), (numbers["products"], 0))
        self.assertEqual(sum(row["products"] for row in numbers["rows"]), numbers["products"])
        self.assertTrue(all("kept_by_step" not in row for row in numbers["rows"]))

    def test_a_shop_over_its_cap_keeps_its_cap_by_the_three_steps(self) -> None:
        numbers = look_shop_cap.measure(self.prepared, cap=5, thin=6)
        over = [row for row in numbers["rows"] if row["over"]]
        self.assertTrue(over)
        for row in over:
            self.assertEqual(sum(row["kept_by_step"]), 5)
            self.assertEqual(row["over"], row["products"] - 5)
        self.assertEqual(numbers["cut"], sum(row["over"] for row in over))
        self.assertEqual(numbers["kept"] + numbers["cut"], numbers["products"])
        # The kinds are counted before and after, and none gains a product.
        for entry in numbers["lost_most"]:
            self.assertLessEqual(entry["after"], entry["before"])

    def test_what_is_said_holds_counts_and_names_only(self) -> None:
        numbers = look_shop_cap.measure(self.prepared, cap=5, thin=6)
        text = "\n".join(look_shop_cap.report(numbers, look_shop_cap.ties(self.prepared), 6))
        self.assertIn("a cap per shop would keep", text)
        self.assertIn("shops over their cap:", text)
        for word in ("http", ".invalid", "row-"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
