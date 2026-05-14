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
    render_demo_info_page,
    render_landing_surface,
    render_review_safe_landing_page,
    render_affiliate_disclosure_page,
    render_contact_page,
    render_cookies_page,
    render_privacy_page,
    render_terms_page,
    render_branded_not_found_page,
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
    @staticmethod
    def _extract_inline_css(html: str) -> str:
        start = html.index("<style>") + len("<style>")
        end = html.index("</style>")
        return html[start:end]

    def test_landing_topbar_precedes_hero_and_brand_is_visible(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertIn('class="pw-topbar"', html)
        self.assertIn('class="pw-hero"', html)
        self.assertLess(html.index('class="pw-topbar"'), html.index('class="pw-hero"'))
        self.assertIn('class="pw-brand"', html)
        self.assertIn("shopping assistant", html)
        self.assertIn(">picwise<", html)

    def test_landing_renders_exactly_4_primary_cards(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertEqual(html.count('<article class="pw-card'), 4)

    def test_landing_renders_exactly_1_recommended_card(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertEqual(html.count("Recommended by PicWise"), 1)
        self.assertGreater(
            html.rfind('<article class="pw-card pw-card-recommended"'),
            html.find('<article class="pw-card"'),
        )
        self.assertIn("pw-rec-ring-a", html)
        self.assertIn("pw-rec-ring-b", html)
        self.assertIn("pw-rec-ring-c", html)

    def test_search_button_uses_css_magnifier_not_emoji_or_arrow(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertIn('class="pw-search-button"', html)
        self.assertIn('class="pw-search-button-icon"', html)
        self.assertIn('class="pw-search-icon"', html)
        self.assertNotIn('class="pw-search-button" type="submit" aria-label="Search">→</button>', html)
        self.assertNotIn("&#128269;", html)
        self.assertNotIn("🔍", html)

    def test_landing_includes_query_confirmation(self) -> None:
        decision = build_decision_output()
        html = render_landing_surface(decision)
        self.assertIn("See the 4 best products before you buy.", html)
        self.assertIn(decision.query, html)
        self.assertIn("Showing 4 options for:", html)

    def test_landing_does_not_render_infinite_list_behavior(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertIn('data-card-count="4"', html)
        self.assertNotIn("infinite scroll", html.lower())

    def test_landing_does_not_include_cart_checkout_eshop_behavior(self) -> None:
        html = render_landing_surface(build_decision_output())
        for forbidden in ("add to cart", "cart", "checkout", "e-shop"):
            self.assertNotIn(forbidden, html.lower())

    def test_landing_has_single_demo_note_before_footer_and_single_credit(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertEqual(html.count("Demo data source"), 1)
        self.assertIn('class="pw-demo-note"', html)
        self.assertIn('class="pw-footer"', html)
        self.assertLess(html.index('class="pw-demo-note"'), html.index('class="pw-footer"'))
        self.assertIn("All rights reserved.", html)

    def test_landing_contains_required_info_link_and_tooltip_text(self) -> None:
        html = render_landing_surface(build_decision_output())
        self.assertIn("What is PicWise?", html)
        self.assertIn(
            "PicWise is your shopping assistant. It compares products for what you want to buy, "
            "recommends the 4 best matches, saves you time, and helps you choose faster.",
            html,
        )
        self.assertNotIn('class="pw-more"', html)

    def test_review_safe_root_and_demo_info_pages_have_no_commerce_cards_or_store_ctas(self) -> None:
        root_html = render_review_safe_landing_page()
        demo_html = render_demo_info_page()
        for html in (root_html, demo_html):
            lowered = html.lower()
            for forbidden in (
                "travelcore 20k",
                "dailybalance pd20",
                "everydaysure 22.5w",
                "powermax elite 25k",
                "view in store",
                "go to store",
                "view details and buy",
                "recommended by picwise",
                "eur ",
            ):
                self.assertNotIn(forbidden, lowered)
        self.assertNotIn("class=\"pw-rating-row\"", demo_html)
        self.assertIn('href="/demo#what-is-picwise"', root_html)
        self.assertIn("How PicWise will help shoppers decide.", demo_html)
        self.assertIn("Back to home", demo_html)
        self.assertNotIn("What is PicWise?", demo_html)
        self.assertIn("This demo page is informational only.", demo_html)
        for page in (root_html, demo_html):
            self.assertIn('href="/terms"', page)
            self.assertIn('href="/privacy"', page)
            self.assertIn('href="/cookies"', page)
            self.assertIn('href="/affiliate-disclosure"', page)
            self.assertIn('href="/contact"', page)

    def test_css_has_no_negative_margin_top_on_shell_or_hero(self) -> None:
        css = self._extract_inline_css(render_landing_surface(build_decision_output())).replace(" ", "")
        self.assertNotIn(".pw-page{margin-top:-", css)
        self.assertNotIn(".pw-hero{margin-top:-", css)

    def test_css_has_no_negative_translate_for_topbar_or_hero(self) -> None:
        css = self._extract_inline_css(render_landing_surface(build_decision_output())).replace(" ", "")
        self.assertNotIn(".pw-topbar{transform:translateY(-", css)
        self.assertNotIn(".pw-hero{transform:translateY(-", css)
        self.assertNotIn("translateY(-", css)

    def test_topbar_is_not_absolutely_positioned(self) -> None:
        css = self._extract_inline_css(render_landing_surface(build_decision_output())).replace(" ", "")
        self.assertIn(".pw-topbar{position:relative;", css)
        self.assertNotIn(".pw-topbar{position:absolute", css)

    def test_hero_has_clear_spacing_below_topbar(self) -> None:
        css = self._extract_inline_css(render_landing_surface(build_decision_output())).replace(" ", "")
        self.assertIn(".pw-topbar{position:relative;", css)
        self.assertIn(".pw-hero{position:relative;", css)
        self.assertIn("text-align:center;", css)

    def test_legal_pages_have_headings_sections_footer_and_meta(self) -> None:
        pages = (
            render_terms_page(),
            render_privacy_page(),
            render_cookies_page(),
            render_affiliate_disclosure_page(),
            render_contact_page(),
        )
        for page in pages:
            self.assertEqual(page.count('<main class="pw-wrap">'), 1)
            self.assertIn("<h1", page)
            self.assertIn("<h2", page)
            self.assertIn('<meta name="description"', page)
            self.assertEqual(page.count('<footer class="pw-footer">'), 1)
            self.assertIn('class="pw-footer-links"', page)
            self.assertIn('class="pw-footer-link"', page)
            self.assertIn('href="/terms"', page)
            self.assertIn('href="/privacy"', page)
            self.assertIn('href="/cookies"', page)
            self.assertIn('href="/affiliate-disclosure"', page)
            self.assertIn('href="/contact"', page)
            self.assertNotIn(
                "HomeDemoPicWise ReferenceTermsPrivacyCookiesAffiliate DisclosureContact",
                page.replace(" ", "").replace("\n", ""),
            )

    def test_legal_pages_do_not_claim_live_tracking_stack_or_fake_commerce(self) -> None:
        legal_blob = " ".join(
            [
                render_terms_page().lower(),
                render_privacy_page().lower(),
                render_cookies_page().lower(),
                render_affiliate_disclosure_page().lower(),
                render_contact_page().lower(),
            ]
        )
        for forbidden in (
            "add to cart",
            "checkout now",
            "buy now",
            "google analytics is active",
            "meta pixel is active",
            "amazon pixel is active",
            "linkwise pixel is active",
        ):
            self.assertNotIn(forbidden, legal_blob)

    def test_terms_privacy_cookies_affiliate_contact_required_wording(self) -> None:
        terms = render_terms_page()
        privacy = render_privacy_page()
        cookies = render_cookies_page()
        affiliate = render_affiliate_disclosure_page()
        contact = render_contact_page()

        self.assertIn("PicWise does not sell products directly", terms)
        self.assertIn("no checkout", terms.lower())
        self.assertIn("SaaS", terms)
        self.assertIn("finance", terms.lower())
        self.assertIn("no financial advice", terms.lower())
        self.assertIn("Disclaimer", terms)
        self.assertIn("Limitation of liability", terms)
        self.assertIn("Use of PicWise is at the user's own risk.", terms)
        self.assertIn("No professional advice", terms)
        self.assertIn("Users remain responsible for their final decision", terms)

        self.assertIn("cookies", privacy.lower())
        self.assertIn("pixels", privacy.lower())
        self.assertIn("European Economic Area", privacy)
        self.assertIn("United Kingdom", privacy)
        self.assertIn("legal basis", privacy.lower())
        self.assertIn("affiliate", privacy.lower())
        self.assertIn("SaaS", privacy)
        self.assertIn("finance", privacy.lower())

        self.assertIn("essential cookies", cookies.lower())
        self.assertIn("non-essential cookies", cookies.lower())
        self.assertIn("pixels", cookies.lower())
        self.assertIn("consent", cookies.lower())
        self.assertIn("affiliate", cookies.lower())

        self.assertIn("As an Amazon Associate I earn from qualifying purchases.", affiliate)
        self.assertIn("Linkwise", affiliate)
        self.assertIn("SaaS", affiliate)
        self.assertIn("finance", affiliate.lower())

        self.assertIn("contact.picwise@subby.cloud", contact)
        for page in (terms, privacy, cookies, affiliate, contact):
            self.assertIn("contact.picwise@subby.cloud", page)
            self.assertNotIn("contact@picwise.subby.cloud", page)
            self.assertNotIn("mysubby.cloud@gmail.com", page)

    def test_branded_not_found_page_has_required_elements(self) -> None:
        html = render_branded_not_found_page()
        self.assertIn("Page not found — PicWise", html)
        self.assertIn("The page you requested could not be found.", html)
        self.assertIn('href="/"', html)
        self.assertIn('href="/terms"', html)


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
