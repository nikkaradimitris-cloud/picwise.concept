import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_verticals.finance_insurance.manifest import get_finance_insurance_taxonomy_manifest
from picwise_verticals.finance_insurance.validation import (
    validate_finance_insurance_taxonomy_manifest,
)


class TestPickwiseFinanceInsuranceTaxonomyContractStage28F(unittest.TestCase):
    def test_manifest_exists_with_exact_official_stage_title(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        self.assertEqual(manifest["stage_title"], "Stage 28F — Finance / Insurance Taxonomy Contract")
        self.assertEqual(manifest["stage_id"], "28F")
        self.assertIsInstance(json.dumps(manifest, sort_keys=True), str)

    def test_vertical_id_is_exact_contract_id(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        self.assertEqual(manifest["vertical_id"], "finance_insurance_business_finance")

    def test_finance_vertical_is_separate_from_retail_and_saas(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        self.assertIn("retail_physical_products", set(manifest["separate_from_vertical_ids"]))
        self.assertIn("software_saas_erp", set(manifest["separate_from_vertical_ids"]))

    def test_finance_vertical_is_not_forced_into_retail_engines(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        self.assertEqual(
            set(manifest["not_forced_into_retail_engines"]),
            {
                "home_living_appliances_engine",
                "tech_electronics_office_engine",
                "auto_moto_mobility_engine",
                "tools_diy_garden_repair_engine",
                "health_beauty_family_lifestyle_engine",
                "fashion_footwear_jewelry_accessories_engine",
            },
        )

    def test_google_taxonomy_is_not_finance_backbone(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        self.assertTrue(manifest["avoids_google_product_taxonomy_backbone"])

    def test_all_required_category_buckets_exist(self) -> None:
        bucket_ids = {
            bucket["bucket_id"]
            for bucket in get_finance_insurance_taxonomy_manifest()["category_buckets"]
        }
        self.assertEqual(
            bucket_ids,
            {
                "banking_accounts_cards",
                "loans_mortgages_leasing",
                "insurance_protection",
                "payments_pos_merchant_services",
                "investing_trading_platforms",
                "business_finance_accounting_tools",
                "tax_legal_compliance_finance_support",
                "financial_education_comparison",
            },
        )

    def test_required_finance_domains_are_represented(self) -> None:
        labels = {
            bucket["display_name"]
            for bucket in get_finance_insurance_taxonomy_manifest()["category_buckets"]
        }
        self.assertIn("Banking / Accounts / Cards", labels)
        self.assertIn("Loans / Mortgages / Leasing", labels)
        self.assertIn("Insurance / Protection", labels)
        self.assertIn("Payments / POS / Merchant Services", labels)
        self.assertIn("Investing / Trading Platforms", labels)
        self.assertIn("Business Finance / Accounting Finance Tools", labels)
        self.assertIn("Tax / Legal / Compliance Finance Support", labels)
        self.assertIn("Financial Education / Comparison / Advisory-safe Content", labels)

    def test_finance_specific_fields_exist_per_bucket(self) -> None:
        required_fields = {
            "fees",
            "interest_rate_type",
            "apr_apy_markers",
            "eligibility_requirements",
            "term_length",
            "coverage_type",
            "deductible_excess",
            "risk_level",
            "country_availability",
            "provider_trust",
            "regulatory_disclaimer_required",
            "manual_review_required",
        }
        for bucket in get_finance_insurance_taxonomy_manifest()["category_buckets"]:
            field_ids = {field["field_id"] for field in bucket["field_definitions"]}
            self.assertTrue(required_fields.issubset(field_ids))

    def test_finance_ranking_dimensions_are_contract_only(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        for dimension in manifest["ranking_dimensions"]:
            self.assertTrue(dimension["contract_only"])
            self.assertFalse(dimension["scoring_implemented"])
        for bucket in manifest["category_buckets"]:
            for dimension in bucket["ranking_dimensions"]:
                self.assertTrue(dimension["contract_only"])
                self.assertFalse(dimension["scoring_implemented"])

    def test_safety_requirements_exist_and_block_regulated_actions(self) -> None:
        required_statuses = {
            "comparison_allowed",
            "review_required",
            "regulated_advice_blocked",
            "quote_application_blocked",
            "eligibility_decision_blocked",
        }
        manifest = get_finance_insurance_taxonomy_manifest()
        for bucket in manifest["category_buckets"]:
            bucket_statuses = {item["safety_status"] for item in bucket["safety_requirements"]}
            self.assertTrue(required_statuses.issubset(bucket_statuses))

    def test_regulated_advice_quote_application_and_eligibility_logic_are_non_goals(self) -> None:
        non_goals = get_finance_insurance_taxonomy_manifest()["non_goals"]
        self.assertTrue(non_goals["regulated_financial_advice_logic"])
        self.assertTrue(non_goals["quote_or_application_logic"])
        self.assertTrue(non_goals["approval_or_eligibility_decision_logic"])

    def test_no_ranking_implementation_exists(self) -> None:
        non_goals = get_finance_insurance_taxonomy_manifest()["non_goals"]
        self.assertTrue(non_goals["ranking_implementation"])
        self.assertTrue(non_goals["finance_or_saas_ranking_implementation"])

    def test_no_stage_29a_massive_query_generator_work_exists(self) -> None:
        non_goals = get_finance_insurance_taxonomy_manifest()["non_goals"]
        self.assertTrue(non_goals["stage_29a_massive_multilingual_noisy_query_generator"])

    def test_no_runtime_or_local_nlu_dependency_required(self) -> None:
        boundaries = get_finance_insurance_taxonomy_manifest()["dependency_boundaries"]
        self.assertFalse(boundaries["runtime_dependency_required"])
        self.assertFalse(boundaries["local_nlu_runtime_dependency_required"])

    def test_no_live_api_or_scraping_dependency_required(self) -> None:
        boundaries = get_finance_insurance_taxonomy_manifest()["dependency_boundaries"]
        self.assertFalse(boundaries["network_or_external_api_calls_required"])

    def test_no_checkout_cart_payment_billing_or_owned_marketplace_inventory(self) -> None:
        non_goals = get_finance_insurance_taxonomy_manifest()["non_goals"]
        self.assertTrue(non_goals["checkout_cart_payment_billing"])
        self.assertTrue(non_goals["owned_provider_marketplace_inventory"])

    def test_references_stage_28d_market_scope(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        self.assertEqual(
            manifest["stage_28d_market_scope_reference"],
            "Stage 28D — PickWise Market Scope Expansion",
        )

    def test_declares_future_finance_source_families_without_live_import(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        self.assertEqual(
            set(manifest["future_source_plans"]),
            {
                "regulated_provider_category_lists",
                "bank_card_loan_insurance_category_references",
                "public_comparison_category_structures",
                "manual_structured_source_lists",
            },
        )

    def test_bucket_source_and_readiness_statuses_are_present(self) -> None:
        manifest = get_finance_insurance_taxonomy_manifest()
        for bucket in manifest["category_buckets"]:
            self.assertTrue(bool(bucket["source_status"]))
            self.assertIn(
                bucket["readiness_status"],
                {
                    "contract_defined",
                    "planned_source_import",
                    "needs_taxonomy_expansion",
                    "blocked_until_future_stage",
                },
            )

    def test_stage_28f_validator_passes_all_required_boundaries(self) -> None:
        report = validate_finance_insurance_taxonomy_manifest()
        self.assertTrue(report["valid"])
        self.assertTrue(report["passed"])
        self.assertTrue(report["stage_title_exact"])
        self.assertTrue(report["vertical_id_exact"])
        self.assertTrue(report["separate_from_retail_physical_products"])
        self.assertTrue(report["separate_from_software_saas_erp"])
        self.assertTrue(report["not_forced_into_any_retail_engine"])
        self.assertTrue(report["google_taxonomy_not_main_backbone"])
        self.assertTrue(report["all_required_buckets_exist"])
        self.assertTrue(report["ranking_dimensions_contract_only_not_implemented"])
        self.assertTrue(report["regulated_advice_blocked"])
        self.assertTrue(report["quote_application_blocked"])
        self.assertTrue(report["eligibility_approval_decision_blocked"])


if __name__ == "__main__":
    unittest.main()
