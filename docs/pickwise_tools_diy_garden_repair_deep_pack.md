# PickWise Stage 23B Deep Taxonomy Expansion Pack 1

This document defines the Stage 23B deep taxonomy expansion pack for the Tools / DIY / Garden / Repair universe.

## Scope

- Pack type: deep taxonomy expansion pack 1
- Engine covered: `tools_diy_garden_repair_engine`
- Mega-categories covered:
  - `power_tools_workshop`
  - `hand_tools_consumables_measuring`
  - `garden_outdoor_repair_building`

## Purpose

This pack is a search taxonomy graph expansion, not product inventory data.

It seeds deep intent and specification structure so each mega-category can scale into a large vertical search universe.

It does **not** include:

- product inventory records
- offers
- prices
- affiliate links
- seller or commission logic

## Current Stage Position

Current flow target:

1. taxonomy pack
2. Local NLU aliases/specs/intents
3. training packs
4. search integration

Current limitation:

- this Stage 23B pack does not change live Local NLU runtime behavior yet
- this Stage 23B pack does not modify app/router/Decision Machine integration

## Data Characteristics

The pack is deterministic and JSON serializable, with each mega-category seeded using:

- departments and subcategories
- product family seeds
- specification fields
- buying priorities
- Greek terms, Greeklish terms, and typo terms
- intent patterns
- ambiguity rules and safety notes

Validation enforces required fields and rejects forbidden key families:

- `product`
- `products`
- `offer`
- `offers`
- `price`
- `affiliate`
- `commission`
- `seller`
- `store_offer`
