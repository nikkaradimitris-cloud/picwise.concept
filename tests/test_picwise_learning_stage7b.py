from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage7b_contracts import SearchLearningCase  # noqa: E402
from picwise_learning.stage7b_contracts import SearchLearningSuggestion  # noqa: E402
from picwise_learning.stage7b_learning_review import classify_search_learning_case  # noqa: E402
from picwise_learning.stage7b_learning_review import collect_search_learning_signals  # noqa: E402
from picwise_learning.stage7b_learning_review import generate_search_learning_suggestions  # noqa: E402
from picwise_learning.stage7b_learning_review import run_controlled_search_learning_review  # noqa: E402

_FORBIDDEN_FIELDS = {
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "prices",
    "affiliate",
    "seller",
    "stock",
    "checkout",
}


class PicWiseLearningStage7BTests(unittest.TestCase):
    def test_contract_payloads_do_not_include_product_or_offer_fields(self) -> None:
        case = SearchLearningCase(
            query="usb caible",
            normalized_query="usb caible",
            observed_status="match",
            expected_behavior="provider_not_connected",
            matched_canonical_id="ca_usb_cable",
            matched_mega_category_id="phones_mobile_accessories",
            confidence=0.91,
            reason_codes=("fuzzy_match",),
            source="test_batch",
            review_status="pending_human_review",
        )
        suggestion = SearchLearningSuggestion(
            suggestion_id="s1",
            suggestion_type="provider needed for category",
            proposed_action="track provider integration priority for category",
            target_layer="provider_connectivity_planning",
            affected_category="phones_mobile_accessories",
            evidence=("usb caible|match|0.9100",),
        )
        self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(set(case.to_dict().keys())))
        self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(set(suggestion.to_dict().keys())))

    def test_collector_classifies_expected_signals(self) -> None:
        rows = (
            SearchLearningCase(
                query="power bank",
                normalized_query="power bank",
                observed_status="match",
                expected_behavior="provider_connected",
                matched_canonical_id="power_banks",
                matched_mega_category_id="phones_mobile_accessories",
                confidence=1.0,
                reason_codes=("exact_normalized_variant_match",),
            ),
            SearchLearningCase(
                query="coffe grindr",
                normalized_query="coffe grindr",
                observed_status="match",
                expected_behavior="provider_not_connected",
                matched_canonical_id="ca_coffee_grinder",
                matched_mega_category_id="kitchen_cooking_household",
                confidence=0.88,
                reason_codes=("fuzzy_match",),
            ),
            SearchLearningCase(
                query="bank",
                normalized_query="bank",
                observed_status="no_match",
                expected_behavior="broad_negative",
                matched_canonical_id="",
                matched_mega_category_id="",
                confidence=0.0,
                reason_codes=("broad_or_ambiguous_query",),
            ),
            SearchLearningCase(
                query="xqzv lmnqpt",
                normalized_query="xqzv lmnqpt",
                observed_status="no_match",
                expected_behavior="unknown",
                matched_canonical_id="",
                matched_mega_category_id="",
                confidence=0.0,
                reason_codes=("no_candidate_found",),
            ),
        )
        classifications = [classify_search_learning_case(row) for row in rows]
        self.assertEqual(classifications[0], "connected_provider_result")
        self.assertEqual(classifications[1], "provider_not_connected")
        self.assertEqual(classifications[2], "broad_negative_safe")
        self.assertEqual(classifications[3], "not_understood")

    def test_suggestions_require_human_approval_and_never_auto_apply(self) -> None:
        report = run_controlled_search_learning_review()
        self.assertTrue(report.suggestions)
        self.assertTrue(all(row.requires_human_approval for row in report.suggestions))
        self.assertTrue(all(not row.can_auto_apply for row in report.suggestions))
        self.assertFalse(report.can_auto_apply_anything)

    def test_contract_rejects_auto_apply_true(self) -> None:
        with self.assertRaises(ValueError):
            SearchLearningSuggestion(
                suggestion_id="bad",
                suggestion_type="no action needed",
                proposed_action="invalid",
                target_layer="offline_learning_review",
                affected_category="unknown_category",
                can_auto_apply=True,
            )

    def test_suggestion_engine_avoids_hardcoded_or_probe_specific_actions(self) -> None:
        report = run_controlled_search_learning_review()
        rendered = " || ".join(
            f"{row.suggestion_type} {row.proposed_action} {row.target_layer}".lower() for row in report.suggestions
        )
        forbidden = (
            "hardcoded lookup",
            "probe example",
            "fixed probe",
            "category_detector.py",
            "live_search_resolver.py",
            "auto_apply=true",
            "add typo string",
            "fake provider",
            "fake product",
            "fake offer",
            "fake price",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, rendered)

    def test_typo_strings_are_not_suggested_as_canonical_vocabulary(self) -> None:
        typo_case = SearchLearningCase(
            query="aaaaab cable",
            normalized_query="aaaaab cable",
            observed_status="no_match",
            expected_behavior="unknown",
            matched_canonical_id="",
            matched_mega_category_id="",
            confidence=0.0,
            reason_codes=("no_candidate_found",),
        )
        results = collect_search_learning_signals((typo_case,))
        suggestions = generate_search_learning_suggestions(results)
        self.assertEqual(len(suggestions), 1)
        self.assertNotEqual(suggestions[0].suggestion_type, "add clean canonical vocabulary term")

    def test_stage6a_generated_blind_evaluation_is_used(self) -> None:
        report = run_controlled_search_learning_review()
        self.assertIn("stage6a_generated_blind_evaluation", report.sources)

    def test_provider_not_connected_yields_provider_needed_not_fake_products(self) -> None:
        report = run_controlled_search_learning_review()
        provider_needed = [row for row in report.suggestions if row.suggestion_type == "provider needed for category"]
        self.assertGreater(len(provider_needed), 0)
        forbidden = " ".join((row.proposed_action + " " + " ".join(row.evidence)).lower() for row in provider_needed)
        for token in ("product", "offer", "price", "seller", "stock"):
            with self.subTest(token=token):
                self.assertNotIn(token, forbidden)

    def test_broad_negative_produces_keep_blocked_or_no_action(self) -> None:
        report = run_controlled_search_learning_review()
        broad_suggestions = [
            row
            for row in report.suggestions
            if row.suggestion_type in {"keep broad negative blocked", "no action needed"}
        ]
        self.assertGreater(len(broad_suggestions), 0)

    def test_connected_power_bank_produces_no_fake_learning_update(self) -> None:
        report = run_controlled_search_learning_review()
        connected_results = [row for row in report.results if row.classification == "connected_provider_result"]
        self.assertGreater(len(connected_results), 0)
        for row in report.suggestions:
            payload = f"{row.suggestion_type} {row.proposed_action}".lower()
            self.assertNotIn("fake", payload)
            self.assertNotIn("provider data seed", payload)


if __name__ == "__main__":
    unittest.main()

