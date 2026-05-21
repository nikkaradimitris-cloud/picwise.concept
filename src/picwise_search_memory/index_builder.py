from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import re

from picwise_nlu.query_variant_generator import _GENERATOR_VERSION as STAGE3_GENERATOR_VERSION
from picwise_nlu.query_variant_generator import generate_generic_english_noisy_variants

from .canonical_registry import build_canonical_vocabulary_registry
from .contracts import CanonicalVocabularyRegistry
from .index_contracts import SearchIndex, SearchIndexBuildReport, SearchIndexEntry
from .lookup_safety import (
    build_canonical_term_index_from_registry,
    derive_product_head_variants,
    derive_source_alias_variants,
    should_reject_generated_variant_for_index,
)
from .validation import normalize_term

_INDEX_SCHEMA_VERSION = "1.0.0"
_INDEX_SOURCE = "picwise_offline_search_index_builder_stage4"
_MIN_VARIANT_LENGTH = 3
_MAX_VARIANT_LENGTH = 80
_MAX_TOKEN_COUNT = 8
_SAFE_VARIANT_RE = re.compile(r"^[a-z0-9 ]+$")


def _stable_index_key(canonical_id: str, mega_category_id: str, normalized_variant: str) -> str:
    digest = hashlib.sha1(f"{canonical_id}|{mega_category_id}|{normalized_variant}".encode("utf-8")).hexdigest()[:20]
    return f"si_{digest}"


def _is_safe_index_variant(normalized_variant: str) -> bool:
    if not normalized_variant:
        return False
    if len(normalized_variant) < _MIN_VARIANT_LENGTH:
        return False
    if len(normalized_variant) > _MAX_VARIANT_LENGTH:
        return False
    if not _SAFE_VARIANT_RE.fullmatch(normalized_variant):
        return False
    tokens = normalized_variant.split()
    if not tokens:
        return False
    if len(tokens) > _MAX_TOKEN_COUNT:
        return False
    if any(len(token) < 2 for token in tokens):
        return False
    return True


def _build_entry(
    *,
    canonical_id: str,
    canonical_term: str,
    normalized_term: str,
    mega_category_id: str,
    variant: str,
    variant_type: str,
    source: str,
    canonical_source: str,
    canonical_status: str,
    generator_version: str,
    quality_flags: tuple[str, ...],
) -> SearchIndexEntry:
    normalized_variant = normalize_term(variant)
    return SearchIndexEntry(
        index_key=_stable_index_key(canonical_id, mega_category_id, normalized_variant),
        variant=variant,
        normalized_variant=normalized_variant,
        canonical_id=canonical_id,
        canonical_term=canonical_term,
        normalized_term=normalized_term,
        mega_category_id=mega_category_id,
        variant_type=variant_type,
        source=source,
        canonical_source=canonical_source,
        canonical_status=canonical_status,
        generator_version=generator_version,
        schema_version=_INDEX_SCHEMA_VERSION,
        token_count=len(normalized_variant.split()),
        quality_flags=quality_flags,
    )


def _derive_collision_flags(
    entries: list[SearchIndexEntry],
) -> tuple[
    dict[str, tuple[str, ...]],
    dict[str, int],
    dict[str, int],
    dict[str, int],
    int,
    int,
]:
    by_variant: dict[str, list[SearchIndexEntry]] = defaultdict(list)
    for entry in entries:
        by_variant[entry.normalized_variant].append(entry)

    collision_flags_by_key: dict[str, tuple[str, ...]] = {}
    collision_keys_by_variant_type: Counter[str] = Counter()
    collision_entries_by_variant_type: Counter[str] = Counter()
    collision_entries_by_category: Counter[str] = Counter()
    total_collision_keys = 0
    collision_entries_count = 0

    for variant, bucket in by_variant.items():
        if len(bucket) <= 1:
            continue
        canonical_ids = {entry.canonical_id for entry in bucket}
        category_ids = {entry.mega_category_id for entry in bucket}
        has_canonical_collision = len(canonical_ids) > 1
        has_cross_category_collision = len(category_ids) > 1
        if not has_canonical_collision and not has_cross_category_collision:
            continue

        total_collision_keys += 1
        collision_entries_count += len(bucket)
        for entry in bucket:
            flags = {"ambiguous_normalized_variant"}
            if has_canonical_collision:
                flags.add("exact_variant_collision")
            if has_cross_category_collision:
                flags.add("cross_category_collision")
            collision_flags_by_key[entry.index_key] = tuple(sorted(flags))
            collision_entries_by_variant_type[entry.variant_type] += 1
            collision_entries_by_category[entry.mega_category_id] += 1
        for variant_type in {entry.variant_type for entry in bucket}:
            collision_keys_by_variant_type[variant_type] += 1

    return (
        collision_flags_by_key,
        dict(sorted(collision_keys_by_variant_type.items())),
        dict(sorted(collision_entries_by_variant_type.items())),
        dict(sorted(collision_entries_by_category.items())),
        total_collision_keys,
        collision_entries_count,
    )


