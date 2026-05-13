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
from picwise_buying_pages import evaluate_promotion_policy_batch  # noqa: E402


def _load_selected_clean_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step9_selected_clean_promotion_batch.json"
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


class PickWiseRoadmapStep9SelectedCleanPromotionTests(unittest.TestCase):
    def test_selected_clean_promotion_batch_loads(self) -> None:
        payload = _load_selected_clean_fixture()
        self.assertIn("page_summaries", payload)
        self.assertIn("assertions", payload)

    def test_all_selected_clean_records_become_promoted_to_limited_exposure(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_promotion_policy_batch(payload["page_summaries"])
        self.assertEqual(result["promoted_to_limited_exposure_count"], len(payload["page_summaries"]))
        for decision in result["decisions"]:
            self.assertEqual(decision["decision_status"], "promoted_to_limited_exposure")
            self.assertTrue(decision["can_enter_limited_exposure"])

    def test_selected_clean_batch_has_no_hold_reject_rollback_or_needs_more(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_promotion_policy_batch(payload["page_summaries"])
        self.assertEqual(result["hold_manual_review_count"], 0)
        self.assertEqual(result["reject_from_promotion_count"], 0)
        self.assertEqual(result["rollback_required_count"], 0)
        self.assertEqual(result["needs_more_observation_count"], 0)
        self.assertTrue(result["can_move_to_step10"])

    def test_promotion_remains_policy_only_without_public_route_or_live_sitemap_exposure(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_promotion_policy_batch(payload["page_summaries"])
        self.assertTrue(result["can_move_to_step10"])
        for decision in result["decisions"]:
            self.assertFalse(decision["is_public"])
            self.assertFalse(decision["is_live_sitemap_included"])
            self.assertTrue(decision["can_expand_sitemap_candidate"])

        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        for page_summary in payload["page_summaries"]:
            self.assertNotIn(page_summary["slug"], body_sitemap)

        status_best_known, _headers_best_known, body_best_known = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_known, "200 OK")
        self.assertIn("Recommended by PickWise", body_best_known)

        status_best_new, _headers_best_new, _body_best_new = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_best_new, "404 Not Found")

    def test_no_revenue_conversion_search_volume_fabrication(self) -> None:
        payload = _load_selected_clean_fixture()
        result = evaluate_promotion_policy_batch(payload["page_summaries"])
        for decision in result["decisions"]:
            evidence = decision["evidence_summary"]
            self.assertNotIn("revenue", evidence)
            self.assertNotIn("conversion", evidence)
            self.assertNotIn("search_volume", evidence)
        self.assertTrue(payload["assertions"]["no_fabricated_revenue_conversion_search_volume"])


if __name__ == "__main__":
    unittest.main()
