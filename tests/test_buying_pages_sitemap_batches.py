from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages import (  # noqa: E402
    build_sitemap_batches,
    collect_indexable_entries,
    generate_second_scale_batch,
    render_sitemap_index_xml,
    split_sitemap_entries,
)


class BuyingPagesSitemapBatchesTests(unittest.TestCase):
    def test_batch_split_is_deterministic_and_scale_safe(self) -> None:
        batch = generate_second_scale_batch()
        combined = (*batch.published_pages, *batch.candidate_pages)
        entries = collect_indexable_entries(combined)
        batches = split_sitemap_entries(entries, batch_size=2500)
        self.assertEqual(len(batches), 4)
        self.assertEqual(sum(len(chunk) for chunk in batches), len(entries))
        self.assertEqual(entries, collect_indexable_entries(combined))

    def test_candidate_pages_are_excluded_from_batched_sitemaps(self) -> None:
        batch = generate_second_scale_batch()
        combined = (*batch.published_pages, *batch.candidate_pages)
        xml_batches = build_sitemap_batches(combined, batch_size=2000, base_url="https://localhost")
        candidate_slug = batch.candidate_pages[0].slug
        self.assertTrue(all(f"/best/{candidate_slug}" not in xml for xml in xml_batches))

    def test_sitemap_index_xml_points_to_batch_files(self) -> None:
        xml = render_sitemap_index_xml(
            ("sitemaps/buying-pages-1.xml", "sitemaps/buying-pages-2.xml"),
            base_url="https://localhost",
        )
        root = ET.fromstring(xml)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [node.text for node in root.findall("sm:sitemap/sm:loc", ns)]
        self.assertEqual(
            locs,
            [
                "https://localhost/sitemaps/buying-pages-1.xml",
                "https://localhost/sitemaps/buying-pages-2.xml",
            ],
        )


if __name__ == "__main__":
    unittest.main()
