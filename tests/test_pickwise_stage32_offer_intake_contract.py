from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers import (  # noqa: E402
    LocalFixtureOfferSourceAdapter,
    OfferIntakeRequest,
    ProductSourceRecord,
    ProductSourceStatus,
    SourceTrustLevel,
    build_default_product_source,
    intake_offer_candidates,
)


class PickWiseStage32OfferIntakeContractTests(unittest.TestCase):
    def test_intake_contract_exposes_required_candidate_fields(self) -> None:
        source = build_default_product_source()
        result = intake_offer_candidates(
            OfferIntakeRequest(
                query="power bank for iphone",
                search_decision={"route_type": "general_intent"},
                local_nlu_intent={"category": "electronics"},
                source=source,
            ),
            adapter=LocalFixtureOfferSourceAdapter(),
        )
        self.assertEqual(result.status, ProductSourceStatus.CONNECTED)
        self.assertGreaterEqual(len(result.candidates), 4)
        candidate = result.candidates[0]
        required = (
            "candidate_id",
            "source_id",
            "source_type",
            "title",
            "brand",
            "model",
            "image_url",
            "price",
            "currency",
            "seller_name",
            "seller_url",
            "availability_status",
            "outbound_url",
            "affiliate_url",
            "category",
            "vertical",
            "engine",
            "category_bucket",
            "google_taxonomy_path",
            "saas_erp_contract_ref",
            "finance_insurance_contract_ref",
            "source_updated_at",
            "metadata",
        )
        for field in required:
            self.assertTrue(hasattr(candidate, field))

    def test_not_connected_source_returns_honest_empty_state(self) -> None:
        disconnected_source = ProductSourceRecord(
            source_id="missing",
            source_type="fixture",
            source_label="missing source",
            status=ProductSourceStatus.NOT_CONNECTED,
            trust_level=SourceTrustLevel.UNKNOWN,
            verticals=("retail_physical_products",),
            metadata={},
        )
        result = intake_offer_candidates(
            OfferIntakeRequest(
                query="power bank",
                search_decision={"route_type": "general_intent"},
                local_nlu_intent={},
                source=disconnected_source,
            ),
            adapter=LocalFixtureOfferSourceAdapter(),
        )
        self.assertEqual(result.status, ProductSourceStatus.NOT_CONNECTED)
        self.assertEqual(result.candidates, tuple())
        self.assertIn("source_not_connected", result.reason_codes)


if __name__ == "__main__":
    unittest.main()
