"""The morning's category of the products not asked yet (`deployment/server/shelves_service.py`;
the checks' rules 5.5 and 7.6; owner, 2026-11-21: «Το AI ρωτιέται μία φορά για την κατηγορία
κάθε προϊόντος. Όποιο προϊόν δεν μπαίνει σε κατηγορία βγαίνει»).

Pinned: only the products named and not answered are asked, as the scan of 20/11 asked
(every answer checked, "no line fits" kept as such); every answer, old and new, is kept in
the file the preparation reads; the night's note says what was asked and what it cost; the
night's brake of $10 stops it and leaves the rest for the next morning; the unit runs under
the AI layer's own user, with its key, after the preparation.

Every product is local test data.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import scan_shelves  # noqa: E402
import shelves_service  # noqa: E402
from picwise_ai import shelves  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402

LINES = shelves.taxonomy_lines()
KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"
_ITEM_RE = re.compile(r"^(\d+)\. (.*?)(?: \| |$)")


def _answer(request: dict) -> tuple[Asked, str]:
    """A model that names no line for a gift card and the kettles' line for the rest."""
    answers = []
    for line in request["messages"][0]["content"].splitlines()[1:]:
        match = _ITEM_RE.match(line)
        if not match:
            continue
        number = int(match.group(1))
        if "gift card" in match.group(2).lower():
            answers.append({"n": number, "line": 0, "name": "none"})
        else:
            answers.append({"n": number, "line": LINES.index(KETTLES) + 1, "name": "Electric Kettles"})
    return Asked({"products": answers}, "end_turn", shelves.MODEL, 900, 300, 0, 40000, 0.004, 0.01, ""), ""


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class ShelvesServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.dir = Path(folder.name)
        (self.dir / "jobs").mkdir()
        self.job = self.dir / "jobs" / shelves_service.JOB_NAME
        items = [
            {"k": "k-kettle", "title": "Zentra Kettle", "brand": "Zentra", "price": "24.99", "category": "Kettles",
             "about": "", "shop": "Kettles", "products": 3},
            {"k": "k-gift", "title": "Zentra Gift Card", "brand": "Zentra", "price": "25.00", "category": "",
             "about": "", "shop": "Kettles", "products": 1},
            {"k": "k-known", "title": "Zentra Kettle Mini", "brand": "Zentra", "price": "19.99", "category": "",
             "about": "", "shop": "Kettles", "products": 1},
        ]
        with gzip.open(self.job, "wt", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(item) + "\n")
        scan_shelves.write_answers(self.dir / shelves_service.ANSWERS_NAME,
                                   {"k-known": {"k": "k-known", "line": KETTLES, "tries": 0, "at": "2026-11-20"},
                                    "k-other": {"k": "k-other", "line": "", "tries": 0, "at": "2026-11-20"}})

    def run_once(self, **limits) -> dict:
        clock = _Clock()
        return shelves_service.run(self.dir, ask_fn=_answer, lines=LINES, today="2026-11-23", clock=clock,
                                   sleep=clock.sleep, workers=1, **limits)

    def test_the_unasked_are_asked_every_answer_kept_and_the_night_noted(self) -> None:
        note = self.run_once()
        answers = scan_shelves.read_answers(self.dir / shelves_service.ANSWERS_NAME)
        self.assertEqual({key: record["line"] for key, record in answers.items()},
                         {"k-kettle": KETTLES, "k-gift": "", "k-known": KETTLES, "k-other": ""})
        self.assertEqual((note["named"], note["asked"], note["answered"], note["no_line_fits"], note["left"]),
                         (3, 2, 2, 1, 0))
        self.assertEqual(note["calls"], 1)
        self.assertAlmostEqual(note["cost_usd"], 0.004)
        self.assertFalse(self.job.exists())
        self.assertEqual(json.loads((self.dir / shelves_service.NOTE_NAME).read_text())["asked"], 2)
        # The preparation reads the same file: a line, "no line fits", and the slips' rule.
        from picwise_providers import ai_shelves

        self.assertEqual(ai_shelves.read_answers(self.dir / shelves_service.ANSWERS_NAME)["k-gift"], "")

    def test_the_nights_brake_stops_it_and_the_rest_waits_for_the_next_morning(self) -> None:
        note = self.run_once(budget=0.001)
        self.assertIn("budget", note["stopped"])
        self.assertEqual((note["asked"], note["calls"], note["left"]), (2, 0, 2))
        self.assertTrue(self.job.exists())

    def test_nothing_named_nothing_asked(self) -> None:
        self.job.unlink()
        note = self.run_once()
        self.assertEqual((note["named"], note["asked"], note["calls"]), (0, 0, 0))

    def test_the_unit_runs_as_the_ai_layer_with_its_key_after_the_preparation(self) -> None:
        unit = (ROOT / "deployment" / "server" / "picwise-shelves.service").read_text(encoding="utf-8")
        self.assertIn("User=picwise-assist", unit)
        self.assertIn("EnvironmentFile=-/etc/picwise/assist.env", unit)
        self.assertIn("After=network-online.target picwise-prepare.service", unit)
        self.assertIn("ReadWritePaths=/srv/picwise/assist/shelves", unit)
        self.assertIn("/srv/picwise/venv-ai/bin/python", unit)
        timer = (ROOT / "deployment" / "server" / "picwise-shelves.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 05:20:00 UTC", timer)
        prepare = (ROOT / "deployment" / "server" / "picwise-prepare.service").read_text(encoding="utf-8")
        self.assertIn("Environment=PICWISE_SHELF_JOBS=/srv/picwise/assist/shelves/jobs", prepare)
        self.assertIn("ReadWritePaths=-/srv/picwise/assist/shelves/jobs", prepare)
        deploy = (ROOT / "deployment" / "server" / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn('install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/shelves/jobs"', deploy)
        self.assertIn("systemctl enable --now picwise-shelves.timer", deploy)


if __name__ == "__main__":
    unittest.main()
