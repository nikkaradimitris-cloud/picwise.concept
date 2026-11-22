# PicWise: the checks' rules

Written 2026-11-21 (evening, Athens) as task 4 of the work split by model (Claude Fable
5.2; `docs/picwise_session_handoff.md`), as rules only. Built in task 5 (section 15),
looked at and mended in task 7 (sections 16 and 17). **The owner's «Ανέβασε», 2026-11-22
(12:50 Athens): `data/checks_switch.json` is true from that day's commit, and the checks cut
from the first night after its deployment** (`PROGRESS.md` says how the deployment went).

Each rule names whose it is:

- **Owner**: his words, with the day.
- **Proposed**: written here so that his decisions work, told to him on 21/11, his yes
  still to come (section 13 lists them). A proposed rule is built as written and is his to
  change.

## Σύνοψη για τον ιδιοκτήτη

- Κάθε προϊόν ελέγχεται στο site του καταστήματός του: ανοίγει η σελίδα του, έχει απόθεμα,
  ποια τιμή γράφει, φορτώνει η φωτογραφία του. Το link της Awin δεν πατιέται ποτέ.
- Ό,τι αποτύχει κόβεται το ίδιο βράδυ, για οποιονδήποτε λόγο (απόφασή σου, 21/11).
  Ξαναρωτιέται το επόμενο βράδυ και γυρίζει μόλις περάσει.
- Όταν η σελίδα του καταστήματος γράφει άλλη τιμή, η κάρτα δείχνει την τιμή της σελίδας
  (απόφασή σου). Πρώτα ο αναγνώστης αποδεικνύει ότι διαβάζει σωστά το κατάστημα: πρέπει να
  συμφωνεί με το feed στα περισσότερα προϊόντα του.
- Κατάστημα που δεν μπορεί να ελεγχθεί (μπλοκάρει το bot, ή η σελίδα του δεν διαβάζεται)
  έχει 3 μέρες. Μετά βγαίνει ολόκληρο και γυρίζει μόλις ελεγχθεί (απόφασή σου, 22/11· στις
  21/11 ήταν 14 μέρες). Το bot ελέγχει όλη μέρα (απόφασή σου, 22/11), ώστε κανένα προϊόν να
  μη μένει ανέλεγκτο πάνω από 3 μέρες.
- Κατάστημα που απορρίπτει την αίτηση στην Awin βγαίνει (απόφασή σου). Όσα δεν έχουν
  απαντήσει ακόμα μένουν.
- Το InStock UK ελέγχεται όπως όλα τα καταστήματα (απόφασή σου).
- Δεν υπάρχουν δοκιμαστικά βράδια: ο έλεγχος κόβει από το πρώτο βράδυ (απόφασή σου). Γι'
  αυτό το φρένο είναι αυστηρό. Όταν ένα κατάστημα πάει να χάσει σε ένα βράδυ πάνω από το
  1/4 όσων ελέγχθηκαν, τα κοψίματά του περιμένουν δεύτερη ματιά. Όταν το ίδιο συμβεί σε
  πολλά καταστήματα μαζί, εκείνο το βράδυ δεν κόβεται τίποτα. Και ένας διακόπτης φέρνει
  πίσω όλα τα προϊόντα, με τη λέξη σου.
- Νέο προϊόν μπαίνει μόνο αφού περάσει τον έλεγχο. Τη θέση όσων κόπηκαν την παίρνουν
  προϊόντα που πέρασαν.
- Προϊόν που το bot δεν πρόλαβε να ελέγξει μέσα στις 3 μέρες δεν φαίνεται μέχρι να ελεγχθεί.
  Δεν «κόβεται»: περιμένει στη σειρά, ρωτιέται την επόμενη μέρα και γυρίζει μόλις περάσει.
- Οι δύο κανόνες που σου είχα προτείνει ισχύουν από 22/11, με το «ναι» σου: (α) προϊόν από
  feed παλαιότερο των 7 ημερών φαίνεται μόνο αν το bot διάβασε το site του τις τελευταίες 3
  μέρες· (β) κατάστημα που η Awin το έχει σε αναστολή, κλειστό ή offline βγαίνει. Το
  κατάστημα που απορρίπτει την αίτησή μας βγαίνει έτσι κι αλλιώς (απόφασή σου).
- Dean Morris Cards: τα προϊόντα του δεν υπάρχουν πια στο site του· κόβονται (απόφασή σου,
  22/11: «Κόψε τα») και γυρίζουν αν ξαναβρεθούν.
- Το AI δίνει σε κάθε προϊόν κατηγορία μία φορά. Όποιο δεν μπαίνει σε κατηγορία βγαίνει, και
  νέο προϊόν μπαίνει μόνο αφού πάρει κατηγορία (απόφασή σου, 21/11).
- Κατάστημα με «φράχτη» για ρομπότ δεν το παρακάμπτουμε. Σου ετοιμάζεται ένα γράμμα για να του
  το στείλεις μέσω Awin, ώστε να αφήσει το bot μας.
- Κάθε μέρα το email σου έχει μία γραμμή με τους αριθμούς των ελέγχων.
- **Πόσα προϊόντα δείχνει ένα κατάστημα (απόφασή σου, 22/11· δεν έχει χτιστεί).** Ό,τι
  προλαβαίνει να σκανάρει το bot σε ένα κατάστημα περνάει στο site: σε ένα 15.000, σε άλλο
  5.000. Ανώτατο όριο 20.000, για κατάστημα που απαντά γρήγορα. Δεν μπαίνει ξεχωριστό
  πλαφόν ανά κατάστημα («μόνο όσα έχουν σκανναριστεί περνάνε»· «τελειώσαμε με αυτό»). Σήμερα
  πάνω από 20.000 έχουν 4 καταστήματα: κόβονται τουλάχιστον 186.900 προϊόντα. Ποια προϊόντα
  κρατά ένα κατάστημα (η λέξη σου, 22/11: «Με τις 3 αλλαγές»): πρώτα τα είδη με τα λίγα
  προϊόντα· μετά ό,τι πουλά φθηνότερα από όσα δείχνει το site· μετά τα υπόλοιπα, πρώτα όσα
  έχουν είδος· ό,τι το κρατά φθηνότερα άλλο κατάστημα μπαίνει τελευταίο. Το bot φτιάχνεται
  να δουλεύει σε περισσότερους επεξεργαστές μαζί («Ναι, μαζί»). Ο κανόνας: ενότητα 19.

## 1. What the checks are for, and what they rest on

The owner, 21/11: some buttons do not lead to the shop, some prices differ from the shop's,
some photos never load; he cannot know the whole feed or every shop, so the check must
remove what fails, not count it. What was measured the same day, on the server, read-only:

- **The site's own side of the button is sound.** 389,735 products, 389,735 ids, none
  shared; all 95 first cards of his own 24 searches find their product and leave through
  an Awin link (run 44909213170). What Awin does with the click no machine may see.
- **Shops' pages**, of those 95: 57 the same product in stock; 6 the same product named
  with its size or colour; 4 sold out on the shop's site while shown; 22 with no product a
  machine reads (Tooled Up, Plusshop UK, Tyres UK, Tirendo UK, MoreThisWay); Aosom UK's
  robots.txt answers 403 to the bot.
- **Prices**, 69 read: 63 the same; pennies apart at PCHUB.UK, £1 at Back to the Office,
  +9% at InStock UK, another size at Starlight Beds. InStock UK alone (run 44904597222): of
  12 products 1 gone (404); of 11 found, 5 the same price, 5 dearer on its site by the
  same 9%, 1 another variant.
- **Photos**: all 95 load in under a second. The night's check holds 6,599 gone (404, 410).
- **Awin** (runs 44914493498, 44914719475): the account is joined to 8 of the catalogue's
  160 shops (16.9% of the products), not joined to 150 (83.1%), 2 in no list; no shop of
  the catalogue is rejected or pending today; 35 shops' feeds were last imported over 7
  days ago (12,684 products).

