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
            "bank loan",
            "car insurance policy",
        ):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertIsNone(resolution.mega_category_id)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.resolver_state, "not_understood")
                self.assertEqual(resolution.provider_status, "not_connected")

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
