# PicWise Mission Truth Audit — 2026-10-08

Audit of whether the running implementation is faithful to `docs/MISSION.md` (Mission
Lock, unchanged by this audit), `concept.picwise.txt` and the contracts in `docs/`.
Findings were established by running the deployed WSGI entrypoint (`api/index.py`, the
file Vercel serves) in-process against feeds, following every card CTA through
`/out/feed`, and tracing the code behind each observation. Unit tests were not taken as
evidence of behaviour.

All feeds used are local test data: the in-repo fixtures plus adversarial feeds built for
this audit (fictional brands, `.invalid` URLs, `data_provenance=local_test_fixture`).
**Nothing here is proof against a real Awin feed** — none is connected, and this cloud
environment blocks `productdata.awin.com` and `picwise.subby.cloud`.

Priority used throughout: truth > correctness > runtime > product behaviour > tests > UI.

## The real chain

```
GET /search?q=… (also /, /results)            api/index.py  (Vercel)  |  src/picwise_app/app.py (local)
 → PicwiseLocalApp.picwise_reference_html
 → resolve_live_search                          src/picwise_search/live_search_resolver.py
     NLU word intent, concept reading, search-index lookup, broad-query gate
 → provider feed                                src/picwise_providers/awin_adapter.py (AWIN_FEED_URL / _FILE)
     normalize_feed_row_to_provider_product     normalization.py
     base eligibility (title/url/id/image/price/availability)   eligibility.py
     purchasability cache enrichment (only if PICWISE_PURCHASABILITY_CACHE_FILE)
     card eligibility: offer health, availability, purchasability   offer_health.py
 → selection of 4                               search_selection.select_provider_products_for_query
     concept path or token path; dedupe; relaxation with disclosure
 → recommendation of 1                          search_selection.decide_recommended_provider_product
 → fact-based labels                            decision_labels.py
 → cards + gate                                 src/picwise_surface/reference.py
 → impression events (in-process list)          app.record_decision_impression
GET /out/feed?pid=… → re-resolve + re-check eligibility → click events (in-process) → 302 merchant URL
```

Not on the user path at all: `picwise_engine` (5 brains, 3 depths, stages 5–9), the MVP
private-beta flow (`LocalFixtureOfferSourceAdapter`), `render_landing_surface` (mock cards
with hardcoded ratings), the purchasability verifier (offline tool). `/best/<slug>` and its
sitemap **are** on the user path — see D1.

## A. What exists today

A provider-feed decision path that delivers four cards and one recommendation from an
Awin-schema feed, with fact-derived labels, a tracked and re-validated redirect, Greek /
greeklish / misspelled query understanding, honest partial-match disclosure, and an empty
state when it cannot deliver. A separate SEO buying-page system serving 95 public pages.

## B. What really works (observed at runtime, fixture data)

| Check | Result |
|---|---|
| `laptop`, `mouse`, `monitor`, `πλυντήριο ρούχων`, `καφετιερα`, `tv` | 4 cards + 1 recommended, every CTA → `/out/feed` → `302` to the row's own URL |
| Click-time re-validation | a product made unavailable after render is refused, not redirected |
| `laptop bag` with no bags in stock | safe empty state, no padding with laptops |
| Varied feed with explicit `discontinued` | row blocked |
| Mixed currencies | role labels refuse to rank (`Price not comparable with the others`) |
| Merchant attribution | taken from the row; absent merchant is stated as absent |
| Commission | no commission, payout or EPC field is read anywhere in selection or recommendation (grep) |
| Fewer than 4 qualifying products | no fake product is ever invented; the page shows nothing (see section 11 of the report) |

## C. What does not work

Summarised in D–I. The decision path is honest in most places; the failures cluster in
(1) a fake-data subsystem that is live, (2) stock truth, (3) product vs offer identity,
(4) how the four and the one are chosen and explained.

## D. Critical blockers

**D1. `/best/<slug>`: fabricated products, prices, ratings and reviews, live.**
95 pages listed in `/sitemap-buying-pages.xml` (absolute `https://picwise.subby.cloud/best/…`
URLs, most marked `index,follow`) render deterministic fixture data from
`picwise_buying_pages/fixtures.py`: brand `Picwise Demo`, price from a formula,
`rating = 4.1 + 0.2 × slot`, `reviews_count = 80 + 3 × page + 17 × slot`, sellers
`PickWise Partner N` marked `TRUSTED`, a "Recommended by PickWise" badge, and a CTA to
`https://example.com/best/…` (a dead link, no tracking). Observed:
`Picwise Demo Home Option 3 — EUR 192.00 — Rating: 4.5 (153 reviews) — Recommended by PickWise`.
On `main` since `881572a` (2026-05-15). Breaks every Trust and Neutrality line of the
Mission Lock.

