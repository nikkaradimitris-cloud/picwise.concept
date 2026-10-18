"""Step 5 of the price-first plan: a search reads the feed as judged once per load.

On the third feed (2026-10-16) every search judged all 40,000 products again -- can a
card show it, is it new -- which was about 4 of the 5 seconds a search took, and each
mega category kept a judged copy of its own. Pinned here:

- the feed is judged once per load, and every search after it reads that judgement;
- every mega category reads the same judged feed;
- a search reads the same products as when it judged the feed itself;
- a checked shop page (the purchasability cache) still counts from the next search.

Every row is written with fictional brands and `.invalid` URLs; the page tests are
served through api/index.py, the deployed entry point.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import search_selection, state  # noqa: E402
from picwise_providers.contracts import ProviderProduct, PurchasabilityVerification  # noqa: E402
from picwise_providers.purchasability_cache import (  # noqa: E402
    CACHE_ENV_VAR,
    clear_purchasability_cache_configuration,
    configure_purchasability_cache,
)
from picwise_providers.search_selection import (  # noqa: E402
    build_search_catalogue,
    select_provider_products_for_query,
)
from fixture_support import fixture_description  # noqa: E402
from test_picwise_price_first import _PageMixin, _ean  # noqa: E402


def _product(pid: str, price: float, *, title: str = "", image: bool = True) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title or f"Fixturon Electric Kettle {pid}",
        brand="Fixturon",
        category_text="Kettles",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg" if image else "",
        price_text=f"{price:.2f}",
        availability_text="in stock",
        currency="GBP",
        raw={
            "product_type": "Kettles",
            "description": fixture_description(),
            "brand_name": "Fixturon",
            "merchant_name": "Fixture Store One",
            "ean": _ean(500000004000 + int(price)),
        },
    )


def _laptops(count: int) -> list[dict[str, str]]:
    return [
        {
            "pid": f"l{index + 1}",
            "title": f"Fixturon Notebook Laptop {index + 1} 15 inch",
            "price": f"{300 + 25 * index:.2f}",
            "type": "Laptops",
            "category": "Computers > Laptops",
            "ean": _ean(500000002000 + index),
        }
        for index in range(count)
    ]


class OneJudgementPerFeedLoadTests(_PageMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.rows = self._kettles([20.0 + 5 * step for step in range(30)]) + _laptops(10)
        self._serve(self.rows)

    def test_the_feed_is_judged_once_for_many_searches(self) -> None:
        counted = Mock(wraps=search_selection.evaluate_product_eligibility)
        # Both modules judge with the one function, each under its own name.
        with patch.object(state, "evaluate_product_eligibility", counted), patch.object(
            search_selection, "evaluate_product_eligibility", counted
        ):
            first = self._page("kettle")
            first_calls = counted.call_count
            counted.reset_mock()
            again = self._page("kettle")
            other = self._page("laptop")
            later_calls = counted.call_count
        self.assertEqual(self._counter(first), "4 of 30")
        self.assertEqual(self._cards(again), self._cards(first))
        self.assertEqual(self._counter(other), "4 of 10")
        # The first search judges each of the 40 rows once, as the feed loads, and
        # then its cards; the next two searches judge only the cards they show.
        self.assertGreaterEqual(first_calls, len(self.rows))
        self.assertLess(first_calls, 2 * len(self.rows))
        self.assertLess(later_calls, len(self.rows))

    def test_every_mega_category_reads_one_judged_feed(self) -> None:
        resolve = state._resolve_provider_feed_pipeline_uncached
        with patch.object(state, "_resolve_provider_feed_pipeline_uncached", wraps=resolve) as built:
            for query in ("kettle", "laptop", "kettle", "laptop"):
                with self.subTest(query=query):
                    self.assertTrue(self._cards(self._page(query)))
        self.assertEqual(built.call_count, 1)


class SameProductsTests(unittest.TestCase):
    """Judged once or on every search, a search reads the same products."""

    def setUp(self) -> None:
        self.products = tuple(
            _product(f"k{index}", 20.0 + 5 * index) for index in range(1, 10)
        ) + (
            _product("r1", 12.0, title="Fixturon Electric Kettle r1 Refurbished"),
            _product("x1", 9.0, image=False),
        )

    def _ids(self, selection) -> list[str]:
        return [product.provider_product_id for product in selection.selected_products]

    def test_a_judged_catalogue_answers_like_the_products_themselves(self) -> None:
        catalogue = build_search_catalogue(self.products)
        expected = {
            "kettle": ["k5", "k1", "k2", "k3"],
            "refurbished kettle": ["r1"],
            "fixturon": ["k5", "k1", "k2", "k3"],
            "electric kettle k3": ["k3"],
        }
        for query, ids in expected.items():
            with self.subTest(query=query):
                judged_here = select_provider_products_for_query(query, self.products)
                judged_once = select_provider_products_for_query(
                    query, self.products, catalogue=catalogue
                )
                self.assertEqual(self._ids(judged_here), ids)
                self.assertEqual(self._ids(judged_once), ids)
                self.assertEqual(judged_once.total_count, judged_here.total_count)
                self.assertEqual(judged_once.status, judged_here.status)

    def test_the_catalogue_keeps_the_rules(self) -> None:
        catalogue = build_search_catalogue(self.products)
        ids = [product.provider_product_id for product in catalogue.products]
        new_ids = [product.provider_product_id for product in catalogue.new_products]
        # No image: no card. Refurbished: read only when the buyer asks for it.
        self.assertNotIn("x1", ids)
        self.assertIn("r1", ids)
        self.assertNotIn("r1", new_ids)
        self.assertEqual(new_ids, [f"k{index}" for index in range(1, 10)])
        self.assertEqual(len(catalogue.fields), len(catalogue.products))
        self.assertEqual(catalogue.new_fields[0]["title"], "fixturon electric kettle k1")


class CheckedShopPageTests(_PageMixin, unittest.TestCase):
    """A shop page checked between two searches counts from the next one."""

    def setUp(self) -> None:
        clear_purchasability_cache_configuration()
        previous = os.environ.pop(CACHE_ENV_VAR, None)

        def restore() -> None:
            clear_purchasability_cache_configuration()
            if previous is not None:
                os.environ[CACHE_ENV_VAR] = previous

        self.addCleanup(restore)
        self._serve(self._kettles([20, 30, 40, 50, 60]))

    def test_a_product_found_out_of_stock_leaves_the_next_search(self) -> None:
        cache = configure_purchasability_cache(str(Path(tempfile.mkdtemp()) / "checked.json"))
        self.assertIn("k1", [card["id"] for card in self._cards(self._page("kettle"))])
        cache.set(
            "https://fixture.example.invalid/out/k1",
            PurchasabilityVerification(
                purchasability_state="out_of_stock",
                buy_button_seen=False,
                out_of_stock_seen=True,
                final_url="https://fixture.example.invalid/out/k1",
                http_status=200,
                last_checked_at="2026-10-17T12:00:00+00:00",
                verification_source="page_verifier",
                verification_confidence="verified",
            ),
        )
        page = self._page("kettle")
        self.assertNotIn("k1", [card["id"] for card in self._cards(page)])
        self.assertEqual(self._counter(page), "4 of 4")


if __name__ == "__main__":
    unittest.main()
