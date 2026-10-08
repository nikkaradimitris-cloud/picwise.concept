"""Public status lines must describe the production state, not a fixture's.

Pins audit findings E5 and E6 in docs/picwise_mission_truth_audit_2026-10-08.md:

- With a feed connected but no four products for a search, the page said "no safe
  provider is connected yet".
- `GET /private-beta-readiness` reported `ready` and "Source intake status: connected",
  computed from the MVP flow's local fixture adapter, with no production feed configured.
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"
_NOT_CONNECTED = "PicWise understood this search, but no safe provider is connected yet."
_CONNECTED_NO_FOUR = "the connected product feed has no four products it can show for it"


def _get(path: str, query: dict[str, str] | None = None) -> tuple[str, str]:
    captured: dict[str, str] = {}

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        captured["status"] = status

    body = b"".join(
        wsgi_app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": path,
                "QUERY_STRING": urlencode(query or {}),
                "wsgi.input": io.BytesIO(b""),
                "wsgi.url_scheme": "https",
            },
            start_response,
        )
    )
    return captured["status"], body.decode("utf-8")


class _FeedEnv(unittest.TestCase):
    feed: str | None = None

    def setUp(self) -> None:
        saved = {name: os.environ.get(name) for name in ("AWIN_FEED_FILE", "AWIN_FEED_URL")}
        os.environ.pop("AWIN_FEED_URL", None)
        if self.feed is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = self.feed
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)


class WithoutFeedTests(_FeedEnv):
    feed = None

    def test_readiness_does_not_claim_a_connected_source(self) -> None:
        status, body = _get("/private-beta-readiness")
        self.assertEqual(status, "200 OK")
        payload = json.loads(body)
        self.assertNotEqual(payload["status"], "ready")
        source = next(
            check for check in payload["checks"]
            if check["key"] == "product_source_connected_or_honest_not_connected"
        )
        self.assertEqual(source["status"], "needs_data")
        self.assertIn("provider_feed_not_configured", source["details"])

    def test_page_says_no_provider_is_connected(self) -> None:
        _status, body = _get("/search", {"q": "laptop"})
        self.assertIn(_NOT_CONNECTED, body)


class WithConnectedFeedTests(_FeedEnv):
    feed = str(FIXTURE_CSV)

    def test_readiness_reports_the_connected_feed(self) -> None:
        _status, body = _get("/private-beta-readiness")
        source = next(
            check for check in json.loads(body)["checks"]
            if check["key"] == "product_source_connected_or_honest_not_connected"
        )
        self.assertEqual(source["status"], "ready")
        self.assertIn("provider_feed_ready", source["details"])

    def test_too_few_matches_is_not_described_as_no_provider(self) -> None:
        # The fixture holds one laptop bag: the feed is connected, it has no four bags.
        _status, body = _get("/search", {"q": "laptop bag"})
        self.assertNotIn(_NOT_CONNECTED, body)
        self.assertIn(_CONNECTED_NO_FOUR, body)


if __name__ == "__main__":
    unittest.main()
