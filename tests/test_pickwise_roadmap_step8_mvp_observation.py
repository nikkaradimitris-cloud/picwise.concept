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
    evaluate_mvp_promotion_readiness,
    summarize_mvp_observations,
    validate_mvp_observation_event,
)


def _load_step8_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step8_mvp_observation_events.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _event_by_id(payload: dict[str, object], event_id: str) -> dict[str, Any]:
    events = payload["events"]
    assert isinstance(events, list)
    for event in events:
        if isinstance(event, dict) and event.get("event_id") == event_id:
            return dict(event)
    raise AssertionError(f"Event not found: {event_id}")


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


class PickWiseRoadmapStep8MVPObservationTests(unittest.TestCase):
    def test_valid_preview_event_is_accepted(self) -> None:
        payload = _load_step8_fixture()
        event = _event_by_id(payload, "step8-preview-us-1")
        result = validate_mvp_observation_event(event)
        self.assertTrue(result["accepted"])
        self.assertIsNone(result["rejected_reason"])
        self.assertEqual(result["event"]["event_type"], "preview_rendered")

    def test_valid_outbound_click_requires_product_id_and_outbound_url(self) -> None:
        payload = _load_step8_fixture()
        valid_event = _event_by_id(payload, "step8-outbound-us-1")
        valid_result = validate_mvp_observation_event(valid_event)
        self.assertTrue(valid_result["accepted"])
        invalid_event = _event_by_id(payload, "step8-outbound-missing-product-id-1")
        invalid_result = validate_mvp_observation_event(invalid_event)
        self.assertFalse(invalid_result["accepted"])
        self.assertEqual(invalid_result["rejected_reason"], "outbound_click_missing_product_id")

    def test_invalid_event_type_is_rejected(self) -> None:
        payload = _load_step8_fixture()
        event = _event_by_id(payload, "step8-invalid-type-1")
        result = validate_mvp_observation_event(event)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "invalid_event_type")

    def test_missing_slug_or_candidate_id_is_rejected(self) -> None:
        payload = _load_step8_fixture()
        missing_slug = _event_by_id(payload, "step8-missing-slug-1")
        missing_slug_result = validate_mvp_observation_event(missing_slug)
        self.assertFalse(missing_slug_result["accepted"])
        self.assertEqual(missing_slug_result["rejected_reason"], "missing_slug")

        missing_candidate = dict(missing_slug)
        missing_candidate["event_id"] = "step8-missing-candidate-id-1"
        missing_candidate["candidate_page_id"] = ""
        missing_candidate["slug"] = "best-all-season-tyres-uk"
        missing_candidate_result = validate_mvp_observation_event(missing_candidate)
        self.assertFalse(missing_candidate_result["accepted"])
        self.assertEqual(missing_candidate_result["rejected_reason"], "missing_candidate_page_id")

    def test_no_revenue_or_conversion_fabrication_is_allowed(self) -> None:
        payload = _load_step8_fixture()
        event = _event_by_id(payload, "step8-fabricated-revenue-1")
        result = validate_mvp_observation_event(event)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "fabricated_revenue_or_conversion_metrics_not_allowed")

    def test_local_test_event_flags_must_be_explicit(self) -> None:
        payload = _load_step8_fixture()
        event = _event_by_id(payload, "step8-non-explicit-flags-1")
        result = validate_mvp_observation_event(event)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "test_mode_flag_must_be_explicit_boolean")

    def test_observation_summary_counts_are_deterministic(self) -> None:
        payload = _load_step8_fixture()
        first = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        second = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        self.assertEqual(first, second)
        self.assertEqual(first["total_events"], 12)
        self.assertEqual(first["accepted_events"], 7)
        self.assertEqual(first["rejected_events"], 5)
        self.assertEqual(first["preview_render_count"], 2)
        self.assertEqual(first["outbound_click_count"], 1)
        self.assertEqual(first["preview_error_count"], 1)
        self.assertEqual(first["outbound_error_count"], 1)
        self.assertEqual(first["manual_review_count"], 1)
        self.assertEqual(first["blocker_event_count"], 1)
        self.assertEqual(first["unique_candidate_pages_observed"], 4)

    def test_blocker_review_and_error_events_affect_status(self) -> None:
        payload = _load_step8_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        summaries = {item["candidate_page_id"]: item for item in result["page_summaries"]}
        self.assertEqual(summaries["step7-clean-de-kaffee"]["status"], "blocked")
        self.assertEqual(summaries["step7-clean-uk-tyres"]["status"], "hold_manual_review")

    def test_promotion_ready_requires_live_mvp_ready_and_evidence(self) -> None:
        payload = _load_step8_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        summaries = {item["candidate_page_id"]: item for item in result["page_summaries"]}
        self.assertTrue(summaries["step7-clean-us-power-banks"]["promotion_ready"])
        self.assertEqual(summaries["step7-clean-us-power-banks"]["status"], "observation_ready")

    def test_non_ready_records_cannot_become_promotion_ready(self) -> None:
        payload = _load_step8_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        summaries = {item["candidate_page_id"]: item for item in result["page_summaries"]}
        self.assertFalse(summaries["step7-hold-candidate"]["promotion_ready"])
        self.assertEqual(summaries["step7-hold-candidate"]["status"], "blocked")
        self.assertIn("not_live_mvp_ready", summaries["step7-hold-candidate"]["reasons"])

    def test_needs_more_data_is_returned_when_evidence_insufficient(self) -> None:
        readiness = evaluate_mvp_promotion_readiness(
            {
                "is_live_mvp_ready": True,
                "controlled_and_reversible": True,
                "total_events": 1,
                "preview_render_count": 1,
                "outbound_click_count": 0,
                "preview_error_count": 0,
                "outbound_error_count": 0,
                "manual_review_count": 0,
                "blocker_event_count": 0,
            }
        )
        self.assertEqual(readiness["status"], "needs_more_data")
        self.assertFalse(readiness["promotion_ready"])

    def test_can_move_to_step9_is_false_for_mixed_non_clean_batch(self) -> None:
        payload = _load_step8_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        self.assertFalse(result["can_move_to_step9"])
        self.assertGreater(result["rejected_events"], 0)
        self.assertGreater(result["blocked_count"], 0)

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

    def test_no_gates_relaxed_and_no_scraping_live_api_or_credentials_added(self) -> None:
        source = inspect.getsource(summarize_mvp_observations).lower() + inspect.getsource(
            validate_mvp_observation_event
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
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
