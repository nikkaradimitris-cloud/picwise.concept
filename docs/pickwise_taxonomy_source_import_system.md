# PickWise Taxonomy Source Import System

## Purpose

This importer layer ingests category/path source data and converts it into Workbench `source_item` records.
It is intentionally foundation-only and does **not** map source records into final PickWise taxonomy yet.

## Safety Boundary: No Product Inventory

The source import system rejects or flags inventory/commercial-like fields, including:

- `product`, `products`
- `offer`, `offers`
- `price`, `prices`
- `affiliate`, `affiliate_url`, `commission`
- `seller`, `store`, `store_offer`
- `sku`, `stock`, `inventory`, `checkout`

Allowed taxonomy-classification keys such as `product_family` and `product_families` remain valid when used for classification metadata only.

## Supported Source Formats

- Manual structured source lists
- Google Product Taxonomy TXT content provided locally
- CSV category exports
- JSON category exports

## Google Taxonomy Import Rule

Google taxonomy parsing is local-input only:

- local file text via explicit file path
- direct text content passed into parser functions

No download, scraping, network request, or external API call is used.

## Current Flow (This Stage)

1. source import  
2. parsed path normalization  
3. Workbench `source_item` record creation  
4. importer validation checks

## Future Flow (Later Stages)

1. source import  
2. `source_item` records  
3. mapping layer  
4. gap registry  
5. canonical taxonomy  
6. NLU export  
7. external offer search (later stage only)
