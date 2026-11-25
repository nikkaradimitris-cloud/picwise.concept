# PicWise — the feed in packages (plan; being built from 25/11)

Written 2026-11-25 on the owner's word, for the session that charts and builds it. Nothing
here is decided beyond what the owner said; the numbers are those measured on 25/11.

## What the owner asked

2026-11-25, in his words: «Να χειρίζονται σε πακέτα τα προϊόντα δηλαδή το σκανάρισμα του
ενός εκατομμυρίου προϊόντων ή των δύο τον τριών των 5 όσα και αν είναι αυτά μπορούμε να τα
διαχειριστούμε χωρίζοντάς τα σε πακέτα σε άλλη περίπτωση και μεγαλύτερο πακέτο server να
πάρουμε κάποια στιγμή θα κολλήσουμε στο μέλλον», and then the mission: «σκέψου ότι θα
έχουμε να διαχειριστούμε 10 εκατομμύρια προϊόντα έρχεται ένα ενιαίο αρχείο αυτό πρέπει να
χωρίζεται σε κομμάτια πρώτες 500.000 και 800 καταστήματα 4 bot από 4 εργασίες στον καθένα
τα καταστήματα ανατίθονται με κωδικό ... τα υπόλοιπα 9 εκατομμύρια 500.000 κωδικοί μένουν
εκτός κατά την διεργασία μετά έρχεται δεύτερο πακέτο τρίτο πακέτο 4ο πακέτο κτλ σε άλλη
περίπτωση ότι server και να κλείνουμε θα ανεβάζουμε τα κόστη σε σημείο που θα κάψουμε το
project». Then «Ναι γράφτην και πάμε σε άλλες συζήτηση» to this plan.

The goal: the night's work holds memory by the size of a package, not of the whole feed, so
that the server of today (OVHcloud VPS-4 2027: 8 vCores, 24 GB, 200 GB; the largest of its
range, no upgrade offered, read in its panel on 25/11) carries ten million rows.

## Where the memory goes today (measured 25/11)

