# Price first: the owner's plan of 2026-10-15

On 2026-10-15 the owner moved PicWise away from ratings and onto price, in a session
conversation, and asked on 2026-10-16 for the project to be updated with it. This file
records what was decided, what it replaces, what stays, where it contradicts the
project's founding files, what is still open, and the marketing analysis given the
same day. The marketing part is proposals, not decisions.

**Built on the branch, 2026-10-16:** steps 1 to 3 of the build order (below), so a
search whose product is understood now runs this plan: see "Step 1 built", "Step 2
built" and "Step 3 built". A search whose product is not understood still runs the rules
this plan replaces. The conflict with the founding files was settled on 2026-10-16: the
owner chose to change them to the plan, and they now say the same (see below).

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
   **Phones (owner, 2026-10-16):** «Smartphone να δείχνεις smartphone... Τα υπόλοιπα
   είναι mobile phone». "smartphone" shows only smartphones. "mobile phone", "cell
   phone", "phone" and «κινητό» show only the other mobile phones: basic, flip and
   big-button phones. The owner chose this over "all mobile phones" when both were
   put to them.
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
   "The same product" means the same EAN/GTIN, or, where that code is missing, **the
   same brand and the same manufacturer code (MPN)** (owner, 2026-10-16). Without
   either, products are not joined, so that two different products are never merged.
   `_product_identity_key` already joins on brand + MPN.
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
   - leaves out extreme top prices (owner, 2026-10-16): before the middle is found, a
     dearest product that costs at least twice the next dearest does not count, and
     again for the next one. It stays in the list. With £100, £150, £200 and £1,000,
     the £1,000 is five times £200 and does not count, so the Recommended is £150;
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
     commission, with nothing on the page saying so, is a legal risk in the UK and the US;
   - **is left out when no product of the search has an EAN/GTIN** (owner,
     2026-10-16). The four cheapest are then shown with no Recommended, because without
     a code PicWise cannot know that the same product is not cheaper elsewhere.

   **Fewer than four right products are shown as they are**, with "2 of 2" (owner,
   2026-10-16). Today such a search shows an empty page.
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
2. ~~A search where no product has an EAN/GTIN.~~ Settled on 2026-10-16: no
   Recommended, the four cheapest only (rule 7).
3. ~~Fewer than four results.~~ Settled on 2026-10-16: shown as they are, "2 of 2"
   (rule 7).
4. ~~What the three cheapest cards say.~~ Settled on 2026-10-16 (owner: «Οκ» to the
   proposal): "Lowest price", and "Lowest price of N shops" when rule 5 joined offers.
5. ~~Whether brand + MPN may also join "the same product".~~ Settled on 2026-10-16:
   yes (rule 5).
6. ~~The line under Recommended.~~ Settled on 2026-10-16 (owner: «Οκ»): "Mid-priced
   for this category". The marketing proposal "Middle of the £X–£Y range" no longer
   fits, because the Recommended is now the median and not the middle of the range.

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
  the plan is built. *Step 3 (2026-10-16): `_next_four_after` is gone and "More" runs on
  every understood search. The contract model is not used by the live page and still
  has the cap.*
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

## Step 1 built: only the kind asked for, 2026-10-16

The owner's rule, in their words: «το laptop πρέπει να βγάζει laptop». Built on the
branch, not on `main`: the kind reader (`src/picwise_nlu/concept_understanding.py`),
the lexicon (`src/picwise_nlu/product_concepts.py`) and the search
(`src/picwise_providers/search_selection.py`), tested in
`tests/test_picwise_strict_kind_reading.py`. The page still shows the old four cards.
Price order, More and the median come in step 3. What they will show is decided here,
because price order puts each kind's cheapest products first, and those were its
accessories and look-alikes.

