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
    evaluate_index_gate,
    generate_first_scale_batch,
    render_buying_pages_sitemap_xml,
)


class BuyingPagesFirstScaleBatchTests(unittest.TestCase):
    def test_first_scale_batch_generates_1000_published_pages_deterministically(self) -> None:
        start = time.perf_counter()
        batch_a = generate_first_scale_batch()
        elapsed = time.perf_counter() - start
        batch_b = generate_first_scale_batch()

        self.assertLess(elapsed, 3.0, "first 1,000-page generation should remain fast")
        self.assertEqual(len(batch_a.published_pages), 1000)
        self.assertEqual(
            [page.slug for page in batch_a.published_pages],
            [page.slug for page in batch_b.published_pages],
        )

    def test_first_batch_pages_meet_contract_requirements(self) -> None:
        batch = generate_first_scale_batch()
        repository = BuyingPagesRepository(batch.published_pages)
        self.assertEqual(len(repository.list_pages()), 1000)

        slugs = [page.slug for page in batch.published_pages]
        self.assertEqual(len(slugs), len(set(slugs)))

        for page in batch.published_pages:
            self.assertTrue(page.main_keyword.strip())
            self.assertGreaterEqual(len(page.keyword_aliases), 1)
            self.assertLessEqual(len(page.keyword_aliases), 10)
            self.assertEqual(len(page.keyword_aliases), len(set(page.keyword_aliases)))
            self.assertEqual(len(page.products), 4)
            self.assertIn(page.recommended_product_id, {product.product_id for product in page.products})
            self.assertGreaterEqual(len(page.faq_items), 1)
            self.assertGreaterEqual(len(page.related_searches), 1)
            self.assertTrue(all((product.affiliate_url or "").strip() for product in page.products))
            self.assertTrue(page.refresh_metadata.refresh_reason.strip())
            self.assertTrue(evaluate_index_gate(page).indexable)

    def test_candidate_only_pages_do_not_leak_into_public_sitemap(self) -> None:
        batch = generate_first_scale_batch()
        combined = (*batch.published_pages, *batch.candidate_pages)
        xml = render_buying_pages_sitemap_xml(combined, base_url="https://localhost")

        for candidate in batch.candidate_pages[:20]:
            self.assertNotIn(f"/best/{candidate.slug}", xml)
        for published in batch.published_pages[:20]:
            self.assertIn(f"/best/{published.slug}", xml)


if __name__ == "__main__":
    unittest.main()
