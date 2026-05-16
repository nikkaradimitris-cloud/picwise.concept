from __future__ import annotations

import inspect
import unittest

from src.picwise_nlu.normalizer import normalize_query
from src.picwise_nlu.typo_normalizer import (
    normalize_greeklish_and_typos,
    normalize_greeklish_terms,
    normalize_known_aliases,
    tokenize_for_alias_matching,
)
import src.picwise_nlu.typo_normalizer as typo_normalizer_module


class LocalNLUGreeklishTypoNormalizerTests(unittest.TestCase):
    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos(""), "")

    def test_none_input_safe_behavior(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos(None), "")
        self.assertEqual(normalize_known_aliases(None), "")
        self.assertEqual(normalize_greeklish_terms(None), "")
        self.assertEqual(tokenize_for_alias_matching(None), [])

    def test_goodyar_to_goodyear(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("goodyar"), "goodyear")

    def test_gudiar_to_goodyear(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("gudiar"), "goodyear")

    def test_brizestone_to_bridgestone(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("brizestone"), "bridgestone")

    def test_micelin_to_michelin(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("micelin"), "michelin")

    def test_continantal_to_continental(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("continantal"), "continental")

    def test_eficiency_grim_to_efficientgrip(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("eficiency grim"), "efficientgrip")

    def test_efficiency_grim_to_efficientgrip(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("efficiency grim"), "efficientgrip")

    def test_efficient_grip_performance_2_stays_sensible(self) -> None:
        self.assertEqual(
            normalize_greeklish_and_typos("efficient grip performance 2"),
            "efficientgrip performance 2",
        )

    def test_touransa_to_turanza(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("touransa"), "turanza")

    def test_kompiouteraki_to_greek(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("kompiouteraki"), "κομπιουτερακι")

    def test_panellinies_to_greek(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("panellinies"), "πανελληνιες")

    def test_aneto_to_greek(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("aneto"), "ανετο")

    def test_isixo_to_greek(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos("isixo"), "ησυχο")

    def test_mixed_messy_tyre_query_preserves_tyre_size(self) -> None:
        raw = "goodyar eficiency grim 195 65 15 aneto"
        stage2 = normalize_query(raw)
        result = normalize_greeklish_and_typos(stage2)
        self.assertIn("goodyear", result)
        self.assertIn("efficientgrip", result)
        self.assertIn("195/65 R15", result)
        self.assertIn("ανετο", result)

    def test_contextual_power_bank_noisy_variants_map_to_power_bank(self) -> None:
        variants = (
            "παουερ μπακ",
            "παουερμπακ",
            "παουερ μπανγκ",
            "pauer bank",
            "paouer bank",
            "paouer bang",
            "power bang",
            "powe bank",
            "powr bang",
            "power bak",
        )
        for query in variants:
            with self.subTest(query=query):
                normalized = normalize_query(query)
                resolved = normalize_greeklish_and_typos(normalized)
                self.assertEqual(resolved, "power bank")

    def test_contextual_portable_charger_and_battery_pack_typos(self) -> None:
        portable_variants = ("portable chargr", "portable chargar")
        for query in portable_variants:
            with self.subTest(query=query):
                normalized = normalize_query(query)
                resolved = normalize_greeklish_and_typos(normalized)
                self.assertEqual(resolved, "portable charger")

        normalized_battery = normalize_query("batery pak")
        self.assertEqual(normalize_greeklish_and_typos(normalized_battery), "battery pack")

    def test_safety_no_global_unsafe_replacements(self) -> None:
        self.assertEqual(normalize_greeklish_and_typos(normalize_query("bank account")), "bank account")
        self.assertEqual(normalize_greeklish_and_typos(normalize_query("river bank")), "river bank")
        self.assertEqual(normalize_greeklish_and_typos(normalize_query("blood bank")), "blood bank")
        self.assertEqual(normalize_greeklish_and_typos(normalize_query("bang speaker")), "bang speaker")
        self.assertEqual(normalize_greeklish_and_typos(normalize_query("wall charger")), "wall charger")

    def test_no_structured_intent_is_produced(self) -> None:
        result = normalize_greeklish_and_typos("goodyar eficiency grim")
        self.assertIsInstance(result, str)
        self.assertNotIsInstance(result, dict)
        self.assertNotIsInstance(result, list)

    def test_no_category_brand_model_resolver_object_returned(self) -> None:
        result = normalize_greeklish_and_typos("micelin turansa")
        self.assertIsInstance(result, str)
        self.assertFalse(hasattr(result, "category"))
        self.assertFalse(hasattr(result, "brand"))
        self.assertFalse(hasattr(result, "model"))

    def test_no_claude_api_live_llm_requirement_exists(self) -> None:
        module_source = inspect.getsource(typo_normalizer_module).lower()
        self.assertNotIn("claude", module_source)
        self.assertNotIn("openai", module_source)
        self.assertNotIn("api_key", module_source)
        self.assertNotIn("http://", module_source)
        self.assertNotIn("https://", module_source)


if __name__ == "__main__":
    unittest.main()
