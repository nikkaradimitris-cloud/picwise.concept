from __future__ import annotations

import re
import unicodedata
from typing import Any

_TIRE_SIZE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?P<width>\d{3})"
    r"\s*[/\-\s]\s*"
    r"(?P<aspect>\d{2})"
    r"\s*(?:[/\-\s]?\s*[Rr]?\s*)"
    r"(?P<rim>\d{2})"
    r"(?!\d)"
)


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def strip_diacritics(text: str) -> str:
    safe = _safe_text(text)
    if not safe:
        return ""
    decomposed = unicodedata.normalize("NFD", safe)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def collapse_query_whitespace(text: str) -> str:
    safe = _safe_text(text)
    if not safe:
        return ""
    normalized = re.sub(r"[\t\r\n]+", " ", safe)
    return " ".join(normalized.split())


def _is_plausible_tire_size(width: str, aspect: str, rim: str) -> bool:
    try:
        width_n = int(width)
        aspect_n = int(aspect)
        rim_n = int(rim)
    except (TypeError, ValueError):
        return False
    return 125 <= width_n <= 395 and 25 <= aspect_n <= 95 and 10 <= rim_n <= 30


def normalize_tire_size_text(text: str) -> str:
    safe = _safe_text(text)
    if not safe:
        return ""

    def _replace(match: re.Match[str]) -> str:
        width = match.group("width")
        aspect = match.group("aspect")
        rim = match.group("rim")
        if not _is_plausible_tire_size(width, aspect, rim):
            return match.group(0)
        return f"{int(width)}/{int(aspect)} R{int(rim)}"

    return _TIRE_SIZE_PATTERN.sub(_replace, safe)


def normalize_query(raw_query: str) -> str:
    safe = _safe_text(raw_query)
    if not safe:
        return ""

    normalized = strip_diacritics(safe).lower()
    normalized = normalized.replace("_", " ")
    normalized = re.sub(r"[^\w\s/\-]", " ", normalized)
    normalized = normalize_tire_size_text(normalized)
    return collapse_query_whitespace(normalized)
