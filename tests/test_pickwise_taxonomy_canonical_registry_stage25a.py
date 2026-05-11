import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.canonical import (
    CanonicalTaxonomyBuildInput,
    CanonicalTaxonomyStatus,
    build_canonical_taxonomy_registry,
    build_canonical_registry_catalog,
    validate_canonical_record,
)
from picwise_taxonomy.importers.google_taxonomy_importer import parse_google_taxonomy_text
from picwise_taxonomy.mapping.google_stage24d import map_google_source_items_stage24d
from picwise_taxonomy.mapping.gap_report_stage24e import build_stage24e_gap_report


class TestPickwiseTaxonomyCanonicalRegistryStage25A(unittest.TestCase):
    def test_builds_canonical_records_from_valid_stage24d_outputs(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Apparel & Accessories > Shoes",
                    "Electronics > Communications > Telephony > Mobile Phones",
                ]
            )
        )
        mapping_batch = map_google_source_items_stage24d(source_items)
        build_result = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(),
            )
        )
        self.assertEqual(build_result.total_records, 2)
        self.assertEqual(build_result.active_records, 2)
        self.assertTrue(build_result.valid)

    def test_active_records_validate_against_real_engine_and_mega_registries(self) -> None:
        source_items = parse_google_taxonomy_text("Apparel & Accessories > Shoes")
        mapping_batch = map_google_source_items_stage24d(source_items)
        build_result = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(),
            )
        )
        active_record = next(record for record in build_result.records if record.status == CanonicalTaxonomyStatus.ACTIVE)
        check = validate_canonical_record(active_record, build_canonical_registry_catalog())
        self.assertTrue(check["engine_exists"])
        self.assertTrue(check["mega_exists"])
        self.assertTrue(check["mega_belongs_to_engine"])
        self.assertTrue(check["valid"])

    def test_weak_or_unmapped_items_do_not_become_active(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Business & Industrial",
                    "Animals & Pet Supplies > Live Animals",
                ]
            )
        )
        mapping_batch = map_google_source_items_stage24d(source_items)
        build_result = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(),
            )
        )
        self.assertEqual(build_result.active_records, 0)
        self.assertTrue(
            all(record.status in {CanonicalTaxonomyStatus.REVIEW_ONLY, CanonicalTaxonomyStatus.BLOCKED_GAP} for record in build_result.records)
        )

    def test_gap_items_only_appear_as_review_or_blocked_gap(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Apparel & Accessories > Shoes",
                    "Animals & Pet Supplies > Live Animals",
                ]
            )
        )
        mapping_batch = map_google_source_items_stage24d(source_items)
        stage24e = build_stage24e_gap_report(
            source_items=source_items,
            mapped_results=mapping_batch["mapped_results"],
        )
        build_result = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(stage24e["gap_records"]),
            )
        )
        uncertain_records = [record for record in build_result.records if record.status != CanonicalTaxonomyStatus.ACTIVE]
        self.assertTrue(all(record.status != CanonicalTaxonomyStatus.ACTIVE for record in uncertain_records))
        self.assertGreaterEqual(build_result.blocked_gap_records + build_result.review_only_records, 1)

    def test_deterministic_ordering_and_stable_record_ids(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Electronics > Communications > Telephony > Mobile Phones",
                    "Apparel & Accessories > Shoes",
                    "Business & Industrial",
                ]
            )
        )
        mapping_batch = map_google_source_items_stage24d(source_items)
        one = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(),
            )
        )
        two = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(),
            )
        )
        self.assertEqual([record.record_id for record in one.records], [record.record_id for record in two.records])
        self.assertEqual(one.counts_by_engine, two.counts_by_engine)
        self.assertEqual(one.counts_by_mega_category, two.counts_by_mega_category)

    def test_summary_counts_are_correct(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Apparel & Accessories > Shoes",
                    "Electronics > Communications > Telephony > Mobile Phones",
                    "Business & Industrial",
                ]
            )
        )
        mapping_batch = map_google_source_items_stage24d(source_items)
        stage24e = build_stage24e_gap_report(
            source_items=source_items,
            mapped_results=mapping_batch["mapped_results"],
        )
        build_result = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(stage24e["gap_records"]),
            )
        )
        self.assertEqual(build_result.total_records, 3)
        self.assertEqual(build_result.active_records + build_result.review_only_records + build_result.blocked_gap_records, 3)
        self.assertEqual(build_result.source_count, 3)
        self.assertEqual(build_result.gap_count, len(stage24e["gap_records"]))

    def test_stage25a_builder_does_not_create_stage25b_or_stage25c_outputs(self) -> None:
        source_items = parse_google_taxonomy_text("Apparel & Accessories > Shoes")
        mapping_batch = map_google_source_items_stage24d(source_items)
        build_result = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(),
            )
        )
        self.assertFalse(build_result.coverage_matrix_created)
        self.assertFalse(build_result.dedup_rules_created)
        self.assertTrue(build_result.canonical_registry_created)

    def test_stage25a_modules_do_not_reference_runtime_routes_or_nlu_modules(self) -> None:
        canonical_paths = [
            SRC / "picwise_taxonomy" / "canonical" / "__init__.py",
            SRC / "picwise_taxonomy" / "canonical" / "contracts.py",
            SRC / "picwise_taxonomy" / "canonical" / "registry_builder.py",
            SRC / "picwise_taxonomy" / "canonical" / "validation.py",
        ]
        forbidden_runtime_tokens = (
            "picwise_app",
            "picwise_search",
            "picwise_nlu",
            "buying_pages",
            "decision_router",
            "specific_product",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in canonical_paths)
        self.assertTrue(all(token not in combined for token in forbidden_runtime_tokens))

    def test_stage25a_canonical_records_hold_taxonomy_only_fields(self) -> None:
        source_items = parse_google_taxonomy_text("Apparel & Accessories > Shoes")
        mapping_batch = map_google_source_items_stage24d(source_items)
        build_result = build_canonical_taxonomy_registry(
            CanonicalTaxonomyBuildInput(
                source_items=tuple(source_items),
                mapped_results=tuple(mapping_batch["mapped_results"]),
                gap_records=tuple(),
            )
        )
        payload = build_result.to_dict()
        serialized = str(payload).lower()
        forbidden_commercial_tokens = (
            "sku",
            "stock",
            "checkout",
            "seller",
            "affiliate",
            "offer_url",
            "product_inventory",
        )
        self.assertTrue(all(token not in serialized for token in forbidden_commercial_tokens))


if __name__ == "__main__":
    unittest.main()
