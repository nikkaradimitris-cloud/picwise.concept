# Picwise Mission

## Mission Lock

> Changed on 2026-10-16 by the owner's decision, "price first" (`docs/picwise_price_first_plan_2026-10-15.md`). It
> replaces "a decision engine, not a search engine" and the limited "more".
>
> Changed on 2026-11-01 by the owner: products a current shop offer covers come first
> («Ένα προϊόν με προσφορά θα μπαίνει πρώτα από το φθηνότερο»; `PROJECT_RULES.md` §5).
>
> Changed on 2026-11-06 by the owner: in a complex search, the products whose own words
> show they fit the buyer's need come first, marked («...πρέπει να έχουν λεκτική αναφορά
> αλλά και οπτική σημείωση καθώς πρέπει να κατατάσσονται και πρώτα»; `PROJECT_RULES.md`
> §2 and §5).
>
> Changed on 2026-11-15 by the owner: no product on offer comes before a cheaper one; each
> stands at its price after its offer where that offer surely applies, and the Recommended
> is the middle price, on offer or not («Οι προσφορές δεν πρέπει να βγαίνουν πάνω από το
> φθηνότερο προϊόν»; said again on 2026-11-19: «Η προσφορές βγαίνουν πρώτα μόνο αν είναι
> φθηνότερες»; `PROJECT_RULES.md` §2 and §5).
>
> Changed on 2026-11-19 by the owner: PicWise works out no price; each product stands at
> the shop's own price, its sale price where the shop's feed gives one («Θα ήθελα να
> αποφύγουμε τους υπολογισμούς τιμής», then «Στην έκπτωση τραβά στην τιμή της έκπτωσης»;
> `PROJECT_RULES.md` §2 and §5).

Picwise finds the product the buyer asked for, shows only what is in stock, cheapest
first, each product at the shop's own price (its sale price where the shop gives one),
and makes one honest pick.

For every purchase-intent query, Picwise must:
- show only the kind of product asked for
- never show a product the shop's feed says is out of stock (the feed's word is
  trusted; no shop page is checked)
- return 4 choices first: exactly 1 Recommended (the middle product of the result in
  price order, each product at the shop's own price, on offer or not, or the
  nearest one to it that has an EAN/GTIN; a dearest product costing at least twice the
  next one does not count towards the middle; owner, 2026-11-15; from 2026-11-01 to
  2026-11-15 it was a product on offer whenever an offer covered one)
  and the 3 cheapest
- show how many there are ("4 of 45")
- after the Recommended, put every product cheapest first, each at the shop's own price,
  its sale price where the shop gives one: a product on offer comes first only when it is
  cheaper (owner, 2026-11-15 and 2026-11-19; from 2026-11-15 to 2026-11-19 each stood at
  its price after an offer that surely applied, and from 2026-11-01 to 2026-11-15 the
  products on offer came first; `docs/PICWISE_DECISION_CONTRACT.md`, "The shop's own
  price")
- in a complex search ("quiet washing machine"), put the products whose own words show
  they fit the need first, in that same order among them, the Recommended chosen among
  them, each marked with a ✓ and its own words (owner, 2026-11-06)
- offer "More": the next 4 in that order, as often as the buyer asks
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
- The order, after the kind asked for and availability: the Recommended, then every
  product cheapest first, each at the shop's own price, its sale price where the shop
  gives one, so a product on offer comes first only when it is cheaper (owner,
  2026-11-15 and 2026-11-19; PicWise works out no price, owner, 2026-11-19). The Recommended is the middle product in price order, on
  offer or not (owner, 2026-11-15). In a complex search, the products that fit
  the need come first in that order, and the Recommended is one of them (owner,
  2026-11-06). No ratings are used. No one pays for a place.

## First Phase Boundary

Closed on 2026-05-06, when the docs contract review passed (`PROGRESS.md`); the app has
been built since and is live (`README.md`). Kept below as the record of the first phase;
its "No fake business metrics" stays binding (`PROJECT_RULES.md` section 4).

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