**D2. Out-of-stock products shown and recommended, with a false "available" line.**
`offer_health._collect_product_availability_values` reads only the *first* non-empty of
`availability, in_stock, stock_status, availability_text`, and a value that is constant
across the feed is downgraded to `weak`, which does not block. Observed:
- Awin shape `in_stock=1` on every row, truth in `stock_status`: the `out of stock` jug was
  **the recommendation**, and its card said *"Listed as available by the provider feed"*.
  `docs/awin_feed_setup_el.md` asks for exactly these two columns.
- `stock_status=OutOfStock` (schema.org form): not recognised; the out-of-stock toaster was
  **the recommendation**.
- A feed whose rows are all `out of stock`: four out-of-stock fans shown, one recommended.

**D3. One product shown as four choices.** The same phone (one EAN, one MPN) from four
merchants with slightly different titles rendered as four cards ranked "lowest" to
"highest price", while two genuinely different phones in the feed were not shown. Dedupe
compares `aw_product_id` and exact normalised title only; EAN/GTIN/MPN are never read.

**D4. Which four are shown among equally relevant products is alphabetical.** The final
sort key is `(-score, -title_matches, -matched_tokens, title, id)`. Broad queries tie on
score, so title order decides: for `laptop` both `Testline` laptops were dropped because
"T" sorts after "F" and "S". On a large feed the four for `laptop` would be the four
alphabetically-first titles. The Decision Contract lists the ranking formula and the
tie-break protocol as `TODO`; replacing this needs an owner decision (see report).

**D5. Decision and click events are not recorded anywhere durable.** They live in a
per-process list of 200–400 entries, lost on every serverless restart. Only
`query_served` has a durable sink, and it is inactive until a Supabase project is chosen.

## E. Product-truth problems

- E1. False "Listed as available by the provider feed" on out-of-stock rows (D2).
- E2. `condition` is ignored: a **refurbished** speaker was the recommendation, labelled
  "Lowest price of these four" against new ones, with nothing on the card saying so.
- E3. `is_for_sale=0` and an offer with `valid_to=2020-01-01` were shown as choices.
- E4. The large price on every card has no currency (`749.00`); the currency appears only
  in the smaller description line.
- E5. With a feed connected but too few matches, the empty state says *"no safe provider
  is connected yet"* — false once the feed is connected.
- E6. `GET /private-beta-readiness` (public) reports `ready` and *"Source intake status:
  connected"*, computed from a local fixture adapter, not from the production feed.
- E7. Purchasability-cache entries never expire (latent: the cache is not configured in
  production).
- E8. `Login` and `Register` controls on the search page and buying pages do nothing.
- E9. `render_landing_surface` (hardcoded `4.4 (1,248)` … `4.8 (5,214)` ratings) is exported
  from `picwise_surface` though no route calls it (latent).

## F. Search / retrieval problems

- F1. `plintirio`: the page says *"This search is too broad"* and shows four washing
  machines with a recommendation at the same time.
- F2. Relaxation fills the four with partial matches and says so only in the query line
  (`power bank 20000mah για iphone` → *"Only some of the four match: 20000mah (1 of 4)"*);
  the cards do not say which ones miss the request.
- F3. The accessory penalty matches substrings: `Standard` counts as `stand`, `Kitchen` as
  `kit`, `… with USB-C Cable` as an accessory. For `power bank` the recommendation went to
  the dearest of four equally relevant power banks only because the others' titles
  contained those strings.

## G. Ranking / recommendation problems

- G1. When the four tie on relevance (every canary query did: 545/545/545/545), the
  recommendation is the cheapest. The code meant to say so never does: the sort key stores
  `-has_price` (`-1`) but the tie check tests `== 1`, so `price_tie_breaker` is dead code,
  and the surface has no label for it. The page shows *"Strong match to your search ·
  Contains the key search terms · Search phrase appears in the product title"*, which is
  equally true of all four. The disclosure says the pick is "based on search fit".
- G2. The tie-break uses its own price parser: `1.099,00` → `1.099`, so the recommendation
  went to a fridge its own card labels "3rd lowest price". It also compares across
  currencies (95 GBP "beat" 100 EUR) while the labels on the same page refuse to.
- G3. When relevance and price both tie, the winner is the alphabetically-first title,
  presented like any other recommendation.
- G4. Ranking uses text relevance, field completeness and accessory/type adjustments only;
  verified purchasability, condition, delivery and real ratings (where a feed has them)
  are not used. Not a fake signal — an absent one.

## H. Runtime / integration problems

- H1. Cold first request ≈ 1.8 s on the 19-row fixture (target 1.5 s): `validate_registry`
  deep-copies the mega-category registry once per record (2,379 copies, ~half the cold
  time under a profiler).
- H2. Brains and decision depths (PROJECT_RULES sections 6–7, concept section 13) are not
  on the runtime path; `brain_selected` / `depth_selected` are never emitted.
- H3. Availability is evaluated against different populations (whole feed, eligible set,
  the four, a single product), so the `availability_state` exported on a card can differ
  from the one selection used (it under-claims; never over-claims).
- H4. A large feed is downloaded and parsed once per serverless cold start (known open item).
- H5. `GET /subby-proof` can be triggered by anyone and stamps `operator_generated: true`.

