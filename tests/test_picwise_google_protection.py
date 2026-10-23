"""What Google may index while the site is being built (owner, 2026-10-23).

«Ναι, βάλε το noindex στο /search και προστάτεψε το site από την google όσο το
χτίζουμε». Pinned here, through both route tables (the deployment's `api/index.py` and
the local server):

- every page that shows a search carries `noindex`: /search, /results,
  /picwise-reference and the home page with a query (`/?q=...`); the home page without
  one does not;
- the demo page, a preview, carries `noindex`;
- `/robots.txt` keeps crawlers off the redirect to the shops (it records a click) and
  off the two routes that act when called, and does not block the search yet: Google
  reads a page's `noindex` only on a page it may fetch
  (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 2);
- the JSON routes answer with `X-Robots-Tag: noindex`.
"""
from __future__ import annotations

import io
import os
import socket
import sys
import threading
import unittest
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as deployment_app  # noqa: E402
from picwise_app import run_local_server  # noqa: E402
from picwise_search import search_warmup  # noqa: E402

_NOINDEX = '<meta name="robots" content="noindex">'
_SEARCH_PAGES = (
    ("/search", "q=kettle"),
    ("/search", "q=kettle&shown=8"),
    ("/search", ""),
    ("/results", "q=kettle"),
    ("/picwise-reference", "q=kettle"),
    ("/", "q=kettle"),
)
_JSON_ROUTES = ("/health", "/suggest.json", "/private-beta-readiness")


def _call_wsgi(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    held: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        held["status"] = status
        held["headers"] = dict(headers)

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "443",
        "HTTP_HOST": "localhost",
        "wsgi.url_scheme": "https",
    }
    body = b"".join(deployment_app(environ, start_response)).decode("utf-8")
    return held["status"], held["headers"], body


def _open_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class _NoFeedMixin:
    def setUp(self) -> None:
        # No feed: these tests are about what each answer tells Google, not its cards.
        self._saved = {key: os.environ.pop(key, None) for key in ("AWIN_FEED_URL", "AWIN_FEED_FILE")}

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is not None:
                os.environ[key] = value
        search_warmup._reset_search_warmup_for_tests()


class DeploymentRoutesTests(_NoFeedMixin, unittest.TestCase):
    def test_every_search_page_carries_noindex(self) -> None:
        for path, query in _SEARCH_PAGES:
            with self.subTest(path=path, query=query):
                status, _headers, body = _call_wsgi(path, query)
                self.assertEqual(status, "200 OK")
                self.assertIn(_NOINDEX, body)

    def test_the_home_page_without_a_search_may_be_indexed(self) -> None:
        for query in ("", "q=", "q=%20%20"):
            with self.subTest(query=query):
                status, _headers, body = _call_wsgi("/", query)
                self.assertEqual(status, "200 OK")
                self.assertNotIn("noindex", body)

    def test_the_demo_page_carries_noindex(self) -> None:
        status, _headers, body = _call_wsgi("/demo")
        self.assertEqual(status, "200 OK")
        self.assertIn(_NOINDEX, body)

    def test_robots_txt_keeps_crawlers_off_the_shop_redirect_and_not_off_the_search(self) -> None:
        status, headers, body = _call_wsgi("/robots.txt")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        rules = [line.strip() for line in body.splitlines() if line.strip()]
        self.assertEqual(rules[0], "User-agent: *")
        self.assertEqual(
            sorted(rules[1:]), ["Disallow: /cron/", "Disallow: /out/", "Disallow: /subby-proof"]
        )

    def test_json_routes_are_kept_out_of_the_index(self) -> None:
        for path in _JSON_ROUTES:
            with self.subTest(path=path):
                status, headers, _body = _call_wsgi(path)
                self.assertEqual(status, "200 OK")
                self.assertEqual(headers.get("X-Robots-Tag"), "noindex")

    def test_pages_carry_no_robots_header(self) -> None:
        # A page says it in its HTML; a header would also cover the home page.
        for path in ("/", "/search", "/terms"):
            with self.subTest(path=path):
                _status, headers, _body = _call_wsgi(path, "q=kettle" if path == "/search" else "")
                self.assertNotIn("X-Robots-Tag", headers)


class LocalServerTests(_NoFeedMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _open_port()
        cls.server = run_local_server(host="127.0.0.1", port=cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _get(self, path: str) -> tuple[int, dict[str, str], str]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=60) as response:
            return response.status, dict(response.headers.items()), response.read().decode("utf-8")

    def test_every_search_page_carries_noindex(self) -> None:
        for path, query in _SEARCH_PAGES:
            with self.subTest(path=path, query=query):
                status, _headers, body = self._get(f"{path}?{query}" if query else path)
                self.assertEqual(status, 200)
                self.assertIn(_NOINDEX, body)

    def test_the_home_page_and_the_demo(self) -> None:
        _status, _headers, home = self._get("/")
        self.assertNotIn("noindex", home)
        _status, _headers, demo = self._get("/demo")
        self.assertIn(_NOINDEX, demo)

    def test_robots_txt_is_the_deployments(self) -> None:
        status, headers, body = self._get("/robots.txt")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(body, _call_wsgi("/robots.txt")[2])

    def test_json_routes_are_kept_out_of_the_index(self) -> None:
        for path in _JSON_ROUTES:
            with self.subTest(path=path):
                status, headers, _body = self._get(path)
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("X-Robots-Tag"), "noindex")


if __name__ == "__main__":
    unittest.main()
