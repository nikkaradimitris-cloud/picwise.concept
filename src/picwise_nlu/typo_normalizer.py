from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .normalizer import collapse_query_whitespace, normalize_tire_size_text

_PHRASE_ALIAS_MAP = {
    "eficiency grim": "efficientgrip",
    "efficiency grim": "efficientgrip",
    "efisiency grip": "efficientgrip",
    "efficient grip": "efficientgrip",
    "fz 991": "fx 991",
    "fast chrge": "fast charge",
    "megali bataria": "μεγαλη μπαταρια",
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
    "handyakku": "battery pack",
    "akku pack": "battery pack",
    "akku pak": "battery pack",
    "powerbank fur handy": "power bank",
    "powerbank furs handy": "power bank",
    "10000mahpowerbank": "powerbank",
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
    "παουερ",
}

_BANK_TAIL_TERMS = {
    "bank",
    "μπανκ",
}

_PORTABLE_TERMS = {"portable", "φορητος", "φορητοσ"}
_CHARGER_NOISY_TERMS = {"charger"}
_BATTERY_NOISY_TERMS = {"battery", "μπαταρια"}
_PACK_NOISY_TERMS = {"pack"}

_POWER_BANK_COMPOUND_PATTERNS = (
    (re.compile(r"^(power)[\-_]?(bank)$"), ("power", "bank")),
    (re.compile(r"^(handy)(akku)$"), ("handy", "akku")),
    (re.compile(r"^(παουερ)[\-_]?(μπανκ)$"), ("power", "bank")),
)
_MAX_REPEAT_RE = re.compile(r"(.)\1{2,}")
_MIN_FUZZY_TOKEN_SCORE = 0.72
_MIN_JOINED_SPLIT_SCORE = 0.8


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


@lru_cache(maxsize=1)
def _token_lexicon() -> tuple[str, ...]:
    return (
        "power", "bank", "powerbank", "portable", "charger", "battery", "pack", "usb", "c", "charge",
        "goodyear", "bridgestone", "michelin", "continental", "turanza", "efficientgrip",
        "washing", "machine", "air", "fryer", "wireless", "headphones", "laptop", "office", "chair", "blender",
        "running", "shoes", "cordless", "drill", "blood", "pressure", "monitor", "screwdriver",
        "caliper", "garden", "hose", "leaf", "blower", "beard", "trimmer", "stroller", "leash",
        "jacket", "trousers", "watch", "handbag", "cable", "storage", "cabinet", "car", "tire", "tyre", "fx", "991",
    )


def _damerau_levenshtein(left: str, right: str, max_distance: int) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > max_distance:
        return max_distance + 1
    left_len = len(left)
    right_len = len(right)
    matrix = [[0] * (right_len + 1) for _ in range(left_len + 1)]
    for i in range(left_len + 1):
        matrix[i][0] = i
    for j in range(right_len + 1):
        matrix[0][j] = j
    for i in range(1, left_len + 1):
        row_min = max_distance + 1
        for j in range(1, right_len + 1):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            value = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost)
            if (
                i > 1
                and j > 1
                and left[i - 1] == right[j - 2]
                and left[i - 2] == right[j - 1]
            ):
                value = min(value, matrix[i - 2][j - 2] + 1)
            matrix[i][j] = value
            row_min = min(row_min, value)
        if row_min > max_distance:
            return max_distance + 1
    return matrix[left_len][right_len]


def _best_fuzzy_token_with_score(token: str) -> tuple[str, float]:
    lexicon = _token_lexicon()
    if token in lexicon or len(token) < 3 or not token.isalpha():
        return token, 1.0
    if len(token) <= 4:
        return token, 0.0
    max_distance = 1 if len(token) <= 4 else (2 if len(token) <= 6 else 2)
    best = token
    best_distance = max_distance + 1
    best_score = 0.0
    tie = False
    for candidate in lexicon:
        if candidate[0] != token[0]:
            continue
        if token.endswith("s") != candidate.endswith("s"):
            continue
        if not token.endswith("s") and candidate.endswith("s"):
            continue
        distance = _damerau_levenshtein(token, candidate, max_distance)
        if distance > max_distance:
            continue
        score = 1.0 - (distance / max(len(token), len(candidate)))
        if distance < best_distance:
            best = candidate
            best_distance = distance
            best_score = score
            tie = False
        elif distance == best_distance and candidate != best:
            tie = True
            if score == best_score:
                tie = True
    if tie or best_score < _MIN_FUZZY_TOKEN_SCORE:
        return token, 0.0
    return best, round(best_score, 2)


