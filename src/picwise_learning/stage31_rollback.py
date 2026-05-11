from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Stage31RollbackResult:
    restored_runtime_result: dict[str, Any]
    rollback_applied: bool
    rollback_reason: str
    error_type: str | None = None


def rollback_stage31_runtime_result(
    *,
    original_runtime_result: dict[str, Any],
    rollback_reason: str,
    error: Exception | None = None,
) -> Stage31RollbackResult:
    return Stage31RollbackResult(
        restored_runtime_result=deepcopy(original_runtime_result),
        rollback_applied=True,
        rollback_reason=str(rollback_reason or "stage31_rollback"),
        error_type=error.__class__.__name__ if error is not None else None,
    )
