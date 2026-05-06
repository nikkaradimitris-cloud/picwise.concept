from __future__ import annotations

import sys
import unittest
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_contracts import ContractValidationError, DecisionOutput, ProductBrain  # noqa: E402
from picwise_surface import (  # noqa: E402
    FinalV1AuditEvidence,
    audit_surface_performance,
    build_dashboard_compatibility_payload,
    build_redirect_outcome_event,
    build_seo_landing_bundle,
    build_surface_metrics,
    prepare_redirect_tracking,
    render_landing_surface,
    run_final_v1_audit_closure,
)


def build_choice(
    product_id: str,
    role: str,
    cta_label: str,
    *,
    recommended: bool = False,
) -> dict:
    metadata = {"source": "test-surface"}
    if recommended:
        metadata["recommendation_reason"] = "Balanced reliability and total value."
    return {
        "product_id": product_id,
        "title": f"Choice {product_id}",
        "merchant_or_provider": "Provider A",
        "price_or_cost_display": "EUR 39",
        "role": role,
        "decision_label": "Clear fit for this query",
        "subtitle": "EUR 39 • practical benefit • lower decision risk",
        "key_reasons": ["Reliable day-to-day use", "Good value balance", "Quick setup"],
        "risks_or_limitations": "Check compatibility before purchase.",
        "cta_label": cta_label,
        "redirect_target": f"https://provider.example/{product_id}",
        "tracking_metadata": metadata,
        "is_recommended": recommended,
    }


def build_decision_output(
    *,
    query: str = "power bank 20000mah for iphone travel",
    selected_brain: str = "tech_specs_electronics",
    include_more: bool = True,
) -> DecisionOutput:
    payload = {
        "query": query,
        "selected_brain": selected_brain,
        "decision_depth": "considered_purchase",
        "page_title": f"4 best options for {query}",
        "choices": [
            build_choice("p1", "budget", "View in Store"),
            build_choice("p2", "value", "Go to Store", recommended=True),
            build_choice("p3", "best_overall", "View Details and Buy"),
            build_choice("p4", "premium", "View in Store"),
        ],
        "recommended_product_id": "p2",
        "missing_data_states": ["unknown"],
        "tracking_context": {"session_hint": "surface-suite"},
    }
    if include_more:
        payload["more_choices"] = [
            build_choice("m1", "budget", "View in Store"),
            build_choice("m2", "value", "Go to Store"),
            build_choice("m3", "best_overall", "View Details and Buy"),
            build_choice("m4", "premium", "View in Store"),
        ]
    return DecisionOutput.from_dict(payload)


