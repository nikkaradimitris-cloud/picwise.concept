import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs import (
    auto_moto_mobility,
    health_beauty_family_lifestyle,
    home_living_appliances,
    tech_electronics_office,
)

_PACK_ACCESSORS = (
    (
        "Stage 26A — Auto / Moto / Mobility Deep Pack",
        auto_moto_mobility.get_auto_moto_mobility_pack,
        auto_moto_mobility.validate_auto_moto_mobility_pack,
    ),
    (
        "Stage 26B — Home / Living / Appliances Deep Pack",
        home_living_appliances.get_home_living_appliances_pack,
        home_living_appliances.validate_home_living_appliances_pack,
    ),
    (
        "Stage 26C — Tech / Electronics / Office Deep Pack",
        tech_electronics_office.get_tech_electronics_office_pack,
        tech_electronics_office.validate_tech_electronics_office_pack,
    ),
    (
        "Stage 26D — Health / Beauty / Family / Lifestyle Deep Pack",
        health_beauty_family_lifestyle.get_health_beauty_family_lifestyle_pack,
        health_beauty_family_lifestyle.validate_health_beauty_family_lifestyle_pack,
    ),
)


class TestPickwiseTaxonomyStage26DeepPackValidation(unittest.TestCase):
    @staticmethod
    def _contains_forbidden_keys(payload: object, forbidden: tuple[str, ...]) -> bool:
        if isinstance(payload, dict):
            for key, value in payload.items():
                lowered = key.lower()
                if any(token in lowered for token in forbidden):
                    return True
                if TestPickwiseTaxonomyStage26DeepPackValidation._contains_forbidden_keys(value, forbidden):
                    return True
            return False
        if isinstance(payload, list):
            return any(TestPickwiseTaxonomyStage26DeepPackValidation._contains_forbidden_keys(item, forbidden) for item in payload)
        return False

    def test_each_stage_26_pack_meets_minimum_depth_rules(self) -> None:
        for _, get_pack, _ in _PACK_ACCESSORS:
            summary = {
                "departments": 0,
                "subcategories": 0,
                "product_families": 0,
                "aliases": 0,
                "spec_fields": 0,
                "intent_patterns": 0,
            }
            for record in get_pack()["mega_categories"]:
                summary["departments"] += len({x.strip().lower() for x in record["departments"] if x.strip()})
                summary["subcategories"] += len({x.strip().lower() for x in record["subcategories"] if x.strip()})
                summary["product_families"] += len({x.strip().lower() for x in record["product_families"] if x.strip()})
                summary["aliases"] += len({x.strip().lower() for x in record["alias_terms"] if x.strip()})
                summary["spec_fields"] += len({x.strip().lower() for x in record["spec_fields"] if x.strip()})
                summary["intent_patterns"] += len({x.strip().lower() for x in record["intent_patterns"] if x.strip()})
            self.assertGreaterEqual(summary["departments"], 3)
            self.assertGreaterEqual(summary["subcategories"], 9)
            self.assertGreaterEqual(summary["product_families"], 30)
            self.assertGreaterEqual(summary["aliases"], 40)
            self.assertGreaterEqual(summary["spec_fields"], 15)
            self.assertGreaterEqual(summary["intent_patterns"], 15)

    def test_structure_and_language_aliases_exist(self) -> None:
        for _, get_pack, _ in _PACK_ACCESSORS:
            for record in get_pack()["mega_categories"]:
                for required in (
                    "departments",
                    "subcategories",
                    "product_families",
                    "alias_terms",
                    "greek_alias_terms",
                    "greeklish_terms",
                    "typo_terms",
                    "spec_fields",
                    "intent_patterns",
                    "source_references",
                ):
                    self.assertIn(required, record)
                    self.assertIsInstance(record[required], list)
                    self.assertGreater(len(record[required]), 0)

    def test_validations_pass_and_registry_alignment_holds(self) -> None:
        for expected_title, _, validate in _PACK_ACCESSORS:
            result = validate()
            self.assertTrue(result["valid"])
            self.assertTrue(result["stage_title_exact"])
            self.assertTrue(result["engine_exists_in_registry"])
            self.assertTrue(result["all_mega_categories_mapped_to_engine"])
            self.assertTrue(result["engine_registry_owns_same_mega_categories"])
            self.assertTrue(result["deterministic_ordering"])

            snapshot = result["coverage_depth_snapshot"]
            self.assertEqual(snapshot["stage_title"], expected_title)

    def test_no_commercial_inventory_tokens_in_packs(self) -> None:
        forbidden = ("price", "sku", "stock", "checkout", "seller", "affiliate", "offer_url", "product_inventory")
        for _, get_pack, _ in _PACK_ACCESSORS:
            self.assertFalse(self._contains_forbidden_keys(get_pack(), forbidden))

    def test_no_runtime_or_local_nlu_dependencies_introduced(self) -> None:
        for module in (
            auto_moto_mobility,
            home_living_appliances,
            tech_electronics_office,
            health_beauty_family_lifestyle,
        ):
            source = inspect.getsource(module)
            self.assertNotIn("picwise_app", source)
            self.assertNotIn("picwise_search", source)
            self.assertNotIn("picwise_nlu", source)
            self.assertNotIn("buying_pages", source)
            self.assertNotIn("decision_router", source)


if __name__ == "__main__":
    unittest.main()
