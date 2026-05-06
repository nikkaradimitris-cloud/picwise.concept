# Decision Depth Specification

## Objective

Every query must also be assigned a decision depth that controls explanation depth, risk disclosure, and UI density.

## Depth Levels

1. Fast Decision
   - For low-risk, quick-purchase intents
   - Minimal explanation, rapid CTA flow

2. Considered Purchase
   - For medium-risk decisions needing clearer comparison
   - Moderate explanation and reassurance

3. High-Stakes / High-Trust
   - For expensive, sensitive, or contract-bound decisions
   - Stronger explanation, terms/risks/unknowns must be explicit

## Selection Rules

- Exactly one depth must be selected for each query.
- Depth selection must reflect risk, cost impact, commitment duration, and mistake cost.
- Depth selection must not use commission/referral values.

## Output Adjustments By Depth

- Fast: short rationale, concise card copy, immediate decision path
- Considered: 2-3 comparison points and clearer recommendation rationale
- High-Stakes: explicit terms/limitations/unknowns, stronger caution language where needed

## Shared Contract Constraint

Depth never changes the base Picwise output contract:
- still exactly 4 choices
- still exactly 1 recommended
- still CTA + redirect + tracking

## Undefined Details

- Numeric threshold model for low/medium/high risk: TODO
- Exact content length caps per depth: TODO
- Depth override policy for edge cases: TODO
