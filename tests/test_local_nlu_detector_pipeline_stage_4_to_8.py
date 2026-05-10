from __future__ import annotations

import unittest

from src.picwise_nlu.detector_pipeline import analyze_normalized_query
from src.picwise_nlu.normalizer import normalize_query
from src.picwise_nlu.typo_normalizer import normalize_greeklish_and_typos


def _run_pipeline(raw_query: str) -> dict:
    normalized = normalize_query(raw_query)
    normalized = normalize_greeklish_and_typos(normalized)
    return analyze_normalized_query(normalized)


class LocalNLUDetectorPipelineStage4To8Tests(unittest.TestCase):
    def test_tyre_flow_goodyear_efficientgrip_comfort(self) -> None:
        result = _run_pipeline("goodyar eficiency grim 195 65 15 aneto")
        self.assertEqual(result["category"], "car_tyres")
        self.assertIn("Goodyear", result["brand_candidates"])
        self.assertIn("EfficientGrip", result["model_candidates"])
        self.assertEqual(result["specs"].get("width"), "195")
        self.assertEqual(result["specs"].get("profile"), "65")
        self.assertEqual(result["specs"].get("rim"), "R15")
        self.assertIn("comfort", result["buying_priority"])

    def test_tyre_flow_bridgestone_turanza_low_noise(self) -> None:
        result = _run_pipeline("brizestone touransa 195/65/15 isixo")
        self.assertEqual(result["category"], "car_tyres")
        self.assertIn("Bridgestone", result["brand_candidates"])
        self.assertIn("Turanza", result["model_candidates"])
        self.assertEqual(result["specs"].get("width"), "195")
        self.assertEqual(result["specs"].get("profile"), "65")
        self.assertEqual(result["specs"].get("rim"), "R15")
        self.assertIn("low_noise", result["buying_priority"])

    def test_calculator_flow_casio_exam_fx991(self) -> None:
        result = _run_pipeline("kompiouteraki casio gia panellinies fx 991")
        self.assertEqual(result["category"], "calculators")
        self.assertIn("Casio", result["brand_candidates"])
        self.assertIn("fx-991", result["model_candidates"])
        self.assertEqual(result["specs"].get("model_code"), "fx-991")
        self.assertIn("exam_approved", result["buying_priority"])

    def test_power_bank_flow_capacity_and_fast_charge(self) -> None:
        result = _run_pipeline("power bank iphone 20000mah fast charge")
        self.assertEqual(result["category"], "power_banks")
        self.assertEqual(result["specs"].get("capacity_mah"), "20000")
        self.assertTrue(
            "battery_life" in result["buying_priority"]
            or "fast_charging" in result["buying_priority"]
        )

    def test_unknown_query_stays_safe_and_does_not_invent(self) -> None:
        result = _run_pipeline("totally unrelated request")
        self.assertIsNone(result["category"])
        self.assertEqual(result["brand_candidates"], [])
        self.assertEqual(result["model_candidates"], [])
        self.assertNotIn("offers", result)
        self.assertNotIn("products", result)


if __name__ == "__main__":
    unittest.main()
