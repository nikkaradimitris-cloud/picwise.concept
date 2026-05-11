from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from picwise_taxonomy.mega_category_registry import get_mega_category_registry

from .contracts import CanonicalTaxonomyRecord, CanonicalTaxonomyStatus


class CoverageStrength(str, Enum):
    STRONG = "strong"
    PARTIAL = "partial"
    THIN = "thin"
    EMPTY = "empty"
    GAP_HEAVY = "gap_heavy"


@dataclass(frozen=True)
class CoverageMatrixInput:
    records: tuple[CanonicalTaxonomyRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CoverageMatrixRow:
    mega_category_id: str
    engine_id: str
    department_count: int
    subcategory_count: int
    product_family_count: int
    alias_count: int
    spec_field_count: int
    intent_pattern_count: int
    gap_count: int
    active_record_count: int
    review_only_record_count: int
    blocked_gap_record_count: int
    coverage_strength: CoverageStrength

    def to_dict(self) -> dict:
        return {
            "mega_category_id": self.mega_category_id,
            "engine_id": self.engine_id,
            "department_count": self.department_count,
            "subcategory_count": self.subcategory_count,
            "product_family_count": self.product_family_count,
            "alias_count": self.alias_count,
            "spec_field_count": self.spec_field_count,
            "intent_pattern_count": self.intent_pattern_count,
            "gap_count": self.gap_count,
            "active_record_count": self.active_record_count,
            "review_only_record_count": self.review_only_record_count,
            "blocked_gap_record_count": self.blocked_gap_record_count,
            "coverage_strength": self.coverage_strength.value,
        }


@dataclass(frozen=True)
class CoverageMatrixResult:
    rows: tuple[CoverageMatrixRow, ...]
    total_mega_categories: int
    strong_count: int
    partial_count: int
    thin_count: int
    empty_count: int
    gap_heavy_count: int
    total_departments: int
    total_subcategories: int
    total_product_families: int
    total_aliases: int
    total_spec_fields: int
    total_intent_patterns: int
    total_gaps: int
    valid: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    stage: str = "Stage 25B — Coverage Matrix for 18 Mega-Categories"
    coverage_matrix_created: bool = True
    dedup_rules_created: bool = False
    deep_packs_created: bool = False

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "rows": [row.to_dict() for row in self.rows],
            "summary": {
                "total_mega_categories": self.total_mega_categories,
                "strong_count": self.strong_count,
                "partial_count": self.partial_count,
                "thin_count": self.thin_count,
                "empty_count": self.empty_count,
                "gap_heavy_count": self.gap_heavy_count,
                "total_departments": self.total_departments,
                "total_subcategories": self.total_subcategories,
                "total_product_families": self.total_product_families,
                "total_aliases": self.total_aliases,
                "total_spec_fields": self.total_spec_fields,
                "total_intent_patterns": self.total_intent_patterns,
                "total_gaps": self.total_gaps,
                "valid": self.valid,
                "warnings": list(self.warnings),
            },
            "coverage_matrix_created": self.coverage_matrix_created,
            "dedup_rules_created": self.dedup_rules_created,
            "deep_packs_created": self.deep_packs_created,
        }


def _coverage_strength_for_row(
    *,
    total_records: int,
    department_count: int,
    subcategory_count: int,
    product_family_count: int,
    gap_count: int,
    active_record_count: int,
) -> CoverageStrength:
    if total_records == 0:
        return CoverageStrength.EMPTY
    if gap_count > 0 and gap_count >= active_record_count:
        return CoverageStrength.GAP_HEAVY

    structure_score = department_count + subcategory_count + product_family_count
    if (
        active_record_count >= 3
        and department_count >= 1
        and subcategory_count >= 1
        and product_family_count >= 2
        and gap_count == 0
    ):
        return CoverageStrength.STRONG
    if active_record_count <= 1 or structure_score <= 3 or product_family_count <= 1:
        return CoverageStrength.THIN
    return CoverageStrength.PARTIAL


