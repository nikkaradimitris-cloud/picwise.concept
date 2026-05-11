from __future__ import annotations

import hashlib
from collections.abc import Iterable

from .stage29_contracts import (
    Stage29EvaluationRecord,
    Stage29FailureRecord,
    Stage29GeneratedQueryRecord,
)


def _failure_type_for(
    generated: Stage29GeneratedQueryRecord,
    evaluation: Stage29EvaluationRecord,
) -> str:
    if evaluation.status == "unsafe_pass":
        return "unsafe_pass"
    if evaluation.failure_type == "unsupported_interface":
        return "unsupported_interface"
    if generated.vertical != "retail_physical_products":
        return "wrong_vertical"
    if evaluation.actual_nlu_target.startswith("unavailable:"):
        return "unknown_intent"
    if generated.expected_nlu_target != evaluation.actual_nlu_target:
        return "wrong_category"
    noise = generated.noise_profile
    if generated.language == "el":
        return "greek_failure"
    if generated.language == "el_gr":
        return "greeklish_failure"
    if generated.language == "en":
        return "english_failure" if noise == "case_mix" else "typo_normalization_failure"
    if generated.language == "de":
        return "german_failure"
    if noise == "brand_model_spec_typos":
        return "brand_model_spec_failure"
    if noise == "partial_query":
        return "partial_query_failure"
    return "intent_phrase_failure"


def analyze_failures(
    generated_records: Iterable[Stage29GeneratedQueryRecord],
    evaluation_rows: Iterable[Stage29EvaluationRecord],
) -> list[Stage29FailureRecord]:
    generated_by_id = {row.record_id: row for row in generated_records}
    failures: list[Stage29FailureRecord] = []
    for evaluation in evaluation_rows:
        if evaluation.status == "passed":
            continue
        generated = generated_by_id.get(evaluation.generated_query_record_id)
        if generated is None:
            continue
        failure_type = _failure_type_for(generated, evaluation)
        failure_id = "s29_fail_" + hashlib.sha1(
            f"{generated.record_id}|{failure_type}".encode("utf-8")
        ).hexdigest()[:12]
        failures.append(
            Stage29FailureRecord(
                failure_id=failure_id,
                generated_query_record_id=generated.record_id,
                failure_type=failure_type,
                language=generated.language,
                vertical=generated.vertical,
                expected_nlu_target=generated.expected_nlu_target,
                actual_nlu_target=evaluation.actual_nlu_target,
                noise_profile=generated.noise_profile,
                applied_noise_types=generated.applied_noise_types,
                intent_phrase_type=generated.intent_phrase_type,
                notes=evaluation.notes,
            )
        )
    return failures
