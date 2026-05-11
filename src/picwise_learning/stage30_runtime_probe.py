from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Any

from .stage30_config import Stage30ShadowConfig, build_default_stage30_config
from .stage30_contracts import Stage30FailureCandidate, Stage30ShadowRecord, Stage30ShadowSummary
from .stage30_failure_bridge import build_failure_candidates
from .stage30_shadow_runner import Stage30ShadowRunner
from .stage30_summary import build_shadow_summary


class Stage30RuntimeProbe:
    def __init__(
        self,
        *,
        runner: Stage30ShadowRunner | None = None,
        config: Stage30ShadowConfig | None = None,
    ) -> None:
        self._config = config or build_default_stage30_config()
        self._runner = runner or Stage30ShadowRunner(self._config)
        self._records: deque[Stage30ShadowRecord] = deque(maxlen=max(1, self._config.max_records))

    def observe_runtime_decision(
        self,
        *,
        runtime_query: str,
        runtime_decision: dict[str, Any],
        source_surface: str | None = None,
        source_route: str | None = None,
    ) -> Stage30ShadowRecord | None:
        if not self._config.enabled:
            return None
        record = self._runner.run_shadow(
            runtime_query=runtime_query,
            runtime_decision=runtime_decision,
            source_surface=source_surface,
            source_route=source_route,
        )
        self._records.append(record)
        return record

    def get_shadow_records(self) -> tuple[Stage30ShadowRecord, ...]:
        return tuple(self._records)

    def build_failure_candidates(self) -> list[Stage30FailureCandidate]:
        return build_failure_candidates(self._records)

    def build_summary(self) -> Stage30ShadowSummary:
        return build_shadow_summary(self._records)

    def extend_records(self, records: Iterable[Stage30ShadowRecord]) -> None:
        for record in records:
            self._records.append(record)


def build_default_stage30_runtime_probe() -> Stage30RuntimeProbe:
    return Stage30RuntimeProbe()
