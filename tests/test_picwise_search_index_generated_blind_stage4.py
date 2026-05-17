from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.query_variant_generator import generate_noisy_variants_for_term  # noqa: E402
from picwise_search_memory import build_canonical_vocabulary_registry, build_offline_search_index, lookup_offline_search_index  # noqa: E402


class PicWiseSearchIndexGeneratedBlindStage4Tests(unittest.TestCase):
    def test_generated_blind_evaluation_resolves_to_same_canonical_or_category(self) -> None:
        registry = build_canonical_vocabulary_registry()
        by_category: dict[str, list] = {}
        for record in registry.records:
            by_category.setdefault(record.mega_category_id, []).append(record)

        sampled: list = []
        for category in sorted(by_category.keys()):
            category_records = sorted(by_category[category], key=lambda row: row.normalized_term)
            sampled.extend(category_records[:2])

        generated: list[dict[str, str]] = []
        for record in sampled:
            generated.extend(generate_noisy_variants_for_term(record.canonical_term, record.mega_category_id))

        index = build_offline_search_index(registry, generated)
        self.assertGreater(len(generated), 0)

        total = 0
        canonical_matches = 0
        category_matches = 0
        for row in generated:
            result = lookup_offline_search_index(row["variant"], index)
            total += 1
            self.assertEqual(result.status, "match")
            self.assertIsNotNone(result.matched_entry)
            if result.matched_entry.canonical_term == row["canonical_term"]:
                canonical_matches += 1
            if result.matched_entry.mega_category_id == row["mega_category_id"]:
                category_matches += 1

        self.assertGreater(total, 0)
        self.assertEqual(category_matches, total)
        self.assertGreaterEqual(canonical_matches, int(total * 0.80))


if __name__ == "__main__":
    unittest.main()
