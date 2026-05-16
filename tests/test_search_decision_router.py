from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_feeds import FeedAdapterProtocol, LocalFixtureFeedAdapter  # noqa: E402
from picwise_search import route_search_query  # noqa: E402


class SearchDecisionRouterTests(unittest.TestCase):
    class _TrackingFeedAdapter(FeedAdapterProtocol):
        def __init__(self) -> None:
            self.last_query: str | None = None
            self.calls = 0
            self._fixture = LocalFixtureFeedAdapter()

        def fetch_candidates(self, query: str):
            self.calls += 1
            self.last_query = query
            return self._fixture.fetch_candidates(query)

    def test_runtime_router_does_not_include_example_specific_terms(self) -> None:
        router_source = (SRC / "picwise_search" / "decision_router.py").read_text(encoding="utf-8").lower()
        forbidden_terms = (
            "goodyear",
            "goodyar",
            "efficientgrip",
            "continental",
            "casio",
            "power bank 20000mah for iphone",
        )
        for term in forbidden_terms:
            self.assertNotIn(term, router_source)

    def test_specific_product_query_routes_to_specific_product(self) -> None:
        for query in (
            "Samsung Galaxy S24 Ultra 256GB",
            "iPhone 15 Pro Max 256GB",
            "Bosch WAN282 washing machine",
            "Casio fx-991CW calculator",
            "Goodyear EfficientGrip Performance 2 195/65 R15",
        ):
            decision = route_search_query(query)
            self.assertEqual(decision.route_type, "specific_product")

    def test_specific_product_uses_multi_store_mode(self) -> None:
        for query in (
            "Samsung Galaxy S24 Ultra 256GB",
            "iPhone 15 Pro Max 256GB",
            "Bosch WAN282 washing machine",
            "Casio fx-991CW calculator",
        ):
            decision = route_search_query(query)
            self.assertEqual(decision.result_mode, "same_product_multi_store_offers")
            self.assertEqual(decision.status, "exact_product_resolution_required")

    def test_general_intent_query_routes_to_general_intent(self) -> None:
        decision = route_search_query("άνετα λάστιχα 195/65 R15 για ταξί")
        self.assertEqual(decision.route_type, "general_intent")
        self.assertEqual(decision.result_mode, "four_product_comparison")

    def test_ambiguous_conflict_query_routes_to_ambiguous_query(self) -> None:
        decision = route_search_query("laptop or tablet for school 256gb")
        self.assertEqual(decision.route_type, "ambiguous_query")
        self.assertEqual(decision.status, "manual_review_required")

    def test_empty_query_routes_to_no_safe_result(self) -> None:
        decision = route_search_query("   ")
        self.assertEqual(decision.route_type, "no_safe_result")
        self.assertEqual(decision.status, "no_valid_offers")

    def test_ambiguous_query_is_not_public_or_indexable_or_sitemap_allowed(self) -> None:
        decision = route_search_query("laptop or tablet for school 256gb")
        self.assertFalse(decision.public_allowed)
        self.assertFalse(decision.indexable_allowed)
        self.assertFalse(decision.sitemap_allowed)

    def test_no_safe_result_is_not_public_or_indexable_or_sitemap_allowed(self) -> None:
        decision = route_search_query("")
        self.assertFalse(decision.public_allowed)
        self.assertFalse(decision.indexable_allowed)
        self.assertFalse(decision.sitemap_allowed)

    def test_unknown_condition_returns_safe_fallback_without_crash(self) -> None:
        with patch("picwise_search.decision_router._is_specific_product", side_effect=RuntimeError("boom")):
            decision = route_search_query("normal query input")
        self.assertEqual(decision.route_type, "no_safe_result")
        self.assertEqual(decision.status, "insufficient_data")
        self.assertIn("router_fallback", decision.reason_codes)

    def test_ambiguous_query_returns_review_only_safe_output_without_products(self) -> None:
        tracking_feed = self._TrackingFeedAdapter()
        app = PicwiseLocalApp(feed_adapter=tracking_feed)
        ambiguous_output = app.build_demo_output("laptop or tablet for school 256gb")
        self.assertEqual(tracking_feed.calls, 0)
        self.assertEqual(ambiguous_output.choices, [])
        self.assertEqual(ambiguous_output.more_choices, [])
        self.assertEqual(ambiguous_output.recommended_product_id, "")
        self.assertEqual(
            ambiguous_output.tracking_context["search_decision"]["route_type"],
            "ambiguous_query",
        )
        self.assertEqual(ambiguous_output.tracking_context["search_decision"]["status"], "manual_review_required")
        self.assertEqual(ambiguous_output.tracking_context["search_decision"]["result_mode"], "review_only")
        self.assertFalse(ambiguous_output.tracking_context["search_decision"]["public_allowed"])
        self.assertFalse(ambiguous_output.tracking_context["search_decision"]["indexable_allowed"])
        self.assertFalse(ambiguous_output.tracking_context["search_decision"]["sitemap_allowed"])

    def test_no_safe_result_returns_explicit_no_result_output_without_products(self) -> None:
        tracking_feed = self._TrackingFeedAdapter()
        app = PicwiseLocalApp(feed_adapter=tracking_feed)
        empty_output = app.build_demo_output("  ")
        self.assertEqual(tracking_feed.calls, 0)
        self.assertEqual(empty_output.choices, [])
        self.assertEqual(empty_output.more_choices, [])
        self.assertEqual(empty_output.recommended_product_id, "")
        self.assertEqual(
            empty_output.tracking_context["search_decision"]["route_type"],
            "no_safe_result",
        )
        self.assertEqual(empty_output.tracking_context["search_decision"]["status"], "no_valid_offers")
        self.assertEqual(empty_output.tracking_context["search_decision"]["result_mode"], "no_result")
        self.assertFalse(empty_output.tracking_context["search_decision"]["public_allowed"])
        self.assertFalse(empty_output.tracking_context["search_decision"]["indexable_allowed"])
        self.assertFalse(empty_output.tracking_context["search_decision"]["sitemap_allowed"])

    def test_specific_product_without_same_product_runtime_data_returns_safe_no_valid_offers(self) -> None:
        tracking_feed = self._TrackingFeedAdapter()
        app = PicwiseLocalApp(feed_adapter=tracking_feed)
        output = app.build_demo_output("Goodyear EfficientGrip Performance 2 195/65 R15")
        self.assertEqual(tracking_feed.calls, 1)
        self.assertEqual(output.choices, [])
        self.assertEqual(output.more_choices, [])
        self.assertEqual(output.recommended_product_id, "")
        self.assertEqual(output.tracking_context["search_decision"]["route_type"], "specific_product")
        self.assertEqual(output.tracking_context["search_decision"]["status"], "no_valid_offers")
        self.assertEqual(output.tracking_context["search_decision"]["result_mode"], "no_result")
        self.assertFalse(output.tracking_context["search_decision"]["public_allowed"])
        self.assertFalse(output.tracking_context["search_decision"]["indexable_allowed"])
        self.assertFalse(output.tracking_context["search_decision"]["sitemap_allowed"])

    def test_ambiguous_and_no_safe_result_html_has_no_product_cards_or_fallback_query(self) -> None:
        app = PicwiseLocalApp()
        ambiguous_html = app.demo_html("laptop or tablet for school 256gb")
        no_result_html = app.demo_html(" ")
        for body in (ambiguous_html, no_result_html):
            self.assertIn("How PicWise will help shoppers decide.", body)
            self.assertIn("This demo page is informational only.", body)
            self.assertNotIn("TravelCore 20K", body)
            self.assertNotIn("DailyBalance PD20", body)
            self.assertNotIn("EverydaySure 22.5W", body)
            self.assertNotIn("PowerMax Elite 25K", body)
            self.assertNotIn('<article class="pw-card', body)
            self.assertNotIn("power bank 20000mah for iphone", body)

    def test_general_queries_keep_existing_demo_card_behavior(self) -> None:
        app = PicwiseLocalApp()
        general_output = app.build_demo_output("power bank for iphone")
        self.assertEqual(len(general_output.choices), 4)
        self.assertEqual(
            general_output.tracking_context["search_decision"]["route_type"],
            "general_intent",
        )


if __name__ == "__main__":
    unittest.main()
