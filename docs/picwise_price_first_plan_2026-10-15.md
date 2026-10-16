# Price first: the owner's plan of 2026-10-15

On 2026-10-15 the owner moved PicWise away from ratings and onto price, in a session
conversation, and asked on 2026-10-16 for the project to be updated with it. This file
records what was decided, what it replaces, what stays, where it contradicts the
project's founding files, what is still open, and the marketing analysis given the
same day. The marketing part is proposals, not decisions.

**Nothing in the code has changed.** The engine still runs the rules this plan
replaces. And the plan is not to be built until the owner settles the conflicts listed
below (PROJECT_RULES section 1.4).

## Why the owner changed course

Both real feeds measured so far, about fifteen Awin shops between them, send zero
ratings and zero sales figures, checked over every row (`PROGRESS.md`, 2026-10-11 and
2026-10-15). The owner's reasons, from their message:

- if no Awin shop sends ratings, the other networks will not either, and where a few
  might, partial coverage still does not fulfil the mission;
- the ratings logic makes the project complicated and still not reliable;
- in many kinds of product ratings play no part at all;
- the project has to reach an end.

In their words: «προτείνω να πάμε με τη λογική της τιμής εμφανίζουμε πρώτα αυτά με τη
φθηνότερη τιμή και πάντα με σκληρό κριτήριο τη διαθεσιμότητα» and «έτσι απαλλασσόμαστε
από το βραχνά των αξιολογήσεων και μπορούμε να έχουμε χιλιάδες προϊόντα».

## What was decided

1. **The kind asked for, and only that.** A search shows only products of the kind
   searched for: "laptop" shows laptops, never cases, chargers or bags, unless those are
   asked for ("laptop case"). A product PicWise cannot say with confidence is the kind
   asked for is not shown; fewer and right beats more and wrong. Owner: «το laptop
   πρέπει να βγάζει laptop».
2. **Availability is a hard criterion.** A product the feed says is out of stock is
   never shown, and the feed is refreshed every day. What this can honestly mean: listed
   as in stock by the feed at its last refresh, not verified at the moment of the click.
   In the first feed Awin's `in_stock` flag is 1 on every row, and the real state is in
   `stock_status` (23% of rows); `offer_health` already reads it that way.
3. **Required on every product**, unchanged from the owner's rule of 2026-10-12: title,
   price, image, a sufficient description, link, availability. **Specifications and
   codes (EAN, GTIN, MPN) are shown when the feed has them and are never required**
   (owner: yes). Requiring them would empty the catalogue: `specifications` is filled on
   1% of the first feed, `ean` on 34% and `product_GTIN` on 26% (their union was not
   measured).
4. **Cheapest first**, by the product's price alone. Delivery cost is left out
   (owner): some shops state it and some do not (31% of the first feed), so using it
   would compare them unevenly.
5. **The same product in several shops is shown once**, from the cheapest shop that has
   it in stock; if the cheapest is out of stock, the next cheapest that is in stock.
   "The same product" means the same EAN/GTIN. Where the code is missing, products are
   not joined, so that two different products are never merged. Implementation note:
   `_product_identity_key` today also joins on brand + MPN. Whether this dedupe may do
   the same is not decided; the owner was told "the code only".
6. **No ratings**, in the ranking or on the cards. The search for a feed with ratings
   stops.
