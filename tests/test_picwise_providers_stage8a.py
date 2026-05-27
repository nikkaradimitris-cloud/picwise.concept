from __future__ import annotations

import gzip
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_offers.amazon_manual_affiliate import (  # noqa: E402
    AmazonManualMatchStatus,
    match_manual_amazon_affiliates,
)
from picwise_providers.awin_adapter import (  # noqa: E402
    awin_feed_config_from_env,
    load_awin_provider_feed,
)
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.eligibility import evaluate_provider_product_eligibility  # noqa: E402
from picwise_providers.graph_projection import project_provider_products_to_graph  # noqa: E402
from picwise_providers.normalization import normalize_feed_row_to_provider_product  # noqa: E402
from picwise_providers.state import resolve_provider_feed_pipeline  # noqa: E402
from picwise_search_graph.export import export_graph_search_memory_terms  # noqa: E402
from picwise_search_graph.contracts import (  # noqa: E402
    SearchEntityGraphEnvelope,
    SearchEntityGraphEntities,
)


class ProviderFeedNotConfiguredTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_env = {
            "AWIN_FEED_FILE": os.environ.pop("AWIN_FEED_FILE", None),
            "AWIN_FEED_URL": os.environ.pop("AWIN_FEED_URL", None),
        }

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_no_feed_configured_returns_safe_state(self) -> None:
        config = ProviderFeedConfig(provider_key="awin")
        pipeline = resolve_provider_feed_pipeline(config)

        self.assertEqual(pipeline.feed_status.status, "provider_feed_not_configured")
        self.assertEqual(pipeline.parse_result.status, "provider_feed_not_configured")
        self.assertEqual(pipeline.feed_status.product_count, 0)
        self.assertEqual(pipeline.eligibility_results, tuple())
        self.assertIsNone(pipeline.graph_projection)
        self.assertIn("no_feed_file_or_url", pipeline.feed_status.reason_codes)

    def test_env_config_without_values_is_not_configured(self) -> None:
        config = awin_feed_config_from_env()
        result = load_awin_provider_feed(config)
        self.assertEqual(result.status, "provider_feed_not_configured")
        self.assertEqual(result.products, tuple())


