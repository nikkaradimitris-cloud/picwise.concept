from __future__ import annotations

import re
from typing import Any

_PRIORITY_TERMS = {
    "comfort": {"ανετο", "ανετα", "comfort", "μαλακο"},
    "low_noise": {"ησυχο", "αθορυβο", "quiet", "low noise"},
    "budget": {"φτηνο", "οικονομικο", "value", "budget"},
    "wet_grip": {"βροχη", "wet grip", "κρατημα βροχη"},
    "fuel_efficiency": {"οικονομια καυσιμου", "fuel efficient"},
    "battery_life": {"μεγαλη μπαταρια", "battery", "battery life"},
    "fast_charging": {"fast charge", "γρηγορη φορτιση"},
    "exam_approved": {"πανελληνιες", "εξετασεις", "σχολειο"},
}

_CATEGORY_PRIORITY_ALLOWLIST = {
    "car_tyres": {"comfort", "low_noise", "budget", "wet_grip", "fuel_efficiency"},
    "calculators": {"budget", "exam_approved"},
    "power_banks": {"budget", "battery_life", "fast_charging"},
}


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return ""


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def detect_buying_priority(text: str, category: str | None = None) -> dict:
    safe = _safe_text(text).lower()
    if not safe:
        return {"buying_priority": [], "confidence": 0.0, "reason_codes": ["empty_input"]}

    allowed = _CATEGORY_PRIORITY_ALLOWLIST.get(category)
    priorities: list[str] = []
    reason_codes: list[str] = []

    for priority, terms in _PRIORITY_TERMS.items():
        if allowed is not None and priority not in allowed:
            continue
        if any(_contains_term(safe, term) for term in terms):
            priorities.append(priority)
            reason_codes.append(f"priority_match_{priority}")

    if not priorities:
        return {"buying_priority": [], "confidence": 0.0, "reason_codes": ["no_priority_match"]}

    confidence = min(0.95, 0.3 + (0.17 * len(priorities)))
    if category is not None:
        confidence = min(0.95, confidence + 0.05)
        reason_codes.append("category_priority_filter_applied")

    return {
        "buying_priority": priorities,
        "confidence": round(confidence, 2),
        "reason_codes": reason_codes,
    }
