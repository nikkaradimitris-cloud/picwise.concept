"""Which shops two Awin feed links hold, compared before a new link replaces the old.

`.github/scripts/compare_feeds.py`, run by `.github/workflows/feed-compare.yml` (owner,
2026-10-31: «πως θα ξέρω οτι συμπεριλαμβάνονται και τα παλιότερα μέσα στο καινούργιο?»).
Pinned here: shops are counted by the advertiser's id, by name when a row has none, from
a plain or a gzipped feed; a new feed holding every shop of the one in use passes and
names the shops it adds; one lacking a shop, or keeping one with over a tenth fewer rows
(a link made with some categories only), fails and names it, while a few rows less
pass; with no new link the shops in use are listed; a link that cannot be read fails; a
link is never printed.

Every feed is local test data: fictional shops, `file://` links to temporary files.
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
SCRIPT = ROOT / ".github" / "scripts" / "compare_feeds.py"

HEADER = ["aw_product_id", "product_name", "advertiser_id", "advertiser_name", "search_price"]


def _feed(path: Path, shops: dict[str, tuple[str, int]], *, gzipped: bool = False) -> str:
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(HEADER)
    number = 0
    for ident, (name, rows) in shops.items():
        for _ in range(rows):
            writer.writerow([f"p{number}", f"Fictional product {number}", ident, name, "9.99"])
            number += 1
    data = text.getvalue().encode("utf-8")
    path.write_bytes(gzip.compress(data) if gzipped else data)
    return path.resolve().as_uri()


def _run(old: str | None, new: str | None) -> subprocess.CompletedProcess:
    env = {name: value for name, value in os.environ.items() if not name.startswith("AWIN_FEED_URL")}
    if old is not None:
        env["AWIN_FEED_URL"] = old
    if new is not None:
        env["AWIN_FEED_URL_NEW"] = new
    return subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, check=False)


OLD = {"101": ("Fictional Home", 3), "102": ("Fictional Rings", 2), "": ("Fictional Unnamed Id", 1)}


class CompareFeedsTests(unittest.TestCase):
    def test_a_new_feed_with_every_old_shop_passes_and_names_the_added(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            old = _feed(Path(folder) / "old.csv.gz", OLD, gzipped=True)
            new = _feed(Path(folder) / "new.csv", {**OLD, "103": ("Fictional Tools", 4)})
            done = _run(old, new)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        out = done.stdout
        self.assertIn("the in use feed: 3 shops, 6 rows", out)
        self.assertIn("the new feed: 4 shops, 10 rows", out)
        self.assertIn("shops of the feed in use that the new one lacks: 0", out)
        self.assertIn("shops the new feed adds: 1", out)
        self.assertIn("4  Fictional Tools (103)", out)
        self.assertIn("the new feed holds every shop of the one in use, with its rows", out)
        self.assertNotIn(folder, out)

    def test_the_columns_size_and_further_photos_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            old = _feed(Path(folder) / "old.csv", OLD)
            path = Path(folder) / "new.csv"
            text = io.StringIO()
            writer = csv.writer(text)
            writer.writerow(HEADER + ["additional_image_link"])
            extras = ["https://example.invalid/a.jpg,https://example.invalid/b.jpg", "", "https://example.invalid/c.jpg"]
            for number, (ident, (name, rows)) in enumerate(OLD.items()):
                for row in range(rows):
                    writer.writerow([f"p{number}{row}", "Fictional", ident, name, "9.99", extras[(number + row) % 3]])
            path.write_text(text.getvalue(), encoding="utf-8")
            done = _run(old, path.resolve().as_uri())
        out = done.stdout
        self.assertIn("additional_image_link: not among its columns", out)
        self.assertIn("additional_image_link: in its columns; rows with further photos: 4 (66.7%); 1 links: 3, 2 links: 1", out)
        self.assertIn("columns the new feed adds: additional_image_link", out)
        self.assertIn("columns the new feed lacks: none", out)
        self.assertIn("MB as downloaded; 6 columns", out)
        self.assertNotIn("example.invalid", out)

    def test_the_sale_prices_are_counted_with_why_each_is_left(self) -> None:
        # 2026-11-19: no product was at its shop's sale price on the first night the site
        # read them; this counts the feed's sale prices by the site's own rule.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feed.csv"
            text = io.StringIO()
            writer = csv.writer(text)
            writer.writerow(["id", "advertiser_id", "advertiser_name", "price", "sale_price",
                             "sale_price_effective_date"])
            writer.writerow(["a1", "101", "Fictional Home", "40.00 GBP", "29.99 GBP", ""])
            writer.writerow(["a2", "101", "Fictional Home", "40.00 GBP", "", ""])
            writer.writerow(["a3", "102", "Fictional Rings", "40.00 GBP", "40.00 GBP", ""])
            writer.writerow(["a4", "102", "Fictional Rings", "40.00 GBP", "29.99 GBP", "from 1 Nov"])
            # A row with one field too many: its fields stand in the wrong columns, and its
            # usual price read as its sale price.
            writer.writerow(["a5", "102", "Fictional Rings", "Union Jack", "40.00 GBP", "", ""])
            path.write_text(text.getvalue(), encoding="utf-8")
            done = _run(path.resolve().as_uri(), None)
        out = done.stdout
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("rows with a sale price: 4; the shop's price tonight by the site's rule: 2", out)
        self.assertIn("rows whose fields do not match the header: 1 (1 with more fields, 0 with fewer)", out)
        self.assertRegex(out, r"1 of\s+3\s+Fictional Rings \(102\)")
        self.assertIn("left, not_lower: 1", out)
        self.assertIn("left, dates_unread: 1", out)
        self.assertIn("dates_unread, written as 'from 9 Nov': 1", out)
        self.assertRegex(out, r"3\s+1\s+Fictional Rings \(102\)")
        self.assertRegex(out, r"1\s+1\s+Fictional Home \(101\)")
        # Without the column, it says so.
        with tempfile.TemporaryDirectory() as folder:
            done = _run(_feed(Path(folder) / "old.csv", OLD), None)
        self.assertIn("sale_price: not among its columns", done.stdout)

    def test_the_variants_are_counted_by_the_site_s_rule(self) -> None:
        # Owner, 2026-11-19: one card per product, its sizes and colours chosen at the shop.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feed.csv"
            text = io.StringIO()
            writer = csv.writer(text)
            writer.writerow(["id", "advertiser_id", "advertiser_name", "title", "brand", "price",
                             "item_group_id", "color", "size"])
            # One shoe in two colours and two sizes: one card, three rows joining it.
            for colour in ("Black", "White"):
                for size in ("8", "9"):
                    writer.writerow([f"s-{colour}-{size}", "101", "Fictional Shoes",
                                     f"Fictional Runner {colour} Size {size}", "Fictional", "40.00 GBP",
                                     "G1", colour, size])
            # A group holding two products: kept apart.
            writer.writerow(["k1", "101", "Fictional Shoes", "Fictional Kettle Black", "Fictional", "20.00 GBP",
                             "G2", "Black", ""])
            writer.writerow(["k2", "101", "Fictional Shoes", "Fictional Toaster Black", "Fictional", "20.00 GBP",
                             "G2", "Black", ""])
            # No group: by brand and title, the colour taken out.
            writer.writerow(["m1", "102", "Fictional Home", "Fictional Mug Red", "Fictional", "5.00 GBP", "", "Red", ""])
            writer.writerow(["m2", "102", "Fictional Home", "Fictional Mug Blue", "Fictional", "5.00 GBP", "", "Blue", ""])
            # Naming nothing: no variant.
            writer.writerow(["p1", "102", "Fictional Home", "Fictional Plate", "Fictional", "5.00 GBP", "", "", ""])
            path.write_text(text.getvalue(), encoding="utf-8")
            done = _run(path.resolve().as_uri(), None)
        out = done.stdout
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("variants: rows naming a group: 6, a color: 8, a size: 4", out)
        self.assertIn(
            "rows that would join another row of their product: 4 (by group 3; with no group, by brand and title 1)", out
        )
        self.assertIn("groups whose rows name different products (kept apart): 1 of 2", out)
        self.assertRegex(out, r"3 of\s+6\s+Fictional Shoes \(101\)")
        self.assertRegex(out, r"1 of\s+3\s+Fictional Home \(102\)")
        self.assertNotIn("Fictional Runner", out)
        # The shops' pages: no row here links to one.
        self.assertIn("pages: rows linking to a product page: 0; naming a variant in its address: 0", out)
        # Without the columns, it says so.
        with tempfile.TemporaryDirectory() as folder:
            done = _run(_feed(Path(folder) / "old.csv", OLD), None)
        self.assertIn("variants: no item_group_id, color or size among its columns", done.stdout)

    def test_the_rows_sharing_a_product_page_are_counted(self) -> None:
        # 2026-11-19: the feed names a group, colour or size on almost no row; a shop's
        # product page, the size and colour chosen on it, may tie them instead.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feed.csv"
            text = io.StringIO()
            writer = csv.writer(text)
            writer.writerow(["id", "advertiser_id", "advertiser_name", "title", "brand", "price", "link"])
            page = "https://shoes.example.invalid/products/runner"
            for number, size in enumerate(("8", "9", "10")):
                writer.writerow([f"r{number}", "101", "Fictional Shoes", f"Fictional Runner Size {size}", "Fictional",
                                 "40.00 GBP", f"{page}?variant={number}"])
            # The same page, a title far apart: counted apart.
            writer.writerow(["x1", "101", "Fictional Shoes", "Fictional Garden Hose Reel 50m", "Fictional",
                             "20.00 GBP", page])
            # A front page: no product's page.
            writer.writerow(["h1", "102", "Fictional Home", "Fictional Mug", "Fictional", "5.00 GBP",
                             "https://home.example.invalid/"])
            path.write_text(text.getvalue(), encoding="utf-8")
            done = _run(path.resolve().as_uri(), None)
        out = done.stdout
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("pages: rows linking to a product page: 4; naming a variant in its address: 3", out)
        self.assertIn("rows whose page another row already has: 3 (titles within 3 words of the first: 2; "
                      "further apart: 1)", out)
        self.assertIn("pages with 20 rows or more: 0 (0 rows)", out)
        self.assertRegex(out, r"2 of\s+4\s+Fictional Shoes \(101\)  \(further apart: 1\)")
        self.assertNotIn("runner", out.lower())

    def test_a_new_feed_lacking_an_old_shop_fails_and_names_it(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            old = _feed(Path(folder) / "old.csv", OLD)
            lacking = {key: value for key, value in OLD.items() if key != "102"}
            new = _feed(Path(folder) / "new.csv.gz", {**lacking, "103": ("Fictional Tools", 4)}, gzipped=True)
            done = _run(old, new)
        self.assertEqual(done.returncode, 1)
        self.assertIn("shops of the feed in use that the new one lacks: 1", done.stdout)
        self.assertIn("2  Fictional Rings (102)", done.stdout)
        self.assertIn("keep the link in use", done.stdout)

    def test_a_shop_kept_with_far_fewer_rows_fails_and_a_few_less_pass(self) -> None:
        big = {"101": ("Fictional Home", 100), "102": ("Fictional Rings", 50)}
        with tempfile.TemporaryDirectory() as folder:
            old = _feed(Path(folder) / "old.csv", big)
            # Only some categories chosen: the home shop keeps 60 of its 100 rows.
            narrowed = _feed(Path(folder) / "narrowed.csv", {"101": ("Fictional Home", 60), "102": ("Fictional Rings", 50)})
            # A day's moves: 95 of 100.
            moved = _feed(Path(folder) / "moved.csv", {"101": ("Fictional Home", 95), "102": ("Fictional Rings", 51)})
            failed = _run(old, narrowed)
            passed = _run(old, moved)
        self.assertEqual(failed.returncode, 1)
        self.assertIn("keeps with over a tenth fewer rows: 1", failed.stdout)
        self.assertIn("100 ->        60  Fictional Home (101)", failed.stdout)
        self.assertIn("keep the link in use", failed.stdout)
        self.assertEqual(passed.returncode, 0, passed.stdout)
        self.assertIn("keeps with over a tenth fewer rows: 0", passed.stdout)

    def test_without_a_new_link_the_shops_in_use_are_listed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            old = _feed(Path(folder) / "old.csv", OLD)
            done = _run(old, None)
        self.assertEqual(done.returncode, 0)
        self.assertIn("no new feed link in GitHub's secrets", done.stdout)
        self.assertIn("3  Fictional Home (101)", done.stdout)
        # A row with no id is counted by its shop's name.
        self.assertIn("1  Fictional Unnamed Id", done.stdout)

    def test_a_link_that_cannot_be_read_fails_without_printing_it(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            missing = (Path(folder) / "nowhere.csv").resolve().as_uri()
            done = _run(missing, None)
            old = _feed(Path(folder) / "old.csv", OLD)
            broken = _run(old, missing)
        self.assertEqual(done.returncode, 1)
        self.assertIn("the in use feed could not be read", done.stdout)
        self.assertEqual(broken.returncode, 1)
        self.assertIn("the new feed could not be read", broken.stdout)
        for out in (done.stdout + done.stderr, broken.stdout + broken.stderr):
            self.assertNotIn("nowhere.csv", out)
            self.assertNotIn(folder, out)

    def test_without_the_link_in_use_nothing_is_compared(self) -> None:
        done = _run(None, None)
        self.assertEqual(done.returncode, 1)
        self.assertIn("no in use feed link in GitHub's secrets", done.stdout)


if __name__ == "__main__":
    unittest.main()
