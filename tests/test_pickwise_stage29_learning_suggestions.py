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
from picwise_learning.stage29_failure_analysis import analyze_failures
from picwise_learning.stage29_query_generator import generate_queries_stream
from picwise_learning.stage29_suggestions import build_learning_suggestions
from picwise_learning.stage29_validation import validate_learning_suggestion


class TestPickwiseStage29LearningSuggestions(unittest.TestCase):
    def test_suggestions_are_structured_and_pending_by_default(self) -> None:
        seeds = build_stage29_seeds()[:2]
        generated = list(
            generate_queries_stream(
                seeds,
                Stage29GenerationConfig(
                    variants_per_seed=1,
                    languages=("de",),
                    noise_types=("brand_model_spec_typos",),
                    intent_phrase_types=("compare",),
                ),
            )
        )
        failures = analyze_failures(generated, evaluate_generated_queries(generated))
        suggestions = build_learning_suggestions(failures)
        self.assertTrue(suggestions)
        for suggestion in suggestions:
            self.assertEqual(suggestion.approval_status, "pending")
            self.assertTrue(validate_learning_suggestion(suggestion)["valid"])


if __name__ == "__main__":
    unittest.main()
