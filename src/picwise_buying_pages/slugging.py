from __future__ import annotations

import re
import unicodedata


def normalize_keyword_text(value: str) -> str:
    """Normalize a keyword/alias to a deterministic matching key."""
    ascii_value = (
        unicodedata.normalize("NFKD", str(value))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    collapsed = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return " ".join(collapsed.split())


def slugify_keyword(value: str) -> str:
    """Generate canonical deterministic slug from keyword text."""
    normalized = normalize_keyword_text(value)
    return normalized.replace(" ", "-")
