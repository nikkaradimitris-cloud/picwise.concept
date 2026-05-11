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


class TestPickwiseStage29FailureAnalysis(unittest.TestCase):
    def test_failure_classifier_labels_non_pass_results(self) -> None:
        seeds = build_stage29_seeds()[:2]
        config = Stage29GenerationConfig(
            variants_per_seed=1,
            languages=("el", "el_gr"),
            noise_types=("missing_letters",),
            intent_phrase_types=("compare",),
        )
        generated = list(generate_queries_stream(seeds, config))
        evaluations = evaluate_generated_queries(generated)
        failures = analyze_failures(generated, evaluations)
        self.assertTrue(failures)
        known = {
            "wrong_vertical",
            "wrong_category",
            "unknown_intent",
            "general_intent_when_specific_expected",
            "greek_failure",
            "greeklish_failure",
            "english_failure",
            "german_failure",
            "typo_normalization_failure",
            "brand_model_spec_failure",
            "partial_query_failure",
            "intent_phrase_failure",
            "unsafe_pass",
            "missing_contract_linkage",
            "unsupported_interface",
        }
        self.assertTrue(all(row.failure_type in known for row in failures))


if __name__ == "__main__":
    unittest.main()
