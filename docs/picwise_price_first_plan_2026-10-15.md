# Price first: the owner's plan of 2026-10-15

On 2026-10-15 the owner moved PicWise away from ratings and onto price, in a session
conversation, and asked on 2026-10-16 for the project to be updated with it. This file
records what was decided, what it replaces, what stays, where it contradicts the
project's founding files, what is still open, and the marketing analysis given the
same day. The marketing part is proposals, not decisions.

**Nothing in the code has changed.** The engine still runs the rules this plan
replaces. The conflict with the founding files was settled on 2026-10-16: the owner
chose to change them to the plan, and they now say the same (see below).

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
   **Decided by the owner on 2026-10-16: the feed's word is trusted, and no shop page
   is checked.** On the third feed no shop sends a usable stock state, so there this
   rule removes nothing; the application messages ask shops to send it.
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
   - is **the middle product in price order** ("A", the median: of 45, the 23rd).
     **Changed on 2026-10-16.** The owner first chose "B", the middle of the price range,
     (cheapest + dearest) ÷ 2, over A, having seen the difference on £200, £250, £300,
     £350 and £1,500 (B gives £350, A £300). Measured on the third feed, B recommended
     the top end: a £4,809.99 MacBook Pro for "laptop", where A gives a £879.99 ThinkPad
     (see "Measured on the third feed"). Shown that, the owner chose A;
   - must have an **EAN/GTIN** (owner: yes), so that "not cheaper elsewhere on PicWise"
     can be known. If the middle product has none, the nearest product to it that has
     one; of two equally near, the cheaper. With rule 5 it is then always the cheapest
     in-stock offer of that product;
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

## Where the plan contradicted the founding files: settled 2026-10-16

PROJECT_RULES section 1.4: when the layers conflict, stop and raise it. Raised with the
owner on 2026-10-16. Given the choice of changing the founding files or narrowing the
plan, **the owner chose to change the files**, and they were changed the same day:
`concept.picwise.txt` sections 1-8, 10, 11, 13 and 22, `docs/MISSION.md`,
`PROJECT_RULES.md` sections 2-5 and `docs/LANDING_PAGE_SPEC.md`. Every changed passage
in the concept carries a dated note. Services (insurance, energy, banking, software)
were not part of the decision, so their passages were left as they were and say so.

What the files said before:

| The plan | What the files said |
| --- | --- |
| "More" again and again, "4 of 45 ... 8 of 45" | `concept.picwise.txt` section 10: «ανοίγει μόνο 4 ακόμα / όχι infinite scroll / όχι κατάλογος / όχι 30 προϊόντα»; section 3: «Δεν τον βάζουμε να συγκρίνει άπειρες επιλογές»; `docs/MISSION.md`: must not become "an infinite product list", "small, decisive ... outputs instead of infinite browsing"; `PROJECT_RULES.md` section 4: never "Show infinite product lists" |
| The three cheapest after the Recommended | `concept.picwise.txt` section 6: «Τα 4 προϊόντα δεν είναι λίστα. Τα 4 προϊόντα είναι 4 διαφορετικές απαντήσεις» (Budget, Value, Best Overall, Premium) |
| A price-ordered list of everything in stock | `docs/MISSION.md` and `PROJECT_RULES.md` sections 2 and 4: "a decision engine, not a search engine" |

## Open, for the owner

1. ~~The conflicts above.~~ Settled on 2026-10-16: the founding files were changed.
2. A search where no product has an EAN/GTIN: no Recommended at all? The Decision
   Contract requires exactly one. Code coverage varies by shop: Aosom 92%, the first
   feed's `ean` 34%.
3. Fewer than four results: show what there is, or nothing? Today the answer is no
   four.
4. What the three cheapest cards say. The contract requires a role label and a reason
   on every card. Proposal: "Lowest price", and "Lowest price of N shops" when rule 5
   joined offers.
5. Whether brand + MPN may also join "the same product" (rule 5).
6. The line under Recommended: "Mid-priced for this category". The marketing
   proposal "Middle of the £X–£Y range" no longer fits, because the Recommended is now
   the median and not the middle of the range.

## What it means for the engineering, later

Recorded so it does not have to be found again. None of it is decided.

