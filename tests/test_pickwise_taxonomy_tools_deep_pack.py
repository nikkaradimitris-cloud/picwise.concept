import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs.tools_diy_garden_repair import get_tools_diy_garden_repair_pack

_EXPECTED_MEGA_CATEGORIES = [
    "power_tools_workshop",
    "hand_tools_consumables_measuring",
    "garden_outdoor_repair_building",
]
_FORBIDDEN_KEYS = {
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "affiliate",
    "commission",
    "seller",
    "store_offer",
}


def _contains_forbidden_keys(payload: object) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in _FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_keys(value):
                return True
        return False
    if isinstance(payload, list):
        return any(_contains_forbidden_keys(item) for item in payload)
    return False


class TestPickwiseTaxonomyToolsDeepPack(unittest.TestCase):
    def test_pack_exists(self) -> None:
        pack = get_tools_diy_garden_repair_pack()
        self.assertIsInstance(pack, dict)
        self.assertIn("mega_categories", pack)

    def test_engine_id_matches_tools_engine(self) -> None:
        pack = get_tools_diy_garden_repair_pack()
        self.assertEqual(pack["engine_id"], "tools_diy_garden_repair_engine")

    def test_exactly_three_mega_categories(self) -> None:
        pack = get_tools_diy_garden_repair_pack()
        self.assertEqual(len(pack["mega_categories"]), 3)

    def test_mega_category_ids_match_expected_list(self) -> None:
        pack = get_tools_diy_garden_repair_pack()
        mega_ids = [record["mega_category_id"] for record in pack["mega_categories"]]
        self.assertEqual(mega_ids, _EXPECTED_MEGA_CATEGORIES)

    def test_every_mega_category_has_required_depth_fields(self) -> None:
        required_list_fields = (
            "departments",
            "subcategories",
            "product_families",
            "spec_fields",
            "buying_priorities",
            "alias_terms",
            "greeklish_terms",
            "typo_terms",
            "intent_patterns",
            "ambiguity_rules",
        )
        for record in get_tools_diy_garden_repair_pack()["mega_categories"]:
            self.assertIn("mega_category_id", record)
            self.assertIn("engine_id", record)
            self.assertIn("display_name", record)
            for field in required_list_fields:
                self.assertIn(field, record)
                self.assertIsInstance(record[field], list)
                self.assertGreater(len(record[field]), 0)

            # Alias compatibility fields requested in stage instructions.
            self.assertIn("aliases", record)
            self.assertIn("greeklish", record)
            self.assertIn("typos", record)
            self.assertIsInstance(record["aliases"], list)
            self.assertIsInstance(record["greeklish"], list)
            self.assertIsInstance(record["typos"], list)

    def test_pack_is_json_serializable(self) -> None:
        payload = {"deep_pack": get_tools_diy_garden_repair_pack()}
        serialized = json.dumps(payload, sort_keys=True)
        self.assertIsInstance(serialized, str)

    def test_no_forbidden_product_offer_price_affiliate_fields(self) -> None:
        pack = get_tools_diy_garden_repair_pack()
        self.assertFalse(_contains_forbidden_keys(pack))


if __name__ == "__main__":
    unittest.main()
