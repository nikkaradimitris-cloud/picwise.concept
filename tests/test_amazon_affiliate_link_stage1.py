from __future__ import annotations

import sys
import unittest
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers.amazon_manual_affiliate import (  # noqa: E402
    AMAZON_ASSOCIATE_DISCLOSURE,
    AMAZON_ASSOCIATES_TRACKING_ID,
    AMAZON_SAFE_NOTE,
    MANUAL_AMAZON_AFFILIATE_REGISTRY,
    AmazonManualAffiliateQualityStatus,
    AmazonManualAffiliateRecord,
    AmazonManualAffiliateSource,
    AmazonManualAffiliateStatus,
    AmazonManualMatchStatus,
    get_approved_manual_amazon_record_by_asin,
    match_manual_amazon_affiliates,
    match_manual_amazon_affiliate,
    validate_amazon_affiliate_url,
    validate_manual_amazon_record,
)


class AmazonAffiliateUrlValidationTests(unittest.TestCase):
    def test_valid_full_amazon_url_with_required_tag_passes(self) -> None:
        record = MANUAL_AMAZON_AFFILIATE_REGISTRY[0]
        result = validate_amazon_affiliate_url(record.affiliate_url)
        self.assertTrue(result.valid)
        self.assertEqual(result.asin, "B08K7GHZ3V")
        self.assertEqual(result.tracking_id, "picwise-20")
        self.assertEqual(result.errors, tuple())

    def test_missing_tag_fails(self) -> None:
        url = "https://www.amazon.com/dp/B08K7GHZ3V"
        result = validate_amazon_affiliate_url(url)
        self.assertFalse(result.valid)
        self.assertIn("missing_tag", result.errors)

    def test_wrong_tag_fails(self) -> None:
        url = "https://www.amazon.com/dp/B08K7GHZ3V?tag=wrong-20"
        result = validate_amazon_affiliate_url(url)
        self.assertFalse(result.valid)
        self.assertIn("wrong_tag", result.errors)

    def test_amzn_to_short_link_fails(self) -> None:
        url = "https://amzn.to/abc123?tag=picwise-20"
        result = validate_amazon_affiliate_url(url)
        self.assertFalse(result.valid)
        self.assertIn("short_links_not_allowed", result.errors)

    def test_non_amazon_url_fails(self) -> None:
        url = "https://example.com/dp/B08K7GHZ3V?tag=picwise-20"
        result = validate_amazon_affiliate_url(url)
        self.assertFalse(result.valid)
        self.assertIn("non_amazon_host", result.errors)

    def test_amazon_search_page_without_asin_fails(self) -> None:
        url = "https://www.amazon.com/s?k=powerbank&tag=picwise-20"
        result = validate_amazon_affiliate_url(url)
        self.assertFalse(result.valid)
        self.assertIn("missing_or_invalid_asin_path", result.errors)

    def test_malformed_url_fails(self) -> None:
        result = validate_amazon_affiliate_url("not a valid url")
        self.assertFalse(result.valid)
        self.assertIn("invalid_scheme", result.errors)


