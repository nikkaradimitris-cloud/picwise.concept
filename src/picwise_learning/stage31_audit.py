from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from .stage31_contracts import Stage31ActivationCandidate, Stage31AuditRecord


def build_stage31_audit_record(candidate: Stage31ActivationCandidate) -> Stage31AuditRecord:
    return Stage31AuditRecord(
        candidate_id=candidate.candidate_id,
        activation_status=candidate.activation_status,
        activation_reason=candidate.activation_reason,
        vertical=candidate.vertical,
        risk_level=candidate.risk_level,
        block_reasons=tuple(candidate.block_reasons),
        did_affect_runtime=bool(candidate.did_affect_runtime),
        source_shadow_record_id=candidate.source_shadow_record_id,
        metadata=dict(candidate.metadata),
    )


class Stage31AuditLog:
    def __init__(self, max_records: int = 5000) -> None:
        self._records: deque[Stage31AuditRecord] = deque(maxlen=max(1, max_records))

    def append_candidate(self, candidate: Stage31ActivationCandidate) -> Stage31AuditRecord:
        record = build_stage31_audit_record(candidate)
        self._records.append(record)
        return record

    def extend_records(self, records: Iterable[Stage31AuditRecord]) -> None:
        for record in records:
            self._records.append(record)

    def get_records(self) -> tuple[Stage31AuditRecord, ...]:
        return tuple(self._records)
