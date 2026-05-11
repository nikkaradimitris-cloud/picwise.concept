from __future__ import annotations

from collections import Counter

from .gap_router import route_mapping_result_to_gap
from .mapper import map_source_item_to_taxonomy
from .validation import build_mapping_catalog


def map_source_items_batch(source_items: list[dict]) -> dict:
    catalog = build_mapping_catalog()
    mapped_results: list[dict] = []
    gap_results: list[dict] = []
    status_counter: Counter[str] = Counter()
    engine_counter: Counter[str] = Counter()
    mega_counter: Counter[str] = Counter()

    for source_item in source_items or []:
        mapping_result = map_source_item_to_taxonomy(source_item, catalog=catalog)
        result_payload = mapping_result.to_dict()
        mapped_results.append(result_payload)
        status_counter[result_payload["status"]] += 1

        target = result_payload.get("target") or {}
        if target.get("engine_id"):
            engine_counter[target["engine_id"]] += 1
        if target.get("mega_category_id"):
            mega_counter[target["mega_category_id"]] += 1

        gap_payload = route_mapping_result_to_gap(mapping_result, source_item=source_item)
        if gap_payload is not None:
            gap_results.append(gap_payload)

    return {
        "mapped_results": mapped_results,
        "gap_results": gap_results,
        "summary": {
            "total_items": len(source_items or []),
            "status_counts": dict(sorted(status_counter.items())),
            "engine_counts": dict(sorted(engine_counter.items())),
            "mega_category_counts": dict(sorted(mega_counter.items())),
            "gap_count": len(gap_results),
        },
    }
