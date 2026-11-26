# PicWise: the checks' rules

Written 2026-11-21 (evening, Athens) as task 4 of the work split by model (Claude Fable
5.2; `docs/picwise_session_handoff.md`), as rules only. Built in task 5 (section 15),
looked at and mended in task 7 (sections 16 and 17). **The owner's «Ανέβασε», 2026-11-22
(12:50 Athens): `data/checks_switch.json` is true from that day's commit, and the checks cut
from the first night after its deployment** (`PROGRESS.md` says how the deployment went).
**How many of a shop's products pass (section 19): deployed 2026-11-23 (09:02 UTC) on the
owner's «Ανέβασε το», its switch true**, after the look of section 20 (22/11) and the same
look on the checks' first real night (23/11, 20.7); how the deployment went, and what the
mornings after read, is 20.8. **A mend to it built the same day (20.9: the places a full
shop's own copies hold) is NOT deployed: looked at on the server's data that afternoon
(20.10), it does what it says and waits for the owner's «ανέβασε».**

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
- **Πόσα προϊόντα δείχνει ένα κατάστημα (απόφασή σου, 22/11· χτίστηκε το βράδυ της 22/11·
  ανέβηκε στις 23/11 στις 11:02, με το «Ανέβασε το» σου, και ο διακόπτης του είναι
  ανοιχτός).** Ό,τι
  προλαβαίνει να σκανάρει το bot σε ένα κατάστημα περνάει στο site: σε ένα 15.000, σε άλλο
  5.000. Ανώτατο όριο 20.000, για κατάστημα που απαντά γρήγορα. Δεν μπαίνει ξεχωριστό
  πλαφόν ανά κατάστημα («μόνο όσα έχουν σκανναριστεί περνάνε»· «τελειώσαμε με αυτό»). Ποια
  προϊόντα κρατά ένα κατάστημα (η λέξη σου, 22/11: «Με τις 3 αλλαγές»): πρώτα τα είδη με τα
  λίγα προϊόντα· μετά ό,τι πουλά φθηνότερα από όσα δείχνει το site· μετά τα υπόλοιπα, πρώτα
  όσα έχουν είδος· ό,τι το κρατά φθηνότερα άλλο κατάστημα μπαίνει τελευταίο. Το bot
  δουλεύει σε περισσότερους επεξεργαστές («Ναι, μαζί»). Ένας έλεγχος μετράει 3 βράδια:
  προϊόν που το bot δεν πρόλαβε να ξαναελέγξει μένει ως 3 μέρες, μετά δεν φαίνεται μέχρι να
  ξαναπεράσει («κρατάμε τα προϊόντα ασκανάριστα μέχρι 3 μέρες», 22/11· σήμερα μετράει 30
  βράδια). Ο κανόνας: ενότητα 19. Τι χτίστηκε: 19.10.
- **Η ματιά πριν από το «ανέβασε» έγινε δύο φορές: 22/11 το βράδυ και 23/11 το πρωί, με το
  πρώτο πραγματικό βράδυ των ελέγχων (ενότητα 20· τα νούμερα της 23/11 στο 20.7).** Τη μέρα
  του «ανέβασε» ο κατάλογος πάει από περίπου 355.000 σε περίπου 200.000 προϊόντα: InStock UK
  97.030 → 19.887, Tooled Up 63.073 → 18.628, GamingKit 36.851 → 18.818, PCHUB.UK 36.625 →
  19.968. Κανένα άλλο κατάστημα δεν χάνει προϊόντα. Πάνω από 20.000 δεν είναι 4 καταστήματα
  αλλά 7 (και Finediam, Tirendo UK, Tyres UK): αυτά τα 3 δείχνουν όσα και σήμερα. Κανένα
  είδος δεν αδειάζει· 14 από τα 289 χάνουν πάνω από τα μισά. Στις 40 δοκιμαστικές
  αναζητήσεις οι 26 δείχνουν τις ίδιες κάρτες. Τα δύο επόμενα βράδια, αν περάσουν όλα όσα
  ρωτήσει το bot, ο κατάλογος ανεβαίνει σε 217.672 και 221.316 και δεν βγαίνει κανένα
  προϊόν που φαινόταν. Το bot ξεκινά στους 4 επεξεργαστές. **Διορθώθηκαν τέσσερα λάθη, δύο
  στις 22/11 και δύο στις 23/11:** το bot θα ρωτούσε 63.000 προϊόντα που η κατηγορία τους
  δεν χωρά· το GamingKit θα κρατούσε 8.962 προϊόντα που το PCHUB.UK δείχνει φθηνότερα· τη
  δεύτερη νύχτα θα έβγαιναν 1.600 προϊόντα που ήδη φαίνονταν και θα έμεναν έξω τα
  περισσότερα που πέρασαν τον έλεγχο (λάθος της πρώτης διόρθωσης)· και προϊόν που άλλο
  κατάστημα έχει φθηνότερα αλλά δεν το δείχνει ακόμα μετρούσε σαν «φθηνότερο αλλού». **Τι
  μένει:** στο GamingKit περίπου 4.500 από τις 20.000 θέσεις κρατούν προϊόντα που άλλο
  κατάστημα δείχνει φθηνότερα (δεν φαίνονται)· δεν διορθώθηκε, είναι επόμενο βήμα (20.7.4).
  Και χωρίς τον κανόνα, ο κατάλογος της 24/11 θα είναι μικρότερος από τον σημερινό
  (374.859 → περίπου 355.000): το AI έδωσε το πρωί της 23/11 κατηγορία σε προϊόντα που δεν
  είχαν, 15.600 δεν πήραν καμία και κόβονται, και όσα πήραν ανταγωνίζονται πια στη νέα
  τους κατηγορία (20.7.1).
- **Ανέβηκε στις 23/11 (20.8).** Ο κατάλογος έγινε 199.771 προϊόντα από 132 καταστήματα,
  όσα ακριβώς έδειξε η ματιά. Η ετοιμασία πήρε 26,9 λεπτά (το πρωί 32,2) και το site
  κρατά 4,4 GB μνήμη (πριν 9,1): οι δύο συναγερμοί του server έσβησαν. Το bot ξεκίνησε
  ξανά στους 4 επεξεργαστές, με τον κανόνα. Μαζί ανέβηκε ο κώδικας της ερώτησης «είναι το
  ίδιο το είδος;» με κλειστό διακόπτη, και ο μετρητής ποιότητας κάνει την πρώτη του
  μέτρηση το πρωί της 24/11 (έως 2 $ τη μέρα).
- **26/11: 8 bot, 10.000 προϊόντα ανά κατάστημα, έως 20.000 έλεγχοι τη μέρα (ενότητα 23).
  Χτίστηκε το βήμα 1, όλα πίσω από διακόπτες κλειστούς· στο site δεν άλλαξε τίποτα.** Κάθε
  κατάστημα πάει πάντα στο ίδιο bot, με τον αριθμό του στην Awin (με το όνομα, αν δεν έχει).
  Διακόπτης για κάθε bot: όσα δεν είναι ανοιχτά τα ρωτά το bot που τρέχει σήμερα. Κάθε bot έως
  1,8 GB, όλα μαζί έως 11 GB και 4 πυρήνες· το site κρατά 6 GB που δεν του τα παίρνει κανείς.
  Το αρχείο ελέγχων σβήνει ό,τι δεν δόθηκε στο bot πάνω από 7 βράδια (κρατά μία γραμμή του).
  Ο δεύτερος έλεγχος έχει δικό του διακόπτη και ανοίγει τελευταίος. Η αναφορά υγείας λέει κάθε
  πρωί αν η μέρα ήταν «σταθερή».

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


## 19. How many of a shop's products pass: what the bot scans, 20,000 the most (owner, 22/11): decided; built 22/11 (19.10); looked at 22/11 and 23/11, four things mended (section 20); DEPLOYED 23/11 on the owner's «Ανέβασε το», its switch true (20.8); the places a full shop's own copies hold mended 23/11, NOT DEPLOYED (20.9)

Written 22/11 (17:10 Athens) by Claude Fable 5.2, after a look with its numbers (19.2), and
**corrected the same day (17:35) on the owner's words of 17:08 and 17:21: what the bot scans
of a shop passes to the site, 20,000 the most; no cap is set for each shop** (19.3); **and, by
his word of 17:35, a pass counts for three nights** (19.3.1). The build is OPUS's by
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
- 17:35, told that this section proposed a pass to count for two nights (30 today, 9.1):
  **«Και 3 βράδια μπορούμε... Αν υπάρξει κάποια έπιπλοκή κρατάμε τα προϊόντα ασκανάριστα
  μέχρι 3 μέρες»**.

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

1. **Scanned** is checked and passed in the bot's last day of asking the shop. **A pass
   counts for three nights. Owner, 22/11 (17:35): «Και 3 βράδια μπορούμε... Αν υπάρξει
   κάποια έπιπλοκή κρατάμε τα προϊόντα ασκανάριστα μέχρι 3 μέρες».** A product the bot could
   not ask again stays shown up to 3 days after its last pass; after them it is not shown
   until it passes again: it waits, it is not cut (9.3). Two nights were proposed here
   before his word. They are the 3 days the rules hold already: a shop that cannot be
   checked (5.6.2), a shop's first round (9.3). (9.1 counts a pass for 30 nights today:
   with that, a shop the bot scans 5,000 a day of would pile up to 20,000 over four days,
   each product checked once in four days, which is not what he says. With three nights
   and nothing else it would pile up to 15,000 over three: 2 below keeps a shop at what the
   bot scans of it in a day, and the three nights are for a complication, as he says.)
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
   which each keeps what it sells cheapest of every shop that sells it. (Mended by the look
   of 22/11, 20.2.2: settled once each, one shop kept 8,962 copies of what the other kept
   cheaper; the shops are now settled until no choice changes. And by the look of 23/11,
   20.7.2: of a shop that is not capped, an offer the site keeps is a row it showed the
   night before or one the checks' gate lets in; a row that waits at the gate is no cheaper
   offer yet.)
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
   the bot asks them in their turn (10.3). **Mended by the look of 22/11 (20.2.1): only
   those the cap of a category has a place for.** A shop's place open is no place open in a
   category at its size. **And by the look of 23/11 (20.7.2): the products given to the cap
   of a category for that are no part of what it counts** (1 above): they move no
   category's size and no kind's share.
3. **The order of asking** (section 10) stands. A capped shop's shown products can all be
   asked within a day: "passed within the last 30 nights" (9.1) is made three nights, by
   his word of 17:35 (19.3.1; 6 below).
4. **A shop that cannot be checked** (5.6) is out on its day 4, as before.
5. **A new shop**: the bot asks its first 20,000 by the order; what it scans and passes enters.
6. **9.1's 30 nights** become the three nights of 19.3.1 for every shop (**Owner**, 17:35;
   9.3's "not passed in 30 nights" with them): a look before the «ανέβασε» counts what that
   hides (19.7).
7. **Task 6's gate, its morning's job and its memory of what was shown** (`kind_itself`,
   built 22/11, its switch false; `docs/PICWISE_KIND_ITSELF_RULES.md`) **stand as they
   are**, after the checks' gate at the category cap; a shop's rule works before them. They
   were built before this rule and have not run with it: the looks see them together. A
   product a shop's rule leaves out is asked nothing. One that leaves by a pass over three
   nights old and comes back keeps its answer (an answer stands until another takes its
   place) and counts as no change for task 6's brakes, which count against what was shown
   the night before. To weigh, not decided: a capped shop's candidates (2 above) named to
   the morning's job as the category cap's are, so that they do not wait a night more once
   task 6's gate is on.

### 19.7 The brake, the switch, what is reported

**Proposed.**

