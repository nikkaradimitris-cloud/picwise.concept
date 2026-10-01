"""Local in-repo provider feed fixture coverage.

Purpose: make the real-feed provider pipeline runnable and regression-testable
without the operator's private Awin feed file.

The fixture is explicitly local test data (`local_test_fixture`). It is never
live-feed proof: stage closure for real feed/affiliate connection still needs
operator-supplied provider data and a runtime truth audit against it.
"""
from __future__ import annotations

import gzip
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.purchasability_cache import (  # noqa: E402
    clear_purchasability_cache_configuration,
    configure_purchasability_cache,
)
from picwise_providers.search_selection import provider_product_to_backend_dict  # noqa: E402
from picwise_providers.state import (  # noqa: E402
    resolve_provider_feed_pipeline,
    resolve_search_provider_feed_selection_with_recommendation,
)

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"
FIXTURE_CACHE = (
    ROOT / "tests" / "fixtures" / "provider_feed_local_test_purchasability_cache.json"
)

_BLOCKED_ROW_IDS = (
    "fx-laptop-oos",
    "fx-laptop-eol",
    "fx-laptop-noimg",
    "fx-laptop-noprice",
)


def _feed_config(feed_file: Path) -> ProviderFeedConfig:
    return ProviderFeedConfig(provider_key="awin", feed_file=str(feed_file))


def _selection(query: str, feed_file: Path = FIXTURE_CSV):
    return resolve_search_provider_feed_selection_with_recommendation(
        query=query,
        feed_config=_feed_config(feed_file),
    )


class LocalFixtureIntegrityTests(unittest.TestCase):
    def test_fixture_files_exist(self) -> None:
        self.assertTrue(FIXTURE_CSV.is_file())
        self.assertTrue(FIXTURE_CACHE.is_file())

    def test_every_fixture_row_is_marked_as_local_test_data(self) -> None:
        lines = FIXTURE_CSV.read_text(encoding="utf-8").strip().splitlines()
        self.assertIn("data_provenance", lines[0])
        for line in lines[1:]:
            self.assertIn("local_test_fixture", line)

    def test_fixture_urls_never_point_at_a_resolvable_host(self) -> None:
        text = FIXTURE_CSV.read_text(encoding="utf-8")
        for token in text.split(","):
            candidate = token.strip()
            if candidate.startswith("http"):
                self.assertIn(
                    ".invalid/",
                    candidate,
                    msg="fixture URLs must stay inside the reserved .invalid TLD",
                )


class ProviderFeedPipelineTests(unittest.TestCase):
    def test_pipeline_reaches_ready_state(self) -> None:
        pipeline = resolve_provider_feed_pipeline(_feed_config(FIXTURE_CSV))
        self.assertEqual(pipeline.feed_status.status, "provider_feed_ready")
        self.assertEqual(pipeline.feed_status.provider_key, "awin")
        self.assertGreater(pipeline.feed_status.eligible_count, 0)

    def test_unavailable_and_incomplete_rows_are_not_card_eligible(self) -> None:
        pipeline = resolve_provider_feed_pipeline(_feed_config(FIXTURE_CSV))
        by_id = {
            row.product.provider_product_id: row for row in pipeline.eligibility_results
        }
        for row_id in _BLOCKED_ROW_IDS:
            self.assertIn(row_id, by_id)
            eligibility = by_id[row_id].product_eligibility
            self.assertIsNotNone(eligibility)
            self.assertFalse(
                eligibility.card_eligible,
                msg=f"{row_id} must never become a card",
            )
            self.assertTrue(eligibility.reason_codes)

    def test_gzip_feed_payload_matches_plain_csv(self) -> None:
        plain = resolve_provider_feed_pipeline(_feed_config(FIXTURE_CSV))
        with tempfile.TemporaryDirectory() as tmp:
            gz_path = Path(tmp) / "provider_feed_local_test_fixture.csv.gz"
            gz_path.write_bytes(gzip.compress(FIXTURE_CSV.read_bytes()))
            gzipped = resolve_provider_feed_pipeline(_feed_config(gz_path))
        self.assertEqual(gzipped.feed_status.status, plain.feed_status.status)
        self.assertEqual(gzipped.feed_status.product_count, plain.feed_status.product_count)
        self.assertEqual(
            gzipped.feed_status.eligible_count, plain.feed_status.eligible_count
        )


