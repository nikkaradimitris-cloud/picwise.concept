"""The search reads English only: Greek and greeklish closed (owner, 2026-11-07).

Owner: «Μήπως να αφαιρούσαμε τα ελληνικά και τα greeklish διότι το site είναι για
αγγλία...», then «Ναι σε όλα, κλείσε και τα δύο». The debugging's first measure
(`deployment/server/print_search_reading.py`) found English searches read as greeklish:
"pones" as «πάνες» (nappies), "couches" as «κούκλες» (dolls), and «μπαταρία» read as
boots. Pinned here, with the switch as the site has it (`PICWISE_GREEK_SEARCH` unset):

- a word in Greek letters names nothing, and a word in Latin letters is read as English
  only: never greeklish, never Greek typed on the English layout;
- English reads as before: names, typos, preference words, a request for a used item;
- a search with a word in Greek letters is answered by the note that PicWise searches in
  English, and nothing else; "Did you mean" offers no Greek name;
- an older vocabulary's category alone (the greeklish "psygeio") is no longer said to be
  understood when nothing is shown;
- the search box offers no Greek name;
- with `PICWISE_GREEK_SEARCH=on`, Greek and greeklish are read as before (the code stays,
  for a Greek site one day).

Every product is local test data: fictional brands, `.invalid` addresses.
"""
from __future__ import annotations

import io
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_nlu.concept_understanding import (  # noqa: E402
    GREEK_SEARCH_ENV,
    greek_search_on,
    read_condition_request,
    suggest_product_names,
    understand_product_query,
)
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.suggestions import build_search_suggestions  # noqa: E402
from picwise_search.live_search_resolver import (  # noqa: E402
    SEARCH_IN_ENGLISH_REASON,
    resolve_live_search,
    searches_in_greek_letters,
)

FIXTURE_FEED = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"


class _Switch:
    """Set the switch for a block, and put back what was there."""

    def __init__(self, value: str | None) -> None:
        self.value = value
        self.previous: str | None = None

    def __enter__(self) -> None:
        self.previous = os.environ.get(GREEK_SEARCH_ENV)
        if self.value is None:
            os.environ.pop(GREEK_SEARCH_ENV, None)
        else:
            os.environ[GREEK_SEARCH_ENV] = self.value

    def __exit__(self, *_exc: object) -> None:
        if self.previous is None:
            os.environ.pop(GREEK_SEARCH_ENV, None)
        else:
            os.environ[GREEK_SEARCH_ENV] = self.previous


def setUpModule() -> None:  # noqa: N802 - unittest's name
    # As the site has it: the switch not set.
    global _OUTER
    _OUTER = _Switch(None)
    _OUTER.__enter__()


def tearDownModule() -> None:  # noqa: N802 - unittest's name
    _OUTER.__exit__()


class ReadingTests(unittest.TestCase):
    def test_the_switch_is_off_unless_set(self) -> None:
        self.assertFalse(greek_search_on())
        for value in ("on", "1", "true", "yes", " ON "):
            with _Switch(value):
                self.assertTrue(greek_search_on(), value)
        for value in ("off", "0", "", "no"):
            with _Switch(value):
                self.assertFalse(greek_search_on(), value)

    def test_a_word_in_greek_letters_names_nothing(self) -> None:
        for query in ("ψυγείο", "μπαταρία", "μπαταρίες 3α", "σακίδιο για σχολείο", "λαπτοπ"):
            reading = understand_product_query(query)
            self.assertFalse(reading.understood, query)
            self.assertIsNone(reading.concept_id, query)

    def test_a_word_in_latin_letters_is_never_read_as_greeklish(self) -> None:
        for query in ("psygeio", "plintirio", "cygeio", "mpataria", "pones", "mobile pones", "couches", "pati"):
            reading = understand_product_query(query)
            self.assertNotIn(reading.concept_id, {"refrigerator", "washing_machine", "nappies", "doll", "insoles"}, query)
        self.assertEqual(understand_product_query("skinny jeans").concept_id, "jeans")

    def test_english_reads_as_before(self) -> None:
        cases = {
            "washing machine": ("washing_machine", True),
            "wahsing machine": ("washing_machine", False),
            "fridge": ("refrigerator", True),
            "gaming laptop": ("laptop", True),
            "inverter air conditioner": ("air_conditioner", True),
        }
        for query, (kind, exact) in cases.items():
            reading = understand_product_query(query)
            self.assertEqual((reading.concept_id, reading.exact), (kind, exact), query)
        self.assertEqual(understand_product_query("gaming laptop").filters, ("gaming",))
        self.assertEqual(understand_product_query("refurbished laptop").condition_request, ("refurbished",))
        self.assertTrue(read_condition_request("used laptop").wants_non_new)
        self.assertFalse(read_condition_request("metaxeirismeno laptop").wants_non_new)
        self.assertFalse(read_condition_request("μεταχειρισμένο laptop").wants_non_new)

    def test_did_you_mean_offers_no_greek_name(self) -> None:
        self.assertEqual(suggest_product_names("ψυγιο"), ())
        self.assertEqual(suggest_product_names("dsk"), ("desk",))

    def test_greek_and_greeklish_read_as_before_with_the_switch_on(self) -> None:
        with _Switch("on"):
            self.assertEqual(understand_product_query("ψυγείο").concept_id, "refrigerator")
            self.assertEqual(understand_product_query("psygeio").concept_id, "refrigerator")
            self.assertEqual(understand_product_query("laptop φθηνό").judgements, ("φθηνο",))
            self.assertTrue(read_condition_request("metaxeirismeno laptop").wants_non_new)
            self.assertIn("ψυγείο", suggest_product_names("ψγειο"))
        self.assertIsNone(understand_product_query("ψυγείο").concept_id)


