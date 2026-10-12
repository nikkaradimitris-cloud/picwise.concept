# Review: what the project already specifies about judging products

Written on the owner's instruction of 2026-10-12: do a proper review, and **change
nothing in the main project**. So nothing in `PROJECT_RULES.md`, `concept.picwise.txt`,
`docs/MISSION.md` or `docs/BRAINS_SPEC.md` is touched by this document. It reports
what they say, where the implementation stands against them, and which of the owner's
three instructions is already specified and which is new.

## 1. The five brains are specified and implemented

`docs/BRAINS_SPEC.md` names five, each with its own criteria, and all five must output
the same contract shape -- four choices and one recommended:

| Brain | Criteria the spec gives it |
| --- | --- |
| Tech / Specs / Electronics | compatibility, core specs, practical performance, value-to-spec ratio |
| Software / Programs / SaaS | feature fit, pricing tiers, ease of use, limits, lock-in risk, support |
| Physical Products / Home / Machines | capacity, consumption, durability, maintenance, warranty, household fit |
| Financial / Utility / Contract | total cost, terms, hidden fees, cancellation rules, provider reliability, user risk |
| High-Trust / Risk / Sensitive | safety, certifications, return policy, reliability, claim seriousness, error risk |

`src/picwise_engine/brain_selector.py` implements the routing, by keyword sets per
brain. Exactly one brain is selected per query, and the spec forbids commission or
payout from being a selection signal.

So the owner's description is accurate: five parallel judges under the search
understanding, each called for the kind of thing asked for.

## 2. The category grouping already exists, in two layers

The owner's point -- there is no "best pair of shoes", no "best bag", no "best
tablecloth", no "best wine", so categories and subcategories must be grouped -- is
already answered by the project in two places, and they are different layers.

**The taxonomy layer: six engines, eighteen mega-categories.**
`src/picwise_taxonomy/engine_registry.py` and `mega_category_registry.py` are the
source of truth, locked at Stage 22B:

| Engine | Its three mega-categories |
| --- | --- |
| home_living_appliances | home_appliances_laundry_climate · kitchen_cooking_household · furniture_living_storage_smart_home |
| tech_electronics_office | phones_mobile_accessories · computers_office_peripherals · audio_video_gaming_cameras |
| auto_moto_mobility | car_parts_service_maintenance · tyres_wheels_car_accessories · moto_bicycle_mobility_gear |
| tools_diy_garden_repair | power_tools_workshop · hand_tools_consumables_measuring · garden_outdoor_repair_building |
| health_beauty_family_lifestyle | health_wellness_safety_devices · beauty_grooming_personal_care · baby_kids_pets_sports_outdoor |
| fashion_footwear_jewelry_accessories | clothing_apparel_workwear · footwear_shoes_sneakers_boots · jewelry_watches_bags_fashion_accessories |

Shoes and bags are already their own engine -- `fashion_footwear_jewelry_accessories`
-- separate from `tech_electronics_office`. The grouping the owner asks for is
therefore not a new structure to invent but a rule to attach to the structure that
exists. Note what is **not** in these eighteen: wine, food and drink, and home
textiles such as tablecloths. The feed PicWise was given is full of them (899 table
runners and placemats), which is one reason so many of its products answer nothing.

**The answer layer: the four roles, which change per category.** This is the project's
actual answer to "there is no best bag", and it is in `concept.picwise.txt`, which the
source-of-truth order puts second only to `PROJECT_RULES.md`:

> «Τα 4 προϊόντα είναι 4 διαφορετικές απαντήσεις.» -- the four products are four
> different answers.

and then, explicitly, that the roles change by category:

| Category in the concept | Its four roles |
| --- | --- |
| A simple technical product | Budget · Value · Best Overall · Premium |
| A child's car seat | Safe Budget · Best Safety · Best Comfort · Premium Isofix |
| Invoicing software | Basic · Best for Small Business · Best Overall · Pro / Premium |
| An electricity plan | Low standing charge · Fixed charge · Flexible plan · Best Overall on terms |

So PicWise never claimed there is one best bag. It claims four answers, each best at
something, and one of them recommended -- «Κάθε σελίδα έχει ένα και μόνο ένα
recommended. Όχι δύο.» What is missing is the **role set per category group**: which
four roles a bag gets, which four a tablecloth gets. That is the piece of work the
owner's point 2 names, and it sits on top of the eighteen mega-categories.

## 3. "Rating first" is new specification, and it fills an open TODO

