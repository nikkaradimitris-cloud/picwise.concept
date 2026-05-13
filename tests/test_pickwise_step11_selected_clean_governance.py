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
from picwise_buying_pages import evaluate_release_governance_batch  # noqa: E402


def _load_step11_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "step11_release_governance_inputs.json"
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


class PickWiseStep11SelectedCleanGovernanceTests(unittest.TestCase):
    def test_selected_clean_limited_rollout_ready_records_become_approval_ready(self) -> None:
        payload = _load_step11_fixture()
        result = evaluate_release_governance_batch(
            payload["selected_clean_governance_cohort"],
            approval_status_by_candidate=payload["selected_clean_approval_status_by_candidate"],
        )
        self.assertEqual(result["approval_ready_count"], len(payload["selected_clean_governance_cohort"]))
        for decision in result["decisions"]:
            self.assertEqual(decision["source_rollout_status"], "limited_rollout_ready")
            self.assertEqual(decision["governance_status"], "approval_ready")

    def test_selected_clean_records_still_require_human_approval_and_represent_pending(self) -> None:
        payload = _load_step11_fixture()
        pending_map = {
            item["candidate_page_id"]: "pending_human_approval"
            for item in payload["selected_clean_governance_cohort"]
        }
        pending_result = evaluate_release_governance_batch(
            payload["selected_clean_governance_cohort"],
            approval_status_by_candidate=pending_map,
        )
        self.assertEqual(pending_result["approval_ready_count"], 0)
        self.assertEqual(pending_result["approval_required_count"], len(payload["selected_clean_governance_cohort"]))
        self.assertEqual(
            pending_result["pending_human_approval_count"],
            len(payload["selected_clean_governance_cohort"]),
        )
        for decision in pending_result["decisions"]:
            self.assertTrue(decision["requires_human_approval"])
            self.assertEqual(decision["approval_status"], "pending_human_approval")
            self.assertFalse(decision["can_request_limited_activation"])

    def test_selected_clean_has_no_blocked_rollback_or_rejected(self) -> None:
        payload = _load_step11_fixture()
        result = evaluate_release_governance_batch(
            payload["selected_clean_governance_cohort"],
            approval_status_by_candidate=payload["selected_clean_approval_status_by_candidate"],
        )
        self.assertEqual(result["blocked_count"], 0)
        self.assertEqual(result["rollback_required_count"], 0)
        self.assertEqual(result["rejected_count"], 0)
        self.assertTrue(result["can_move_to_real_provider_activation_review"])

    def test_selected_clean_no_public_publish_or_live_sitemap_or_mass_publish(self) -> None:
        payload = _load_step11_fixture()
        result = evaluate_release_governance_batch(
            payload["selected_clean_governance_cohort"],
            approval_status_by_candidate=payload["selected_clean_approval_status_by_candidate"],
        )
        self.assertTrue(result["can_move_to_real_provider_activation_review"])
        for decision in result["decisions"]:
            self.assertFalse(decision["can_publish_publicly"])
            self.assertFalse(decision["can_expand_live_sitemap"])
            self.assertFalse(decision["is_public"])
            self.assertFalse(decision["is_live_sitemap_included"])
            self.assertFalse(decision["is_mass_publish"])

        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        for source in payload["selected_clean_governance_cohort"]:
            self.assertNotIn(source["slug"], body_sitemap)

        status_best_known, _headers_best_known, body_best_known = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_known, "200 OK")
        self.assertIn("Recommended by PickWise", body_best_known)

        status_best_new, _headers_best_new, _body_best_new = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_best_new, "404 Not Found")

    def test_selected_clean_has_no_credentials_api_or_live_provider_integration(self) -> None:
        payload = _load_step11_fixture()
        result = evaluate_release_governance_batch(
            payload["selected_clean_governance_cohort"],
            approval_status_by_candidate=payload["selected_clean_approval_status_by_candidate"],
        )
        for decision in result["decisions"]:
            evidence = decision["evidence_summary"]
            self.assertFalse(evidence["source_has_live_provider_connection"])
            self.assertFalse(evidence["source_has_credentials"])


if __name__ == "__main__":
    unittest.main()
