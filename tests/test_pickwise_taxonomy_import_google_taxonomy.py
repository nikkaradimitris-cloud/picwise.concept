import inspect
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.importers import google_taxonomy_importer
from picwise_taxonomy.importers.google_taxonomy_importer import (
    parse_google_taxonomy_file,
    parse_google_taxonomy_text,
    summarize_google_taxonomy_import,
)


class TestPickwiseTaxonomyImportGoogleTaxonomy(unittest.TestCase):
    def _sample_text(self) -> str:
        return "\n".join(
            [
                "# Google Product Taxonomy sample",
                "Google_Product_Taxonomy_Version: 2026-01-01",
                "",
                "Apparel & Accessories > Shoes",
                "Hardware > Tools",
                "Vehicles & Parts > Vehicle Parts & Accessories",
                "Home & Garden > Kitchen & Dining",
            ]
        )

    def test_parse_google_taxonomy_text_parses_sample_content(self) -> None:
        items = parse_google_taxonomy_text(self._sample_text())
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0]["raw_path"], "Apparel & Accessories > Shoes")

    def test_ignores_comment_header_and_empty_lines(self) -> None:
        items = parse_google_taxonomy_text(self._sample_text())
        raw_paths = {item["raw_path"] for item in items}
        self.assertNotIn("", raw_paths)
        self.assertNotIn("Google_Product_Taxonomy_Version: 2026-01-01", raw_paths)

    def test_source_name_and_source_type_are_google_defaults(self) -> None:
        items = parse_google_taxonomy_text(self._sample_text())
        self.assertTrue(all(item["source_name"] == "google_product_taxonomy" for item in items))
        self.assertTrue(all(item["source_type"] == "public_taxonomy_reference" for item in items))

    def test_parses_required_examples(self) -> None:
        items = parse_google_taxonomy_text(self._sample_text())
        raw_paths = {item["raw_path"] for item in items}
        self.assertIn("Apparel & Accessories > Shoes", raw_paths)
        self.assertIn("Hardware > Tools", raw_paths)
        self.assertIn("Vehicles & Parts > Vehicle Parts & Accessories", raw_paths)
        self.assertIn("Home & Garden > Kitchen & Dining", raw_paths)

    def test_parse_google_taxonomy_file_reads_local_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
            handle.write(self._sample_text())
            local_path = handle.name
        try:
            items = parse_google_taxonomy_file(local_path)
            self.assertEqual(len(items), 4)
        finally:
            Path(local_path).unlink(missing_ok=True)

    def test_summarize_google_taxonomy_import_returns_counts(self) -> None:
        items = parse_google_taxonomy_text(self._sample_text())
        summary = summarize_google_taxonomy_import(items)
        self.assertEqual(summary["total_items"], 4)
        self.assertEqual(summary["unique_path_count"], 4)
        self.assertTrue(summary["local_file_or_text_only"])

    def test_no_network_download_or_api_behavior(self) -> None:
        source = inspect.getsource(google_taxonomy_importer).lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)

    def test_no_products_prices_offers_or_skus(self) -> None:
        items = parse_google_taxonomy_text(self._sample_text())
        forbidden = {"product", "products", "offer", "offers", "price", "sku", "affiliate"}
        for item in items:
            self.assertTrue(forbidden.isdisjoint(set(item.keys())))


if __name__ == "__main__":
    unittest.main()
