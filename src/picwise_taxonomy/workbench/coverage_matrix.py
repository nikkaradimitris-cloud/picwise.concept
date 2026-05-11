from __future__ import annotations

from collections import Counter
from copy import deepcopy


def _normalize_records(records: list[dict]) -> list[dict]:
    normalized = deepcopy(records)
    normalized.sort(
        key=lambda record: (
            str(record.get("engine_id", "")),
            str(record.get("mega_category_id", "")),
            str(record.get("taxonomy_id", "")),
            str(record.get("canonical_label", "")),
        )
    )
    return normalized


def _count_terms(records: list[dict], field: str) -> int:
    return sum(len(record.get(field, [])) for record in records if isinstance(record.get(field), list))


def summarize_coverage_by_engine(records: list[dict]) -> dict:
    normalized = _normalize_records(records)
    per_engine: dict[str, dict] = {}
    for record in normalized:
        engine_id = str(record.get("engine_id", "")).strip()
        if not engine_id:
            continue
        if engine_id not in per_engine:
            per_engine[engine_id] = {
                "record_count": 0,
                "departments": 0,
                "subcategories": 0,
                "product_families": 0,
                "gaps": 0,
            }
        node_type = str(record.get("node_type", "")).strip()
        per_engine[engine_id]["record_count"] += 1
        if node_type == "department":
            per_engine[engine_id]["departments"] += 1
        if node_type == "subcategory":
            per_engine[engine_id]["subcategories"] += 1
        if node_type == "product_family":
            per_engine[engine_id]["product_families"] += 1
        if node_type == "gap":
            per_engine[engine_id]["gaps"] += 1
    return dict(sorted(per_engine.items()))


def summarize_coverage_by_mega_category(records: list[dict]) -> dict:
    normalized = _normalize_records(records)
    per_mega: dict[str, dict] = {}
    for record in normalized:
        mega_category_id = str(record.get("mega_category_id", "")).strip()
        if not mega_category_id:
            continue
        if mega_category_id not in per_mega:
            per_mega[mega_category_id] = {
                "record_count": 0,
                "departments": 0,
                "subcategories": 0,
                "product_families": 0,
                "gaps": 0,
            }
        node_type = str(record.get("node_type", "")).strip()
        per_mega[mega_category_id]["record_count"] += 1
        if node_type == "department":
            per_mega[mega_category_id]["departments"] += 1
        if node_type == "subcategory":
            per_mega[mega_category_id]["subcategories"] += 1
        if node_type == "product_family":
            per_mega[mega_category_id]["product_families"] += 1
        if node_type == "gap":
            per_mega[mega_category_id]["gaps"] += 1
    return dict(sorted(per_mega.items()))


def detect_coverage_gaps(records: list[dict]) -> list[dict]:
    normalized = _normalize_records(records)
    weak_status = {"not_started", "weak", "partial", "blocked", "needs_review"}
    detected: list[dict] = []
    for record in normalized:
        node_type = str(record.get("node_type", "")).strip()
        coverage_status = str(record.get("coverage_status", "")).strip()
        if node_type == "gap" or coverage_status in weak_status:
            detected.append(
                {
                    "taxonomy_id": str(record.get("taxonomy_id", "")).strip(),
                    "canonical_label": str(record.get("canonical_label", "")).strip(),
                    "engine_id": str(record.get("engine_id", "")).strip(),
                    "mega_category_id": str(record.get("mega_category_id", "")).strip(),
                    "coverage_status": coverage_status,
                    "reason": "explicit_gap_node"
                    if node_type == "gap"
                    else "weak_or_missing_coverage_status",
                }
            )
    detected.sort(
        key=lambda item: (
            item["engine_id"],
            item["mega_category_id"],
            item["taxonomy_id"],
            item["canonical_label"],
        )
    )
    return detected


def build_coverage_matrix(records: list[dict]) -> dict:
    normalized = _normalize_records(records)
    status_counts = Counter(str(record.get("coverage_status", "")).strip() for record in normalized)
    node_counts = Counter(str(record.get("node_type", "")).strip() for record in normalized)
    engine_ids = sorted(
        {
            str(record.get("engine_id", "")).strip()
            for record in normalized
            if str(record.get("engine_id", "")).strip()
        }
    )
    mega_category_ids = sorted(
        {
            str(record.get("mega_category_id", "")).strip()
            for record in normalized
            if str(record.get("mega_category_id", "")).strip()
        }
    )

    matrix = {
        "record_count": len(normalized),
        "engines": len(engine_ids),
        "engine_ids": engine_ids,
        "mega_categories": len(mega_category_ids),
        "mega_category_ids": mega_category_ids,
        "departments": node_counts.get("department", 0),
        "subcategories": node_counts.get("subcategory", 0),
        "product_families": node_counts.get("product_family", 0),
        "aliases": _count_terms(normalized, "aliases"),
        "greek_aliases": _count_terms(normalized, "greek_aliases"),
        "greeklish_aliases": _count_terms(normalized, "greeklish_aliases"),
        "typo_aliases": _count_terms(normalized, "typo_aliases"),
        "spec_fields": _count_terms(normalized, "spec_fields"),
        "priority_terms": _count_terms(normalized, "priority_terms"),
        "intent_patterns": _count_terms(normalized, "intent_patterns"),
        "ambiguity_rules": _count_terms(normalized, "ambiguity_rules"),
        "gaps": node_counts.get("gap", 0),
        "coverage_status_counts": dict(sorted(status_counts.items())),
        "coverage_by_engine": summarize_coverage_by_engine(normalized),
        "coverage_by_mega_category": summarize_coverage_by_mega_category(normalized),
        "detected_gaps": detect_coverage_gaps(normalized),
    }
    return matrix
