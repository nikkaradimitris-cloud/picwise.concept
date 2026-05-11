# PickWise Stage 23C Deep Taxonomy Expansion Pack 2

This document defines the Stage 23C deep taxonomy expansion pack for the Fashion / Footwear / Jewelry / Accessories universe.

## Scope

- Pack type: deep taxonomy expansion pack 2
- Engine covered: `fashion_footwear_jewelry_accessories_engine`
- Mega-categories covered:
  - `clothing_apparel_workwear`
  - `footwear_shoes_sneakers_boots`
  - `jewelry_watches_bags_fashion_accessories`

## Purpose

This pack is a search taxonomy graph expansion, not product inventory data.

Fashion is represented as a dedicated engine with deep category coverage, fit/size ambiguity handling, Greek and Greeklish query support, typo patterns, and intent templates.

It does **not** include:

- product inventory records
- offers
- prices
- affiliate links
- seller, commission, or sku logic

## Current Stage Position

Current path:

1. taxonomy pack
2. Local NLU aliases/specs/intents
3. training packs
4. search integration

Current limitation:

- this Stage 23C pack does not change live Local NLU runtime behavior yet
- this Stage 23C pack does not modify app/router/Decision Machine integration

## Data Characteristics

The pack is deterministic and JSON serializable, and each mega-category is seeded with:

- departments and subcategories
- product family seeds
- specification fields
- buying priorities
- Greek terms, Greeklish terms, and typo terms
- intent patterns
- ambiguity rules and safety notes

Validation enforces required fields, minimum depth thresholds, broad expansion markers, and forbidden key protection for:

- `product`
- `products`
- `offer`
- `offers`
- `price`
- `affiliate`
- `commission`
- `seller`
- `store_offer`
- `sku`
