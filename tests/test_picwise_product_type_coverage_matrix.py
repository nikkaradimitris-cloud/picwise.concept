"""Table-driven product-type coverage across the 18 mega categories.

`docs/picwise_runtime_truth_audit_rules.md` states that example queries (laptop, mouse,
webcam) are canaries only: they detect regressions but do not prove generic product-type
intelligence. This module is the matrix that rule asks for. Each row is a mega category, a
feed product type and the query a buyer would type, and the assertion is end-to-end
through the deployed WSGI entrypoint: four rendered cards and exactly one recommendation.

Inventory comes from `tests/fixtures/provider_feed_coverage_matrix_fixture.csv`, which
holds four products for each product type below. It is local test data, not provider data,
and proves nothing about a real feed's contents — only that PicWise delivers the decision
for a product type when the inventory for it exists.
"""
from __future__ import annotations

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

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"
_FEED_ENV = "AWIN_FEED_FILE"

# (mega category, feed product type, buyer query)
COVERAGE_MATRIX: tuple[tuple[str, str, str], ...] = (
    ("home_appliances_laundry_climate", "Washing Machines", "washing machine"),
    ("home_appliances_laundry_climate", "Air Conditioners", "air conditioner"),
    ("kitchen_cooking_household", "Coffee Machines", "coffee machine"),
    ("kitchen_cooking_household", "Microwave Ovens", "microwave"),
    ("furniture_living_storage_smart_home", "Office & Computer Chairs", "office chair"),
    ("furniture_living_storage_smart_home", "Desks", "desk"),
    ("phones_mobile_accessories", "Mobile Phones", "smartphone"),
    ("phones_mobile_accessories", "Power Banks", "power bank"),
    ("computers_office_peripherals", "Keyboards", "keyboard"),
    ("computers_office_peripherals", "Webcams", "webcam"),
    ("computers_office_peripherals", "Toner Cartridges", "toner cartridge"),
    ("computers_office_peripherals", "Ink Cartridges", "ink cartridge"),
    ("computers_office_peripherals", "Multifunction Printers", "printer"),
    ("audio_video_gaming_cameras", "Headphones & Headsets", "headphones"),
    ("car_parts_service_maintenance", "Car Batteries", "car battery"),
    ("tyres_wheels_car_accessories", "Tyres", "tyres"),
    ("moto_bicycle_mobility_gear", "Bicycle Helmets", "bicycle helmet"),
    ("power_tools_workshop", "Power Drills", "drill"),
    ("hand_tools_consumables_measuring", "Screwdriver Sets", "screwdriver set"),
    ("garden_outdoor_repair_building", "Lawn Mowers", "lawn mower"),
    ("health_wellness_safety_devices", "Blood Pressure Monitors", "blood pressure monitor"),
    ("beauty_grooming_personal_care", "Electric Shavers", "electric shaver"),
    ("baby_kids_pets_sports_outdoor", "Baby Strollers", "stroller"),
    ("clothing_apparel_workwear", "Work Trousers", "work trousers"),
    ("footwear_shoes_sneakers_boots", "Athletic Shoes", "running shoes"),
    ("jewelry_watches_bags_fashion_accessories", "Wristwatches", "watch"),
)

# Known gap, asserted so it cannot regress silently and cannot be forgotten.
# "tv" is not recognised as a synonym of "television". The word is not a substring of
# "television", so nothing in the title or product type matches, and the query only
# reaches a weak match. The fix belongs in the taxonomy/vocabulary layer, whose deep packs
# feed the search artifact fingerprint; it must not be patched into the feed scorer,
# because the runtime truth rules forbid building a second vocabulary system.
KNOWN_VOCABULARY_GAPS: tuple[tuple[str, str], ...] = (
    ("audio_video_gaming_cameras", "tv"),
)



def _render(query: str) -> str:
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
    return b"".join(wsgi_app(environ, start_response)).decode("utf-8")


def _card_count(body: str) -> int:
    return len(re.findall(r'<article class="pw-card', body))


def _recommended_count(body: str) -> int:
    return len(re.findall(r'<article class="pw-card pw-card-recommended', body))


class _CoverageFixtureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_feed = os.environ.get(_FEED_ENV)
        os.environ[_FEED_ENV] = str(FIXTURE_CSV)
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


class ProductTypeCoverageMatrixTests(_CoverageFixtureTestCase):
    def test_every_covered_product_type_delivers_four_plus_one(self) -> None:
        for mega_category, product_type, query in COVERAGE_MATRIX:
            with self.subTest(mega_category=mega_category, product_type=product_type):
                body = _render(query)
                self.assertEqual(
                    _card_count(body),
                    4,
                    msg=f"{query!r} ({product_type}) did not render four choices",
                )
                self.assertEqual(
                    _recommended_count(body),
                    1,
                    msg=f"{query!r} did not render exactly one recommendation",
                )

    def test_matrix_spans_every_mega_category(self) -> None:
        from picwise_taxonomy import get_mega_categories

        registry_ids = set()
        for entry in get_mega_categories():
            data = entry if isinstance(entry, dict) else entry.__dict__
            identifier = data.get("mega_category_id") or data.get("id")
            if identifier:
                registry_ids.add(str(identifier))
        covered = {mega for mega, _type, _query in COVERAGE_MATRIX}
        covered.update(mega for mega, _query in KNOWN_VOCABULARY_GAPS)
        # phones_mobile_accessories is covered by the smartphone row; its power-bank
        # query is tracked separately under the Amazon-path gap below.
        self.assertEqual(
            registry_ids - covered,
            set(),
            msg="a mega category has no product type in the coverage matrix",
        )

    def test_selected_products_never_overclaim_purchasability(self) -> None:
        for _mega, _product_type, query in COVERAGE_MATRIX:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                for product in resolution.provider_feed_selected_products:
                    self.assertFalse(product.get("verified_purchasable"))
                    self.assertEqual(
                        product.get("purchasability_state"), "purchasability_unknown"
                    )


