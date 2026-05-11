# PickWise Taxonomy Architecture Reconciliation (Stage 24A.5)

## Purpose

This document reconciles the taxonomy architecture layers introduced so far and sets strict boundaries before the mapping and canonical registry stages begin.

PickWise taxonomy is a search-understanding and routing knowledge foundation. It is not a product catalog and it is not an e-shop inventory system.

## Core Principles

- PickWise is **not** an e-shop.
- PickWise does **not** keep owned product inventory.
- Taxonomy exists to structure search understanding and later external offer discovery/redirect flows.
- Real products, offers, prices, sellers, stores, and checkout belong to external offer sources later, not the taxonomy architecture.
- No scraping, no downloader pipelines, no external API dependency, and no live LLM calls are required for this reconciliation stage.

## Current Taxonomy Architecture

### `engine_registry` (implemented)

- Path: `src/picwise_taxonomy/engine_registry.py`
- Role: Top-level six PickWise search engines.
- Source of truth: **Yes**, for engine identifiers.
- Must not do:
  - Product/SKU/offer/price/seller/store/affiliate logic.
  - Runtime app/router integration.

### `mega_category_registry` (implemented)

- Path: `src/picwise_taxonomy/mega_category_registry.py`
- Role: Eighteen mega-categories (three per engine).
- Source of truth: **Yes**, for mega-category identifiers.
- Must not do:
  - Product inventory or commercial transaction responsibilities.
  - Runtime decision routing behavior.

### `coverage_plan` (implemented)

- Path: `src/picwise_taxonomy/coverage_plan.py`
- Role: Blueprint for future coverage depth across all 18 mega-categories.
- Source of truth: **No** (planning blueprint only).
- Must not do:
  - Pretend deep taxonomy is complete.
  - Store product inventory or offer-level commerce data.

### `deep_packs` (implemented)

- Path: `src/picwise_taxonomy/deep_packs/`
- Current curated packs:
  - Tools / DIY / Garden / Repair
  - Fashion / Footwear / Jewelry / Accessories
- Role: Curated seed taxonomy packs for selected domains.
- Source of truth: **No** (seed data, not final authority).
- Must not do:
  - Become final product inventory.
  - Introduce SKU/price/seller/affiliate semantics.

### `workbench` (implemented)

- Path: `src/picwise_taxonomy/workbench/`
- Role: Foundation layer for:
  - Canonical schema
  - `source_item` records
  - Gap registry
  - Coverage matrix
  - Validation utilities
- Must not do:
  - Runtime mapping and app/router coupling.
  - Commercial inventory logic.

### `importers` (implemented)

- Path: `src/picwise_taxonomy/importers/`
- Role: Convert external/local structured taxonomy source paths into Workbench `source_item` records.
- Output scope: **source_item producer only**.
- Must not do:
  - Direct runtime mapping/integration.
  - Create products, SKUs, offers, prices, sellers, stores, stock, checkout, or affiliate links.

## Future Layers (Planned, Not Implemented)

### `future_mapping_layer` (planned)

- Planned path: `src/picwise_taxonomy/mapping/`
- Role: Map imported `source_item` records into PickWise engines, mega-categories, departments, subcategories, and product families.
- Not implemented in this stage.

### `future_canonical_registry` (planned)

- Planned path: `src/picwise_taxonomy/canonical/`
- Role: Future normalized PickWise taxonomy records built from approved source items, mappings, gap registry, and curated deep-pack seeds.
- Not implemented in this stage.

### `future_nlu_export` (planned)

- Planned path: `src/picwise_taxonomy/exports/`
- Role: Export aliases, greeklish variants, typo terms, spec fields, priority terms, and intent patterns toward Local NLU.
- Not implemented in this stage.
- Must not change Local NLU runtime directly in this stage.

## How Deep Packs Are Used Going Forward

- Deep packs remain curated taxonomy seeds.
- They enrich taxonomy language and structure where depth is needed.
- They are consumed as curated inputs to future mapping/canonical consolidation.
- They are never treated as owned product inventory.

## How Importers Feed the Workbench

Importers normalize source taxonomy paths/records and emit Workbench `source_item` records only. Those records are then evaluated by Workbench validation and gap analysis before any future mapping/canonical decisions.

## Clean Future Flow

`source taxonomy files`
-> `importers`
-> `workbench source_items`
-> `mapping layer`
-> `gap registry`
-> `canonical taxonomy registry`
-> `coverage matrix`
-> `NLU exports`
-> `search/runtime integration later`

## Boundary Summary

This reconciliation layer exists so future taxonomy growth remains clean:

- IDs stay anchored in `engine_registry` and `mega_category_registry`.
- Coverage remains explicit blueprint logic in `coverage_plan`.
- Deep packs stay curated taxonomy seeds.
- Importers stay source-item-only producers.
- Future mapping/canonical/export layers remain planned and bounded.
- Taxonomy never mutates into product inventory or commerce logic.
