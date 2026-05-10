from __future__ import annotations

from typing import Any

_DEFAULT_SEEDS = [
    {
        "case_id": "stage11_tyre_goodyear",
        "input": "Goodyear EfficientGrip Performance 2 195/65 R15 comfort",
        "expected": {
            "category": "car_tyres",
            "brand_candidates": ["Goodyear"],
            "model_candidates": ["EfficientGrip Performance 2"],
            "specs": {"width": "195", "profile": "65", "rim": "R15"},
            "buying_priority": ["comfort"],
        },
    },
    {
        "case_id": "stage11_tyre_bridgestone",
        "input": "Bridgestone Turanza 195/65 R15 low noise",
        "expected": {
            "category": "car_tyres",
            "brand_candidates": ["Bridgestone"],
            "model_candidates": ["Turanza"],
            "specs": {"width": "195", "profile": "65", "rim": "R15"},
            "buying_priority": ["low_noise"],
        },
    },
    {
        "case_id": "stage11_calculator_casio",
        "input": "Casio fx-991 calculator for exams",
        "expected": {
            "category": "calculators",
            "brand_candidates": ["Casio"],
            "model_candidates": ["fx-991"],
            "buying_priority": ["exam_approved"],
        },
    },
    {
        "case_id": "stage11_powerbank_iphone",
        "input": "power bank iphone 20000mah fast charge",
        "expected": {
            "category": "power_banks",
            "specs": {"capacity_mah": "20000"},
            "buying_priority": ["fast_charging"],
        },
    },
]

_VARIANTS_BY_SEED = {
    "stage11_tyre_goodyear": [
        "goodyar eficiency grim 195 65 15 aneto",
        "goodyear efficient grip 195/65r15 comfort",
    ],
    "stage11_tyre_bridgestone": [
        "brizestone touransa 195/65/15 isixo",
        "bridgestone turanza 195 65 r15 low noise",
    ],
    "stage11_calculator_casio": [
        "kompiouteraki casio gia panellinies fx 991",
        "casio fx991 calculator exams",
    ],
    "stage11_powerbank_iphone": [
        "powerbank iphone 20.000mah fast charge",
        "power bank for iphone 20000 mah battery life",
    ],
}


def _safe_expected(seed: dict[str, Any]) -> dict[str, Any]:
    expected = seed.get("expected", {})
    if not isinstance(expected, dict):
        return {}
    return dict(expected)


def generate_query_variants(seed: dict) -> list[dict]:
    if not isinstance(seed, dict):
        return []
    case_id = str(seed.get("case_id", "")).strip()
    if not case_id:
        return []
    expected = _safe_expected(seed)
    variants = _VARIANTS_BY_SEED.get(case_id, [str(seed.get("input", "")).strip()])
    records: list[dict] = []
    for index, variant in enumerate(variants, start=1):
        text = str(variant).strip()
        if not text:
            continue
        records.append(
            {
                "case_id": f"{case_id}_v{index}",
                "input": text,
                "expected": expected,
                "source": "local_generated",
            }
        )
    return records


def generate_default_stage_11_dataset() -> list[dict]:
    dataset: list[dict] = []
    for seed in _DEFAULT_SEEDS:
        dataset.extend(generate_query_variants(seed))
    return dataset
