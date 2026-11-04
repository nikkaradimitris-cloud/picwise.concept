"""The kinds of the server's prepared catalogue that may be wrong, printed by its deployment.

`deployment/server/print_kinds.py`. Owner, 2026-10-25: with every Google-format shop on
the server, the 12 searches showed products of another kind ("Colleen Hoover" books for
"vacuum cleaner", "Chocolate Mice" for "mouse"), so the deployment prints the note's two
lists per kind, the products whose title names none of the kind's words and those whose
title alone names it, each with its cheapest three and, since the same day, the shelves
they most often sit on. Pinned here: both lists as the note gives them, a kind written
before its shelves were, a note written before the second list, and on a missing or
failed note a line that says so and exit 0, so a deployment never fails because of the
list.

Every row is local test data: fictional brands and shops.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "print_kinds.py"


def _print_kinds(note_text: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=note_text, capture_output=True, text=True, check=False
    )


_KINDS = {
    "products": 12_500,
    "title_names_no_kind": 1_200,
    "by_kind": [
        {
            "kind": "camera",
            "products": 377,
            "title_without_kind": 40,
            "cheapest": [
                "5.50 GBP | Fixture Store One | Fixturon OV7670 Module | Electronic Components",
                "9.99 GBP | Fixture Store One | Fixturon 50mm Lens | Camera Lenses",
            ],
            "shelves": [
                {"shelf": "electronics > electronic components", "products": 30},
                {"shelf": "cameras & optics > camera lenses", "products": 10},
            ],
        }
    ],
    "doubted_by_aisle": 85,
    "by_kind_doubted_by_aisle": [
        {
            "kind": "mouse",
            "products": 27,
            "doubted_by_its_aisle": 85,
            "cheapest": ["1.49 GBP | Fixture Sweets | Fixturon Chocolate Mice | Sweets & Chocolate"],
            "shelves": [{"shelf": "food, beverages & tobacco > food items > sweets & chocolate", "products": 85}],
        }
    ],
    "only_title_names_kind": 300,
    "by_kind_only_title": [
        {
            "kind": "vacuum_cleaner",
            "products": 16,
            "only_title_names_it": 12,
            "cheapest": ["2.99 GBP | Fixture Books | Fixturon Hoover Paperback | Books"],
        }
    ],
}


class PrintKindsTests(unittest.TestCase):
    def test_both_lists_with_their_cheapest(self) -> None:
        result = _print_kinds(json.dumps({"prepared": True, "kinds": _KINDS}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                (
                    "12,500 products shown as a kind; the title names none of its kinds: 1,200; "
                    "only the title names one: 300; made doubtful by their aisle: 85"
                ),
                "",
                (
                    "== the title names none of the kind's words: the kinds with the most, each with its "
                    "cheapest (price | shop | title | shelf)"
                ),
                "camera: 40 of 377",
                "    5.50 GBP | Fixture Store One | Fixturon OV7670 Module | Electronic Components",
                "    9.99 GBP | Fixture Store One | Fixturon 50mm Lens | Camera Lenses",
                "    shelves: electronics > electronic components (30); cameras & optics > camera lenses (10)",
                "",
                (
                    "== only the title names the kind, neither the type nor the shelf: the kinds with the most, "
                    "each with its cheapest (price | shop | title | shelf)"
                ),
                "vacuum_cleaner: 12 of 16",
                "    2.99 GBP | Fixture Books | Fixturon Hoover Paperback | Books",
                "",
                (
                    "== made doubtful by their aisle, per kind they were read as before: "
                    "the kinds with the most, each with its cheapest (price | shop | title | shelf)"
                ),
                "mouse: 85 doubted; still of the kind: 27",
                "    1.49 GBP | Fixture Sweets | Fixturon Chocolate Mice | Sweets & Chocolate",
                "    shelves: food, beverages & tobacco > food items > sweets & chocolate (85)",
                "",
                "== the title alone against the shelf: not measured (None)",
            ],
        )

    def test_the_title_alone_against_the_shelf(self) -> None:
        title_alone = {
            "products": 1_000, "agrees": 720, "differs": 80, "accessory": 50, "doubtful": 100, "none": 50,
            "by_shop": [
                {"shop": "Fixture Store One", "products": 900, "agrees": 700, "differs": 50, "accessory": 50,
                 "doubtful": 50, "none": 50},
                {"shop": "Fixture Store Two", "products": 100, "agrees": 20, "differs": 30, "accessory": 0,
                 "doubtful": 50, "none": 0},
            ],
            "differs_by_pair": [
                {"shelf_kind": "kettle", "title_kind": "mouse", "products": 40,
                 "cheapest": ["9.99 GBP | Fixture Store Two | Fixturon Wireless Optical Mouse | Kettles"]},
            ],
        }
        lines = _print_kinds(json.dumps({"prepared": True, "kinds": _KINDS, "title_alone": title_alone})).stdout
        self.assertEqual(
            lines.split("== the title alone against the shelf")[1].splitlines(),
            [
                (
                    ": 1,000 products with a kind from their shelf; the title alone gives one to 800 (80.0%), "
                    "the shelf's 720 (90.0% of those), another 80; none: an accessory 50, doubtful 100, nothing 50"
                ),
                " products  a kind  agrees    desc  agrees  shop",
                "      900   83.3%   93.3%       -       -  Fixture Store One",
                "      100   50.0%   40.0%       -       -  Fixture Store Two",
                "-- the shelf's kind -> the title's other kind, the most frequent, each with its cheapest",
                "kettle -> mouse: 40",
                "    9.99 GBP | Fixture Store Two | Fixturon Wireless Optical Mouse | Kettles",
            ],
        )

    def test_a_note_written_before_the_second_list(self) -> None:
        # Written before the second list, and before each kind gave its shelves.
        kinds = {key: value for key, value in _KINDS.items() if key in ("products", "title_names_no_kind")}
        kinds["by_kind"] = [
            {key: value for key, value in entry.items() if key != "shelves"} for entry in _KINDS["by_kind"]
        ]
        lines = _print_kinds(json.dumps({"prepared": True, "kinds": kinds})).stdout.splitlines()
        self.assertTrue(lines[0].endswith("only the title names one: not measured; made doubtful by their aisle: not measured"))
        self.assertEqual(
            lines[-3:],
            [
                "    9.99 GBP | Fixture Store One | Fixturon 50mm Lens | Camera Lenses",
                "",
                "== the title alone against the shelf: not measured (None)",
            ],
        )

    def test_no_note_or_no_kinds_says_so_and_never_fails(self) -> None:
        for note_text, said in (
            ("", "no prepared note on the server"),
            ('{"prepared": false, "reason": "preparing_failed"}', "nothing prepared: preparing_failed"),
            ('{"prepared": true}', "no kinds in the note: None"),
            (
                '{"prepared": true, "kinds": {"error": "KeyError at x.py:1"}}',
                "no kinds in the note: {'error': 'KeyError at x.py:1'}",
            ),
        ):
            with self.subTest(said=said):
                result = _print_kinds(note_text)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), said)

    def test_where_the_title_gives_none_the_description(self) -> None:
        title_alone = {
            "products": 100, "agrees": 60, "differs": 5, "accessory": 5, "doubtful": 10, "none": 20,
            "title_gives_none": 35, "description_gives": 20, "description_agrees": 18,
            "by_shop": [
                {"shop": "Fixture Store One", "products": 100, "agrees": 60, "differs": 5, "accessory": 5,
                 "doubtful": 10, "none": 20, "title_gives_none": 35, "description_gives": 20,
                 "description_agrees": 18},
            ],
            "differs_by_pair": [],
        }
        out = _print_kinds(json.dumps({"prepared": True, "kinds": _KINDS, "title_alone": title_alone})).stdout
        self.assertIn(
            "-- where the title gives none (35), the description's first sentence gives a kind to 20 (57.1%), "
            "the shelf's for 18 (90.0% of those)",
            out,
        )
        self.assertIn("      100   65.0%   92.3%   57.1%   90.0%  Fixture Store One", out)


if __name__ == "__main__":
    unittest.main()
