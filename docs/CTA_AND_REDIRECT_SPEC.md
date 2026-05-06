# CTA and Redirect Specification

## Purpose

CTA actions must move users directly to the merchant/provider with minimal friction and complete tracking coverage.

## CTA Rules

- Every choice card must have exactly one primary CTA.
- CTA text must match product type and intent clarity.
- CTA must represent a real next step (not vague exploration).

## CTA Text Guidelines

E-commerce examples:
- "View in Store"
- "Go to Store"
- "View Details and Buy"

Software/SaaS examples:
- "View Plan"
- "View Pricing"
- "View Details"

Financial/Utility/Contract examples:
- "View Offer"
- "Compare Terms"
- "Estimate Cost"
- "Continue to Provider"
- "Request Offer"

Exact localization/copy set: TODO

## Redirect Rules

- CTA click must trigger direct redirect to provider/merchant URL.
- No unnecessary intermediate pages.
- No redirect loops.
- Redirect should happen within performance target (`< 300ms` from click where technically feasible).

## Tracking Requirements

At minimum, system must track:
- `cta_click`
- `recommended_click` or `non_recommended_click`
- `redirect_attempt`
- `redirect_success` / `redirect_failure`

## Safety Rules

- Do not mask destination intent.
- Do not present fake pricing, fake urgency, or fake confidence near CTA.
- Recommended CTA styling must not imply guaranteed outcomes.

## Undefined Details

- Redirect fallback policy for provider downtime: TODO
- Retry behavior and timeout values: TODO
- URL signing/attribution parameter strategy: TODO
