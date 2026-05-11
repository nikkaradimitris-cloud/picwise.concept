from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

from .stage30_contracts import Stage30ShadowRecord
from .stage31_activation_gate import evaluate_stage31_activation_gate
from .stage31_audit import Stage31AuditLog
from .stage31_candidate_builder import build_stage31_activation_candidate
from .stage31_config import Stage31ActivationConfig, build_default_stage31_config
from .stage31_contracts import Stage31ActivationCandidate
from .stage31_rollback import rollback_stage31_runtime_result
from .stage31_validation import validate_stage31_activation_candidate


class Stage31RuntimeController:
    def __init__(
        self,
        *,
        config: Stage31ActivationConfig | None = None,
        audit_log: Stage31AuditLog | None = None,
    ) -> None:
        self._config = config or build_default_stage31_config()
        self._audit_log = audit_log or Stage31AuditLog()

    @property
    def audit_log(self) -> Stage31AuditLog:
        return self._audit_log

    def process_runtime_decision(
        self,
        *,
        runtime_query: str,
        runtime_decision: dict[str, Any],
        source_shadow_record: Stage30ShadowRecord | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Stage31ActivationCandidate]:
        original = deepcopy(runtime_decision)
        candidate = build_stage31_activation_candidate(
            runtime_query=runtime_query,
            runtime_decision=runtime_decision,
            source_shadow_record=source_shadow_record,
            activation_enabled=self._config.activation_enabled,
            metadata=metadata,
        )
        try:
            gate_result = evaluate_stage31_activation_gate(candidate, config=self._config)
            candidate = replace(
                candidate,
                activation_status=gate_result.activation_status,
                activation_reason=gate_result.activation_reason,
                block_reasons=gate_result.block_reasons,
                risk_level=gate_result.risk_level,
            )
            if candidate.activation_status in {"disabled", "blocked", "manual_review", "unsupported"}:
                candidate = replace(candidate, did_affect_runtime=False)
                self._audit_log.append_candidate(candidate)
                return original, candidate

            if candidate.activation_status == "eligible":
                runtime_after = deepcopy(original)
                did_affect_runtime = False
                if self._config.allow_nlu_target_influence:
                    runtime_after["existing_runtime_target"] = candidate.shadow_nlu_target
                    did_affect_runtime = True
                metadata_bucket = dict(runtime_after.get("stage31_internal") or {})
                metadata_bucket["candidate_id"] = candidate.candidate_id
                metadata_bucket["activation_reason"] = candidate.activation_reason
                metadata_bucket["shadow_target"] = candidate.shadow_nlu_target
                runtime_after["stage31_internal"] = metadata_bucket
                candidate = replace(
                    candidate,
                    activation_status="activated",
                    activation_reason="controlled_activation_applied",
                    did_affect_runtime=did_affect_runtime,
                )
                validation = validate_stage31_activation_candidate(candidate)
                if validation["valid"]:
                    self._audit_log.append_candidate(candidate)
                    return runtime_after, candidate
                candidate = replace(
                    candidate,
                    activation_status="rollback",
                    activation_reason="validation_failed_rollback",
                    block_reasons=tuple(validation["errors"]),
                    did_affect_runtime=False,
                )
                self._audit_log.append_candidate(candidate)
                rollback = rollback_stage31_runtime_result(
                    original_runtime_result=original,
                    rollback_reason="validation_failed_rollback",
                )
                return rollback.restored_runtime_result, candidate
        except Exception as error:
            if self._config.rollback_on_error:
                candidate = replace(
                    candidate,
                    activation_status="rollback",
                    activation_reason="controller_error_rollback",
                    block_reasons=(error.__class__.__name__,),
                    did_affect_runtime=False,
                )
                self._audit_log.append_candidate(candidate)
                rollback = rollback_stage31_runtime_result(
                    original_runtime_result=original,
                    rollback_reason="controller_error_rollback",
                    error=error,
                )
                return rollback.restored_runtime_result, candidate
            raise

        candidate = replace(
            candidate,
            activation_status="unsupported",
            activation_reason="unexpected_activation_path",
            block_reasons=("unexpected_activation_path",),
            did_affect_runtime=False,
        )
        self._audit_log.append_candidate(candidate)
        return original, candidate


def build_default_stage31_runtime_controller() -> Stage31RuntimeController:
    return Stage31RuntimeController()
