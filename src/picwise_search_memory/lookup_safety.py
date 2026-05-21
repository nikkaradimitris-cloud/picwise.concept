from __future__ import annotations

from collections import defaultdict

from .contracts import CanonicalVocabularyRegistry
from .index_contracts import SearchIndex, SearchIndexEntry
from .validation import normalize_term

_META_INTENT_TOKENS = {
    "taxonomy",
    "categories",
    "category",
    "guides",
    "guide",
    "systems",
    "system",
    "premium",
    "families",
    "family",
    "source",
    "entry",
    "entries",
    "valid",
    "daily",
    "compatibility",
    "sets",
}

_HOMOGRAPH_NEIGHBORHOOD_DISTANCE = 2
_SHORT_QUERY_MAX_LEN = 4
_HIGH_NEIGHBORHOOD_CATEGORY_COUNT = 3


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


def consonant_skeleton(value: str) -> str:
    return "".join(char for char in value.replace(" ", "") if char not in "aeiou")


def is_meta_only_query(normalized_query: str) -> bool:
    tokens = tuple(token for token in normalized_query.split() if token)
    if not tokens:
        return False
    if len(tokens) == 1 and tokens[0] in _META_INTENT_TOKENS:
        return True
    if len(tokens) <= 2 and all(token in _META_INTENT_TOKENS for token in tokens):
        return True
    return False


def build_canonical_term_index_from_registry(registry: CanonicalVocabularyRegistry) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in registry.records:
        signature = (record.normalized_term, record.mega_category_id)
        if signature in seen:
            continue
        seen.add(signature)
        rows.append(signature)
    return tuple(rows)


def build_exact_canonical_term_index(index: SearchIndex) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in index.entries:
        if entry.variant_type != "exact_canonical":
            continue
        signature = (entry.normalized_term, entry.mega_category_id)
        if signature in seen:
            continue
        seen.add(signature)
        rows.append(signature)
    return tuple(rows)


def _neighbor_canonical_hits(
    normalized_query: str,
    canonical_term_index: tuple[tuple[str, str], ...],
    *,
    max_distance: int = _HOMOGRAPH_NEIGHBORHOOD_DISTANCE,
) -> list[tuple[int, str, str]]:
    query_joined = normalized_query.replace(" ", "")
    if not query_joined:
        return []
    hits: list[tuple[int, str, str]] = []
    for canonical_term, mega_category_id in canonical_term_index:
        distance = _levenshtein_distance(query_joined, canonical_term.replace(" ", ""))
        if distance <= max_distance:
            hits.append((distance, canonical_term, mega_category_id))
    return sorted(hits, key=lambda row: (row[0], row[1], row[2]))


def has_cross_canonical_neighborhood_collision(
    normalized_query: str,
    *,
    matched_canonical_term: str,
    matched_mega_category_id: str,
    canonical_term_index: tuple[tuple[str, str], ...],
    max_distance: int = _HOMOGRAPH_NEIGHBORHOOD_DISTANCE,
) -> bool:
    hits = _neighbor_canonical_hits(normalized_query, canonical_term_index, max_distance=max_distance)
    if not hits:
        return False
    if matched_canonical_term.replace(" ", "") == normalized_query.replace(" ", ""):
        return False

    close_hits = [row for row in hits if row[0] <= 1]
    if not close_hits:
        return False
    close_categories = {row[2] for row in close_hits}
    if len(close_categories) <= 1:
        return False
    return True


def has_dense_cross_category_neighborhood(
    normalized_query: str,
    *,
    canonical_term_index: tuple[tuple[str, str], ...],
    max_distance: int = _HOMOGRAPH_NEIGHBORHOOD_DISTANCE,
) -> bool:
    if len(normalized_query.replace(" ", "")) > _SHORT_QUERY_MAX_LEN:
        return False
    neighbor_categories = {row[2] for row in _neighbor_canonical_hits(normalized_query, canonical_term_index, max_distance=max_distance)}
    return len(neighbor_categories) >= _HIGH_NEIGHBORHOOD_CATEGORY_COUNT


