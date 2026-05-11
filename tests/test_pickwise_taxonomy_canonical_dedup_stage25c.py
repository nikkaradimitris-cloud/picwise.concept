import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.canonical import (
    DeduplicationInput,
    MergeReason,
    MergeStatus,
    build_taxonomy_deduplication,
)
from picwise_taxonomy.canonical.contracts import (
    CanonicalSourceReference,
    CanonicalTaxonomyRecord,
    CanonicalTaxonomyStatus,
)


class TestPickwiseTaxonomyCanonicalDedupStage25C(unittest.TestCase):
    def _record(
        self,
        *,
        record_id: str,
        engine_id: str,
        mega_category_id: str,
        product_family: str,
        aliases: tuple[str, ...] = (),
        status: CanonicalTaxonomyStatus = CanonicalTaxonomyStatus.ACTIVE,
        source_item_id: str | None = None,
    ) -> CanonicalTaxonomyRecord:
        source_reference = CanonicalSourceReference(
            source_item_id=source_item_id or f"source_{record_id}",
            source_name="stage24_source",
            source_type="google_taxonomy",
            mapping_status="mapped",
            mapping_confidence="exact",
            mapping_gap_reason="",
        )
        return CanonicalTaxonomyRecord(
            record_id=record_id,
            status=status,
            engine_id=engine_id,
            mega_category_id=mega_category_id,
            department="dept",
            subcategory="sub",
            product_family=product_family,
            aliases=aliases,
            spec_fields=("size",),
            intent_patterns=("compare",),
            source_references=(source_reference,),
            provenance=("stage25a_canonical_registry_builder",),
        )

    def _find_candidate(self, result, left_id: str, right_id: str):
        requested = {left_id, right_id}
        for candidate in result.candidates:
            if set(candidate.record_ids) == requested:
                return candidate
        self.fail(f"Missing candidate for pair {(left_id, right_id)}")

    def test_exact_normalized_duplicates_produce_merge_allowed(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="Electric Scooter",
            ),
            self._record(
                record_id="r2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        candidate = self._find_candidate(result, "r1", "r2")
        self.assertEqual(candidate.decision.status, MergeStatus.MERGE_ALLOWED)
        self.assertIn(MergeReason.EXACT_NORMALIZED_MATCH, candidate.decision.reasons)

    def test_alias_duplicates_produce_safe_merge_when_scope_is_compatible(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
                aliases=("e scooter",),
            ),
            self._record(
                record_id="r2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="urban rides",
                aliases=("electric scooter",),
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        candidate = self._find_candidate(result, "r1", "r2")
        self.assertEqual(candidate.decision.status, MergeStatus.MERGE_ALLOWED)
        self.assertIn(MergeReason.ALIAS_MATCH, candidate.decision.reasons)

    def test_greek_and_greeklish_variants_can_be_grouped_safely(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="ηλεκτρικό πατίνι",
            ),
            self._record(
                record_id="r2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="ilektriko patini",
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        candidate = self._find_candidate(result, "r1", "r2")
        self.assertEqual(candidate.decision.status, MergeStatus.MERGE_ALLOWED)
        self.assertIn(MergeReason.GREEK_GREEKLISH_MATCH, candidate.decision.reasons)

    def test_typo_variants_can_be_grouped_when_deterministic(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
            ),
            self._record(
                record_id="r2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooteer",
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        candidate = self._find_candidate(result, "r1", "r2")
        self.assertEqual(candidate.decision.status, MergeStatus.MERGE_ALLOWED)
        self.assertIn(MergeReason.TYPO_VARIANT_MATCH, candidate.decision.reasons)

    def test_ambiguous_concepts_become_review_required(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="tools_diy_garden_repair_engine",
                mega_category_id="power_tools_workshop",
                product_family="accessories",
            ),
            self._record(
                record_id="r2",
                engine_id="tools_diy_garden_repair_engine",
                mega_category_id="power_tools_workshop",
                product_family="accessories",
                aliases=("generic accessories",),
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        candidate = self._find_candidate(result, "r1", "r2")
        self.assertEqual(candidate.decision.status, MergeStatus.REVIEW_REQUIRED)
        self.assertIn(MergeReason.AMBIGUOUS_MATCH, candidate.decision.reasons)

    def test_incompatible_engine_or_mega_candidates_are_not_merge_allowed(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
            ),
            self._record(
                record_id="r2",
                engine_id="tech_electronics_office_engine",
                mega_category_id="phones_mobile_accessories",
                product_family="electric scooter",
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        candidate = self._find_candidate(result, "r1", "r2")
        self.assertIn(candidate.decision.status, {MergeStatus.BLOCKED, MergeStatus.REVIEW_REQUIRED})
        self.assertIn(MergeReason.INCOMPATIBLE_ENGINE, candidate.decision.reasons)
        self.assertIn(MergeReason.INCOMPATIBLE_MEGA_CATEGORY, candidate.decision.reasons)

    def test_unrelated_concepts_are_not_merged(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
            ),
            self._record(
                record_id="r2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="mountain bike helmet",
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        self.assertEqual(result.total_candidates, 0)

    def test_deduplication_ordering_and_summary_are_stable(self) -> None:
        records = (
            self._record(
                record_id="z2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="e-scooter",
            ),
            self._record(
                record_id="a1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
            ),
            self._record(
                record_id="b3",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooteer",
            ),
        )
        one = build_taxonomy_deduplication(DeduplicationInput(records=records))
        two = build_taxonomy_deduplication(DeduplicationInput(records=records))
        self.assertEqual([candidate.candidate_id for candidate in one.candidates], sorted(c.candidate_id for c in one.candidates))
        self.assertEqual(one.to_dict(), two.to_dict())
        self.assertEqual(
            one.total_candidates,
            one.merge_allowed_count + one.review_required_count + one.blocked_count,
        )

    def test_source_references_and_provenance_are_preserved(self) -> None:
        records = (
            self._record(
                record_id="r1",
                source_item_id="source_1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
            ),
            self._record(
                record_id="r2",
                source_item_id="source_2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="e scooter",
                aliases=("electric scooter",),
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        candidate = self._find_candidate(result, "r1", "r2")
        source_ids = {reference.source_item_id for reference in candidate.source_references}
        self.assertEqual(source_ids, {"source_1", "source_2"})
        self.assertIn("stage25a_canonical_registry_builder", candidate.provenance)

    def test_stage25c_does_not_create_stage26_deep_packs(self) -> None:
        records = (
            self._record(
                record_id="r1",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="electric scooter",
            ),
            self._record(
                record_id="r2",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                product_family="e-scooter",
            ),
        )
        result = build_taxonomy_deduplication(DeduplicationInput(records=records))
        self.assertTrue(result.dedup_rules_created)
        self.assertFalse(result.deep_packs_created)

    def test_stage25c_does_not_export_to_local_nlu(self) -> None:
        stage25c_paths = [
            SRC / "picwise_taxonomy" / "canonical" / "__init__.py",
            SRC / "picwise_taxonomy" / "canonical" / "deduplication.py",
        ]
        forbidden_local_nlu_tokens = ("local_nlu", "picwise_nlu", "export_nlu")
        combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in stage25c_paths)
        self.assertTrue(all(token not in combined for token in forbidden_local_nlu_tokens))

    def test_stage25c_does_not_reference_runtime_app_router_search_or_nlu(self) -> None:
        stage25c_paths = [
            SRC / "picwise_taxonomy" / "canonical" / "__init__.py",
            SRC / "picwise_taxonomy" / "canonical" / "deduplication.py",
        ]
        forbidden_runtime_tokens = (
            "picwise_app",
            "picwise_search",
            "picwise_nlu",
            "buying_pages",
            "decision_router",
            "specific_product",
        )
        combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in stage25c_paths)
        self.assertTrue(all(token not in combined for token in forbidden_runtime_tokens))

    def test_stage25c_adds_no_inventory_or_offer_logic(self) -> None:
        stage25c_paths = [
            SRC / "picwise_taxonomy" / "canonical" / "__init__.py",
            SRC / "picwise_taxonomy" / "canonical" / "deduplication.py",
        ]
        forbidden_commercial_tokens = (
            "price",
            "sku",
            "stock",
            "checkout",
            "seller",
            "affiliate",
            "offer_url",
            "product_inventory",
        )
        combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in stage25c_paths)
        self.assertTrue(all(token not in combined for token in forbidden_commercial_tokens))


if __name__ == "__main__":
    unittest.main()