1. **The first night cuts at least 186,900 products, by his decision.** Its look, before the
   «ανέβασε» (task 7's kind), the only measuring left (19.1, 17:16): the catalogue prepared
   on GitHub's runner with the rule; per shop what the bot scanned and what passes; what
   leaves by a pass over three nights old; each kind before and after; the first cards of the
   40 searches before and after; the preparation's time and memory.
2. **A switch** (`data/shop_cap_switch.json`, frozen with the code): false, no shop is
   capped, within one preparation. (What the rule left out does not come back with it: the
   checks' gate stands, so those products are named candidates and come back as their
   passes are read, the ones never asked as the bot asks them: 20.7.5.)
3. **The night's note** (`/prepared.json`), per shop over the cap: its products a card can
   show, kept by step, cut, candidates named. The health run prints them. Counts and shop
   names only.

### 19.8 Open: the owner's to say

Answered on 22/11: what the bot scans of a shop passes, 20,000 the most, no cap for each
shop (17:08, 17:21; 19.3); the order, with the three changes (17:15; 19.4); the bot over
several processes, built with it (17:15; 19.5); a pass counts for three nights (17:35, his
own word, told that two were proposed; 19.3.1). He asked for no more questions on it
(«τελειώσαμε με αυτό»): what follows is built as written and shown to him in the look.

1. A kind is thin under 100 products (19.4 a).
2. The proposed rules of 19.3.2, 19.3.3, 19.4 d to f, 19.6 and 19.7.

### 19.9 For the builder

- **Task 6 lives in the same step.** The preparation (`tools/prepare_catalogue.py`: `_Cap`,
  `_itself_job`, `write_itself_job`, `write_itself_shown`) carries task 6's gate, job and
  memory of what was shown, pinned by `tests/test_picwise_kind_itself.py` and
  `tests/test_picwise_prepared_catalogue.py`. Build the shop's rule beside them and keep
  them as they are (19.6.7).
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

### 19.10 Built (22/11, Claude Opus 5.5): what the code settles that this section left open

Built on the work branch, with tests; **`data/shop_cap_switch.json` is false: nothing on the
site changes, and the bot asks as before, until the owner's «ανέβασε» after the look (19.7.1)
turns it true.** (It is true from 23/11: 20.8.) No question was put to the owner and nothing
was measured (19.1, 17:16).
Task 6's code is as it was built (19.6.7): its gate, its morning's job and its memory of what
was shown, and its tests, untouched and passing.

Where:

- `src/picwise_providers/shop_cap.py`: the order of 19.4 (`ordered`), the rule in the
  preparation (`cap_shops`), the order the bot asks a shop's shown products in (`shop_order`),
  the switch (`shop_cap_on`), the note (`shop_cap_summary`).
- `tools/prepare_catalogue.py` (`_Cap._shops`, `_widened`, `_shop_cap`): the rule worked out
  before the category cap, on every product a card can show; the category cap then works on
  what the shops keep, behind the gate as it stood (the checks', and task 6's when its switch
  is on). A failure of the rule keeps every product and is said (the health run passes a
  limit).
- `src/picwise_checks/ledger.py`: `PASS_NIGHTS_SCANNED` (3) and its reason "not passed in 3
  nights" (19.3.1); `decisions(..., pass_nights, passed_over)`; `asking_order(..., scanned,
  shown_order, limit)` (19.3.2, 19.3.3).
- `src/picwise_providers/checks_applied.py`: `THREE_NIGHTS`, `passed`.
- `deployment/bot/shop_checks_bot.py`: the switch read when a round starts (`--shop-rule` for
  a look), the order read from the prepared catalogue, the most asked of a shop, the pages
  read on processes of their own (`Readers`, `--processes`), every shop at once.
- `deployment/server/print_health.py`: the bot's `shop_rule` and the preparation's
  `checks.shop_cap`, printed.
- Tests: `tests/test_picwise_shop_cap.py`, `tests/test_picwise_checks_shop_rule.py`, and the
  walk of nights (`tests/test_picwise_checks_walk.py`, class `Rules19...`): a capped shop
  shows the most and no more, the same products each night, and is asked no more; a place a
  cut leaves goes to a candidate that passed; a slow shop settles at what the bot scans of it
  in a day, the same products each night; a pass counts for three nights, then the product
  waits and is back the night it passes; with the switch off the waits of three nights are
  left aside.

Points the code settled (each **Proposed**, built so, for the look to show and the owner to
change):

1. **The order is one list.** Inside a step the passed come first (19.4 f, every night, not
   only the first: after it a shop's new products are all passed ones, so it matters only
   when the night before kept more than the most); then fair shares over the parts, taken
   round by round, the largest part first in each round (as `fair_quotas` gives the places
   left over to the largest); inside a part the clean ones first, as the category cap ranks
   them (an identity, here the code of `same_product_key`; an image; a stock state that
   varies), then the ones more than one shop sells; each rank spread over its prices by
   midpoints (the middle, the quarters, the eighths...), ties by the row's id. So the first N
   of the list are what a shop keeps with N places, and the bot asks in the same order. The
   category cap's own choosing (a number for each part, spread at that number) is not
   prefix-steady; the counts each part gets are the same, the products picked can differ.
2. **Thin** is read by the kinds of what the site kept the night before (the category cap's
   pool, as far as a card can still show them), every kind a product carries counted (as the
   look counted them); a product is of a thin kind when the smallest of its narrowest kinds
   is under 100. On a night with no pool, by every product given. On the first night that is
   today's catalogue, as the look read it.
3. **A capped shop** is one with more than 20,000 products a card can show, counted before the
   category cap (19.6.1). That count is over the rows a card can show (1.6 million on the
   server), not the 399,000 the site shows: more shops than the look's four may be over it.
   The look counts them. A shop at or under 20,000 is not touched by this rule: its products
   meet the category cap and its gate as before; what the bot scans of it shows by the three
   nights and the order of asking alone.
4. **What a capped shop keeps**, in this order, up to 20,000: what it kept the night before
   that no cheaper shop keeps (e; more than 20,000 of them, the first night, by the order, so
   the passed first); then the products that may enter (the checks' gate: passed, a candidate,
   a category, 9.4) and no cheaper shop keeps, by the order; then the kept ones a cheaper shop
   keeps; then those that may enter and a cheaper shop keeps. A dearer copy is last whatever
   its kind (a thin kind's too): it shows nothing on the site.
5. **The shops are settled by name** in the second pass (19.4 b says the smallest cap first;
   every cap is 20,000 now). **Since the look of 22/11 (20.2.2): and again, the shops whose
   choice rests on one that has since chosen otherwise, until no choice changes, five rounds
   at most (`shop_cap.SETTLE_ROUNDS`).**
6. **Candidates**: one and a quarter times the places open, the next by the order among the
   products that wait at the gate, the dearer copies last; no minimum (the category cap names
   at least 4 a kind). They go to the bot first, in their order, and to the AI's category
   (5.5) with the category cap's; not to task 6's morning job (19.6.7, to weigh). **Since the
   look of 22/11 (20.2.1): of them, only those the cap of a category names too
   (`shop_cap.vetted`): every product of a capped shop that waits at the gate is given to the
   cap of a category with the ones the shops keep, where it can take no place and is named
   only where a place is open for it.**
7. **The bot, with the switch on**: per shop, (1) the held and the failed that are due; (2)
   the shown whose row changed, and the sold-out readings about to lapse; (3) the shown asked
   before, in the order of 19.4, which the bot works out from the prepared catalogue
   (`shop_order`: every shown product read as kept, so a product another shop shows cheaper is
   last, and a kind thin by what the catalogue shows); (4) the candidates in the order named;
   (5) the shown never asked (10.4's order). Past (1), at most 20,000 of a shop (19.3.3): the
   failed products due are cut ones asked on their schedule (8.1) and are not counted. So of
   a capped shop's candidates the bot asks as many as its places open: the quarter more is
   named but not asked (19.3.3 read before 19.6.2), and a candidate that fails leaves its
   place to the next one the night after. With the switch off, as before (10).
8. **Three nights** (19.3.1): passed on a night, shown that night and the two after; then "not
   passed in 3 nights", a wait, not a cut (9.3). A pass over 30 nights old keeps its own reason.
   A candidate enters only with a pass of the last 3 nights. The bot reads the switch when a
   round starts; **with the switch off the preparation leaves aside the waits of three nights
   the bot wrote** (counted in the note, `three_nights_left_aside`), so turning it off brings
   them back within one preparation, as 19.7.2 asks.
9. **The passed** (19.4 f): the decisions name them (`passed`) only for a shop that shows more
   than 20,000, the only place they change what is kept; a list of every passed product would
   add about 400,000 keys to the file the preparation reads.
10. **Several processes** (19.5): the pages, the products' own `.js` and the catalogue's pages
    are read on 4 processes of their own, started fresh (not copied from the bot, so they hold
    no catalogue) before the catalogue is read; each holds what the bot's own reading held. If
    they cannot start (the service's sandbox), or one dies, the bot reads on its own process,
    as before, and says so in its journal and note. **Every shop is asked at once**, one thread
    each (up to 200; until now 48 at a time, the rest waiting for a shop to end): rules 4.3,
    "many shops at once", and what the bot scans is what passes. The pace a shop allows (3 s,
    its crawl-delay, one request at a time) is unchanged.
11. **The note**: the preparation's under `checks.shop_cap` in `/prepared.json` (the note's own
    keys are pinned by the preparation's tests); the bot's `shop_rule` in its note. The health
    run prints both, per shop over the most what it kept by step, and passes a limit when the
    rule was not worked out.

Not measured (the look's, 19.7.1): the preparation's time and memory with it (the rule itself
took 4 s on 300,000 made-up rows here; the category cap and the catalogue after it then work on
fewer products), the shops over 20,000 before the category cap, and what each night cuts.

## 20. The look before the «ανέβασε» of how many of a shop's products pass (22/11, Claude Fable 5.2): what it found, what was mended, its numbers

Read-only: nothing on the server or the site changed, no shop was asked, nothing was asked of
any AI. `data/shop_cap_switch.json` is false. What was mended is on the work branch, with
tests, not deployed. Each number below names its run.

### 20.1 How it looked

- **The preparation, off the server** (`deployment/server/look_shop_rule.py`;
  `.github/workflows/server-look-shop-rule.yml`, on a push of `claude/shop-rule-look` that
  changes the workflow's "Run:" line): the catalogue prepared on GitHub's runner by the
  preparation's own code (`tools/prepare_catalogue.py`), from copies of what the server
  prepared from on 22/11 (its two feed copies of 11:10 UTC, the pool of 11:28 UTC, the shops'
  catalogues, the AI's lines), with the switch off and with it on. The caps are counted
  where they are worked out: per shop, category and kind, what a card can show, what the
  shops' rule keeps, what is kept in the end, the candidates named. Each catalogue is then
  read as the site reads it and searched: every kind by its first name (312 searches), and
  the 40 searches of the measure after.
- **The run with the switch off gave the server's own catalogue to the product**: 398,957
  products of 135 shops, 134,097 with a kind. So the runner prepares as the server does.
- **The gate.** The server holds no decisions until the checks' first night is recorded
  (03:05 UTC on 23/11): there the cap's gate is still off, as on the site on 22/11. From
  23/11 it is on. So the pair was prepared a second time with the gate on, on a decisions
  file of the look's own that fails no product and lets no new one in; the AI's categories
  are applied as the preparation applies them (20,370 rows with none cut, 13,300 of them
  shown). **That pair is what the «ανέβασε» does on its day**, but for the products the
  first night itself fails. The pair with the gate off is what it would do before any night
  is recorded, and is not what will happen.
- **The night after**, the gate on: the same preparation once more from the first night's
  own pool, every candidate the caps named taken as asked and passed. It is the most that
  can enter in a night: the bot gets through fewer, not every one passes, and a new product
  enters only once the AI has given it a category (5.5; the look's AI lines are 22/11's).
- **The bot, on the server** (`deployment/server/look_bot_rule.py`): this commit's code
  unpacked in the private temporary folder of a unit with the sandbox and the memory of
  `picwise-checks.service`, which goes with the unit. It starts the processes the pages are
  read on, reads the catalogue as the bot reads it, works out the order of 19.4 and what the
  bot would ask with the rule off and on, and counts what the round running has answered. No
  shop is asked, nothing is written; the real round went on beside it.
- **Runs**: 45050561292 (the code as built), 45053630532 (20.2.1 mended; the night after),
  45058022788 (20.2.2 mended too). Tests: `tests/test_picwise_look_shop_rule.py` (18).

### 20.2 Found and mended on the work branch, with tests

1. **A capped shop's candidates were named for the shop's own places open, whatever their
   category** (19.6.2, 19.10.6). **Seven shops, not four, have more than 20,000 products a
   card can show, counted before the cap of a category** (20.4): Finediam, Tirendo UK and
   Tyres UK too, which the site shows 6,619, 1,431 and 1,337 products of, since the cap of a
   category has no more places for them. As built, each named one and a quarter times its
   own places open: 16,727, 23,212 and 23,329 candidates, 63,268 between them, and 86,329
   for the bot in all (run 45050561292). A category at its size takes none of them. Walked
   through nights (`tests/test_picwise_checks_walk.py`), such a candidate is asked, passes,
   is let into the shop's places, is refused by its category, and is named again two nights
   later, for good: thousands of requests a day to a shop for products that can never be
   shown, and the cap's own candidates of that shop, which do have a place, asked after
   them. **Now** every product of a capped shop that waits at the gate is given to the cap
   of a category with the ones the shops keep (`ShopCapResult.waiting`). It can take no
   place there (the gate); the cap names it a candidate only where a place is open for it,
   and a shop's candidates are those, in its own order, as many as it may name
   (`shop_cap.vetted`; `tools/prepare_catalogue.py`, `_Cap.__call__`). The three name 1,502,
   4,211 and 4,286, and the bot is given 31,961 candidates in all (run 45058022788). The
   night after, 14,798 products had entered and 14,649 more were named: the candidates
   enter and their number falls.
2. **Two shops with one catalogue kept the same products** (19.4 b, 19.10.5). GamingKit and
   PCHUB.UK sell the same 307,000 rows, PCHUB.UK the cheaper. Each shop was settled once
   against what the others kept in the first pass. PCHUB.UK, settled after GamingKit, then
   chose otherwise, since the shops whose cheaper offers it had counted kept only some of
   them. So GamingKit's choice rested on a choice no longer there: **8,962 of its 20,000
   places held copies of what PCHUB.UK keeps cheaper**, which show nothing (one product is
   shown once, from the cheapest; owner, 16/10), and its note called them its cheapest. The
   night after showed them (run 45053630532). **Now** a shop whose choice rests on a shop
   that has since chosen otherwise is settled again, until no choice changes, five rounds at
   most (`shop_cap.SETTLE_ROUNDS`); a shop that shares no product with another capped shop
   is settled once. GamingKit keeps 138 such copies, the fewest it can: of the 46,240
   products the site shows of it, only 19,862 are kept cheaper by no other shop (run
   45058022788; the same 138 the night after). With it the kind `ram_memory` keeps 1,853
   products where it kept 457.

### 20.3 Found, not mended: each a later step

1. **The first night, the passed do not come before the never asked** (19.4 f). The bot
   names the passed only while its round runs with the switch on, and only for a shop that
   shows more than 20,000 (19.10.9). The «ανέβασε» prepares before the bot starts again, from
   the decisions of a round that ran with the switch off: they name none. So the first
   night each of the four keeps its 20,000 by the order alone. After that night none of them
   shows more than 20,000, so the bot never names any. What it costs: the bot's work of the
   days before on the four (24,675 of their 266,900 products asked by 19:00 UTC on 22/11,
   about a fifth by the end of that night at its pace) is not what decides which stay; the
   20,000 kept are asked in the day or two after. From the
   shops' day 4 (26/11) a product never asked is not shown (9.3), so an «ανέβασε» from that
   day on finds only checked products to choose among.
2. **A full shop names no candidate, so 19.4 e's second sentence is not reached**: a kept
   product that a cheaper shop comes to keep holds its place, last in the shop's order,
   since no product is ever asked for it. GamingKit's 138 are of this kind. (On the real
   night of 23/11 they are 4,477: 20.7.4.)
3. **A candidate enters only once the AI has given it a category** (5.5). The first days
   after the «ανέβασε» the AI's morning job is asked tens of thousands of products, not a
   few thousand: its $10 a night stands (7.6); what it costs is to be read those mornings.
4. Corrected in the records only: the handoff said a round running keeps the old order
   until the next morning. A deployment that prepares stops the bot and starts it again
   (`deploy.sh`), and the round started again reads the switch then: it goes on with the rule
   on, from the answers it kept.

### 20.4 The numbers

**The shops over 20,000 products a card can show, counted before the cap of a category**
(run 45058022788, the gate on):

| shop | a card can show | shown, the switch off | the rule keeps | shown, the rule on | candidates for the bot |
|---|---|---|---|---|---|
| Finediam | 357,936 | 6,619 | 6,619 | 6,619 | 1,502 |
| PCHUB.UK | 306,871 | 46,053 | 20,000 | 20,000 | 0 |
| GamingKit | 306,854 | 46,240 | 20,000 | 20,000 | 0 |
| Tooled Up | 209,588 | 66,241 | 20,000 | 20,000 | 0 |
| InStock UK | 153,562 | 99,013 | 20,000 | 20,000 | 0 |
| Tirendo UK | 39,494 | 1,431 | 1,431 | 1,431 | 4,211 |
| Tyres UK | 30,713 | 1,337 | 1,337 | 1,337 | 4,286 |

- **The catalogue: 385,657 products to 208,110** (177,547 fewer), 134 shops before and
  after; with a kind 129,264 to 106,474. Only the four change what the site shows of them.
  By step, of each one's 20,000: InStock UK thin kinds 811, cheapest kept 1,809, with a kind
  16,236, the rest 1,144; Tooled Up 336, 2,348, 17,316; PCHUB.UK thin kinds 233, cheapest
  kept 19,767; GamingKit cheapest kept 19,840, with a kind 19, the rest 3, a cheaper
  shop's 138.
- **The categories**: over their size 16 before, 6 after. The four's categories empty out:
  electronics > computers 11,334 to 3,610; hardware > tools 11,636 to 4,431; hardware > tool
  accessories 11,651 to 138; vehicles & parts > vehicle parts & accessories 11,641 to 4,330.
  The places left are for other shops' products that pass their checks.
- **The kinds** (289): none is left without a product. Under 4 products 16 before and 19
  after (car_audio 6 to 3, e_reader 4 to 2, printer_paper 6 to 3); under 24, 61 and 63
  (game_console 37 to 22, smoke_detector 32 to 20); under 100, 109 and 118. **17 lose over
  half**: ram_memory 4,662 to 1,853, headphones 4,060 to 1,946, ink_cartridge 3,243 to
  1,542, printer 1,656 to 328, label_printer 1,310 to 498, toner 1,284 to 588, phone_charger
  1,132 to 507, storage_drive 1,035 to 434, access_point 951 to 455, television 869 to 388,
  projector 843 to 412, router 815 to 392, desk_phone 680 to 311, scanner 476 to 215,
  power_supply 419 to 204, spanner 187 to 55, soundbar 63 to 31.
- **Every kind searched by its first name** (312): the same first 4 cards in 262, the same
  Recommended in 263; none with cards before and none after; none with 4 cards before and
  fewer after. The searches that lose the most products: "monitor" 1,482 to 1,195, "cable"
  1,220 to 975, "toner" 714 to 516, "ink cartridge" 1,375 to 1,246, "spanner" 118 to 38.
  Some show more, since two shops no longer show the same products: "headphones" 1,400 to
  1,519, "camera" 796 to 831.
- **The 40 searches, their first 12 cards**: the same in 25; they differ in 15 (router,
  monitor, tv, laptop, headphones, speaker, keyboard, mouse, printer, camera, phone charger,
  drill, jacket, shampoo, backpack). The Recommended is the same in 25.
- **The night after, every candidate passed** (the most that can enter): 208,110 to
  222,908; tyres 2,391 to 6,711, shoes 9,490 to 10,576, cable 1,764 to 2,676; no kind loses.
  Finediam 6,619 to 7,590, Tirendo UK 1,431 to 2,645, Tyres UK 1,337 to 4,443. Of the 31,961
  candidates, 9,791 are of Plusshop UK, Bazta UK and TV Cables, which the bot cannot check
  (section 17): those do not enter.
- **Before any night is recorded** (the gate off, as on the server on 22/11; run
  45058022788): 398,957 to 239,129, and new products never checked enter the places the four
  leave (TV Cables 3,663, Tyres UK 3,519, Tirendo UK 3,077, Bazta UK 2,602, Plusshop UK
  2,584); the 40 searches show the same 12 cards in 19. An «ανέβασε» before the first night
  is applied (04:17 UTC on 23/11) would do this; after it, it does not.
- **The preparation's time and memory, on the runner** (4 processors, 15 GB; the server's
  own run of 22/11 took 28.4 minutes, peak 15.08 GB; twelve preparations in the three runs):
  the caps take 33 to 43 s without the rule and 39 to 73 s with it (73 s with the gate on
  and both mends); the catalogue built and written after them takes 94 to 128 s without the
  rule and 79 to 88 s with it, being smaller. So the rule adds and saves about the same.
  Whole runs: 13.3 to 18.8 minutes without it, 14.6 to 18.7 with it; the same job took
  13.3 minutes on one runner and 18.8 on another, so the whole runs tell no difference.
  **Peak memory 0.6 GB lower with the rule** (14.49 to 13.90 GB; 14.70 to 14.10 GB with the
  gate on).
- **The bot on the server** (three looks, 17:38, 18:11 and 18:58 UTC): "the pages are read
  on 4 processes of their own", 4 of 4 answering at once, inside the unit's sandbox
  (`PrivateDevices`, `ProtectSystem=strict` and the rest). The catalogue read and the order
  of 19.4 worked out for 398,957 products in 57 s; the unit's memory at its peak 1,891 MB of
  its 4,096 (the readers take 11 MB each). The round running held 2,531 MB after 7.3 hours
  and 136,662 answers.
- **What the bot scans of a shop in a day** (the round running, which asks every shop at
  once on one process; a day of asking is 21 hours 35 minutes): seconds a request over the
  round's first 7.3 hours, and over the 80 minutes between the looks: InStock UK 3.6 and
  3.4, about 21,600 to 22,600 a day; Tooled Up 3.6 and 3.6, about 21,300 to 21,800;
  GamingKit 4.5 and 4.3, about 17,300 to 17,900; PCHUB.UK 6.6 and 6.3, about 11,700 to
  12,300. **So by 19.3 GamingKit and PCHUB.UK settle under 20,000**, at what the bot scans
  of them in a day and passes: PCHUB.UK's own pages called 25 to 29 in 100 sold out
  (section 17). InStock UK: 926 of the 7,365 asked that day were gone from its site.

### 20.5 Not measured

- **What leaves by a pass over three nights old** (19.7.1): there is no ledger until the
  first night is recorded, and no pass can be three nights old before the night of 26/11.
  Which shops it touches is read from the pace above: GamingKit and PCHUB.UK are not asked
  whole within a day; every other shop the bot can check is (the largest of them, Back to
  the Office, 11,280 products, within the round's first 6 hours).
- **The preparation's time on the server**: only a deployment prepares there. The health
  run says it the morning after (its limit is 30 minutes).
- **The bot's pace with the pages read on 4 processes**: only the round after the «ανέβασε».
- **The first real night's decisions**: the look is run once more on 23/11, when the server
  holds them (the same workflow: its first pair is then the real one, and the pair on the
  look's own decisions is not run). **Done: 20.7.**

### 20.6 For the «ανέβασε»

- Not before the checks' first night is recorded and applied (23/11, 04:17 UTC): 20.4,
  "before any night is recorded".
- The look once more on the real decisions first (20.5), read against 20.4.
- As the handoff says: the site restarted first by a fast-forward to a commit that does not
  concern the catalogue, then the commit that turns the switch; the bot starts again with
  the rule on (20.3.4); the standing texts change with it (19.9).
- What it carries besides the rule: task 6's code with its switch false, and its meter,
  which starts measuring (`docs/PICWISE_KIND_ITSELF_RULES.md`: $2 a day at most).

### 20.7 The look once more, on the checks' first real night (23/11, Claude Fable 5.2)

**Read-only, as on 22/11; nothing deployed, the switch false.** Runs 45119398312 (the code
as mended on 22/11; the server's files copied 05:42 UTC) and 45123975734 (after the two
mends of 20.7.2; copied 06:27 UTC); the health run by hand, 45119975809 (`main`) and
45120579013 (the deployed branch's own script, which says the checks).

#### 20.7.1 The first night itself, and what moved under the look

- **The checks' first night** (recorded 03:05 UTC, applied by the preparation of 04:17):
  135 shops asked; decided 141,330 products, passed 137,360, failed 3,970 (gone 3,084, moved
  503, no answer 166, price far apart 108, not a product page 78, another product 31); cut
  2,396, the rest held by the brakes (a kind's 355, the owner's 868, a shop's 351: Dean
  Morris Cards, Happy Days Factory Flowers, Optimum Nutrition UK). Nine shops cannot be
  checked, day 1 (section 17). usmile out by Awin's reading (94 products).
- **Applied**: 22,637 products cut (20,255 of them with no category of the AI's), 122 not
  shown until checked, 2,716 at the price of the shop's own page; no new product entered
  (the gate). **The catalogue: 398,957 products of 135 shops to 374,859 of 132.**
- **The preparation on the server took 32.2 minutes, peak 14.6 GB: over the health run's 30
  minutes** (28.4 on 22/11; the unit's own limit is 60), before any of this rule. The site
  held 9.0 GB after reading the night's catalogue (7.3 on 22/11): 23.6 GB together, over
  the health run's 20 as on 22/11 (21.7).
- **The AI's categories of that morning came after the preparation** (`picwise-shelves`,
  05:20 UTC: 27,956 asked and $2.03 by 05:54; more answers in its file by 06:27). The
  look's copies hold them, so its "switch off" is the catalogue the server would prepare
  next from that morning's files, not the one it showed that morning: **362,432 products at
  05:42 (29,274 with no category), 355,114 at 06:27 (35,854)**. Two things in it, neither
  of this rule: 15,600 more products cut for no category than the server cut that morning;
  and the products that got a category now stand in it and share its places: "electronics >
  computers" keeps 3,277 where it kept 11,334 on 22/11's files (a card can show 347,350 of
  it against 385,420), "electronics > electronics accessories" stays at its size with
  176,744 a card can show against 156,220, and `ram_memory` is 219 products where it was
  4,662, `ink_cartridge` 1,679 where 3,243. **The numbers of 20.4 are therefore not the day's:
  read 20.7.3.**

#### 20.7.2 Found and mended on the work branch, with tests

1. **The night after the first with the rule, products shown the night before left, and
   candidates that had passed were refused** (run 45119398312: with 33,836 candidates
   taken as passed the catalogue grew by 3,192; GamingKit showed 800 fewer of the products
   it showed the night before, Tooled Up 235, Tirendo UK 213, PCHUB.UK 172, Tyres UK 152,
   InStock UK 26; Tirendo UK kept 2,671 by the shops' rule and 1,218 by the cap of a
   category, fewer than the night before). The
   cause is the mend of 20.2.1: it gave the cap of a category every product of a capped
   shop that waits at the gate, to name the candidates a place is open for, and the cap
   counted them like the rest: in its categories' sizes and in each kind's share. On
   22/11's files the four large shops were full after the cap of a category and offered
   nothing the night after; on the real night it takes a few of their 20,000 (a kind over
   its share), each then has places open, and its waiting rows, 880,000 between the four,
   moved every kind's share in their categories from one night to the next. **Now** they
   are given as `offered` (`catalogue_cap.cap_catalogue`; `tools/prepare_catalogue.py`): the
   cap counts what the shops keep, as 19.6.1 says; none of the offered is kept; they are
   named only for the places their kind has open (a category over its size) or for the
   places the category would still have were they counted in it (one under its size), one
   and a quarter times, at least 4 (`c340e1b`). After it (run 45123975734): the night after
   the catalogue grows by 17,901 and one shop shows one product fewer; the night after
   that it grows by 3,644 and two shops show 2 fewer each.
2. **A cheaper row that waits at the gate counted as a cheaper offer.** For the shops that
   are not capped the shops' rule read every row a card can show ("they keep every
   product"); with the gate, 109,000 of their 224,000 rows wait and show nothing. A capped
   shop's product was put last for such a row. **Now** a row of a shop that is not capped is
   an offer the site keeps when it was shown the night before or the gate lets it in
   (`shop_cap.cap_shops`, `fa2e8e0`). What it changed on the day's files: little (GamingKit's
   products a cheaper shop keeps, 4,671 before and 4,477 after, the files having moved too);
   it is the rule's own wording (19.4 b), kept for the nights when it matters.

Tests: three in `tests/test_picwise_catalogue_cap.py` (`OfferedTests`), a walk of nights in
`tests/test_picwise_checks_walk.py` (two kinds in one category: counted as before, a kettle
shown the night before left), one in `tests/test_picwise_shop_cap.py`; the 22 modules around
the caps and the preparation pass (328 tests); GitHub's "Tests" green on `cb5ce0d` (both
branches). The look itself now prepares one night more ("two nights after"), to see that
what a night shows stays the next.

#### 20.7.3 The numbers, the real first night (run 45123975734, both mends)

| shop | a card can show | shown that morning | shown, the switch off | the rule keeps | shown, the rule on | candidates for the bot |
|---|---|---|---|---|---|---|
| Finediam | 357,579 | 6,465 | 6,287 | 6,465 | 6,465 | 1,125 |
| PCHUB.UK | 298,161 | 42,418 | 36,625 | 20,000 | 19,968 | 0 |
| GamingKit | 297,500 | 41,990 | 36,851 | 20,000 | 18,818 | 0 |
| Tooled Up | 208,848 | 65,948 | 63,073 | 20,000 | 18,628 | 0 |
| InStock UK | 153,713 | 97,644 | 97,030 | 20,000 | 19,887 | 0 |
| Tirendo UK | 39,497 | 1,431 | 1,178 | 1,431 | 1,431 | 4,288 |
| Tyres UK | 30,448 | 1,322 | 1,118 | 1,322 | 1,322 | 4,153 |

("Shown that morning": of the server's catalogue, what a card can still show. The cap of a
category takes a few of the four's 20,000, a kind over its share; the places are named for
candidates the next night.)

- **The catalogue: 355,114 products to 199,771** (155,343 fewer), 132 shops before and
  after; with a kind 110,404 to 98,235. **Only the four lose** (InStock UK 77,143, Tooled Up
  44,445, GamingKit 18,033, PCHUB.UK 16,657); 18 other shops show a few more (Tirendo UK
  253, Tyres UK 204, Finediam 178, TV Cables 135), none fewer. By step, of each one's
  20,000: InStock UK thin kinds 769, cheapest kept 1,832, with a kind 16,088, the rest
  1,311; Tooled Up 340, 2,681, 16,979; PCHUB.UK thin kinds 148, cheapest kept 19,852;
  GamingKit thin kinds 6, cheapest kept 15,200, with a kind 58, the rest 259, **a cheaper
  shop's 4,477** (20.7.4).
- **The categories**: over their size 17 before, 6 after. hardware > tools 11,168 to 3,961;
  hardware > tool accessories 11,691 to 198; electronics > print, copy, scan & fax 11,274
  to 4,783; electronics > video 11,043 to 5,122; home & garden > decor 11,574 to 5,668;
  health & beauty > personal care 11,381 to 6,699; vehicles & parts > vehicle parts &
  accessories 9,635 to 4,373; apparel & accessories > clothing 11,435 to 8,229; electronics
  > computers 3,277 to 1,092.
- **The kinds** (289): none is left without a product. Under 4 products 18 before and 19
  after (printer_paper 4 to 2); under 24, 63 and 63; under 100, 113 and 118 (amplifier 130
  to 32, car_charger 113 to 71, microphone 197 to 94, software 161 to 84, spanner 175 to
  57). **14 lose over half**: headphones 4,024 to 1,921, printer 1,300 to 176, label_printer
  1,258 to 452, access_point 938 to 468, router 843 to 415, television 835 to 334,
  desk_phone 667 to 287, server 481 to 228, scanner 472 to 188, speaker 447 to 192,
  firewall 269 to 123, microphone 197 to 94, spanner 175 to 57, amplifier 130 to 32. Some
  gain, their kind's share no longer counted over rows the four do not show: tyres 1,919 to
  2,376, trousers 1,057 to 1,461, cable 884 to 1,142, ram_memory 219 to 476, docking_station
  381 to 594.
- **Every kind searched by its first name** (312): the same first 4 cards in 250, the same
  Recommended in 257; none with cards before and none after. "monitor" 1,478 to 1,223, "ink
  cartridge" 941 to 809, "motherboard" 531 to 432, "spanner" 101 to 39.
- **The 40 searches, their first 12 cards**: the same in 26; they differ in 14 (router, car
  tyres, monitor, tv, tablet, headphones, keyboard, mouse, camera, phone charger,
  smartphone, drill, jacket, backpack). The Recommended is the same in 28.
- **Candidates for the bot**: 34,148 of 82 shops (31,425 with the switch off: the places
  the first night's cuts and the AI's categories opened are named either way). Of them
  7,161 are of Plusshop UK, Bazta UK and TV Cables, which the bot cannot check.
- **The night after and the one after it, every candidate taken as passed** (the most that
  can enter): 199,771 to **217,672** to **221,316**. The night after, 72 shops show more
  (Tyres UK 3,066, Back to the Office 2,793, Bazta UK 1,454, Shopping Ads: Google & Bing
  1,355, Tirendo UK 1,291, TV Cables 1,276) and one shows one product fewer (Tooled Up);
  the kinds: tyres 2,376 to 6,733, storage_drive 381 to 1,227, ram_memory 476 to 954, none
  loses over half; the 40 searches show the same 12 cards in 28. Two nights after:
  GamingKit 18,818 to 19,898, Tooled Up 18,627 to 19,241, Tyres UK 4,388 to 5,427, PCHUB.UK
  at 20,000; two shops show 2 products fewer each; the same 12 cards in 32. (Bazta UK and
  TV Cables cannot be checked: theirs do not enter.)
- **The preparation on the runner**: the caps 39 s with the switch off; with the rule 87,
  98 and 91 s on a runner that took one and a half times as long for everything (722 s to
  reach the caps against 482); on 05:42's run, the code as mended on 22/11, 39 s against 51
  on like runners, and the whole preparation 13.6 minutes against 10.7. Peak memory 14.53
  GB without the rule, 14.09 to 14.33 with it. **Nothing here says what the server's 32.2
  minutes become**; the catalogue to build and write after the caps is a little over half.
- **The bot on the server** (05:42 and 06:25 UTC, the round of 23/11 running): 4 of 4
  processes answer at once inside the unit's sandbox; the catalogue of 374,859 read and
  ordered in 53 s; the unit's memory at its peak 1,801 MB of 4,096. The ledger after its
  first night: 172,928 products, 157 shops. With a pass counting for 3 nights the decisions
  hold back none yet (no pass is three nights old before 26/11) and name 43,652 products as
  passed for the shops over 20,000. With the rule on it would ask 209,074 products of 134
  shops that day, against 389,801. Seconds a request over the round's first 55 minutes:
  GamingKit 4.5, PCHUB.UK 6.3 (as on 22/11); Tooled Up 3.9, InStock UK 5.5 (its first
  requests of the day are the failed ones due again).

#### 20.7.4 Found, not mended then: a later step (1 below is built 23/11, section 20.9)

1. **GamingKit keeps 4,477 products a cheaper shop shows** among its 20,000 (4,694 and
   4,717 the two nights after): 20.3.2, no longer small. Of the products it showed that
   morning, 15,523 are what no other shop keeps cheaper; the rest of its places go to
   copies, which show nothing, and a full shop names no candidate for them. Left as it is,
   the bot's pace settles part of it: GamingKit is asked about 17,300 a day, a product a
   cheaper shop shows is last in its order (19.3.2), so about 2,600 of the copies are not
   asked again and leave after three nights; about 2,000 stay and are asked every day.
   **To mend (two halves, neither built):** in `shop_cap.cap_shops`, count a place held by
   a product of the step "a cheaper shop's" as open when naming the shop's candidates, the
   candidates for those only among the ones no cheaper shop keeps (19.4 e's second
   sentence); and in `ledger.asking_order`, with the rule on, ask a shop's candidates
   before its shown products a cheaper shop shows (`shop_cap.shop_order` knows which: they
   are the last of its order), or the candidates of a shop the bot cannot scan whole in a
   day are never reached. What it would gain: about 2,000 to 4,500 products of GamingKit
   shown that are not shown elsewhere.
2. 20.3.1 and 20.3.3 stand as written. Of 20.3.3: the AI's morning of 23/11 was asked
   27,956 products for $2.03 by 05:54 UTC and went on; with the rule the candidates named
   are 34,148 against 31,425 without it, so the rule adds little to that.

#### 20.7.5 For the «ανέβασε»

- The look reads right after the two mends: only the four lose products the first night,
  and the two nights after no shop shows fewer but three, by 5 products in all.
- **Turning the switch off does not bring the products back at once** (19.7.2). The checks'
  gate stands: what the rule left out is no longer in the memory of the night before, so
  it is named a candidate for the places open, a product whose pass still counts enters
  the night after it is named (two preparations), and one never asked enters when the bot
  has asked it (InStock UK's 77,000 at its 20,000 or so a day). By the code; not measured.
- The numbers move with the AI's categories of the day (20.7.1): the day's own numbers are
  the preparation's note the morning after (`checks.shop_cap`, the health run).
- 20.6 stands: the site restarted first, then the commit that turns the switch; the bot
  starts again with the rule on; the standing texts change with it (19.9); it carries task
  6's code with its switch false, and its meter starts ($2 a day at most).

### 20.8 The «ανέβασε» (23/11): how it went, and what the mornings after read

- **Owner, 23/11 (10:31 Athens), told the numbers of 20.7.3, what is left (20.7.4), that the
  products do not come back at once (20.7.5) and what the deployment carries: «Ποια είναι η
  άποψή σου». Answered: to deploy that day** (what is not known shows only live: the bot
  with the rule, the preparation's time on the server, the three nights; a mistake costs
  little now, with about 30 searches a day and nothing declared to Google; it does what he
  asked; and it eases the server); the reserve told with it (one of the day's two mends was
  of the session's own mend of the day before: no promise that there is no other), and that
  the surest way was to wait a day more. **10:34: «Ανέβασε το».**
- **The switch true** in `7ba917c` (`data/shop_cap_switch.json`: `cap` true, `set`, `by`), the
  test that pinned it off now pinning his word. Before it: every fast module on its own,
  355 modules, 3,387 tests, 353 pass, 2 fail as known; GitHub's "Tests" on that commit, every
  module but the two slow ones, green (run 45141548329; the two slow ones, of the search's
  index and its learning, green on `cb5ce0d`, which they do not differ from).
- **Two fast-forwards of the site's branch, for the server's memory** (as on 22/11):
  `0e3a683` (08:58 UTC, run 45142919631: "not prepared again: the change does not concern
  the catalogue", the site restarted, 15 of 15 pages the same), then `7ba917c` (09:02 UTC, run
  45143440046, release `20261123T090212Z-7ba917c`): the bot stopped, the catalogue prepared
  in **26.9 minutes, peak 14.0 GB** (32.2 minutes and 14.6 GB that morning, without the
  rule), the site restarted on it at 09:31 UTC, 15 of 15 pages answering, the bot started
  again. The deployment's job may take 75 minutes from this commit (it was 45, under the
  preparation's own 60 on the server).
- **The catalogue: 199,771 products of 132 shops, the look's number to the product**
  (20.7.3). 7 shops over 20,000, 1,296,528 of their products left out; InStock UK, Tooled Up,
  GamingKit and PCHUB.UK 20,000 each by the rule, the cap of a category then taking a few;
  GamingKit's "a cheaper shop's" 4,477; candidates for the bot 34,148 (9,566 of the capped
  shops); 38,236 products cut by the checks (35,854 with no category); for the AI the next
  morning 12,031 questions (15,605 products).
- **The health run after it** (45148116992): within every limit but the three shops' brake,
  which is the owner's (20.7.1). The preparation 26.9 minutes; the site 4.4 GB (9.1 before),
  18.4 GB with the preparation's peak (23.8 before; the limit is 20); 17.8 GB available.
- **The bot** (run 45148112347): stopped 09:02 UTC with its answers kept, started again
  09:31: "the pages are read on 4 processes of their own"; "the night of 2026-11-24: 199,771
  products shown, 34,148 candidates, 2,476 cut ones the feed still lists"; "to ask: 234,426
  products of 137 shops; 96,180 answered already tonight (the round goes on)".
- **With it**: task 6's code, its switch false (the health run: "kind itself: its answers
  are not read"); its timers in place: `picwise-itself` (05:40 UTC; nothing to ask while its
  switch is false) and `picwise-meter` (06:20 UTC: the first cards of the fixed searches
  judged by Claude Opus 5.5, $2 a day at most; its first morning is 24/11).
- **To read the morning after (24/11) and the next days**, the health run started on the
  site's branch: "checks, how many of a shop's products pass" (the four near 20,000,
  GamingKit's "a cheaper shop's", the candidates); no shop but the four with fewer products
  than the day before for this rule; the preparation's minutes and the memory together; the
  bot's note of its first night with the rule ("on; a pass counts for 3 nights; at most
  20,000 asked of a shop; N shops at once, pages read on 4 processes") and its pace on 4
  processes (20.5); what the AI's categories cost; the meter's first line. From 26/11: what
  leaves by a pass over three nights old, and the nine shops that cannot be checked.
- **If a night goes wrong**: the switch false on the owner's word and a deployment (it
  prepares: the site restarted first); 20.7.5 says how the products come back.

### 20.9 The places a full shop's own copies hold: mended (23/11, the daily session, Claude Opus 5.5). BUILT AND TESTED, LOOKED AT (20.10), NOT DEPLOYED

20.7.4's first item, the one thing the look of 23/11 left: **a shop whose cap is full of
products a cheaper shop shows keeps places that show nothing and names no candidate for
them**, so nothing is asked that could fill them. GamingKit held 4,477 such places of its
20,000 on the night of 23/11 (4,694 and 4,717 the two nights after), and its candidates were
0. Both halves 20.7.4 named are built, with their tests; **nothing is on the site: it waits
for the owner's «ανέβασε»** (it changes what the bot asks and what the preparation names, so
it belongs with a deployment, not on its own).

1. **The cap (`shop_cap.cap_shops`, `name_candidates`).** A place held by a product of the
   step "a cheaper shop's" counts as open when the shop names its candidates (one and a
   quarter times, as for a place truly open), and **the candidates for such a place are only
   products no cheaper shop keeps** (19.4 e's second sentence), or the shop would ask for a
   place that shows nothing again. A shop's truly open places name as before, among every
   product that waits, its own copies included: `ShopCapResult.allowed` is what it may name in
   all, `allowed_dearer` how many of them may be copies (0 for a full shop).
2. **The bot's order (`ledger.asking_order`, `dearer`).** With the rule on, a shop's shown
   products that a cheaper shop shows are asked **after** the cap's candidates, not before:
   they are the last of its order (`shop_cap.shop_order`, which now says which they are), and
   a shop the bot cannot scan whole in a day (GamingKit is asked about 17,300 of 20,000 a day)
   never reached its candidates. The bot reads them from the prepared catalogue with the order
   (`shop_checks_bot.rows_from_catalogue`).
3. **And, found while building it: a product no place of a shop can ever name is no longer
   given to the cap of a category.** Every product of a capped shop that waits at the gate
   goes on to the cap of a category to be named among (19.6.2, the look of 22/11). With the
   mend the four full shops would have sent their copies too — about 710,000 rows on 23/11,
   which the preparation would hold in memory to name none of them (a full shop's
   `allowed_dearer` is 0). A shop with no truly open place now offers only the products that
   can be named. The catalogue is not changed by it (what is offered is counted for nothing
   and kept never, the look of 23/11): only the preparation's work and memory.

What it should gain, by 20.7.4's reading of the night of 23/11: **about 2,000 to 4,500
products of GamingKit shown that no other shop shows**, in the days after the deployment (its
candidates are asked, pass, and enter the night after they are named). Not measured: the look's
workflow reads the server's catalogue, and the numbers of the day move with the AI's categories
(20.7.1), so what it is worth shows in the health run's "checks, how many of a shop's products
pass" the mornings after.

**Tested**: `tests/test_picwise_shop_cap.py` (a full shop names candidates again and only ones
that can show; the cap of a category names among them under the same rule; `name_candidates`
itself), `tests/test_picwise_checks_shop_rule.py` (the shown a cheaper shop shows asked after
the candidates; with the rule off nothing changes). Every fast module on its own after it: its
numbers are in `PROGRESS.md`'s entry of the day.

### 20.10 The look at the mend of 20.9, on the server's data (23/11, afternoon, Claude Fable 5.2): it does what it says; two things found, each a later step

On the owner's «Ναι» (13:15 Athens) to the advice that the mend be looked at on the server's
data before its «ανέβασε» (the two looks of the rule had found four defects its tests had
not). Run 45165463672 (`claude/shop-rule-look` at `a2aeba1`, 11:28 to 12:12 UTC). Read-only:
no shop asked, no AI, nothing on the server or the site changed.

#### 20.10.1 How it looked

The look's workflow set the switch off against the switch on; the rule is live, so it now
sets **a change to the rule against the code the site runs** (`server-look-shop-rule.yml`,
`deployment/server/look_shop_rule.py`, `look_bot_rule.py`; `tests/test_picwise_look_shop_rule.py`):

- Two runs from the same copies of what the server prepared from (the same to the byte: the
  feed's two copies, the pool of the 199,771 products the site shows since 09:21 UTC, the
  decisions of the night of 23/11, the AI's lines). "site": the catalogue prepared by the head
  of the site's branch (`7ba917c`, without the mend), in a folder of its own on the runner.
  "mend": by the work branch's head (`a2aeba1`, which holds `2a264ba`). The rule on in both.
- Each then lives the two nights after by its own code, every candidate the caps named taken
  as asked and passed: the most that can enter in a night, not what the bot gets through.
- Every summary and comparison by one code. A summary now counts, on its own and not through
  `shop_cap`, the products a cheaper shop shows too (`look_shop_rule.copies_by_shop`: the same
  product by its code, in another shop, at a lower price): its count and the rule's own
  agreed to the product on every night (GamingKit 4,476, 4,707, 4,744 by the site's code;
  4,476, 2,680, 885 by the mend).
- The bot's look on the server, in its unit's limits, now says where each shop's candidates
  stand in what it is asked, its products a cheaper shop shows asked after them (the mend) and
  among its shown (before it): `look_bot_rule.candidates_standing`.

#### 20.10.2 What it found

- **The night it is deployed nothing shown changes.** The first night (tonight's, if nothing
  more passed): 199,770 products of 132 shops by both codes (the site shows 199,771); no
  shop's count differs; the same 20,861 products a cheaper shop shows; the same categories and
  kinds; the same cards in all 312 kinds' own searches and in all 40 searches.
- **The candidates: 31,368 by the site's code, 36,963 by the mend: 5,595 more, every one
  GamingKit's** (1,478 to 7,073). Of the 18,818 it keeps, 4,476 are a cheaper shop's and 1,182
  places are open: it may name 7,345, and the cap of a category has a place for 7,073.
- **The night after** (every candidate passed): GamingKit keeps 20,000 by both; a cheaper
  shop's among them 4,707 by the site's code, 2,680 by the mend: **it shows 17,320 products no
  cheaper shop shows, 15,214 without the mend (+2,106)**. The catalogue's products that show:
  193,244 and 195,353 (+2,109). No shop has fewer products by the mend (GamingKit +79 and
  PCHUB.UK +3: the cap of a category cuts none of theirs).
- **Two nights after**: GamingKit's a cheaper shop's 4,744 and 885: **it shows 19,115, 15,213
  without the mend (+3,902)**. The catalogue's products that show: 197,600 and 200,853
  (+3,253). The catalogue holds 599 fewer rows by the mend (220,561 and 219,962): 3,852 fewer
  that show nothing, and fewer of TV Cables (1,481 and 793), Bazta UK (13,238 and 13,185) and
  Tirendo UK (3,096 and 3,083): 20.10.4.
- **What a night shows stays the next**: by the mend, from the night after to two nights
  after, no shop loses more than one product (by the site's code, two).
- **The searches**, two nights after, the mend against the site's code: "monitor" 1,709
  products for 1,378, "laptop" 578 for 567, "watches" 1,084 for 1,074; the kinds monitor
  (1,997 rows for 1,549), ink_cartridge (1,357 for 1,215), cable, ram_memory. Of the 312
  kinds' own searches 27 find more products and 19 fewer (20.10.3, 20.10.4).
- **The preparation**: 12.4 to 12.5 minutes and 14.18 to 14.33 GB at its peak by the mend;
  13.2 to 13.5 minutes and 14.13 to 14.32 GB by the site's code, on GitHub's runner (15 GB).
  No difference: the mend's third part (20.9, 3) holds on these nights.
- **The bot** (on the server, 11:28 UTC): the order worked out in 3 s, 1.0 GB of the unit's 4.
  20,861 shown products of 23 shops are a cheaper shop's (Plusshop UK 7,431, Bazta UK 6,150,
  GamingKit 4,476, Back to the Office 929, Lightsin UK 566, PCHUB.UK 505). With the mend a
  shop's candidates stand before them: Plusshop UK's first candidate after 5,300 products
  (after 12,711 before the mend), Bazta UK's after 5,709 (11,828), Back to the Office's after
  6,576 (7,505). GamingKit had no candidate that day (the site's code named none that
  morning), so its order shows nothing of the mend yet.

#### 20.10.3 Found, not mended: a product a cheaper shop keeps is not always one that shows nothing

The rule puts last, and the mend now has replaced, a shop's product that another shop keeps
cheaper by its code (19.4). But the site joins the offers of one product among the products
a search finds: where the cheaper shop's row is not found by a search (most likely its own
title and shelf read as another kind or as none, or its shop's own page says it is sold out;
not read product by product here, the summaries hold counts), the dearer row is that search's
card, and with it gone the search shows one product fewer.

As GamingKit's own copies leave, the kinds' own searches that find fewer products by the mend
than by the site's code, and that this explains: the night after, when no other shop's
products differ, 9 products in 8 kinds (motherboard
2; shelving unit, charger, firewall, household battery, mouse, docking station, graphics card
1 each); two nights after, 23 in 13 kinds (charger 5, motherboard 4, charging cable 2,
household battery 2, mouse 2; air purifier 10 to 9, games console 16 to 15, gps navigator 4
to 3; shelving unit, ip phone, firewall, tv, graphics card 1 each), with 3,859 of its copies
gone: about six in a thousand. The same nights it shows 2,106 and 3,902 more products.

**And such a product is counted on the cheaper shop's card.** A shown card of a product more
than one shop sells says "Lowest price of N shops" (`search_selection`, `shop_counts`; the
decision contract, the owner's rule of 16/10). With the dearer row gone the card counts one
shop fewer and, where two sold it, says "Lowest price" alone. So "it shows nothing" (19.4 b,
20.9) is true of a card of its own, not of that line. Not counted by the look (its summaries
hold no card's shops): at most one card for each copy that leaves, and only where that card
is among the shown ones that carry the line. Found on 23/11 (16:00 Athens) when the owner
asked what the mechanism is for, and told to him then.

The site's code does the same wherever a capped shop's product that a cheaper shop keeps
gives its place to one that enters (19.4 e, the owner's order): the mend makes it happen for
GamingKit's 4,476. **Left as it is, the owner told. A later step, his to weigh:** a product
counted as a cheaper shop's only when the cheaper row is found wherever this one is (it
carries every kind this one carries). It changes the rule's order for every shop (20,861
such products of 23 shops today) and wants a look of its own.

#### 20.10.4 Found, not mended: what the cap of a category names of a capped shop beyond what the shop may name is named for no one

The cap of a category names candidates for a part's open places among every product that
waits, the capped shops' rows that are offered to it with them (19.6.2), and each capped shop
then keeps of its own only as many as it may name (`vetted`). The rest of the cap's choices
are dropped, and no other shop's product is named in their place.

- By the site's code, tonight: the cap names at least 7,073 of GamingKit's rows and the shop
  keeps 1,478 (its 1,182 open places): 5,595 or more dropped. The mend uses them.
- By the mend, GamingKit is offered to the cap on every night it has a copy to replace. The
  night after, the site's code has it full and not offered, and the cap's choices in its
  categories go to the others; by the mend GamingKit takes many of them and may name 3,350.
  Two nights after: TV Cables 793 products for 1,481, Bazta UK 13,185 for 13,238, Tirendo UK
  3,083 for 3,096; "electronics > electronics accessories" keeps 10,333 for 11,613 (GamingKit's
  own copies gone are part of that). And, the cap's choices falling otherwise, the searches
  "spanner" 87 products for 97 and "tyre" 4,005 for 4,013.
- TV Cables and Bazta UK cannot be checked today (the one by its robots.txt, the other
  refuses the bot: `PROGRESS.md`, 23/11, the day's reading), so their candidates would not
  pass by either code: **on the site this costs nothing now**.
  It would cost a shop that can be checked and shares a part with a capped shop.

**Left as it is. A later step:** the cap of a category worked out a second time with each
capped shop's offered rows cut down to the ones it names (about a minute more of the
preparation), or told how many of a shop it may name.

#### 20.10.5 Not measured

- **How fast the gain comes.** The look takes every candidate as asked and passed in one
  night. The bot asks GamingKit's candidates after its shown products that show (14,342
  today), and past 20,000 of a shop nothing: by the first round's pace (about 17,300 of its
  pages a day) about 3,000 candidates a day; the round of 23/11, stopped for the deployment,
  says nothing sure of its pace on 4 processes. If the bot reads fewer of its pages in a day
  than it shows, no candidate is reached and the mend changes nothing for it. The reading of
  24/11 measures the pace.
- GamingKit's own products a cheaper shop shows are no longer asked again before its
  candidates, and not at all past its 20,000: their passes run out after three nights and
  they leave, whatever passes. They show nothing but for the few of 20.10.3.
- A night on which a shop is full with no place open and names for its copies' places alone
  was lived by GamingKit and PCHUB.UK (the night after and two nights after): the
  preparation's time and memory as on the others.
- **Seen in the bot's look, not looked into.** The bot's order counts 505 of PCHUB.UK's shown
  products as a cheaper shop's; the rule's own note counts none to 6 of them on the same
  nights. The two read it differently: `shop_order` sets a row against the lowest price of
  its code among every row of the catalogue, its own shop's included (a shop's own dearer
  listing of a product another shop sells too); `cap_shops` against what the other shops
  keep. Such a row shows nothing by either (one card a product, at the cheapest), so nothing
  shown is at stake; but by the cap it holds a place as "cheapest kept", and the mend does
  not replace it. That this is the whole of the 505 is read from the code, not product by
  product. GamingKit's two counts agree (4,476). A later step with 20.10.3: one reading of
  "shows nothing" for the cap and for the bot's order.

#### 20.10.6 For the «ανέβασε»

**Fit to deploy as built** (`2a264ba`; the work branch's head holds it). The night it is
deployed nothing shown changes; what it gains shows from the night after the bot has asked
GamingKit's candidates. As in 20.8: the site restarted first (a commit that starts a
deployment and does not concern the catalogue), then the commit that prepares.

Advised to the owner: **after the reading of 24/11**, so that the first night with the rule
is read alone against 20.8. The look's "site" run is that night's forecast if nothing more
passes: 199,770 products, 31,368 candidates, GamingKit's 1,478. A day sooner gains almost
nothing: deployed on the afternoon of 23/11 the bot would not reach GamingKit's candidates
before the night's end either way (they stand after its 14,342 shown products that show),
and the first of them would be shown on 25/11 by both.

## 21. A pass counts for the day; three nights only on a complication (owner, 25/11): decided; built 25/11; DEPLOYED 25/11 on the owner's «Ανέβασε» (release `20261125T141027Z-0df89e3`), in force from the night recorded 26/11 at 03:05 UTC

### 21.1 His words

Asked (25/11) whether the check should take three days, in the conversation of the feed in
packages: **«Ο έλεγχος δεν πρέπει να διαρκεί τρεις μέρες ο έλεγχος πρέπει να διαρκεί μέγιστο 24
ώρες...»**; then, of 19.3.1: **«Το όριο των τριών ημερών ήταν εάν δεν περάσει ο έλεγχος ή
σταματήσει και υπάρχει κάποια επιπλοκή να μη σβηστούν τα προϊόντα ... 24 ώρες είναι το
σκανάρισμα και ότι προλάβει να σκανάρει.... Εάν το σύστημα κολλήσει και δεν κάνεις κανάρισμα την
επόμενη μέρα τα προϊόντα μένουν όπως έχουν πρέπει μετά την τρίτη ή την τέταρτη να σβηστούν»**.
Asked to state the rule clearly so that he could answer, he was given, in Greek:

1. Κάθε 24ωρο το σκανάρισμα ρωτά όλα τα καταστήματα ταυτόχρονα, το καθένα με τον ρυθμό που δέχεται.
2. Πρώτα ξαναελέγχει όσα είναι ήδη στο site και μετά, με όσο χρόνο μένει, νέα προϊόντα.
3. Στο site μπαίνει μόνο ό,τι πέρασε τον έλεγχο τις τελευταίες 24 ώρες, έως 20.000 προϊόντα ανά κατάστημα.
4. Ό,τι αποτύχει στον έλεγχο βγαίνει την ίδια νύχτα και γυρνά μόλις ξαναπεράσει.
5. Αν κολλήσει ο server ή το bot, ή αν το κατάστημα σταματήσει να απαντά, τα προϊόντα μένουν
   όπως είναι έως 3 μέρες. Μετά βγαίνουν από το site μέχρι να ξαναπεράσουν.

**«Ναι συμφωνώ και αυτό έπρεπε να γίνει από την αρχή».** Three days, not four: the three of
19.3.1, proposed to him so («Προτείνω 3, όπως τώρα, όχι 4»), not contradicted.

### 21.2 What it changes, read on the code and the server (and a correction told to him)

- **Points 1, 2 and 4 stand already** (19.3.2, 19.5, 5): every shop asked at once, a shop's shown
  products asked again first, a failure cut that night.
- He was first told, wrongly, that a slow shop piled up three days of scanning (5,000 a day to
  15,000) and that GamingKit and PCHUB.UK would fall to about 18,000 and 12,000. **Corrected the
  same hour, in Greek:** with the shown asked again first, a shop settles at what the bot scans
  of it in a day (`tests/test_picwise_checks_walk.py`, a slow shop); the health run of 25/11
  10:01 UTC: PCHUB.UK 12,501, GamingKit 13,543.
- **What changes on a normal day:** a product the bot did not reach again that day leaves the
  site at once, not after up to three nights (a shop's day that read fewer pages than the day
  before no longer keeps the difference shown).
- **What changes when something breaks** (told to him): until now, decisions over two nights old
  were not applied at all (`checks_applied.MAX_AGE_NIGHTS`): with the bot down three nights the
  checks stopped and unchecked products could enter. Now a pass counts three nights and no more
  however old the file: with the bot down past three days the products leave the site, and if it
  stays down **the site empties until the bot answers again**. He was told so, with his choice
  open; the health run's limits say the first missed night.

### 21.3 How it is built (25/11, deployed 25/11)

- `picwise_checks.ledger`: `PASS_NIGHTS_DAY` (1) and `NOT_PASSED_TODAY` ("not passed in the last
  24 hours"); `Shop.complete_on`, the last night a shop was asked whole (`record_night(...,
  complete=)`; a round that is ours, 7.1, marks none; a shop that cannot be checked that night is
  never whole). `not_shown_until_checked` with the day's rule: shown when passed tonight; else it
  waits once its shop was asked whole on a night after its pass, and in any case three nights
  after it (`NOT_PASSED_IN_THREE`). A ledger written before (no `complete_on`) keeps the three
  nights until its shop's first whole night. `decisions` name each pass's night (`passed_on`) for
  the shown and those entering.
- `deployment/bot/shop_checks_bot.py`: with the shop rule on, `pass_nights` is the day's.
  **Asked whole** (`asked_whole`): nothing stopped the shop (no 429 or 503 that said to come
  back, no error, its robots.txt answered: a shop asked nothing was not asked), and the bot asked
  it every product of its order, or asked it all day in a round that asked all day and began on
  it within an hour of the round's start. **A round that asked all day** (`RoundTime`): at least
  20 hours asked (from 05:30 to 03:05 a round asks about 21.5), the hours of a round stopped and
  started again added up (`tonight-<night>.time.json`, kept every 5 minutes beside the night's
  answers), never the hours it was down. The note's `shop_rule` says the round's hours, whether
  all day, the shops asked whole and the first 60 not.
- `picwise_providers.checks_applied`: `A_DAY`, left aside with the switch of 19 off as the three
  nights are; decisions that name the passes' nights are read however old, and on a morning
  with no newer night `expire` makes a pass of three nights or more wait (and enter nowhere).
  Decisions without them keep the old rule (over two nights old, not applied).
- `deployment/server/print_health.py`: the rule's line; the round's hours; a round that did not
  ask all day passes a limit.
- Tests: `tests/test_picwise_checks_day_rule.py` (16), the walk's `Rules21...` (2), the health
  run's line (1); the checks' modules as before.

### 21.4 For the «ανέβασε»

The deployment changes the bot's code, so `deploy.sh` starts its round again on the new release;
the round of that day goes on from its kept answers, and its hours kept from then on (the hours
before the deployment are not counted: that first round may read as not all day, which keeps
every product as it was, the safe side). Nothing is prepared again by it. From the first whole
night after it, a product not reached that day waits. Read the morning after: the health run's
"the round asked ... hours (all day)" and the shops asked whole; PCHUB.UK's and GamingKit's
counts against 25/11's.

## 22. The four clones (owner, 25/11): built 25/11 behind `data/checks_clones.json` (false); deployed 25/11 with the switch false, NOT TURNED ON

### 22.1 His words

In the conversation of the feed in packages: «οι πρώτες 500.000 κωδικοί σκανάρονται από 4
κλωνοποιημένα συστήματα για να τελειώνει πιο γρήγορα δηλαδή αν έχουν ανατεθεί 50 καταστήματα στον
κάθε κλώνο ερωτώνται 200 καταστήματα αυτό μειώνει το χρόνο σκαναρίσματος ... μην αγνοείς τους 4
κλώνους»; earlier the same day: «800 καταστήματα 4 bot από 4 εργασίες στον καθένα τα καταστήματα
ανατίθονται με κωδικό». Put to him and agreed (the Project's doc `claude/PicWise-protasi-paketa.md`):
the four clones ask every shop at once, all day, each its own shops by a code, and only what
passed the rules; one clone stopping leaves the other three.

### 22.2 How it is built

- **A shop's clone** (`shop_checks_bot.clone_of`): a code of the shop's name (CRC-32 of its name,
  spaces and case aside) modulo 4, plus one. Always the same clone; a shop asked by one clone only,
  so never faster than it allows (4.3).
- **A clone's day** (`--clone K/4`, `picwise-checks@K.service` and `.timer`, 05:30 UTC): reads
  the catalogue, keeps only its shops' rows, asks them in the rules' order (10, 19.3.2) until
  03:05 UTC, its answers kept as they come (`tonight-<night>-cloneKof4.jsonl`) and its hours
  (`...time.json`, 21); at its end it keeps its day (`clone-<night>-cloneKof4.json`: per shop what
  asking it gave, whether something stopped it, how many its order held, its seconds) and
  records nothing. It reads pages on one process of its own (`--processes 1`; four in all, as
  the bot alone today), at most 3 GB.
- **The night's recording** (`--record 4`, `picwise-checks-record.service` and `.timer`, 03:07
  UTC): waits up to 20 minutes for a clone still finishing, reads Awin, judges every answer of
  the four days and records the night once (the ledger, the decisions the preparation of 04:17
  reads, the note), as the bot alone does (`record_round`, the code the bot alone now runs too).
  **A clone that kept no day** counts as stopped: its shops' answers so far count, none of its
  shops was asked whole, so their products stay as they were (21).
- The note's `shop_rule` says the clones and each one's hours; the health run reads the
  recording's result and each clone's, a clone that did not end well passing a limit.
- **Behind `data/checks_clones.json`** (`"on": false`): off, `deploy.sh` keeps the bot alone
  (`picwise-checks.timer`), the clones' timers and the recording's disabled; on, the four
  clones' timers and the recording's enabled and the bot alone's disabled, never both. The
  units are installed either way.
- Tests: `tests/test_picwise_checks_clones.py` (two clones and the recording decide what the bot
  alone decides from the same answers, each shop asked by its own clone only; a clone that kept
  no day), the deployment's unit count, the health run's lines.

### 22.3 For the «ανέβασε»

Deploying the code changes nothing while the switch is false (the bot alone runs as before, on
`record_round`). Turning it true is a commit of its own, deployed on his word, best right after
a night was recorded (before 05:30 UTC), so that the first clones' day starts fresh: a day the
bot alone began is not carried into the clones' files (its answers are asked again by the
clones). To read the morning after: the health run's four clones "success", the recording's
night, the shops asked whole.

## 23. Eight bots, 10,000 a shop on the site, 20,000 asked a day (owner, 26/11): step 1 built 26/11 (Claude Opus 5.5), every part behind its switch; NOTHING DEPLOYED

### 23.1 His words, and the brief he gave the builder

Decided by the owner on 2026-11-26 (in a conversation of his PicWise Project, put to him in
Greek and approved as he wrote it):

1. «Προϊόντα ανά κατάστημα στο site: έως 10.000, αντί για 20.000.»
2. «Έλεγχοι ανά κατάστημα: όσους αντέχει το κατάστημα, έως 20.000 τη μέρα. Τα γρήγορα καταστήματα
   ξαναελέγχουν ένα μέρος των προϊόντων τους και δεύτερη φορά μέσα στην ίδια μέρα. Μετράει ο πιο
   πρόσφατος έλεγχος.»
3. «8 bot αντί για 4, 2 σε κάθε πυρήνα. Κάθε bot είναι ξεχωριστό πρόγραμμα και αναλαμβάνει έως περίπου
   100 καταστήματα.»
4. «Ανάθεση καταστημάτων: κάθε κατάστημα παίρνει σταθερό κωδικό από το όνομά του και πηγαίνει πάντα στο
   ίδιο bot.»
5. «Όριο μνήμης: 1,8 GB για κάθε bot, δηλαδή το πολύ 14,4 GB όλα μαζί.»
6. «Αρχή: όποιο προϊόν δεν πληροί τις προϋποθέσεις σβήνεται αμέσως και δεν μένει να πιάνει μνήμη.»
7. and 8., open then, made part of the brief: a reserve of memory for the site that the bots never
   take; the ledger lets go of products missing for over 7 days, and each bot loads its own shops.

The order: step 1 the build and its tests, nothing on the site; step 2, on «ανέβασε», the 10,000,
the 20,000 asked and the memory's limits, the 8 bots deployed switched off (about 98,000 products
was said); step 3, on another «ανέβασε», the bots switched on early in the morning; then 3 stable
days in a row; then the second asking.

The brief (written for him by Claude Fable 5.2 the same day, his «Okay ξεκίνα» to it) added, each
named in his Greek as Π1 to Π6: a limit for all the bots together, the arithmetic shown, a bot at
its limit started again from where it stopped, the bots below the site's priority (Π1); a switch
for each bot, so they open one by one (Π2); the code from the shop's number at Awin, not its name
(Π3, which replaces "από το όνομά του" of point 4: a name changes, the number does not; where no
number is given, the name, as from 25/11); the second asking cuts only on a clear answer, stops for
the day when a shop slows or refuses, starts from each kind's first cards, its own switch, opened
last (Π4); one short line kept of a product let go, the AI's answers never let go (Π5); the stable
day (Π6, 23.6).

### 23.2 What is built, and behind which switch (nothing changes until each is turned)

| Part | Where | Switch, as committed | Turned by |
|---|---|---|---|
| 10,000 shown, 20,000 asked | `shop_cap.shop_limits` | `data/shop_cap_switch.json` names no `most` / `asked`: 20,000 both, as from 22/11 | step 2: `"most": 10000, "asked": 20000` |
| 8 bots, a switch each | `picwise_checks.bot_rows`, the bot's `--clone`, `deploy.sh` | `data/checks_clones.json` `"bots": []`: the bot alone asks every shop | step 3: `"bots": [1, 2]`, then all eight |
| Memory and cores | `picwisebots.slice`, the units, `system.slice.d/picwise-site-reserve.conf` | in force with the deployment of step 2 | the deployment |
| The ledger lets go after 7 nights | `ledger.forget_unseen` | in force with the deployment of step 2 (the first 7 nights let nothing go) | the deployment |
| The second asking | the bot's `_ask_again` | `data/checks_second_switch.json` `"on": false` | last, after 3 stable days |

### 23.3 The bots

- **Which bot asks a shop** (`bot_rows.clone_of`): a CRC-32 of "awin <advertiser id>" modulo the
  number of bots, plus one; a shop whose rows give no advertiser id (`advertiser_id` or
  `merchant_id`, which both Awin links give: `awin_adapter.shop_key`), the CRC-32 of its name, as
  from 25/11. The row the checks know now carries the id (`Row.advertiser`, `row_record`'s 15th
  value; a record of 14 reads with none). Every bot works the assignment out from the same files,
  so a shop is asked by one bot only, never faster than it allows (4.3). Not known yet: how many of
  the real shops' rows give the id (the look, 23.8).
- **The switch** (`data/checks_clones.json`): `clones` 8, `bots` the ones on. None: the bot alone,
  as before. Some: each of them asks its shops as a program of its own (`picwise-checks@K`), the bot
  alone asks the others' shops, **waits for the day's end** (a bot of its own asks until 03:05, so
  the night is never recorded while one still asks) and records the night from its day and theirs.
  All: the bot alone is off and `picwise-checks-record` (03:07 UTC) records from the eight days.
  `deploy.sh` enables the timers of the bots on and disables the others', and stops and starts the
  round when the switch changed, so that no shop is asked by two at once. A shop moves bot only
  when its id first appears (a new shop asked first by name); the day's answers kept are its old
  bot's, and a day started fresh asks it again.
- **What a bot reads, and how it lets go** (owner's point 6): the catalogue, the preparation's rows
  for the bot and its shops' part of the ledger are read **in a process of its own**
  (`bot_rows.read_apart`, spawned fresh), which hands back only its shops' rows and ends, so the
  memory the catalogue took goes back to the server. A process that cannot start (the sandbox):
  read on the bot's own, said so. One that stops while it reads (its memory): the bot ends with an
  error, never reads it again on its own. Bot K starts its reading `(K-1) x 75 s` after it starts
  (`STAGGER_SECONDS`), so that no two read at once.
- **Started again**: a bot stopped (its memory's limit, a deployment) is started again by systemd
  (`Restart=on-failure`, 60 s, five times in four hours at most) and goes on from the answers it
  kept; its day counts how many times it started (`RoundTime.starts`), the night's note says each
  asker's day (`shop_rule.bots`: shops, hours, starts, its peak and its reading's peak in MB).
- **A whole day**: a bot whose shops all ended before 03:05 (all asked) asked a whole day
  (`Round.done`): with eight bots, the ones with small shops end early.

### 23.4 Memory and cores: the arithmetic

The server: 8 vCores, 24 GB (22.9 GB seen by the system); no swap is known of. Measured (25/11 and
26/11, the health runs): the site 4.3 GB (2.6 just restarted), the preparation's peak 11.9 GB at
night (04:17 to 04:45 UTC); the bot alone 1.0 GB on 23/11 (2.2 GB with the 399,000 products of
22/11); the night's memory, site and preparation together, 16.7 to 17.0 GB of the limit of 20.

- **Each bot**: `MemoryHigh=1536M` (slowed), `MemoryMax=1843M` (stopped): 1.8 GB, the owner's number.
- **All of them together** (Π1): `picwisebots.slice` `MemoryHigh=10G`, `MemoryMax=11G`, the bot
  alone and the night's recording in it too. Not the 14.4 GB of 8 x 1.8: in the day the site may
  hold up to its reserve of 6, the system and the AI's services about 2, and from 04:40 to about 06:10
  the photos' check (its limit 4) and the families' jobs (05:10, its limit 8) may run; 22.9 - 6 - 2
  - 4 leaves about 11. The bots measured (23.8) hold about 1.3 GB together once they have read,
  their answers adding about 0.4 GB through the day.
- **The site's reserve** (point 7): `MemoryMin=6G` on `picwise-web.service` (and on `system.slice`,
  which a unit's protection needs), `OOMScoreAdjust=-500`; every bot `+500`. Without swap a
  process's own memory is never taken back anyway; what holds the reserve is that the bots together
  cannot pass 11 GB, and that when the server runs short the kernel stops a bot, never the site.
- **At night**: the bots ask nothing from 03:05 to 05:30 UTC; the recording (03:07, its limit 5 GB)
  ends before the preparation (04:17), which now waits for it (`After=`); a deployment that prepares
  stops every bot first, as before, and its preparation waits for a recording still running. Night: site 4.3 + preparation 11.9 + system,
  as today.
- **Cores** («2 σε κάθε πυρήνα»): the slice has `CPUQuota=400%` (four of the eight cores for eight
  bots: two to a core) and `CPUWeight=50` (the site 100), `Nice=10` as before. Pinning bots to cores
  was not done: on a VPS the cores are virtual, and a pinned bot cannot use a core another leaves
  idle. Measured: none yet on the server.

### 23.5 The ledger: what is let go, and each bot its own part

- `ledger.forget_unseen`, run where the night is recorded: a product the bot was not given for
  over 7 nights (not shown, no candidate, no cut product the feed still lists) leaves the ledger;
  one short line of it is kept 30 nights in `gone` (the night, its last state and reason) and
  counted in the note. **Read against his words**: "missing from the feed" is read as "not given to
  the bot", which is the feed's products the site can use; a product still in the feed that the
  site has not shown, named or cut for 7 nights is let go too: its last pass counts for a day at
  most (21), so it is asked again before it shows, as a new one. A failed product the feed still
  lists is given every night, so it is asked again on its schedule (8.1) and the brakes count as
  before (Π5). A ledger written before has no nights seen: the first 7 nights let nothing go. The
  AI's categories are in their own files (`/srv/picwise/assist`), never touched.
- `ledger.load(path, shops=...)`: a bot of its own reads only its shops' products and entries, in
  its reading process (23.3). `seen` and `gone` are new keys of the file: an older bot reads
  nothing of them, and writes the ledger without them (the way back loses only them).

### 23.6 The stable day (Π6)

The health run says it, one line, under the rule of the day (21): the round asked all day; the
night recorded on time; the server not started again during the round (`/proc/uptime`); every shop
asked whole but those that cannot be checked; no bot started again by systemd nor near its memory's
limit (90%), nor the bots together near theirs; the failures at most twice a usual day's (1.2% on
25/11); no shop newly unable to be checked. The site's speed is the workflow's own line (four
searches from outside). The parts that are limits already pass their own; the line adds none.

### 23.7 The second asking (behind `data/checks_second_switch.json`, false)

A shop whose day's asking ended asks again, from the round's eighth hour (`SECOND_AFTER_HOURS`,
about 13:30 UTC), its shown products of the day's order, within the most it is asked a day less
what its first asking took: each kind's Recommended (its middle price) and its four cheapest first,
over every shop (`bot_rows.first_cards`), then the order of 19.4. Only products its first asking
read are asked again. A clear answer (`clear_answer`: the page read, its catalogue read, or the page
not there) counts in place of the first, so the latest counts; anything else (no answer, a server's
error, a refusal, a challenge, another site, a page with no product read) keeps the first and stops
the asking for the day, as does a request of 10 s or more (`SECOND_SLOW_SECONDS`). It never stops
the shop's own night, nor counts against its checkability (5.6.2). A Shopify shop whose catalogue
was read whole reads it again instead (at most 100 requests). Kept in the night's file (`"n": 2`, and
a line for a shop whose asking stopped), so a round started again asks nothing twice. The note's
`second` and `second_by_shop`. A shop's thread waits for the asking's hour: an asker of more than
200 shops (`SHOPS_AT_ONCE`) would keep its later shops waiting for a thread, so the second asking is
for the eight bots (about 15 shops each today, 100 at most by his number), not for the bot alone
with every shop.

### 23.8 What was measured, and the look before step 2

- **Here, on a made catalogue of today's size** (`tools/measure_bot_memory.py`: 111,487 products of
  105 shops, the four large ones as on 26/11, 70,331 candidates, 47,007 cut ones listed, a ledger of
  261,600): the bot alone as it reads today peaks at 895 MB and holds 868 MB; each of the eight
  bots' reading peaks at 797 to 813 MB, one at a time, and the bot then holds 108 to 274 MB (1,344 MB
  the eight together, each with its part of the ledger); the night's recording peaks at 843 MB. A
  bot's reading grows with the catalogue: about 7 KB a product shown, so the 1.8 GB holds up to
  about twice today's catalogue; past that (more shops) the bots must stop reading the site's
  catalogue and read their own rows, which the preparation would write for them (not built).
- **The table per bot** on that catalogue: 12 to 14 shops each; shown 8,216 to 23,977 (the two with
  InStock UK's and Tooled Up's sizes), the mean 13,936: none over twice it. On the real shops it is
  the look's (their ids are not known here).
- **The look before step 2** (read-only; on the owner's yes, since it reads the server's files):
  `.github/workflows/server-look-shop-rule.yml`, pushed to `claude/shop-rule-look`: the catalogue
  prepared on GitHub's runner from the server's copies by the code the site runs (20,000) and by this
  commit with 10,000 shown and 20,000 asked set in the runner's copy only, two nights after each;
  the products the site would have, the kinds that lose over half, the 40 searches' first cards
  before and after; then, on the server in the bots' sandbox, no shop asked and nothing written,
  `tools/measure_bot_memory.py` on its own catalogue and ledger: each way's memory and the table of
  shops and products per bot with how many by their number at Awin.

### 23.8b The look before step 2, run 26/11 17:37 Athens on the owner's «Ναι τρέχτην» (run 45850860004, read-only)

- **The products** (the code the site runs against 10,000 shown and 20,000 asked, on the server's
  copies, every candidate asked and passed): the first night 112,189 -> 99,601; the night after
  138,860 -> 110,764; two nights after 141,770 -> 111,169 (-30,601, about -22%). The four large shops
  to 10,000 each (GamingKit 18,471, InStock UK 18,448, Tooled Up 18,130; PCHUB.UK 14,741 -> 7,322 two
  nights after, rising as its candidates pass); Back to the Office 10,709 -> 10,000; 28 smaller
  shops gain (the categories' places the large ones leave: Santoro Milan +759, Bad Shirt Club +417,
  Shopping Ads +325, Fila UK +282 ...). No shop left with none.
- **The kinds** two nights after: 12 of 222 lose over half: monitor 3,610 -> 1,247, headphones
  2,213 -> 877, safety_shoes 1,758 -> 768, smartphone 1,382 -> 474, spanner 928 -> 76, printer 567 ->
  264, screwdriver 502 -> 237, pliers 327 -> 108, drill 294 -> 110, firewall 251 -> 115, shampoo 5 ->
  1, bed_linen 5 -> 2. None empty (the night after, bed_linen, hair_brush and shampoo had none for a
  night). Every kind searched keeps cards; "ram memory" 2,120 -> 1,009, "headphones" 1,400 -> 743,
  "monitor" 1,710 -> 1,158.
- **The 40 searches** two nights after: the same first 4 cards in 21, the same Recommended in 24
  (the site's own code from one night to the next: 35 and 36); none with fewer than 4 cards.
- **The eight bots on the server's own files** (118 shops; 105 by their Awin number, 13 by name:
  shops whose rows are only in the rows for the bot, which the live preparation writes without the
  number; after step 2's preparation they carry it, and move bot once): each holds 43 to 285 MB once
  it has read (980 MB the eight), its reading peaks 808 to 847 MB; the bot alone as today 942 MB peak,
  871 held; the recording 760. Per bot 11 to 19 shops; shown 2,334 to 33,467: bot 7 (Tooled Up and 10
  others) over twice the mean. Not a fault: a shop is asked at its own pace whichever bot asks it, and
  bot 7 holds 285 MB of its 1,800; with 10,000 a shop it falls. Nothing to mend now.

### 23.9 For the «ανέβασε»

- **Step 2** (his «ανέβασε»): one commit, `"most": 10000, "asked": 20000` in
  `data/shop_cap_switch.json` (frozen with the code: the deployment prepares the catalogue again,
  about 30 minutes, the bot stopped meanwhile); the code of steps 1 deployed with it, every other
  switch as committed. Read the morning after: the health run's "at most 20,000 asked of a shop; at
  most 10,000 shown of a shop", the products, the four large shops at 10,000 or what they allow, the
  ledger's line, the bot alone's memory in its slice.
- **Step 3** (another «ανέβασε»), best between 03:10 and 04:10 UTC (05:10 to 06:10 Athens: after the
  night is recorded, before the preparation): `"bots": [1, 2]` first; after a good day, all eight.
  Read: the health run's lines of each bot (its day, systemd's restarts, its peak against 1.8 GB),
  the bots together, the night's `shop_rule.bots`.
- **Then**: three stable days in a row (23.6). Then, on his word, `data/checks_second_switch.json`
  true.
- **The standing texts** (`PROJECT_RULES.md` section 5's paragraph of the checks, beside "20,000 products
  the most"; `docs/PICWISE_DECISION_CONTRACT.md`; `docs/PICWISE_DAILY_WORK.md`, the health run's new
  lines) change with step 2's deployment, not before (as 19.9 for section 19).
- **The way back**: each switch as it was; the code back by a deployment of the release before,
  which prepares the catalogue again (the frozen package changed), so the rows for the bot are
  written with 14 values again; an older bot ignores the ledger's `seen` and `gone`, the night's
  file's `"n"` and its lines of a stopped second asking.
