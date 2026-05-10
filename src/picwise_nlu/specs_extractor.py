from __future__ import annotations

import re
from typing import Any

_TIRE_SIZE_PATTERN = re.compile(
    r"(?<!\d)(?P<width>\d{3})/(?P<profile>\d{2})\s*[Rr](?P<rim>\d{2})(?!\d)"
)
_FX_MODEL_PATTERN = re.compile(r"(?<!\w)fx[\s\-]?(?P<code>(991)(?:ex|es)?|570)(?!\w)")


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return ""


def _extract_capacity_mah(text: str) -> str | None:
    match = re.search(r"(?<!\d)(?P<raw>20[\s\.]?000|20000|10[\s\.]?000|10000)\s*mah(?!\w)", text)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group("raw"))
    if digits in {"20000", "10000"}:
        return digits
    return None


def extract_specs(text: str, category: str | None = None) -> dict:
    safe = _safe_text(text).lower()
    if not safe:
        return {"specs": {}, "confidence": 0.0, "reason_codes": ["empty_input"]}

    specs: dict[str, str] = {}
    reason_codes: list[str] = []

    tire_match = _TIRE_SIZE_PATTERN.search(safe)
    if tire_match and category in {None, "car_tyres"}:
        specs["width"] = tire_match.group("width")
        specs["profile"] = tire_match.group("profile")
        specs["rim"] = f"R{tire_match.group('rim')}"
        reason_codes.append("spec_tire_size_extracted")

    capacity = _extract_capacity_mah(safe)
    if capacity and category in {None, "power_banks"}:
        specs["capacity_mah"] = capacity
        reason_codes.append("spec_capacity_mah_extracted")

    fx_match = _FX_MODEL_PATTERN.search(safe)
    if fx_match and category in {None, "calculators"}:
        specs["model_code"] = f"fx-{fx_match.group('code')}"
        reason_codes.append("spec_fx_model_code_extracted")

    if not specs:
        return {"specs": {}, "confidence": 0.0, "reason_codes": ["no_specs_extracted"]}

    confidence = min(0.95, 0.35 + (0.15 * len(specs)))
    return {"specs": specs, "confidence": round(confidence, 2), "reason_codes": reason_codes}
