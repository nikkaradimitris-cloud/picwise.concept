from __future__ import annotations

import inspect
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
from picwise_buying_pages import (  # noqa: E402
    build_provider_activation_checklist,
    build_provider_activation_rollback_drill,
    evaluate_provider_activation_pilot,
    validate_provider_activation_input,
)


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


class PickWiseStep12ProviderActivationPilotTests(unittest.TestCase):
    def test_input_contract_validates_clean_local_input(self) -> None:
        payload = _load_step12_fixture()
        result = validate_provider_activation_input(payload["clean_local_provider_pilot_input"])
        self.assertTrue(result["valid"])
        self.assertEqual(result["blocker_reasons"], ())

    def test_missing_feed_file_blocks_pilot(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["missing_provider_feed_file_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertEqual(result["pilot_status"], "pilot_blocked")
        self.assertIn("missing_provider_feed_export_file", result["blocker_reasons"])

    def test_missing_seller_map_is_remediation_or_blocked_per_policy(self) -> None:
        payload = _load_step12_fixture()
        default_result = evaluate_provider_activation_pilot(
            payload["missing_trusted_seller_map_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertIn(default_result["pilot_status"], {"pilot_needs_remediation", "pilot_blocked"})
        self.assertTrue(
            ("provide_trusted_seller_map" in default_result["remediation_actions"])
            or ("missing_trusted_seller_map" in default_result["blocker_reasons"])
            or ("missing_trusted_seller_map_file" in default_result["blocker_reasons"])
        )

        blocked_policy_result = evaluate_provider_activation_pilot(
            payload["missing_trusted_seller_map_scenario"],
            local_inputs=payload["local_inputs"],
            policy={"missing_trusted_seller_map_outcome": "blocked"},
        )
        self.assertEqual(blocked_policy_result["pilot_status"], "pilot_blocked")
        self.assertIn("missing_trusted_seller_map", blocked_policy_result["blocker_reasons"])

    def test_missing_keyword_cluster_batch_blocks_page_planning(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["missing_keyword_cluster_batch_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertEqual(result["pilot_status"], "pilot_blocked")
        self.assertTrue(
            ("missing_keyword_cluster_batch" in result["blocker_reasons"])
            or ("missing_keyword_cluster_batch_file" in result["blocker_reasons"])
        )

    def test_wrong_target_market_locale_blocks_pilot(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["wrong_target_market_locale_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertEqual(result["pilot_status"], "pilot_blocked")
        self.assertIn("target_market_locale_mismatch", result["blocker_reasons"])

    def test_dry_run_only_false_is_rejected(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["dry_run_only_false_scenario"],
            local_inputs=payload["local_inputs"],
        )
        self.assertEqual(result["pilot_status"], "pilot_blocked")
        self.assertIn("dry_run_only_must_be_true", result["blocker_reasons"])

    def test_hard_locks_publish_sitemap_mass_publish_false(self) -> None:
        payload = _load_step12_fixture()
        result = evaluate_provider_activation_pilot(
            payload["clean_local_provider_pilot_input"],
            local_inputs=payload["local_inputs"],
        )
        self.assertFalse(result["can_publish_publicly"])
        self.assertFalse(result["can_expand_live_sitemap"])
        self.assertFalse(result["is_mass_publish"])

    def test_checklist_is_deterministic(self) -> None:
        payload = _load_step12_fixture()
        contract = payload["clean_local_provider_pilot_input"]
        first = build_provider_activation_checklist(contract, pipeline_result={"feed_rows_total": 1})
        second = build_provider_activation_checklist(contract, pipeline_result={"feed_rows_total": 1})
        self.assertEqual(first, second)

    def test_rollback_drill_is_deterministic(self) -> None:
        payload = _load_step12_fixture()
        contract = payload["clean_local_provider_pilot_input"]
        first = build_provider_activation_rollback_drill(contract)
        second = build_provider_activation_rollback_drill(contract)
        self.assertEqual(first, second)

    def test_no_route_sitemap_or_naming_changes(self) -> None:
        status_best_ok, _headers_best_ok, body_best_ok = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_ok, "200 OK")
        self.assertIn("PickWise", body_best_ok)

        status_new_best, _headers_new_best, _body_new_best = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_new_best, "404 Not Found")

        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        self.assertNotIn("best-power-banks-for-travel-usa", body_sitemap)

    def test_no_gates_relaxed_and_no_fake_metrics_or_live_api_credentials(self) -> None:
        source = inspect.getsource(evaluate_provider_activation_pilot).lower()
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "scrape",
            "selenium",
            "playwright",
            "google api",
            "analytics api",
            "affiliate api",
            "api_key",
            "credential =",
            "impression",
            "clicks",
            "conversion",
            "revenue",
            "search_volume",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
