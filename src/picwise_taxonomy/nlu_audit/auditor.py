from __future__ import annotations

from collections import Counter

from picwise_taxonomy.nlu_training import NLUTrainingPackStatus, QueryVariantType, build_nlu_training_packs

from .contracts import (
    NLUCoverageAuditInput,
    NLUCoverageAuditResult,
    NLUCoverageStrength,
    NLUMegaCategoryAuditRow,
    NLUSafetyStatus,
)
from .validation import validate_audit_result

_SAFE_STATUS = "safe_training_example"
_REVIEW_STATUS = "review_only"
_DISABLED_STATUS = "disabled_gap"
_REQUIRED_VARIANTS = frozenset(item.value for item in QueryVariantType)
_REQUIRED_SCRIPT_MARKERS = frozenset(("english", "greek", "greeklish", "typo"))


def _coverage_strength(
    *,
    pack_status: NLUTrainingPackStatus,
    safe_examples: int,
    variant_counts: Counter,
    script_counts: Counter,
) -> NLUCoverageStrength:
    if pack_status == NLUTrainingPackStatus.INSUFFICIENT_DATA:
        return NLUCoverageStrength.INSUFFICIENT_DATA
    if pack_status == NLUTrainingPackStatus.NEEDS_REVIEW:
        return NLUCoverageStrength.NEEDS_REVIEW
    has_variant_coverage = _REQUIRED_VARIANTS.issubset(set(variant_counts.keys()))
    has_script_coverage = _REQUIRED_SCRIPT_MARKERS.issubset(set(script_counts.keys()))
    if safe_examples >= 100 and has_variant_coverage and has_script_coverage:
        return NLUCoverageStrength.STRONG
    if safe_examples >= 50:
        return NLUCoverageStrength.PARTIAL
    return NLUCoverageStrength.THIN


def _safety_status(unsafe_passes: int, review_only_examples: int, disabled_gap_examples: int) -> NLUSafetyStatus:
    if unsafe_passes > 0:
        return NLUSafetyStatus.INVALID_UNSAFE_PASS
    if review_only_examples > 0 or disabled_gap_examples > 0:
        return NLUSafetyStatus.REVIEW_REQUIRED
    return NLUSafetyStatus.SAFE


