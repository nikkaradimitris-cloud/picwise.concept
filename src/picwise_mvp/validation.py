from __future__ import annotations

from .launch_readiness import MVPPrivateBetaReadinessReport, ReadinessStatus


def validate_private_beta_report(report: MVPPrivateBetaReadinessReport) -> None:
    if not report.checks:
        raise ValueError("MVP private beta readiness report requires checks.")
    allowed = {
        ReadinessStatus.READY,
        ReadinessStatus.NOT_READY,
        ReadinessStatus.NEEDS_DATA,
        ReadinessStatus.BLOCKED,
        ReadinessStatus.MANUAL_REVIEW,
    }
    if report.status not in allowed:
        raise ValueError(f"Unsupported readiness status: {report.status}")
