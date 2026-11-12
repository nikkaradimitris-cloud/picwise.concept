"""What every answer tells the browser to refuse (the audit, 2026-11-10; owner, the same
day: «Ζητώ διόρθωση και βελτίωση ... την ασφάλεια»).

The audit found the live site sending only `Strict-Transport-Security`, from its front
door: no content security policy, nothing against another site showing PicWise's pages
inside its own, and the preparation's public note (`prepared.json`) open to Google's
index. Pinned here, through both route tables and the server's own entry point
(`picwise_app.app.SECURITY_HEADERS`, `api/index.py`, `deployment/server/wsgi_server.py`):

- every answer carries the same five headers: a page, a JSON answer, a file, a page not
  found, a method refused, and the redirect to a shop;
- the policy lets a page do what it does and nothing else: its own scripts and styles,
  the shops' photos, requests to the site only, no frame, no plug-in, no form sent away;
- a page asks for nothing the policy would refuse;
- the redirect to a shop is never kept by a browser or a cache;
- the site's own files and the pages that say who runs PicWise may be kept a while; a
  search's page never says so;
- the server's public note is kept out of Google like every other JSON answer.

Rendered in a browser with these headers (2026-11-10, phone and computer): nothing
refused; the cards, the suggestions and the favourites worked.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import test_picwise_google_protection as protection  # noqa: E402
from api.index import app as deployment_app  # noqa: E402
from picwise_app.app import (  # noqa: E402
    ASSET_CACHE_CONTROL,
    CONTENT_SECURITY_POLICY,
    INFO_PAGE_CACHE_CONTROL,
    SECURITY_HEADERS,
)
from test_picwise_google_protection import _call_wsgi, _NoFeedMixin  # noqa: E402
from test_picwise_prepared_catalogue import _PreparedMixin, _feed_rows  # noqa: E402

_NAMES = (
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
)


def _call(path: str, query: str = "", method: str = "GET") -> tuple[str, dict[str, str], bytes]:
    held: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        held["status"], held["headers"] = status, dict(headers)

    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query, "HTTP_HOST": "localhost"}
    body = b"".join(deployment_app(environ, start_response))
    return str(held["status"]), dict(held["headers"]), body  # type: ignore[arg-type]


class TheHeadersTests(unittest.TestCase):
    def test_the_five_headers(self) -> None:
        self.assertEqual(tuple(name for name, _value in SECURITY_HEADERS), _NAMES)
        headers = dict(SECURITY_HEADERS)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        # The microphone, for the search by voice, on the site's own pages only.
        self.assertIn("microphone=(self)", headers["Permissions-Policy"])
        for refused in ("camera=()", "geolocation=()", "payment=()"):
            self.assertIn(refused, headers["Permissions-Policy"])

    def test_the_policy_lets_a_page_do_what_it_does_and_nothing_else(self) -> None:
        policy = {
            part.split()[0]: part.split()[1:] for part in CONTENT_SECURITY_POLICY.split(";") if part.strip()
        }
        self.assertEqual(policy["default-src"], ["'self'"])
        self.assertEqual(policy["script-src"], ["'self'", "'unsafe-inline'"])
        self.assertEqual(policy["style-src"], ["'self'", "'unsafe-inline'"])
        # A shop's photo comes from the shop's server, at the address its feed gives.
        self.assertEqual(policy["img-src"], ["'self'", "https:", "http:", "data:"])
        self.assertEqual(policy["connect-src"], ["'self'"])
        self.assertEqual(policy["form-action"], ["'self'"])
        for directive in ("object-src", "base-uri", "frame-ancestors"):
            self.assertEqual(policy[directive], ["'none'"], directive)
        for never in ("unsafe-eval", "*"):
            self.assertNotIn(never, CONTENT_SECURITY_POLICY)


class EveryAnswerTests(_NoFeedMixin, unittest.TestCase):
    def test_every_answer_of_the_deployment_carries_them(self) -> None:
        answers = (
            ("/", "", "GET", "200 OK"),
            ("/search", "q=kettle", "GET", "200 OK"),
            ("/about", "", "GET", "200 OK"),
            ("/demo", "", "GET", "200 OK"),
            ("/health", "", "GET", "200 OK"),
            ("/suggest.json", "", "GET", "200 OK"),
            ("/robots.txt", "", "GET", "200 OK"),
            # No sitemap while nothing is declared to Google (owner, 2026-11-12).
            ("/sitemap.xml", "", "GET", "404 Not Found"),
            ("/assets/picwise/favicon.svg", "", "GET", "200 OK"),
            ("/no-such-page", "", "GET", "404 Not Found"),
            ("/out/feed", "pid=no-such-product&q=kettle", "GET", "200 OK"),
            ("/search", "q=kettle", "POST", "405 Method Not Allowed"),
        )
        for path, query, method, expected in answers:
            with self.subTest(path=path, method=method):
                status, headers, _body = _call(path, query, method)
                self.assertEqual(status, expected)
                for name, value in SECURITY_HEADERS:
                    self.assertEqual(headers.get(name), value, name)

    def test_a_page_asks_for_nothing_the_policy_would_refuse(self) -> None:
        for path, query in (("/", ""), ("/search", "q=kettle"), ("/about", ""), ("/demo", "")):
            with self.subTest(path=path):
                _status, _headers, body = _call_wsgi(path, query)
                # No script, style or frame from another site; no plug-in; forms sent here.
                self.assertEqual(re.findall(r"<script[^>]*\ssrc=", body), [])
                self.assertEqual(re.findall(r'<link[^>]*rel="stylesheet"', body), [])
                self.assertEqual(re.findall(r"<(?:iframe|object|embed|base)\b", body), [])
                self.assertEqual(
                    [action for action in re.findall(r'<form[^>]*action="([^"]*)"', body) if not action.startswith("/")],
                    [],
                )
                for address in re.findall(r'<link[^>]*href="([^"]*)"', body):
                    self.assertTrue(address.startswith("/") or address.startswith("https://picwise.subby.cloud/"), address)

    def test_what_may_be_kept_a_while_and_what_never_says_so(self) -> None:
        self.assertEqual(_call("/assets/picwise/favicon.svg")[1].get("Cache-Control"), ASSET_CACHE_CONTROL)
        for path in ("/about", "/terms", "/privacy", "/cookies", "/affiliate-disclosure", "/contact"):
            with self.subTest(path=path):
                self.assertEqual(_call(path)[1].get("Cache-Control"), INFO_PAGE_CACHE_CONTROL)
        # A search's page is the catalogue's of that moment; the home page says nothing either.
        for path, query in (("/search", "q=kettle"), ("/", "q=kettle"), ("/", "")):
            with self.subTest(path=path, query=query):
                self.assertNotIn("Cache-Control", _call(path, query)[1])


class TheRedirectTests(_PreparedMixin, unittest.TestCase):
    def test_the_redirect_to_a_shop_carries_them_and_is_never_kept(self) -> None:
        self._write_feed(_feed_rows())
        status, headers, body = _call("/out/feed", "pid=k1&q=kettle&src=search&rec=0")
        self.assertEqual(status, "302 Found")
        self.assertEqual(headers["Location"], "https://fixture.example.invalid/out/k1")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(body, b"")
        for name, value in SECURITY_HEADERS:
            self.assertEqual(headers.get(name), value, name)


class LocalServerHeadersTests(protection.LocalServerTests):
    """The local server answers the same (`picwise_app.app`)."""

    # The protection tests of the class this borrows its server from run in their module.
    test_every_search_page_carries_noindex = None
    test_the_home_page_and_the_demo = None
    test_robots_txt_is_the_deployments = None
    test_json_routes_are_kept_out_of_the_index = None

    def test_every_answer_of_the_local_server_carries_them(self) -> None:
        for path in ("/", "/search?q=kettle", "/about", "/health", "/robots.txt", "/assets/picwise/favicon.svg"):
            with self.subTest(path=path):
                status, headers, _body = self._get(path)
                self.assertEqual(status, 200)
                for name, value in SECURITY_HEADERS:
                    self.assertEqual(headers.get(name), value, name)
        _status, headers, _body = self._get("/assets/picwise/favicon.svg")
        self.assertEqual(headers.get("Cache-Control"), ASSET_CACHE_CONTROL)


class TheServersPublicNoteTests(unittest.TestCase):
    def _server(self, folder: Path):
        saved = os.environ.get("PICWISE_STATIC_DIR")
        os.environ["PICWISE_STATIC_DIR"] = str(folder)
        self.addCleanup(
            lambda: os.environ.pop("PICWISE_STATIC_DIR", None)
            if saved is None
            else os.environ.__setitem__("PICWISE_STATIC_DIR", saved)
        )
        spec = importlib.util.spec_from_file_location(
            "picwise_wsgi_server_under_test", ROOT / "deployment" / "server" / "wsgi_server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_the_note_is_kept_out_of_google_and_carries_the_headers(self) -> None:
        folder = Path(tempfile.mkdtemp())
        (folder / "prepared.json").write_text(json.dumps({"prepared": True, "products": 3}), encoding="utf-8")
        server = self._server(folder)
        held: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            held["status"], held["headers"] = status, dict(headers)

        body = b"".join(
            server.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/prepared.json", "QUERY_STRING": ""}, start_response)
        )
        headers = held["headers"]
        self.assertEqual(held["status"], "200 OK")
        self.assertEqual(json.loads(body), {"prepared": True, "products": 3})
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["X-Robots-Tag"], "noindex")
        for name, value in SECURITY_HEADERS:
            self.assertEqual(headers.get(name), value, name)
        # Anything else is the app's answer, as before.
        b"".join(server.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/health", "QUERY_STRING": ""}, start_response))
        self.assertEqual(held["status"], "200 OK")
        self.assertEqual(held["headers"]["X-Robots-Tag"], "noindex")


if __name__ == "__main__":
    unittest.main()
