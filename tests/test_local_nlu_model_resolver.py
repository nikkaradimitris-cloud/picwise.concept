from __future__ import annotations

import unittest

from src.picwise_nlu.model_resolver import resolve_model_candidates


class LocalNLUModelResolverTests(unittest.TestCase):
    def test_none_and_empty_safe_behavior(self) -> None:
        self.assertEqual(resolve_model_candidates(None)["model_candidates"], [])
        self.assertEqual(resolve_model_candidates("")["model_candidates"], [])

    def test_efficientgrip(self) -> None:
        result = resolve_model_candidates("efficientgrip")
        self.assertIn("EfficientGrip", result["model_candidates"])

    def test_efficientgrip_performance_2(self) -> None:
        result = resolve_model_candidates("efficientgrip performance 2")
        self.assertIn("EfficientGrip Performance 2", result["model_candidates"])

    def test_turanza(self) -> None:
        result = resolve_model_candidates("turanza")
        self.assertIn("Turanza", result["model_candidates"])

    def test_primacy_4(self) -> None:
        result = resolve_model_candidates("primacy 4")
        self.assertIn("Primacy 4", result["model_candidates"])

    def test_ecocontact(self) -> None:
        result = resolve_model_candidates("ecocontact")
        self.assertIn("EcoContact", result["model_candidates"])

    def test_premiumcontact(self) -> None:
        result = resolve_model_candidates("premiumcontact")
        self.assertIn("PremiumContact", result["model_candidates"])

    def test_fx_991(self) -> None:
        result = resolve_model_candidates("fx 991")
        self.assertIn("fx-991", result["model_candidates"])

    def test_fx_991ex(self) -> None:
        result = resolve_model_candidates("fx-991ex")
        self.assertIn("fx-991ex", result["model_candidates"])

    def test_20000mah(self) -> None:
        result = resolve_model_candidates("20000mah")
        self.assertIn("20000mah", result["model_candidates"])

    def test_unknown_model_returns_empty_and_no_invention(self) -> None:
        result = resolve_model_candidates("unknownmodel")
        self.assertEqual(result["model_candidates"], [])
        self.assertNotIn("UnknownModel", result["model_candidates"])


if __name__ == "__main__":
    unittest.main()
