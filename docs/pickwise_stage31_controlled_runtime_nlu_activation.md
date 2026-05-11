# PickWise Stage 31 - Controlled Runtime NLU Activation

## Scope

Stage 31 introduces a controlled activation layer on top of Stage 30 shadow observation.
The baseline runtime remains the default driver. Stage 31 influence is gated and disabled by default.

This stage does not implement Stage 32 and does not add commerce execution logic.

## Components

- `stage31_contracts.py`: activation candidate, audit record, and summary contracts.
- `stage31_config.py`: safe defaults for controlled activation.
- `stage31_activation_gate.py`: strict eligibility guardrails.
- `stage31_candidate_builder.py`: candidate construction from runtime + Stage 30 shadow record.
- `stage31_runtime_controller.py`: rollback-safe orchestration with optional narrow target influence.
- `stage31_rollback.py`: original runtime restoration on failure.
- `stage31_audit.py`: internal audit log collection.
- `stage31_summary.py`: aggregate activation outcomes.
- `stage31_validation.py`: activation contract validation rules.

## Runtime Integration

`picwise_app.app.PicwiseLocalApp._observe_stage30_shadow` remains the Stage 30 hook point.
After Stage 30 observation, Stage 31 receives runtime decision snapshots and evaluates activation internally.

Default behavior is unchanged because:

- Stage 31 activation is disabled by default.
- Controller errors are swallowed and rolled back.
- Runtime output remains unchanged when activation is disabled or blocked.

## Guardrails

Activation can only become eligible when all checks pass:

- activation explicitly enabled
- non-empty runtime query
- confidence >= configured minimum
- safe Stage 30 comparison status
- vertical allowed and not blocked
- sufficient runtime/shadow data
- no manual review, unsafe, ambiguous, or unsupported markers
- no regulated finance auto-activation

Blocked verticals include finance/insurance/business finance by default.
SaaS/ERP requires explicit enablement.

## Notes

- Stage 31 does not mutate Stage 30 records.
- Stage 31 does not apply Stage 29 update packs directly to runtime.
- Stage 31 does not alter broader runtime output paths by default.