**How a product's kind is read now.**
- **The product type, by its last words.**
  - "Tablet Cases" are cases; "Printer Labels" and "Printer Drums" are supplies.
  - A type that names a kind PicWise does not know makes the product doubtful, and
    its title is not searched for a kind instead. "Temperature & Humidity Sensors"
    are not monitors.
  - A type that lists such a kind ("Industrial Environmental Sensors & Monitors",
    "Power Adapters & Inverters") needs the title to name the known kind.
- **Each category field is its own breadcrumb.** A feed row carries the shop's own
  path, the network's taxonomy and a short name. These used to be joined into one
  text, and the shelves ran into each other ("console tables home & garden"). The
  first field that says anything decides: the shop's "Laundry > Tumble Dryers" over
  the network's "Bathroom Accessories".
- **The title's lead** is the part before "(", ",", " - ", ":", "+", "with", "for" or
  "w/". A "+" between digits does not end it, so "4+1 Burner" stays in.
  - The noun the lead ends with is the product: "Lenovo Tab 11" Folio Case" is a
    case, "Sandbox Cover" a cover.
  - A lead that names a kind only to describe something else makes the product
    doubtful: "Coat Rack ... Shelf", "Sofa Arm Tray", "Safety Bed Rail", "Basketball
    Hoop".
  - On a shelf, a kind named inside the product's own phrase only describes it:
    "Kids Desk Chairs" on the kids' desks shelf are chairs.
- **A product filed in another department is doubtful,** such as a car booster seat
  on the "Changing Tables" shelf. Toys and garden furniture are aisles and keep what
  is filed there: a kids' scooter is a toy, and a bistro table is garden furniture.
- **Pet and camping products carry their context.** "bed" shows no dog beds or
  camping cots; "dog bed" shows dog beds.
- **A doubtful product is never shown for a kind** but is still found by its own
  words. This is 11,187 of the 42,076 rows. Another 4,714 are accessories, against
  4,409 before.

Products counted per kind on the whole feed, before and after:

| Kind | Before | After |
| --- | --- | --- |
| laptop | 1,118 | 734 |
| smartphone | 840 | 132 |
| tablet | 326 | 123 |
| printer | 535 | 260 |
| ups | 918 | 211 |
| fan | 229 | 38 |

**New kinds,** so that the look-alikes have their own:
- desk phone (IP and conference phones);
- label printer;
- PC cooling;
- sofa bed;
- game table (foosball, pool, table tennis, poker);
- play tent (a toy);
- shower seat;
- greenhouse (grow tents, polytunnels);
- barbell (weight plates).

Existing kinds were widened too: raised garden beds are planters, electric
fireplaces are heaters, and ceiling and pendant lights are lamps.

**Measured on the third feed** (42,076 rows), with the same 118 English searches as
before, every card read by hand:

| Outcome | Before | After |
| --- | --- | --- |
| all four cards right | 80 | 95 |
| right kind, but a card misses a word of the search | 7 | 12 |
| wrong things shown | 21 | 0 |
| nothing shown | 10 | 11 |

The misspelling benchmark is unchanged: 96.0%, 1 wrong, 27 not understood. Of 106
test modules, 105 pass. The other, `test_picwise_query_understanding`, fails the same
two tests ("machine" ambiguity) on the unchanged code too.

**What price order would list first,** the cheapest product of each kind on this feed
that passes the card rules:

| Kind | Before | Now |
| --- | --- | --- |
| laptop | £3.99 USB-C audio adapter | £125.99 HP Stream laptop |
| smartphone | £2.99 screen protector | £67.99 Crosscall mobile phone |
| tablet | £15.99 folio case | £72.99 Samsung Galaxy Tab A |
| monitor | £20.99 temperature and humidity monitor | £58.99 piXL portable monitor |
| printer | £2.99 ribbon cartridge | £45.99 Canon PIXMA inkjet printer |
| desk | £8.99 letter tray | £19.99 foldable laptop desk |
| table | £16.99 table football | £17.99 bedside table |
| sofa | £14.99 sofa arm tray | £39.99 kids' sofa |
| bed | £12.99 cat bed | £59.99 single bed frame |
| tent | £19.99 kids' play tent | £22.99 2-person camping tent |
| toy | £12.99 sandbox cover | £16.99 kids' playhouse |
| fan | £4.99 PC case fan | £16.99 handheld fan |
| ups | £44.99 replacement battery | £46.99 VIDA 650VA UPS |

