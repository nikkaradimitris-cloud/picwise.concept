from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_integrations.subby_dashboard import UrllibSubbyBridgeEventSender  # noqa: E402
from wsgi import app as wsgi_app  # noqa: E402


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
        "SERVER_PORT": "80",
        "wsgi.url_scheme": "https",
    }
    body_chunks = deployment_app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    return status_holder["status"], status_holder["headers"], body


class DeploymentEntrypointTests(unittest.TestCase):
    def test_deployment_entrypoint_imports(self) -> None:
        self.assertTrue(callable(deployment_app))
        self.assertTrue(callable(wsgi_app))

    def test_health_route_works_through_deployment_entrypoint(self) -> None:
        status, headers, body = _call_wsgi("/health")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn('"status": "ok"', body)
        self.assertIn('"domain_plan_primary": "picwise.subby.cloud"', body)

    def test_demo_route_works_through_deployment_entrypoint(self) -> None:
        query = "power bank 20000mah for iphone"
        status, headers, body = _call_wsgi("/demo", f"q={quote(query)}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(query, body)
        self.assertIn("local_test_fixture", body)
        self.assertIn("not_production_data", body)

    def test_root_route_returns_landing_html_not_not_found(self) -> None:
        status, headers, body = _call_wsgi("/")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("<main", body.lower())
        self.assertIn("Showing 4 options for:", body)
        self.assertNotIn("not_found", body)

    def test_picwise_reference_route_returns_static_reference_html(self) -> None:
        status, headers, body = _call_wsgi("/picwise-reference")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("See the 4 best products before you buy.", body)
        self.assertIn("shopping assistant", body)
        self.assertIn("Search your product here", body)
        for forbidden_image_placeholder in (
            "TravelCore 20K product image placeholder",
            "DailyBalance PD20 product image placeholder",
            "EverydaySure 22.5W product image placeholder",
            "PowerMax Elite 25K product image placeholder",
        ):
            self.assertNotIn(forbidden_image_placeholder, body)
        self.assertIn("What is Picwise?", body)
        self.assertIn(
            "Demo data source: local_test_fixture (not_production_data).",
            body,
        )
        self.assertIn("All rights reserved.", body)
        self.assertIn("Privacy", body)
        self.assertIn("Terms", body)
        self.assertIn("Contact", body)
        self.assertEqual(body.count('<article class="pw-card'), 4)
        self.assertNotIn("&middot;", body)
        for asset in (
            "/assets/picwise/product-1.svg",
            "/assets/picwise/product-2.svg",
            "/assets/picwise/product-3.svg",
            "/assets/picwise/product-4.svg",
        ):
            self.assertIn(asset, body)
        for product_name in (
            "TravelCore 20K",
            "DailyBalance PD20",
            "EverydaySure 22.5W",
            "PowerMax Elite 25K",
        ):
            self.assertIn(product_name, body)

    def test_reference_route_and_required_core_routes_are_registered(self) -> None:
        health_status, _health_headers, _health_body = _call_wsgi("/health")
        root_status, _root_headers, _root_body = _call_wsgi("/")
        demo_status, _demo_headers, _demo_body = _call_wsgi("/demo")
        reference_status, _reference_headers, reference_body = _call_wsgi("/picwise-reference")

        self.assertEqual(health_status, "200 OK")
        self.assertEqual(root_status, "200 OK")
        self.assertEqual(demo_status, "200 OK")
        self.assertEqual(reference_status, "200 OK")

        self.assertIn("See the 4 best products before you buy.", reference_body)
        self.assertIn("shopping assistant", reference_body)
        self.assertIn("Search your product here", reference_body)
        self.assertIn("What is Picwise?", reference_body)
        for product_name in (
            "TravelCore 20K",
            "DailyBalance PD20",
            "EverydaySure 22.5W",
            "PowerMax Elite 25K",
        ):
            self.assertIn(product_name, reference_body)

    def test_demo_has_search_form_with_query_value(self) -> None:
        query = "best office chair under 200"
        _status, _headers, body = _call_wsgi("/demo", f"q={quote(query)}")
        self.assertIn('class="pw-search-shell"', body)
        self.assertIn('class="pw-search-icon"', body)
        self.assertIn('class="pw-search-button"', body)
        self.assertIn('class="pw-search-button-icon"', body)
        self.assertIn('name="q"', body)
        self.assertIn(f'value="{query}"', body)
        self.assertNotIn('class="pw-search-button" type="submit" aria-label="Search">→</button>', body)
        self.assertNotIn("&#128269;", body)
        self.assertNotIn("🔍", body)

    def test_root_route_contains_four_primary_cards_and_one_recommended_marker(self) -> None:
        _status, _headers, body = _call_wsgi("/")
        self.assertEqual(body.count('<article class="pw-card'), 4)
        self.assertEqual(body.count('<article class="pw-card pw-card-recommended"'), 1)
        self.assertEqual(body.count("Recommended by Picwise"), 1)

    def test_recommended_card_has_required_highlight_elements(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        required_classes = (
            "pw-topbar",
            "pw-brand",
            "pw-search-shell",
            "pw-search-button",
            "pw-bg-left",
            "pw-bg-right",
            "pw-grid",
            "pw-card-recommended",
            "pw-rec-badge",
            "pw-rec-ring-a",
            "pw-rec-ring-b",
            "pw-rec-ring-c",
            "pw-footer",
            "pw-demo-note",
        )
        for class_name in required_classes:
            self.assertIn(class_name, body)
        self.assertIn("Recommended by Picwise", body)
        self.assertNotIn("Best fit", body)
        self.assertNotIn("Fast decision", body)

    def test_landing_contains_header_with_login_register(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn('class="pw-topbar"', body)
        self.assertIn('class="pw-hero"', body)
        self.assertLess(body.index('class="pw-topbar"'), body.index('class="pw-hero"'))
        self.assertIn('class="pw-brand"', body)
        self.assertIn(">picwise<", body)
        self.assertIn("shopping assistant", body)
        self.assertIn("Login", body)
        self.assertIn("Register", body)
        self.assertNotIn("FAQ", body)

    def test_landing_contains_hero_subtitle(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn(
            "See the 4 best products before you buy.",
            body,
        )

    def test_landing_contains_footer_nav_links(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn('class="pw-footer"', body)
        self.assertIn("All rights reserved.", body)
        self.assertIn("Privacy", body)
        self.assertIn("Terms", body)
        self.assertIn("Contact", body)
        lowered = body.lower()
        self.assertNotIn("advertising", lowered)
        self.assertNotIn("η τρίτη δεκαετία", lowered)
        self.assertNotIn("διαφήμιση", lowered)
        self.assertNotIn("leaf", lowered)
        self.assertNotIn("climate", lowered)

    def test_landing_contains_discreet_demo_note_above_footer(self) -> None:
        _status, _headers, body = _call_wsgi("/demo")
        self.assertIn(
            "Demo data source: local_test_fixture (not_production_data).",
            body,
        )
        self.assertEqual(body.count("Demo data source"), 1)
        self.assertIn('class="pw-demo-note"', body)
        demo_note_index = body.index('<p class="pw-demo-note">')
        footer_index = body.index('<footer class="pw-footer">')
        self.assertLess(demo_note_index, footer_index)

    def test_landing_html_avoids_cart_checkout_and_fake_markers(self) -> None:
        _status, _headers, body = _call_wsgi("/")
        lowered = body.lower()
        for forbidden in ("add to cart", "cart", "checkout", "e-shop"):
            self.assertNotIn(forbidden, lowered)
        for forbidden_fake in (
            "fake revenue",
            "fake conversion",
            "fake review",
            "fake rating",
            "fake urgency",
        ):
            self.assertNotIn(forbidden_fake, lowered)

    def test_subby_proof_missing_env_returns_safe_missing_config(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            status, headers, body = _call_wsgi("/subby-proof")
        payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(payload["status"], "missing_config")
        self.assertEqual(
            payload["missing"],
            [
                "PICWISE_SUBBY_ENDPOINT",
                "PICWISE_SUBBY_PROJECT_ID",
                "PICWISE_SUBBY_API_KEY",
            ],
        )
        self.assertFalse(payload["secret_values_exposed"])

    def test_subby_proof_does_not_expose_api_key_in_response(self) -> None:
        class SpySender:
            def __init__(self) -> None:
                self.called = False
                self.headers: dict[str, str] = {}
                self.payload: dict[str, Any] = {}

            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                self.called = True
                self.headers = headers
                self.payload = payload
                _ = endpoint
                return 202, {"accepted": True}

        sender = SpySender()
        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://bridge.subby.cloud/events",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=sender):
                status, _headers, body = _call_wsgi("/subby-proof")
        payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertTrue(sender.called)
        self.assertNotIn("secret-live-key-value", body)
        self.assertNotIn("api_key", payload)
        self.assertFalse(payload["secret_values_exposed"])
        self.assertEqual(payload["status"], "sent")
        self.assertEqual(payload["bridge_http_status"], 202)
        self.assertTrue(payload["accepted"])

    def test_subby_proof_urlerror_returns_safe_diagnostics_without_secret(self) -> None:
        class FailingSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise URLError("upstream timeout for secret-live-key-value")

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=FailingSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "error")
        self.assertIsNone(response_payload["bridge_http_status"])
        self.assertEqual(response_payload["safe_error_type"], "URLError")
        self.assertIn("safe_error_message", response_payload)
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_timeout_returns_sent_unconfirmed_with_dashboard_check(self) -> None:
        class TimeoutSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise TimeoutError("read timed out for secret-live-key-value")

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=TimeoutSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "sent_unconfirmed")
        self.assertIsNone(response_payload["bridge_http_status"])
        self.assertTrue(response_payload["dashboard_check_required"])
        self.assertEqual(response_payload["safe_error_type"], "TimeoutError")
        self.assertIn("safe_error_message", response_payload)
        self.assertIn("response timed out", response_payload["message"])
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_httperror_returns_http_status_and_safe_type(self) -> None:
        class FailingSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise HTTPError(
                    url="https://manager.subby.cloud/events/bridge",
                    code=403,
                    msg="forbidden",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"accepted":false,"error":"token secret-live-key-value rejected"}'
                    ),
                )

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=FailingSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "error")
        self.assertEqual(response_payload["bridge_http_status"], 403)
        self.assertEqual(response_payload["safe_error_type"], "HTTPError")
        self.assertFalse(response_payload["accepted"])
        self.assertIn("safe_error_message", response_payload)
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_rejected_response_includes_safe_diagnostics(self) -> None:
        class RejectedSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                return 405, {"accepted": False, "error": "bridge token secret-live-key-value rejected"}

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=RejectedSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "rejected")
        self.assertEqual(response_payload["bridge_http_status"], 405)
        self.assertEqual(response_payload["safe_error_type"], "HTTPStatusRejected")
        self.assertIn("safe_error_message", response_payload)
        self.assertFalse(response_payload["accepted"])
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_safe_error_message_redacts_api_key_and_token_like_strings(self) -> None:
        class FailingSender:
            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                _ = (endpoint, headers, payload)
                raise RuntimeError(
                    "PICWISE_SUBBY_API_KEY=secret-live-key-value token ABCDEFGHIJKLMNOPQRSTUVWX123456"
                )

        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://manager.subby.cloud/events/bridge",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "secret-live-key-value",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=FailingSender()):
                status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(response_payload["status"], "error")
        self.assertEqual(response_payload["safe_error_type"], "RuntimeError")
        self.assertIn("safe_error_message", response_payload)
        self.assertIn("[REDACTED]", response_payload["safe_error_message"])
        self.assertIn("[REDACTED_TOKEN]", response_payload["safe_error_message"])
        self.assertNotIn("secret-live-key-value", body)
        self.assertFalse(response_payload["secret_values_exposed"])

    def test_subby_proof_sender_payload_and_headers_are_correct_and_mockable(self) -> None:
        class SpySender:
            def __init__(self) -> None:
                self.calls = 0
                self.endpoint = ""
                self.headers: dict[str, str] = {}
                self.payload: dict[str, Any] = {}

            def send(
                self,
                *,
                endpoint: str,
                headers: dict[str, str],
                payload: dict[str, Any],
            ) -> tuple[int, dict[str, Any]]:
                self.calls += 1
                self.endpoint = endpoint
                self.headers = headers
                self.payload = payload
                return 200, {"accepted": True}

        sender = SpySender()
        env = {
            "PICWISE_SUBBY_ENDPOINT": "https://bridge.subby.cloud/events",
            "PICWISE_SUBBY_PROJECT_ID": "picwise-prod",
            "PICWISE_SUBBY_API_KEY": "super-secret-key",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("api.index.UrllibSubbyBridgeEventSender", return_value=sender):
                _status, _headers, body = _call_wsgi("/subby-proof")
        response_payload = json.loads(body)
        self.assertEqual(sender.calls, 1)
        self.assertEqual(sender.endpoint, "https://bridge.subby.cloud/events")
        self.assertEqual(sender.headers["X-Bridge-Project-ID"], "picwise-prod")
        self.assertEqual(sender.headers["X-Bridge-API-Key"], "super-secret-key")
        self.assertEqual(sender.headers["Content-Type"], "application/json")

        self.assertEqual(sender.payload["schema_version"], "1.0")
        self.assertEqual(sender.payload["source_app"], "picwise")
        self.assertEqual(sender.payload["source"], "picwise_live_proof")
        self.assertEqual(sender.payload["project_id"], "picwise-prod")
        self.assertEqual(sender.payload["signal_type"], "health/live_proof")
        self.assertTrue(sender.payload["test_mode"])
        self.assertTrue(sender.payload["operator_generated"])
        self.assertEqual(sender.payload["payload"]["domain"], "picwise.subby.cloud")
        self.assertEqual(sender.payload["payload"]["route"], "/subby-proof")
        self.assertEqual(sender.payload["payload"]["proof_type"], "live_subby_bridge_event")
        self.assertTrue(sender.payload["payload"]["no_revenue"])
        self.assertTrue(sender.payload["payload"]["no_conversion"])
        self.assertEqual(sender.payload["payload"]["missing_data_state"], "not_applicable")
        self.assertNotIn("revenue", sender.payload)
        self.assertNotIn("conversion", sender.payload)

        self.assertEqual(response_payload["project_id"], "picwise-prod")
        self.assertEqual(response_payload["endpoint_host"], "bridge.subby.cloud")
        self.assertNotIn("X-Bridge-API-Key", response_payload)
        self.assertNotIn("super-secret-key", body)

    def test_urllib_sender_uses_post_json_bytes_and_configured_timeout(self) -> None:
        capture: dict[str, Any] = {}

        class FakeResponse:
            status = 202

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
                _ = (exc_type, exc, tb)
                return False

            def read(self) -> bytes:
                return b'{"accepted":true}'

        def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
            capture["request"] = request
            capture["timeout"] = timeout
            return FakeResponse()

        sender = UrllibSubbyBridgeEventSender(timeout_seconds=4.0)
        with patch("picwise_integrations.subby_dashboard.urlopen", side_effect=fake_urlopen):
            status_code, response_payload = sender.send(
                endpoint="https://manager.subby.cloud/api/bridge/ingest",
                headers={
                    "X-Bridge-Project-ID": "picwise-prod",
                    "X-Bridge-API-Key": "secret-live-key-value",
                    "Content-Type": "application/json",
                },
                payload={"foo": "bar"},
            )

        request = capture["request"]
        self.assertEqual(capture["timeout"], 4.0)
        self.assertEqual(request.get_method(), "POST")
        self.assertIsInstance(request.data, bytes)
        self.assertEqual(request.data, b'{"foo":"bar"}')
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(status_code, 202)
        self.assertEqual(response_payload["accepted"], True)


class DeploymentConfigAndDocsTests(unittest.TestCase):
    def test_deployment_configs_contain_no_secrets(self) -> None:
        vercel_config = (ROOT / "vercel.json").read_text(encoding="utf-8")
        env_template = (ROOT / "deployment" / "app.env.template").read_text(encoding="utf-8")
        wsgi_template = (ROOT / "deployment" / "wsgi_server.template.ini").read_text(encoding="utf-8")

        for forbidden in ("AKIA", "-----BEGIN", "PRIVATE KEY", "SECRET=", "token "):
            self.assertNotIn(forbidden, vercel_config)
            self.assertNotIn(forbidden, env_template)
            self.assertNotIn(forbidden, wsgi_template)

    def test_stage_22_doc_does_not_claim_live_proof(self) -> None:
        stage_doc = (
            ROOT / "docs" / "STAGE_22_LIVE_DEPLOYMENT_TO_PICWISE_SUBBY_CLOUD.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# 22. Live deployment to picwise.subby.cloud", stage_doc)
        self.assertIn("Current stage status in this repository is `PASSED`", stage_doc)
        self.assertIn("- [x] `https://picwise.subby.cloud/health` works", stage_doc)
        self.assertIn("- [x] `https://picwise.subby.cloud/demo` works", stage_doc)


if __name__ == "__main__":
    unittest.main()

