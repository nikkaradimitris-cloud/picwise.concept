from __future__ import annotations

import re
from typing import Any

_BRAND_ALIAS_TO_CANONICAL = {
    "goodyear": "Goodyear",
    "bridgestone": "Bridgestone",
    "michelin": "Michelin",
    "continental": "Continental",
    "casio": "Casio",
    "anker": "Anker",
    "xiaomi": "Xiaomi",
    "samsung": "Samsung",
    "belkin": "Belkin",
}

_CATEGORY_BRAND_HINTS = {
    "car_tyres": {"Goodyear", "Bridgestone", "Michelin", "Continental"},
    "calculators": {"Casio"},
    "power_banks": {"Anker", "Xiaomi", "Samsung", "Belkin"},
}


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return ""


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def resolve_brand_candidates(text: str, category: str | None = None) -> dict:
    safe = _safe_text(text).lower()
    if not safe:
        return {"brand_candidates": [], "confidence": 0.0, "reason_codes": ["empty_input"]}

    candidates: list[str] = []
    reason_codes: list[str] = []

    for alias, canonical in _BRAND_ALIAS_TO_CANONICAL.items():
        if _contains_term(safe, alias) and canonical not in candidates:
            candidates.append(canonical)
            reason_codes.append(f"brand_match_{alias}")

    if not candidates:
        return {"brand_candidates": [], "confidence": 0.0, "reason_codes": ["no_brand_match"]}

    confidence = min(0.95, 0.3 + (0.2 * len(candidates)))
    if category in _CATEGORY_BRAND_HINTS and any(
        candidate in _CATEGORY_BRAND_HINTS[category] for candidate in candidates
    ):
        confidence = min(0.95, confidence + 0.1)
        reason_codes.append("category_brand_confidence_boost")

    return {
        "brand_candidates": candidates,
        "confidence": round(confidence, 2),
        "reason_codes": reason_codes,
    }
