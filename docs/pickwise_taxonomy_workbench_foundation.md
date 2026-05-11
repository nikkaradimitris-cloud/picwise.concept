# PickWise Taxonomy Workbench Foundation (Stage 24A)

## Why this exists

PickWise is scaling toward 6 search engines, 18 mega-categories, and eventually thousands of structured taxonomy nodes. Manual scattered lists are not stable enough for that scale. Stage 24A introduces a deterministic Taxonomy Workbench foundation so taxonomy growth becomes structured, auditable, and validation-first.

## Why scattered manual lists are not acceptable

- They are hard to normalize across engines and mega-categories.
- They are hard to validate for consistency, status, and coverage depth.
- They make gap tracking informal and easy to lose.
- They do not provide deterministic machine-readable outputs for future large imports.

## What the workbench supports

The Stage 24A foundation introduces:

- Canonical taxonomy record schema
- Source item schema for future structured imports
- Gap registry schema for missing-term workflows
- Coverage matrix helpers for deterministic summaries
- Validation helpers for JSON serialization and forbidden field protection

This structure is designed to support all 6 engines and all 18 mega-categories consistently.

## Foundation workflow

Future structured flow supported by this foundation:

source lists/imports  
-> source items  
-> canonical taxonomy records  
-> gap registry  
-> coverage matrix  
-> deep packs  
-> Local NLU exports  
-> search integration

## Current limitations (intentional)

- Stage 24A does **not** import full external taxonomy data.
- Stage 24A does **not** scrape websites.
- Stage 24A does **not** add live API or LLM dependencies.
- Stage 24A does **not** change Local NLU runtime behavior.
- Stage 24A does **not** create product inventory, offers, prices, affiliate data, seller/store data, or SKU logic.
- Stage 24A does **not** integrate with app/router/Decision Machine runtime paths.
