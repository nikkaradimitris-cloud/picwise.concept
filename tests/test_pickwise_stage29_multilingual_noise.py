import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import build_stage29_seeds
from picwise_learning.stage29_config import Stage29GenerationConfig
from picwise_learning.stage29_query_generator import generate_queries_stream


class TestPickwiseStage29MultilingualNoise(unittest.TestCase):
    def test_languages_and_noise_types_are_present(self) -> None:
        seeds = build_stage29_seeds()[:1]
        config = Stage29GenerationConfig(variants_per_seed=1)
        rows = list(generate_queries_stream(seeds, config))
        languages = {row.language for row in rows}
        noises = {row.noise_profile for row in rows}
        self.assertEqual(languages, {"el", "el_gr", "en", "de"})
        self.assertIn("missing_letters", noises)
        self.assertIn("swapped_letters", noises)
        self.assertIn("bad_typing", noises)
        self.assertIn("wrong_spaces", noises)

    def test_mixed_case_noise_changes_surface_form(self) -> None:
        seeds = build_stage29_seeds()[:1]
        config = Stage29GenerationConfig(
            variants_per_seed=1,
            languages=("en",),
            intent_phrase_types=("compare",),
            noise_types=("case_mix",),
        )
        row = next(generate_queries_stream(seeds, config))
        self.assertNotEqual(row.generated_query, row.generated_query.lower())
        self.assertNotEqual(row.generated_query, row.generated_query.upper())


if __name__ == "__main__":
    unittest.main()
