import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_market_scope.manifest import get_market_scope_manifest, validate_market_scope_manifest


class TestPickwiseMarketScopeStage28D(unittest.TestCase):
    def test_manifest_exists_and_is_json_serializable(self) -> None:
        manifest = get_market_scope_manifest()
        self.assertIsInstance(manifest, dict)
        self.assertTrue(manifest)
        serialized = json.dumps(manifest, sort_keys=True)
        self.assertIsInstance(serialized, str)

    def test_stage_id_and_exact_vertical_set(self) -> None:
        manifest = get_market_scope_manifest()
        self.assertEqual(manifest["stage_id"], "28D")
        self.assertEqual(
            sorted(manifest["verticals"].keys()),
            sorted(
                [
                    "retail_physical_products",
                    "software_saas_erp",
                    "finance_insurance_business_finance",
                ]
            ),
        )

    def test_retail_vertical_scope_and_google_taxonomy_backbone(self) -> None:
        retail = get_market_scope_manifest()["verticals"]["retail_physical_products"]
        self.assertEqual(retail["taxonomy_contract"], "google_product_taxonomy_backbone")
        self.assertTrue(retail["uses_existing_pickwise_6_engines"])
        self.assertTrue("six" in retail["notes"].lower() or "6" in retail["notes"])
        self.assertIn("18", retail["notes"])

    def test_saas_and_finance_are_explicitly_separate_from_retail(self) -> None:
        manifest = get_market_scope_manifest()["verticals"]
        self.assertTrue(
            manifest["software_saas_erp"][
                "must_not_be_forced_into_retail_tech_electronics_office"
            ]
        )
        self.assertTrue(manifest["finance_insurance_business_finance"]["must_not_be_forced_into_retail"])

    def test_each_vertical_has_distinct_contract_and_ranking_dimensions(self) -> None:
        verticals = get_market_scope_manifest()["verticals"].values()
        contracts = {vertical["taxonomy_contract"] for vertical in verticals}
        dimensions = {tuple(vertical["ranking_dimensions"]) for vertical in verticals}
        self.assertEqual(len(contracts), 3)
        self.assertEqual(len(dimensions), 3)

    def test_clarifications_and_non_goals_are_fully_declared(self) -> None:
        manifest = get_market_scope_manifest()
        self.assertTrue(all(manifest["clarifications"].values()))
        self.assertTrue(all(manifest["non_goals"].values()))

    def test_validator_reports_passed_true(self) -> None:
        report = validate_market_scope_manifest()
        self.assertTrue(report["valid"])
        self.assertTrue(report["passed"])
        self.assertTrue(report["has_exact_three_required_verticals"])
        self.assertTrue(report["all_verticals_have_distinct_taxonomy_contracts"])
        self.assertTrue(report["all_verticals_have_distinct_ranking_dimensions"])


if __name__ == "__main__":
    unittest.main()
