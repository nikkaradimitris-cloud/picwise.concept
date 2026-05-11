import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.canonical import (
    CoverageMatrixInput,
    CoverageStrength,
    build_canonical_coverage_matrix,
)
from picwise_taxonomy.canonical.contracts import CanonicalTaxonomyRecord, CanonicalTaxonomyStatus
from picwise_taxonomy.mega_category_registry import get_mega_category_registry


class TestPickwiseTaxonomyCanonicalCoverageStage25B(unittest.TestCase):
    def _record(
        self,
        *,
        record_id: str,
        status: CanonicalTaxonomyStatus,
        engine_id: str,
        mega_category_id: str,
        department: str = "",
        subcategory: str = "",
        product_family: str = "",
        aliases: tuple[str, ...] = (),
        spec_fields: tuple[str, ...] = (),
        intent_patterns: tuple[str, ...] = (),
    ) -> CanonicalTaxonomyRecord:
        return CanonicalTaxonomyRecord(
            record_id=record_id,
            status=status,
            engine_id=engine_id,
            mega_category_id=mega_category_id,
            department=department,
            subcategory=subcategory,
            product_family=product_family,
            aliases=aliases,
            spec_fields=spec_fields,
            intent_patterns=intent_patterns,
        )

    def _sample_stage25a_like_records(self) -> tuple[CanonicalTaxonomyRecord, ...]:
        return (
            self._record(
                record_id="r1",
                status=CanonicalTaxonomyStatus.ACTIVE,
                engine_id="fashion_footwear_jewelry_accessories_engine",
                mega_category_id="footwear_shoes_sneakers_boots",
                department="footwear",
                subcategory="sneakers",
                product_family="running_shoes",
                aliases=("shoes", "sneakers"),
                spec_fields=("size", "material"),
                intent_patterns=("daily_walking",),
            ),
            self._record(
                record_id="r2",
                status=CanonicalTaxonomyStatus.ACTIVE,
                engine_id="fashion_footwear_jewelry_accessories_engine",
                mega_category_id="footwear_shoes_sneakers_boots",
                department="footwear",
                subcategory="boots",
                product_family="hiking_boots",
                aliases=("boots",),
                spec_fields=("size", "weather_resistance"),
                intent_patterns=("trail_use",),
            ),
            self._record(
                record_id="r3",
                status=CanonicalTaxonomyStatus.ACTIVE,
                engine_id="fashion_footwear_jewelry_accessories_engine",
                mega_category_id="footwear_shoes_sneakers_boots",
                department="footwear",
                subcategory="sandals",
                product_family="summer_sandals",
                aliases=("sandals",),
                spec_fields=("size", "closure"),
                intent_patterns=("summer_comfort",),
            ),
            self._record(
                record_id="r4",
                status=CanonicalTaxonomyStatus.ACTIVE,
                engine_id="tech_electronics_office_engine",
                mega_category_id="computers_office_peripherals",
                department="computers",
                subcategory="laptops",
                product_family="business_laptops",
                aliases=("notebooks",),
                spec_fields=("ram", "cpu"),
                intent_patterns=("remote_work",),
            ),
            self._record(
                record_id="r5",
                status=CanonicalTaxonomyStatus.REVIEW_ONLY,
                engine_id="tech_electronics_office_engine",
                mega_category_id="computers_office_peripherals",
                department="computers",
                subcategory="desktops",
                product_family="mini_pcs",
                aliases=("desktop_pc",),
                spec_fields=("ram", "gpu"),
                intent_patterns=("office_setup",),
            ),
            self._record(
                record_id="r6",
                status=CanonicalTaxonomyStatus.BLOCKED_GAP,
                engine_id="auto_moto_mobility_engine",
                mega_category_id="car_parts_service_maintenance",
                department="car_parts",
                subcategory="brakes",
                product_family="brake_pads",
                aliases=("pads",),
                spec_fields=("fitment",),
                intent_patterns=("replace_worn_parts",),
            ),
            self._record(
                record_id="r7",
                status=CanonicalTaxonomyStatus.BLOCKED_GAP,
                engine_id="auto_moto_mobility_engine",
                mega_category_id="car_parts_service_maintenance",
                department="car_parts",
                subcategory="filters",
                product_family="air_filters",
                aliases=("filter",),
                spec_fields=("fitment",),
                intent_patterns=("routine_service",),
            ),
            self._record(
                record_id="r8",
                status=CanonicalTaxonomyStatus.ACTIVE,
                engine_id="auto_moto_mobility_engine",
                mega_category_id="car_parts_service_maintenance",
                department="car_parts",
                subcategory="oils",
                product_family="engine_oils",
                aliases=("engine_oil",),
                spec_fields=("viscosity",),
                intent_patterns=("maintenance",),
            ),
            self._record(
                record_id="r9",
                status=CanonicalTaxonomyStatus.ACTIVE,
                engine_id="tools_diy_garden_repair_engine",
                mega_category_id="power_tools_workshop",
                department="tools",
                subcategory="drills",
                product_family="cordless_drills",
                aliases=("drills",),
                spec_fields=("battery",),
                intent_patterns=("diy_projects",),
            ),
        )

    def test_coverage_matrix_includes_all_18_mega_categories(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        self.assertEqual(result.total_mega_categories, 18)
        self.assertEqual(len(result.rows), 18)
        self.assertEqual({row.mega_category_id for row in result.rows}, {entry["mega_category_id"] for entry in get_mega_category_registry()})

    def test_every_row_validates_against_locked_mega_category_registry(self) -> None:
        registry = {entry["mega_category_id"]: entry["engine_id"] for entry in get_mega_category_registry()}
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        self.assertTrue(result.valid)
        self.assertTrue(all(row.mega_category_id in registry for row in result.rows))
        self.assertTrue(all(row.engine_id == registry[row.mega_category_id] for row in result.rows))

    def test_counts_department_subcategory_and_product_family(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        footwear_row = next(row for row in result.rows if row.mega_category_id == "footwear_shoes_sneakers_boots")
        self.assertEqual(footwear_row.department_count, 1)
        self.assertEqual(footwear_row.subcategory_count, 3)
        self.assertEqual(footwear_row.product_family_count, 3)

    def test_counts_aliases_specs_and_intents(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        footwear_row = next(row for row in result.rows if row.mega_category_id == "footwear_shoes_sneakers_boots")
        self.assertEqual(footwear_row.alias_count, 4)
        self.assertEqual(footwear_row.spec_field_count, 4)
        self.assertEqual(footwear_row.intent_pattern_count, 3)

    def test_gap_counts_are_calculated(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        car_row = next(row for row in result.rows if row.mega_category_id == "car_parts_service_maintenance")
        self.assertEqual(car_row.gap_count, 2)
        self.assertEqual(car_row.blocked_gap_record_count, 2)
        self.assertEqual(result.total_gaps, 2)

    def test_empty_mega_categories_remain_visible(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        empty_rows = [row for row in result.rows if row.active_record_count + row.review_only_record_count + row.blocked_gap_record_count == 0]
        self.assertGreaterEqual(len(empty_rows), 1)
        self.assertTrue(all(row.coverage_strength == CoverageStrength.EMPTY for row in empty_rows))
        self.assertGreaterEqual(result.empty_count, 1)

    def test_gap_heavy_categories_are_classified_honestly(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        car_row = next(row for row in result.rows if row.mega_category_id == "car_parts_service_maintenance")
        self.assertEqual(car_row.coverage_strength, CoverageStrength.GAP_HEAVY)
        self.assertGreaterEqual(result.gap_heavy_count, 1)

    def test_deterministic_ordering_and_summary(self) -> None:
        once = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        twice = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        self.assertEqual([row.mega_category_id for row in once.rows], sorted(row.mega_category_id for row in once.rows))
        self.assertEqual(once.to_dict(), twice.to_dict())

    def test_stage25b_does_not_create_stage25c_dedup_rules(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        self.assertTrue(result.coverage_matrix_created)
        self.assertFalse(result.dedup_rules_created)

    def test_stage25b_does_not_create_stage26_deep_packs(self) -> None:
        result = build_canonical_coverage_matrix(CoverageMatrixInput(records=self._sample_stage25a_like_records()))
        self.assertFalse(result.deep_packs_created)

    def test_stage25b_modules_do_not_reference_runtime_app_router_search_or_nlu(self) -> None:
        stage25b_paths = [
            SRC / "picwise_taxonomy" / "canonical" / "__init__.py",
            SRC / "picwise_taxonomy" / "canonical" / "coverage_matrix.py",
        ]
        forbidden_runtime_tokens = (
            "picwise_app",
            "picwise_search",
            "picwise_nlu",
            "buying_pages",
            "decision_router",
            "specific_product",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in stage25b_paths)
        self.assertTrue(all(token not in combined for token in forbidden_runtime_tokens))

    def test_stage25b_adds_no_commercial_inventory_or_offer_logic(self) -> None:
        stage25b_paths = [
            SRC / "picwise_taxonomy" / "canonical" / "__init__.py",
            SRC / "picwise_taxonomy" / "canonical" / "coverage_matrix.py",
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
        combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in stage25b_paths)
        self.assertTrue(all(token not in combined for token in forbidden_commercial_tokens))


if __name__ == "__main__":
    unittest.main()
