from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers import (  # noqa: E402
    ExternalOffer,
    ExternalOfferStatus,
    OfferRankingReason,
    RankedOffer,
    RedirectProofInput,
    RedirectStatus,
    build_redirect_proof,
)


def _ranked_offer(
    offer_id: str = "offer-1",
    *,
    external_url: str = "https://example.com/products/offer-1",
    affiliate_url: str = "https://example.invalid/aff/offer-1",
    status: ExternalOfferStatus = ExternalOfferStatus.VALID_EXTERNAL_OFFER,
) -> RankedOffer:
    return RankedOffer(
        offer=ExternalOffer(
            offer_id=offer_id,
            external_product_title="best running shoes",
            external_store="Example Store",
            external_url=external_url,
            price=99.0,
            availability="available",
            delivery="next day delivery",
            returns="free returns in 30-day period",
            review_score=4.5,
            affiliate_url=affiliate_url,
            data_source="fixture_redirect",
            status=status,
            is_external_temporary_data=True,
            pickwise_owned_inventory=False,
        ),
        weighted_score=0.9,
        reasons=(OfferRankingReason.AFFILIATE_URL_VALID,),
        data_completeness=1.0,
    )


class RedirectProofStage28CTests(unittest.TestCase):
    def test_selected_valid_offer_produces_redirect_ready(self) -> None:
        result = build_redirect_proof(
            RedirectProofInput(
                decision_id="decision-1",
                intent_label="best running shoes",
                selected_offer=_ranked_offer(),
                timestamp="2026-01-01T00:00:00Z",
            )
        )
        self.assertEqual(result.status, RedirectStatus.REDIRECT_READY)
        self.assertEqual(result.redirect_target_url, "https://example.invalid/aff/offer-1")
        assert result.tracking_payload is not None
        self.assertEqual(result.tracking_payload.source, "pickwise_external_offer_redirect_proof")
        self.assertTrue(result.tracking_payload.test_mode)

    def test_missing_url_blocks_redirect(self) -> None:
        result = build_redirect_proof(
            RedirectProofInput(
                decision_id="decision-2",
                intent_label="best running shoes",
                selected_offer=_ranked_offer(external_url=""),
            )
        )
        self.assertEqual(result.status, RedirectStatus.BLOCKED_MISSING_URL)

    def test_invalid_affiliate_url_blocks_redirect(self) -> None:
        result = build_redirect_proof(
            RedirectProofInput(
                decision_id="decision-3",
                intent_label="best running shoes",
                selected_offer=_ranked_offer(affiliate_url="javascript:alert(1)"),
            )
        )
        self.assertEqual(result.status, RedirectStatus.BLOCKED_INVALID_AFFILIATE_URL)

    def test_tracking_payload_is_deterministic(self) -> None:
        payload_input = RedirectProofInput(
            decision_id="decision-4",
            intent_label="best running shoes",
            selected_offer=_ranked_offer(),
            timestamp="2026-01-01T00:00:00Z",
        )
        first = build_redirect_proof(payload_input)
        second = build_redirect_proof(payload_input)
        self.assertEqual(first, second)

    def test_affiliate_url_treated_as_external_input_not_owned_inventory(self) -> None:
        result = build_redirect_proof(
            RedirectProofInput(
                decision_id="decision-5",
                intent_label="best running shoes",
                selected_offer=_ranked_offer(),
            )
        )
        assert result.tracking_payload is not None
        self.assertTrue(result.tracking_payload.affiliate_url_present)
        self.assertEqual(result.tracking_payload.external_store, "Example Store")

    def test_no_production_router_route_or_live_network_call_exists(self) -> None:
        source_text = inspect.getsource(build_redirect_proof)
        forbidden_runtime_tokens = ("FastAPI", "APIRouter", "add_api_route", "@app.", "@router.")
        forbidden_network_tokens = (
            "requests",
            "httpx",
            "urllib",
            "BeautifulSoup",
            "selenium",
            "playwright",
            "scrapy",
            "aiohttp",
            "fetch(",
            "Invoke-WebRequest",
            "curl",
        )
        for token in forbidden_runtime_tokens + forbidden_network_tokens:
            self.assertNotIn(token, source_text)


if __name__ == "__main__":
    unittest.main()