Three things no check here ever does (owner's standing rules): press an Awin link or the
site's own `/out/...`; claim that a click was tracked or a commission earned; print or keep
in a public place an address, a feed link, a key or a server name.

## 2. The owner's decisions

### 2.1 His plan of 21/11 (kept whole in the handoff)

- «Ποιότητα πάνω από ποσότητα. Όποιο προϊόν δεν περνά τον έλεγχο κόβεται, και όποιο
  κατάστημα δεν δέχεται το bot βγαίνει ολόκληρο. Τη θέση τους μέσα στο όριο των 12.000 την
  παίρνουν προϊόντα που πέρασαν τον έλεγχο.»
- «Το AI ρωτιέται μία φορά για την κατηγορία κάθε προϊόντος. Όποιο προϊόν δεν μπαίνει σε
  κατηγορία βγαίνει.»
- «Δεν γίνεται σκανάρισμα ούτε μέτρηση πριν: φτιάχνουμε τους μηχανισμούς και τους
  ανεβάζουμε. Δεν υπάρχει ημερήσιο όριο κόστους, μόνο ένα φρένο για λάθη.»
- «Δεν πατιούνται ποτέ αυτόματα τα links του Awin, για να μη γίνονται ψεύτικα κλικ. Η
  διεύθυνση του καταστήματος διαβάζεται μέσα από το link.»
- Every product's link checked first, then each new product before it enters, and some old
  ones again each night; a night that cuts unusually many stops the removal; the checks use
  the barcode and every other code that names a product.
- 21/11, 16:51, of the 150 shops the account is not joined to: «Θα κάνουμε αιτήματα να
  δούμε ποια από αυτά θα μας εγκρίνουν».

### 2.2 His six answers of 21/11 (evening), each to a question that put his first word beside another

1. A shop the bot cannot check (it blocks the bot, or its page is not read by a machine):
   **«Προθεσμία 14 μέρες»**. He writes to a shop that blocks through Awin; a way to read
   an unread page is made; still unchecked after 14 days, it leaves whole and comes back
   once checked. (His first word: out at once.) **Changed 22/11** (00:13: «15 μέρες θα
   βλέπουνε οι χρήστες σαββούρα είναι πάρα πολύ!»; then, asked: out from the first night,
   or in 3 days): **«Σε 3 μέρες»**, and the bot asks all day (**«Ναι, όλη μέρα»**), and
   nothing goes on the site before the end (**«Όχι, όλα μαζί στο τέλος»**: the bot is not
   deployed ahead of the rest).
2. A page's price other than the card's: **«Δείχνουμε την τιμή της σελίδας»**. (His first
   word: the product is cut.)
3. A page or a photo that does not answer one night: **«Αμέσως, για κάθε λόγο»**: the
   product is cut that night. (Proposed and not taken: on the third night in a row.)
4. Three first nights of report only: **«Όχι, κόβει από το πρώτο βράδυ»**. (Proposed and
   not taken: three nights that say what they would cut.)
5. InStock UK, never asked by the bot since 26/10: **«Ναι, να ελέγχεται»**, as every shop.
6. A shop that rejects the account's application at Awin: **«Βγαίνουν»**, its products
   leave.

Answers 3 and 4 leave one safeguard, the one he named: the brake (section 7). It is
written to carry that weight.

## 3. Words

- **Product**: one row of a feed, known from night to night by its shop and its id
  (`catalogue_memory.product_key`). A card may join several rows of one product page
  (`search_selection._join_variants`); each row is checked for itself.
- **Check**: one question about one product on one night: its page, its stock, its price,
  its photo, its category. A shop has its own: can it be checked, Awin, its feed's age.
- **Verdict**: `passed`; `failed`, with its reason; or `not checked` (never asked yet, or
  its shop cannot be checked).
- **Decided**: a check that ended `passed` or `failed`.
- **Cut**: a failed product is no product a card can show: not shown, counted, recommended
  or kept by the cap. **At once** means from the catalogue prepared that same night (the
  checks end before the preparation of 04:17 UTC); for a photo, from the list the site
  reads within a minute of the night's photo check.
- **Held**: failed, but kept as it was by a brake until a second look.
- **Night**: one round of checks, ending before a night's preparation.

## 4. How a shop is asked

1. **Only the shop's own address**, read as text from the row
   (`shop_catalogue.own_address`: the address its Awin link carries, else its
   `merchant_deep_link`). Never an Awin link, never the site's `/out/...` (owner). A
   redirect to another site is not followed.
2. **Its robots.txt first**, each night; only what that allows; its crawl-delay when
   longer than the bot's own pause, up to 60 s.
3. **One request at a time a shop, 3 seconds apart**, many shops at once, under the bot's
   own name (`PicWiseBot/…`, with the site's address). A 429, or a 503 that says when to
   come back, ends that shop's night: what was not asked is not failed.
4. **Never around a block**: no other name, no changing addresses, no CAPTCHA solved.
5. **Readers, the cheapest first:**
   1. *Shopify's catalogue* (`/products.json`, 250 products a request; by collections
      over 25,000): per product that it is there and its type; per variant its id, SKU,
      price and whether it can be bought. A product's own `.js` (one request) adds each
      variant's barcode, asked only where a code is needed.
   2. *The product's page, as HTML*: its schema.org Product and Offer (JSON-LD, then
      microdata), then the `product:` and `og:` tags: availability, price, currency, SKU,
      GTIN, MPN.
   3. *A shop's recipe*: where 1 and 2 read nothing on a shop's pages, the AI is asked
      once for that shop where its HTML writes the price, the stock and the codes; code
      then reads by the recipe, and the AI is asked again only when the recipe stops
      reading (owner's plan, step 4: by code, by the AI only where code cannot).
   4. Nothing else: no page drawn in a browser, no guess from words such as "Add to
      basket". A shop none of these reads cannot be checked (5.6).
6. **The codes** (owner, 21/11: the barcode and every code that names a product): a GTIN
   whose check digit agrees (`product_identity.valid_gtin`), a brand with its part number
   (`product_identity.same_product_key`), a shop's own SKU, a Shopify variant's id. Like
   is compared with like only. An IMEI is one handset's own number, not a product's: no
   feed and no shop page gives one.
7. **The server's room**: the checks stop before the preparation starts and never run
   beside it (the server has 22.9 GB; the preparation peaks at 14.9 GB, the site at up to
   8.3 GB). The bot asks all day (owner, 22/11), from 05:30 to 03:05 UTC: the round of the
   largest shop asked a page at a time fits in 3 days (Tooled Up's 68,508 pages at 3 s are
   about 57 hours; InStock UK's products past its catalogue's 25,000, about 64).

## 5. The verdicts

### 5.1 The page (the button's far end)

| What the shop's site answers at the product's own address | Verdict | Reason |
|---|---|---|
| 200 with the product read on it; or, in a Shopify shop, the product found in the catalogue read that night | passed | |
| 404 or 410 | failed | `gone` |
| nothing: a timeout, a connection refused or reset, a 5xx; asked once more at the end of the shop's round | failed | `no answer` |
| a redirect to the home page, a category, a collection or a search; or to another product whose codes differ or, with no code on both sides, whose title is not alike | failed | `moved` |
| 200 with no product on it, in a shop whose reader reads at least 9 in 10 of its other pages that night | failed | `not a product page` |
| the page gives a GTIN for every one of its variants and the row's own valid GTIN is none of them | failed | `another product` |
| on our own side: the product's id is one another product of the catalogue shares (the site's button finds a product by its id alone; none on 21/11) | failed | `id shared` |
| 401, 403, 429, a challenge or CAPTCHA page; robots.txt says no; no reader reads the shop | not checked | the shop's matter (5.6) |

- A product missing from a Shopify catalogue read whole is asked at its own address
  before it is called gone.
- **A title alone never fails a product** at its own address: 6 of the 95 cards of 21/11
  had a title under 60% alike and were the same product (a size or a colour in the name).
  A title is compared only after a redirect to another product's address.
