# 4. Contracts/schemas

## Scope Delivered

This stage adds enforceable Python contracts/schemas and validation rules for:

- canonical enums
- product choices
- decision outputs
- tracking events
- redirect events
- anti-fake and revenue-neutrality safeguards

Implementation location:

- `src/picwise_contracts/`
- `tests/test_contracts.py`

## Canonical Enums

Defined and validated:

- `MissingDataState`:
  - `not_connected`
  - `data_not_yet`
  - `not_applicable`
  - `unknown`
- `ProductBrain`:
  - `tech_specs_electronics`
  - `software_programs_saas`
  - `physical_products_home_machines`
  - `financial_utility_contract_products`
  - `high_trust_risk_sensitive_decisions`
- `DecisionDepth`:
  - `fast_decision`
  - `considered_purchase`
  - `high_stakes_high_trust`

## ProductChoiceRole Contract

Supported common roles:

- `budget`
- `value`
- `best_overall`
- `premium`

Controlled brain/category-specific roles are allowed from a fixed enum set (not free text).  
Current brain-specific examples include:

- software: `basic`, `best_for_small_business`
- financial/utility: `lowest_monthly_cost`, `stable_price`, `flexible_plan`
- high-trust: `safe_budget`, `best_safety`, `best_comfort`, `premium_isofix`

TODO:

- expand full role taxonomy per category once dedicated role specs are added.

## ProductChoice Schema Rules

Required fields:

- `product_id`
- `title`
- `merchant_or_provider`
- `price_or_cost_display`
- `role`
- `decision_label`
- `subtitle`
- `key_reasons`
- `risks_or_limitations`
- `cta_label`
- `redirect_target`
- `tracking_metadata`
- `is_recommended`

Enforced safeguards:

- no fake review/rating/revenue/savings/urgency/confidence markers
- no commission-ranking fields
- role must be from controlled enum taxonomy

## DecisionOutput Schema Rules

Required fields:

- `query`
- `selected_brain`
- `decision_depth`
- `page_title`
- `choices`
- `recommended_product_id`
- `missing_data_states`
- `tracking_context`
- `more_choices` (optional)

Enforced rules:

- exactly 4 primary choices
- exactly 1 recommended choice
- `recommended_product_id` must be one of primary 4
- no infinite list behavior (`more_choices` capped to 4)
- no fake-data markers
- no commission-ranking input
- financial/utility choices must include terms/risks/unknown handling in risk text

## TrackingEvent Schema Rules

Required event types:

- `page_impression`
- `query_served`
- `cards_shown`
- `recommended_shown`
- `cta_click`
- `recommended_click`
- `non_recommended_click`
- `more_click`
- `redirect_attempt`
- `redirect_success`
- `redirect_failure`

Required fields:

- `event_type`
- `event_id`
- `timestamp`
- `query`
- `selected_brain`
- `decision_depth`
- `session_id`
- `source`
- `metadata`
- `missing_data_states`

Conditionally required:

- `product_id` for click/redirect/recommended shown events
- `recommended` with strict true/false checks for recommended/non-recommended click flows

## RedirectEvent Schema Rules

Required fields:

- `event_id`
- `timestamp`
- `query`
- `product_id`
- `merchant_or_provider`
- `redirect_target`
- `recommended`
- `click_to_redirect_budget_ms`
- `tracking_metadata`

Enforced:

- click-to-redirect budget must be `< 300ms`
- strict anti-fake checks
- strict no commission-ranking input

## Validation Helpers

Helpers enforce:

- exactly 4 primary choices
- exactly 1 recommended choice
- recommended belongs to primary choices
- no fake-data fields/flags
- no commission-ranking fields
- financial/utility terms-risks-unknown handling
- CTA appropriateness by brain via canonical label maps (non-standard labels currently returned as warnings)

## Tests Added

`tests/test_contracts.py` covers:

- valid `DecisionOutput` passes
- 3 choices fails
- 5 choices fails
- 0 recommended fails
- 2 recommended fails
- recommended outside primary choices fails
- fake review/rating/revenue/savings/urgency/confidence markers fail
- commission ranking field fails
- missing-data enum canonical values pass and non-canonical fail
- `TrackingEvent` required fields pass/fail checks
- `RedirectEvent` required fields pass/fail checks
- financial/utility output without terms/risk/unknown handling fails
