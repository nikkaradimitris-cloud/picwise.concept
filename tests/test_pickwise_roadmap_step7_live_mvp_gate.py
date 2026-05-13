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


class PickWiseRoadmapStep7LiveMVPGateTests(unittest.TestCase):
    def test_only_index_candidate_can_become_live_mvp_ready(self) -> None:
        payload = _load_step7_fixture()
        selected = payload["selected_clean_batch"]["candidate_page_ids"]
        policy = LiveMVPGatePolicy(
            max_live_mvp_ready=3,
            sitemap_candidate_page_ids=tuple(payload["selected_clean_batch"]["sitemap_candidate_page_ids"]),
            public_exposure_candidate_page_ids=tuple(payload["selected_clean_batch"]["public_exposure_candidate_page_ids"]),
        )
        result = build_live_mvp_batch(payload["candidate_pages"], payload["index_decisions"], policy=policy)
        records = {record["candidate_page_id"]: record for record in result["records"]}

        for candidate_page_id in selected:
            self.assertEqual(records[candidate_page_id]["source_index_decision_status"], "index_candidate")
            self.assertEqual(records[candidate_page_id]["exposure_status"], "live_mvp_ready")

    def test_noindex_hold_rejected_duplicate_do_not_become_live_mvp_ready(self) -> None:
        payload = _load_step7_fixture()
        policy = LiveMVPGatePolicy(max_live_mvp_ready=8)
        result = build_live_mvp_batch(payload["candidate_pages"], payload["index_decisions"], policy=policy)
        records = {record["candidate_page_id"]: record for record in result["records"]}

        self.assertNotEqual(records["step7-noindex-candidate"]["exposure_status"], "live_mvp_ready")
        self.assertNotEqual(records["step7-hold-candidate"]["exposure_status"], "live_mvp_ready")
        self.assertNotEqual(records["step7-rejected-candidate"]["exposure_status"], "live_mvp_ready")
        self.assertNotEqual(records["step7-duplicate-candidate"]["exposure_status"], "live_mvp_ready")

    def test_live_mvp_ready_records_remain_controlled_not_mass_published(self) -> None:
        payload = _load_step7_fixture()
        policy = LiveMVPGatePolicy(max_live_mvp_ready=3)
        result = build_live_mvp_batch(payload["candidate_pages"], payload["index_decisions"], policy=policy)
        self.assertEqual(result["live_mvp_ready_count"], 3)
        self.assertGreater(result["hold_manual_review_count"], 0)
        for record in result["records"]:
            self.assertFalse(record["is_mass_publish"])
            self.assertFalse(record["can_be_publicly_exposed"])

    def test_preview_readiness_is_deterministic(self) -> None:
        payload = _load_step7_fixture()
        policy = LiveMVPGatePolicy(max_live_mvp_ready=3)
        first = build_live_mvp_batch(payload["candidate_pages"], payload["index_decisions"], policy=policy)
        second = build_live_mvp_batch(payload["candidate_pages"], payload["index_decisions"], policy=policy)
        self.assertEqual(first, second)
        self.assertEqual(
            first["preview_ready_count"],
            sum(1 for record in first["records"] if record["can_render_preview"]),
        )

    def test_outbound_click_tracking_event_names_are_contract_only(self) -> None:
        payload = _load_step7_fixture()
        policy = LiveMVPGatePolicy(max_live_mvp_ready=3)
        result = build_live_mvp_batch(payload["candidate_pages"], payload["index_decisions"], policy=policy)
        for record in result["records"]:
            if record["can_collect_outbound_click"]:
                self.assertIn("live_mvp_outbound_click", record["tracking_event_names"])

    def test_sitemap_candidate_is_candidate_level_only(self) -> None:
        payload = _load_step7_fixture()
        policy = LiveMVPGatePolicy(
            max_live_mvp_ready=3,
            sitemap_candidate_page_ids=tuple(payload["selected_clean_batch"]["sitemap_candidate_page_ids"]),
        )
        result = build_live_mvp_batch(payload["candidate_pages"], payload["index_decisions"], policy=policy)
        status, _headers, body = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status, "200 OK")
        for record in result["records"]:
            if record["can_be_sitemap_candidate"]:
                self.assertNotIn(record["slug"], body)

    def test_existing_best_behavior_unchanged_and_no_public_route_replacement(self) -> None:
        status_ok, _headers_ok, body_ok = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status_ok, "200 OK")
        self.assertIn("Recommended by PickWise", body_ok)

        status_missing, _headers_missing, _body_missing = _call_wsgi("/best/step7-clean-us-power-banks")
        self.assertEqual(status_missing, "404 Not Found")

        status_preview, _headers_preview, _body_preview = _call_wsgi("/preview-live-mvp/step7-clean-us-power-banks")
        self.assertEqual(status_preview, "404 Not Found")

    def test_no_naming_changes(self) -> None:
        _status, _headers, body = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertIn("PickWise", body)
        self.assertNotIn("Pic Wise", body)

    def test_no_gates_relaxed_and_no_fake_live_dependencies(self) -> None:
        source = inspect.getsource(build_live_mvp_batch).lower()
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "scrape",
            "selenium",
            "playwright",
            "google api",
            "affiliate api",
            "api_key",
            "credential",
            "fabricate",
            "search volume api",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
