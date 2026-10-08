"""Stock and offer truth: an offer the feed says cannot be bought is never a choice.

Pins the audit findings D2, E1-E4 in docs/picwise_mission_truth_audit_2026-10-08.md:

- Awin rows carry both `in_stock` and `stock_status`. Only the first was read, so a
  merchant default of `in_stock=1` on every row hid `stock_status=out of stock`, and the
  out-of-stock product became the recommendation with a card saying "listed as available".
- schema.org values (`OutOfStock`) were not recognised and read as in stock.
- A feed whose every row said "out of stock" was treated as uninformative and shown.
- `is_for_sale=0` and an offer whose `valid_to` date has passed were shown.
- The card's large price carried no currency.

All rows are local test data: fictional brands, `.invalid` URLs.
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

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import (  # noqa: E402
    build_feed_availability_context,
    evaluate_product_eligibility,
    interpret_availability_state,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "product_type",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "stock_status",
    "merchant_name", "condition", "is_for_sale", "pre_order", "valid_to", "data_provenance",
)


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
        "is_for_sale": "1",
        "pre_order": "0",
        "valid_to": "",
        "data_provenance": "local_test_fixture",
    }
    row.update(fields)
    return row


def _product(pid: str, **raw: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=f"Fixturon Kettle {pid}",
        brand="Fixturon",
        category_text="Kettles",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text="20.00",
        availability_text=str(raw.get("in_stock") or raw.get("stock_status") or ""),
        currency="GBP",
        raw={"product_type": "Kettles", **raw},
    )


class AvailabilityReadingTests(unittest.TestCase):
    def _state(self, target: ProviderProduct, *others: ProviderProduct) -> str:
        ctx = build_feed_availability_context((target, *others))
        return interpret_availability_state(target, feed_ctx=ctx)[0]

    def test_any_column_stating_out_of_stock_decides(self) -> None:
        # in_stock=1 on every row is a merchant default; stock_status carries the truth.
        target = _product("a", in_stock="1", stock_status="out of stock")
        other = _product("b", in_stock="1", stock_status="in stock")
        self.assertEqual(self._state(target, other), "out_of_stock")

    def test_schema_org_and_spelling_variants_are_read(self) -> None:
        other = _product("z", stock_status="in stock")
        for value, expected in (
            ("OutOfStock", "out_of_stock"),
            ("http://schema.org/OutOfStock", "out_of_stock"),
            ("SoldOut", "out_of_stock"),
            ("Out-Of-Stock", "out_of_stock"),
            ("Currently unavailable", "out_of_stock"),
            ("PreOrder", "out_of_stock"),
            ("backorder", "out_of_stock"),
            ("Discontinued", "discontinued"),
            ("InStock", "trusted"),
        ):
            with self.subTest(value=value):
                self.assertEqual(self._state(_product("a", stock_status=value), other), expected)

    def test_out_of_stock_in_words_counts_even_when_every_row_says_it(self) -> None:
        rows = [_product(str(index), stock_status="out of stock") for index in range(4)]
        self.assertEqual(self._state(*rows), "out_of_stock")

    def test_a_flag_identical_on_every_row_is_not_read_as_a_statement(self) -> None:
        rows = [_product(str(index), in_stock="0") for index in range(4)]
        state = self._state(*rows)
        self.assertEqual(state, "unknown")
        ctx = build_feed_availability_context(tuple(rows))
        self.assertTrue(evaluate_product_eligibility(rows[0], feed_ctx=ctx).card_eligible)

    def test_a_flag_that_varies_is_read(self) -> None:
        self.assertEqual(
            self._state(_product("a", in_stock="0"), _product("b", in_stock="1")),
            "out_of_stock",
        )

    def test_an_unreadable_value_is_never_taken_as_available(self) -> None:
        state = self._state(_product("a", stock_status="ships in 3 days"), _product("b", stock_status="in stock"))
        self.assertEqual(state, "unknown")


class OfferFlagTests(unittest.TestCase):
    def _eligibility(self, target: ProviderProduct, *others: ProviderProduct):
        ctx = build_feed_availability_context((target, *others))
        return evaluate_product_eligibility(target, feed_ctx=ctx)

    def test_not_for_sale_blocks_where_the_column_varies(self) -> None:
        result = self._eligibility(
            _product("a", in_stock="1", is_for_sale="0"),
            _product("b", in_stock="1", is_for_sale="1"),
        )
        self.assertFalse(result.card_eligible)
        self.assertIn("offer_not_for_sale", result.reason_codes)

    def test_pre_order_flag_blocks_where_the_column_varies(self) -> None:
        result = self._eligibility(
            _product("a", in_stock="1", pre_order="1"),
            _product("b", in_stock="1", pre_order="0"),
        )
        self.assertFalse(result.card_eligible)
        self.assertIn("availability_out_of_stock", result.reason_codes)

    def test_expired_and_not_yet_valid_offers_are_blocked(self) -> None:
        other = _product("b", in_stock="1")
        expired = self._eligibility(_product("a", in_stock="1", valid_to="2020-01-01"), other)
        self.assertIn("offer_expired", expired.reason_codes)
        future = self._eligibility(_product("a", in_stock="1", valid_from="2999-01-01"), other)
        self.assertIn("offer_not_yet_valid", future.reason_codes)
        unreadable = self._eligibility(_product("a", in_stock="1", valid_to="soon"), other)
        self.assertTrue(unreadable.card_eligible)


class DeployedSurfaceStockTruthTests(unittest.TestCase):
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

    def _get(self, path: str, query: dict[str, str]) -> tuple[str, dict[str, str], str]:
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": path,
                    "QUERY_STRING": urlencode(query),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        )
        return str(captured["status"]), dict(captured["headers"]), body.decode("utf-8")

    def _cards(self, query: str) -> list[dict[str, object]]:
        _status, _headers, body = self._get("/search", {"q": query})
        cards = []
        for match in re.finditer(
            r'<article class="pw-card([^"]*)" data-choice-id="([^"]+)">(.*?)</article>', body, re.S
        ):
            classes, choice_id, inner = match.groups()
            text = html.unescape(re.sub(r"<[^>]+>", " ", inner))
            price = re.search(r'<p class="pw-price">(.*?)</p>', inner, re.S)
            cards.append(
                {
                    "choice_id": choice_id,
                    "recommended": "recommended" in classes,
                    "text": " ".join(text.split()),
                    "price": html.unescape(price.group(1)) if price else "",
                }
            )
        return cards

    def test_out_of_stock_by_stock_status_is_never_a_choice_or_the_recommendation(self) -> None:
        self._serve(
            [
                _row("k1", "Fixturon Aero Kettle 1.7L", "9.00", stock_status="out of stock"),
                _row("k2", "Testline Boil Kettle 1.5L", "14.00"),
                _row("k3", "Sampleworks Steam Kettle 1.7L", "19.00"),
                _row("k4", "Fixturon Mini Kettle 0.8L", "24.00", stock_status="OutOfStock"),
                _row("k5", "Testline Glass Kettle 1.7L", "29.00"),
                _row("k6", "Sampleworks Quiet Kettle 1.5L", "34.00"),
            ]
        )
        cards = self._cards("kettle")
        self.assertEqual(len(cards), 4)
        shown = {card["choice_id"] for card in cards}
        self.assertNotIn("k1", shown)
        self.assertNotIn("k4", shown)
        self.assertEqual(sum(1 for card in cards if card["recommended"]), 1)
        for card in cards:
            self.assertIn("Listed as available by the provider feed", card["text"])
            self.assertTrue(str(card["price"]).endswith("GBP"), card["price"])
        status, _headers, _body = self._get("/out/feed", {"pid": "k1", "q": "kettle", "rec": "0"})
        self.assertEqual(status, "200 OK")  # the "no longer available" page, not a redirect

    def test_a_feed_that_says_out_of_stock_on_every_row_shows_nothing(self) -> None:
        self._serve(
            [
                _row(f"f{index}", f"Fixturon Breeze Kettle Model {index}", f"{20 + index}.00",
                     in_stock="0", stock_status="out of stock")
                for index in range(1, 6)
            ]
        )
        self.assertEqual(self._cards("kettle"), [])

    def test_offers_the_feed_says_cannot_be_bought_are_not_choices(self) -> None:
        self._serve(
            [
                _row("o1", "Fixturon Aero Kettle 1.7L", "19.00"),
                _row("o2", "Testline Boil Kettle 1.5L", "21.00", is_for_sale="0"),
                _row("o3", "Sampleworks Steam Kettle 1.7L", "23.00", valid_to="2020-01-01"),
                _row("o4", "Fixturon Mini Kettle 0.8L", "25.00", pre_order="1"),
                _row("o5", "Testline Glass Kettle 1.7L", "27.00"),
                _row("o6", "Sampleworks Quiet Kettle 1.5L", "29.00"),
                _row("o7", "Fixturon Travel Kettle 0.5L", "31.00"),
            ]
        )
        shown = {card["choice_id"] for card in self._cards("kettle")}
        self.assertEqual(shown, {"o1", "o5", "o6", "o7"})

    def test_a_refurbished_choice_says_so_on_its_card(self) -> None:
        self._serve(
            [
                _row("r1", "Fixturon Aero Kettle 1.7L", "9.00", condition="refurbished"),
                _row("r2", "Testline Boil Kettle 1.5L", "14.00"),
                _row("r3", "Sampleworks Steam Kettle 1.7L", "19.00"),
                _row("r4", "Fixturon Mini Kettle 0.8L", "24.00"),
            ]
        )
        cards = {card["choice_id"]: card for card in self._cards("kettle")}
        self.assertIn("condition: refurbished", cards["r1"]["text"])
        self.assertIn("not new", cards["r1"]["text"])
        self.assertNotIn("not new", cards["r2"]["text"])


if __name__ == "__main__":
    unittest.main()
