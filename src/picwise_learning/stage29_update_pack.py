from __future__ import annotations

import hashlib
from collections import Counter

from .stage29_approval_gate import filter_approved_suggestions
from .stage29_contracts import Stage29LearningSuggestion, Stage29UpdatePack


def build_update_pack(
    suggestions: list[Stage29LearningSuggestion],
    pack_id: str | None = None,
) -> Stage29UpdatePack:
    approved = filter_approved_suggestions(suggestions)
    approved_ids = tuple(row.suggestion_id for row in approved)
    digest = hashlib.sha1("|".join(approved_ids).encode("utf-8")).hexdigest()[:10] if approved_ids else "empty"
    resolved_pack_id = pack_id or f"s29_update_pack_{digest}"
    risk_summary = dict(Counter(row.risk_level for row in approved))
    proposed_changes = tuple(row.suggested_rule_or_mapping for row in approved)
    examples = tuple(example for row in approved for example in row.examples[:1])
    validation_status = "valid" if approved else "no_approved_suggestions"
    return Stage29UpdatePack(
        pack_id=resolved_pack_id,
        approved_suggestion_ids=approved_ids,
        proposed_changes=proposed_changes,
        risk_summary=risk_summary,
        examples=examples,
        rollback_notes="Offline artifact only. Runtime unchanged unless separately reviewed and applied.",
        validation_status=validation_status,
    )
