import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import build_stage29_seeds
from picwise_learning.stage29_config import Stage29GenerationConfig
from picwise_learning.stage29_evaluation import evaluate_generated_queries
from picwise_learning.stage29_query_generator import generate_queries_stream


class TestPickwiseStage29Evaluation(unittest.TestCase):
    def test_evaluation_outputs_required_fields(self) -> None:
        seeds = build_stage29_seeds()[:1]
        config = Stage29GenerationConfig(
            variants_per_seed=1,
            languages=("en",),
            noise_types=("partial_query",),
            intent_phrase_types=("compare",),
        )
        generated = list(generate_queries_stream(seeds, config))
        rows = evaluate_generated_queries(generated)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(bool(row.generated_query_record_id))
        self.assertTrue(bool(row.generated_query))
        self.assertIn(row.status, {"passed", "failed", "manual_review", "unknown", "unsafe_pass"})
        self.assertTrue(row.offline_only)

    def test_not_supported_fields_are_honest_for_non_retail(self) -> None:
        saas_seed = next(seed for seed in build_stage29_seeds() if seed.vertical == "software_saas_erp")
        generated = list(
            generate_queries_stream(
                [saas_seed],
                Stage29GenerationConfig(
                    variants_per_seed=1,
                    languages=("en",),
                    noise_types=("partial_query",),
                    intent_phrase_types=("compare",),
                ),
            )
        )
        row = evaluate_generated_queries(generated)[0]
        self.assertEqual(row.actual_vertical, "unavailable:not_supported")


if __name__ == "__main__":
    unittest.main()
