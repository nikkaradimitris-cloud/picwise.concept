# PicWise Stage 8C — Real Feed Search Activation

## Goal

Connect the existing PicWise search/provider mechanism to the real Geekbuying Awin feed so recognized product searches can return exactly four real provider products when enough relevant products exist.

## Generic backend path

```
query
  → existing resolver/search understanding
  → provider feed products
  → relevance match (`select_provider_products_for_query`)
  → duplicate filter
  → select 4 real products
  → expose backend selection safely on `LiveSearchResolution`
```

## Selection rules

- Query normalization uses existing `normalize_query`.
- Matching uses real feed fields only:
  - title / product_name
  - category_name / merchant_category / category_text
  - keywords
  - description only when present and safely bounded
- Title matches score strongest, then category, then keywords, then description.
- All query tokens must match somewhere across searchable fields.
- Near-identical titles and duplicate product IDs are deduped.
- Ordering is deterministic; no randomness and no commission-based ranking.
- No 80–250 SEO price filtering is applied in search selection.

## Resolver exposure

When a recognized product search resolves with `provider_feed_ready`:

- `provider_feed_selection_status`
- `provider_feed_selection_reason_codes`
- `provider_feed_matched_count`
- `provider_feed_selected_count`
- `provider_feed_selected_products` (masked URLs, real title/price/availability only)

If fewer than four relevant products exist:

- `provider_feed_selection_status = insufficient_relevant_products`
- no selected products are attached

`result_allowed` remains unchanged. Manual Amazon `power_banks` behavior is unchanged.

## Real feed test env

```powershell
$env:AWIN_FEED_FILE="C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz"
python -m unittest tests.test_picwise_real_feed_search_activation_stage8c
```

## Out of scope

- UI card rendering
- artifact rebuild
- Amazon manual path changes
- category-by-category hardcoding
- commission-first ranking