`tools/measure_prepare_memory.py` on both Awin links, GitHub's runner (trial run
45592756926): 2,685,295 rows; 1,590,120 eligible; 220,498 kept by the cap (the runner has
no checks, no shop rule). Peak 13.85 GB (the server's of the same night: 14.1 GB).

| Step | Memory now | Peak |
|---|---|---|
| first link's 1,687,331 rows read (dicts) | 5.36 GB | 5.36 |
| made products | 6.81 | 6.81 |
| second link's 997,964 rows read, made products | 9.68 | 9.68 |
| every row judged (the pipeline) | 11.15 | 11.15 |
| search catalogue of the 1,590,120 eligible | 12.29 | 12.38 |
| kinds read, before the cap | 12.79 | 12.79 |
| the cap decided | 13.16 | 13.63 |
| file written | 13.16 | 13.85 |

About 3.2 KB a row as a dict, 0.9 KB more as a product. The rows never eligible
(1,095,175) stayed to the end, held by the pipeline's cache for the intake measured last.

## Step 0, built 25/11, NOT deployed

**The trial read (run 45597029695, both links, GitHub's runner):** "the catalogue: 220,503
products with the live code, 220,503 with the new; the same in every field", every key of the
note the same; peak memory 14.53 GB with the live code, 12.01 GB with step 0 (816 s against
786 s). Fit to deploy; it waits for the owner's «ανέβασε».

`e9e6256` on the work branch: the intake is measured as soon as every row is judged
(`state.prepare_feed_catalogue(measure_intake=True)`, `state.last_prepared_intake`), then
the rows never shown and the caches that held them are let go before the search catalogue,
the kinds and the cap. Same catalogue (pinned: `tests/test_picwise_prepare_lets_go_of_rows.py`;
trial run 45597029695 prepares the same feed with the live code and the new and compares the
files and the note). It lowers the later steps, not the pipeline's peak of 11.15 GB: the
packages below are what lowers that. Deploying it prepares the catalogue again (state.py).

## The plan, as put to the owner on 25/11

1. **The file cut into packages on disk.** The feed (both links) read line by line and
   written to package files of about 500,000 rows each (the disk has 188 GB free).
   **A package is made of whole shops** (a correction put to the owner): the rules per shop
   need every row of a shop together (the most a shop passes, 20,000; one card per product;
   sizes and colours joined; one shop in several networks known by its domain).
2. **One package at a time.** Each package judged, its kinds read and the shop rule applied;
   only what the site can show (and the checks' candidates) kept, the rest let go.
3. **The rules over all shops last, on a small summary.** The cap of 15% and 12,000 a
   category, a product a cheaper shop keeps, the thin kinds: worked out on a summary of a
   few hundred bytes a product, not on whole products.
4. **The bots.** Shops given to the 4 bots by a code (the owner: 200 shops each of 800).
   **The bots ask only what can be shown and the next in line**, never every row (a
   correction put to the owner: 10 million pages every 3 days is past any server and the
   shops would block it; the caps bound what is shown).

Expected: the night about 2 hours for 10 million rows (31 minutes for 2.7 million today).

## What ties the rows together today (found 25/11; each must become a first pass's summary)

- `offer_health.build_feed_availability_context`: which availability columns vary across
  the whole feed (a bare flag decides only where its column varies).
- `awin_adapter.second_row_keep` and `merge_feeds`: the second link's rows kept by the first
  link's shops and ids.
- `shop_catalogue.apply_shop_catalogues`: `_apply_barcodes`, a row without a category takes
  the category most rows with its barcode write, over every row; its note's counts.
- `checks_applied.apply_checks`: its sets and notes (`_LAST_NOTE`, `_LAST_CUT`, waiting,
  unchecked).
- `feed_intake.measure_feed_intake`: `categories_by_barcode` over every row before the rows.
- `shop_cap.cap_shops`: thin kinds by the night before's kept rows or every row; prices of
  the same product (`same_product_key`) in other shops; capped shops tied by shared
  products settled over rounds.
- `catalogue_cap.cap_catalogue`: the category shares over every product.
- The order of the products (the feed's) must be kept: every rule after reads it.

Each step is built so that the catalogue comes out the same as today's on the same feed
(the trial's comparison), then deployed on the owner's «ανέβασε».

## The flow agreed with the owner (25/11, the conversation of the packages)

His words of 13:11 Athens: «Το αρχείο κατεβαίνει ολόκληρο και αποθηκεύεται στο σκληρό δίσκο ... οι
πρώτες 500.000 κωδικοί σκανάρονται από 4 κλωνοποιημένα συστήματα για να τελειώνει πιο γρήγορα ...
επόμενη κίνηση από τα σκαναρίσματα αυτά που βγήκαν άχρηστα σβήνονται επόμενη κίνηση προώθηση άλλα
500.000 ... μην αγνοείς τους 4 κλώνους». Put to him with two corrections, and written in the
Project's doc `claude/PicWise-protasi-paketa.md` on his «Ναι συμφωνώ» (to the rule of the check,
with the flow):

1. The whole file downloaded to disk.
2. Cut into packages of about 500,000 rows, whole shops.
3. One package at a time through the rules (the categories, the floors, the 20,000 of a shop...)
   on the server, minutes, no network; what can never be shown let go at once, what stays written
   to disk, not held in memory. This is what bounds the memory.
4. The rules over all shops last (15% and 12,000 a category, a product a cheaper shop keeps), on
   a small summary of each product, gathered by a first pass over the whole file for the seven
   points above.
5. **The 4 clones scan all day, every shop at once, each clone its own shops by a code** (e.g.
   200 of 800), and only what passed the rules; one clone stopping leaves the other three.

The two corrections, and why (told to him with the numbers):

- **The rules first, the scanning after.** Of 2.7 million rows about 147,000 reach the site, 1
  in 18: scanning every row is mostly lost.
- **The clones scan every shop at once, not package by package.** A shop gives a page every 3 to
  10 seconds, whatever the other shops wait for (the rules 4.3, 4.7; 20,000 a day the most): a
  package holding a large shop takes about a day, so 20 packages one after another would take
  up to 20 days against a pass that counts for the day (the checks' rules 21). Every shop at
  once, the round closes within the day; the clones are what keeps the server from being the
  brake with 800 shops (the look of 22/11: 140 shops on one process, GamingKit 10 s a page
  instead of 4.3), and a clone that stops leaves the others running.

The check's own rule, decided the same hour: `docs/PICWISE_CHECKS_RULES.md`, section 21.
