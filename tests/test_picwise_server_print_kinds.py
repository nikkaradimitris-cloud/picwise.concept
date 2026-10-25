"""The kinds of the server's prepared catalogue that may be wrong, printed by its deployment.

`deployment/server/print_kinds.py`. Owner, 2026-10-25: with every Google-format shop on
the server, the 12 searches showed products of another kind ("Colleen Hoover" books for
"vacuum cleaner", "Chocolate Mice" for "mouse"), so the deployment prints the note's two
lists per kind, the products whose title names none of the kind's words and those whose
title alone names it, each with its cheapest three. Pinned here: both lists as the note
gives them, a note written before the second list, and on a missing or failed note a
line that says so and exit 0, so a deployment never fails because of the list.

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
                    "only the title names one: 300"
                ),
                "",
                (
                    "== the title names none of the kind's words: the kinds with the most, each with its "
                    "cheapest (price | shop | title | shelf)"
                ),
                "camera: 40 of 377",
                "    5.50 GBP | Fixture Store One | Fixturon OV7670 Module | Electronic Components",
                "    9.99 GBP | Fixture Store One | Fixturon 50mm Lens | Camera Lenses",
                "",
                (
                    "== only the title names the kind, neither the type nor the shelf: the kinds with the most, "
                    "each with its cheapest (price | shop | title | shelf)"
                ),
                "vacuum_cleaner: 12 of 16",
                "    2.99 GBP | Fixture Books | Fixturon Hoover Paperback | Books",
            ],
        )

    def test_a_note_written_before_the_second_list(self) -> None:
        kinds = {key: value for key, value in _KINDS.items() if key in ("products", "title_names_no_kind", "by_kind")}
        lines = _print_kinds(json.dumps({"prepared": True, "kinds": kinds})).stdout.splitlines()
        self.assertTrue(lines[0].endswith("only the title names one: not measured"))
        self.assertEqual(lines[-1], "    9.99 GBP | Fixture Store One | Fixturon 50mm Lens | Camera Lenses")

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


if __name__ == "__main__":
    unittest.main()
