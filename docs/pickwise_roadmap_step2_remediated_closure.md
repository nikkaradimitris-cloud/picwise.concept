# PickWise Roadmap Step 2 Remediated Closure

This document records a **Roadmap Step 2** remediation pass for real product/affiliate source readiness.  
It does not move work to Step 3 yet by itself, and it does not publish any new public pages.

## Step 2 context

Step 2 remains focused on proving source/contract readiness for a selected provider batch:

- Local fixture-based proof only.
- No live provider API calls.
- No scraping.
- No credentials.
- No public `/best` route wiring.
- No sitemap expansion.

## Why the previous closure batch failed

The prior selected provider batch included rows that violated Step 2 closure gates:

- Missing one or more required fields among the 1-9 closure set.
- At least one rejected row.
- At least one locale/market/currency mismatch.
- Provider readiness therefore remained `step2_not_ready` with `can_move_to_step3: false`.

## What was corrected in the local provider batch

A corrected fixture was added at:

- `tests/fixtures/roadmap_step2_selected_provider_batch_corrected.json`

Each selected row in that fixture now includes all required Step 2 fields together:

1. `title`
2. `image_url`
3. `price` (+ consistent `currency`)
4. `description`
5. `specifications`
6. `availability`
7. `merchant`/seller
8. `affiliate_url`
9. category/taxonomy data (`category`, `category_bucket`, `google_taxonomy_path`)

Additional constraints in the corrected fixture:

- Only usable selected rows.
- No rejected rows.
- No invalid URLs.
- No missing required fields from the 1-9 set.
- Locale/market/currency aligned (`en-IE`, `IE`, `EUR`).

## Evidence that Step 2 can close (for corrected local batch)

The remediated closure test suite validates:

- corrected fixture loads;
- strict 1-9 field coverage is `1.0` across selected usable rows;
- rejected count is `0`;
- review-required rate is `0` (below threshold);
- locale/currency mismatch count is `0`;
- provider readiness evaluator returns `step2_ready`;
- closure proof returns `step2_closed`;
- `can_move_to_step3` is `true`;
- no fabricated enrichment is applied;
- no routes/sitemap/naming changes are introduced;
- no gate relaxations are introduced;
- no scraping/live API/credentials are introduced.

## What still must happen with a real external provider

This closure proof remains a local deterministic contract validation.  
A real external provider integration still needs:

- actual provider onboarding,
- verified production feed delivery and stability,
- operational monitoring and failure handling,
- staged rollout controls.

Those external integration steps are separate from this local Step 2 closure proof.

## Why this does not publish/index pages or create candidate pages

This remediation validates data contract readiness only. It does not:

- publish pages,
- index new public URLs,
- create candidate page batches for release,
- wire any data into public buying routes.

## What Step 3 should handle next

Once Step 2 closure is accepted, Step 3 should handle controlled progression activities such as:

- downstream candidate-page dry-run planning under existing gates,
- rollout sequencing and quality guardrails,
- preserving unchanged naming/routes/sitemap policy until explicitly approved.
