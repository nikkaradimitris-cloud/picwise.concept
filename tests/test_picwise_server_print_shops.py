"""Each shop of the server's prepared catalogue, printed by its deployment.

`deployment/server/print_shops.py`. Owner, 2026-10-25: the server's deployment said only
how many shops its feed link brought (82), not which, so whether the shops taken out in
Awin's Create-a-Feed were out could not be read from its log. Pinned here: on the note
`tools/prepare_catalogue.py --static-dir` writes, every shop of the feed is printed with
its rows, shown, only when asked for and held, and why held, also a shop none of whose
rows is shown, which the count of shops with a product shown leaves out (the note's own
82 counted shops whose rows were all out of stock: 77 showed something); and on a
missing or failed note the script says so and exits 0, so a deployment never fails
because of the list. Owner, the same day: then, per shop, its rows without a category
(about 532,000 of 1,123,857 on the server), how many could be shown by the shop's own
type or by the title alone and read as a kind, and for the shops with the most, their
types and titles; a note written before that measure says it has none.

Every row is local test data (`tests/fixtures`, or written here): fictional shops,
`.invalid` URLs.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "print_shops.py"
FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"


def _print_shops(note_text: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=note_text, capture_output=True, text=True, check=False
    )


def _prepared_note(feed: Path) -> str:
    """The public note `tools/prepare_catalogue.py` writes for this feed file."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("AWIN_")}
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run(
            [
                sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"),
                "--feed-file", str(feed),
                "--out", str(Path(folder) / "catalogue.json.gz"),
                "--static-dir", folder,
            ],
            env=env, capture_output=True, check=True,
        )
        return (Path(folder) / "prepared.json").read_text(encoding="utf-8")


_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "product_type",
)


def _row(pid: str, title: str, category: str = "", product_type: str = "") -> list[str]:
    return [
        pid, title, "Fixturon", category, f"https://fixture.example.invalid/out/{pid}",
        f"https://fixture.example.invalid/img/{pid}.jpg", "20.00", "GBP", "1", "Fixture Store Two",
        product_type,
    ]


