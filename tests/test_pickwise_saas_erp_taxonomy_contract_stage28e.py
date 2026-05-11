import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_verticals.saas_erp.manifest import get_saas_erp_taxonomy_manifest
from picwise_verticals.saas_erp.validation import validate_saas_erp_taxonomy_manifest


class TestPickwiseSaaSErpTaxonomyContractStage28E(unittest.TestCase):
    def test_manifest_exists_with_exact_stage_title_and_vertical_id(self) -> None:
        manifest = get_saas_erp_taxonomy_manifest()
        self.assertEqual(manifest["stage_title"], "Stage 28E — SaaS / ERP Taxonomy Contract")
        self.assertEqual(manifest["vertical_id"], "software_saas_erp")
        self.assertIsInstance(json.dumps(manifest, sort_keys=True), str)

    def test_saas_erp_is_separate_from_retail_and_not_forced_into_retail_engine(self) -> None:
        manifest = get_saas_erp_taxonomy_manifest()
        self.assertEqual(manifest["separate_from_vertical_id"], "retail_physical_products")
        self.assertEqual(manifest["not_forced_into_retail_engine"], "tech_electronics_office")

    def test_google_product_taxonomy_is_not_the_saas_backbone(self) -> None:
        manifest = get_saas_erp_taxonomy_manifest()
        self.assertTrue(manifest["avoids_google_product_taxonomy_backbone"])

    def test_required_category_buckets_exist(self) -> None:
        bucket_ids = {bucket["bucket_id"] for bucket in get_saas_erp_taxonomy_manifest()["category_buckets"]}
        self.assertEqual(
            bucket_ids,
            {
                "erp_business_management",
                "crm_sales_marketing",
                "accounting_invoicing_payroll",
                "hr_workforce_scheduling",
                "project_management_collaboration",
                "ecommerce_booking_pos_software",
                "cybersecurity_cloud_hosting",
                "industry_specific_software",
            },
        )

    def test_core_saas_domains_are_represented(self) -> None:
        manifest = get_saas_erp_taxonomy_manifest()
        labels = {bucket["display_name"] for bucket in manifest["category_buckets"]}
        self.assertIn("ERP / Business Management", labels)
        self.assertIn("CRM / Sales / Marketing", labels)
        self.assertIn("Accounting / Invoicing / Payroll", labels)
        self.assertIn("HR / Workforce / Scheduling", labels)
        self.assertIn("Project Management / Collaboration", labels)
        self.assertIn("E-commerce / Booking / POS Software", labels)
        self.assertIn("Cybersecurity / Cloud / Hosting", labels)
        self.assertIn("Industry-specific Software", labels)

    def test_taxi_dispatch_and_fleet_management_exist_under_industry_bucket(self) -> None:
        buckets = get_saas_erp_taxonomy_manifest()["category_buckets"]
        industry = next(bucket for bucket in buckets if bucket["bucket_id"] == "industry_specific_software")
        family_ids = {family["family_id"] for family in industry["example_software_families"]}
        self.assertIn("taxi_dispatch", family_ids)
        self.assertIn("fleet_management", family_ids)

    def test_software_specific_fields_exist_for_each_bucket(self) -> None:
        required_fields = {
            "pricing_model",
            "monthly_cost_range",
            "users_or_seats",
            "deployment_type",
            "integrations",
            "support_level",
            "api_availability",
            "security_compliance",
            "trial_demo_availability",
            "business_size_fit",
            "industry_fit",
        }
        for bucket in get_saas_erp_taxonomy_manifest()["category_buckets"]:
            field_ids = {field["field_id"] for field in bucket["field_definitions"]}
            self.assertTrue(required_fields.issubset(field_ids))

    def test_ranking_dimensions_are_contract_only(self) -> None:
        manifest = get_saas_erp_taxonomy_manifest()
        for dimension in manifest["ranking_dimensions"]:
            self.assertTrue(dimension["contract_only"])
            self.assertFalse(dimension["scoring_implemented"])
        for bucket in manifest["category_buckets"]:
            for dimension in bucket["ranking_dimensions"]:
                self.assertTrue(dimension["contract_only"])
                self.assertFalse(dimension["scoring_implemented"])

    def test_no_stage_28f_or_stage_29a_implementation_flags(self) -> None:
        non_goals = get_saas_erp_taxonomy_manifest()["non_goals"]
        self.assertTrue(non_goals["stage_28f_work"])
        self.assertTrue(non_goals["stage_29a_work"])

    def test_no_runtime_or_local_nlu_or_network_dependency_required(self) -> None:
        boundaries = get_saas_erp_taxonomy_manifest()["dependency_boundaries"]
        self.assertFalse(boundaries["runtime_dependency_required"])
        self.assertFalse(boundaries["local_nlu_runtime_dependency_required"])
        self.assertFalse(boundaries["network_or_external_api_calls_required"])

    def test_no_checkout_or_owned_marketplace_inventory_logic(self) -> None:
        non_goals = get_saas_erp_taxonomy_manifest()["non_goals"]
        self.assertTrue(non_goals["checkout_cart_payment_subscription_billing"])
        self.assertTrue(non_goals["owned_marketplace_inventory_storage"])

    def test_validator_reports_all_required_boundaries(self) -> None:
        report = validate_saas_erp_taxonomy_manifest()
        self.assertTrue(report["valid"])
        self.assertTrue(report["passed"])
        self.assertTrue(report["stage_title_exact"])
        self.assertTrue(report["vertical_id_is_software_saas_erp"])
        self.assertTrue(report["separate_from_retail_physical_products"])
        self.assertTrue(report["not_forced_into_tech_electronics_office"])
        self.assertTrue(report["google_taxonomy_not_main_backbone"])
        self.assertTrue(report["all_required_buckets_exist"])
        self.assertTrue(report["ranking_is_contract_only_not_implemented"])


if __name__ == "__main__":
    unittest.main()

