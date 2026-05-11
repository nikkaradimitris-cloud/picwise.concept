from __future__ import annotations

from .contracts import NLUCoverageAuditResult


def validate_audit_result(result: NLUCoverageAuditResult) -> dict:
    reasons: list[str] = []
    if result.unsafe_passes != 0:
        reasons.append("unsafe_passes_must_equal_zero")
    if result.unsafe_passes > 0 and result.valid:
        reasons.append("unsafe_passes_should_invalidate_result")
    expected_total = (
        result.strong_count
        + result.partial_count
        + result.thin_count
        + result.insufficient_data_count
        + result.needs_review_count
    )
    if expected_total != result.total_mega_categories:
        reasons.append("coverage_strength_counts_mismatch")
    if result.total_examples != sum(result.examples_by_mega_category.values()):
        reasons.append("total_examples_mismatch")
    if len(result.rows) != result.total_mega_categories:
        reasons.append("row_count_mismatch")
    valid = not reasons and result.unsafe_passes == 0
    return {"valid": valid, "reasons": tuple(sorted(set(reasons)))}
