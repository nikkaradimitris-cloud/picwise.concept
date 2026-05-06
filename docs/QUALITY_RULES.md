# Quality Rules

## Mandatory Quality Gate

- Every implementation step must be small, closed, testable, and reviewable.
- No step is considered complete without proof.
- No fake data is allowed.
- No commission-first ranking is allowed.
- No frontend/backend implementation before specs/contracts are reviewed.
- No overwriting existing files without inspecting them first.
- Every product decision must respect the Picwise Decision Contract.
- Every brain must output 4 choices + 1 recommended.
- Financial/utility outputs must show terms, risks, and unknowns where applicable.
- Missing data must be explicit: `not_connected`, `data_not_yet`, `not_applicable`, or `unknown`.
- Recommended choice must always have a reason.
- Performance targets must be respected.
- UI must reduce decision time, not increase browsing.
- Each step must include a closure checklist.

## Proof Requirement

No status can be treated as complete without concrete evidence such as:
- test outputs
- validation logs
- manual audit records
- measurable performance results

## Closure Checklist Template (Required Per Step)

- [ ] scope is small and closed
- [ ] implementation evidence attached
- [ ] relevant tests executed and recorded
- [ ] no fake-data check passed
- [ ] no commission-ranking check passed
- [ ] contract compliance verified (4 choices + 1 recommended)
- [ ] risk/unknowns explicitly handled
- [ ] review completed before commit

## Undefined Details

- Formal review sign-off roles: TODO
- Standard evidence artifact path convention: TODO
