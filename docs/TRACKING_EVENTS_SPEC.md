# Tracking Events Specification

## Purpose

Track real user decisions and system behavior for optimization and auditing, without fake metrics.

## Event Principles

- Events must reflect real actions and real system states.
- No synthetic/fake revenue or conversion events.
- Missing values must be explicit.

## Required Event Set

- `page_impression`
- `query_served`
- `brain_selected`
- `depth_selected`
- `choices_shown`
- `recommended_shown`
- `cta_click`
- `recommended_click`
- `non_recommended_click`
- `more_click`
- `redirect_attempt`
- `redirect_success`
- `redirect_failure`
- `conversion` (only where truly available)
- `revenue` (only where truly available)
- `error`
- `speed_metric`

## Core Payload Fields

All events should include:
- `event_id`
- `event_name`
- `timestamp`
- `session_id`
- `query_id`
- `brain_id`
- `depth_id`
- `page_id`

Contextual fields where applicable:
- `choice_id`
- `is_recommended`
- `provider_id`
- `redirect_url`
- `latency_ms`
- `revenue_value`
- `conversion_value`

## Missing Data Representation

When unavailable, use:
- `not_connected`
- `data_not_yet`
- `not_applicable`
- `unknown`

## Data Integrity Constraints

- Commission fields must not be used for ranking/recommendation decisions.
- Event ingestion must preserve original values and missing-state markers.
- No "PASSED" claims for analytics quality without event output evidence or audit proof.

## Undefined Details

- Canonical schema versioning method: TODO
- PII handling and privacy constraints: TODO
- Retention windows by event type: TODO