def build_offline_search_index(
    registry: CanonicalVocabularyRegistry | None = None,
    generated_variants: list[dict[str, str]] | None = None,
) -> SearchIndex:
    canonical_registry = registry or build_canonical_vocabulary_registry()

    record_by_signature: dict[tuple[str, str], dict[str, str]] = {}
    for record in canonical_registry.records:
        record_by_signature[(record.mega_category_id, record.normalized_term)] = {
            "canonical_id": record.canonical_id,
            "canonical_term": record.canonical_term,
            "normalized_term": record.normalized_term,
            "mega_category_id": record.mega_category_id,
            "canonical_source": record.source,
            "canonical_status": record.status,
            "canonical_flags": tuple(record.quality_flags),
        }

    canonical_term_index = build_canonical_term_index_from_registry(canonical_registry)

    variants = generated_variants
    if variants is None:
        vocab_by_category: dict[str, set[str]] = {}
        for record in canonical_registry.records:
            vocab_by_category.setdefault(record.mega_category_id, set()).add(record.canonical_term)
        variants = generate_generic_english_noisy_variants(
            vocab_by_category,
            source="taxonomy_clean_vocabulary",
            generator_version=STAGE3_GENERATOR_VERSION,
        )
        variants = [
            *variants,
            *derive_source_alias_variants(canonical_registry),
            *derive_product_head_variants(canonical_registry),
        ]

    entries: list[SearchIndexEntry] = []
    seen_signatures: set[tuple[str, str, str]] = set()
    duplicates_removed = 0
    rejected_count = 0
    counts_by_category: Counter[str] = Counter()
    counts_by_variant_type: Counter[str] = Counter()

    for record in sorted(canonical_registry.records, key=lambda row: (row.mega_category_id, row.normalized_term)):
        normalized_variant = normalize_term(record.canonical_term)
        signature = (normalized_variant, record.mega_category_id, record.canonical_id)
        # Stage 4 must include every canonical term as an exact variant.
        if not normalized_variant:
            rejected_count += 1
            continue
        if signature in seen_signatures:
            duplicates_removed += 1
            continue
        seen_signatures.add(signature)
        entry = _build_entry(
            canonical_id=record.canonical_id,
            canonical_term=record.canonical_term,
            normalized_term=record.normalized_term,
            mega_category_id=record.mega_category_id,
            variant=record.canonical_term,
            variant_type="exact_canonical",
            source=record.source,
            canonical_source=record.source,
            canonical_status=record.status,
            generator_version="stage4_exact_seed",
            quality_flags=tuple(sorted(set(record.quality_flags + ("offline_search_index", "exact_variant")))),
        )
        entries.append(entry)
        counts_by_category[entry.mega_category_id] += 1
        counts_by_variant_type[entry.variant_type] += 1

    for row in sorted(
        variants,
        key=lambda item: (
            str(item.get("mega_category_id", "")),
            normalize_term(item.get("canonical_term", "")),
            normalize_term(item.get("variant", "")),
            str(item.get("variant_type", "")),
        ),
    ):
        mega_category_id = str(row.get("mega_category_id", "")).strip()
        canonical_term = normalize_term(row.get("canonical_term", ""))
        normalized_variant = normalize_term(row.get("variant", ""))
        variant_type = str(row.get("variant_type", "")).strip() or "generated"
        source = str(row.get("source", "")).strip() or "taxonomy_clean_vocabulary"
        generator_version = str(row.get("generator_version", "")).strip() or STAGE3_GENERATOR_VERSION

        if not mega_category_id or not canonical_term or not normalized_variant:
            rejected_count += 1
            continue
        if not _is_safe_index_variant(normalized_variant):
            rejected_count += 1
            continue

        match = record_by_signature.get((mega_category_id, canonical_term))
        if not match:
            rejected_count += 1
            continue

        if should_reject_generated_variant_for_index(
            canonical_term=canonical_term,
            variant=normalized_variant,
            variant_type=variant_type,
            mega_category_id=mega_category_id,
            canonical_term_index=canonical_term_index,
        ):
            rejected_count += 1
            continue

        signature = (normalized_variant, mega_category_id, match["canonical_id"])
        if signature in seen_signatures:
            duplicates_removed += 1
            continue
        seen_signatures.add(signature)

        entry = _build_entry(
            canonical_id=match["canonical_id"],
            canonical_term=match["canonical_term"],
            normalized_term=match["normalized_term"],
            mega_category_id=mega_category_id,
            variant=row.get("variant", ""),
            variant_type=variant_type,
            source=source,
            canonical_source=match["canonical_source"],
            canonical_status=match["canonical_status"],
            generator_version=generator_version,
            quality_flags=tuple(
                sorted(
                    set(
                        (
                            "offline_search_index",
                            "generated_variant",
                            *match["canonical_flags"],
                        )
                    )
                )
            ),
        )
        entries.append(entry)
        counts_by_category[entry.mega_category_id] += 1
        counts_by_variant_type[entry.variant_type] += 1

    (
        collision_flags_by_key,
        collision_keys_by_variant_type,
        collision_entries_by_variant_type,
        collision_entries_by_category,
        total_collision_keys,
        collision_entries_count,
    ) = _derive_collision_flags(entries)

    enriched_entries: list[SearchIndexEntry] = []
    for entry in entries:
        extra_flags = collision_flags_by_key.get(entry.index_key, ())
        if not extra_flags:
            enriched_entries.append(entry)
            continue
        merged_flags = tuple(sorted(set(entry.quality_flags + extra_flags)))
        enriched_entries.append(
            SearchIndexEntry(
                index_key=entry.index_key,
                variant=entry.variant,
                normalized_variant=entry.normalized_variant,
                canonical_id=entry.canonical_id,
                canonical_term=entry.canonical_term,
                normalized_term=entry.normalized_term,
                mega_category_id=entry.mega_category_id,
                variant_type=entry.variant_type,
                source=entry.source,
                canonical_source=entry.canonical_source,
                canonical_status=entry.canonical_status,
                generator_version=entry.generator_version,
                schema_version=entry.schema_version,
                token_count=entry.token_count,
                quality_flags=merged_flags,
            )
        )

    ordered_entries = tuple(
        sorted(
            enriched_entries,
            key=lambda entry: (
                entry.mega_category_id,
                entry.canonical_id,
                entry.normalized_variant,
                entry.variant_type,
                entry.index_key,
            ),
        )
    )
    report = SearchIndexBuildReport(
        total_canonical_records=len(canonical_registry.records),
        total_generated_variants=len(variants),
        total_index_entries=len(ordered_entries),
        duplicates_removed=duplicates_removed,
        rejected_count=rejected_count,
        counts_by_mega_category_id=dict(sorted(counts_by_category.items())),
        counts_by_variant_type=dict(sorted(counts_by_variant_type.items())),
        total_collision_keys=total_collision_keys,
        collision_entries_count=collision_entries_count,
        collision_keys_by_variant_type=collision_keys_by_variant_type,
        collision_entries_by_variant_type=collision_entries_by_variant_type,
        collision_entries_by_mega_category_id=collision_entries_by_category,
        schema_version=_INDEX_SCHEMA_VERSION,
        source=_INDEX_SOURCE,
    )
    return SearchIndex(
        entries=ordered_entries,
        report=report,
        schema_version=_INDEX_SCHEMA_VERSION,
        source=_INDEX_SOURCE,
    )
