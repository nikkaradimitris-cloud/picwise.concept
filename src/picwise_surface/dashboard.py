from __future__ import annotations

from typing import Any

from picwise_contracts import DecisionOutput, RedirectEvent, TrackingEvent

CANONICAL_MISSING_DATA_ENUM = {
    "not_connected",
    "data_not_yet",
    "not_applicable",
    "unknown",
}


def build_dashboard_compatibility_payload(
    decision_output: DecisionOutput,
    *,
    tracking_events: list[TrackingEvent] | None = None,
    redirect_event: RedirectEvent | None = None,
    speed_metrics: dict[str, Any] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    tracking_events = tracking_events or []
    speed_metrics = speed_metrics or {}
    errors = errors or []
    shown_products = [choice.product_id for choice in decision_output.choices]
    recommended = decision_output.recommended_product_id

    clicks = [event for event in tracking_events if event.event_type.value in {"cta_click", "recommended_click", "non_recommended_click"}]
    redirects = [
        event
        for event in tracking_events
        if event.event_type.value in {"redirect_attempt", "redirect_success", "redirect_failure"}
    ]
    if redirect_event is not None:
        redirects_count = len(redirects) + 1
    else:
        redirects_count = len(redirects)

    return {
        "schema_version": "v1_local_surface",
        "query": decision_output.query,
        "selected_brain": decision_output.selected_brain.value,
        "decision_depth": decision_output.decision_depth.value,
        "shown_products": shown_products,
        "recommended_product": recommended,
        "clicks": len(clicks),
        "redirects": redirects_count,
        "speed_metrics": {
            "first_render_ms": speed_metrics.get("first_render_ms", "data_not_yet"),
            "full_interactive_ms": speed_metrics.get("full_interactive_ms", "data_not_yet"),
            "click_to_redirect_ms": speed_metrics.get("click_to_redirect_ms", "data_not_yet"),
        },
        "errors": errors if errors else "not_applicable",
        "conversion_tracking": {"status": "not_connected", "value": None},
        "revenue_tracking": {"status": "not_connected", "value": None},
        "subby_channel": {"status": "not_connected"},
        "missing_data_states": _normalize_missing_data_states(
            [state.value for state in decision_output.missing_data_states]
        ),
    }


def _normalize_missing_data_states(states: list[str]) -> list[str]:
    normalized = []
    for state in states:
        if state in CANONICAL_MISSING_DATA_ENUM:
            normalized.append(state)
        else:
            normalized.append("unknown")
    if not normalized:
        return ["unknown"]
    return normalized