- A redirect to another address of the same product (the shop renamed it; the codes or the
  variant's id agree) is passed.
- What agreed is kept with the verdict: `by variant id`, `by code`, or `by address` (there
  was nothing to compare).

### 5.2 Stock

Owner, 2026-11-12 (`PROJECT_RULES.md` §5), unchanged: the shop's own site, read within the
last 3 days, decides a product's stock before the feed, either way; with no reading of the
last 3 days the feed decides. Added here:

- In stock is a state that lets the buyer order now for delivery. Out of stock, sold out,
  discontinued, pre-order, back-order and "in store only" are not in stock, where a page
  says so (Proposed, as the bot's design of 23/10 had it,
  `docs/PICWISE_SERVER_ARCHITECTURE.md` 3.5; Shopify's catalogue says only whether a
  variant can be bought).
- A product hidden on the site's "sold out" comes back the night the site says in stock.
  It is no failure and trips no brake of section 7.2.
- A product the site called sold out while its feed calls it in stock is asked again
  within the 3 days, before the reading lapses, so that it does not come back on the
  feed's word between two readings (Proposed).
- A reader other than Shopify's catalogue proves itself in a shop first (7.5).

### 5.3 Price

Owner, 21/11: **«Δείχνουμε την τιμή της σελίδας»**. No price is worked out: the page's
price is the shop's own, as the feed's is.

1. **A reading belongs to a row only when it is tied to it.** In a Shopify shop: the
   variant the row's address names, else the variant whose SKU or barcode is the row's,
   else the product's one price (one variant, or every variant at one price). On a page:
   the offer whose SKU, GTIN or MPN is the row's, else the page's one price when the feed
   has one row for that address or all its rows for it at one price. In pounds only.
2. **A reading not tied changes nothing**: the row keeps its feed's price and is not
   failed. A product with sizes shows, on its page, the price of the size the shop puts
   first (Starlight Beds, 21/11: £84.99 on the card for one size, £54.99 on the page for
   its smallest).
3. **A tied reading other than the feed's price is the card's price** (the feed's price
   being the one the card shows today: its sale price where one is in force,
   `normalization.sale_price_in_force`), read as the shop's own price by everything that
   reads a price: the order, "More", the counter, "Lowest price", the price bar, the
   Recommended, the one shop shown for a product several sell.
4. **It stands until the product's next reading.** When the feed's price for the row
   changes, the reading is old: the row is asked again before any product never asked
   (section 10) and shows its feed's new price until then.
5. **The price's history starts again the night a row's price changes its source** (feed
   to site, or back), as it did the night sale prices were first read (`catalogue_memory`,
   `sale_prices_read_from`): no ▲ or ▼ is told for a change of source (`PROJECT_RULES.md`
   §4: no fake savings). (Proposed.)
6. **The reader proves itself in a shop before it changes a price there, and a price far
   apart is no price** (7.5). (Proposed.)

### 5.4 The photo

Owner, 21/11: **«Αμέσως, για κάθε λόγο»**. Until these rules are deployed the rule of
2026-11-01 stands: only 404 and 410 call a photo gone.

- passed: 200 with an image and a body.
- failed, that night: 404, 410; no answer or a 5xx (asked once more at the end of the
  night's run); an answer that is no image; an empty one. The product is cut by the list
  the site reads (`product_photos`), as today.
- A 429 is our own pace: asked again later in the run, more slowly; still 429, not asked,
  not failed.
- Refused (401, 403) on at least 9 in 10 of a shop's photos asked that night (at least
  20): the shop's photo host refuses the checker, which is not each photo's failure. Those
  photos are `not checked`, the shop is named in the report, and nothing of it is cut for
  that: in the visitor's browser a card whose photo fails, or has not come 10 s after it is
  in view, is never seen (deployed 21/11), so the browser is the judge. The owner's answer
  on a shop that cannot be checked was about its pages; whether a shop whose photos alone
  cannot be checked leaves is his to say (section 13). A refusal on fewer photos is a
  failure like any other.
- Asked again: the next night after any failure but 404 and 410; those after 7 days (as
  today). A photo that answers again is back on the next list.

### 5.5 The category

Owner, 21/11: the AI is asked once for each product's category; a product that gets none
is out, never forced in.

- passed: the AI gave the product a line of Google's taxonomy (`ai_shelves`); a line it
  gives when it slips (`SLIP_LINES`) is no line.
- failed, `no category`: "no line fits", refused, or a slip. Cut.
- Asked once for the product's own words (`picwise_ai.shelves.ask_key`: its title less
  sizes and colours, its brand, its shop's category words). A product whose words change
  is a new question. All are asked again only when the question itself changes (its
  wording, the taxonomy, the model), which is a new version of it (Proposed: «μία φορά»
  read as once for each question).
- not asked yet: a new product waits for its answer (section 9); one the catalogue already
  holds stays until asked.
- **A product with a line but no PicWise kind is not cut here**: the 264,642 products of
  no kind are task 9.
- How many products have no line today is not known: read in the look before the
  «ανέβασε» (task 7).

### 5.6 The shop

1. **Left out by the owner** (`eligibility.LEFT_OUT_SHOPS`): as today; only his word.
2. **A shop that cannot be checked** (owner, 22/11: 3 days; 14 on 21/11). It is so on a night when: its
   rows give no address of its own (an Awin link alone, which is never pressed); or its
   robots.txt disallows its product pages or answers 401 or 403; or it asks for a
   crawl-delay over 60 s; or at least 9 in 10 of the round's requests to it are refused
   (401, 403, 429, a challenge page); or no reader reads a product on at least 9 in 10 of
   its pages that answer 200 (at least 10 asked).
   - Day 1 is the first such night. The next morning's report names the shop and why, with
     a letter for the owner to send it through Awin when it refuses the bot (the bot's
     name, what it reads, its pace); for an unread page a recipe is made (4.5.3).
   - Meanwhile its products stay as they are and none new enters.
   - On day 4, still so: every product of it is cut (`shop cannot be checked`).
   - Each night it is asked again (its robots.txt, then up to 5 of its pages). The first
     night a product is read on it, its count ends; if it was out, its products come back
     as they pass, as new products do.
   - The count starts afresh only after 7 nights in a row of being checked; a shop that
     falls back sooner goes on from the day it had reached. (Proposed.)
   - Today: Aosom UK refuses (10,052 products; the account is joined to it); Tooled Up
     (68,508), Plusshop UK, Tyres UK, Tirendo UK and MoreThisWay showed pages no reader
     reads. Their days count from the first night of the built checks.
3. **Awin**, read each night from its API (as `deployment/server/print_programmes.py`
   reads it), never by a click:
   - joined: in.
   - rejected: out from that night (owner, 21/11: «Βγαίνουν»); back the night it is joined.
   - suspended, or in none of Awin's lists (a programme closed): out likewise (Proposed:
     the same reason, no partnership; 2 shops, 28 products on 21/11). Built off until his
     yes (22/11, task 7; `data/checks_owner_words.json`, `awin_closed_out`). **His yes,
     22/11, 12:50 Athens: «Ναι, να βγαίνει»: on** (that day usmile, 28 products).
   - not joined, or pending: in (owner, 21/11, 16:51: the applications first). The button
     of a shop the account is not joined to opens the shop (the owner's tap on InStock UK,
     22/11; section 13, 1).
   - Awin's link status `offline` (advertisers upgraded from ShareASale): Awin sends the
     shop's links to the publisher's fallback address, or to its page "This link is
     inactive". The shop is out while offline, back the night it is online (Proposed: the
     button would not reach the shop; **on by his yes of 22/11**, with the line above). The
     owner sets a fallback address in his Awin profile.
   - A night Awin's API does not answer changes nothing: the last reading stands, and
     after 7 such nights the report says so.
   - A reading of Awin (relationships, link status, the feeds' ages) that would put out,
     in one night, more than 3 shops, or shops holding over 5% of the products shown,
     changes nothing that night: it is reported, and waits for the owner's word (Proposed:
     an answer of Awin's cut short must not empty the site; several rejections arriving
     together are one word of his).
4. **Its feed's age** (Proposed): Awin's feed list gives each feed's last import. Over 7
   days old, the feed's word on stock and price is old: a product of it is shown only with
   a reading of its shop's own site of the last 3 nights. From the end of the shop's first
   round (9.3). A feed the list does not show has no known age and is not judged by it. On
   21/11: 35 shops, 12,684 products (MoreThisWay since 16/09). Built off until his yes
   (22/11, task 7; `data/checks_owner_words.json`, `old_feed_rule`). **His yes, 22/11,
   12:50 Athens: «Ναι»: on** (told with the question: how many products it hides was not
   known; proposed and not taken: to count first). Such a product is not cut: it waits as
   9.3 says, and a candidate of such a shop enters only with a reading of that night. The
   reading is the latest of the price's and the stock's.

## 6. What is cut, and when

