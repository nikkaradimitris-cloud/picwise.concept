# PROGRESS.md

Official human-readable progress tracker for Picwise Production.

## 1) Project Identity

- Project: Picwise Production
- Primary domain: picwise.subby.cloud
- Product type: decision engine, not search engine
- Current phase: Contracts / Schemas Foundation completed, Core decision engine next

## 2) Source Of Truth Order

1. PROJECT_RULES.md
2. concept.picwise.txt
3. docs/*.md specs
4. PROGRESS.md for progress tracking only

## 3) Current Verified Status

PASSED:
- Root rules created
- concept filename normalized to concept.picwise.txt
- Mission docs/spec foundation created
- Quality rules created
- Testing strategy created
- Missing-data enum aligned:
  - not_connected
  - data_not_yet
  - not_applicable
  - unknown
- Final docs contract review passed
- Contracts/schemas foundation implemented with validation tests passing
- No frontend/backend implementation created yet

## 4) Locked Implementation Roadmap Status

| # | Roadmap Step | Status |
|---|---|---|
| 1 | Root rules and concept lock | PASSED |
| 2 | Mission docs/spec foundation | PASSED |
| 3 | Quality rules and testing strategy | PASSED |
| 4 | Contracts/schemas | PASSED |
| 5 | Core decision engine | PENDING |
| 6 | Brain selector | PENDING |
| 7 | Decision depth selector | PENDING |
| 8 | Product candidate adapter | PENDING |
| 9 | Decision arbitration | PENDING |
| 10 | Landing UI | PENDING |
| 11 | CTA/redirect tracking | PENDING |
| 12 | SEO landing generation | PENDING |
| 13 | Dashboard/Subby event compatibility | PENDING |
| 14 | Performance audit | PENDING |
| 15 | Final V1 audit closure | PENDING |

## 5) Completion Rule

A step may only be marked PASSED when there is:
- implementation or documentation proof
- relevant tests where applicable
- quality checklist
- no fake-data check
- no commission-ranking check
- audit notes
- user review before git commit

## 6) Current Next Step

Core decision engine.

## 7) Do-Not-Claim Rules

- Do not claim Picwise is implemented.
- Do not claim UI exists.
- Do not claim backend exists.
- Do not claim product data exists.
- Do not claim dashboard integration exists.
- Do not claim affiliate/revenue tracking exists.
- Only docs/spec foundation is currently passed.

## 8) Progress Log

- 2026-05-06: Root rules, concept lock, docs/spec foundation, quality/testing strategy, missing-data enum alignment, and docs contract review are passed. Next step is Contracts / Schemas Foundation. No app code exists yet.
- 2026-05-06: Contracts/schemas stage implemented under src/picwise_contracts with tests in tests/test_contracts.py. Test command: python -m unittest discover -s tests. Result: 16 tests passed (OK). Next step is Core decision engine.
