from __future__ import annotations

import io
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_app.buying_routes import get_buying_pages_repository  # noqa: E402
from picwise_buying_pages.index_gate import evaluate_index_gate  # noqa: E402


def _call_wsgi(path: str) -> tuple[str, dict[str, str], str]:
    status_holder: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = {key: value for key, value in headers}

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
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


class BuyingPagesSitemapTests(unittest.TestCase):
    def test_sitemap_route_returns_xml(self) -> None:
        status, headers, body = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/xml; charset=utf-8")
        self.assertIn("<?xml", body)
        self.assertIn("<urlset", body)

    def test_sitemap_includes_only_indexable_pages(self) -> None:
        _status, _headers, body = _call_wsgi("/sitemap-buying-pages.xml")
        root = ET.fromstring(body)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = [node.text or "" for node in root.findall("sm:url/sm:loc", ns)]

        pages = get_buying_pages_repository().list_pages()
        indexable_slugs = sorted(
            page.slug for page in pages if evaluate_index_gate(page).indexable
        )
        expected_urls = [f"https://localhost/best/{slug}" for slug in indexable_slugs]
        self.assertEqual(loc_values, expected_urls)

    def test_sitemap_excludes_protected_routes_and_is_sorted(self) -> None:
        _status, _headers, body = _call_wsgi("/sitemap-buying-pages.xml")
        root = ET.fromstring(body)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = [node.text or "" for node in root.findall("sm:url/sm:loc", ns)]
        disallowed = (
            "https://localhost/picwise-reference",
            "https://localhost/demo",
            "https://localhost/health",
            "https://localhost/subby-proof",
        )
        for route in disallowed:
            self.assertNotIn(route, loc_values)
        self.assertEqual(loc_values, sorted(loc_values))


if __name__ == "__main__":
    unittest.main()
