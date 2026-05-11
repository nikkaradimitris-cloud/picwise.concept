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
        self.assertIn("PickWise MVP Search", body)
        self.assertIn('content="noindex, nofollow"', body)
        self.assertIn("Detected intent/category", body)
        self.assertIn("Recommendation status", body)
        self.assertTrue(
            ("Wise Recommended Product" in body)
            or ("wise recommendation is withheld" in body.lower())
            or ("Outbound contract:</strong> not_available" in body)
        )

    def test_search_route_handles_no_data_honestly(self) -> None:
        status, _headers, body = _call_wsgi("/search", f"q={quote('   ')}")
        self.assertEqual(status, "200 OK")
        self.assertIn("No result state", body)
        self.assertIn("needs_data", body)
        self.assertNotIn("checkout", body.lower())
        self.assertNotIn("fake revenue", body.lower())

    def test_core_existing_routes_remain_healthy(self) -> None:
        for path in ("/health", "/", "/demo", "/picwise-reference", "/sitemap-buying-pages.xml"):
            status, _headers, _body = _call_wsgi(path)
            self.assertEqual(status, "200 OK")


if __name__ == "__main__":
    unittest.main()
