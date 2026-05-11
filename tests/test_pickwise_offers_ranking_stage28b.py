from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers import (  # noqa: E402
    ExternalOffer,
    ExternalOfferSource,
    ExternalOfferSourceType,
    ExternalOfferStatus,
    OfferRankingInput,
    OfferRankingReason,
    OfferRankingStatus,
    rank_external_offers,
    validate_external_offer,
)


def _offer_payload(offer_id: str, **overrides: object) -> dict:
    payload: dict[str, object] = {
        "offer_id": offer_id,
        "external_product_title": "best running shoes air flex",
        "external_store": "Example Store",
        "external_url": f"https://example.com/products/{offer_id}",
        "price": 99.0,
        "availability": "available",
        "delivery": "next day delivery",
        "returns": "free returns in 30-day period",
        "review_score": 4.5,
        "affiliate_url": f"https://example.invalid/aff/{offer_id}",
        "data_source": "fixture_batch",
        "is_external_offer": True,
    }
    payload.update(overrides)
    return payload


def _validated_offer(payload: dict) -> ExternalOffer:
    source = ExternalOfferSource(
        source_id="fixture-source",
        source_type=ExternalOfferSourceType.FIXTURE,
        source_label="fixture_source",
    )
    result = validate_external_offer(payload, source)
    assert result.offer is not None
    return result.offer


class OfferRankingStage28BTests(unittest.TestCase):
    def test_valid_offers_rank_deterministically(self) -> None:
        offers = (
            _validated_offer(_offer_payload("offer-a", price=89.0)),
            _validated_offer(_offer_payload("offer-b", price=109.0)),
            _validated_offer(_offer_payload("offer-c", price=119.0)),
            _validated_offer(_offer_payload("offer-d", price=139.0)),
        )
        ranking_input = OfferRankingInput(intent_label="best running shoes", offers=offers)
        first = rank_external_offers(ranking_input)
        second = rank_external_offers(ranking_input)
        self.assertEqual(first, second)
        self.assertEqual(first.status, OfferRankingStatus.RANKED)

    def test_top_4_options_selected_when_available(self) -> None:
        offers = tuple(_validated_offer(_offer_payload(f"offer-{index}", price=80.0 + index * 10)) for index in range(1, 6))
        result = rank_external_offers(OfferRankingInput(intent_label="best running shoes", offers=offers))
        self.assertEqual(len(result.top_offers), 4)

    def test_single_recommended_offer_selected_when_safe(self) -> None:
        offers = (
            _validated_offer(_offer_payload("offer-top", price=79.0, review_score=4.9)),
            _validated_offer(_offer_payload("offer-mid", price=109.0, review_score=4.0)),
            _validated_offer(_offer_payload("offer-low", price=129.0, review_score=3.9)),
            _validated_offer(_offer_payload("offer-low2", price=149.0, review_score=3.8)),
        )
        result = rank_external_offers(OfferRankingInput(intent_label="best running shoes", offers=offers))
        self.assertEqual(result.status, OfferRankingStatus.RANKED)
        self.assertEqual(result.recommended_offer_id, "offer-top")

    def test_unavailable_or_invalid_offers_are_excluded(self) -> None:
        valid_offer = _validated_offer(_offer_payload("offer-valid", price=88.0))
        unavailable_offer = _validated_offer(_offer_payload("offer-unavailable", availability="out_of_stock"))
        invalid_offer = ExternalOffer(
            offer_id="offer-invalid",
            external_product_title="best running shoes",
            external_store="Example Store",
            external_url="https://example.com/products/offer-invalid",
            price=88.0,
            availability="available",
            delivery="next day",
            returns="free returns",
            review_score=4.4,
            affiliate_url="https://example.invalid/aff/offer-invalid",
            data_source="fixture",
            status=ExternalOfferStatus.INVALID_EXTERNAL_OFFER,
        )
        result = rank_external_offers(
            OfferRankingInput(
                intent_label="best running shoes",
                offers=(valid_offer, unavailable_offer, invalid_offer),
            )
        )
        self.assertEqual(result.status, OfferRankingStatus.INSUFFICIENT_VALID_OFFERS)
        self.assertEqual([entry.offer.offer_id for entry in result.top_offers], ["offer-valid"])

    def test_incomplete_but_usable_offers_rank_lower(self) -> None:
        complete_offer = _validated_offer(_offer_payload("offer-complete", price=95.0))
        incomplete_offer = _validated_offer(
            _offer_payload(
                "offer-incomplete",
                price=90.0,
                delivery="unknown",
                returns="n/a",
                data_source="unknown",
            )
        )
        result = rank_external_offers(
            OfferRankingInput(intent_label="best running shoes", offers=(complete_offer, incomplete_offer))
        )
        self.assertEqual(result.top_offers[0].offer.offer_id, "offer-complete")
        self.assertIn(OfferRankingReason.LOWER_DATA_COMPLETENESS, result.top_offers[1].reasons)

    def test_insufficient_offers_do_not_get_fake_filled(self) -> None:
        offers = (_validated_offer(_offer_payload("offer-only", price=99.0)),)
        result = rank_external_offers(OfferRankingInput(intent_label="best running shoes", offers=offers))
        self.assertEqual(result.status, OfferRankingStatus.INSUFFICIENT_VALID_OFFERS)
        self.assertEqual(len(result.top_offers), 1)

    def test_ambiguous_ranking_returns_manual_review_required(self) -> None:
        offers = (
            _validated_offer(_offer_payload("offer-a", price=100.0, review_score=4.4)),
            _validated_offer(_offer_payload("offer-b", price=100.0, review_score=4.4)),
            _validated_offer(_offer_payload("offer-c", price=130.0, review_score=3.8)),
        )
        result = rank_external_offers(OfferRankingInput(intent_label="best running shoes", offers=offers))
        self.assertEqual(result.status, OfferRankingStatus.MANUAL_REVIEW_REQUIRED)
        self.assertIsNone(result.recommended_offer_id)

    def test_no_unrelated_fallback_offer_returned(self) -> None:
        offers = (
            _validated_offer(_offer_payload("offer-1", price=90.0)),
            _validated_offer(_offer_payload("offer-2", price=99.0)),
        )
        result = rank_external_offers(OfferRankingInput(intent_label="best running shoes", offers=offers))
        returned_ids = {entry.offer.offer_id for entry in result.top_offers}
        self.assertTrue(returned_ids.issubset({"offer-1", "offer-2"}))

    def test_ranking_reasons_are_explainable(self) -> None:
        offers = (
            _validated_offer(_offer_payload("offer-1", price=85.0)),
            _validated_offer(_offer_payload("offer-2", price=110.0)),
        )
        result = rank_external_offers(OfferRankingInput(intent_label="best running shoes", offers=offers))
        first_reasons = result.top_offers[0].reasons
        self.assertTrue(len(first_reasons) >= 2)
        self.assertIn(OfferRankingReason.AFFILIATE_URL_VALID, first_reasons)


if __name__ == "__main__":
    unittest.main()
