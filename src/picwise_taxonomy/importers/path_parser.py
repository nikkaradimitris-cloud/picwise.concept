from __future__ import annotations

import hashlib
import json

from picwise_taxonomy.workbench.source_item import build_source_item, validate_source_item


def split_taxonomy_path(path: str) -> list[str]:
    text = str(path or "").strip()
    if not text:
        return []
    return [segment.strip() for segment in text.split(">") if segment and segment.strip()]


def normalize_taxonomy_path(path: str) -> dict:
    raw_path = str(path or "").strip()
    path_segments = split_taxonomy_path(raw_path)
    normalized_path = " > ".join(path_segments)
    leaf_label = path_segments[-1] if path_segments else ""
    parent_label = path_segments[-2] if len(path_segments) >= 2 else ""
    return {
        "raw_path": raw_path,
        "path_segments": path_segments,
        "leaf_label": leaf_label,
        "parent_label": parent_label,
        "depth": len(path_segments),
        "normalized_path": normalized_path,
        "has_path": bool(path_segments),
        "is_empty_path": not bool(path_segments),
    }


def parse_taxonomy_path(path: str) -> dict:
    normalized = normalize_taxonomy_path(path)
    normalized["source_item_seed"] = {
        "raw_label": normalized["leaf_label"],
        "raw_parent_label": normalized["parent_label"],
        "raw_path": normalized["normalized_path"],
        "raw_metadata": {
            "path_segments": list(normalized["path_segments"]),
            "depth": normalized["depth"],
        },
    }
    return normalized


def _stable_source_item_id(source_name: str, source_type: str, normalized_path: str) -> str:
    payload = json.dumps(
        {
            "source_name": str(source_name or "").strip(),
            "source_type": str(source_type or "").strip(),
            "normalized_path": str(normalized_path or "").strip(),
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"source_path_{digest[:16]}"


def build_source_item_from_path(
    path: str,
    source_name: str,
    source_type: str = "manual_seed",
) -> dict:
    parsed = parse_taxonomy_path(path)
    source_item = build_source_item(
        source_item_id=_stable_source_item_id(
            source_name=source_name,
            source_type=source_type,
            normalized_path=parsed["normalized_path"],
        ),
        source_name=str(source_name or "").strip(),
        source_type=str(source_type or "manual_seed").strip() or "manual_seed",
        raw_label=parsed["leaf_label"],
        raw_parent_label=parsed["parent_label"],
        raw_path=parsed["normalized_path"],
        raw_metadata={
            "path_segments": list(parsed["path_segments"]),
            "depth": parsed["depth"],
            "normalized_path": parsed["normalized_path"],
        },
    )
    validation = validate_source_item(source_item)
    if not validation["valid"]:
        return validation["item"]
    return validation["item"]
