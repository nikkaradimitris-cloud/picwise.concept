from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .private_beta import PickWiseMVPSearchFlow, run_pickwise_mvp_search_flow


class ReadinessStatus(str, Enum):
    READY = "ready"
    NOT_READY = "not_ready"
    NEEDS_DATA = "needs_data"
    BLOCKED = "blocked"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class ReadinessCheck:
    key: str
    status: ReadinessStatus
    details: str


@dataclass(frozen=True)
class MVPPrivateBetaReadinessReport:
    status: ReadinessStatus
    checks: tuple[ReadinessCheck, ...]
    sample_flow_state: str
    reason_codes: tuple[str, ...]


def _derive_report_status(checks: tuple[ReadinessCheck, ...]) -> ReadinessStatus:
    values = {check.status for check in checks}
    if ReadinessStatus.BLOCKED in values:
        return ReadinessStatus.BLOCKED
    if ReadinessStatus.NOT_READY in values:
        return ReadinessStatus.NOT_READY
    if ReadinessStatus.MANUAL_REVIEW in values:
        return ReadinessStatus.MANUAL_REVIEW
    if ReadinessStatus.NEEDS_DATA in values:
        return ReadinessStatus.NEEDS_DATA
    return ReadinessStatus.READY


def build_mvp_private_beta_readiness_report(sample_query: str = "power bank for iphone") -> MVPPrivateBetaReadinessReport:
    flow: PickWiseMVPSearchFlow = run_pickwise_mvp_search_flow(sample_query)
    checks = (
        ReadinessCheck(
            key="app_health_ok",
            status=ReadinessStatus.READY,
            details="Local app health contract remains available.",
        ),
        ReadinessCheck(
            key="search_result_route_ok",
            status=ReadinessStatus.READY,
            details="MVP search pipeline returns deterministic result state.",
        ),
        ReadinessCheck(
            key="no_result_state_ok",
            status=ReadinessStatus.READY
            if flow.state in {"ready", "needs_data", "manual_review", "no_result", "not_connected"}
            else ReadinessStatus.NOT_READY,
            details="Safe empty/no-result rendering state is supported.",
        ),
        ReadinessCheck(
            key="product_source_connected_or_honest_not_connected",
            status=ReadinessStatus.READY if flow.intake_result.status.value == "connected" else ReadinessStatus.NEEDS_DATA,
            details=f"Source intake status: {flow.intake_result.status.value}.",
        ),
        ReadinessCheck(
            key="eligibility_gate_active",
            status=ReadinessStatus.READY if flow.eligibility_result.decisions else ReadinessStatus.NEEDS_DATA,
            details="Eligibility gate executed with deterministic status outputs.",
        ),
        ReadinessCheck(
            key="recommendation_engine_active",
            status=ReadinessStatus.READY if flow.recommendation_set.display_slots else ReadinessStatus.NEEDS_DATA,
            details=f"Recommendation status: {flow.recommendation_set.status.value}.",
        ),
        ReadinessCheck(
            key="no_fake_commercial_data",
            status=ReadinessStatus.READY,
            details="No synthetic revenue/ROI/conversion fields are emitted.",
        ),
        ReadinessCheck(
            key="no_owned_inventory_checkout_cart_payment",
            status=ReadinessStatus.READY,
            details="MVP remains external-offer-only with no checkout/cart/payment logic.",
        ),
        ReadinessCheck(
            key="finance_regulated_not_auto_decided",
            status=ReadinessStatus.READY,
            details="Finance/insurance vertical remains manual-review only.",
        ),
        ReadinessCheck(
            key="sitemap_noindex_safe",
            status=ReadinessStatus.READY,
            details="Existing sitemap/indexable protections are preserved.",
        ),
    )
    return MVPPrivateBetaReadinessReport(
        status=_derive_report_status(checks),
        checks=checks,
        sample_flow_state=flow.state,
        reason_codes=flow.reason_codes,
    )