## I. UI / data-contract problems

- I1. CTA reads "View product"; the spec and concept call for a store-direction CTA
  ("View in Store", "Δες στο κατάστημα").
- I2. No secondary "More" (concept section 10).
- I3. Role labels are price ranks by design (no data supports Budget / Best Overall / …).
- I4. `/out/feed` without `rec` is logged as `non_recommended_click`; `cta_click` and
  `redirect_attempt` are not emitted; `redirect_success` is written when the 302 is issued.

## J. Test / verification gaps

- J1. Route tests assert that the fixture buying pages render — they encode D1 as correct.
- J2. No test for multi-field availability, schema.org tokens or a constant out-of-stock feed.
- J3. No test for one product sold by several merchants.
- J4. The `price_tie_breaker` branch is dead and untested; no test checks that the shown
  reason distinguishes the recommended product.
- J5. No European-format or cross-currency test on the recommendation path.
- J6. **NOT VERIFIED:** anything against a real Awin feed, real merchant pages, the live
  domain, or real click/redirect latency in production.

## Reproduction

Probe scripts used for this audit drive `api/index.py` exactly as Vercel does; the
adversarial feeds are generated, never committed. The regression tests added with the
fixes (see the commits that follow this document) pin each finding.

## Status after fixes (2026-10-08)

Fixed at the layer that caused each, one commit per root cause, each with tests. The
Mission Lock was not changed.

| Finding | Status | Where it was fixed | Pinned by |
|---|---|---|---|
| D1 fabricated `/best` pages | **Fixed** — public repository empty, sitemap lists nothing, every seed slug 404 | `picwise_app/buying_routes.py` | `test_picwise_no_fabricated_public_pages` (+30 route guards rewritten to the truthful baseline) |
| D2 / E1 out-of-stock shown and recommended | **Fixed** — every availability column read; stock words decide anywhere; bare flags decide where their column varies; schema.org forms read | `offer_health.interpret_availability_state` | `test_picwise_stock_and_offer_truth` |
| E3 not-for-sale, pre-order, expired, not-yet-valid offers | **Fixed** (needs the columns in the feed) | `offer_health.offer_flag_reason_codes` | same |
| H3 four availability populations | **Fixed** — one context over the whole feed for selection, card fields, recommendation and redirect | `state.py`, `search_selection.py`, resolver | same |
| E2 hidden refurbished / used condition | **Fixed** — disclosed next to the price rank and in the limitation | `decision_labels.py` | `test_picwise_fact_based_decision_labels`, `test_picwise_stock_and_offer_truth` |
| E4 price without currency | **Fixed** | `reference.py` via `format_price_display` | same |
| G1 hidden deciding reason | **Fixed** — `closer_search_match` / `price_tie_breaker` / `tie_on_search_match_and_price`, shown first | `decide_recommended_provider_product` | `test_picwise_recommendation_reason_truth` |
| G2 tie-break parser and cross-currency compare | **Fixed** — labels' parser, never across currencies | same | same |
| G3 arbitrary full tie presented as a judgement | **Disclosed**, not changed: the card says nothing separates them | same | same |
| D3 one product as four choices | **Fixed** — GTIN / brand+MPN identity, cheapest offer kept, planner counts products | `search_selection.py` | `test_picwise_product_offer_identity` |
| F3 accessory substrings | **Fixed** — whole words, plurals, "with …" is in the box | `search_selection.py` | `test_picwise_recommendation_reason_truth` |
| E5 "no provider connected" with a connected feed | **Fixed** | `reference.py` | `test_picwise_public_status_truth` |
| E6 readiness endpoint claiming "connected" | **Fixed** — reports the production feed status | `launch_readiness.py`, `app.py` | same |
| H1 cold start | **Fixed** — first request 1,019–1,081 ms → 677–724 ms; import + first request 1,360–1,462 ms → 1,045–1,078 ms (19-row fixture) | `validation.py` (+ artifact rebuilt) | `test_picwise_performance_stage1a` (race fixed) |
| I1 CTA hid the destination | **Fixed** — "View in Store" | `reference.py` | `test_picwise_stock_and_offer_truth` |
| D4 alphabetical choice of the four | **Fixed by owner decision** — more than four substantially equivalent products are spread across the price range (cheapest, two between, dearest), hard filters first; recorded in the Decision Contract | `search_selection._choose_shown_products` | `test_picwise_price_range_diversity` |
| D5 click and decision events not stored | **Open — owner decision** (Supabase project) | — | — |
| F1, F2, G4, H2, H4, H5, I2, I4, E7–E9 | **Open**, recorded above; none is a fabricated claim on the live path | — | — |

Misspelling benchmark after all fixes: **96.0% pass, 0 wrong kind of product** (unchanged).
`docs/awin_feed_setup_el.md` now asks for the columns the new gates read (`ean`,
`product_GTIN`, `mpn`, `condition`, `is_for_sale`, `pre_order`, `valid_from`, `valid_to`).
