from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.buying_routes import get_buying_pages_repository, render_best_slug_html  # noqa: E402
from picwise_buying_pages import render_buying_pages_sitemap_xml  # noqa: E402
from picwise_offers import (  # noqa: E402
    LocaleEligibilityStatus,
    TargetMarket,
    evaluate_locale_batch_eligibility,
    evaluate_locale_product_eligibility,
)


def _load_locale_fixture() -> list[dict[str, object]]:
    fixture_path = ROOT / "tests" / "fixtures" / "roadmap_step3_locale_candidates.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


def _candidate_by_id(candidate_id: str) -> dict[str, object]:
    for item in _load_locale_fixture():
        if str(item.get("candidate_id")) == candidate_id:
            return item
    raise AssertionError(f"Missing fixture candidate: {candidate_id}")


class PickWiseRoadmapStep3LocaleLogicTests(unittest.TestCase):
    def test_us_usd_product_is_ready_for_us(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("us-valid-usd"), TargetMarket.US)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_READY)
        self.assertTrue(decision.can_show_to_user)
        self.assertTrue(decision.can_continue_to_candidate_page)

    def test_uk_gbp_product_is_ready_for_uk(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("uk-valid-gbp"), TargetMarket.UK)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_READY)
        self.assertEqual(decision.candidate_currency, "GBP")

    def test_de_eur_product_is_ready_for_de(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("de-valid-eur"), TargetMarket.DE)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_READY)
        self.assertEqual(decision.target_market, "DE")

    def test_gr_eur_product_is_ready_for_gr(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("gr-valid-eur"), TargetMarket.GR)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_READY)
        self.assertEqual(decision.target_market, "GR")

    def test_eu_compatible_delivery_can_pass_for_de_and_gr_when_explicit(self) -> None:
        de_decision = evaluate_locale_product_eligibility(_candidate_by_id("eu-valid-for-de"), TargetMarket.DE)
        gr_decision = evaluate_locale_product_eligibility(_candidate_by_id("eu-valid-for-gr"), TargetMarket.GR)
        self.assertEqual(de_decision.status, LocaleEligibilityStatus.LOCALE_READY)
        self.assertEqual(gr_decision.status, LocaleEligibilityStatus.LOCALE_READY)

    def test_us_product_is_blocked_for_de_when_no_de_or_eu_delivery_exists(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("us-targeted-to-de-invalid"), TargetMarket.DE)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_BLOCKED)
        self.assertIn("de_market_requires_explicit_de_or_eu_de_coverage", decision.blocker_reasons)

    def test_de_product_is_blocked_for_us_when_no_us_delivery_exists(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("de-targeted-to-us-invalid"), TargetMarket.US)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_BLOCKED)
        self.assertIn("us_market_rejects_non_us_delivery_profile", decision.blocker_reasons)

    def test_currency_mismatch_is_blocked_under_strict_rules(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("uk-usd-mismatch"), TargetMarket.UK)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_BLOCKED)
        self.assertIn("currency_mismatch_for_target_market", decision.blocker_reasons)

    def test_missing_delivery_coverage_does_not_pass_silently(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("gr-missing-delivery"), TargetMarket.GR)
        self.assertNotEqual(decision.status, LocaleEligibilityStatus.LOCALE_READY)
        self.assertIn("delivery_coverage_missing", decision.review_reasons)

    def test_unknown_market_does_not_pass_silently(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("unknown-market-candidate"), TargetMarket.DE)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_BLOCKED)
        self.assertIn("candidate_market_unknown", decision.blocker_reasons)

    def test_missing_currency_requires_review_without_fabrication(self) -> None:
        decision = evaluate_locale_product_eligibility(_candidate_by_id("de-missing-currency"), TargetMarket.DE)
        self.assertEqual(decision.status, LocaleEligibilityStatus.LOCALE_REVIEW_REQUIRED)
        self.assertIn("currency_missing", decision.review_reasons)

    def test_batch_counts_are_deterministic(self) -> None:
        batch = _load_locale_fixture()
        first = evaluate_locale_batch_eligibility(batch, TargetMarket.DE)
        second = evaluate_locale_batch_eligibility(batch, TargetMarket.DE)
        self.assertEqual(first, second)
        self.assertEqual(first["total_candidates"], len(batch))
        self.assertEqual(
            first["ready_count"] + first["review_required_count"] + first["blocked_count"],
            first["total_candidates"],
        )

    def test_can_continue_to_step4_only_when_no_blockers_and_review_rate_is_acceptable(self) -> None:
        passing_batch = [
            _candidate_by_id("de-valid-eur"),
            _candidate_by_id("eu-valid-for-de"),
            _candidate_by_id("de-missing-currency"),
        ]
        passing = evaluate_locale_batch_eligibility(
            passing_batch,
            TargetMarket.DE,
            ruleset={"review_rate_threshold_for_step4": 0.5},
        )
        self.assertTrue(passing["can_continue_to_step4"])

        blocked_batch = [_candidate_by_id("de-valid-eur"), _candidate_by_id("us-targeted-to-de-invalid")]
        blocked = evaluate_locale_batch_eligibility(blocked_batch, TargetMarket.DE)
        self.assertFalse(blocked["can_continue_to_step4"])

        strict_review_batch = [
            _candidate_by_id("de-valid-eur"),
            _candidate_by_id("de-missing-currency"),
        ]
        strict_review = evaluate_locale_batch_eligibility(
            strict_review_batch,
            TargetMarket.DE,
            ruleset={"review_rate_threshold_for_step4": 0.0},
        )
        self.assertFalse(strict_review["can_continue_to_step4"])

    def test_no_fake_locale_shipping_currency_assumptions_are_made(self) -> None:
        decision = evaluate_locale_product_eligibility(
            {
                "candidate_id": "unknown-evidence",
                "market": "",
                "locale": "",
                "currency": "",
                "delivery_coverage": [],
            },
            TargetMarket.UK,
        )
        self.assertNotEqual(decision.status, LocaleEligibilityStatus.LOCALE_READY)
        self.assertIn("candidate_market_unknown", decision.blocker_reasons)
        self.assertIn("currency_missing", decision.review_reasons)
        self.assertIn("delivery_coverage_missing", decision.review_reasons)

    def test_no_naming_routes_sitemap_or_public_labels_changed(self) -> None:
        status, body = render_best_slug_html("power-bank-20000mah-for-iphone")
        self.assertEqual(status, 200)
        self.assertIn("Recommended by PickWise", body)
        candidate_status, _candidate_body = render_best_slug_html("roadmap-step3-locale-logic-candidate")
        self.assertEqual(candidate_status, 404)
        repository = get_buying_pages_repository()
        self.assertIsNone(repository.get_by_slug("roadmap-step3-locale-logic-candidate"))
        sitemap = render_buying_pages_sitemap_xml(repository.list_pages(), base_url="https://localhost")
        self.assertNotIn("roadmap-step3-locale-logic-candidate", sitemap)

    def test_no_gates_relaxed_and_no_scraping_live_api_or_credentials_added(self) -> None:
        source = (
            inspect.getsource(evaluate_locale_product_eligibility).lower()
            + inspect.getsource(evaluate_locale_batch_eligibility).lower()
        )
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "beautifulsoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
            "api_key",
            "secret",
            "token",
            "credential",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
