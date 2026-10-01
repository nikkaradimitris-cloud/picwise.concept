"""Coverage for the fact-derived choice labels required by the Decision Contract.

`docs/PICWISE_DECISION_CONTRACT.md` requires `role_label`, `decision_label`,
`key_reasons` and `risk_or_limitation` on each of the four choices. The chosen approach
is fact-derived only: every label restates the feed's own numbers or the verifier's own
evidence, never a judgement about which product is better.

The point of these tests is that a label can never assert something untrue. A wrong
"lowest price" badge on the dearest product would be exactly the fake data PROJECT_RULES
section 4 forbids, so the price-comparison edge cases are covered directly.
"""
from __future__ import annotations

import html
import io
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.index import app as wsgi_app  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.decision_labels import (  # noqa: E402
    SAME_PRICE_ROLE_LABEL,
    UNCOMPARABLE_PRICE_ROLE_LABEL,
    build_fact_based_choice_labels,
    parse_price_amount,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"
_FEED_ENV = "AWIN_FEED_FILE"

_FORBIDDEN_JUDGEMENT_WORDS = (
    "best",
    "great",
    "premium",
    "ideal",
    "perfect",
    "top pick",
    "bargain",
    "excellent",
)


def _rows(*prices: str, currency: str = "GBP") -> list[dict[str, object]]:
    return [
        {
            "provider_product_id": f"p{index}",
            "price_text": price,
            "currency": currency,
        }
        for index, price in enumerate(prices)
    ]


def _roles(*prices: str, currency: str = "GBP") -> list[str]:
    return [
        label.role_label
        for label in build_fact_based_choice_labels(_rows(*prices, currency=currency))
    ]


class PriceParsingTests(unittest.TestCase):
    def test_plain_and_thousands_separated_prices(self) -> None:
        self.assertEqual(parse_price_amount("749.00"), 749.0)
        self.assertEqual(parse_price_amount("1,299.50"), 1299.5)
        self.assertEqual(parse_price_amount("£1,049.99"), 1049.99)

    def test_comma_decimal_convention_is_read_correctly(self) -> None:
        # "1.299,50" is one thousand two hundred ninety-nine and a half, not 1.299.
        self.assertEqual(parse_price_amount("1.299,50"), 1299.5)
        self.assertEqual(parse_price_amount("999,00"), 999.0)
        self.assertEqual(parse_price_amount("19,99 EUR"), 19.99)

    def test_unusable_prices_are_rejected_rather_than_guessed(self) -> None:
        for value in ("", "See details", "Price on request", "0.00", "-5", None):
            with self.subTest(value=value):
                self.assertIsNone(parse_price_amount(value))  # type: ignore[arg-type]


class PriceRankRoleLabelTests(unittest.TestCase):
    def test_four_distinct_prices_get_four_distinct_labels(self) -> None:
        roles = _roles("749.00", "1249.00", "399.00", "1099.00")
        self.assertEqual(
            roles,
            [
                "2nd lowest price of these four",
                "Highest price of these four",
                "Lowest price of these four",
                "3rd lowest price of these four",
            ],
        )

    def test_comma_decimal_prices_are_not_ranked_backwards(self) -> None:
        roles = _roles("1.299,50", "999,00", "1.500,00", "899,00", currency="EUR")
        self.assertEqual(roles[3], "Lowest price of these four")
        self.assertEqual(roles[2], "Highest price of these four")

    def test_equal_prices_do_not_claim_one_is_lowest(self) -> None:
        roles = _roles("99.00", "99.00", "99.00", "99.00")
        self.assertEqual(roles, [SAME_PRICE_ROLE_LABEL] * 4)
        for role in roles:
            self.assertNotIn("Lowest", role)

    def test_tied_cheapest_products_share_the_lowest_label(self) -> None:
        roles = _roles("10.00", "10.00", "20.00", "30.00")
        self.assertEqual(roles[0], "Lowest price of these four")
        self.assertEqual(roles[1], "Lowest price of these four")
        self.assertEqual(roles[3], "Highest price of these four")

    def test_unparseable_price_is_labelled_not_comparable(self) -> None:
        roles = _roles("See details", "10.00", "20.00", "30.00")
        self.assertEqual(roles[0], UNCOMPARABLE_PRICE_ROLE_LABEL)
        self.assertEqual(roles[1], "Lowest price of these four")

    def test_mixed_currencies_are_never_ranked_against_each_other(self) -> None:
        labels = build_fact_based_choice_labels(
            [
                {"provider_product_id": "a", "price_text": "100", "currency": "USD"},
                {"provider_product_id": "b", "price_text": "90", "currency": "GBP"},
                {"provider_product_id": "c", "price_text": "80", "currency": "GBP"},
                {"provider_product_id": "d", "price_text": "70", "currency": "GBP"},
            ]
        )
        for label in labels:
            self.assertEqual(label.role_label, UNCOMPARABLE_PRICE_ROLE_LABEL)

    def test_empty_input_returns_no_labels(self) -> None:
        self.assertEqual(build_fact_based_choice_labels([]), tuple())


class ContractFieldTests(unittest.TestCase):
    def _labels(self):
        return build_fact_based_choice_labels(
            [
                {
                    "provider_product_id": "verified",
                    "price_text": "399.00",
                    "currency": "GBP",
                    "brand": "Sampleworks",
                    "product_type": "Laptops",
                    "verified_purchasable": True,
                    "purchasability_state": "purchasable",
                },
                {
                    "provider_product_id": "unverified",
                    "price_text": "749.00",
                    "currency": "GBP",
                    "brand": "Fixturon",
                    "product_type": "Laptops",
                },
            ]
        )

    def test_every_choice_carries_all_contract_label_fields(self) -> None:
        for label in self._labels():
            self.assertTrue(label.choice_id)
            self.assertTrue(label.role_label)
            self.assertTrue(label.decision_label)
            self.assertTrue(label.key_reasons)
            self.assertLessEqual(len(label.key_reasons), 3)
            self.assertTrue(label.risk_or_limitation)

    def test_verified_and_unverified_choices_state_their_evidence(self) -> None:
        verified, unverified = self._labels()
        self.assertIn(
            "Purchase availability verified on the merchant page", verified.key_reasons
        )
        self.assertIn("verified", verified.risk_or_limitation)
        self.assertIn(
            "Listed as available by the provider feed, not verified",
            unverified.key_reasons,
        )
        self.assertIn("has not verified", unverified.risk_or_limitation)

    def test_labels_never_assert_a_quality_judgement(self) -> None:
        for label in self._labels():
            text = " ".join(
                (label.role_label, label.decision_label, label.risk_or_limitation)
                + tuple(label.key_reasons)
            ).lower()
            for word in _FORBIDDEN_JUDGEMENT_WORDS:
                self.assertNotIn(
                    word,
                    text,
                    msg=(
                        f"label text asserts the unsupported judgement {word!r}; "
                        "PicWise holds no review or benchmark data to back it"
                    ),
                )


class RenderedCardContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_feed = os.environ.get(_FEED_ENV)
        os.environ[_FEED_ENV] = str(FIXTURE_CSV)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._previous_feed is None:
            os.environ.pop(_FEED_ENV, None)
        else:
            os.environ[_FEED_ENV] = self._previous_feed
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def _cards(self, query: str = "laptop") -> list[dict[str, object]]:
        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            return None

        environ: dict[str, object] = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/search",
            "QUERY_STRING": f"q={query}",
            "wsgi.input": io.BytesIO(b""),
            "CONTENT_LENGTH": "0",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "wsgi.url_scheme": "https",
        }
        body = b"".join(wsgi_app(environ, start_response)).decode("utf-8")

        def text(pattern: str, chunk: str) -> str:
            found = re.search(pattern, chunk, re.S)
            if found is None:
                return ""
            return html.unescape(re.sub(r"<[^>]+>", "", found.group(1))).strip()

        cards: list[dict[str, object]] = []
        for match in re.finditer(
            r'<article class="pw-card([^"]*)" data-choice-id="([^"]+)">(.*?)</article>',
            body,
            re.S,
        ):
            classes, choice_id, inner = match.groups()
            cards.append(
                {
                    "choice_id": choice_id,
                    "recommended": "recommended" in classes,
                    "role_label": text(r'<p class="pw-role-label">(.*?)</p>', inner),
                    "decision_label": text(
                        r'<p class="pw-card-description">(.*?)</p>', inner
                    ),
                    "risk": text(r'<p class="pw-warning">(.*?)</p>', inner),
                    "key_reasons": [
                        html.unescape(re.sub(r"<[^>]+>", "", item)).strip()
                        for item in re.findall(
                            r'<li class="pw-feature-item">(.*?)</li>', inner, re.S
                        )
                    ],
                }
            )
        return cards

    def test_all_four_rendered_cards_carry_the_contract_fields(self) -> None:
        cards = self._cards()
        self.assertEqual(len(cards), 4)
        for card in cards:
            self.assertTrue(card["role_label"], card)
            self.assertTrue(card["decision_label"], card)
            self.assertTrue(card["key_reasons"], card)
            self.assertTrue(card["risk"], card)

    def test_choice_id_is_the_real_product_id_not_a_placeholder(self) -> None:
        cards = self._cards()
        for card in cards:
            self.assertTrue(str(card["choice_id"]).startswith("fx-"), card["choice_id"])
            self.assertNotIn("fixed-", str(card["choice_id"]))

    def test_rendered_role_labels_are_distinct_for_distinct_prices(self) -> None:
        roles = [card["role_label"] for card in self._cards()]
        self.assertEqual(len(set(roles)), 4, roles)

    def test_exactly_one_rendered_card_is_recommended(self) -> None:
        cards = self._cards()
        self.assertEqual(sum(1 for card in cards if card["recommended"]), 1)

    def test_unverified_cards_state_the_limitation_on_every_card(self) -> None:
        for card in self._cards():
            self.assertIn("not verified", card["risk"].lower())


if __name__ == "__main__":
    unittest.main()
