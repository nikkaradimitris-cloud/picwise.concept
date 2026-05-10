from __future__ import annotations

import unittest

from src.picwise_nlu.brand_resolver import resolve_brand_candidates


class LocalNLUBrandResolverTests(unittest.TestCase):
    def test_none_and_empty_safe_behavior(self) -> None:
        self.assertEqual(resolve_brand_candidates(None)["brand_candidates"], [])
        self.assertEqual(resolve_brand_candidates("")["brand_candidates"], [])

    def test_goodyear(self) -> None:
        self.assertEqual(resolve_brand_candidates("goodyear")["brand_candidates"], ["Goodyear"])

    def test_bridgestone(self) -> None:
        self.assertEqual(resolve_brand_candidates("bridgestone")["brand_candidates"], ["Bridgestone"])

    def test_michelin(self) -> None:
        self.assertEqual(resolve_brand_candidates("michelin")["brand_candidates"], ["Michelin"])

    def test_continental(self) -> None:
        self.assertEqual(resolve_brand_candidates("continental")["brand_candidates"], ["Continental"])

    def test_casio(self) -> None:
        self.assertEqual(resolve_brand_candidates("casio")["brand_candidates"], ["Casio"])

    def test_anker(self) -> None:
        self.assertEqual(resolve_brand_candidates("anker")["brand_candidates"], ["Anker"])

    def test_xiaomi(self) -> None:
        self.assertEqual(resolve_brand_candidates("xiaomi")["brand_candidates"], ["Xiaomi"])

    def test_samsung(self) -> None:
        self.assertEqual(resolve_brand_candidates("samsung")["brand_candidates"], ["Samsung"])

    def test_unknown_brand_returns_empty_and_no_invention(self) -> None:
        result = resolve_brand_candidates("randombrand")
        self.assertEqual(result["brand_candidates"], [])
        self.assertNotIn("RandomBrand", result["brand_candidates"])


if __name__ == "__main__":
    unittest.main()
