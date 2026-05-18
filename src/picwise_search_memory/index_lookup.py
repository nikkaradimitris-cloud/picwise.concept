from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .index_contracts import SearchIndex, SearchIndexEntry, SearchIndexLookupResult
from .validation import normalize_term

_LOW_CONFIDENCE_THRESHOLD = 0.72
_MEDIUM_CONFIDENCE_THRESHOLD = 0.84
_HIGH_CONFIDENCE_THRESHOLD = 0.93
_SINGLE_TOKEN_CANONICAL_ACCEPT_THRESHOLD = 0.90
_SINGLE_TOKEN_GENERATED_ACCEPT_THRESHOLD = 0.84
_MAX_CANDIDATE_DISTANCE = 3
_PER_TOKEN_DISTANCE_CAP = 2
_EXACT_COLLISION_RECOVERY_MIN_SCORE = 0.82
_EXACT_COLLISION_RECOVERY_MARGIN = 0.12
_BROAD_AMBIGUOUS_TERMS = {"bank", "charger", "apple", "nike", "bosch", "insurance", "loan", "erp", "crm", "accounting software"}
_SINGLE_TOKEN_REJECT_TERMS = {
    "bank",
    "charger",
    "apple",
    "nike",
    "bosch",
    "insurance",
    "loan",
    "erp",
    "crm",
    "accounting",
    "software",
}
_SINGLE_TOKEN_ACCEPTABLE_CANONICAL_SOURCES = {
    "taxonomy_bridge",
    "offline_canonical_vocabulary_coverage",
    "taxonomy_clean_vocabulary",
}
_SINGLE_TOKEN_ACCEPTABLE_CANONICAL_STATUSES = {
    "active",
    "offline_source_only",
}
_VARIANT_TYPE_PRIORITY = {
    "exact_canonical": 0,
    "joined_words": 1,
    "missing_letter": 2,
    "swapped_adjacent_letters": 3,
    "repeated_letter": 4,
    "vowel_drop": 5,
    "extra_letter": 6,
    "us_uk_spelling": 7,
    "generated": 8,
}


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


def _collision_severity(entry: SearchIndexEntry) -> int:
    score = 0
    if "cross_category_collision" in entry.quality_flags:
        score += 2
    if "exact_variant_collision" in entry.quality_flags:
        score += 1
    return score


def _specificity_score(entry: SearchIndexEntry) -> float:
    # Prefer entries that have richer lexical signal and match canonical form.
    token_specificity = min(entry.token_count, 5) / 5.0
    canonical_alignment = _canonical_term_similarity(entry.normalized_variant, entry)
    return 0.55 * token_specificity + 0.45 * canonical_alignment


def _variant_priority(variant_type: str) -> int:
    return _VARIANT_TYPE_PRIORITY.get(variant_type, 99)


def _query_specificity(query: str) -> float:
    tokens = [token for token in query.split() if token]
    if not tokens:
        return 0.0
    token_count_signal = min(len(tokens), 4) / 4.0
    avg_token_length = sum(len(token) for token in tokens) / len(tokens)
    token_length_signal = min(avg_token_length, 10.0) / 10.0
    long_token_signal = min(sum(1 for token in tokens if len(token) >= 6), 2) / 2.0
    return 0.45 * token_count_signal + 0.35 * token_length_signal + 0.20 * long_token_signal


def _canonical_specificity(entry: SearchIndexEntry) -> float:
    canonical_tokens = [token for token in entry.normalized_term.split() if token]
    if not canonical_tokens:
        return 0.0
    token_count_signal = min(len(canonical_tokens), 4) / 4.0
    avg_token_length = sum(len(token) for token in canonical_tokens) / len(canonical_tokens)
    token_length_signal = min(avg_token_length, 10.0) / 10.0
    overlap_signal = _token_overlap(entry.normalized_variant, entry.normalized_term)
    return 0.40 * token_count_signal + 0.30 * token_length_signal + 0.30 * overlap_signal


def _single_token_query_gate(normalized_query: str) -> tuple[bool, str]:
    tokens = [token for token in normalized_query.split() if token]
    if len(tokens) != 1:
        return False, ""
    token = tokens[0]
    if token in _SINGLE_TOKEN_REJECT_TERMS:
        return True, "single_token_broad_or_unsafe"
    if len(token) < 3:
        return True, "single_token_too_short"
    return False, ""


