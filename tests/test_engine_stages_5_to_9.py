from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_contracts import ContractValidationError, DecisionDepth, ProductBrain  # noqa: E402
from picwise_engine import (  # noqa: E402
    BrainSelector,
    DecisionArbitrator,
    DecisionDepthSelector,
    PicwiseDecisionEngine,
    ProductCandidateAdapter,
)


def base_candidate(product_id: str, role: str) -> dict:
    return {
        "product_id": product_id,
        "title": f"Choice {product_id}",
        "merchant_or_provider": "Provider A",
        "price_or_cost_display": "EUR 49",
        "role": role,
        "decision_label": f"{role} option with clear fit",
        "subtitle": "EUR 49 • reliable delivery • low decision risk",
        "key_reasons": ["Clear role fit", "Strong reliability"],
        "risks_or_limitations": "Includes warranty limits and return conditions.",
        "cta_label": "View in Store",
        "redirect_target": "https://provider.example/product",
        "tracking_metadata": {"source": "test"},
    }


def build_engine_context() -> dict:
    return {
        "category": "electronics",
        "product_type": "power bank",
        "service_type": "retail",
        "risk_level": "medium",
        "price_band": "mid",
        "missing_data_states": ["unknown"],
        "tracking_context": {"session_hint": "stage-5-9"},
    }


class IntegratedEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PicwiseDecisionEngine()

    def test_engine_returns_valid_output_exactly_4_choices_and_1_recommended(self) -> None:
        candidates = [
            base_candidate("c1", "budget"),
            base_candidate("c2", "value"),
            base_candidate("c3", "best_overall"),
            base_candidate("c4", "premium"),
            base_candidate("c5", "value"),
        ]
        output = self.engine.run("best power bank for iphone", candidates, build_engine_context())
        self.assertEqual(len(output.choices), 4)
        self.assertEqual(sum(1 for choice in output.choices if choice.is_recommended), 1)
        selected_ids = {choice.product_id for choice in output.choices}
        self.assertIn(output.recommended_product_id, selected_ids)

    def test_engine_fails_with_fewer_than_4_valid_candidates(self) -> None:
        candidates = [
            base_candidate("c1", "budget"),
            base_candidate("c2", "value"),
            base_candidate("c3", "best_overall"),
        ]
        with self.assertRaises(ContractValidationError):
            self.engine.run("best power bank for iphone", candidates, build_engine_context())

    def test_engine_rejects_fake_markers(self) -> None:
        for fake_marker in (
            "fake_reviews",
            "fake_ratings",
            "fake_revenue",
            "fake_savings",
            "fake_urgency",
            "fake_ai_confidence",
        ):
            with self.subTest(marker=fake_marker):
                candidates = [
                    base_candidate("c1", "budget"),
                    base_candidate("c2", "value"),
                    base_candidate("c3", "best_overall"),
                    base_candidate("c4", "premium"),
                ]
                candidates[0][fake_marker] = True
                with self.assertRaises(ContractValidationError):
                    self.engine.run("best power bank for iphone", candidates, build_engine_context())

    def test_engine_rejects_commission_ranking_fields(self) -> None:
        candidates = [
            base_candidate("c1", "budget"),
            base_candidate("c2", "value"),
            base_candidate("c3", "best_overall"),
            base_candidate("c4", "premium"),
        ]
        candidates[1]["commission_rank"] = 1
        with self.assertRaises(ContractValidationError):
            self.engine.run("best power bank for iphone", candidates, build_engine_context())


class BrainSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.selector = BrainSelector()

    def test_brain_selector_tech_specs_electronics(self) -> None:
        result = self.selector.select(
            "best iphone power bank usb-c",
            {"category": "electronics", "product_type": "charger"},
        )
        self.assertEqual(result.brain, ProductBrain.TECH_SPECS_ELECTRONICS)

    def test_brain_selector_software_programs_saas(self) -> None:
        result = self.selector.select(
            "best invoicing software for freelancers",
            {"service_type": "saas subscription"},
        )
        self.assertEqual(result.brain, ProductBrain.SOFTWARE_PROGRAMS_SAAS)

    def test_brain_selector_physical_products_home_machines(self) -> None:
        result = self.selector.select(
            "air fryer for family home use",
            {"category": "home appliance"},
        )
        self.assertEqual(result.brain, ProductBrain.PHYSICAL_PRODUCTS_HOME_MACHINES)

    def test_brain_selector_financial_utility_contract_products(self) -> None:
        result = self.selector.select(
            "cheap car insurance with stable terms",
            {"service_type": "insurance contract", "risk_flags": ["financial"]},
        )
        self.assertEqual(result.brain, ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS)

    def test_brain_selector_high_trust_risk_sensitive_decisions(self) -> None:
        result = self.selector.select(
            "safe child car seat with certifications",
            {"risk_flags": ["high_trust"]},
        )
        self.assertEqual(result.brain, ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS)


class DecisionDepthSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.selector = DecisionDepthSelector()

    def test_depth_fast_decision(self) -> None:
        result = self.selector.select(
            query="simple cheap phone case quick buy",
            context={"risk_level": "low", "price_band": "budget", "estimated_price": 25},
            selected_brain=ProductBrain.TECH_SPECS_ELECTRONICS,
        )
        self.assertEqual(result.depth, DecisionDepth.FAST_DECISION)

    def test_depth_considered_purchase(self) -> None:
        result = self.selector.select(
            query="best office chair for daily comfort",
            context={"risk_level": "medium", "price_band": "mid", "estimated_price": 220},
            selected_brain=ProductBrain.PHYSICAL_PRODUCTS_HOME_MACHINES,
        )
        self.assertEqual(result.depth, DecisionDepth.CONSIDERED_PURCHASE)

    def test_depth_high_stakes_high_trust(self) -> None:
        result = self.selector.select(
            query="best electricity contract for family home",
            context={"risk_level": "high", "service_type": "contract", "estimated_price": 1300},
            selected_brain=ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS,
        )
        self.assertEqual(result.depth, DecisionDepth.HIGH_STAKES_HIGH_TRUST)


class CandidateAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = ProductCandidateAdapter()

    def test_candidate_adapter_validates_valid_external_candidates(self) -> None:
        candidates = [
            base_candidate("c1", "lowest_monthly_cost")
            | {
                "cta_label": "Compare Terms",
                "risks_or_limitations": "Risk of fee changes; check term and cancel conditions.",
                "terms_summary": "12 month term",
                "unknowns_summary": "unknown network fee updates",
            },
            base_candidate("c2", "stable_price")
            | {
                "cta_label": "View Offer",
                "risks_or_limitations": "Includes risk notes and term clauses.",
            },
            base_candidate("c3", "flexible_plan")
            | {
                "cta_label": "Estimate Cost",
                "risks_or_limitations": "Term details and unknown adjustments apply.",
            },
            base_candidate("c4", "best_overall")
            | {
                "cta_label": "Continue to Provider",
                "risks_or_limitations": "Risk and condition details shown before contract.",
            },
        ]
        adapted = self.adapter.adapt_candidates(
            candidates,
            ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS,
        )
        self.assertEqual(len(adapted), 4)
        self.assertIn("Terms:", adapted[0].payload["risks_or_limitations"])
        self.assertIn("Unknowns:", adapted[0].payload["risks_or_limitations"])

    def test_candidate_adapter_rejects_invalid_candidates(self) -> None:
        invalid = base_candidate("bad-1", "budget")
        invalid.pop("decision_label")
        with self.assertRaises(ContractValidationError):
            self.adapter.adapt_candidates([invalid], ProductBrain.TECH_SPECS_ELECTRONICS)


class ArbitrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = ProductCandidateAdapter()
        self.arbitrator = DecisionArbitrator()

    def test_arbitration_role_diverse_four_choices_where_possible(self) -> None:
        candidates = [
            base_candidate("c1", "budget"),
            base_candidate("c2", "value"),
            base_candidate("c3", "best_overall"),
            base_candidate("c4", "premium"),
            base_candidate("c5", "budget"),
        ]
        adapted = self.adapter.adapt_candidates(candidates, ProductBrain.TECH_SPECS_ELECTRONICS)
        result = self.arbitrator.arbitrate(adapted, ProductBrain.TECH_SPECS_ELECTRONICS)
        selected_roles = {choice["role"] for choice in result.selected_choices}
        self.assertEqual(len(result.selected_choices), 4)
        self.assertGreaterEqual(len(selected_roles), 4)

    def test_arbitration_produces_exactly_one_recommended_and_belongs_to_selected(self) -> None:
        candidates = [
            base_candidate("c1", "budget"),
            base_candidate("c2", "value"),
            base_candidate("c3", "best_overall"),
            base_candidate("c4", "premium"),
        ]
        adapted = self.adapter.adapt_candidates(candidates, ProductBrain.TECH_SPECS_ELECTRONICS)
        result = self.arbitrator.arbitrate(adapted, ProductBrain.TECH_SPECS_ELECTRONICS)
        recommended_count = sum(1 for choice in result.selected_choices if choice["is_recommended"])
        self.assertEqual(recommended_count, 1)
        selected_ids = {choice["product_id"] for choice in result.selected_choices}
        self.assertIn(result.recommended_product_id, selected_ids)

    def test_financial_without_risks_terms_unknown_handling_fails(self) -> None:
        candidates = [
            base_candidate("f1", "lowest_monthly_cost")
            | {"cta_label": "Compare Terms", "risks_or_limitations": "Good offer"},
            base_candidate("f2", "stable_price")
            | {"cta_label": "View Offer", "risks_or_limitations": "Popular plan"},
            base_candidate("f3", "flexible_plan")
            | {"cta_label": "Estimate Cost", "risks_or_limitations": "Simple setup"},
            base_candidate("f4", "best_overall")
            | {"cta_label": "Continue to Provider", "risks_or_limitations": "Low cost"},
        ]
        with self.assertRaises(ContractValidationError):
            self.adapter.adapt_candidates(candidates, ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS)

    def test_high_trust_without_risk_or_reassurance_fails(self) -> None:
        candidates = [
            base_candidate("h1", "safe_budget")
            | {
                "subtitle": "EUR 120 • affordable",
                "key_reasons": ["Lightweight", "Compact"],
                "risks_or_limitations": "Some notes.",
            },
            base_candidate("h2", "best_safety")
            | {
                "subtitle": "EUR 180 • affordable",
                "key_reasons": ["Soft fabric", "Compact"],
                "risks_or_limitations": "General notes.",
            },
            base_candidate("h3", "best_comfort")
            | {
                "subtitle": "EUR 200 • affordable",
                "key_reasons": ["Comfort", "Breathable"],
                "risks_or_limitations": "General notes.",
            },
            base_candidate("h4", "premium_isofix")
            | {
                "subtitle": "EUR 260 • affordable",
                "key_reasons": ["New model", "Color options"],
                "risks_or_limitations": "General notes.",
            },
        ]
        adapted = self.adapter.adapt_candidates(
            candidates, ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS
        )
        with self.assertRaises(ContractValidationError):
            self.arbitrator.arbitrate(adapted, ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS)


class EngineRegressionBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PicwiseDecisionEngine()

    def test_engine_pipeline_attaches_tracking_context_and_missing_data(self) -> None:
        candidates = [
            base_candidate("e1", "budget"),
            base_candidate("e2", "value"),
            base_candidate("e3", "best_overall"),
            base_candidate("e4", "premium"),
        ]
        context = build_engine_context()
        output = self.engine.run("power bank for iphone", candidates, context)
        self.assertEqual([state.value for state in output.missing_data_states], ["unknown"])
        self.assertIn("brain_confidence", output.tracking_context)
        self.assertIn("depth_confidence", output.tracking_context)
        self.assertIn("recommended_reason", output.tracking_context)

    def test_engine_does_not_mutate_input_candidates(self) -> None:
        original = [
            base_candidate("m1", "budget"),
            base_candidate("m2", "value"),
            base_candidate("m3", "best_overall"),
            base_candidate("m4", "premium"),
        ]
        snapshot = deepcopy(original)
        _ = self.engine.run("best power bank", original, build_engine_context())
        self.assertEqual(original, snapshot)


if __name__ == "__main__":
    unittest.main()