The middle product moved the same way. For "smartphone" it was a £23.99 phone case and
is now a £868.99 iPhone 16. For "tablet" it was a £93.99 folio and is now a £936.99
iPad mini.

**Phones, split the same day by the owner's rule.** The cheapest "smartphone" results
were Crosscall and Doro basic phones that the feed files as "Mobile Phones". There are
now two kinds:
- **smartphone** answers "smartphone", "smart phone", "android phone" and "galaxy
  phone";
- **mobile phone** answers "mobile phone", "cell phone", "phone", «κινητό», "flip
  phone" and "basic phone".

Feeds file both under "Mobile Phones": the first real feed held its smartphones there,
the third its basic phones. So the title says which. A phone is a smartphone when its
title says so, or names what only a smartphone has: Android, iOS, iPhone or 5G, 16 GB
of storage or more, or a screen of 4 inches or more.

On the third feed, "smartphone" now opens with a £113.99 TCL smartphone, and "mobile
phone", "cell phone" and «κινητό» with a £67.99 Crosscall and Doro basic phones. A
plain "phone" shows the search's suggestions instead of cards, as it did before.

The misspelling benchmark falls from 96.0% to 93.9% (42 not understood, 27 before). The
15 new misses are all «κινητό τηλέφωνο» and its misspellings. The benchmark expects
them to find its fixture's "Mobile Phones" rows, which are smartphones. Under the rule
they now look for basic phones, which that fixture does not stock. The benchmark was
left as it is, so that the number shows the rule's effect.

**What step 1 does not fix:**
- **The other words of a search still do not narrow the kind.** "ceiling fan with
  light" shows handheld fans, "portable ssd" shows portable hard drives, and one
  wired headset appears under "wireless headphones". This is step 3: the price-first
  engine reads those words.
- **Empty pages** for "3 seater sofa grey", "4 person camping tent", "electric kettle
  1.7l" and now "gas bbq with 4 burners". The search finds four right products,
  here four 4+1 burner gas grills, and the old decision step answers
  "insufficient_selected_products", so no page is drawn. That step goes in step 3.
- **"patio"** was read as greeklish. Fixed in step 2, below.
- **Searches for an accessory of a kind** are read as the accessory's own kind:
  "bbq cover" is read as a phone case, through the lexicon's weak "cover". This was
  found, not fixed, and the old code reads it the same way.
- **Prices:** £0.99 headsets and a £1,344,000 monitor reach the cards. A price check
  before cards are drawn belongs to step 3.

## Step 2 built: English before greeklish, 2026-10-16

The bug: "patio set" and "patio heater" answered with insoles, because "patio" was
read as the greeklish of «πάτοι». The rule now: a Latin-script word that PicWise's own
lexicon knows as English is not read as the greeklish of a Greek name of another kind.
A greeklish reading that names the same kind stays: "consoles" and «κονσόλες»,
"laptop", "mixer". Greeklish that is not an English word is read as before: "patoi"
is still insoles, and "skales" is still ladders.

Checked across the whole lexicon, the rule changed two words:
- "patio" was insoles;
- "scales" was ladders («σκάλες»).

"patio" is now a word buyers use for garden furniture ("patio set"). In feed titles it
names nothing by itself: a "Patio Heater" is a heater.

On the third feed, of the same 118 searches:
- "patio set" now shows four garden furniture sets;
- "patio heater" shows four patio heaters;
- before, both showed nothing.

