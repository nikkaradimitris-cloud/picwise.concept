"""Understanding a buyer's request however it is phrased.

Real buyers add words: "power bank for iphone", "comfortable office chair", "cheap
washing machine". Every word used to be a hard filter, so one word that did not appear
in the feed text emptied the result set. The buyer who described their need got less
than the one who typed a bare noun, which inverts the promise the concept makes.

Selection now looks for the largest set of the buyer's words that four products all
satisfy, and states the rest. These tests pin the three properties that make that safe:

1. a word the inventory can be filtered by is never silently dropped
2. relaxing never changes which product family answers the query
3. whatever could not be matched is reported, never quietly ignored
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
from picwise_providers.search_selection import (  # noqa: E402
    resolve_query_token_plan,
    select_provider_products_for_query,
)
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    load_eligible_provider_feed_products,
    resolve_search_provider_feed_product_selection,
    resolve_search_provider_feed_selection_with_recommendation,
)
from picwise_search_memory.broad_query_suggestions import (  # noqa: E402
    is_unsafe_broad_query,
)

COVERAGE_FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"
LOCAL_FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"
_FEED_ENV = "AWIN_FEED_FILE"


class _FeedTestCase(unittest.TestCase):
    feed = COVERAGE_FIXTURE

    def setUp(self) -> None:
        self._previous_feed = os.environ.get(_FEED_ENV)
        os.environ[_FEED_ENV] = str(self.feed)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._previous_feed is None:
            os.environ.pop(_FEED_ENV, None)
        else:
            os.environ[_FEED_ENV] = self._previous_feed
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def _select(self, query: str):
        return resolve_search_provider_feed_product_selection(query=query)

    def _families(self, selection) -> set[str]:
        return {
            str(
                (product.raw or {}).get("product_type")
                or product.category_text
                or ""
            ).strip()
            for product in selection.selected_products
        }


class QualifiedQueriesStillDeliverTests(_FeedTestCase):
    QUALIFIED = (
        ("power bank for iphone", "Power Banks", ("iphone",)),
        ("power bank 20000mah for iphone", "Power Banks", ("20000mah", "iphone")),
        ("comfortable office chair", "Office & Computer Chairs", ("comfortable",)),
        ("running shoes for men", "Athletic Shoes", ("men",)),
        ("quiet lawn mower", "Lawn Mowers", ("quiet",)),
        ("cheap washing machine", "Washing Machines", ("cheap",)),
        ("bicycle helmet for kids", "Bicycle Helmets", ("kids",)),
        ("coffee machine for office", "Coffee Machines", ("office",)),
    )

    def test_a_qualifier_no_longer_empties_the_result_set(self) -> None:
        for query, _family, _unmatched in self.QUALIFIED:
            with self.subTest(query=query):
                selection = self._select(query)
                self.assertEqual(selection.status, "selected", query)
                self.assertEqual(len(selection.selected_products), 4, query)

    def test_relaxing_never_changes_the_product_family(self) -> None:
        for query, family, _unmatched in self.QUALIFIED:
            with self.subTest(query=query):
                self.assertEqual(self._families(self._select(query)), {family})

    def test_the_unmatched_words_are_reported(self) -> None:
        for query, _family, unmatched in self.QUALIFIED:
            with self.subTest(query=query):
                selection = self._select(query)
                self.assertEqual(
                    set(selection.unmatched_query_terms), set(unmatched), query
                )

    def test_a_qualified_query_still_gets_a_recommendation(self) -> None:
        for query, _family, _unmatched in self.QUALIFIED:
            with self.subTest(query=query):
                selection, decision = (
                    resolve_search_provider_feed_selection_with_recommendation(
                        query=query
                    )
                )
                self.assertEqual(decision.decision_status, "recommended", query)
                selected_ids = {
                    product.provider_product_id
                    for product in selection.selected_products
                }
                self.assertIn(decision.recommended_product_id, selected_ids)


class PrecisionIsPreservedTests(_FeedTestCase):
    def test_a_bare_product_query_drops_nothing(self) -> None:
        for query in ("power bank", "coffee machine", "office chair", "running shoes"):
            with self.subTest(query=query):
                selection = self._select(query)
                self.assertEqual(selection.status, "selected")
                self.assertEqual(selection.unmatched_query_terms, tuple())

    def test_a_word_the_inventory_can_filter_by_is_kept(self) -> None:
        # Four products carry "bicycle helmet", so neither word is droppable.
        selection = self._select("bicycle helmet")
        self.assertEqual(selection.unmatched_query_terms, tuple())
        self.assertEqual(self._families(selection), {"Bicycle Helmets"})

    def test_an_unrelated_query_is_not_answered_by_relaxation(self) -> None:
        for query in ("submarine periscope", "wedding cake topper"):
            with self.subTest(query=query):
                self.assertNotEqual(self._select(query).status, "selected")

    def test_a_query_whose_words_point_at_two_families_is_refused(self) -> None:
        # "battery" matches car batteries and "smartphone" matches mobile phones.
        # Answering either would mean guessing which product was meant.
        selection = self._select("smartphone with good battery")
        self.assertEqual(selection.status, "ambiguous_product_family")
        self.assertEqual(selection.selected_products, tuple())
        self.assertTrue(selection.ambiguous_product_families)


class AccessoryProtectionTests(_FeedTestCase):
    feed = LOCAL_FIXTURE

    def test_an_accessory_query_is_never_answered_with_the_main_product(self) -> None:
        # The fixture holds one laptop bag and six laptops. Relaxing "laptop bag" to
        # "laptop" would answer with laptops, which is not what was asked.
        for query in ("laptop bag", "laptop case"):
            with self.subTest(query=query):
                selection = self._select(query)
                self.assertNotEqual(selection.status, "selected")
                self.assertEqual(selection.selected_products, tuple())

    def test_the_main_product_query_still_excludes_the_accessory(self) -> None:
        selection = self._select("laptop")
        self.assertEqual(selection.status, "selected")
        ids = {product.provider_product_id for product in selection.selected_products}
        self.assertNotIn("fx-laptop-bag", ids)


class TokenPlanTests(_FeedTestCase):
    def test_connectives_are_never_treated_as_filters(self) -> None:
        products = load_eligible_provider_feed_products()
        plan = resolve_query_token_plan(("power", "bank", "for", "iphone"), products)
        self.assertIn("for", plan.connectives)
        self.assertNotIn("for", plan.required)
        self.assertNotIn("for", plan.unmatchable)

    def test_an_empty_query_plan_requires_nothing(self) -> None:
        plan = resolve_query_token_plan(tuple(), tuple())
        self.assertEqual(plan.required, tuple())
        self.assertEqual(plan.unmatchable, tuple())

    def test_a_query_of_only_connectives_requires_nothing(self) -> None:
        plan = resolve_query_token_plan(("for", "the", "with"), tuple())
        self.assertEqual(plan.required, tuple())

    def test_selection_reports_the_reading_it_committed_to(self) -> None:
        selection = self._select("comfortable office chair")
        self.assertEqual(set(selection.required_query_terms), {"office", "chair"})
        self.assertEqual(selection.unmatched_query_terms, ("comfortable",))

    def test_selection_survives_an_empty_inventory(self) -> None:
        result = select_provider_products_for_query("power bank", tuple())
        self.assertNotEqual(result.status, "selected")


class AmbiguousTermsNarrowedByProductWordsTests(unittest.TestCase):
    """A brand or finance word alone is ambiguous; with a product word it is not."""

    def test_a_bare_ambiguous_term_stays_unsafe(self) -> None:
        for query in ("bank", "insurance", "loan", "apple", "nike", "software", "erp"):
            with self.subTest(query=query):
                self.assertTrue(is_unsafe_broad_query(query))

    def test_an_ambiguous_term_with_only_connectives_stays_unsafe(self) -> None:
        self.assertTrue(is_unsafe_broad_query("insurance for the"))
        self.assertTrue(is_unsafe_broad_query("bank loan"))

    def test_a_product_word_narrows_an_ambiguous_term(self) -> None:
        # These are ordinary buyer queries and were all being treated as too broad.
        for query in (
            "power bank for iphone",
            "nike running shoes",
            "bosch drill",
            "apple laptop",
            "galaxy smartphone",
        ):
            with self.subTest(query=query):
                self.assertFalse(is_unsafe_broad_query(query))

    def test_empty_and_whitespace_queries_stay_unsafe(self) -> None:
        for query in ("", "   "):
            with self.subTest(query=query):
                self.assertTrue(is_unsafe_broad_query(query))


class SurfaceStatesWhatItCouldNotMatchTests(_FeedTestCase):
    """Four products for a partly-matched request is honest only if the page says so."""

    def _page(self, query: str) -> tuple[int, str, str]:
        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            return None

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
        body = b"".join(wsgi_app(environ, start_response)).decode("utf-8")

        def text(pattern: str) -> str:
            found = re.search(pattern, body, re.S)
            if found is None:
                return ""
            return html.unescape(re.sub(r"<[^>]+>", "", found.group(1))).strip()

        return (
            len(re.findall(r'<article class="pw-card', body)),
            text(r'<p class="pw-query-line">(.*?)</p>'),
            text(r'<p class="pw-reference-disclaimer">(.*?)</p>'),
        )

    def test_the_page_names_the_words_it_could_not_match(self) -> None:
        cards, query_line, _notice = self._page("power bank 20000mah for iphone")
        self.assertEqual(cards, 4)
        self.assertIn("could not match", query_line)
        self.assertIn("20000mah", query_line)
        self.assertIn("iphone", query_line)

    def test_a_fully_matched_query_carries_no_such_note(self) -> None:
        cards, query_line, _notice = self._page("coffee machine")
        self.assertEqual(cards, 4)
        self.assertNotIn("could not match", query_line)

    def test_an_ambiguous_query_asks_for_the_product_name(self) -> None:
        cards, _query_line, notice = self._page("smartphone with good battery")
        self.assertEqual(cards, 0)
        self.assertIn("not sure which product you mean", notice)

    def test_the_flagship_concept_example_returns_a_decision(self) -> None:
        # The concept's own example and the README's documented demo query.
        cards, query_line, _notice = self._page("power bank 20000mah for iphone")
        self.assertEqual(cards, 4)
        self.assertIn("power bank 20000mah for iphone", query_line)


if __name__ == "__main__":
    unittest.main()
