from __future__ import annotations

import unittest

from src.picwise_nlu.category_detector import detect_category


class LocalNLUCategoryDetectorTests(unittest.TestCase):
    def test_none_and_empty_safe_behavior(self) -> None:
        self.assertEqual(detect_category(None)["category"], None)
        self.assertEqual(detect_category("")["category"], None)

    def test_power_bank_iphone_capacity_detects_power_banks(self) -> None:
        result = detect_category("power bank iphone 20000mah")
        self.assertEqual(result["category"], "power_banks")
        self.assertEqual(result["mega_category_id"], "phones_mobile_accessories")
        self.assertEqual(result["lower_level_provider_category"], "power_banks")

    def test_powerbank_with_capacity_detects_power_banks(self) -> None:
        result = detect_category("powerbank 10000 mah")
        self.assertEqual(result["category"], "power_banks")

    def test_battery_pack_detects_power_banks(self) -> None:
        result = detect_category("battery pack")
        self.assertEqual(result["category"], "power_banks")

    def test_portable_charger_detects_power_banks(self) -> None:
        result = detect_category("portable charger")
        self.assertEqual(result["category"], "power_banks")

    def test_unknown_query_returns_none_with_low_confidence(self) -> None:
        result = detect_category("best thing for home")
        self.assertIsNone(result["category"])
        self.assertLessEqual(result["confidence"], 0.2)

    def test_retail_mega_categories_have_english_detection(self) -> None:
        matrix = {
            "home_appliances_laundry_climate": (
                "washing machine",
                "washng machine",
                "airconditioner",
            ),
            "kitchen_cooking_household": (
                "air fryer",
                "blnder",
                "coffee maker",
            ),
            "furniture_living_storage_smart_home": (
                "office chair",
                "officechair",
                "smart bulb",
            ),
            "phones_mobile_accessories": (
                "wireless charger",
                "iphone charger",
                "screen protector",
            ),
            "computers_office_peripherals": (
                "laptop",
                "wireless mouse",
                "printer",
            ),
            "audio_video_gaming_cameras": (
                "wireless headphones",
                "gaming headset",
                "action camera",
            ),
            "car_parts_service_maintenance": (
                "brake pads",
                "oil filter",
                "wiper blades",
            ),
            "tyres_wheels_car_accessories": (
                "car tyres 205/55 r16",
                "car tires",
                "all season tires",
            ),
            "moto_bicycle_mobility_gear": (
                "motorbike helmet",
                "bicycle lock",
                "bike lights",
            ),
            "power_tools_workshop": (
                "cordless drill",
                "cordlessdrill",
                "angle grinder",
            ),
            "hand_tools_consumables_measuring": (
                "screwdriver set",
                "screwdriverset",
                "digital caliper",
            ),
            "garden_outdoor_repair_building": (
                "garden hose",
                "gardenhose",
                "leaf blower",
            ),
            "health_wellness_safety_devices": (
                "blood pressure monitor",
                "bloodpressure monitor",
                "pulse oximeter",
            ),
            "beauty_grooming_personal_care": (
                "hair dryer",
                "hairdryer",
                "beard trimmer",
            ),
            "baby_kids_pets_sports_outdoor": (
                "baby stroller",
                "babystroller",
                "pet leash",
            ),
            "clothing_apparel_workwear": (
                "mens jacket",
                "workwear trousers",
                "rain jacket",
            ),
            "footwear_shoes_sneakers_boots": (
                "running shoes",
                "runing shoes",
                "hiking boots",
            ),
            "jewelry_watches_bags_fashion_accessories": (
                "wrist watch",
                "wristwatch",
                "handbag",
            ),
        }
        for mega_category_id, queries in matrix.items():
            for query in queries:
                with self.subTest(mega_category_id=mega_category_id, query=query):
                    result = detect_category(query)
                    self.assertEqual(result["mega_category_id"], mega_category_id)

    def test_out_of_scope_vertical_terms_do_not_force_retail_category(self) -> None:
        for query in ("ERP software", "CRM platform", "bank loan", "insurance policy", "accounting software"):
            with self.subTest(query=query):
                result = detect_category(query)
                self.assertIsNone(result["category"])
                self.assertIn("out_of_scope_non_retail_vertical", result["reason_codes"])

    def test_overmatch_single_token_guards(self) -> None:
        for query in ("bank", "apple", "galaxy", "bosch", "nike"):
            with self.subTest(query=query):
                result = detect_category(query)
                self.assertIsNone(result["category"])
                self.assertIn("overmatch_guard_single_token", result["reason_codes"])

    def test_no_product_or_offer_result_generated(self) -> None:
        result = detect_category("car tyres 205/55 R16")
        self.assertNotIn("offers", result)
        self.assertNotIn("products", result)


if __name__ == "__main__":
    unittest.main()
