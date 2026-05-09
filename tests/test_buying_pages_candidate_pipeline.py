from __future__ import annotations

import io
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_buying_pages.candidate_pipeline import run_candidate_pipeline  # noqa: E402
from picwise_buying_pages.economic_scoring import ScoredCandidate  # noqa: E402
from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_buying_pages.keyword_clusters import KeywordSeed  # noqa: E402
from picwise_buying_pages.repository import BuyingPagesRepository  # noqa: E402


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


class BuyingPagesCandidatePipelineTests(unittest.TestCase):
    def test_pipeline_outputs_scored_candidates_only(self) -> None:
        repository = BuyingPagesRepository(load_seed_buying_pages())
        seeds = (
            KeywordSeed(
                category="electronics/gadgets",
                product="wireless headphones",
                brand="Acme",
                specs=("noise cancelling", "travel"),
            ),
            KeywordSeed(
                category="home/appliances",
                product="air purifier",
                brand="PureHome",
                specs=("hepa", "silent"),
            ),
        )
        scored = run_candidate_pipeline(seeds, published_repository=repository)
        self.assertGreater(len(scored), 0)
        self.assertTrue(all(isinstance(item, ScoredCandidate) for item in scored))
        self.assertTrue(all(repository.get_by_slug(item.candidate.slug) is None for item in scored))

    def test_candidate_only_items_do_not_appear_in_sitemap(self) -> None:
        repository = BuyingPagesRepository(load_seed_buying_pages())
        seeds = (
            KeywordSeed(
                category="electronics/gadgets",
                product="office webcam",
                brand="Acme",
                specs=("4k", "autofocus", "streaming"),
            ),
        )
        scored = run_candidate_pipeline(seeds, published_repository=repository)
        self.assertGreater(len(scored), 0)
        _status, _headers, body = _call_wsgi("/sitemap-buying-pages.xml")
        root = ET.fromstring(body)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = [node.text or "" for node in root.findall("sm:url/sm:loc", ns)]
        for candidate in scored:
            self.assertNotIn(f"https://localhost/best/{candidate.candidate.slug}", loc_values)

    def test_candidate_only_items_do_not_resolve_through_best_slug(self) -> None:
        repository = BuyingPagesRepository(load_seed_buying_pages())
        seeds = (
            KeywordSeed(
                category="electronics/gadgets",
                product="portable projector",
                brand="Acme",
                specs=("1080p", "battery"),
            ),
        )
        scored = run_candidate_pipeline(seeds, published_repository=repository)
        self.assertGreater(len(scored), 0)
        status, _headers, body = _call_wsgi(f"/best/{scored[0].candidate.slug}")
        self.assertEqual(status, "404 Not Found")
        self.assertIn("Buying page not found", body)


if __name__ == "__main__":
    unittest.main()
