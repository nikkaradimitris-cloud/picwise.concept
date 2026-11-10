"""No visitor waits for the prepared catalogue: the server's keeper (the audit, 2026-11-10).

The audit measured, on the live site, the first request of each of its four workers
after the night's preparation waiting 5.4 to 5.7 s while the worker read the new
prepared file, and each worker's first search of the day 2.9 to 3.2 s while it built
the day's catalogue. On the server each worker now has a keeper
(`state.keep_prepared_catalogue_loaded`, started by `deployment/server/wsgi_server.py`):
a thread that loads the file as the worker starts, and brings in a new file, a new day or
newly gone photos off to the side (`state.refresh_prepared_catalogue`), the worker
answering from what it has until the new is put in place in one step. Pinned here:

- a worker that just started is loaded, catalogue and indexes, before a visitor asks;
- a new file answers only once the keeper has put it in place, and a request never
  reads it itself;
- a file that cannot stand in for the feed (written by other code, as during a
  deployment) is refused once, and the one loaded goes on answering while it is fresh;
- a new day, or newly gone photos, rebuild the catalogue off to the side;
- without a keeper (a serverless host, a test, a forked process, a thread that ended)
  everything loads on the request, as before.

Every row is written with fictional brands and `.invalid` URLs.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import search_selection as ss  # noqa: E402
from picwise_providers import state  # noqa: E402
from picwise_providers.prepared_catalogue import PREPARED_CATALOGUE_ENV, PREPARED_MAX_AGE_ENV  # noqa: E402
from picwise_providers.product_photos import set_gone_photos  # noqa: E402
from picwise_providers.state import (  # noqa: E402
    keep_prepared_catalogue_loaded,
    prepared_catalogue_status,
    refresh_prepared_catalogue,
    resolve_card_eligible_provider_feed_product_by_id,
)
from test_picwise_prepared_catalogue import _COLUMNS, _PreparedMixin, _feed_rows, _row  # noqa: E402


class _KeeperMixin(_PreparedMixin):
    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(state._KEEPER.clear)
        self.addCleanup(set_gone_photos, None)

    def _keeper_at_work(self) -> None:
        """As while the keeper's thread runs in this process; each look is made by hand."""
        state._KEEPER.update(thread=threading.current_thread(), pid=os.getpid())

    def _start(self, rows: list[list[str]] | None = None) -> None:
        self._write_feed(rows if rows is not None else _feed_rows())
        self._prepare()
        self._answer_from_prepared()
        self._keeper_at_work()

    def _new_file(self, rows: list[list[str]], *, code: str = "") -> None:
        """The night's new prepared file, written over the old one, this process left as
        it was: with what it had loaded, and no feed of its own to read. With `code`,
        the file says other code wrote it, as a deployment's preparation writes before
        the site's workers are restarted."""
        loaded = dict(state._PREPARED_STATE)
        kinds = dict(ss._PREPARED_KINDS)
        before = os.stat(self.prepared_path).st_mtime_ns
        # Preparing here clears what this process loaded (the tests' own tidying).
        self._write_feed(rows)
        self._prepare()
        if code:
            payload = json.loads(gzip.decompress(self.prepared_path.read_bytes()).decode("utf-8"))
            payload["code"] = code
            self.prepared_path.write_bytes(gzip.compress(json.dumps(payload).encode("ascii")))
        os.utime(self.prepared_path, ns=(before + 5_000_000_000, before + 5_000_000_000))
        state._PREPARED_STATE.update(loaded)
        ss.remember_product_kinds(kinds, keep_indexes=True)
        os.environ[PREPARED_CATALOGUE_ENV] = str(self.prepared_path)
        os.environ.pop("AWIN_FEED_FILE", None)

    def _kettles(self) -> list[str]:
        return self._ids(self._page("kettle"))


