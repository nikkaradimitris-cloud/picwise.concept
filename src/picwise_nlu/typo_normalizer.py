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
    "powr bank": "power bank",
    "powerbnk": "powerbank",
    "power pank": "power bank",
    "power bankk": "power bank",
    "portable chrger": "portable charger",
    "batery pack": "battery pack",
    "battery pak": "battery pack",
    "παουερ μπανκ": "power bank",
    "παουερμπανκ": "power bank",
    "φορητος φορτιστης": "portable charger",
    "φορητοσ φορτιστησ": "portable charger",
    "εξωτερικη μπαταρια": "battery pack",
    "μπαταρια κινητου": "battery pack",
    "φορτιστης χωρις πριζα": "portable charger",
    "tragbares ladegerat": "portable charger",
    "externe batterie": "battery pack",
    "externe baterie": "battery pack",
    "handy akku": "battery pack",
    "akku pack": "battery pack",
    "akku pak": "battery pack",
    "powerbank fur handy": "power bank",
    "powerbank furs handy": "power bank",
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
    "powr": "power",
    "powerbnk": "powerbank",
    "bankk": "bank",
    "chrger": "charger",
    "batery": "battery",
    "pak": "pack",
    "usbc": "usb c",
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

_POWER_HEAD_TERMS = {
    "power",
    "pauer",
    "paouer",
    "powe",
    "powr",
    "pwer",
    "παουερ",
}

_BANK_TAIL_TERMS = {
    "bank",
    "bang",
    "bak",
    "bnk",
    "μπανκ",
    "μπακ",
    "μπανγκ",
}

_PORTABLE_TERMS = {"portable", "φορητος", "φορητοσ"}
_CHARGER_NOISY_TERMS = {"charger", "chargr", "chargar", "chrger"}
_BATTERY_NOISY_TERMS = {"battery", "batery", "μπαταρια"}
_PACK_NOISY_TERMS = {"pack", "pak"}

_POWER_BANK_COMPOUND_PATTERNS = (
    (re.compile(r"^(power|pauer|paouer|powe|powr|pwer)[\-_]?(bank|bang|bak|bnk)$"), ("power", "bank")),
    (re.compile(r"^(παουερ)[\-_]?(μπανκ|μπακ|μπανγκ)$"), ("power", "bank")),
)


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


def _expand_compound_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    for token in tokens:
        lowered = token.lower()
        replaced = False
        for pattern, normalized_pair in _POWER_BANK_COMPOUND_PATTERNS:
            if pattern.match(lowered):
                expanded.extend(normalized_pair)
                replaced = True
                break
        if not replaced:
            expanded.append(token)
    return expanded


def _has_neighbor(tokens: list[str], idx: int, allowed_terms: set[str]) -> bool:
    left = tokens[idx - 1].lower() if idx - 1 >= 0 else ""
    right = tokens[idx + 1].lower() if idx + 1 < len(tokens) else ""
    return left in allowed_terms or right in allowed_terms


def _apply_context_aware_noisy_corrections(tokens: list[str]) -> list[str]:
    if not tokens:
        return []

    corrected = list(tokens)
    for idx, token in enumerate(tokens):
        lowered = token.lower()

        if lowered in _POWER_HEAD_TERMS and _has_neighbor(tokens, idx, _BANK_TAIL_TERMS):
            corrected[idx] = "power"
            continue
        if lowered in _BANK_TAIL_TERMS and _has_neighbor(tokens, idx, _POWER_HEAD_TERMS):
            corrected[idx] = "bank"
            continue
        if lowered in _CHARGER_NOISY_TERMS and _has_neighbor(tokens, idx, _PORTABLE_TERMS):
            corrected[idx] = "charger"
            continue
        if lowered in _BATTERY_NOISY_TERMS and _has_neighbor(tokens, idx, _PACK_NOISY_TERMS):
            corrected[idx] = "battery"
            continue
        if lowered in _PACK_NOISY_TERMS and _has_neighbor(tokens, idx, _BATTERY_NOISY_TERMS):
            corrected[idx] = "pack"
            continue

    return corrected


def normalize_known_aliases(text: str) -> str:
    safe = collapse_query_whitespace(_safe_text(text))
    if not safe:
        return ""

    normalized = safe
    for source in sorted(_PHRASE_ALIAS_MAP, key=len, reverse=True):
        normalized = _replace_whole_phrase(normalized, source, _PHRASE_ALIAS_MAP[source])

    tokens = tokenize_for_alias_matching(normalized)
    tokens = _expand_compound_tokens(tokens)
    tokens = _apply_context_aware_noisy_corrections(tokens)

    mapped_tokens: list[str] = []
    for token in tokens:
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
