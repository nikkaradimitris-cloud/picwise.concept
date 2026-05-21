from __future__ import annotations

from dataclasses import dataclass

from .contracts import CanonicalVocabularyRegistry
from .index_contracts import SearchIndexLookupResult
from .lookup_safety import is_meta_only_query
from .validation import normalize_term

_MAX_SUGGESTIONS = 5
_MIN_SUGGESTIONS = 2
_MIN_SUGGESTION_SCORE = 0.48
_MAX_QUERY_TOKENS = 2
_MIN_ROOT_TOKEN_LENGTH = 3
_MAX_SUGGESTION_TERM_TOKENS = 4

_UNSAFE_BROAD_QUERY_TERMS = frozenset(
    {
        "bank",
        "apple",
        "nike",
        "bosch",
        "insurance",
        "loan",
        "erp",
        "crm",
        "accounting",
        "software",
        "accounting software",
        "amazon",
        "galaxy",
    }
)

_NON_RETAIL_MARKERS = frozenset(
    {
        "accounting",
        "banking",
        "broker",
        "crm",
        "erp",
        "finance",
        "insurance",
        "loan",
        "saas",
        "software",
    }
)

_TAXONOMY_TERM_MARKERS = frozenset(
    {
        "taxonomy",
        "families",
        "family",
        "equipment",
        "solutions",
        "systems",
        "workflows",
        "organization",
        "lines",
        "distribution",
        "compatibility",
        "entries",
        "entry",
        "valid",
        "daily",
        "source",
        "catalog",
        "guides",
        "guide",
        "categories",
        "category",
    }
)

_ACCEPTABLE_CANONICAL_SOURCES = frozenset(
    {
        "taxonomy_bridge",
        "offline_canonical_vocabulary_coverage",
        "taxonomy_clean_vocabulary",
    },
)

_HIGH_CONFIDENCE_SCORE = 0.84


@dataclass(frozen=True)
class BroadQuerySuggestion:
    canonical_term: str
    mega_category_id: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return {
            "canonical_term": self.canonical_term,
            "mega_category_id": self.mega_category_id,
            "source": self.source,
        }


def is_unsafe_broad_query(normalized_query: str) -> bool:
    if not normalized_query:
        return True
    if is_meta_only_query(normalized_query):
        return True
    if normalized_query in _UNSAFE_BROAD_QUERY_TERMS:
        return True
    tokens = tuple(token for token in normalized_query.split() if token)
    if not tokens:
        return True
    if any(token in _UNSAFE_BROAD_QUERY_TERMS for token in tokens):
        return True
    if any(token in _NON_RETAIL_MARKERS for token in tokens):
        return True
    return False


def is_retail_product_canonical_term(normalized_term: str) -> bool:
    if not normalized_term:
        return False
    tokens = tuple(token for token in normalized_term.split() if token)
    if not tokens or len(tokens) > _MAX_SUGGESTION_TERM_TOKENS:
        return False
    if any(token in _TAXONOMY_TERM_MARKERS for token in tokens):
        return False
    if any(token in _NON_RETAIL_MARKERS for token in tokens):
        return False
    if len(tokens) == 1 and len(tokens[0]) <= 7 and tokens[0] in {"taxonomy", "families", "family", "source", "valid", "daily"}:
        return False
    return True


def _root_token_position_score(term_tokens: tuple[str, ...], root_token: str) -> float:
    if not term_tokens or root_token not in term_tokens:
        return 0.0
    if term_tokens[0] == root_token:
        return 1.0
    if term_tokens[-1] == root_token:
        return 0.88
    return 0.45


def _score_suggestion(*, root_token: str, canonical_term: str, token_count: int) -> float:
    tokens = tuple(canonical_term.split())
    position_score = _root_token_position_score(tokens, root_token)
    if position_score <= 0.0:
        return 0.0
    specificity = min(token_count, 4) / 4.0
    prefix_bonus = 0.20 if tokens and tokens[0] == root_token else 0.0
    length_penalty = min(max(len(canonical_term) - len(root_token) - 1, 0), 30) / 60.0
    return (0.45 * specificity + 0.35 * position_score + 0.10 + prefix_bonus - length_penalty)


