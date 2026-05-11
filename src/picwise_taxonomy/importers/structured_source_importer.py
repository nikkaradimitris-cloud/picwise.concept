from __future__ import annotations

import csv
import io
import json

from picwise_taxonomy.workbench.source_item import build_source_item, validate_source_item

from .import_validation import reject_inventory_like_source_record
from .path_parser import normalize_taxonomy_path, split_taxonomy_path


def _normalize_aliases(value: object) -> list[str]:
    if isinstance(value, list):
        aliases = [str(item).strip() for item in value]
    elif isinstance(value, str):
        aliases = [segment.strip() for segment in value.replace("|", ",").split(",")]
    else:
        aliases = []
    return sorted({alias for alias in aliases if alias})


def _build_path_from_record(record: dict) -> str:
    path = str(record.get("path", "")).strip()
    if path:
        return path
    label = str(record.get("label", "")).strip()
    parent = str(record.get("parent", "")).strip()
    if parent and label:
        return f"{parent} > {label}"
    return label


def _stable_record_source_item_id(source_name: str, source_type: str, parsed_path: dict) -> str:
    normalized_path = str(parsed_path.get("normalized_path", "")).strip()
    if normalized_path:
        from .path_parser import _stable_source_item_id

        return _stable_source_item_id(source_name, source_type, normalized_path)
    raw_label = str(parsed_path.get("leaf_label", "")).strip()
    basis = f"{source_name}|{source_type}|{raw_label}"
    import hashlib

    return f"source_record_{hashlib.sha1(basis.encode('utf-8')).hexdigest()[:16]}"


def import_source_records(records: list[dict], source_name: str, source_type: str) -> list[dict]:
    items: list[dict] = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        inventory_check = reject_inventory_like_source_record(record)
        if not inventory_check["valid"]:
            continue

        path = _build_path_from_record(record)
        parsed = normalize_taxonomy_path(path)
        if not parsed["path_segments"]:
            continue

        source_item = build_source_item(
            source_item_id=_stable_record_source_item_id(source_name, source_type, parsed),
            source_name=str(source_name or "").strip(),
            source_type=str(source_type or "").strip(),
            raw_label=parsed["leaf_label"] or str(record.get("label", "")).strip(),
            raw_parent_label=parsed["parent_label"] or str(record.get("parent", "")).strip(),
            raw_path=parsed["normalized_path"],
            raw_metadata={
                "path_segments": split_taxonomy_path(parsed["normalized_path"]),
                "depth": parsed["depth"],
                "normalized_path": parsed["normalized_path"],
                "source_metadata": record.get("metadata", {}) if isinstance(record.get("metadata"), dict) else {},
            },
            proposed_aliases=_normalize_aliases(record.get("aliases")),
        )
        validated = validate_source_item(source_item)
        if validated["valid"]:
            items.append(validated["item"])
    return items


def import_source_json_text(
    json_text: str,
    source_name: str,
    source_type: str = "json_import",
) -> list[dict]:
    payload = json.loads(str(json_text or "[]"))
    records: list[dict]
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        records = payload["records"]
    else:
        records = []
    return import_source_records(records, source_name=source_name, source_type=source_type)


def import_source_csv_text(
    csv_text: str,
    source_name: str,
    source_type: str = "csv_import",
) -> list[dict]:
    buffer = io.StringIO(str(csv_text or ""))
    reader = csv.DictReader(buffer)
    records: list[dict] = []
    for row in reader:
        aliases = row.get("aliases", "")
        records.append(
            {
                "path": row.get("path", ""),
                "label": row.get("label", ""),
                "parent": row.get("parent", ""),
                "aliases": aliases,
                "metadata": {},
            }
        )
    return import_source_records(records, source_name=source_name, source_type=source_type)


def summarize_source_import(items: list[dict]) -> dict:
    imported_items = items or []
    unique_sources = sorted(
        {
            (str(item.get("source_name", "")).strip(), str(item.get("source_type", "")).strip())
            for item in imported_items
        }
    )
    aliases_count = sum(len(item.get("proposed_aliases", [])) for item in imported_items)
    return {
        "total_items": len(imported_items),
        "unique_source_count": len(unique_sources),
        "sources": [{"source_name": name, "source_type": kind} for name, kind in unique_sources],
        "with_aliases_count": sum(1 for item in imported_items if item.get("proposed_aliases")),
        "total_aliases": aliases_count,
        "json_serializable": True,
        "inventory_free_import": True,
    }
