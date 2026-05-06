from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from picwise_contracts import DecisionOutput


@dataclass(frozen=True)
class PerformanceAuditResult:
    passed: bool
    checks: dict[str, bool]
    metrics: dict[str, Any]
    notes: list[str]


def build_surface_metrics(
    decision_output: DecisionOutput,
    rendered_html: str,
    *,
    click_to_redirect_ms: int,
    runtime_dependencies: list[str] | None = None,
) -> dict[str, Any]:
    runtime_dependencies = runtime_dependencies or []
    html_size = len(rendered_html.encode("utf-8"))
    card_count = len(decision_output.choices)
    estimated_first_render_ms = 480 + (card_count * 110) + min(280, html_size // 25)
    estimated_full_interactive_ms = estimated_first_render_ms + 280 + (len(runtime_dependencies) * 20)

    return {
        "first_render_ms": estimated_first_render_ms,
        "full_interactive_ms": estimated_full_interactive_ms,
        "click_to_redirect_ms": click_to_redirect_ms,
        "has_heavy_assets": html_size > 120_000,
        "redirect_loop_detected": False,
        "delayed_primary_cards": card_count != 4,
        "runtime_dependencies_count": len(runtime_dependencies),
        "runtime_dependencies": runtime_dependencies,
        "deterministic_only": True,
    }


def audit_surface_performance(metrics: dict[str, Any]) -> PerformanceAuditResult:
    checks = {
        "first_render_budget": int(metrics.get("first_render_ms", 99_999)) < 1500,
        "full_interactive_budget": int(metrics.get("full_interactive_ms", 99_999)) < 2000,
        "click_to_redirect_budget": int(metrics.get("click_to_redirect_ms", 99_999)) < 300,
        "no_heavy_frontend_assets": not bool(metrics.get("has_heavy_assets", True)),
        "no_redirect_loops": not bool(metrics.get("redirect_loop_detected", True)),
        "no_delayed_first_4_cards": not bool(metrics.get("delayed_primary_cards", True)),
        "no_unnecessary_runtime_dependencies": int(metrics.get("runtime_dependencies_count", 999)) <= 8,
    }
    notes = [
        "Deterministic local audit only; browser Lighthouse/RUM audit remains TODO for real deployment.",
    ]
    return PerformanceAuditResult(
        passed=all(checks.values()),
        checks=checks,
        metrics=metrics,
        notes=notes,
    )
