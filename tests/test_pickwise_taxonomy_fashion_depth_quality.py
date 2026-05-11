import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs.fashion_footwear_jewelry_accessories import (
    get_fashion_footwear_jewelry_accessories_pack,
    get_fashion_mega_category_pack,
    validate_fashion_footwear_jewelry_accessories_pack,
)


def _joined(values: list[str]) -> str:
    return " ".join(values).lower()


class TestPickwiseTaxonomyFashionDepthQuality(unittest.TestCase):
    _MINIMUMS = {
        "clothing_apparel_workwear": {
            "departments": 12,
            "subcategories": 70,
            "product_families": 140,
            "spec_fields": 35,
            "buying_priorities": 25,
            "alias_terms": 100,
            "greeklish_terms": 60,
            "typo_terms": 40,
            "intent_patterns": 80,
            "ambiguity_rules": 12,
        },
        "footwear_shoes_sneakers_boots": {
            "departments": 12,
            "subcategories": 70,
            "product_families": 140,
            "spec_fields": 40,
            "buying_priorities": 30,
            "alias_terms": 110,
            "greeklish_terms": 65,
            "typo_terms": 45,
            "intent_patterns": 90,
            "ambiguity_rules": 14,
        },
        "jewelry_watches_bags_fashion_accessories": {
            "departments": 12,
            "subcategories": 70,
            "product_families": 140,
            "spec_fields": 35,
            "buying_priorities": 25,
            "alias_terms": 100,
            "greeklish_terms": 60,
            "typo_terms": 40,
            "intent_patterns": 80,
            "ambiguity_rules": 12,
        },
    }

    def test_clothing_apparel_workwear_contains_required_coverage(self) -> None:
        record = get_fashion_mega_category_pack("clothing_apparel_workwear")
        self.assertIsNotNone(record)
        assert record is not None
        haystack = _joined(record["departments"] + record["subcategories"] + record["product_families"])
        for keyword in (
            "clothing",
            "jackets",
            "trousers",
            "dresses",
            "underwear",
            "sportswear",
            "workwear",
            "plus size",
            "thermal clothing",
            "rainwear",
        ):
            self.assertIn(keyword, haystack)

    def test_footwear_contains_required_coverage(self) -> None:
        record = get_fashion_mega_category_pack("footwear_shoes_sneakers_boots")
        self.assertIsNotNone(record)
        assert record is not None
        haystack = _joined(record["departments"] + record["subcategories"] + record["product_families"])
        for keyword in (
            "sneakers",
            "walking shoes",
            "running shoes",
            "work shoes",
            "safety shoes",
            "boots",
            "sandals",
            "wide fit shoes",
            "insoles",
            "shoe care accessories",
        ):
            self.assertIn(keyword, haystack)

    def test_jewelry_watches_bags_accessories_contains_required_coverage(self) -> None:
        record = get_fashion_mega_category_pack("jewelry_watches_bags_fashion_accessories")
        self.assertIsNotNone(record)
        assert record is not None
        haystack = _joined(record["departments"] + record["subcategories"] + record["product_families"])
        for keyword in (
            "jewelry",
            "watches",
            "sunglasses",
            "handbags",
            "backpacks",
            "laptop bags",
            "travel bags",
            "wallets",
            "belts",
        ):
            self.assertIn(keyword, haystack)

    def test_each_mega_category_meets_stage_23c_minimum_depth(self) -> None:
        for mega_category_id, minimums in self._MINIMUMS.items():
            record = get_fashion_mega_category_pack(mega_category_id)
            self.assertIsNotNone(record)
            assert record is not None
            for field, minimum in minimums.items():
                unique_count = len({item.strip().lower() for item in record[field] if item.strip()})
                self.assertGreaterEqual(
                    unique_count,
                    minimum,
                    msg=f"{mega_category_id} field '{field}' has {unique_count}, needs >= {minimum}",
                )

    def test_validation_reports_stage_23c_depth_and_broad_expansion_passed(self) -> None:
        validation = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertTrue(validation["all_depth_minimums_passed"])
        self.assertTrue(validation["all_broad_expansion_checks_passed"])
        self.assertTrue(validation["valid"])

    def test_validation_fails_when_any_mega_category_is_shallow(self) -> None:
        shallow_pack = get_fashion_footwear_jewelry_accessories_pack()
        shallow_pack["mega_categories"][0]["product_families"] = shallow_pack["mega_categories"][0]["product_families"][:12]
        with patch(
            "picwise_taxonomy.deep_packs.fashion_footwear_jewelry_accessories.get_fashion_footwear_jewelry_accessories_pack",
            return_value=shallow_pack,
        ):
            validation = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertFalse(validation["all_depth_minimums_passed"])
        self.assertFalse(validation["valid"])

    def test_validation_fails_for_examples_only_without_broad_expansion(self) -> None:
        pack = get_fashion_footwear_jewelry_accessories_pack()
        for record in pack["mega_categories"]:
            record["departments"] = record["departments"][:6]
            record["subcategories"] = record["subcategories"][:8]
            record["product_families"] = record["product_families"][:10]
            record["alias_terms"] = record["alias_terms"][:12]
            record["greeklish_terms"] = record["greeklish_terms"][:12]
            record["typo_terms"] = record["typo_terms"][:12]
            record["intent_patterns"] = record["intent_patterns"][:12]
            record["buying_priorities"] = record["buying_priorities"][:10]
            record["spec_fields"] = record["spec_fields"][:10]
            record["ambiguity_rules"] = record["ambiguity_rules"][:4]
        with patch(
            "picwise_taxonomy.deep_packs.fashion_footwear_jewelry_accessories.get_fashion_footwear_jewelry_accessories_pack",
            return_value=pack,
        ):
            validation = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertFalse(validation["all_depth_minimums_passed"])
        self.assertFalse(validation["all_broad_expansion_checks_passed"])
        self.assertFalse(validation["valid"])


if __name__ == "__main__":
    unittest.main()
