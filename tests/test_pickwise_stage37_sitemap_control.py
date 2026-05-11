from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.seo_contracts import PageQualityStatus, SEOIndexStatus  # noqa: E402
from picwise_buying_pages.seo_page_builder import SEOPageBuildRequest, build_seo_buying_page  # noqa: E402
from picwise_buying_pages.seo_sitemap_control import (  # noqa: E402
    render_stage37_sitemap_xml,
    select_stage37_sitemap_pages,
)
from picwise_mvp import run_pickwise_mvp_search_flow  # noqa: E402


def _page_for_query(query: str):
    flow = run_pickwise_mvp_search_flow(query)
    request = SEOPageBuildRequest(
        target_query=query,
        query_aliases=(query,),
        search_decision=flow.search_decision,
        intake_result=flow.intake_result,
        eligibility_result=flow.eligibility_result,
        recommendation_set=flow.recommendation_set,
    )
    return build_seo_buying_page(request)


class PickWiseStage37SitemapControlTests(unittest.TestCase):
    def test_sitemap_includes_only_quality_passed_indexable_pages(self) -> None:
        indexable = _page_for_query("power bank for iphone")
        noindex = replace(
            _page_for_query("power bank for iphone"),
            index_status=SEOIndexStatus.NOINDEX,
            page_quality_status=PageQualityStatus.NEEDS_DATA,
            sitemap_eligible=False,
            noindex_reason="needs_data",
        )
        selected = select_stage37_sitemap_pages((indexable, noindex))
        self.assertEqual([page.slug for page in selected], [indexable.slug])

    def test_sitemap_xml_renders_only_selected_pages(self) -> None:
        pages = (
            _page_for_query("power bank for iphone"),
            _page_for_query("loan insurance comparison"),
        )
        xml = render_stage37_sitemap_xml(pages, base_url="https://localhost", max_entries=10)
        root = ET.fromstring(xml)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = [node.text or "" for node in root.findall("sm:url/sm:loc", ns)]
        self.assertEqual(len(loc_values), 1)
        self.assertIn("/best/", loc_values[0])
        self.assertNotIn("loan-insurance-comparison", loc_values[0])

    def test_mass_generation_is_blocked(self) -> None:
        pages = tuple(_page_for_query("power bank for iphone") for _ in range(3))
        with self.assertRaises(ValueError):
            select_stage37_sitemap_pages(pages, max_entries=2)


if __name__ == "__main__":
    unittest.main()
