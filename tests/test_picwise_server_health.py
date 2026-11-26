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


class _AServer:
    """The notes a server keeps, of the test's own, and the health run printed."""

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
            mock.patch.object(print_health, "CHECKS_NOTE", self.folder / "checks-note.json"),
            mock.patch.object(print_health, "SHELVES_NOTE", self.folder / "shelves-night.json"),
            mock.patch.object(print_health, "ITSELF_NOTE", self.folder / "itself-night.json"),
            mock.patch.object(print_health, "METER_NOTE", self.folder / "meter-day.json"),
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


class HealthTests(_AServer, unittest.TestCase):
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

    def test_the_checks_not_running_yet_change_nothing(self) -> None:
        lines = self.printed()
        self.assertIn("checks: no night recorded yet", lines)
        self.assertEqual(lines[-1], "within every limit")

    def test_the_checks_night_its_shops_that_cannot_be_checked_and_its_limits(self) -> None:
        note = {"night": "2026-11-22", "shops_asked": 151, "decided": 3120, "passed": 3001,
                "failed": {"gone": 101, "moved": 18}, "cut_tonight": 119, "back_tonight": 4, "held": {},
                "braked_shops": [], "night_brake": False, "stopped": False,
                "cannot_be_checked": {"Plusshop UK": ["refuses the bot", 1], "Aosom UK": ["robots.txt refused", 3]},
                "awin": {"newly_out": [["usmile", "Awin: in no list"]], "waits": False, "products": 0,
                         "would_be_out_if_proposed": [["Paused Shop", "Awin: suspended", 28]]},
                "old_feed_would_wait": {"products": 412, "shops": 3, "most": [["Old Feed Shop", 300], ["Another", 100]]}}
        self.write(self.folder / "checks-note.json", note)
        lines = self.printed()
        self.assertEqual(lines[-1], "within every limit")
        # Named, not out: the Proposed part of the rule waits for the owner's yes.
        self.assertIn("checks, not out while the Proposed rule waits for the owner's yes (rules 5.6.3): "
                      "Paused Shop (suspended, 28 products)", lines)
        self.assertIn("checks, the Proposed rule of a feed over 7 days old would not show 412 products of 3 shops "
                      "(rules 5.6.4; waits for the owner's yes): Old Feed Shop 300, Another 100", lines)
        self.assertIn("checks, the night of 2026-11-22: 151 shops asked; the last round: unknown", lines)
        self.assertIn("checks: decided 3,120, passed 3,001, failed 119 (gone 101, moved 18); cut tonight 119, back 4", lines)
        self.assertIn("checks, cannot be checked: Aosom UK: robots.txt refused, day 3; leaves tomorrow", lines)
        self.assertIn("checks, cannot be checked: Plusshop UK: refuses the bot, day 1; leaves on day 4", lines)
        self.assertIn("checks, out by Awin's reading tonight: usmile (Awin: in no list)", lines)
        # A brake that held, the cutting stopped, an Awin reading that waits, an old night: limits.
        self.write(self.folder / "checks-note.json", {**note, "night": "2026-11-19", "braked_shops": ["Kettles"],
                                                      "night_brake": True, "stopped": True,
                                                      "awin": {"newly_out": [], "waits": True, "products": 20511}})
        over = self.over(self.printed())
        self.assertIn("over the limit: a shop's brake held the checks' cuts: Kettles (rules 7.2)", over)
        self.assertIn("over the limit: the whole night's brake held: nothing new cut (rules 7.4)", over)
        self.assertIn("over the limit: the checks' cutting stopped until the owner's word (rules 7.4)", over)
        self.assertIn("over the limit: a reading of Awin that would put many shops out waits for the owner's word (rules 5.6.3)", over)
        self.assertIn("over the limit: the checks recorded no night since 2026-11-19", over)
        # The night of the day is due from 03:30 UTC: at 08:07 yesterday's is a night missed
        # (24/11: the round ended by an error at 03:05, read as within every limit).
        self.write(self.folder / "checks-note.json", {**note, "night": "2026-11-21"})
        self.assertIn("over the limit: the checks recorded no night since 2026-11-21", self.over(self.printed()))
        early = io.StringIO()
        with redirect_stdout(early):
            print_health.main(now=NOW.replace(hour=2), runner=_runner())
        self.assertNotIn("over the limit: the checks recorded no night since 2026-11-21", early.getvalue())
        self.write(self.folder / "checks-note.json", {"night": "2026-11-22", "shops_asked": 151, "ours": True})
        self.assertIn("over the limit: the checks' round was ours: fewer than half of the shops answered (rules 7.1)",
                      self.over(self.printed()))

    def test_how_many_of_a_shops_products_pass_is_printed_and_a_failure_passes_a_limit(self) -> None:
        # The checks' rules 19.7.3: per shop over the most, what it kept by step.
        self.write(self.folder / "checks-note.json", {"night": "2026-11-25", "shops_asked": 135, "decided": 10,
                                                      "passed": 10, "failed": {},
                                                      "shop_rule": {"on": True, "pass_nights": 3,
                                                                    "most_asked_of_a_shop": 20000, "processes": 4,
                                                                    "shops_at_once": 135}})
        note = json.loads(self.note.read_text())
        shops = {"applied": True, "limit": 20000, "capped_shops": 1, "cut": 82278, "candidates": 0,
                 "shops": [{"shop": "Big Shop", "products": 102278, "kept": 20000, "waiting_at_the_gate": 12,
                            "kept_by_step": {"thin kinds": 840, "cheapest kept": 1438, "with a kind": 17722,
                                             "the rest": 0, "a cheaper shop's": 0}}]}
        self.write(self.note, {**note, "checks": {"applied": True, "shops_out": {}, "cut": 0, "shop_cap": shops}})
        lines = self.printed()
        self.assertIn("checks, how many of a shop's products pass: on; a pass counts for 3 nights; at most 20,000 asked "
                      "of a shop; 135 shops at once, pages read on 4 processes", lines)
        self.assertIn("checks, how many of a shop's products pass (at most 20,000): 1 shops over it, 82,278 products "
                      "left out, candidates 0", lines)
        self.assertIn("checks, Big Shop: 20,000 of 102,278 (cheapest kept 1,438, thin kinds 840, with a kind 17,722); "
                      "waiting at the gate 12", lines)
        self.assertEqual(lines[-1], "within every limit")
        self.write(self.note, {**note, "checks": {"applied": True, "shops_out": {}, "cut": 0,
                                                  "shop_cap": {"applied": False, "error": "KeyError at shop_cap.py:1"}}})
        self.assertIn("over the limit: how many of a shop's products pass was not worked out last night: every shop's "
                      "products went on to the category cap (KeyError at shop_cap.py:1)", self.over(self.printed()))

    def test_with_bots_on_each_ones_day_restarts_and_memory_are_read(self) -> None:
        # The checks' rules 22 and 23 (owner, 26/11: «8 bot αντί για 4», «Όριο μνήμης: 1,8 GB για κάθε
        # bot»): each bot switched on, its last day, systemd's restarts of it, its memory now and its
        # peak; the bots together against their slice; a bot that ended badly, was started again or
        # came near its limit passes a limit. With every one on the night is the recording's.
        switch = self.folder / "checks_clones.json"
        self.write(switch, {"clones": 8, "bots": list(range(1, 9))})
        rule = {"on": True, "pass_nights": 1, "most_asked_of_a_shop": 20000, "most_shown_of_a_shop": 10000,
                "processes": 8, "shops_at_once": 116, "round_hours": 21.5, "whole_round": True, "asked_whole": 108,
                "not_whole": [], "bots": [{"bot": 3, "shops": 14, "hours": 21.5, "starts": 2, "peak_mb": 1720,
                                           "read_peak_mb": 640}]}
        self.write(self.folder / "checks-note.json", {"night": "2026-11-25", "shops_asked": 135, "decided": 10,
                                                      "passed": 10, "failed": {}, "shop_rule": rule})
        base = _runner()
        gb = 1024 ** 3
        shown = {"picwise-checks@3.service": f"Result=oom-kill\nNRestarts=1\nMemoryCurrent={int(0.4 * gb)}\n"
                                             f"MemoryPeak={int(1.75 * gb)}\nActiveState=active\n",
                 "picwisebots.slice": f"MemoryCurrent={int(3.1 * gb)}\nMemoryPeak={int(6.2 * gb)}\n"}

        def run(command):
            if command[:2] == ["systemctl", "show"] and "-p" in command and "," in command[-1]:
                return shown.get(command[2], f"Result=success\nNRestarts=0\nMemoryCurrent={int(0.3 * gb)}\n"
                                             f"MemoryPeak={int(0.9 * gb)}\nActiveState=active\n")
            if command[:2] == ["systemctl", "show"] and "Result" in command:
                return {"picwise-checks-record.service": "success"}.get(command[2], "success") + "\n"
            return base(command)

        out = io.StringIO()
        with mock.patch.object(print_health, "CLONES_SWITCH", switch), redirect_stdout(out):
            self.assertEqual(print_health.main(now=NOW, runner=run), 0)
        lines = out.getvalue().splitlines()
        self.assertIn("checks, the bots: 8 of 8 on (1, 2, 3, 4, 5, 6, 7, 8); the night recorded from their days", lines)
        self.assertIn("checks, bot 1: active, its last day: success; started again by systemd 0 times; memory 0.30 GB, "
                      "its peak 0.90 GB of 1.8", lines)
        self.assertIn("checks, bot 3: active, its last day: oom-kill; started again by systemd 1 times; memory 0.40 GB, "
                      "its peak 1.75 GB of 1.8", lines)
        self.assertIn("checks, the bots together: memory 3.10 GB, their peak 6.20 GB of 11", lines)
        self.assertIn("checks, the night's day of bot 3: 14 shops, 21.5 hours, started 2 times, peak 1,720 MB "
                      "(its reading 640 MB)", lines)
        over = self.over(lines)
        self.assertIn("over the limit: the checks' bot 3 ended: oom-kill", over)
        self.assertIn("over the limit: the checks' bot 3 was started again 1 times (its memory's limit?)", over)
        self.assertIn("over the limit: the checks' bot 3 came near its memory's limit (1.75 GB of 1.8)", over)
        self.assertFalse(any("bot 1" in line for line in over))
        self.assertTrue(any(line.startswith("checks, the night of 2026-11-25") and line.endswith("the last round: success")
                            for line in lines), lines)
        self.assertTrue(any("at most 20,000 asked of a shop; at most 10,000 shown of a shop" in line for line in lines))
        stable = next(line for line in lines if line.startswith("checks, the stable day of 2026-11-25"))
        self.assertIn("NO;", stable)
        self.assertIn("no bot started again or near its memory's limit (not: bot 3): NO", stable)
        # None on (or no switch at all): the bot alone, as before; no bot named.
        self.write(switch, {"clones": 8, "bots": []})
        with mock.patch.object(print_health, "CLONES_SWITCH", switch):
            self.assertFalse(any(line.startswith("checks, bot") or line.startswith("checks, the bots") for line in self.printed()))

    def test_the_stable_day_is_said_under_the_rule_of_the_day(self) -> None:
        # The checks' rules 23.6: the round all day, the night on time, the server up through the
        # round, every shop asked whole but those that cannot be checked, no bot in trouble, the
        # failures near a usual day's, no shop newly unable to be checked.
        rule = {"on": True, "pass_nights": 1, "most_asked_of_a_shop": 20000, "round_hours": 21.5, "whole_round": True,
                "asked_whole": 100, "not_whole": ["Slow Shop"]}
        note = {"night": NOW.date().isoformat(), "shops_asked": 105, "decided": 1000, "passed": 990,
                "failed": {"gone": 10}, "shop_rule": rule, "cannot_be_checked": {"Walled Shop": ["refused", 1]}}
        self.write(self.folder / "checks-note.json", note)
        uptime = self.folder / "uptime"
        uptime.write_text(f"{3 * 86400:.2f} 100.00\n")
        with mock.patch.object(print_health, "UPTIME", uptime):
            lines = self.printed()
        stable = next(line for line in lines if line.startswith(f"checks, the stable day of {NOW.date()}"))
        self.assertIn("the round asked all day: yes", stable)
        self.assertIn("the server up all the round: yes", stable)
        self.assertIn("every shop asked whole but those that cannot be checked (not: Slow Shop): NO", stable)
        self.assertIn("the failures 1.0% of 1,000 decided (usual 1.2%): yes", stable)
        self.assertIn("no shop newly unable to be checked (new: Walled Shop): NO", stable)
        self.assertTrue(stable.startswith(f"checks, the stable day of {NOW.date()} (rules 23.6): NO;"))
        # Everything right, and the server up since before the round: YES.
        note.update({"cannot_be_checked": {"Walled Shop": ["refused", 2]}, "shop_rule": {**rule, "not_whole": []}})
        self.write(self.folder / "checks-note.json", note)
        with mock.patch.object(print_health, "UPTIME", uptime):
            stable = next(line for line in self.printed() if line.startswith("checks, the stable day"))
        self.assertTrue(stable.startswith(f"checks, the stable day of {NOW.date()} (rules 23.6): YES;"), stable)
        # Started again during the round: not a stable day.
        uptime.write_text("3600.00 10.00\n")
        with mock.patch.object(print_health, "UPTIME", uptime):
            stable = next(line for line in self.printed() if line.startswith("checks, the stable day"))
        self.assertIn("the server up all the round", stable)
        # Off the rule of the day, nothing said.
        self.write(self.folder / "checks-note.json", {**note, "shop_rule": {"on": True, "pass_nights": 3}})
        self.assertFalse(any(line.startswith("checks, the stable day") for line in self.printed()))

    def test_a_pass_counts_for_the_day_and_a_round_not_all_day_passes_a_limit(self) -> None:
        # The checks' rules 21 (owner, 25/11): a pass counts for the day it was made, three nights
        # while a shop is not asked whole; a round that did not ask all day is said and passes a limit.
        rule = {"on": True, "pass_nights": 1, "most_asked_of_a_shop": 20000, "processes": 4, "shops_at_once": 135,
                "round_hours": 9.5, "whole_round": False, "asked_whole": 0, "not_whole": ["Kettles"]}
        self.write(self.folder / "checks-note.json", {"night": "2026-11-25", "shops_asked": 135, "decided": 10,
                                                      "passed": 10, "failed": {}, "shop_rule": rule})
        lines = self.printed()
        self.assertIn("checks, how many of a shop's products pass: on; a pass counts for the day it was made, 3 nights "
                      "while its shop is not asked whole; at most 20,000 asked of a shop; 135 shops at once, pages "
                      "read on 4 processes", lines)
        self.assertIn("checks, the round asked 9.5 hours (NOT all day: shops not asked all their products keep them); "
                      "shops asked whole 0; not whole: Kettles", lines)
        self.assertIn("over the limit: the checks' round did not ask all day (rules 21): its products stay as they were",
                      self.over(lines))
        self.write(self.folder / "checks-note.json", {"night": "2026-11-25", "shops_asked": 135, "decided": 10,
                                                      "passed": 10, "failed": {},
                                                      "shop_rule": {**rule, "round_hours": 21.4, "whole_round": True,
                                                                    "asked_whole": 135, "not_whole": []}})
        lines = self.printed()
        self.assertIn("checks, the round asked 21.4 hours (all day); shops asked whole 135", lines)
        self.assertNotIn("over the limit: the checks' round did not ask all day (rules 21): its products stay as they were",
                         self.over(lines))

    def test_a_night_the_caps_gate_did_not_stand_passes_a_limit(self) -> None:
        self.write(self.folder / "checks-note.json", {"night": "2026-11-22", "shops_asked": 151, "decided": 10,
                                                      "passed": 10, "failed": {}})
        note = json.loads(self.note.read_text())
        why = "the night before's pool could not be read: only the products not checked are held back"
        self.write(self.note, {**note, "checks": {"applied": True, "shops_out": {}, "cut": 12, "gate_off": why}})
        lines = self.printed()
        self.assertIn(f"checks, the cap's gate did not stand last night: {why}", lines)
        self.assertIn(f"over the limit: the checks' gate did not stand last night: new products entered unchecked ({why})",
                      self.over(lines))

    def test_the_category_its_brake_and_the_ais_night_are_told(self) -> None:
        self.write(self.folder / "checks-note.json", {"night": "2026-11-22", "shops_asked": 151, "decided": 10,
                                                      "passed": 10, "failed": {}})
        note = json.loads(self.note.read_text())
        self.write(self.note, {**note, "checks": {"applied": True, "shops_out": {}, "cut": 4100,
                                                  "not_shown_until_checked": 5200,
                                                  "not_shown_until_checked_by_reason": {"never checked": 5200},
                                                  "held_by_the_gate": 61000, "candidates": 6500,
                                                  "category": {"answers": True, "no_category": 4093,
                                                               "held_by_its_brake": False, "not_asked_yet": 812}}})
        self.write(self.folder / "shelves-night.json", {"night": "2026-11-22", "asked": 812, "answered": 790,
                                                        "no_line_fits": 21, "refused": 0, "left": 22,
                                                        "cost_usd": 0.06, "stopped": ""})
        lines = self.printed()
        self.assertEqual(lines[-1], "within every limit")
        self.assertIn("checks, the category: 4,093 products with none, 812 not asked yet", lines)
        # The products never asked by their shop's day 4 (rules 9.3): not shown, waiting at the cap's gate.
        self.assertIn("checks, not shown until checked: 5,200 products (never checked 5,200); at the cap's gate 61,000, "
                      "named for the bot's next night 6,500", lines)
        self.assertIn("checks, the AI's categories on 2026-11-22: 812 asked, 790 answered (21 no line fits), "
                      "0 refused, 22 left; $0.06", lines)
        self.write(self.note, {**note, "checks": {"applied": True, "category": {"no_category": 90000,
                                                                               "held_by_its_brake": True}}})
        self.write(self.folder / "shelves-night.json", {"night": "2026-11-22", "asked": 9000, "cost_usd": 9.98,
                                                        "stopped": "the budget of $10.00 would be passed"})
        over = self.over(self.printed())
        self.assertIn("over the limit: the category's brake held: too many products with none in one night, none cut "
                      "(rules 5.5, 7.4)", over)
        self.assertIn("over the limit: the AI's categories stopped at the night's brake of $10 "
                      "(the budget of $10.00 would be passed)", over)

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
        with mock.patch.object(print_health, "site_memory_gb", lambda *a, **k: 10.5):
            over = self.over(self.printed(prepare="prepare_catalogue: peak memory 10485760 KB, 2400.00 s"))
        self.assertIn("over the limit: the site and the preparation together need 20.5 GB", over)
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


