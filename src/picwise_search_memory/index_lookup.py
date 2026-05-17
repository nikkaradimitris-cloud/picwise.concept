from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .index_contracts import SearchIndex, SearchIndexEntry, SearchIndexLookupResult
from .validation import normalize_term

_LOW_CONFIDENCE_THRESHOLD = 0.72
_MEDIUM_CONFIDENCE_THRESHOLD = 0.84
_HIGH_CONFIDENCE_THRESHOLD = 0.93
_MAX_CANDIDATE_DISTANCE = 3
_PER_TOKEN_DISTANCE_CAP = 2
_BROAD_AMBIGUOUS_TERMS = {"bank", "charger", "apple", "nike", "bosch", "insurance", "loan"}


@dataclass(frozen=True)
class _ScoredCandidate:
    entry: SearchIndexEntry
    score: float
    reason_codes: tuple[str, ...]


def _normalize_query(query: str) -> str:
    return normalize_term(query)


def _token_overlap(a: str, b: str) -> float:
    a_tokens = [token for token in a.split() if token]
    b_tokens = [token for token in b.split() if token]
    if not a_tokens or not b_tokens:
        return 0.0
    matched = 0.0
    for token in a_tokens:
        best = 0.0
        for candidate in b_tokens:
            distance = _levenshtein_distance(token, candidate)
            if distance > _PER_TOKEN_DISTANCE_CAP:
                continue
            max_len = max(len(token), len(candidate), 1)
            similarity = 1.0 - (distance / max_len)
            if similarity > best:
                best = similarity
        if best >= 0.72:
            matched += best
    normalizer = max(len(a_tokens), len(b_tokens), 1)
    return matched / normalizer


@lru_cache(maxsize=5000)
def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            substitution = previous[j - 1] + (0 if ca == cb else 1)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def _to_confidence(score: float) -> str:
    if score >= _HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if score >= _MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    if score >= _LOW_CONFIDENCE_THRESHOLD:
        return "low"
    return "none"


def _score_candidate(query: str, entry: SearchIndexEntry) -> _ScoredCandidate | None:
    normalized_variant = entry.normalized_variant
    query_joined = query.replace(" ", "")
    variant_joined = normalized_variant.replace(" ", "")
    distance = _levenshtein_distance(query_joined, variant_joined)
    allowed_distance = _MAX_CANDIDATE_DISTANCE
    if len(query_joined) >= 10 and len(variant_joined) >= 10:
        allowed_distance = 4
    if distance > allowed_distance and query_joined != variant_joined:
        return None

    max_len = max(len(query_joined), len(variant_joined), 1)
    edit_score = 1.0 - (distance / max_len)
    overlap = _token_overlap(query, normalized_variant)
    score = 0.75 * edit_score + 0.25 * overlap
    reasons: list[str] = ["fuzzy_match"]
    if query_joined == variant_joined and query != normalized_variant:
        reasons.append("joined_words_match")
        score = min(1.0, score + 0.03)
    if "tyre" in query and "tire" in normalized_variant:
        reasons.append("us_uk_spelling_match")
        score = min(1.0, score + 0.02)
    if "tire" in query and "tyre" in normalized_variant:
        reasons.append("us_uk_spelling_match")
        score = min(1.0, score + 0.02)

    return _ScoredCandidate(entry=entry, score=score, reason_codes=tuple(sorted(set(reasons))))


def _canonical_term_similarity(normalized_query: str, entry: SearchIndexEntry) -> float:
    query_joined = normalized_query.replace(" ", "")
    canonical_joined = entry.normalized_term.replace(" ", "")
    max_len = max(len(query_joined), len(canonical_joined), 1)
    distance = _levenshtein_distance(query_joined, canonical_joined)
    if distance > 4:
        return 0.0
    return 1.0 - (distance / max_len)


def _no_match(query: str, normalized_query: str, reason_codes: tuple[str, ...]) -> SearchIndexLookupResult:
    return SearchIndexLookupResult(
        query=query,
        normalized_query=normalized_query,
        status="no_match",
        score=0.0,
        confidence="none",
        matched_entry=None,
        reason_codes=reason_codes,
    )


def lookup_offline_search_index(query: str, index: SearchIndex) -> SearchIndexLookupResult:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return _no_match(query, normalized_query, ("empty_query",))

    if normalized_query in _BROAD_AMBIGUOUS_TERMS:
        return _no_match(query, normalized_query, ("broad_or_ambiguous_query",))

    by_exact = [entry for entry in index.entries if entry.normalized_variant == normalized_query]
    if by_exact:
        best = sorted(
            by_exact,
            key=lambda row: (
                0 if row.variant_type == "exact_canonical" else 1,
                row.mega_category_id,
                row.canonical_id,
                row.index_key,
            ),
        )[0]
        return SearchIndexLookupResult(
            query=query,
            normalized_query=normalized_query,
            status="match",
            score=1.0,
            confidence="high",
            matched_entry=best,
            reason_codes=("exact_normalized_variant_match",),
        )

    candidates: list[_ScoredCandidate] = []
    for entry in index.entries:
        candidate = _score_candidate(normalized_query, entry)
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return _no_match(query, normalized_query, ("no_candidate_found",))

    ranked = sorted(
        candidates,
        key=lambda row: (
            -row.score,
            0 if row.entry.variant_type == "exact_canonical" else 1,
            row.entry.mega_category_id,
            row.entry.canonical_id,
            row.entry.index_key,
        ),
    )
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None

    if best.score < _LOW_CONFIDENCE_THRESHOLD:
        return _no_match(query, normalized_query, ("low_confidence_match",))

    if second and abs(best.score - second.score) <= 0.03:
        if second.entry.canonical_id == best.entry.canonical_id:
            reason_codes = tuple(sorted(set(best.reason_codes + ("same_canonical_cluster",))))
            return SearchIndexLookupResult(
                query=query,
                normalized_query=normalized_query,
                status="match",
                score=round(best.score, 4),
                confidence=_to_confidence(best.score),
                matched_entry=best.entry,
                reason_codes=reason_codes,
            )
        best_canonical_sim = _canonical_term_similarity(normalized_query, best.entry)
        second_canonical_sim = _canonical_term_similarity(normalized_query, second.entry)
        if best_canonical_sim - second_canonical_sim >= 0.08:
            reason_codes = tuple(sorted(set(best.reason_codes + ("canonical_tie_break",))))
            return SearchIndexLookupResult(
                query=query,
                normalized_query=normalized_query,
                status="match",
                score=round(best.score, 4),
                confidence=_to_confidence(best.score),
                matched_entry=best.entry,
                reason_codes=reason_codes,
            )
        return _no_match(query, normalized_query, ("ambiguous_top_candidates",))

    return SearchIndexLookupResult(
        query=query,
        normalized_query=normalized_query,
        status="match",
        score=round(best.score, 4),
        confidence=_to_confidence(best.score),
        matched_entry=best.entry,
        reason_codes=best.reason_codes,
    )
