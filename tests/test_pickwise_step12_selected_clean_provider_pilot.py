from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_buying_pages import evaluate_provider_activation_pilot  # noqa: E402


def _load_step12_fixture() -> dict[str, Any]:
    fixture_path = ROOT / "tests" / "fixtures" / "step12_provider_activation_pilot_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


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


class PickWiseStep12SelectedCleanProviderPilotTests(unittest.TestCase):
    def test_selected_clean_pilot_fixture_loads(self) -> None:
        payload = _load_step12_fixture()
        self.assertIn("selected_clean_pilot_scenario", payload)
        self.assertIn("local_inputs", payload)

    def test_selected_clean_pilot_ready_and_non_public(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["selected_clean_pilot_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertEqual(result["pilot_status"], "pilot_ready")
        self.assertTrue(result["can_request_human_activation_review"])
        self.assertFalse(result["can_publish_publicly"])
        self.assertFalse(result["can_expand_live_sitemap"])
        self.assertFalse(result["is_mass_publish"])

    def test_selected_clean_checklist_and_rollback_complete(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["selected_clean_pilot_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertTrue(result["approval_checklist"]["is_complete"])
        self.assertTrue(result["rollback_drill"]["is_complete"])

    def test_no_public_route_exposure_or_sitemap_expansion(self) -> None:
        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        self.assertNotIn("best-power-banks-for-travel-usa", body_sitemap)

        status_best_known, _headers_best_known, _body_best_known = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_known, "200 OK")
        status_best_new, _headers_best_new, _body_best_new = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_best_new, "404 Not Found")

    def test_no_credentials_api_or_live_provider_integration(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["selected_clean_pilot_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertEqual(result["provider_name"], "trusted-affiliate-export-v1")
        self.assertGreater(result["feed_rows_total"], 0)
        self.assertFalse(result["can_publish_publicly"])
        self.assertFalse(result["can_expand_live_sitemap"])


if __name__ == "__main__":
    unittest.main()