class FourPlusOneDecisionTests(unittest.TestCase):
    def test_supported_product_types_produce_four_plus_one(self) -> None:
        for query in ("laptop", "mouse", "monitor"):
            with self.subTest(query=query):
                selection, decision = _selection(query)
                self.assertEqual(selection.status, "selected")
                self.assertEqual(len(selection.selected_products), 4)
                self.assertEqual(decision.decision_status, "recommended")
                selected_ids = {
                    product.provider_product_id
                    for product in selection.selected_products
                }
                self.assertIn(decision.recommended_product_id, selected_ids)
                self.assertTrue(decision.recommendation_reason_codes)

    def test_blocked_rows_never_appear_in_a_selection(self) -> None:
        for query in ("laptop", "mouse", "monitor"):
            with self.subTest(query=query):
                selection, _ = _selection(query)
                selected_ids = {
                    product.provider_product_id
                    for product in selection.selected_products
                }
                for row_id in _BLOCKED_ROW_IDS:
                    self.assertNotIn(row_id, selected_ids)

    def test_accessory_row_does_not_satisfy_a_main_product_query(self) -> None:
        selection, _ = _selection("laptop")
        selected_ids = {
            product.provider_product_id for product in selection.selected_products
        }
        self.assertNotIn("fx-laptop-bag", selected_ids)

    def test_query_without_matching_inventory_stays_safely_empty(self) -> None:
        for query in ("office chair", "laptop bag"):
            with self.subTest(query=query):
                selection, decision = _selection(query)
                self.assertEqual(selection.status, "insufficient_relevant_products")
                self.assertEqual(selection.selected_products, tuple())
                self.assertEqual(decision.decision_status, "insufficient_selected_products")
                self.assertIsNone(decision.recommended_product_id)


class RuntimeTruthTests(unittest.TestCase):
    def test_unverified_feed_rows_never_claim_purchasability(self) -> None:
        selection, _ = _selection("laptop")
        self.assertEqual(len(selection.selected_products), 4)
        for product in selection.selected_products:
            payload = provider_product_to_backend_dict(product)
            self.assertEqual(payload["purchasability_state"], "purchasability_unknown")
            self.assertFalse(payload["verified_purchasable"])
            self.assertEqual(payload["recommendation_confidence_ceiling"], "limited")

    def test_feed_availability_text_alone_is_not_strong_availability(self) -> None:
        selection, _ = _selection("laptop")
        for product in selection.selected_products:
            payload = provider_product_to_backend_dict(product)
            self.assertEqual(payload["availability_state"], "weak")

    def test_backend_dict_exports_common_provider_fields(self) -> None:
        selection, _ = _selection("laptop")
        for product in selection.selected_products:
            payload = provider_product_to_backend_dict(product)
            self.assertTrue(payload["brand"])
            self.assertTrue(payload["currency"])
            self.assertEqual(payload["product_type"], "Laptops")


class PurchasabilityCacheGateTests(unittest.TestCase):
    def setUp(self) -> None:
        configure_purchasability_cache(str(FIXTURE_CACHE))
        self.addCleanup(clear_purchasability_cache_configuration)
        self.addCleanup(os.environ.pop, "PICWISE_PURCHASABILITY_CACHE_FILE", None)

    def test_verified_purchasable_row_is_reported_as_verified(self) -> None:
        selection, _ = _selection("laptop")
        payloads = {
            product.provider_product_id: provider_product_to_backend_dict(product)
            for product in selection.selected_products
        }
        self.assertIn("fx-laptop-1", payloads)
        verified = payloads["fx-laptop-1"]
        self.assertEqual(verified["purchasability_state"], "purchasable")
        self.assertTrue(verified["verified_purchasable"])

    def test_verified_unbuyable_rows_are_dropped_from_the_four(self) -> None:
        selection, decision = _selection("laptop")
        self.assertEqual(selection.status, "selected")
        self.assertEqual(len(selection.selected_products), 4)
        selected_ids = {
            product.provider_product_id for product in selection.selected_products
        }
        # fx-laptop-3 is verified out_of_stock, fx-laptop-6 missing_buy_button,
        # even though the feed row claims "in stock".
        self.assertNotIn("fx-laptop-3", selected_ids)
        self.assertNotIn("fx-laptop-6", selected_ids)
        self.assertIn(decision.recommended_product_id, selected_ids)


if __name__ == "__main__":
    unittest.main()