| Outcome | After step 1 | After step 2 |
| --- | --- | --- |
| all four cards right | 95 | 97 |
| right kind, but a card misses a word of the search | 12 | 12 |
| wrong things shown | 0 | 0 |
| nothing shown | 11 | 9 |

"mobile phone" and "cell phone" now show basic phones, which is right by the owner's
rule of the same day. The misspelling benchmark is unchanged by this step, at 93.9%
with the same cases. Tests: `tests/test_picwise_english_over_greeklish.py` (3).

The nine that show nothing:
- "3 seater sofa grey", "4 person camping tent", "electric kettle 1.7l" and "gas bbq
  with 4 burners" are the old decision step, which goes in step 3;
- "inc cartridge epson", "tnet", "lamb for bedroom" and "mirrer" each offer the right
  "did you mean";
- "dsek for home office" offers none.

## Step 3 built: price first, 2026-10-16

Built on the branch, not on `main`, for every search whose product is understood:
`src/picwise_providers/search_selection.py` (the selection), `src/picwise_providers/state.py`
(the decision), `src/picwise_surface/reference.py` (the page). "More" is a `shown`
parameter on `/search`. Tested in `tests/test_picwise_price_first.py`.

**What a search shows now.**
- Every product of the kind asked for that carries the search's other words, cheapest
  first, each product once.
- The first page: the Recommended, then the three cheapest. Under the cards, "4 of 677"
  and a "More" button.
- "More" opens the next four cheapest, as often as asked: "8 of 677", and the page opens
  at the first new card. Nothing it opens is recommended. It needs no JavaScript: the
  page is drawn again with four more. A page holds at most 400 products (100 presses),
  so that a hand-typed address cannot ask for the whole feed at once.
- Fewer than four are shown as they are. "gas bbq with 4 burners" shows its 4 grills,
  "standing desk" 3 and "hp 26a toner" 2, where the old decision step showed an empty
  page.

**The Recommended**, as the owner ruled, and where a rule needed reading to be built:
- the middle product by price over the whole answer: of 677 laptops, the 339th. Of an
  even number, the cheaper of the two middle ones;
- a dearest product at least twice the next dearest is left out of the count, and
  again for the next one. It stays in the list;
- it carries an EAN/GTIN whose check digit agrees. If the middle product has none, the
  product nearest to it **in price** that has one, the cheaper of two equally near;
- it is priced above the cheapest and below the dearest that count, because its card
  says "Mid-priced for this category". On a short list the nearest product with a code
  can be the cheapest one, and calling that mid-priced would be false;
- with fewer than three products there is no middle, and so no Recommended. With no
  mid-priced product carrying a code there is none either, as the owner ruled. The
  note above the cards says which.

**The cards.**
- The Recommended: a "★ Recommended" badge and the owner's line, "Mid-priced for this
  category".
- The cheap cards: "Lowest price", or "Lowest price of N shops" when one product is sold
  by several. On this feed no product is in two shops.
- Every card states its place in the whole answer by price: "Cheapest of 677", "3rd
  cheapest of 677", and for the Recommended of "laptop" "341st cheapest of 677": the
  middle one, the 339th, carries no EAN, nor does the 340th, and the 341st is the
  nearest by price that does. Products at one price share a place. A product that is
  not new says so on the same line. This is the card's decision label, as concept
  section 8 has it ("Η φθηνότερη από τις διαθέσιμες"), and it is arithmetic over the
  prices, nothing else.
- "Lowest price" goes only on first-page cards priced at or below the Recommended. On a
  short list one of the three cheapest can be dearer than the Recommended (of four: the
  Recommended is the 2nd cheapest, and the 4th cheapest is on the page too), and calling
  it the lowest price would be false. It then carries no price label. The cards "More"
  opens carry none either, except "Lowest price of N shops".
