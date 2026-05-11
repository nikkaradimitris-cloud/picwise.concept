from __future__ import annotations

import io
import json
import sys
import threading
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_app import run_local_server  # noqa: E402
from picwise_mvp import run_pickwise_mvp_search_flow  # noqa: E402


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


def _call_local_http(base_url: str, path: str) -> tuple[int, dict[str, str], str]:
    try:
        with urlopen(f"{base_url}{path}") as response:
            body = response.read().decode("utf-8")
            headers = {key: value for key, value in response.headers.items()}
            return int(response.status), headers, body
    except HTTPError as error:
        body = error.read().decode("utf-8")
        headers = {key: value for key, value in error.headers.items()}
        return int(error.code), headers, body


class PickWiseStage3236RuntimeGuardrailsTests(unittest.TestCase):
    def test_local_runtime_handler_exposes_stage32_to_36_routes(self) -> None:
        server = run_local_server(host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base_url = f"http://{host}:{port}"
        try:
            for path in (
                "/health",
                "/",
                "/demo?q=power+bank",
                "/search?q=power+bank",
                "/results?q=power+bank",
                "/picwise-reference",
                "/private-beta-readiness",
                "/best/power-bank-20000mah-for-iphone",
                "/sitemap-buying-pages.xml",
            ):
                status, _headers, _body = _call_local_http(base_url, path)
                self.assertEqual(status, 200)
            missing_status, _missing_headers, missing_body = _call_local_http(base_url, "/not-a-route")
            self.assertEqual(missing_status, 404)
            payload = json.loads(missing_body)
            available_routes = payload.get("available_routes", [])
            for expected_route in ("/search", "/results", "/private-beta-readiness"):
                self.assertIn(expected_route, available_routes)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    def test_local_runtime_server_refuses_second_bind_on_same_port(self) -> None:
        server = run_local_server(host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        _host, port = server.server_address
        try:
            with self.assertRaises(OSError):
                run_local_server(host="127.0.0.1", port=int(port))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    def test_no_owned_inventory_cart_checkout_payment_implementation(self) -> None:
        source = "\n".join(
            [
                (SRC / "picwise_offers" / "source_intake.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_offers" / "eligibility.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_offers" / "recommendation_engine.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_mvp" / "private_beta.py").read_text(encoding="utf-8").lower(),
            ]
        )
        forbidden = ("owned_inventory", "warehouse", "checkout", "cart", "payment", "application_flow")
        self.assertTrue(all(token not in source for token in forbidden))

    def test_no_scraping_or_live_external_api_calls_in_new_stage_modules(self) -> None:
        source = "\n".join(
            [
                (SRC / "picwise_offers" / "fixture_adapter.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_offers" / "import_adapter.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_mvp" / "private_beta.py").read_text(encoding="utf-8").lower(),
            ]
        )
        forbidden = (
            "requests",
            "httpx",
            "urllib.request",
            "beautifulsoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
            "invoke-webrequest",
            "subprocess",
        )
        self.assertTrue(all(token not in source for token in forbidden))

    def test_stage37_is_not_implemented(self) -> None:
        source = "\n".join(
            [
                (SRC / "picwise_offers" / "contracts.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_mvp" / "launch_readiness.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_surface" / "mvp_search_results.py").read_text(encoding="utf-8").lower(),
            ]
        )
        self.assertNotIn("stage37", source)

    def test_sitemap_and_noindex_safety_is_preserved(self) -> None:
        status, _headers, sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status, "200 OK")
        root = ET.fromstring(sitemap)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = [node.text or "" for node in root.findall("sm:url/sm:loc", ns)]
        self.assertTrue(all("/best/" in value for value in loc_values))
        search_status, _search_headers, search_body = _call_wsgi("/search", "q=power+bank")
        self.assertEqual(search_status, "200 OK")
        self.assertIn('content="noindex, nofollow"', search_body)

    def test_finance_regulated_cases_do_not_auto_decide_quotes_or_approval(self) -> None:
        flow = run_pickwise_mvp_search_flow("loan insurance comparison")
        self.assertEqual(flow.state, "manual_review")
        self.assertIsNone(flow.recommendation_set.wise_recommended_product)
        self.assertIn("finance_vertical_manual_review_only", flow.reason_codes)


if __name__ == "__main__":
    unittest.main()
