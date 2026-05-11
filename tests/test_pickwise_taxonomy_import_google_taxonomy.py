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
    import_google_taxonomy_local_file,
    parse_google_taxonomy_file,
    parse_google_taxonomy_text,
    summarize_google_taxonomy_import,
)
from picwise_taxonomy.importers.import_validation import validate_imported_source_items

REAL_GOOGLE_TAXONOMY_FILE = ROOT / "data" / "taxonomy_sources" / "google" / "taxonomy.en-US.txt"


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

    def _real_or_fixture_items(self) -> tuple[str, list[dict]]:
        if REAL_GOOGLE_TAXONOMY_FILE.exists():
            return ("real_file", parse_google_taxonomy_file(str(REAL_GOOGLE_TAXONOMY_FILE)))
        return ("fixture_text", parse_google_taxonomy_text(self._sample_text()))

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
        self.assertTrue(summary["deterministic_path_fingerprint"])

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

    def test_real_google_file_exists_or_fixture_path_is_explicit(self) -> None:
        source, items = self._real_or_fixture_items()
        self.assertIn(source, {"real_file", "fixture_text"})
        self.assertGreater(len(items), 0)

    def test_real_google_file_parses_into_many_paths(self) -> None:
        if not REAL_GOOGLE_TAXONOMY_FILE.exists():
            self.skipTest("Real local Google taxonomy file not present in this checkout.")
        items = parse_google_taxonomy_file(str(REAL_GOOGLE_TAXONOMY_FILE))
        self.assertGreaterEqual(len(items), 1000)

    def test_raw_path_hierarchy_is_preserved(self) -> None:
        source, items = self._real_or_fixture_items()
        self.assertGreater(len(items), 0)
        candidate = next((item for item in items if " > " in item.get("raw_path", "")), items[0])
        segments = candidate["raw_metadata"].get("path_segments", [])
        self.assertEqual(candidate["raw_path"], " > ".join(segments))
        self.assertEqual(candidate["raw_label"], segments[-1] if segments else "")
        if len(segments) > 1:
            self.assertEqual(candidate["raw_parent_label"], segments[-2])

    def test_source_items_generated_and_validate(self) -> None:
        source, items = self._real_or_fixture_items()
        self.assertIn(source, {"real_file", "fixture_text"})
        self.assertTrue(all("source_item_id" in item for item in items))
        validation = validate_imported_source_items(items)
        self.assertTrue(validation["valid"])

    def test_import_report_is_deterministic_and_local_only(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
            handle.write(self._sample_text())
            local_path = handle.name
        try:
            report_one = import_google_taxonomy_local_file(local_path)
            report_two = import_google_taxonomy_local_file(local_path)
        finally:
            Path(local_path).unlink(missing_ok=True)
        self.assertEqual(report_one["summary"], report_two["summary"])
        self.assertTrue(report_one["summary"]["deterministic_path_fingerprint"])
        self.assertTrue(report_one["local_file_or_text_only"])
        self.assertFalse(report_one["mapping_layer_used"])

    def test_no_mapping_fields_or_runtime_dependencies_in_importer(self) -> None:
        source = inspect.getsource(google_taxonomy_importer)
        self.assertNotIn("proposed_engine_id=", source)
        self.assertNotIn("proposed_mega_category_id=", source)
        self.assertNotIn("picwise_app.app", source)
        self.assertNotIn("picwise_search.decision_router", source)
        self.assertNotIn("picwise_nlu", source)


if __name__ == "__main__":
    unittest.main()
