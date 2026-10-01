# PicWise Local Provider Feed Fixture

In-repo provider feed fixture that makes the real-feed provider pipeline runnable and
regression-testable without the operator's private Awin feed file.

## Why

Before this fixture, every provider/search/recommendation stage could only be exercised
end-to-end on one machine: `AWIN_FEED_FILE` pointed at a private feed on the operator's
desktop. Anywhere else the pipeline stopped at `provider_feed_not_configured`, so the 4+1
decision path, the offer-health gates and the purchasability cache gate had no runtime
coverage at all — only unit tests. `docs/picwise_runtime_truth_audit_rules.md` forbids
closing those stages on unit tests alone.

## Files

| File | Role |
|---|---|
| `tests/fixtures/provider_feed_local_test_fixture.csv` | Awin-schema feed rows (plain CSV, reviewable in git) |
| `tests/fixtures/provider_feed_local_test_purchasability_cache.json` | Verified purchasability cache entries for three of those rows |
| `tests/test_picwise_provider_feed_local_fixture.py` | Regression coverage over both |

The feed is stored as plain CSV so diffs stay reviewable. The gzip code path
(`stage 8A`) is exercised by gzipping the fixture into a temp file inside the test, so
both payload shapes are covered without a binary blob in the repo.

## What the fixture is not

This is **local test data**, not provider data:

- Every row carries `data_provenance=local_test_fixture`.
- Every URL sits inside the reserved `.invalid` TLD, so no fixture URL can ever resolve
  to a real merchant page or be mistaken for an affiliate link.
- Brands (`Fixturon`, `Testline`, `Sampleworks`) are non-existent by construction.

It therefore **cannot** support stage closure for real feed/affiliate connection. Stages
23-25 and the real-feed provider stages still require operator-supplied provider data plus
a runtime truth audit against it. A test run against this fixture is not live proof, and
must never be reported as one.

## Feed rows

The 19 rows are chosen to cover each gate, not to look like a catalogue:

| Rows | Purpose |
|---|---|
| 6 × `Laptops`, 4 × `Mice`, 4 × `Computer Monitors` (in stock, complete) | enough inventory for a real 4+1 decision per product type |
| `fx-laptop-oos` (`out of stock`) | verified-unavailable row must never become a card |
| `fx-laptop-eol` (`discontinued`) | discontinued row must never become a card |
| `fx-laptop-bag` (`Laptop Cases & Bags`) | accessory must not win a main-product query |
| `fx-laptop-noimg`, `fx-laptop-noprice` | incomplete rows must fall to `needs_review` |

## Purchasability cache fixture

Three cache entries prove the gate works in both directions:

| Row | Cached state | Expected runtime truth |
|---|---|---|
| `fx-laptop-1` | `purchasable`, confidence `high` | `purchasability_state=purchasable`, `verified_purchasable=true` |
| `fx-laptop-3` | `out_of_stock` | dropped from the four, although the feed row says `in stock` |
| `fx-laptop-6` | `missing_buy_button` | dropped from the four |

The last two are the important ones: feed `availability_text` never overrides verifier
evidence.

## Runtime behaviour observed on this fixture

`python tools/runtime_truth_audit.py`

| Query | Selection | Decision |
|---|---|---|
| `laptop`, `mouse`, `monitor` | `selected` (4) | `recommended` (1 of the 4) |
| `office chair`, `laptop bag`, `dell laptop`, `headphones`, `printer`, `logitech webcam` | `insufficient_relevant_products` | safe empty |
| `toner cartridge`, `ink cartridge`, `mini pc` | `insufficient_relevant_products` | safe empty, but `resolver_state=not_understood` |

All selected products report `purchasability_state=purchasability_unknown`,
`availability_state=weak`, `verified_purchasable=false` and
`recommendation_confidence_ceiling=limited` unless the cache fixture is applied. That is
the truthful result: feed fields alone are not purchasability evidence.

## Audit tool changes

`tools/runtime_truth_audit.py` and `tools/purchasability_verifier_audit.py` previously
hardcoded the operator's Windows feed path as their only fallback. Both now resolve a feed
source in this order:

1. `AWIN_FEED_FILE` env variable
2. the operator's private feed, if present on this machine
3. the in-repo local test fixture

Both report `feed_source_kind` in their output, and `runtime_truth_audit.py` reports
`feed_source_is_real_feed_proof`, which is `false` for the fixture. This keeps audit output
self-labelling: it can never be pasted into a stage closure as real-feed proof by mistake.

`purchasability_verifier_audit.py` refuses to run page verification against the fixture
instead of fetching `.invalid` hosts, because those fetches would write meaningless
`invalid_page` states into the cache.

`runtime_truth_audit.py` truth rows now include `provider_product_id`. They previously
omitted it, so per-product field inspection (audit rule 6) could not tell which product a
row described.

## Open items this does not close

- Stage 8C blocker: no batch verification loop populating the cache at scale.
- Stage 8C blocker: canary queries only — no table-driven product-type matrix across mega
  categories. This fixture is the harness such a matrix can be built on; it is not the
  matrix.
- Stage 8C blocker: `toner cartridge`, `ink cartridge` and `mini pc` reach the feed path
  with `resolver_state=not_understood`.
- Observed on the cache fixture: when one of the four is verified purchasable and the
  others are `purchasability_unknown`, the recommendation can still land on an unverified
  product, and `recommendation_confidence_ceiling` stays `limited`. Whether verification
  evidence should promote a product into the recommended slot is a product decision that
  the concept and specs do not currently answer — flagged, not implemented.

## Test command

```bash
python -m unittest tests.test_picwise_provider_feed_local_fixture
```
