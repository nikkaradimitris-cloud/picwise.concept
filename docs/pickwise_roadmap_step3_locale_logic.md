# PickWise Roadmap Step 3 - Locale Logic Closure

## Step 3 purpose

Roadmap Step 3 adds deterministic locale eligibility checks before any candidate page generation or indexing decisions. The scope is validation only: locale/market/currency/delivery evidence is inspected and classified, but no public publishing flow is opened.

This closure package is additive to Step 2 and does not modify naming, public routes, sitemap exposure, or search/runtime routers.

## Supported target markets

Step 3 currently supports:

- US
- UK
- DE
- GR

Any unsupported or unknown target market is blocked by default.

## Currency and delivery rules

- US expects `USD` unless explicit alternate currency rules are provided.
- UK expects `GBP` unless explicit alternate currency rules are provided.
- DE expects `EUR`.
- GR expects `EUR`.
- Unknown or missing currency is never auto-filled.
- Missing delivery coverage is never treated as valid.
- Conflicting market/currency evidence is blocked.

Delivery evidence must be explicit and candidate-linked:

- US requires explicit `US` delivery coverage.
- UK requires explicit `UK` delivery coverage.
- DE requires explicit `DE` delivery, or explicit `EU` + `DE` delivery evidence.
- GR requires explicit `GR` delivery, or explicit `EU` + `GR` delivery evidence.

## EU compatibility rules

EU-compatibility is accepted only for `DE` and `GR`, and only when delivery evidence explicitly contains both `EU` and the target market token (`DE` or `GR`).

This means:

- EU products do not pass DE/GR by assumption.
- US/UK do not accept EU-only delivery evidence as a substitute for explicit US/UK coverage.

## What blocks a product

Typical blockers include:

- unsupported target market
- unknown candidate market
- target-market currency mismatch
- candidate market/currency conflict
- locale-to-market conflict where locale region evidence contradicts market
- missing required explicit delivery compatibility

Blocked products cannot be shown to users and cannot continue to candidate-page staging.

## What requires review

Review-required outcomes capture incomplete-but-not-fabricated evidence, for example:

- missing candidate currency
- missing delivery coverage

Review-required candidates are not silently promoted; they remain non-ready until explicit trusted evidence is provided.

## Evidence that closes Step 3

Step 3 can be considered closed when deterministic tests show:

- US/UK/DE/GR happy-path products become `locale_ready`
- cross-market invalid cases are blocked
- DE/GR EU compatibility only passes when explicit delivery evidence exists
- missing/unknown locale-market-currency-delivery inputs are not fabricated
- batch counting is deterministic and gate outcomes are stable
- step4 continuation gate is true only when blockers are zero and review rate is within threshold

## Why Step 3 does not publish pages or generate 3,000 pages

Step 3 is an internal eligibility closure package. It does not:

- publish candidate pages
- wire into public `/best` routes
- expand sitemap output
- generate keyword clusters
- create mass candidate pages

Those are explicitly outside Step 3 and remain gated by later roadmap stages.