| What | When | Whose |
|---|---|---|
| A page that fails, for any reason (5.1) | that night | Owner, 21/11 |
| A photo that fails, for any reason (5.4) | that night | Owner, 21/11 |
| A product with no category (5.5) | that night | Owner, 21/11 |
| A product sold out on its shop's site (5.2) | that night, hidden as out of stock | Owner, 12/11 |
| A price far apart (7.5) | that night | Proposed |
| A shop rejected at Awin | that night | Owner, 21/11 |
| A shop suspended, closed or offline at Awin | that night | Owner, 22/11 (Proposed until then) |
| A shop that cannot be checked | on its day 4 | Owner, 22/11 |
| A product of an old feed with no fresh reading of its shop | not shown, from the end of its shop's first round | Owner, 22/11 (Proposed until then) |
| A product never asked, or not passed in 30 nights (9.3) | not shown until checked, from the end of its shop's first round; it waits, it is not cut | Owner, 22/11 |
| A new product never asked | it does not enter | Owner, 21/11 |

Not cut: a price that differs (the page's price is shown); a price not tied to its row; a
title unlike the page's; a product of a shop not joined or pending at Awin; a product with
a category and no PicWise kind; a product asked of a shop that refused that night.

## 7. The brakes

Owner, 21/11: «μόνο ένα φρένο για λάθη»; a night that cuts unusually many stops the
removal; no nights of report only. So the brake is what stands between a fault of ours and
the catalogue. Its numbers are Proposed.

### 7.1 What is no failure

- A refusal (401, 403, 429, a challenge) is the shop's matter (5.6), never a product's
  failure.
- A product not asked is not failed.
- **A round that is ours to blame records nothing**: when fewer than half of the shops
  asked in a round gave any answer at all, the fault is on our side (the server's
  network). The report says so first.

### 7.2 A shop's night

Of a shop's products decided on a night (at least 20), when more than a quarter fail that
were not failed the night before, the shop's brake holds: those products are `held`, kept
as they were, and asked again the next night before anything else.

- What fails again is cut on that second night; what passes, passes.
- **Only where the shop has at least 20 passes on record**, that night or before: they
  show that the reader reads that shop. A shop with fewer stays held until a look finds
  whose the failures are, and the owner's word on it («κόψε»): nothing yet shows that
  what failed there is the shop's and not ours.
- Photos are counted apart, by the same numbers.

### 7.3 A kind's night

When a night's new cuts would take more than a quarter of the products a kind shows (a
part as the cap reads it, `catalogue_cap.part_of`, with at least 40 shown), that kind's new
cuts are held one night and asked again first; what fails again is cut. A search keeps its
products while a second look runs.

### 7.4 The whole night

When the brake of 7.2 holds for more than a third of the shops decided that night (at
least 6 shops), or the night's new cuts pass 10% of the products shown, **nothing new is
cut that night**, by any check: all of it is held, the report says so first, and the next
night asks the held again. Two such nights running, the cutting stays stopped until a look
and the owner's word. A shop that leaves whole under 5.6 is not counted here: its day 4
is in the report days before, and Awin's readings have their own stop (5.6.3).

### 7.5 A reader proves itself; a price far apart

- In a shop, a reader's word on price, and on stock for a reader other than Shopify's
  catalogue, changes the site only once it is proven there: of its tied readings of the
  last 7 nights (at least 20), at least 7 in 10 say what the feed says (the price to the
  penny; the same stock). A reader that reads the right place agrees with the feed on most
  products; only then may it overrule the feed on the rest.
- Not proven: the feed's price and stock stand for that shop. The report gives the share
  that agrees and the commonest ratio between the two prices (1.2 is VAT; 100 is pence;
  1.09 is InStock UK's on 21/11, 5 of 10). A look names the cause and the shop is then set
  by hand, in a list kept in the repo with its date and reason (as
  `shop_words.LEARNED_TYPES` is): the site's prices stand there, or the reader is mended.
- **Far apart**: a tied reading under half of the feed's price or over twice it is no
  price to show. The product is failed, `price far apart`, cut that night and asked again
  the next: one of the shop's two words is badly wrong.

### 7.6 The AI's cost

Owner: no daily limit of cost, a brake for errors. The checks' own calls to the AI (the
shops' recipes, the category of new products) stop for the night at $10, far above a
night's need (a recipe is a few calls a shop, once): a stop for a loop gone wrong, not a
budget. Reaching it is reported.

### 7.7 The switch

One setting on the server turns every cut of these rules off: the preparation reads no
verdict, the photo list holds only 404 and 410 as before, the cards' prices are the
feed's. It is turned on the owner's word; the catalogue is whole again from the next
preparation. The checks go on asking and recording meanwhile. From the deployment of the
checks the switch is on: they cut from their first night (owner, 21/11).

## 8. Coming back

1. **A failed product is asked again**: the next night and the two after; then every 7
   nights while the feed lists it. `gone` and `another product`: after 7 nights, then
   every 30. Any failed product: the next night after its feed row changes its address,
   its photo's address or its price.
2. **The night its failed check passes, the failure ends.** It is a product a card can
   show again and takes a place by the cap's rules. One that passes again within 7 nights
   of its cut counts for the cap as kept the night before, so that one bad night does not
   cost a product its place (Proposed).
3. **Stock**: the night the shop's site says in stock; with no reading of the last 3 days,
   the feed (5.2).
4. **The category**: 5.5. **A shop**: 5.6.

## 9. What the cap reads

Owner, 21/11: «Τη θέση τους μέσα στο όριο των 12.000 την παίρνουν προϊόντα που πέρασαν τον
έλεγχο»; a new product is checked before it enters.

1. **A product a card can show** (today `offer_health.evaluate_product_eligibility`: in
   stock, a price, an image, a readable currency, a type or category) must also: be of a
   shop that is in (5.6); have no failed check; carry its category (5.5); and, once its
   shop's first round is over (3 below), have its page passed within the last 30 nights.
2. **The cap's own rules stand**: 15% a category, 12,000 at most, the night before's
   first, a fair share for each kind, the clean ones first, each tier spread over its
   prices (`catalogue_cap`). The share and the sizes are worked out from the products of 1:
   a failed product counts nowhere.
3. **The first round.** The products the catalogue holds the night the checks start were
   never asked: they stay as they are until asked. A shop's first round is over the night
   every product it has in the catalogue has been asked once, or 3 days after its first
   night, whichever comes first. From then a product of it never asked, or not passed in 30
   nights, is not shown until it is. No check of it failed: it is not cut. It leaves the
   cap's memory of the night before and waits at the gate as a new product does (4 below),
   so the cap may name it a candidate that same night and the bot asks it the next.
4. **A place left free goes only to a product whose checks passed.** A product never asked
   takes no place: the cap names it a candidate. For each kind with places open, the
   products it would choose next by its own order, one and a quarter times the places open
   and at least 4; the bots ask them the next night (section 10); those that pass take the
   places at that night's preparation.
5. **A product cut leaves the cap's memory of the night before**, save as 8.2 says.

## 10. The order of asking

In a shop, within its night:

1. the products held by a brake, and the failed ones due again (section 8);
2. the shown products whose feed row changed its price, its address or its photo's address
   since their last check; and the ones hidden on the site's "sold out" whose reading is
   3 days old;
3. the cap's candidates (9.4);
4. the shown products never asked, those a visitor sees first: of each kind the 24
   cheapest and the Recommended, then the rest, the cheapest first;
5. the shown products asked longest ago. One whose last pass is over 14 nights old comes
   before the rest of this step.

A Shopify catalogue read whole serves all five at once. Among shops, when there is not
room for all in a night: those the account is joined to at Awin first, then pending, then
the rest, so that work is not done twice on a shop that may leave (owner, 21/11: «...θα
πρέπει να ξαναπεράσουμε από την ίδια διαδικασία»).

## 11. What is remembered and what is reported

**The ledger**, on the server beside the catalogue's memory, never in the repo or in a
public place:

- per product (its shop and id; also its product's name in its own address, so that a row
  whose id changes takes the checks of its address): for each check its verdict, its
  reason, when it was asked, how many nights it has failed, when it is due again; what
  agreed (5.1); the site's price read and the feed's price that night;
- per shop: its reader and whether it is proven; whether it can be checked, and its day;
  its brake's state; Awin's relationship and link status; its feed's last import; the
  night's counts;
- per night: what each brake held and why.

**The night's public note** (counts and shop names only: never an address, an id or a
key): per check, asked, passed and failed by reason; cut that night, back that night, held
and by which brake; the shops that cannot be checked and their day; the shops out and why;
prices tied, the same, other, shown from the site; per shop not proven, the share that
agrees and the commonest ratio; each shop's oldest check; the AI's cost. The owner's daily
email carries the same numbers in Greek (his plan, step 12).

