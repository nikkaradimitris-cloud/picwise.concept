from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping, Protocol

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
class SubbyConfig:
    endpoint: str
    project_id: str
    api_key: str


@dataclass(frozen=True)
class SubbyReadiness:
    status: str
    reason: str


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


class LiveSubbyTransport:
    """Live-ready transport wrapper. Real HTTP sender is injectable for tests."""

    def __init__(
        self,
        *,
        config: SubbyConfig,
        sender: SubbyHttpSender | None = None,
    ) -> None:
        self._config = config
        self._sender = sender or NoopSubbyHttpSender()

    def send(self, payload: dict[str, Any]) -> SubbyTransportResult:
        _validate_subby_payload(payload)
        response = self._sender.send(
            endpoint=self._config.endpoint,
            project_id=self._config.project_id,
            api_key=self._config.api_key,
            payload=payload,
        )
        return SubbyTransportResult(
            sent=response.accepted,
            mode="live_http",
            reason=response.reason,
        )


class SubbyHttpSender(Protocol):
    def send(
        self,
        *,
        endpoint: str,
        project_id: str,
        api_key: str,
        payload: dict[str, Any],
    ) -> "SubbyHttpResponse":
        """Send payload to a Subby endpoint."""


@dataclass(frozen=True)
class SubbyHttpResponse:
    accepted: bool
    reason: str


class NoopSubbyHttpSender:
    def send(
        self,
        *,
        endpoint: str,
        project_id: str,
        api_key: str,
        payload: dict[str, Any],
    ) -> SubbyHttpResponse:
        _ = (endpoint, project_id, api_key, payload)
        return SubbyHttpResponse(accepted=False, reason="No live sender configured.")


def load_subby_config_from_env(env: Mapping[str, str] | None = None) -> SubbyConfig:
    source = env if env is not None else os.environ
    return SubbyConfig(
        endpoint=str(source.get("PICWISE_SUBBY_ENDPOINT", "")).strip(),
        project_id=str(source.get("PICWISE_SUBBY_PROJECT_ID", "")).strip(),
        api_key=str(source.get("PICWISE_SUBBY_API_KEY", "")).strip(),
    )


def evaluate_subby_readiness(config: SubbyConfig) -> SubbyReadiness:
    if not config.endpoint or not config.project_id or not config.api_key:
        return SubbyReadiness(
            status="NEEDS_LIVE_SUBBY_CONFIG",
            reason=(
                "Missing PICWISE_SUBBY_ENDPOINT, PICWISE_SUBBY_PROJECT_ID, "
                "or PICWISE_SUBBY_API_KEY."
            ),
        )
    return SubbyReadiness(
        status="INTEGRATION_READY",
        reason="Subby config is present. Live dashboard proof still required.",
    )


def prepare_subby_dashboard_payload(
    decision_output: DecisionOutput,
    *,
    speed_metrics: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    transport: SubbyTransport | None = None,
    config: SubbyConfig | None = None,
    live_sender: SubbyHttpSender | None = None,
) -> tuple[dict[str, Any], SubbyTransportResult]:
    payload = build_dashboard_compatibility_payload(
        decision_output,
        speed_metrics=speed_metrics,
        errors=errors,
    )
    _validate_subby_payload(payload)
    if transport is not None:
        selected_transport = transport
    else:
        chosen_config = config or load_subby_config_from_env()
        readiness = evaluate_subby_readiness(chosen_config)
        if readiness.status == "INTEGRATION_READY":
            selected_transport = LiveSubbyTransport(config=chosen_config, sender=live_sender)
        else:
            selected_transport = NoopSubbyTransport()
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
    forbidden = _find_forbidden_fake_markers(payload)
    if forbidden:
        raise ContractValidationError("Subby payload contains forbidden fake metric markers.")


def _validate_metric_stub(metric: dict[str, Any], key: str) -> None:
    status = metric.get("status")
    if status not in CANONICAL_MISSING_DATA_VALUES:
        raise ContractValidationError(f"{key}.status must use canonical missing-data values.")
    value = metric.get("value")
    if status in {"not_connected", "data_not_yet", "unknown"} and value is not None:
        raise ContractValidationError(f"{key}.value must remain None when status is not connected.")


def _find_forbidden_fake_markers(payload: Any) -> list[str]:
    forbidden = (
        "fake revenue",
        "fake conversion",
        "fake savings",
        "fake urgency",
        "fake confidence",
        "fake ai confidence",
    )
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key).lower()
            if key_text.startswith("fake_") or "commission_rank" in key_text:
                hits.append(str(key))
            hits.extend(_find_forbidden_fake_markers(value))
    elif isinstance(payload, list):
        for item in payload:
            hits.extend(_find_forbidden_fake_markers(item))
    elif isinstance(payload, str):
        lowered = payload.lower()
        for marker in forbidden:
            if marker in lowered:
                hits.append(payload)
    return hits
