# Dashboard Compatibility Specification

## Objective

Design data contracts so Picwise can send operational/business events into Subby dashboard workflows.

## Required Compatibility Fields

At minimum, dashboard-compatible pipelines must support:
- queries
- selected brain
- selected decision depth
- shown choices
- recommended choice
- CTA clicks
- more clicks
- redirect outcomes
- conversions (where available)
- revenue (where available)
- errors
- speed metrics
- provider/merchant health
- category/product performance

## Missing Data Contract

When unavailable, use only:
- `not_connected`
- `data_not_yet`
- `not_applicable`
- `unknown`

No fake business metrics are allowed.

## Schema Constraints

- Event payloads must be versioned.
- Required fields must be machine-validated before ingestion.
- Revenue and conversion fields must be source-attributable.

## Neutrality Constraint

Dashboard metrics may observe commission values, but commission must not influence recommendation ranking.

## Undefined Details

- Exact Subby schema mapping and transport protocol: TODO
- Retry/backfill policy for failed event delivery: TODO
- Data ownership boundaries across systems: TODO
