# PicWise Runtime Truth Audit Rules

Permanent closure gate for PicWise provider, search, recommendation, and product-card stages.

## Stage closure is forbidden with unit tests only

No PicWise provider/search/recommendation/card stage may be closed using unit tests alone. Every relevant stage must include all of the following before closure:

1. **Unit tests** — isolated logic for normalization, eligibility, selection, offer health, and recommendation.
2. **Regression tests** — canary queries (e.g. laptop, mouse, webcam) that detect regressions but do not prove full generic intelligence.
3. **Integration / runtime tests** — end-to-end resolver wiring with real or representative feed data.
4. **Git diff forbidden-file audit** — confirm no changes to UI surfaces, Amazon manual path, SEO/sitemap/buying pages, artifacts, `api/index.py`, `wsgi.py`, reference UI, or visual assets unless explicitly scoped.
5. **Runtime output inspection** — run live resolver/search flow and capture decision status, selected products, and truth fields.
6. **Selected product / card field inspection** — verify `card_eligible`, `availability_state`, `purchasability_state`, `recommendation_confidence`, and reason codes on each selected product.
7. **Real product URL checks** (where applicable) — manual or audit-only reachability / buy-button / stock checks; not live scraping in search runtime.
8. **No-overclaim proof** — backend and UI output must not overclaim availability, reviews, ratings, recommendation confidence, or purchasability without verifier evidence.

## Product card truth rules

- Product cards must **not** be treated as verified purchasable unless real verification evidence exists.
- `purchasability_unknown` is **not** `purchasable_confirmed`.
- Verified `out_of_stock`, `missing_buy_button`, `discontinued`, invalid URL, or `redirect_suspect` must **block** purchasable cards and recommendation.
- Feed `availability_text` alone is not verified purchasability unless `purchasability_state` is `purchasable` with verifier confidence.

## Canary vs full proof

Example query tests (laptop, mouse, webcam, monitor, etc.) are **canaries only**. They detect regressions; they do not prove full generic product-type intelligence or feed-wide correctness.

## Full stage closure requirement

Full stage closure requires: **Runtime Truth Audit OK**.

If runtime truth contradicts tests, the stage **remains open**. Document mismatches as blockers for the next stage.

## Forbidden during audit-only runs

Do not modify provider logic, UI, Amazon manual path, SEO/sitemap/buying pages, artifacts, `api/index.py`, `wsgi.py`, reference UI, or visual files as part of an audit. Do not create a second search/index system. Do not fake availability, reviews, ratings, stock, cart status, delivery time, revenue, popularity, or store trust.

## Pass criteria

An audit passes only when:

1. This rule file exists.
2. Required tests pass.
3. Runtime output is truthfully labeled.
4. No product is claimed as verified purchasable without verification evidence.
5. Real-world mismatches are documented as blockers.
6. No forbidden files are changed.
