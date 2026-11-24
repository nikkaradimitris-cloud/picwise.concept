"""The price bar above the cards (owner, 2026-11-12).

«Να μπει ένα φίλτρο με τη μορφή μπάρας που να διαλέγει με την τιμή για να γλιτώσουμε το
πρόβλημα που βγάζει τα φθηνότερα και μπορεί να είναι smartwatch και να δείχνει λουράκια
μπορεί να είναι tablet και να βγάζει πρώτα θήκες ... βάζοντας ένα φίλτρο τιμής το οποίο να
τερματίζει στην υψηλοτερή και να ξεκινάει από την χαμηλότερη κουνώντας μία μπίλια θα μπορεί
αμέσως να φιλτράρει και να ανεβαίνει πιο πάνω στην τιμή».

The bar runs from the answer's lowest price to its highest; the price chosen on it starts
the answer from that price: offers first, then cheapest first, "More" and the counter hold
for the products from it, and there is no Recommended (owner, the same day: «Το recommendit
πρέπει να ακιρονετε όταν χρησιμοποιεί φίλτρο...σε άλλη περίπτωση δείχνει την μέση τιμή
παράδειγμα ο Χρίστης επιλέγει από 90 ευρώ και αυτό προτείνει 890»).
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
        self.assertIn('<output class="pw-pricebar-value" id="pw-pricebar-value" for="pw-pricebar-range pw-pricebar-range-max">Any price</output>', bar)
        # The second knob stands at the dearest price: nothing chosen.
        self.assertIn('name="max" min="8" max="120" step="1" value="120"', bar)
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
        # Eight kettles from £30, the cheapest first; the counter and the heading say so.
        self.assertEqual(prices, [34.0, 39.0, 45.0, 52.0])
        self.assertIn('<p class="pw-results-count">4 of 8</p>', page)
        self.assertEqual(_heading(page), "Results for: kettle, from £30, cheapest first")
        self.assertIn(">From £30</output>", _bar(page))
        # The bar is still the whole answer's: the buyer can move back down.
        self.assertIn('data-low="8.00" data-high="120.00"', _bar(page))
        # The steps below the price chosen are pale.
        self.assertIn('class="out"', _bar(page))

    def test_a_chosen_price_has_no_recommended(self) -> None:
        # Owner, 2026-11-12: from £90 the middle of the prices had been a product of £890.
        page = _call("/search", {"q": "kettle", "min": "30"})
        grid = re.search(r'<section class="pw-grid".*?</section>', page, re.S).group(0)
        self.assertNotIn("pw-card-recommended", grid)
        self.assertNotIn("Recommended", _text(grid))
        # The line above the cards says only whose prices they are.
        disclaimer = re.search(r'<p class="pw-reference-disclaimer">(.*?)</p>', page, re.S).group(1)
        self.assertEqual(_text(disclaimer), "Prices and stock are as the shops list them.")
        # Every click to a shop is counted as no Recommended's.
        self.assertNotIn("rec=1", grid)
        self.assertEqual(grid.count("rec=0"), 4)
        # Without a price the Recommended is as it was.
        plain = _call("/search", {"q": "kettle"})
        self.assertIn("pw-card-recommended", re.search(r'<section class="pw-grid".*?</section>', plain, re.S).group(0))

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
        self.assertIn('type="range" name="max"', bar)
        for words in ('range.addEventListener("change"', 'top.addEventListener("change"', "form.submit()",
                      'scan.hidden=false', 'range.removeAttribute("name")', 'top.removeAttribute("name")',
                      'hidden("min")', 'hidden("max")'):
            self.assertIn(words, PRICE_BAR_SCRIPT)

    def test_a_page_whose_price_was_chosen_is_not_logged_as_a_new_search(self) -> None:
        self.assertIn("/[?&](shown|assist|min|max)=/.test(location.search)", _SEARCH_SCRIPT)

    def test_the_ai_layer_is_not_asked_again_for_a_price(self) -> None:
        # Its daily spend is capped: a page whose price was chosen reads the answer alone.
        with patch("picwise_app.app.assist_directory", return_value=Path("/nonexistent-assist")), \
                patch("picwise_app.app.resolve_with_assist", side_effect=AssertionError("asked")):
            page = _call("/search", {"q": "kettle", "min": "30"})
        self.assertEqual(len(_prices(page)), 4)


class PriceToTests(_FeedMixin, unittest.TestCase):
    """The second knob: the answer ends at a price (owner, 2026-11-15: «Ο χρήστης μπορεί να
    διαλέξει στο φίλτρο τιμής από έως»)."""

    def setUp(self) -> None:
        self._serve(_kettles())

    def test_a_chosen_end_leaves_out_what_costs_more(self) -> None:
        page = _call("/search", {"q": "kettle", "max": "40"})
        self.assertEqual(_prices(page), [8.0, 9.0, 11.0, 12.0])
        self.assertIn('<p class="pw-results-count">4 of 6</p>', page)
        self.assertEqual(_heading(page), "Results for: kettle, up to £40, cheapest first")
        self.assertIn(">Up to £40</output>", _bar(page))
        opened = _call("/search", {"q": "kettle", "max": "40", "shown": "8"})
        self.assertEqual(_prices(opened), [8.0, 9.0, 11.0, 12.0, 34.0, 39.0])
        # The bar is still the whole answer's, and the steps above the price are pale.
        self.assertIn('data-low="8.00" data-high="120.00"', _bar(page))
        self.assertIn('name="max" min="8" max="120" step="1" value="40"', _bar(page))
        self.assertIn('class="out"', _bar(page))

    def test_from_and_to_together(self) -> None:
        page = _call("/search", {"q": "kettle", "min": "30", "max": "60"})
        self.assertEqual(_prices(page), [34.0, 39.0, 45.0, 52.0])
        self.assertIn('<p class="pw-results-count">4 of 5</p>', page)
        self.assertEqual(_heading(page), "Results for: kettle, £30 – £60, cheapest first")
        more = html.unescape(re.search(r'<a class="pw-more-button" href="([^"]+)"', page).group(1))
        self.assertEqual(more, "/search?q=kettle&min=30&max=60&shown=8#pw-choice-5")
        self.assertEqual(_prices(_call("/search", {"q": "kettle", "min": "30", "max": "60", "shown": "8"})),
                         [34.0, 39.0, 45.0, 52.0, 60.0])

    def test_a_chosen_end_has_no_recommended(self) -> None:
        page = _call("/search", {"q": "kettle", "max": "60"})
        grid = re.search(r'<section class="pw-grid".*?</section>', page, re.S).group(0)
        self.assertNotIn("pw-card-recommended", grid)
        self.assertNotIn("rec=1", grid)

    def test_an_end_under_the_start_never_empties_the_answer(self) -> None:
        self.assertEqual(_prices(_call("/search", {"q": "kettle", "min": "50", "max": "20"})), [52.0])
        self.assertEqual(_prices(_call("/search", {"q": "kettle", "max": "2"})), [8.0])

    def test_an_end_at_or_above_the_dearest_chooses_nothing(self) -> None:
        plain = _prices(_call("/search", {"q": "kettle"}))
        for value in ("120", "500", "abc", "0"):
            page = _call("/search", {"q": "kettle", "max": value})
            self.assertEqual(_prices(page), plain, value)
            self.assertIn(">Any price</output>", _bar(page), value)


class SixDecimalPriceTests(_FeedMixin, unittest.TestCase):
    """A shop that writes its prices with six decimals (owner, 2026-11-24: «το φίλτρο τιμής
    δεν δουλεύει σωστά σε κάποιες κατηγορίες»; GamingKit's "269.448001", shown £269.45, stood
    at £269,448,001: the bar ran to billions, the product left every range and came last)."""

    def setUp(self) -> None:
        rows = _kettles()
        rows[6]["price"] = "45.448001"
        self._serve(rows)

    def test_the_bar_ends_at_the_dearest_real_price(self) -> None:
        self.assertIn('data-low="8.00" data-high="120.00"', _bar(_call("/search", {"q": "kettle"})))

    def test_the_product_stands_at_its_price_in_the_order_and_in_a_range(self) -> None:
        self.assertEqual(_prices(_call("/search", {"q": "kettle", "min": "40", "max": "50"})), [45.45])
        self.assertEqual(_prices(_call("/search", {"q": "kettle", "min": "30", "shown": "8"})),
                         [34.0, 39.0, 45.45, 52.0, 60.0, 74.0, 89.0, 120.0])


class FarDearerTests(_FeedMixin, unittest.TestCase):
    """A product priced far above the rest of its answer is left out (owner, 2026-11-24: «Ναι»,
    of GamingKit's 24" monitor at £1,281,010.87, which ran the bar of "monitor" to a million):
    forty times the next dearest (the owner's number, the same day), in an answer of twenty products or more."""

    _TWENTY = tuple(float(8 + 4 * index) for index in range(20))

    def test_a_price_forty_times_the_next_dearest_is_left_out(self) -> None:
        rows = _kettles(self._TWENTY + (1281010.87,))
        self._serve(rows)
        page = _call("/search", {"q": "kettle", "shown": "24"})
        self.assertIn('data-low="8.00" data-high="84.00"', _bar(page))
        self.assertNotIn(1281010.87, _prices(page))
        self.assertIn('<p class="pw-results-count">20 of 20</p>', page)

    def test_a_dear_product_within_forty_times_stays(self) -> None:
        self._serve(_kettles(self._TWENTY + (3300.0,)))
        self.assertIn('data-high="3300.00"', _bar(_call("/search", {"q": "kettle"})))

    def test_a_short_answer_keeps_its_dearest(self) -> None:
        # Measured 24/11: a handmade £880 knife among 8 knife sets is a real product.
        self._serve(_kettles((8.0, 9.0, 11.0, 12.0, 14.0, 15.0, 17.0, 880.0)))
        self.assertIn(880.0, _prices(_call("/search", {"q": "kettle", "shown": "8"})))


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
