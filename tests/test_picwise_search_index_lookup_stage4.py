from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.query_variant_generator import generate_noisy_variants_for_term  # noqa: E402
from picwise_search_memory import build_canonical_vocabulary_registry, build_offline_search_index, lookup_offline_search_index  # noqa: E402


class PicWiseSearchIndexLookupStage4Tests(unittest.TestCase):
    def setUp(self) -> None:
        vocab = {
            "kitchen_cooking_household": {"coffee grinder", "vacuum cleaner"},
            "phones_mobile_accessories": {"bluetooth speaker", "gaming mouse", "usb cable"},
            "car_tyres": {"car battery"},
            "baby_kids_pets_sports_outdoor": {"bike helmet", "baby car seat"},
            "power_tools_workshop": {"garden shears"},
            "fashion_clothing_accessories": {"winter jacket"},
            "home_furniture_appliances": {"car tyre"},
        }
        generated: list[dict[str, str]] = []
        for category, terms in vocab.items():
            for term in sorted(terms):
                generated.extend(generate_noisy_variants_for_term(term, category))

        from picwise_search_memory.contracts import CanonicalVocabularyBuildReport, CanonicalVocabularyRecord, CanonicalVocabularyRegistry
        from picwise_search_memory.validation import normalize_term, stable_canonical_id

        records: list[CanonicalVocabularyRecord] = []
        for category, terms in sorted(vocab.items()):
            for term in sorted(terms):
                normalized = normalize_term(term)
                records.append(
                    CanonicalVocabularyRecord(
                        canonical_id=stable_canonical_id(category, normalized),
                        canonical_term=normalized,
                        normalized_term=normalized,
                        mega_category_id=category,
                        source="taxonomy_clean_vocabulary",
                        source_file="vocabulary_source.py",
                        language="english",
                        status="active",
                        schema_version="1.0.0",
                        token_count=len(normalized.split()),
                        quality_flags=("offline_registry",),
                    )
                )
        registry = CanonicalVocabularyRegistry(
            records=tuple(records),
            report=CanonicalVocabularyBuildReport(
                total_input_terms=len(records),
                total_records=len(records),
                rejected_terms=0,
                duplicate_terms=0,
                rejected_by_reason={},
                counts_by_mega_category={category: len(terms) for category, terms in vocab.items()},
                source="taxonomy_clean_vocabulary",
                schema_version="1.0.0",
                language="english",
                status="active",
            ),
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
        )
        self.index = build_offline_search_index(registry, generated)

    def test_fixed_probe_group_a(self) -> None:
        probes = {
            "coffe grindr": "coffee grinder",
            "vaccum cleaner": "vacuum cleaner",
            "bluethoth speker": "bluetooth speaker",
            "gming mouse": "gaming mouse",
            "car batery": "car battery",
            "bike helmt": "bike helmet",
            "gardn shears": "garden shears",
            "winter jakcet": "winter jacket",
            "baby car seet": "baby car seat",
            "usb caible": "usb cable",
        }
        for query, expected in probes.items():
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match")
                self.assertIsNotNone(result.matched_entry)
                self.assertEqual(result.matched_entry.canonical_term, expected)
                self.assertIn(result.confidence, {"low", "medium", "high"})

    def test_supports_us_uk_tyre_tire(self) -> None:
        result = lookup_offline_search_index("car tire", self.index)
        self.assertEqual(result.status, "match")
        self.assertIsNotNone(result.matched_entry)
        self.assertEqual(result.matched_entry.canonical_term, "car tyre")

    def test_negative_broad_ambiguous_queries_return_no_match(self) -> None:
        for query in ("bank", "charger", "apple", "nike", "bosch", "insurance", "loan"):
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")
                self.assertIsNone(result.matched_entry)

    def test_collided_exact_match_does_not_blindly_choose_first(self) -> None:
        from picwise_search_memory.contracts import CanonicalVocabularyBuildReport, CanonicalVocabularyRecord, CanonicalVocabularyRegistry

        records = (
            CanonicalVocabularyRecord(
                canonical_id="id_cat_a",
                canonical_term="apple",
                normalized_term="apple",
                mega_category_id="electronics_audio_video",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=1,
                quality_flags=("offline_registry",),
            ),
            CanonicalVocabularyRecord(
                canonical_id="id_cat_b",
                canonical_term="apple",
                normalized_term="apple",
                mega_category_id="office_supplies_school",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=1,
                quality_flags=("offline_registry",),
            ),
        )
        registry = CanonicalVocabularyRegistry(
            records=records,
            report=CanonicalVocabularyBuildReport(
                total_input_terms=2,
                total_records=2,
                rejected_terms=0,
                duplicate_terms=0,
                rejected_by_reason={},
                counts_by_mega_category={"electronics_audio_video": 1, "office_supplies_school": 1},
                source="taxonomy_clean_vocabulary",
                schema_version="1.0.0",
                language="english",
                status="active",
            ),
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
        )
        index = build_offline_search_index(registry=registry, generated_variants=[])
        result = lookup_offline_search_index("apple", index)
        self.assertEqual(result.status, "no_match")
        self.assertTrue(
            "cross_category_exact_collision" in result.reason_codes or "broad_or_ambiguous_query" in result.reason_codes
        )

    def test_shared_cross_category_taxonomy_terms_remain_safe_no_match(self) -> None:
        from picwise_search_memory.contracts import CanonicalVocabularyBuildReport, CanonicalVocabularyRecord, CanonicalVocabularyRegistry

        records = (
            CanonicalVocabularyRecord(
                canonical_id="id_cat_a",
                canonical_term="taxonomy families",
                normalized_term="taxonomy families",
                mega_category_id="audio_video_gaming_cameras",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=2,
                quality_flags=("offline_registry",),
            ),
            CanonicalVocabularyRecord(
                canonical_id="id_cat_b",
                canonical_term="taxonomy families",
                normalized_term="taxonomy families",
                mega_category_id="kitchen_cooking_household",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=2,
                quality_flags=("offline_registry",),
            ),
            CanonicalVocabularyRecord(
                canonical_id="id_cat_c",
                canonical_term="taxonomy families",
                normalized_term="taxonomy families",
                mega_category_id="phones_mobile_accessories",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=2,
                quality_flags=("offline_registry",),
            ),
        )
        registry = CanonicalVocabularyRegistry(
            records=records,
            report=CanonicalVocabularyBuildReport(
                total_input_terms=3,
                total_records=3,
                rejected_terms=0,
                duplicate_terms=0,
                rejected_by_reason={},
                counts_by_mega_category={
                    "audio_video_gaming_cameras": 1,
                    "kitchen_cooking_household": 1,
                    "phones_mobile_accessories": 1,
                },
                source="taxonomy_clean_vocabulary",
                schema_version="1.0.0",
                language="english",
                status="active",
            ),
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
        )
        index = build_offline_search_index(registry=registry, generated_variants=[])
        result = lookup_offline_search_index("taxonomy families", index)
        self.assertEqual(result.status, "no_match")
        self.assertIsNone(result.matched_entry)
        self.assertTrue(
            {"shared_taxonomy_or_meta_term", "meta_or_taxonomy_query"}.intersection(result.reason_codes),
            result.reason_codes,
        )

    def test_specific_cross_category_collision_recovers_when_clear_specificity_winner_exists(self) -> None:
        from picwise_search_memory.contracts import CanonicalVocabularyBuildReport, CanonicalVocabularyRecord, CanonicalVocabularyRegistry

        records = (
            CanonicalVocabularyRecord(
                canonical_id="id_generic",
                canonical_term="headphone",
                normalized_term="headphone",
                mega_category_id="audio_video_gaming_cameras",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=1,
                quality_flags=("offline_registry",),
            ),
            CanonicalVocabularyRecord(
                canonical_id="id_specific",
                canonical_term="wireless noise cancelling headphone",
                normalized_term="wireless noise cancelling headphone",
                mega_category_id="phones_mobile_accessories",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=4,
                quality_flags=("offline_registry",),
            ),
        )
        registry = CanonicalVocabularyRegistry(
            records=records,
            report=CanonicalVocabularyBuildReport(
                total_input_terms=2,
                total_records=2,
                rejected_terms=0,
                duplicate_terms=0,
                rejected_by_reason={},
                counts_by_mega_category={
                    "audio_video_gaming_cameras": 1,
                    "phones_mobile_accessories": 1,
                },
                source="taxonomy_clean_vocabulary",
                schema_version="1.0.0",
                language="english",
                status="active",
            ),
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
        )
        generated = [
            {
                "canonical_term": "headphone",
                "variant": "wireless noise cancelling headphone",
                "mega_category_id": "audio_video_gaming_cameras",
                "variant_type": "generated",
                "source": "taxonomy_clean_vocabulary",
                "generator_version": "stage3_generic",
            }
        ]
        index = build_offline_search_index(registry=registry, generated_variants=generated)
        result = lookup_offline_search_index("wireless noise cancelling headphone", index)
        self.assertEqual(result.status, "match")
        self.assertIsNotNone(result.matched_entry)
        self.assertEqual(result.matched_entry.canonical_id, "id_specific")
        self.assertTrue(
            "exact_collision_specificity_recovery" in result.reason_codes
            or "exact_collision_disambiguated" in result.reason_codes
        )

    def test_broad_negative_terms_stay_no_match_even_when_present_as_exact_collision(self) -> None:
        from picwise_search_memory.contracts import CanonicalVocabularyBuildReport, CanonicalVocabularyRecord, CanonicalVocabularyRegistry

        records = (
            CanonicalVocabularyRecord(
                canonical_id="id_cat_a",
                canonical_term="bank",
                normalized_term="bank",
                mega_category_id="audio_video_gaming_cameras",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=1,
                quality_flags=("offline_registry",),
            ),
            CanonicalVocabularyRecord(
                canonical_id="id_cat_b",
                canonical_term="bank",
                normalized_term="bank",
                mega_category_id="kitchen_cooking_household",
                source="taxonomy_clean_vocabulary",
                source_file="vocabulary_source.py",
                language="english",
                status="active",
                schema_version="1.0.0",
                token_count=1,
                quality_flags=("offline_registry",),
            ),
        )
        registry = CanonicalVocabularyRegistry(
            records=records,
            report=CanonicalVocabularyBuildReport(
                total_input_terms=2,
                total_records=2,
                rejected_terms=0,
                duplicate_terms=0,
                rejected_by_reason={},
                counts_by_mega_category={
                    "audio_video_gaming_cameras": 1,
                    "kitchen_cooking_household": 1,
                },
                source="taxonomy_clean_vocabulary",
                schema_version="1.0.0",
                language="english",
                status="active",
            ),
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
        )
        index = build_offline_search_index(registry=registry, generated_variants=[])
        result = lookup_offline_search_index("bank", index)
        self.assertEqual(result.status, "no_match")
        self.assertIn("broad_or_ambiguous_query", result.reason_codes)

    def test_contextual_specific_query_still_matches_when_safe(self) -> None:
        result = lookup_offline_search_index("gaming mouse", self.index)
        self.assertEqual(result.status, "match")
        self.assertIsNotNone(result.matched_entry)
        self.assertEqual(result.matched_entry.canonical_term, "gaming mouse")

    def test_broad_terms_extended_guard_remain_safe(self) -> None:
        for query in ("bank", "charger", "apple", "nike", "bosch", "insurance", "loan", "erp", "crm", "accounting software"):
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")
                self.assertIsNone(result.matched_entry)


