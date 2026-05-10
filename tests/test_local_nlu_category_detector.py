from __future__ import annotations

import unittest

from src.picwise_nlu.category_detector import detect_category


class LocalNLUCategoryDetectorTests(unittest.TestCase):
    def test_none_and_empty_safe_behavior(self) -> None:
        self.assertEqual(detect_category(None)["category"], None)
        self.assertEqual(detect_category("")["category"], None)

    def test_lastixa_with_tire_size_detects_car_tyres(self) -> None:
        result = detect_category("lastixa 195/65 R15")
        self.assertEqual(result["category"], "car_tyres")

    def test_lastiha_greek_with_tire_size_detects_car_tyres(self) -> None:
        result = detect_category("λαστιχα 195/65 R15")
        self.assertEqual(result["category"], "car_tyres")

    def test_tyres_with_tire_size_detects_car_tyres(self) -> None:
        result = detect_category("tyres 205/55 R16")
        self.assertEqual(result["category"], "car_tyres")

    def test_calculator_exam_context_detects_calculators(self) -> None:
        result = detect_category("κομπιουτερακι πανελληνιες")
        self.assertEqual(result["category"], "calculators")

    def test_calculator_casio_exam_detects_calculators(self) -> None:
        result = detect_category("calculator casio exam")
        self.assertEqual(result["category"], "calculators")

    def test_power_bank_iphone_capacity_detects_power_banks(self) -> None:
        result = detect_category("power bank iphone 20000mah")
        self.assertEqual(result["category"], "power_banks")

    def test_powerbank_with_capacity_detects_power_banks(self) -> None:
        result = detect_category("powerbank 10000 mah")
        self.assertEqual(result["category"], "power_banks")

    def test_unknown_query_returns_none_with_low_confidence(self) -> None:
        result = detect_category("best thing for home")
        self.assertIsNone(result["category"])
        self.assertLessEqual(result["confidence"], 0.2)

    def test_no_product_or_offer_result_generated(self) -> None:
        result = detect_category("tyres 205/55 R16")
        self.assertNotIn("offers", result)
        self.assertNotIn("products", result)


if __name__ == "__main__":
    unittest.main()
