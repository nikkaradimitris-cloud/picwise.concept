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
from picwise_buying_pages import evaluate_controlled_rollout_batch  # noqa: E402


def _load_selected_clean_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step10_selected_clean_rollout_batch.json"
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


class PickWiseRoadmapStep10SelectedCleanRolloutTests(unittest.TestCase):
    def test_selected_clean_rollout_batch_loads(self) -> None:
        payload = _load_selected_clean_fixture()
        self.assertIn("promotion_decisions", payload)
        self.assertIn("assertions", payload)

    def test_all_selected_clean_records_become_limited_rollout_ready(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_controlled_rollout_batch(payload["promotion_decisions"])
        self.assertEqual(result["limited_rollout_ready_count"], len(payload["promotion_decisions"]))
        for decision in result["decisions"]:
            self.assertEqual(decision["rollout_status"], "limited_rollout_ready")
            self.assertEqual(decision["rollout_tier"], "limited")
            self.assertTrue(decision["can_enter_limited_rollout"])

    def test_selected_clean_batch_has_no_hold_rollback_blocked_or_needs_more(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_controlled_rollout_batch(payload["promotion_decisions"])
        self.assertEqual(result["hold_manual_review_count"], 0)
        self.assertEqual(result["rollback_required_count"], 0)
        self.assertEqual(result["scale_blocked_count"], 0)
        self.assertEqual(result["needs_more_observation_count"], 0)
        self.assertTrue(result["can_close_roadmap"])

    def test_rollout_remains_policy_only_without_public_routes_or_live_sitemap_expansion(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_controlled_rollout_batch(payload["promotion_decisions"])
        self.assertTrue(result["can_close_roadmap"])
        for decision in result["decisions"]:
            self.assertFalse(decision["is_public"])
            self.assertFalse(decision["is_live_sitemap_included"])
            self.assertFalse(decision["is_mass_publish"])
            self.assertTrue(decision["can_be_considered_for_sitemap_later"])

        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        for source in payload["promotion_decisions"]:
            self.assertNotIn(source["slug"], body_sitemap)

        status_best_known, _headers_best_known, body_best_known = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_known, "200 OK")
        self.assertIn("Recommended by PickWise", body_best_known)

        status_best_new, _headers_best_new, _body_best_new = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_best_new, "404 Not Found")

    def test_no_revenue_conversion_search_volume_fabrication(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_controlled_rollout_batch(payload["promotion_decisions"])
        for decision in result["decisions"]:
            evidence = decision["evidence_summary"]
            self.assertNotIn("revenue", evidence)
            self.assertNotIn("conversion", evidence)
            self.assertNotIn("search_volume", evidence)
            self.assertNotIn("impressions", evidence)
        self.assertTrue(payload["assertions"]["no_fabricated_revenue_conversion_search_volume"])


if __name__ == "__main__":
    unittest.main()
