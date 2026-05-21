from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from picwise_search_memory import (
    build_canonical_vocabulary_registry,
    build_offline_search_index,
    lookup_offline_search_index,
)
from picwise_search_memory.index_contracts import SearchIndex

_LOW_CONFIDENCE_SCORE = 0.75
_AMBIGUOUS_REASON_MARKERS = ("ambiguous", "collision", "shared_taxonomy")
_LOW_CONFIDENCE_REASON_MARKERS = ("low_confidence",)

_CACHED_OFFLINE_INDEX: SearchIndex | None = None


def _is_empty_lookup_query(query: str) -> bool:
    return not " ".join(str(query or "").split()).strip()


def _empty_index_resolver_result() -> IndexResolverResult:
    return IndexResolverResult(
        status="no_match",
        canonical_id=None,
        canonical_term=None,
        normalized_term=None,
        mega_category_id=None,
        confidence=0.0,
        score=0.0,
        reason_codes=("empty_query",),
    )


@dataclass(frozen=True)
class IndexResolverResult:
    status: str
    canonical_id: str | None
    canonical_term: str | None
    normalized_term: str | None
    mega_category_id: str | None
    confidence: float
    score: float
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "canonical_id": self.canonical_id,
            "canonical_term": self.canonical_term,
            "normalized_term": self.normalized_term,
            "mega_category_id": self.mega_category_id,
            "confidence": self.confidence,
            "score": self.score,
            "reason_codes": list(self.reason_codes),
        }


def _cached_offline_index() -> SearchIndex:
    global _CACHED_OFFLINE_INDEX
    if _CACHED_OFFLINE_INDEX is None:
        registry = build_canonical_vocabulary_registry()
        _CACHED_OFFLINE_INDEX = build_offline_search_index(registry=registry)
    return _CACHED_OFFLINE_INDEX


def _map_lookup_status(*, lookup_status: str, score: float, reason_codes: tuple[str, ...]) -> str:
    lowered_reasons = tuple(code.lower() for code in reason_codes)
    if lookup_status != "match":
        if any(marker in code for marker in _AMBIGUOUS_REASON_MARKERS for code in lowered_reasons):
            return "ambiguous"
        if any(marker in code for marker in _LOW_CONFIDENCE_REASON_MARKERS for code in lowered_reasons):
            return "low_confidence"
        return "no_match"
    if score < _LOW_CONFIDENCE_SCORE:
        return "low_confidence"
    if any(marker in code for marker in _AMBIGUOUS_REASON_MARKERS for code in lowered_reasons):
        return "ambiguous"
    return "matched"


def _confidence_to_float(confidence: str, score: float) -> float:
    if confidence == "high":
        return 0.95
    if confidence == "medium":
        return 0.86
    if confidence == "low":
        return 0.74
    return max(0.0, min(score, 1.0))


def resolve_query_with_search_index(query: str) -> IndexResolverResult:
    if _is_empty_lookup_query(query):
        return _empty_index_resolver_result()

    lookup = lookup_offline_search_index(query, _cached_offline_index())
    reason_codes = tuple(sorted({str(code).strip() for code in lookup.reason_codes if str(code).strip()}))
    score = round(float(lookup.score), 4)
    mapped_status = _map_lookup_status(
        lookup_status=str(lookup.status),
        score=score,
        reason_codes=reason_codes,
    )
    matched_entry = lookup.matched_entry
    return IndexResolverResult(
        status=mapped_status,
        canonical_id=matched_entry.canonical_id if matched_entry else None,
        canonical_term=matched_entry.canonical_term if matched_entry else None,
        normalized_term=matched_entry.normalized_term if matched_entry else None,
        mega_category_id=matched_entry.mega_category_id if matched_entry else None,
        confidence=_confidence_to_float(str(lookup.confidence), score),
        score=score,
        reason_codes=reason_codes,
    )
