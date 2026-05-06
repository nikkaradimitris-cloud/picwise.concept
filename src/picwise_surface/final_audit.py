from __future__ import annotations

from dataclasses import dataclass

LOCKED_ROADMAP_TITLES = [
    "10. Landing UI",
    "11. CTA/redirect tracking",
    "12. SEO landing generation",
    "13. Dashboard/Subby event compatibility",
    "14. Performance audit",
    "15. Final V1 audit closure",
]


@dataclass(frozen=True)
class FinalV1AuditEvidence:
    stage_10_implemented: bool
    stage_11_implemented: bool
    stage_12_implemented: bool
    stage_13_implemented: bool
    stage_14_implemented: bool
    tests_passed: bool
    no_fake_data: bool
    no_commission_ranking: bool
    roadmap_titles_unchanged: bool
    progress_updated_accurately: bool


@dataclass(frozen=True)
class FinalV1AuditResult:
    passed: bool
    checks: dict[str, bool]
    ready_claim: str
    not_live_claim: str


def run_final_v1_audit_closure(evidence: FinalV1AuditEvidence) -> FinalV1AuditResult:
    checks = {
        "stage_10_implemented": evidence.stage_10_implemented,
        "stage_11_implemented": evidence.stage_11_implemented,
        "stage_12_implemented": evidence.stage_12_implemented,
        "stage_13_implemented": evidence.stage_13_implemented,
        "stage_14_implemented": evidence.stage_14_implemented,
        "tests_passed": evidence.tests_passed,
        "no_fake_data": evidence.no_fake_data,
        "no_commission_ranking": evidence.no_commission_ranking,
        "roadmap_titles_unchanged": evidence.roadmap_titles_unchanged,
        "progress_updated_accurately": evidence.progress_updated_accurately,
    }
    passed = all(checks.values())
    ready_claim = (
        "Local V1 product-surface readiness layer is implemented, tested, and commit-ready."
        if passed
        else "Final V1 audit closure cannot be marked PASSED yet."
    )
    not_live_claim = (
        "Not live/deployed: no live production deployment, no live dashboard connection, "
        "no real product feed, and no real revenue/conversion tracking."
    )
    return FinalV1AuditResult(
        passed=passed,
        checks=checks,
        ready_claim=ready_claim,
        not_live_claim=not_live_claim,
    )
