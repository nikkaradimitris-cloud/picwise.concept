# Stage 29 - Offline NLU Learning System

## Scope

Stage 29 implements an integrated offline learning pipeline for PickWise Local NLU:

1. Build deterministic multilingual noisy query variants from linked seeds.
2. Evaluate generated queries through local offline NLU interfaces.
3. Detect and classify failures.
4. Convert failures into structured learning suggestions.
5. Gate suggestions by explicit approval status.
6. Build controlled update-pack artifacts from approved suggestions.
7. Build regression-pack artifacts for future verification.

## Strict Boundaries

- Offline only.
- No runtime activation.
- No app/router/search updates.
- No live network calls.
- No direct mutation of Local NLU runtime dictionaries or rules.
- No Stage 30 implementation.

## Package

`src/picwise_learning/` contains:

- `stage29_contracts.py`: strict dataclass contracts for records and artifacts.
- `stage29_config.py`: deterministic generation configuration.
- `stage29_seed_builder.py`: seed linkage to retail, SaaS/ERP, and finance contracts.
- `stage29_query_generator.py`: multilingual noisy variant generation with streaming/chunking.
- `stage29_evaluation.py`: offline evaluator against existing Local NLU interfaces.
- `stage29_failure_analysis.py`: deterministic failure classification.
- `stage29_suggestions.py`: structured suggestion builder from failures.
- `stage29_approval_gate.py`: approval-status transitions and approved-only filtering.
- `stage29_update_pack.py`: controlled update-pack artifact builder.
- `stage29_regression_pack.py`: regression-pack artifact builder.
- `stage29_validation.py`: contract and guardrail validation.

## Operational Notes

- Test mode uses small deterministic sample sizes.
- Massive scale is supported through iterator streaming and chunk batching.
- Update packs and regression packs are artifact data structures only.
