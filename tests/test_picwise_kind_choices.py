"""The choices a search for a general word could offer, from the catalogue itself.

Owner, 2026-10-28: «Το search όταν του βάζεις καλώδιο πρέπει να συμπληρώνει προτάσεις τι
καλώδιο ζητάει ... το ίδιο με όλες αυτές τις γενικές λέξεις»; 2026-10-29: one logic for all
of them, never word by word (`picwise_providers.kind_choices`, measured only).

Pinned here: a kind's products are grouped by the words their titles name it with (the
word right before the noun of its name and that noun, as written: "sofa bed" under
sofas, a hyphenated word whole: "zip-up hoodie"), by their narrower kinds and by their
shelves; a group is a choice from a number of products, whatever share of the kind it
is; a kind is general with two choices of one way; a word before the nouns of many kinds
("black") is no choice, and neither is a number, the product's brand or a connective; a
kind of too few products is not read; accessories and doubtful products count for no
kind. And what a search offers (`build_kind_choices`, owner 2026-10-29: «εσύ πρέπει να
αποφασίσεις ποιος είναι ο βέλτιστος τρόπος»), each rule on its own: a choice by the
words is named so by two shops or more, or its word is one another shop uses too
("thermal socks" of one shop, "thermal gloves" of another), and one shop's own word is
none ("robertson suit"); a word that is half of a phrase is read whole ("3 piece suit",
"slim fit suit"), a word many titles name with other words before it is not ("dining
chair"); no choice keeps 90% of its kind ("extension cable"); the noun as the titles
write it ("bootcut jeans", which the search reads, not "bootcut jean", which it does
not); no two choices searched the same ("cross pendant", "cross necklace"). Every row is
local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_nlu.concept_understanding import ACCESSORY_MARKER  # noqa: E402
from picwise_providers import kind_choices  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

CABLES = "Electronics > Electronics Accessories > Cables"


def _product(number: int, title: str, *, category: str = "", brand: str = "Fictbrand") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand=brand,
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text="9.99",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": "Fictional Store"},
    )


def _two_shops(
    rows: list[tuple[str, str, set[str]]], one_shop: tuple[str, ...] = (), other_shop: tuple[str, ...] = ()
) -> list[ProviderProduct]:
    """The rows as products of two shops, turn about; titles starting with one of
    `one_shop` all of the first shop, with one of `other_shop` all of the second."""
    products = []
    for number, (title, category, _kinds) in enumerate(rows):
        product = _product(number, title, category=category, brand="Fixturon")
        if title.startswith(one_shop or ("\0",)):
            shop = "Fictional Store One"
        elif title.startswith(other_shop or ("\0",)):
            shop = "Fictional Store Two"
        else:
            shop = "Fictional Store One" if number % 2 else "Fictional Store Two"
        products.append(replace(product, raw={"merchant_name": shop}))
    return products


def _measure(rows: list[tuple[str, str, set[str]]], brand: str = "Fictbrand") -> kind_choices.ChoicesMeasure:
    products = [_product(number, title, category=category, brand=brand) for number, (title, category, _kinds) in enumerate(rows)]
    return kind_choices.measure_kind_choices(products, [kinds for _title, _category, kinds in rows])


def _entry(measure: kind_choices.ChoicesMeasure, kind: str) -> kind_choices.KindChoices:
    return next(entry for entry in measure.kinds if entry.kind == kind)


class KindChoicesTests(unittest.TestCase):
    def _cables_and_rings(self) -> list[tuple[str, str, set[str]]]:
        return (
            [("Fictional HDMI Cable 2m", CABLES + " > Audio & Video Cables", {"cable"})] * 30
            + [("Fictional Satellite Coaxial Cable 10m", CABLES + " > Audio & Video Cables", {"cable"})] * 25
            + [("Fictional Cat6 Ethernet Cable 5m", CABLES + " > Network Cables", {"cable"})] * 22
            + [("Fictional USB Charging Cable 1m", CABLES, {"charging_cable", "cable"})] * 21
            + [("Fictional 2m Cable", CABLES, {"cable"})] * 3
            + [("Fictional Diamond Engagement Ring", "Apparel & Accessories > Jewelry > Rings", {"ring"})] * 55
            + [("Fictional Wedding Ring 9ct", "Apparel & Accessories > Jewelry > Rings", {"ring"})] * 5
            + [("Fictional Cable Tidy Clips", CABLES, {ACCESSORY_MARKER})] * 30
        )

    def test_a_kind_is_grouped_three_ways(self) -> None:
        cable = _entry(_measure(self._cables_and_rings()), "cable")
        # The accessories count for no kind: 101 cables, not 131.
        self.assertEqual(cable.products, 101)
        self.assertEqual(cable.noun, "cable")
        self.assertEqual(cable.named, 101)
        # "Cat6" has a number and "2m" is a spec: the word before the noun counts only
        # when it could be a choice ("ethernet").
        self.assertEqual(
            cable.words,
            (("hdmi cable", 30), ("coaxial cable", 25), ("ethernet cable", 22), ("charging cable", 21)),
        )
        self.assertEqual(cable.narrower, (("charging_cable", 21),))
        self.assertEqual(cable.shelves, (("Audio & Video Cables", 55), ("Cables", 24), ("Network Cables", 22)))
        self.assertTrue(cable.general_by_words)
        self.assertTrue(cable.general_by_shelves)

    def test_a_choice_counts_its_products_not_its_share(self) -> None:
        # One range holding most of a kind does not hide the others (on the server's
        # catalogue of 2026-10-29, fabric extension leads were 81% of the cables).
        rows = (
            [("Fictional Fabric Extension Cable 3m", CABLES, {"cable"})] * 900
            + [("Fictional HDMI Cable 2m", CABLES, {"cable"})] * 25
            + [("Fictional Speaker Cable 20m", CABLES, {"cable"})] * 21
        )
        cable = _entry(_measure(rows), "cable")
        self.assertEqual(cable.words, (("extension cable", 900), ("hdmi cable", 25), ("speaker cable", 21)))
        self.assertTrue(cable.general_by_words)

    def test_one_choice_is_not_general(self) -> None:
        measure = _measure(self._cables_and_rings())
        ring = _entry(measure, "ring")
        # Five wedding rings are under the twenty a choice needs; one shelf only.
        self.assertEqual(ring.words, (("engagement ring", 55),))
        self.assertFalse(ring.general)
        # A kind of too few products is not read at all: the 21 charging cables.
        self.assertNotIn("charging_cable", {entry.kind for entry in measure.kinds})

    def test_the_words_as_the_title_writes_them(self) -> None:
        rows = (
            [("Fixturon Corner Sofa", "", {"sofa"})] * 30
            + [("Fixturon Velvet Sofa Bed", "", {"sofa_bed", "sofa"})] * 25
            + [("Fixturon Zip-Up Hoodie", "", {"hoodie"})] * 30
            + [("Fixturon Oversized Hoodie", "", {"hoodie"})] * 25
        )
        measure = _measure(rows, brand="Fixturon")
        # Under sofas, a sofa bed is named "sofa bed": its own noun, not the sofa's.
        self.assertEqual(_entry(measure, "sofa").words, (("corner sofa", 30), ("sofa bed", 25)))
        self.assertEqual(_entry(measure, "hoodie").words, (("zip-up hoodie", 30), ("oversized hoodie", 25)))

    def test_a_word_before_the_nouns_of_many_kinds_is_no_choice(self) -> None:
        rows: list[tuple[str, str, set[str]]] = []
        nouns = (
            ("Cable", "cable"), ("Ring", "ring"), ("Laptop", "laptop"), ("Kettle", "kettle"),
            ("Toaster", "toaster"), ("Smartwatch", "smartwatch"), ("Mouse", "mouse"), ("Monitor", "monitor"),
            ("Keyboard", "keyboard"),
        )
        for position, (noun, kind) in enumerate(nouns):
            title_name = "Engagement Ring" if kind == "ring" else noun
            # A word of its own before each kind's noun, and "Black" before all of them.
            own = "Fict" + "abcdefghi"[position] * 2
            for word, count in (("Black", 30), (own, 20)):
                rows += [(f"Fixturon {word} {title_name}", "", {kind})] * count
        measure = _measure(rows, brand="Fixturon")
        self.assertEqual(measure.generic_words, (("black", 8),))
        # "black" came before the nouns of 8 kinds and is left out everywhere; "Fixturon"
        # is the brand. The ring's titles put "engagement" before its noun.
        self.assertEqual(_entry(measure, "laptop").words, (("fictcc laptop", 20),))
        self.assertEqual(_entry(measure, "ring").words, (("engagement ring", 50),))



class BuiltChoicesTests(unittest.TestCase):
    """What a search offers, each rule on its own (`kind_choices.CHOICE_RULES`)."""

    def _rows(self) -> list[tuple[str, str, set[str]]]:
        return (
            [("Fixturon 3 Piece Suit", "", {"suit"})] * 30
            + [("Fixturon 2 Piece Suit", "", {"suit"})] * 25
            + [("Fixturon Slim Fit Suit", "", {"suit"})] * 25
            + [("Fixturon Robertson Suit", "", {"suit"})] * 22
            + [("Fixturon Slim Fit Shirt", "", {"shirt"})] * 25
            + [("Fixturon Oxford Shirt", "", {"shirt"})] * 25
            + [("Fixturon Slim Fit Jeans", "", {"jeans"})] * 25
            + [("Fixturon Bootcut Jeans", "", {"jeans"})] * 25
            # Dining chairs named with several words before "dining": no half of a phrase.
            + [("Fixturon Velvet Dining Chair", "", {"chair"})] * 10
            + [("Fixturon Oak Dining Chair", "", {"chair"})] * 10
            + [("Fixturon Grey Dining Chair", "", {"chair"})] * 10
            + [("Fixturon Ergonomic Office Chair", "", {"office_chair", "chair"})] * 25
            # Nine cables in ten are extension cables.
            + [("Fixturon Extension Cable 3m", "", {"cable"})] * 360
            + [("Fixturon HDMI Cable 2m", "", {"cable"})] * 20
            + [("Fixturon Coaxial Cable 5m", "", {"cable"})] * 20
            # A pendant is a necklace: "cross pendant" and "cross necklace" are one search.
            + [("Fixturon Cross Pendant", "", {"necklace"})] * 30
            + [("Fixturon Cross Necklace", "", {"necklace"})] * 25
            + [("Fixturon Initial Necklace", "", {"necklace"})] * 20
            # One shop's thermal socks; the other shop's thermal gloves.
            + [("Fixturon Thermal Socks", "", {"socks"})] * 30
            + [("Fixturon Cotton Socks", "", {"socks"})] * 25
            + [("Fixturon Thermal Gloves", "", {"gloves"})] * 50
            # "Diamond Bracelet" names the kind with "diamond" alone: a diamond tennis
            # bracelet is a tennis bracelet, though "diamond tennis" comes before
            # necklaces too.
            + [("Fixturon Diamond Tennis Bracelet", "", {"bracelet"})] * 25
            + [("Fixturon Diamond Bracelet", "", {"bracelet"})] * 20
            + [("Fixturon Silver Link Bracelet", "", {"bracelet"})] * 10
            + [("Fixturon Diamond Tennis Necklace", "", {"necklace"})] * 5
        )

    def _products(self, rows: list[tuple[str, str, set[str]]]) -> list[ProviderProduct]:
        return _two_shops(
            rows, one_shop=("Fixturon Robertson", "Fixturon Thermal Socks"), other_shop=("Fixturon Thermal Gloves",)
        )

    def _choices(self, rules=kind_choices.CHOICE_RULES) -> dict[str, list[str]]:
        rows = self._rows()
        built = kind_choices.build_kind_choices(self._products(rows), [kinds for _t, _c, kinds in rows], rules=rules)
        return {kind: [choice.text for choice in choices] for kind, choices in built.items()}

    def test_every_rule(self) -> None:
        choices = self._choices()
        self.assertEqual(choices["suit"], ["3 piece suit", "2 piece suit", "slim fit suit"])
        self.assertEqual(choices["shirt"], ["oxford shirt", "slim fit shirt"])
        self.assertEqual(choices["jeans"], ["bootcut jeans", "slim fit jeans"])
        self.assertEqual(choices["chair"], ["dining chair", "office chair"])
        self.assertEqual(choices["cable"], ["coaxial cable", "hdmi cable"])
        self.assertEqual(choices["necklace"], ["cross pendant", "initial necklace"])
        self.assertEqual(choices["socks"], ["thermal socks", "cotton socks"])
        self.assertEqual(choices["bracelet"], ["tennis bracelet", "diamond bracelet"])

    def test_a_shelf_naming_one_word_before_the_noun(self) -> None:
        # Network cables named "Cat6" and "Cat5e" by their titles, and by their shelves; a
        # shelf the search cannot read ("Ethernet Cables" in no field it searches) is none.
        rows = (
            [("Fixturon Cat6 Cable 5m", "Electronics > Cables > Network Cables", {"cable"})] * 25
            + [("Fixturon Cat5e Cable 2m", "Electronics > Cables > LAN Cables", {"cable"})] * 25
            + [("Fixturon HDMI Cable 2m", "Electronics > Cables > Audio & Video Cables", {"cable"})] * 25
            + [("Fixturon Cat7 Cable 1m", "Electronics > Cables > Ethernet Cables", {"cable"})] * 25
        )
        products = [
            # The shop's own type names the shelf, except for the Cat7 cables.
            product if "Cat7" in product.title else replace(
                product, raw={**product.raw, "product_type": product.category_text.split(" > ")[-1]}
            )
            for product in _two_shops(rows)
        ]
        kinds = [row_kinds for _t, _c, row_kinds in rows]
        built = kind_choices.build_kind_choices(products, kinds)
        self.assertEqual([choice.text for choice in built["cable"]], ["hdmi cable", "lan cables", "network cables"])
        considered = {row.text: row.outcome for row in kind_choices.kind_choice_candidates(products, kinds)["cable"]}
        self.assertEqual(considered["ethernet cables"], kind_choices.FINDS_NONE)
        rules = kind_choices.CHOICE_RULES - {kind_choices.RULE_SHELVES}
        self.assertNotIn("cable", kind_choices.build_kind_choices(products, kinds, rules=rules))

    def test_why_each_was_left_out(self) -> None:
        rows = self._rows()
        considered = kind_choices.kind_choice_candidates(self._products(rows), [kinds for _t, _c, kinds in rows])
        outcome = {(kind, row.text): row.outcome for kind, rows_of in considered.items() for row in rows_of}
        self.assertEqual(outcome[("suit", "robertson suit")], kind_choices.FEW_SHOPS)
        self.assertEqual(outcome[("suit", "piece suit")], kind_choices.HALF_PHRASE)
        self.assertEqual(outcome[("suit", "fit suit")], kind_choices.HALF_PHRASE)
        self.assertEqual(outcome[("cable", "extension cable")], kind_choices.WHOLE_KIND)
        self.assertEqual(outcome[("necklace", "cross necklace")], kind_choices.SAME_SEARCH)
        shops = {(kind, row.text): row.shops for kind, rows_of in considered.items() for row in rows_of}
        self.assertEqual(shops[("socks", "thermal socks")], 1)
        found = {(kind, row.text): row.found for kind, rows_of in considered.items() for row in rows_of}
        # "extension" comes before "cable" in 360 of the 400 cables' titles, as the search
        # reads a word naming a sub-kind.
        self.assertEqual(found[("cable", "extension cable")], 360)
        self.assertEqual(found[("cable", "hdmi cable")], 20)

    def test_one_shop_s_words_without_the_rule(self) -> None:
        rules = kind_choices.CHOICE_RULES - {kind_choices.RULE_SHOPS}
        self.assertIn("robertson suit", self._choices(rules)["suit"])

    def test_halves_of_phrases_without_the_rule(self) -> None:
        rules = kind_choices.CHOICE_RULES - {kind_choices.RULE_PHRASES}
        self.assertEqual(self._choices(rules)["suit"], ["piece suit", "fit suit"])

    def test_a_choice_keeping_the_kind_without_the_rule(self) -> None:
        rules = kind_choices.CHOICE_RULES - {kind_choices.RULE_WHOLE_KIND}
        self.assertEqual(self._choices(rules)["cable"][0], "extension cable")

    def test_the_singular_without_the_rule(self) -> None:
        # "bootcut jean" is no search the understanding reads: the jeans keep no choice.
        rules = kind_choices.CHOICE_RULES - {kind_choices.RULE_WRITTEN}
        self.assertNotIn("jeans", self._choices(rules))

    def test_one_search_twice_without_the_rule(self) -> None:
        rules = kind_choices.CHOICE_RULES - {kind_choices.RULE_SAME_SEARCH}
        self.assertEqual(self._choices(rules)["necklace"], ["cross pendant", "cross necklace", "initial necklace"])


if __name__ == "__main__":
    unittest.main()
