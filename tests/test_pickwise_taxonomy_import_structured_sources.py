import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.importers.structured_source_importer import (
    import_source_csv_text,
    import_source_json_text,
    import_source_records,
)
from picwise_taxonomy.importers.import_validation import validate_imported_source_items


class TestPickwiseTaxonomyImportStructuredSources(unittest.TestCase):
    def test_import_source_json_text_parses_json_list(self) -> None:
        payload = json.dumps(
            [
                {
                    "path": "Home & Garden > Kitchen & Dining",
                    "aliases": ["kitchen dining", "cookware area"],
                    "metadata": {"origin": "seed"},
                }
            ]
        )
        items = import_source_json_text(payload, source_name="json_export")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["raw_path"], "Home & Garden > Kitchen & Dining")

    def test_import_source_csv_text_parses_csv_text(self) -> None:
        csv_text = (
            "path,label,parent,aliases\n"
            "Hardware > Tools,,,tools|hardware tools\n"
            "Apparel & Accessories > Shoes,,,shoes\n"
        )
        items = import_source_csv_text(csv_text, source_name="csv_export")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_type"], "csv_import")

    def test_records_become_valid_workbench_source_items(self) -> None:
        records = [
            {"path": "Vehicles & Parts > Vehicle Parts & Accessories", "aliases": ["vehicle parts"]},
        ]
        items = import_source_records(records, source_name="manual_records", source_type="manual_seed")
        validation = validate_imported_source_items(items)
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["total_items"], 1)

    def test_aliases_preserved_as_proposed_aliases(self) -> None:
        records = [
            {"path": "Hardware > Tools > Hand Tools", "aliases": ["hand tools", "manual tools"]},
        ]
        items = import_source_records(records, source_name="manual_records", source_type="manual_seed")
        self.assertEqual(items[0]["proposed_aliases"], ["hand tools", "manual tools"])

    def test_invalid_or_empty_records_handled_safely(self) -> None:
        records = [{}, {"path": "   "}, "bad-record", {"label": "Missing Parent Path"}]
        items = import_source_records(records, source_name="manual_records", source_type="manual_seed")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["raw_path"], "Missing Parent Path")

    def test_inventory_commercial_fields_do_not_pass_silently(self) -> None:
        records = [
            {"path": "Hardware > Tools", "price": "10.00"},
            {"path": "Home & Garden > Kitchen & Dining", "sku": "ABCD"},
        ]
        items = import_source_records(records, source_name="manual_records", source_type="manual_seed")
        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
