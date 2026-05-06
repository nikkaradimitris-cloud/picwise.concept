from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_contracts import (  # noqa: E402
    ContractValidationError,
    DecisionOutput,
    MissingDataState,
    RedirectEvent,
    TrackingEvent,
    validate_missing_data_states,
)


def build_choice(
    product_id: str,
    *,
    is_recommended: bool = False,
    role: str = "budget",
    cta_label: str = "View in Store",
    risks_or_limitations: str = "Limited stock in some regions.",
) -> dict:
    return {
        "product_id": product_id,
        "title": f"Product {product_id}",
        "merchant_or_provider": "Merchant A",
        "price_or_cost_display": "$49",
        "role": role,
        "decision_label": "Strong practical fit",
        "subtitle": "$49 • Reliable daily use • Low regret risk",
        "key_reasons": ["Reliable", "Good value"],
        "risks_or_limitations": risks_or_limitations,
        "cta_label": cta_label,
        "redirect_target": "https://example.com/product",
        "tracking_metadata": {"source": "organic"},
        "is_recommended": is_recommended,
    }


def build_valid_decision_output() -> dict:
    return {
        "query": "best power bank for iphone",
        "selected_brain": "tech_specs_electronics",
        "decision_depth": "considered_purchase",
        "page_title": "4 best options for power bank iPhone",
        "choices": [
            build_choice("p1", role="budget"),
            build_choice("p2", role="value", is_recommended=True),
            build_choice("p3", role="best_overall"),
            build_choice("p4", role="premium"),
        ],
        "recommended_product_id": "p2",
        "more_choices": [
            build_choice("p5", role="value"),
            build_choice("p6", role="premium"),
        ],
        "missing_data_states": [
            "not_connected",
            "data_not_yet",
            "not_applicable",
            "unknown",
        ],
        "tracking_context": {"session_hint": "abc123"},
    }


