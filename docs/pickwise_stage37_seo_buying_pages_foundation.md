# PickWise Stage 37 - SEO Buying Pages Foundation

## Scope

Stage 37 adds a strict SEO buying-page foundation on top of the existing Stage 32-36 MVP flow:

- Input pipeline: search decision -> offer intake -> eligibility gate -> recommendation set.
- Output contract: `SEOBuyingPage` with explicit index/noindex states.
- Safety-first publication: no sitemap entry unless quality is passed and indexable.

This stage is additive and does not replace `/search`, `/results`, `/private-beta-readiness`, existing `/best/{slug}` runtime behavior, or previous stage contracts.

## Core Contract

The Stage 37 contract lives in `src/picwise_buying_pages/seo_contracts.py` and requires:

- `page_id`, `slug`, `canonical_path`, `main_keyword`, `query_aliases`.
- intent and market attributes: `detected_intent`, `vertical`, optional retail/contract/taxonomy refs.
- recommendation state: `recommendation_set`, `wise_recommended_product`, product counts.
- publication controls: `page_quality_status`, `index_status`, `noindex_reason`, `sitemap_eligible`.
- timestamps and metadata.

Allowed status enums:

- `page_quality_status`: `quality_passed`, `needs_data`, `not_ready`, `manual_review`, `blocked`, `not_applicable`
- `index_status`: `indexable`, `noindex`, `blocked`, `manual_review`

## Quality Gate

The Stage 37 quality gate (`seo_quality_gate.py`) blocks indexability when any required signal fails:

- invalid keyword or ambiguous intent,
- unsupported/regulated vertical for auto-indexing,
- source not connected,
- recommendation set not ready,
- fewer than 4 valid eligible products,
- fake/placeholder/thin commercial data,
- invalid or duplicate slug/canonical path.

If any check fails, page state is downgraded to `noindex`, `manual_review`, or `blocked` with an explicit `noindex_reason`, and sitemap eligibility is disabled.

## Slug and Canonical Rules

`seo_slug_builder.py` builds deterministic slug/canonical values:

- lower-case URL-safe output,
- unsafe characters removed,
- duplicate separators collapsed,
- empty/too-short/reserved slugs blocked,
- canonical path always under `/best/...`.

## Builder and Surface

`seo_page_builder.py` builds `SEOBuyingPage` from Stage 32-36 outputs and fails safely:

- source not connected -> `needs_data` + `noindex`,
- insufficient eligible products -> `needs_data` + `noindex`,
- finance/regulated contract -> `manual_review`,
- invalid slug/canonical -> `blocked`.

`src/picwise_surface/buying_page_seo_surface.py` renders honest SEO surface metadata:

- canonical and robots meta reflect Stage 37 decision,
- product cards only from valid recommendation slots,
- safe noindex notice when page is not ready for indexing.

## Sitemap Control

`seo_sitemap_control.py` includes only Stage 37 pages that are:

- `index_status = indexable`,
- `page_quality_status = quality_passed`,
- `sitemap_eligible = true`,
- canonical under `/best/...`,
- at least 4 valid products.

It also blocks bulk inclusion through `MAX_STAGE37_SITEMAP_ENTRIES` to prevent mass generation.
