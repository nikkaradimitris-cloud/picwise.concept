from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers import OfferCandidate, SourceTrustLevel, run_product_eligibility_gate  # noqa: E402
from picwise_offers.eligibility import EligibilityStatus  # noqa: E402


def _candidate(candidate_id: str, **overrides: object) -> OfferCandidate:
    payload = {
        "candidate_id": candidate_id,
        "source_id": "fixture-source",
        "source_type": "fixture",
        "title": "Sample Product",
        "brand": "Brand",
        "model": "Model",
        "image_url": "https://example.com/images/sample.jpg",
        "price": 10.0,
        "currency": "EUR",
        "seller_name": "Seller",
        "seller_url": "https://example.com/store",
        "availability_status": "available",
        "outbound_url": "https://example.com/product",
        "affiliate_url": None,
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


class PickWiseStage33ProductEligibilityGateTests(unittest.TestCase):
    def test_missing_title_or_outbound_url_is_needs_data(self) -> None:
        candidates = (
            _candidate("c1", title=None),
            _candidate("c2", outbound_url=None),
        )
        result = run_product_eligibility_gate(
            candidates,
            expected_vertical="retail_physical_products",
            source_trust_level=SourceTrustLevel.PARTNER_VERIFIED,
            source_connected=True,
        )
        self.assertEqual(result.decisions[0].status, EligibilityStatus.NEEDS_DATA)
        self.assertEqual(result.decisions[1].status, EligibilityStatus.NEEDS_DATA)

    def test_invalid_url_duplicate_and_unsafe_source_are_rejected(self) -> None:
        candidates = (
            _candidate("c1", outbound_url="javascript:alert(1)"),
            _candidate("c2"),
            _candidate("c3"),
        )
        result = run_product_eligibility_gate(
            candidates,
            expected_vertical="retail_physical_products",
            source_trust_level=SourceTrustLevel.UNSAFE,
            source_connected=True,
        )
        statuses = [decision.status for decision in result.decisions]
        self.assertTrue(all(status == EligibilityStatus.REJECTED for status in statuses))
        reason_codes = {code for decision in result.decisions for code in decision.reason_codes}
        self.assertIn("invalid_outbound_url", reason_codes)
        self.assertIn("duplicate_product", reason_codes)
        self.assertIn("unsafe_source", reason_codes)

    def test_saas_or_finance_forced_into_retail_is_not_applicable_or_manual_review(self) -> None:
        candidates = (
            _candidate("s1", vertical="software_saas_erp", model="SaaSModel"),
            _candidate(
                "f1",
                vertical="finance_insurance_business_finance",
                model="FinanceModel",
                title="Finance Product",
                metadata={"regulated": True},
            ),
        )
        result = run_product_eligibility_gate(
            candidates,
            expected_vertical="retail_physical_products",
            source_trust_level=SourceTrustLevel.PARTNER_VERIFIED,
            source_connected=True,
        )
        self.assertEqual(result.decisions[0].status, EligibilityStatus.NOT_APPLICABLE)
        self.assertEqual(result.decisions[1].status, EligibilityStatus.MANUAL_REVIEW)


if __name__ == "__main__":
    unittest.main()
