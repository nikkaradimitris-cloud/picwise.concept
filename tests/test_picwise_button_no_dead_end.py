"""A product's button whose product is gone meets no dead end (owner, 2026-11-21).

Shown a picture of the page a refused click met ("This option is no longer available",
with only a button back) beside the same search's current results with one line above
them, the owner chose the line «Οι τωρινές επιλογές»: «The product you chose is no longer
available. Here are the current choices for “…”.» (in Greek: «Το προϊόν που διάλεξες δεν
είναι πια διαθέσιμο. Αυτές είναι οι τωρινές επιλογές για “…”.»). Pinned here: a refused
click that carries its search is sent to that search with `gone=1`, never to the shop; the
search page says the line above its results, the search escaped; without `gone=1` nothing
is said; a click with no search keeps the page of its own.

Every row is local test data (the fixture feed of the local pipeline).
"""
from __future__ import annotations

import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"


def _call(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    from api.index import app

    holder: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        holder["status"] = status
        holder["headers"] = dict(headers)

    environ = {"REQUEST_METHOD": "GET", "PATH_INFO": path, "QUERY_STRING": query_string,
               "wsgi.input": io.BytesIO(b""), "CONTENT_LENGTH": "0", "SERVER_NAME": "localhost",
               "SERVER_PORT": "80", "wsgi.url_scheme": "https"}
    body = b"".join(app(environ, start_response)).decode("utf-8")
    return str(holder["status"]), holder["headers"], body  # type: ignore[return-value]


class NoDeadEndTests(unittest.TestCase):
    def setUp(self) -> None:
        from picwise_providers.awin_adapter import clear_awin_feed_parse_cache
        from picwise_providers.state import clear_provider_feed_pipeline_cache
        from picwise_search import search_warmup

        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("AWIN_FEED_", "PICWISE_PREPARED", "PICWISE_SHOP_CATALOGUES"))}
        env["AWIN_FEED_FILE"] = str(FIXTURE)
        patch = mock.patch.dict(os.environ, env, clear=True)
        patch.start()
        self.addCleanup(patch.stop)
        for clear in (clear_awin_feed_parse_cache, clear_provider_feed_pipeline_cache):
            clear()
            self.addCleanup(clear)
        self.addCleanup(search_warmup._reset_search_warmup_for_tests)

    def test_a_refused_click_goes_to_its_search_never_to_the_shop(self) -> None:
        status, headers, body = _call("/out/feed", "pid=fx-laptop-oos&q=gaming%20laptop&src=search&rec=0")
        self.assertEqual(status, "302 Found")
        self.assertEqual(headers["Location"], "/search?q=gaming%20laptop&gone=1")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(body, "")
        # The favourites' button carries the search it was saved from.
        status, headers, _body = _call("/out/feed", "pid=gone-long-ago&q=laptop&src=favourites&rec=0")
        self.assertEqual((status, headers["Location"]), ("302 Found", "/search?q=laptop&gone=1"))

    def test_the_search_says_why_above_its_current_choices(self) -> None:
        from picwise_app.app import PRODUCT_GONE_NOTE

        self.assertEqual(PRODUCT_GONE_NOTE, "The product you chose is no longer available.")
        status, _headers, page = _call("/search", "q=laptop&gone=1")
        self.assertEqual(status, "200 OK")
        line = ('<p class="pw-gone-note" role="status"><strong>The product you chose is no longer available.</strong> '
                "Here are the current choices for “laptop”.</p>")
        self.assertIn(line, page)
        # Above the results, which are there as for any search.
        self.assertLess(page.index(line), page.index('<div class="pw-results-head">'))
        self.assertIn('class="pw-card', page)
        _status, _headers, plain = _call("/search", "q=laptop")
        # The style sheet names its class on every page; the line itself only here.
        self.assertNotIn('class="pw-gone-note"', plain)

    def test_the_search_in_the_line_is_escaped(self) -> None:
        _status, _headers, page = _call("/search", "q=laptop%20%3Cb%3E&gone=1")
        self.assertNotIn("<b>”", page)
        if 'class="pw-gone-note"' in page:
            self.assertIn("&lt;b&gt;", page)

    def test_a_click_with_no_search_keeps_its_own_page(self) -> None:
        status, headers, body = _call("/out/feed", "pid=gone-long-ago&src=favourites&rec=0")
        self.assertEqual(status, "200 OK")
        self.assertNotIn("Location", headers)
        self.assertIn("This option is no longer available", body)
        self.assertIn('href="/"', body)


if __name__ == "__main__":
    unittest.main()
