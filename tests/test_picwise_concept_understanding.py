"""Understanding which product a buyer means, however it was spelled.

The misspellings here are the ones Greek buyers actually make. What must hold:

1. every ordinary way of writing a product reaches the same concept
2. a word that merely looks like a product name is never turned into one
3. specs and preferences are kept as filters, in the feed's own words
4. feed products are annotated with the same concepts, from their own type
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.concept_understanding import (  # noqa: E402
    annotate_product_concepts,
    damerau_levenshtein,
    greek_key,
    greeklish_key,
    normalize_spec_text,
    understand_product_query,
)
from picwise_nlu.product_concepts import (  # noqa: E402
    broader_concepts,
    get_product_concepts,
    spec_fields_for_mega_category,
)


def concept_of(query: str) -> str | None:
    reading = understand_product_query(query)
    return reading.concept_id if reading.understood else None


class PhoneticKeyTests(unittest.TestCase):
    def test_every_spelling_of_a_greek_sound_shares_a_key(self) -> None:
        keys = {greek_key(word) for word in ("πλυντήριο", "πλιντηριο", "πληντιριο", "πλειντηριω")}
        self.assertEqual(len(keys), 1, keys)

    def test_greeklish_habits_share_the_greek_key(self) -> None:
        greek = greek_key("τηλεόραση")
        for word in ("tileorasi", "tileorasy", "tilaiorasi"):
            with self.subTest(word=word):
                self.assertEqual(greeklish_key(word), greek)

    def test_mp_and_nt_are_written_either_way(self) -> None:
        self.assertEqual(greeklish_key("bataria"), greek_key("μπαταρία"))
        self.assertEqual(greeklish_key("mpataria"), greek_key("μπαταρία"))
        self.assertEqual(greeklish_key("plidirio"), greek_key("πλυντήριο"))

    def test_distance_counts_a_transposition_as_one_edit(self) -> None:
        self.assertEqual(damerau_levenshtein("lapotp", "laptop", 2), 1)
        self.assertEqual(damerau_levenshtein("abc", "xyz", 1), 2)


class EverySpellingReachesTheConceptTests(unittest.TestCase):
    CASES = {
        "washing_machine": (
            "πλυντήριο ρούχων", "πλυντηριο ρουχων", "πλιντηριο ρουχον", "plyntirio rouchon",
            "plintirio rouhon", "plynthrio rouxwn", "πλυντηριορουχων", "washing machine",
            "wasing machine",
        ),
        "refrigerator": ("ψυγείο", "ψιγειο", "psygeio", "psigio", "cygeio", "fridge", "fridge freezer"),
        "power_bank": (
            "εξωτερική μπαταρία", "εξωτερικη μπαταρια", "exoteriki bataria", "power bank",
            "pawer bank", "powerbank",
        ),
        # "thleorash" is written by shape, where "th" reads as θ: one edit away.
        "television": ("τηλεόραση", "τηλαιοραση", "tileorasi", "thleorash", "tv", "television"),
        "laptop": ("λάπτοπ", "λαπτοπ", "laptop", "lapotp", "φορητός υπολογιστής"),
        "air_fryer": ("φριτέζα αέρος", "fritieza aeros", "air fryer", "φριτέζα χωρίς λάδι"),
        "blood_pressure_monitor": ("πιεσόμετρο", "piesometro", "blood pressure monitor"),
        "car_battery": ("μπαταρία αυτοκινήτου", "bataria aftokinitou", "car battery"),
    }

    def test_every_spelling_reaches_the_concept(self) -> None:
        for concept, queries in self.CASES.items():
            for query in queries:
                with self.subTest(query=query):
                    self.assertEqual(concept_of(query), concept)

    def test_the_longest_name_wins(self) -> None:
        self.assertEqual(concept_of("φούρνος μικροκυμάτων"), "microwave")
        self.assertEqual(concept_of("φούρνος"), "oven")
        self.assertEqual(concept_of("πλυντήριο πιάτων"), "dishwasher")
        self.assertEqual(concept_of("κράνος ποδηλάτου"), "bicycle_helmet")

    def test_the_product_bought_is_the_one_before_for(self) -> None:
        self.assertEqual(concept_of("webcam για laptop"), "webcam")
        self.assertEqual(concept_of("τόνερ για εκτυπωτή laser"), "toner")
        self.assertEqual(concept_of("power bank for iphone"), "power_bank")
        self.assertEqual(concept_of("κινητο με καλη καμερα"), "smartphone")

    def test_greek_names_the_product_first_and_english_last(self) -> None:
        self.assertEqual(concept_of("θήκη κινητού"), "phone_case")
        self.assertEqual(concept_of("laptop bag"), "laptop_bag")


class NothingIsInventedTests(unittest.TestCase):
    def test_everyday_words_are_not_turned_into_products(self) -> None:
        for query in (
            "κρασι", "παιδια", "πιστωτικη καρτα", "πορτοκαλι", "horse",
            "wedding cake topper", "submarine periscope", "καιρος αυριο",
        ):
            with self.subTest(query=query):
                self.assertIsNone(concept_of(query))

    def test_non_retail_searches_are_not_products(self) -> None:
        for query in ("δανειο", "τραπεζα", "ασφαλεια αυτοκινητου", "loan", "insurance"):
            with self.subTest(query=query):
                self.assertIsNone(concept_of(query))

    def test_a_misspelling_equally_close_to_two_products_names_neither(self) -> None:
        from picwise_nlu.concept_understanding import _Span, _drop_uncertain_ties

        tie = [_Span(0, 1, "camera", 1.0, "el"), _Span(0, 1, "coffee_machine", 1.0, "el")]
        self.assertEqual(_drop_uncertain_ties(tie), [])
        # Related concepts are not a tie: a helmet reading and a bicycle helmet one agree.
        related = [_Span(0, 1, "helmet", 1.0, "el"), _Span(0, 1, "bicycle_helmet", 1.0, "el")]
        self.assertEqual(len(_drop_uncertain_ties(related)), 2)
        # An exact match is never dropped.
        exact = [_Span(0, 1, "camera", 0.0, "el"), _Span(0, 1, "coffee_machine", 0.0, "el")]
        self.assertEqual(len(_drop_uncertain_ties(exact)), 2)

    def test_a_long_word_with_a_missing_letter_is_corrected(self) -> None:
        self.assertEqual(concept_of("καφειερα"), "coffee_machine")

    def test_a_short_word_is_only_matched_by_sound_not_corrected(self) -> None:
        self.assertEqual(concept_of("ψιγειο"), "refrigerator")  # same sound
        self.assertIsNone(concept_of("δραανο"))  # a letter missing from a short word


class FiltersTests(unittest.TestCase):
    def test_specs_are_fused_and_linked_to_the_product_rules(self) -> None:
        reading = understand_product_query("πλυντηριο ρουχων 8 κιλα")
        self.assertEqual(reading.filters, ("8kg",))
        self.assertEqual(reading.specs[0].spec_field, "load_capacity_kg")
        self.assertIn(
            reading.specs[0].spec_field,
            spec_fields_for_mega_category(reading.mega_category_id),
        )

    def test_spec_units_in_every_language(self) -> None:
        for query, expected in (
            ("τηλεοραση 55 ιντσες", "55inch"),
            ("air fryer 5 λιτρα", "5l"),
            ("powerbank 10000mah", "10000mah"),
            ("κλιματιστικο 12000 btu", "12000btu"),
            ("laptop 16gb ram", "16gb"),
        ):
            with self.subTest(query=query):
                self.assertIn(expected, understand_product_query(query).filters)

    def test_greek_preferences_become_feed_words(self) -> None:
        reading = understand_product_query("ποντικι ασυρματο")
        self.assertEqual(reading.concept_id, "mouse")
        self.assertIn("wireless", reading.filters)
        self.assertEqual(reading.filter_sources["wireless"], "ασυρματο")

    def test_judgements_are_understood_but_never_filters(self) -> None:
        reading = understand_product_query("φθηνο κλιματιστικο")
        self.assertEqual(reading.concept_id, "air_conditioner")
        self.assertEqual(reading.filters, ())
        self.assertEqual(reading.judgements, ("φθηνο",))

    def test_feed_spec_text_is_fused_the_same_way(self) -> None:
        self.assertEqual(normalize_spec_text("fixturon 55 inch 4k television"), "fixturon 55inch 4k television")
        self.assertEqual(normalize_spec_text("8 kg washer"), "8kg washer")
        self.assertEqual(normalize_spec_text("2 in 1 laptop"), "2 in 1 laptop")


class ProductAnnotationTests(unittest.TestCase):
    def test_feed_types_map_to_concepts(self) -> None:
        for product_type, concept in (
            ("Washing Machines", "washing_machine"),
            ("Mobile Phones", "smartphone"),
            ("Multifunction Printers", "printer"),
            ("Blood Pressure Monitors", "blood_pressure_monitor"),
            ("Πλυντήρια Ρούχων", "washing_machine"),
        ):
            with self.subTest(product_type=product_type):
                self.assertIn(concept, annotate_product_concepts(product_type, "", ""))

    def test_an_accessory_type_is_not_the_main_product(self) -> None:
        concepts = annotate_product_concepts("Laptop Cases & Bags", "", "Fixturon Laptop Bag")
        self.assertIn("laptop_bag", concepts)
        self.assertNotIn("laptop", concepts)

    def test_a_listed_type_carries_each_kind(self) -> None:
        self.assertEqual(annotate_product_concepts("Fans & Heaters", "", ""), {"fan", "heater"})

    def test_the_title_refines_but_never_changes_the_type(self) -> None:
        refined = annotate_product_concepts("Vacuum Cleaners", "", "Robot Vacuum Cleaner")
        self.assertEqual(refined, {"vacuum_cleaner", "robot_vacuum"})
        # A laptop whose title mentions its SSD is still only a laptop.
        self.assertEqual(annotate_product_concepts("Laptops", "", "Laptop 16GB RAM 512GB SSD"), {"laptop"})

    def test_greek_titles_are_annotated_when_there_is_no_type(self) -> None:
        self.assertEqual(annotate_product_concepts("", "", "Ψυγειοκαταψύκτης Samsung 350L"), {"refrigerator"})


class AccessoryGuardTests(unittest.TestCase):
    """An accessory of a product is never annotated as the product itself."""

    def test_english_accessory_word_after_the_product(self) -> None:
        self.assertEqual(
            annotate_product_concepts("Washing Machine Accessories", "", "Fixturon washing machine hose"),
            {"__accessory__"},
        )
        self.assertEqual(
            annotate_product_concepts("", "", "Fixturon Coffee Machine Filter 4 pack"),
            {"__accessory__"},
        )

    def test_a_word_before_the_product_is_a_type_not_an_accessory(self) -> None:
        self.assertEqual(annotate_product_concepts("", "", "Filter Coffee Machine"), {"coffee_machine"})

    def test_greek_order_is_the_other_way_round(self) -> None:
        self.assertEqual(annotate_product_concepts("", "", "Καφετιέρα φίλτρου Fixturon"), {"coffee_machine"})
        self.assertNotIn("coffee_machine", annotate_product_concepts("", "", "Φίλτρο καφετιέρας"))

    def test_text_naming_a_product_only_after_for_is_an_accessory_of_it(self) -> None:
        # These used to be annotated as the product they are for: a shop category of
        # laptop accessories answered "laptop".
        for product_type, title in (
            ("Accessories for Laptops", "Fixturon Sleeve 15"),
            ("Spare Parts for Washing Machines", "Fixturon Door Seal"),
            ("", "Replacement Battery for Fixturon Laptop"),
            ("", "Filter for Coffee Machine"),
            ("", "Fixturon Sleeve for Laptop"),
            ("", "Φίλτρο για καφετιέρα"),
        ):
            with self.subTest(product_type=product_type, title=title):
                self.assertEqual(annotate_product_concepts(product_type, "", title), {"__accessory__"})

    def test_what_comes_with_a_product_does_not_make_it_an_accessory(self) -> None:
        # An accessory word after "with" lists what is in the box; these real products
        # used to be annotated as accessories and never shown.
        for title, concept in (
            ("Fixturon Robot Vacuum Cleaner with HEPA Filter", "robot_vacuum"),
            ("Testline Espresso Coffee Machine with Milk Frother and Filter", "coffee_machine"),
            ("Sampleworks Stand Mixer with Splash Guard Cover", "mixer"),
            ("Καφετιέρα με φίλτρο", "coffee_machine"),
        ):
            with self.subTest(title=title):
                self.assertIn(concept, annotate_product_concepts("", "", title))
        # The product is still named before "for": a charger for a phone is a charger.
        self.assertEqual(annotate_product_concepts("", "", "Charger for iPhone"), {"phone_charger"})


class ExpandedLexiconTests(unittest.TestCase):
    def test_common_greek_shop_categories(self) -> None:
        for query, concept in (
            ("ταμπλετ", "tablet"),
            ("tablet samsung", "tablet"),
            ("ταμπλέτες πλυντηρίου πιάτων", "dishwasher_tablets"),
            ("ψησταρια υγραεριου", "grill"),
            ("καρτα γραφικων", "graphics_card"),
            ("σεντονια διπλα", "bed_linen"),
            ("μπαλα ποδοσφαιρου", "football"),
        ):
            with self.subTest(query=query):
                self.assertEqual(concept_of(query), concept)

    def test_a_tablet_and_dishwasher_tablets_never_mix(self) -> None:
        self.assertEqual(annotate_product_concepts("Dishwasher Tablets", "", ""), {"dishwasher_tablets"})
        self.assertEqual(annotate_product_concepts("Tablets", "", ""), {"tablet"})


class DidYouMeanTests(unittest.TestCase):
    def test_a_short_typo_is_asked_about_not_answered(self) -> None:
        from picwise_nlu.concept_understanding import suggest_product_names

        self.assertIsNone(concept_of("dsk"))
        self.assertEqual(suggest_product_names("dsk"), ("desk",))
        self.assertEqual(suggest_product_names("τοερ"), ("τόνερ",))

    def test_an_equally_close_pair_is_offered_both_ways(self) -> None:
        from picwise_nlu.concept_understanding import suggest_product_names

        self.assertEqual(set(suggest_product_names("ακοσυτικα")), {"ακουστικά", "αποσμητικό"})

    def test_no_suggestion_for_understood_or_everyday_words(self) -> None:
        from picwise_nlu.concept_understanding import suggest_product_names

        for query in ("πλυντηριο", "κρασι", "δανειο", "asdfgh"):
            with self.subTest(query=query):
                self.assertEqual(suggest_product_names(query), ())


class LexiconIntegrityTests(unittest.TestCase):
    def test_every_concept_has_english_and_greek_names_and_a_mega_category(self) -> None:
        for concept in get_product_concepts():
            with self.subTest(concept=concept.concept_id):
                self.assertTrue(concept.english)
                self.assertTrue(concept.greek)
                self.assertTrue(spec_fields_for_mega_category(concept.mega_category_id))

    def test_broader_links_resolve(self) -> None:
        self.assertEqual(broader_concepts("running_shoes"), ("running_shoes", "athletic_shoes", "shoes"))


if __name__ == "__main__":
    unittest.main()