## 12. What changes in the standing texts when this is built

- `PROJECT_RULES.md` §2, the photo: "only a link to nothing (HTTP 404, 410) is gone"
  becomes any failure (5.4). §5: beside the stock rule, the price of the shop's own page
  (5.3) and the checks (noted there on 21/11 as decided and not yet in force).
- `docs/PICWISE_DECISION_CONTRACT.md`: "What a product must carry to be shown" (the photo;
  a page that passes; a category); "The shop's own price" (the page's price).
- `deployment/bot/shop_catalogue_bot.py`: `LEFT_ALONE` no longer holds InStock UK (owner,
  21/11). `deployment/server/check_photos.py`: what calls a photo gone.
- `docs/PICWISE_SERVER_ARCHITECTURE.md`, section 3 (the bot designed on 23/10: a sample a
  night, a reliability score, a blocked page counting neither for nor against): these
  rules stand where the two differ.

## 13. Open: the owner's to say

1. ~~What a visitor meets behind the button of a shop the account is not joined to~~
   **Answered 22/11, 03:24 Athens**, by the owner's own tap on a button of InStock UK (not
   joined): «Το in stock μπαίνει»: the shop opens. Whether Awin counts such a sale for a
   commission is not known (likely not, with no partnership): never claimed.
2. **Proposed, his yes to come** (each built as written until he says otherwise). **The
   first two had his yes on 22/11** (asked with the «ανέβασε»; `data/checks_owner_words.json`
   holds his words): a feed
   over 7 days old (5.6.4); a shop suspended, closed or offline at Awin (5.6.3). Still his to say: the stop on a
   reading of Awin that would put out many shops at once (5.6.3); a shop's 3 days
   starting afresh only after 7 nights checked (5.6.2); the category asked again only when
   the question changes (5.5); the brakes' numbers (7.2 to 7.4, 7.6); a reader proves
   itself and a price far apart (7.5); the price's history starting again on a change of
   source (5.3.5); a sold-out reading asked again before it lapses, and pre-order or
   back-order read as not in stock (5.2); a product back within 7 nights keeps its place
   (8.2).
3. **A code read on a shop's site standing in for one the feed lacks**, so that one
   product in several shops is joined into one card (`same_product_key`): kept in the
   ledger, put to him with numbers once the ledger has them.
4. **The share of a shop's products that pass**: reported only; what it does is his to
   say (open since the design of 23/10).
5. **A page of the site about the bot** (what it reads, how a shop asks to be left
   alone): a text visitors read, so his words and a picture first.
6. **A reader that draws the page in a browser**, for shops whose pages no HTML reader
   reads: not in these rules; such a shop cannot be checked (5.6.2).
7. **A shop whose photo host refuses the checker** while its pages are read (5.4):
   reported, nothing cut; whether it leaves is his to say, with the report's numbers.
8. ~~The shop's recipe by the AI (4.5.3)~~ **Answered 22/11, 10:18 Athens: «Όχι τώρα»**: not built
   while it would serve one shop (Pro-Camera, 433 products, which leaves on its day 4); built when
   a larger shop needs it.

## 14. For the builder (task 5)

- Verdicts and brakes are code without a network: one function per table of section 5 and
  per brake of section 7, each row and each number pinned by a test named after its
  section here. The bots only fetch; what an answer means is decided there.
- The preparation reads the ledger behind the one setting of 7.7. The photo check, the
  cap's candidates and the night's note read the same ledger.
- Logs are public: counts and shop names only; no address, id, key, token or server name.
- Nothing is deployed without the owner's «ανέβασε», after the look of task 7. That look
  is of the same day: it is not nights of report only (2.2, 4).

## 15. Built (task 5, 21/11): what the code settles that these rules left open

Built on the work branch; `data/checks_switch.json` stayed `false` until the look of task 7,
and the deployment the owner approved on 22/11 turned it `true`, so that the checks cut
from their first night live (2.2, 4). Where the code had to settle a point:

1. A redirect to another site is not followed (4.1) and is `not checked`; it counts with the
   refusals for whether the shop can be checked (5.6.2).
2. An answer no table names (a 400, a 405, a redirect with no address) is `not checked`, never a
   cut: such a product passes nothing either, so after its shop's first round it is not shown
   (9.3).
3. The round: all day (owner, 22/11), 05:30 to 03:05 UTC (before the updates' reboot window of
   03:30, the shops' bot of 03:40 and the preparation of 04:17; between 03:05 and 05:30 a round
   started asks nothing); its night is the morning's date, the preparation's. Each answer is kept
   as it comes (`tonight-<night>.jsonl`): a deployment that prepares the catalogue stops the round
   for the server's memory and starts it again after, and it goes on from where it was; a night
   recorded already is not asked again.
4. A Shopify shop: its catalogue up to 100 pages of 250 (25,000 products); a product past them,
   or missing from a catalogue read whole, by its own `/products/<name>.js` (one request, which
   also gives each variant's barcode). Collections are not read by the checks.
5. The photo: a 200 that is no image is read as 415, an empty one as 204 (their HTTP meanings).
   The photo check runs apart (04:40), so its brakes are counted inside it: a shop's night (7.2)
   by its photos, and the night's (7.4) by the products new photo failures would leave out.
6. A shop out because it cannot be checked is asked each night by up to 5 of its pages (5.6.2):
   the preparation names 20 of its rows for the bot.
7. A reading of Awin is whole or none: if one of its five lists does not answer, the last reading
   stands (a list missing would put its shops "in no list").
8. A price far apart fails its product only where the shop's reader of prices is proven (7.5):
   the look on the server of 21/11 (1,233 products of 135 shops, 10 a shop) found Shopify
   catalogues whose prices are in another currency than the feed's (InStock UK: the commonest
   ratio 1.2, 1 price in 10 the same; Finediam 1.08; Bern Helmets 1.47): an unproven reader there
   would have cut 3 of InStock UK's 10 as far apart. Unproven, it changes nothing, as 7.5 says of
   its prices.
9. A shop of the catalogue whose name Awin's reading does not hold is not judged by it: only a shop
   Awin's reading names, in none of its lists, is "in no list" (5.6.3). Names are matched with
   "&amp;", accents, case and spaces read alike. The look of 21/11 had two names written
   otherwise read as "in no list"; the stop of 5.6.3 held them (5,158 products).
10. A shop's first round (9.3) ends when every product it shows has been decided once, passed or
    failed, or after 3 days: a product the shop refused was not checked, so a shop that refuses
    keeps the 3 days of 5.6.2 (in the look of 21/11 a shop of 4 products, all refused, would
    have ended its round, and lost them, on its first night).
11. Not built: the shop's recipe by the AI (4.5.3), on the owner's word (22/11, 10:18 Athens, asked
    whether to build it for the one shop it would serve: «Όχι τώρα»); built when a larger shop needs
    it. Without it a shop whose pages no reader reads leaves on its day 4 (5.6.2). The looks on the server of 22/11 (runs 44971761757,
    44972305197, 44973108097, 44973503931) left one such shop: Pro-Camera (433 products; Magento,
    its price written only as words on the page).
