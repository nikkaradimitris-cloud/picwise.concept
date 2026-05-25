# PicWise Stage 8B — Provider Resolver Wiring

## Goal

Expose provider/feed readiness metadata in live search resolution without changing UI card behavior or manual Amazon behavior.

## Resolver metadata

`LiveSearchResolution` now optionally includes:

- `provider_feed_status`
- `provider_feed_reason_codes`
- `provider_feed_eligible_count`

These fields are populated only when:

1. A graph/search-recognized mega category is present
2. The category is not served by a connected manual provider (currently only `power_banks`)
3. The query is not in broad-query suggestion mode
4. The query is not blocked/unsafe

## Feed status behavior

| Status | Cards allowed | Typical resolver state |
| --- | --- | --- |
| `provider_feed_not_configured` | No | `understood_provider_not_connected` |
| `provider_feed_parse_failed` | No | `understood_provider_not_connected` |
| `provider_feed_empty` | No | `understood_provider_not_connected` |
| `provider_feed_no_eligible_products` | No | `understood_provider_not_connected` |
| `provider_feed_ready` | No (metadata only) | `understood_provider_not_connected` |

`result_allowed` remains `False` for all Awin/feed statuses in this stage.

## Manual Amazon preservation

`power_banks` continues to use:

- `provider_key = manual_amazon_affiliate`
- `provider_status = connected`
- `resolver_state = connected_provider_results`
- `result_allowed = True` when existing gates pass

No provider feed lookup runs for connected manual categories.

## Next stage

Stage 8C+ can consume `provider_feed_ready` metadata for ranking and 4+1 card selection without changing resolver safety gates in this stage.