class KindItselfHealthTests(_AServer, unittest.TestCase):
    """The question "is it the kind itself" (`docs/PICWISE_KIND_ITSELF_RULES.md`, 7 and 10)."""

    def _note(self, itself: dict) -> None:
        note = json.loads(self.note.read_text(encoding="utf-8"))
        note["itself"] = itself
        self.write(self.note, note)

    def _applied(self, **more) -> dict:
        return {"applied": True, "products_with_a_second_reading": 15210, "left_a_kind": 4120,
                "left_by_answer": {"accessory": 2100, "other": 1500, "part": 520}, "came_back": 610, "brakes": "stood",
                "changed_of_what_was_shown": 12, "held_as_shown": 0, "held_by_a_kinds_brake": [],
                "held_by_the_nights_brake": "", "products_with_a_question_waiting": 31, "products_to_ask_again": 0, **more}

    def test_a_release_without_it_says_nothing(self) -> None:
        self.assertNotIn("kind itself", "\n".join(self.printed()))

    def test_the_switch_off_is_said_and_is_no_limit(self) -> None:
        self._note({"applied": False, "why": "the switch is off"})
        lines = self.printed()
        self.assertIn("kind itself: its answers are not read (the switch is off)", lines)
        self.assertEqual(lines[-1], "within every limit")

    def test_a_quiet_night_is_within_every_limit(self) -> None:
        self._note(self._applied())
        self.write(self.folder / "itself-night.json", {
            "night": "2026-11-22", "named": 412, "first": {"asked": 380, "answered": 380}, "second": {"asked": 95, "answered": 94},
            "left": 1, "cost_usd": 0.0731, "stopped": ""})
        lines = self.printed()
        self.assertIn("kind itself: 15,210 products read twice; 4,120 left a kind (accessory 2,100, other 1,500, part 520), "
                      "610 came back; 31 wait for an answer, 0 to ask again; changed of what was shown the night before 12", lines)
        self.assertIn("kind itself, the AI's answers on 2026-11-22: 412 questions named; first reading 380 of 380 asked, "
                      "second 94 of 95; 1 left; $0.07", lines)
        self.assertEqual(lines[-1], "within every limit")

    def test_a_brake_that_holds_is_a_limit(self) -> None:
        self._note(self._applied(held_as_shown=31, held_by_a_kinds_brake=[{"kind": "printer", "products": 31, "since": "2026-11-22"}]))
        lines = self.printed()
        self.assertIn("kind itself, a kind's brake holds: printer 31 (since 2026-11-22)", lines)
        self.assertEqual(self.over(lines), ["over the limit: a kind's brake holds answers to \"is it the kind itself\" until the "
                                            "owner's word: printer 31 (since 2026-11-22) (rules 7.3)"])
        self._note(self._applied(held_as_shown=900, held_by_the_nights_brake="2026-11-22"))
        lines = self.printed()
        self.assertIn("kind itself, the night's brake holds since 2026-11-22: 900 products stay as shown", lines)
        self.assertEqual(len(self.over(lines)), 1)
        self.assertIn("the night's brake holds every new answer", self.over(lines)[0])

    def test_brakes_with_nothing_to_hold_against_and_a_stopped_asking_are_limits(self) -> None:
        self._note(self._applied(brakes="no memory of the night before: nothing to hold against", shown_not_kept="OSError"))
        self.write(self.folder / "itself-night.json", {"night": "2026-11-22", "named": 90000, "left": 61000, "cost_usd": 4.97,
                                                       "stopped": "its limit of $5.00"})
        over = self.over(self.printed())
        self.assertEqual(len(over), 3)
        self.assertIn("had no night before to hold against", over[0])
        self.assertIn("was not kept for the next night's brakes", over[1])
        self.assertIn("stopped at the night's brake of $5 (its limit of $5.00)", over[2])
        self.write(self.folder / "itself-night.json", {"night": "2026-11-22", "named": 5, "left": 0, "cost_usd": 0.0,
                                                       "stopped": "the answers file cannot be read: nothing asked"})
        self.assertIn("over the limit: the answers file of \"is it the kind itself\" cannot be read: nothing was asked",
                      self.over(self.printed()))


