import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import build_stage29_seeds
from picwise_learning.stage29_config import Stage29GenerationConfig
from picwise_learning.stage29_query_generator import chunk_generated_queries, generate_queries_stream


class TestPickwiseStage29QueryGenerator(unittest.TestCase):
    def test_generator_is_deterministic_for_same_seed_and_config(self) -> None:
        seeds = build_stage29_seeds()[:2]
        config = Stage29GenerationConfig(variants_per_seed=1, chunk_size=3)
        first = [row.record_id for row in generate_queries_stream(seeds, config)]
        second = [row.record_id for row in generate_queries_stream(seeds, config)]
        self.assertEqual(first, second)

    def test_chunking_supports_streaming_without_full_materialization(self) -> None:
        seeds = build_stage29_seeds()[:1]
        config = Stage29GenerationConfig(variants_per_seed=1)
        chunks = list(chunk_generated_queries(generate_queries_stream(seeds, config), chunk_size=5))
        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 5 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
