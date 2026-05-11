import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning.stage30_shadow_records import build_shadow_record


class TestPickwiseStage30ShadowRecords(unittest.TestCase):
    def test_noise_and_language_detection(self) -> None:
        record = build_shadow_record(
            runtime_query="Καλη ??",
            normalized_query="καλη ??",
            source_surface="runtime_app",
            source_route="/demo",
            existing_runtime_decision="manual_review_required",
            existing_runtime_target="unknown",
            existing_runtime_vertical="retail_physical_products",
            shadow_nlu_target="unknown",
            shadow_vertical="retail_physical_products",
            shadow_confidence=0.12,
            comparison_status="both_unknown",
            failure_type=None,
            expected_learning_action="none",
            vertical="retail_physical_products",
        )
        self.assertEqual(record.language, "el")
        self.assertIn("punctuation_noise", record.noise_signals)
        self.assertFalse(record.did_affect_runtime)

    def test_shadow_record_id_is_stable_for_same_timestamp(self) -> None:
        common = {
            "runtime_query": "best erp software",
            "normalized_query": "best erp software",
            "source_surface": "runtime_app",
            "source_route": "/demo",
            "existing_runtime_decision": "general_product_discovery_allowed",
            "existing_runtime_target": "erp_core",
            "existing_runtime_vertical": "software_saas_erp",
            "shadow_nlu_target": "erp_core",
            "shadow_vertical": "software_saas_erp",
            "shadow_confidence": 0.8,
            "comparison_status": "aligned",
            "failure_type": None,
            "expected_learning_action": "none",
            "vertical": "software_saas_erp",
            "timestamp": "2026-05-11T17:05:00+00:00",
        }
        record_a = build_shadow_record(**common)
        record_b = build_shadow_record(**common)
        self.assertEqual(record_a.shadow_record_id, record_b.shadow_record_id)


if __name__ == "__main__":
    unittest.main()
