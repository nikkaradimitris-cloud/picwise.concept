"""The server's daily health check, printed for the daily work (owner, 2026-11-16: «Έλεγχος
προσφορών, ταχύτητας και πόρων», «Εβδομαδιαία σύνοψη Κυριακής»).

`deployment/server/print_health.py` and `deployment/server/count_searches.py`, sent to the
server by `.github/workflows/server-health.yml`. Pinned here: each limit is told when passed
and only then; a day within every limit says so; the offers' failure is told by the fetch's
own (redacted) line and its service's result; the visitors' searches are counted, and no
word of theirs is ever printed, nor is any search's page asked anywhere but the server's
own site; the workflow only reads, pins the server's key, masks its names and removes the
key.

Every file is local test data.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "deployment" / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import count_searches  # noqa: E402
import print_health  # noqa: E402

NOW = datetime(2026, 11, 22, 8, 7, tzinfo=timezone.utc)
PREPARE_LINE = "prepare_catalogue: peak memory 9856000 KB, 801.40 s"


def _runner(*, web="active", offers="success", photos="success", prepare=PREPARE_LINE, offers_said=None):
    def run(command):
        if command[:2] == ["systemctl", "is-active"]:
            return f"{web}\n"
        if command[:2] == ["systemctl", "show"] and "ActiveEnterTimestamp" in command:
            return "Sun 2026-11-15 10:00:00 UTC\n"
        if command[:2] == ["systemctl", "show"]:
            return {"picwise-offers.service": offers, "picwise-photos.service": photos}.get(command[2], "") + "\n"
        if command[0] == "journalctl" and "picwise-prepare.service" in command:
            return f"Starting...\n{prepare}\n" if prepare else "Starting...\n"
        if command[0] == "journalctl" and "picwise-offers.service" in command:
            return "\n".join(offers_said or ["offers: 12 live from 3 of the 78 shops in the feed"]) + "\n"
        return ""

    return run


class HealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.note = self.folder / "prepared.json"
        self.offers = self.folder / "offers.json"
        self.photos = self.folder / "gone.json"
        self.spend = self.folder / "spend"
        self.spend.mkdir()
        self.write(self.note, {
            "prepared": True, "prepared_at": (NOW - timedelta(hours=3, minutes=42)).isoformat(),
            "products": 254756, "shops": 78,
            "intake_change": {"compared_with": "2026-11-21T04:25:00+00:00", "shrunk": [], "gone": [], "new": []},
            "memory": {"nights": 11, "new_tonight": 472, "price_changed_tonight": 20, "gone_since": 489},
            "price_notes": {"down": 14, "up": 9, "same": 250000, "watch": 2220},
        })
        self.write(self.offers, {
            "fetched_at": (NOW - timedelta(hours=3)).isoformat(), "shops_in_feed": 78,
            "shops": {"1": {"name": "Fixture Shop", "offers": [{"id": 1}, {"id": 2}]}, "2": {"name": "Other", "offers": [{"id": 3}]}},
        })
        self.write(self.photos, {"gone": ["a", "b"], "photos": 240000, "checked_at": (NOW - timedelta(hours=3, minutes=20)).isoformat()})
        self.write(self.spend / "2026-11-21.json", {"spent_usd": 0.31, "calls": 40})
        patches = [
            mock.patch.object(print_health, "PREPARED_NOTE", self.note),
            mock.patch.object(print_health, "OFFERS_FILE", self.offers),
            mock.patch.object(print_health, "PHOTOS_FILE", self.photos),
            mock.patch.object(print_health, "SPEND_DIR", self.spend),
            mock.patch.object(print_health, "site_memory_gb", lambda *a, **k: 4.0),
            mock.patch.object(print_health, "memory_available_gb", lambda *a, **k: (23.4, 15.2)),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    @staticmethod
    def write(path: Path, data: object) -> None:
        path.write_text(json.dumps(data), encoding="utf-8")

    def printed(self, **runner) -> list[str]:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(print_health.main(now=NOW, runner=_runner(**runner)), 0)
        return out.getvalue().splitlines()

    def over(self, lines: list[str]) -> list[str]:
        return [line for line in lines if line.startswith("over the limit: ")]

    def test_a_good_day_is_within_every_limit_and_says_what_it_read(self) -> None:
        lines = self.printed()
        self.assertEqual(lines[-1], "within every limit")
        self.assertEqual(self.over(lines), [])
        text = "\n".join(lines)
        self.assertIn("prepared: 254756 products, 78 shops, prepared 3.7 h ago", text)
        self.assertIn("preparation, the last in 26 h: peak memory 9.4 GB, 13.4 minutes", text)
        self.assertIn("memory at night, the site and the preparation together: 13.4 GB", text)
        self.assertIn("offers: 3 live from 2 of the 78 shops in the feed, fetched 3.0 h ago; the last fetch: success", text)
        self.assertIn("price notes: 14 down, 9 up, 250000 same, 2220 watched", text)
        self.assertIn("catalogue memory: 11 nights, 472 new tonight, 20 prices changed tonight, 489 gone since", text)
        self.assertIn("shops since the preparation before: gone 0; shrunk 0; new 0", text)
        self.assertIn("AI spend yesterday: $0.31 in 40 calls", text)

    def test_offers_not_fetched_for_days_and_a_failed_fetch_are_told(self) -> None:
        self.write(self.offers, {"fetched_at": "2026-11-03T05:05:10+00:00", "shops_in_feed": 78, "shops": {}})
        lines = self.printed(offers="exit-code", offers_said=[
            "offers: not fetched (HTTP Error 401: Unauthorized); the last file kept",
        ])
        over = self.over(lines)
        self.assertIn("over the limit: the offers were fetched 19.1 days ago", over)
        self.assertIn("over the limit: the last fetch of the offers ended: exit-code", over)
        self.assertIn("offers, the last fetch said: offers: not fetched (HTTP Error 401: Unauthorized); the last file kept", lines)

    def test_only_the_fetch_s_own_lines_are_printed(self) -> None:
        # A traceback is the fetch's too, but only its own lines are redacted: never printed.
        lines = self.printed(offers_said=["Traceback (most recent call last):", "  url https://example.invalid/?token=x"])
        self.assertFalse([line for line in lines if "example.invalid" in line or "Traceback" in line])

    def test_a_failed_or_old_preparation_and_a_lost_shop_are_told(self) -> None:
        self.write(self.note, {"prepared": False, "reason": "feed download failed", "written_at": NOW.isoformat(),
                               "intake_change": {"compared_with": "x", "gone": [{"shop": "Fixture Shop", "rows_before": 5000, "rows": 0}],
                                                 "shrunk": [{"shop": "Other Shop", "rows_before": 4000, "rows": 900}], "new": ["New Shop"]}})
        lines = self.printed()
        over = self.over(lines)
        self.assertIn("over the limit: the night's preparation failed (feed download failed)", over)
        self.assertIn("over the limit: a shop was lost or shrank to less than half", over)
        self.assertIn(
            "shops since the preparation before: gone 1 (Fixture Shop: 5000 -> 0 rows); "
            "shrunk 1 (Other Shop: 4000 -> 900 rows); new 1 (New Shop)",
            lines,
        )
        self.write(self.note, {"prepared": True, "prepared_at": (NOW - timedelta(hours=31)).isoformat(), "products": 1, "shops": 1})
        self.assertIn("over the limit: the catalogue was prepared 31.0 h ago", self.over(self.printed()))

    def test_memory_disk_and_length_limits(self) -> None:
        with mock.patch.object(print_health, "site_memory_gb", lambda *a, **k: 9.5):
            over = self.over(self.printed(prepare="prepare_catalogue: peak memory 10485760 KB, 2400.00 s"))
        self.assertIn("over the limit: the site and the preparation together need 19.5 GB", over)
        self.assertIn("over the limit: the preparation took 40 minutes", over)
        with mock.patch.object(print_health, "memory_available_gb", lambda *a, **k: (23.4, 3.1)):
            self.assertIn("over the limit: only 3.1 GB of memory available", self.over(self.printed()))
        Usage = type("Usage", (), {"free": 12 * 1024**3, "total": 200 * 1024**3})
        with mock.patch.object(print_health.shutil, "disk_usage", lambda path: Usage()):
            self.assertIn("over the limit: only 12 GB of disk free", self.over(self.printed()))

    def test_a_missing_preparation_line_is_said_not_guessed(self) -> None:
        lines = self.printed(prepare="")
        self.assertIn("preparation, the last in 26 h: no line of its memory", lines)
        self.assertEqual(lines[-1], "within every limit")

    def test_the_site_down_photos_late_and_the_ai_cap_are_told(self) -> None:
        self.write(self.photos, {"gone": [], "photos": 1, "checked_at": (NOW - timedelta(hours=40)).isoformat()})
        self.write(self.spend / "2026-11-21.json", {"spent_usd": 1.0, "calls": 300})
        over = self.over(self.printed(web="failed"))
        self.assertIn("over the limit: the site's service is failed", over)
        self.assertIn("over the limit: the photos were checked 40.0 h ago", over)
        self.assertIn("over the limit: the AI spent its whole day's cap yesterday ($1.00)", over)


class CountSearchesTests(unittest.TestCase):
    WORDS = ["Velvet Sofa", "velvet  sofa", "iphone 15 case", "my private words 07700 900123", "kettle"]

    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        today = NOW.date()

        def day(back: int, searches: list[str]) -> None:
            lines = [json.dumps({"q": words}) for words in searches]
            (self.folder / f"{(today - timedelta(days=back)).isoformat()}.jsonl").write_text(
                "\n".join(lines + ["not json", json.dumps({"x": 1})]) + "\n", encoding="utf-8"
            )

        day(0, ["today, not counted yet"])
        day(1, self.WORDS[:3])
        day(3, self.WORDS[3:])
        day(7, ["Velvet sofa"])
        day(8, ["eight days ago, not counted"])

    def printed(self, argv: list[str], fetch=None) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            kwargs = {"fetch": fetch} if fetch else {}
            self.assertEqual(count_searches.main(["--dir", str(self.folder), *argv], now=NOW, **kwargs), 0)
        return out.getvalue()

    def assert_no_words(self, text: str) -> None:
        for words in self.WORDS + ["today", "eight days", "iphone", "07700", "velvet", "kettle"]:
            self.assertNotIn(words.casefold(), text.casefold())

    def test_the_last_seven_whole_days_are_counted_by_their_words_alone(self) -> None:
        text = self.printed([])
        self.assertEqual(
            text,
            "searches by visitors: 3 yesterday (2026-11-21); 6 in the 7 days 2026-11-15 to 2026-11-21, "
            "4 different, the most searched one 3 times\n",
        )
        self.assert_no_words(text)

    def test_the_check_asks_the_server_s_own_site_and_prints_numbers_only(self) -> None:
        asked = []

        def fetch(words):
            asked.append(words)
            if words == "kettle":
                return None
            return "<main></main>" if words.startswith("my private") else '<article class="pw-card">'

        text = self.printed(["--check"], fetch=fetch)
        self.assertIn(
            "searches that found no product, asked again on the server: 1 of the 4 different "
            "(1 of the 6 searches); not checked: 1\n",
            text,
        )
        self.assertEqual(asked[0], "Velvet sofa")  # the most searched first, as first typed in the 7 days
        self.assertEqual(len(asked), 4)
        self.assert_no_words(text)

    def test_the_check_stops_at_its_limits(self) -> None:
        counted = Counter({"a": 5, "b": 3, "c": 1})
        firsts = {"a": "a", "b": "b", "c": "c"}
        self.assertEqual(count_searches.check(counted, firsts, lambda w: "", max_checked=2), (2, 8, 1))
        ticks = iter([0.0, 0.0, 500.0, 500.0])
        self.assertEqual(count_searches.check(counted, firsts, lambda w: "", clock=lambda: next(ticks)), (1, 5, 2))

    def test_no_folder_and_no_searches(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            count_searches.main(["--dir", str(self.folder / "none"), "--check"], now=NOW)
        self.assertEqual(out.getvalue(), "searches by visitors: none kept (the server has no folder for them)\n")
        empty = Path(tempfile.mkdtemp())
        out = io.StringIO()
        with redirect_stdout(out):
            count_searches.main(["--dir", str(empty), "--check"], now=NOW, fetch=lambda w: self.fail("asked"))
        self.assertIn("searches that found no product: none to check", out.getvalue())

    def test_the_page_is_asked_of_the_server_alone(self) -> None:
        self.assertEqual(count_searches.SITE, "http://127.0.0.1:8016")
        seen = {}

        class Opener:
            def open(self, request, timeout):
                seen["url"], seen["host"], seen["timeout"] = request.full_url, request.get_header("Host"), timeout
                raise OSError("no site here")

        with mock.patch.object(count_searches.urllib.request, "build_opener", lambda *handlers: Opener()):
            self.assertIsNone(count_searches.fetch_page("velvet sofa"))
        self.assertEqual(seen["url"], "http://127.0.0.1:8016/search?q=velvet+sofa")
        self.assertEqual(seen["host"], "picwise.subby.cloud")

    def test_the_script_runs_from_its_standard_input_as_the_workflow_sends_it(self) -> None:
        done = subprocess.run(
            [sys.executable, "-", "--dir", str(self.folder)],
            input=(SERVER / "count_searches.py").read_text(encoding="utf-8"),
            capture_output=True, text=True, check=True, cwd=tempfile.mkdtemp(),
        )
        self.assertTrue(done.stdout.startswith("searches by visitors: "))
        done = subprocess.run(
            [sys.executable, "-"], input=(SERVER / "print_health.py").read_text(encoding="utf-8"),
            capture_output=True, text=True, check=True, cwd=tempfile.mkdtemp(),
        )
        self.assertTrue(done.stdout.splitlines()[-1].startswith(("within every limit", "over the limit: ")))


class WorkflowTests(unittest.TestCase):
    def test_the_workflow_only_reads_pins_the_server_and_removes_the_key(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "server-health.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("python3 .github/scripts/host_key_pin.py", workflow)
        self.assertIn("StrictHostKeyChecking yes", workflow)
        self.assertIn('echo "::add-mask::$name"', workflow)
        self.assertIn("ssh picwise 'sudo python3 -' < deployment/server/print_health.py", workflow)
        self.assertIn('< deployment/server/count_searches.py', workflow)
        self.assertIn("if: always()\n        run: rm -f ~/.ssh/deploy_key ~/.ssh/config", workflow)
        # Nothing that changes the server, and no visitor's search read out.
        for word in ("systemctl restart", "systemctl start", "systemctl stop", "rm -rf", "shared/searches", "deploy.sh"):
            self.assertNotIn(word, workflow)


if __name__ == "__main__":
    unittest.main()
