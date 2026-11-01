"""Products whose photo is gone are not shown (owner, 2026-11-01).

«Όταν το προϊόν δεν φέρνει φωτογραφία δεν πρέπει να εμφανίζεται... Στις περισσότερες
περιπτώσεις είναι not found». Pinned here:

- the list of gone photos the site reads (`picwise_providers.product_photos`), read again
  when it changes;
- a product whose photo is on it is not shown, counted or recommended, from the feed and
  from the prepared file, and is shown again when the list no longer names it;
- the preparation keeps every product, so that the nightly check can ask again;
- the nightly check (`deployment/server/check_photos.py`): only a link to nothing (404,
  410) is gone; what it asks each night, within its time; what it keeps and writes; how
  it asks a real server (HEAD, one byte where HEAD is refused, redirects, kept-open
  connections);
- the browser's last guard: a card whose photo fails is hidden whole.

Every shop, product and address is fictional.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import product_photos  # noqa: E402
from picwise_providers.prepared_catalogue import write_prepared_catalogue  # noqa: E402
from picwise_providers.product_photos import gone_photos, photo_is_gone, set_gone_photos  # noqa: E402
from picwise_providers.state import prepare_feed_catalogue  # noqa: E402
from picwise_surface.browser_lists import HEAD_SCRIPT  # noqa: E402
from picwise_surface.reference import _PAGE_STYLES  # noqa: E402
from test_picwise_prepared_catalogue import _PreparedMixin, _feed_rows  # noqa: E402

_SPEC = importlib.util.spec_from_file_location("check_photos", ROOT / "deployment" / "server" / "check_photos.py")
check_photos = importlib.util.module_from_spec(_SPEC)
sys.modules["check_photos"] = check_photos
_SPEC.loader.exec_module(check_photos)

NOW = datetime(2026, 11, 2, 4, 40, tzinfo=timezone.utc)


def _photo(pid: str) -> str:
    return f"https://fixture.example.invalid/img/{pid}.jpg"


class GonePhotosFileTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_gone_photos(None)

    def test_the_file_is_read_and_read_again_when_it_changes(self) -> None:
        path = Path(tempfile.mkdtemp()) / "gone.json"
        path.write_text(json.dumps({"checked_at": "2026-11-02T04:40:00+00:00", "gone": [_photo("k1")]}))
        saved_env, saved_recheck = os.environ.get(product_photos.GONE_PHOTOS_FILE_ENV), product_photos._RECHECK_SECONDS
        os.environ[product_photos.GONE_PHOTOS_FILE_ENV] = str(path)
        product_photos._RECHECK_SECONDS = 0.0
        try:
            set_gone_photos(None)
            self.assertEqual(gone_photos(), frozenset({_photo("k1")}))
            first = product_photos.gone_photos_key()
            path.write_text(json.dumps({"gone": [_photo("k1"), _photo("k2")]}))
            os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
            self.assertEqual(gone_photos(), frozenset({_photo("k1"), _photo("k2")}))
            self.assertNotEqual(product_photos.gone_photos_key(), first)
            path.unlink()
            self.assertEqual(gone_photos(), frozenset())
        finally:
            product_photos._RECHECK_SECONDS = saved_recheck
            if saved_env is None:
                os.environ.pop(product_photos.GONE_PHOTOS_FILE_ENV, None)
            else:
                os.environ[product_photos.GONE_PHOTOS_FILE_ENV] = saved_env
            set_gone_photos(None)

    def test_without_the_file_no_photo_is_gone(self) -> None:
        saved = os.environ.pop(product_photos.GONE_PHOTOS_FILE_ENV, None)
        try:
            set_gone_photos(None)
            self.assertEqual(gone_photos(), frozenset())

            class Product:
                image_url = _photo("k1")

            self.assertFalse(photo_is_gone(Product()))
        finally:
            if saved is not None:
                os.environ[product_photos.GONE_PHOTOS_FILE_ENV] = saved


class GonePhotosPageTests(_PreparedMixin, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(set_gone_photos, None)

    def test_a_product_whose_photo_is_gone_is_not_shown_from_the_feed(self) -> None:
        self._write_feed(_feed_rows())
        page = self._page("kettle")
        self.assertIn("w1", self._ids(page))
        self.assertEqual(self._counter(page), "4 of 10")
        set_gone_photos({_photo("w1")})
        page = self._page("kettle")
        self.assertNotIn("w1", self._ids(page))
        self.assertEqual(self._counter(page), "4 of 9")

    def test_a_product_whose_photo_is_gone_is_not_shown_from_the_prepared_file(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        self.assertIn("w1", self._ids(self._page("kettle")))
        set_gone_photos({_photo("w1")})
        page = self._page("kettle")
        self.assertNotIn("w1", self._ids(page))
        self.assertEqual(self._counter(page), "4 of 9")
        # Back on the next list: the photo answered again.
        set_gone_photos(set())
        self.assertIn("w1", self._ids(self._page("kettle")))

    def test_a_recommended_whose_photo_is_gone_is_replaced(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        before = self._cards(self._page("kettle"))
        self.assertTrue(before[0]["recommended"])
        set_gone_photos({_photo(before[0]["id"])})
        after = self._cards(self._page("kettle"))
        self.assertTrue(after[0]["recommended"])
        self.assertNotEqual(after[0]["id"], before[0]["id"])
        self.assertNotIn(before[0]["id"], [card["id"] for card in after])

    def test_the_preparation_keeps_every_product_whatever_the_list(self) -> None:
        self._write_feed(_feed_rows())
        set_gone_photos({_photo("k5"), _photo("w1")})
        prepared = prepare_feed_catalogue()
        ids = {product.provider_product_id for product in prepared.products}
        self.assertTrue({"k5", "w1"} <= ids)


class BrowserGuardTests(unittest.TestCase):
    def test_a_card_whose_photo_fails_is_hidden_whole(self) -> None:
        self.assertIn("addEventListener('error'", HEAD_SCRIPT)
        self.assertIn("closest('.pw-card')", HEAD_SCRIPT)
        self.assertIn("pw-no-photo", HEAD_SCRIPT)
        self.assertNotIn("setItem", HEAD_SCRIPT)
        self.assertIn(".pw-card.pw-no-photo{display:none;}", _PAGE_STYLES)
        self.assertNotIn("No photo from the shop", _PAGE_STYLES)


class PhotoCheckDeploymentTests(unittest.TestCase):
    def test_the_check_runs_every_night_and_once_by_each_deployment(self) -> None:
        server = ROOT / "deployment" / "server"
        deploy = (server / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn("picwise-photos.service picwise-photos.timer", deploy)
        self.assertIn("systemctl start --no-block picwise-photos.service", deploy)
        self.assertIn("systemctl enable --now picwise-photos.timer", deploy)
        self.assertIn('"$SHARED/photos"', deploy)
        service = (server / "picwise-photos.service").read_text(encoding="utf-8")
        self.assertIn("ExecStart=/usr/bin/python3 deployment/server/check_photos.py", service)
        self.assertIn("After=network-online.target picwise-prepare.service", service)
        self.assertIn("ReadWritePaths=/srv/picwise/shared", service)
        # It needs no secret.
        self.assertNotIn("EnvironmentFile", service)
        timer = (server / "picwise-photos.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 04:40:00 UTC", timer)
        web = (server / "picwise-web.service").read_text(encoding="utf-8")
        self.assertIn("Environment=PICWISE_GONE_PHOTOS_FILE=/srv/picwise/shared/photos/gone.json", web)
        # The preparation keeps every product: it is never given the list.
        prepare = (server / "picwise-prepare.service").read_text(encoding="utf-8")
        self.assertNotIn("PICWISE_GONE_PHOTOS_FILE", prepare)
        workflow = (ROOT / ".github" / "workflows" / "server-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("photos gone:", workflow)


class CheckRulesTests(unittest.TestCase):
    def test_only_a_link_to_nothing_is_gone(self) -> None:
        for status, state in ((200, "ok"), (206, "ok"), (404, "gone"), (410, "gone"), (403, "unread"),
                              (429, "unread"), (500, "unread"), (503, "unread"), (301, "unread"), (0, "unread")):
            with self.subTest(status=status):
                self.assertEqual(check_photos.state_of(status), state)

    def test_what_is_asked_tonight_and_in_which_order(self) -> None:
        now = int(NOW.timestamp())
        day = check_photos.DAY
        seen = {
            "ok-recent": ("ok", now - 3 * day),
            "ok-old": ("ok", now - 15 * day),
            "gone-recent": ("gone", now - 2 * day),
            "gone-old": ("gone", now - 8 * day),
            "unread-recent": ("unread", now - 3600),
            "unread-old": ("unread", now - day),
        }
        urls = ["new-b", "ok-recent", "ok-old", "gone-recent", "gone-old", "unread-recent", "unread-old", "new-a"]
        self.assertEqual(check_photos.due(urls, seen, now), ["new-a", "new-b", "unread-old", "gone-old", "ok-old"])

    def test_no_photo_is_asked_once_the_time_is_spent(self) -> None:
        ticks = iter(range(1000))
        asked: list[str] = []

        def fetch(url: str) -> int:
            asked.append(url)
            return 200

        answers = check_photos.ask_all([f"u{index}" for index in range(100)], fetch, workers=1,
                                       budget_seconds=10, clock=lambda: next(ticks))
        # The first four were sent before the clock was read; then one more per tick
        # until ten ticks had passed.
        self.assertLess(len(answers), 100)
        self.assertEqual(set(answers), set(asked))
        everything = check_photos.ask_all([f"u{index}" for index in range(100)], lambda url: 404, workers=4,
                                          budget_seconds=3600)
        self.assertEqual(len(everything), 100)
        self.assertEqual(set(everything.values()), {404})


class CheckRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.db = check_photos.open_db(self.folder / "photos.sqlite3")
        self.addCleanup(self.db.close)
        self.out = self.folder / "gone.json"

    def _run(self, photos, answers, when):
        asked: list[str] = []

        def fetch(url: str) -> int:
            asked.append(url)
            return answers[url]

        lines = check_photos.run(photos, self.db, self.out, fetch, workers=2, budget_seconds=3600, now=when)
        return asked, lines, json.loads(self.out.read_text())

    def test_the_gone_photos_are_written_and_asked_again_a_week_later(self) -> None:
        photos = {
            _photo("a"): ("Fixture Store One", 1),
            _photo("b"): ("Fixture Store Two", 3),
            _photo("c"): ("Fixture Store Two", 1),
        }
        answers = {_photo("a"): 200, _photo("b"): 404, _photo("c"): 503}
        asked, lines, written = self._run(photos, answers, NOW)
        self.assertEqual(sorted(asked), sorted(photos))
        self.assertEqual(written["gone"], [_photo("b")])
        self.assertEqual(written["photos"], 3)
        self.assertIn("asked tonight 3 of the 3 due (read 1, gone 1, could not be read 1)", lines[0])
        self.assertIn("photos gone: 1, of 3 products, left out of the site", lines[1])
        self.assertIn("Fixture Store Two", lines[2])
        self.assertNotIn("https://", "\n".join(lines))
        # The next night only the one that could not be read is asked again; the gone
        # one stays gone without being asked.
        asked, _lines, written = self._run(photos, answers, NOW + timedelta(days=1))
        self.assertEqual(asked, [_photo("c")])
        self.assertEqual(written["gone"], [_photo("b")])
        # A week later the gone one is asked again, and it has come back.
        answers[_photo("b")] = 200
        asked, _lines, written = self._run(photos, answers, NOW + timedelta(days=8))
        self.assertIn(_photo("b"), asked)
        self.assertEqual(written["gone"], [])

    def test_an_address_gone_from_the_catalogue_for_a_month_is_forgotten(self) -> None:
        photos = {_photo("a"): ("Fixture Store One", 1), _photo("b"): ("Fixture Store One", 1)}
        self._run(photos, {_photo("a"): 200, _photo("b"): 404}, NOW)
        later = {_photo("a"): ("Fixture Store One", 1)}
        self._run(later, {_photo("a"): 200}, NOW + timedelta(days=15))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM photo").fetchone()[0], 2)
        _asked, _lines, written = self._run(later, {_photo("a"): 200}, NOW + timedelta(days=31))
        self.assertEqual([row[0] for row in self.db.execute("SELECT url FROM photo")], [_photo("a")])
        self.assertEqual(written["gone"], [])

    def test_main_reads_the_photos_of_the_prepared_catalogue(self) -> None:
        class Prepared(_PreparedMixin, unittest.TestCase):
            def runTest(self) -> None:
                pass

        prepared_test = Prepared()
        prepared_test.setUp()
        try:
            prepared_test._write_feed(_feed_rows())
            prepared_test._prepare()
            gone = {_photo("k3")}
            out = io.StringIO()
            with redirect_stdout(out):
                code = check_photos.main(
                    ["--catalogue", str(prepared_test.prepared_path), "--db", str(self.folder / "main.sqlite3"),
                     "--out", str(self.out), "--budget-minutes", "5", "--workers", "2"],
                    fetch=lambda url: 404 if url in gone else 200,
                )
            self.assertEqual(code, 0)
            written = json.loads(self.out.read_text())
            self.assertEqual(written["gone"], [_photo("k3")])
            # Nine kettles, a refurbished one, one with an end date, five laptops.
            self.assertEqual(written["photos"], 16)
            self.assertIn("photos gone: 1, of 1 products", out.getvalue())
            self.assertIn("Fixture Store One", out.getvalue())
        finally:
            prepared_test.doCleanups()

    def test_a_catalogue_that_cannot_be_read_keeps_the_last_file(self) -> None:
        self.out.write_text('{"gone": ["kept"]}')
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_photos.main(["--catalogue", str(self.folder / "missing.json.gz"),
                                      "--db", str(self.folder / "x.sqlite3"), "--out", str(self.out)],
                                     fetch=lambda url: 200)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(self.out.read_text())["gone"], ["kept"])
        self.assertIn("not checked", out.getvalue())


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    connections: set[int] = set()

    def log_message(self, *args) -> None:
        pass

    def _answer(self, head: bool) -> None:
        type(self).connections.add(id(self.connection))
        path = self.path
        if path.startswith("/moved"):
            self.send_response(302)
            self.send_header("Location", "/ok.jpg")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path.startswith("/no-head") and head:
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path.startswith("/gone"):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = b"\xff\xd8\xff\xe0"
        if self.headers.get("Range") == "bytes=0-0":
            self.send_response(206)
            body = body[:1]
        else:
            self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self._answer(True)

    def do_GET(self) -> None:
        self._answer(False)


class AskerTests(unittest.TestCase):
    def setUp(self) -> None:
        _Handler.connections = set()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def test_a_real_server_asked_as_the_nightly_check_asks_it(self) -> None:
        ask = check_photos.Asker()
        self.assertEqual(ask(f"{self.base}/ok.jpg"), 200)
        self.assertEqual(ask(f"{self.base}/gone.jpg"), 404)
        self.assertEqual(ask(f"{self.base}/moved.jpg"), 200)
        self.assertEqual(ask(f"{self.base}/no-head.jpg"), 206)
        self.assertEqual(ask("ftp://fixture.example.invalid/a.jpg"), 0)
        self.assertEqual(ask("http://127.0.0.1:9/nothing-listens.jpg"), 0)
        # One connection kept open for every ask made to this server from this thread.
        self.assertEqual(len(_Handler.connections), 1)
        ask.close()


if __name__ == "__main__":
    unittest.main()
