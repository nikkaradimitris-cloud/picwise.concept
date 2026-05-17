from __future__ import annotations

import hashlib
import re

from picwise_taxonomy.mega_category_registry import get_mega_category_registry

from .contracts import CanonicalVocabularyRecord, CanonicalVocabularyRegistry

_FORBIDDEN_FIELDS = {
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "prices",
    "affiliate",
    "affiliate_url",
    "seller",
    "stock",
    "checkout",
}
_ALLOWED_LANGUAGE = "english"
_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_term(value: object) -> str:
    compact = " ".join(str(value or "").split()).strip().lower()
    return _NORMALIZE_RE.sub(" ", compact).strip()


def stable_canonical_id(mega_category_id: str, normalized_term: str) -> str:
    digest = hashlib.sha1(f"{mega_category_id}|{normalized_term}".encode("utf-8")).hexdigest()[:16]
    return f"cv_{digest}"


def known_mega_category_ids() -> set[str]:
    return {
        str(row.get("mega_category_id", "")).strip()
        for row in get_mega_category_registry()
        if str(row.get("mega_category_id", "")).strip()
    }


def record_has_forbidden_fields(record: CanonicalVocabularyRecord) -> bool:
    keys = set(record.to_dict().keys())
    return not _FORBIDDEN_FIELDS.isdisjoint({key.lower() for key in keys})


def validate_record(record: CanonicalVocabularyRecord, allowed_mega_categories: set[str] | None = None) -> list[str]:
    reasons: list[str] = []
    known_categories = allowed_mega_categories if isinstance(allowed_mega_categories, set) else known_mega_category_ids()
    required_fields = (
        "canonical_id",
        "canonical_term",
        "normalized_term",
        "mega_category_id",
        "source",
        "source_file",
        "language",
        "status",
        "schema_version",
        "token_count",
        "quality_flags",
    )
    payload = record.to_dict()
    for field_name in required_fields:
        if field_name not in payload:
            reasons.append(f"missing_required_field:{field_name}")
            continue
        value = payload[field_name]
        if isinstance(value, str) and not value.strip():
            reasons.append(f"empty_required_field:{field_name}")

    expected_id = stable_canonical_id(record.mega_category_id, record.normalized_term)
    if record.canonical_id != expected_id:
        reasons.append("canonical_id_not_stable")
    if not record.normalized_term.strip():
        reasons.append("normalized_term_empty")
    if record.mega_category_id not in known_categories:
        reasons.append("unknown_mega_category_id")
    if record.language.strip().lower() != _ALLOWED_LANGUAGE:
        reasons.append("language_not_english")
    if record_has_forbidden_fields(record):
        reasons.append("forbidden_commercial_field_present")
    if record.token_count <= 0:
        reasons.append("invalid_token_count")
    if "fake_data" in {flag.lower() for flag in record.quality_flags}:
        reasons.append("fake_data_flag_present")
    return reasons


def validate_registry(registry: CanonicalVocabularyRegistry) -> dict[str, object]:
    reasons: list[str] = []
    by_category_term: set[tuple[str, str]] = set()

    for record in registry.records:
        record_reasons = validate_record(record)
        reasons.extend(record_reasons)
        signature = (record.mega_category_id, record.normalized_term)
        if signature in by_category_term:
            reasons.append("duplicate_normalized_term_per_category")
        by_category_term.add(signature)

    valid = len(reasons) == 0
    return {
        "valid": valid,
        "reasons": tuple(sorted(set(reasons))),
        "total_records": len(registry.records),
        "offline_only": True,
    }
