"""The four choices are always priced in one currency.

Owner decision, 2026-10-11, taken on the first real feed, whose 11,573 products are
priced in GBP, USD and EUR, mixed inside the same kind of product (headphones: 151
USD, 124 GBP, 9 EUR). Prices in different currencies are never compared, so a four
drawn from several of them has no price rank, no price spread and no honest
"cheapest" -- the buyer is left converting in their head, which is the opposite of a
decision engine.

The currency kept is the best-ranked one that can supply the whole four. When none
can, PicWise shows no four rather than mixing them.

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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "product_type",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "stock_status",
    "merchant_name", "condition", "description", "data_provenance",
)


def _row(pid: str, name: str, price: str, currency: str) -> dict[str, str]:
    return {
        "aw_product_id": pid,
        "product_name": name,
        "brand_name": name.split()[0],
        "merchant_category": "Kettles",
        "product_type": "Kettles",
        "aw_deep_link": f"https://fixture.example.invalid/out/{pid}",
        "aw_image_url": f"https://fixture.example.invalid/img/{pid}.jpg",
        "search_price": price,
        "currency": currency,
        "in_stock": "1",
        "stock_status": "in stock",
        "merchant_name": "Fixture Store One",
        "condition": "new",
        "description": fixture_description(),
        "data_provenance": "local_test_fixture",
    }


def _kettles(prefix: str, count: int, currency: str, first_price: int) -> list[dict[str, str]]:
    names = ("Boil", "Steam", "Mini", "Glass", "Quiet", "Travel")
    return [
        _row(
            f"{prefix}{index}",
            f"Testline {names[index % len(names)]} Kettle 1.{index}L",
            f"{first_price + 5 * index}.00",
            currency,
        )
        for index in range(count)
    ]


class SingleCurrencyFourTests(unittest.TestCase):
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

    def _cards(self, query: str) -> list[dict[str, str]]:
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
        cards = []
        for match in re.finditer(
            r'<article class="pw-card([^"]*)" data-choice-id="([^"]+)">(.*?)</article>', body, re.S
        ):
            _classes, choice_id, inner = match.groups()
            text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", inner)).split())
            cards.append({"choice_id": choice_id, "text": text})
        return cards

    def _currencies(self, query: str) -> set[str]:
        found = set()
        for card in self._cards(query):
            found |= {code for code in ("GBP", "USD", "EUR") if code in card["text"]}
        return found

    def test_the_four_never_mix_currencies(self) -> None:
        self._serve(
            _kettles("g", 4, "GBP", 10) + _kettles("u", 4, "USD", 12) + _kettles("e", 4, "EUR", 14)
        )
        cards = self._cards("kettle")
        self.assertEqual(len(cards), 4)
        self.assertEqual(len(self._currencies("kettle")), 1)

    def test_a_currency_too_thin_for_four_gives_way_to_one_that_is_not(self) -> None:
        self._serve(_kettles("g", 3, "GBP", 10) + _kettles("u", 5, "USD", 12))
        shown = {card["choice_id"] for card in self._cards("kettle")}
        self.assertEqual(len(shown), 4)
        self.assertTrue(all(choice_id.startswith("u") for choice_id in shown), shown)
        self.assertEqual(self._currencies("kettle"), {"USD"})

    def test_no_currency_with_four_shows_no_four(self) -> None:
        # Three and three is not four: PicWise would have to compare prices it cannot
        # compare, so it answers nothing instead.
        self._serve(_kettles("g", 3, "GBP", 10) + _kettles("u", 3, "USD", 12))
        self.assertEqual(self._cards("kettle"), [])

    def test_one_currency_in_the_feed_is_unaffected(self) -> None:
        self._serve(_kettles("g", 6, "GBP", 10))
        self.assertEqual(len(self._cards("kettle")), 4)
        self.assertEqual(self._currencies("kettle"), {"GBP"})


if __name__ == "__main__":
    unittest.main()
