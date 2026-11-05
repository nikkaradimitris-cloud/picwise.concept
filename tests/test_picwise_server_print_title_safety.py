"""Which kinds a title alone reads right at least 99% of the time, and what they would
bring in of the rows held for want of a category, printed.

`deployment/server/print_title_safety.py`, run by `.github/workflows/server-cap.yml` on
a copy of the feed the server prepared from (owner, 2026-10-31: «Ναι, κάνε τη μέτρηση»;
"safe" as a number, put to them on 26/10). Pinned here: a kind the title reads right on
every row with a shelf, with enough rows to tell by, brings in the held rows of its kind;
one read wrong too often, or with too few rows to tell by, brings in none; a row held
for something else besides counts nowhere; the kinds from 3 shops are counted before and
after; an unreadable feed says so; every case exits 0.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "print_title_safety.py"

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "stock_status", "merchant_name",
)


def _row(number: int, title: str, shop: str, category: str, *, image: bool = True) -> list[str]:
    return [
        f"p{number}", title, "Fixturon", category, f"https://fixture.example.invalid/out/{number}",
        f"https://fixture.example.invalid/img/{number}.jpg" if image else "",
        "20.00", "GBP", "1", "", shop,
    ]


def _feed(path: Path) -> None:
    rows = []

    def add(count: int, title: str, shop: str, category: str, **extra) -> None:
        for _ in range(count):
            rows.append(_row(len(rows), f"{title} {len(rows)}", shop, category, **extra))

    # Kettles: the title is right on all 120 rows with a shelf; 7 held without one.
    add(60, "Fixturon Electric Kettle", "Fictional Kitchen", "Kettles")
    add(60, "Fixturon Electric Kettle", "Fictional Home", "Kettles")
    add(5, "Fixturon Glass Kettle", "Fictional Outlet", "")
    add(2, "Fixturon Steel Kettle", "Fictional Odds", "")
    # A held kettle with no image is held for that too, and counts nowhere.
    add(1, "Fixturon Copper Kettle", "Fictional Outlet", "", image=False)
    # Toasters: right on 100 of 105 (the shelf says kettle on 5): under 99%.
    add(100, "Fixturon Toaster", "Fictional Kitchen", "Toasters")
    add(5, "Fixturon Toaster", "Fictional Kitchen", "Kettles")
    add(4, "Fixturon Slim Toaster", "Fictional Outlet", "")
    # Blenders: right on 3 rows only, too few to tell.
    add(3, "Fixturon Blender", "Fictional Kitchen", "Blenders")
    add(6, "Fixturon Power Blender", "Fictional Outlet", "")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_COLUMNS)
        writer.writerows(rows)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)


class PrintTitleSafetyTests(unittest.TestCase):
    def test_only_the_kinds_read_right_99_percent_bring_their_held_rows_in(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            feed = Path(folder) / "feed.csv"
            _feed(feed)
            done = _run(str(feed), str(Path(folder) / "no-such-catalogues.json.gz"))
        self.assertEqual(done.returncode, 0, done.stderr)
        out = done.stdout
        self.assertIn("held for want of a category alone and showable by their title: 17", out)
        self.assertIn("with at least 100 rows to tell by: 1; they would bring in 7 of the 17", out)
        self.assertIn("  kettle: right 100.0% of 120; brings in 7 (Fictional Outlet 5, Fictional Odds 2)", out)
        self.assertIn("kinds under 99%: 1, holding 4 held rows", out)
        self.assertIn("  toaster: right 95.2% of 105; held 4; the shelf said instead: kettle 5", out)
        self.assertIn("kinds with fewer than 100 rows to tell by: 1, holding 6 held rows", out)
        self.assertIn("blender 6 (3)", out)
        # Kettles come from 2 shops shown, and from 4 with the held ones.
        self.assertIn("kinds with products from at least 3 shops: 0 today, 1 with the kinds at 99% brought in", out)
        self.assertNotIn("fixture.example.invalid", out)

    def test_an_unreadable_feed_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            feed = Path(folder) / "feed.csv"
            feed.write_text("", encoding="utf-8")
            done = _run(str(feed))
        self.assertEqual(done.returncode, 0)
        self.assertIn("the feed could not be read", done.stdout)

    def test_without_a_feed_it_says_how_to_run(self) -> None:
        done = _run()
        self.assertEqual(done.returncode, 0)
        self.assertIn("usage: print_title_safety.py", done.stdout)


if __name__ == "__main__":
    unittest.main()
