"""The products that fit a complex search first (owner, 2026-11-06).

«Όταν η αναζήτηση είναι συνθετή και το ai έχει εμπλακεί στον ευρετηριασμό τα προϊόντα που
υποδεικνύει πρέπει να έχουν λεκτική αναφορά αλλά και οπτική σημείωση καθώς πρέπει να
κατατάσσονται και πρώτα», then «Ναι, συμφωνώ με όλα, προχώρα» to the order, the time and
the mark proposed (the Decision Contract, "The products that fit a complex search first").
Pinned here:

- the order: the products that fit first, in the usual order among them (on offer first,
  then cheapest), then the rest in the usual order; "More" goes on in that order;
- the Recommended chosen among those that fit by its own rules (on offer when an offer
  covers one of them, else the middle one in price with a code), none with fewer than
  three that fit;
- the products the AI reads are named by a signature of their ids and prices in the usual
  order, the same with or without an answer applied, and another when a price changes;
- nothing changes without an answer, with an empty one, with ids the AI never read, or
  when the stored answer cannot be read.

Every product is fictional; the feed rows are served as the price-first tests serve them.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.search_selection import (  # noqa: E402
    AI_CANDIDATES,
    _fitting_first,
    _price_first_products,
    candidates_signature,
)
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402
from test_picwise_price_first import _ean, _offer, _PageMixin  # noqa: E402

PRICES = [20, 30, 40, 50, 60, 70, 80, 90, 100]


def _ids(rows) -> list[str]:
    return [str(row.get("provider_product_id") or "") for row in rows]


class FittingFirstOrderTests(unittest.TestCase):
    """The order itself, on an answer cheapest first."""

    def _answer(self, prices=PRICES):
        return _price_first_products(
            [_offer(f"k{index + 1}", price, gtin=_ean(500000001000 + index)) for index, price in enumerate(prices)]
        )

    @staticmethod
    def _order_ids(order) -> list[str]:
        return [entry.product.provider_product_id for entry in order]

    def test_the_fitting_first_the_recommended_their_middle_then_the_rest(self) -> None:
        order, recommended, status, for_offer = _fitting_first(self._answer(), {}, frozenset({"k2", "k7", "k9"}))
        # The three that fit, £30, £80 and £100: their middle is £80.
        self.assertEqual((recommended.product.provider_product_id, status, for_offer), ("k7", "recommended", False))
        self.assertEqual(self._order_ids(order), ["k7", "k2", "k9", "k1", "k3", "k4", "k5", "k6", "k8"])

    def test_fewer_than_three_that_fit_have_no_recommended(self) -> None:
        order, recommended, status, _for_offer = _fitting_first(self._answer(), {}, frozenset({"k3", "k8"}))
        self.assertIsNone(recommended)
        self.assertEqual(status, "too_few_products")
        self.assertEqual(self._order_ids(order), ["k3", "k8", "k1", "k2", "k4", "k5", "k6", "k7", "k9"])

    def test_an_offer_among_the_fitting_is_their_recommended_and_offers_lead_each_part(self) -> None:
        answer = self._answer()
        by_id = {entry.product.provider_product_id: entry for entry in answer}
        # An offer covers k9 (fits) and k1 (does not fit).
        covered = {id(by_id["k9"].product): object(), id(by_id["k1"].product): object()}
        order, recommended, status, for_offer = _fitting_first(answer, covered, frozenset({"k2", "k7", "k9"}))
        self.assertEqual((recommended.product.provider_product_id, status, for_offer), ("k9", "recommended", True))
        # Then the others that fit, cheapest first; then the rest: on offer first.
        self.assertEqual(self._order_ids(order), ["k9", "k2", "k7", "k1", "k3", "k4", "k5", "k6", "k8"])

    def test_the_signature_is_the_ids_and_prices_in_order(self) -> None:
        first = candidates_signature([("k1", 20.0), ("k2", 30.0)])
        self.assertEqual(len(first), 32)
        self.assertEqual(first, candidates_signature([("k1", 20), ("k2", 30.00)]))
        self.assertNotEqual(first, candidates_signature([("k2", 30.0), ("k1", 20.0)]))
        self.assertNotEqual(first, candidates_signature([("k1", 20.0), ("k2", 30.01)]))
        self.assertEqual(AI_CANDIDATES, 30)


class FittingFirstSearchTests(_PageMixin, unittest.TestCase):
    """The whole search, served from fictional feed rows, as the site runs it."""

    def setUp(self) -> None:
        self._serve(self._kettles(PRICES))

    def test_without_an_answer_the_usual_order_and_its_signature(self) -> None:
        plain = resolve_live_search("kettle")
        asked: list[str] = []
        empty = resolve_live_search("kettle", fitting_for=lambda signature: asked.append(signature) or ())
        self.assertEqual(_ids(plain.provider_feed_selected_products), ["k5", "k1", "k2", "k3"])
        self.assertEqual(_ids(empty.provider_feed_selected_products), ["k5", "k1", "k2", "k3"])
        self.assertEqual(empty.provider_feed_recommended_product_id, "k5")
        self.assertEqual(asked, [plain.provider_feed_candidates_signature])
        self.assertEqual(len(plain.provider_feed_candidates_signature), 32)
        self.assertEqual(plain.provider_feed_fitting_product_ids, ())
        self.assertFalse(plain.provider_feed_recommended_among_fitting)
        # The signature is of the usual order: k5 first, then the rest cheapest first.
        self.assertEqual(
            plain.provider_feed_candidates_signature,
            candidates_signature([("k5", 60), ("k1", 20), ("k2", 30), ("k3", 40), ("k4", 50), ("k6", 70),
                                  ("k7", 80), ("k8", 90), ("k9", 100)]),
        )

    def test_the_answer_puts_the_fitting_first_with_their_own_recommended(self) -> None:
        plain = resolve_live_search("kettle")
        given: dict[str, tuple[str, ...]] = {plain.provider_feed_candidates_signature: ("k9", "k2", "k7")}
        fitted = resolve_live_search("kettle", fitting_for=given.get)
        self.assertEqual(_ids(fitted.provider_feed_selected_products), ["k7", "k2", "k9", "k1"])
        self.assertEqual(fitted.provider_feed_recommended_product_id, "k7")
        self.assertTrue(fitted.provider_feed_recommended_among_fitting)
        self.assertEqual(fitted.provider_feed_fitting_product_ids, ("k7", "k2", "k9"))
        # The signature stays the usual order's, so the answer is found again.
        self.assertEqual(fitted.provider_feed_candidates_signature, plain.provider_feed_candidates_signature)
        self.assertEqual(fitted.provider_feed_total_count, 9)
        # "More" goes on in that order.
        more = resolve_live_search("kettle", shown=8, fitting_for=given.get)
        self.assertEqual(_ids(more.provider_feed_selected_products + more.provider_feed_more_products),
                         ["k7", "k2", "k9", "k1", "k3", "k4", "k5", "k6"])

    def test_two_that_fit_come_first_with_no_recommended(self) -> None:
        plain = resolve_live_search("kettle")
        fitted = resolve_live_search(
            "kettle", fitting_for={plain.provider_feed_candidates_signature: ("k3", "k8")}.get
        )
        self.assertEqual(_ids(fitted.provider_feed_selected_products), ["k3", "k8", "k1", "k2"])
        self.assertFalse(fitted.provider_feed_recommended_product_id)
        self.assertFalse(fitted.provider_feed_recommended_among_fitting)

    def test_ids_the_ai_never_read_and_an_answer_that_cannot_be_read_change_nothing(self) -> None:
        plain = resolve_live_search("kettle")

        def broken(_signature: str):
            raise ValueError("a stored answer that cannot be read")

        for fitting_for in (lambda _signature: ("k404", ""), broken, lambda _signature: None):
            resolution = resolve_live_search("kettle", fitting_for=fitting_for)
            self.assertEqual(_ids(resolution.provider_feed_selected_products), ["k5", "k1", "k2", "k3"])
            self.assertEqual(resolution.provider_feed_recommended_product_id, "k5")
            self.assertEqual(resolution.provider_feed_fitting_product_ids, ())
        # An answer kept under another signature is not this one's.
        other = resolve_live_search("kettle", fitting_for={"0" * 32: ("k2",)}.get)
        self.assertEqual(_ids(other.provider_feed_selected_products), ["k5", "k1", "k2", "k3"])
        self.assertEqual(plain.provider_feed_fitting_product_ids, ())

    def test_another_price_is_another_signature(self) -> None:
        first = resolve_live_search("kettle").provider_feed_candidates_signature
        self._serve(self._kettles(PRICES[:-1] + [101]))
        self.assertNotEqual(resolve_live_search("kettle").provider_feed_candidates_signature, first)


if __name__ == "__main__":
    unittest.main()
