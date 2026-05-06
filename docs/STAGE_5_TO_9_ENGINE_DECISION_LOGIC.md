# STAGE 5 TO 9 ENGINE DECISION LOGIC

This document describes the integrated implementation for roadmap stages 5-9 in the engine layer under `src/picwise_engine/`.

## 5. Core decision engine

- Implemented `PicwiseDecisionEngine` in `src/picwise_engine/engine.py`.
- Input contract:
  - `query`
  - external candidate/product-provider dictionaries
  - `context_metadata`
- Deterministic pipeline:
  - candidate adapter
  - brain selector
  - decision depth selector
  - arbitration
  - final `DecisionOutput` schema validation via `picwise_contracts`
- Enforced behavior:
  - exactly 4 primary choices
  - exactly 1 recommended choice
  - `recommended_product_id` must belong to the selected 4
  - commission-ranking fields are rejected
  - fake-data markers are rejected
  - missing-data states must use canonical enum values
  - tracking context is always attached
  - no synthetic or internal fake product dataset generation

## 6. Brain selector

- Implemented `BrainSelector` in `src/picwise_engine/brain_selector.py`.
- Uses deterministic keyword/context scoring against:
  - query
  - `category`
  - `product_type`
  - `service_type`
  - `risk_flags`
- Selects exactly one `ProductBrain` value:
  - `tech_specs_electronics`
  - `software_programs_saas`
  - `physical_products_home_machines`
  - `financial_utility_contract_products`
  - `high_trust_risk_sensitive_decisions`
- Exposes structured confidence and notes.
- If unclear, applies deterministic safe fallback:
  - `physical_products_home_machines`

## 7. Decision depth selector

- Implemented `DecisionDepthSelector` in `src/picwise_engine/depth_selector.py`.
- Uses deterministic scoring based on:
  - selected brain
  - query intent keywords
  - risk level
  - service/product type
  - price band and optional estimated price
- Selects exactly one `DecisionDepth` value:
  - `fast_decision`
  - `considered_purchase`
  - `high_stakes_high_trust`
- Exposes structured confidence and notes.

## 8. Product candidate adapter

- Implemented `ProductCandidateAdapter` in `src/picwise_engine/candidate_adapter.py`.
- Accepts external candidate dictionaries and converts to ProductChoice-compatible payloads.
- No built-in fake dataset and no fabricated sample products.
- Rejects candidates containing:
  - fake review/rating/revenue/savings/urgency/confidence markers
  - commission-ranking fields
- Requires enough fields to build ProductChoice-compatible output.
- Applies controlled role validation via existing contract enums/rules.
- Preserves and appends terms/unknown summaries into financial/utility risk text when provided.

## 9. Decision arbitration

- Implemented `DecisionArbitrator` in `src/picwise_engine/arbitration.py`.
- Deterministic rule-based ranking only.
- No commission-based ranking signal.
- Chooses:
  - final 4 primary choices
  - exactly 1 recommended choice
- Ranking heuristics prioritize:
  - decision label clarity
  - subtitle quality
  - key reasons quality
  - risk handling completeness
  - tracking metadata readiness
- Applies role diversity selection where possible before fill.
- Fails clearly if fewer than 4 valid candidates exist.
- Brain-specific safeguards:
  - financial/utility candidates require terms/risks/unknown handling
  - high-trust/risk candidates require risk/limitations and reassurance signals
- Recommended choice always receives a concrete recommendation reason.
