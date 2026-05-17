from __future__ import annotations

import re
from typing import Any

_MODEL_PHRASES = [
    ("efficientgrip performance 2", "EfficientGrip Performance 2"),
    ("premiumcontact", "PremiumContact"),
    ("ecocontact", "EcoContact"),
    ("efficientgrip", "EfficientGrip"),
    ("primacy 4", "Primacy 4"),
    ("turanza", "Turanza"),
    ("turan", "Turanza"),
    ("primacy", "Primacy"),
]


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return ""


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def _extract_fx_model(text: str) -> str | None:
    match = re.search(r"(?<!\w)f[xxz][\s\-]?((991)(ex|es)?|570)(?!\w)", text)
    if not match:
        return None
    suffix = match.group(1).lower()
    return f"fx-{suffix}"


def _extract_powerbank_capacity_model(text: str) -> list[str]:
    models: list[str] = []
    if re.search(r"(?<!\d)(20[\s\.]?000|20000)\s*mah(?!\w)", text) or _contains_term(text, "20000mah"):
        models.append("20000mah")
    if re.search(r"(?<!\d)(10[\s\.]?000|10000)\s*mah(?!\w)", text) or _contains_term(text, "10000mah"):
        models.append("10000mah")
    if _contains_term(text, "magsafe"):
        models.append("magsafe")
    return models


def resolve_model_candidates(
    text: str, category: str | None = None, brand_candidates: list[str] | None = None
) -> dict:
    safe = _safe_text(text).lower()
    if not safe:
        return {"model_candidates": [], "confidence": 0.0, "reason_codes": ["empty_input"]}

    _ = brand_candidates or []
    candidates: list[str] = []
    reason_codes: list[str] = []

    for phrase, canonical in _MODEL_PHRASES:
        if _contains_term(safe, phrase) and canonical not in candidates:
            if phrase == "efficientgrip" and "EfficientGrip Performance 2" in candidates:
                continue
            if phrase == "primacy" and "Primacy 4" in candidates:
                continue
            candidates.append(canonical)
            reason_codes.append(f"model_match_{phrase.replace(' ', '_')}")

    fx_model = _extract_fx_model(safe)
    if fx_model and fx_model not in candidates:
        candidates.append(fx_model)
        reason_codes.append("model_match_fx_series")

    for capacity_model in _extract_powerbank_capacity_model(safe):
        if capacity_model not in candidates:
            candidates.append(capacity_model)
            reason_codes.append(f"model_match_{capacity_model}")

    if not candidates:
        return {"model_candidates": [], "confidence": 0.0, "reason_codes": ["no_model_match"]}

    confidence = min(0.95, 0.28 + (0.18 * len(candidates)))
    if category:
        confidence = min(0.95, confidence + 0.05)
        reason_codes.append("category_model_confidence_boost")

    return {
        "model_candidates": candidates,
        "confidence": round(confidence, 2),
        "reason_codes": reason_codes,
    }
