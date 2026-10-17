"""Step 4 of the price-first plan (2026-10-17): the search page.

The owner's decisions of 2026-10-16 and 2026-10-17, as `docs/LANDING_PAGE_SPEC.md`
records them, and what is pinned here:

- the box reads "What are you looking for?", and "What is PicWise?" says what price
  first does;
- a scanning screen shows as a search starts, with the real number of products and
  shops when the server has the feed loaded, and no number otherwise. It names no step
  the browser cannot see;
- suggestions are the names of the kinds PicWise knows (English and Greek), a brand
  with a kind, and the shops' own names for what they sell, each offered only when it
  finds products, the larger first, and fetched once from `/suggest.json`;
- a microphone shows only where the browser can listen, and the privacy page says who
  hears the audio.

Every row is written with fictional brands, with `.invalid` URLs.
"""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    load_eligible_provider_feed_products,
    peek_search_catalogue_counts,
)
from picwise_providers.suggestions import build_search_suggestions, suggestion_key  # noqa: E402
from picwise_surface.legal import render_privacy_page  # noqa: E402
from picwise_surface.reference import _SEARCH_SCRIPT, render_picwise_reference_surface  # noqa: E402


def _product(pid: str, title: str, *, brand: str, product_type: str = "", category: str = "") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand=brand,
        category_text=category,
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text="20.00",
        availability_text="in stock",
        currency="GBP",
        raw={"product_type": product_type, "merchant_product_category_path": category, "brand_name": brand},
    )


def _catalogue() -> tuple[ProviderProduct, ...]:
    hutches = "Pet Supplies > Small Animal Habitats > Rabbit Hutches"
    return (
        _product("k1", "Fixturon Electric Kettle 1.7L", brand="Fixturon", product_type="Kettles"),
        _product("k2", "Fixturon Glass Kettle 1.5L", brand="Fixturon", product_type="Kettles"),
        _product("k3", "Testline Travel Kettle 0.5L", brand="Testline", product_type="Kettles"),
        _product("l1", "Fixturon Book 14 Laptop", brand="Fixturon", product_type="Laptops"),
        _product("l2", "Fixturon Book 16 Laptop", brand="Fixturon", product_type="Laptops"),
        _product("h1", "Sampleworks Wooden Rabbit Hutch, 2 Tier", brand="Sampleworks", category=hutches),
        _product("h2", "Sampleworks Rabbit Hutch with Run", brand="Sampleworks", category=hutches),
        _product("h3", "Sampleworks Large Rabbit Hutch, Fir Wood", brand="Sampleworks", category=hutches),
        _product("h4", "Sampleworks Rabbit Hutch Outdoor", brand="Sampleworks", category=hutches),
        _product("c1", "Sampleworks Rabbit Hutch Cover, Waterproof", brand="Sampleworks", category=hutches),
    )


class WordingTests(unittest.TestCase):
    """Owner, 2026-10-17."""

    def test_the_box_asks_what_the_buyer_is_looking_for(self) -> None:
        page = render_picwise_reference_surface("")
        self.assertIn('placeholder="What are you looking for?"', page)
        self.assertIn('aria-label="What are you looking for?"', page)
        self.assertNotIn("See the 4 best products", page)

    def test_what_is_picwise_says_what_price_first_does(self) -> None:
        page = render_picwise_reference_surface("")
        self.assertIn(
            "PicWise finds the product you want in the shops it is connected to, shows what "
            "the shops list as in stock, cheapest first, and marks one mid-priced Recommended.",
            page,
        )
        self.assertNotIn("recommends the 4 best matches", page)

    def test_the_page_still_searches_without_javascript(self) -> None:
        page = render_picwise_reference_surface("kettle")
        self.assertIn('<form class="pw-search-shell" action="/search" method="get"', page)
        self.assertIn('name="q" value="kettle"', page)


class ScanningScreenTests(unittest.TestCase):
    def test_it_carries_the_real_counts_when_the_feed_is_loaded(self) -> None:
        page = render_picwise_reference_surface("", catalogue=(39815, 2))
        self.assertIn('id="pw-scan"', page)
        self.assertIn('data-products="39,815" data-shops="2" hidden', page)

    def test_it_names_no_number_without_them(self) -> None:
        page = render_picwise_reference_surface("", catalogue=None)
        self.assertIn('<div class="pw-scan" id="pw-scan" role="status" aria-live="polite" hidden>', page)

    def test_it_says_only_what_the_browser_sees(self) -> None:
        # "Found these, cross-checking, sending" happen on the server within the one
        # request: a screen narrating them would say what it cannot see.
        self.assertIn("Searching ", _SEARCH_SCRIPT)
        for step in ("Found", "Cross-checking", "Sending", "Checking prices"):
            self.assertNotIn(step, _SEARCH_SCRIPT)

    def test_the_counts_come_only_from_a_loaded_feed(self) -> None:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        with handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
                 "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock",
                 "merchant_name", "description", "data_provenance"]
            )
            for index, shop in enumerate(("Fixture Store One", "Fixture Store One", "Fixture Store Two"), start=1):
                writer.writerow(
                    [f"p{index}", f"Fixturon Electric Kettle {index}", "Fixturon", "Kettles", "Kitchen",
                     f"https://fixture.example.invalid/out/p{index}",
                     f"https://fixture.example.invalid/img/p{index}.jpg", f"{20 + index}.00", "GBP", "1",
                     shop, fixture_description(), "local_test_fixture"]
                )
        self.addCleanup(os.unlink, handle.name)
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = handle.name
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
        # Drawing a page never loads the feed to count it.
        self.assertIsNone(peek_search_catalogue_counts())
        load_eligible_provider_feed_products()
        self.assertEqual(peek_search_catalogue_counts(), (3, 2))


