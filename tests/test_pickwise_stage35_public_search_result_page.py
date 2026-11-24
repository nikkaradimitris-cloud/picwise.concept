from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_surface import home_store  # noqa: E402


def _call_wsgi(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    status_holder: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = {key: value for key, value in headers}

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
    body_chunks = deployment_app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    return status_holder["status"], status_holder["headers"], body


class PickWiseStage35PublicSearchResultPageTests(unittest.TestCase):
    def test_search_route_renders_public_result_surface_with_noindex(self) -> None:
        status, headers, body = _call_wsgi("/search", f"q={quote('power bank for iphone')}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("picwise", body.lower())
        # Amazon has been removed from the product, so this query no longer takes a
        # manual connected-provider path. With no provider feed configured here the
        # public surface must stay honestly empty rather than render anything.
        self.assertNotIn("Safe connected provider mode", body)
        self.assertNotIn("manual_amazon_affiliate", body)
        self.assertNotIn("View on Amazon", body)
        self.assertIn("No products found for \u201cpower bank for iphone\u201d.", body)
        self.assertIn('data-card-count="0"', body)
        self.assertNotIn("fake product", body.lower())
        self.assertNotIn("checkout", body.lower())

    def test_search_route_handles_no_data_honestly(self) -> None:
        # This pins today's page of 2026-11-12, which since the owner's «ανέβασε» of 2026-11-24 is the home page with the store's switch off (the way back); the same guarantees on the store's pages: tests/test_picwise_home_store_live.py.
        home_store.set_home_store_on_for_tests(False)
        self.addCleanup(home_store.set_home_store_on_for_tests, None)
        status, _headers, body = _call_wsgi("/search", f"q={quote('   ')}")
        self.assertEqual(status, "200 OK")
        # A search of blanks is the page without a search (the design of 2026-10-31):
        # what PicWise is, and no cards at all.
        self.assertIn('<h1 class="pw-hero-title">Find the product you want in UK shops</h1>', body)
        self.assertNotIn("<article", body)
        self.assertNotIn("manual_amazon_affiliate", body)
        self.assertNotIn("provider_not_connected", body)
        self.assertNotIn("not_understood", body)
        self.assertNotIn("checkout", body.lower())
        self.assertNotIn("fake revenue", body.lower())

    def test_core_existing_routes_remain_healthy(self) -> None:
        for path in ("/health", "/", "/demo", "/picwise-reference", "/sitemap-buying-pages.xml"):
            status, _headers, _body = _call_wsgi(path)
            self.assertEqual(status, "200 OK")

    def test_results_route_for_unrelated_query_stays_safe_and_non_leaky(self) -> None:
        status, headers, body = _call_wsgi("/results", f"q={quote('wireless earbuds')}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn('data-card-count="0"', body)
        self.assertIn("No products found for \u201cwireless earbuds\u201d.", body)
        self.assertNotIn("power bank", body.lower())
        self.assertNotIn("manual_amazon_affiliate", body)


if __name__ == "__main__":
    unittest.main()
