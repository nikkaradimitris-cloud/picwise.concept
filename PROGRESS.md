# PROGRESS.md

Official human-readable progress tracker for Picwise Production.

## 1) Project Identity

- Project: Picwise Production
- Primary domain: picwise.subby.cloud
- Product type: decision engine, not search engine
- Current phase: Local app implementation + live-production integration readiness through stage 26

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
- Engine stages 5-9 implemented and tested:
  - 5. Core decision engine
  - 6. Brain selector
  - 7. Decision depth selector
  - 8. Product candidate adapter
  - 9. Decision arbitration
- Product-surface readiness stages 10-15 implemented and tested locally:
  - 10. Landing UI
  - 11. CTA/redirect tracking
  - 12. SEO landing generation
  - 13. Dashboard/Subby event compatibility
  - 14. Performance audit
  - 15. Final V1 audit closure
- App/production path stages 16-21 implemented with honest non-live statuses:
  - 16. App implementation foundation
  - 17. Real product feed adapter
  - 18. Affiliate/provider redirect integration
  - 19. Live app deployment (deployment readiness only)
  - 20. Live Subby dashboard integration (integration readiness only)
  - 21. Production V1 audit closure (needs live proof)
- 22. Live deployment to picwise.subby.cloud — PASSED
- 23. Real product/feed and affiliate redirect connection — NEEDS_REAL_FEED_CONFIG
- 24. Live Subby dashboard event integration — NEEDS_LIVE_SUBBY_PROOF
- 25. Production V1 live audit closure — NEEDS_LIVE_PROOF
- 26. Live route and proof response cleanup — PASSED
- Stage 22 has operator-supplied live URL proof; stages 23-25 remain non-PASSED pending real provider/Subby credentials and live proof.

## 4) Locked Implementation Roadmap Status

| # | Roadmap Step | Status |
|---|---|---|
| 1 | Root rules and concept lock | PASSED |
| 2 | Mission docs/spec foundation | PASSED |
| 3 | Quality rules and testing strategy | PASSED |
| 4 | Contracts/schemas | PASSED |
| 5 | Core decision engine | PASSED |
| 6 | Brain selector | PASSED |
| 7 | Decision depth selector | PASSED |
| 8 | Product candidate adapter | PASSED |
| 9 | Decision arbitration | PASSED |
| 10 | Landing UI | PASSED |
| 11 | CTA/redirect tracking | PASSED |
| 12 | SEO landing generation | PASSED |
| 13 | Dashboard/Subby event compatibility | PASSED |
| 14 | Performance audit | PASSED |
| 15 | Final V1 audit closure | PASSED |
| 16 | App implementation foundation | PASSED |
| 17 | Real product feed adapter | PASSED |
| 18 | Affiliate/provider redirect integration | PASSED |
| 19 | Live app deployment | DEPLOYMENT_READY |
| 20 | Live Subby dashboard integration | INTEGRATION_READY |
| 21 | Production V1 audit closure | NEEDS_LIVE_PROOF |
| 22 | Live deployment to picwise.subby.cloud | PASSED |
| 23 | Real product/feed and affiliate redirect connection | NEEDS_REAL_FEED_CONFIG |
| 24 | Live Subby dashboard event integration | NEEDS_LIVE_SUBBY_PROOF |
| 25 | Production V1 live audit closure | NEEDS_LIVE_PROOF |
| 26 | Live route and proof response cleanup | PASSED |

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

Obtain real feed/affiliate provider credentials and proof, plus live Subby endpoint/key proof and dashboard-ingested event proof, before upgrading stages 23-25 to PASSED.

## 7) Do-Not-Claim Rules

- Do not claim live dashboard/Subby integration.
- Do not claim real product feed integration.
- Do not claim live revenue/conversion tracking.
- 22. Live deployment to picwise.subby.cloud is PASSED only because operator supplied live URL proof.
- 19. Live app deployment must NOT be PASSED unless actual live deployment proof exists.
- 20. Live Subby dashboard integration must NOT be PASSED unless actual live Subby proof exists.
- 21. Production V1 audit closure must NOT be PASSED unless both live deployment and live Subby proofs exist.
- 23. Real product/feed and affiliate redirect connection must NOT be PASSED unless real provider config/proof exists.
- 24. Live Subby dashboard event integration must NOT be PASSED unless real Subby config/proof exists.
- 25. Production V1 live audit closure must NOT be PASSED unless stages 22-24 all have required live proof.
- Current status is: 22 PASSED with live URL proof; 23-24 readiness layer implemented but missing real credentials/live proof; 25 remains `NEEDS_LIVE_PROOF`.

## 8) Progress Log