class LandingUiTests(unittest.TestCase):
    def test_landing_renders_exactly_4_primary_cards(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertEqual(html.count('<article class="pw-card'), 4)

    def test_landing_renders_exactly_1_recommended_card(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertEqual(html.count("Recommended by Picwise"), 1)

    def test_landing_includes_query_confirmation(self) -> None:
        decision = build_decision_output()
        html = render_landing_surface(decision)
        self.assertIn(decision.query, html)
        self.assertIn("Showing 4 decision-ready options for:", html)

    def test_landing_does_not_render_infinite_list_behavior(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertIn('data-card-count="4"', html)
        self.assertNotIn("infinite", html.lower())

    def test_landing_does_not_include_cart_checkout_eshop_behavior(self) -> None:
        html = render_landing_surface(build_decision_output())
        for forbidden in ("add to cart", "cart", "checkout", "e-shop"):
            self.assertNotIn(forbidden, html.lower())

    def test_more_section_is_secondary_and_max_4_choices(self) -> None:
        html = render_landing_surface(build_decision_output(include_more=True))
        self.assertIn('class="pw-more"', html)
        self.assertEqual(html.count('<li data-choice-id="m'), 4)


class CtaRedirectTrackingTests(unittest.TestCase):
    def test_cta_labels_match_product_brain_expectations(self) -> None:
        tech_output = build_decision_output(selected_brain=ProductBrain.TECH_SPECS_ELECTRONICS.value)
        labels = {choice.cta_label for choice in tech_output.choices}
        self.assertTrue(labels.issubset({"View in Store", "Go to Store", "View Details and Buy"}))

    def test_redirect_tracking_creates_valid_redirect_event(self) -> None:
        decision = build_decision_output()
        preparation = prepare_redirect_tracking(
            decision,
            "p2",
            str(uuid4()),
            210,
        )
        self.assertEqual(preparation.redirect_event.product_id, "p2")
        self.assertTrue(preparation.redirect_event.recommended)

    def test_cta_click_creates_valid_tracking_event(self) -> None:
        decision = build_decision_output()
        preparation = prepare_redirect_tracking(
            decision,
            "p2",
            str(uuid4()),
            180,
        )
        self.assertEqual(preparation.cta_click_event.event_type.value, "cta_click")
        self.assertEqual(preparation.cta_click_event.product_id, "p2")

    def test_redirect_tracking_preserves_recommended_and_non_recommended_metadata(self) -> None:
        decision = build_decision_output()
        recommended = prepare_redirect_tracking(decision, "p2", str(uuid4()), 170)
        non_recommended = prepare_redirect_tracking(decision, "p1", str(uuid4()), 190)
        self.assertTrue(recommended.redirect_event.recommended)
        self.assertFalse(non_recommended.redirect_event.recommended)
        self.assertEqual(recommended.click_kind_event.event_type.value, "recommended_click")
        self.assertEqual(non_recommended.click_kind_event.event_type.value, "non_recommended_click")

    def test_redirect_budget_validation_enforces_less_than_300ms(self) -> None:
        decision = build_decision_output()
        with self.assertRaises(ContractValidationError):
            prepare_redirect_tracking(decision, "p2", str(uuid4()), 300)

    def test_redirect_outcome_event_success_failure_contract(self) -> None:
        decision = build_decision_output()
        success_event = build_redirect_outcome_event(
            decision,
            "p2",
            str(uuid4()),
            success=True,
            latency_ms=210,
        )
        failure_event = build_redirect_outcome_event(
            decision,
            "p1",
            str(uuid4()),
            success=False,
            latency_ms=250,
            error_message="timeout",
        )
        self.assertEqual(success_event.event_type.value, "redirect_success")
        self.assertEqual(failure_event.event_type.value, "redirect_failure")


class SeoLandingGenerationTests(unittest.TestCase):
    def test_seo_slug_and_path_generation_for_long_tail_queries(self) -> None:
        query = "Power bank 20000mAh for iPhone fast charging"
        bundle = build_seo_landing_bundle(query, build_decision_output(query=query))
        self.assertIn("power-bank-20000mah-for-iphone-fast-charging", bundle.slug)
        self.assertTrue(all(path.startswith("/") for path in bundle.canonical_candidates))

    def test_seo_metadata_is_query_matched_without_fake_claims(self) -> None:
        query = "best invoicing software for taxi drivers"
        output = build_decision_output(
            query=query,
            selected_brain=ProductBrain.SOFTWARE_PROGRAMS_SAAS.value,
        )
        bundle = build_seo_landing_bundle(query, output)
        self.assertIn(query, bundle.title)
        self.assertIn(query, bundle.description)
        for forbidden in ("fake", "guaranteed", "urgent", "save 90%", "5-star"):
            self.assertNotIn(forbidden, bundle.description.lower())


class DashboardCompatibilityTests(unittest.TestCase):
    def test_dashboard_payload_uses_canonical_missing_data_enum(self) -> None:
        decision = build_decision_output()
        payload = build_dashboard_compatibility_payload(decision)
        self.assertEqual(payload["missing_data_states"], ["unknown"])

    def test_dashboard_payload_does_not_fake_revenue_or_conversions(self) -> None:
        decision = build_decision_output()
        payload = build_dashboard_compatibility_payload(decision)
        self.assertEqual(payload["conversion_tracking"]["status"], "not_connected")
        self.assertIsNone(payload["conversion_tracking"]["value"])
        self.assertEqual(payload["revenue_tracking"]["status"], "not_connected")
        self.assertIsNone(payload["revenue_tracking"]["value"])


class PerformanceAuditTests(unittest.TestCase):
    def test_performance_audit_passes_deterministic_budgets(self) -> None:
        decision = build_decision_output()
        html = render_landing_surface(decision)
        metrics = build_surface_metrics(
            decision,
            html,
            click_to_redirect_ms=220,
            runtime_dependencies=["python_stdlib"],
        )
        result = audit_surface_performance(metrics)
        self.assertTrue(result.passed)


class FinalAuditClosureTests(unittest.TestCase):
    def test_final_audit_fails_if_stage_evidence_missing(self) -> None:
        evidence = FinalV1AuditEvidence(
            stage_10_implemented=True,
            stage_11_implemented=True,
            stage_12_implemented=False,
            stage_13_implemented=True,
            stage_14_implemented=True,
            tests_passed=True,
            no_fake_data=True,
            no_commission_ranking=True,
            roadmap_titles_unchanged=True,
            progress_updated_accurately=True,
        )
        result = run_final_v1_audit_closure(evidence)
        self.assertFalse(result.passed)

    def test_final_audit_passes_when_local_evidence_present(self) -> None:
        evidence = FinalV1AuditEvidence(
            stage_10_implemented=True,
            stage_11_implemented=True,
            stage_12_implemented=True,
            stage_13_implemented=True,
            stage_14_implemented=True,
            tests_passed=True,
            no_fake_data=True,
            no_commission_ranking=True,
            roadmap_titles_unchanged=True,
            progress_updated_accurately=True,
        )
        result = run_final_v1_audit_closure(evidence)
        self.assertTrue(result.passed)
        self.assertIn("commit-ready", result.ready_claim)


if __name__ == "__main__":
    unittest.main()
