# 24. Live Subby dashboard event integration

Current stage status in this repository is `NEEDS_LIVE_SUBBY_PROOF`.

## Endpoint

- `GET /subby-proof`
- Operator live proof endpoint for `picwise.subby.cloud`

## Behavior

- Reads env vars:
  - `PICWISE_SUBBY_ENDPOINT`
  - `PICWISE_SUBBY_PROJECT_ID`
  - `PICWISE_SUBBY_API_KEY`
- If any required env var is missing, returns safe JSON:
  - `status: "missing_config"`
  - `missing: [...]`
  - `secret_values_exposed: false`
- If config exists, sends exactly one test bridge event with:
  - `test_mode: true`
  - `operator_generated: true`
  - signal `health/live_proof`

## Safety Rules

- Sends test-only event payload for operator confirmation.
- No revenue or conversion event values are sent.
- API key is only read from Vercel environment variables.
- API key is never returned in endpoint response JSON.

## Live Proof Requirement

Stage 24 remains `NEEDS_LIVE_SUBBY_PROOF` until the operator confirms the test event appears in the live Subby dashboard.
