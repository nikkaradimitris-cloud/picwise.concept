import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import build_stage29_seeds
from picwise_learning.stage29_validation import validate_seed_record


class TestPickwiseStage29SeedLinkage(unittest.TestCase):
    def test_retail_saas_finance_have_separate_linkage_rules(self) -> None:
        seeds = build_stage29_seeds()
        retail = [row for row in seeds if row.vertical == "retail_physical_products"]
        saas = [row for row in seeds if row.vertical == "software_saas_erp"]
        finance = [row for row in seeds if row.vertical == "finance_insurance_business_finance"]

        self.assertTrue(retail and saas and finance)
        self.assertTrue(all(bool(row.retail_engine) for row in retail))
        self.assertTrue(all(row.retail_engine is None for row in saas))
        self.assertTrue(all(row.retail_engine is None for row in finance))
        self.assertTrue(all(row.saas_erp_contract_ref == "Stage 28E" for row in saas))
        self.assertTrue(all(row.finance_insurance_contract_ref == "Stage 28F" for row in finance))

    def test_all_seed_records_validate(self) -> None:
        seeds = build_stage29_seeds()
        reports = [validate_seed_record(seed) for seed in seeds]
        self.assertTrue(all(report["valid"] for report in reports))


if __name__ == "__main__":
    unittest.main()
