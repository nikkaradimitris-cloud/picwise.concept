import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs.tools_diy_garden_repair import (
    get_tools_diy_garden_repair_pack,
    get_tools_diy_mega_category_pack,
    validate_tools_diy_garden_repair_pack,
)


def _joined(values: list[str]) -> str:
    return " ".join(values).lower()


class TestPickwiseTaxonomyToolsDepthQuality(unittest.TestCase):
    _MINIMUMS = {
        "power_tools_workshop": {
            "departments": 10,
            "subcategories": 45,
            "product_families": 100,
            "spec_fields": 30,
            "buying_priorities": 20,
            "alias_terms": 80,
            "greeklish_terms": 40,
            "typo_terms": 30,
            "intent_patterns": 60,
            "ambiguity_rules": 10,
        },
        "hand_tools_consumables_measuring": {
            "departments": 12,
            "subcategories": 60,
            "product_families": 130,
            "spec_fields": 30,
            "buying_priorities": 20,
            "alias_terms": 90,
            "greeklish_terms": 50,
            "typo_terms": 35,
            "intent_patterns": 70,
            "ambiguity_rules": 10,
        },
        "garden_outdoor_repair_building": {
            "departments": 12,
            "subcategories": 60,
            "product_families": 130,
            "spec_fields": 30,
            "buying_priorities": 20,
            "alias_terms": 90,
            "greeklish_terms": 50,
            "typo_terms": 35,
            "intent_patterns": 70,
            "ambiguity_rules": 10,
        },
    }

    def test_power_tools_workshop_contains_required_coverage(self) -> None:
        record = get_tools_diy_mega_category_pack("power_tools_workshop")
        self.assertIsNotNone(record)
        assert record is not None
        haystack = _joined(record["departments"] + record["subcategories"] + record["product_families"])
        for keyword in (
            "demolition hammers",
            "bench grinders",
            "table saws",
            "miter saws",
            "tile cutters",
            "polishers",
            "concrete mixers",
            "air tools",
            "battery platforms",
            "dust extraction",
            "workshop lighting",
            "tool organizers",
            "torque tools",
            "inspection cameras",
            "engraving tools",
            "sharpening tools",
            "pumps used in workshop context",
        ):
            self.assertIn(keyword, haystack)

    def test_hand_tools_consumables_measuring_contains_required_coverage(self) -> None:
        record = get_tools_diy_mega_category_pack("hand_tools_consumables_measuring")
        self.assertIsNotNone(record)
        assert record is not None
        haystack = _joined(record["departments"] + record["subcategories"] + record["product_families"])
        for keyword in (
            "hex keys",
            "torx keys",
            "allen keys",
            "torque wrenches",
            "pipe wrenches",
            "adjustable wrenches",
            "crimping tools",
            "stripping tools",
            "soldering tools",
            "tap and die sets",
            "masonry drill bits",
            "metal drill bits",
            "wood drill bits",
            "hole saws",
            "router bits",
            "grinding wheels",
            "flap discs",
            "polishing pads",
            "staples",
            "rivets",
            "cable ties",
            "lubricants",
            "cleaning solvents",
            "threadlockers",
            "tapes",
            "ppe workwear accessories",
        ):
            self.assertIn(keyword, haystack)

    def test_garden_outdoor_repair_building_contains_required_coverage(self) -> None:
        record = get_tools_diy_mega_category_pack("garden_outdoor_repair_building")
        self.assertIsNotNone(record)
        assert record is not None
        haystack = _joined(record["departments"] + record["subcategories"] + record["product_families"])
        for keyword in (
            "robotic lawn mowers",
            "tillers",
            "cultivators",
            "garden sprayers",
            "irrigation timers",
            "drip irrigation",
            "garden hoses and reels",
            "outdoor power cables",
            "outdoor lighting",
            "patio cleaning",
            "drainage accessories",
            "gutters",
            "sealants for roof/walls",
            "waterproofing membranes",
            "plaster repair",
            "tile adhesives",
            "grout",
            "wall fillers",
            "electrical boxes",
            "cable conduits",
            "switches/sockets installation accessories",
            "plumbing fittings",
            "valves",
            "siphons",
            "pipe insulation",
            "ladders by type",
            "step ladders",
            "telescopic ladders",
            "work platforms",
        ):
            self.assertIn(keyword, haystack)

    def test_each_mega_category_meets_stage_23b_minimum_depth(self) -> None:
        for mega_category_id, minimums in self._MINIMUMS.items():
            record = get_tools_diy_mega_category_pack(mega_category_id)
            self.assertIsNotNone(record)
            assert record is not None
            for field, minimum in minimums.items():
                unique_count = len({item.strip().lower() for item in record[field] if item.strip()})
                self.assertGreaterEqual(
                    unique_count,
                    minimum,
                    msg=f"{mega_category_id} field '{field}' has {unique_count}, needs >= {minimum}",
                )

    def test_validation_reports_stage_23b_depth_and_broad_expansion_passed(self) -> None:
        validation = validate_tools_diy_garden_repair_pack()
        self.assertTrue(validation["all_depth_minimums_passed"])
        self.assertTrue(validation["all_broad_expansion_checks_passed"])
        self.assertTrue(validation["valid"])

    def test_validation_fails_when_any_mega_category_is_shallow(self) -> None:
        shallow_pack = get_tools_diy_garden_repair_pack()
        shallow_pack["mega_categories"][0]["product_families"] = shallow_pack["mega_categories"][0]["product_families"][:12]
        with patch(
            "picwise_taxonomy.deep_packs.tools_diy_garden_repair.get_tools_diy_garden_repair_pack",
            return_value=shallow_pack,
        ):
            validation = validate_tools_diy_garden_repair_pack()
        self.assertFalse(validation["all_depth_minimums_passed"])
        self.assertFalse(validation["valid"])

    def test_validation_fails_for_examples_only_without_broad_expansion(self) -> None:
        pack = get_tools_diy_garden_repair_pack()
        for record in pack["mega_categories"]:
            record["subcategories"] = record["subcategories"][:8]
            record["product_families"] = record["product_families"][:10]
            record["alias_terms"] = record["alias_terms"][:12]
            record["greeklish_terms"] = record["greeklish_terms"][:12]
            record["typo_terms"] = record["typo_terms"][:12]
            record["intent_patterns"] = record["intent_patterns"][:12]
            record["buying_priorities"] = record["buying_priorities"][:10]
            record["spec_fields"] = record["spec_fields"][:10]
            record["ambiguity_rules"] = record["ambiguity_rules"][:4]
            record["departments"] = record["departments"][:6]
        with patch(
            "picwise_taxonomy.deep_packs.tools_diy_garden_repair.get_tools_diy_garden_repair_pack",
            return_value=pack,
        ):
            validation = validate_tools_diy_garden_repair_pack()
        self.assertFalse(validation["all_depth_minimums_passed"])
        self.assertFalse(validation["all_broad_expansion_checks_passed"])
        self.assertFalse(validation["valid"])


if __name__ == "__main__":
    unittest.main()