class SuggestionTests(unittest.TestCase):
    """What the box suggests, read from the catalogue a search reads."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.suggestions = build_search_suggestions(_catalogue())
        cls.texts = [suggestion.text for suggestion in cls.suggestions]

    def test_the_kinds_with_products_are_offered_in_english_and_greek(self) -> None:
        for text in ("kettle", "βραστήρας", "laptop", "λάπτοπ"):
            self.assertIn(text, self.texts)

    def test_a_kind_without_products_is_not_offered(self) -> None:
        self.assertNotIn("washing machine", self.texts)
        self.assertNotIn("πλυντήριο ρούχων", self.texts)

    def test_a_name_is_offered_once_not_with_its_plural(self) -> None:
        self.assertNotIn("laptops", self.texts)
        self.assertNotIn("βραστήρες", self.texts)

    def test_a_brand_with_a_kind_needs_two_products_and_a_brand_alone_is_never_offered(self) -> None:
        self.assertIn("Fixturon kettle", self.texts)
        self.assertNotIn("Testline kettle", self.texts)
        self.assertNotIn("Fixturon", self.texts)

    def test_a_shops_own_name_is_offered_when_three_products_answer_it(self) -> None:
        # Four hutches are named so in their titles; the cover is not a hutch.
        hutches = next(s for s in self.suggestions if s.text == "rabbit hutches")
        self.assertEqual(hutches.products, 4)

    def test_the_larger_come_first(self) -> None:
        self.assertLess(self.texts.index("rabbit hutches"), self.texts.index("kettle"))
        self.assertLess(self.texts.index("kettle"), self.texts.index("laptop"))

    def test_accents_case_and_final_sigma_do_not_matter(self) -> None:
        self.assertEqual(suggestion_key("Λάπτοπ"), "λαπτοπ")
        self.assertEqual(suggestion_key("φορητός"), suggestion_key("φορητοσ"))


class SuggestEndpointTests(unittest.TestCase):
    """`/suggest.json`, served through api/index.py, the deployed entry point."""

    def _get(self, path: str) -> tuple[str, dict[str, str], bytes]:
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": path,
                    "QUERY_STRING": "",
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        )
        return str(captured["status"]), captured["headers"], body  # type: ignore[return-value]

    def _without_feed(self) -> None:
        previous = {key: os.environ.pop(key, None) for key in ("AWIN_FEED_FILE", "AWIN_FEED_URL")}
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            for key, value in previous.items():
                if value is not None:
                    os.environ[key] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def test_the_list_is_json_and_kept_by_the_browser_for_an_hour(self) -> None:
        self._without_feed()
        status, headers, body = self._get("/suggest.json")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "public, max-age=3600")
        # No feed connected: nothing to find, so nothing is suggested.
        self.assertEqual(json.loads(body), {"v": 1, "suggestions": []})

    def test_with_a_feed_the_list_holds_its_kinds(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(fixture)
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
        _status, _headers, body = self._get("/suggest.json")
        suggestions = json.loads(body)["suggestions"]
        self.assertIn("laptop", suggestions)
        self.assertIn("λάπτοπ", suggestions)
        self.assertEqual(len(suggestions), len(set(suggestions)))


class MicrophoneTests(unittest.TestCase):
    def test_the_button_is_hidden_until_the_browser_can_listen(self) -> None:
        page = render_picwise_reference_surface("")
        self.assertIn('id="pw-mic" type="button" aria-label="Search by voice"', page)
        mic = page[page.index('id="pw-mic"'):page.index("</button>", page.index('id="pw-mic"'))]
        self.assertIn(" hidden>", mic)
        self.assertIn("in Chrome the audio is sent to Google", mic)

    def test_the_search_starts_when_the_buyer_stops_speaking(self) -> None:
        # Owner, 2026-10-17: "Αναζήτηση αμέσως".
        self.assertIn("recognition.onend", _SEARCH_SCRIPT)
        self.assertIn("if(q){choose(q);}", _SEARCH_SCRIPT)

    def test_the_privacy_page_says_who_hears_it(self) -> None:
        page = render_privacy_page()
        self.assertIn("Voice search (microphone)", page)
        self.assertIn("in Google Chrome the audio is sent to Google", page)
        self.assertIn("never the audio", page)


class ScriptTests(unittest.TestCase):
    def test_the_script_is_valid_javascript(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
            handle.write(_SEARCH_SCRIPT)
        self.addCleanup(os.unlink, handle.name)
        result = subprocess.run([node, "--check", handle.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_script_is_small(self) -> None:
        # PROJECT_RULES section 9 and the concept forbid heavy scripts.
        self.assertLess(len(_SEARCH_SCRIPT.encode("utf-8")), 8000)


if __name__ == "__main__":
    unittest.main()
