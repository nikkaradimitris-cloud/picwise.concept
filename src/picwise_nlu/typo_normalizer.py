from __future__ import annotations

import re
from typing import Any

from .normalizer import collapse_query_whitespace

_PHRASE_ALIAS_MAP = {
    "eficiency grim": "efficientgrip",
    "efficiency grim": "efficientgrip",
    "efisiency grip": "efficientgrip",
    "efficient grip": "efficientgrip",
    "fz 991": "fx 991",
    "fast chrge": "fast charge",
    "megali bataria": "μεγαλη μπαταρια",
    "pwer bank": "power bank",
}

_TOKEN_ALIAS_MAP = {
    "goodyar": "goodyear",
    "gudiar": "goodyear",
    "brizestone": "bridgestone",
    "bridgeston": "bridgestone",
    "micelin": "michelin",
    "continantal": "continental",
    "touransa": "turanza",
    "touranza": "turanza",
    "turansa": "turanza",
    "turan": "turanza",
    "pwer": "power",
    "chrge": "charge",
    "fz-991": "fx-991",
}

_GREEKLISH_TERM_MAP = {
    "kompiouteraki": "κομπιουτερακι",
    "kompiouterakia": "κομπιουτερακια",
    "panellinies": "πανελληνιες",
    "panelinies": "πανελληνιες",
    "aneto": "ανετο",
    "aneta": "ανετα",
    "isixo": "ησυχο",
    "fthino": "φτηνο",
    "oikonomiko": "οικονομικο",
    "grigoros": "γρηγορη",
    "fortistis": "φορτιστης",
    "bataria": "μπαταρια",
    "megali": "μεγαλη",
}


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _replace_whole_phrase(text: str, source: str, target: str) -> str:
    pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", flags=re.IGNORECASE)
    return pattern.sub(target, text)


def tokenize_for_alias_matching(text: str) -> list[str]:
    safe = collapse_query_whitespace(_safe_text(text))
    if not safe:
        return []
    return safe.split(" ")


def normalize_known_aliases(text: str) -> str:
    safe = collapse_query_whitespace(_safe_text(text))
    if not safe:
        return ""

    normalized = safe
    for source in sorted(_PHRASE_ALIAS_MAP, key=len, reverse=True):
        normalized = _replace_whole_phrase(normalized, source, _PHRASE_ALIAS_MAP[source])

    mapped_tokens: list[str] = []
    for token in tokenize_for_alias_matching(normalized):
        mapped_tokens.append(_TOKEN_ALIAS_MAP.get(token.lower(), token))

    return " ".join(mapped_tokens)


def normalize_greeklish_terms(text: str) -> str:
    safe = collapse_query_whitespace(_safe_text(text))
    if not safe:
        return ""

    mapped_tokens: list[str] = []
    for token in tokenize_for_alias_matching(safe):
        mapped_tokens.append(_GREEKLISH_TERM_MAP.get(token.lower(), token))

    return " ".join(mapped_tokens)


def normalize_greeklish_and_typos(text: str) -> str:
    safe = collapse_query_whitespace(_safe_text(text))
    if not safe:
        return ""

    normalized = normalize_known_aliases(safe)
    normalized = normalize_greeklish_terms(normalized)
    return collapse_query_whitespace(normalized)