The owner's point 3 gives an order for the judgement: **first and foremost the
product's rating**, then availability, then the merchant's reliability -- a product
bought thousands of times with a good rating being the reliable one.

That order is **not currently written anywhere in the project**, and this review says
so rather than claiming otherwise. What the project has today:

- `docs/MISSION.md`: "Recommendation logic is based on user fit, reliability, cost,
  terms, risk, availability, and decision quality." A list, with no order, and no
  rating in it.
- `docs/BRAINS_SPEC.md`: per-brain criteria, none of which is a rating.
- `concept.picwise.txt`: forbids fake ratings; does not rank by real ones.
- `docs/PICWISE_DECISION_CONTRACT.md`: "Ranking formula weights: TODO".

So point 3 is not a restatement, it is the decision that closes that TODO. It is
recorded in the Decision Contract under Undefined Details, where the owner's earlier
decisions were recorded, and nothing in the mission, the brains spec or the concept is
edited.

## 4. Where the implementation actually stands

The design above is complete and coherent. The implementation has fallen back from it
in one specific place, and the reason is data, not design.

`src/picwise_providers/decision_labels.py` builds each card's `role_label` from the
only comparable fact the feed supplies -- its price. Today a card reads "Lowest price
of these four", "Second lowest price of these four", "Highest price of these four".
Those are not the concept's roles. Budget, Value, Best Overall and Premium are
judgements about the product; lowest and highest price are facts about the offer.

The measurements behind that, all taken on the first real feed (11,573 products):

- **No ratings.** 127 rows carry `average_rating` and every value is `0`.
- **Almost no rankable specifications.** After the description rule, headphones state
  one on 17% of showable products, speakers 8%, cameras 5%, every other kind 0%.
- **Two thirds of products can be looked up elsewhere.** 7,592 of 11,573 carry a valid
  GTIN or a brand with a real part code, which is what a product database needs.
- **The relevance scoring does not separate products within a kind.** Measured through
  the live path: for "charging cable" 625 products are judged substantially equivalent
  and the four shown are chosen from them by price zone alone; for "speaker" 130, for
  "amplifier" 64, for "headphones" 55. The first recommendation reason code on those
  answers is literally `price_tie_breaker`.

That last line is the whole problem in one measurement: with no rating and no
specification, "the four best" degrades to "four price points", which is what the
owner has twice ruled out.

## 5. The three instructions of 2026-10-12, as rules

1. **A shop that does not meet the specifications is rejected, temporarily.** This is
   now measurable rather than a judgement: `tools/check_awin_feed.py` reports, per
   shop, whether its products can be found in a product database at all (a valid GTIN,
   or a brand with a real part code), plus description, specifications, product type,
   brand and rating. A shop at 0% findable can never be enriched and so can never be
   ranked on anything but price. On the current feed that rejects TV Cables (1,745
   products), Geekbuying (877), AmberPromos (151) and Printerval (120); it keeps
   Boxed2me (3,474, 100%), Aperturee (1,802, 100%), Tooled Up (423, 100%), Plusshop
   (856, 98%), Bazta (404, 98%) and Cerqular (672, 55%). "Temporarily" is the right
   word: a rejected shop is re-measured on every feed, so one that fixes its data
   returns on its own.
2. **The direction does not change.** The mission stands: four best products where a
   comparison can exist, and the grouping decides where it can. No no-recommendation
   state was built, and the conflict that would have required it is resolved by this
   instruction instead.
3. **Sources must be collected that meet the specifications.** The first feed does not,
   and that is settled by measurement, not opinion. What a second source can and
   cannot supply is in `docs/picwise_rating_source_plan.md`: a product database
   (Icecat, free, keyed by the GTIN on 59% of rows and the brand-plus-part-code on
   63%) answers specifications; ratings have no equivalent public source keyed by
   barcode, so they come from the merchants' own pages or from a licensed review
   provider. That document also lists what still blocks the first measurement -- the
   environment's network policy denies the merchant hosts.

## 6. What this review does not decide

- **The role set per category group.** Which four roles a bag, a tablecloth or a wine
  gets. The concept gives four worked examples and the shape; the sets for the
  eighteen mega-categories are not written, and they are the owner's to approve.
- **Where wine, food and home textiles belong.** They are not in the eighteen
  mega-categories, and the first feed is full of them.
- **What happens when one of the four has a rating and another does not.** Ranking by
  rating needs that rule before it can run.
