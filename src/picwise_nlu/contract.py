from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LOCAL_NLU_SOURCE = "local_nlu"
LOCAL_NLU_SCHEMA_VERSION = "1.0.0"

ALLOWED_QUERY_TYPES = {
    "specific_product",
    "general_intent",
    "ambiguous_query",
    "unknown",
}

ALLOWED_STATUSES = {
    "intent_resolved",
    "specific_product_resolved",
    "general_intent_resolved",
    "ambiguous_needs_review",
    "manual_review_required",
    "insufficient_data",
    "no_safe_result",
    "invalid_intent",
}

REVIEW_REQUIRED_STATUSES = {
    "ambiguous_needs_review",
    "manual_review_required",
    "insufficient_data",
    "no_safe_result",
    "invalid_intent",
}


@dataclass(frozen=True)
class LocalNLUIntent:
    raw_query: str
    normalized_query: str | None = None
    query_type: str = "unknown"
    category: str | None = None
    brand_candidates: list[str] = field(default_factory=list)
    model_candidates: list[str] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)
    buying_priority: list[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_review: bool = False
    status: str = "intent_resolved"
    reason_codes: list[str] = field(default_factory=list)
    source: str = LOCAL_NLU_SOURCE
    schema_version: str = LOCAL_NLU_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "normalized_query": self.normalized_query,
            "query_type": self.query_type,
            "category": self.category,
            "brand_candidates": list(self.brand_candidates),
            "model_candidates": list(self.model_candidates),
            "specs": dict(self.specs),
            "buying_priority": list(self.buying_priority),
            "confidence": float(self.confidence),
            "needs_review": bool(self.needs_review),
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "source": self.source,
            "schema_version": self.schema_version,
        }
