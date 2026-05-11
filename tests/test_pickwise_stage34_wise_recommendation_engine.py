from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers import OfferCandidate, build_pickwise_recommendation_set  # noqa: E402
from picwise_offers.recommendation_engine import RecommendationStatus  # noqa: E402


def _candidate(candidate_id: str, price: float, **overrides: object) -> OfferCandidate:
    payload = {
        "candidate_id": candidate_id,
        "source_id": "fixture-source",
        "source_type": "fixture",
        "title": f"Power Bank {candidate_id}",
        "brand": "Brand",
        "model": candidate_id,
        "image_url": "https://example.com/images/item.jpg",
        "price": price,
        "currency": "EUR",
        "seller_name": "Seller",
        "seller_url": "https://example.com/store",
        "availability_status": "available",
        "outbound_url": f"https://example.com/product/{candidate_id}",
        "affiliate_url": f"https://example.invalid/aff/{candidate_id}",
        "category": "power_bank",
        "vertical": "retail_physical_products",
        "engine": "electronics_hypermarket",
        "category_bucket": "power_banks",
        "google_taxonomy_path": "Electronics > Power Banks",
        "saas_erp_contract_ref": None,
        "finance_insurance_contract_ref": None,
        "source_updated_at": "2026-05-01T00:00:00Z",
        "metadata": {},
    }
    payload.update(overrides)
    return OfferCandidate(**payload)


class PickWiseStage34WiseRecommendationEngineTests(unittest.TestCase):
    def test_four_display_slots_when_enough_eligible_candidates_exist(self) -> None:
        candidates = tuple(_candidate(f"c{i}", price=20.0 + i) for i in range(1, 6))
        result = build_pickwise_recommendation_set(
            query="power bank for iphone",
            eligible_candidates=candidates,
        )
        self.assertEqual(result.status, RecommendationStatus.READY)
        self.assertEqual(len(result.display_slots), 4)

    def test_not_enough_valid_candidates_does_not_create_filler(self) -> None:
        candidates = (_candidate("c1", price=29.0), _candidate("c2", price=39.0))
        result = build_pickwise_recommendation_set(
            query="power bank",
            eligible_candidates=candidates,
        )
        self.assertEqual(result.status, RecommendationStatus.NOT_ENOUGH_VALID_CANDIDATES)
        self.assertEqual(len(result.display_slots), 2)
        slot_ids = {slot.candidate_id for slot in result.display_slots}
        self.assertEqual(slot_ids, {"c1", "c2"})

    def test_wise_recommended_product_is_deterministic_and_explainable(self) -> None:
        candidates = (
            _candidate("best", price=25.0, title="power bank iphone fast charge best"),
            _candidate("mid", price=39.0, title="power bank phone", availability_status="unknown", affiliate_url=None),
            _candidate("alt", price=49.0, title="backup charger", availability_status="unknown", affiliate_url=None),
            _candidate("alt2", price=55.0, title="portable battery", availability_status="unknown", affiliate_url=None),
        )
        first = build_pickwise_recommendation_set(query="power bank iphone fast charge", eligible_candidates=candidates)
        second = build_pickwise_recommendation_set(query="power bank iphone fast charge", eligible_candidates=candidates)
        self.assertEqual(first, second)
        self.assertIsNotNone(first.wise_recommended_product)
        assert first.wise_recommended_product is not None
        self.assertTrue(first.wise_recommended_product.explanation)


if __name__ == "__main__":
    unittest.main()