class AmazonAffiliateRecordValidationTests(unittest.TestCase):
    def test_power_bank_registry_has_expected_audit_and_active_visibility_split(self) -> None:
        power_bank_records = [record for record in MANUAL_AMAZON_AFFILIATE_REGISTRY if record.category == "power_banks"]
        self.assertEqual(len(power_bank_records), 4)
        approved_records = [record for record in power_bank_records if record.status == AmazonManualAffiliateStatus.APPROVED]
        self.assertEqual(len(approved_records), 3)
        disabled_records = [record for record in power_bank_records if record.status == AmazonManualAffiliateStatus.DISABLED]
        self.assertEqual(len(disabled_records), 1)
        self.assertEqual(disabled_records[0].asin, "B08K7GHZ3V")
        self.assertEqual(disabled_records[0].quality_status, AmazonManualAffiliateQualityStatus.UNAVAILABLE_MANUAL)
        asins = {record.asin for record in power_bank_records}
        self.assertSetEqual(asins, {"B08K7GHZ3V", "B0FQJH2XSY", "B0GR1257LT", "B0GH75LWKN"})
        self.assertNotIn("B0F518CRGK", asins)

    def test_every_power_bank_registry_record_validates_successfully(self) -> None:
        power_bank_records = [record for record in MANUAL_AMAZON_AFFILIATE_REGISTRY if record.category == "power_banks"]
        self.assertEqual(len(power_bank_records), 4)
        for record in power_bank_records:
            validation = validate_manual_amazon_record(record)
            self.assertTrue(validation.valid, msg=f"record {record.asin} should be valid: {validation.errors}")

    def test_source_and_status_allow_list_accepts_expected_values(self) -> None:
        for status in (
            AmazonManualAffiliateStatus.APPROVED,
            AmazonManualAffiliateStatus.DISABLED,
            AmazonManualAffiliateStatus.NEEDS_REVIEW,
        ):
            record = AmazonManualAffiliateRecord(
                asin="B08K7GHZ3V",
                title="INIU Portable Charger 10500mAh Fast Charging Power Bank",
                category="power_banks",
                slot_label="Everyday portable",
                affiliate_url=MANUAL_AMAZON_AFFILIATE_REGISTRY[0].affiliate_url,
                tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
                source=AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL,
                status=status,
                quality_status=(
                    AmazonManualAffiliateQualityStatus.ACTIVE
                    if status == AmazonManualAffiliateStatus.APPROVED
                    else AmazonManualAffiliateQualityStatus.NEEDS_MANUAL_REVIEW
                ),
                quality_note=None,
                last_manual_reviewed_at=None,
                operator_note=None,
                created_at="2026-05-15T00:00:00Z",
            )
            result = validate_manual_amazon_record(record)
            self.assertTrue(result.valid)

    def test_unknown_source_rejected(self) -> None:
        record = AmazonManualAffiliateRecord(
            asin="B08K7GHZ3V",
            title="INIU Portable Charger 10500mAh Fast Charging Power Bank",
            category="power_banks",
            slot_label="Everyday portable",
            affiliate_url=MANUAL_AMAZON_AFFILIATE_REGISTRY[0].affiliate_url,
            tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
            source="unknown_source",  # type: ignore[arg-type]
            status=AmazonManualAffiliateStatus.APPROVED,
            quality_status=AmazonManualAffiliateQualityStatus.ACTIVE,
            quality_note=None,
            last_manual_reviewed_at=None,
            operator_note=None,
            created_at="2026-05-15T00:00:00Z",
        )
        result = validate_manual_amazon_record(record)
        self.assertFalse(result.valid)
        self.assertIn("unknown_source", result.errors)

    def test_unknown_status_rejected(self) -> None:
        record = AmazonManualAffiliateRecord(
            asin="B08K7GHZ3V",
            title="INIU Portable Charger 10500mAh Fast Charging Power Bank",
            category="power_banks",
            slot_label="Everyday portable",
            affiliate_url=MANUAL_AMAZON_AFFILIATE_REGISTRY[0].affiliate_url,
            tracking_id=AMAZON_ASSOCIATES_TRACKING_ID,
            source=AmazonManualAffiliateSource.AMAZON_SITESTRIPE_MANUAL,
            status="unknown_status",  # type: ignore[arg-type]
            quality_status=AmazonManualAffiliateQualityStatus.ACTIVE,
            quality_note=None,
            last_manual_reviewed_at=None,
            operator_note=None,
            created_at="2026-05-15T00:00:00Z",
        )
        result = validate_manual_amazon_record(record)
        self.assertFalse(result.valid)
        self.assertIn("unknown_status", result.errors)


