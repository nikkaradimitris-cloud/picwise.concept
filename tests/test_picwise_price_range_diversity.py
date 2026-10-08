"""Which four are shown when more than four products are substantially equivalent.

Owner decision, 2026-10-08: when the ranking leaves more than four substantially
equivalent products, the four shown are the cheapest, the dearest and two in between,
without bypassing any hard filter. Before it, the alphabetical order of the titles
decided (audit finding D4 in docs/picwise_mission_truth_audit_2026-10-08.md).

"Substantially equivalent" means the same match with the search in what identifies the
product (title, product type, category, brand, accessory or not); a word found only in
merchant free text (keywords, description) does not make a product a closer match.

All rows are local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
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
from picwise_providers.search_selection import _spread_across_price  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"
_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "product_type",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "stock_status",
    "merchant_name", "description", "keywords", "ean", "valid_to", "data_provenance",
)


def _offer(pid: str, price: str, currency: str = "GBP") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=f"Fixturon Kettle {pid}",
        brand="Fixturon",
        category_text="Kettles",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in stock",
        currency=currency,
        raw={"product_type": "Kettles"},
    )


def _ids(products: list[ProviderProduct]) -> list[str]:
    return [product.provider_product_id for product in products]


class SpreadAcrossPriceTests(unittest.TestCase):
    def setUp(self) -> None:
        # Rank order deliberately unrelated to price.
        self.group = [
            _offer("p749", "749.00"),
            _offer("p529", "529.00"),
            _offer("p1249", "1249.00"),
            _offer("p399", "399.00"),
            _offer("p899", "899.00"),
            _offer("p1099", "1099.00"),
        ]

    def test_four_slots_are_cheapest_dearest_and_two_between(self) -> None:
        self.assertEqual(
            _ids(_spread_across_price(self.group, 4)), ["p399", "p749", "p899", "p1249"]
        )

    def test_fewer_slots_keep_the_ends_of_the_range(self) -> None:
        self.assertEqual(_ids(_spread_across_price(self.group, 2)), ["p399", "p1249"])
        # Six products have two middle positions; a halfway position rounds up, the same
        # way for one slot as for three.
        self.assertEqual(_ids(_spread_across_price(self.group, 3)), ["p399", "p899", "p1249"])
        self.assertEqual(_ids(_spread_across_price(self.group, 1)), ["p899"])
        self.assertEqual(_ids(_spread_across_price(self.group[:5], 1)), ["p749"])

    def test_a_group_that_fits_is_shown_whole_cheapest_first(self) -> None:
        self.assertEqual(_ids(_spread_across_price(self.group[:3], 4)), ["p529", "p749", "p1249"])

    def test_no_range_without_comparable_prices(self) -> None:
        mixed = self.group[:4] + [_offer("eur", "100.00", "EUR")]
        self.assertEqual(_ids(_spread_across_price(mixed, 4)), _ids(mixed[:4]))
        unpriced = self.group[:4] + [_offer("none", "call for price")]
        self.assertEqual(_ids(_spread_across_price(unpriced, 4)), _ids(unpriced[:4]))


class _FeedCase(unittest.TestCase):
    def _serve_file(self, path: Path) -> None:
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

    def _serve_rows(self, rows: list[dict[str, str]]) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        self._serve_file(path)

    def _cards(self, query: str) -> tuple[list[str], str | None, str]:
        def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
            return None

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
        cards = re.findall(r'<article class="pw-card([^"]*)" data-choice-id="([^"]+)"', body)
        recommended = next((pid for classes, pid in cards if "recommended" in classes), None)
        return [pid for _classes, pid in cards], recommended, body


def _kettle(pid: str, name: str, price: str, **fields: str) -> dict[str, str]:
    row = {
        "aw_product_id": pid, "product_name": name, "brand_name": name.split()[0],
        "merchant_category": "Kettles", "product_type": "Kettles",
        "aw_deep_link": f"https://fixture.example.invalid/out/{pid}",
        "aw_image_url": f"https://fixture.example.invalid/img/{pid}.jpg",
        "search_price": price, "currency": "GBP", "in_stock": "1", "stock_status": "in stock",
        "merchant_name": "Fixture Store One", "description": "", "keywords": "",
        "ean": "", "valid_to": "", "data_provenance": "local_test_fixture",
    }
    row.update(fields)
    return row


class DeployedPriceRangeTests(_FeedCase):
    def test_six_equivalent_laptops_show_the_price_range_not_the_alphabet(self) -> None:
        self._serve_file(FIXTURE_CSV)
        shown, recommended, body = self._cards("laptop")
        # 399, 529, 749, 899, 1099, 1249 are equivalent: cheapest, two between, dearest.
        # Alphabetical order used to drop both Testline laptops (529, 899).
        self.assertEqual(shown, ["fx-laptop-4", "fx-laptop-1", "fx-laptop-5", "fx-laptop-3"])
        self.assertEqual(recommended, "fx-laptop-4")
        self.assertIn("Lowest price among the choices that match your search equally", body)

    def test_hard_filters_hold_before_the_range_is_taken(self) -> None:
        self._serve_rows(
            [
                _kettle("k05", "Fixturon Aero Kettle", "5.00", stock_status="out of stock"),
                _kettle("k10", "Testline Boil Kettle", "10.00"),
                _kettle("k20", "Sampleworks Steam Kettle", "20.00"),
                _kettle("k30", "Fixturon Mini Kettle", "30.00"),
                _kettle("k40", "Testline Glass Kettle", "40.00"),
                _kettle("k50", "Sampleworks Quiet Kettle", "50.00"),
                _kettle("k90", "Fixturon Grand Kettle", "90.00", valid_to="2020-01-01"),
            ]
        )
        shown, _recommended, _body = self._cards("kettle")
        # The out-of-stock cheapest and the expired dearest never widen the range.
        self.assertEqual(shown, ["k10", "k20", "k40", "k50"])

    def test_better_matches_come_first_and_the_rest_spread(self) -> None:
        self._serve_rows(
            [
                _kettle("w1", "Fixturon Aero Kettle 1.7L", "35.00"),
                _kettle("w2", "Testline Boil Kettle 1.7L", "25.00"),
                _kettle("n1", "Sampleworks Steam Kettle 1.5L", "10.00"),
                _kettle("n2", "Fixturon Mini Kettle 0.8L", "20.00"),
                _kettle("n3", "Testline Glass Kettle 1.2L", "30.00"),
                _kettle("n4", "Sampleworks Quiet Kettle 1.0L", "40.00"),
                _kettle("n5", "Fixturon Travel Kettle 0.5L", "50.00"),
            ]
        )
        shown, _recommended, body = self._cards("kettle 1.7l")
        # The two carrying 1.7L match more closely; the other two slots take the cheapest
        # and dearest of the rest.
        self.assertEqual(shown, ["w2", "w1", "n1", "n5"])
        self.assertIn("Only some of the four match", body)

    def test_merchant_free_text_does_not_buy_a_place(self) -> None:
        self._serve_rows(
            [
                _kettle("d15", "Fixturon Aero Kettle", "15.00", description="the best kettle"),
                _kettle("d10", "Testline Boil Kettle", "10.00"),
                _kettle("d20", "Sampleworks Steam Kettle", "20.00"),
                _kettle("d30", "Fixturon Mini Kettle", "30.00"),
                _kettle("d40", "Testline Glass Kettle", "40.00"),
                _kettle("d50", "Sampleworks Quiet Kettle", "50.00", keywords="kettle"),
            ]
        )
        shown, recommended, _body = self._cards("kettle")
        # d15 and d50 mention "kettle" only in description/keywords: still equivalent.
        self.assertEqual(shown, ["d10", "d20", "d30", "d50"])
        self.assertEqual(recommended, "d10")

    def test_offers_of_one_product_count_once_before_the_range(self) -> None:
        self._serve_rows(
            [
                _kettle("s1", "Fixturon Aero Kettle", "10.00", ean="5000000000048"),
                _kettle("s2", "Fixturon Aero Kettle 1.7L", "12.00", ean="5000000000048"),
                _kettle("o20", "Testline Boil Kettle", "20.00"),
                _kettle("o30", "Sampleworks Steam Kettle", "30.00"),
                _kettle("o40", "Fixturon Mini Kettle", "40.00"),
                _kettle("o50", "Testline Glass Kettle", "50.00"),
            ]
        )
        shown, _recommended, _body = self._cards("kettle")
        # Five distinct products (s1 and s2 are one, at its cheaper offer): positions
        # 0, 1, 3, 4 of the price-sorted five.
        self.assertEqual(shown, ["s1", "o20", "o40", "o50"])


if __name__ == "__main__":
    unittest.main()
