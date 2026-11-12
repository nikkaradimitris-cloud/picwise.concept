"""The price bar above the cards (owner, 2026-11-12).

«Να μπει ένα φίλτρο με τη μορφή μπάρας που να διαλέγει με την τιμή για να γλιτώσουμε το
πρόβλημα που βγάζει τα φθηνότερα και μπορεί να είναι smartwatch και να δείχνει λουράκια
μπορεί να είναι tablet και να βγάζει πρώτα θήκες ... βάζοντας ένα φίλτρο τιμής το οποίο να
τερματίζει στην υψηλοτερή και να ξεκινάει από την χαμηλότερη κουνώντας μία μπίλια θα μπορεί
αμέσως να φιλτράρει και να ανεβαίνει πιο πάνω στην τιμή».

The bar runs from the answer's lowest price to its highest; the price chosen on it starts
the answer from that price, and the same rules (the Recommended, offers first, cheapest
first, "More", the counter) hold for the products from it.
"""
from __future__ import annotations

import html
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.search_selection import PRICE_BAR_STEPS, _price_bar  # noqa: E402
from picwise_search.live_search_resolver import parse_min_price  # noqa: E402
from picwise_surface.price_bar import PRICE_BAR_SCRIPT, PRICE_BAR_STYLES  # noqa: E402
from picwise_surface.search_script import _SEARCH_SCRIPT  # noqa: E402
from test_picwise_design_2026_10_31 import _FeedMixin, _call, _cards, _ean13, _text  # noqa: E402
from test_picwise_prepared_catalogue import _PreparedMixin, _feed_rows  # noqa: E402

# Twelve kettles: four cheap ones, eight dearer, each with a barcode.
_PRICES = (8.0, 9.0, 11.0, 12.0, 34.0, 39.0, 45.0, 52.0, 60.0, 74.0, 89.0, 120.0)


def _kettles(prices: tuple[float, ...] = _PRICES) -> list[dict[str, str]]:
    shops = ("Fixture Store One", "Fixture Store Two", "Fixture Store Three")
    return [
        {"pid": f"k{index}", "title": f"Fixturon Kettle Model {index} 1.7L", "price": f"{price:.2f}",
         "ean": _ean13(f"51{index:010d}"), "shop": shops[index % 3]}
        for index, price in enumerate(prices, start=1)
    ]


def _prices(page: str) -> list[float]:
    return [
        float(html.unescape(re.search(r'<p class="pw-price">(.*?)</p>', card).group(1)).lstrip("£"))
        for card in _cards(page)
    ]


def _bar(page: str) -> str:
    found = re.search(r'<form class="pw-pricebar".*?</form>', page, re.S)
    return found.group(0) if found else ""


def _heading(page: str) -> str:
    return _text(re.search(r'<h1 class="pw-query-line">(.*?)</h1>', page, re.S).group(1))


def _recommended_label(page: str) -> str:
    card = next(card for card in _cards(page) if "pw-card-recommended" in card)
    return _text(re.search(r'<p class="pw-role-label">(.*?)</p>', card).group(1))