def has_ambiguous_closest_canonical_neighborhood(
    normalized_query: str,
    *,
    canonical_term_index: tuple[tuple[str, str], ...],
    max_distance: int = _HOMOGRAPH_NEIGHBORHOOD_DISTANCE,
) -> bool:
    hits = _neighbor_canonical_hits(normalized_query, canonical_term_index, max_distance=max_distance)
    if not hits:
        return False
    min_distance = hits[0][0]
    closest_categories = {row[2] for row in hits if row[0] == min_distance}
    return len(closest_categories) > 1


def should_reject_generated_variant_for_index(
    *,
    canonical_term: str,
    variant: str,
    variant_type: str,
    mega_category_id: str,
    canonical_term_index: tuple[tuple[str, str], ...],
) -> bool:
    if variant_type not in {"missing_letter", "vowel_drop"}:
        return False
    if variant == canonical_term:
        return False
    if len(variant.replace(" ", "")) > 4:
        return False
    pseudo_entry = type(
        "PseudoEntry",
        (),
        {
            "normalized_variant": variant,
            "normalized_term": canonical_term,
            "variant_type": variant_type,
            "mega_category_id": mega_category_id,
        },
    )()
    if not is_generated_variant_exact_match_risky(pseudo_entry, variant):
        return False
    return has_dense_cross_category_neighborhood(variant, canonical_term_index=canonical_term_index)


def is_generated_variant_exact_match_risky(entry: SearchIndexEntry, normalized_query: str) -> bool:
    if entry.normalized_variant != normalized_query:
        return False
    if entry.normalized_variant == entry.normalized_term:
        return False
    if entry.variant_type not in {"missing_letter", "vowel_drop", "consonant_skeleton"}:
        return False
    return len(normalized_query.replace(" ", "")) <= 5


def derive_product_head_variants(registry: CanonicalVocabularyRegistry) -> list[dict[str, str]]:
    trailing: dict[str, list] = defaultdict(list)
    leading: dict[str, list] = defaultdict(list)

    for record in registry.records:
        tokens = record.normalized_term.split()
        if len(tokens) < 2:
            continue
        trailing[tokens[-1]].append(record)
        if len(tokens[0]) >= 9:
            leading[tokens[0]].append(record)

    variants: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def _append(record, variant: str, variant_type: str) -> None:
        signature = (variant, record.mega_category_id, record.canonical_id)
        if signature in seen:
            return
        seen.add(signature)
        variants.append(
            {
                "canonical_term": record.normalized_term,
                "variant": variant,
                "mega_category_id": record.mega_category_id,
                "variant_type": variant_type,
                "source": record.source,
                "generator_version": "stage7e_product_head_derivation",
            }
        )

    for token, records in trailing.items():
        if len(token) < 4:
            continue
        categories = {record.mega_category_id for record in records}
        if len(categories) != 1:
            continue
        if len(records) < 3 and not (len(records) >= 2 and len(token) >= 5):
            continue
        representative = sorted(records, key=lambda row: (len(row.normalized_term), row.canonical_id))[0]
        _append(representative, token, "product_head_token")

    for token, records in leading.items():
        categories = {record.mega_category_id for record in records}
        if len(categories) != 1 or len(records) != 1:
            continue
        _append(records[0], token, "product_head_token")

    return variants


def derive_source_alias_variants(registry: CanonicalVocabularyRegistry) -> list[dict[str, str]]:
    variants: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for record in registry.records:
        if not record.aliases:
            continue
        for alias in record.aliases:
            normalized_alias = normalize_term(alias)
            if not normalized_alias or normalized_alias == record.normalized_term:
                continue
            if len(normalized_alias.split()) > 3 or len(normalized_alias) > 48:
                continue
            signature = (normalized_alias, record.mega_category_id, record.canonical_id)
            if signature in seen:
                continue
            seen.add(signature)
            variants.append(
                {
                    "canonical_term": record.normalized_term,
                    "variant": normalized_alias,
                    "mega_category_id": record.mega_category_id,
                    "variant_type": "source_alias",
                    "source": record.source,
                    "generator_version": "stage7e_source_alias",
                }
            )
    return variants
