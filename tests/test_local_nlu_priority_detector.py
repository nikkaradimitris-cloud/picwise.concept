from __future__ import annotations

import unittest

from src.picwise_nlu.priority_detector import detect_buying_priority


class LocalNLUPriorityDetectorTests(unittest.TestCase):
    def test_none_and_empty_safe_behavior(self) -> None:
        self.assertEqual(detect_buying_priority(None)["buying_priority"], [])
        self.assertEqual(detect_buying_priority("")["buying_priority"], [])

    def test_aneto_maps_to_comfort(self) -> None:
        result = detect_buying_priority("ανετο", category="car_tyres")
        self.assertIn("comfort", result["buying_priority"])

    def test_isyxo_maps_to_low_noise(self) -> None:
        result = detect_buying_priority("ησυχο", category="car_tyres")
        self.assertIn("low_noise", result["buying_priority"])

    def test_fthino_maps_to_budget(self) -> None:
        result = detect_buying_priority("φτηνο", category="car_tyres")
        self.assertIn("budget", result["buying_priority"])

    def test_oikonomiko_maps_to_budget(self) -> None:
        result = detect_buying_priority("οικονομικο", category="car_tyres")
        self.assertIn("budget", result["buying_priority"])

    def test_vroxi_maps_to_wet_grip(self) -> None:
        result = detect_buying_priority("βροχη", category="car_tyres")
        self.assertIn("wet_grip", result["buying_priority"])

    def test_battery_life_priority(self) -> None:
        result_a = detect_buying_priority("battery life", category="power_banks")
        result_b = detect_buying_priority("μεγαλη μπαταρια", category="power_banks")
        self.assertIn("battery_life", result_a["buying_priority"])
        self.assertIn("battery_life", result_b["buying_priority"])

    def test_fast_charging_priority(self) -> None:
        result_a = detect_buying_priority("fast charge", category="power_banks")
        result_b = detect_buying_priority("γρηγορη φορτιση", category="power_banks")
        self.assertIn("fast_charging", result_a["buying_priority"])
        self.assertIn("fast_charging", result_b["buying_priority"])

    def test_exam_approved_priority(self) -> None:
        result_a = detect_buying_priority("πανελληνιες", category="calculators")
        result_b = detect_buying_priority("εξετασεις", category="calculators")
        self.assertIn("exam_approved", result_a["buying_priority"])
        self.assertIn("exam_approved", result_b["buying_priority"])

    def test_unknown_query_has_no_unrelated_priority(self) -> None:
        result = detect_buying_priority("hello random query")
        self.assertEqual(result["buying_priority"], [])


if __name__ == "__main__":
    unittest.main()