class AmazonAffiliateMatcherTests(unittest.TestCase):
    def test_power_bank_query_returns_eligible(self) -> None:
        result = match_manual_amazon_affiliate("power bank")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        self.assertIsNotNone(result.result)
        assert result.result is not None
        self.assertIn("tag=picwise-20", result.result.affiliate_url)
        self.assertEqual(result.result.disclosure, AMAZON_ASSOCIATE_DISCLOSURE)

    def test_power_bank_query_returns_four_eligible_results(self) -> None:
        result = match_manual_amazon_affiliates("power bank")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        self.assertEqual(len(result.results), 3)
        self.assertSetEqual(
            {entry.asin for entry in result.results},
            {"B0FQJH2XSY", "B0GR1257LT", "B0GH75LWKN"},
        )
        self.assertNotIn("B08K7GHZ3V", {entry.asin for entry in result.results})

    def test_powerbank_query_returns_four_eligible_results(self) -> None:
        result = match_manual_amazon_affiliates("powerbank")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        self.assertEqual(len(result.results), 3)

    def test_compact_power_bank_query_includes_compact_asin(self) -> None:
        result = match_manual_amazon_affiliates("compact power bank")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        compact_asins = {entry.asin for entry in result.results}
        self.assertIn("B0FQJH2XSY", compact_asins)

    def test_20000mah_query_includes_20000mah_asin(self) -> None:
        result = match_manual_amazon_affiliates("20000mah power bank")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        asins = {entry.asin for entry in result.results}
        self.assertIn("B0GR1257LT", asins)

    def test_powerbank_fast_charging_query_returns_eligible(self) -> None:
        result = match_manual_amazon_affiliate("powerbank fast charging")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)

    def test_portable_charger_query_returns_eligible(self) -> None:
        result = match_manual_amazon_affiliate("portable charger")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)

    def test_unrelated_query_returns_no_match(self) -> None:
        result = match_manual_amazon_affiliate("laptop")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.NO_MATCH)
        multi_result = match_manual_amazon_affiliates("laptop")
        self.assertEqual(multi_result.match_status, AmazonManualMatchStatus.NO_MATCH)
        self.assertEqual(len(multi_result.results), 0)

    def test_every_eligible_result_url_contains_required_tag(self) -> None:
        result = match_manual_amazon_affiliates("portable charger")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        self.assertEqual(len(result.results), 3)
        for entry in result.results:
            self.assertIn("tag=picwise-20", entry.affiliate_url)

    def test_eligible_safe_result_has_no_forbidden_data_fields(self) -> None:
        result = match_manual_amazon_affiliate("charger 10500mah")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        assert result.result is not None
        payload = asdict(result.result)
        for forbidden in (
            "price",
            "rating",
            "review_count",
            "image_url",
            "stock",
            "prime",
            "availability",
        ):
            self.assertNotIn(forbidden, payload)
        self.assertEqual(payload["disclosure"], "As an Amazon Associate I earn from qualifying purchases.")
        self.assertEqual(payload["safe_note"], AMAZON_SAFE_NOTE)

    def test_get_approved_record_by_asin_returns_expected_record(self) -> None:
        record = get_approved_manual_amazon_record_by_asin("B0FQJH2XSY")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.asin, "B0FQJH2XSY")
        self.assertEqual(record.status, AmazonManualAffiliateStatus.APPROVED)
        self.assertEqual(record.quality_status, AmazonManualAffiliateQualityStatus.ACTIVE)

    def test_get_approved_record_by_asin_rejects_unknown_or_invalid(self) -> None:
        self.assertIsNone(get_approved_manual_amazon_record_by_asin("B000000000"))
        self.assertIsNone(get_approved_manual_amazon_record_by_asin("https://evil.example"))
        self.assertIsNone(get_approved_manual_amazon_record_by_asin("B08K7GHZ3V"))

    def test_disabled_record_is_retained_for_audit_history(self) -> None:
        records = [record for record in MANUAL_AMAZON_AFFILIATE_REGISTRY if record.asin == "B08K7GHZ3V"]
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.status, AmazonManualAffiliateStatus.DISABLED)
        self.assertEqual(record.quality_status, AmazonManualAffiliateQualityStatus.UNAVAILABLE_MANUAL)


if __name__ == "__main__":
    unittest.main()
