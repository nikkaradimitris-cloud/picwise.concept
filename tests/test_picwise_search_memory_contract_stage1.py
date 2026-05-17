from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_memory.contracts import (  # noqa: E402
    CanonicalVocabularyBuildReport,
    CanonicalVocabularyRecord,
    CanonicalVocabularyRegistry,
)
from picwise_search_memory.validation import stable_canonical_id, validate_record  # noqa: E402

_FORBIDDEN_FIELDS = {
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "prices",
    "affiliate",
    "affiliate_url",
    "seller",
    "stock",
    "checkout",
}


class PicWiseSearchMemoryContractStage1Tests(unittest.TestCase):
    def test_record_contract_contains_required_fields(self) -> None:
        term = "coffee grinder"
        category = "kitchen_cooking_household"
        record = CanonicalVocabularyRecord(
            canonical_id=stable_canonical_id(category, term),
            canonical_term=term,
            normalized_term=term,
            mega_category_id=category,
            source="taxonomy_clean_vocabulary",
            source_file="vocabulary_source.py",
            language="english",
            status="active",
            schema_version="1.0.0",
            token_count=2,
            quality_flags=("offline_registry",),
        )
        payload = record.to_dict()
        expected_keys = {
            "canonical_id",
            "canonical_term",
            "normalized_term",
            "mega_category_id",
            "source",
            "source_file",
            "language",
            "status",
            "schema_version",
            "token_count",
            "quality_flags",
            "aliases",
            "product_family",
            "source_path",
            "confidence_weight",
        }
        self.assertEqual(set(payload.keys()), expected_keys)

    def test_forbidden_fields_not_present_in_record_dict(self) -> None:
        record = CanonicalVocabularyRecord(
            canonical_id=stable_canonical_id("phones_mobile_accessories", "usb c cable"),
            canonical_term="usb c cable",
            normalized_term="usb c cable",
            mega_category_id="phones_mobile_accessories",
            source="taxonomy_clean_vocabulary",
            source_file="vocabulary_source.py",
            language="english",
            status="active",
            schema_version="1.0.0",
            token_count=3,
            quality_flags=("offline_registry",),
        )
        self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(set(record.to_dict().keys())))

    def test_validate_record_requires_stable_id(self) -> None:
        record = CanonicalVocabularyRecord(
            canonical_id="cv_not_stable",
            canonical_term="baby monitor",
            normalized_term="baby monitor",
            mega_category_id="baby_kids_pets_sports_outdoor",
            source="taxonomy_clean_vocabulary",
            source_file="vocabulary_source.py",
            language="english",
            status="active",
            schema_version="1.0.0",
            token_count=2,
            quality_flags=("offline_registry",),
        )
        reasons = validate_record(record)
        self.assertIn("canonical_id_not_stable", reasons)

    def test_registry_and_report_contracts_are_serializable(self) -> None:
        record = CanonicalVocabularyRecord(
            canonical_id=stable_canonical_id("power_tools_workshop", "cordless drill"),
            canonical_term="cordless drill",
            normalized_term="cordless drill",
            mega_category_id="power_tools_workshop",
            source="taxonomy_clean_vocabulary",
            source_file="vocabulary_source.py",
            language="english",
            status="active",
            schema_version="1.0.0",
            token_count=2,
            quality_flags=("offline_registry",),
        )
        report = CanonicalVocabularyBuildReport(
            total_input_terms=1,
            total_records=1,
            rejected_terms=0,
            duplicate_terms=0,
            rejected_by_reason={},
            counts_by_mega_category={"power_tools_workshop": 1},
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
            language="english",
            status="active",
        )
        registry = CanonicalVocabularyRegistry(
            records=(record,),
            report=report,
            source="taxonomy_clean_vocabulary",
            schema_version="1.0.0",
        )
        payload = registry.to_dict()
        self.assertEqual(payload["report"]["total_records"], 1)
        self.assertEqual(len(payload["records"]), 1)


if __name__ == "__main__":
    unittest.main()
