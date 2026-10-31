"""Each server card of the deployment's comparison, with the shelf and kinds it was read with.

`deployment/server/compare_with_vercel.py`. Owner, 2026-10-25, while fixing the kinds a
title alone gives: after the rule for an aisle that holds no such department, two real
smartwatches left the server's "smartwatch" page, and a card shows no shelf, so it could
not be told why. With the server's prepared catalogue the comparison now prints, under
each server card, the shelf and the kinds the search read it with, found by its title.
Pinned here: the shelves read from a catalogue `tools/prepare_catalogue.py` writes, each
card's whole title, the line under each card, and a catalogue that cannot be read
leaving the comparison to go on without shelves.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "compare_with_vercel.py"

_spec = importlib.util.spec_from_file_location("compare_with_vercel", SCRIPT)
compare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare)

# The category in Google's column, as the server's feed of Google-format shops has it.
_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "google_product_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
)


def _row(pid: str, title: str, category: str) -> list[str]:
    return [
        pid, title, "Fixturon", category, f"https://fixture.example.invalid/out/{pid}",
        f"https://fixture.example.invalid/img/{pid}.jpg", "3.75", "GBP", "1", "Fixture Store One",
    ]


def _page(*titles: str) -> str:
    cards = "".join(
        f'<article class="pw-card"><h2 class="pw-card-title">{title}</h2><p class="pw-price">3.75 GBP</p></article>'
        for title in titles
    )
    return f'<p class="pw-counter">{len(titles)} of {len(titles)}</p>{cards}'


class ServerCardShelvesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        folder = Path(cls.folder.name)
        feed = folder / "feed.csv"
        with feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            writer.writerows(
                [
                    _row("k1", "Fixturon Glass Kettle 1.7L", "Kettles"),
                    _row("m1", "Fixturon Chocolate Mice - 225g Sweet Pouch",
                         "Food, Beverages & Tobacco > Food Items > Sweets & Chocolate"),
                ]
            )
        cls.catalogue = folder / "catalogue.json.gz"
        env = {key: value for key, value in os.environ.items() if not key.startswith("AWIN_")}
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"), "--feed-file", str(feed),
             "--out", str(cls.catalogue)],
            env=env, capture_output=True, check=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.folder.cleanup()

    def test_the_shelf_and_kinds_each_product_was_read_with(self) -> None:
        shelves = compare.catalogue_shelves(str(self.catalogue))
        self.assertEqual(shelves["Fixturon Glass Kettle 1.7L"], "kettles | kettle")
        self.assertEqual(
            shelves["Fixturon Chocolate Mice - 225g Sweet Pouch"],
            "food, beverages & tobacco > food items > sweets & chocolate | __uncertain_kind__",
        )
        self.assertNotIn("fixture.example.invalid", repr(shelves))

    def test_each_server_card_with_its_shelf(self) -> None:
        page = _page("Fixturon Glass Kettle 1.7L", "Fixturon Unknown &amp; Gone")
        self.assertEqual(compare.card_titles(page), ["Fixturon Glass Kettle 1.7L", "Fixturon Unknown & Gone"])
        shelves = compare.catalogue_shelves(str(self.catalogue))
        out = io.StringIO()
        with redirect_stdout(out):
            compare.print_cards(
                compare.search_cards(page), [shelves.get(title, "-") for title in compare.card_titles(page)]
            )
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], "    counter: 2 of 2")
        self.assertEqual(lines[2], "        shelf: kettles | kettle")
        self.assertEqual(lines[4], "        shelf: -")
        self.assertEqual(len(lines), 5)

    def test_a_catalogue_that_cannot_be_read_gives_no_shelves(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "catalogue.json.gz"
            broken.write_bytes(b"")
            out = io.StringIO()
            with redirect_stdout(out):
                shelves = compare.catalogue_shelves(str(broken))
        self.assertEqual(shelves, {})
        self.assertTrue(out.getvalue().startswith("=== no shelves for the cards"))


if __name__ == "__main__":
    unittest.main()
