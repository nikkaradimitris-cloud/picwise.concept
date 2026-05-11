from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .stage30_contracts import Stage30ShadowRecord, Stage30ShadowSummary


def build_shadow_summary(records: Iterable[Stage30ShadowRecord]) -> Stage30ShadowSummary:
    rows = list(records)
    statuses = Counter(record.comparison_status for record in rows)
    verticals = Counter(record.vertical for record in rows)
    languages = Counter(record.language for record in rows)
    noise_signals = Counter(signal for record in rows for signal in record.noise_signals)
    failure_types = Counter(record.failure_type for record in rows if record.failure_type)
    return Stage30ShadowSummary(
        total_shadow_records=len(rows),
        aligned_count=statuses.get("aligned", 0),
        disagreement_count=statuses.get("disagreement", 0),
        runtime_unknown_count=statuses.get("runtime_unknown", 0),
        shadow_unknown_count=statuses.get("shadow_unknown", 0),
        manual_review_count=statuses.get("manual_review", 0),
        unsupported_count=statuses.get("unsupported", 0),
        by_vertical=dict(verticals),
        by_language=dict(languages),
        by_noise_signal=dict(noise_signals),
        top_failure_types=tuple(failure_types.most_common(5)),
    )