def build_nlu_coverage_audit(
    audit_input: NLUCoverageAuditInput | None = None,
) -> NLUCoverageAuditResult:
    active_input = audit_input or NLUCoverageAuditInput()
    training_result = active_input.training_result or build_nlu_training_packs()

    rows: list[NLUMegaCategoryAuditRow] = []
    warnings: list[str] = []
    for pack in training_result.packs:
        variant_counts = Counter(example.variant_type.value for example in pack.examples)
        script_counts = Counter(example.language_script for example in pack.examples)
        safety_counts = Counter(example.safety_status for example in pack.examples)
        unsafe_passes = sum(
            count
            for safety_status, count in safety_counts.items()
            if safety_status not in {_SAFE_STATUS, _REVIEW_STATUS, _DISABLED_STATUS}
        )
        safe_examples = safety_counts.get(_SAFE_STATUS, 0)
        review_only_examples = safety_counts.get(_REVIEW_STATUS, 0)
        disabled_gap_examples = safety_counts.get(_DISABLED_STATUS, 0)
        row_warnings = list(pack.warnings)
        for required_variant in sorted(_REQUIRED_VARIANTS):
            if variant_counts.get(required_variant, 0) == 0:
                row_warnings.append(f"missing_variant_type:{required_variant}")
        for required_script in sorted(_REQUIRED_SCRIPT_MARKERS):
            if script_counts.get(required_script, 0) == 0:
                row_warnings.append(f"missing_language_script:{required_script}")
        if unsafe_passes > 0:
            row_warnings.append("unsafe_pass_detected")
        row = NLUMegaCategoryAuditRow(
            mega_category_id=pack.mega_category_id,
            engine_id=pack.engine_id,
            pack_status=pack.status.value,
            coverage_strength=_coverage_strength(
                pack_status=pack.status,
                safe_examples=safe_examples,
                variant_counts=variant_counts,
                script_counts=script_counts,
            ),
            safety_status=_safety_status(unsafe_passes, review_only_examples, disabled_gap_examples),
            total_examples=len(pack.examples),
            safe_examples=safe_examples,
            review_only_examples=review_only_examples,
            disabled_gap_examples=disabled_gap_examples,
            unsafe_passes=unsafe_passes,
            examples_by_variant_type=dict(sorted(variant_counts.items())),
            examples_by_language_script=dict(sorted(script_counts.items())),
            warnings=tuple(sorted(set(row_warnings))),
        )
        rows.append(row)
        warnings.extend(row.warnings)

    ordered_rows = tuple(sorted(rows, key=lambda item: (item.engine_id, item.mega_category_id)))
    strength_counts = Counter(row.coverage_strength.value for row in ordered_rows)
    total_examples = sum(row.total_examples for row in ordered_rows)
    safe_examples = sum(row.safe_examples for row in ordered_rows)
    review_only_examples = sum(row.review_only_examples for row in ordered_rows)
    disabled_gap_examples = sum(row.disabled_gap_examples for row in ordered_rows)
    unsafe_passes = sum(row.unsafe_passes for row in ordered_rows)

    audit_result = NLUCoverageAuditResult(
        rows=ordered_rows,
        total_mega_categories=len(ordered_rows),
        strong_count=strength_counts.get(NLUCoverageStrength.STRONG.value, 0),
        partial_count=strength_counts.get(NLUCoverageStrength.PARTIAL.value, 0),
        thin_count=strength_counts.get(NLUCoverageStrength.THIN.value, 0),
        insufficient_data_count=strength_counts.get(NLUCoverageStrength.INSUFFICIENT_DATA.value, 0),
        needs_review_count=strength_counts.get(NLUCoverageStrength.NEEDS_REVIEW.value, 0),
        total_examples=total_examples,
        safe_examples=safe_examples,
        review_only_examples=review_only_examples,
        disabled_gap_examples=disabled_gap_examples,
        unsafe_passes=unsafe_passes,
        examples_by_variant_type=dict(
            sorted(Counter(example.variant_type.value for pack in training_result.packs for example in pack.examples).items())
        ),
        examples_by_language_script=dict(
            sorted(Counter(example.language_script for pack in training_result.packs for example in pack.examples).items())
        ),
        examples_by_engine=dict(
            sorted(Counter(example.expected_engine_id for pack in training_result.packs for example in pack.examples).items())
        ),
        examples_by_mega_category=dict(
            sorted((pack.mega_category_id, len(pack.examples)) for pack in training_result.packs)
        ),
        valid=False,
        warnings=tuple(sorted(set(warnings))),
        stage_title=active_input.stage_title,
    )
    validation = validate_audit_result(audit_result)
    return NLUCoverageAuditResult(
        rows=audit_result.rows,
        total_mega_categories=audit_result.total_mega_categories,
        strong_count=audit_result.strong_count,
        partial_count=audit_result.partial_count,
        thin_count=audit_result.thin_count,
        insufficient_data_count=audit_result.insufficient_data_count,
        needs_review_count=audit_result.needs_review_count,
        total_examples=audit_result.total_examples,
        safe_examples=audit_result.safe_examples,
        review_only_examples=audit_result.review_only_examples,
        disabled_gap_examples=audit_result.disabled_gap_examples,
        unsafe_passes=audit_result.unsafe_passes,
        examples_by_variant_type=audit_result.examples_by_variant_type,
        examples_by_language_script=audit_result.examples_by_language_script,
        examples_by_engine=audit_result.examples_by_engine,
        examples_by_mega_category=audit_result.examples_by_mega_category,
        valid=validation["valid"],
        warnings=tuple(sorted(set((*audit_result.warnings, *validation["reasons"])))),
        stage_title=audit_result.stage_title,
    )
