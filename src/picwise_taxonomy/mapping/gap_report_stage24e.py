from __future__ import annotations

from collections import Counter

from .gap_router import route_mapping_payload_to_gap
from .validation import normalize_path_segments

STAGE_24E_TITLE = "Stage 24E — Unmapped / Gap Report"
_SUPPORTED_GOOGLE_TOP_LEVELS = {
    "apparel accessories",
    "electronics",
    "home garden",
    "vehicles parts",
}
_DO_NOT_OVERRIDE_REASON_CODES = {
    "invalid_source_item",
    "forbidden_inventory_field",
    "ambiguous_engine",
    "ambiguous_mega_category",
    "unknown_department",
    "unknown_subcategory",
    "unknown_product_family",
    "no_engine_match",
}


def _index_source_items(source_items: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for source_item in source_items or []:
        source_item_id = str(source_item.get("source_item_id", "")).strip()
        if source_item_id:
            indexed[source_item_id] = source_item
    return indexed


def _should_mark_unsupported_google_path(mapping_payload: dict, source_item: dict) -> bool:
    reason_code = str(mapping_payload.get("gap_reason", "")).strip()
    if reason_code in _DO_NOT_OVERRIDE_REASON_CODES:
        return False
    source_name = str(source_item.get("source_name", "")).strip()
    source_type = str(source_item.get("source_type", "")).strip()
    if source_name != "google_product_taxonomy" and source_type != "public_taxonomy_reference":
        return False
    normalized_path = normalize_path_segments(str(source_item.get("raw_path", "")).strip())
    if not normalized_path:
        return False
    return normalized_path[0] not in _SUPPORTED_GOOGLE_TOP_LEVELS


def build_stage24e_gap_report(
    *,
    source_items: list[dict],
    mapped_results: list[dict],
) -> dict:
    source_items_index = _index_source_items(source_items or [])
    reason_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    confidence_counter: Counter[str] = Counter()
    gap_records: list[dict] = []
    ordered_results = sorted(
        (mapped_results or []),
        key=lambda item: (
            str(item.get("source_item_id", "")).strip(),
            str(item.get("status", "")).strip(),
        ),
    )
    for mapping_payload in ordered_results:
        status = str(mapping_payload.get("status", "")).strip()
        status_counter[status] += 1
        source_item_id = str(mapping_payload.get("source_item_id", "")).strip()
        source_item = source_items_index.get(source_item_id, {"source_item_id": source_item_id})
        reason_override = ""
        if _should_mark_unsupported_google_path(mapping_payload, source_item):
            reason_override = "unsupported_google_path"
        gap_record = route_mapping_payload_to_gap(
            mapping_payload,
            source_item=source_item,
            reason_code_override=reason_override,
        )
        if gap_record is None:
            continue
        reason_counter[gap_record["reason_code"]] += 1
        confidence_counter[str(gap_record.get("confidence", "")).strip()] += 1
        gap_records.append(gap_record)

    deterministic_gap_records = sorted(gap_records, key=lambda record: str(record.get("gap_id", "")).strip())
    return {
        "stage": STAGE_24E_TITLE,
        "source_name": "google_product_taxonomy",
        "source_item_count": len(source_items or []),
        "mapping_result_count": len(mapped_results or []),
        "gap_records": deterministic_gap_records,
        "summary": {
            "gap_count": len(deterministic_gap_records),
            "reason_counts": dict(sorted(reason_counter.items())),
            "mapping_status_counts": dict(sorted(status_counter.items())),
            "confidence_counts": dict(sorted(confidence_counter.items())),
            "deterministic_ordering": True,
        },
        "canonical_registry_created": False,
        "coverage_matrix_created": False,
        "dedup_rules_created": False,
    }