- 2026-05-06: Root rules, concept lock, docs/spec foundation, quality/testing strategy, missing-data enum alignment, and docs contract review are passed. Next step is Contracts / Schemas Foundation. No app code exists yet.
- 2026-05-06: Contracts/schemas stage implemented under src/picwise_contracts with tests in tests/test_contracts.py. Test command: python -m unittest discover -s tests. Result: 16 tests passed (OK). Next step is Core decision engine.
- 2026-05-06: Engine stages 5-9 implemented under src/picwise_engine with integrated tests in tests/test_engine_stages_5_to_9.py. Test command: python -m unittest discover -s tests. Result: 36 tests passed (OK). Stages 5-9 marked PASSED. No frontend/backend/dashboard/live redirect implementation added.
- 2026-05-06: Group 3 stages 10-15 implemented under src/picwise_surface with tests in tests/test_surface_stages_10_to_15.py and docs/STAGE_10_TO_15_PRODUCT_SURFACE_READINESS.md. Test command: python -m unittest discover -s tests. Result: 55 tests passed (OK). Stages 10-15 marked PASSED for local implementation/test status only; no live deployment, no live dashboard/Subby channel, no real product feed, and no real revenue/conversion tracking.
- 2026-05-06: Integrated stages 16-21 implemented under src/picwise_app, src/picwise_feeds, src/picwise_redirects, src/picwise_integrations with docs/STAGE_16_TO_21_APP_PRODUCTION_PATH.md, docs/STAGE_19_LIVE_APP_DEPLOYMENT.md, docs/STAGE_20_LIVE_SUBBY_DASHBOARD_INTEGRATION.md, deployment templates, and tests/test_app_stages_16_to_21.py. Test command: python -m unittest discover -s tests. Result: 72 tests passed (OK). Statuses updated honestly: 16-18 PASSED, 19 DEPLOYMENT_READY, 20 INTEGRATION_READY, 21 NEEDS_LIVE_PROOF.
- 2026-05-06: Stage 22 deployment-readiness layer added with WSGI deployment entrypoints (`wsgi.py`, `api/index.py`), Vercel routing config (`vercel.json`), stage doc (`docs/STAGE_22_LIVE_DEPLOYMENT_TO_PICWISE_SUBBY_CLOUD.md`), and deployment-entrypoint tests. Status set to `DEPLOYMENT_READY` pending real live URL proof at picwise.subby.cloud.
- 2026-05-06: Stage 22 upgraded to `PASSED` using operator-supplied live proof: `https://picwise.subby.cloud/health` (OK) and `https://picwise.subby.cloud/demo` (OK). Added stage 23-25 live-production integration readiness layer: env-driven feed/affiliate/Subby configs, strict anti-fake and anti-commission validations, honest readiness/audit gates, `docs/STAGE_23_TO_25_LIVE_PRODUCTION_INTEGRATION.md`, and test coverage. Honest statuses remain: 23 `NEEDS_REAL_FEED_CONFIG`, 24 `NEEDS_LIVE_SUBBY_PROOF`, 25 `NEEDS_LIVE_PROOF`.
- 2026-05-06: Added operator live proof endpoint `GET /subby-proof` for stage 24 with env-driven Subby bridge send, safe missing-config behavior, and mocked test coverage (no real network calls). Stage 24 remains `NEEDS_LIVE_SUBBY_PROOF` pending operator confirmation that the test event appears in the live Subby dashboard; stage 25 remains `NEEDS_LIVE_PROOF`.
- 2026-05-06: Added safe non-secret diagnostics for stage 24 `/subby-proof` outbound bridge failures (`safe_error_type`, `safe_error_message`, and HTTP status passthrough for HTTPError), with sanitizer-based redaction for API key/token-like values and expanded mocked tests. Stage 24 remains `NEEDS_LIVE_SUBBY_PROOF`; stage 25 remains `NEEDS_LIVE_PROOF`.
- 2026-05-06: Improved stage 24 outbound HTTP diagnostics in `UrllibSubbyBridgeEventSender` and `/subby-proof` to prioritize explicit POST/json bridge behavior, short timeout, sanitized HTTPError/rejection diagnostics (`bridge_http_status`, `safe_error_type`, `safe_error_message`), and optional `accepted` extraction from error/rejection payloads. Stage 24 remains `NEEDS_LIVE_SUBBY_PROOF`; stage 25 remains `NEEDS_LIVE_PROOF`.
- 2026-05-06: Stage 26 implemented and validated with `python -m unittest discover -s tests` (101 tests, OK). `GET /` now renders the same landing content as `GET /demo`, landing output is polished with lightweight inline CSS while keeping decision-contract constraints, and `/subby-proof` timeout/read-timeout responses are now represented as `sent_unconfirmed` with `dashboard_check_required: true` and sanitized non-secret diagnostics. Stage 24 remains `NEEDS_LIVE_SUBBY_PROOF` and stage 25 remains `NEEDS_LIVE_PROOF`.
- 2026-05-06: Landing/demo UI polish implemented on the existing rendering path (`src/picwise_surface/landing.py`) with top search form (`/demo?q=...`), cleaner 4-card layout, recommended-card emphasis updates (Picwise badge, two bubble chips, 3-pulse ring), lightweight day/night theme toggle, and minimal bottom bar credit ("Designed by Subby.cloud"). Route and safety behavior preserved (`/`, `/demo`, `/health`, `/subby-proof`), and tests updated in `tests/test_stage_22_live_deployment.py` and `tests/test_app_stages_16_to_21.py`. Test command: `python -m unittest discover -s tests` -> 106 tests passed (OK).
- 2026-05-06: Stage 27 visual correction pass completed for the live landing UI: premium header/nav + day/night pill toggle, centered hero/subtitle, unified rounded search component, subtle AI/circuit background accents, polished 4-card comparison layout, refined single recommended card with badge + bubble/pulse accents, discreet demo-data note, and full-width footer navigation with `Design by subby.cloud`. Routes and non-fake/no-cart behavior preserved; `python -m unittest discover -s tests` -> 109 tests passed (OK). Stages 23-25 remain unchanged (`NEEDS_REAL_FEED_CONFIG`, `NEEDS_LIVE_SUBBY_PROOF`, `NEEDS_LIVE_PROOF`).
- 2026-05-06: Stage 27 approved mockup structural alignment pass.
- 2026-05-06: Stage 27 final visual alignment pass.
- 2026-05-06: Landing/demo visual refinement pass aligned to latest approved reference direction: thin topbar with Picwise brand + required nav + day/night toggle, exact hero headline/subtitle, unified premium search shell with magnifier icons, subtle left/right background accents, 4 equal-height comparison cards with 4th recommended emphasis, single demo note placement, and thin full-width footer links/credit. Updated regression coverage in `tests/test_surface_stages_10_to_15.py`, `tests/test_app_stages_16_to_21.py`, and `tests/test_stage_22_live_deployment.py` (headline text, brand casing, structure guards, and forbidden legacy chips). Test command: `python -m unittest discover -s tests` -> 112 tests passed (OK). Stages 23-25 remain unchanged (`NEEDS_REAL_FEED_CONFIG`, `NEEDS_LIVE_SUBBY_PROOF`, `NEEDS_LIVE_PROOF`).
- 2026-05-06: Visual-match correction pass for the Picwise landing/demo based on latest reference crops: larger Picwise brand mark + wordmark spacing, premium sun/knob/moon day-night pill with `Day / Night` label, reduced hero title density, refined centered search pill with integrated blue action capsule, clearer low-contrast left network/right circuit background accents, softer 3 normal cards hierarchy, stronger single recommended card emphasis with upgraded badge and 3 crisp pulse rings plus anchored corner accents, and tightened thin footer spacing. Updated assertions in `tests/test_app_stages_16_to_21.py` and `tests/test_stage_22_live_deployment.py` for the approved toggle structure. Test command: `python -m unittest discover -s tests` -> 116 tests passed (OK). `/health` and `/subby-proof` semantics unchanged; no fake commerce/revenue/review behavior added.
- 2026-09-30: Added in-repo local provider feed fixture so the real-feed provider pipeline is runnable and regression-testable without the operator's private Awin feed. New files: `tests/fixtures/provider_feed_local_test_fixture.csv` (19 Awin-schema rows, every row marked `data_provenance=local_test_fixture`, all URLs inside the reserved `.invalid` TLD), `tests/fixtures/provider_feed_local_test_purchasability_cache.json`, `tests/test_picwise_provider_feed_local_fixture.py` (15 tests), and `docs/picwise_local_provider_feed_fixture.md`. Fixture proves at runtime: `provider_feed_ready`; 4+1 decision for `laptop`/`mouse`/`monitor`; out-of-stock, discontinued, image-less and price-less rows never become cards; accessory row never wins a main-product query; unmatched queries stay safely empty; all unverified selections report `purchasability_unknown` / `availability_state=weak` / `verified_purchasable=false` / ceiling `limited`; and cached verified `out_of_stock` + `missing_buy_button` rows are dropped from the four even though the feed row says `in stock`. Audit tools `tools/runtime_truth_audit.py` and `tools/purchasability_verifier_audit.py` no longer depend on a hardcoded operator Windows path: both resolve feed source as env -> operator private feed -> in-repo fixture and report `feed_source_kind`, with `feed_source_is_real_feed_proof=false` for the fixture; the verifier audit refuses page verification against fixture URLs; audit truth rows now carry `provider_product_id`, which they previously omitted. Also fixed a pre-existing failure (reproduced at HEAD in a clean worktree): `tests/test_picwise_runtime_truth_audit_fields.py::test_backend_dict_includes_truth_fields` hard-failed with `BTO feed required for audit` on any machine without the operator's feed; it now resolves a feed via the same env -> operator feed -> fixture order and restores `AWIN_FEED_FILE` in `tearDownClass` so no feed path leaks into modules that assert the provider-not-connected path. Test commands: `python -m unittest tests.test_picwise_provider_feed_local_fixture` -> 15 tests passed (OK); `python tools/runtime_truth_audit.py` -> full 11-query runtime capture now runs in-repo. THIS IS NOT REAL-FEED PROOF: stages 23-25 and the real-feed provider stages remain unchanged (`NEEDS_REAL_FEED_CONFIG`, `NEEDS_LIVE_SUBBY_PROOF`, `NEEDS_LIVE_PROOF`) and still require operator-supplied provider data plus a runtime truth audit against it. Stage 8C blockers still open: no batch verification loop at scale; no table-driven product-type matrix across mega categories (this fixture is the harness for one, not the matrix); `toner cartridge`/`ink cartridge`/`mini pc` still reach the feed path with `resolver_state=not_understood`.
- 2026-09-30: Mission delivery pass on the purchase-intent decision path, driven by running the app against a connected feed rather than reading code. Closed four Decision Contract / PROJECT_RULES gaps. (1) `/?q=<intent>` ignored the query and served the empty landing, so a visitor arriving from Google never saw a decision; `root_landing_html()` now passes the query through, fixed in BOTH route tables (`src/picwise_app/app.py` and `api/index.py`, which dispatch separately). `/demo` deliberately left informational. (2) `_PROVIDER_STORE_LABELS = {"awin": "Geekbuying via Awin"}` attributed every merchant in the Awin network to one shop; merchant now comes from the feed row via `extract_merchant_name()`, exported as `merchant_name`, rendered as `"<merchant> via <network>"` or `"<network> provider feed (merchant not named in feed)"` when the row names none -- never a guess. (3) Feed CTAs linked the raw product URL and emitted no tracking event; new `GET /out/feed?pid=&q=&src=&rec=` route (both route tables) re-resolves the product, re-checks card eligibility so an offer gone out of stock / discontinued / verified unbuyable is REFUSED not redirected, validates the URL, records `recommended_click`/`non_recommended_click` + `redirect_success` (or `redirect_failure`) per `docs/TRACKING_EVENTS_SPEC.md`, then 302s; `session_id=not_connected`, `conversion_value`/`revenue_value=not_applicable`, no fake revenue. (4) The committed search runtime artifact was STALE (`source_fingerprint_mismatch`), so every process start rebuilt the index live: first request measured 8,798ms on a 19-row feed against the 1,500ms target. Rebuilt via `tools/build_picwise_search_artifact.py` -> 945ms, and a new guard test fails loudly if it goes stale again (verified: the guard fails on the old artifact, passes on the rebuilt one). Latency, measured through `wsgi.py` on a generated 50,000-row gz feed (scratch, not committed): warm render 4,997ms -> 993ms (target <1500); click->redirect 3,241ms -> 23ms (target <300). Achieved by a parsed-feed cache and a resolved-pipeline cache, both keyed on feed file identity (path, mtime, size; URL feeds never cached), plus making the graph projection opt-in since nothing in search/selection/redirect reads it and it cost ~1s per render. All three are performance-only; no decision, eligibility or truth logic changed, and a test rewrites a feed file mid-run to prove a cached parse cannot keep an out-of-stock offer redirectable. Tests: `python -m unittest tests.test_picwise_mission_decision_delivery` -> 19 passed; provider/search modules -> 140 passed; app/surface/route modules -> 191 passed. Doc: `docs/picwise_mission_decision_delivery.md`. STILL OPEN and NOT claimed: per-choice `role_label`/`decision_label`/`key_reasons`/`risk_or_limitation` (contract item 3-4) are unimplemented because the label vocabulary is an undecided product decision and PROJECT_RULES section 4 forbids inventing business logic; impression events (`page_impression`, `choices_shown`, `recommended_shown`) are not emitted on the feed path; product-type coverage is limited to the query-intent map; and first request on a 50,000-row feed is still 5,534ms against the 1,500ms target. No stage status changed: 23-25 remain `NEEDS_REAL_FEED_CONFIG`, `NEEDS_LIVE_SUBBY_PROOF`, `NEEDS_LIVE_PROOF`.
