# PickWise Stage 30 - Runtime Shadow Learning Integration

## Scope

Stage 30 connects runtime search flow to Stage 29 learning in shadow mode only.

- Runtime path remains the system of record.
- Shadow path is passive and internal.
- No runtime decision override is allowed.
- No user-facing payload changes are allowed.
- No Stage 31 behavior is implemented.

## Components

Stage 30 is implemented under `src/picwise_learning`:

- `stage30_contracts.py`
- `stage30_config.py`
- `stage30_shadow_runner.py`
- `stage30_runtime_probe.py`
- `stage30_decision_comparison.py`
- `stage30_shadow_records.py`
- `stage30_failure_bridge.py`
- `stage30_summary.py`
- `stage30_validation.py`

## Passive Runtime Hook

The passive hook is in `picwise_app.app.PicwiseLocalApp.build_demo_output`.

- Trigger point: after runtime router decision is computed.
- Input: runtime query, runtime decision snapshot, local NLU debug context.
- Behavior: invokes Stage 30 probe inside a guarded `try/except`.
- Safety: probe failures are swallowed and do not affect runtime output.

## Shadow Record Contract

Each shadow record includes:

- `shadow_record_id`
- `stage = "30"`
- `runtime_query`
- `normalized_query`
- `timestamp`
- `source_surface`
- `source_route`
- `existing_runtime_decision`
- `existing_runtime_target`
- `existing_runtime_vertical`
- `shadow_nlu_target`
- `shadow_vertical`
- `shadow_confidence`
- `comparison_status`
- `failure_type`
- `vertical`
- `language`
- `noise_signals`
- `expected_learning_action`
- `offline_only = true`
- `internal_only = true`
- `did_affect_runtime = false`
- `metadata`

Validation rejects records where `did_affect_runtime` is `true`.

## Decision Comparison

Stage 30 compares runtime and shadow decisions with statuses:

- `aligned`
- `disagreement`
- `runtime_unknown`
- `shadow_unknown`
- `both_unknown`
- `manual_review`
- `unsafe_shadow`
- `unsupported`

It also keeps separation rules for:

- retail physical products vs non-retail verticals
- SaaS / ERP
- Finance / Insurance / Business Finance (regulated path defaults to manual review when needed)

## Failure Bridge

Shadow disagreements are converted to Stage 29 compatible failure candidates:

- `source = runtime_shadow`
- includes runtime query, observed runtime decision, shadow decision
- includes failure type, language/noise, vertical, risk level
- marks manual review for regulated or sensitive cases

No automatic approvals and no runtime application of learning updates.

## Summary Layer

Stage 30 summary builder provides internal metrics:

- total records
- aligned/disagreement/runtime_unknown/shadow_unknown/manual_review/unsupported counts
- breakdown by vertical
- breakdown by language
- breakdown by noise signals
- top failure types

All outputs are internal and offline-only.
