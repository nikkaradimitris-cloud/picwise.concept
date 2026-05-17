from __future__ import annotations

from collections import Counter

from picwise_nlu.vocabulary_source import load_clean_vocab_by_mega_category

from .contracts import CanonicalVocabularyBuildReport, CanonicalVocabularyRecord, CanonicalVocabularyRegistry
from .validation import known_mega_category_ids, normalize_term, stable_canonical_id, validate_registry

_SCHEMA_VERSION = "1.0.0"
_SOURCE = "taxonomy_clean_vocabulary"
_LANGUAGE = "english"
_STATUS = "active"
_MIN_TERM_LENGTH = 3
_MAX_TERM_LENGTH = 80
_MAX_TOKEN_COUNT = 8
_OUT_OF_SCOPE_KEYWORDS = {
    "saas",
    "erp",
    "finance",
    "insurance",
    "loan",
    "broker",
    "banking",
}


def _is_retail_scope_term(normalized_term: str) -> bool:
    tokens = set(normalized_term.split())
    return _OUT_OF_SCOPE_KEYWORDS.isdisjoint(tokens)


def _reject_reason(term: str, mega_category_id: str, known_categories: set[str]) -> str:
    normalized = normalize_term(term)
    if not normalized:
        return "empty"
    if len(normalized) < _MIN_TERM_LENGTH:
        return "too_short"
    if len(normalized) > _MAX_TERM_LENGTH:
        return "too_long"
    if len(normalized.split()) > _MAX_TOKEN_COUNT:
        return "too_many_tokens"
    if mega_category_id not in known_categories:
        return "unknown_mega_category_id"
    if not _is_retail_scope_term(normalized):
        return "out_of_scope_vertical"
    return ""


def _build_record(
    *,
    mega_category_id: str,
    normalized_term: str,
    source_file: str,
    source_path: str,
) -> CanonicalVocabularyRecord:
    token_count = len(normalized_term.split())
    quality_flags = ("offline_registry", "validated_english_retail")
    return CanonicalVocabularyRecord(
        canonical_id=stable_canonical_id(mega_category_id, normalized_term),
        canonical_term=normalized_term,
        normalized_term=normalized_term,
        mega_category_id=mega_category_id,
        source=_SOURCE,
        source_file=source_file,
        language=_LANGUAGE,
        status=_STATUS,
        schema_version=_SCHEMA_VERSION,
        token_count=token_count,
        quality_flags=quality_flags,
        aliases=(),
        product_family="",
        source_path=source_path,
        confidence_weight=1.0,
    )


def build_canonical_vocabulary_registry() -> CanonicalVocabularyRegistry:
    raw_vocab = load_clean_vocab_by_mega_category()
    known_categories = known_mega_category_ids()

    records: list[CanonicalVocabularyRecord] = []
    rejected_by_reason: Counter[str] = Counter()
    counts_by_mega_category: Counter[str] = Counter()
    dedupe_signatures: set[tuple[str, str]] = set()
    total_input_terms = 0
    duplicate_terms = 0

    for mega_category_id in sorted(raw_vocab.keys()):
        terms = raw_vocab.get(mega_category_id) or set()
        iterable = terms if isinstance(terms, (set, list, tuple)) else []
        for term in sorted(iterable):
            total_input_terms += 1
            reason = _reject_reason(term, mega_category_id, known_categories)
            if reason:
                rejected_by_reason[reason] += 1
                continue

            normalized = normalize_term(term)
            signature = (mega_category_id, normalized)
            if signature in dedupe_signatures:
                duplicate_terms += 1
                rejected_by_reason["duplicate"] += 1
                continue
            dedupe_signatures.add(signature)

            records.append(
                _build_record(
                    mega_category_id=mega_category_id,
                    normalized_term=normalized,
                    source_file="vocabulary_source.py",
                    source_path="src/picwise_nlu/vocabulary_source.py",
                )
            )
            counts_by_mega_category[mega_category_id] += 1

    ordered_records = tuple(sorted(records, key=lambda row: (row.mega_category_id, row.normalized_term)))
    report = CanonicalVocabularyBuildReport(
        total_input_terms=total_input_terms,
        total_records=len(ordered_records),
        rejected_terms=sum(rejected_by_reason.values()),
        duplicate_terms=duplicate_terms,
        rejected_by_reason=dict(sorted(rejected_by_reason.items())),
        counts_by_mega_category=dict(sorted(counts_by_mega_category.items())),
        source=_SOURCE,
        schema_version=_SCHEMA_VERSION,
        language=_LANGUAGE,
        status=_STATUS,
    )
    registry = CanonicalVocabularyRegistry(
        records=ordered_records,
        report=report,
        source=_SOURCE,
        schema_version=_SCHEMA_VERSION,
    )
    validation_result = validate_registry(registry)
    if not validation_result["valid"]:
        reasons = ", ".join(validation_result["reasons"])  # type: ignore[arg-type]
        raise ValueError(f"Canonical vocabulary registry validation failed: {reasons}")
    return registry
