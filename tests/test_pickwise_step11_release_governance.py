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
    build_release_audit_record,
    evaluate_release_governance_batch,
    evaluate_release_governance_decision,
)


def _load_step11_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "step11_release_governance_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _decision_by_id(payload: dict[str, object], candidate_page_id: str) -> dict[str, Any]:
    decisions = payload["rollout_decisions"]
    assert isinstance(decisions, list)
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("candidate_page_id") == candidate_page_id:
            return dict(decision)
    raise AssertionError(f"Rollout decision not found: {candidate_page_id}")


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


class PickWiseStep11ReleaseGovernanceTests(unittest.TestCase):
    def test_only_limited_rollout_ready_can_become_approval_ready(self) -> None:
        payload = _load_step11_fixture()
        limited = _decision_by_id(payload, "step11-limited-ready-approval-not-requested")
        keep = _decision_by_id(payload, "step11-keep-preview")
        result_limited = evaluate_release_governance_decision(limited, approval_status="approved")
        result_keep = evaluate_release_governance_decision(keep, approval_status="approved")
        self.assertEqual(result_limited["governance_status"], "approval_ready")
        self.assertEqual(result_keep["governance_status"], "approval_required")

    def test_approval_ready_still_requires_human_approval_and_explicit_status(self) -> None:
        payload = _load_step11_fixture()
        limited = _decision_by_id(payload, "step11-limited-ready-approval-not-requested")
        not_requested = evaluate_release_governance_decision(limited)
        pending = evaluate_release_governance_decision(limited, approval_status="pending_human_approval")
        approved = evaluate_release_governance_decision(limited, approval_status="approved")
        self.assertEqual(not_requested["approval_status"], "not_requested")
        self.assertEqual(not_requested["governance_status"], "approval_required")
        self.assertFalse(not_requested["can_request_limited_activation"])
        self.assertEqual(pending["approval_status"], "pending_human_approval")
        self.assertEqual(pending["governance_status"], "approval_required")
        self.assertEqual(approved["approval_status"], "approved")
        self.assertEqual(approved["governance_status"], "approval_ready")
        self.assertTrue(approved["can_request_limited_activation"])
        self.assertTrue(approved["requires_human_approval"])

    def test_approval_status_is_never_assumed(self) -> None:
        payload = _load_step11_fixture()
        limited = _decision_by_id(payload, "step11-limited-ready-approval-not-requested")
        result = evaluate_release_governance_decision(limited)
        self.assertEqual(result["approval_status"], "not_requested")
        self.assertTrue(result["evidence_summary"]["approval_status_provided_explicitly"] is False)

    def test_keep_in_preview_cannot_request_activation(self) -> None:
        payload = _load_step11_fixture()
        keep = _decision_by_id(payload, "step11-keep-preview")
        result = evaluate_release_governance_decision(keep, approval_status="approved")
        self.assertEqual(result["governance_status"], "approval_required")
        self.assertFalse(result["can_request_limited_activation"])

    def test_hold_manual_review_cannot_request_activation(self) -> None:
        payload = _load_step11_fixture()
        hold = _decision_by_id(payload, "step11-hold-manual-review")
        result = evaluate_release_governance_decision(hold, approval_status="pending_human_approval")
        self.assertEqual(result["governance_status"], "approval_required")
        self.assertFalse(result["can_request_limited_activation"])

    def test_rollback_required_forces_rollback_required_governance(self) -> None:
        payload = _load_step11_fixture()
        rollback = _decision_by_id(payload, "step11-rollback-required")
        result = evaluate_release_governance_decision(rollback, approval_status="rollback_approved")
        self.assertEqual(result["governance_status"], "rollback_required")
        self.assertTrue(result["requires_rollback"])

    def test_scale_blocked_becomes_blocked_or_rejected(self) -> None:
        payload = _load_step11_fixture()
        blocked = _decision_by_id(payload, "step11-scale-blocked")
        result = evaluate_release_governance_decision(blocked, approval_status="not_requested")
        self.assertIn(result["governance_status"], {"blocked", "rejected"})
        self.assertFalse(result["can_request_limited_activation"])

    def test_needs_more_observation_cannot_request_activation(self) -> None:
        payload = _load_step11_fixture()
        needs_more = _decision_by_id(payload, "step11-needs-more-observation")
        result = evaluate_release_governance_decision(needs_more, approval_status="approved")
        self.assertEqual(result["governance_status"], "approval_required")
        self.assertFalse(result["can_request_limited_activation"])

    def test_explicit_rejected_approval_blocks_activation(self) -> None:
        payload = _load_step11_fixture()
        rejected = _decision_by_id(payload, "step11-limited-ready-explicit-rejected-approval")
        result = evaluate_release_governance_decision(rejected, approval_status="rejected")
        self.assertEqual(result["governance_status"], "rejected")
        self.assertFalse(result["can_request_limited_activation"])

    def test_audit_record_is_deterministic(self) -> None:
        payload = _load_step11_fixture()
        limited = _decision_by_id(payload, "step11-limited-ready-pending-approval")
        decision = evaluate_release_governance_decision(limited, approval_status="pending_human_approval")
        first = build_release_audit_record(decision, actor="system", action="evaluated")
        second = build_release_audit_record(decision, actor="system", action="evaluated")
        self.assertEqual(first, second)
        self.assertIn("event_signature", first)
        self.assertEqual(first["audit_id"], "step11-audit-step11-limited-ready-pending-approval")

    def test_public_and_sitemap_flags_remain_false(self) -> None:
        payload = _load_step11_fixture()
        result = evaluate_release_governance_batch(
            payload["rollout_decisions"],
            approval_status_by_candidate=payload["approval_status_by_candidate"],
        )
        for decision in result["decisions"]:
            self.assertFalse(decision["can_publish_publicly"])
            self.assertFalse(decision["can_expand_live_sitemap"])
            self.assertFalse(decision["is_public"])
            self.assertFalse(decision["is_live_sitemap_included"])
            self.assertFalse(decision["is_mass_publish"])

    def test_no_route_sitemap_or_naming_changes(self) -> None:
        status_best_ok, _headers_best_ok, body_best_ok = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_ok, "200 OK")
        self.assertIn("PickWise", body_best_ok)
        self.assertNotIn("Pic Wise", body_best_ok)

        status_new_best, _headers_new_best, _body_new_best = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_new_best, "404 Not Found")

        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        self.assertNotIn("best-power-banks-for-travel-usa", body_sitemap)
        self.assertNotIn("best-all-season-tyres-uk", body_sitemap)

    def test_no_gates_relaxed_and_no_fake_metrics_products_search_volume_api_credentials(self) -> None:
        source = inspect.getsource(evaluate_release_governance_decision).lower() + inspect.getsource(
            evaluate_release_governance_batch
        ).lower()
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
            "price",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_batch_summary_is_deterministic_and_mixed(self) -> None:
        payload = _load_step11_fixture()
        first = evaluate_release_governance_batch(
            payload["rollout_decisions"],
            approval_status_by_candidate=payload["approval_status_by_candidate"],
        )
        second = evaluate_release_governance_batch(
            payload["rollout_decisions"],
            approval_status_by_candidate=payload["approval_status_by_candidate"],
        )
        self.assertEqual(first, second)
        self.assertEqual(first["total_records"], 8)
        self.assertEqual(first["approval_ready_count"], 0)
        self.assertEqual(first["approval_required_count"], 5)
        self.assertEqual(first["blocked_count"], 1)
        self.assertEqual(first["rollback_required_count"], 1)
        self.assertEqual(first["rejected_count"], 1)
        self.assertEqual(first["pending_human_approval_count"], 2)
        self.assertEqual(first["approved_count"], 0)
        self.assertFalse(first["can_move_to_real_provider_activation_review"])


if __name__ == "__main__":
    unittest.main()
