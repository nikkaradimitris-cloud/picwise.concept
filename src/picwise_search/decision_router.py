from __future__ import annotations

from dataclasses import dataclass
import re


RouteType = str

_DEFAULT_CONFIDENCE = 0.5
_MIN_QUERY_LENGTH = 3
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "for",
        "to",
        "and",
        "or",
        "with",
        "of",
        "σε",
        "για",
        "και",
        "το",
        "τα",
        "να",
    }
)
_MEANINGLESS_TOKENS = frozenset({"?", ".", "-", "_", "x", "xx", "test", "none", "n/a"})
_GENERAL_INTENT_TERMS = frozenset(
    {
        "best",
        "cheap",
        "budget",
        "top",
        "for",
        "under",
        "need",
        "needs",
        "gift",
        "travel",
        "office",
        "school",
        "home",
        "daily",
        "compare",
        "comparison",
        "guide",
        "versus",
        "vs",
        "for",
        "για",
        "καλύτερο",
        "καλυτερο",
        "καλύτερα",
        "ανάγκη",
        "αναγκη",
        "ταξί",
        "ταξι",
    }
)
_CONFLICT_TERMS = frozenset({"vs", "versus", "or", "compare", "between"})

_SIZE_REGEX = re.compile(r"\b\d{3}/\d{2}(?:\s*r\d{2}|/\d{2})\b", flags=re.IGNORECASE)
_STRICT_SIZE_REGEX = re.compile(r"\b\d{3}/\d{2}\s*r\d{2}\b", flags=re.IGNORECASE)
_MALFORMED_SIZE_REGEX = re.compile(r"\b\d{3}/\d{2}/\d{2}\b", flags=re.IGNORECASE)
_STORAGE_SPEC_REGEX = re.compile(r"\b\d+(?:\.\d+)?\s?(?:gb|tb|mb|mah|wh)\b", flags=re.IGNORECASE)
_DIMENSION_SPEC_REGEX = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:mm|cm|m|inch|in|kg|g|w|kw|hz|mhz)\b",
    flags=re.IGNORECASE,
)
_MODEL_CODE_REGEX = re.compile(r"\b(?!r\d+\b)[a-z]{1,6}[-]?\d{2,}[a-z0-9-]*\b", flags=re.IGNORECASE)
_SPACE_REGEX = re.compile(r"\s+")
_TOKEN_REGEX = re.compile(r"[^\w]+", flags=re.UNICODE)
_LATIN_ALPHA_REGEX = re.compile(r"^[a-z]+$")
_MODEL_TOKEN_REGEX = re.compile(r"^(?!r\d+$)(?=.*[a-z])(?=.*\d)[a-z0-9-]+$", flags=re.IGNORECASE)
_STORAGE_TOKEN_REGEX = re.compile(r"^\d+(?:\.\d+)?(?:gb|tb|mb|mah|wh)$", flags=re.IGNORECASE)


@dataclass(frozen=True)
class SearchDecision:
    query: str
    normalized_query: str
    route_type: str
    status: str
    result_mode: str
    public_allowed: bool
    indexable_allowed: bool
    sitemap_allowed: bool
    reason_codes: tuple[str, ...]
    confidence: float

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "route_type": self.route_type,
            "status": self.status,
            "result_mode": self.result_mode,
            "public_allowed": self.public_allowed,
            "indexable_allowed": self.indexable_allowed,
            "sitemap_allowed": self.sitemap_allowed,
            "reason_codes": list(self.reason_codes),
            "confidence": self.confidence,
        }


def _normalize_query(query: str) -> str:
    lowered = str(query or "").strip().lower()
    lowered = _SPACE_REGEX.sub(" ", lowered)
    return lowered


def _tokenize(normalized_query: str) -> list[str]:
    if not normalized_query:
        return []
    return [token for token in _TOKEN_REGEX.split(normalized_query) if token]


def _is_meaningless_query(normalized_query: str, tokens: list[str]) -> bool:
    if not normalized_query:
        return True
    if len(normalized_query) < _MIN_QUERY_LENGTH:
        return True
    if all(token in _STOPWORDS or token in _MEANINGLESS_TOKENS for token in tokens):
        return True
    has_alnum = any(char.isalnum() for char in normalized_query)
    return not has_alnum


def _concrete_tokens(tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in _STOPWORDS and token not in _MEANINGLESS_TOKENS]


def _count_model_like_tokens(tokens: list[str]) -> int:
    return sum(1 for token in tokens if _MODEL_TOKEN_REGEX.match(token) and not _STORAGE_TOKEN_REGEX.match(token))


def _count_descriptive_latin_tokens(tokens: list[str]) -> int:
    return sum(
        1
        for token in tokens
        if len(token) >= 4 and _LATIN_ALPHA_REGEX.match(token) and token not in _GENERAL_INTENT_TERMS
    )


def _count_numeric_tokens(tokens: list[str]) -> int:
    return sum(1 for token in tokens if any(char.isdigit() for char in token))


def _product_signal_score(tokens: list[str], normalized_query: str) -> int:
    score = 0
    if _STRICT_SIZE_REGEX.search(normalized_query):
        score += 2
    if _STORAGE_SPEC_REGEX.search(normalized_query):
        score += 2
    if _DIMENSION_SPEC_REGEX.search(normalized_query):
        score += 1
    if _MODEL_CODE_REGEX.search(normalized_query):
        score += 2
    if _count_model_like_tokens(tokens) >= 1:
        score += 1
    if _count_descriptive_latin_tokens(tokens) >= 2:
        score += 2
    return score


