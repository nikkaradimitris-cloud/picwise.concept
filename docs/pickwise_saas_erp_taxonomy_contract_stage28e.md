# Stage 28E — SaaS / ERP Taxonomy Contract

## Scope

Stage 28E defines a taxonomy contract for `software_saas_erp` as a dedicated PickWise vertical.
This stage is contract-only and references Stage 28D market scope boundaries.

## Vertical Separation

- Vertical ID: `software_saas_erp`
- Separate from: `retail_physical_products`
- Must not be forced into: `tech_electronics_office`
- Google Product Taxonomy is not the SaaS/ERP backbone

## Contract Buckets

- `erp_business_management`
- `crm_sales_marketing`
- `accounting_invoicing_payroll`
- `hr_workforce_scheduling`
- `project_management_collaboration`
- `ecommerce_booking_pos_software`
- `cybersecurity_cloud_hosting`
- `industry_specific_software`

Industry-specific software includes taxi dispatch, fleet management, restaurant systems,
hotel/property management, field service, warehouse/WMS, retail POS, service booking systems,
and AI/automation tools.

## Software-specific Fields

- `pricing_model`
- `monthly_cost_range`
- `users_or_seats`
- `deployment_type`
- `integrations`
- `support_level`
- `api_availability`
- `security_compliance`
- `trial_demo_availability`
- `business_size_fit`
- `industry_fit`

## Intent Patterns

- compare software
- find alternative
- best for small business
- best for industry workflows (taxi/fleet/restaurant/etc.)
- cheap/free/trial
- cloud vs on-premise
- integration needed
- GDPR/security/compliance need

## Future Sources (Planned, Not Implemented)

- SaaS category lists
- software directories
- ERP/CRM/POS category references
- manual structured source lists

## Non-goals in Stage 28E

- No app/router/search runtime behavior changes
- No Local NLU runtime changes
- No ranking/scoring implementation
- No external offers, affiliate, or marketplace implementation
- No scraping or live API ingestion
- No checkout/cart/payment/subscription billing logic
- No owned marketplace inventory
- No Stage 28F implementation
- No Stage 29 implementation

