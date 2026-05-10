from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search.offer_resolver import (  # noqa: E402
    SpecificProductIdentity,
    SpecificProductOffer,
    build_normalized_key,
    resolve_specific_product_offer_set,
)


def _make_identity() -> SpecificProductIdentity:
    brand = "Goodyear"
    model = "EfficientGrip Performance 2"
    size = "195/65 R15"
    return SpecificProductIdentity(
        brand=brand,
        model=model,
        title=f"{brand} {model} {size}",
        size_specs=size,
        normalized_key=build_normalized_key(brand, model, size),
    )


def _make_offer(
    *,
    seller: str,
    price: float,
    brand: str = "Goodyear",
    model: str = "EfficientGrip Performance 2",
    size_specs: str = "195/65 R15",
    availability: str = "in_stock",
    seller_reliability: str = "trusted",
    store_rating: float = 4.6,
    review_count: int = 300,
    delivery_returns_available: bool = True,
    affiliate_url_valid: bool = True,
    data_completeness: float = 0.9,
) -> SpecificProductOffer:
    return SpecificProductOffer(
        brand=brand,
        model=model,
        title=f"{brand} {model} {size_specs}",
        size_specs=size_specs,
        seller_or_store=seller,
        price=price,
        currency="EUR",
        availability=availability,
        seller_reliability=seller_reliability,
        store_rating=store_rating,
        review_count=review_count,
        delivery_returns_available=delivery_returns_available,
        affiliate_url_valid=affiliate_url_valid,
        data_completeness=data_completeness,
        normalized_key=build_normalized_key(brand, model, size_specs),
    )