def _is_ambiguous(tokens: list[str], normalized_query: str) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    concrete = _concrete_tokens(tokens)
    token_set = set(concrete)
    token_set_all = set(tokens)
    if _MALFORMED_SIZE_REGEX.search(normalized_query):
        reasons.append("malformed_spec_pattern")
    if token_set_all & _CONFLICT_TERMS:
        reasons.append("conflicting_intent_signals")
    if "??" in normalized_query or "!!" in normalized_query:
        reasons.append("query_noise_detected")
    score = _product_signal_score(concrete, normalized_query)
    has_any_spec = bool(
        _SIZE_REGEX.search(normalized_query)
        or _STORAGE_SPEC_REGEX.search(normalized_query)
        or _DIMENSION_SPEC_REGEX.search(normalized_query)
        or _MODEL_CODE_REGEX.search(normalized_query)
    )
    if (
        has_any_spec
        and score <= 2
        and len(concrete) <= 3
        and not (token_set & _GENERAL_INTENT_TERMS)
    ):
        reasons.append("low_confidence_product_identity")
    return bool(reasons), tuple(reasons)


def _is_specific_product(tokens: list[str], normalized_query: str) -> bool:
    concrete = _concrete_tokens(tokens)
    if len(concrete) < 3:
        return False
    score = _product_signal_score(concrete, normalized_query)
    descriptive_count = _count_descriptive_latin_tokens(concrete)
    has_strict_size = bool(_STRICT_SIZE_REGEX.search(normalized_query))
    has_model_code = bool(_MODEL_CODE_REGEX.search(normalized_query))
    has_model_like_token = _count_model_like_tokens(concrete) >= 1
    numeric_token_count = _count_numeric_tokens(concrete)
    has_identity_anchor = bool(
        has_model_code
        or has_model_like_token
        or (has_strict_size and descriptive_count >= 2)
        or (numeric_token_count >= 2 and descriptive_count >= 1)
    )
    has_general_intent_language = bool(set(concrete) & _GENERAL_INTENT_TERMS)
    has_any_spec = bool(
        _SIZE_REGEX.search(normalized_query)
        or _STORAGE_SPEC_REGEX.search(normalized_query)
        or _DIMENSION_SPEC_REGEX.search(normalized_query)
        or _MODEL_CODE_REGEX.search(normalized_query)
    )
    has_numeric_identity_combo = numeric_token_count >= 2 and descriptive_count >= 1
    return (
        (score >= 3 or has_numeric_identity_combo)
        and has_any_spec
        and has_identity_anchor
        and not (has_general_intent_language and not has_model_code and not has_strict_size)
    )


def _safe_no_result_decision(
    *,
    query: str,
    normalized_query: str,
    status: str,
    reasons: tuple[str, ...],
    confidence: float,
) -> SearchDecision:
    return SearchDecision(
        query=query,
        normalized_query=normalized_query,
        route_type="no_safe_result",
        status=status,
        result_mode="no_result",
        public_allowed=False,
        indexable_allowed=False,
        sitemap_allowed=False,
        reason_codes=reasons,
        confidence=confidence,
    )


def route_search_query(query: str) -> SearchDecision:
    raw_query = str(query or "")
    normalized_query = _normalize_query(raw_query)
    tokens = _tokenize(normalized_query)

    try:
        if _is_meaningless_query(normalized_query, tokens):
            return _safe_no_result_decision(
                query=raw_query,
                normalized_query=normalized_query,
                status="no_valid_offers",
                reasons=("empty_or_meaningless_query",),
                confidence=1.0,
            )

        is_ambiguous, ambiguity_reasons = _is_ambiguous(tokens, normalized_query)
        if is_ambiguous:
            return SearchDecision(
                query=raw_query,
                normalized_query=normalized_query,
                route_type="ambiguous_query",
                status="manual_review_required",
                result_mode="review_only",
                public_allowed=False,
                indexable_allowed=False,
                sitemap_allowed=False,
                reason_codes=ambiguity_reasons,
                confidence=0.95,
            )

        if _is_specific_product(tokens, normalized_query):
            return SearchDecision(
                query=raw_query,
                normalized_query=normalized_query,
                route_type="specific_product",
                status="exact_product_resolution_required",
                result_mode="same_product_multi_store_offers",
                public_allowed=False,
                indexable_allowed=False,
                sitemap_allowed=False,
                reason_codes=("exact_match_required", "offers_must_be_same_product"),
                confidence=0.9,
            )

        return SearchDecision(
            query=raw_query,
            normalized_query=normalized_query,
            route_type="general_intent",
            status="general_product_discovery_allowed",
            result_mode="four_product_comparison",
            public_allowed=False,
            indexable_allowed=False,
            sitemap_allowed=False,
            reason_codes=("general_buying_intent_detected",),
            confidence=0.8,
        )
    except Exception:
        # Safe deterministic fallback; never throw from router path.
        return _safe_no_result_decision(
            query=raw_query,
            normalized_query=normalized_query,
            status="insufficient_data",
            reasons=("router_fallback",),
            confidence=_DEFAULT_CONFIDENCE,
        )
