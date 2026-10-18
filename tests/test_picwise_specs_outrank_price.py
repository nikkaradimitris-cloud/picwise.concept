"""A stated specification decides the recommendation before the price does.

The owner's rule, held since 2026-10-11: the recommendation must not rest on price.
Until now it did, because the feed gave nothing else -- the first reason code on a
real answer was literally `price_tie_breaker`. These tests pin the route out of that:
where the kind of product has a criterion whose direction no buyer would dispute, and
the feed states it, the specification decides and price falls back to the last resort
it was always meant to be.

Three conditions keep it from overclaiming, and each has a test here: the kind must
carry a ranking criterion at all, at least two of the four must state the same one,
and every value must come from something the feed stated **as a property** rather than
from a number loose in marketing prose.

All rows are local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.search_selection import (  # noqa: E402
    _comparable_ranking_property,
    decide_recommended_provider_product,
)
from picwise_surface.reference import _FEED_RECOMMENDATION_REASON_LABELS  # noqa: E402
from picwise_taxonomy.comparison_rules import RANKING_CRITERIA  # noqa: E402


def _product(
    pid: str,
    title: str,
    price: str,
    *,
    kind: str = "TV Boxes",
    description: str = "",
) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand=title.split()[0],
        category_text=kind,
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in stock",
        currency="GBP",
        raw={
            "product_type": kind,
            "in_stock": "1",
            "aw_deep_link": f"https://fixture.example.invalid/out/{pid}",
            "description": description or fixture_description(),
        },
    )


def _decide(products, query: str, concept_id: str):
    return decide_recommended_provider_product(
        query,
        tuple(products),
        concept_verified=True,
        concept_id=concept_id,
    )


class SpecificationDecidesTests(unittest.TestCase):
    def test_more_storage_wins_over_a_lower_price(self) -> None:
        # The whole point: the dearer box wins because it holds four times as much.
        four = (
            _product("cheap", "Testline Android TV Box 8GB ROM", "39.00"),
            _product("best", "Testline Android TV Box 64GB ROM", "49.00"),
            _product("mid", "Testline Android TV Box 32GB ROM", "59.00"),
            _product("dear", "Testline Android TV Box 16GB ROM", "79.00"),
        )
        decision = _decide(four, "tv box", "tv_box")
        self.assertEqual(decision.recommended_product_id, "best")
        self.assertEqual(decision.recommendation_reason_codes[0], "better_storage")
        self.assertNotIn("price_tie_breaker", decision.recommendation_reason_codes)

    def test_a_ram_figure_never_decides_a_storage_ranking(self) -> None:
        # "4GB RAM 64GB ROM": ranking on the 4 would recommend the wrong box.
        four = (
            _product("a", "Testline TV Box 8GB RAM 32GB ROM", "39.00"),
            _product("b", "Testline TV Box 2GB RAM 128GB ROM", "49.00"),
            _product("c", "Testline TV Box 4GB RAM 64GB ROM", "59.00"),
            _product("d", "Testline TV Box 1GB RAM 16GB ROM", "29.00"),
        )
        self.assertEqual(_decide(four, "tv box", "tv_box").recommended_product_id, "b")

    def test_a_larger_battery_wins_for_a_power_bank(self) -> None:
        four = (
            _product("small", "Testline Powerbank 5000mAh", "15.00", kind="Power Banks"),
            _product("big", "Testline Powerbank 20000mAh", "35.00", kind="Power Banks"),
            _product("mid", "Testline Powerbank 10000mAh", "22.00", kind="Power Banks"),
            _product("tiny", "Testline Powerbank 2000mAh", "9.00", kind="Power Banks"),
        )
        decision = _decide(four, "power bank", "power_bank")
        self.assertEqual(decision.recommended_product_id, "big")
        self.assertEqual(decision.recommendation_reason_codes[0], "better_battery")


class WhenItMustNotDecideTests(unittest.TestCase):
    def test_a_kind_with_no_ranking_criterion_is_untouched(self) -> None:
        # More watts is not a better amplifier, and more metres is not a better cable.
        for concept_id, kind, titles in (
            ("amplifier", "Amplifiers", ("Amplifier 50W", "Amplifier 200W",
                                         "Amplifier 100W", "Amplifier 20W")),
            ("charging_cable", "Cables", ("USB Cable 0.5 m", "USB Cable 3 m",
                                          "USB Cable 1 m", "USB Cable 2 m")),
        ):
            with self.subTest(concept_id=concept_id):
                four = tuple(
                    _product(f"p{index}", f"Testline {title}", f"{10 + index}.00", kind=kind)
                    for index, title in enumerate(titles)
                )
                prop, values = _comparable_ranking_property(four, concept_id)
                self.assertEqual(prop, "")
                self.assertEqual(values, {})

    def test_one_product_stating_a_specification_is_not_a_comparison(self) -> None:
        # A fact about one product is not a ranking of four.
        four = (
            _product("only", "Testline Android TV Box 64GB ROM", "59.00"),
            _product("b", "Testline Android TV Box", "39.00"),
            _product("c", "Testline Android TV Box Pro", "49.00"),
            _product("d", "Testline Android TV Box Max", "69.00"),
        )
        self.assertEqual(_comparable_ranking_property(four, "tv_box")[0], "")

    def test_a_number_loose_in_marketing_prose_never_ranks(self) -> None:
        # "works with 128 GB cards" is not this box's storage.
        prose = fixture_description("Plays everything and works with 128 GB cards.")
        four = (
            _product("a", "Testline Android TV Box", "39.00", description=prose),
            _product("b", "Testline Android TV Box Pro", "49.00", description=prose),
            _product("c", "Testline Android TV Box Max", "59.00", description=prose),
            _product("d", "Testline Android TV Box Lite", "29.00", description=prose),
        )
        self.assertEqual(_comparable_ranking_property(four, "tv_box")[0], "")

    def test_price_still_decides_when_nothing_else_can(self) -> None:
        # The fallback is unchanged, and still says so on the card.
        four = (
            _product("a", "Testline Android TV Box", "39.00"),
            _product("b", "Testline Android TV Box", "49.00"),
            _product("c", "Testline Android TV Box", "59.00"),
            _product("d", "Testline Android TV Box", "29.00"),
        )
        decision = _decide(four, "tv box", "tv_box")
        self.assertEqual(decision.recommendation_reason_codes[0], "price_tie_breaker")


class PartialStatementTests(unittest.TestCase):
    def test_two_of_four_stating_it_is_enough_to_decide(self) -> None:
        four = (
            _product("quiet_a", "Testline Android TV Box", "39.00"),
            _product("stated_low", "Testline Android TV Box 16GB ROM", "45.00"),
            _product("quiet_b", "Testline Android TV Box Pro", "55.00"),
            _product("stated_high", "Testline Android TV Box 64GB ROM", "65.00"),
        )
        prop, values = _comparable_ranking_property(four, "tv_box")
        self.assertEqual(prop, "storage")
        self.assertEqual(len(values), 2)
        decision = _decide(four, "tv box", "tv_box")
        self.assertEqual(decision.recommended_product_id, "stated_high")

    def test_the_label_admits_that_only_some_stated_theirs(self) -> None:
        label = _FEED_RECOMMENDATION_REASON_LABELS["better_storage"]
        self.assertIn("that state theirs", label)


class LabelCoverageTests(unittest.TestCase):
    def test_every_ranking_criterion_has_words_for_the_card(self) -> None:
        # A deciding reason with no label renders as nothing, which would leave the
        # recommended card without the one line that says why.
        for criterion in RANKING_CRITERIA:
            with self.subTest(criterion=criterion):
                self.assertIn(f"better_{criterion}", _FEED_RECOMMENDATION_REASON_LABELS)


if __name__ == "__main__":
    unittest.main()
