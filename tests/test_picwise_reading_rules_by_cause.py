"""The search read by rules, one per cause, not word by word (owner, 2026-11-07).

The debugging's first measure (`deployment/server/print_search_reading.py`) listed the
causes of wrong readings; the owner: «αυτά που μου προτείνεις είναι πολύ συγκεκριμένα
από αυτά θα βγάλουμε άλλες λέξεις», then «Ναι σε όλα» to fixing each cause once, for every
word. Pinned here, with the site's English only:

- a name's other number: every English name is read in both numbers ("drill bit" is
  drill bits, not a drill; "boot", "sock", "nappy" are read), a form only a search reads:
  a feed product is still classified by the names as written; a weak name keeps one
  number ("covers" is no phone case);
- a word spelt right is never corrected into another product's word: "iphone" is no desk
  phone, "rubber" no router, "boxes" no boxers, "chains" no chair; a word no list holds
  still is ("wahsing machine"); "Did you mean" never offers a word spelt right as another
  word on its own; a dropped h after a first p is read ("pones" for phones);
- the words that judge or shop ("best", "cheap", "deals", "uk") are set aside, never a
  filter, never "could not match".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_nlu.concept_understanding import (  # noqa: E402
    _concepts_in_text,
    is_known_english_word,
    suggest_product_names,
    understand_product_query,
)
from picwise_nlu.english_number import english_other_number  # noqa: E402


def _kind(query: str) -> str | None:
    return understand_product_query(query).concept_id


class OtherNumberTests(unittest.TestCase):
    def test_every_name_is_read_in_both_numbers(self) -> None:
        cases = {
            "drill bit": "drill_bits",
            "dishwasher pod": "dishwasher_tablets",
            "external batteries": "power_bank",
            "vehicle batteries": "car_battery",
            "boot": "boots",
            "sock": "socks",
            "sneaker": "athletic_shoes",
            "nappy": "nappies",
            "hair brushes": "hair_brush",
            "settees": "sofa",
            "couches": "sofa",
            "tool boxes": "tool_box",
            "lunch boxes": "food_storage",
            "litter boxes": "cat_litter",
            "computer mice": "mouse",
        }
        for query, kind in cases.items():
            reading = understand_product_query(query)
            self.assertEqual((reading.concept_id, reading.exact), (kind, True), query)

    def test_a_weak_name_keeps_one_number(self) -> None:
        self.assertNotEqual(_kind("book covers"), "phone_case")
        self.assertNotEqual(_kind("cotton balls"), "football")

    def test_the_other_number_never_classifies_a_feed_product(self) -> None:
        self.assertEqual(_kind("boot"), "boots")
        self.assertEqual(_concepts_in_text("boot"), [])
        self.assertEqual([span.concept_id for span in _concepts_in_text("boots")], ["boots"])

    def test_the_inflection(self) -> None:
        self.assertEqual(english_other_number("drill bits"), "drill bit")
        self.assertEqual(english_other_number("chest of drawers"), "chests of drawers")
        self.assertIsNone(english_other_number("reading glasses"))
        self.assertEqual(english_other_number("bookshelf"), "bookshelves")
        self.assertEqual(english_other_number("bookshelves"), "bookshelf")
        self.assertEqual(english_other_number("steak knife"), "steak knives")


class WordsSpeltRightTests(unittest.TestCase):
    def test_a_word_spelt_right_is_never_corrected_into_another_products(self) -> None:
        self.assertNotEqual(_kind("iphone"), "desk_phone")
        self.assertNotEqual(_kind("iphone 15"), "desk_phone")
        self.assertIsNone(_kind("chains"))
        self.assertIsNone(_kind("crutches"))
        rubber = understand_product_query("rubber gloves")
        self.assertEqual((rubber.concept_id, rubber.filters), ("gloves", ("rubber",)))
        self.assertEqual(_kind("snow chains"), "snow_chains")
        self.assertEqual(_kind("laser level"), "spirit_level")
        self.assertEqual(_kind("screen protector"), "screen_protector")
        for word in ("rubber", "boxes", "chains", "iphone", "iphones", "pulse", "receiver"):
            self.assertTrue(is_known_english_word(word), word)

    def test_a_word_no_list_holds_is_still_corrected(self) -> None:
        for query, kind in (("wahsing machine", "washing_machine"), ("coffe maker", "coffee_machine")):
            reading = understand_product_query(query)
            self.assertEqual((reading.concept_id, reading.exact), (kind, False), query)
        self.assertFalse(is_known_english_word("wahsing"))

    def test_did_you_mean_never_offers_a_word_spelt_right_as_another_on_its_own(self) -> None:
        self.assertEqual(suggest_product_names("chains"), ())
        self.assertEqual(suggest_product_names("iphone"), ())
        self.assertEqual(suggest_product_names("dsk"), ("desk",))

    def test_a_dropped_h_after_a_first_p(self) -> None:
        for query, kind in (("pones", "mobile_phone"), ("mobile pones", "mobile_phone"), ("desk pone", "desk_phone")):
            self.assertEqual(_kind(query), kind, query)
        self.assertEqual(_kind("poto frame"), "photo_frame")


class JudgementWordTests(unittest.TestCase):
    def test_words_that_judge_or_shop_are_set_aside(self) -> None:
        for query, kind in (
            ("best laptop", "laptop"),
            ("cheap kettle uk", "kettle"),
            ("air fryer deals", "air_fryer"),
            ("laptop sale", "laptop"),
        ):
            reading = understand_product_query(query)
            self.assertEqual(reading.concept_id, kind, query)
            self.assertEqual(reading.filters, (), query)
            self.assertEqual(reading.judgements, (), query)


if __name__ == "__main__":
    unittest.main()