class ProviderFeedParseTests(unittest.TestCase):
    def test_valid_csv_fixture_parses_and_normalizes(self) -> None:
        csv_text = (
            "product_id,product_name,brand,category_name,deeplink,image_url,current_price,in_stock,currency\n"
            "SKU-100,Portable Charger 10000mAh,AcmeBrand,Power Banks,"
            "https://merchant.example/products/sku-100,https://cdn.example/img.jpg,29.99,in stock,USD\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as handle:
            handle.write(csv_text)
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_loaded")
            self.assertEqual(len(result.products), 1)

            product = result.products[0]
            self.assertEqual(product.provider_key, "awin")
            self.assertEqual(product.provider_product_id, "SKU-100")
            self.assertEqual(product.title, "Portable Charger 10000mAh")
            self.assertEqual(product.brand, "AcmeBrand")
            self.assertEqual(product.category_text, "Power Banks")
            self.assertEqual(product.product_url, "https://merchant.example/products/sku-100")
            self.assertEqual(product.image_url, "https://cdn.example/img.jpg")
            self.assertEqual(product.price_text, "29.99")
            self.assertEqual(product.availability_text, "in stock")
            self.assertEqual(product.currency, "USD")
        finally:
            os.unlink(feed_path)

    def test_valid_json_fixture_parses_without_faking_missing_values(self) -> None:
        payload = [
            {
                "id": "J-200",
                "title": "USB-C Cable 2m",
                "url": "https://merchant.example/products/j-200",
            }
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(payload, handle)
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_loaded")
            product = result.products[0]
            self.assertEqual(product.brand, "")
            self.assertEqual(product.image_url, "")
            self.assertEqual(product.price_text, "")
            self.assertEqual(product.availability_text, "")
            self.assertEqual(product.currency, "")
        finally:
            os.unlink(feed_path)

    def test_invalid_feed_returns_parse_failed(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            handle.write("{not valid json")
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_parse_failed")
            self.assertIn("json_decode_failed", result.parse_errors)
        finally:
            os.unlink(feed_path)

    def test_missing_feed_file_returns_parse_failed(self) -> None:
        config = ProviderFeedConfig(
            provider_key="awin",
            feed_file=str(Path(tempfile.gettempdir()) / "picwise_missing_feed_stage8a.csv"),
        )
        result = load_awin_provider_feed(config)
        self.assertEqual(result.status, "provider_feed_parse_failed")
        self.assertTrue(any(code.startswith("feed_file_read_failed") for code in result.parse_errors))

    def test_gzip_csv_fixture_parses_successfully(self) -> None:
        csv_text = (
            "product_id,product_name,brand,category_name,deeplink,image_url,current_price,in_stock,currency\n"
            "SKU-GZ-100,Portable Charger 10000mAh,AcmeBrand,Power Banks,"
            "https://merchant.example/products/sku-gz-100,https://cdn.example/img.jpg,29.99,in stock,USD\n"
        )
        with tempfile.NamedTemporaryFile("wb", suffix=".csv.gz", delete=False) as handle:
            handle.write(gzip.compress(csv_text.encode("utf-8")))
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_loaded")
            self.assertEqual(len(result.products), 1)
            self.assertEqual(result.products[0].provider_product_id, "SKU-GZ-100")
        finally:
            os.unlink(feed_path)

    def test_invalid_gzip_returns_parse_failed(self) -> None:
        with tempfile.NamedTemporaryFile("wb", suffix=".csv.gz", delete=False) as handle:
            handle.write(b"\x1f\x8bnot-valid-gzip-payload")
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_parse_failed")
            self.assertTrue(any(code.startswith("gzip_decompress_failed") for code in result.parse_errors))
        finally:
            os.unlink(feed_path)

    def test_gzip_magic_bytes_without_gz_extension_parses(self) -> None:
        csv_text = "product_id,title,url\nG-1,Sample,https://merchant.example/g-1\n"
        with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as handle:
            handle.write(gzip.compress(csv_text.encode("utf-8")))
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_loaded")
            self.assertEqual(result.products[0].title, "Sample")
        finally:
            os.unlink(feed_path)

    def test_gzip_csv_with_missing_fields_does_not_fake_values(self) -> None:
        csv_text = "product_id,title,url\nG-2,USB Cable,https://merchant.example/g-2\n"
        with tempfile.NamedTemporaryFile("wb", suffix=".csv.gz", delete=False) as handle:
            handle.write(gzip.compress(csv_text.encode("utf-8")))
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_loaded")
            product = result.products[0]
            self.assertEqual(product.brand, "")
            self.assertEqual(product.image_url, "")
            self.assertEqual(product.price_text, "")
            self.assertEqual(product.availability_text, "")
            self.assertEqual(product.currency, "")
        finally:
            os.unlink(feed_path)


class ProviderEligibilityTests(unittest.TestCase):
    def _product(self, **overrides: object):
        base = {
            "provider_key": "awin",
            "provider_product_id": "SKU-1",
            "title": "Sample Product",
            "brand": "SampleBrand",
            "category_text": "Gadgets",
            "product_url": "https://merchant.example/products/sku-1",
            "image_url": "https://cdn.example/img.jpg",
            "price_text": "19.99",
            "availability_text": "in stock",
            "currency": "USD",
            "raw": {},
        }
        base.update(overrides)
        from picwise_providers.contracts import ProviderProduct

        return ProviderProduct(**base)

    def test_valid_product_is_eligible(self) -> None:
        result = evaluate_provider_product_eligibility(self._product())
        self.assertEqual(result.status, "eligible")
        self.assertNotIn("missing_title", result.reason_codes)

    def test_missing_title_is_blocked(self) -> None:
        result = evaluate_provider_product_eligibility(self._product(title=""))
        self.assertEqual(result.status, "blocked")
        self.assertIn("missing_title", result.reason_codes)

    def test_invalid_url_is_blocked(self) -> None:
        result = evaluate_provider_product_eligibility(self._product(product_url="not-a-url"))
        self.assertEqual(result.status, "blocked")
        self.assertIn("invalid_product_url", result.reason_codes)

    def test_missing_image_price_availability_not_faked(self) -> None:
        result = evaluate_provider_product_eligibility(
            self._product(image_url="", price_text="", availability_text="")
        )
        self.assertEqual(result.status, "needs_review")
        self.assertIn("missing_image_url", result.reason_codes)
        self.assertIn("missing_price_text", result.reason_codes)
        self.assertIn("missing_availability_text", result.reason_codes)

        offer = project_provider_products_to_graph((result,)).product_offers[0]
        self.assertEqual(offer.image_url, "")
        self.assertEqual(offer.price_text, "")
        self.assertEqual(offer.availability_text, "")


class ProviderGraphProjectionTests(unittest.TestCase):
    def test_provider_product_creates_offer_and_brand_entities(self) -> None:
        row = {
            "product_id": "G-300",
            "title": "BrandX Wireless Mouse",
            "brand": "BrandX",
            "category": "Computer Mice",
            "product_url": "https://merchant.example/products/g-300",
            "image_url": "https://cdn.example/mouse.jpg",
            "price": "24.50",
            "availability": "available",
        }
        product = normalize_feed_row_to_provider_product(row, provider_key="awin")
        assert product is not None
        eligibility = evaluate_provider_product_eligibility(product)
        projection = project_provider_products_to_graph((eligibility,))

        self.assertEqual(len(projection.product_offers), 1)
        self.assertEqual(len(projection.brands), 1)
        offer = projection.product_offers[0]
        brand = projection.brands[0]
        self.assertEqual(offer.title, "BrandX Wireless Mouse")
        self.assertEqual(offer.provider_key, "awin")
        self.assertEqual(offer.brand_entity_id, brand.entity_id)
        self.assertIn("no_ui_card_eligibility", offer.quality_flags)
        self.assertIn("no_canonical_search_term", offer.quality_flags)

    def test_product_offer_does_not_export_as_canonical_term(self) -> None:
        row = {
            "product_id": "G-301",
            "title": "Unique Offer Title For Export Guard",
            "brand": "BrandY",
            "category": "Keyboards",
            "product_url": "https://merchant.example/products/g-301",
            "image_url": "https://cdn.example/kb.jpg",
        }
        product = normalize_feed_row_to_provider_product(row, provider_key="awin")
        assert product is not None
        eligibility = evaluate_provider_product_eligibility(product)
        projection = project_provider_products_to_graph((eligibility,))

        envelope = SearchEntityGraphEnvelope(
            graph_schema_version="1.0.0",
            source="provider_feed_test_fixture",
            entities=SearchEntityGraphEntities(
                product_offers=projection.product_offers,
                brands=projection.brands,
                product_families=projection.product_families,
                query_aliases=projection.query_aliases,
            ),
            edges=projection.edges,
            export_notes=("provider_feed_stage8a_fixture",),
        )
        terms = export_graph_search_memory_terms(envelope)
        exported = {term.canonical_term for term in terms}
        self.assertNotIn("unique offer title for export guard", exported)


class ProviderRegressionTests(unittest.TestCase):
    def test_manual_amazon_power_banks_still_works(self) -> None:
        result = match_manual_amazon_affiliates("power bank")
        self.assertEqual(result.match_status, AmazonManualMatchStatus.ELIGIBLE)
        self.assertEqual(result.matched_category, "power_banks")
        self.assertGreater(len(result.results), 0)


if __name__ == "__main__":
    unittest.main()
