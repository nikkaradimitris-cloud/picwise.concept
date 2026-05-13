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
from picwise_buying_pages import LiveMVPGatePolicy, build_live_mvp_batch  # noqa: E402


def _load_step7_fixture() -> dict[str, object]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step7_live_mvp_inputs.json"
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


class PickWiseRoadmapStep7SelectedCleanLiveMVPTests(unittest.TestCase):
    def test_selected_clean_live_mvp_batch_is_ready_for_step8(self) -> None:
        payload = _load_step7_fixture()
        selected_ids = set(payload["selected_clean_batch"]["candidate_page_ids"])
        selected_pages = [page for page in payload["candidate_pages"] if page["candidate_page_id"] in selected_ids]
        selected_decisions = [
            decision for decision in payload["index_decisions"] if decision["candidate_page_id"] in selected_ids
        ]
        policy = LiveMVPGatePolicy(
            max_live_mvp_ready=len(selected_ids),
            sitemap_candidate_page_ids=tuple(payload["selected_clean_batch"]["sitemap_candidate_page_ids"]),
            public_exposure_candidate_page_ids=tuple(payload["selected_clean_batch"]["public_exposure_candidate_page_ids"]),
        )
        result = build_live_mvp_batch(selected_pages, selected_decisions, policy=policy)

        self.assertEqual(result["total_candidates"], len(selected_ids))
        self.assertEqual(result["live_mvp_ready_count"], len(selected_ids))
        self.assertEqual(result["blocked_count"], 0)
        self.assertEqual(result["hold_manual_review_count"], 0)
        self.assertEqual(result["preview_ready_count"], result["live_mvp_ready_count"])
        self.assertEqual(result["outbound_tracking_ready_count"], result["live_mvp_ready_count"])
        self.assertTrue(result["can_move_to_step8"])
        for record in result["records"]:
            self.assertFalse(record["is_mass_publish"])
            self.assertFalse(record["can_be_publicly_exposed"])
            self.assertEqual(record["exposure_status"], "live_mvp_ready")

    def test_selected_clean_live_mvp_does_not_expand_live_sitemap_or_replace_best(self) -> None:
        payload = _load_step7_fixture()
        selected_ids = set(payload["selected_clean_batch"]["candidate_page_ids"])
        selected_pages = [page for page in payload["candidate_pages"] if page["candidate_page_id"] in selected_ids]
        selected_decisions = [
            decision for decision in payload["index_decisions"] if decision["candidate_page_id"] in selected_ids
        ]
        policy = LiveMVPGatePolicy(
            max_live_mvp_ready=len(selected_ids),
            sitemap_candidate_page_ids=tuple(payload["selected_clean_batch"]["sitemap_candidate_page_ids"]),
        )
        result = build_live_mvp_batch(selected_pages, selected_decisions, policy=policy)

        status_sitemap, _headers_sitemap, body_sitemap = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status_sitemap, "200 OK")
        for record in result["records"]:
            if record["can_be_sitemap_candidate"]:
                self.assertNotIn(record["slug"], body_sitemap)

        status_best_known, _headers_best_known, body_best_known = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_best_known, "200 OK")
        self.assertIn("Recommended by PickWise", body_best_known)

        status_best_new, _headers_best_new, _body_best_new = _call_wsgi("/best/best-power-banks-for-travel-usa")
        self.assertEqual(status_best_new, "404 Not Found")


if __name__ == "__main__":
    unittest.main()
