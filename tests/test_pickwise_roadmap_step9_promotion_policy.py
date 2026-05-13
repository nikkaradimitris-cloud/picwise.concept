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
    evaluate_promotion_decision,
    evaluate_promotion_policy_batch,
)


def _load_step9_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step9_promotion_policy_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _summary_by_id(payload: dict[str, object], candidate_page_id: str) -> dict[str, Any]:
    summaries = payload["page_summaries"]
    assert isinstance(summaries, list)
    for summary in summaries:
        if isinstance(summary, dict) and summary.get("candidate_page_id") == candidate_page_id:
            return dict(summary)
    raise AssertionError(f"Summary not found: {candidate_page_id}")


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


class PickWiseRoadmapStep9PromotionPolicyTests(unittest.TestCase):
    def test_only_promotion_ready_observation_can_be_promoted(self) -> None:
        payload = _load_step9_fixture()
        ready_summary = _summary_by_id(payload, "step8-clean-ready-us")
        non_ready_summary = _summary_by_id(payload, "step8-needs-more-data-uk")
        ready_decision = evaluate_promotion_decision(ready_summary)
        non_ready_decision = evaluate_promotion_decision(non_ready_summary)
        self.assertEqual(ready_decision["decision_status"], "promoted_to_limited_exposure")
        self.assertEqual(non_ready_decision["decision_status"], "needs_more_observation")

    def test_needs_more_data_becomes_needs_more_observation(self) -> None:
        payload = _load_step9_fixture()
        summary = _summary_by_id(payload, "step8-needs-more-data-uk")
        decision = evaluate_promotion_decision(summary)
        self.assertEqual(decision["source_observation_status"], "needs_more_data")
        self.assertEqual(decision["decision_status"], "needs_more_observation")

    def test_manual_review_event_becomes_hold_manual_review(self) -> None:
        payload = _load_step9_fixture()
        summary = _summary_by_id(payload, "step8-manual-review-de")
        decision = evaluate_promotion_decision(summary)
        self.assertEqual(decision["decision_status"], "hold_manual_review")
        self.assertTrue(decision["requires_manual_review"])

    def test_blocker_event_rejects_promotion(self) -> None:
        payload = _load_step9_fixture()
        summary = _summary_by_id(payload, "step8-blocker-reject-fr")
        decision = evaluate_promotion_decision(summary)
        self.assertEqual(decision["decision_status"], "reject_from_promotion")
        self.assertIn("source_blocked_or_blocker_event_present", decision["blocker_reasons"])

    def test_severe_error_trend_triggers_rollback_required(self) -> None:
        payload = _load_step9_fixture()
        summary = _summary_by_id(payload, "step8-rollback-required-jp")
        decision = evaluate_promotion_decision(summary)
        self.assertEqual(decision["decision_status"], "rollback_required")
        self.assertTrue(decision["requires_rollback"])
        self.assertGreater(len(decision["rollback_reasons"]), 0)

    def test_missing_evidence_blocks_promotion(self) -> None:
        payload = _load_step9_fixture()
        summary = _summary_by_id(payload, "step8-needs-more-data-uk")
        decision = evaluate_promotion_decision(summary)
        self.assertEqual(decision["decision_status"], "needs_more_observation")
        self.assertFalse(decision["can_enter_limited_exposure"])

    def test_error_threshold_holds_without_forcing_rollback(self) -> None:
        payload = _load_step9_fixture()
        outbound_hold_summary = _summary_by_id(payload, "step8-outbound-errors-hold-es")
        preview_hold_summary = _summary_by_id(payload, "step8-preview-errors-hold-it")
        outbound_hold_decision = evaluate_promotion_decision(outbound_hold_summary)
        preview_hold_decision = evaluate_promotion_decision(preview_hold_summary)
        self.assertEqual(outbound_hold_decision["decision_status"], "hold_manual_review")
        self.assertEqual(preview_hold_decision["decision_status"], "hold_manual_review")
        self.assertFalse(outbound_hold_decision["requires_rollback"])
        self.assertFalse(preview_hold_decision["requires_rollback"])

    def test_can_expand_sitemap_candidate_is_policy_flag_only(self) -> None:
        payload = _load_step9_fixture()
        summary = _summary_by_id(payload, "step8-clean-ready-us")
        decision = evaluate_promotion_decision(summary)
        self.assertTrue(decision["can_expand_sitemap_candidate"])
        self.assertFalse(decision["is_live_sitemap_included"])

    def test_is_public_and_live_sitemap_included_remain_false(self) -> None:
        payload = _load_step9_fixture()
        result = evaluate_promotion_policy_batch(payload["page_summaries"])
        for decision in result["decisions"]:
            self.assertFalse(decision["is_public"])
            self.assertFalse(decision["is_live_sitemap_included"])

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
        source = inspect.getsource(evaluate_promotion_decision).lower() + inspect.getsource(
            evaluate_promotion_policy_batch
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
            "revenue",
            "conversion",
            "search_volume",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_batch_evaluator_counts_are_deterministic(self) -> None:
        payload = _load_step9_fixture()
        first = evaluate_promotion_policy_batch(payload["page_summaries"])
        second = evaluate_promotion_policy_batch(payload["page_summaries"])
        self.assertEqual(first, second)
        self.assertEqual(first["total_pages"], 8)
        self.assertEqual(first["promoted_to_limited_exposure_count"], 1)
        self.assertEqual(first["hold_manual_review_count"], 3)
        self.assertEqual(first["reject_from_promotion_count"], 2)
        self.assertEqual(first["rollback_required_count"], 1)
        self.assertEqual(first["needs_more_observation_count"], 1)
        self.assertFalse(first["can_move_to_step10"])


if __name__ == "__main__":
    unittest.main()
