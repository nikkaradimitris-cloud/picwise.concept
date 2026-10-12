"""A product PicWise shows always carries a description.

Owner rule, 2026-10-12: "Τα προϊόντα που παρουσιάζει η πλατφόρμα πρέπει πάντα να
έχουν διαθεσιμότητα τιμή επαρκή περιγραφή ... καθώς και εικόνα" -- the products the
platform presents must always have availability, a price, a sufficient description and
an image, the description partly so the pages built from them are not thin content.

Availability, price and image were already required for a card. These tests pin the
description: what counts as one, what does not, and that a feed row without one is
never shown, counted or recommended.

Measured on the first real feed the day the rule was taken: it costs 1,495 of 11,573
products, and the cost falls on shops rather than kinds -- Geekbuying (877 products)
and Xiaomi RO (66) send no descriptions at all, every other shop fills them on 88% to
100% of its rows. `tools/check_awin_feed.py` reports that per shop so the owner can
see which shops it silences.

All rows here are local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import html
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import evaluate_product_eligibility  # noqa: E402
from picwise_providers.product_description import (  # noqa: E402
    DESCRIPTION_MIN_CHARS,
    has_sufficient_description,
    product_description_text,
)
from picwise_providers.state import (  # noqa: E402
    build_feed_availability_context,
    clear_provider_feed_pipeline_cache,
)

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "product_type",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "stock_status",
    "merchant_name", "condition", "description", "data_provenance",
)

_LONG_ENOUGH = fixture_description()


def _row(pid: str, name: str, price: str, **fields: str) -> dict[str, str]:
    row = {
        "aw_product_id": pid,
        "product_name": name,
        "brand_name": name.split()[0],
        "merchant_category": "Kettles",
        "product_type": "Kettles",
        "aw_deep_link": f"https://fixture.example.invalid/out/{pid}",
        "aw_image_url": f"https://fixture.example.invalid/img/{pid}.jpg",
        "search_price": price,
        "currency": "GBP",
        "in_stock": "1",
        "stock_status": "in stock",
        "merchant_name": "Fixture Store One",
        "condition": "new",
        "description": _LONG_ENOUGH,
        "data_provenance": "local_test_fixture",
    }
    row.update(fields)
    return row


def _kettles(count: int, *, described: int | None = None) -> list[dict[str, str]]:
    """`count` kettles, the first `described` of them with a description."""
    names = ("Boil", "Steam", "Mini", "Glass", "Quiet", "Travel")
    shown = count if described is None else described
    return [
        _row(
            f"k{index}",
            f"Testline {names[index % len(names)]} Kettle 1.{index}L",
            f"{10 + 5 * index}.00",
            **({} if index < shown else {"description": ""}),
        )
        for index in range(count)
    ]


def _product(pid: str, **raw: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=raw.pop("title", f"Fixturon Kettle {pid}"),
        brand="Fixturon",
        category_text="Kettles",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text="20.00",
        availability_text="in stock",
        currency="GBP",
        raw={"product_type": "Kettles", "in_stock": "1", **raw},
    )


def _card_result(product: ProviderProduct):
    ctx = build_feed_availability_context((product,))
    return evaluate_product_eligibility(product, feed_ctx=ctx)


class WhatCountsAsADescriptionTests(unittest.TestCase):
    def test_no_description_at_all_is_not_one(self) -> None:
        for value in ("", "   ", None):
            with self.subTest(value=value):
                self.assertFalse(has_sufficient_description({"description": value}))

    def test_markup_without_words_is_not_a_description(self) -> None:
        self.assertEqual(product_description_text({"description": "<div><br/><p></p></div>"}), "")
        self.assertFalse(has_sufficient_description({"description": "<br/>" * 60}))

    def test_tags_are_stripped_before_the_length_is_measured(self) -> None:
        # The words a reader sees decide, not the bytes the merchant sent.
        wrapped = f"<div class='x'><p>{_LONG_ENOUGH}</p></div>"
        self.assertEqual(product_description_text({"description": wrapped}), _LONG_ENOUGH)
        self.assertTrue(has_sufficient_description({"description": wrapped}))

    def test_a_description_that_only_repeats_the_title_is_not_one(self) -> None:
        title = (
            "Fixturon Aero Kettle 1.7L Stainless Steel Rapid Boil Cordless Jug Kettle "
            "Black with Washable Filter and Blue Illuminated Water Window"
        )
        self.assertGreaterEqual(len(title), DESCRIPTION_MIN_CHARS)
        self.assertEqual(product_description_text({"description": title}, title=title), "")
        self.assertFalse(has_sufficient_description({"description": title}, title=title))

    def test_a_short_sentence_is_not_enough(self) -> None:
        self.assertFalse(has_sufficient_description({"description": "A good kettle."}))

    def test_the_longest_description_column_is_the_one_read(self) -> None:
        # A feed may leave `description` empty and write the real text elsewhere.
        row = {"description": "Kettle.", "product_short_description": _LONG_ENOUGH}
        self.assertEqual(product_description_text(row), _LONG_ENOUGH)
        self.assertTrue(has_sufficient_description(row))

    def test_a_greek_description_counts_by_its_characters(self) -> None:
        greek = fixture_description(greek=True)
        self.assertTrue(has_sufficient_description({"description": greek}))

    def test_entities_do_not_inflate_the_length(self) -> None:
        # "&nbsp;" is six bytes of markup and one space to a reader.
        padded = "Kettle." + "&nbsp;" * 40
        self.assertFalse(has_sufficient_description({"description": padded}))


class CardGateTests(unittest.TestCase):
    def test_a_product_without_a_description_is_not_card_eligible(self) -> None:
        result = _card_result(_product("k1", description=""))
        self.assertFalse(result.card_eligible)
        self.assertIn("missing_product_description", result.reason_codes)

    def test_a_product_with_one_is_card_eligible(self) -> None:
        result = _card_result(_product("k2", description=_LONG_ENOUGH))
        self.assertTrue(result.card_eligible, result.reason_codes)
        self.assertNotIn("missing_product_description", result.reason_codes)

    def test_the_gate_and_the_rule_never_disagree(self) -> None:
        # One source of truth: whatever `has_sufficient_description` says about a row
        # is what the card gate does with it. A second copy of the rule would let the
        # feed audit report one thing and the site do another.
        for description in ("", "Kettle.", "<br/>", _LONG_ENOUGH, fixture_description(greek=True)):
            with self.subTest(description=description[:20]):
                product = _product("k3", description=description)
                expected = has_sufficient_description(product.raw, title=product.title)
                blocked = "missing_product_description" in _card_result(product).reason_codes
                self.assertEqual(expected, not blocked)


class DeployedSearchTests(unittest.TestCase):
    """End to end through api/index.py, the entrypoint Vercel serves."""

    def _serve(self, rows: list[dict[str, str]]) -> None:
        directory = tempfile.mkdtemp()
        path = Path(directory) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if previous is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = previous
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def _cards(self, query: str) -> tuple[list[str], str]:
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": urlencode({"q": query}),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        ).decode("utf-8")
        self.assertEqual(captured["status"], "200 OK")
        shown = re.findall(r'<article class="pw-card[^"]*" data-choice-id="([^"]+)">', body)
        return shown, " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())

    def test_undescribed_products_never_take_a_slot(self) -> None:
        # Six kettles, the last two undescribed: the four shown are all from the four
        # that are described, so no undescribed row can reach a card.
        self._serve(_kettles(6, described=4))
        shown, _body = self._cards("kettle")
        self.assertEqual(len(shown), 4)
        self.assertEqual(set(shown), {"k0", "k1", "k2", "k3"})

    def test_a_kind_with_fewer_than_four_described_products_shows_no_four(self) -> None:
        # Six kettles but only three described. PicWise has no four and says so
        # rather than filling the page with products it may not show.
        self._serve(_kettles(6, described=3))
        shown, _body = self._cards("kettle")
        self.assertEqual(shown, [])

    def test_a_fully_described_feed_is_unaffected(self) -> None:
        self._serve(_kettles(6))
        shown, _body = self._cards("kettle")
        self.assertEqual(len(shown), 4)


if __name__ == "__main__":
    unittest.main()
