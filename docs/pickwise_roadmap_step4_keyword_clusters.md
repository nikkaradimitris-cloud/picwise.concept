# PickWise Roadmap Step 4 - Keyword Cluster Contract Closure

## Step 4 purpose

Roadmap Step 4 defines deterministic keyword cluster contracts for future buying pages before any large candidate-page generation. The scope is contract + validation only, so keyword evidence can be normalized and quality-checked consistently.

This stage does not generate 3,000 pages, does not publish pages, and does not wire new routes into `/best`.

## Where keyword data may come from later

The Step 4 contract supports explicit source provenance so later stages can consume trusted data from:

- local fixtures
- provider feed exports
- Google Keyword Planner exports
- Search Console exports
- taxonomy-generated suggestions
- NLU-generated suggestions
- manual review inputs

Only explicit local input is accepted in this closure package.

## Why no live Google APIs are called in Step 4

Step 4 is an offline deterministic contract stage. It does not call Google live services, does not scrape autocomplete, and does not use credentials. This keeps validation reproducible and prevents fabricated evidence from entering buyer-page workflows.

## Keyword cluster structure

Each cluster includes:

- cluster identity: `cluster_id`, `locale`, `market`, `target_category`
- buying intent evidence: `buyer_intent`, `intent_type`
- keyword groups:
  - exactly one `main_keyword`
  - `support_keywords` (preferred 3-5)
  - `long_tail_keywords` (preferred 10-30 for page-ready)
- variants: language/Greek/Greeklish/German, typos, specs, brand-model variations
- product/category linkage signals: `product_spec_signals`, `brand_model_signals`
- source provenance: `source_type`
- explicit per-keyword volume buckets when provided: `low`, `medium`, `high`, `unknown`
- governance fields: `confidence_score`, `review_required`, `rejection_reasons`, `blocker_reasons`

## Main/support/long-tail/variant rules

Validation enforces:

- one-and-only-one main keyword
- support range preference (3-5)
- long-tail sufficiency requirement for page-ready status (10-30 window)
- deterministic duplicate detection and de-duplication logic
- keyword stuffing protection
- preservation of language, typo, spec, and brand-model variants

## Buyer-intent requirement

Clusters must clearly map to buying intent and product/category relevance. Informational-only clusters are blocked for buying-page readiness, and ambiguous clusters are review-required.

## Volume-bucket honesty

Volume buckets are accepted only when explicitly supplied in local input. Missing data is represented as `unknown`; the contract never fabricates search volume values.

## Evidence that closes Step 4

Step 4 is closed when tests demonstrate:

- deterministic contract normalization + validation
- valid US/UK/DE/GR buyer-intent clusters pass
- invalid clusters are blocked/reviewed for clear reasons
- batch counts remain deterministic
- `can_move_to_step5` is true only with zero blockers and acceptable review rate
- no public route/sitemap/naming changes
- no gate relaxations
- no scraping/live Google API/credentials additions

## Why this does not create 3,000 pages

This closure package only defines and validates keyword clusters. Candidate-page generation, publication, sitemap expansion, and index decisions remain in later roadmap steps with separate gates.
