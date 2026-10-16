# Picwise Mission

## Mission Lock

> Changed on 2026-10-16 by the owner's decision, "price first" (`docs/picwise_price_first_plan_2026-10-15.md`). It
> replaces "a decision engine, not a search engine" and the limited "more".

Picwise finds the product the buyer asked for, shows only what is in stock, cheapest
first, and makes one honest pick.

For every purchase-intent query, Picwise must:
- show only the kind of product asked for
- never show a product the shop's feed says is out of stock (the feed's word is
  trusted; no shop page is checked)
- return 4 choices first: exactly 1 Recommended (the middle product of the result in
  price order, or the nearest one to it that has an EAN/GTIN; a dearest product
  costing at least twice the next one does not count towards the middle) and the 3
  cheapest
- show how many there are ("4 of 45")
- offer "More": the next 4 cheapest, as often as the buyer asks
- explain the recommendation briefly and clearly
- include a clear CTA per choice
- track decision and click events
- redirect directly to the merchant/provider

This covers products from shops: PicWise rests on volume, it is a shopping search. For
services (insurance, banking, energy, software) there is no Recommended in this phase,
unless a mechanism is found that can decide what is the better deal (owner,
2026-10-16).

## Product Promise

Enter confused. Leave decided.

Picwise reduces search-to-decision time by showing only what was asked for and only
what is in stock, cheapest first, with one honest pick on top and as many more as the
buyer wants.

## Non-Negotiable Identity

Picwise must not become:
- an e-shop
- a marketplace
- an affiliate blog
- a list padded with accessories, out-of-stock products or products the buyer did not
  ask for

## Trust and Neutrality Commitments

- No fake products, reviews, ratings, conversions, revenue, savings, urgency, or confidence signals.
- No commission-first ranking or recommendation. Commission never decides the order
  or the Recommended.
- The order is the price, after the kind asked for and availability. The Recommended
  is the middle product in price order. No ratings are used.

## First Phase Boundary

Current phase is documentation/spec/contracts foundation.

No frontend implementation.
No backend implementation.
No product datasets.
No fake business metrics.

## Source of Truth Order

1. `PROJECT_RULES.md` (first operating rulebook)
2. `concept.picwise.txt` (product concept source of truth)
3. `docs/` contracts/specs (implementation contracts)

If conflicts appear between these layers, stop implementation and raise the conflict.
