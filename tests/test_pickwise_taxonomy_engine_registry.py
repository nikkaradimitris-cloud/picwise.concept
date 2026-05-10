import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.engine_registry import get_engine_registry


class TestPickwiseTaxonomyEngineRegistry(unittest.TestCase):
    def test_exactly_six_engines(self) -> None:
        engines = get_engine_registry()
        self.assertEqual(len(engines), 6)

    def test_engine_ids_are_unique(self) -> None:
        engines = get_engine_registry()
        engine_ids = [engine["engine_id"] for engine in engines]
        self.assertEqual(len(engine_ids), len(set(engine_ids)))

    def test_each_engine_has_three_mega_categories(self) -> None:
        for engine in get_engine_registry():
            self.assertEqual(len(engine["mega_category_ids"]), 3)

    def test_fashion_engine_exists(self) -> None:
        engine_ids = [engine["engine_id"] for engine in get_engine_registry()]
        self.assertIn("fashion_footwear_jewelry_accessories_engine", engine_ids)

    def test_no_product_offer_price_affiliate_fields(self) -> None:
        forbidden = ("product", "offer", "price", "affiliate")
        for engine in get_engine_registry():
            for key in engine.keys():
                lowered = key.lower()
                self.assertFalse(any(token in lowered for token in forbidden))

    def test_json_serializable(self) -> None:
        payload = {"engines": get_engine_registry()}
        serialized = json.dumps(payload, sort_keys=True)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