- **Measure first.** Re-upload the 51,630-row feed (Tyres UK, Aosom UK, Living and
  Home) and count, per shop and per kind: how many products pass rules 1–3, how many
  join under rule 5, and how many carry an EAN/GTIN for the Recommended.
- **Tyres UK** (39,403 rows, the largest feed) writes its description in `custom_6`.
  Under rule 3, no tyre appears until that column is read.
- **Living and Home** (2,255 rows) sends no category, so every row is held at the feed
  gate as `missing_category_text`.
- **The code caps "more" today.** `src/picwise_contracts/models.py` rejects more than 4
  `more_choices` ("no infinite list behavior"), and `search_selection._next_four_after`
  offers a second four only for `fit` kinds. Both follow the old rule and change when
  the plan is built.
- **Thousands of products and a repeated "more"** need a store refreshed daily. Today
  every serverless cold start downloads and parses the whole feed (`AWIN_FEED_URL`,
  reused for 6 hours). Supabase only with the owner's yes.

## Measured on the third feed, 2026-10-16

The owner sent a new file for the shops asked for: 42,076 rows, 100 columns, all GBP.
**Back to the Office** has 29,831 rows and is an IT and office-supplies shop, not a
furniture one: cables, toner, laptops, drives, UPS units, monitors, phones, ink,
keyboards, printers. **Aosom UK** has 9,984 and **Living and Home** 2,261. Songmics and
Euroffice are not in it.

Method: the project's own loader and checks (`offer_health`, `product_description`,
`product_identity`, `search_selection._product_concepts` and `_title_accessory_penalty`).
The kind test is membership in the concept with the accessory penalty at zero. That is
a stand-in for the strict test the plan needs, not that test.

- **`tools/check_awin_feed.py`:** 39,592 products card-eligible; **Living and Home 0**,
  all its rows held at the feed gate for having no category; ratings 0; 15 refurbished;
  a known kind for 61% of eligible products. **Each sample search took 3.7 to 16.2
  seconds**, against the section 9 target of a first render under 1.5 seconds.
- **Rules 1–3:** 41,692 rows carry title, price, image, description, link and
  availability (Aosom 9,930, Back to the Office 29,661, Living and Home 2,101; 159 of its
  rows have no price). With a known kind that is not an accessory, 21,135: Aosom 5,083,
  Back to the Office 15,358, and Living and Home 694 with the kind read from the title.
  The plan does not require a category, so those 694 could be shown.
- **Rule 2 removes nothing, because no shop sends a usable stock state.** `in_stock` is 1
  on every row of all three. `stock_status` reads "in stock" on every Aosom row and is
  empty for the other two, and `stock_quantity` is empty everywhere. Every product is
  "listed as available", and nothing in the feed can pick out one that is not.
- **Rule 5 joins nothing.** No EAN/GTIN appears in two shops: these shops sell
  different products. 17 codes repeat inside a single shop.
- **Kinds:** 167 have at least one product and 122 have four or more. Kinds where two
  shops each have four or more: chair, table, toy, bag, garden furniture, lamp, bed,
  office chair, shelving, fan, desk, mirror, heater, sofa, tent, grill, kettle, coffee
  machine, dinnerware. Laptops, phones, printers, toner and the other IT kinds come
  from Back to the Office alone.
- **Cheapest first exposes every mistake in reading the kind,** because accessories and
  look-alikes are the cheapest things in any kind. Even with the engine's accessory test
  as a strict gate:
  - the three cheapest "laptops" are docking stations (£11.99, £16.99, £17.99);
  - the cheapest "smartphone" is a screen protector (£2.99), and the cheapest "tablets"
    are folio cases (£15.99);
  - the cheapest "monitor" is a temperature-and-humidity monitor (£20.99), and the
    cheapest "printers" are ribbon cartridges (£2.99);
  - the cheapest "desk" is a letter tray (£8.99), and the cheapest "sofa" an armrest
    tray (£14.99);
  - "bed" opens with pet beds, and "garden furniture" with furniture covers.

  Today the relevance order keeps these at the bottom; price order puts them at the
  top. So rule 1 needs a strict yes/no test of the kind, and that is the first
  engineering step.
