# Stage 28F - Finance / Insurance Taxonomy Contract

Official stage title: **Stage 28F — Finance / Insurance Taxonomy Contract**

## Scope

This stage defines a taxonomy and safety contract for the vertical:

- `finance_insurance_business_finance`

This vertical is explicitly separate from:

- `retail_physical_products`
- `software_saas_erp`

This stage is contract-only and references Stage 28D market scope:

- `Stage 28D — PickWise Market Scope Expansion`

## Contract Coverage

Stage 28F defines required category buckets for:

1. Banking / Accounts / Cards
2. Loans / Mortgages / Leasing
3. Insurance / Protection
4. Payments / POS / Merchant Services
5. Investing / Trading Platforms
6. Business Finance / Accounting Finance Tools
7. Tax / Legal / Compliance Finance Support
8. Financial Education / Comparison / Advisory-safe Content

Each bucket includes:

- display name and description
- example product/service families
- relevant user/business profiles
- intent examples
- finance field definitions
- contract-level ranking dimensions
- safety requirements
- source status
- readiness status

## Source and Backbone Boundaries

Stage 28F does not use Google Product Taxonomy as a finance backbone.

Stage 28F declares planned future source families (no live import in this stage):

- regulated provider category lists
- bank/card/loan/insurance category references
- public comparison category structures
- manual structured source lists

## Safety and Non-Goals

Safety statuses include:

- `comparison_allowed`
- `review_required`
- `regulated_advice_blocked`
- `quote_application_blocked`
- `eligibility_decision_blocked`

This stage does not implement:

- ranking/scoring logic
- regulated financial advice
- quote/application/approval/eligibility decision flows
- app/router/search runtime changes
- Local NLU runtime changes
- live scraping or external API calls
- checkout/cart/payment/billing logic
- owned provider marketplace inventory
- Stage 29A massive query generator
