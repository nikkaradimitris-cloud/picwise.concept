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
    ControlledRolloutPolicy,
    evaluate_controlled_rollout_batch,
    evaluate_controlled_rollout_decision,
)


def _load_step10_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step10_controlled_rollout_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _decision_by_id(payload: dict[str, object], candidate_page_id: str) -> dict[str, Any]:
    decisions = payload["promotion_decisions"]
    assert isinstance(decisions, list)
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("candidate_page_id") == candidate_page_id:
            return dict(decision)
    raise AssertionError(f"Promotion decision not found: {candidate_page_id}")


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


class PickWiseRoadmapStep10ControlledRolloutTests(unittest.TestCase):
    def test_only_promoted_to_limited_exposure_can_become_limited_rollout_ready(self) -> None:
        payload = _load_step10_fixture()
        promoted = _decision_by_id(payload, "step10-promoted-clean-us")
        keep = _decision_by_id(payload, "step10-keep-preview-uk")
        promoted_result = evaluate_controlled_rollout_decision(promoted)
        keep_result = evaluate_controlled_rollout_decision(keep)
        self.assertEqual(promoted_result["rollout_status"], "limited_rollout_ready")
        self.assertEqual(keep_result["rollout_status"], "keep_in_preview")

    def test_keep_controlled_becomes_keep_in_preview(self) -> None:
        payload = _load_step10_fixture()
        keep = _decision_by_id(payload, "step10-keep-preview-uk")
        result = evaluate_controlled_rollout_decision(keep)
        self.assertEqual(result["source_promotion_status"], "keep_controlled")
        self.assertEqual(result["rollout_status"], "keep_in_preview")
        self.assertEqual(result["rollout_tier"], "preview_only")

    def test_hold_manual_review_stays_hold_manual_review(self) -> None:
        payload = _load_step10_fixture()
        hold = _decision_by_id(payload, "step10-hold-review-de")
        result = evaluate_controlled_rollout_decision(hold)
        self.assertEqual(result["rollout_status"], "hold_manual_review")
        self.assertTrue(result["requires_manual_review"])

    def test_reject_from_promotion_becomes_scale_blocked(self) -> None:
        payload = _load_step10_fixture()
        rejected = _decision_by_id(payload, "step10-reject-blocked-fr")
        result = evaluate_controlled_rollout_decision(rejected)
        self.assertEqual(result["rollout_status"], "scale_blocked")
        self.assertIn("promotion_rejected_from_scale", result["blocker_reasons"])

    def test_rollback_required_stays_rollback_required(self) -> None:
        payload = _load_step10_fixture()
        rollback = _decision_by_id(payload, "step10-rollback-required-jp")
        result = evaluate_controlled_rollout_decision(rollback)
        self.assertEqual(result["rollout_status"], "rollback_required")
        self.assertTrue(result["requires_rollback"])

    def test_needs_more_observation_stays_needs_more_observation(self) -> None:
        payload = _load_step10_fixture()
        needs_more = _decision_by_id(payload, "step10-needs-more-es")
        result = evaluate_controlled_rollout_decision(needs_more)
        self.assertEqual(result["rollout_status"], "needs_more_observation")
        self.assertFalse(result["can_enter_limited_rollout"])

    def test_rollout_cap_is_enforced(self) -> None:
        payload = _load_step10_fixture()
        policy = ControlledRolloutPolicy(max_limited_rollout_records=1)
        result = evaluate_controlled_rollout_batch(payload["promotion_decisions"], policy=policy)
        self.assertEqual(result["limited_rollout_ready_count"], 1)
        self.assertGreaterEqual(result["keep_in_preview_count"], 2)
        overflow = [item for item in result["decisions"] if item["candidate_page_id"] == "step10-promoted-cap-overflow-it"][0]
        self.assertEqual(overflow["rollout_status"], "keep_in_preview")
        self.assertIn("outside_max_limited_rollout_records_cap", overflow["review_reasons"])

    def test_rollback_signals_force_rollback_required(self) -> None:
        payload = _load_step10_fixture()
        promoted = _decision_by_id(payload, "step10-promoted-clean-us")
        promoted["requires_rollback"] = True
        promoted["rollback_reasons"] = ["runtime_regression_detected"]
        result = evaluate_controlled_rollout_decision(promoted)
        self.assertEqual(result["rollout_status"], "rollback_required")
        self.assertIn("rollback_signal_detected", result["rollback_reasons"])

    def test_sitemap_consideration_is_policy_only(self) -> None:
        payload = _load_step10_fixture()
        promoted = _decision_by_id(payload, "step10-promoted-clean-us")
        result = evaluate_controlled_rollout_decision(promoted)
        self.assertTrue(result["can_be_considered_for_sitemap_later"])
        self.assertFalse(result["is_live_sitemap_included"])

    def test_is_public_live_sitemap_and_mass_publish_remain_false(self) -> None:
        payload = _load_step10_fixture()
        result = evaluate_controlled_rollout_batch(payload["promotion_decisions"])
        for decision in result["decisions"]:
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

    def test_no_gates_relaxed_or_fake_metrics_or_external_api_credentials_added(self) -> None:
        source = inspect.getsource(evaluate_controlled_rollout_decision).lower() + inspect.getsource(
            evaluate_controlled_rollout_batch
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
            "credential",
            "impression",
            "revenue",
            "conversion",
            "search_volume",
            "price",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_batch_evaluator_counts_are_deterministic(self) -> None:
        payload = _load_step10_fixture()
        policy = ControlledRolloutPolicy(max_limited_rollout_records=2)
        first = evaluate_controlled_rollout_batch(payload["promotion_decisions"], policy=policy)
        second = evaluate_controlled_rollout_batch(payload["promotion_decisions"], policy=policy)
        self.assertEqual(first, second)
        self.assertEqual(first["total_records"], 8)
        self.assertEqual(first["limited_rollout_ready_count"], 2)
        self.assertEqual(first["keep_in_preview_count"], 1)
        self.assertEqual(first["hold_manual_review_count"], 1)
        self.assertEqual(first["rollback_required_count"], 1)
        self.assertEqual(first["scale_blocked_count"], 2)
        self.assertEqual(first["needs_more_observation_count"], 1)
        self.assertFalse(first["can_close_roadmap"])


if __name__ == "__main__":
    unittest.main()
