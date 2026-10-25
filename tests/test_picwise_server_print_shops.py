"""Each shop of the server's prepared catalogue, printed by its deployment.

`deployment/server/print_shops.py`. Owner, 2026-10-25: the server's deployment said only
how many shops its feed link brought (82), not which, so whether the shops taken out in
Awin's Create-a-Feed were out could not be read from its log. Pinned here: on the note
`tools/prepare_catalogue.py --static-dir` writes, every shop of the feed is printed with
its rows, shown, only when asked for and held, and why held, also a shop none of whose
rows is shown, which the count of shops with a product shown leaves out (the note's own
82 counted shops whose rows were all out of stock: 77 showed something); and on a
missing or failed note the script says so and exits 0, so a deployment never fails
because of the list.

Every row is local test data (`tests/fixtures`): fictional shops, `.invalid` URLs.
"""
from __future__ import annotations

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


class PrintShopsTests(unittest.TestCase):
    def test_every_shop_of_the_prepared_note_with_its_counts_and_reasons(self) -> None:
        env = {key: value for key, value in os.environ.items() if not key.startswith("AWIN_")}
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(
                [
                    sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"),
                    "--feed-file", str(FIXTURE),
                    "--out", str(Path(folder) / "catalogue.json.gz"),
                    "--static-dir", folder,
                ],
                env=env, capture_output=True, check=True,
            )
            note_text = (Path(folder) / "prepared.json").read_text(encoding="utf-8")
        result = _print_shops(note_text)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(
            lines[0],
            "4 shops in the feed, 4 with a product shown; 19 rows: shown 15, only when asked for 0, held 4",
        )
        self.assertEqual(len(lines), 2 + 4)
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
        self.assertEqual(lines[-1], "      250         0       0       250  Euro Shop: a 250, b 20, c 3")
        self.assertIn("    1,000     1,000       0         0  Kept Shop", result.stdout)

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
