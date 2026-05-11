# PickWise Stage 32-36 MVP Launch Flow

## Scope Delivered

This package implements Stage 32 through Stage 36 as one integrated MVP flow:

1. Query enters existing NLU/runtime intent path.
2. Product source intake returns deterministic external offer candidates.
3. Eligibility gate filters candidates using safe status outcomes.
4. Recommendation engine builds up to 4 display slots and one Wise recommendation only when safe.
5. Public `/search` and `/results` surface renders honest states.
6. Private beta readiness report verifies MVP launch checks.

## Stage 32: Product Source / Offer Intake Layer

- Added contract-first source and offer candidate models in `picwise_offers`.
- Added deterministic fixture adapter with no network or scraping.
- Added CSV/JSON import contract adapters (parse-only, local text input).
- Added source status handling for `connected`, `not_connected`, `needs_data`, and manual review-safe paths.
- All candidate fields stay null/absent when source data is not available; no fake data is injected.

## Stage 33: Product Eligibility Gate

- Added gate statuses: `eligible`, `rejected`, `needs_data`, `manual_review`, `not_connected`, `not_applicable`.
- Rejects/holds candidates for:
  - missing title,
  - missing required image for retail physical products,
  - missing or invalid outbound URL,
  - vertical/category mismatch,
  - duplicate product records,
  - unsafe or unknown source trust,
  - placeholder/fake commercial markers,
  - finance-regulated/manual review cases,
  - missing retail taxonomy linkage.
- Gate does not invent missing fields.

## Stage 34: 4-Product Wise Recommendation Engine

- Deterministic recommendation scoring (no LLM, no external API).
- Produces:
  - up to 4 `ProductDisplaySlot` entries,
  - `not_enough_valid_candidates` when fewer than 4 safe candidates exist,
  - one `WiseRecommendedProduct` only when score margin and outbound contract are safe.
- No filler cards are generated.
- Output includes explanation, tradeoff summary, confidence, and risk status.

## Stage 35: Public Search / Buying Result Page

- Added public result route support:
  - `/search`
  - `/results`
- Route integrates:
  - existing query decision/router behavior,
  - Stage 32 intake,
  - Stage 33 eligibility,
  - Stage 34 recommendation output,
  - honest empty/not_connected/needs_data/manual_review states.
- Search results are rendered with `noindex, nofollow`.
- Existing routes remain intact:
  - `/health`
  - `/`
  - `/demo`
  - `/picwise-reference`
  - `/best/...`
  - `/sitemap-buying-pages.xml`

## Stage 36: MVP Deploy / Private Beta Readiness

- Added `picwise_mvp.launch_readiness` report builder.
- Readiness checks include:
  - app/search route health,
  - honest source status behavior,
  - eligibility gate active,
  - recommendation engine active,
  - no fake commercial data,
  - no owned inventory/cart/checkout/payment,
  - finance manual-review safety,
  - sitemap/noindex safe behavior.
- Readiness statuses:
  - `ready`
  - `not_ready`
  - `needs_data`
  - `blocked`
  - `manual_review`

## Explicit Non-Goals Preserved

- Stage 37 is deferred and not implemented.
- No SEO buying pages foundation in this stage.
- No new indexable SEO pages.
- No sitemap expansion beyond existing buying pages behavior.
- No scraping.
- No live external API integration.
- No owned inventory, cart, checkout, payment, warehouse, or marketplace ownership.
- No fake prices, availability, sellers, affiliate payouts, revenue, ROI, or conversion claims.
- No finance quote/approval/eligibility/application decision automation.
