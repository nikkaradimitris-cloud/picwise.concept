# 20. Live Subby dashboard integration

Stage 20 is implemented as **integration readiness** only.

## What is included

- `src/picwise_integrations/subby_dashboard.py` integration-readiness module
- Subby payload preparation from existing dashboard compatibility helpers
- transport interface with default local/noop transport
- canonical missing-data enum checks:
  - `not_connected`
  - `data_not_yet`
  - `not_applicable`
  - `unknown`
- guards that prevent fake revenue/conversion values

## What is intentionally not included

- no live Subby endpoint connection
- no live API key usage
- no external network calls by default transport
- no claim of live integration

## Readiness Checklist

- [x] payload preparation implemented
- [x] transport abstraction implemented
- [x] default transport is noop/local-safe
- [x] fake revenue/conversion metrics blocked
- [ ] live endpoint/key proof
- [ ] end-to-end live ingestion verification

## Status

Integration status: `INTEGRATION_READY`  
Not live integrated yet: live proof is required before marking PASSED.
