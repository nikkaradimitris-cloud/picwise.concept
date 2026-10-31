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
