from __future__ import annotations

import json
from typing import Any

from .evaluation_runner import evaluate_local_nlu_cases
from .query_variant_generator import generate_variants_for_training_pack


def _as_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def get_stage_19_training_pack(max_variants_per_seed: int = 200) -> list[dict]:
    cases = generate_variants_for_training_pack(max_variants_per_seed=max_variants_per_seed)
    return json.loads(json.dumps(cases, ensure_ascii=True, sort_keys=True))


def summarize_stage_19_training_pack(cases: list[dict]) -> dict:
    safe_cases = cases if isinstance(cases, list) else []
    by_seed: dict[str, int] = {}
    by_variant_type: dict[str, int] = {}
    by_category: dict[str, int] = {}

    for case in safe_cases:
        row = dict(case or {})
        seed_id = _as_text(row.get("seed_id")) or "unknown_seed"
        variant_type = _as_text(row.get("variant_type")) or "unknown_variant"
        expected = row.get("expected", {})
        category = ""
        if isinstance(expected, dict):
            category = _as_text(expected.get("category"))
        if not category:
            category = "unknown_category"

        by_seed[seed_id] = by_seed.get(seed_id, 0) + 1
        by_variant_type[variant_type] = by_variant_type.get(variant_type, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1

    summary = {
        "total_cases": len(safe_cases),
        "by_seed": by_seed,
        "by_variant_type": by_variant_type,
        "by_category": by_category,
    }
    return json.loads(json.dumps(summary, ensure_ascii=True, sort_keys=True))


def evaluate_stage_19_training_pack(max_variants_per_seed: int = 200) -> dict:
    cases = get_stage_19_training_pack(max_variants_per_seed=max_variants_per_seed)
    evaluation_report = evaluate_local_nlu_cases(cases)
    report = dict(evaluation_report or {})
    report["stage"] = "stage_19_training_pack"
    report["pack_summary"] = summarize_stage_19_training_pack(cases)
    report["cases"] = cases
    return json.loads(json.dumps(report, ensure_ascii=True, sort_keys=True))
