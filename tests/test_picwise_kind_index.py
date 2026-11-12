"""A search for a kind reads only the products that may be of it (the audit, 2026-11-10).

The audit measured every search for a kind reading every product of the catalogue to
find the kind's own: 0.85 to 1.2 s on the live site's 242,817 products, 0.07 s on 108
(`search_selection._select_products_for_concept`, `members_for`). Each catalogue now has
a kind index, built once (`search_selection._kind_index`): the places of the products of
each kind, and, for the products no kind was read for, the places carrying each whole
word of their title and type. A search reads the kind's products and the products with
no kind that may name it, each judged as before, so the answers are the same. Pinned
here on a catalogue of the test's own: the index; the same answers with it and reading
every product; a product with no kind still found by the words of its title; and the
index dropped when the kinds are read anew.

Every product is local test data: fictional brands, `.invalid` addresses.
"""
from __future__ import annotations

import re
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
from test_picwise_unsure_reading import _KETTLES, _product  # noqa: E402
from test_picwise_word_lookup import _wider  # noqa: E402

_DECOR = "Home & Garden > Decor"


def _products() -> tuple:
    """The wider catalogue of the words tests, with products no kind is read for."""
    extra = [
        _product(f"gift{i}", f"Sampleworks Giftware Piece {i} in Blue", _DECOR, brand="Sampleworks", price=f"{5 + i}.00")
        for i in range(1, 7)
    ]
    return _wider() + tuple(extra)


def _read_every_product(index: ss._KindIndex, _concept_id: str, _feed_terms: tuple[str, ...]) -> range:
    """As before the index: every product of the catalogue is judged."""
    return range(index.size)


def _answer(query: str, products: tuple, catalogue: ss.SearchCatalogue | None = None, *, shown: int = 0) -> tuple:
    result = ss.select_provider_products_for_query(
        query, products, max_products=4, catalogue=catalogue, shown=shown
    )
    return (
        result.status,
        tuple(str(product.provider_product_id) for product in result.selected_products),
        tuple(str(product.provider_product_id) for product in result.more_products),
        result.total_count,
        result.recommended_product_id,
        result.understood_concept,
        tuple(result.unmatched_query_terms),
        tuple(result.reason_codes),
    )


class KindIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(ss.remember_product_kinds, {})

    def test_each_kind_with_its_products_once_per_catalogue(self) -> None:
        catalogue = ss.build_search_catalogue(_products())
        products, fields = catalogue.new_products, catalogue.new_fields
        index = ss._kind_index(products, fields)
        self.assertIs(index, ss._kind_index(products, fields))
        self.assertEqual(index.size, len(products))
        kinds = [ss._product_concepts(product, row) for product, row in zip(products, fields)]
        self.assertEqual(
            list(index.by_kind["kettle"]), [place for place, kind in enumerate(kinds) if "kettle" in kind]
        )
        self.assertTrue(index.by_kind["kettle"])
        self.assertEqual(list(index.no_kind), [place for place, kind in enumerate(kinds) if not kind])
        self.assertEqual(len(index.no_kind), 6)
        # Each whole word of a product with no kind, case folded, with its places; not a
        # number alone nor a single letter.
        self.assertEqual(list(index.no_kind_words["giftware"]), list(index.no_kind))
        self.assertEqual(list(index.no_kind_words["in"]), list(index.no_kind))
        self.assertNotIn("1", index.no_kind_words)
        self.assertNotIn("fixturon", index.no_kind_words)
        # Another catalogue has an index of its own.
        other = ss.build_search_catalogue(_products())
        self.assertIsNot(ss._kind_index(other.new_products, other.new_fields), index)

    def test_only_the_products_that_may_be_of_the_kind_are_read(self) -> None:
        catalogue = ss.build_search_catalogue(_products())
        index = ss._kind_index(catalogue.new_products, catalogue.new_fields)
        places = list(ss._kind_member_places(index, "kettle", ("kettle",)))
        self.assertEqual(places, list(index.by_kind["kettle"]))
        self.assertLess(len(places), index.size)
        # A name no product with no kind carries reads none of them; no name, none either.
        self.assertEqual(list(ss._no_kind_places_naming(index, ("kettle",))), [])
        self.assertEqual(list(ss._kind_member_places(index, "kettle", ())), list(index.by_kind["kettle"]))
        # A name that cannot be looked up (a single letter, a number) reads them all.
        self.assertEqual(list(ss._no_kind_places_naming(index, ("7",))), list(index.no_kind))
        # Every word of every name must be carried.
        self.assertEqual(list(ss._no_kind_places_naming(index, ("giftware piece",))), list(index.no_kind))
        self.assertEqual(list(ss._no_kind_places_naming(index, ("giftware", "kettle"))), [])

    def test_a_word_is_looked_up_as_a_pattern_without_regard_to_case_finds_it(self) -> None:
        # "i" matches "İ" and "ı" in such a pattern; case folding alone keeps them apart.
        for title in ("Silver RİNG", "silver rıng", "SILVER RING", "Silver Ring"):
            with self.subTest(title=title):
                self.assertIsNotNone(re.search(r"\bring\b", title, flags=re.IGNORECASE))
                self.assertIn("ring", ss._index_words(title))
        self.assertTrue(ss._kind_index_word("tv"))
        self.assertFalse(ss._kind_index_word("7"))
        self.assertFalse(ss._kind_index_word("l"))