class PriceBarTests(_FeedMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._serve(_kettles())

    def test_the_bar_runs_from_the_lowest_price_to_the_highest(self) -> None:
        page = _call("/search", {"q": "kettle"})
        bar = _bar(page)
        self.assertTrue(bar)
        self.assertIn('data-low="8.00" data-high="120.00"', bar)
        self.assertIn('min="8" max="120" step="1" value="8"', bar)
        self.assertEqual(len(re.findall(r"<i[ >]", bar)), PRICE_BAR_STEPS)
        self.assertIn('<output class="pw-pricebar-value" id="pw-pricebar-value" for="pw-pricebar-range">Any price</output>', bar)
        # Above the cards, under the heading and its counter.
        self.assertLess(page.index('<div class="pw-results-head">'), page.index('<form class="pw-pricebar"'))
        self.assertLess(page.index('<form class="pw-pricebar"'), page.index('<article class="pw-card'))
        # Without a price chosen the answer is as it was: the cheap kettles first.
        self.assertEqual(_heading(page), "Results for: kettle, cheapest first")
        self.assertEqual(_recommended_label(page), "Mid-priced for this category")

    def test_a_chosen_price_starts_the_answer_from_it(self) -> None:
        page = _call("/search", {"q": "kettle", "min": "30"})
        prices = _prices(page)
        self.assertEqual(len(prices), 4)
        self.assertTrue(all(price >= 30 for price in prices), prices)
        # Eight kettles from £30; the counter, the heading and the words say so.
        self.assertIn('<p class="pw-results-count">4 of 8</p>', page)
        self.assertEqual(_heading(page), "Results for: kettle, from £30, cheapest first")
        self.assertIn("The Recommended is mid-priced of the products from £30.", page)
        self.assertNotIn("mid-priced for this category", page)
        self.assertEqual(_recommended_label(page), "Mid-priced from £30")
        self.assertIn(">From £30</output>", _bar(page))
        # The bar is still the whole answer's: the buyer can move back down.
        self.assertIn('data-low="8.00" data-high="120.00"', _bar(page))
        # The steps below the price chosen are pale.
        self.assertIn('class="out"', _bar(page))

    def test_the_recommended_is_the_middle_of_the_products_from_that_price(self) -> None:
        # From £34: seven kettles, £34 to £120; the middle one is £52.
        page = _call("/search", {"q": "kettle", "min": "34"})
        self.assertEqual(_prices(page)[0], 52.0)
        # Then the cheapest from that price, the cheap end of those (owner, 2026-10-16).
        self.assertEqual(_prices(page)[1:], [34.0, 39.0, 45.0])

    def test_more_keeps_the_chosen_price(self) -> None:
        page = _call("/search", {"q": "kettle", "min": "30"})
        more = html.unescape(re.search(r'<a class="pw-more-button" href="([^"]+)"', page).group(1))
        self.assertEqual(more, "/search?q=kettle&min=30&shown=8#pw-choice-5")
        opened = _call("/search", {"q": "kettle", "min": "30", "shown": "8"})
        self.assertEqual(len(_prices(opened)), 8)
        self.assertTrue(all(price >= 30 for price in _prices(opened)))

    def test_a_price_above_the_dearest_shows_the_dearest(self) -> None:
        page = _call("/search", {"q": "kettle", "min": "5000"})
        self.assertEqual(_prices(page), [120.0])
        self.assertEqual(_heading(page), "Results for: kettle, from £120, cheapest first")

    def test_what_is_not_a_price_chooses_none(self) -> None:
        plain = _prices(_call("/search", {"q": "kettle"}))
        for value in ("abc", "-5", "0", "1e3", "12.345", "30.", "１５", " ", "9" * 20):
            page = _call("/search", {"q": "kettle", "min": value})
            self.assertEqual(_prices(page), plain, value)
            self.assertIn(">Any price</output>", _bar(page), value)

    def test_the_bar_works_without_javascript(self) -> None:
        bar = _bar(_call("/search", {"q": "kettle"}))
        self.assertTrue(bar.startswith('<form class="pw-pricebar" action="/search" method="get" aria-label="Price">'))
        self.assertIn('<input type="hidden" name="q" value="kettle">', bar)
        self.assertIn('type="range" name="min"', bar)
        self.assertIn('<button class="pw-pricebar-go" type="submit">Show</button>', bar)
        # With JavaScript the button goes and letting the knob go shows the answer.
        self.assertIn(".pw-js .pw-pricebar-go{display:none;}", PRICE_BAR_STYLES)
        for words in ('range.addEventListener("change"', "form.submit()", 'scan.hidden=false',
                      'range.removeAttribute("name")', 'price.name="min"'):
            self.assertIn(words, PRICE_BAR_SCRIPT)

    def test_a_page_whose_price_was_chosen_is_not_logged_as_a_new_search(self) -> None:
        self.assertIn("/[?&](shown|assist|min)=/.test(location.search)", _SEARCH_SCRIPT)

    def test_the_ai_layer_is_not_asked_again_for_a_price(self) -> None:
        # Its daily spend is capped: a page whose price was chosen reads the answer alone.
        with patch("picwise_app.app.assist_directory", return_value=Path("/nonexistent-assist")), \
                patch("picwise_app.app.resolve_with_assist", side_effect=AssertionError("asked")):
            page = _call("/search", {"q": "kettle", "min": "30"})
        self.assertEqual(len(_prices(page)), 4)


class ShortAnswerTests(_FeedMixin, unittest.TestCase):
    def test_an_answer_of_one_page_has_no_bar(self) -> None:
        self._serve(_kettles((8.0, 12.0, 40.0, 90.0)))
        page = _call("/search", {"q": "kettle"})
        self.assertEqual(len(_cards(page)), 4)
        self.assertEqual(_bar(page), "")

    def test_one_price_has_no_bar(self) -> None:
        self._serve(_kettles((20.0,) * 6))
        self.assertEqual(_bar(_call("/search", {"q": "kettle"})), "")

    def test_the_home_page_has_no_bar(self) -> None:
        self._serve(_kettles())
        self.assertNotIn("pw-pricebar", _call("/"))


class PreparedCatalogueTests(_PreparedMixin, unittest.TestCase):
    def test_the_server_s_prepared_catalogue_starts_from_the_chosen_price_too(self) -> None:
        # The server answers from the prepared catalogue (`prepared_catalogue`): the price
        # reaches its search as it reaches the feed's.
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        plain = _prices(_call("/search", {"q": "kettle"}))
        chosen = _prices(_call("/search", {"q": "kettle", "min": "40"}))
        self.assertTrue(any(price < 40 for price in plain), plain)
        self.assertTrue(chosen and all(price >= 40 for price in chosen), chosen)


class PartsTests(unittest.TestCase):
    def test_a_price_from_the_address(self) -> None:
        for value, expected in (("150", 150.0), ("149.99", 149.99), ("7.5", 7.5), (" 30 ", 30.0)):
            self.assertEqual(parse_min_price(value), expected, value)
        for value in ("", None, "0", "0.00", "-1", "1e3", "abc", "30.", ".5", "12.345", "１５", "1000001"):
            self.assertIsNone(parse_min_price(value), value)

    def test_the_steps_count_every_product_on_a_scale_of_ratios(self) -> None:
        prices = [2.0, 2.5, 3.0, 40.0, 45.0, 400.0]
        low, high, steps = _price_bar(prices)
        self.assertEqual((low, high), (2.0, 400.0))
        self.assertEqual(len(steps), PRICE_BAR_STEPS)
        self.assertEqual(sum(steps), len(prices))
        # The £2 straps fill the first steps, the £400 watch the last.
        self.assertEqual(steps[0], 1)
        self.assertEqual(steps[-1], 1)
        self.assertEqual(_price_bar([20.0, 20.0]), (20.0, 20.0, ()))
        self.assertEqual(_price_bar([]), (0.0, 0.0, ()))


if __name__ == "__main__":
    unittest.main()
