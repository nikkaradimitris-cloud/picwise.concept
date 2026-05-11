from __future__ import annotations

from pathlib import Path

from .path_parser import build_source_item_from_path

_GOOGLE_SOURCE_NAME = "google_product_taxonomy"
_GOOGLE_SOURCE_TYPE = "public_taxonomy_reference"


def _extract_google_path(line: str) -> str:
    cleaned = str(line or "").strip()
    if " - " in cleaned:
        left, right = cleaned.split(" - ", 1)
        if left.strip().isdigit():
            return right.strip()
    return cleaned


def _is_ignored_line(line: str) -> bool:
    cleaned = str(line or "").strip()
    if not cleaned:
        return True
    lowered = cleaned.lower()
    if lowered.startswith("#"):
        return True
    if lowered.startswith("//"):
        return True
    if lowered.startswith("id,"):
        return True
    if lowered.startswith("google_product_taxonomy"):
        return True
    if "taxonomy version" in lowered:
        return True
    return False


def parse_google_taxonomy_lines(lines: list[str]) -> list[dict]:
    items: list[dict] = []
    for line in lines or []:
        if _is_ignored_line(line):
            continue
        path = _extract_google_path(line)
        parsed_item = build_source_item_from_path(
            path=path,
            source_name=_GOOGLE_SOURCE_NAME,
            source_type=_GOOGLE_SOURCE_TYPE,
        )
        if parsed_item.get("raw_path"):
            items.append(parsed_item)
    return items


def parse_google_taxonomy_text(text: str) -> list[dict]:
    lines = str(text or "").splitlines()
    return parse_google_taxonomy_lines(lines)


def parse_google_taxonomy_file(file_path: str) -> list[dict]:
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    return parse_google_taxonomy_text(text)


def summarize_google_taxonomy_import(items: list[dict]) -> dict:
    parsed_items = items or []
    unique_paths = sorted(
        {str(item.get("raw_path", "")).strip() for item in parsed_items if str(item.get("raw_path", "")).strip()}
    )
    depth_values = [int(item.get("raw_metadata", {}).get("depth", 0)) for item in parsed_items]
    return {
        "source_name": _GOOGLE_SOURCE_NAME,
        "source_type": _GOOGLE_SOURCE_TYPE,
        "total_items": len(parsed_items),
        "unique_path_count": len(unique_paths),
        "max_depth": max(depth_values) if depth_values else 0,
        "min_depth": min(depth_values) if depth_values else 0,
        "sample_paths": unique_paths[:5],
        "local_file_or_text_only": True,
        "network_calls_used": False,
        "external_downloads_used": False,
    }