def _single_token_candidate_score(normalized_query: str, candidate: _ScoredCandidate) -> float:
    entry = candidate.entry
    lexical_score = candidate.score
    canonical_overlap = _token_overlap(normalized_query, entry.normalized_term)
    canonical_similarity = _canonical_term_similarity(normalized_query, entry)
    source_strength = 1.0 if entry.canonical_source in _SINGLE_TOKEN_ACCEPTABLE_CANONICAL_SOURCES else 0.0
    status_strength = 1.0 if entry.canonical_status in _SINGLE_TOKEN_ACCEPTABLE_CANONICAL_STATUSES else 0.0
    canonical_variant_bonus = 0.03 if entry.variant_type == "exact_canonical" else 0.0
    generated_variant_penalty = 0.0
    collision_penalty = min(_collision_severity(entry) * 0.16, 0.35)
    score = (
        0.55 * lexical_score
        + 0.20 * canonical_overlap
        + 0.15 * canonical_similarity
        + 0.10 * source_strength
        + 0.05 * status_strength
        + canonical_variant_bonus
        - generated_variant_penalty
        - collision_penalty
    )
    return max(0.0, min(score, 1.0))


def _resolve_single_token_fuzzy(
    query: str, normalized_query: str, candidates: list[_ScoredCandidate]
) -> SearchIndexLookupResult | None:
    scored = sorted(
        [
            (
                _single_token_candidate_score(normalized_query, row),
                row,
            )
            for row in candidates
            if row.entry.canonical_source in _SINGLE_TOKEN_ACCEPTABLE_CANONICAL_SOURCES
            and row.entry.canonical_status in _SINGLE_TOKEN_ACCEPTABLE_CANONICAL_STATUSES
        ],
        key=lambda row: (
            -row[0],
            _collision_severity(row[1].entry),
            _variant_priority(row[1].entry.variant_type),
            row[1].entry.mega_category_id,
            row[1].entry.canonical_id,
            row[1].entry.index_key,
        ),
    )
    if not scored:
        return _no_match(query, normalized_query, ("single_token_no_provenance_backed_candidate",))

    best_score, best_candidate = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else None
    threshold = (
        _SINGLE_TOKEN_CANONICAL_ACCEPT_THRESHOLD
        if best_candidate.entry.variant_type == "exact_canonical"
        else _SINGLE_TOKEN_GENERATED_ACCEPT_THRESHOLD
    )
    if best_score < threshold:
        return _no_match(query, normalized_query, ("single_token_low_confidence",))
    if second_score is not None and abs(best_score - second_score) < 0.05:
        if scored[1][1].entry.mega_category_id != best_candidate.entry.mega_category_id:
            return _no_match(query, normalized_query, ("single_token_cross_category_collision",))
        if scored[1][1].entry.canonical_id != best_candidate.entry.canonical_id:
            return _no_match(query, normalized_query, ("single_token_ambiguous_canonical_collision",))

    reason = (
        "single_token_exact_canonical_safe_match"
        if best_candidate.entry.variant_type == "exact_canonical"
        else "single_token_generated_variant_safe_match"
    )
    reason_codes = tuple(sorted(set(best_candidate.reason_codes + (reason,))))
    return SearchIndexLookupResult(
        query=query,
        normalized_query=normalized_query,
        status="match",
        score=round(best_score, 4),
        confidence=_to_confidence(max(best_score, _LOW_CONFIDENCE_THRESHOLD)),
        matched_entry=best_candidate.entry,
        reason_codes=reason_codes,
    )


def _is_overly_generic_collision(normalized_query: str, entries: list[SearchIndexEntry]) -> bool:
    categories = {entry.mega_category_id for entry in entries}
    canonical_terms = {entry.normalized_term for entry in entries}
    query_tokens = [token for token in normalized_query.split() if token]
    query_specificity = _query_specificity(normalized_query)

    # Shared taxonomy/source/meta-like terms are too ambiguous to recover safely.
    if len(categories) >= 3 and len(canonical_terms) == 1:
        return True
    if len(categories) >= 4 and len(query_tokens) <= 2:
        return True
    if len(categories) >= 2 and len(query_tokens) <= 1 and len(normalized_query) <= 7:
        return True
    if len(categories) >= 2 and query_specificity < 0.42:
        return True
    return False


