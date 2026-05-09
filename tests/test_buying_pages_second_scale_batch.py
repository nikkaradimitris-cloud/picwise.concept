from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages import (  # noqa: E402
    BuyingPagesRepository,
    build_sitemap_batches,
    evaluate_index_gate,
    generate_second_scale_batch,
)


class BuyingPagesSecondScaleBatchTests(unittest.TestCase):
    def test_second_scale_batch_supports_10000_pages_without_static_fixtures(self) -> None:
        started = time.perf_counter()
        batch = generate_second_scale_batch()
        elapsed = time.perf_counter() - started

        self.assertEqual(len(batch.published_pages), 10000)
        self.assertLess(elapsed, 20.0, "10,000-page generation should stay deterministic and bounded")

        repository = BuyingPagesRepository(batch.published_pages)
        self.assertEqual(len(repository.list_pages()), 10000)
        self.assertEqual(len({page.slug for page in batch.published_pages}), 10000)

    def test_lookup_and_index_gate_remain_deterministic(self) -> None:
        batch_a = generate_second_scale_batch()
        batch_b = generate_second_scale_batch()
        probe_indexes = (0, 1, 777, 2048, 8191, 9999)
        for idx in probe_indexes:
            page_a = batch_a.published_pages[idx]
            page_b = batch_b.published_pages[idx]
            self.assertEqual(page_a.slug, page_b.slug)
            self.assertEqual(page_a.main_keyword, page_b.main_keyword)
            self.assertTrue(evaluate_index_gate(page_a).indexable)

    def test_sitemap_batching_is_ready_for_scale(self) -> None:
        batch = generate_second_scale_batch()
        combined = (*batch.published_pages, *batch.candidate_pages)
        batched_xml = build_sitemap_batches(
            combined,
            batch_size=2000,
            base_url="https://localhost",
        )
        self.assertEqual(len(batched_xml), 5)
        self.assertTrue(all("<?xml" in xml for xml in batched_xml))
        self.assertTrue(all("/best/" in xml for xml in batched_xml))

        candidate_slug = batch.candidate_pages[0].slug
        self.assertTrue(all(f"/best/{candidate_slug}" not in xml for xml in batched_xml))


if __name__ == "__main__":
    unittest.main()
