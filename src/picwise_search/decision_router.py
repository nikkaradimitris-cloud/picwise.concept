from __future__ import annotations

from dataclasses import dataclass
import re


RouteType = str

_DEFAULT_CONFIDENCE = 0.5
_MIN_QUERY_LENGTH = 3
_DEFAULT_QUERY_FALLBACK = "power bank 20000mah for iphone"

_KNOWN_BRANDS = frozenset(
    {
        "goodyear",
        "continental",
        "michelin",
        "bridgestone",
        "pirelli",
        "dunlop",
        "yokohama",
        "hankook",
        "nokian",
        "firestone",
    }
)
_KNOWN_MODEL_TOKENS = frozenset(
    {
        "efficientgrip",
        "performance",
        "ecocontact",
        "primacy",
        "pilot",
        "potenza",
        "turanza",
    }
)
_TYPO_BRAND_TOKENS = frozenset({"goodyar", "michelan", "continetal"})
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

_SIZE_REGEX = re.compile(r"\b\d{3}/\d{2}(?:\s*r\d{2}|/\d{2})\b", flags=re.IGNORECASE)
_SPACE_REGEX = re.compile(r"\s+")
_TOKEN_REGEX = re.compile(r"[^\w]+", flags=re.UNICODE)


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


def _detect_conflicting_brand_model(tokens: list[str]) -> bool:
    token_set = set(tokens)
    has_goodyear_family = bool({"goodyear", "goodyar", "efficientgrip"} & token_set)
    has_continental_family = bool({"continental", "ecocontact", "eco", "contact"} & token_set)
    if has_goodyear_family and has_continental_family:
        return True
    brand_hits = token_set & (_KNOWN_BRANDS | _TYPO_BRAND_TOKENS)
    return len(brand_hits) > 1


def _is_ambiguous(tokens: list[str]) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    token_set = set(tokens)
    if token_set & _TYPO_BRAND_TOKENS:
        reasons.append("brand_typo_detected")
    if _detect_conflicting_brand_model(tokens):
        reasons.append("brand_model_conflict_detected")
    if "??" in "".join(tokens):
        reasons.append("query_noise_detected")
    return bool(reasons), tuple(reasons)


def _is_specific_product(tokens: list[str], normalized_query: str) -> bool:
    token_set = set(tokens)
    has_size = bool(_SIZE_REGEX.search(normalized_query))
    has_known_brand_or_model = bool((_KNOWN_BRANDS | _KNOWN_MODEL_TOKENS) & token_set)
    has_numeric_spec = any(char.isdigit() for char in normalized_query)
    return has_size and has_known_brand_or_model and has_numeric_spec


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

        is_ambiguous, ambiguity_reasons = _is_ambiguous(tokens)
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
            normalized_query=normalized_query or _DEFAULT_QUERY_FALLBACK,
            status="insufficient_data",
            reasons=("router_fallback",),
            confidence=_DEFAULT_CONFIDENCE,
        )
