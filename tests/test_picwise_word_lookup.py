"""A search for words reads only the products carrying them (the debugging's server measure, 2026-11-08).

The measure found a search with a word the kind could not explain ("bth rugs", "laptop
bas", "pc fns") taking 8 to 9 s on the server's 597,270 products: the words search read
every product's text on every search. Each catalogue now has a word lookup, built once
(`search_selection._word_lookup`): each whole word of the products' titles, types and
brands with the places of the products carrying it. A search reads only the products
that may carry its words (`_places_carrying`), each then read as before, so the answers
are the same; and a search none of whose products carries every word is not run at all.
Pinned here on a catalogue of the test's own: the lookup, its forms and its letter case;
the same answers with and without it; and the early "Did you mean ...?".

Every product is local test data: fictional brands, `.invalid` addresses.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import search_selection as ss  # noqa: E402
from test_picwise_unsure_reading import _catalogue, _product  # noqa: E402

_PITS = "Home & Garden > Lawn & Garden > Outdoor Living > Outdoor Fireplaces & Fire Pits"
_POTS = "Office Supplies > Desk Pen Pots"
_FEED = "Animals & Pet Supplies > Horse Feed Lams"
_LAMPS = "Home & Garden > Lighting > Lamps"
_RUGS = "Home & Garden > Decor > Rugs"


def _wider() -> tuple:
    extra = []
    for i in range(1, 5):
        extra.append(_product(f"pit{i}", f"Testline Steel Fire Pit {i}0cm", _PITS, brand="Testline", price=f"{90 + i}.00"))
        extra.append(_product(f"pot{i}", "Sampleworks Metal Pen Pot - Black", _POTS, brand="Sampleworks", price=f"{1 + i}.50"))
        extra.append(_product(f"lam{i}", "Horsefix Anti Lam 15kg", _FEED, brand="Horsefix", price=f"{30 + i}.00"))
        extra.append(_product(f"lamp{i}", f"Fixturon LED Desk Lamp {i}", _LAMPS, price=f"{15 + i}.00"))
        extra.append(_product(f"rug{i}", f"Sampleworks Bath Rug {i}0x60cm Grey", _RUGS, brand="Sampleworks", price=f"{12 + i}.00"))
    return _catalogue() + tuple(extra)


def _answer(query: str, products: tuple) -> tuple:
    result = ss.select_provider_products_for_query(query, products, max_products=4)
    return (
        result.status,
        tuple(str(product.provider_product_id) for product in result.selected_products),
        tuple(result.unmatched_query_terms),
        tuple(result.reason_codes),
    )


class LookupTests(unittest.TestCase):
    def test_each_word_with_the_products_carrying_it_once_per_catalogue(self) -> None:
        fields = (
            {"title": "fixturon electric kettle 1.7l", "product_type": "kettles", "brand": "fixturon"},
            {"title": "Testline Bath RUG", "product_type": "Rugs", "brand": "Testline"},
        )
        lookup = ss._word_lookup(fields)
        self.assertIs(lookup, ss._word_lookup(fields))
        self.assertEqual(list(lookup["kettle"]), [0])
        self.assertEqual(list(lookup["fixturon"]), [0])
        # Case folded, as the filters read it (`re.IGNORECASE`).
        self.assertEqual(list(lookup["rug"]), [1])
        self.assertEqual(list(lookup["rugs"]), [1])
        # A number alone, or a word of one or two letters, is not kept: such a unit is
        # read in every product, as before.
        self.assertNotIn("7l", lookup)
        self.assertIsNone(ss._unit_words(ss._filter_units(("1.7l",), {})[0]))
        self.assertIsNone(ss._unit_words(ss._filter_units(("tv",), {})[0]))
        other = tuple(dict(row) for row in fields)
        self.assertIsNot(ss._word_lookup(other), lookup)

    def test_the_places_that_may_carry_every_word_with_its_forms(self) -> None:
        fields = (
            {"title": "sampleworks bath rug grey", "product_type": "rugs", "brand": "sampleworks"},
            {"title": "sampleworks bath mat", "product_type": "bath mats", "brand": "sampleworks"},
            {"title": "fixturon rugs runner", "product_type": "rugs", "brand": "fixturon"},
        )
        units = ss._filter_units(("bath", "rugs"), {})
        self.assertEqual(ss._places_carrying(units, fields), [0])
        self.assertEqual(ss._carrying_every(units, fields), [0])
        self.assertEqual(ss._places_carrying(ss._filter_units(("rug",), {}), fields), [0, 2])
        self.assertEqual(ss._places_carrying(ss._filter_units(("bth", "rugs"), {}), fields), [])
        # A count with its noun can be fused ("3seater"): it narrows nothing by itself.
        self.assertIsNone(ss._places_carrying(ss._filter_units(("3", "seater"), {}), fields))
        # "tv" narrows nothing; "rug" still does.
        self.assertEqual(ss._places_carrying(ss._filter_units(("tv", "rug"), {}), fields), [0, 2])


class SameAnswersTests(unittest.TestCase):
    QUERIES = (
        "tv stand", "fire pots", "desk lam", "laptop bgs", "lptop bag", "coffee grinder",
        "kettle", "small kettle", "brandex kettle", "laptop 8gb", "pen pot", "metal pen pot",
        "anti lam", "steel fire pit", "fire pit", "desk lamp", "bath rug", "bth rugs",
        "sampleworks", "used kettle", "grey bath rug", "fixturon laptop", "testline",
    )

    def test_the_same_answers_with_and_without_the_lookup(self) -> None:
        products = _wider()
        for query in self.QUERIES:
            with self.subTest(query=query):
                looked_up = _answer(query, products)
                with mock.patch.object(ss, "_places_carrying", lambda units, fields: None):
                    read_all = _answer(query, products)
                self.assertEqual(looked_up, read_all)

    def test_no_product_carrying_every_word_asks_without_the_words_search(self) -> None:
        products = _wider()
        with mock.patch.object(ss, "_select_products_by_words", wraps=ss._select_products_by_words) as words:
            result = ss.select_provider_products_for_query("bth rugs", products, max_products=4)
        self.assertEqual(result.status, "unsure_reading")
        self.assertEqual(result.selected_products, ())
        words.assert_not_called()


if __name__ == "__main__":
    unittest.main()
