# PickWise Roadmap Step 8 - Measurement / Controlled MVP Observation

## Purpose

Roadmap Step 8 adds deterministic local observation contracts for controlled Live MVP records approved in Step 7.  
This step measures observation readiness and promotion readiness signals without publishing pages or changing public routing.

Step 8 is additive and non-breaking:

- no mass publish behavior
- no live sitemap expansion
- no `/best` route replacement
- no live analytics provider integration
- no credentials or live API wiring

## What Step 8 measures

Step 8 records local/operator observation events for controlled MVP records:

- preview render events
- outbound click contract events
- preview and outbound error trends
- manual review openings
- blocker detections
- per-page observation health status
- promotion readiness to move from controlled MVP observation toward later limited exposure

## What Step 8 does not measure yet

Step 8 does not claim or infer real production traffic outcomes:

- no real impressions aggregation
- no real user clickstream analytics
- no conversion attribution
- no revenue reporting
- no external search volume pulls

These remain outside Step 8 to preserve deterministic local validation and avoid fabricated performance claims.

## Why no fabricated revenue/conversion/traffic claims

Step 8 is a contract validation stage, not a growth-reporting stage.  
Fabricating traffic, conversions, or revenue would invalidate readiness signals and undermine safe release gates.

Event validation rejects fabricated metrics keys such as revenue/conversion/impressions/search volume in observation payloads.

## Event contract

`MVPObservationEventType`:

- `preview_rendered`
- `outbound_click`
- `preview_error`
- `outbound_error`
- `manual_review_opened`
- `blocker_detected`

`MVPObservationEvent` requires deterministic fields:

- `event_id`
- `candidate_page_id`
- `slug`
- `event_type`
- `timestamp`
- `source`
- `test_mode` (explicit boolean)
- `operator_generated` (explicit boolean)
- `locale`
- `market`
- `product_id` (required for `outbound_click`)
- `outbound_url` (required for `outbound_click`)
- `metadata`
- `rejected_reason` (set on deterministic rejection)

Validation rules:

- unknown event types are rejected
- missing `candidate_page_id` or `slug` is rejected
- non-explicit `test_mode` / `operator_generated` flags are rejected
- outbound click events without `product_id` and `outbound_url` are rejected
- fabricated revenue/conversion/traffic metric keys are rejected
- events do not publish pages, mutate sitemap, or alter routes

## Promotion readiness criteria

A page can become `promotion_ready` only when all conditions hold:

- Step 7 exposure status is `live_mvp_ready`
- preview evidence exists
- blocker events are absent
- outbound error trend is within policy threshold
- outbound click evidence exists, or minimum observation coverage is met by policy
- state remains controlled and reversible

Status outcomes:

- `observation_ready`
- `needs_more_data`
- `hold_manual_review`
- `blocked`

`promotion_ready` in Step 8 is only a contract outcome and never means public publishing.

## Promotion ready vs public publish

`promotion_ready` means a controlled MVP record has enough deterministic local evidence to proceed to the next controlled roadmap stage.  
It does not grant automatic `/best` route exposure and does not add sitemap entries.

Public publish decisions remain gated by later steps and explicit release controls.

## Evidence required to close Step 8

Step 8 closure evidence requires:

- deterministic event validation contracts
- deterministic batch summary counters and rejected reason counts
- page-level status and promotion readiness outputs
- selected clean batch where all selected Step 7 live-ready records are `promotion_ready`
- zero rejected/blocked/manual-review statuses in selected clean closure batch
- `can_move_to_step9 = true` for selected clean closure batch
- tests proving no route replacement, no sitemap expansion, no gate relaxation, no fabricated metrics

## What Step 9 should do next

Step 9 should consume Step 8 promotion-ready records and define tightly scoped limited exposure controls, including:

- explicit release cohort definition
- reversible rollout checkpoints
- stricter monitoring and rollback thresholds
- continued non-mass-publish safeguards

Step 9 should remain policy-driven and should not bypass existing index/publish/sitemap guardrails.
