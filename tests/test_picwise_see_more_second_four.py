"""A second four, for the kinds of product where there is no best.

Owner instruction, 2026-10-12: where a kind of product does not support the notions of
comparison and best -- a dress, a bag, a tablecloth, a cable of a particular length --
the four are four different answers and the buyer gets a "see more" button, because
the engine cannot narrow a taste for them.

These tests pin the three things that make it honest: the button is offered only where
the kind carries no best, it is never offered with nothing behind it, and nothing in
the second four claims to be recommended -- there is still exactly one recommendation
on the page, as the mission requires.

All rows are local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_taxonomy.comparison_rules import comparison_rule  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "product_type",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "stock_status",
    "merchant_name", "condition", "description", "data_provenance",
)


def _row(pid: str, name: str, price: str, kind: str) -> dict[str, str]:
    return {
        "aw_product_id": pid,
        "product_name": name,
        "brand_name": name.split()[0],
        "merchant_category": kind,
        "product_type": kind,
        "aw_deep_link": f"https://fixture.example.invalid/out/{pid}",
        "aw_image_url": f"https://fixture.example.invalid/img/{pid}.jpg",
        "search_price": price,
        "currency": "GBP",
        "in_stock": "1",
        "stock_status": "in stock",
        "merchant_name": "Fixture Store One",
        "condition": "new",
        "description": fixture_description(),
        "data_provenance": "local_test_fixture",
    }


def _products(kind_label: str, word: str, count: int) -> list[dict[str, str]]:
    """`count` products of one kind, each at its own price so zones are available."""
    makers = ("Testline", "Fixturon", "Sampleworks")
    return [
        _row(
            f"p{index}",
            f"{makers[index % len(makers)]} {word} Model {index}",
            f"{10 + 7 * index}.00",
            kind_label,
        )
        for index in range(count)
    ]


class _FeedCase(unittest.TestCase):
    def _serve(self, rows: list[dict[str, str]]) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
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

    def _page(self, query: str) -> str:
        captured: dict[str, object] = {}
        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": urlencode({"q": query}),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                lambda status, headers: captured.setdefault("status", status),
            )
        ).decode("utf-8")
        self.assertEqual(captured["status"], "200 OK")
        return body

    def _cards(self, body: str) -> list[str]:
        return re.findall(r'<article class="pw-card[^"]*" data-choice-id="([^"]+)">', body)

    def _has_see_more(self, body: str) -> bool:
        # The class also appears in the stylesheet, so the element itself is matched.
        return '<summary class="pw-more-summary">' in body


class SeeMoreTests(_FeedCase):
    def test_a_kind_with_no_best_offers_a_second_four(self) -> None:
        self.assertEqual(comparison_rule("handbag").comparison_class, "fit")
        self._serve(_products("Handbags", "Handbag", 12))
        body = self._page("handbag")
        self.assertTrue(self._has_see_more(body))
        self.assertEqual(len(self._cards(body)), 8)

    def test_a_kind_that_carries_a_best_offers_none(self) -> None:
        # A drill is judged on quality, so PicWise owes a recommendation, not a longer
        # list. Offering "see more" there would say the engine could not decide.
        self.assertEqual(comparison_rule("drill").comparison_class, "rating")
        self._serve(_products("Drills", "Drill", 12))
        body = self._page("drill")
        self.assertFalse(self._has_see_more(body))
        self.assertEqual(len(self._cards(body)), 4)

    def test_the_button_is_never_offered_with_nothing_behind_it(self) -> None:
        # Exactly four handbags in the feed: there is no second four, so no button.
        self._serve(_products("Handbags", "Handbag", 4))
        body = self._page("handbag")
        self.assertFalse(self._has_see_more(body))
        self.assertEqual(len(self._cards(body)), 4)

    def test_a_partial_second_four_is_not_shown(self) -> None:
        # Six handbags: four shown, two left. Two is not a four, and the contract owes
        # four answers, so the control stays closed rather than showing a remainder.
        self._serve(_products("Handbags", "Handbag", 6))
        body = self._page("handbag")
        self.assertFalse(self._has_see_more(body))
        self.assertEqual(len(self._cards(body)), 4)

    def test_no_product_appears_in_both_fours(self) -> None:
        self._serve(_products("Handbags", "Handbag", 12))
        shown = self._cards(self._page("handbag"))
        self.assertEqual(len(shown), len(set(shown)))


class RecommendationStaysUniqueTests(_FeedCase):
    def test_the_page_still_has_exactly_one_recommendation(self) -> None:
        # The mission requires exactly one recommended choice per query. A second four
        # adds answers, never a second recommendation.
        self._serve(_products("Handbags", "Handbag", 12))
        body = self._page("handbag")
        self.assertEqual(len(self._cards(body)), 8)
        self.assertEqual(body.count("rec=1"), 1)
        # The class name also appears in the stylesheet, so count the card itself.
        self.assertEqual(body.count('<article class="pw-card pw-card-recommended"'), 1)

    def test_nothing_in_the_second_four_is_tracked_as_recommended(self) -> None:
        self._serve(_products("Handbags", "Handbag", 12))
        body = self._page("handbag")
        second_four = body.split('class="pw-grid pw-grid-more"', 1)[1]
        self.assertNotIn("rec=1", second_four)
        self.assertNotIn("pw-rec-badge", second_four)

    def test_the_second_four_says_why_there_is_no_best(self) -> None:
        self._serve(_products("Handbags", "Handbag", 12))
        body = self._page("handbag")
        self.assertIn("no single best choice in this kind of product", body)


if __name__ == "__main__":
    unittest.main()
