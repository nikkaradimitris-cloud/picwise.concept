# Brains Specification

## Objective

Picwise must route each purchase-intent query to one of 5 product brains.  
All brains must output the same contract shape: 4 choices + 1 recommended.

## Brain Catalog

1. Tech / Specs / Electronics
   - Examples: phones, laptops, chargers, power banks, monitors
   - Key criteria: compatibility, core specs, practical performance, value-to-spec ratio

2. Software / Programs / SaaS
   - Examples: invoicing, CRM, AI tools, subscriptions, booking systems
   - Key criteria: feature fit, pricing tiers, ease-of-use, limits, lock-in risk, support

3. Physical Products / Home / Machines
   - Examples: appliances, tools, air fryers, home devices
   - Key criteria: capacity, consumption, durability, maintenance, warranty, household fit

4. Financial / Utility / Contract Products
   - Examples: insurance, energy plans, banking products, telecom plans, contracts
   - Key criteria: total cost, terms, hidden fees, cancellation rules, provider reliability, user risk

5. High-Trust / Risk / Sensitive Decisions
   - Examples: child safety items, high-risk purchases, trust-heavy categories
   - Key criteria: safety, certifications, return policy, reliability, claim seriousness, error risk

## Brain Selection Rules

- Exactly one primary brain must be selected per query.
- Selection must be based on user intent and product type signals.
- If confidence is low, output must mark uncertainty explicitly and still remain contract-compliant.
- Selection must never use commission/referral payout as a signal.

## Output Rules Shared By All Brains

- produce exactly 4 primary choices
- produce exactly 1 recommended choice
- provide recommendation reason
- include decision labels, CTA, redirect, tracking payload
- include risk/limitation notes where relevant

## Brain-Level Safety Rules

- Financial/Utility brain must expose terms, risks, and unknowns.
- High-Trust brain must prioritize trust/safety over price-only outcomes.
- Any unknown critical field must be explicit (`not_connected`, `data_not_yet`, `not_applicable`, `unknown`).

## Undefined Details

- Brain selection confidence threshold: TODO
- Keyword/entity taxonomy for routing: TODO
- Multi-intent query arbitration logic: TODO