class LoadedBeforeAVisitorAsksTests(_KeeperMixin, unittest.TestCase):
    def test_a_worker_that_just_started_is_loaded_with_its_catalogue_and_indexes(self) -> None:
        self._start()
        self.assertEqual(refresh_prepared_catalogue(), "loaded")
        catalogue = state._PREPARED_STATE["catalogue"][1]
        self.assertIn(id(catalogue.new_fields), ss._KIND_INDEXES)
        self.assertIn(id(catalogue.new_fields), ss._WORD_LOOKUPS)
        self.assertEqual(refresh_prepared_catalogue(), "current")
        # The page reads no file and builds no catalogue: both are there.
        with patch.object(state, "check_prepared_catalogue", side_effect=AssertionError("read on a request")), \
                patch.object(state, "_build_prepared_search_catalogue", side_effect=AssertionError("built on a request")):
            ids = self._kettles()
        self.assertEqual(len(ids), 4)
        self.assertIn("w1", ids)
        self.assertEqual(prepared_catalogue_status()["state"], "in_use")

    def test_without_a_prepared_file_there_is_nothing_to_keep(self) -> None:
        self.assertIsNone(keep_prepared_catalogue_loaded())
        self.assertEqual(refresh_prepared_catalogue(), "not_used")
        self.assertFalse(state._keeper_on())


class ANewFileTests(_KeeperMixin, unittest.TestCase):
    _WITH_A_CHEAPER_KETTLE = [_row("k0", "Fixturon Electric Kettle 0 1.7L", 5.0, code=30)]

    def _load_first(self) -> None:
        self._start()
        self.assertEqual(refresh_prepared_catalogue(), "loaded")
        self.assertNotIn("k0", self._kettles())

    def test_a_new_file_answers_once_the_keeper_has_put_it_in_place(self) -> None:
        self._load_first()
        old_catalogue = state._PREPARED_STATE["catalogue"][1]
        self._new_file(_feed_rows() + self._WITH_A_CHEAPER_KETTLE)

        # Until the keeper looks, the worker answers from the file it has, reading none.
        with patch.object(state, "check_prepared_catalogue", side_effect=AssertionError("read on a request")):
            self.assertNotIn("k0", self._kettles())
            self.assertIsNone(resolve_card_eligible_provider_feed_product_by_id("k0"))
        self.assertEqual(refresh_prepared_catalogue(), "changed")
        self.assertEqual(self._kettles()[1], "k0")
        self.assertIsNotNone(resolve_card_eligible_provider_feed_product_by_id("k0"))
        self.assertEqual(refresh_prepared_catalogue(), "current")
        # What was built for the catalogue left behind is dropped; the new one's is there.
        new_catalogue = state._PREPARED_STATE["catalogue"][1]
        self.assertIsNot(new_catalogue, old_catalogue)
        self.assertNotIn(id(old_catalogue.new_fields), ss._KIND_INDEXES)
        self.assertNotIn(id(old_catalogue.new_fields), ss._WORD_LOOKUPS)
        self.assertIn(id(new_catalogue.new_fields), ss._KIND_INDEXES)
        self.assertIn(id(new_catalogue.new_fields), ss._WORD_LOOKUPS)

    def test_a_file_written_by_other_code_is_refused_once_and_the_loaded_one_goes_on(self) -> None:
        self._load_first()
        loaded = state._PREPARED_STATE["prepared"]
        self._new_file(_feed_rows() + self._WITH_A_CHEAPER_KETTLE, code="written-by-other-code")
        with patch.object(state, "check_prepared_catalogue", wraps=state.check_prepared_catalogue) as read:
            self.assertEqual(refresh_prepared_catalogue(), "refused")
            self.assertEqual(refresh_prepared_catalogue(), "current")
            self.assertEqual(refresh_prepared_catalogue(), "current")
            ids = self._kettles()
        self.assertEqual(read.call_count, 1)
        self.assertEqual(len(ids), 4)
        self.assertNotIn("k0", ids)
        self.assertIs(state._PREPARED_STATE["prepared"], loaded)
        self.assertEqual(prepared_catalogue_status()["state"], "in_use")

    def test_the_loaded_one_too_old_the_refused_file_is_what_a_request_finds(self) -> None:
        self._load_first()
        self._new_file(_feed_rows() + self._WITH_A_CHEAPER_KETTLE, code="written-by-other-code")
        self.assertEqual(refresh_prepared_catalogue(), "refused")
        os.environ[PREPARED_MAX_AGE_ENV] = "0"
        # Nothing fresh to answer from: the request reads the file, as without a keeper,
        # and with no feed of its own shows no product.
        self.assertEqual(self._kettles(), [])
        self.assertEqual(prepared_catalogue_status()["state"], "other_code")

    def test_without_a_keeper_the_request_reads_the_new_file_itself(self) -> None:
        self._load_first()
        self._new_file(_feed_rows() + self._WITH_A_CHEAPER_KETTLE)
        state._KEEPER.clear()
        self.assertEqual(self._kettles()[1], "k0")


