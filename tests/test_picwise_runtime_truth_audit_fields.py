"""Audit-only tests: backend truth fields must not overclaim purchasability.

These tests do not change runtime behavior; they assert honest labeling
on provider_product_to_backend_dict output for representative feed rows.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.search_selection import (  # noqa: E402
    provider_product_to_backend_dict,
)
from picwise_providers.state import (  # noqa: E402
    load_eligible_provider_feed_products,
    resolve_search_provider_feed_product_selection,
)
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402

_BTO_FEED_DEFAULT = Path(
    r"C:\Users\User\Desktop\picwise-private-feeds\back_to_office_clean_full_columns.csv.gz"
)


def _ensure_bto_feed() -> None:
    if not os.environ.get("AWIN_FEED_FILE") and _BTO_FEED_DEFAULT.is_file():
        os.environ["AWIN_FEED_FILE"] = str(_BTO_FEED_DEFAULT)


class RuntimeTruthBackendFieldsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_bto_feed()

    def test_backend_dict_includes_truth_fields(self) -> None:
        products = load_eligible_provider_feed_products()
        self.assertGreater(len(products), 0, "BTO feed required for audit")
        payload = provider_product_to_backend_dict(products[0])
        for field in (
            "card_eligible",
            "availability_state",
            "purchasability_state",
            "recommendation_confidence_ceiling",
            "card_eligibility_reason_codes",
            "feed_availability_signal",
        ):
            self.assertIn(field, payload, f"missing truth field: {field}")

    def test_selected_products_are_purchasability_unknown_not_verified(self) -> None:
        selection = resolve_search_provider_feed_product_selection(query="laptop")
        if selection.status != "selected":
            self.skipTest("laptop selection unavailable in current feed")
        for product in selection.selected_products:
            payload = provider_product_to_backend_dict(product)
            self.assertEqual(
                payload.get("purchasability_state"),
                "purchasability_unknown",
                "must not claim verified purchasability without verifier evidence",
            )
            self.assertNotEqual(
                payload.get("verification_confidence"),
                "verified",
            )
            self.assertIn(
                payload.get("availability_state"),
                {"weak", "unknown", "trusted", "out_of_stock", "discontinued"},
            )

    def test_office_chair_safe_no_pass_has_zero_selected(self) -> None:
        selection = resolve_search_provider_feed_product_selection(query="office chair")
        self.assertEqual(selection.status, "insufficient_relevant_products")
        self.assertEqual(len(selection.selected_products), 0)


if __name__ == "__main__":
    unittest.main()
