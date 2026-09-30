"""A buyer who misspells a product still gets four suitable products and a recommendation.

End to end through the deployed WSGI entrypoint, against two local fixture feeds: the
English coverage fixture, and a fixture whose products are titled and typed in Greek,
because Greek merchants' feeds name their products in Greek. Both are local test data
(`.invalid` URLs, fictional brands) and prove nothing about any real provider feed.
"""
from __future__ import annotations

import html
import io
import os
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.index import app as wsgi_app  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402
from picwise_surface import provider_feed_cards_will_render  # noqa: E402

COVERAGE_FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"
GREEK_FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_greek_titles_fixture.csv"
_FEED_ENV = "AWIN_FEED_FILE"


class _FeedCase(unittest.TestCase):
    feed = COVERAGE_FIXTURE

    def setUp(self) -> None:
        self._previous = os.environ.get(_FEED_ENV)
        os.environ[_FEED_ENV] = str(self.feed)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._previous is None:
            os.environ.pop(_FEED_ENV, None)
        else:
            os.environ[_FEED_ENV] = self._previous
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def assertDelivers(self, query: str, product_type: str) -> None:
        resolution = resolve_live_search(query)
        self.assertTrue(provider_feed_cards_will_render(resolution), query)
        types = {p.get("product_type") for p in resolution.provider_feed_selected_products}
        self.assertEqual(types, {product_type}, query)
        self.assertEqual(len(resolution.provider_feed_selected_products), 4, query)
        self.assertTrue(resolution.provider_feed_recommended_product_id, query)

    def page(self, query: str) -> tuple[int, str]:
        environ: dict[str, object] = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/search",
            "QUERY_STRING": f"q={quote(query)}",
            "wsgi.input": io.BytesIO(b""),
            "CONTENT_LENGTH": "0",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "wsgi.url_scheme": "https",
        }
        body = b"".join(wsgi_app(environ, lambda status, headers: None)).decode("utf-8")
        found = re.search(r'<p class="pw-query-line">(.*?)</p>', body, re.S)
        line = html.unescape(re.sub(r"<[^>]+>", "", found.group(1))).strip() if found else ""
        return len(re.findall(r'<article class="pw-card', body)), line


class GreekAndGreeklishQueriesOnAnEnglishFeedTests(_FeedCase):
    CASES = (
        ("πλυντηριο ρουχων", "Washing Machines"),
        ("plintirio rouxon", "Washing Machines"),
        ("ψιγειο", "Refrigerators"),
        ("cygeio", "Refrigerators"),
        ("τηλαιοραση", "Televisions"),
        ("εξωτερικη μπαταρια", "Power Banks"),
        ("pawer bank 20000 gia iphone", "Power Banks"),
        ("κλιματηστικο 12000 btu", "Air Conditioners"),
        ("καρεκλα γραφειου εργονομικη", "Office & Computer Chairs"),
        ("ksiristiki mixani", "Electric Shavers"),
        ("xlookoptiko", "Lawn Mowers"),
        ("μπαταρια αυτοκινητου 70ah", "Car Batteries"),
        ("τόνερ για εκτυπωτή laser", "Toner Cartridges"),
    )

    def test_each_delivers_four_of_the_right_kind(self) -> None:
        for query, product_type in self.CASES:
            with self.subTest(query=query):
                self.assertDelivers(query, product_type)

    def test_a_spec_filters_the_four(self) -> None:
        # "70ah" matches one battery: it is reported, and all four are still batteries.
        resolution = resolve_live_search("μπαταρια αυτοκινητου 70ah")
        self.assertIn("70ah", resolution.provider_feed_unmatched_query_terms)
        resolution = resolve_live_search("πλυντηριο 8 κιλα")
        titles = [p.get("title", "") for p in resolution.provider_feed_selected_products]
        self.assertTrue(titles and all("Washing Machine" in t for t in titles), titles)

    def test_the_page_quotes_what_it_could_not_match_in_the_buyers_words(self) -> None:
        # Two of the four fixture mice are wireless, so "ασυρματο" cannot hold for all
        # four; "φθηνο" is a judgement no feed field confirms. Both are quoted as
        # typed, not as the feed-language filter "wireless" they were read as.
        cards, line = self.page("ποντικι ασυρματο φθηνο")
        self.assertEqual(cards, 4)
        self.assertIn("could not match: ασυρματο, φθηνο", line)
        self.assertNotIn("wireless", line)
        resolution = resolve_live_search("ποντικι ασυρματο")
        top_two = [p.get("title", "") for p in resolution.provider_feed_selected_products[:2]]
        self.assertTrue(all("Wireless" in title for title in top_two), top_two)

    def test_a_corrected_reading_is_stated_on_the_page(self) -> None:
        cards, line = self.page("lapotp")
        self.assertEqual(cards, 4)
        self.assertIn("Understood as: laptop", line)

    def test_an_exact_reading_is_not_announced_as_a_correction(self) -> None:
        _cards, line = self.page("ψυγειο")
        self.assertNotIn("Understood as", line)

    def test_non_product_searches_render_nothing(self) -> None:
        for query in ("δανειο", "τραπεζα", "κρασι", "καιρος αυριο"):
            with self.subTest(query=query):
                self.assertFalse(provider_feed_cards_will_render(resolve_live_search(query)))


class GreekTitledFeedTests(_FeedCase):
    feed = GREEK_FIXTURE

    def test_greek_products_answer_every_spelling(self) -> None:
        for query, product_type in (
            ("πλυντήριο ρούχων", "Πλυντήρια Ρούχων"),
            ("plintirio", "Πλυντήρια Ρούχων"),
            ("washing machine", "Πλυντήρια Ρούχων"),
            ("ψιγειο", "Ψυγεία"),
            ("fridge", "Ψυγεία"),
            ("power bank", "Εξωτερικές Μπαταρίες"),
            ("exoteriki bataria", "Εξωτερικές Μπαταρίες"),
            ("car battery", "Μπαταρίες Αυτοκινήτου"),
        ):
            with self.subTest(query=query):
                self.assertDelivers(query, product_type)

    def test_power_bank_and_car_battery_never_mix(self) -> None:
        # Both are "μπαταρία" in Greek. The concept, not the shared word, decides.
        for query, product_type in (
            ("εξωτερικη μπαταρια", "Εξωτερικές Μπαταρίες"),
            ("μπαταρια αυτοκινητου", "Μπαταρίες Αυτοκινήτου"),
        ):
            with self.subTest(query=query):
                self.assertDelivers(query, product_type)

    def test_a_spec_written_differently_in_feed_and_query_still_matches(self) -> None:
        # The feed writes "8kg" and "8 kg"; the buyer writes "8 κιλα".
        resolution = resolve_live_search("πλυντηριο ρουχων 8 κιλα")
        self.assertTrue(provider_feed_cards_will_render(resolution))
        # Only two of four are 8kg, so the four cannot all carry it; the two that do
        # rank first, and the page says the spec could not be met by all four.
        ranked = [p.get("provider_product_id") for p in resolution.provider_feed_selected_products]
        self.assertEqual(set(ranked[:2]), {"gr-wm-1", "gr-wm-4"}, ranked)
        self.assertIn("8 κιλα", resolution.provider_feed_unmatched_query_terms)


if __name__ == "__main__":
    unittest.main()