- The note above the cards: "Sorted by price, lowest first, from the shops connected to
  PicWise. The Recommended is mid-priced for this category. Prices and stock are as the
  shops list them."

**The same product once.** Offers with the same EAN/GTIN (check digit agreeing; the UPC
and EAN forms of one code agree) or, without it, the same brand and MPN are one card, at
the cheapest offer. Only the `mpn` columns count: a model column names a range ("Galaxy
S24"), not one product. The card counts the shops the feed names, and an offer whose
shop is not named is not counted as another shop. The same shop listing one title at
one price twice is one card. Without either code nothing is joined.

**The search's other words now decide what is in the answer.** In price order the
cheapest product carrying a word comes first, so a loose match is the first card a buyer
sees. Measured and fixed on the 118 searches:
- a word is matched whole, with its singular or plural: "set" is not found in "settee",
  and "burners" finds "4 Burner";
- a count is read with its noun: "3 seater", "4 burners", "4 person". "4+1 Burner" counts
  as 4 burners;
- the words are read in the product's own title, type and brand. The description is a
  shop's marketing text, and a shop's shelf is shared and joins kinds: "Floor & Table
  Lamps" put table lamps under "floor lamp", "Kitchen & Dining" bar tables under "dining
  table", and "Garden Furniture Sets" single chairs under "rattan garden furniture set".
  The kind itself is still read from the shelf;
- a word typed just before the product's name that names a sub-kind ("floor lamp",
  "dining table", "standing desk", "bunk bed", "patio heater", "bathroom mirror") must
  stand before the kind's name in the title, with at most one word between: "Coffee
  Wood Effect" is a colour, not a coffee table. Brands, numbers, specs, the lexicon's
  preference words and words that say what a product has or is made of (wireless,
  bluetooth, LED, glass, wooden, the colours) are read anywhere in the title;
- "Set of 2" is how many come in the pack, not a set;
- every word is required while one product carries them all, and the answer is the
  products that do ("wireless headphones noise cancelling": 2 of 2). When none carries
  them all, specs, counts and preference words are kept while one product carries them:
  "power bank 20000mah for iphone" answers with the one 20000mAh power bank. Any other
  word is kept only if a full page carries it: "web cam for zoom calls" no longer
  answers with the one webcam that mentions a digital zoom. Every word left out is
  named on the page: "PicWise could not match: calls", or "Only some match: zoom (1 of
  76)";
- "24in" is read as 24 inches ("2 in 1" is not), and "pc screen" as a monitor.

**Item condition.** A buyer who asks for refurbished or used gets only products that are
not new, cheapest first, each card naming its condition ("refurbished" does not exclude a
used one); when the feed has none, the new ones, with the condition named as not matched.
New products no longer make up a four: fewer and right. Titles graded by a refurbisher,
"(Grade B - Average)", "(Grade A1 - Like New)", are now read as not new: 158 laptops,
desktops and televisions at Back to the Office, with an empty condition column, which
price order put first among laptops (a £125.99 "HP Stream ... (Grade B - Average)").

**Kinds split, because price order showed them.** The cheapest products of a broad kind
are its smallest or nearest things, so each of these led a search with the wrong product:
- a USB stick is its own kind: "hard drive" opened with 8 GB sticks at £7.99 (241
  products);
- a bookcase is its own kind, inside shelving: "bookcase" opened with a plant shelf, a
  CD rack and a TV shelf (97 products; 4 more are CD racks the shop files under
  bookcases);
- a fire pit is its own kind: through the "patio heaters" shelf fire pits were heaters,
  and "electric heater" listed a £29.99 fire pit (16 products);
- drive bay panels and brackets are not drives (9 products), which "hard drive" opened
  with once the sticks had gone.

**Measured on the third feed** (42,076 rows), with the same 118 English searches, every
first page read by hand:

