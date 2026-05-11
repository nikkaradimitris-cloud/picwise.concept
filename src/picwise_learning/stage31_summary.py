from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .stage31_contracts import Stage31ActivationSummary, Stage31AuditRecord


def build_stage31_activation_summary(records: Iterable[Stage31AuditRecord]) -> Stage31ActivationSummary:
    rows = list(records)
    statuses = Counter(record.activation_status for record in rows)
    by_vertical = Counter(record.vertical for record in rows)
    by_risk_level = Counter(record.risk_level for record in rows)
    by_block_reason = Counter(reason for record in rows for reason in record.block_reasons)
    return Stage31ActivationSummary(
        total_candidates=len(rows),
        eligible=statuses.get("eligible", 0),
        activated=statuses.get("activated", 0),
        blocked=statuses.get("blocked", 0),
        manual_review=statuses.get("manual_review", 0),
        unsupported=statuses.get("unsupported", 0),
        rollback=statuses.get("rollback", 0),
        disabled=statuses.get("disabled", 0),
        by_vertical=dict(by_vertical),
        by_block_reason=dict(by_block_reason),
        by_risk_level=dict(by_risk_level),
    )
