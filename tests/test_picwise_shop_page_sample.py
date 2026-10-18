"""Whether listed products can really be bought, checked on a sample of shop pages.

`src/picwise_providers/shop_page_sample.py`. Owner, 2026-10-18: most products shown are
out of stock on the shop's own page, and the feed cannot tell. Pinned here: how a page
is read (structured data first, then the HTTP answer, then the page's words), that the
Awin tracked link is never opened, that robots.txt is obeyed, how the sample is drawn,
and the counts the build's note carries.

Every page here is written in the test: fictional shops, `.invalid` URLs, no network.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.shop_page_sample import (  # noqa: E402
    check_shop_pages,
    choose_sample,
    classify_page,
    direct_shop_url,
    page_availability,
)

_SHOP = "https://shop-one.example.invalid"


def _ld(availability: str) -> str:
    return (
        '<html><head><script type="application/ld+json">'
        '{"@context": "https://schema.org", "@type": "Product", "name": "Fixturon Kettle",'
        f' "offers": {{"@type": "Offer", "price": "20.00", "availability": "{availability}"}}}}'
        "</script></head><body>Fixturon Kettle</body></html>"
    )


def _product(pid: str, shop: str, price: str, **raw: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=f"Fixturon Kettle {pid}",
        brand="Fixturon",
        category_text="Kettles",
        product_url=f"https://www.awin1.com/cread.php?p={pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in stock",
        currency="GBP",
        raw={
            "merchant_name": shop,
            "aw_deep_link": f"https://www.awin1.com/cread.php?p={pid}",
            "merchant_deep_link": f"{_SHOP}/products/{pid}",
            **raw,
        },
    )


class PageReadingTests(unittest.TestCase):
    def test_structured_data_decides(self) -> None:
        for availability, expected in (
            ("https://schema.org/InStock", "in_stock"),
            ("http://schema.org/OutOfStock", "out_of_stock"),
            ("SoldOut", "out_of_stock"),
            ("https://schema.org/Discontinued", "out_of_stock"),
            ("https://schema.org/PreOrder", "preorder"),
        ):
            with self.subTest(availability=availability):
                self.assertEqual(page_availability(_ld(availability)), expected)

    def test_a_page_with_a_variant_in_stock_is_in_stock(self) -> None:
        page = (
            '<script type="application/ld+json">{"@graph": [{"@type": "Product", "offers": ['
            '{"availability": "https://schema.org/OutOfStock"}, {"availability": "https://schema.org/InStock"}'
            "]}]}</script>"
        )
        self.assertEqual(page_availability(page), "in_stock")

    def test_microdata_and_meta_tags(self) -> None:
        self.assertEqual(
            page_availability('<link itemprop="availability" href="https://schema.org/OutOfStock">'),
            "out_of_stock",
        )
        self.assertEqual(
            page_availability('<meta property="product:availability" content="in stock">'), "in_stock"
        )
        self.assertEqual(page_availability("<p>A kettle.</p>"), "")
        self.assertEqual(page_availability('<script type="application/ld+json">{broken</script>'), "")

    def test_the_http_answer_and_the_words(self) -> None:
        url = f"{_SHOP}/products/k1"
        cases = {
            "gone": ("", 404, url),
            "gone too": ("", 410, url),
            "blocked": ("", 403, url),
            "rate limited": ("", 429, url),
            "challenged": ("<title>Just a moment...</title>", 503, url),
            "server error": ("", 500, url),
            "sent home": (_ld("InStock"), 200, f"{_SHOP}/"),
            "sent to a category": ("<p>Kettles</p>", 200, f"{_SHOP}/category/kettles"),
            "structured": (_ld("OutOfStock"), 200, url),
            "words: buy": ("<p>Fixturon Kettle</p><button>Add to basket</button>", 200, url),
            "words: sold out": ("<p>Fixturon Kettle</p><p>Sold out</p>", 200, url),
            "nothing to read": ("<p>Fixturon Kettle</p>", 200, url),
        }
        expected = {
            "gone": "gone", "gone too": "gone", "blocked": "blocked", "rate limited": "blocked",
            "challenged": "blocked", "server error": "unreachable", "sent home": "redirected",
            "sent to a category": "redirected", "structured": "out_of_stock", "words: buy": "text_buyable",
            "words: sold out": "text_out_of_stock", "nothing to read": "unclear",
        }
        for name, (body, status, final_url) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(classify_page(url, body, status, final_url), expected[name])


class LinkTests(unittest.TestCase):
    def test_only_the_shops_own_link_is_opened(self) -> None:
        self.assertEqual(direct_shop_url(_product("k1", "One", "20.00")), f"{_SHOP}/products/k1")
        tracked = _product("k2", "One", "20.00", merchant_deep_link="https://www.awin1.com/cread.php?p=k2")
        self.assertEqual(direct_shop_url(tracked), "")
        self.assertEqual(direct_shop_url(_product("k3", "One", "20.00", merchant_deep_link="")), "")


class SampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [_product(f"a{index}", "Shop A", f"{10 + index}.00") for index in range(10)]
        self.products += [_product(f"b{index}", "Shop B", f"{5 + index}.00") for index in range(3)]

    def test_half_the_cheapest_the_rest_at_random(self) -> None:
        sample = choose_sample(self.products, per_shop=4, seed="2026-10-18")
        cheapest, drawn = sample["Shop A"]
        self.assertEqual([item.provider_product_id for item in cheapest], ["a0", "a1"])
        self.assertEqual(len(drawn), 2)
        self.assertFalse({item.provider_product_id for item in drawn} & {"a0", "a1"})
        again = choose_sample(self.products, per_shop=4, seed="2026-10-18")
        self.assertEqual(again["Shop A"][1], drawn)
        small_cheapest, small_drawn = sample["Shop B"]
        self.assertEqual(len(small_cheapest) + len(small_drawn), 3)


class CheckTests(unittest.TestCase):
    def test_the_counts_and_what_is_never_opened(self) -> None:
        products = [
            _product("k1", "Shop A", "1.00"),
            _product("k2", "Shop A", "2.00"),
            _product("k3", "Shop A", "30.00"),
            _product("k4", "Shop A", "40.00"),
            _product("k5", "Shop A", "50.00", merchant_deep_link=""),
            _product("p1", "Shop A", "60.00", merchant_deep_link=f"{_SHOP}/private/p1"),
        ]
        pages = {
            f"{_SHOP}/robots.txt": ("User-agent: *\nDisallow: /private", 200, f"{_SHOP}/robots.txt"),
            f"{_SHOP}/products/k1": (_ld("https://schema.org/OutOfStock"), 200, f"{_SHOP}/products/k1"),
            f"{_SHOP}/products/k2": ("", 404, f"{_SHOP}/products/k2"),
            f"{_SHOP}/products/k3": (_ld("https://schema.org/InStock"), 200, f"{_SHOP}/products/k3"),
            f"{_SHOP}/products/k4": ("<p>Fixturon</p><button>Add to cart</button>", 200, f"{_SHOP}/products/k4"),
        }
        opened: list[str] = []

        def fetch(url: str):
            opened.append(url)
            self.assertNotIn("awin", url)
            return pages[url]

        result = check_shop_pages(products, per_shop=6, seed="2026-10-18", fetch=fetch, delay=0)
        self.assertNotIn(f"{_SHOP}/private/p1", opened)
        self.assertEqual(result["checked"], 6)
        shop = result["shops"][0]
        self.assertEqual(shop["shop"], "Shop A")
        self.assertEqual(
            {key: value for key, value in shop.items() if key not in ("shop", "checked", "of_its_cheapest")},
            {"in_stock": 1, "out_of_stock": 1, "gone": 1, "text_buyable": 1, "no_direct_link": 1,
             "robots_disallowed": 1},
        )
        # The three cheapest: 1.00 (out of stock), 2.00 (gone) and 30.00 (in stock).
        self.assertEqual(shop["of_its_cheapest"], {"in_stock": 1, "out_of_stock": 1, "gone": 1})
        self.assertEqual(result["totals"]["out_of_stock"], 1)

    def test_a_network_failure_is_counted_not_raised(self) -> None:
        def fetch(url: str):
            if url.endswith("robots.txt"):
                return "", 404, url
            raise OSError("no route")

        result = check_shop_pages([_product("k1", "Shop A", "1.00")], per_shop=2, seed="d", fetch=fetch, delay=0)
        self.assertEqual(result["totals"], {"unreachable": 1})

    def test_the_time_budget_stops_the_checks(self) -> None:
        result = check_shop_pages(
            [_product("k1", "Shop A", "1.00")], per_shop=2, seed="d",
            fetch=lambda url: ("", 404, url), delay=0, time_budget_seconds=0,
        )
        self.assertEqual(result["checked"], 0)


if __name__ == "__main__":
    unittest.main()
