import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import STAGE29_ID, build_stage29_seeds, validate_generated_query_record
from picwise_learning.stage29_config import build_default_stage29_config
from picwise_learning.stage29_query_generator import generate_queries_stream


class TestPickwiseStage29Contracts(unittest.TestCase):
    def test_generated_query_record_has_required_contract_fields(self) -> None:
        seed = build_stage29_seeds()[0]
        config = build_default_stage29_config()
        row = next(generate_queries_stream([seed], config))
        self.assertEqual(row.stage, STAGE29_ID)
        self.assertTrue(bool(row.record_id))
        self.assertTrue(bool(row.generated_query))
        self.assertTrue(bool(row.canonical_query))
        self.assertTrue(bool(row.source_seed_id))
        self.assertTrue(bool(row.expected_nlu_target))
        self.assertTrue(bool(row.expected_intent))
        self.assertTrue(bool(row.language))
        self.assertTrue(bool(row.vertical))
        self.assertTrue(bool(row.noise_profile))
        self.assertTrue(bool(row.applied_noise_types))
        self.assertTrue(bool(row.intent_phrase_type))
        self.assertTrue(row.offline_only)

    def test_validation_rejects_missing_expected_target(self) -> None:
        seed = build_stage29_seeds()[0]
        config = build_default_stage29_config()
        row = next(generate_queries_stream([seed], config))
        broken = row.__class__(**{**row.__dict__, "expected_nlu_target": ""})
        report = validate_generated_query_record(broken)
        self.assertFalse(report["valid"])
        self.assertIn("missing:expected_nlu_target", report["errors"])


if __name__ == "__main__":
    unittest.main()