class PrintShopsTests(unittest.TestCase):
    def test_every_shop_of_the_prepared_note_with_its_counts_and_reasons(self) -> None:
        result = _print_shops(_prepared_note(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(
            lines[0],
            "4 shops in the feed, 4 with a product shown; 19 rows: shown 15, only when asked for 0, held 4",
        )
        # The table of the 4 shops, then the rows without a category: none here.
        self.assertEqual(lines[6:8], ["", "rows without a category: 0; held for that alone 0, 0 of them with the shop's own type"])
        self.assertEqual(len(lines), 2 + 4 + 1 + 7)
        self.assertIn(
            "        4         2       0         2  Fixture Store Two: availability_discontinued 1, "
            "purchasability_discontinued 1, missing_price_text 1",
            lines,
        )
        self.assertIn("        3         3       0         0  Fixture Store Three", lines)

    def test_a_shop_none_of_whose_rows_is_shown_is_still_listed(self) -> None:
        note = {
            "prepared": True,
            "shops": 1,
            "intake": {
                "rows": 1_250, "shown": 1_000, "not_new": 0, "held": 250,
                "shops": [
                    {"shop": "Kept Shop", "rows": 1_000, "shown": 1_000, "not_new": 0, "held": 0,
                     "held_reasons": {}},
                    {"shop": "Euro Shop", "rows": 250, "shown": 0, "not_new": 0, "held": 250,
                     "held_reasons": {"a": 250, "b": 20, "c": 3, "d": 1}},
                ],
            },
        }
        result = _print_shops(json.dumps(note))
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.splitlines()
        self.assertEqual(
            lines[0], "2 shops in the feed, 1 with a product shown; 1,250 rows: shown 1,000, only when asked for 0, held 250"
        )
        self.assertEqual(lines[3], "      250         0       0       250  Euro Shop: a 250, b 20, c 3")
        self.assertIn("    1,000     1,000       0         0  Kept Shop", result.stdout)
        # A note written before the rows without a category were measured.
        self.assertEqual(lines[-1], "no count of the rows without a category in the note")

    def test_rows_without_a_category_by_type_or_by_title(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            feed = Path(folder) / "feed.csv"
            with feed.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(_COLUMNS)
                writer.writerows(
                    [
                        _row("e1", "Fixturon Glass Kettle", product_type="Kitchen > Kettles"),
                        _row("e2", "Fixturon Chocolate Mice 225g"),
                        _row("e3", "Fixturon Thing 3"),
                        _row("e4", "Fixturon Steel Kettle", category="Kettles"),
                    ]
                )
            result = _print_shops(_prepared_note(feed))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        start = lines.index("rows without a category: 3; held for that alone 3, 1 of them with the shop's own type")
        self.assertEqual(
            lines[start + 1:],
            [
                "  could be shown by their own type: 1 (kind 1, accessory 0, doubtful 0, none 0)",
                "  could be shown by their title alone: 2 (kind 1, accessory 0, doubtful 0, none 1)",
                (
                    "  of those, the shop's address names shelves for 2 of 2, a kind for 0; with the title's kind "
                    "too 0, agreeing 0"
                ),
                (
                    "  of those, another shop's category for the same barcode: a barcode on 0 of 2, a category "
                    "found for 0, a kind for 0 (0 where the title gives none); with the title's kind too 0, agreeing 0"
                ),
                "  of those, where the title gives no kind (1), the description's first sentence gives one to 0",
                "   no cat     alone  own type   by type    a kind  by title    a kind  shop",
                "        3         3         1         1         1         2         1  Fixture Store Two",
                "      types: Kitchen > Kettles (1)",
                "      titles: Fixturon Chocolate Mice 225g -> mouse",
                (
                    "      columns: aw_deep_link (2); aw_image_url (2); aw_product_id (2); brand_name (2); "
                    "currency (2); in_stock (2); merchant_name (2); product_name (2); search_price (2)"
                ),
                (
                    "      the shop's address names shelves for 2 of 2, a kind for 0; with the title's kind too 0, "
                    "agreeing 0"
                ),
                "      address shelves: out (2)",
                (
                    "      another shop's category for the same barcode: a barcode on 0 of 2, a category found for 0, "
                    "a kind for 0 (0 where the title gives none); with the title's kind too 0, agreeing 0"
                ),
                "      where the title gives no kind (1), the description's first sentence gives one to 0",
            ],
        )

    def test_the_shops_with_the_most_rows_without_a_category_first_and_detailed(self) -> None:
        def shop(number: int) -> dict:
            return {
                "shop": f"Shop {number:02d}", "rows": 100, "shown": 0, "not_new": 0, "held": 100,
                "held_reasons": {"missing_category_text": 100 - number},
                "without_category": {
                    "rows": 100 - number, "only_this": 100 - number, "with_product_type": 1,
                    "shown_by_type": 1, "shown_by_title": 2,
                    "kinds_by_type": {"kind": 1, "accessory": 0, "doubtful": 0, "none": 0},
                    "kinds_by_title": None,
                    "types": [{"value": "Kitchen > Kettles", "rows": 1}], "titles": [],
                },
            }

        shops = [shop(number) for number in range(17)]
        shops.append({"shop": "Shop With Categories", "rows": 5, "shown": 5, "not_new": 0, "held": 0,
                      "held_reasons": {}, "without_category": {"rows": 0}})
        note = {
            "prepared": True,
            "intake": {
                "rows": 1_705, "shown": 5, "not_new": 0, "held": 1_700, "shops": shops,
                "without_category": {
                    "rows": 1_564, "only_this": 1_564, "with_product_type": 17, "shown_by_type": 17,
                    "shown_by_title": 34,
                    "kinds_by_type": {"kind": 17, "accessory": 0, "doubtful": 0, "none": 0},
                    "kinds_by_title": None,
                },
            },
        }
        lines = _print_shops(json.dumps(note)).stdout.splitlines()
        start = lines.index("   no cat     alone  own type   by type    a kind  by title    a kind  shop")
        table = lines[start + 1:]
        # Kinds not read show as "-"; the 15 shops with the most show their types.
        self.assertEqual(table[0], "      100       100         1         1         1         2         -  Shop 00")
        self.assertEqual(table[1], "      types: Kitchen > Kettles (1)")
        self.assertEqual(table[-2:], [
            "       85        85         1         1         1         2         -  Shop 15",
            "       84        84         1         1         1         2         -  Shop 16",
        ])
        self.assertNotIn("Shop With Categories", "\n".join(table))
        self.assertIn("  could be shown by their title alone: 34 (kinds not read)", lines)

    def test_no_note_or_no_list_says_so_and_never_fails(self) -> None:
        for note_text, said in (
            ("", "no prepared note on the server"),
            ('{"prepared": false, "reason": "feed_not_readable"}', "nothing prepared: feed_not_readable"),
            ('{"prepared": true, "shops": 3, "intake": null}', "no shop list in the note: None"),
            (
                '{"prepared": true, "shops": 3, "intake": {"error": "MemoryError at x.py:1"}}',
                "no shop list in the note: {'error': 'MemoryError at x.py:1'}",
            ),
        ):
            with self.subTest(said=said):
                result = _print_shops(note_text)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), said)


if __name__ == "__main__":
    unittest.main()