def _exact_collision_candidate_score(normalized_query: str, entry: SearchIndexEntry) -> float:
    query_to_variant_overlap = _token_overlap(normalized_query, entry.normalized_variant)
    query_to_canonical_overlap = _token_overlap(normalized_query, entry.normalized_term)
    canonical_similarity = _canonical_term_similarity(normalized_query, entry)
    canonical_specificity = _canonical_specificity(entry)
    variant_quality = max(0.0, 1.0 - (_variant_priority(entry.variant_type) / 10.0))
    collision_penalty = min(_collision_severity(entry) * 0.18, 0.45)
    category_consistency = 1.0 if entry.mega_category_id else 0.0
    exact_phrase_quality = 1.0 if entry.normalized_term == normalized_query else 0.0
    normalized_quality = _query_specificity(normalized_query)

    score = (
        0.22 * query_to_variant_overlap
        + 0.22 * query_to_canonical_overlap
        + 0.16 * canonical_similarity
        + 0.16 * canonical_specificity
        + 0.10 * variant_quality
        + 0.07 * category_consistency
        + 0.05 * exact_phrase_quality
        + 0.02 * normalized_quality
        - collision_penalty
    )
    return max(0.0, min(score, 1.0))


def _recover_exact_collision(entries: list[SearchIndexEntry], normalized_query: str) -> _ScoredCandidate | None:
    if _is_overly_generic_collision(normalized_query, entries):
        return None

    scored = sorted(
        [
            _ScoredCandidate(
                entry=entry,
                score=_exact_collision_candidate_score(normalized_query, entry),
                reason_codes=("exact_collision_specificity_scored",),
            )
            for entry in entries
        ],
        key=lambda row: (
            -row.score,
            _collision_severity(row.entry),
            _variant_priority(row.entry.variant_type),
            -_specificity_score(row.entry),
            row.entry.mega_category_id,
            row.entry.canonical_id,
            row.entry.index_key,
        ),
    )
    if not scored:
        return None
    best = scored[0]
    second = scored[1] if len(scored) > 1 else None
    if best.score < _EXACT_COLLISION_RECOVERY_MIN_SCORE:
        return None
    if second and (best.score - second.score) < _EXACT_COLLISION_RECOVERY_MARGIN:
        return None
    return _ScoredCandidate(
        entry=best.entry,
        score=best.score,
        reason_codes=("exact_collision_specificity_recovery",),
    )


def _prefer_deterministic_exact(entries: list[SearchIndexEntry], normalized_query: str) -> SearchIndexEntry | None:
    best = sorted(
        entries,
        key=lambda row: (
            _collision_severity(row),
            _variant_priority(row.variant_type),
            -_specificity_score(row),
            row.mega_category_id,
            row.canonical_id,
            row.index_key,
        ),
    )[0]
    tied = [
        row
        for row in entries
        if (
            _collision_severity(row),
            _variant_priority(row.variant_type),
            round(_specificity_score(row), 5),
        )
        == (
            _collision_severity(best),
            _variant_priority(best.variant_type),
            round(_specificity_score(best), 5),
        )
    ]
    if len(tied) > 1:
        return None
    # Guard broad single token terms when collided.
    if normalized_query in _BROAD_AMBIGUOUS_TERMS and _collision_severity(best) > 0:
        return None
    return best


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

    single_token_guarded, single_token_guard_reason = _single_token_query_gate(normalized_query)
    if single_token_guarded:
        return _no_match(query, normalized_query, (single_token_guard_reason,))

    by_exact = [entry for entry in index.entries if entry.normalized_variant == normalized_query]
    if by_exact:
        canonical_ids = {entry.canonical_id for entry in by_exact}
        category_ids = {entry.mega_category_id for entry in by_exact}
        has_collision = len(canonical_ids) > 1 or len(category_ids) > 1
        if has_collision:
            deterministic = _prefer_deterministic_exact(by_exact, normalized_query)
            if deterministic is not None:
                return SearchIndexLookupResult(
                    query=query,
                    normalized_query=normalized_query,
                    status="match",
                    score=0.96,
                    confidence="high",
                    matched_entry=deterministic,
                    reason_codes=("exact_collision_disambiguated",),
                )

            recovered = _recover_exact_collision(by_exact, normalized_query)
            if recovered is None:
                if _is_overly_generic_collision(normalized_query, by_exact):
                    return _no_match(query, normalized_query, ("shared_taxonomy_or_meta_term", "cross_category_exact_collision"))
                reason = "cross_category_exact_collision" if len(category_ids) > 1 else "ambiguous_exact_collision"
                return _no_match(query, normalized_query, (reason,))
            return SearchIndexLookupResult(
                query=query,
                normalized_query=normalized_query,
                status="match",
                score=round(max(recovered.score, 0.84), 4),
                confidence=_to_confidence(max(recovered.score, _LOW_CONFIDENCE_THRESHOLD)),
                matched_entry=recovered.entry,
                reason_codes=recovered.reason_codes,
            )
        best = _prefer_deterministic_exact(by_exact, normalized_query) or by_exact[0]
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

    if len(normalized_query.split()) == 1:
        return _resolve_single_token_fuzzy(query, normalized_query, ranked)

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
