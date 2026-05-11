# Stage 28D - PickWise Market Scope Expansion

## Intent

Stage 28D defines a strict market-scope manifest and contract boundaries for PickWise.
It does not modify runtime routing, search execution, Local NLU runtime behavior, or any
offer-serving integration logic.

## Required Market Verticals

1. `retail_physical_products`
2. `software_saas_erp`
3. `finance_insurance_business_finance`

## Clarifications Captured in Contract

- The existing six PickWise engines are retail hypermarket domains only.
- The existing 18 buckets are category/subcategory structures under those six retail
  domains, and are not 18 independent market verticals.
- Google Product Taxonomy remains the deep backbone for physical retail products.
- SaaS/ERP is a separate market vertical and is not forced into
  Tech/Electronics/Office retail taxonomy logic.
- Finance/Insurance/Business Finance is a separate market vertical and is not forced
  into retail taxonomy logic.
- Each vertical requires its own taxonomy contract and ranking dimensions.

## Stage Boundaries (Non-Goals)

- No app router runtime changes.
- No search runtime changes.
- No Local NLU runtime changes.
- No Stage 28E, Stage 28F, or Stage 29A work.
- No scraping, external API live calls, or network extraction tasks.
- No owned inventory, checkout, cart, warehouse, or seller marketplace behavior.
