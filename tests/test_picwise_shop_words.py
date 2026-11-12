"""The shops' own words for a kind, learned by review (`picwise_providers.shop_words`;
the owner, 12/11: «να μαθαίνει νέες λέξεις από τα καταστήματα», then «Ναι, προχώρα με
όλα»).

Pinned here:

- every learned type names a kind PicWise has;
- a learned type names its kind for the shop it was learned in, whatever its case and
  spaces, and only there: the same type and title from another shop stay as the
  lexicon reads them;
- each night's note lists the shops' own types of the products kept with no kind, the
  most first, with their shop, count and two titles; a product with a kind, or with no
  type, is not listed; the server's report prints the list.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_nlu.concept_understanding import annotate_product_concepts  # noqa: E402
from picwise_nlu.product_concepts import get_product_concepts_by_id  # noqa: E402
from picwise_providers.catalogue_balance import measure_catalogue_balance  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.search_selection import _product_concepts, _product_search_fields  # noqa: E402
from picwise_providers.shop_words import LEARNED_TYPES, learned_kind  # noqa: E402

# A title the lexicon reads as no kind: "ring" alone never classifies a feed row.
_TITLE = "Fixturon 18ct White Gold 1ct Diamond Solitaire Ring"


def _product(pid: str, shop: str, product_type: str, title: str = _TITLE) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=title, brand="Fixturon",
        category_text=product_type, product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg", price_text="99.00",
        availability_text="in stock", currency="GBP",
        raw={"merchant_name": shop, "product_type": product_type},
    )


def _kinds(product: ProviderProduct) -> frozenset[str]:
    return _product_concepts(product, _product_search_fields(product))


class LearnedTypesTests(unittest.TestCase):
    def test_every_learned_type_names_a_kind_picwise_has(self) -> None:
        kinds = get_product_concepts_by_id()
        self.assertTrue(LEARNED_TYPES)
        for (shop, product_type), kind in LEARNED_TYPES.items():
            with self.subTest(shop=shop, product_type=product_type):
                self.assertIn(kind, kinds)
                self.assertTrue(product_type.strip())

    def test_a_learned_type_names_its_kind_in_its_shop_and_only_there(self) -> None:
        # Without the table, the lexicon reads nothing here.
        self.assertEqual(
            {kind for kind in annotate_product_concepts("Diamond Ring", "Diamond Ring", _TITLE) if not kind.startswith("__")},
            set(),
        )
        self.assertEqual(_kinds(_product("a", "Finediam", "Diamond Ring")), frozenset({"ring"}))
        self.assertEqual(_kinds(_product("b", "  finediam ", "  diamond   RING ")), frozenset({"ring"}))
        self.assertEqual(learned_kind({"merchant_name": "Fixture Other Shop"}, "Diamond Ring"), "")
        self.assertEqual(
            {kind for kind in _kinds(_product("c", "Fixture Other Shop", "Diamond Ring")) if not kind.startswith("__")},
            set(),
        )
        self.assertEqual(learned_kind({"merchant_name": "Finediam"}, ""), "")


class ShopCatalogueBotTests(unittest.TestCase):
    """The rows the shops' catalogue bot gives a type are rows held for no category: a
    learned type gives them their kind there too (`shop_catalogue._has_kind`)."""

    def test_a_learned_type_from_the_bot_gives_the_row_its_kind(self) -> None:
        from picwise_providers.shop_catalogue import _has_kind, _with_category

        finediam = _with_category(_product("r1", "Finediam", ""), "Diamond Ring", "Diamond Ring")
        self.assertTrue(_has_kind(finediam))
        other = _with_category(_product("r2", "Fixture Other Shop", ""), "Diamond Ring", "Diamond Ring")
        self.assertFalse(_has_kind(other))


class WordsToLearnTests(unittest.TestCase):
    def _words(self) -> list[dict]:
        products = [
            _product("p1", "Fixture Shop One", "Tablet Security Enclosures", "Fixturon Kiosk Enclosure 1"),
            _product("p2", "Fixture Shop One", "Tablet Security Enclosures", "Fixturon Kiosk Enclosure 2"),
            _product("p3", "Fixture Shop One", "Tablet Security Enclosures", "Fixturon Kiosk Enclosure 3"),
            _product("p4", "Fixture Shop Two", "Brooches", "Fixturon Silver Brooch"),
            _product("p4b", "Fixture Shop Two", "Brooches", "Fixturon Gold Brooch"),
            # One product's own description, not a shop's word: not listed.
            _product("p7", "Fixture Shop Three", "Lenses > Fixturon 50mm f/1.8 Lens", "Fixturon 50mm Lens"),
            _product("p5", "Fixture Shop Two", "Laptops", "Fixturon Laptop 15"),
            _product("p6", "Fixture Shop Two", "", "Fixturon Mystery Thing"),
        ]
        kinds = [frozenset(), frozenset({"__accessory__"}), frozenset(), frozenset({"__uncertain_kind__"}),
                 frozenset(), frozenset(), frozenset({"laptop"}), frozenset()]
        return measure_catalogue_balance(products, kinds)["words_to_learn"]

    def test_the_night_lists_the_types_of_the_products_kept_with_no_kind(self) -> None:
        self.assertEqual(
            self._words(),
            [
                {"shop": "Fixture Shop One", "type": "Tablet Security Enclosures", "products": 3,
                 "titles": ["Fixturon Kiosk Enclosure 1", "Fixturon Kiosk Enclosure 2"]},
                {"shop": "Fixture Shop Two", "type": "Brooches", "products": 2,
                 "titles": ["Fixturon Silver Brooch", "Fixturon Gold Brooch"]},
            ],
        )

    def test_the_servers_report_prints_them(self) -> None:
        view = {"groups": 1, "products": 1, "largest": [{"name": "x", "products": 1, "share": 1.0}], "over": 0,
                "cap": None, "kept": None, "cut": None, "cut_by_group": []}
        note = {
            "prepared": True,
            "intake": {"rows": 1, "shown": 1, "not_new": 0, "held": 0, "shops": []},
            "balance": {"share": 0.15, "products": 1, "department": view, "aisle": view, "shop": view, "kind": view,
                        "no_kind": 0, "kinds_by_shops": {"kinds": 0, "one_shop": 0, "two_shops": 0, "three_or_more": 0},
                        "kinds_from_few_shops": [], "words_to_learn": self._words()},
        }
        report = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "print_shops.py")],
            input=json.dumps(note), capture_output=True, text=True, check=True,
        ).stdout
        self.assertIn(
            "  the shops' own types of the products kept with no kind, to review (shop_words.py), the most first: "
            "Tablet Security Enclosures (Fixture Shop One) 3; Brooches (Fixture Shop Two) 2",
            report,
        )


if __name__ == "__main__":
    unittest.main()