12. A challenge page (4.4, 5.6.2) is told by what only a challenge writes: a 403, 429 or 503, or a
    200 under 100 KB, with an interstitial's own signs (Cloudflare's challenge, PerimeterX,
    Imperva's incident page, DataDome, SiteGround's and Sucuri's walls, Anubis, "One moment,
    please..."), and never a page a product was read on. A reCAPTCHA box or Cloudflare's script sit
    on ordinary pages too: until 22/11 they made GamingKit's (48,126) and Webbs Motorcycles' (940)
    whole, readable pages count as refusals; now both pass (20 of 20 in the look). A wall that
    makes a browser work or wait before the page is a refusal, never got around: Anubis on Plusshop
    UK (13,110) and Bazta UK (12,159), "One moment, please..." on Elixir Garden Supplies (76) and
    Luxe Mattress Affiliation (5,761; one of its pages in ten came from Cloudflare's cache, unwalled).
    They cannot be checked unless they let the bot through: the letter of
    `docs/PICWISE_CHECKS_LETTER.md`.
13. The page reader reads Magento's own price box last (`text/x-magento-init`, `priceConfig`): its
    price, of one product only; never its stock, which Magento writes as words (4.5.4).
14. The category (5.5) is applied by the preparation, not counted by the bot: a product the AI gave
    no line ("no line fits", refused twice, a slip) is cut (`no category`); one not asked yet stays
    if shown and waits if new (the cap's gate). Its brake, for an answers file gone wrong: more cut
    so in one night than 10% of the products (7.4's share), none is, and the health run says so.
    The products shown or next for the cap with no answer are named each night
    (`jobs/shelves.jsonl.gz`), and `picwise-shelves` (05:20 UTC, the AI layer's user and key)
    asks them as the scan of 20/11 asked every product, stopping at the night's $10 (7.6). The
    scan of 20/11: 4,449 keys "no line fits" and 2,163 refused twice of 203,097 (3.3%).
15. The night's numbers (11): the bot's note goes into the public note (`checks.bot`) beside what
    the preparation applied; the morning's health run prints them with their limits;
    `docs/PICWISE_DAILY_WORK.md` puts one line of them in the owner's daily email, and on a shop's
    day 1 the letter for it, on its day 3 «βγαίνει αύριο».

Where: `src/picwise_checks` (verdicts, brakes, the ledger, the page reader, rows), the bot
`deployment/bot/shop_checks_bot.py` (`picwise-checks.service`, `.timer`), the preparation's side
`src/picwise_providers/checks_applied.py` (with `offer_health`, the cap's gate in
`catalogue_cap`, the price's source in `catalogue_memory`), the photos in
`deployment/server/check_photos.py`, the category's morning in `deployment/server/shelves_service.py`
(`picwise-shelves.service`, `.timer`); looks on the server, read-only:
`.github/workflows/server-checks-look.yml`, `.github/workflows/server-look-unread.yml`.

## 16. The look of task 7 (22/11): what it found and what was mended before the «ανέβασε»

The look walked the ledger and the preparation's side together, night after night
(`tests/test_picwise_checks_walk.py`), and looked on the server, read-only (section 17 gives
the numbers). Mended on the work branch before the deployment of 22/11:

1. **A product not shown until it is checked is not cut** (9.3). As built, a product never
   asked by its shop's day 4 (or not passed in 30 nights) was marked cut like a failed one:
   the cap never saw it that night, the bot did not ask it the night after, and in a
   category at its size its place went to another product before it could be named for it.
   Now the decisions name it apart (`wait`); the preparation does not mark it, takes it out of
   the cap's memory of the night before and holds it at the gate; the cap may name it a
   candidate that night; the bot asks it the next; it is back the night it passes.
2. **The two Proposed rules he asked to be reminded of are off until his yes** (5.6.3's
   suspended, closed or offline; 5.6.4's old feed): `data/checks_owner_words.json`,
   `awin_closed_out` and `old_feed_rule`. A rejected shop is out either way. **Asked that
   day with the «ανέβασε», he said yes to both: true from the deployment's commit.**
3. **The category's brake** (5.5, 15.14) counts among the rows the AI answered (a line, or
   none), not among every row of the feed: the feed has about seven rows for each product
   shown, most never asked, so a tenth of them was more than every product with an answer.
4. **The photo** (5.4, 15.5): a photo is no image, or empty, only when a GET says so (a HEAD
   that says it is asked again with a GET of one byte); a bare binary type
   (`binary/octet-stream`, a store's default) is a photo's.
5. **A night with no memory of the night before**: the cap's pool file missing or unreadable
   reads as an empty pool, and the gate would then take every product for a new one and hold
   the whole site back. On such a night the gate holds back only the products named as not
   shown until checked; the preparation's note says so (`gate_off`) and the health run
   passes a limit.
6. **A Shopify product is asked at its own page before it is called gone** (5.1, 15.4): a
   `.js` answers 404 for a product the shop renamed, while its own address sends a visitor
   on to the new one. A `.js` 404 is followed by one request for the page, judged as any
   shop's page (the same product at a new address passes; the home page or a collection is
   moved; a 404 is gone).
7. For a look only: each shop's pace (requests, seconds, its crawl-delay) and the shops' own
   stock words behind a sold-out reading.

## 17. The looks of task 7 on the server (22/11, read-only): the numbers

Nothing written on the server; counts and shop names only. Runs: the health and the
preparation's runs 45003593319, 45003595123; the bot, 100 products a shop, every shop
45004081526; the photos 45005122012; the pace of the six largest shops 45005863163; the
shops with products called gone, asked at their own page first, and the stock words
45006137403.

- **The catalogue that morning**: 398,994 products of 135 shops; the night's preparation 28.6
  minutes, peak 15.1 GB; the site 6.7 to 6.9 GB after the night's swap (a preparation beside
  it by day needs the site restarted first); the shops' bot's first round with both links:
  143 of 145 shops with an address, 706 requests, 100,274 products known.
- **The page** (100 a shop, 9,531 asked of 135 shops, 8,629 decided): passed 8,355 (96.8%),
  failed 274: gone 262, moved 4, not a product page 4, another product 2, a price far apart
  2. Three shops hold 171 of them. Asked again with a product's own page asked before it is
  called gone (16.6): no product called gone was found passed at its page; 94 of 254 are
  moved (the shop's site sends the visitor to another page), the rest gone there too.
  **Dean Morris Cards: 100 of 100 gone at the page a visitor's button opens** (held for the
  owner: under 20 passes on record); Happy Days Factory Flowers 56 of 100 moved (held one
  night by its brake); Bern Helmets (UK) 15 of 15 moved (cut: under 20 decided, no brake).
- **Shops that cannot be checked, day 1**: Aosom UK, InterRose, TV Cables (robots.txt
  refused), Bazta UK, Plusshop UK, Elixir Garden Supplies, Luxe Mattress Affiliation (a wall),
  Juicy Couture UK (no address of its own), Pro-Camera (its pages not read): nine shops,
  about 43,000 products (the six whose sizes were read on 21/11 hold 41,591), out on their day 4.
- **Prices**: tied readings the same as the feed's in most shops; 73 of 8,355 passed would
  show the page's price (shops whose reader is proven). Not proven, so the feed's price
  stands: InStock UK (20 of 93 the same, then 54 of 216; the commonest ratio 1.19: its
  `.js` prices read as another currency), Finediam (0 of 99; 1.08), ANCHOR & CREW (0 of 84;
  1.2), Natkina, WAU, MOH, Optimum Nutrition UK, Webbs Motorcycles. Each wants a look that
  names the cause (7.5).
- **Stock**: where the page reader is proven, a product its shop's own page calls out of
  stock is hidden (owner, 12/11). PCHUB.UK 25 of 99 and 47 of 164, GamingKit 14 of 90 and 46
  of 248, MoreThisWay 15 of 96, Sport and Leisure UK 6 of 93: the shops' own word is
  `OutOfStock` in every one. About 22,000 products of the catalogue by these shares. PCHUB.UK's
  reader agrees with the feed on 71% to 75% of its readings, near the 70% the proof asks:
  under it nothing of the shop is hidden. Gains Nutrition's pages say `BackOrder` for 46 of
  100 (read as not in stock by 5.2, Proposed): its reader is not proven, so nothing changes.
- **The photos** (5.4): the night's check holds 278,946 read and 6,601 gone of the catalogue's
  285,547 photos, **none it could not read**; 3,989 asked as the strict check asks (40 a
  shop, 131 shops): 3,985 read, 4 gone (404), no refusal, none that is no image or empty, no
  host that refuses. The strict check starting at the deployment leaves out nothing more.
- **The pace** (4.7), seconds a request, each shop alone: InStock UK 3.3 (and none of 324
  products asked was among its catalogue's first 25,000: each is asked by its own `.js`),
  Tyres UK 3.3, Tooled Up 4.1, GamingKit 4.3, PCHUB.UK 6.3 to 6.5, Tirendo UK 10.0 (its
  crawl-delay). With every shop asked at once (140 workers) GamingKit gave 10 s a request:
  the bot reads pages on one processor. A round of the whole shop: InStock UK about 103 hours
  (4.6 days of the bot's 21.6 hours), PCHUB.UK 85, Tooled Up 78, GamingKit 58. The first
  round's four rounds give about 80 hours: **about 23,000 products of InStock UK, and up to
  a few thousand of PCHUB.UK and Tooled Up, are not asked by day 4**, are not shown from
  that night (9.3), and their places are refilled by products that passed over the next one
  to two days.

## 18. The owner's answers of 22/11 (12:50 Athens), asked after the look with its numbers

Put to him with what the deployment would do (the catalogue from about 399,000 products to
about 285,000 at its lowest, on day 4, then filling again with checked products):

1. To deploy the checks now: **«Ανέβασε»**. `data/checks_switch.json` true.
2. Dean Morris Cards (869 products), all 100 asked gone at the page a visitor's button opens:
   **«Κόψε τα»**. `cut_held_shops` (7.2): its products, held for him the first night, are cut
   the night they fail again, and come back if they pass.
3. A shop suspended, closed or offline at Awin: **«Ναι, να βγαίνει»** (5.6.3).
4. A product of a feed over 7 days old, shown only with a reading of its shop's own site of
   the last 3 days: **«Ναι»** (5.6.4). Offered first and not taken: to count each night what
   it would hide and decide with the number. The night's note and the health run say how
   many products wait for it (`not shown until checked`, by reason).


## 19. How many of a shop's products pass: what the bot scans, 20,000 the most (owner, 22/11): decided, NOT BUILT

Written 22/11 (17:10 Athens) by Claude Fable 5.2, after a look with its numbers (19.2), and
**corrected the same day (17:35) on the owner's words of 17:08 and 17:21: what the bot scans
of a shop passes to the site, 20,000 the most; no cap is set for each shop** (19.3). The build is OPUS's by
the work split; a look before its «ανέβασε» is FABLE's, since it cuts products. Each rule
names whose it is, as everywhere in this file.

### 19.1 His words

After the server's panel showed no larger server to move to, and told that a round of a
large shop takes days by the pace rule (4.3, 4.7):

- «Δεν μας ενδιαφέρει η ποσότητα αλλά η ποιότητα το να κάνει μία δύο μέρες ένα κατάστημα να
  σκαναριστεί και στο εν τω μεταξύ να πετάει σαβούρες μέσα είναι πρόβλημα ή να απασχολεί το
  μηχανισμό για τόσο μεγάλο διάστημα! πρέπει λοιπόν να βάλουμε κι άλλο πλαφόν που να αφορά
  το μέγιστο όγκο που δίνει να κατάστημα παράδειγμα 80.000 προϊόντα».
- Told that 80,000 touches one shop only, and that the measure is what the bot checks in a
  day at each shop's pace: «...πρέπει κάθε κατάστημα να έχει πλαφόν μέχρι 20.000 πού είναι ο
  αριθμός που μπορούμε να ελέγξουμε στις 24 ώρες συνεχής λειτουργίας», then «Εφόσον αυτός ο
  κανόνας μπορεί να επαληθεύεται να θεσπιστεί ως σύστημα λειτουργίας μπορούμε να το κάνουμε
  έτσι κάθε κατάστημα που θα μπαίνει μέσα πρέπει να τηρούμε τα όρια που επιτρέπει».
- Which products, 16:00: «Ναι συμφωνώ επισήμανση 20.000 είναι το μέγιστο όριο που μπορούμε να
  βάλουμε από ένα κατάστημα».
- The order, 16:03 (his proposal at 16:02: «Προτείνω να διαλέξουμε πρώτα με βάση την
  πληρότητα της κατηγορίας που λείπουν»; one step was put before it; his «Ναι»): (1) the
  products the shop sells cheapest of all, the same product by its code; (2) the products of
  the site's kinds with the fewest products; (3) the rest, a share of each kind over its
  prices, the most complete first.
- 17:08, shown this section's first table, which gave each shop a cap of its own by its pace
  (20,000, 18,951, 18,069, 12,140), as the record of 15:51 had it ("at most what the bot can
  check in one day at that shop's own measured pace"): **«Το πλαφόνι είναι 20.000 προϊόντα
  και εξαρτάται και από τον όγκο που μπορεί να σκανάρει το bot αυτό που επιτρέπει δηλαδή το
  κάθε κατάστημα το πλαφόν είναι ένα και είναι 20.000 προϊόντα.. δεν μπαίνει πλαφών για το
  κάθε κατάστημα.. μπαίνει κανόνας μόνο όσα έχουν σκανναριστεί περνάνε»**.
- 17:21, the rule having been written back to him as one cap of 20,000 for every shop:
  **«Δεν υπάρχει διαφορετικό πλαφών ανά ανακατάστημα... Το πώς μπορεί να επιτρέπει ένα
  κατάστημα μπορεί να σκανάρει 15.000 προϊόντα σε ένα άλλο 20 και σε ένα άλλο 5 αυτά περνάνε
  στο site μέγιστο όριο αν το κατάστημα απαντά σύντομα κι αν επιτρέπει πολλούς ελέγχου το
  δευτερόλεπτο είναι τα 20.000... τελειώσαμε με αυτό..»**.
- 17:16, while the look was run once more with one cap: «Για ποιο λόγο μετράς δεν μας
  ενδιαφέρει κάτι τέτοιο». Nothing more is measured of it before the look of 19.7.

### 19.2 What the look measured (22/11, read-only, no AI)

`deployment/server/look_shop_cap.py` on a copy of the server's catalogue of 22/11 11:26 UTC:
the 398,957 products the category cap keeps, of 135 shops; with 20,000 of every shop, the
most that can pass (run 45036794087). The runs before it, 45034692763 and 45035123154, took
of each shop what the bot would scan of it in a day at the pace the morning's look measured
for it alone (20,000, 18,951, 18,069, 12,140): 197,740 cut, and the numbers the owner was
asked the order with (19.4).

| shop | products | cut | a code another shop sells too | cheapest here | dearer here | with a kind |
|---|---|---|---|---|---|---|
| InStock UK | 102,278 | 82,278 | 2,172 | 1,438 | 734 | 18,637 |
| Tooled Up | 68,449 | 48,449 | 2,311 | 486 | 1,825 | 22,983 |
| GamingKit | 48,191 | 28,191 | 43,634 | 0 | 43,634 | 17,455 |
| PCHUB.UK | 47,982 | 27,982 | 43,446 | 33,373 | 10,073 | 17,090 |

- **Four shops are over 20,000, and no other**: the next largest, Plusshop UK, holds 13,095.
  **At least 186,900 products are cut; at most 212,057 stay** (more are cut where the bot
  scans fewer than 20,000 of a shop in a day). (The estimate given to him at 15:51: about
  190,000.) Those four hold 266,900 of the catalogue's 398,957 products today: two in three.
- **GamingKit and PCHUB.UK sell the same 43,500 products. PCHUB.UK is the cheaper on 33,373;
  GamingKit is the cheapest on none**: nine in ten of its products are sold cheaper by
  another shop.
- **Few of the big shops' products have a kind of the site's**: 76,165 of their 266,900.
- **The steps tried as recorded at 16:03** (each step's products, when more than the places
  left, chosen as the category cap chooses: fair shares over the parts, each spread over its
  prices): of the 134,097 products with a kind, 76,012 stay; 80 of the 292 kinds lose over
  half their products (printer 1,902 to 301, ram_memory 4,938 to 394, safety_shoes 3,048 to
  133, trousers 3,117 to 292, vacuum_cleaner 1,024 to 118); the kinds under 100 products go
  from 111 to 162; none is left empty. PCHUB.UK's step 1 alone holds 33,373 and fills its
  whole cap. GamingKit's step 1 is empty: it keeps mostly what PCHUB.UK sells cheaper. Of the
  80,000 products the four keep, 17,098 are sold cheaper by a shop that keeps them too: since
  16/10 one product in several shops is shown once, from the cheapest, so those places show
  nothing.
- **Tried with the three changes he chose (19.4)**: of the products with a kind, **109,651
  stay**; **12 kinds lose over half** (printer to 1,021, ram_memory to 1,405, safety_shoes to
  1,261, trousers to 2,440); the kinds under 100 go from 111 to 122; none is left empty; the
  four show 60,063 different products (56,185 as recorded); GamingKit's whole cap goes to
  products PCHUB.UK's cap left out.

What the look could not measure: the cap's effect before the category cap (it read the
products the category cap had already chosen, not the 1.6 million rows a card can show).

### 19.3 How many of a shop's products pass

**Owner** (22/11: 16:00, 17:08, 17:21). **What the bot scans of a shop passes to the site:
as many as the shop lets it scan, 15,000 in one, 5,000 in another. The most, for a shop that
answers fast and allows many checks, is 20,000. No cap is set for each shop.** «Μπαίνει
κανόνας μόνο όσα έχουν σκανναριστεί περνάνε». «Τελειώσαμε με αυτό.»

**Proposed, so that it holds steady; for the builder, and his to change:**

1. **Scanned** is checked and passed in the bot's last day of asking the shop. A pass counts
   for two nights, so that one bad day does not empty a shop. (9.1 counts a pass for 30
   nights today: with that, a shop the bot scans 5,000 a day of would pile up to 20,000 over
   four days, each product checked once in four days, which is not what he says.)
2. **Each day the bot asks a shop's shown products again first**, in the order of 19.4, and
   new ones only in the time left. So a shop settles at what it lets the bot scan in a day,
   and its products do not take turns on the site.
3. **The bot asks of a shop only its first 20,000 by the order of 19.4.**

Nothing is worked out to set a number for a shop: the number is what was scanned.

### 19.4 Which products a capped shop keeps

**Owner**: the three steps of 19.1; 20,000 the most. **And, 22/11 (17:15 Athens), asked with
the look's numbers as they then stood, counted with a cap by each shop's pace (as recorded,
71,972 of the 134,097 products with a kind stay and 90 kinds lose over half; with the three
changes a, b and c, 104,718 stay and 21 kinds lose over half; with one cap of 20,000 the
same comparison is 76,012 and 80 against 109,651 and 12, 19.2): «Με τις 3 αλλαγές».** So the order a shop over its cap keeps its products by is:
first its products of the thin kinds (a); then what it sells cheapest of the offers the site
keeps (b); then the rest, the products with a kind before those with none (c); last, and
only when places are left, a product a cheaper shop keeps (b). d, e and f are **Proposed**.

a. **The thin kinds first, as he first proposed.** A shop's products of a kind the whole
   catalogue holds fewer than 100 of are kept before anything else. They are 1,625 products
   in all four shops (840, 371, 207, 207). Put second, GamingKit and PCHUB.UK keep none for
   that step, their caps full by step 1.
b. **"Cheapest of all" is read among the offers the site keeps.** A product a cheaper shop
   keeps is kept last of all, only when places are left: the site shows one product once,
   from the cheapest (owner, 16/10), so a dearer copy of a kept product shows nothing. A
   product whose cheaper offers were all cut by their own shops' caps is the next shop's to
   keep, as cheapest. So two shops with one catalogue show two different halves of it, not
   the same half twice. The shops are settled the smallest cap first, after a first pass in
   which each keeps what it sells cheapest of every shop that sells it.
c. **In "the rest", the products with a kind of the site's before those with none.** A
   product of a kind is found by a search for the kind; one with none only by its own words.
   His step 3 says "a share of each kind"; the category cap shares over its "parts" (a kind,
   else the shop's shelf), and with thousands of shelves the kinds are left a small share.
d. **Inside a step that holds more than the places left**: the category cap's own choosing
   (`catalogue_cap`): fair shares over the kinds, the clean ones first, each tier spread
   over its prices; ties by the row's id, so the same ones come each night.
e. **The night before's first** (owner, 27/10, for the category cap: «κοιτώντας πάντα το
   χθεσινό σαν αφετηρία»): a product the shop kept the night before, that a card can still
   show, stays; the order chooses for the places left. A kept product that became a cheaper
   shop's too gives its place to a product that waits, checked and passed, when there is one.
f. **The first night**: a capped shop's products that have passed their check come before
   the ones never asked, inside each step: the bot's work until then is not thrown away.

### 19.5 The bot over several processes, built with it

**Owner, 22/11 (17:15 Athens), asked whether the bot should be made to work on several
processors together with this: «Ναι, μαζί».**

Why it is needed: what the bot scans of a shop is what passes (19.3), so the bot's own
slowness would hold a shop's products back. The look of 22/11: asked alone, GamingKit answers
in 4.3 seconds a request, about 18,000 a day; with every shop asked at once, in 10, about
7,800 a day: the bot reads the pages on one processor (section 17). (At 17:25 this section
said it was no longer needed, the rule then read as a cap that does not depend on the bot;
his word of 17:21 puts it back.)

### 19.6 Beside the other rules

**Proposed**, for the builder to keep or to bring back with a reason:

1. **Before the category cap.** A shop's cap chooses among the shop's products a card can
   show (9.1); the category cap (15% a category, 12,000 at most) then counts and chooses
   among what the shops' caps keep. Its own rules stand.
2. **The checks' gate stands** (9.4): a place in a shop's cap goes only to a product whose
   checks passed. For each capped shop with places open, the shop's cap names its
   candidates: the products it would choose next, one and a quarter times the places open;
   the bot asks them in their turn (10.3).
3. **The order of asking** (section 10) stands. A capped shop's shown products can all be
   asked within a day: "passed within the last 30 nights" (9.1) can then be made shorter;
   that is another rule, his to say, not this one.
4. **A shop that cannot be checked** (5.6) is out on its day 4, as before.
5. **A new shop**: the bot asks its first 20,000 by the order; what it scans and passes enters.
6. **9.1's 30 nights** become the two nights of 19.3.1 for every shop: a look before the
   «ανέβασε» counts what that hides (19.7).

### 19.7 The brake, the switch, what is reported

**Proposed.**

1. **The first night cuts at least 186,900 products, by his decision.** Its look, before the
   «ανέβασε» (task 7's kind), the only measuring left (19.1, 17:16): the catalogue prepared
   on GitHub's runner with the rule; per shop what the bot scanned and what passes; what
   leaves by a pass over two nights old; each kind before and after; the first cards of the
   40 searches before and after; the preparation's time and memory.
2. **A switch** (`data/shop_cap_switch.json`, frozen with the code): false, no shop is
   capped, within one preparation.
3. **The night's note** (`/prepared.json`), per shop over the cap: its products a card can
   show, kept by step, cut, candidates named. The health run prints them. Counts and shop
   names only.

### 19.8 Open: the owner's to say

Answered on 22/11: what the bot scans of a shop passes, 20,000 the most, no cap for each
shop (17:08, 17:21; 19.3); the order, with the three changes (17:15; 19.4); the bot over
several processes, built with it (17:15; 19.5). He asked for no more questions on it
(«τελειώσαμε με αυτό»): what follows is built as written and shown to him in the look.

1. A pass counts for two nights (19.3.1); a kind is thin under 100 products (19.4 a).
2. The proposed rules of 19.3.2, 19.3.3, 19.4 d to f, 19.6 and 19.7.

### 19.9 For the builder

- What exists: the same product by its code (`product_identity.same_product_key`); the
  category cap's shares and spread (`catalogue_cap.fair_quotas`, `_spread`, `part_of`, its
  ranks of clean products, its memory of the night before and its gate, `may_enter`, with
  the candidates); the walk of nights through the ledger and the preparation's own cap
  (`tests/test_picwise_checks_walk.py`): walk this rule through it before anything else. In
  the bot: the order of asking (19.3.2, beside section 10), the first 20,000 of a shop
  (19.3.3), several processes (19.5).
- `look_shop_cap.py` tries the steps to count them (`measure`, `tried`): it is a look on
  399,000 products, not the build, and it does not know the night before or the checks.
- The preparation holds 21.8 of the server's 22.9 GB at night. A shop's cap worked out
  before the kinds of 1.6 million rows are read would spare time and memory, but steps a and
  c need a product's kinds: where it runs is the builder's to settle, with the same result.
- The standing texts change when it is deployed, not before: `PROJECT_RULES.md` (2 and 5,
  beside the category cap), `docs/PICWISE_DECISION_CONTRACT.md` ("What a product must carry
  to be shown"), `docs/PICWISE_DAILY_WORK.md` (the health run's lines).
