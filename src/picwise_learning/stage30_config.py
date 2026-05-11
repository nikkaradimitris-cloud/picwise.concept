from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stage30ShadowConfig:
    enabled: bool = True
    max_records: int = 5000
    source_surface_default: str = "runtime_app"
    source_route_default: str = "/demo"
    regulated_verticals: tuple[str, ...] = ("finance_insurance_business_finance",)
    unsupported_verticals: tuple[str, ...] = ()
    unknown_target_markers: tuple[str, ...] = (
        "",
        "unknown",
        "unavailable:not_supported",
        "unavailable:not_connected",
        "unavailable",
    )
    metadata: dict[str, str] = field(default_factory=dict)


def build_default_stage30_config() -> Stage30ShadowConfig:
    return Stage30ShadowConfig()
