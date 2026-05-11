import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import build_stage29_seeds
from picwise_learning.stage29_approval_gate import set_approval_status
from picwise_learning.stage29_config import Stage29GenerationConfig
from picwise_learning.stage29_evaluation import evaluate_generated_queries
from picwise_learning.stage29_failure_analysis import analyze_failures
from picwise_learning.stage29_query_generator import generate_queries_stream
from picwise_learning.stage29_regression_pack import build_regression_pack
from picwise_learning.stage29_suggestions import build_learning_suggestions


class TestPickwiseStage29RegressionPack(unittest.TestCase):
    def test_regression_pack_contains_generated_and_guardrail_cases(self) -> None:
        seeds = build_stage29_seeds()[:2]
        generated = list(
            generate_queries_stream(
                seeds,
                Stage29GenerationConfig(
                    variants_per_seed=1,
                    languages=("el",),
                    noise_types=("partial_query",),
                    intent_phrase_types=("compare",),
                ),
            )
        )
        evaluations = evaluate_generated_queries(generated)
        failures = analyze_failures(generated, evaluations)
        suggestions = build_learning_suggestions(failures)
        if suggestions:
            suggestions[0] = set_approval_status(suggestions[0], "approved")
            if len(suggestions) > 1:
                suggestions[1] = set_approval_status(suggestions[1], "manual_review")
        approved = [row for row in suggestions if row.approval_status == "approved"]
        pack = build_regression_pack(generated, evaluations, approved, suggestions)
        self.assertTrue(pack.cases)
        self.assertIn("generated_case", pack.source_counts)
        self.assertTrue(pack.offline_only)


if __name__ == "__main__":
    unittest.main()
