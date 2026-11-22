"""A product page read as text (`picwise_checks.page_reader`; the checks' rules, 4.5).

JSON-LD first (a Product, a ProductGroup's variants, in a @graph, an AggregateOffer),
then microdata, then the `product:` and `og:` tags; a page that gives none of them has no
product a machine reads; a category page's list of products is not its product. Prices
are read as written, never worked out; GTINs padded to 14 digits; Shopify's own JSON in
pence (`.js`) and in pounds (`products.json`).

Every page is local test data: fictional brands, `.invalid` hosts. Nothing is opened.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_checks.page_reader import (  # noqa: E402
    amount,
    availability_word,
    gtin14,
    read_page,
    read_shopify_product,
    stock_of,
    title_alike,
)


def _ld(data: object) -> str:
    return f'<html><head><script type="application/ld+json">{json.dumps(data)}</script></head><body></body></html>'


class ReaderTwoJsonLdTests(unittest.TestCase):
    def test_a_product_with_one_offer(self) -> None:
        page = read_page(_ld({
            "@context": "https://schema.org", "@type": "Product", "name": "Zentra Kettle 1.7L",
            "sku": "ZK-17", "gtin13": "5012345678900", "mpn": "ZK17W",
            "offers": {"@type": "Offer", "price": "24.99", "priceCurrency": "GBP",
                       "availability": "https://schema.org/InStock"},
        }))
        self.assertEqual(page.how, "json-ld")
        self.assertEqual(page.name, "Zentra Kettle 1.7L")
        self.assertEqual(len(page.offers), 1)
        offer = page.offers[0]
        self.assertEqual((offer.price, offer.currency, offer.availability), (24.99, "GBP", "instock"))
        self.assertEqual((offer.sku, offer.gtin, offer.mpn), ("ZK-17", "05012345678900", "ZK17W"))
        self.assertEqual(page.gtins, frozenset({"05012345678900"}))

    def test_a_product_group_gives_each_variant_its_offer_and_codes(self) -> None:
        page = read_page(_ld({
            "@type": "ProductGroup", "name": "Nordel Mattress",
            "hasVariant": [
                {"@type": "Product", "name": "Single", "sku": "NM-S", "gtin": "5000000000017",
                 "offers": {"@type": "Offer", "price": 54.99, "priceCurrency": "GBP",
                            "availability": "InStock"}},
                {"@type": "Product", "name": "Double", "sku": "NM-D", "gtin": "5000000000024",
                 "offers": {"@type": "Offer", "price": 84.99, "priceCurrency": "GBP",
                            "availability": "OutOfStock"}},
            ],
        }))
        self.assertEqual([offer.price for offer in page.offers], [54.99, 84.99])
        self.assertEqual([offer.sku for offer in page.offers], ["NM-S", "NM-D"])
        self.assertEqual(page.skus, frozenset({"NM-S", "NM-D"}))
        self.assertEqual([offer.availability for offer in page.offers], ["instock", "outofstock"])

    def test_a_product_in_a_graph_and_an_escaped_block(self) -> None:
        data = {"@graph": [{"@type": "BreadcrumbList"},
                           {"@type": ["Product"], "name": "Quill Drill",
                            "offers": [{"@type": "Offer", "price": "49.00", "priceCurrency": "GBP"}]}]}
        escaped = json.dumps(data).replace('"', "&quot;")
        page = read_page(f'<script type="application/ld+json">{escaped}</script>')
        self.assertEqual(page.name, "Quill Drill")
        self.assertEqual(page.offers[0].price, 49.0)

    def test_an_aggregate_offer_of_several_prices_is_no_one_price(self) -> None:
        page = read_page(_ld({"@type": "Product", "name": "Lumo Lamp", "offers": {
            "@type": "AggregateOffer", "lowPrice": "10.00", "highPrice": "30.00", "priceCurrency": "GBP",
            "availability": "InStock"}}))
        self.assertIsNone(page.offers[0].price)
        self.assertEqual(page.offers[0].availability, "instock")
        one = read_page(_ld({"@type": "Product", "name": "Lumo Lamp", "offers": {
            "@type": "AggregateOffer", "lowPrice": "12.00", "highPrice": "12.00", "priceCurrency": "GBP"}}))
        self.assertEqual(one.offers[0].price, 12.0)

    def test_a_price_in_its_specification(self) -> None:
        page = read_page(_ld({"@type": "Product", "name": "Vanta Fan", "offers": {
            "@type": "Offer", "priceSpecification": {"price": "19.50", "priceCurrency": "GBP"}}}))
        self.assertEqual((page.offers[0].price, page.offers[0].currency), (19.5, "GBP"))

    def test_a_category_page_lists_products_but_has_none_of_its_own(self) -> None:
        page = read_page(_ld({"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "item": {"@type": "Product", "name": "One", "offers": {"price": "1"}}}]}))
        self.assertFalse(page.found)

    def test_only_the_first_product_of_a_page_counts(self) -> None:
        text = _ld({"@type": "Product", "name": "First", "offers": {"price": "5.00"}}) + _ld(
            {"@type": "Product", "name": "Related", "offers": {"price": "99.00"}})
        page = read_page(text)
        self.assertEqual((page.name, [offer.price for offer in page.offers]), ("First", [5.0]))


class ReaderTwoMicrodataAndTagsTests(unittest.TestCase):
    def test_microdata(self) -> None:
        page = read_page(
            '<div itemscope itemtype="https://schema.org/Product"><h1 itemprop="name">Orla Toaster</h1>'
            '<span itemprop="sku">OT-2</span><meta itemprop="gtin13" content="5012345678900">'
            '<div itemprop="offers" itemscope itemtype="https://schema.org/Offer">'
            '<span itemprop="price" content="29.95">£29.95</span><meta itemprop="priceCurrency" content="GBP">'
            '<link itemprop="availability" href="https://schema.org/OutOfStock"></div></div>'
        )
        self.assertEqual(page.how, "microdata")
        self.assertEqual(page.name, "Orla Toaster")
        offer = page.offers[0]
        self.assertEqual((offer.price, offer.currency, offer.availability, offer.sku), (29.95, "GBP", "outofstock", "OT-2"))
        self.assertEqual(offer.gtin, "05012345678900")

    def test_product_tags_when_nothing_else(self) -> None:
        page = read_page(
            '<link rel="canonical" href="https://shop.invalid/p/kettle">'
            '<meta property="og:title" content="Zentra Kettle"><meta property="product:price:amount" content="1,299.00">'
            '<meta property="product:price:currency" content="GBP"><meta property="product:availability" content="in stock">'
        )
        self.assertEqual(page.how, "tags")
        self.assertEqual((page.offers[0].price, page.offers[0].availability), (1299.0, "instock"))
        self.assertEqual(page.canonical, "https://shop.invalid/p/kettle")

    def test_a_page_with_nothing_has_no_product(self) -> None:
        page = read_page("<html><body><button>Add to basket</button> £12.99</body></html>")
        self.assertFalse(page.found)
        self.assertEqual(page.offers, ())


class MagentoPriceBoxTests(unittest.TestCase):
    def test_magentos_own_price_box_of_one_product(self) -> None:
        box = {"[data-role=priceBox][data-price-box=product-id-42]": {"priceBox": {"priceConfig": {
            "productId": "42", "prices": {"oldPrice": {"amount": 149.99}, "finalPrice": {"amount": 129.99}}}}}}
        page = read_page('<html><div class="stock available"><span>In stock</span></div>'
                         f'<script type="text/x-magento-init">{json.dumps(box)}</script></html>')
        self.assertEqual(page.how, "magento")
        self.assertEqual((page.offers[0].price, page.offers[0].availability), (129.99, ""))

    def test_a_page_listing_several_products_has_none(self) -> None:
        boxes = [{"a": {"priceBox": {"priceConfig": {"productId": str(n), "prices": {"finalPrice": {"amount": n}}}}}}
                 for n in (1, 2)]
        text = "".join(f'<script type="text/x-magento-init">{json.dumps(box)}</script>' for box in boxes)
        self.assertFalse(read_page(text).found)


class ReaderOneShopifyTests(unittest.TestCase):
    def test_the_product_js_in_pence(self) -> None:
        page = read_shopify_product({"title": "Fila Runner", "variants": [
            {"id": 111, "sku": "FR-8", "barcode": "5012345678900", "price": 4999, "available": True},
            {"id": 112, "sku": "FR-9", "barcode": "", "price": 4999, "available": False},
        ]}, pence=True)
        self.assertEqual(page.how, "shopify")
        self.assertEqual([(o.variant, o.price, o.availability) for o in page.offers],
                         [("111", 49.99, "instock"), ("112", 49.99, "outofstock")])
        self.assertEqual(page.gtins, frozenset({"05012345678900"}))

    def test_the_products_json_in_pounds(self) -> None:
        page = read_shopify_product({"title": "Fila Runner", "variants": [{"id": 7, "price": "49.99", "available": True}]},
                                    pence=False)
        self.assertEqual(page.offers[0].price, 49.99)


class WordsAndNumbersTests(unittest.TestCase):
    def test_amounts_as_written(self) -> None:
        for text, expected in (("£12.99", 12.99), ("1,299.00", 1299.0), ("1.299,00", 1299.0), ("12,99", 12.99),
                               (7, 7.0), ("free", None), ("", None), (None, None), (True, None)):
            with self.subTest(text=text):
                self.assertEqual(amount(text), expected)

    def test_gtins_padded_to_fourteen_digits(self) -> None:
        self.assertEqual(gtin14("012345678905"), "00012345678905")
        self.assertEqual(gtin14("5012345678900"), "05012345678900")
        self.assertEqual(gtin14("123"), "")
        self.assertEqual(gtin14("0000000000000"), "")

    def test_rules_5_2_preorder_and_backorder_are_not_in_stock(self) -> None:
        self.assertEqual(stock_of(availability_word("https://schema.org/InStock")), "in stock")
        self.assertEqual(stock_of(availability_word("http://schema.org/LimitedAvailability")), "in stock")
        for word in ("PreOrder", "BackOrder", "OutOfStock", "SoldOut", "Discontinued", "InStoreOnly", "out of stock"):
            with self.subTest(word=word):
                self.assertEqual(stock_of(availability_word(word)), "sold out")
        self.assertEqual(stock_of(availability_word("")), "")

    def test_rules_5_1_a_title_is_alike_at_sixty_per_cent(self) -> None:
        self.assertTrue(title_alike("Starlight Beds Memory Foam Mattress", "Starlight Beds Memory Foam Mattress - 2ft6"))
        self.assertFalse(title_alike("Zentra Kettle 1.7L White", "Garden Hose 30m"))


if __name__ == "__main__":
    unittest.main()