class QualityMeterHealthTests(_AServer, unittest.TestCase):
    """The quality meter's day (`docs/PICWISE_KIND_ITSELF_RULES.md`, 9)."""

    def _day(self, **more) -> None:
        self.write(self.folder / "meter-day.json", {
            "day": "2026-11-22",
            "searches": {"searches": 40, "pages_failed": 0, "cards": 471, "yes": 430, "no": 38, "unsure": 3, "not_judged": 0,
                         "share": 0.9188},
            "kinds": {"of_the_day": 45, "cards": 500, "yes": 450, "no": 40, "unsure": 10, "not_judged": 0, "share": 0.9184},
            "kinds_week": {"days": 7, "yes": 3000, "no": 300, "share": 0.9091},
            "before": {"day": "2026-11-21", "share": 0.9102}, "fell_points": -0.9, "fell": False,
            "wrong": [{"part": "search", "q": "printer", "title": "Fixturon Pickup Roller", "shop": "Fixture Shop via Awin",
                       "price": "£3.99", "why": "a roller for printers"},
                      {"part": "kind", "q": "humidor", "title": "Cigar Cutter", "shop": "Other via Awin", "price": "£5.00",
                       "why": "a cutter"}],
            "wrong_in_all": 78, "judged_today": 31, "calls": 9, "failed_calls": 0, "cost_usd": 0.0712, "stopped": "",
            "asked": True, **more})

    def test_before_its_first_day_nothing_is_said(self) -> None:
        self.assertNotIn("quality", "\n".join(self.printed()))

    def test_the_day_is_said_with_the_day_before_and_the_wrong_cards_of_the_searches(self) -> None:
        self._day()
        lines = self.printed()
        self.assertIn("quality on 2026-11-22, the 40 searches: 430 of 468 cards right (91.9%); 3 cannot be told, 0 not judged; "
                      "the day before (2026-11-21) 91.0%", lines)
        self.assertIn("quality, the day's 45 kinds: 450 of 490 cards right (91.8%); the last 7 days' kinds 90.9%; "
                      "31 cards judged today, $0.07", lines)
        self.assertIn('quality, wrong for "printer": Fixturon Pickup Roller (Fixture Shop via Awin, £3.99): a roller for printers',
                      lines)
        # The kinds' wrong cards are in the note, not in the log.
        self.assertNotIn("Cigar Cutter", "\n".join(lines))
        self.assertEqual(lines[-1], "within every limit")

    def test_a_fall_a_stop_an_old_day_and_a_page_that_failed_are_limits(self) -> None:
        self._day(fell=True, fell_points=4.2, stopped="its limit of $2.00")
        over = self.over(self.printed())
        self.assertEqual(over, [
            "over the limit: the quality of the 40 searches fell 4.2 points from the day before: 91.0% to 91.9%",
            "over the limit: the quality meter stopped at its day's $2 (its limit of $2.00)",
        ])
        self._day(day="2026-11-19")
        self.assertIn("over the limit: the quality meter recorded no day since 2026-11-19", self.over(self.printed()))
        self._day(searches={"yes": 400, "no": 30, "unsure": 0, "not_judged": 0, "pages_failed": 2, "share": 0.93})
        self.assertIn("over the limit: the quality meter could not read 2 of the 40 searches' pages", self.over(self.printed()))


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