def build_canonical_coverage_matrix(matrix_input: CoverageMatrixInput) -> CoverageMatrixResult:
    records = tuple(matrix_input.records or ())
    registry = sorted(get_mega_category_registry(), key=lambda entry: str(entry.get("mega_category_id", "")))
    mega_to_engine = {
        str(entry.get("mega_category_id", "")).strip(): str(entry.get("engine_id", "")).strip() for entry in registry
    }

    warnings: list[str] = []
    rows: list[CoverageMatrixRow] = []
    valid = True

    for mega_entry in registry:
        mega_category_id = str(mega_entry.get("mega_category_id", "")).strip()
        expected_engine_id = str(mega_entry.get("engine_id", "")).strip()
        row_records = tuple(record for record in records if record.mega_category_id == mega_category_id)

        departments = {record.department for record in row_records if record.department}
        subcategories = {record.subcategory for record in row_records if record.subcategory}
        product_families = {record.product_family for record in row_records if record.product_family}
        aliases = {alias for record in row_records for alias in record.aliases if alias}
        spec_fields = {field_name for record in row_records for field_name in record.spec_fields if field_name}
        intent_patterns = {pattern for record in row_records for pattern in record.intent_patterns if pattern}

        active_record_count = sum(1 for record in row_records if record.status == CanonicalTaxonomyStatus.ACTIVE)
        review_only_record_count = sum(1 for record in row_records if record.status == CanonicalTaxonomyStatus.REVIEW_ONLY)
        blocked_gap_record_count = sum(1 for record in row_records if record.status == CanonicalTaxonomyStatus.BLOCKED_GAP)
        gap_count = blocked_gap_record_count

        engine_ids_in_rows = {record.engine_id for record in row_records if record.engine_id}
        if any(engine_id != expected_engine_id for engine_id in engine_ids_in_rows):
            valid = False
            warnings.append(
                f"Mega category {mega_category_id} has records with engine mismatch; expected {expected_engine_id}."
            )

        coverage_strength = _coverage_strength_for_row(
            total_records=len(row_records),
            department_count=len(departments),
            subcategory_count=len(subcategories),
            product_family_count=len(product_families),
            gap_count=gap_count,
            active_record_count=active_record_count,
        )

        if coverage_strength in {CoverageStrength.EMPTY, CoverageStrength.THIN, CoverageStrength.GAP_HEAVY}:
            warnings.append(f"Mega category {mega_category_id} has {coverage_strength.value} coverage.")

        rows.append(
            CoverageMatrixRow(
                mega_category_id=mega_category_id,
                engine_id=expected_engine_id,
                department_count=len(departments),
                subcategory_count=len(subcategories),
                product_family_count=len(product_families),
                alias_count=len(aliases),
                spec_field_count=len(spec_fields),
                intent_pattern_count=len(intent_patterns),
                gap_count=gap_count,
                active_record_count=active_record_count,
                review_only_record_count=review_only_record_count,
                blocked_gap_record_count=blocked_gap_record_count,
                coverage_strength=coverage_strength,
            )
        )

    row_mega_ids = {row.mega_category_id for row in rows}
    expected_mega_ids = set(mega_to_engine)
    if row_mega_ids != expected_mega_ids:
        valid = False
        missing = sorted(expected_mega_ids - row_mega_ids)
        extra = sorted(row_mega_ids - expected_mega_ids)
        if missing:
            warnings.append(f"Missing mega categories in coverage matrix: {', '.join(missing)}.")
        if extra:
            warnings.append(f"Unknown mega categories in coverage matrix: {', '.join(extra)}.")

    strength_counts = {strength.value: 0 for strength in CoverageStrength}
    for row in rows:
        strength_counts[row.coverage_strength.value] += 1

    return CoverageMatrixResult(
        rows=tuple(rows),
        total_mega_categories=len(rows),
        strong_count=strength_counts[CoverageStrength.STRONG.value],
        partial_count=strength_counts[CoverageStrength.PARTIAL.value],
        thin_count=strength_counts[CoverageStrength.THIN.value],
        empty_count=strength_counts[CoverageStrength.EMPTY.value],
        gap_heavy_count=strength_counts[CoverageStrength.GAP_HEAVY.value],
        total_departments=sum(row.department_count for row in rows),
        total_subcategories=sum(row.subcategory_count for row in rows),
        total_product_families=sum(row.product_family_count for row in rows),
        total_aliases=sum(row.alias_count for row in rows),
        total_spec_fields=sum(row.spec_field_count for row in rows),
        total_intent_patterns=sum(row.intent_pattern_count for row in rows),
        total_gaps=sum(row.gap_count for row in rows),
        valid=valid,
        warnings=tuple(sorted(set(warnings))),
    )
