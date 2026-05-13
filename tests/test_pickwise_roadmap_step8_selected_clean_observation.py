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
from picwise_buying_pages import summarize_mvp_observations  # noqa: E402


def _load_selected_clean_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step8_selected_clean_observation_batch.json"
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


class PickWiseRoadmapStep8SelectedCleanObservationTests(unittest.TestCase):
    def test_selected_clean_observation_batch_loads(self) -> None:
        payload = _load_selected_clean_fixture()
        self.assertIn("events", payload)
        self.assertIn("live_mvp_records", payload)
        self.assertIn("assertions", payload)

    def test_all_selected_live_mvp_ready_records_become_promotion_ready(self) -> None:
        payload = _load_selected_clean_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        self.assertEqual(result["promotion_ready_count"], len(payload["live_mvp_records"]))
        self.assertEqual(result["status_counts"]["observation_ready"], len(payload["live_mvp_records"]))
        for page_summary in result["page_summaries"]:
            self.assertTrue(page_summary["promotion_ready"])
            self.assertEqual(page_summary["status"], "observation_ready")

    def test_selected_clean_batch_has_no_rejections_blocks_or_holds(self) -> None:
        payload = _load_selected_clean_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        self.assertEqual(result["rejected_events"], 0)
        self.assertEqual(result["blocked_count"], 0)
        self.assertEqual(result["hold_manual_review_count"], 0)
        self.assertTrue(result["can_move_to_step9"])

    def test_promotion_readiness_does_not_publish_or_expand_sitemap_or_replace_best(self) -> None:
        payload = _load_selected_clean_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        self.assertTrue(result["can_move_to_step9"])

        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        for record in payload["live_mvp_records"]:
            self.assertNotIn(record["slug"], body_sitemap)

        status_best_known, _headers_best_known, body_best_known = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_known, "200 OK")
        self.assertIn("Recommended by PickWise", body_best_known)

        status_best_new, _headers_best_new, _body_best_new = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_best_new, "404 Not Found")

    def test_no_revenue_or_conversion_fabrication(self) -> None:
        payload = _load_selected_clean_fixture()
        result = summarize_mvp_observations(payload["events"], live_mvp_records=payload["live_mvp_records"])
        self.assertEqual(result["rejected_reason_counts"], {})
        source = inspect.getsource(summarize_mvp_observations).lower()
        self.assertNotIn("fabricate", source)
        self.assertTrue(payload["assertions"]["no_revenue_or_conversion_fabrication"])
        self.assertTrue(payload["assertions"]["no_publishing_side_effects"])
        self.assertTrue(payload["assertions"]["no_live_sitemap_expansion"])
        self.assertTrue(payload["assertions"]["no_best_route_replacement"])


if __name__ == "__main__":
    unittest.main()
