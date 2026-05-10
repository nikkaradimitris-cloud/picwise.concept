from __future__ import annotations

from typing import Any

from .brand_resolver import resolve_brand_candidates
from .category_detector import detect_category
from .model_resolver import resolve_model_candidates
from .priority_detector import detect_buying_priority
from .specs_extractor import extract_specs


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return ""


def _merge_reason_codes(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for code in group:
            text = str(code).strip()
            if text and text not in seen:
                merged.append(text)
                seen.add(text)
    return merged


def analyze_normalized_query(text: str) -> dict:
    safe = _safe_text(text)
    if not safe:
        return {
            "category": None,
            "brand_candidates": [],
            "model_candidates": [],
            "specs": {},
            "buying_priority": [],
            "confidence": 0.0,
            "reason_codes": ["empty_input"],
        }

    category_result = detect_category(safe)
    category = category_result.get("category")

    brand_result = resolve_brand_candidates(safe, category=category)
    model_result = resolve_model_candidates(
        safe,
        category=category,
        brand_candidates=brand_result.get("brand_candidates", []),
    )
    specs_result = extract_specs(safe, category=category)
    priority_result = detect_buying_priority(safe, category=category)

    confidences = [
        float(category_result.get("confidence", 0.0)),
        float(brand_result.get("confidence", 0.0)),
        float(model_result.get("confidence", 0.0)),
        float(specs_result.get("confidence", 0.0)),
        float(priority_result.get("confidence", 0.0)),
    ]
    non_zero_confidences = [value for value in confidences if value > 0.0]
    confidence = (
        round(sum(non_zero_confidences) / len(non_zero_confidences), 2)
        if non_zero_confidences
        else 0.0
    )

    return {
        "category": category,
        "brand_candidates": brand_result.get("brand_candidates", []),
        "model_candidates": model_result.get("model_candidates", []),
        "specs": specs_result.get("specs", {}),
        "buying_priority": priority_result.get("buying_priority", []),
        "confidence": confidence,
        "reason_codes": _merge_reason_codes(
            category_result.get("reason_codes", []),
            brand_result.get("reason_codes", []),
            model_result.get("reason_codes", []),
            specs_result.get("reason_codes", []),
            priority_result.get("reason_codes", []),
        ),
    }