class DecisionOutputContractTests(unittest.TestCase):
    def test_valid_decision_output_passes(self) -> None:
        payload = build_valid_decision_output()
        decision_output = DecisionOutput.from_dict(payload)
        self.assertEqual(len(decision_output.choices), 4)
        self.assertEqual(decision_output.recommended_product_id, "p2")

    def test_output_with_3_choices_fails(self) -> None:
        payload = build_valid_decision_output()
        payload["choices"] = payload["choices"][:3]
        with self.assertRaises(ContractValidationError):
            DecisionOutput.from_dict(payload)

    def test_output_with_5_choices_fails(self) -> None:
        payload = build_valid_decision_output()
        payload["choices"].append(build_choice("p_extra", role="value"))
        with self.assertRaises(ContractValidationError):
            DecisionOutput.from_dict(payload)

    def test_output_with_0_recommended_fails(self) -> None:
        payload = build_valid_decision_output()
        for choice in payload["choices"]:
            choice["is_recommended"] = False
        with self.assertRaises(ContractValidationError):
            DecisionOutput.from_dict(payload)

    def test_output_with_2_recommended_fails(self) -> None:
        payload = build_valid_decision_output()
        payload["choices"][0]["is_recommended"] = True
        with self.assertRaises(ContractValidationError):
            DecisionOutput.from_dict(payload)

    def test_recommended_outside_primary_choices_fails(self) -> None:
        payload = build_valid_decision_output()
        payload["recommended_product_id"] = "outside_product"
        with self.assertRaises(ContractValidationError):
            DecisionOutput.from_dict(payload)

    def test_fake_markers_fail_validation(self) -> None:
        forbidden_fields = (
            "fake_reviews",
            "fake_ratings",
            "fake_revenue",
            "fake_savings",
            "fake_urgency",
            "fake_ai_confidence",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                payload = build_valid_decision_output()
                payload["tracking_context"][field_name] = True
                with self.assertRaises(ContractValidationError):
                    DecisionOutput.from_dict(payload)

    def test_commission_ranking_field_fails(self) -> None:
        payload = build_valid_decision_output()
        payload["tracking_context"]["commission_rank"] = 1
        with self.assertRaises(ContractValidationError):
            DecisionOutput.from_dict(payload)

    def test_financial_utility_without_risk_terms_fails(self) -> None:
        payload = build_valid_decision_output()
        payload["selected_brain"] = "financial_utility_contract_products"
        payload["choices"] = [
            build_choice("f1", role="budget", risks_or_limitations="Low monthly cost."),
            build_choice(
                "f2",
                role="stable_price",
                is_recommended=True,
                cta_label="Compare Terms",
                risks_or_limitations="Very popular offer.",
            ),
            build_choice("f3", role="best_overall", cta_label="View Offer"),
            build_choice("f4", role="premium", cta_label="Request Offer"),
        ]
        payload["recommended_product_id"] = "f2"
        with self.assertRaises(ContractValidationError):
            DecisionOutput.from_dict(payload)


class CanonicalEnumsTests(unittest.TestCase):
    def test_missing_data_enum_accepts_only_canonical_values(self) -> None:
        canonical = {
            "not_connected",
            "data_not_yet",
            "not_applicable",
            "unknown",
        }
        self.assertEqual(canonical, {state.value for state in MissingDataState})
        validate_missing_data_states(sorted(canonical))
        with self.assertRaises(ContractValidationError):
            validate_missing_data_states(["not_connected", "pending_sync"])


class TrackingEventContractTests(unittest.TestCase):
    def test_tracking_event_required_fields_pass(self) -> None:
        payload = {
            "event_type": "page_impression",
            "event_id": str(uuid4()),
            "timestamp": "2026-05-06T12:00:00Z",
            "query": "best laptop under 1000",
            "selected_brain": "tech_specs_electronics",
            "decision_depth": "high_stakes_high_trust",
            "session_id": str(uuid4()),
            "source": "seo",
            "metadata": {"page_id": "landing-123"},
            "missing_data_states": ["unknown"],
        }
        event = TrackingEvent.from_dict(payload)
        self.assertEqual(event.event_type.value, "page_impression")

    def test_tracking_event_missing_required_field_fails(self) -> None:
        payload = {
            "event_type": "cta_click",
            "event_id": str(uuid4()),
            "timestamp": "2026-05-06T12:00:00Z",
            "query": "best laptop under 1000",
            "selected_brain": "tech_specs_electronics",
            "decision_depth": "considered_purchase",
            "session_id": str(uuid4()),
            "metadata": {"page_id": "landing-123"},
            "missing_data_states": ["unknown"],
            "product_id": "p2",
            "recommended": True,
        }
        with self.assertRaises(ContractValidationError):
            TrackingEvent.from_dict(payload)

    def test_tracking_event_product_required_for_click_event(self) -> None:
        payload = {
            "event_type": "recommended_click",
            "event_id": str(uuid4()),
            "timestamp": "2026-05-06T12:00:00Z",
            "query": "best laptop under 1000",
            "selected_brain": "tech_specs_electronics",
            "decision_depth": "considered_purchase",
            "session_id": str(uuid4()),
            "source": "seo",
            "metadata": {"page_id": "landing-123"},
            "missing_data_states": ["unknown"],
            "recommended": True,
        }
        with self.assertRaises(ContractValidationError):
            TrackingEvent.from_dict(payload)


class RedirectEventContractTests(unittest.TestCase):
    def test_redirect_event_required_fields_pass(self) -> None:
        payload = {
            "event_id": str(uuid4()),
            "timestamp": "2026-05-06T12:00:00Z",
            "query": "best power bank",
            "product_id": "p2",
            "merchant_or_provider": "Merchant A",
            "redirect_target": "https://example.com/product",
            "recommended": True,
            "click_to_redirect_budget_ms": 220,
            "tracking_metadata": {"source": "seo"},
        }
        event = RedirectEvent.from_dict(payload)
        self.assertTrue(event.recommended)

    def test_redirect_event_missing_required_field_fails(self) -> None:
        payload = {
            "event_id": str(uuid4()),
            "timestamp": "2026-05-06T12:00:00Z",
            "query": "best power bank",
            "product_id": "p2",
            "redirect_target": "https://example.com/product",
            "recommended": True,
            "click_to_redirect_budget_ms": 220,
            "tracking_metadata": {"source": "seo"},
        }
        with self.assertRaises(ContractValidationError):
            RedirectEvent.from_dict(payload)

    def test_redirect_event_budget_over_target_fails(self) -> None:
        payload = {
            "event_id": str(uuid4()),
            "timestamp": "2026-05-06T12:00:00Z",
            "query": "best power bank",
            "product_id": "p2",
            "merchant_or_provider": "Merchant A",
            "redirect_target": "https://example.com/product",
            "recommended": True,
            "click_to_redirect_budget_ms": 300,
            "tracking_metadata": {"source": "seo"},
        }
        with self.assertRaises(ContractValidationError):
            RedirectEvent.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
