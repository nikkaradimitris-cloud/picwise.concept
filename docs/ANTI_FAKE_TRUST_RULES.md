# Anti-Fake Trust Rules

## Trust Foundation

Picwise must clearly separate known facts, unknowns, and unavailable data.  
Trust is built through honesty and clarity, not fabricated confidence.

## Strictly Forbidden

- fake reviews
- fake ratings
- fake sales
- fake urgency
- fake discounts
- fake conversions
- fake revenue
- fake savings
- fake approval chances
- fake "AI confidence"
- recommendation without real reason
- recommendation driven by higher commission

## Required Honesty Rules

- If data is missing, declare it explicitly.
- If certainty is low, do not present fake certainty.
- If comparison is incomplete, mark the gap and add `TODO` at spec layer.

## Allowed Missing-State Values

- `not_connected`
- `data_not_yet`
- `not_applicable`
- `unknown`

## Enforcement

Any output containing fabricated factual/business signals is non-compliant and must fail quality review.