| Outcome | After step 2 | After step 3 |
| --- | --- | --- |
| every card of the first page right | 97 | 100 |
| right kind, but a card misses a word of the search | 12 | 12 |
| a card of the wrong kind | 0 | 1 |
| nothing shown | 9 | 5 |

After step 2 a page meant four cards; now it holds one to four. Three searches show
fewer than four, all of them right: "wireless headphones noise cancelling" 2, "hp 26a
toner" 2 and "standing desk" 3.

- The four pages the old decision step left empty are answered: "3 seater sofa grey"
  with 16 grey three-seaters, "4 person camping tent" with 10 tents, "electric kettle
  1.7l" with 52 kettles and "gas bbq with 4 burners" with its 4 grills. The five still
  empty are misspellings with no product understood: "inc cartridge epson", "tnet",
  "lamb for bedroom" and "mirrer" offer the right "did you mean", "dsek for home office"
  none.
- The search's words narrow it now: "floor lamp" lists 126 floor lamps and no table lamp,
  "table lamp" 37, "patio heater" 14 patio heaters and no fire pit, "bunk bed for kids" 4
  kids' bunk beds, "pc screen 24in" 36 24-inch monitors. "ceiling fan with light" shows
  the feed's 5 handheld fans and says that none carries "ceiling" or "light".
