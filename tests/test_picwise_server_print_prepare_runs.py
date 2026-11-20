"""The catalogue preparation's runs, printed from the server's journal by a read-only
workflow (`deployment/server/print_prepare_runs.py`, `.github/workflows/prepare-runs.yml`).

Owner, 2026-11-20: «μας ενδιαφέρει γιατί δεν δούλεψε το feed», after two deployments whose
preparation failed with no line saying why. Pinned here: the journal is cut into runs where
systemd starts the unit; each run's lines worth a look and its last lines are printed, at
most `LINES_A_RUN`; and nothing secret reaches the public log: every value of the server's
environment files and each long piece of it (a feed link's key), every link and every long
token, and the server's own names, are masked before a line is printed.

Every value here is invented: `.invalid` links, fictional keys and names.
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment" / "server"))

import print_prepare_runs as runs  # noqa: E402

FEED_KEY = "f00dfeedcafe1234f00dfeedcafe1234"
FEED_LINK = f"https://feeds.example.invalid/datafeed/download/apikey/{FEED_KEY}/fid/1,2,3/format/csv"
ENV_TEXT = f"""# written by the deployment
AWIN_FEED_URL='{FEED_LINK}'
AWIN_API_TOKEN=tok-0123456789ab
PICWISE_FLAG=1
"""

JOURNAL = """2026-11-20T04:17:00+0000 host-a systemd[1]: Starting picwise-prepare.service - PicWise: prepare the catalogue from the feed...
2026-11-20T04:20:00+0000 host-a time[100]: prepare_catalogue: memory after the feed read: peak 9.1 GB so far
2026-11-20T04:42:00+0000 host-a time[100]: prepare_catalogue: peak memory 14574592 KB, 1554.00 s
2026-11-20T04:42:01+0000 host-a systemd[1]: picwise-prepare.service: Deactivated successfully.
2026-11-20T10:04:47+0000 host-a systemd[1]: Starting picwise-prepare.service - PicWise: prepare the catalogue from the feed...
2026-11-20T10:10:00+0000 host-a time[200]: prepare_catalogue: memory after the feed read: peak 9.3 GB so far
2026-11-20T10:30:00+0000 host-a time[200]: urllib.error.URLError: could not read """ + FEED_LINK + """
2026-11-20T10:30:33+0000 host-a systemd[1]: picwise-prepare.service: A process of this unit has been killed by the OOM killer.
2026-11-20T10:30:33+0000 host-a systemd[1]: picwise-prepare.service: Failed with result 'oom-kill'.
2026-11-20T10:30:33+0000 host-a systemd[1]: picwise-prepare.service: Consumed 16min 25.269s CPU time.
"""


def fake_runner(command):
    if command[:3] == ["journalctl", "-u", runs.UNIT]:
        return JOURNAL
    if command[:2] == ["journalctl", "-k"]:
        return (
            "2026-11-20T10:30:32+0000 host-a kernel: python3 invoked oom-killer: gfp_mask=0xcc0\n"
            "2026-11-20T10:30:32+0000 host-a kernel: usb 1-1: new device\n"
        )
    if command[0] == "hostname":
        return {1: "host-a\n", 2: "host-a.example.invalid\n"}.get(len(command), "192.0.2.10 \n")
    if command[0] == "systemctl":
        return "Result=oom-kill\nMemoryMax=19327352832\n"
    return ""


class SecretsTests(unittest.TestCase):
    def test_every_value_and_each_long_piece_of_a_link(self) -> None:
        secrets = runs.secrets_in(ENV_TEXT)
        self.assertIn(FEED_LINK, secrets)
        self.assertIn(FEED_KEY, secrets)
        self.assertIn("tok-0123456789ab", secrets)
        self.assertNotIn("1", secrets)  # too short to mask: it would mask every digit
        self.assertEqual(secrets, sorted(secrets, key=len, reverse=True))

    def test_mask_leaves_no_secret_link_or_token(self) -> None:
        secrets = runs.secrets_in(ENV_TEXT)
        line = f"read {FEED_LINK} key {FEED_KEY} token tok-0123456789ab other https://x.invalid/a " + "a" * 40
        masked = runs.mask(line, secrets)
        for secret in (FEED_LINK, FEED_KEY, "tok-0123456789ab", "https://x.invalid/a", "a" * 40):
            self.assertNotIn(secret, masked)
        self.assertIn("<secret>", masked)
        self.assertIn("<link>", masked)
        self.assertIn("<token>", masked)


class RunsTests(unittest.TestCase):
    def test_the_journal_is_cut_where_systemd_starts_the_unit(self) -> None:
        lines = ["before the window"] + JOURNAL.splitlines()
        cut = runs.split_runs(lines)
        self.assertEqual([len(run) for run in cut], [1, 4, 6])
        self.assertIn("Starting picwise-prepare.service", cut[2][0])

    def test_a_run_says_its_lines_worth_a_look_and_its_last_lines_at_most_a_limit(self) -> None:
        noise = [f"line {number}" for number in range(400)]
        lines = ["prepare_catalogue: memory after the feed read"] + noise + ["Failed with result 'oom-kill'."]
        chosen = runs.lines_of_a_run(lines)
        self.assertEqual(chosen[0], "prepare_catalogue: memory after the feed read")
        self.assertEqual(chosen[-1], "Failed with result 'oom-kill'.")
        self.assertIn("line 399", chosen)
        self.assertNotIn("line 10", chosen)
        many = [f"Error {number}" for number in range(500)]
        self.assertLessEqual(len(runs.lines_of_a_run(many)), runs.LINES_A_RUN + 1)


class MainTests(unittest.TestCase):
    def test_the_report_names_each_run_and_prints_nothing_secret(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = runs.main(["--since=-30h"], runner=fake_runner, secrets=runs.secrets_in(ENV_TEXT))
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("2 runs since -30h", text)
        self.assertIn("Failed with result 'oom-kill'.", text)
        self.assertIn("prepare_catalogue: peak memory 14574592 KB", text)
        self.assertIn("invoked oom-killer", text)
        self.assertNotIn("usb 1-1", text)
        for secret in (FEED_LINK, FEED_KEY, "host-a", "192.0.2.10", "feeds.example.invalid"):
            self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
