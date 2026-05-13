# PickWise Stage 38 - Real Offer Source Adapter + Gate-Aligned Candidate Enrichment

## What this stage adds

Stage 38 adds an additive adapter module at `src/picwise_offers/affiliate_feed_adapter.py` that prepares local feed rows for the existing `OfferCandidate` contract.

- Accepts local dict-like rows that are suitable for future CSV/JSON feed ingestion.
- Maps external feed keys into `OfferCandidate` fields without changing the contract.
- Preserves optional `affiliate_url` and `outbound_url` handling for existing outbound flow compatibility.
- Attaches transparent enrichment metadata for seller trust, shipping, returns, short description, specifications, and taxonomy linkage when present.
- Produces deterministic row-level statuses and reason codes (`mapped`, `review_required`, `rejected`) for auditability.

## What this stage does not add

This stage is intentionally non-breaking and does not change runtime behavior:

- No public route changes and no new `/best/...` page wiring.
- No sitemap expansion and no mass page generation.
- No changes to closed Local NLU, decision router, search engine, or core runtime behavior.
- No scraping, no live API calls, and no affiliate credentials.
- No synthetic/fake products or fabricated product claims.

## How real affiliate feeds map into `OfferCandidate`

The adapter maps incoming row keys into existing fields using deterministic key aliases:

- Identity: `candidate_id` from `candidate_id|offer_id|product_id|id|sku|item_id`
- Core required for mapping quality: `title`, `seller_name`, and at least one of `outbound_url` or `affiliate_url`
- URLs: `product_url|url|landing_page_url|link` -> `outbound_url`; `affiliate_url|tracking_url|deeplink` -> `affiliate_url`
- Seller: `seller_name|merchant|store|vendor` -> `seller_name`; optional seller URL fields map to `seller_url`
- Product data when present: `brand`, `model`, `image_url`, `price`, `currency`, `availability`
- Taxonomy/category when present: `category`, `category_bucket`, `google_taxonomy_path`, `vertical`, `engine`
- Metadata-only optional context: `locale` and `market` are preserved under `metadata["locale_market"]`

No field is fabricated; missing values remain `None`.

## Gate-aligned enrichment behavior

Enrichment fields are added to candidate metadata and remain honest:

- `seller_reliability_status` comes only from explicit trusted input mapping by seller name.
- If no trusted mapping is provided, seller reliability remains `unknown` and receives `seller_reliability_unknown`.
- `shipping_info_available` is `True` only when explicitly provided as true; unknown stays `None`.
- `return_policy_available` is `True` only when explicitly provided as true; unknown stays `None`.
- `short_description` and `specifications` are mapped only when present in row payload.
- Taxonomy linkage is marked present only if category/taxonomy fields exist in the row.

## Required fields for public/index eligibility

Public/index eligibility still depends on existing Stage 33/37 gates and remains unchanged. For retail flows, a candidate typically still needs:

- non-empty title,
- valid outbound URL,
- seller identity,
- required image (for retail),
- taxonomy linkage (`category_bucket` or `google_taxonomy_path`),
- valid non-fake/non-placeholder content.

Adapter output can still be `review_required` or fail eligibility if feed rows are sparse or missing required gate fields.

## Why raw feeds can fail gates before enrichment

Raw affiliate/merchant feeds often omit seller trust, shipping, return policy, or full taxonomy linkage. Stage 38 intentionally does not fabricate these fields. Missing coverage therefore correctly produces `review_required` or gate `needs_data` outcomes until enrichment is provided from trusted upstream data.

## Why this stage does not create 3,000 pages yet

Stage 38 is a source normalization and enrichment-readiness step only. It ensures feed rows can be transformed safely into `OfferCandidate` while preserving all existing publication/index controls. Page scale-up remains blocked until upstream feed completeness, trust mapping, quality gates, and controlled publication strategy are validated.

## Recommended next stage

Stage 39 should introduce a controlled enrichment pipeline for trusted seller reliability and structured shipping/returns/taxonomy completeness checks, then run staged candidate-to-page dry runs under existing publish/index/google/sitemap gates before any controlled scale increase.
