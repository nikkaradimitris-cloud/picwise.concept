# PicWise Stage 8C Patch — Feed Selection Quality + Resolver Feed Opportunity Gate

## Goal

Improve generic real-feed product selection quality and allow the backend resolver to expose feed selection metadata when the provider feed has strong, safe matches — even if the resolver would otherwise stop at `not_understood`, `broad_query_suggestions`, or `manual_review_required`.

## Selection quality changes

`select_provider_products_for_query()` now uses deterministic scoring bonuses and penalties:

- Positive: phrase-in-title, all tokens in title, category alignment, product-type token in title, complete product signals (image, URL, price, availability), non-accessory titles.
- Negative: accessory/part terms when the query appears to seek a main product, accessory-for-product title patterns, accessory pack prefixes, weak description-only matches, duplicate titles.

Accessory terms are penalized only when the query does not itself request accessories (for example `vacuum filter` or `printer filament` remain valid).

## Feed opportunity gate

The resolver may expose backend feed selection metadata when all of the following are true:

- query is not blocked or unsafe
- manual Amazon provider is not active
- provider feed is configured and ready
- selection returns at least four strong relevant products

Highly ambiguous broad single-token queries with five or more broad suggestions (for example `charger`) still skip feed lookup entirely.

Unsafe broad negatives (`bank`, `insurance`, homograph collisions such as `bots`) remain safe no-selection behavior.

This patch does not turn on UI cards and does not change `result_allowed`.

## Real feed test env

```powershell
$env:AWIN_FEED_FILE="C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz"
python -m unittest tests.test_picwise_feed_selection_quality_stage8c_patch
python -m unittest tests.test_picwise_real_feed_search_activation_stage8c
```

## Out of scope

- UI card rendering
- artifact rebuild
- Amazon manual path changes
- category-by-category hardcoding
- 80–250 price filtering
