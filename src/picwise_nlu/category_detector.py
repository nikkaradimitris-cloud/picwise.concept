from __future__ import annotations

import re
from typing import Any

_TYRE_KEYWORDS = {
    "lastixa",
    "λαστιχα",
    "λάστιχα",
    "tyres",
    "tires",
    "tyre",
    "tire",
}
_CALCULATOR_KEYWORDS = {
    "κομπιουτερακι",
    "κομπιουτερακια",
    "calculator",
}
_CALCULATOR_CONTEXT_KEYWORDS = {
    "calculator",
    "κομπιουτερακι",
    "κομπιουτερακια",
    "exam",
    "exams",
    "πανελληνιες",
    "εξετασεις",
    "σχολειο",
}
_POWER_BANK_KEYWORDS = {
    "power bank",
    "powerbank",
}
_CHARGER_KEYWORDS = {
    "charger",
    "φορτιστης",
    "fortistis",
    "usb-c",
    "usbc",
}
_TYRE_STRONG_TERMS = {
    "goodyear",
    "bridgestone",
    "michelin",
    "continental",
    "efficientgrip",
    "turanza",
    "primacy",
    "ecocontact",
    "premiumcontact",
}
_TIRE_SIZE_PATTERN = re.compile(r"(?<!\d)(\d{3})/(\d{2})\s*[Rr](\d{2})(?!\d)")


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return ""


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def detect_category(text: str) -> dict:
    safe = _safe_text(text).lower()
    if not safe:
        return {"category": None, "confidence": 0.0, "reason_codes": ["empty_input"]}

    car_score = 0
    calculator_score = 0
    power_bank_score = 0
    charger_score = 0
    reason_codes: list[str] = []

    tyre_context = any(_contains_term(safe, term) for term in _TYRE_KEYWORDS)
    has_tire_size = bool(_TIRE_SIZE_PATTERN.search(safe))
    if tyre_context:
        car_score += 2
        reason_codes.append("category_signal_tyre_keyword")
    if has_tire_size:
        car_score += 2
        reason_codes.append("category_signal_tyre_size")
    if (
        any(_contains_term(safe, term) for term in _TYRE_STRONG_TERMS)
        and (tyre_context or has_tire_size)
    ):
        car_score += 1
        reason_codes.append("category_signal_tyre_strong_term_with_context")

    calculator_context = any(_contains_term(safe, term) for term in _CALCULATOR_CONTEXT_KEYWORDS)
    if any(_contains_term(safe, term) for term in _CALCULATOR_KEYWORDS):
        calculator_score += 2
        reason_codes.append("category_signal_calculator_keyword")
    if _contains_term(safe, "casio") and calculator_context:
        calculator_score += 2
        reason_codes.append("category_signal_casio_calculator_context")
    if any(_contains_term(safe, term) for term in {"πανελληνιες", "εξετασεις", "σχολειο"}) and (
        calculator_context or _contains_term(safe, "casio")
    ):
        calculator_score += 1
        reason_codes.append("category_signal_exam_calculator_context")

    if any(term in safe for term in _POWER_BANK_KEYWORDS):
        power_bank_score += 2
        reason_codes.append("category_signal_power_bank_keyword")
    if _contains_term(safe, "mah"):
        power_bank_score += 1
        reason_codes.append("category_signal_mah")
    if _contains_term(safe, "iphone") and _contains_term(safe, "battery"):
        power_bank_score += 2
        reason_codes.append("category_signal_iphone_battery_context")
    if _contains_term(safe, "iphone") and _contains_term(safe, "μπαταρια"):
        power_bank_score += 2
        reason_codes.append("category_signal_iphone_battery_context_greek")

    if any(_contains_term(safe, term) for term in _CHARGER_KEYWORDS):
        charger_score += 2
        reason_codes.append("category_signal_charger_keyword")
    if _contains_term(safe, "iphone") and any(_contains_term(safe, term) for term in {"charger", "φορτιστης", "usb-c", "usbc"}):
        charger_score += 1
        reason_codes.append("category_signal_iphone_charger_context")
    if any(_contains_term(safe, term) for term in {"fast", "γρηγορη", "grigoros"}) and any(
        _contains_term(safe, term) for term in {"charger", "φορτιστης", "usb-c", "usbc"}
    ):
        charger_score += 1
        reason_codes.append("category_signal_fast_charger_context")

    scores = {
        "car_tyres": car_score,
        "calculators": calculator_score,
        "power_banks": power_bank_score,
        "chargers": charger_score,
    }
    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]
    tied_categories = [name for name, score in scores.items() if score == best_score and score > 0]

    if best_score < 2:
        return {"category": None, "confidence": 0.1 if best_score > 0 else 0.0, "reason_codes": ["no_clear_category_signal"]}
    if len(tied_categories) > 1:
        return {"category": None, "confidence": 0.15, "reason_codes": ["ambiguous_category_signals"]}

    confidence = min(0.95, 0.25 + (best_score * 0.18))
    reason_codes.append(f"category_selected_{best_category}")
    return {"category": best_category, "confidence": round(confidence, 2), "reason_codes": reason_codes}
