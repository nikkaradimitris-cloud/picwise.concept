"""Which kinds of product support "better", and on what.

Owner instruction, 2026-10-12: make rules for the subcategories that cannot be
compared with each other, find the ones that do not support the notions of comparison
and best -- those get a "see more" button -- and find which ones have criteria such as
bytes, megabytes or kilos, for grouping and for the comparison logic.

Their examples were exact: no best pair of shoes, no best bag, no best tablecloth.
These tests pin that those kinds never carry a best claim, and that the distinction
the rules rest on holds everywhere: a criterion either decides which is **better**
(more is better for every buyer) or decides which **fits** (the buyer wants a value),
and no criterion is ever both.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_nlu.product_concepts import get_product_concepts  # noqa: E402
from picwise_providers.product_specs import RANKING_PROPERTIES  # noqa: E402
from picwise_taxonomy.comparison_rules import (  # noqa: E402
    MATCHING_CRITERIA,
    RANKING_CRITERIA,
    comparison_rule,
    kinds_with_a_ranking_criterion,
    kinds_without_a_best,
)


class OwnersExamplesTests(unittest.TestCase):
    """The kinds the owner named as having no best."""

    def test_shoes_a_bag_and_home_textiles_claim_no_best(self) -> None:
        for concept_id in ("shoes", "bag", "handbag", "curtains", "bed_linen", "towels",
                           "dress", "ring", "wall_clock"):
            with self.subTest(concept_id=concept_id):
                rule = comparison_rule(concept_id)
                self.assertEqual(rule.comparison_class, "fit")
                self.assertFalse(rule.supports_best)
                self.assertTrue(rule.shows_see_more)

    def test_a_kind_with_no_best_never_carries_a_ranking_criterion(self) -> None:
        for concept_id in kinds_without_a_best():
            with self.subTest(concept_id=concept_id):
                self.assertEqual(comparison_rule(concept_id).ranking_criteria, tuple())


class RankingVersusMatchingTests(unittest.TestCase):
    """A criterion decides which is better, or which fits. Never both."""

    def test_no_criterion_is_both_for_the_same_kind(self) -> None:
        for concept in get_product_concepts():
            rule = comparison_rule(concept.concept_id)
            with self.subTest(concept_id=concept.concept_id):
                self.assertEqual(
                    set(rule.ranking_criteria) & set(rule.matching_criteria), set()
                )

    def test_the_two_vocabularies_never_overlap(self) -> None:
        self.assertEqual(set(RANKING_CRITERIA) & set(MATCHING_CRITERIA), set())

    def test_every_criterion_named_is_a_known_criterion(self) -> None:
        for concept in get_product_concepts():
            rule = comparison_rule(concept.concept_id)
            with self.subTest(concept_id=concept.concept_id):
                for name in rule.ranking_criteria:
                    self.assertIn(name, RANKING_CRITERIA)
                for name in rule.matching_criteria:
                    self.assertIn(name, MATCHING_CRITERIA)

    def test_the_ranking_criteria_a_feed_can_read_match_the_spec_reader(self) -> None:
        # Whatever `product_specs` is willing to rank on must be a ranking criterion
        # here, or the engine would rank on something these rules call a fit.
        self.assertTrue(set(RANKING_PROPERTIES).issubset(set(RANKING_CRITERIA)))

    def test_cable_length_fits_and_never_ranks(self) -> None:
        # Owner's explicit answer, 2026-10-12: shown on the card, decides nothing.
        rule = comparison_rule("charging_cable")
        self.assertIn("length", rule.matching_criteria)
        self.assertEqual(rule.ranking_criteria, tuple())

    def test_inches_and_kilos_fit_and_never_rank(self) -> None:
        # A 10 kg washing machine is not better than a 7 kg one, and a 65 inch
        # television is not better than a 50 inch one. They are bigger.
        washing = comparison_rule("washing_machine")
        self.assertIn("capacity_kg", washing.matching_criteria)
        self.assertNotIn("capacity_kg", washing.ranking_criteria)
        television = comparison_rule("television")
        self.assertIn("screen", television.matching_criteria)
        self.assertNotIn("screen", television.ranking_criteria)

    def test_a_part_that_must_fit_is_decided_by_fitment_not_merit(self) -> None:
        for concept_id in ("ink_cartridge", "oil_filter", "spark_plugs", "wiper_blades",
                           "phone_case", "snow_chains"):
            with self.subTest(concept_id=concept_id):
                rule = comparison_rule(concept_id)
                self.assertEqual(rule.comparison_class, "fit")
                self.assertTrue(rule.matching_criteria)


class SpecClassTests(unittest.TestCase):
    def test_every_spec_kind_names_a_ranking_criterion(self) -> None:
        for concept_id in kinds_with_a_ranking_criterion():
            with self.subTest(concept_id=concept_id):
                rule = comparison_rule(concept_id)
                self.assertEqual(rule.comparison_class, "spec")
                self.assertTrue(rule.ranking_criteria)
                self.assertTrue(rule.supports_best)
                self.assertFalse(rule.shows_see_more)

    def test_storage_and_battery_bearers_are_spec_comparable(self) -> None:
        self.assertIn("storage", comparison_rule("storage_drive").ranking_criteria)
        self.assertIn("battery", comparison_rule("power_bank").ranking_criteria)
        self.assertIn("storage", comparison_rule("tv_box").ranking_criteria)
        self.assertIn("playtime", comparison_rule("headphones").ranking_criteria)


class RatingClassTests(unittest.TestCase):
    """Quality is real, no feed number measures it, so only a rating separates them."""

    def test_a_tool_or_an_appliance_without_a_number_falls_to_rating(self) -> None:
        for concept_id in ("drill", "frying_pan", "shampoo", "child_car_seat", "kettle",
                           "camera", "amplifier", "speaker"):
            with self.subTest(concept_id=concept_id):
                rule = comparison_rule(concept_id)
                self.assertEqual(rule.comparison_class, "rating")
                self.assertTrue(rule.supports_best)
                self.assertFalse(rule.shows_see_more)

    def test_an_unknown_kind_falls_to_rating_not_to_a_best_claim_on_price(self) -> None:
        rule = comparison_rule("something_picwise_has_never_seen")
        self.assertEqual(rule.comparison_class, "rating")
        self.assertEqual(rule.ranking_criteria, tuple())

    def test_performance_goods_are_separated_from_their_fashion_twins(self) -> None:
        # A safety boot has a standard to meet; a sandal has a style. Deliberate, and
        # the owner may move either.
        self.assertEqual(comparison_rule("safety_shoes").comparison_class, "rating")
        self.assertEqual(comparison_rule("running_shoes").comparison_class, "rating")
        self.assertEqual(comparison_rule("shoes").comparison_class, "fit")
        self.assertEqual(comparison_rule("work_trousers").comparison_class, "rating")
        self.assertEqual(comparison_rule("trousers").comparison_class, "fit")


class CoverageTests(unittest.TestCase):
    def test_every_kind_picwise_recognises_has_a_rule(self) -> None:
        for concept in get_product_concepts():
            with self.subTest(concept_id=concept.concept_id):
                rule = comparison_rule(concept.concept_id)
                self.assertIn(rule.comparison_class, ("spec", "rating", "fit"))
                self.assertEqual(rule.concept_id, concept.concept_id)

    def test_a_rule_is_never_silently_both_classes(self) -> None:
        both = set(kinds_without_a_best()) & set(kinds_with_a_ranking_criterion())
        self.assertEqual(both, set())


if __name__ == "__main__":
    unittest.main()