7. **The first four: one "Recommended" card first, then the three cheapest** (not
   counting the recommended one), with a counter beneath: "4 of 45". Owner: «δεν
   χαλάμε την τετράδα, γράφει 4 από 45 ... 8 από 45». The Recommended:
   - is computed over **every result of the search** (all 45), not over the four;
   - sits at **the middle of the price range: (cheapest + dearest) ÷ 2**. The owner chose
     this ("B") over the middle product by position ("A") after seeing the difference:
     with £200, £250, £300, £350, £1,500 the middle of the range is £850 and the closest
     product is £350, where A would give £300;
   - is the product whose price is **closest to that midpoint, among products with an
     EAN/GTIN** (owner: yes), so that "not cheaper elsewhere on PicWise" can be known.
     With rule 5 it is then always the cheapest in-stock offer of that product;
   - on a tie, the cheaper of the two (stated to the owner, not objected to);
   - carries the label **"Recommended"** (the owner's word, held over "Featured"). The
     line under it was proposed as "Mid-priced for this category" and not objected to.
     The owner's reasoning, with their own example of £100, £150 and £200: recommend
     £150, because for that kind of product we believe it is not worth paying £100, nor
     £200;
   - never mentions commission on the card (owner: never);
   - **uses no commission.** The owner first asked for the highest commission in money
     (€100 at 2% gives €2, €80 at 6% gives €4.80, so the €80 product wins), then
     dropped it because PicWise does not know the commission: it is not in the feed and
     is set per shop in Awin's terms. As the plan stands, the rule that commission never
     decides a recommendation is untouched. If commission ever comes back, it contradicts
     `concept.picwise.txt` (section 14, "Revenue Rule"), `docs/MISSION.md`,
     `PROJECT_RULES.md` sections 4 and 5, `docs/REVENUE_NEUTRALITY_RULES.md` and the
     Decision Contract. The owner was also told that a "Recommended" chosen by
     commission, with nothing on the page saying so, is a legal risk in the UK and the US.
8. **"More"**: the next four cheapest, "8 of 45", and again and again until the list
   ends. Nothing in them is recommended. Owner: «ο κόσμος θέλει να δει ποσότητα».
9. **One general affiliate line in the site footer**, about all links, not about the
   Recommended, e.g. *"PicWise earns a commission from shops when you buy through our
   links."* Claude stated it as required: UK (ASA, CAP Code) and US (FTC) rules on
   affiliate disclosure, which Awin expects its publishers to follow. That last point
   was not checked against Awin's own terms, because `help.awin.com` is blocked from
   sessions. The owner did not object.

## What it replaces

The earlier decisions stay in `docs/PICWISE_DECISION_CONTRACT.md` as history, each now
marked as superseded:

- the main judgement on how many bought and how they rated (2026-10-13), the
  ratings-first rule (2026-10-11), and the confidence-weighted scoring still waiting for
  a yes (floor 5 reviews, weight 20);
- a stated specification decides before the price (2026-10-13);
- the four spread across distinct price zones (2026-10-08, restated 2026-10-12);
- "see more" only for the `fit` kinds, and only once (2026-10-12). It now comes on every
  search, by price, as often as the buyer asks. The comparison classes (`spec`,
  `rating`, `fit`) no longer decide anything on the page; they stay in the code until
  the plan is built;
- the four roles of `concept.picwise.txt` (Budget, Value, Best Overall, Premium).

## What stays

- One currency per answer (2026-10-11). The plan needs it: prices in different
  currencies cannot be sorted, nor can a midpoint be taken across them.
- Item condition (2026-10-10): products that are not new appear only when asked for.
- What a product must carry (2026-10-12), see rule 3.
- Reading specifications (2026-10-12), now for display only.
- Reading the kind of a feed row and the accessory guard. This is what makes "laptop"
  show laptops.
- No fake data, the missing-data values, Amazon removed, and commission never in the
  recommendation.

## Where the plan contradicts the founding files (owner's call)

PROJECT_RULES section 1.4: when the layers conflict, stop and raise it. Raised with the
owner on 2026-10-16. None of these files was changed, because changing the mission is
the owner's decision.

| The plan | Says the opposite |
| --- | --- |
| "More" again and again, "4 of 45 ... 8 of 45" | `concept.picwise.txt` section 10: «ανοίγει μόνο 4 ακόμα / όχι infinite scroll / όχι κατάλογος / όχι 30 προϊόντα»; section 3: «Δεν τον βάζουμε να συγκρίνει άπειρες επιλογές»; `docs/MISSION.md`: must not become "an infinite product list", "small, decisive ... outputs instead of infinite browsing"; `PROJECT_RULES.md` section 4: never "Show infinite product lists" |
| The three cheapest after the Recommended | `concept.picwise.txt` section 6: «Τα 4 προϊόντα δεν είναι λίστα. Τα 4 προϊόντα είναι 4 διαφορετικές απαντήσεις» (Budget, Value, Best Overall, Premium) |
| A price-ordered list of everything in stock | `docs/MISSION.md` and `PROJECT_RULES.md` sections 2 and 4: "a decision engine, not a search engine" |

The owner has two ways out: update those files to the new plan, or bring the plan
back inside them (for example, a limited "more"). Until they choose, the plan is
recorded and not built.

## Open, for the owner

1. The conflicts above.
2. A search where no product has an EAN/GTIN: no Recommended at all? The Decision
   Contract requires exactly one. Code coverage varies by shop: Aosom 92%, the first
   feed's `ean` 34%.
3. Fewer than four results: show what there is, or nothing? Today the answer is no
   four.
4. What the three cheapest cards say. The contract requires a role label and a reason
   on every card. Proposal: "Lowest price", and "Lowest price of N shops" when rule 5
   joined offers.
5. Whether brand + MPN may also join "the same product" (rule 5).
6. The line under Recommended: "Mid-priced for this category", or the marketing
   proposal "Middle of the £X–£Y range". Also, optionally, whether to leave the extreme
   prices out of the midpoint.

## What it means for the engineering, later

Recorded so it does not have to be found again. None of it is decided.

- **Measure first.** Re-upload the 51,630-row feed (Tyres UK, Aosom UK, Living and
  Home) and count, per shop and per kind: how many products pass rules 1–3, how many
  join under rule 5, and how many carry an EAN/GTIN for the Recommended.
- **Tyres UK** (39,403 rows, the largest feed) writes its description in `custom_6`.
  Under rule 3, no tyre appears until that column is read.
- **Living and Home** (2,255 rows) sends no category, so every row is held at the feed
  gate as `missing_category_text`.
- **Thousands of products and a repeated "more"** need a store refreshed daily. Today
  every serverless cold start downloads and parses the whole feed (`AWIN_FEED_URL`,
  reused for 6 hours). Supabase only with the owner's yes.

## Marketing analysis, 2026-10-15 (proposals, not decisions)

Asked by the owner: analyse the plan at the level of marketing, and make proposals on
that basis only, across all the product categories.

### Strong

- **A promise anyone understands at once:** cheapest first, only what is in stock.
- **A Recommended in the middle is a sound choice.** Buyers tend to avoid the cheapest
  (fear about quality) and the dearest (fear of overpaying), and the middle is the
  easiest decision to make. Commission is a share of the price, so it also earns more
  than recommending the cheapest would.
- **"4 of 45" and More** show that there is plenty to choose from.

### Weak

- **Google Shopping already sorts by price**, with every shop. PicWise has a few. So
  PicWise cannot sell "the cheapest"; it sells **clean results and one sensible pick**.
- **Without ratings, the strongest tool of persuasion is gone.** Other signals have to
  take its place, and they must be true (below).
- **The middle of the range in a wide range:** watches at £5 to £5,000 put a £2,500
  Recommended next to three at £5.

### By how people buy, across the 18 mega categories

1. **"I know the model, I want the best price."** Phones, laptops, consoles and
   games, televisions, washing machines and fridges, branded cosmetics
   (`phones_mobile_accessories`, `computers_office_peripherals`,
   `audio_video_gaming_cameras`, `home_appliances_laundry_climate`, part of
   `beauty_grooming_personal_care`).
   - The plan fits perfectly here.
   - Proposal: a "Lowest price of 4 shops" badge when several shops sell the same
     product.
   - It needs several shops in the same category; with one shop there is nothing to
     compare.
2. **"I search by size, or by what it must fit."** Tyres, car parts, ink and toner,
   phone cases, cables (`tyres_wheels_car_accessories`,
   `car_parts_service_maintenance`, the accessory parts of phones and computers).
   - It fits well. In tyres the middle lands on the mid-range brand, between budget and
     premium, which is how a driver thinks.
   - Proposal: pages per size, e.g. *"Cheapest 205/55 R16 tyres in stock"*. October
     is the winter-tyre season.
   - Tyres UK is the largest feed, and its descriptions sit in `custom_6`.
3. **"I choose by eye."** Furniture, garden, clothing, shoes, jewellery, watches, bags,
   decoration, toys (`furniture_living_storage_smart_home`,
   `garden_outdoor_repair_building`, `clothing_apparel_workwear`,
   `footwear_shoes_sneakers_boots`, `jewelry_watches_bags_fashion_accessories`, toys in
   `baby_kids_pets_sports_outdoor`).
   - Here people want quantity, so More is the main tool, and the photograph sells.
   - It is the category of the shops already joined (Aosom, Living and Home, Back to the
     Office).
   - It holds the widest price ranges: watches, jewellery, sofas.
4. **"The quality cannot be seen."** Tools, small kitchen appliances, health devices,
   child car seats, helmets (`power_tools_workshop`,
   `hand_tools_consumables_measuring`, `kitchen_cooking_household`,
   `health_wellness_safety_devices`, `moto_bicycle_mobility_gear`, safety items in
   `baby_kids_pets_sports_outdoor`).
   - The cheapest is often the worst here, and without ratings the buyer cannot tell.
     So this is where a middle Recommended is worth the most.
   - Proposal: show the brand prominently (Bosch, Tefal, ...); it is the trust signal
     that stands in for ratings.
   - In child and health products, never words like "safe" or "best".
5. **"Consumables, again and again."** Nappies, printer paper, toner, razor blades,
   filters, pet food.
   - It fits perfectly: people want the cheapest in stock, and they come back.
   - Caution: 24 nappies at £5 against 96 at £15. The cheapest pack is not always the
     cheapest buy, so the pack size must be clear on the card.

### General proposals

1. **One sentence for the whole site:** *"Cheapest first. Only what's in stock. One
   smart pick."* The homepage and `/about` should say the same. That also helps the
   Awin approvals still pending (Currys, Boots). The homepage still reads "Buying
   Decision Preview" and `/about` is a 404; the owner declined a fix on 2026-10-14,
   before the plan changed.
2. **Put the price range in the label:** *"Recommended · Middle of the £130–£3,500
   range"*. It is entirely true and explains by itself why the Recommended can cost more
   than the cheap three. Optionally, leave the extreme prices out of the midpoint.
3. **The strongest trust line available:** *"Our pick is never paid for."* True as long
   as commission stays out of the Recommended, which it does under this plan.
4. **Never "the cheapest in the UK".** Use "Sorted by price" or "Lowest price across 4
   shops". And no "Save £X" against a list price (RRP) unless it is certain; UK pricing
   rules check this strictly.
5. **Awin applications:** two or three shops in the same category, because comparison
   needs overlap. Shops that sell mainly their own brand (Gtech, Road Angel, Aosom,
   Songmics) give nothing to compare against. In the application: "we send only
   in-stock products, and our pick is mid-priced, not the cheapest". Some shops are wary
   of price-comparison sites, and this reassures them.
6. **Pages for search engines per subcategory:** *"Cheapest [X] in stock — updated
   daily"*. The feeds can supply thousands of real pages.
7. **Calendar:**
   - now: winter tyres;
   - 27 November 2026: Black Friday (electronics, consoles);
   - December: toys, perfume;
   - January: furniture, mattresses;
   - spring: garden;
   - August: laptops and office.

**Top three:** tyres first (the largest feed, in its season); electronics before
Black Friday; "Our pick is never paid for" and a new homepage sentence.