- **The middle of the range picks the top end.** The Recommended under the rule as
  decided ("B"), under the middle product by position ("A", the median), and under B
  with the cheapest and dearest 5% left out:

  | Kind | B (decided) | A (median) | B without extremes |
  | --- | --- | --- | --- |
  | laptop | £4,809.99 MacBook Pro 16" | £879.99 ThinkPad L13 | £1,804.99 |
  | monitor | £2,574.99 | £226.99 | £580.99 |
  | printer | £6,504.99 large-format | £161.99 | £1,105.99 |
  | headphones | £279.99 | £67.99 | £129.99 |
  | office chair | £332.99 | £94.99 | £205.99 |
  | garden furniture | £643.99 | £110.99 | £288.99 |
  | sofa | £600.00 | £295.99 | £600.00 |
  | kettle | £69.99 | £41.99 | £45.99 |

  Prices are skewed: a few dear products stretch the range, so its middle sits near
  the top. One mistyped price can decide it. The "monitor" range runs to a product
  listed at £1,344,000. The median moves for neither, but any accessory left in the list
  pulls it down: for "smartphone" it lands on a £23.99 screen protector. So it needs rule
  1 first. Put to the owner on 2026-10-16.

## Search understanding, English, measured 2026-10-16

Asked by the owner: does the search understand English typed with misspellings and in
different phrasings, so that it knows what to send? Test: 118 queries written by
hand for the kinds in the third feed, run through the real resolver
(`resolve_live_search`) on that feed (42,076 rows). The styles were 37 clean names, 26
misspellings, 30 phrasings and sentences, 14 synonyms, 4 with a brand and 7 for kinds
the lexicon does not know. Every card shown was then read by hand.

**Understanding is good; what is shown is not yet.**

| Outcome | Searches |
| --- | --- |
| the right kind understood | 109 of 118 (92%) |
| all four cards right | 80 |
| three of four right, or a qualifier missed ("gaming", "ssd") | 7 |
| wrong things shown | 21 |
| nothing shown | 10 |

- **Misspellings: 21 of 26 understood:** labtop, lapptop, smartfone, tablit, moniter,
  headfones, keybord, mosue, printor, tonner, hardrive, ofice chair, tabel, soffa,
  garden furnature, barbeque, kettel, heatr, shelfs, dumbells and the rest. Not
  understood: "inc cartridge", "tnet", "lamb for bedroom" and "mirrer", each offered
  the right "did you mean" (ink cartridge, tent, lamp, mirror). "dsek for home office"
  got no suggestion.
- **Phrasings and synonyms work:** "i need a new laptop for work", "cell phone",
  "mobile phone", "notebook computer 15 inch", "pc screen 24in", "couch", "web cam
  for zoom calls", "uninterruptible power supply". Kinds the lexicon does not know
  were found by their words: greenhouse, cat tree, dog crate, rabbit hutch, memory
  card, network switch.
- **The 21 with wrong things are kind-reading errors, not understanding errors.**
  - "tablet" (4 searches) shows tablet casings and mounts;
  - "desk" (3) shows desk trays and under-desk drawers;
  - "dining table" and "coffee table" show a wall clock and table football;
  - "printer" (3) shows label makers;
  - "desk fan" and "pedestal fan" show fan speed controllers, and "ceiling fan with
    light" shows PC case fans;
  - "floor lamp" shows table lamps, and "double bed frame" camping cots;
  - "corner sofa bed" shows dog sofa beds, and "ups battery backup" shows replacement
    UPS batteries.

  This is the same flaw the price-first measurement found, and the same fix: a strict
  yes/no test of the kind.
- **Two bugs.**
  - "patio set" and "patio heater" are read as "insoles": "patio" is taken for the
    greeklish of «πάτοι». English must win over a greeklish reading of a real English
    word.
  - "3 seater sofa grey", "4 person camping tent" and "electric kettle 1.7l" find
    four right products, and the page still shows nothing. The old recommendation step
    demands every word of the search from each card, finds no card with all of them,
    recommends none, and the render gate then refuses the page. The median rule
    replaces that step.
- **Data:** an iiyama monitor priced £1,344,000.00 appears on two answers. A price
  sanity check is needed before cards are drawn.
- **Speed:** 3.4 to 20 seconds per search, median 4.1 s, against the 1.5 s target.

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
2. ~~**Put the price range in the label:** *"Recommended · Middle of the £130–£3,500
   range"*.~~ No longer fits since 2026-10-16: the Recommended is the median, not the
   middle of the range.
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
