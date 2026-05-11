from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers.fixture_adapter import LocalFixtureOfferSourceAdapter  # noqa: E402
from picwise_offers.import_adapter import (  # noqa: E402
    import_offer_candidates_from_csv_text,
    import_offer_candidates_from_json_text,
)
from picwise_offers.source_intake import build_default_product_source  # noqa: E402


class PickWiseStage32SourceAdaptersTests(unittest.TestCase):
    def test_fixture_source_adapter_is_deterministic(self) -> None:
        adapter = LocalFixtureOfferSourceAdapter()
        source = build_default_product_source()
        first = adapter.fetch(
            query="power bank for iphone",
            search_decision={"route_type": "general_intent"},
            local_nlu_intent={"category": "electronics"},
            source=source,
        )
        second = adapter.fetch(
            query="power bank for iphone",
            search_decision={"route_type": "general_intent"},
            local_nlu_intent={"category": "electronics"},
            source=source,
        )
        self.assertEqual(first, second)

    def test_import_adapters_parse_json_and_csv_without_network(self) -> None:
        json_payload = """
        [
          {
            "candidate_id": "c-1",
            "source_id": "s",
            "source_type": "fixture",
            "title": "Sample Product",
            "brand": "Sample",
            "model": "One",
            "outbound_url": "https://example.com/p/1",
            "vertical": "retail_physical_products"
          }
        ]
        """
        csv_payload = (
            "candidate_id,source_id,source_type,title,brand,model,outbound_url,vertical\n"
            "c-2,s,fixture,Sample Product 2,Sample,Two,https://example.com/p/2,retail_physical_products\n"
        )
        json_candidates = import_offer_candidates_from_json_text(json_payload)
        csv_candidates = import_offer_candidates_from_csv_text(csv_payload)
        self.assertEqual(len(json_candidates), 1)
        self.assertEqual(len(csv_candidates), 1)
        self.assertEqual(json_candidates[0].candidate_id, "c-1")
        self.assertEqual(csv_candidates[0].candidate_id, "c-2")

    def test_source_adapters_do_not_include_scraping_or_live_network_calls(self) -> None:
        source_text = (
            inspect.getsource(LocalFixtureOfferSourceAdapter.fetch)
            + inspect.getsource(import_offer_candidates_from_json_text)
            + inspect.getsource(import_offer_candidates_from_csv_text)
        ).lower()
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "beautifulsoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
            "curl",
            "invoke-webrequest",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source_text)


if __name__ == "__main__":
    unittest.main()
