# PicWise Runtime Truth Audit Report — 2026-05-31

Strict audit run after Stage 8B closure (commits `3bd5741`, `1969408`).

## Rule file

- `.cursor/rules/` — **does not exist**
- Created: `docs/picwise_runtime_truth_audit_rules.md`

## Audit helpers (read-only)

- `tools/runtime_truth_audit.py` — JSON runtime truth capture
- `tests/test_picwise_runtime_truth_audit_fields.py` — backend truth field assertions

## Test results

| Command | Result |
|---------|--------|
| Required 73-test suite | **PASS** (311.6s) |
| `tests.test_picwise_runtime_truth_audit_fields` | **PASS** (3 tests, 18.5s) |

## Runtime truth summary

Feed: `AWIN_FEED_FILE=C:\Users\User\Desktop\picwise-private-feeds\back_to_office_clean_full_columns.csv.gz`

**Global truth pattern for all selected products:**

- `purchasability_state`: **purchasability_unknown** (not verified purchasable)
- `availability_state`: **weak** (`constant_feed_availability` signal)
- `card_eligible`: **true** (feed fields complete; no verifier block)
- `recommendation_confidence_ceiling`: **limited**
- `verification_confidence`: **empty**
- `result_allowed`: **false** (Awin not a connected manual provider)
- UI feed gate (`_provider_feed_ui_display_allowed`) for laptop: **true** — cards can render on reference surface despite unverified purchasability

## Stage 8C blockers

1. No live purchasability verifier — all feed products remain `purchasability_unknown`.
2. `card_eligible=true` while purchasability unverified — pool cards allowed without merchant-page proof.
3. UI reference surface can expose REAL FEED cards when backend recommends, without checking `purchasability_state`.
4. Backend dict omits `brand`, `currency`, `product_type` from `provider_product_to_backend_dict` (present on `ProviderProduct` but not exported).
5. No automated real-world URL/stock/buy-button verification loop.
6. Canary queries only — no table-driven generic product-type matrix across mega-categories.
7. `office chair` correctly safe-no-passes; toner/ink/mini-pc use feed-opportunity gate with `resolver_state=not_understood` — resolver/selection alignment gap.

## Real URL sample (manual audit-only)

Affiliate links redirect to `backtotheoffice.co.uk` with HTTP 200. Keyword heuristics on merchant HTML are unreliable (footer noise triggers false positives). **No verified buy-button or stock state** was written into backend fields.

## Git

Only audit artifacts changed — no forbidden paths.
