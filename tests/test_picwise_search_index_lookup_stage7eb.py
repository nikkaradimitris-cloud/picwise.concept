from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_memory import (  # noqa: E402
    build_canonical_vocabulary_registry,
    build_offline_search_index,
    lookup_offline_search_index,
)


def _changed_implementation_lines() -> str:
    import subprocess

    proc = subprocess.run(
        [
            "git",
            "diff",
            "-U0",
            "--",
            "src/picwise_search_memory/",
            "src/picwise_nlu/query_variant_generator.py",
            "src/picwise_search/index_resolver_adapter.py",
            "src/picwise_search/live_search_resolver.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout


class PicWiseSearchIndexLookupStage7EBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = build_canonical_vocabulary_registry()
        cls.index = build_offline_search_index(cls.registry)

    def test_changed_implementation_lines_have_no_probe_specific_logic(self) -> None:
        diff = _changed_implementation_lines()
        forbidden_markers = (
            "if query ==",
            "hardcoded",
            "fixed probe",
            "probe examples",
            "jewelery",
            "jewlery",
            "jwlry",
            "joulary",
            "bluethoth",
            "baby monitor",
        )
        for line in diff.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            lowered = line[1:].lower()
            for marker in forbidden_markers:
                if marker in lowered:
                    self.fail(f"Probe-specific marker {marker!r} found in changed line: {line}")

    def test_spelling_family_recovery_across_categories(self) -> None:
        probes = {
            "jewellery": "jewelry_watches_bags_fashion_accessories",
            "jewelery": "jewelry_watches_bags_fashion_accessories",
            "jewlery": "jewelry_watches_bags_fashion_accessories",
            "jwlry": "jewelry_watches_bags_fashion_accessories",
            "tyre": "tyres_wheels_car_accessories",
            "car tire": "tyres_wheels_car_accessories",
            "vaccum": "home_appliances_laundry_climate",
            "vacum": "home_appliances_laundry_climate",
            "headphnes": "audio_video_gaming_cameras",
            "headphones": "audio_video_gaming_cameras",
            "alternaotr": "car_parts_service_maintenance",
            "alternator": "car_parts_service_maintenance",
            "helment": "moto_bicycle_mobility_gear",
            "helmet": "moto_bicycle_mobility_gear",
            "powerbnk": "phones_mobile_accessories",
            "powerbank": "phones_mobile_accessories",
            "wach": "jewelry_watches_bags_fashion_accessories",
            "watch": "jewelry_watches_bags_fashion_accessories",
            "mixr": "kitchen_cooking_household",
            "mixer": "kitchen_cooking_household",
            "bookshef": "furniture_living_storage_smart_home",
            "bookshelf": "furniture_living_storage_smart_home",
            "keyboad": "computers_office_peripherals",
            "keyboard": "computers_office_peripherals",
            "driil": "power_tools_workshop",
            "drill": "power_tools_workshop",
            "thremometer": "health_wellness_safety_devices",
            "thermometer": "health_wellness_safety_devices",
        }
        categories = set()
        for query, category in probes.items():
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match", result.reason_codes)
                self.assertIsNotNone(result.matched_entry)
                self.assertEqual(result.matched_entry.mega_category_id, category)
                categories.add(category)
        self.assertGreaterEqual(len(categories), 8)

    def test_standalone_product_tokens_across_categories(self) -> None:
        probes = {
            "shoes": "footwear_shoes_sneakers_boots",
            "shears": "garden_outdoor_repair_building",
            "watch": "jewelry_watches_bags_fashion_accessories",
            "mixer": "kitchen_cooking_household",
            "vacuum": "home_appliances_laundry_climate",
            "keyboard": "computers_office_peripherals",
            "drill": "power_tools_workshop",
            "stroller": "baby_kids_pets_sports_outdoor",
            "boots": "footwear_shoes_sneakers_boots",
            "earrings": "jewelry_watches_bags_fashion_accessories",
            "trimmer": "beauty_grooming_personal_care",
            "chainsaw": "garden_outdoor_repair_building",
            "hoodie": "clothing_apparel_workwear",
            "jigsaw": "power_tools_workshop",
            "tyre": "tyres_wheels_car_accessories",
            "bookshelf": "furniture_living_storage_smart_home",
            "thermometer": "health_wellness_safety_devices",
            "bluetooth": "audio_video_gaming_cameras",
            "jewelry": "jewelry_watches_bags_fashion_accessories",
            "sneakers": "footwear_shoes_sneakers_boots",
        }
        categories = set()
        for query, category in probes.items():
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match", result.reason_codes)
                self.assertIsNotNone(result.matched_entry)
                self.assertEqual(result.matched_entry.mega_category_id, category)
                categories.add(category)
        self.assertGreaterEqual(len(categories), 8)

    def test_meta_noise_terms_are_rejected(self) -> None:
        for query in ("categories", "guides", "systems", "premium", "taxonomy"):
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")
                self.assertIsNone(result.matched_entry)

    def test_collision_homograph_probe_is_safe(self) -> None:
        bots = lookup_offline_search_index("bots", self.index)
        self.assertEqual(bots.status, "no_match")
        boots = lookup_offline_search_index("boots", self.index)
        self.assertEqual(boots.status, "match")
        self.assertEqual(boots.matched_entry.mega_category_id, "footwear_shoes_sneakers_boots")

    def test_broad_negatives_remain_safe(self) -> None:
        for query in (
            "bank",
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
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")
                self.assertIsNone(result.matched_entry)


if __name__ == "__main__":
    unittest.main()
