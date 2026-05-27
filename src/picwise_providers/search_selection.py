from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from picwise_nlu import normalize_query

from .contracts import ProviderProduct

_TITLE_WEIGHT = 100
_CATEGORY_WEIGHT = 40
_KEYWORD_WEIGHT = 20
_DESCRIPTION_WEIGHT = 5
_PHRASE_IN_TITLE_BONUS = 150
_ALL_TOKENS_IN_TITLE_BONUS = 80
_PRODUCT_TYPE_IN_TITLE_BONUS = 60
_COMPLETE_PRODUCT_BONUS = 25
_NOT_ACCESSORY_BONUS = 40
_ACCESSORY_PENALTY = 220
_STRONG_MATCH_MIN_SCORE = 280
_DESCRIPTION_MAX_LEN = 500
_MIN_TOKEN_LEN = 2

_ACCESSORY_TERMS = frozenset(
    {
        "accessories",
        "accessory",
        "bag",
        "bags",
        "filter",
        "filters",
        "cloth",
        "mop",
        "replacement",
        "spare",
        "parts",
        "kit",
        "tool kit",
        "nozzle",
        "filament",
        "adapter",
        "docking station",
        "lens",
        "cable",
        "battery",
        "sensor",
        "cover",
        "case",
        "stand",
        "bracket",
        "brush",
        "brushes",
        "mount",
    }
)
_ACCESSORY_FOR_PRODUCT_PENALTY = 260
_ACCESSORY_PACK_PREFIX_RE = re.compile(r"^\d+\s*(?:pcs|pc|pack|pieces?)\b", flags=re.IGNORECASE)

_DEDUPE_PUNCT_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)


@dataclass(frozen=True)
class ProviderProductSelectionResult:
    status: str
    matched_count: int = 0
    strong_matched_count: int = 0
    selected_products: tuple[ProviderProduct, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "matched_count": self.matched_count,
            "strong_matched_count": self.strong_matched_count,
            "selected_count": len(self.selected_products),
            "reason_codes": list(self.reason_codes),
            "selected_products": [
                provider_product_to_backend_dict(product)
                for product in self.selected_products
            ],
        }


def mask_provider_product_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return "<invalid-url>"
    path = parsed.path or "/"
    if len(path) > 24:
        path = f"{path[:20]}...{path[-1]}"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def provider_product_to_backend_dict(product: ProviderProduct) -> dict[str, Any]:
    return {
        "provider_key": str(product.provider_key or "").strip(),
        "provider_product_id": str(product.provider_product_id or "").strip(),
        "title": str(product.title or "").strip(),
        "price_text": str(product.price_text or "").strip(),
        "availability_text": str(product.availability_text or "").strip(),
        "product_url_masked": mask_provider_product_url(product.product_url),
    }


def _tokenize_query(query: str) -> tuple[str, ...]:
    normalized = normalize_query(str(query or ""))
    if not normalized:
        return tuple()
    return tuple(
        token
        for token in normalized.split()
        if len(token) >= _MIN_TOKEN_LEN
    )


def _normalize_dedupe_title(title: str) -> str:
    collapsed = " ".join(str(title or "").split()).strip().lower()
    if not collapsed:
        return ""
    return _DEDUPE_PUNCT_RE.sub(" ", collapsed)


def _product_search_fields(product: ProviderProduct) -> dict[str, str]:
    raw = product.raw if isinstance(product.raw, dict) else {}
    category_parts = [
        product.category_text,
        str(raw.get("category_name") or ""),
        str(raw.get("merchant_category") or ""),
    ]
    description = str(raw.get("description") or "").strip()
    if len(description) > _DESCRIPTION_MAX_LEN:
        description = ""

    return {
        "title": str(product.title or "").strip().lower(),
        "category": " ".join(part.strip().lower() for part in category_parts if str(part).strip()),
        "keywords": str(raw.get("keywords") or "").strip().lower(),
        "description": description.lower(),
    }


def _token_matches_field(token: str, field_text: str) -> bool:
    if not token or not field_text:
        return False
    return token in field_text


def _word_in_text(word: str, text: str) -> bool:
    if not word or not text:
        return False
    pattern = rf"\b{re.escape(word)}\b"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _query_seeks_accessory(tokens: tuple[str, ...], normalized_query: str) -> bool:
    if any(token in _ACCESSORY_TERMS for token in tokens):
        return True
    normalized = str(normalized_query or "").strip().lower()
    return any(term in normalized for term in _ACCESSORY_TERMS)


def _title_accessory_penalty(
    title: str,
    *,
    normalized_query: str,
    query_seeks_accessory: bool,
) -> int:
    if query_seeks_accessory or not title:
        return 0
    penalty = 0
    for term in _ACCESSORY_TERMS:
        if term in title:
            penalty += _ACCESSORY_PENALTY
    if _ACCESSORY_PACK_PREFIX_RE.search(title):
        penalty += _ACCESSORY_PENALTY
    if normalized_query and normalized_query in title and " for " in title:
        for_index = title.find(" for ")
        phrase_index = title.find(normalized_query)
        if phrase_index > for_index:
            penalty += _ACCESSORY_FOR_PRODUCT_PENALTY
    return penalty