def _page(query: str) -> str:
    from api.index import app

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/search",
        "QUERY_STRING": "q=" + quote(query),
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "HTTP_HOST": "localhost",
        "wsgi.input": io.BytesIO(),
        "wsgi.url_scheme": "http",
    }
    return b"".join(app(environ, lambda *_args: None)).decode("utf-8")


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._feed = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(FIXTURE_FEED)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._feed is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = cls._feed

    def test_a_search_in_greek_letters_is_told_picwise_searches_in_english(self) -> None:
        self.assertTrue(searches_in_greek_letters("ψυγείο"))
        self.assertTrue(searches_in_greek_letters("laptop φθηνό"))
        self.assertFalse(searches_in_greek_letters("fridge"))
        for query in ("ψυγείο", "μπαταρία", "laptop φθηνό"):
            resolution = resolve_live_search(query)
            self.assertIn(SEARCH_IN_ENGLISH_REASON, resolution.reason_codes, query)
            self.assertEqual(resolution.resolver_state, "not_understood", query)
            self.assertEqual(resolution.provider_feed_selected_products, (), query)
            page = _page(query)
            self.assertIn("PicWise searches in English. Please type the product's name in English.", page)
            self.assertNotIn('<article class="pw-card', page)

    def test_greeklish_is_no_longer_said_to_be_understood(self) -> None:
        for query in ("psygeio", "plintirio ruxon"):
            resolution = resolve_live_search(query)
            self.assertEqual(resolution.resolver_state, "not_understood", query)
            self.assertNotIn(SEARCH_IN_ENGLISH_REASON, resolution.reason_codes, query)
            page = _page(query)
            self.assertNotIn("PicWise understood this search", page)
            self.assertNotIn('<article class="pw-card', page)

    def test_english_searches_are_answered_as_before(self) -> None:
        resolution = resolve_live_search("fridge")
        self.assertNotIn(SEARCH_IN_ENGLISH_REASON, resolution.reason_codes)
        self.assertNotIn("resolver_state_not_understood_by_the_reading", resolution.reason_codes)
        self.assertTrue(resolution.provider_feed_selected_products)
        self.assertIn('<article class="pw-card', _page("fridge"))

    def test_with_the_switch_on_greek_is_answered_as_before(self) -> None:
        with _Switch("on"):
            resolution = resolve_live_search("ψυγείο")
            self.assertNotIn(SEARCH_IN_ENGLISH_REASON, resolution.reason_codes)
            self.assertTrue(resolution.provider_feed_selected_products)


def _product(pid: str, title: str, product_type: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand="Fixturon",
        category_text="",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text="20.00",
        availability_text="in stock",
        currency="GBP",
        raw={"product_type": product_type, "brand_name": "Fixturon"},
    )


class SuggestionTests(unittest.TestCase):
    def test_the_search_box_offers_no_greek_name(self) -> None:
        catalogue = tuple(
            _product(f"k{index}", f"Fixturon Electric Kettle {index}", "Kettles") for index in range(1, 4)
        )
        texts = [suggestion.text for suggestion in build_search_suggestions(catalogue)]
        self.assertIn("kettle", texts)
        self.assertFalse(any(searches_in_greek_letters(text) for text in texts), texts)
        with _Switch("on"):
            texts = [suggestion.text for suggestion in build_search_suggestions(catalogue)]
            self.assertIn("βραστήρας", texts)


if __name__ == "__main__":
    unittest.main()