def _best_fuzzy_token(token: str) -> str:
    resolved, _ = _best_fuzzy_token_with_score(token)
    return resolved


def _split_joined_token(token: str) -> list[str]:
    lexicon = set(_token_lexicon())
    if token in lexicon or len(token) < 8:
        return [token]
    for idx in range(3, len(token) - 2):
        left = token[:idx]
        right = token[idx:]
        if left in lexicon and right in lexicon:
            return [left, right]
        left_candidate, left_score = _best_fuzzy_token_with_score(left)
        right_candidate, right_score = _best_fuzzy_token_with_score(right)
        left_exact = left_candidate == left and left in lexicon
        right_exact = right_candidate == right and right in lexicon
        if (
            left_candidate in lexicon
            and right_candidate in lexicon
            and (left_exact or right_exact)
            and ((left_score + right_score) / 2) >= _MIN_JOINED_SPLIT_SCORE
        ):
            return [left_candidate, right_candidate]
    return [token]


def _collapse_repeats(token: str) -> str:
    if not token.isalpha():
        return token
    return _MAX_REPEAT_RE.sub(r"\1\1", token)


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


def _is_power_like(token: str) -> bool:
    return _damerau_levenshtein(token, "power", 2) <= 2


def _is_bank_like(token: str) -> bool:
    return _damerau_levenshtein(token, "bank", 1) <= 1


def _is_charger_like(token: str) -> bool:
    return _damerau_levenshtein(token, "charger", 2) <= 2


def _is_battery_like(token: str) -> bool:
    if token in {"akku", "batterie"}:
        return True
    return _damerau_levenshtein(token, "battery", 2) <= 2


def _is_pack_like(token: str) -> bool:
    return _damerau_levenshtein(token, "pack", 1) <= 1


def _apply_context_aware_noisy_corrections(tokens: list[str]) -> list[str]:
    if not tokens:
        return []

    corrected = list(tokens)
    for idx, token in enumerate(tokens):
        lowered = token.lower()
        left = tokens[idx - 1].lower() if idx - 1 >= 0 else ""
        right = tokens[idx + 1].lower() if idx + 1 < len(tokens) else ""

        if _is_power_like(lowered) and (_is_bank_like(left) or _is_bank_like(right)):
            corrected[idx] = "power"
            continue

        if _is_bank_like(lowered) and (_is_power_like(left) or _is_power_like(right)):
            corrected[idx] = "bank"
            continue

        if _is_charger_like(lowered) and _has_neighbor(tokens, idx, _PORTABLE_TERMS):
            corrected[idx] = "charger"
            continue

        if _is_battery_like(lowered) and (_is_pack_like(left) or _is_pack_like(right)):
            corrected[idx] = "battery"
            continue
        if _is_battery_like(lowered) and (left in {"externe", "external", "extern"} or right in {"externe", "external", "extern"}):
            corrected[idx] = "battery"
            continue

        if _is_pack_like(lowered) and (_is_battery_like(left) or _is_battery_like(right)):
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
    normalized = re.sub(
        r"(?<!\w)παουερ[\s\-_]*μπ[^\s]*(?!\w)",
        "power bank",
        normalized,
        flags=re.IGNORECASE,
    )

    tokens = tokenize_for_alias_matching(normalized)
    tokens = _expand_compound_tokens(tokens)
    tokens = _apply_context_aware_noisy_corrections(tokens)

    mapped_tokens: list[str] = []
    for token in tokens:
        lowered = _collapse_repeats(token.lower())
        if lowered in {"goodyar", "gudiar"}:
            lowered = "goodyear"
        if lowered == "bankk":
            lowered = "bank"
        for split_token in _split_joined_token(lowered):
            mapped_tokens.append(_best_fuzzy_token(split_token))

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
    normalized = normalize_tire_size_text(normalized)
    return collapse_query_whitespace(normalized)