- 98 of the 106 price-first pages have a Recommended. 4 have none because no mid-priced
  product carries a code ("notebook computer 15 inch" and the three fan searches), and 4
  because there is no middle price: two products, or three of which the dearest counts
  as extreme ("standing desk"), or four whose middle price is also the cheapest ("bunk
  bed for kids").
- The one wrong card: "toy" lists a £17.99 trampoline ladder, an accessory its shop
  files under toys.
- The twelve with a card that misses a word: a word inside the product's own name
  ("unlocked android phone" recommends an iPhone, "ipad 11 inch" lists Honor and Lenovo
  tablets, "android tablet for kids" recommends an iPad, "bluetooth earbuds" a headband
  headset, "bluetooth speaker" a Dell soundbar); "external" and "ssd" inside the drive
  kind ("external hard drive 2tb" recommends an internal drive, "portable ssd 1tb" lists
  portable hard drives); "patio set" answered with sets of chairs; the "Kettle & 2 Slice
  Toaster Set" as the Recommended of the three kettle searches; and a TV shelf among
  "shelving unit".
- Speed: a median of 4.0 s a search with the tests running beside it, 24 s for the first
  search after a cold start. Unchanged by this step.

**What step 3 does not fix:**
- Searches whose product is not understood ("cat tree", "dog crate", "kids ride on car",
  "memory card 128gb", "network switch", "lenovo thinkpad 16gb ram") still show four
  cards by the earlier rules: relevance, price zones and the old decision step. That is
  part 3b, and it needs the strict kind test the understood searches have.
- A word inside the product's own name does not narrow it. "android phone" and "ipad"
  are names of smartphone and tablet, so "unlocked android phone" recommends an
  iPhone and "ipad 11 inch" lists Honor and Lenovo tablets; "gas bbq" lists charcoal
  grills too.
- A word after "for" narrows like any other: "printer for home" shows the 4 Epson
  "Expression Home" printers, "4 of 4", not the 260 printers.
- £0.99 headsets open "headphones", and a £1,344,000 monitor stays at the end of its
  list (the extreme rule keeps it out of the middle). A check on implausible prices is
  still a proposal.
- A "Kettle & 2 Slice Toaster Set" is read as a kettle, and it is the Recommended for
  "kettle".
- Without a Recommended every first-page card says "Lowest price", on a short list even
  the dearest: "standing desk" shows a £630.99 desk as "Lowest price" and "3rd cheapest
  of 3". Put to the owner.
- Speed is unchanged: about 4 s a search on this feed, about 25 s for the first
  after a cold start.
- The search box still says "See the 4 best products before you buy", and "What is
  PicWise?" still says it "recommends the 4 best matches". Neither is true of price
  first; the wording is the owner's call.
- `src/picwise_contracts/models.py` still rejects more than 4 `more_choices`. The live
  page does not use that model; the model follows when the contract objects are next
  changed.

Tests: `tests/test_picwise_price_first.py` is new (36 tests): the same product once (one
GTIN in two shops, its UPC and EAN forms, brand and MPN but not a model name, no code no
join, a wrong check digit, one currency), the Recommended (the 23rd of 45, the owner's
£100, £150 and £200, an extreme price once and twice, an even count, the nearest by price
and the cheaper on a tie, never the cheapest or the dearest, no code, too few), graded
titles, the `shown` parameter (a typed "²" or a number of 5,000 digits opens the first
page or the last and breaks nothing), and the deployed page (the first page, "More" to
the end, no product twice, "2 of 2", a dearer card without "Lowest price", no barcode,
two shops, the search's words, a word named when dropped, whole words, description
words, a spec kept when another word fails, a word one product happens to carry, a
dropped word that every product shown carries after all is not reported, graded
laptops). `tests/test_picwise_strict_kind_reading.py` gains 4 tests for the split kinds.
`tests/test_picwise_see_more_second_four.py` is removed: its rule is superseded, and its
guarantees for "More" (nothing in it recommended, no product twice, no button with
nothing behind it) are in the new module. 18 other modules were changed to the owner's
price-first rules, each change saying why in the test. The three shared fixture feeds
now carry a valid EAN on every row, as most real products do, so that the tests reach
the Recommended.

Of 238 test modules, 234 pass. The other four fail the same way on the unchanged code
(checked in a clean worktree of `3ca88bc`): `test_picwise_query_understanding` (two
"machine" tests), `test_picwise_canonical_vocabulary_registry_stage2`,
`test_picwise_search_index_generated_blind_stage4`, and
`test_picwise_search_index_blind_evaluation_stage6a`, which imports none of the changed
modules, takes 43 minutes, and fails one of its 13 tests ("amazon" and "galaxy" missing
from its broad terms). The misspelling benchmark stays at 93.9% (1 wrong, 42 not
understood). Its "pass" now asks that every card be the kind expected, and no longer
four cards and a Recommended, because fewer than four are shown as they are.

## The owner's additions, 2026-10-16

Decided by the owner after the understanding test, each with what it means in
practice:

1. **Search suggestions as the buyer types.** The likely word appears in faint letters
   and fills in on a tap; below the box, word suggestions from the first letter that
   narrow with each letter ("l" -> laptop, lamp). In practice:
   - the suggestions come from PicWise's own vocabulary (the 278 kinds in English and
     Greek, plus brands and words found in the feeds), and only words that return
     products are offered;
   - the list is loaded with the page, so a keystroke costs no request to the server;
   - it needs JavaScript, which today's pages do not use.
2. **A microphone in the search box.** The buyer speaks and the words are written. In
   practice:
   - it uses the browser's own speech recognition, which works in Chrome, Edge and
     Safari but not Firefox, and needs no key and costs nothing;
   - in Chrome the audio goes to Google's speech service, so the privacy note must say
     so;
   - phone keyboards already have dictation, so the button helps desktop most;
   - the spoken words then go through the same misspelling understanding as typed
     ones.
3. **Availability is what the feed says** (confirmed).
4. **Many more shops at once.** Apply to every Awin programme that has a product feed,
   accept the shops that invite PicWise, and add other networks later. In practice:
   - for the UK and US the main other networks are CJ, Rakuten Advertising and Impact,
     plus Webgains in the UK;
   - each network has its own feed format, so each needs its own reader. Amazon stays
     removed;
   - the bigger change is engineering. Today every cold start downloads and parses the
     whole feed, and a search took about 4 s on 42,076 products, so many shops need a
     store refreshed daily and a search index;
   - a store large enough for millions of products is likely a paid plan, to be costed
     before anything is created.