class SpecificProductOfferResolverTests(unittest.TestCase):
    def test_exact_key_match_accepts_same_brand_model_size(self) -> None:
        identity = _make_identity()
        exact = _make_offer(seller="Store A", price=120.0)
        different_brand = _make_offer(seller="Store B", price=118.0, brand="Michelin")
        offer_set, ranking = resolve_specific_product_offer_set(identity, [exact, different_brand])
        self.assertEqual(offer_set.status, "ready")
        self.assertEqual(len(offer_set.offers), 1)
        self.assertEqual(ranking.ranked_offers[0].seller_or_store, "Store A")

    def test_different_model_rejected(self) -> None:
        identity = _make_identity()
        wrong_model = _make_offer(seller="Store A", price=115.0, model="EfficientGrip Performance 3")
        offer_set, _ = resolve_specific_product_offer_set(identity, [wrong_model])
        self.assertEqual(offer_set.status, "no_valid_offers")
        self.assertEqual(len(offer_set.offers), 0)

    def test_different_size_specs_rejected(self) -> None:
        identity = _make_identity()
        wrong_size = _make_offer(seller="Store A", price=115.0, size_specs="205/55 R16")
        offer_set, _ = resolve_specific_product_offer_set(identity, [wrong_size])
        self.assertEqual(offer_set.status, "no_valid_offers")
        self.assertEqual(len(offer_set.offers), 0)

    def test_similar_product_rejected(self) -> None:
        identity = _make_identity()
        similar = _make_offer(seller="Store A", price=115.0, model="EfficientGrip Performance")
        offer_set, _ = resolve_specific_product_offer_set(identity, [similar])
        self.assertEqual(offer_set.status, "no_valid_offers")
        self.assertEqual(len(offer_set.offers), 0)

    def test_returns_one_valid_offer_without_filler(self) -> None:
        identity = _make_identity()
        valid = _make_offer(seller="Store A", price=118.0)
        blocked = _make_offer(seller="Store B", price=117.0, seller_reliability="blocked")
        offer_set, _ = resolve_specific_product_offer_set(identity, [valid, blocked])
        self.assertEqual(offer_set.status, "ready")
        self.assertEqual(len(offer_set.offers), 1)

    def test_returns_two_valid_offers_without_filler(self) -> None:
        identity = _make_identity()
        offer_a = _make_offer(seller="Store A", price=118.0)
        offer_b = _make_offer(seller="Store B", price=122.0, seller_reliability="acceptable")
        offer_set, ranking = resolve_specific_product_offer_set(identity, [offer_a, offer_b])
        self.assertEqual(offer_set.status, "ready")
        self.assertEqual(len(offer_set.offers), 2)
        self.assertEqual(len(ranking.ranked_offers), 2)

    def test_caps_valid_offers_at_four(self) -> None:
        identity = _make_identity()
        offers = [
            _make_offer(seller="Store 1", price=111.0),
            _make_offer(seller="Store 2", price=112.0),
            _make_offer(seller="Store 3", price=113.0),
            _make_offer(seller="Store 4", price=114.0),
            _make_offer(seller="Store 5", price=115.0),
        ]
        offer_set, ranking = resolve_specific_product_offer_set(identity, offers)
        self.assertEqual(offer_set.status, "ready")
        self.assertEqual(len(offer_set.offers), 4)
        self.assertEqual(len(ranking.ranked_offers), 4)
        self.assertIn("capped_to_4_offers", offer_set.reason_codes)

    def test_zero_valid_offers_returns_no_valid_offers(self) -> None:
        identity = _make_identity()
        unrelated = _make_offer(seller="Store A", price=110.0, brand="Pirelli")
        offer_set, ranking = resolve_specific_product_offer_set(identity, [unrelated])
        self.assertEqual(offer_set.status, "no_valid_offers")
        self.assertEqual(ranking.status, "no_valid_offers")
        self.assertEqual(len(ranking.ranked_offers), 0)

    def test_insufficient_identity_returns_manual_review_required(self) -> None:
        offer = _make_offer(seller="Store A", price=110.0)
        offer_set, ranking = resolve_specific_product_offer_set(None, [offer])
        self.assertEqual(offer_set.status, "manual_review_required")
        self.assertEqual(ranking.status, "manual_review_required")
        self.assertIn("insufficient_identity", offer_set.reason_codes)

    def test_ranking_not_price_only(self) -> None:
        identity = _make_identity()
        cheap_weak = _make_offer(
            seller="Cheap Weak",
            price=95.0,
            availability="unknown",
            seller_reliability="acceptable",
            store_rating=2.9,
            review_count=3,
            delivery_returns_available=False,
            data_completeness=0.45,
            affiliate_url_valid=False,
        )
        trusted_expensive = _make_offer(
            seller="Trusted Strong",
            price=112.0,
            availability="in_stock",
            seller_reliability="trusted",
            store_rating=4.9,
            review_count=1200,
            delivery_returns_available=True,
            data_completeness=0.98,
            affiliate_url_valid=True,
        )
        _, ranking = resolve_specific_product_offer_set(identity, [cheap_weak, trusted_expensive])
        self.assertEqual(ranking.status, "ready")
        self.assertEqual(ranking.ranked_offers[0].seller_or_store, "Trusted Strong")

    def test_unknown_seller_does_not_auto_ready_public_recommendation(self) -> None:
        identity = _make_identity()
        unknown = _make_offer(seller="Unknown Store", price=109.0, seller_reliability="unknown")
        offer_set, ranking = resolve_specific_product_offer_set(identity, [unknown])
        self.assertEqual(offer_set.status, "manual_review_required")
        self.assertEqual(ranking.status, "manual_review_required")
        self.assertEqual(len(ranking.ranked_offers), 0)

    def test_unreliable_or_blocked_sellers_rejected(self) -> None:
        identity = _make_identity()
        unreliable = _make_offer(seller="Bad A", price=100.0, seller_reliability="unreliable")
        blocked = _make_offer(seller="Bad B", price=101.0, seller_reliability="blocked")
        offer_set, ranking = resolve_specific_product_offer_set(identity, [unreliable, blocked])
        self.assertEqual(offer_set.status, "no_valid_offers")
        self.assertEqual(ranking.status, "no_valid_offers")
        self.assertIn("seller_blocked_or_unreliable", offer_set.reason_codes)

    def test_deterministic_tie_break(self) -> None:
        identity = _make_identity()
        offer_b = _make_offer(seller="Beta Store", price=120.0)
        offer_a = _make_offer(seller="Alpha Store", price=120.0)
        _, ranking = resolve_specific_product_offer_set(identity, [offer_b, offer_a])
        self.assertEqual(ranking.status, "ready")
        self.assertEqual(ranking.ranked_offers[0].seller_or_store, "Alpha Store")


if __name__ == "__main__":
    unittest.main()
