# Performance Rules

## Mandatory Targets

- First render: `< 1.5s`
- Full interactive: `< 2.0s`
- Click to redirect start: `< 300ms`

## Performance Intent

Performance is part of decision quality.  
Slow delivery increases browsing friction and harms mission outcomes.

## Prohibited Patterns

- heavy scripts that delay first decision view
- delayed rendering of the 4 primary choices
- fake loaders masking slow delivery
- redirect loops
- unnecessary intermediate redirect pages
- unnecessary animations before core decision content
- excessive blocking calls before showing result

## Release Rule

Do not ship knowingly violating targets without explicit approval and documented exception.

## Measurement Requirements

- capture and store speed metrics as real events
- tie metrics to query/session context where possible
- no fake performance numbers

## Undefined Details

- Measurement tooling baseline (RUM/synthetic split): TODO
- Alert thresholds and escalation ownership: TODO
