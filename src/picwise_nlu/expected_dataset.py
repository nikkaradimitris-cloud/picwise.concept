from __future__ import annotations


def get_expected_intent_cases() -> list[dict]:
    return [
        {
            "case_id": "stage12_tyre_exactish_messy",
            "input": "goodyar eficiency grim 195 65 15 aneto",
            "expected": {
                "category": "car_tyres",
                "brand_candidates": ["Goodyear"],
                "model_candidates": ["EfficientGrip"],
                "specs": {"width": "195", "profile": "65", "rim": "R15"},
                "buying_priority": ["comfort"],
                "needs_review": False,
            },
            "source": "local_expected",
        },
        {
            "case_id": "stage12_tyre_general_intent",
            "input": "thelo lastixa 195/65 r15 isixo",
            "expected": {
                "category": "car_tyres",
                "buying_priority": ["low_noise"],
                "status": "general_intent_resolved",
            },
            "source": "local_expected",
        },
        {
            "case_id": "stage12_calculator_exam",
            "input": "kompiouteraki casio gia panellinies fx 991",
            "expected": {
                "category": "calculators",
                "brand_candidates": ["Casio"],
                "model_candidates": ["fx-991"],
                "buying_priority": ["exam_approved"],
            },
            "source": "local_expected",
        },
        {
            "case_id": "stage12_powerbank_iphone",
            "input": "power bank iphone 20000mah fast charge",
            "expected": {
                "category": "power_banks",
                "specs": {"capacity_mah": "20000"},
                "buying_priority": ["fast_charging"],
            },
            "source": "local_expected",
        },
        {
            "case_id": "stage12_ambiguous_unknown",
            "input": "asdf qwer zzzz ???",
            "expected": {
                "needs_review": True,
                "status": "insufficient_data",
            },
            "source": "local_expected",
        },
    ]
