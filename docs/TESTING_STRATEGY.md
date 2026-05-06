# Testing Strategy

## Testing Policy

No implementation claim is valid without test output or audit proof.

No `PASSED` status is allowed without recorded evidence.

## Required Test Suites

- Docs/spec validation tests.
- Contract/schema tests.
- Brain selection tests.
- Decision output tests.
- Recommended uniqueness tests: exactly 1 recommended.
- Four-choice output tests: exactly 4 primary choices.
- No fake-data tests.
- Revenue neutrality tests: commission fields must not affect ranking.
- Financial/utility safety tests.
- CTA behavior tests.
- Redirect event tests.
- Tracking payload tests.
- Performance budget tests.
- Dashboard compatibility tests.
- Regression tests for every future implementation step.
- Manual audit checklist when automated tests are not enough.

## Contract-Specific Assertions

For each decision response, assert:
- output contains exactly 4 primary choices
- exactly one choice is marked recommended
- recommended choice contains non-empty reason
- each choice contains CTA + redirect mapping
- missing data values are explicit and valid

## Evidence Requirements

For every test execution:
- capture command/output artifact or structured report
- capture date/time and scope
- link result to implementation step

## Manual Audit Checklist (When Needed)

- verify no fake metrics/content in output
- verify no commission-first behavior
- verify terms/risks/unknowns for financial/utility flows
- verify CTA copy aligns with intent type
- verify redirect behavior and event logs
- verify performance evidence against budgets

## Undefined Details

- Test framework/toolchain selection: TODO
- CI policy and blocking thresholds: TODO
