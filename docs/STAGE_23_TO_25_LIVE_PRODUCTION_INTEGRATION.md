# STAGE 23 TO 25 LIVE PRODUCTION INTEGRATION

This document records the production-safe readiness layer for stages 23-25 with strict honesty gating.

## 23. Real product/feed and affiliate redirect connection

- Added env-driven feed config support:
  - `PICWISE_FEED_SOURCE_TYPE`
  - `PICWISE_FEED_SOURCE_URL`
  - `PICWISE_FEED_API_KEY`
- Added `ConfiguredFeedAdapter` and transport abstraction:
  - accepts configured provider feed transport
  - defaults to noop transport for safe local/testing behavior
- Added readiness status gates:
  - `NEEDS_REAL_FEED_CONFIG`
  - `FEED_READY`
- Added affiliate redirect config support:
  - `PICWISE_AFFILIATE_PROVIDER`
  - `PICWISE_AFFILIATE_TRACKING_ID`
  - `PICWISE_AFFILIATE_REDIRECT_TEMPLATE`
- Added affiliate readiness status gates:
  - `NEEDS_AFFILIATE_CONFIG`
  - `REDIRECT_READY`
- Added validation hardening:
  - rejects fake review/rating/price/availability/revenue/conversion/savings/urgency/confidence markers
  - rejects commission ranking fields/signals
- Demo/local fixture remains separate and explicitly non-production.
- No real provider credentials or live provider proof are committed in repository.

Current honest stage status for this repository: `NEEDS_REAL_FEED_CONFIG`.

## 24. Live Subby dashboard event integration

- Added env-driven Subby config support:
  - `PICWISE_SUBBY_ENDPOINT`
  - `PICWISE_SUBBY_PROJECT_ID`
  - `PICWISE_SUBBY_API_KEY`
- Added integration readiness gates:
  - `NEEDS_LIVE_SUBBY_CONFIG`
  - `INTEGRATION_READY`
- Added live-ready transport wrapper with injectable sender abstraction.
- Default behavior remains noop/local-safe when live config is missing.
- Payload mapping remains contract-driven via surface dashboard payload builder.
- Missing fields use canonical states:
  - `not_connected`
  - `data_not_yet`
  - `not_applicable`
  - `unknown`
- Validation blocks fake revenue/conversion markers and non-canonical missing-data usage.
- Tests use mock/noop transport only; no external network calls are made in tests.

Current honest stage status for this repository: `NEEDS_LIVE_SUBBY_CONFIG`.

## 25. Production V1 live audit closure

- Extended production audit checks for stages 22-25:
  - stage 22 live proof URLs recorded
  - stage 23 feed/affiliate readiness vs status honesty
  - stage 24 Subby readiness vs status honesty
  - stage 25 closure gate honesty
  - no fake data markers
  - no commission ranking logic
  - no committed secret-like values
  - tests-passed gate
  - roadmap title continuity checks
  - PROGRESS.md honesty checks
- Audit pass criteria remain strict:
  - stage 22 live proof exists
  - stage 23 live feed/affiliate proof exists
  - stage 24 live Subby event proof exists
  - no fake data
  - no commission ranking
  - no committed secrets
  - tests pass

Current honest stage status for this repository: `NEEDS_LIVE_PROOF`.

## Not Live Claims

- This repository does not claim real feed ingestion is live.
- This repository does not claim affiliate redirect provider integration is live.
- This repository does not claim live Subby dashboard ingestion is proven.
- This repository does not mark stage 25 as PASSED without full live proof.
