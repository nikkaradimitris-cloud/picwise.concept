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
from picwise_learning.stage29_suggestions import build_learning_suggestions
from picwise_learning.stage29_update_pack import build_update_pack


class TestPickwiseStage29UpdatePack(unittest.TestCase):
    def test_update_pack_uses_approved_suggestions_only(self) -> None:
        seeds = build_stage29_seeds()[:2]
        generated = list(
            generate_queries_stream(
                seeds,
                Stage29GenerationConfig(variants_per_seed=1, languages=("en",), noise_types=("bad_typing",)),
            )
        )
        failures = analyze_failures(generated, evaluate_generated_queries(generated))
        suggestions = build_learning_suggestions(failures)
        gated = [set_approval_status(row, "approved" if idx == 0 else "pending") for idx, row in enumerate(suggestions)]
        pack = build_update_pack(gated)
        self.assertEqual(len(pack.approved_suggestion_ids), 1)
        self.assertEqual(pack.validation_status, "valid")
        self.assertTrue(pack.offline_only)


if __name__ == "__main__":
    unittest.main()