class ANewDayTests(_KeeperMixin, unittest.TestCase):
    def test_a_new_day_rebuilds_the_catalogue_off_to_the_side(self) -> None:
        today = datetime.now(timezone.utc).date()
        self._start(_feed_rows(valid_to=today.isoformat()))
        self.assertEqual(refresh_prepared_catalogue(), "loaded")
        self.assertIn("w1", self._kettles())
        with patch.object(state, "_today", return_value=today + timedelta(days=1)):
            # The request builds nothing: yesterday's catalogue answers for the seconds
            # the keeper takes.
            with patch.object(state, "_build_prepared_search_catalogue", side_effect=AssertionError("built on a request")):
                self.assertIn("w1", self._kettles())
            self.assertEqual(refresh_prepared_catalogue(), "rebuilt")
            self.assertNotIn("w1", self._kettles())
            self.assertEqual(refresh_prepared_catalogue(), "current")

    def test_newly_gone_photos_rebuild_the_catalogue_off_to_the_side(self) -> None:
        self._start()
        self.assertEqual(refresh_prepared_catalogue(), "loaded")
        self.assertIn("w1", self._kettles())
        set_gone_photos(["https://fixture.example.invalid/img/w1.jpg"])
        self.assertEqual(refresh_prepared_catalogue(), "rebuilt")
        self.assertNotIn("w1", self._kettles())

    def test_without_a_keeper_the_request_builds_the_new_day_itself(self) -> None:
        today = datetime.now(timezone.utc).date()
        self._start(_feed_rows(valid_to=today.isoformat()))
        self.assertEqual(refresh_prepared_catalogue(), "loaded")
        state._KEEPER.clear()
        with patch.object(state, "_today", return_value=today + timedelta(days=1)):
            self.assertNotIn("w1", self._kettles())


class TheKeepersThreadTests(_KeeperMixin, unittest.TestCase):
    def _wait(self, condition, seconds: float = 20.0) -> bool:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if condition():
                return True
            time.sleep(0.02)
        return False

    def test_the_thread_loads_and_brings_in_a_new_file_by_itself(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        called: list[int] = []
        stop = keep_prepared_catalogue_loaded(
            every_seconds=0.05, once_loaded=lambda: called.append(len(state._PREPARED_STATE["prepared"].products))
        )
        self.assertIsNotNone(stop)
        thread = state._KEEPER["thread"]

        def halt() -> None:
            stop.set()
            thread.join(timeout=10)

        self.addCleanup(halt)
        self.assertTrue(state._keeper_on())
        # One keeper for a process.
        self.assertIsNone(keep_prepared_catalogue_loaded(every_seconds=0.05))
        self.assertTrue(self._wait(lambda: state._PREPARED_STATE.get("catalogue") is not None))
        first = state._PREPARED_STATE["prepared"]

        # The night's new file, prepared as the server's preparation does, in a process
        # of its own: this one keeps what it has loaded.
        rows = _feed_rows() + [_row("k0", "Fixturon Electric Kettle 0 1.7L", 5.0, code=30)]
        feed = self.folder / "night.csv"
        with feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            writer.writerows(rows)
        environment = {**os.environ, "AWIN_FEED_FILE": str(feed)}
        environment.pop(PREPARED_CATALOGUE_ENV, None)
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"), "--out", str(self.prepared_path)],
            check=True, capture_output=True, env=environment, cwd=ROOT,
        )
        self.assertTrue(self._wait(lambda: state._PREPARED_STATE.get("prepared") is not first))
        self.assertEqual(self._kettles()[1], "k0")
        halt()
        self.assertFalse(state._keeper_on())
        # Called once, when the worker first had a catalogue: not again for the new file.
        self.assertEqual(called, [len(first.products)])

    def test_no_keeper_in_another_process_nor_once_its_thread_has_ended(self) -> None:
        ended = threading.Thread(target=lambda: None)
        ended.start()
        ended.join()
        state._KEEPER.update(thread=ended, pid=os.getpid())
        self.assertFalse(state._keeper_on())
        state._KEEPER.update(thread=threading.current_thread(), pid=os.getpid() + 1)
        self.assertFalse(state._keeper_on())
        state._KEEPER.update(thread=threading.current_thread(), pid=os.getpid())
        self.assertTrue(state._keeper_on())


if __name__ == "__main__":
    unittest.main()
