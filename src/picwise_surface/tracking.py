from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from picwise_contracts import (
    ContractValidationError,
    DecisionOutput,
    RedirectEvent,
    TrackingEvent,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class RedirectPreparation:
    redirect_event: RedirectEvent
    cta_click_event: TrackingEvent
    click_kind_event: TrackingEvent
    redirect_attempt_event: TrackingEvent
    click_to_redirect_budget_ms: int


def prepare_redirect_tracking(
    decision_output: DecisionOutput,
    selected_product_id: str,
    session_id: str,
    click_to_redirect_budget_ms: int,
    *,
    source: str = "landing_ui",
) -> RedirectPreparation:
    if click_to_redirect_budget_ms >= 300:
        raise ContractValidationError("Click-to-redirect budget must remain < 300ms.")

    choice = _find_choice(decision_output, selected_product_id)
    timestamp = _utc_timestamp()
    metadata = {
        "provider_id": choice.merchant_or_provider,
        "redirect_url": choice.redirect_target,
        "recommended_product_id": decision_output.recommended_product_id,
        "selected_product_id": choice.product_id,
        "click_to_redirect_budget_ms": click_to_redirect_budget_ms,
        "prepared_without_network_call": True,
    }

    redirect_event = RedirectEvent.from_dict(
        {
            "event_id": str(uuid4()),
            "timestamp": timestamp,
            "query": decision_output.query,
            "product_id": choice.product_id,
            "merchant_or_provider": choice.merchant_or_provider,
            "redirect_target": choice.redirect_target,
            "recommended": choice.is_recommended,
            "click_to_redirect_budget_ms": click_to_redirect_budget_ms,
            "tracking_metadata": {
                **choice.tracking_metadata,
                "selected_product_id": choice.product_id,
                "recommended": choice.is_recommended,
            },
        }
    )

    cta_click_event = _build_tracking_event(
        event_type="cta_click",
        decision_output=decision_output,
        session_id=session_id,
        source=source,
        timestamp=timestamp,
        product_id=choice.product_id,
        recommended=choice.is_recommended,
        metadata=metadata,
    )
    click_kind_event = _build_tracking_event(
        event_type="recommended_click" if choice.is_recommended else "non_recommended_click",
        decision_output=decision_output,
        session_id=session_id,
        source=source,
        timestamp=timestamp,
        product_id=choice.product_id,
        recommended=choice.is_recommended,
        metadata=metadata,
    )
    redirect_attempt_event = _build_tracking_event(
        event_type="redirect_attempt",
        decision_output=decision_output,
        session_id=session_id,
        source=source,
        timestamp=timestamp,
        product_id=choice.product_id,
        recommended=choice.is_recommended,
        metadata=metadata,
    )

    return RedirectPreparation(
        redirect_event=redirect_event,
        cta_click_event=cta_click_event,
        click_kind_event=click_kind_event,
        redirect_attempt_event=redirect_attempt_event,
        click_to_redirect_budget_ms=click_to_redirect_budget_ms,
    )


def build_redirect_outcome_event(
    decision_output: DecisionOutput,
    selected_product_id: str,
    session_id: str,
    *,
    success: bool,
    latency_ms: int,
    source: str = "landing_ui",
    error_message: str | None = None,
) -> TrackingEvent:
    event_type = "redirect_success" if success else "redirect_failure"
    choice = _find_choice(decision_output, selected_product_id)
    metadata: dict[str, Any] = {
        "provider_id": choice.merchant_or_provider,
        "redirect_url": choice.redirect_target,
        "latency_ms": latency_ms,
    }
    if error_message:
        metadata["error_message"] = error_message

    return _build_tracking_event(
        event_type=event_type,
        decision_output=decision_output,
        session_id=session_id,
        source=source,
        timestamp=_utc_timestamp(),
        product_id=choice.product_id,
        recommended=choice.is_recommended,
        metadata=metadata,
    )


def _find_choice(decision_output: DecisionOutput, selected_product_id: str):
    all_choices = list(decision_output.choices) + list(decision_output.more_choices or [])
    for choice in all_choices:
        if choice.product_id == selected_product_id:
            return choice
    raise ContractValidationError("Selected product/provider does not exist in decision output.")


def _build_tracking_event(
    *,
    event_type: str,
    decision_output: DecisionOutput,
    session_id: str,
    source: str,
    timestamp: str,
    metadata: dict[str, Any],
    product_id: str | None = None,
    recommended: bool | None = None,
) -> TrackingEvent:
    payload: dict[str, Any] = {
        "event_type": event_type,
        "event_id": str(uuid4()),
        "timestamp": timestamp,
        "query": decision_output.query,
        "selected_brain": decision_output.selected_brain.value,
        "decision_depth": decision_output.decision_depth.value,
        "session_id": session_id,
        "source": source,
        "metadata": metadata,
        "missing_data_states": [state.value for state in decision_output.missing_data_states],
    }
    if product_id is not None:
        payload["product_id"] = product_id
    if recommended is not None:
        payload["recommended"] = recommended
    return TrackingEvent.from_dict(payload)
