"""The words of the searches visitors make, kept on the server (owner, 2026-11-07).

Asked whether the server should keep the searches visitors make, only their text, to
measure the search on real searches every week, the owner answered «Ναι σε όλα».
Pinned here (`picwise_app.search_log`):

- kept only where the site is given a folder that exists; on Vercel and in tests, nothing;
- one line per search, `{"q": ...}`, in the day's file by the UTC day: the words as typed,
  spaces collapsed, cut at 300 characters; nothing else, no IP, no browser, no time of day;
- an empty search is not kept; a day's file stops growing at its limit;
- files older than 12 months are deleted when a day's first search is kept;
- `/searched` keeps the words and answers 204, never kept by a browser or a cache, never
  indexed, on the WSGI app (Vercel and the server) and the local server alike;
- the search page's script reports only a search's first page, from a browser, on
  /search and /results;
- the privacy page says what is kept, why and for how long;
- the server's site is given the folder, and the deployment makes it.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import date, datetime, timezone
from http.server import HTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_app import search_log  # noqa: E402
from picwise_app.search_log import (  # noqa: E402
    MAX_SEARCH_LENGTH,
    SEARCH_LOG_DIR_ENV,
    SEARCH_LOG_PATH,
    prune_search_logs,
    read_search_log,
    record_search,
)

NOW = datetime(2026, 11, 7, 10, 30, tzinfo=timezone.utc)


class _Folder:
    """A temporary folder given to the site as its search log folder."""

    def __enter__(self) -> Path:
        self._temp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get(SEARCH_LOG_DIR_ENV)
        os.environ[SEARCH_LOG_DIR_ENV] = self._temp.name
        return Path(self._temp.name)

    def __exit__(self, *_exc: object) -> None:
        if self._previous is None:
            os.environ.pop(SEARCH_LOG_DIR_ENV, None)
        else:
            os.environ[SEARCH_LOG_DIR_ENV] = self._previous
        self._temp.cleanup()


class KeepingTests(unittest.TestCase):
    def test_nothing_is_kept_without_a_folder(self) -> None:
        previous = os.environ.pop(SEARCH_LOG_DIR_ENV, None)
        try:
            self.assertFalse(record_search("fridge", now=NOW))
            os.environ[SEARCH_LOG_DIR_ENV] = "/nonexistent/picwise-searches"
            self.assertFalse(record_search("fridge", now=NOW))
        finally:
            if previous is None:
                os.environ.pop(SEARCH_LOG_DIR_ENV, None)
            else:
                os.environ[SEARCH_LOG_DIR_ENV] = previous

    def test_one_line_a_search_the_words_only(self) -> None:
        with _Folder() as folder:
            self.assertTrue(record_search("  quiet   washing machine ", now=NOW))
            self.assertTrue(record_search("μπαταρία", now=NOW))
            self.assertFalse(record_search("   ", now=NOW))
            path = folder / "2026-11-07.jsonl"
            self.assertEqual(
                path.read_text(encoding="utf-8").splitlines(),
                ['{"q": "quiet washing machine"}', '{"q": "μπαταρία"}'],
            )
            self.assertEqual(read_search_log(folder, date(2026, 11, 7)), ["quiet washing machine", "μπαταρία"])
            # Nothing but the words: no time of day, no address, no browser.
            self.assertEqual({key for line in path.read_text().splitlines() for key in json.loads(line)}, {"q"})

    def test_the_words_are_cut_at_the_limit(self) -> None:
        with _Folder() as folder:
            record_search("a" * 1000, now=NOW)
            self.assertEqual(read_search_log(folder, NOW.date()), ["a" * MAX_SEARCH_LENGTH])

    def test_the_day_is_the_utc_day(self) -> None:
        with _Folder() as folder:
            record_search("kettle", now=datetime(2026, 11, 7, 23, 59, tzinfo=timezone.utc))
            record_search("toaster", now=datetime(2026, 11, 8, 0, 1, tzinfo=timezone.utc))
            self.assertEqual(read_search_log(folder, date(2026, 11, 7)), ["kettle"])
            self.assertEqual(read_search_log(folder, date(2026, 11, 8)), ["toaster"])

    def test_a_days_file_stops_at_its_limit(self) -> None:
        with _Folder() as folder, mock.patch.object(search_log, "MAX_DAY_FILE_BYTES", 60):
            self.assertTrue(record_search("washing machine", now=NOW))
            self.assertTrue(record_search("tumble dryer", now=NOW))
            self.assertFalse(record_search("dishwasher", now=NOW))
            self.assertEqual(read_search_log(folder, NOW.date()), ["washing machine", "tumble dryer"])

    def test_files_older_than_a_year_go_when_a_day_begins(self) -> None:
        with _Folder() as folder:
            (folder / "2025-11-06.jsonl").write_text('{"q": "old"}\n', encoding="utf-8")
            (folder / "2025-11-08.jsonl").write_text('{"q": "kept"}\n', encoding="utf-8")
            (folder / "notes.txt").write_text("not a day file", encoding="utf-8")
            record_search("fridge", now=NOW)
            self.assertFalse((folder / "2025-11-06.jsonl").exists())
            self.assertTrue((folder / "2025-11-08.jsonl").exists())
            self.assertTrue((folder / "notes.txt").exists())
            self.assertEqual(prune_search_logs(folder, date(2027, 1, 1)), 1)

    def test_a_line_that_is_not_one_is_left_out_when_read(self) -> None:
        with _Folder() as folder:
            (folder / "2026-11-07.jsonl").write_text('{"q": "fridge"}\nnot json\n{"x": 1}\n', encoding="utf-8")
            self.assertEqual(read_search_log(folder, date(2026, 11, 7)), ["fridge"])


def _wsgi(path: str, query_string: str) -> tuple[str, dict[str, str], bytes]:
    from api.index import app

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "HTTP_HOST": "localhost",
        "wsgi.input": io.BytesIO(),
        "wsgi.url_scheme": "http",
    }
    found: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]], *_args: object) -> None:
        found["status"], found["headers"] = status, dict(headers)

    body = b"".join(app(environ, start_response))
    return str(found["status"]), dict(found["headers"]), body


class EndpointTests(unittest.TestCase):
    def test_the_wsgi_app_keeps_the_words_and_answers_nothing(self) -> None:
        with _Folder() as folder:
            status, headers, body = _wsgi(SEARCH_LOG_PATH, "q=air%20fryer")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertIn("noindex", headers.get("X-Robots-Tag", ""))
            today = datetime.now(timezone.utc).date()
            self.assertEqual(read_search_log(folder, today), ["air fryer"])

    def test_without_a_folder_it_answers_the_same_and_keeps_nothing(self) -> None:
        previous = os.environ.pop(SEARCH_LOG_DIR_ENV, None)
        try:
            status, _headers, body = _wsgi(SEARCH_LOG_PATH, "q=air%20fryer")
        finally:
            if previous is not None:
                os.environ[SEARCH_LOG_DIR_ENV] = previous
        self.assertEqual((status, body), ("204 No Content", b""))

    def test_the_local_server_keeps_the_words_too(self) -> None:
        from picwise_app.app import PicwiseLocalApp, PicwiseRequestHandler

        handler = type("Handler", (PicwiseRequestHandler,), {"app": PicwiseLocalApp()})
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with _Folder() as folder:
                url = f"http://127.0.0.1:{server.server_address[1]}{SEARCH_LOG_PATH}?q=kettle"
                with urllib.request.urlopen(url, timeout=10) as answer:
                    self.assertEqual(answer.status, 204)
                    self.assertEqual(answer.headers["Cache-Control"], "no-store")
                self.assertEqual(read_search_log(folder, datetime.now(timezone.utc).date()), ["kettle"])
        finally:
            server.shutdown()
            server.server_close()


class PageScriptTests(unittest.TestCase):
    def test_the_page_reports_a_searchs_first_page_from_a_browser(self) -> None:
        from picwise_surface.reference import _SEARCH_SCRIPT

        self.assertIn('fetch("/searched?q="+encodeURIComponent(q)', _SEARCH_SCRIPT)
        self.assertIn('credentials:"omit"', _SEARCH_SCRIPT)
        # Only on a search page, and not for "More" or the AI layer's refresh.
        self.assertIn('path!=="/search"&&path!=="/results"', _SEARCH_SCRIPT)
        self.assertIn("/[?&](shown|assist)=/.test(location.search)", _SEARCH_SCRIPT)


class PrivacyAndServerTests(unittest.TestCase):
    def test_the_privacy_page_says_what_is_kept_why_and_how_long(self) -> None:
        from picwise_surface.legal import render_privacy_page

        page = render_privacy_page()
        self.assertIn("<h2>Searches</h2>", page)
        self.assertIn(
            "PicWise keeps the words of the searches made on its pages, on its own server: only the words and the "
            "day, and nothing that identifies you: no IP address, no browser or device details and no cookie. "
            "They are kept for 12 months.",
            page,
        )
        self.assertIn("Searches: PicWise's legitimate interest in improving its search.", page)
        self.assertIn("the words of searches for 12 months", page)
        self.assertIn("Last updated: 7 November 2026", page)

    def test_the_server_gives_the_site_its_folder_and_makes_it(self) -> None:
        unit = (ROOT / "deployment" / "server" / "picwise-web.service").read_text(encoding="utf-8")
        self.assertIn("Environment=PICWISE_SEARCH_LOG_DIR=/srv/picwise/shared/searches", unit)
        self.assertIn("ReadWritePaths=/srv/picwise/shared", unit)
        deploy = (ROOT / "deployment" / "server" / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn('"$SHARED/searches"', deploy)


if __name__ == "__main__":
    unittest.main()