class SameAnswersTests(unittest.TestCase):
    QUERIES = (
        "kettle", "small kettle", "brandex kettle", "electric kettle black", "used kettle",
        "laptop", "laptop 8gb", "fixturon laptop", "laptop bag", "laptop bgs", "lptop bag",
        "tv", "television", "tv stand", "4k television", "coffee grinder", "angle grinder",
        "fire pit", "steel fire pit", "fire pots", "pen pot", "desk lamp", "desk lam",
        "bath rug", "grey bath rug", "bth rugs", "giftware", "giftware piece", "blue giftware",
        "sampleworks", "testline", "washing machine", "ring", "xyzzy",
    )

    def setUp(self) -> None:
        self.addCleanup(ss.remember_product_kinds, {})

    def test_the_same_answers_with_the_index_and_reading_every_product(self) -> None:
        products = _products()
        for query in self.QUERIES:
            for shown in (0, 8):
                with self.subTest(query=query, shown=shown):
                    indexed = _answer(query, products, shown=shown)
                    with mock.patch.object(ss, "_kind_member_places", _read_every_product):
                        read_all = _answer(query, products, shown=shown)
                    self.assertEqual(indexed, read_all)

    def test_a_product_with_no_kind_is_still_found_by_the_words_of_its_title(self) -> None:
        # Two kettles whose kinds a prepared file gives as none: found by their own words
        # (`_unannotated_product_names_concept`), with the index as when every product
        # was read.
        products = _products() + (
            _product("plain1", "Sampleworks Whistling Kettle 2L", _DECOR, brand="Sampleworks", price="9.00"),
            _product("plain2", "Sampleworks Travel KETTLE 0.5L", _DECOR, brand="Sampleworks", price="8.00"),
        )
        catalogue = ss.build_search_catalogue(products)
        fields = dict(zip((str(p.provider_product_id) for p in catalogue.new_products), catalogue.new_fields))
        by_id = {str(p.provider_product_id): p for p in catalogue.new_products}
        ss.remember_product_kinds(
            {ss.product_kind_key(by_id[pid], fields[pid]): frozenset() for pid in ("plain1", "plain2")}
        )
        index = ss._kind_index(catalogue.new_products, catalogue.new_fields)
        named = list(ss._no_kind_places_naming(index, ("kettle",)))
        self.assertEqual(
            [str(catalogue.new_products[place].provider_product_id) for place in named], ["plain1", "plain2"]
        )
        indexed = _answer("kettle", products, catalogue)
        with mock.patch.object(ss, "_kind_member_places", _read_every_product):
            read_all = _answer("kettle", products, catalogue)
        self.assertEqual(indexed, read_all)
        # The four kettles of the catalogue and these two; the two cheapest are these.
        self.assertEqual(indexed[3], 6)
        self.assertIn("plain2", indexed[1])
        self.assertIn("plain1", indexed[1])

    def test_kinds_read_anew_drop_the_index(self) -> None:
        catalogue = ss.build_search_catalogue(_products())
        products, fields = catalogue.new_products, catalogue.new_fields
        index = ss._kind_index(products, fields)
        place = next(iter(index.by_kind["kettle"]))
        ss.remember_product_kinds({ss.product_kind_key(products[place], fields[place]): frozenset()})
        again = ss._kind_index(products, fields)
        self.assertIsNot(again, index)
        self.assertNotIn(place, list(again.by_kind["kettle"]))
        self.assertIn(place, list(again.no_kind))


if __name__ == "__main__":
    unittest.main()