def _product_completeness_bonus(product: ProviderProduct) -> int:
    bonus = 0
    if str(product.image_url or "").strip():
        bonus += 8
    if str(product.product_url or "").strip():
        bonus += 6
    if str(product.price_text or "").strip():
        bonus += 6
    if str(product.availability_text or "").strip():
        bonus += 5
    return bonus if bonus == 25 else 0


def _score_product_for_tokens(
    product: ProviderProduct,
    tokens: tuple[str, ...],
    *,
    normalized_query: str,
    query_seeks_accessory: bool,
) -> tuple[int, int, int, str, str] | None:
    fields = _product_search_fields(product)
    matched_tokens = 0
    score = 0
    title_matches = 0
    category_matches = 0

    for token in tokens:
        token_matched = False
        if _token_matches_field(token, fields["title"]):
            score += _TITLE_WEIGHT
            title_matches += 1
            token_matched = True
        if _token_matches_field(token, fields["category"]):
            score += _CATEGORY_WEIGHT
            category_matches += 1
            token_matched = True
        if _token_matches_field(token, fields["keywords"]):
            score += _KEYWORD_WEIGHT
            token_matched = True
        if fields["description"] and _token_matches_field(token, fields["description"]):
            score += _DESCRIPTION_WEIGHT
            token_matched = True
        if token_matched:
            matched_tokens += 1

    if matched_tokens < len(tokens):
        return None

    normalized = str(normalized_query or "").strip().lower()
    if normalized and normalized in fields["title"]:
        score += _PHRASE_IN_TITLE_BONUS
    if title_matches == len(tokens):
        score += _ALL_TOKENS_IN_TITLE_BONUS
    if category_matches > 0:
        score += _CATEGORY_WEIGHT // 2
    if tokens and _word_in_text(tokens[-1], fields["title"]):
        score += _PRODUCT_TYPE_IN_TITLE_BONUS

    accessory_penalty = _title_accessory_penalty(
        fields["title"],
        normalized_query=normalized,
        query_seeks_accessory=query_seeks_accessory,
    )
    score -= accessory_penalty
    if accessory_penalty == 0 and not query_seeks_accessory:
        score += _NOT_ACCESSORY_BONUS
    score += _product_completeness_bonus(product)

    return (
        matched_tokens,
        score,
        title_matches,
        str(product.title or "").strip().lower(),
        str(product.provider_product_id or "").strip(),
    )


def _dedupe_selected_products(
    ranked_products: list[tuple[tuple[int, int, int, str, str], ProviderProduct]],
) -> list[ProviderProduct]:
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    selected: list[ProviderProduct] = []

    for _, product in ranked_products:
        product_id = str(product.provider_product_id or "").strip()
        dedupe_title = _normalize_dedupe_title(product.title)
        if product_id and product_id in seen_ids:
            continue
        if dedupe_title and dedupe_title in seen_titles:
            continue
        if product_id:
            seen_ids.add(product_id)
        if dedupe_title:
            seen_titles.add(dedupe_title)
        selected.append(product)

    return selected


def _count_strong_matches(
    ranked_products: list[tuple[tuple[int, int, int, str, str], ProviderProduct]],
    *,
    token_count: int,
) -> int:
    strong_count = 0
    for ranking, _product in ranked_products:
        _matched_tokens, score, title_matches, _title_key, _product_id = ranking
        if score >= _STRONG_MATCH_MIN_SCORE and title_matches >= token_count:
            strong_count += 1
    return strong_count


def is_strong_feed_opportunity_selection(
    selection: ProviderProductSelectionResult,
    *,
    max_products: int = 4,
) -> bool:
    safe_max = max(1, int(max_products))
    if selection.status != "selected":
        return False
    if len(selection.selected_products) < safe_max:
        return False
    return selection.strong_matched_count >= safe_max


def select_provider_products_for_query(
    query: str,
    products: tuple[ProviderProduct, ...],
    *,
    max_products: int = 4,
) -> ProviderProductSelectionResult:
    safe_max = max(1, int(max_products))
    normalized_query = normalize_query(str(query or ""))
    tokens = _tokenize_query(query)
    if not tokens:
        return ProviderProductSelectionResult(
            status="no_query_tokens",
            matched_count=0,
            strong_matched_count=0,
            selected_products=tuple(),
            reason_codes=("empty_query",),
        )

    query_seeks_accessory = _query_seeks_accessory(tokens, normalized_query)
    ranked: list[tuple[tuple[int, int, int, str, str], ProviderProduct]] = []
    for product in products:
        ranking = _score_product_for_tokens(
            product,
            tokens,
            normalized_query=normalized_query,
            query_seeks_accessory=query_seeks_accessory,
        )
        if ranking is not None:
            ranked.append((ranking, product))

    ranked.sort(key=lambda row: (-row[0][1], -row[0][2], -row[0][0], row[0][3], row[0][4]))
    strong_matched_count = _count_strong_matches(ranked, token_count=len(tokens))
    deduped = _dedupe_selected_products(ranked)
    matched_count = len(deduped)

    if matched_count < safe_max:
        return ProviderProductSelectionResult(
            status="insufficient_relevant_products",
            matched_count=matched_count,
            strong_matched_count=strong_matched_count,
            selected_products=tuple(),
            reason_codes=("insufficient_relevant_products",),
        )

    return ProviderProductSelectionResult(
        status="selected",
        matched_count=matched_count,
        strong_matched_count=strong_matched_count,
        selected_products=tuple(deduped[:safe_max]),
        reason_codes=("provider_feed_products_selected",),
    )
