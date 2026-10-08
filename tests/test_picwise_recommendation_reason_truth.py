"""The recommended card must say what actually decided it.

Pins audit findings G1-G3 in docs/picwise_mission_truth_audit_2026-10-08.md. Every
canary query had four choices tied on search match, so the cheapest won; the code meant
to say so never did (a sign error made `price_tie_breaker` unreachable), and the card
listed reasons equally true of all four. The tie-break also parsed "1.099,00" as 1.099
and compared prices across currencies.

All rows are local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import html
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.search_selection import decide_recommended_provider_product  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_PRICE_DECIDED = "Lowest price among the choices that match your search equally"


def _product(pid: str, title: str, price: str, currency: str = "GBP") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand=title.split()[0],
        category_text="Refrigerators",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in stock",
        currency=currency,
        raw={"product_type": "Refrigerators", "in_stock": "in stock"},
    )


def _decide(*products: ProviderProduct, query: str = "refrigerator"):
    return decide_recommended_provider_product(query, tuple(products))


class DecidingReasonTests(unittest.TestCase):
    def test_equal_match_is_decided_by_price_and_says_so_first(self) -> None:
        decision = _decide(
            _product("a", "Fixturon Frost Refrigerator 300L", "749.00"),
            _product("b", "Testline Frost Refrigerator 250L", "399.00"),
            _product("c", "Sampleworks Frost Refrigerator 350L", "1249.00"),
            _product("d", "Fixturon Cool Refrigerator 200L", "1099.00"),
        )
        self.assertEqual(decision.recommended_product_id, "b")
        self.assertEqual(decision.recommendation_reason_codes[0], "price_tie_breaker")

    def test_comma_decimal_prices_are_compared_as_the_labels_read_them(self) -> None:
        decision = _decide(
            _product("eu1", "Fixturon Frost Refrigerator 300L", "1.299,00", "EUR"),
            _product("eu2", "Testline Frost Refrigerator 250L", "899,00", "EUR"),
            _product("eu3", "Sampleworks Frost Refrigerator 350L", "1.099,00", "EUR"),
            _product("eu4", "Fixturon Cool Refrigerator 200L", "649,00", "EUR"),
        )
        # 649,00 is the lowest. The old parser read 1.099,00 as 1.099 and picked eu3.
        self.assertEqual(decision.recommended_product_id, "eu4")
        self.assertEqual(decision.recommendation_reason_codes[0], "price_tie_breaker")

    def test_prices_in_different_currencies_are_never_compared(self) -> None:
        decision = _decide(
            _product("x1", "Fixturon Frost Refrigerator 300L", "100.00", "EUR"),
            _product("x2", "Testline Frost Refrigerator 250L", "95.00", "GBP"),
            _product("x3", "Sampleworks Frost Refrigerator 350L", "120.00", "USD"),
            _product("x4", "Fixturon Cool Refrigerator 200L", "150.00", "EUR"),
        )
        self.assertEqual(decision.recommendation_reason_codes[0], "tie_on_search_match_and_price")
        self.assertNotIn("price_tie_breaker", decision.recommendation_reason_codes)

    def test_a_full_tie_is_reported_as_a_tie(self) -> None:
        decision = _decide(
            _product("t1", "Fixturon Frost Refrigerator 300L", "500.00"),
            _product("t2", "Testline Frost Refrigerator 250L", "500.00"),
            _product("t3", "Sampleworks Frost Refrigerator 350L", "500.00"),
            _product("t4", "Fixturon Cool Refrigerator 200L", "500.00"),
        )
        self.assertEqual(decision.recommendation_reason_codes[0], "tie_on_search_match_and_price")

    def test_a_closer_match_is_decided_by_the_match(self) -> None:
        decision = _decide(
            _product("m1", "Fixturon Frost Refrigerator 300L", "900.00"),
            _product("m2", "Testline Frost Fridge Freezer Refrigerator 250L", "999.00"),
            _product("m3", "Sampleworks Frost Refrigerator 350L", "400.00"),
            _product("m4", "Fixturon Cool Refrigerator 200L", "500.00"),
            query="fridge freezer refrigerator",
        )
        self.assertEqual(decision.recommended_product_id, "m2")
        self.assertEqual(decision.recommendation_reason_codes[0], "closer_search_match")


class RenderedRecommendationReasonTests(unittest.TestCase):
    """Through api/index.py: the deciding reason is the first line on the card."""

    def setUp(self) -> None:
        directory = tempfile.mkdtemp()
        path = Path(directory) / "feed.csv"
        rows = [
            ("eu1", "Fixturon Frost Refrigerator 300L", "1.299,00"),
            ("eu2", "Testline Frost Refrigerator 250L", "899,00"),
            ("eu3", "Sampleworks Frost Refrigerator 350L", "1.099,00"),
            ("eu4", "Fixturon Cool Refrigerator 200L", "649,00"),
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
                 "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock",
                 "merchant_name", "data_provenance"]
            )
            for pid, title, price in rows:
                writer.writerow(
                    [pid, title, title.split()[0], "Refrigerators", "Refrigerators",
                     f"https://fixture.example.invalid/out/{pid}",
                     f"https://fixture.example.invalid/img/{pid}.jpg", price, "EUR", "1",
                     "Fixture Store One", "local_test_fixture"]
                )
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if previous is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = previous
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def test_recommended_card_leads_with_the_price_decision_and_its_rank_agrees(self) -> None:
        def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
            return None

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": urlencode({"q": "refrigerator"}),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        ).decode("utf-8")
        recommended = re.search(
            r'<article class="pw-card pw-card-recommended" data-choice-id="([^"]+)">(.*?)</article>',
            body,
            re.S,
        )
        self.assertIsNotNone(recommended)
        choice_id, inner = recommended.groups()
        self.assertEqual(choice_id, "eu4")
        role = html.unescape(re.search(r'<p class="pw-role-label">(.*?)</p>', inner, re.S).group(1))
        self.assertEqual(role, "Lowest price of these four")
        bullets = [
            html.unescape(re.sub(r"<[^>]+>", "", item)).strip()
            for item in re.findall(r'<li class="pw-feature-item">(.*?)</li>', inner, re.S)
        ]
        # The fact-derived key reasons come first, then the recommendation's own reasons.
        recommendation_reasons = bullets[3:]
        self.assertEqual(recommendation_reasons[0], _PRICE_DECIDED)
        self.assertIn("then by price when they match equally", html.unescape(body))


if __name__ == "__main__":
    unittest.main()
