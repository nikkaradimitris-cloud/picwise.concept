import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import build_stage29_seeds
from picwise_learning.stage29_approval_gate import filter_approved_suggestions, set_approval_status
from picwise_learning.stage29_config import Stage29GenerationConfig
from picwise_learning.stage29_evaluation import evaluate_generated_queries
from picwise_learning.stage29_failure_analysis import analyze_failures
from picwise_learning.stage29_query_generator import generate_queries_stream
from picwise_learning.stage29_suggestions import build_learning_suggestions


class TestPickwiseStage29ApprovalGate(unittest.TestCase):
    def test_only_approved_suggestions_pass_gate(self) -> None:
        seeds = build_stage29_seeds()[:2]
        generated = list(
            generate_queries_stream(
                seeds,
                Stage29GenerationConfig(variants_per_seed=1, languages=("en",), noise_types=("partial_query",)),
            )
        )
        failures = analyze_failures(generated, evaluate_generated_queries(generated))
        suggestions = build_learning_suggestions(failures)
        updated = [
            set_approval_status(suggestions[0], "approved"),
            set_approval_status(suggestions[-1], "rejected"),
        ] if len(suggestions) > 1 else [set_approval_status(suggestions[0], "approved")]
        approved = filter_approved_suggestions(updated)
        self.assertTrue(all(row.approval_status == "approved" for row in approved))
        self.assertEqual(len(approved), 1)


if __name__ == "__main__":
    unittest.main()
