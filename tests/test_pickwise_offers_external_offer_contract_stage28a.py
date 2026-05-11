from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers import (  # noqa: E402
    ExternalOfferSource,
    ExternalOfferSourceType,
    ExternalOfferStatus,
    validate_external_offer,
)


def _valid_offer_payload() -> dict:
    return {
        "offer_id": "offer-1",
        "external_product_title": "Running Shoes Air Flex",
        "external_store": "Example Store",
        "external_url": "https://example.com/products/running-shoes-air-flex",
        "price": 89.9,
        "availability": "available",
        "delivery": "next day delivery",
        "returns": "free returns within 30-day window",
        "review_score": 4.6,
        "affiliate_url": "https://example.invalid/aff/running-shoes-air-flex",
        "data_source": "fixture_catalog",
        "is_external_offer": True,
    }


class ExternalOfferContractStage28ATests(unittest.TestCase):
    def test_valid_external_offer_contract_accepts_required_fields(self) -> None:
        source = ExternalOfferSource(
            source_id="fixture-source",
            source_type=ExternalOfferSourceType.FIXTURE,
            source_label="fixture_source",
        )
        result = validate_external_offer(_valid_offer_payload(), source)
        self.assertTrue(result.valid)
        self.assertEqual(result.status, ExternalOfferStatus.VALID_EXTERNAL_OFFER)
        self.assertIsNotNone(result.offer)
        assert result.offer is not None
        self.assertEqual(result.offer.external_store, "Example Store")
        self.assertTrue(result.offer.is_external_temporary_data)
        self.assertFalse(result.offer.pickwise_owned_inventory)

    def test_missing_required_fields_fail_validation(self) -> None:
        payload = _valid_offer_payload()
        payload["external_product_title"] = " "
        payload.pop("data_source")
        result = validate_external_offer(payload)
        self.assertFalse(result.valid)
        self.assertEqual(result.status, ExternalOfferStatus.BLOCKED_MISSING_REQUIRED_FIELDS)
        self.assertEqual(result.errors, ("data_source", "external_product_title"))

    def test_invalid_urls_fail_validation(self) -> None:
        payload = _valid_offer_payload()
        payload["external_url"] = "javascript:alert(1)"
        result = validate_external_offer(payload)
        self.assertFalse(result.valid)
        self.assertEqual(result.status, ExternalOfferStatus.BLOCKED_INVALID_URL)

    def test_offer_data_is_marked_external_temporary_not_owned_inventory(self) -> None:
        payload = _valid_offer_payload()
        payload["pickwise_owned_inventory"] = True
        result = validate_external_offer(payload)
        self.assertFalse(result.valid)
        self.assertEqual(result.status, ExternalOfferStatus.BLOCKED_NOT_EXTERNAL)
        self.assertIn("pickwise_owned_inventory_not_allowed", result.errors)

    def test_no_checkout_stock_or_store_ownership_behavior_exists(self) -> None:
        payload = _valid_offer_payload()
        payload["stock_management"] = True
        payload["checkout_enabled"] = True
        result = validate_external_offer(payload)
        self.assertFalse(result.valid)
        self.assertEqual(result.status, ExternalOfferStatus.BLOCKED_NOT_EXTERNAL)
        self.assertIn("stock_management_not_allowed", result.errors)
        self.assertIn("checkout_not_allowed", result.errors)

    def test_no_scraping_or_live_fetch_logic_exists(self) -> None:
        source_text = inspect.getsource(validate_external_offer)
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib",
            "BeautifulSoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
            "fetch(",
            "Invoke-WebRequest",
            "curl",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source_text)

    def test_deterministic_validation_output(self) -> None:
        payload = _valid_offer_payload()
        source = ExternalOfferSource(
            source_id="manual-source",
            source_type=ExternalOfferSourceType.MANUAL_IMPORT,
            source_label="manual_import",
        )
        result_a = validate_external_offer(payload, source)
        result_b = validate_external_offer(payload, source)
        self.assertEqual(result_a, result_b)


if __name__ == "__main__":
    unittest.main()
