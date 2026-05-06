from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from picwise_contracts import ContractValidationError, DecisionOutput
from picwise_surface import build_dashboard_compatibility_payload

CANONICAL_MISSING_DATA_VALUES = {
    "not_connected",
    "data_not_yet",
    "not_applicable",
    "unknown",
}


class SubbyTransport(Protocol):
    def send(self, payload: dict[str, Any]) -> "SubbyTransportResult":
        """Send payload to a target transport layer."""


@dataclass(frozen=True)
class SubbyTransportResult:
    sent: bool
    mode: str
    reason: str


class NoopSubbyTransport:
    def send(self, payload: dict[str, Any]) -> SubbyTransportResult:
        _validate_subby_payload(payload)
        return SubbyTransportResult(
            sent=False,
            mode="noop_local_test",
            reason="No live endpoint or credentials configured.",
        )


def prepare_subby_dashboard_payload(
    decision_output: DecisionOutput,
    *,
    speed_metrics: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    transport: SubbyTransport | None = None,
) -> tuple[dict[str, Any], SubbyTransportResult]:
    payload = build_dashboard_compatibility_payload(
        decision_output,
        speed_metrics=speed_metrics,
        errors=errors,
    )
    _validate_subby_payload(payload)
    selected_transport = transport or NoopSubbyTransport()
    transport_result = selected_transport.send(payload)
    return payload, transport_result


def _validate_subby_payload(payload: dict[str, Any]) -> None:
    states = payload.get("missing_data_states", [])
    if not isinstance(states, list):
        raise ContractValidationError("Subby payload missing_data_states must be a list.")
    for state in states:
        if state not in CANONICAL_MISSING_DATA_VALUES:
            raise ContractValidationError(f"Invalid missing-data enum for Subby payload: {state}")

    conversion = payload.get("conversion_tracking", {})
    revenue = payload.get("revenue_tracking", {})
    _validate_metric_stub(conversion, "conversion_tracking")
    _validate_metric_stub(revenue, "revenue_tracking")


def _validate_metric_stub(metric: dict[str, Any], key: str) -> None:
    status = metric.get("status")
    if status not in CANONICAL_MISSING_DATA_VALUES:
        raise ContractValidationError(f"{key}.status must use canonical missing-data values.")
    value = metric.get("value")
    if status in {"not_connected", "data_not_yet", "unknown"} and value is not None:
        raise ContractValidationError(f"{key}.value must remain None when status is not connected.")
