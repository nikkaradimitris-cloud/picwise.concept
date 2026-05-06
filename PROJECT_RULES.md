# PROJECT_RULES.md

Mandatory operating rulebook for Picwise Production.

## 1) Source Of Truth Order

1. `PROJECT_RULES.md` is the first operating rulebook.
2. `concept.picwise.txt` (or the existing concept file in this repository) is the product concept source of truth.
3. `docs/` specs/contracts become implementation contracts once created.
4. If any conflict exists between these sources, do not guess, do not improvise, and do not continue implementation. Stop and report the conflict clearly.

## 2) Core Identity

- Picwise is a decision engine, not a search engine.
- Picwise must reduce search-to-decision time.
- Every purchase-intent query must lead to exactly 4 curated buying decisions and 1 honest recommended choice.

## 3) Required Output Contract (Always)

Every purchase-intent result must include all of the following:

- 4 choices
- 1 recommended
- decision labels
- clear CTA
- direct redirect
- tracking event
- no fake data
- no commission-first ranking

If any item is missing, the output is non-compliant.

## 4) Forbidden Behavior

The project must never:

- Turn Picwise into a search engine.
- Turn Picwise into an e-shop.
- Turn Picwise into a marketplace.
- Turn Picwise into an affiliate blog.
- Show infinite product lists.
- Add fake products, fake reviews, fake ratings, fake conversions, fake revenue, fake savings, fake urgency, or fake AI confidence.
- Use commission as a product ranking or recommendation criterion.
- Create frontend/backend implementation before required specs/contracts exist, unless explicitly instructed.
- Invent business logic when concept/spec is missing. Add a `TODO` and flag the gap.

## 5) Revenue Neutrality

- Picwise may earn through affiliate/referral/lead/conversion models.
- Commission is never part of recommendation logic.
- Recommendations must be based on user fit, reliability, cost, terms, risk, availability, and decision quality.

## 6) Brain Model

All implementation must respect these 5 product brains:

1. Tech / Specs / Electronics
2. Software / Programs / SaaS
3. Physical Products / Home / Machines
4. Financial / Utility / Contract Products
5. High-Trust / Risk / Sensitive Decisions

## 7) Decision Depth Model

All implementation must respect these 3 decision depths:

1. Fast Decision
2. Considered Purchase
3. High-Stakes / High-Trust

## 8) Domain Rule

- Primary launch domain: `picwise.subby.cloud`
- Do not use `picwise.cloud` as primary domain.
- `picwise.cloud` is optional future standalone brand domain only.

## 9) Performance Targets

Mandatory targets:

- First render < 1.5 sec
- Full interactive < 2 sec
- Click to redirect < 300 ms

Do not ship changes that knowingly violate these targets without explicit approval.

## 10) Dashboard / Subby Compatibility

- Picwise must be designed to send operational/business events to Subby dashboard later.
- Missing data must be represented as `not_connected`, `data_not_yet`, `not_applicable`, or `unknown`.
- Never fake dashboard metrics.

## 11) Workflow Rule

Before and during every change:

- Inspect current files before modifying them.
- Do not overwrite existing files blindly.
- Make small, closed, testable steps.
- Every implementation step must include relevant tests.
- Do not claim completion without proof (tests, checks, or concrete evidence).

## 12) First Project Phase Rule

- First phase is docs/spec/contracts foundation.
- Do not build live product UI until mission docs and contracts are created and reviewed.

## Enforcement

These rules are mandatory for all Codex-assisted changes in this project, including code, docs, architecture, tests, UI, backend, routing, product, tracking, SEO, dashboard, and deployment work.
