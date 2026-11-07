"""A word the kind cannot explain: "Did you mean ...?", never the kind's products (owner, 2026-11-07).

The debugging's first measure found searches answered with another product because one
of their words was dropped: "laptop bgs" with laptops, "tv stand" with televisions,
"coffee grinder" with angle grinders, "gme table" with tables. Asked «Όταν η μηχανή δεν
είναι σίγουρη, να δείχνει «Μήπως εννοείτε…;» αντί να μαντεύει;», the owner answered «Ναι σε
όλα». Pinned here (`search_selection._unexplained_words`, `_unsure_reading_selection`;
`live_search_resolver`), on a catalogue of the test's own:

- a word after the kind's name that no product of the kind carries renames it: the
  answer is the products all the words name ("tv stand": the stands), else nothing;
- a word before the name is a need ("small", "quiet"), unless it is a slip, a word of
  another kind's name ("coffee grinder") or, with the name, close to another kind's;
- a brand of the catalogue, a word that describes, a number, what the product is for:
  the kind's products as before, the page saying which word it could not match;
- on the page: no product, no "Understood as", and "Did you mean: laptop bag?".

Every product is local test data: fictional brands, `.invalid` addresses.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.search_selection import select_provider_products_for_query  # noqa: E402

FIXTURE_FEED = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"


def _product(pid: str, title: str, category: str, *, brand: str = "Fixturon", price: str = "50.00") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand=brand,
        category_text=category,
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in stock",
        currency="GBP",
        raw={"product_type": category, "merchant_product_category_path": category, "brand_name": brand},
    )


_LAPTOPS = "Electronics > Computers > Laptops"
_BAGS = "Luggage & Bags > Laptop Bags"
_TVS = "Electronics > Video > Televisions"
_STANDS = "Furniture > Entertainment Centers & TV Stands"
_KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"
_GRINDERS = "Hardware > Tools > Grinders"
_COFFEE = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Coffee Grinders"
_SHAVERS = "Health & Beauty > Personal Care > Shaving & Grooming > Electric Razors"


def _catalogue() -> tuple[ProviderProduct, ...]:
    rows = []
    for i in range(1, 5):
        rows.append(_product(f"lap{i}", f"Fixturon Book {i}4 Laptop 8GB RAM", _LAPTOPS, price=f"{300 + i * 50}.00"))
        rows.append(_product(f"bag{i}", f"Testline Laptop Bag {i}5 inch", _BAGS, brand="Testline", price=f"{20 + i}.00"))
        rows.append(_product(f"tv{i}", f"Fixturon {i}0 inch 4K Television", _TVS, price=f"{200 + i * 40}.00"))
        rows.append(_product(f"stand{i}", f"Sampleworks TV Stand {i}20cm Oak", _STANDS, brand="Sampleworks", price=f"{60 + i}.00"))
        rows.append(_product(f"ket{i}", f"Fixturon Electric Kettle 1.{i}L Black", _KETTLES, price=f"{20 + i}.00"))
        rows.append(_product(f"ag{i}", f"Testline Angle Grinder 1{i}5mm", _GRINDERS, brand="Testline", price=f"{40 + i}.00"))
        rows.append(_product(f"cg{i}", f"Sampleworks Electric Coffee Grinder {i}", _COFFEE, brand="Sampleworks", price=f"{25 + i}.00"))
        # A brand with no kettle: asked for, the kettles are shown and the brand is said unmatched.
        rows.append(_product(f"sh{i}", f"Brandex Electric Shaver Series {i}", _SHAVERS, brand="Brandex", price=f"{70 + i}.00"))
    return tuple(rows)


def _select(query: str):
    return select_provider_products_for_query(query, _catalogue(), max_products=4)


def _ids(result) -> set[str]:
    return {str(product.provider_product_id) for product in result.selected_products}


class SelectionTests(unittest.TestCase):
    def test_a_slip_after_the_name_is_asked_about_never_answered_with_the_kind(self) -> None:
        result = _select("laptop bgs")
        self.assertEqual(result.status, "unsure_reading")
        self.assertEqual(result.selected_products, ())
        self.assertEqual(result.unmatched_query_terms, ("bgs",))

    def test_a_word_after_the_name_renames_the_product(self) -> None:
        result = _select("tv stand")
        self.assertTrue(result.selected_products)
        self.assertTrue(all(pid.startswith("stand") for pid in _ids(result)), _ids(result))

    def test_a_word_of_another_kinds_name_before_it(self) -> None:
        result = _select("coffee grinder")
        self.assertFalse(any(pid.startswith("ag") for pid in _ids(result)), _ids(result))
        if result.selected_products:
            self.assertTrue(all(pid.startswith("cg") for pid in _ids(result)), _ids(result))

    def test_a_slip_before_the_name(self) -> None:
        result = _select("lptop bag")
        self.assertFalse(any(pid.startswith("lap") for pid in _ids(result)), _ids(result))

    def test_words_that_describe_or_need_keep_the_kind(self) -> None:
        for query in ("small kettle", "quiet kettle", "kettle black", "kettle for camping", "kettle 1.5l"):
            result = _select(query)
            self.assertNotEqual(result.status, "unsure_reading", query)
            self.assertTrue(result.selected_products, query)
            self.assertTrue(all(pid.startswith("ket") for pid in _ids(result)), (query, _ids(result)))

    def test_a_brand_of_the_catalogue_keeps_the_kind_and_is_said_unmatched(self) -> None:
        result = _select("brandex kettle")
        self.assertNotEqual(result.status, "unsure_reading")
        self.assertTrue(all(pid.startswith("ket") for pid in _ids(result)), _ids(result))
        self.assertIn("brandex", result.unmatched_query_terms)

    def test_a_words_answer_that_drops_a_word_is_no_answer(self) -> None:
        # The debugging's server measure (2026-11-07): "fire pots" was answered with pen
        # pots and "desk lam" with a horse feed, the words search having dropped "fire"
        # and "desk". Every word, or "Did you mean ...?".
        pits = "Home & Garden > Lawn & Garden > Outdoor Living > Outdoor Fireplaces & Fire Pits"
        pots = "Office Supplies > Desk Pen Pots"
        feed = "Animals & Pet Supplies > Horse Feed Lams"
        lamps = "Home & Garden > Lighting > Lamps"
        extra = []
        for i in range(1, 5):
            extra.append(_product(f"pit{i}", f"Testline Steel Fire Pit {i}0cm", pits, brand="Testline", price=f"{90 + i}.00"))
            extra.append(_product(f"pot{i}", "Sampleworks Metal Pen Pot - Black", pots, brand="Sampleworks", price=f"{1 + i}.50"))
            extra.append(_product(f"lam{i}", "Horsefix Anti Lam 15kg", feed, brand="Horsefix", price=f"{30 + i}.00"))
            extra.append(_product(f"lamp{i}", f"Fixturon LED Desk Lamp {i}", lamps, price=f"{15 + i}.00"))
        catalogue = _catalogue() + tuple(extra)
        for query in ("fire pots", "desk lam"):
            result = select_provider_products_for_query(query, catalogue, max_products=4)
            self.assertEqual(result.status, "unsure_reading", query)
            self.assertEqual(result.selected_products, (), query)
        for query, prefix in (("fire pit", "pit"), ("desk lamp", "lamp"), ("tv stand", "stand")):
            result = select_provider_products_for_query(query, catalogue, max_products=4)
            self.assertTrue(result.selected_products, query)
            self.assertTrue(all(pid.startswith(prefix) for pid in _ids(result)), (query, _ids(result)))

    def test_a_word_the_kinds_products_carry_is_a_filter_as_before(self) -> None:
        result = _select("laptop 8gb")
        self.assertTrue(result.selected_products)
        self.assertTrue(all(pid.startswith("lap") for pid in _ids(result)))


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

    def test_the_page_asks_did_you_mean_and_shows_nothing(self) -> None:
        from picwise_search.live_search_resolver import resolve_live_search

        for query, meant in (("laptop bgs", "laptop bag"), ("gme table", "game table"), ("hat pump", "heat pump")):
            resolution = resolve_live_search(query)
            self.assertEqual(resolution.provider_feed_selected_products, (), query)
            self.assertIn("unsure_reading", resolution.reason_codes, query)
            self.assertEqual(resolution.resolver_state, "not_understood", query)
            self.assertIsNone(resolution.understood_concept_id, query)
            self.assertIn(meant, resolution.did_you_mean, query)

    def test_a_search_for_the_kind_is_answered_as_before(self) -> None:
        from picwise_search.live_search_resolver import resolve_live_search

        resolution = resolve_live_search("laptop")
        self.assertTrue(resolution.provider_feed_selected_products)
        self.assertNotIn("unsure_reading", resolution.reason_codes)
        self.assertEqual(resolution.understood_concept_id, "laptop")


if __name__ == "__main__":
    unittest.main()