def build_broad_query_suggestions(
    registry: CanonicalVocabularyRegistry,
    query: str,
) -> tuple[BroadQuerySuggestion, ...]:
    normalized_query = normalize_term(query)
    if is_unsafe_broad_query(normalized_query):
        return ()

    query_tokens = tuple(token for token in normalized_query.split() if token)
    if not query_tokens or len(query_tokens) > _MAX_QUERY_TOKENS:
        return ()

    root_token = query_tokens[0]
    if len(root_token) < _MIN_ROOT_TOKEN_LENGTH:
        return ()

    scored: dict[tuple[str, str], tuple[float, str]] = {}
    for record in registry.records:
        if record.source not in _ACCEPTABLE_CANONICAL_SOURCES:
            continue
        normalized_term = record.normalized_term
        if normalized_term == normalized_query:
            continue
        if not is_retail_product_canonical_term(normalized_term):
            continue
        term_tokens = tuple(normalized_term.split())
        if root_token not in term_tokens:
            continue
        if len(term_tokens) < 2:
            continue
        if term_tokens[-1] == root_token and term_tokens[0] != root_token and len(term_tokens) > 3:
            continue

        score = _score_suggestion(
            root_token=root_token,
            canonical_term=normalized_term,
            token_count=len(term_tokens),
        )
        if score < _MIN_SUGGESTION_SCORE:
            continue

        signature = (normalized_term, record.mega_category_id)
        existing = scored.get(signature)
        if existing is None or score > existing[0]:
            scored[signature] = (score, record.source)

    if len(scored) < _MIN_SUGGESTIONS:
        return ()

    ranked = sorted(
        scored.items(),
        key=lambda row: (
            -row[1][0],
            row[0][0],
            row[0][1],
        ),
    )[:_MAX_SUGGESTIONS]

    return tuple(
        BroadQuerySuggestion(
            canonical_term=signature[0],
            mega_category_id=signature[1],
            source=source,
        )
        for signature, (_, source) in ranked
    )


def build_definite_single_token_match_tokens(index) -> frozenset[str]:
    """Precompute single-token queries that resolve as definite product intents."""
    tokens: set[str] = set()
    for entry in index.entries:
        variant = entry.normalized_variant
        if not variant or " " in variant:
            continue
        if entry.normalized_term == variant:
            tokens.add(variant)
            continue
        if entry.variant_type == "product_head_token":
            tokens.add(variant)
            continue
        if entry.variant_type in {"exact_canonical", "source_alias", "spelling_family"}:
            tokens.add(variant)
    return frozenset(tokens)


def is_definite_index_product_resolution(
    normalized_query: str,
    lookup_result: SearchIndexLookupResult,
) -> bool:
    if lookup_result.status != "match":
        return False
    if lookup_result.score < _HIGH_CONFIDENCE_SCORE:
        return False
    entry = lookup_result.matched_entry
    if entry is None:
        return False
    if entry.normalized_variant != normalized_query:
        return False
    if entry.normalized_term == normalized_query:
        return True
    if entry.variant_type == "product_head_token":
        return True
    if entry.variant_type in {"exact_canonical", "source_alias", "spelling_family"}:
        return True
    return lookup_result.score >= 0.93


def should_offer_broad_query_suggestions(
    *,
    normalized_query: str,
    lookup_result: SearchIndexLookupResult,
    suggestions: tuple[BroadQuerySuggestion, ...],
) -> bool:
    if not suggestions:
        return False
    if is_unsafe_broad_query(normalized_query):
        return False
    if is_definite_index_product_resolution(normalized_query, lookup_result):
        return False
    query_tokens = tuple(token for token in normalized_query.split() if token)
    if len(query_tokens) != 1:
        return False
    return True
