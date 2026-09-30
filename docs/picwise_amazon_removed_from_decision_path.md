# Amazon Removed From The Decision Path

Operator decision: the manually curated Amazon layer was a marketplace test. The
partnership is with Awin, and Amazon is no longer part of the product. Power banks — the
only category Amazon served — now resolve through the same provider-feed engine as every
other product type.

## What changed

One mapping drove the whole interception:

```python
_CONNECTED_PROVIDER_BY_CATEGORY = {"power_banks": "manual_amazon_affiliate"}
```

It is now empty. The dict is kept rather than deleted so a future manually connected
provider has a place to register, and so the generic gates built around it keep their
shape.

A second special case went with it. The resolver rewrote every power-bank query down to
the bare phrase:

```python
canonical_query = "power bank" if canonical_category == "power_banks" else ...
```

That existed only so the manual Amazon matcher would hit, and it discarded exactly the
tokens the feed selection needs to tell four choices apart: `power bank 20000mah for
iphone` reached selection as `power bank`. Queries now keep their own terms.

## What this fixes

The Amazon path rendered four cards with `recommended: False` on every one — four choices
and zero recommended, breaking Decision Contract item 2 on the flagship demo query. Routed
through the feed, `power bank` now returns four cards and exactly one recommendation, with
the fact-derived role labels, the tracked `/out/feed` redirect and the same truth fields as
every other product type.

## Consequences worth knowing

- `canonical_category` for power-bank queries is now the index phrase `power bank` instead
  of the id `power_banks`. This is the shape every other category already returned
  (`office chair`, `drill`, `webcam`); the old id came from the connected-provider branch
  that no longer applies. Power banks are now consistent with the engine rather than
  special.
- `resolver_state` for power banks is `understood_provider_not_connected` instead of
  `connected_provider_results`, and `result_allowed` is now `False`. Nothing is currently a
  connected manual provider, so no query produces `connected_provider_results`.
- With no provider feed configured, power-bank queries render the safe empty state, the
  same as any other query without inventory. They are no longer a special case that
  always had results.

## What was left in place

The Amazon code is dormant, not deleted: the manual registry, the matching functions, the
`/out/amazon` redirect and the Amazon proof routes still exist and their unit tests still
pass. Nothing in the decision path can reach them, because no category maps to
`manual_amazon_affiliate`.

Removing that layer entirely — registry, routes, proof pages and their tests — is a
separate cleanup. It is deliberately not bundled here: this change is closed and testable
on its own, and keeping the code dormant makes the decision reversible.

## Tests updated

Nineteen assertions across nine files encoded "power bank stays on the manual Amazon
path". Each was updated to the new intent rather than deleted, so the behaviour stays
pinned:

| File | Change |
|---|---|
| `test_live_search_resolver.py` | power bank resolves through the feed engine; query is not rewritten away |
| `test_picwise_real_feed_ui_exposure_stage8e.py` | power bank no longer uses the Amazon path |
| `test_app_stages_16_to_21.py` | search/results routes keep their shell assertions, assert no Amazon |
| `test_stage_22_live_deployment.py` | same, through the deployed entrypoint |
| `test_picwise_provider_resolver_wiring_stage8b.py` | the duplicated Amazon guard, one of five |
| `test_picwise_real_feed_search_activation_stage8c.py` | same guard |
| `test_picwise_real_feed_four_plus_one_stage8d.py` | same guard |
| `test_picwise_feed_selection_quality_stage8c_patch.py` | same guard |
| `test_picwise_common_provider_field_priority.py` | same guard |
| `test_pickwise_stage35_public_search_result_page.py` | public surface stays honestly empty |
| `test_pickwise_stage32_36_runtime_guardrails.py` | no connected-provider copy remains |

`tests/test_picwise_product_type_coverage_matrix.py` gained
`AmazonRemovedFromDecisionPathTests`: power bank is served by the feed with exactly one
recommendation, no matrix query renders an Amazon CTA, and no category maps to a manual
Amazon provider.

## Open finding this exposed

Routing power banks through the feed surfaced a much larger relevance problem, recorded in
`docs/picwise_query_qualifier_finding.md`: the selection scorer rejects any product unless
**every** query token matches feed text, so a single qualifier word that does not appear
literally empties the result set. `power bank` returns four choices; `power bank for
iphone` returns none.

## Test command

```bash
python -m unittest tests.test_live_search_resolver tests.test_picwise_product_type_coverage_matrix
```
