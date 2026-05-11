from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_buying_pages.seo_contracts import PageQualityStatus, SEOIndexStatus  # noqa: E402
from picwise_buying_pages.seo_page_builder import SEOPageBuildRequest, build_seo_buying_page  # noqa: E402
from picwise_buying_pages.seo_sitemap_control import select_stage37_sitemap_pages  # noqa: E402
from picwise_mvp import run_pickwise_mvp_search_flow  # noqa: E402
from picwise_offers import ProductSourceStatus  # noqa: E402


def _call_wsgi(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    status_holder: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = {key: value for key, value in headers}

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "443",
        "HTTP_HOST": "localhost",
        "wsgi.url_scheme": "https",
    }
    body_chunks = deployment_app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    return status_holder["status"], status_holder["headers"], body


def _build_stage37_page(query: str):
    flow = run_pickwise_mvp_search_flow(query)
    return build_seo_buying_page(
        SEOPageBuildRequest(
            target_query=query,
            query_aliases=(query,),
            search_decision=flow.search_decision,
            intake_result=flow.intake_result,
            eligibility_result=flow.eligibility_result,
            recommendation_set=flow.recommendation_set,
        )
    )


class PickWiseStage37RuntimeGuardrailsTests(unittest.TestCase):
    def test_no_fake_product_or_commercial_data_in_stage37_page(self) -> None:
        page = _build_stage37_page("power bank for iphone")
        text = " ".join(slot.title for slot in page.display_slots).lower()
        self.assertNotIn("fake", text)
        self.assertNotIn("placeholder", text)

    def test_no_mass_page_generation_in_stage37_builder(self) -> None:
        pages = tuple(_build_stage37_page("power bank for iphone") for _ in range(5))
        self.assertEqual(len(pages), 5)
        unique_page_ids = {page.page_id for page in pages}
        self.assertEqual(len(unique_page_ids), 1)

    def test_noindex_when_source_is_not_connected(self) -> None:
        flow = run_pickwise_mvp_search_flow("power bank for iphone")
        page = build_seo_buying_page(
            SEOPageBuildRequest(
                target_query="power bank for iphone",
                query_aliases=("power bank for iphone",),
                search_decision=flow.search_decision,
                intake_result=flow.intake_result.__class__(
                    source=flow.intake_result.source,
                    status=ProductSourceStatus.NOT_CONNECTED,
                    candidates=flow.intake_result.candidates,
                    reason_codes=flow.intake_result.reason_codes,
                    metadata=flow.intake_result.metadata,
                ),
                eligibility_result=flow.eligibility_result,
                recommendation_set=flow.recommendation_set,
            )
        )
        self.assertEqual(page.index_status, SEOIndexStatus.NOINDEX)
        self.assertEqual(page.page_quality_status, PageQualityStatus.NEEDS_DATA)
        self.assertFalse(page.sitemap_eligible)

    def test_sitemap_excludes_noindex_or_non_quality_pages(self) -> None:
        ready = _build_stage37_page("power bank for iphone")
        blocked = _build_stage37_page("!!")
        selected = select_stage37_sitemap_pages((ready, blocked))
        self.assertEqual([page.slug for page in selected], [ready.slug])

    def test_existing_routes_remain_working(self) -> None:
        for path in ("/search", "/results", "/private-beta-readiness", "/sitemap-buying-pages.xml", "/best/power-bank-20000mah-for-iphone"):
            status, _headers, _body = _call_wsgi(path, "q=power+bank")
            self.assertEqual(status, "200 OK")

    def test_stage37_does_not_implement_cart_checkout_or_inventory(self) -> None:
        source = "\n".join(
            [
                (SRC / "picwise_buying_pages" / "seo_page_builder.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_surface" / "buying_page_seo_surface.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_buying_pages" / "seo_sitemap_control.py").read_text(encoding="utf-8").lower(),
            ]
        )
        forbidden = ("checkout", "cart", "payment", "owned_inventory", "warehouse")
        self.assertTrue(all(token not in source for token in forbidden))

    def test_stage37_module_no_network_scrape_calls(self) -> None:
        source = "\n".join(
            [
                (SRC / "picwise_buying_pages" / "seo_page_builder.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_buying_pages" / "seo_quality_gate.py").read_text(encoding="utf-8").lower(),
                (SRC / "picwise_buying_pages" / "seo_sitemap_control.py").read_text(encoding="utf-8").lower(),
            ]
        )
        forbidden = ("requests", "httpx", "urllib.request", "scrape", "crawler", "selenium", "playwright")
        self.assertTrue(all(token not in source for token in forbidden))


if __name__ == "__main__":
    unittest.main()