5. **Extreme top prices do not count for the Recommended** (rule 7 above). The reading
   "at least twice, and again for the next one, still listed" was stated to the owner.
   With the median one extreme price moves the middle by half a place, so the rule
   matters most on short lists and against feed errors such as the £1,344,000 monitor.
   That monitor would still show at the end of the list, so a price sanity check
   remains proposed.
6. **Services get no Recommended in this phase:** insurance, banking, energy and
   software, unless a mechanism is found that can decide what is the better deal.
   PicWise rests on volume; it is a shopping search.
7. **Trends below the search box:** what people look for today, a tap fills the box.
   They must state only what is known (ANTI_FAKE):
   - at first, seasonal picks labelled as such;
   - then the most frequent searches on PicWise, which needs the query log stored (a
     Supabase project, the owner's yes first);
   - "what people buy" only from real purchase data, such as PicWise's own sales in
     Awin's reports.
8. **Why volume pays.** A buyer who reaches a shop through PicWise gets its cookie.
   Anything they buy there within the cookie's life earns commission, the product they
   saw or any other. The cookie's length and what counts are set per programme in its
   terms.

9. **An app, not only a website** (owner, the same day). PicWise will install on phones
   and later go to the Play Store. In practice:
   - the website becomes installable as an app, and the Play Store version is the same
     site in an Android wrapper, with one codebase;
   - links to shops must open in the phone's browser, so the shop's cookie is set where
     the buyer buys and the commission is not lost;
   - the Play Store needs the owner's Play Console account, a privacy page (the mic and
     cookies must be described there) and a verification file on the domain;
   - Apple's store is stricter with sites in a wrapper and is not planned now.
10. **A scanning screen while a search runs** (owner, the same day): "searching N shops,
    M products, found these, cross-checking, sending". It appears within 1.5 s, and the
    results may take about 4 s behind it. Written into the concept (section 18) and
    PROJECT_RULES section 9 under two conditions: the screen states only true facts,
    and results are never held back on purpose. In practice:
    - it makes today's 4 s acceptable without making the search faster;
    - it cannot cover growth. Every search reads every product, so the time grows with
      the catalogue: 4 s at 42,076 products, tens of seconds at hundreds of thousands;
    - every cold start downloads and parses the whole feed (10 s here), and the first
      search after it took 20 s;
    - the answer to both is data prepared once a day, such as an index by kind of
      product. That need not cost anything: a scheduled job can build it and store it
      as files. A paid database comes in only if it outgrows free limits.

**Also decided on 2026-10-16, for step 3:**
- no Recommended when no product has an EAN/GTIN;
- fewer than four results are shown as they are;
- brand + MPN is the same product.

All three are recorded in rules 5 and 7. The owner then accepted the two remaining
proposals («Οκ»): the three cheapest cards say "Lowest price" ("Lowest price of N
shops" when offers are joined), and the line under the Recommended is "Mid-priced for
this category". Nothing in "Open, for the owner" is left.

**Build order proposed to the owner (updated the same day).** The owner restated the
extreme-price rule for step 3 in their own words («όταν το ακριβότερο είναι δύο φορές
ακριβότερο από το προηγούμενο φθηνότερο να εξαιρείται από το μέσο όρο»), which matches
the reading above, and did not object to the order. Steps 1 to 3 were built the same
day: see "Step 1 built", "Step 2 built" and "Step 3 built". Next is step 4, the search
page.
1. the strict kind test;
2. English over greeklish ("patio");
3. the price-first engine: cheapest first, the median Recommended with the
   extreme-price rule, More, the counter, and the same-product join;
4. the search page in the browser: the scanning screen, suggestions as the buyer
   types, and the microphone;
5. data prepared once a day, for fast cold starts and for many shops. Going live
   needs steps 1-5;
6. trends;
7. the app, installable first and then in the Play Store;
8. other networks.

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
