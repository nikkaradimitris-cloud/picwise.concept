from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search.index_resolver_adapter import resolve_query_with_search_index  # noqa: E402
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402


class LiveSearchResolverTests(unittest.TestCase):
    def test_empty_query_skips_offline_index_build(self) -> None:
        import time

        import picwise_search.index_resolver_adapter as adapter

        adapter._CACHED_OFFLINE_INDEX = None
        started = time.time()
        result = resolve_query_with_search_index("")
        elapsed = time.time() - started

        self.assertLess(elapsed, 2.0)
        self.assertEqual(result.status, "no_match")
        self.assertIn("empty_query", result.reason_codes)
        self.assertIsNone(adapter._CACHED_OFFLINE_INDEX)

        resolution = resolve_live_search("")
        self.assertIn(
            resolution.resolver_state,
            {"not_understood", "blocked_or_unsafe"},
        )
        self.assertIn("empty_query", resolution.reason_codes)
        self.assertFalse(resolution.result_allowed)

    def test_index_adapter_matches_noisy_product_queries(self) -> None:
        expected = {
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
        for query, mega_category in expected.items():
            with self.subTest(query=query):
                result = resolve_query_with_search_index(query)
                self.assertEqual(result.status, "matched")
                self.assertEqual(result.mega_category_id, mega_category)
                self.assertIsNotNone(result.canonical_term)
                self.assertGreaterEqual(result.score, 0.75)

    def test_power_bank_connected_provider_state(self) -> None:
        resolution = resolve_live_search("power bank")
        self.assertEqual(resolution.canonical_category, "power_banks")
        self.assertEqual(resolution.mega_category_id, "phones_mobile_accessories")
        self.assertEqual(resolution.lower_level_provider_category, "power_banks")
        self.assertEqual(resolution.canonical_query, "power bank")
        self.assertEqual(resolution.provider_key, "manual_amazon_affiliate")
        self.assertEqual(resolution.provider_status, "connected")
        self.assertTrue(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "connected_provider_results")

    def test_power_bank_variants_resolve_connected_provider(self) -> None:
        variants = (
            "power bank",
            "powerbank",
            "portable charger",
            "battery pack",
            "batery pack",
            "battery pak",
            "externe batterie",
            "handy akku",
            "akku pack",
            "pauer bank",
            "powr bang",
            "portable chargr",
        )
        for query in variants:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.canonical_category, "power_banks")
                self.assertEqual(resolution.mega_category_id, "phones_mobile_accessories")
                self.assertEqual(resolution.lower_level_provider_category, "power_banks")
                self.assertEqual(resolution.canonical_query, "power bank")
                self.assertEqual(resolution.provider_key, "manual_amazon_affiliate")
                self.assertEqual(resolution.provider_status, "connected")
                self.assertTrue(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "connected_provider_results")

    def test_noisy_product_queries_become_understood_provider_not_connected(self) -> None:
        expected = {
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
        for query, mega_category in expected.items():
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.mega_category_id, mega_category)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")

    def test_stage7a_noisy_queries_cover_all_18_categories_as_not_connected(self) -> None:
        expected = {
            "vaccum cleaner": "home_appliances_laundry_climate",
            "washing machne": "home_appliances_laundry_climate",
            "coffe grindr": "kitchen_cooking_household",
            "air frier": "kitchen_cooking_household",
            "office chiar": "furniture_living_storage_smart_home",
            "storage cabnet": "furniture_living_storage_smart_home",
            "usb caible": "phones_mobile_accessories",
            "screen protecter": "phones_mobile_accessories",
            "gming mouse": "computers_office_peripherals",
            "laptop chrger": "phones_mobile_accessories",
            "bluethoth speker": "audio_video_gaming_cameras",
            "wirless headphones": "audio_video_gaming_cameras",
            "car batery": "car_parts_service_maintenance",
            "breake pads": "car_parts_service_maintenance",
            "car tyre": "tyres_wheels_car_accessories",
            "tyre 195 65 r15": "tyres_wheels_car_accessories",
            "bike helmt": "moto_bicycle_mobility_gear",
            "motorbike glovs": "moto_bicycle_mobility_gear",
            "cordless dril": "power_tools_workshop",
            "hammer dril": "power_tools_workshop",
            "screwdrivr set": "hand_tools_consumables_measuring",
            "digital calper": "hand_tools_consumables_measuring",
            "gardn shears": "garden_outdoor_repair_building",
            "leaf blwer": "garden_outdoor_repair_building",
            "blood presure monitor": "health_wellness_safety_devices",
            "pulse oxymeter": "health_wellness_safety_devices",
            "beard trimr": "beauty_grooming_personal_care",
            "hair dryier": "beauty_grooming_personal_care",
            "baby car seet": "baby_kids_pets_sports_outdoor",
            "dog leesh": "baby_kids_pets_sports_outdoor",
            "winter jakcet": "clothing_apparel_workwear",
            "workwear trousres": "clothing_apparel_workwear",
            "runing shoes": "footwear_shoes_sneakers_boots",
            "hikng boots": "footwear_shoes_sneakers_boots",
            "wrist watc": "jewelry_watches_bags_fashion_accessories",
            "handbg": "jewelry_watches_bags_fashion_accessories",
        }
        for query, mega_category in expected.items():
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.mega_category_id, mega_category)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
                self.assertEqual(resolution.provider_key, "not_connected")

    def test_random_garbage_maps_to_not_understood_state(self) -> None:
        for query in ("7437ηφσδνω==", "asdf@@@", "###$$$"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "not_understood")
                self.assertIn("resolver_state_not_understood", resolution.reason_codes)

    def test_known_non_provider_category_returns_understood_provider_not_connected(self) -> None:
        resolution = resolve_live_search("wall charger")
        self.assertEqual(resolution.mega_category_id, "phones_mobile_accessories")
        self.assertIsNone(resolution.lower_level_provider_category)
        self.assertEqual(resolution.provider_status, "not_connected")
        self.assertFalse(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
        self.assertIn("provider_not_connected", resolution.reason_codes)

    def test_understood_but_not_connected_category(self) -> None:
        resolution = resolve_live_search("goodyear tyres 195/65 r15")
        self.assertEqual(resolution.mega_category_id, "tyres_wheels_car_accessories")
        self.assertIsNone(resolution.lower_level_provider_category)
        self.assertEqual(resolution.provider_status, "not_connected")
        self.assertFalse(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
        self.assertIn("provider_not_connected", resolution.reason_codes)

    def test_stage12b_retail_mega_categories_understood_in_english(self) -> None:
        expected = {
            "washing machine": "home_appliances_laundry_climate",
            "air fryer": "kitchen_cooking_household",
            "office chair": "furniture_living_storage_smart_home",
            "wireless charger": "phones_mobile_accessories",
            "laptop": "computers_office_peripherals",
            "wireless headphones": "audio_video_gaming_cameras",
            "brake pads": "car_parts_service_maintenance",
            "car tyres 225/45 r17": "tyres_wheels_car_accessories",
            "motorcycle helmet": "moto_bicycle_mobility_gear",
            "cordless drill": "power_tools_workshop",
            "screwdriver set": "hand_tools_consumables_measuring",
            "garden hose": "garden_outdoor_repair_building",
            "blood pressure monitor": "health_wellness_safety_devices",
            "hair dryer": "beauty_grooming_personal_care",
            "baby stroller": "baby_kids_pets_sports_outdoor",
            "mens jacket": "clothing_apparel_workwear",
            "running shoes": "footwear_shoes_sneakers_boots",
            "wrist watch": "jewelry_watches_bags_fashion_accessories",
        }
        for query, mega_category in expected.items():
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.mega_category_id, mega_category)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")

    def test_broad_negatives_remain_safe_not_understood(self) -> None:
        for query in (
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
        ):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertIsNone(resolution.mega_category_id)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "not_understood")
                self.assertEqual(resolution.provider_status, "not_connected")

    def test_stage7d_single_token_product_queries_become_understood_provider_not_connected(self) -> None:
        expected = {
            "watch": "jewelry_watches_bags_fashion_accessories",
            "wach": "jewelry_watches_bags_fashion_accessories",
            "mixer": "kitchen_cooking_household",
            "mixr": "kitchen_cooking_household",
        }
        for query, mega_category in expected.items():
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.mega_category_id, mega_category)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
                self.assertEqual(resolution.provider_key, "not_connected")

    def test_exact_canonical_and_product_head_tokens_understood_provider_not_connected(self) -> None:
        expected = {
            "jewelry": "jewelry_watches_bags_fashion_accessories",
            "jewellery": "jewelry_watches_bags_fashion_accessories",
            "bluetooth": "audio_video_gaming_cameras",
            "bluetooth speaker": "audio_video_gaming_cameras",
        }
        for query, mega_category in expected.items():
            with self.subTest(query=query):
                index_result = resolve_query_with_search_index(query)
                self.assertEqual(index_result.status, "matched", index_result.reason_codes)
                self.assertEqual(index_result.mega_category_id, mega_category)
                self.assertGreaterEqual(index_result.score, 0.84)

                resolution = resolve_live_search(query)
                self.assertEqual(resolution.mega_category_id, mega_category)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")

    def test_collision_homograph_token_stays_not_understood(self) -> None:
        resolution = resolve_live_search("bots")
        self.assertEqual(resolution.resolver_state, "not_understood")
        self.assertFalse(resolution.result_allowed)

    def test_no_connected_provider_except_power_banks(self) -> None:
        queries = (
            "coffe grindr",
            "bluethoth speker",
            "car batery",
            "baby car seet",
            "usb caible",
        )
        for query in queries:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.provider_key, "not_connected")
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)


if __name__ == "__main__":
    unittest.main()