class KnownVocabularyGapTests(_CoverageFixtureTestCase):
    def test_known_gap_is_still_a_gap_and_stays_safe(self) -> None:
        for _mega, query in KNOWN_VOCABULARY_GAPS:
            with self.subTest(query=query):
                body = _render(query)
                # If this starts rendering four cards the vocabulary gap has been
                # closed: move the row into COVERAGE_MATRIX rather than deleting it.
                self.assertEqual(_card_count(body), 0)
                self.assertNotIn("Showing 4 selected real products", body)


class WithheldRecommendationTests(_CoverageFixtureTestCase):
    """A recommendation is never reported without the products behind it."""

    def test_weak_feed_opportunity_withholds_the_recommendation(self) -> None:
        resolution = resolve_live_search("tv")
        self.assertEqual(len(resolution.provider_feed_selected_products), 0)
        self.assertEqual(
            resolution.provider_feed_decision_status,
            "recommendation_withheld_weak_feed_opportunity",
        )
        self.assertIsNone(resolution.provider_feed_recommended_product_id)
        self.assertEqual(resolution.provider_feed_recommendation_confidence, "unknown")

    def test_exposed_selection_still_reports_a_real_recommendation(self) -> None:
        resolution = resolve_live_search("coffee machine")
        self.assertEqual(len(resolution.provider_feed_selected_products), 4)
        self.assertEqual(resolution.provider_feed_decision_status, "recommended")
        self.assertTrue(resolution.provider_feed_recommended_product_id)
        selected_ids = {
            str(product.get("provider_product_id"))
            for product in resolution.provider_feed_selected_products
        }
        self.assertIn(resolution.provider_feed_recommended_product_id, selected_ids)

    def test_every_reported_recommendation_has_products_behind_it(self) -> None:
        queries = [query for _m, _t, query in COVERAGE_MATRIX]
        queries.extend(query for _m, query in KNOWN_VOCABULARY_GAPS)
        for query in queries:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                if resolution.provider_feed_decision_status == "recommended":
                    self.assertTrue(
                        resolution.provider_feed_selected_products,
                        msg=f"{query!r} claims a recommendation with no products",
                    )


class AmazonRemovedFromDecisionPathTests(_CoverageFixtureTestCase):
    """Amazon has been removed from the product.

    The manually curated Amazon path used to intercept power-bank queries and render
    four choices with no recommendation, breaking Decision Contract item 2. Power banks
    now resolve through the same provider-feed engine as everything else, which supplies
    the recommendation the contract requires.
    """

    def test_power_bank_is_served_by_the_feed_with_one_recommendation(self) -> None:
        body = _render("power bank")
        self.assertEqual(_card_count(body), 4)
        self.assertEqual(_recommended_count(body), 1)

    def test_no_query_in_the_matrix_renders_an_amazon_cta(self) -> None:
        queries = [query for _m, _t, query in COVERAGE_MATRIX]
        queries.extend(query for _m, query in KNOWN_VOCABULARY_GAPS)
        for query in queries:
            with self.subTest(query=query):
                body = _render(query)
                self.assertNotIn("View on Amazon", body)
                self.assertNotIn("/out/amazon", body)

    def test_no_category_is_routed_to_a_manual_amazon_provider(self) -> None:
        from picwise_search.live_search_resolver import _CONNECTED_PROVIDER_BY_CATEGORY

        self.assertNotIn(
            "manual_amazon_affiliate", set(_CONNECTED_PROVIDER_BY_CATEGORY.values())
        )


class IntentMapDoesNotOverrideFeedTypeTests(_CoverageFixtureTestCase):
    """The single-token intent map must not veto the feed's own categorisation.

    "monitor" maps to computer monitors, which made "blood pressure monitor" collide
    with its own correct feed product type and take the conflict penalty.
    """

    def test_multi_word_query_matching_its_feed_type_is_not_penalised(self) -> None:
        resolution = resolve_live_search("blood pressure monitor")
        self.assertEqual(resolution.provider_feed_selection_status, "selected")
        self.assertEqual(len(resolution.provider_feed_selected_products), 4)
        for product in resolution.provider_feed_selected_products:
            self.assertEqual(product.get("product_type"), "Blood Pressure Monitors")

    def test_single_token_query_still_rejects_its_accessories(self) -> None:
        # Guarding the case the penalty exists for: the relaxation applies only to
        # multi-token queries, so "laptop" must still not be served bags.
        from picwise_providers.search_selection import (
            _product_type_alignment_adjustment,
            _PRODUCT_TYPE_CONFLICT_PENALTY,
        )

        self.assertEqual(
            _product_type_alignment_adjustment(
                "Laptop Cases & Bags",
                allowed_product_types=("laptops",),
                query_seeks_accessory=False,
                tokens=("laptop",),
            ),
            -_PRODUCT_TYPE_CONFLICT_PENALTY,
        )


if __name__ == "__main__":
    unittest.main()
