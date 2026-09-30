# PicWise Product-Type Coverage Matrix

Replaces canary-query testing with a table-driven matrix across all 18 mega categories,
and records what it found.

## Correction to an earlier claim

`docs/picwise_mission_decision_delivery.md` previously listed as still open: *"the
decision only lands for product types the query-intent map knows
(`_QUERY_INTENT_ALLOWED_PRODUCT_TYPES`); everything else falls to the safe empty state."*

**That was wrong.** It was inferred from the 19-row fixture, where queries like `printer`
and `headphones` returned nothing — not because the code could not handle them, but
because that fixture holds no printers or headphones. The conclusion confused missing
inventory with missing capability.

Measured with inventory present, the selection layer is already generic: it matches on
title, category, brand and keyword tokens, and `_QUERY_INTENT_ALLOWED_PRODUCT_TYPES` is a
disambiguation hint, not a gate. A product type absent from that map still produces a
clean 4+1.

## The matrix

`tests/test_picwise_product_type_coverage_matrix.py` drives one row per mega category and
product type end-to-end through the deployed WSGI entrypoint, asserting four rendered
cards and exactly one recommendation. Inventory comes from
`tests/fixtures/provider_feed_coverage_matrix_fixture.csv`: 108 rows, four products for
each of 27 product types, every row marked `data_provenance=local_test_fixture` with
`.invalid` URLs.

This is what `docs/picwise_runtime_truth_audit_rules.md` asks for when it says example
queries are canaries only and do not prove generic product-type intelligence. It proves
capability given inventory. It proves nothing about what a real feed contains.

Result: **26 of 27 product types deliver 4+1**, spanning all 18 mega categories.

## What the matrix found

### 1. The intent map vetoed the feed's own product type

`_QUERY_INTENT_ALLOWED_PRODUCT_TYPES` keys on single tokens, so `monitor` maps to
`computer monitors`. A query of `blood pressure monitor` therefore scored its own correct
feed type, `Blood Pressure Monitors`, as a *conflict* and applied the −320 penalty,
dropping every match below the threshold. `baby monitor` collides the same way.

Fix: when a multi-token query's tokens all appear in the feed's own product type, the feed
is the better authority and the mapped hint no longer applies. The relaxation is
restricted to multi-token queries on purpose — a single token matching a broader type is
exactly what the penalty exists for, so `laptop` must still not be satisfied by
`Laptop Cases & Bags`. That case is asserted directly.

Matching is by substring, because feed product types are plural (`Blood Pressure
Monitors`) while queries are singular (`blood pressure monitor`). Requiring every token
keeps it tight.

### 2. A recommendation was reported with no products behind it

For `tv`, the resolution reported `provider_feed_selection_status="selected"`,
`provider_feed_decision_status="recommended"` and a `recommended_product_id`, while
`provider_feed_selected_products` was **empty**.

The cause: a weak feed-opportunity selection is *reported* for audit purposes but not
*exposed*, and the reporting branch set the decision fields regardless of exposure. The UI
refused to render, which is why nothing visibly broke, but the backend truth fields
contradicted each other — and `docs/picwise_runtime_truth_audit_rules.md` forbids
overclaiming a recommendation without the evidence behind it.

Fix: when products are not exposed, the decision is reported as
`recommendation_withheld_weak_feed_opportunity`, with no recommended id and confidence
`unknown`. An exposed selection still reports `recommended` with its id, unchanged. A test
asserts across every matrix query that a reported `recommended` always has products behind
it.

### 3. The Amazon path renders four choices and no recommendation

`power bank` is the one query routed to the manually curated Amazon path rather than the
provider feed. That path renders four cards with `recommended: False` on every one, so it
delivers **4 choices and 0 recommended**, breaking Decision Contract item 2 (exactly one
recommended choice). It is the flagship demo query, so this is the most visible instance
of the violation.

It is **not fixed here**, deliberately. The manual records carry a title, a `slot_label`
and an ASIN — no price, no rating, no verification — so no fact in the data can select one
of the four, and PROJECT_RULES section 4 forbids inventing the criterion. Picking the
recommended option among four real products is an editorial decision for the operator.

The mechanism that would close it: an operator-set recommended flag plus a reason on the
manual registry record, rendered as the single recommendation. The choice itself has to
come from the operator.

`tests/test_picwise_product_type_coverage_matrix.py` asserts the current
non-compliant state so it cannot regress silently or be forgotten. When the operator
supplies the recommended slot, that test should be changed to require exactly one, not
deleted.

## Remaining gap: `tv`

`tv` is not recognised as a synonym of `television`. The string is not a substring of
`television`, so neither the title nor the product type matches, and the query reaches
only a weak match that the feed-opportunity gate correctly refuses to expose.

This belongs in the taxonomy/vocabulary layer, whose deep packs feed the search artifact
fingerprint. It is deliberately **not** patched into the feed scorer: the runtime truth
rules forbid building a second vocabulary system, and a synonym added there would diverge
from the index the rest of the product uses. Closing it means editing a deep pack,
rebuilding the search artifact and revalidating the index blind-evaluation thresholds
across 38,216 entries — a separate change with its own blast radius.

The matrix asserts that `tv` still renders zero cards, so if the vocabulary gap is closed
the test fails and the row moves into the covered matrix.

## Test command

```bash
python -m unittest tests.test_picwise_product_type_coverage_matrix
```
