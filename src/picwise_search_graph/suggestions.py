from __future__ import annotations

import re
from dataclasses import dataclass, field

from .contracts import (
    SUGGESTION_TYPES,
    SearchEntityGraphEnvelope,
)
from .validation import validate_search_entity_graph_envelope

_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]+")

_SCORE_EXACT_PREFIX = 1000
_SCORE_TOKEN_PREFIX = 900
_SCORE_FUZZY_TOKEN = 800
_SCORE_CANDIDATE_BONUS = 50
_SCORE_ALIAS_BONUS = 25


def _normalize_text(value: object) -> str:
    compact = " ".join(str(value or "").split()).strip().lower()
    return _NORMALIZE_RE.sub(" ", compact).strip()


def _tokenize(value: str) -> tuple[str, ...]:
    return tuple(token for token in value.split() if token)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for index, char_a in enumerate(a, start=1):
        current = [index]
        for col, char_b in enumerate(b, start=1):
            insert_cost = current[col - 1] + 1
            delete_cost = previous[col] + 1
            replace_cost = previous[col - 1] + (char_a != char_b)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _fuzzy_token_match(partial_token: str, candidate_token: str) -> bool:
    if not partial_token or not candidate_token:
        return False
    if candidate_token.startswith(partial_token):
        return True
    if partial_token.startswith(candidate_token):
        return True
    shorter = min(len(partial_token), len(candidate_token))
    if shorter >= 4 and partial_token[:3] == candidate_token[:3]:
        max_distance = 2
    elif shorter >= 3:
        max_distance = 1
    else:
        max_distance = 0
    return _levenshtein(partial_token, candidate_token) <= max_distance


def _token_prefix_match(partial_tokens: tuple[str, ...], candidate_tokens: tuple[str, ...]) -> bool:
    if not partial_tokens or len(partial_tokens) > len(candidate_tokens):
        return False
    for partial_token, candidate_token in zip(partial_tokens, candidate_tokens, strict=False):
        if not candidate_token.startswith(partial_token):
            return False
    return True


def _fuzzy_token_prefix_match(partial_tokens: tuple[str, ...], candidate_tokens: tuple[str, ...]) -> bool:
    if not partial_tokens or len(partial_tokens) > len(candidate_tokens):
        return False
    for partial_token, candidate_token in zip(partial_tokens, candidate_tokens, strict=False):
        if not _fuzzy_token_match(partial_token, candidate_token):
            return False
    return True


def _match_score(partial_query: str, candidate_text: str) -> tuple[int, tuple[str, ...]]:
    partial = _normalize_text(partial_query)
    candidate = _normalize_text(candidate_text)
    if not partial or not candidate:
        return 0, ()

    if candidate.startswith(partial):
        return _SCORE_EXACT_PREFIX, ("exact_prefix",)

    partial_tokens = _tokenize(partial)
    candidate_tokens = _tokenize(candidate)
    if _token_prefix_match(partial_tokens, candidate_tokens):
        return _SCORE_TOKEN_PREFIX, ("token_prefix",)
    if _fuzzy_token_prefix_match(partial_tokens, candidate_tokens):
        return _SCORE_FUZZY_TOKEN, ("fuzzy_token_prefix",)
    return 0, ()


def _is_brand_only_text(text: str) -> bool:
    return len(_tokenize(text)) < 2


@dataclass(frozen=True)
class QueryAssistSuggestion:
    suggestion_text: str
    suggestion_type: str
    target_entity_ids: tuple[str, ...]
    score: float
    source: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "suggestion_text": self.suggestion_text,
            "suggestion_type": self.suggestion_type,
            "target_entity_ids": list(self.target_entity_ids),
            "score": self.score,
            "source": self.source,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, data: dict) -> QueryAssistSuggestion:
        return cls(
            suggestion_text=str(data["suggestion_text"]),
            suggestion_type=str(data["suggestion_type"]),
            target_entity_ids=tuple(str(entity_id) for entity_id in data.get("target_entity_ids") or ()),
            score=float(data["score"]),
            source=str(data["source"]),
            reason_codes=tuple(str(code) for code in data.get("reason_codes") or ()),
        )


@dataclass(frozen=True)
class _SuggestionSeed:
    suggestion_text: str
    suggestion_type: str
    target_entity_ids: tuple[str, ...]
    source: str
    reason_codes: tuple[str, ...]
    score_bonus: int = 0


def _assert_suggestion_type(value: str) -> str:
    if value not in SUGGESTION_TYPES:
        raise ValueError(f"Unsupported suggestion_type: {value}")
    return value


