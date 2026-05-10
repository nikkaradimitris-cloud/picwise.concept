from __future__ import annotations

import json
import unittest

from src.picwise_nlu.specs_extractor import extract_specs


class LocalNLUSpecsExtractorTests(unittest.TestCase):
    def test_none_and_empty_safe_behavior(self) -> None:
        self.assertEqual(extract_specs(None)["specs"], {})
        self.assertEqual(extract_specs("")["specs"], {})

    def test_tyre_specs_from_195_65_r15(self) -> None:
        specs = extract_specs("195/65 R15", category="car_tyres")["specs"]
        self.assertEqual(specs["width"], "195")
        self.assertEqual(specs["profile"], "65")
        self.assertEqual(specs["rim"], "R15")

    def test_tyre_specs_from_205_55_r16(self) -> None:
        specs = extract_specs("205/55 R16", category="car_tyres")["specs"]
        self.assertEqual(specs["width"], "205")
        self.assertEqual(specs["profile"], "55")
        self.assertEqual(specs["rim"], "R16")

    def test_tyre_specs_from_225_45_r17(self) -> None:
        specs = extract_specs("225/45 R17", category="car_tyres")["specs"]
        self.assertEqual(specs["width"], "225")
        self.assertEqual(specs["profile"], "45")
        self.assertEqual(specs["rim"], "R17")

    def test_no_unsafe_random_triple_extraction(self) -> None:
        result = extract_specs("2024 05 10", category="car_tyres")
        self.assertEqual(result["specs"], {})

    def test_power_bank_capacity_from_20000mah(self) -> None:
        specs = extract_specs("powerbank 20000mah", category="power_banks")["specs"]
        self.assertEqual(specs["capacity_mah"], "20000")

    def test_power_bank_capacity_from_20_000_mah(self) -> None:
        specs = extract_specs("power bank 20.000 mah", category="power_banks")["specs"]
        self.assertEqual(specs["capacity_mah"], "20000")

    def test_calculator_model_code_from_fx_991(self) -> None:
        specs = extract_specs("casio fx-991", category="calculators")["specs"]
        self.assertEqual(specs["model_code"], "fx-991")

    def test_specs_are_json_serializable(self) -> None:
        result = extract_specs("195/65 R15")
        serialized = json.dumps(result["specs"], sort_keys=True)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
