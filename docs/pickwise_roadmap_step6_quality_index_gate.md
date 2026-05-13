# PickWise Roadmap Step 6 - Quality and Index Gate

## Purpose
Step 6 adds deterministic quality and index eligibility decisioning for Step 5 candidate buying pages.  
This stage classifies candidate pages for next-step readiness without publishing anything live.

## Candidate vs Index Candidate vs Public Page
- **Candidate page**: planning artifact from Step 5; always non-public and non-indexed.
- **index_candidate**: quality/index eligible decision outcome for Step 7 preparation only.
- **Public/indexed page**: a separately approved and published page, outside Step 6 scope.

Step 6 only returns decisions. It does not expose pages in public routes, does not publish pages, and does not include candidates in live sitemaps.

## Why Step 6 Does Not Publish
Step 6 is a gate, not a publishing stage.  
Its job is deterministic verification of evidence and quality constraints:
- exact product composition
- recommendation integrity
- locale/provider readiness
- duplicate/canonical handling
- SEO quality guardrails

Publishing remains controlled by later stages and existing publish gates.

## Decision Statuses
`CandidateIndexDecisionStatus` values:
- `index_candidate`
- `noindex_candidate`
- `hold_manual_review`
- `rejected`
- `duplicate_canonical_required`

## Core Rules Enforced
- Candidate must remain non-public.
- Candidate must have 4 valid selected products.
- Recommended product must be within selected products.
- Page-ready keyword cluster evidence is required.
- Locale-ready and provider-ready product evidence are required.
- Fake or filler products are blocked.
- Duplicate slug is blocked for index candidate and handled as duplicate/canonical flow.
- Near-duplicate candidates require canonical decisioning.
- Monetized pages require complete affiliate link coverage.
- Title/meta intent evidence is required.
- Keyword stuffing is blocked.
- Unsupported locale/market/currency is blocked.
- Thin content indicators prevent index candidate status (policy-driven noindex/review/reject).
- Uncertain evidence is routed to manual review.

## Four Product Rule
Step 6 requires exactly four selected products for index eligibility evaluation.  
If fewer than four products are available, the candidate is blocked from `index_candidate` and classified by policy (default: `rejected`).

## Recommended Product Rule
`recommended_product_id` must be one of `selected_product_ids`.  
If recommendation evidence is missing or inconsistent, the page cannot be `index_candidate`.

## Duplicate and Canonical Handling
- Duplicate slug conflicts are not allowed as `index_candidate`.
- Near-duplicate candidates with high similarity are classified as `duplicate_canonical_required`.
- Canonical target is captured in decision output for later canonical planning.

## Noindex / Hold / Rejected
- **noindex_candidate**: deterministic quality blocker that is not a hard reject (for example thin content policy outcome).
- **hold_manual_review**: uncertain or incomplete evidence requiring human review.
- **rejected**: critical blocker (invalid core composition, unsupported locale/currency, fake/filler risk, recommendation inconsistency).

## `sitemap_allowed` Means Candidate-Level Only
`sitemap_allowed=true` in Step 6 indicates candidate-level eligibility only.  
It does **not** update live sitemap files, routes, or search exposure.

## Evidence That Closes Step 6
Step 6 can be considered closed when:
- Candidate index gate contracts exist and are deterministic.
- Required statuses and rule paths are covered by fixtures and tests.
- Clean selected batch produces only `index_candidate` decisions.
- `can_move_to_step7` is true for clean selected batch.
- No public route exposure, no live sitemap expansion, and no publishing side effects occur.

## Step 7 Next
Step 7 should consume Step 6 decision outputs and:
- apply canonical decisions for duplicate candidates
- manage editorial/manual review queues
- prepare controlled publish-ready packages using existing publish gates
- keep production route/sitemap changes behind explicit release controls
