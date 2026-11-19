"""`.github/scripts/measure_awin_feed.py`, run by `.github/workflows/awin-feed-measure.yml`
(owner, 2026-11-19: the Awin-format feeds come back, in a second link). Pinned here: the
rows in pounds, priced, with a category and in stock are counted and so are the rows that
have all four; each shop is listed; the shops already in the feed in use are named by
their advertiser id; a link that cannot be read is reported by its kind only, never
printed. Every row is local test data: fictional shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import gzip
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "measure_awin_feed.py"
AWIN = ["aw_product_id", "product_name", "merchant_id", "merchant_name", "search_price", "currency",
        "merchant_category", "in_stock", "ean", "aw_deep_link"]


def _awin(path: Path, rows: list[list[str]]) -> str:
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(AWIN)
    writer.writerows(rows)
    path.write_bytes(gzip.compress(text.getvalue().encode("utf-8")))
    return path.resolve().as_uri()


def _google(path: Path, ids: list[str]) -> str:
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(["id", "title", "advertiser_id", "advertiser_name", "price"])
    for number, ident in enumerate(ids):
        writer.writerow([f"g{number}", "Fictional", ident, f"Shop {ident}", "9.99 GBP"])
    path.write_text(text.getvalue(), encoding="utf-8")
    return path.resolve().as_uri()


def _run(env_extra: dict[str, str]) -> subprocess.CompletedProcess:
    env = {name: value for name, value in os.environ.items() if not name.startswith("AWIN_FEED_URL")}
    env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, check=False)


class MeasureAwinFeedTests(unittest.TestCase):
    def test_the_rows_that_could_show_and_the_shops_already_in_use(self) -> None:
        rows = [
            ["1", "Kettle", "201", "Fictional Kitchen", "19.99", "GBP", "Kettles", "1", "5012345678900", "https://example.invalid/1"],
            ["2", "Toaster", "201", "Fictional Kitchen", "24.99", "GBP", "", "1", "", "https://example.invalid/2"],
            ["3", "Ball", "202", "Fictional Sports", "9.99", "EUR", "Balls", "1", "", "https://example.invalid/3"],
            ["4", "Bat", "202", "Fictional Sports", "0", "GBP", "Bats", "1", "", "https://example.invalid/4"],
            ["5", "Doll", "203", "Fictional Toys", "12.00", "GBP", "Dolls", "0", "", "https://example.invalid/5"],
            ["6", "Car", "203", "Fictional Toys", "15.00", "GBP", "Cars", "", "", "https://example.invalid/6"],
        ]
        with tempfile.TemporaryDirectory() as folder:
            done = _run({
                "AWIN_FEED_URL_AWIN": _awin(Path(folder) / "awin.csv.gz", rows),
                "AWIN_FEED_URL": _google(Path(folder) / "google.csv", ["201", "999"]),
            })
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        out = done.stdout
        self.assertIn("the Awin-format feed: 3 shops, 6 rows", out)
        self.assertIn("rows priced in pounds: 5 (83.3%)", out)
        self.assertIn("rows with a category: 5 (83.3%)", out)
        self.assertIn("rows PicWise could show (pounds, a price, a category, in stock): 2 (33.3%)", out)
        self.assertIn("currencies: GBP 5, EUR 1", out)
        self.assertIn("shops already in the feed in use: 1", out)
        self.assertIn("2  Fictional Kitchen (201)", out)
        self.assertIn("        2          1  Fictional Toys (203)", out)
        self.assertNotIn("example.invalid", out)
        self.assertNotIn(folder, out)

    def test_a_link_that_cannot_be_read_is_not_printed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            missing = (Path(folder) / "none.csv").resolve().as_uri()
            done = _run({"AWIN_FEED_URL_AWIN": missing})
        self.assertEqual(done.returncode, 1)
        self.assertIn("the Awin-format feed could not be read:", done.stdout)
        self.assertNotIn(folder, done.stdout)

    def test_without_the_link_nothing_is_measured(self) -> None:
        done = _run({})
        self.assertEqual(done.returncode, 1)
        self.assertIn("no Awin-format feed link (AWIN_FEED_URL_AWIN)", done.stdout)


if __name__ == "__main__":
    unittest.main()
