"""PRODUCT is not OFFER: one product sold by several merchants is one choice.

Pins audit finding D3 in docs/picwise_mission_truth_audit_2026-10-08.md: the same phone
(one EAN, one MPN) from four merchants, titles worded slightly differently, rendered as
four cards ranked "lowest" to "highest price", while different phones were pushed out.

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
from picwise_providers.search_selection import (  # noqa: E402
    _dedupe_selected_products,
    _product_identity_key,
    resolve_query_token_plan,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "product_type",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
    "ean", "mpn", "data_provenance",
)


def _offer(pid: str, title: str, price: str, **raw: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand=title.split()[0],
        category_text="Mobile Phones",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in stock",
        currency=raw.pop("currency", "GBP"),
        raw={"product_type": "Mobile Phones", **raw},
    )


class ProductIdentityTests(unittest.TestCase):
    def test_gtin_forms_of_one_code_agree(self) -> None:
        upc = _offer("a", "Fixturon Nova 12", "1", upc="012345678905")
        ean = _offer("b", "Fixturon Nova 12", "1", ean="0012345678905")
        self.assertEqual(_product_identity_key(upc), _product_identity_key(ean))
        self.assertTrue(_product_identity_key(upc).startswith("gtin:"))

    def test_header_case_does_not_matter(self) -> None:
        self.assertTrue(_product_identity_key(_offer("a", "Fixturon Nova", "1", product_GTIN="5000000000017")))
        self.assertTrue(_product_identity_key(_offer("b", "Fixturon Nova", "1", EAN="5000000000017")))

    def test_brand_and_part_number_identify_without_a_gtin(self) -> None:
        one = _offer("a", "Fixturon Nova 12 Black", "1", mpn="FXN12-BK")
        two = _offer("b", "FIXTURON Nova 12 (Black)", "1", mpn="fxn12-bk")
        self.assertEqual(_product_identity_key(one), _product_identity_key(two))

    def test_no_identity_without_a_code(self) -> None:
        self.assertEqual(_product_identity_key(_offer("a", "Fixturon Nova", "1")), "")
        self.assertEqual(_product_identity_key(_offer("b", "Fixturon Nova", "1", ean="0000000000000")), "")

    def test_one_product_keeps_its_cheapest_offer_whatever_the_rank_order(self) -> None:
        pricey = _offer("z-first", "Fixturon Aero Kettle 1.7L", "45.00", ean="5000000000048")
        cheap = _offer("a-later", "Fixturon Aero Kettle 1.7L", "29.00", ean="5000000000048")
        other = _offer("o", "Testline Boil Kettle", "25.00", ean="5000000000055")
        ranked = [((0,), pricey), ((0,), other), ((0,), cheap)]
        kept = _dedupe_selected_products(ranked)
        self.assertEqual([product.provider_product_id for product in kept], ["a-later", "o"])

    def test_offers_in_another_currency_never_replace_on_price(self) -> None:
        gbp = _offer("g", "Fixturon Nova 12", "500.00", ean="5000000000017")
        eur = _offer("e", "Fixturon Nova 12", "400.00", ean="5000000000017", currency="EUR")
        kept = _dedupe_selected_products([((0,), gbp), ((0,), eur)])
        self.assertEqual([product.provider_product_id for product in kept], ["g"])

    def test_relaxation_counts_products_not_offers(self) -> None:
        offers = tuple(
            _offer(f"s{index}", f"Fixturon Nova 12 20000mah Store {index}", "1", ean="5000000000017")
            for index in range(4)
        ) + tuple(
            _offer(f"d{index}", f"Testline Model {index} Phone", "1", ean=f"500000000010{index}")
            for index in range(4)
        )
        plan = resolve_query_token_plan(("phone", "20000mah"), offers, max_products=4)
        # Four offers of one product cannot fill four choices with "20000mah".
        self.assertIn("20000mah", plan.unmatchable)


class DeployedSurfaceIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        rows = [
            ("ph-a", "Fixturon Nova 12 Smartphone 128GB Black", "499.00", "Fixture Store One", "5000000000017"),
            ("ph-b", "Fixturon Nova 12 128GB Smartphone - Black", "479.00", "Fixture Store Two", "5000000000017"),
            ("ph-c", "Fixturon Nova 12 Smartphone (128GB, Black)", "489.00", "Fixture Store Three", "5000000000017"),
            ("ph-d", "FIXTURON Nova 12 Smartphone 128 GB Black", "509.00", "Fixture Store Four", "5000000000017"),
            ("ph-e", "Testline Orbit 5 Smartphone 256GB", "599.00", "Fixture Store One", "5000000000024"),
            ("ph-f", "Sampleworks Edge Smartphone 64GB", "199.00", "Fixture Store Two", "5000000000031"),
            ("ph-g", "Testline Wave 3 Smartphone 128GB", "349.00", "Fixture Store Three", "5000000000062"),
        ]
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
            writer.writeheader()
            for pid, title, price, merchant, ean in rows:
                writer.writerow(
                    {
                        "aw_product_id": pid, "product_name": title, "brand_name": title.split()[0].title(),
                        "merchant_category": "Mobile Phones", "product_type": "Mobile Phones",
                        "aw_deep_link": f"https://fixture.example.invalid/out/{pid}",
                        "aw_image_url": f"https://fixture.example.invalid/img/{pid}.jpg",
                        "search_price": price, "currency": "GBP", "in_stock": "1",
                        "merchant_name": merchant, "ean": ean, "mpn": "", "data_provenance": "local_test_fixture",
                    }
                )
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

    def test_four_choices_are_four_different_products(self) -> None:
        def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
            return None

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": urlencode({"q": "smartphone"}),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        ).decode("utf-8")
        shown = re.findall(r'<article class="pw-card[^"]*" data-choice-id="([^"]+)"', body)
        self.assertEqual(len(shown), 4)
        nova_offers = {"ph-a", "ph-b", "ph-c", "ph-d"}
        self.assertEqual(len(nova_offers & set(shown)), 1)
        # The phone is offered by the merchant with its lowest price.
        self.assertIn("ph-b", shown)
        self.assertTrue({"ph-e", "ph-f", "ph-g"} <= set(shown))


if __name__ == "__main__":
    unittest.main()