class PicWiseSearchIndexLookupIntegrationStage43Tests(unittest.TestCase):
    """Acceptance probes against the full offline registry + Stage 3 generated index."""

    def setUp(self) -> None:
        self.registry = build_canonical_vocabulary_registry()
        self.index = build_offline_search_index(self.registry)

    def test_realistic_noisy_queries_resolve_to_expected_mega_category(self) -> None:
        probes = {
            "coffe grindr": "kitchen_cooking_household",
            "vaccum cleaner": "home_appliances_laundry_climate",
            "bluethoth speker": "audio_video_gaming_cameras",
            "gming mouse": "computers_office_peripherals",
            "car batery": "car_parts_service_maintenance",
            "bike helmt": "moto_bicycle_mobility_gear",
            "winter jakcet": "clothing_apparel_workwear",
            "baby car seet": "baby_kids_pets_sports_outdoor",
            "usb caible": "phones_mobile_accessories",
        }
        for query, expected_category in probes.items():
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match")
                self.assertIsNotNone(result.matched_entry)
                self.assertEqual(result.matched_entry.mega_category_id, expected_category)
                self.assertIn(result.confidence, {"low", "medium", "high"})

    def test_broad_and_contextual_negatives_remain_safe_on_full_index(self) -> None:
        negatives = (
            "bank",
            "charger",
            "apple",
            "nike",
            "bosch",
            "insurance",
            "loan",
            "erp",
            "crm",
            "accounting software",
            "river bank",
            "bank account",
            "car insurance",
        )
        for query in negatives:
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")
                self.assertIsNone(result.matched_entry)

    def test_lookup_output_has_no_commercial_fields(self) -> None:
        forbidden = {"product", "products", "offer", "offers", "price", "prices", "affiliate", "provider"}
        result = lookup_offline_search_index("coffe grindr", self.index)
        self.assertIsNotNone(result.matched_entry)
        keys = set(result.matched_entry.to_dict().keys())
        self.assertTrue(forbidden.isdisjoint(keys))

    def test_stage7d_single_token_probes_resolve_through_generic_policy(self) -> None:
        expected = {
            "watch": "jewelry_watches_bags_fashion_accessories",
            "wach": "jewelry_watches_bags_fashion_accessories",
            "mixer": "kitchen_cooking_household",
            "mixr": "kitchen_cooking_household",
        }
        for query, category in expected.items():
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match")
                self.assertIsNotNone(result.matched_entry)
                self.assertEqual(result.matched_entry.mega_category_id, category)
                self.assertIn(result.confidence, {"medium", "high"})
                self.assertGreaterEqual(result.score, 0.84)
                self.assertIn(result.matched_entry.canonical_source, {"offline_canonical_vocabulary_coverage", "taxonomy_bridge", "taxonomy_clean_vocabulary"})

    def test_stage7d_single_token_generated_variants_have_generic_coverage(self) -> None:
        generated_variant_queries = (
            "wach",
            "mixr",
            "vacum",
            "bookshef",
            "powerbnk",
            "keyboad",
            "headphnes",
            "alternaotr",
            "helment",
            "driil",
            "wrnch",
            "thremometer",
        )
        for query in generated_variant_queries:
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match")
                self.assertIsNotNone(result.matched_entry)
                self.assertIn(result.matched_entry.canonical_source, {"offline_canonical_vocabulary_coverage", "taxonomy_bridge", "taxonomy_clean_vocabulary"})
                self.assertGreaterEqual(result.score, 0.84)

    def test_stage7d_minimum_single_token_products_across_categories(self) -> None:
        terms = (
            ("watch", "jewelry_watches_bags_fashion_accessories"),
            ("mixer", "kitchen_cooking_household"),
            ("vacuum", "home_appliances_laundry_climate"),
            ("bookshelf", "furniture_living_storage_smart_home"),
            ("powerbank", "phones_mobile_accessories"),
            ("keyboard", "computers_office_peripherals"),
            ("headphones", "audio_video_gaming_cameras"),
            ("alternator", "car_parts_service_maintenance"),
            ("tyre", "tyres_wheels_car_accessories"),
            ("helmet", "moto_bicycle_mobility_gear"),
            ("drill", "power_tools_workshop"),
            ("wrench", "hand_tools_consumables_measuring"),
            ("chainsaw", "garden_outdoor_repair_building"),
            ("thermometer", "health_wellness_safety_devices"),
            ("trimmer", "beauty_grooming_personal_care"),
            ("stroller", "baby_kids_pets_sports_outdoor"),
            ("hoodie", "clothing_apparel_workwear"),
            ("boots", "footwear_shoes_sneakers_boots"),
            ("earrings", "jewelry_watches_bags_fashion_accessories"),
            ("jigsaw", "power_tools_workshop"),
        )
        for query, category in terms:
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match")
                self.assertIsNotNone(result.matched_entry)
                self.assertEqual(result.matched_entry.mega_category_id, category)

    def test_stage7d_single_token_broad_negatives_remain_safe(self) -> None:
        for query in ("bank", "charger", "apple", "nike", "bosch", "insurance", "loan", "erp", "crm"):
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")
                self.assertIsNone(result.matched_entry)
                self.assertTrue(
                    ("broad_or_ambiguous_query" in result.reason_codes)
                    or ("single_token_broad_or_unsafe" in result.reason_codes)
                )

    def test_stage7d_single_token_collision_does_not_blindly_match(self) -> None:
        from picwise_search_memory.contracts import CanonicalVocabularyBuildReport, CanonicalVocabularyRecord, CanonicalVocabularyRegistry

        records = (
            CanonicalVocabularyRecord(
                canonical_id="id_cat_a",
                canonical_term="monitor",
                normalized_term="monitor",
                mega_category_id="computers_office_peripherals",
                source="offline_canonical_vocabulary_coverage",
                source_file="canonical_vocabulary_coverage.py",
                language="english",
                status="offline_source_only",
                schema_version="1.0.0",
                token_count=1,
                quality_flags=("offline_registry",),
            ),
            CanonicalVocabularyRecord(
                canonical_id="id_cat_b",
                canonical_term="monitor",
                normalized_term="monitor",
                mega_category_id="health_wellness_safety_devices",
                source="offline_canonical_vocabulary_coverage",
                source_file="canonical_vocabulary_coverage.py",
                language="english",
                status="offline_source_only",
                schema_version="1.0.0",
                token_count=1,
                quality_flags=("offline_registry",),
            ),
        )
        registry = CanonicalVocabularyRegistry(
            records=records,
            report=CanonicalVocabularyBuildReport(
                total_input_terms=2,
                total_records=2,
                rejected_terms=0,
                duplicate_terms=0,
                rejected_by_reason={},
                counts_by_mega_category={"computers_office_peripherals": 1, "health_wellness_safety_devices": 1},
                source="taxonomy_clean_vocabulary",
                schema_version="1.0.0",
                language="english",
                status="active",
            ),
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
        )
        index = build_offline_search_index(registry=registry, generated_variants=[])
        result = lookup_offline_search_index("monitor", index)
        self.assertEqual(result.status, "no_match")


if __name__ == "__main__":
    unittest.main()