def _collect_seeds(envelope: SearchEntityGraphEnvelope) -> list[_SuggestionSeed]:
    product_families = {entity.entity_id: entity for entity in envelope.entities.product_families}
    brands = {entity.entity_id: entity for entity in envelope.entities.brands}
    seeds: list[_SuggestionSeed] = []

    for candidate in envelope.entities.suggestions:
        if _is_brand_only_text(candidate.suggestion_text):
            continue
        seeds.append(
            _SuggestionSeed(
                suggestion_text=candidate.suggestion_text,
                suggestion_type=_assert_suggestion_type(candidate.suggestion_type),
                target_entity_ids=candidate.target_entity_ids,
                source=candidate.source,
                reason_codes=("graph_suggestion_candidate",),
                score_bonus=_SCORE_CANDIDATE_BONUS,
            )
        )

    for entity in envelope.entities.product_families:
        if _is_brand_only_text(entity.canonical_name):
            continue
        seeds.append(
            _SuggestionSeed(
                suggestion_text=entity.canonical_name,
                suggestion_type="product_family",
                target_entity_ids=(entity.entity_id,),
                source=entity.source,
                reason_codes=("graph_product_family",),
            )
        )

    for edge in envelope.edges:
        if edge.edge_type != "appears_in":
            continue
        brand = brands.get(edge.from_entity_id)
        product_family = product_families.get(edge.to_entity_id)
        if brand is None or product_family is None:
            continue
        suggestion_text = product_family.canonical_name
        if _is_brand_only_text(suggestion_text):
            suggestion_text = f"{brand.normalized_brand_name} {product_family.canonical_name}".strip()
        if _is_brand_only_text(suggestion_text):
            continue
        seeds.append(
            _SuggestionSeed(
                suggestion_text=suggestion_text,
                suggestion_type="brand_product",
                target_entity_ids=(brand.entity_id, product_family.entity_id),
                source=edge.source,
                reason_codes=("graph_brand_appears_in_product_family",),
            )
        )

    for alias in envelope.entities.query_aliases:
        if alias.target_entity_type == "BrandEntity":
            continue
        if alias.target_entity_type != "ProductFamilyEntity":
            continue
        target = product_families.get(alias.target_entity_id)
        if target is None:
            continue
        if _is_brand_only_text(alias.normalized_alias):
            continue
        suggestion_type = "product_family"
        target_ids: tuple[str, ...] = (target.entity_id,)
        reason_codes: tuple[str, ...] = ("graph_query_alias",)
        if alias.alias_type == "brand_modifier":
            suggestion_type = "brand_product"
            brand_entity_id = ""
            for edge in envelope.edges:
                if edge.edge_type != "maps_to_brand" or edge.from_entity_id != alias.entity_id:
                    continue
                brand_entity_id = edge.to_entity_id
                break
            if brand_entity_id and brand_entity_id in brands:
                target_ids = (brand_entity_id, target.entity_id)
            reason_codes = ("graph_query_alias", "brand_modifier")
        elif alias.alias_type == "spec_modifier":
            suggestion_type = "spec_product"
            reason_codes = ("graph_query_alias", "spec_modifier")
        seeds.append(
            _SuggestionSeed(
                suggestion_text=alias.normalized_alias,
                suggestion_type=_assert_suggestion_type(suggestion_type),
                target_entity_ids=target_ids,
                source=alias.source,
                reason_codes=reason_codes,
                score_bonus=_SCORE_ALIAS_BONUS,
            )
        )

    return seeds


def build_query_assist_suggestions(
    envelope: SearchEntityGraphEnvelope,
    partial_query: str,
    *,
    max_suggestions: int = 8,
) -> tuple[QueryAssistSuggestion, ...]:
    validation = validate_search_entity_graph_envelope(envelope)
    if not validation["valid"]:
        return ()

    normalized_partial = _normalize_text(partial_query)
    if not normalized_partial:
        return ()

    if max_suggestions <= 0:
        return ()

    ranked: dict[str, QueryAssistSuggestion] = {}
    for seed in _collect_seeds(envelope):
        normalized_text = _normalize_text(seed.suggestion_text)
        if not normalized_text:
            continue
        base_score, match_reasons = _match_score(normalized_partial, normalized_text)
        if base_score <= 0:
            continue
        total_score = float(base_score + seed.score_bonus)
        reason_codes = tuple(sorted(set(match_reasons + seed.reason_codes)))
        suggestion = QueryAssistSuggestion(
            suggestion_text=normalized_text,
            suggestion_type=seed.suggestion_type,
            target_entity_ids=seed.target_entity_ids,
            score=total_score,
            source=seed.source,
            reason_codes=reason_codes,
        )
        existing = ranked.get(normalized_text)
        if existing is None or suggestion.score > existing.score:
            ranked[normalized_text] = suggestion

    ordered = sorted(
        ranked.values(),
        key=lambda row: (-row.score, len(row.suggestion_text), row.suggestion_text),
    )
    return tuple(ordered[:max_suggestions])
