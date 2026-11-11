"""The daily session is told to look whether the night's preparation worked (the audit's
fixes, 2026-11-11, `docs/PICWISE_AUDIT_FIXES.md` 4.A.3).

The site answers from the last prepared file until it is 30 hours old, then shows no
product, and nothing told anyone. `docs/PICWISE_DAILY_WORK.md` now has the daily session
read `/prepared.json` with `curl` and put first in its report a failed night, a file over
30 hours old, or a shop whose feed shrank or vanished. Pinned here: that the file says
so, and that what it says agrees with the code it describes, so a change to the code
that would make the file wrong fails here:

- the age limit (`prepared_catalogue.DEFAULT_MAX_AGE_HOURS`) and its variable;
- a failed night's note: `"prepared": false`, a `reason`, no `prepared_at`
  (`tools/prepare_catalogue.py --keep-going`, as the server runs it);
- "fewer than half" (`SHRUNK_SHARE`) and the `shrunk` and `gone` lists of `intake_change`;
- the night's hour (`picwise-prepare.timer`).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import prepared_catalogue  # noqa: E402

DAILY = ROOT / "docs" / "PICWISE_DAILY_WORK.md"


def _load_tool():
    spec = importlib.util.spec_from_file_location("prepare_catalogue_night_check", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _look_step() -> str:
    """Step 2 of "How a day goes", where the session looks before it works."""
    text = " ".join(DAILY.read_text(encoding="utf-8").split())
    found = re.search(r"2\. \*\*Look\.\*\*(.*?)3\. \*\*Work\.\*\*", text)
    if found is None:
        raise AssertionError("no Look step in the daily work's file")
    return found.group(1)


class DailyNightCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.step = _look_step()

    def test_the_session_reads_the_note_with_curl_and_reports_it_first(self) -> None:
        self.assertIn("https://picwise.subby.cloud/prepared.json", self.step)
        self.assertIn("with `curl`", self.step)
        self.assertIn("The report puts first", self.step)
        # No email is built: it is the owner's to choose.
        self.assertIn("is not built: it needs the owner's choice of address and sender", self.step)

    def test_the_age_limit_it_names_is_the_codes(self) -> None:
        self.assertEqual(prepared_catalogue.DEFAULT_MAX_AGE_HOURS, 30.0)
        self.assertEqual(prepared_catalogue.PREPARED_MAX_AGE_ENV, "PICWISE_PREPARED_MAX_AGE_HOURS")
        self.assertIn("30 hours", self.step)
        self.assertIn("`PICWISE_PREPARED_MAX_AGE_HOURS`", self.step)

    def test_a_failed_nights_note_is_as_the_file_says(self) -> None:
        self.assertIn('`"prepared"` not `true`', self.step)
        self.assertIn("carries no `prepared_at`", self.step)
        env = {key: value for key, value in os.environ.items() if not key.startswith("AWIN_")}
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "none.csv"
            env["AWIN_FEED_FILE"] = str(missing)
            subprocess.run(
                [sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"), "--keep-going",
                 "--out", str(Path(folder) / "catalogue.json.gz"), "--static-dir", folder],
                env=env, capture_output=True, check=True,
            )
            note = json.loads((Path(folder) / "prepared.json").read_text(encoding="utf-8"))
        self.assertIs(note["prepared"], False)
        self.assertTrue(note.get("reason"))
        self.assertNotIn("prepared_at", note)
        self.assertIn("written_at", note)

    def test_the_shrunk_and_gone_shops_it_names_are_the_notes(self) -> None:
        tool = _load_tool()
        self.assertEqual(tool.SHRUNK_SHARE, 0.5)
        self.assertIn("fewer than half", self.step)
        self.assertIn("`shrunk`", self.step)
        self.assertIn("`gone`", self.step)
        before = {"prepared": True, "intake": {"shops": [
            {"shop": "Big Shop", "rows": 1000}, {"shop": "Lost Shop", "rows": 300}]}}
        change = tool._intake_change(before, {"shops": [{"shop": "Big Shop", "rows": 100}]})
        self.assertEqual([entry["shop"] for entry in change["shrunk"]], ["Big Shop"])
        self.assertEqual([entry["shop"] for entry in change["gone"]], ["Lost Shop"])

    def test_the_nights_hour_it_names_is_the_timers(self) -> None:
        timer = (ROOT / "deployment" / "server" / "picwise-prepare.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 04:17:00 UTC", timer)
        self.assertIn("04:17 UTC", self.step)


if __name__ == "__main__":
    unittest.main()
