# PicWise Stage 8D — Real Feed 4+1 Backend Decision

## Purpose

Stage 8D adds backend-only recommendation metadata on top of Stage 8C real feed product selection. When exactly four real feed products are selected, the backend chooses one recommended product from those four and exposes reason codes explaining the decision.

## Behavior

### Selection (unchanged from Stage 8C)

- Generic dynamic feed selection via `select_provider_products_for_query`.
- Exactly four products when enough relevant matches exist.
- No hardcoded product IDs, titles, or categories.
- No 80–250 price band filtering.
- No commission-first ranking.

### Recommendation (Stage 8D)

When `selected_count == 4`:

- `provider_feed_decision_status = "recommended"`
- `provider_feed_recommended_product_id` is one of the four selected product IDs
- `provider_feed_recommendation_reason_codes` explains the choice

When `selected_count < 4`:

- `provider_feed_decision_status = "insufficient_selected_products"`
- No recommended product ID

When no feed selection is attempted:

- Decision fields remain unset in resolver output

### Scoring signals

Recommendation reuses real feed/search signals only:

- Strong query/title fit
- All query tokens in title
- Query phrase in title
- Product-type phrase in title
- Category alignment
- Main product (not accessory-like) when query seeks a main product
- Complete product fields (image, URL, price, availability)
- Price used only as a deterministic tie-breaker among equal primary scores
- No commission, random, rating, or review signals

## Exposed backend fields

Resolver and selection helpers expose:

- `provider_feed_selected_products`
- `provider_feed_decision_status`
- `provider_feed_recommended_product_id`
- `provider_feed_recommendation_reason_codes`

`result_allowed` remains `false` for feed-backed results. Manual Amazon `power_banks` path is unchanged.

## Files

- `src/picwise_providers/search_selection.py` — recommendation decision logic
- `src/picwise_providers/state.py` — selection + recommendation helpers
- `src/picwise_search/live_search_resolver.py` — resolver metadata wiring
- `tests/test_picwise_real_feed_four_plus_one_stage8d.py` — Stage 8D tests

## Test feed

```powershell
$env:AWIN_FEED_FILE="C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz"
python -m unittest tests.test_picwise_real_feed_four_plus_one_stage8d
```
