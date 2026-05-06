from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

from picwise_contracts import ContractValidationError, DecisionOutput
from picwise_surface import RedirectPreparation, prepare_redirect_tracking


@dataclass(frozen=True)
class RedirectResolution:
    selected_product_id: str
    selected_provider: str
    is_recommended: bool
    original_target: str
    resolved_target: str
    tracking_payload: RedirectPreparation
    mode: str
    budget_ms: int


def resolve_redirect(
    decision_output: DecisionOutput,
    *,
    selected_product_id: str,
    session_id: str,
    click_to_redirect_budget_ms: int,
    local_safe_mode: bool = True,
) -> RedirectResolution:
    if click_to_redirect_budget_ms >= 300:
        raise ContractValidationError("Redirect budget must remain < 300ms.")
    if not session_id.strip():
        raise ContractValidationError("session_id is required for redirect tracking payloads.")

    choice = _find_choice(decision_output, selected_product_id)
    _validate_redirect_target(choice.redirect_target)
    tracking_payload = prepare_redirect_tracking(
        decision_output=decision_output,
        selected_product_id=selected_product_id,
        session_id=session_id,
        click_to_redirect_budget_ms=click_to_redirect_budget_ms,
    )
    resolved_target = (
        _build_local_safe_target(choice.redirect_target)
        if local_safe_mode
        else choice.redirect_target
    )
    return RedirectResolution(
        selected_product_id=choice.product_id,
        selected_provider=choice.merchant_or_provider,
        is_recommended=choice.is_recommended,
        original_target=choice.redirect_target,
        resolved_target=resolved_target,
        tracking_payload=tracking_payload,
        mode="local_safe" if local_safe_mode else "direct",
        budget_ms=click_to_redirect_budget_ms,
    )


def build_redirect_tracking_payload(resolution: RedirectResolution) -> dict[str, Any]:
    return {
        "selected_product_id": resolution.selected_product_id,
        "selected_provider": resolution.selected_provider,
        "recommended": resolution.is_recommended,
        "mode": resolution.mode,
        "resolved_target": resolution.resolved_target,
        "budget_ms": resolution.budget_ms,
        "cta_click_event_id": resolution.tracking_payload.cta_click_event.event_id,
        "click_kind_event_id": resolution.tracking_payload.click_kind_event.event_id,
        "redirect_attempt_event_id": resolution.tracking_payload.redirect_attempt_event.event_id,
        "redirect_event_id": resolution.tracking_payload.redirect_event.event_id,
        "contains_conversion_data": False,
        "contains_revenue_data": False,
    }


def _build_local_safe_target(target_url: str) -> str:
    return f"/local-safe-redirect?target={quote(target_url, safe='')}"


def _validate_redirect_target(target_url: str) -> None:
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"}:
        raise ContractValidationError("Redirect target must use http/https scheme.")
    if not parsed.netloc:
        raise ContractValidationError("Redirect target must include network location.")


def _find_choice(decision_output: DecisionOutput, selected_product_id: str):
    all_choices = list(decision_output.choices) + list(decision_output.more_choices or [])
    for choice in all_choices:
        if choice.product_id == selected_product_id:
            return choice
    raise ContractValidationError("Selected product/provider does not exist in decision output.")
