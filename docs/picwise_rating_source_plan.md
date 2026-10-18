# Where a real product rating can come from

Owner instruction, 2026-10-12: PicWise needs specific data to recommend and rank. If
the feed does not send it, find another network as well so the numbers can be
cross-checked from there, and in the end use scraping so real ratings can be taken
from the whole platform. **The comparison process always starts with the criterion of
the product's rating.** Always refer back to the mission and to the ranking specs.

This document records what was established before any of that is built, because two
of the three parts turn out to rest on assumptions the data does not support.

## The conflict this resolves, raised as PROJECT_RULES section 1.4 requires

- `docs/MISSION.md` (Mission Lock): "For every purchase-intent query, Picwise must
  return exactly 4 curated choices, **return exactly 1 recommended choice**".
- `docs/BRAINS_SPEC.md`: "produce exactly 4 primary choices, **produce exactly 1
  recommended choice**, provide recommendation reason".
- `docs/ANTI_FAKE_TRUST_RULES.md` forbids "recommendation without real reason", and
  requires that an incomplete comparison be marked rather than hidden.
- Owner, earlier the same day: where the feed gives neither a rating nor a
  specification, show the four with **no** recommended choice and say the category
  does not support comparison.

The last of these cannot hold with the first two: there is no state in the mission
where a purchase-intent query returns four choices and no recommendation. The code has
one neighbouring state, `recommendation_withheld_weak_feed_opportunity`, but it
withholds the recommendation **and** the products together, so it is not a precedent
for showing four without one. The instruction above resolves the conflict the other
way -- get the data rather than drop the recommendation -- so the no-recommendation
state was not built. That is the right resolution and this document follows it.

## What a second network can and cannot fix

A network does not generate ratings; it passes on what a merchant uploads. Awin's own
column reference describes `average_rating` as "sometimes used" and `rating` as
"seldom used": they are optional fields, and in the feed PicWise has, 127 of 11,573
rows carry one and every value is `0`. No network can compel a merchant to fill an
optional column, so **changing network does not guarantee ratings** -- it has to be
tested with a real feed from that network, the same way this one was.

What a second source **can** fix is specifications, and there the answer is concrete:

- **Icecat** publishes a free, licensed product catalogue (Open Icecat) keyed by GTIN
  (EAN/UPC) and by brand plus manufacturer part code, with real-time CSV/XML/JSON
  interfaces. The feed PicWise has carries `mpn` on 67% of its rows and `ean` on 34%,
  so a large part of the catalogue is addressable. Its fair-use terms require the
  "Specs Icecat" attribution and an "as is" disclaimer on any data sheet built from
  it, which is a condition to honour, not an obstacle.

That gives the cross-check the owner asked for, for specifications. It does not give
ratings: Icecat carries editorial and award content, not customer scores.

## Why ratings have no clean source, and what is left

Searched for a source of aggregate product ratings addressable by GTIN. The GTIN
lookup providers (Barcode Lookup, EAN-Data, the Apify actors) return product
attributes, not ratings. The two that do return customer reviews reach them by
resolving a GTIN into a marketplace item -- eBay and Amazon -- and both come with
licensing limits on storing and redistributing the reviews; Amazon is in any case
already out of PicWise's decision path by `docs/picwise_amazon_removed_from_decision_path.md`.

So the realistic source is the one the owner named: **the merchant's own product page**,
where a shop that collects reviews usually publishes them as schema.org
`AggregateRating` in JSON-LD, because that is what search engines read. Reading it is
scraping, and it carries conditions:

1. **Each shop's terms and robots.txt govern it, per shop.** Some forbid automated
   access outright. This is decided shop by shop, not once.
2. **Volume.** 9,954 showable products across 26 hosts is 9,954 requests per refresh.
   It needs a rate limit, a cache, and a refresh policy, or it is a crawl that will be
   blocked and should be.
3. **A scraped rating must carry its source and its date** and be shown that way --
   "4.3 from 128 reviews at <shop>, read on <date>". A number without them is an
   unattributed claim, which `ANTI_FAKE_TRUST_RULES` forbids as surely as a made-up one.
4. **Two shops' ratings for two different products are not directly comparable**:
   different audiences, different sample sizes, different review prompts. A minimum
   review count, and a rule for what happens when one of the four has no rating, are
   decisions for the owner before any ranking uses them.

## The cheapest next step, and what blocks it

Before a scraper is written for 9,954 products, the question is whether these shops
publish a rating at all. That is a measurement of about twenty pages per shop: fetch
the product page, look for `AggregateRating` in its JSON-LD, count how many shops
carry one and on what share of their products. If the shops do not publish ratings,
scraping yields nothing and the plan has to change before any of it is built.

**It cannot be run from this environment today.** Outbound requests to the merchant
hosts are denied by the environment's network policy -- the proxy answers 403 and the
hostnames do not resolve -- so neither the measurement nor Icecat can be reached. The
owner opens this under Network access in the cloud environment's settings (the
environment menu in the session title bar, then Edit), either at a broader access
level or by adding these hosts, leaving "Allow package managers" ticked. The steps are
at https://code.claude.com/docs/en/cloud-environments#network-access

The hosts in the current feed, by how many products each carries:

```
boxed2me.co.uk (3474)          www.aperturee.com (1802)      www.tvcables.co.uk (1059)
www.geekbuying.com (877)       www.cabledepot.co.uk (686)    cerqular.com (672)
fanink.com (621)               ie.plusshop.com (515)         www.tooled-up.com (423)
uk.plusshop.com (341)          ie.bazta.com (202)            uk.bazta.com (202)
www.amberpromos.com (151)      printerval.com (120)          www.4x4predator.co.uk (109)
tluxyit.myshopify.com (105)    www.doctorblooms.co.uk (99)   www.mi.com (65)
www.baccusstore.co.uk (18)     morethisway.co.uk (9)         lumipia.com (6)
likaclothes.com (6)            petcube.com (6)               www.fivestardirect.co.uk (3)
www.workoutforless.co.uk (1)   ams.buy.mi.com (1)
```

Plus `data.icecat.biz` for the specification cross-check.

## Order of work this implies

1. Open network access, then **measure** which shops publish `AggregateRating` and on
   what share of their products. Report per shop, as `tools/check_awin_feed.py`
   already does for descriptions and specifications.
2. If ratings exist: build the reader with source and date stored per rating, decide
   with the owner the minimum review count and the rule for a four where one product
   has no rating, then make the rating the first criterion of the comparison, as the
   owner requires.
3. In parallel, and independent of ratings: **Icecat** for specifications by MPN/EAN,
   which is the cross-check the owner asked for and needs no scraping.
4. Only if neither yields enough: return to the owner with what the data allows,
   rather than inventing a signal or dropping the recommendation the mission requires.
