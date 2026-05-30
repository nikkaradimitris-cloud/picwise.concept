# PicWise Common Provider Field Priority

This patch improves generic provider/feed selection by prioritizing official feed fields across all Awin-style feeds. It is not merchant-specific logic.

## Brand

- Official `brand_name` maps to `ProviderProduct.brand` when populated.
- Existing `brand`, `manufacturer`, and `merchant_brand` fields remain first in priority.
- Missing brand stays unknown. Brand is never inferred from title.

## Category and product type

Search and category alignment use signals in this order:

1. `product_type` (highest weight when populated)
2. `merchant_product_category_path` and secondary/tertiary merchant categories
3. `merchant_category` and `category_name` only when not generic flat values such as `Computers`

Flat generic category values receive reduced weight so they do not dominate feeds where every row shares the same category.

When a query maps to a known main-product intent and `product_type` is populated:

- matching official product types receive a deterministic alignment bonus
- conflicting accessory product types are excluded from selection

Feeds without `product_type` continue to use title, brand, keywords, and non-generic category fields.

## Product identity

Identity remains unchanged in this patch:

- GTIN/EAN/UPC/ISBN when present
- MPN when present
- merchant product id + merchant name
- aw_product_id
- product name is display/search text only

## Description and specs

- `description` is used only as unstructured search evidence with low weight.
- Structured `specifications` are not faked from description.

## Availability and reviews

- Availability continues to use official `stock_status` / `in_stock` / related fields during normalization.
- No review or rating scoring is added when official review fields are absent.

## Selection behavior

- Deterministic scoring is preserved.
- No commission-first ranking.
- No fake data rules remain enforced.
- Amazon manual affiliate path, UI, reference surface, and search artifacts are untouched.

## Test feed

Back to the Office is used only as a proof feed because it exposes broad-query accessory leakage when `product_type` is ignored. The logic itself is common infrastructure for all feeds.
