# PicWise — session handoff

Where the project is now and how to work on it; short on purpose. Updated 2026-11-21 (17:15 Athens: task 3, Awin's programmes, the offers and the photo's limit deployed, the button built; 15:45: task 2, the look at 95 cards; 15:05: task 1 of the work split by model deployed, the shops' bot and both links, the memory fix, InStock UK looked at; before it, 13:50, a second opinion on the owner's plan of 21/11; 12:55, the daily session: the site's memory at night).
`PROGRESS.md` is the dated log. The history before 12/11 is kept whole in
`docs/archive/picwise_session_handoff_until_2026-11-12.md` (this file as it was, 3,959
lines) and `docs/archive/PROGRESS_log_until_2026-11-08.md`; read them only to trace how
a decision came about.

## Next conversation: start here

- **FIRST (21/11, 17:15 Athens): task 3 of the work split by model (OPUS) DONE** (PROGRESS.md, 21/11 17:15).
  **Awin:** the account is joined to 12 programmes; of the catalogue's 160 shops 150 are not joined (83.1% of
  the site's products: InStock UK, Tooled Up, GamingKit, Plusshop UK, Bazta UK...), 8 joined (16.9%); 35
  shops' feeds last imported over 7 days ago (12,684 products). The owner (16:51): «Θα κάνουμε αιτήματα να
  δούμε ποια από αυτά θα μας εγκρίνουν»: his Sheet "PicWise — Αιτήσεις στην Awin"
  (https://claude.ai/artifact/3iwKs8EgNgkeJcSF97ksaT) lists the 160 with a dropdown for each application;
  `server-programmes.yml` (push of `claude/programmes-2026-11-21`, change its `# Run:` line) reads the
  relationships again, to update the Sheet when he asks. **Deployed** (`a07b2c8`, run 44916373013, no
  preparation): the offers from both links' shops (55 of 160 with offers, before 39 of 104); a card whose
  photo has not come 10 s after it is in view leaves the page. **Built, NOT deployed, waits for «ανέβασε»:**
  `e82387c`, a gone product's button lands on its search's current results with the line the owner chose
  («Οι τωρινές επιλογές»). **Next by the split: task 4 is FABLE** (the checks' rules): a session on Opus
  stops there and tells the owner, in Greek, to switch to Fable 5.2. Open for the rules: a feed over 7 days
  old; shops not joined that Awin rejects; Aosom UK's robots.txt 403; InStock UK accepts the bot (about
  930,000 feed rows). The owner reads questions only in Greek: English wording for the site goes with its
  Greek meaning.
- **(21/11, 15:45 Athens): task 2 of the work split by model (OPUS) DONE: an hour's look at the
  buttons, prices and photos of 95 first cards of the owner's own searches; read-only** (PROGRESS.md, 21/11
  15:45; `deployment/server/look_cards.py`, `server-look-cards.yml` on `claude/look-cards-2026-11-21`, run
  44909213170). No id shared by two products (389,735 of each); all 95 buttons find their own product and
  lead to an Awin link (59 `pclick.php`, 36 `cread.php`); all 95 photos load in under 1 s; prices: 63 of
  69 read the same (InStock UK +9% again; pence at PCHUB.UK; Back to the Office -£1); 4 shown while the
  shop's site says sold out (PCHUB.UK 2, MoreThisWay 1, InStock UK 1); 22 pages no machine reads (Tooled Up,
  Plusshop UK, Tyres UK, Tirendo UK, MoreThisWay); Aosom UK's robots.txt 403 to the bot. **Next, task 3
  (OPUS):** Awin's programmes (joined, closed, last update): a button that fails past our side is Awin's;
  and `fetch_offers.py` reads only the newest copy of the feed (the first link's shops' offers not fetched
  since 20/11; fix with both copies, as the bot). Put to the owner: his 5 favourites, if they are the
  products that failed.
- **(21/11, 15:05 Athens): task 1 of the work split by model (OPUS, the next item) DONE and DEPLOYED
  on the owner's «Ανέβασε και τα δύο»: the shops' bot reads both Awin links again; a second-link row's own
  address; the memory fix. InStock UK looked at: it accepts the bot.** (owner: «PicWise: συνέχισε από το
  handoff, εργασία 1»; PROGRESS.md, 21/11 14:50 and 15:05.)
  - **Deployed:** `11cd5ab` (run 44903940464, no preparation, the site 4,535 MB after its restart), then
    `3701751` (run 44904192982: prepared beside the fresh site, peak 14.9 GB, 28.6 min; the site 4,488 MB;
    15 of 15 pages, 12 of 12 searches the same). The site runs `3701751`; the work branch is ahead of it by
    the InStock UK look and records only (inert on the site).
  - **To read next:** the bot's first round with both links, 22/11 03:40 UTC (`prepare-runs.yml` by hand,
    `since=-30h`: copies 2, shops with an address, requests, ends; first the 19/11 shops, then the rest by
    size, the large second-link shops over several rounds); the site's memory the morning after the
    night's swap (the memory fix: 8.3 GB the morning of 21/11 without it).
  - **InStock UK** (run 44904597222, `shop_product_test.py`): robots.txt read, its Shopify catalogue
    answers (500 on 26/10); of 12 products 11 the same product and in stock on its site, 1 gone (404);
    price: 5 the same, 5 about 9% dearer on its site (cause not known), 1 another variant. Put to the
    owner: it accepts the bot; how to check about 930,000 feed rows (Shopify pages 25,000) belongs to
    the checks' rules (task 4, FABLE).
  - **Confirmed on the server** (`prepare-runs.yml` by hand, run 44901697947; `print_prepare_runs.py` now
    prints the bot's own lines a night, counts only): 19/11 the first link's copy (1,681,066 rows), 82 shops
    asked, 498 requests, the file 149,495 products; 20/11 and 21/11 the second link's copy only (~1,446,000
    rows, 413 MB, written 96 s after the first's 248 MB), 87 and 86 shops, **0 requests, all "no address"**,
    and the file **149,495 -> 28,135 products on 20/11**: a shop in both links met only `pclick.php` links in
    the second copy and kept none of its products. So those shops' readings were gone from 20/11, the
    others' from 23/11. The cache also holds a copy of 25/10 (367 KB): left by the new rule.
  - **Built.** `11cd5ab` on the live `e383e7c` (branch `claude/bot-two-feeds-site-2026-11-21`), nothing under
    `src/`, so the prepared file's fingerprint stays the live one (`2f1a4bbf33bc`) and its deployment alone
    does not prepare: every copy written within 30 h of the newest read (`shop_catalogue_test.feed_copies`),
    a shop in both from both; a row's own address its link's, else its `merchant_deep_link`; a shop not asked
    for lack of time keeps its `read_at` (until now every shop took the round's time, so with 145 shops the
    largest went first every night and the last were never asked). Then on the work line (merge `341a9d8`)
    `c87ba01`: `shop_catalogue.own_address`, read by the bot and by `apply_shop_catalogues`, so a second-link
    row meets its shop's reading ("sold out" holds it, also one variant; "in stock" stands; no address, the
    feed decides). Tests `test_picwise_shop_bot_two_feeds` (8), `test_picwise_shop_catalogue_second_link` (2).
  - **Corrected: the memory fix `8b12ae3` prepares the catalogue again** (it changes
    `src/picwise_providers/state.py`, which the code fingerprint reads: `acd77199db6c` against the live
    `2f1a4bbf33bc`), about 25-30 minutes, not the 3-5 the daily session wrote. With the site at 8.3 GB and
    13.9 GB available (11:55 UTC, run 44901351119) and a preparation's peak of 14.3 GB, that preparation would
    likely be killed for memory (20/11 08:56); remedy 1 would keep the site as it is. Tonight's 04:17 faces
    the same sum unless the site is restarted before it.
  - **Put to the owner (14:50; both chosen and deployed, above):** (1) `11cd5ab` to `ccr-1361f1a7-dcpo60` (3-5 minutes, no preparation; the site
    restarts with fresh workers, about 5 GB); (2) right after it, the work line's head (the memory fix and
    the second link's readings: prepares, beside a fresh site, as on 20/11 12:16 and 20:49, both fast-forwards.
    And InStock UK (about 100,000 products, a quarter; never asked by the bot, owner 26/10): a look at a few
    products first, a product at a time (about 3.5 days a round at 3 s), left unchecked, or out.
  - **After a deployment:** the bot's first round with the fix is 22/11 03:40 UTC; read it with
    `prepare-runs.yml` (by hand, `since=-30h`): how many copies, shops with an address, requests, ends.
    First the 19/11 shops (the oldest `read_at`), then the rest by size; the large ones (Tooled Up,
    GamingKit, PCHUB.UK) need several rounds at 200 requests a round.
- **(21/11, 13:50 Athens): a second opinion on the owner's plan of 21/11 (links, prices, photos,
  sorting), by Claude Fable 5.2 in the PicWise Project: what was found, what was put to the owner, and the
  work split by model. Records only: nothing built, nothing deployed, no decision of the owner changed.**
  The memory fix of 12:55 (the next item) still waits for its «ανέβασε».
  - **The owner's plan, as he sent it (it is in no other file).** The problems he saw: some buttons do not
    lead to the shop; some prices differ from the shop's; some photos never load; common searches (printer,
    tablet, laptop, drill, perfume, mattress, car tyres) show cheap accessories or parts first. His
    decisions: «Ποιότητα πάνω από ποσότητα. Όποιο προϊόν δεν περνά τον έλεγχο κόβεται, και όποιο κατάστημα
    δεν δέχεται το bot βγαίνει ολόκληρο. Τη θέση τους μέσα στο όριο των 12.000 την παίρνουν προϊόντα που
    πέρασαν τον έλεγχο»; «Το AI ρωτιέται μία φορά για την κατηγορία κάθε προϊόντος. Όποιο προϊόν δεν μπαίνει
    σε κατηγορία βγαίνει»; «Δεν γίνεται σκανάρισμα ούτε μέτρηση πριν: φτιάχνουμε τους μηχανισμούς και τους
    ανεβάζουμε. Δεν υπάρχει ημερήσιο όριο κόστους, μόνο ένα φρένο για λάθη»; «Δεν πατιούνται ποτέ αυτόματα
    τα links του Awin, για να μη γίνονται ψεύτικα κλικ. Η διεύθυνση του καταστήματος διαβάζεται μέσα από
    το link». Its steps: (1) many bots, shared by shop; a Shopify shop's whole catalogue read (barcode,
    price and stock of each size); (2) link: the shop's page opens and is the same product (EAN, MPN,
    SKU); the shop's Awin programme active; (3) photo: fails for any reason; on the site a card is hidden
    when its photo has not come in 10 s; (4) price: that of the same size or colour, found by its code,
    read by code and by the AI only where code cannot; the button opens the size the card shows, where it
    can; (5) category: one question to the AI; no category, out; (6) the failed removed; a night that cuts
    unusually many stops the removal; (7) each night the new products checked before they enter, and some
    old ones again; (8) a new question to the AI for every product, «είναι το ίδιο το προϊόν ή αξεσουάρ,
    ανταλλακτικό ή αναλώσιμο;», the cheapest of each kind first, accessories a choice of their own, about
    $25 once; (9) a quality meter: the same 40 searches each day; (10) questions in the search («Men's or
    women's?» for watches, «Car or motorbike?» for tyres), accessories a choice after the products;
    (11) the brands' list; (12) a daily email with the checks' numbers, the quality and the cost; (13) a
    picture to the owner before anything a visitor sees changes.
  - **Found.** Read in the code and in the night's public note (`/prepared.json`, prepared 04:35:03 UTC,
    read about 11:15 UTC with the session's fetch tool, in parts of 100,000 characters each summarised by
    that tool; the session's shell does not reach the site): **confirm a number on the server
    (`server-shops.yml`) before building on it.**
    1. **The shops' bot has read no shop since 19/11.** `shop_catalogues.shops`: 50 "read", 49 of them
       with `read_at` 2026-11-19T03:40 (Fila UK, Susan Caplan, MonsterPiercing, Finediam...); 88 "no
       address", 86 of them `read_at` 2026-11-21T03:40 (Tooled Up, GamingKit, PCHUB.UK, Back to the
       Office, Tirendo UK, Tyres UK, Plusshop UK, Bazta UK, Aosom UK, MoreThisWay, TV Cables...); four
       "robots.txt 423", FLOWERFIX "catalogue 403". In the code: `shop_catalogue_test.feed_copy` returns
       the newest single `picwise_awin_feed_*.bin`, and since both links (19/11 evening) the cache holds
       one per link (`awin_adapter._feed_cache_path`); the newest would be the second link's, whose links
       are Awin's `pclick.php?p=...`, and `feed_intake._shop_address` gives "" for those (its own
       docstring). A second-link row's own address is in its column `merchant_deep_link`, which the
       prepared file keeps. `shop_catalogue.STOCK_DAYS` is 3: the readings of 19/11 count until the night
       of 22/11; **from 23/11 no shop's site decides any product's stock.**
    2. The shops the bot does not read hold over 90% of the 389,735 kept products (`by_shop`): InStock UK
       102,242 (26%; never asked, owner 26/10), the "no address" shops about 248,000 (64%; counted over
       the 40 largest shops). Four shops hold 68%: InStock UK, Tooled Up 68,506, GamingKit 48,124 and
       PCHUB.UK 47,915 (about 41,600 of each of the last two also at another shop).
    3. `kinds.products` 125,093; `no_kind` 264,642 (68%), found by their words only. The plan leaves them.
    4. Why the first cards go wrong: the order is cheapest first and a part or an accessory is the
       cheapest, so a kind's few misread products all rise to its first cards (80.4% right on 20/11:
       first link 92.3%, second 71.9%). Step 8 of the plan aims there, rightly.
    5. The button: `/out/feed` answers "This option is no longer available" for a product no longer in
       the catalogue (a favourite, an old page). It finds the product by its id alone
       (`state._PREPARED_STATE["by_id"]`) while the memory keys a product by shop and id: whether two
       shops share an id was **not measured**. And it leaves through the Awin link, which no bot may
       follow: what breaks there, no check of the shops' pages sees.
    6. Read on the web on 21/11, to check at the source before building: Shopify's public
       `/products.json` carries no barcode (a product's own `/products/<handle>.js` does, with prices in
       the visitor's currency), so a barcode costs a request per product, 28,800 a day per shop at 3 s
       (Tooled Up's kept products 2.4 days, InStock UK's 3.6). Awin's Product Feed List Download gives
       each feed's last update and joined status; it can list feeds of advertisers that let publishers
       promote them before joining; the Publisher API's programmes take `relationship=joined`.
    7. `docs/PICWISE_SERVER_ARCHITECTURE.md`, section 3 (23/10), already designs this bot: JSON-LD first,
       a blocked or unreadable page counting neither for nor against, 8 s apart, a reliability score per
       shop. The plan's "a shop that does not accept the bot goes out" and "fails for any reason" differ
       from it.
  - **Put to the owner, none decided: his decisions above stand until he changes them.** Three verdicts
    (passed, failed, not known: blocked, slow, unreadable), cutting only on "failed". A ledger of checks per
    product (shop and id: what was checked, when, what was found, when again, how it comes back), read by
    the cap. Two or three nights with the cutting off: the built mechanism reports what it would cut, by
    shop and reason, then his «ανέβασε». A brake per shop and per kind, not only in all. A photo cut at once
    only on 404 or 410, else after two or three failures on different nights; the page's 10 s counted
    from when the photo starts to load (the cards past the first row are `loading="lazy"`). A shop that
    blocks the bot reported to him and written to through Awin, not taken out by itself. The shop's own
    price shown when its page states it clearly, instead of cutting. The AI asked "once per version of the
    question". Where the AI reads a price, it learns once per shop where the shop writes it, under a brake
    in dollars. The accessory question asked for the kind («είναι αυτό drill το ίδιο;»:
    `audit_search.KIND_PROMPT` is that question), never in general (ink cartridges, phone cases and drill
    bits are kinds of the site); a kind's search shows only the "yes"; each night for the cheapest 24 of
    each kind and the Recommended (about 7,000 products), with a stronger model; where a title names a
    kind and the AI's Google line disagrees, that question decides (the about 1,900 real products hidden,
    20/11). A price far below the kind's others as a sign to ask again, never a price worked out. A meter
    judged by another, stronger model (Haiku judges today what Haiku would filter), over every kind and
    the visitors' own searches.
  - **The work split by model** (owner, 13:37: «Είναι καλύτερα να αναπτύξεις εσύ τις διορθώσεις ή ... το
    opus 5.5 που έχει μικρότερη κατανάλωση?»; answered: Opus 5.5 builds, Fable 5.2 for the hard points;
    13:40: «Κάνε αυτό που λες... σημείωσε τις εργασίες που πρέπει να αναλάβει το fable έτσι ώστε να αλλάξω
    το μοντέλο»). **A session on another model that reaches a task marked FABLE stops and tells the owner,
    in Greek, to change the model to Fable 5.2 first; after it, back to Opus 5.5.** The order proposed:
    1. OPUS: the memory fix's «ανέβασε» (next item); **the bot reads both links' copies and takes a
       second-link row's address from `merchant_deep_link`** (urgent: 23/11); InStock UK put to the owner
       (asked a product at a time, left unchecked, or out). **Done 21/11: built, deployed on the owner's
       «Ανέβασε και τα δύο», InStock UK looked at (the first item).**
    2. OPUS: an hour's look, no scan, at the buttons, prices and photos the owner saw fail: ours, Awin's
       or the shop's; the ids two shops share, counted. **Done 21/11 15:45 (the first item): no id shared; our side of every
       button sound; photos load; prices mostly the shop's.**
    3. OPUS: what needs no bot: Awin's feed list and programmes (joined, last update); the photo's limit
       on the page; a button that meets no dead end (a picture to the owner first; the wording is his). **Done 21/11 17:15 (the first item): Awin read (12 joined;
       150 of 160 shops not); offers and the photo's limit deployed; the button built, waits for «ανέβασε».**
    4. **FABLE: the checks' rules:** the verdicts, what cuts at once and what after how many failures, the
       brakes, how a product or a shop comes back, what the cap reads; each point that touches a decision
       of the owner's put to him.
    5. OPUS: the ledger and the per-shop bots, built to those rules; the nights with the cutting off, if
       the owner agrees.
    6. **FABLE: the question "is it the kind itself":** its gate, the rescue of the hidden real products,
       the independent meter.
    7. **FABLE: a look before each «ανέβασε» of a change that cuts products.**
    8. OPUS: the search's questions (step 10) and the brands' list (step 11).
    9. **FABLE, later:** what becomes of the 264,642 products of no kind.

- **FIRST (21/11, 12:55 Athens, the daily session): the site's memory at night over the limit; a fix built,
  NOT deployed, put to the owner.** The night passed (`/prepared.json` read 09:43 UTC: prepared 04:35:03,
  389,735 products, 135 shops, no shop gone, shrunk or new). `server-health.yml` by hand (run 44890957471, 09:44
  UTC): **over the limit: the site and the preparation together need 22.5 GB** (limit 20, server 22.9): the
  site 8.3 GB (5,833 MB after the deployment of 20/11 21:20), the night's preparation peak 14.3 GB, 27.9 min;
  13.9 GB available now; every search's server part under 0.6 s; disk 189 GB free; AI yesterday $0.00. Every
  night since both links (19/11) the site had been restarted by a deployment the day before; tonight (22/11
  04:17 UTC) is the first with swollen workers, as on 20/11 08:56 (workers ~2.9 GB each + a preparation of 14 GB:
  out of memory). The cause looked for: no catalogue stays referenced once replaced (a new test, weakrefs);
  Python and glibc keep the pages the old one was freed from. **The fix** (`state.give_memory_back`, called by
  the keeper after a look that loaded, changed or rebuilt the catalogue: `gc.collect()` then glibc's
  `malloc_trim(0)`; tests `MemoryGivenBackTests`, 3): measured only on models, offline: a model of mixed sizes
  1,669 MB with both, 1,260 MB once the old was dropped, 914 MB after (one alone 825); the keeper itself on a
  prepared file of 12,000 fictional products, three nights: 80 MB without, 75 MB with (start 64). The model does
  not reproduce the server's growth (+43%), so the real gain is known only on the site. Put to the owner: put it
  on the site (a deployment of about 3-5 minutes, the catalogue not prepared again: **wrong, corrected 21/11
  14:50: `state.py` is under the fingerprint's packages, so it prepares again, the first item; deployed 21/11 12:48 UTC as `3701751`**), and, if the memory stays
  high, the stronger remedy that needs the owner (restart the site before the night's preparation; or two
  workers, remedy 3, refused on 20/11). Still waiting: the daily limit of the nightly scan (asked 20/11 23:55).

- **20/11, 23:30 Athens: DEPLOYED on the owner's «Ανέβασε»: the kinds' lists, their rule and the AI's
  answers asked again** (PROGRESS.md, 20/11 20:40, 21:35, 22:25 and 23:30). `e383e7c` on the site (run
  44814871339, release `20261120T205008Z-e383e7c`, prepared 21:09:04 UTC: 389,679 products, 135 shops; site since
  21:20:29 UTC). Read live (run 44819927760, `claude/live-check-2026-11-20`): "boots" and "watches" right, no cables
  or straps; still wrong among the first four cards: printer, tablet, perfume, drill, lego, washing machine, dress,
  mattress, desk, laptop, car tyres. The work branch carries the deployed code (merge `a8e29fc`). What is where: the
  lists `data/kind_lines/google_lines_by_kind.json` (312 kinds, 603 lines chosen by Haiku, each with the lines under
  it; 968 lines its check added, each alone; written by `ai-kind-lines.yml`, push `claude/kind-lines`, `--lists`
  keeps them and asks only the check); rule 2 `ai_shelves.checked_kinds` (a kind kept only when the AI's line is on
  its list; the scan's slips, the tree's first five lines, are no answer); the AI's answers on the server
  (`/srv/picwise/assist/shelves/answers.jsonl.gz`, asked again by `reask_shelves.py` / `ai-shelves-reask.yml`, push
  `claude/shelves-reask`, a key never asked a third time; the first answers in `answers.before-reask.jsonl.gz`); the
  measure `measure_after.py` / `ai-shelves-after.yml` (push `claude/shelves-after`). The last measure (run
  44808052331): 353 of 439 cards right (80.4%; first link 92.3%, second 71.9%); about 1,900 real products hidden
  (1.6%). AI for this work on 20/11: $2.56. **Next:** the nightly scan of new products (a product with no answer
  keeps the old reading), with the daily limit the owner sets (asked 20/11 23:55, proposed $1 a day; measured:
  16,547 keys, 30,264 products not answered now, about $1.15 with the scan's question or $2.25 with the careful
  one, once; then about 900 keys a night, $0.07 or $0.13; `ai-shelves-count.yml`, push `claude/shelves-count`,
  counts them with no key); "car tyres" apart from motorcycle tyres; garden taps (still on the threading taps'
  line); the weak searches above.
- **20/11, 18:50 Athens: the scan DONE ($14.22; answers on the server); the measure after: 69.8% of the
  first 12 cards right (first link 83.5%, second 61.4%; boots, watches, kettle fixed); NOT deployed: rule 2 hides
  some real products and the kind reader misreads some AI lines (PROGRESS.md, 20/11 18:50). **Done at 20:40 (the
  item above), the owner's decision (20/11 18:59: «αυτό πρέπει να το κάνουμε και θα το ξεκινήσουμε σε άλλη συζήτηση»): each kind of the
  site its own list of Google lines (tablet: "Tablet Computers"; watch: "Watches"), written once by the AI (about
  $0.50) and checked; a product in a kind only when the AI's line for it is on the kind's list, the same for both
  links (replacing rule 2's reading of the AI's line through the kind reader). Build it on
  `claude/ai-shelves-rules-2026-11-20`; then the measure after again (push to `claude/shelves-after`; the owner
  wants only the measure after, in plain numbers), and check that real products are not hidden; the site only on
  the owner's «ανέβασε».** Earlier the same day: The owner: the search fell after the second link («στο boots βγάζει και καλώδια ...
  επιλέγω ρολόγια μου δείχνει και λουράκια»; live, read with a fetch: "boots" 3 of 4 cards TV Cables' RJ45
  boots, "watches" Plusshop's and Bazta's Garmin Fenix 6 strap and InStock UK's earring backs), «ότι κανόνες
  ισχύουν για το ένα feed πρέπει να ισχύουν και για το καινούργιο», not product by product: «να φτιάξουμε
  μηχανισμούς και κανόνες σχετικά με το ai που μπορεί να κάνει την ταξινόμηση», «Θέλω να σκαναριστεί σήμερα
  όλος ο κατάλογος... Μετά συντήρηση τα όρια ανα ημέρα θα καθοριστούν μετά». Why: a first-link row carries
  two words of its shop that check each other (its type and a Google line); a second-link row only the first,
  and the Google line was guessed from the same words (`awin_categories`), so it checked nothing. (1) `94e4dfd`
  re-applied on `claude/accessories-fix-2026-11-20` (`5eed766`), NOT deployed: offline it fixes neither live
  example and reads some straps as watches. (2) **The scan** (`claude/shelves-scan`, `c51014d`..`ebf213a`):
  `deployment/server/scan_shelves.py` + `.github/workflows/ai-shelves-scan.yml`: every product once (sizes and
  colours one key, `picwise_ai.shelves.ask_key`), Haiku gives a Google line, checked (`checked_lines` now
  reads a miscopied number by the name, unique in Google's list); answers (keys and lines only) to
  `/srv/picwise/assist/shelves/answers.jsonl.gz`; a run asks only what has none. The owner put $40 in the API
  account («ΠΡΟΣΘΕΣΑ 40»; the PicWise key is in the Console org "Νικος's Individual Org"; the Max plan's
  monthly API credit not linked yet; the first run, 44746448398, was stopped at the owner's word before the
  money). **Run 44750012387 started 14:04 UTC, $38 at most, 300 minutes of asking at most**; GitHub shows its
  notes (`::notice`, read without a login at `check-runs/<job>/annotations`) only when it ends. (3) **The rules**
  (`claude/ai-shelves-rules-2026-11-20`, `picwise_providers.ai_shelves`; 329 modules, 327 pass, 2 as known):
  rule 1, a second-link row's Google line is the AI's, its Awin category columns leave the row, its key kept
  (`ai_shelf_key`); rule 2, every product doubtful when the AI's line gives none of its kinds;
  `picwise-prepare.service` names the answers file. (4) **The measure after** (`measure_after.py`,
  `ai-shelves-after.yml`, push `claude/shelves-after` once the scan's answers are on the server): both links
  prepared with the answers on GitHub's runner, 40 searches, first 12 cards judged. The owner wants only the
  measure after, no before/after. Then the owner's «ανέβασε»; then the nightly scan of new products, with
  daily limits the owner sets.
- **FIRST (20/11, 14:20 Athens): DEPLOYED on the owner's «Ανέβασε»: remedies 1 and 2, and a deployment that
  prepares only when needed.** `ea1e7dd` pushed to `ccr-1361f1a7-dcpo60` at 11:53:02 UTC (fast-forward from
  `857cdb2`; rode along, inert on the site: the AI shelves trial's files, `print_prepare_runs.py`); run
  `44731201677`, success, release `20261120T115315Z-ea1e7dd`, site since 12:16:48 UTC. It prepared (remedy 2 changed
  `tools/prepare_catalogue.py`): **success**, peak 14,615,528 KB, 1,319 s; the step after it: "fresh
  2026-11-20T12:06:09"; 397,577 products, 137 shops (valid until 21/11 18:06 UTC); the price notes written again;
  the site 4,701 MB; 15 of 15 pages and 12 of 12 searches with cards the same on the public site and the server
  (tv 411, laptop 56, kettle 90...). "Tests" on `ea1e7dd`: every module but the two slow ones green. From now on a
  deployment that changes neither the catalogue's rules nor the preparation takes about 3-5 minutes (owner:
  «από ποια αλλαγή δεν αφορά τον κατάλογο γιατί πρέπει να περιμένουμε μισή ώρα?»): `deploy.sh` prepares again
  only when the new release would not read the file in place, `tools/prepare_catalogue.py` or
  `picwise-prepare.service` changed against the release the site runs, or the file is 24 h old or more. Remedies: (owner, of three remedies: «Κάνε το ένα και το τρία», then «Άκυρο ... κάνε μόνο το ένα», then «Φτιάξε
  και αυτό [το 2]»: 3 not done, the site keeps three workers). Remedy 2: `tools/prepare_catalogue.py` chooses the
  feed's copy once and the intake reads the same (no second download or parse in a run; test
  `tests/test_picwise_prepare_reads_the_feed_once.py`). Remedy 1, on the work branch: `deploy.sh` runs `deployment/server/prepared_state.py` with the
  new release's code after the preparation and before the restart (the file's first fields, the site's own states,
  without loading the catalogue); unless "fresh", `current` goes back to the release the site runs, its units are
  put back, the site is not restarted, and the deployment fails. Tests: `tests/test_picwise_deploy_keeps_the_site.py`
  (11, the step run in bash both ways). Nothing under `src/picwise_providers` or `src/picwise_nlu` changed:
  fingerprint `744f91ce…`, so this deployment keeps the site's file whatever its preparation does. Rides along to
  the site: the AI shelves trial's files (`bff970a`; nothing of the site imports `picwise_ai.shelves`),
  `prepare-runs.yml` and its script, records.
- **The site now (read on the server, run `44726998584`, 11:26 UTC):** it answers from the catalogue the 10:04
  deployment's run prepared at **10:17:27 UTC** (written 10:19:40, before that run was killed in its intake), from
  the night's download: valid until **21/11 16:17 UTC**, not 10:33 as written before. The public note
  `/prepared.json` still names 04:33:55 (that run never rewrote it), and the price notes are the night's, so the
  cards tell no price history until a preparation completes (`price_history.notes_for_catalogue`). The site's three
  workers 1,619 + 1,560 + 1,607 MB (fresh since 10:31; about 2.9 GB each after a night's swap); 17.9 GB available.
- **Why the feed's preparation failed (owner: «μας ενδιαφέρει γιατί δεν δούλεψε το feed»): memory, each time**,
  read with `prepare-runs.yml` (`deployment/server/print_prepare_runs.py`; runs `44724187812`, `44724683162`).
  (a) 08:56-09:10 (`94e4dfd`): the whole server out of memory (23.4 GB, no swap): the site's three workers 2,953 +
  2,909 + 2,939 MB (the night's catalogue, swapped in at 04:43), the preparation 13,994 MB, killed before writing
  anything: not shown to be `94e4dfd`'s code. (b) 10:04-10:30 (`857cdb2`, `02e0ac5`'s code): its own ceiling,
  18,405 MB of 18 GB: the feed's download lives 6 h (`awin_adapter._DEFAULT_FEED_CACHE_TTL_SECONDS`); the night's,
  of 04:17, expired at about 10:17; `_intake()` (`measure_configured_feed_intake`) after the catalogue (10:19:40)
  downloaded both links again (10:21:52, 10:23:32), missed the pipeline's cache (keyed by the file's identity) and
  parsed all 2.7 M rows a second time beside the first. (c) 19/11 17:21 (`5500291`): its ceiling, then 17 GB. The
  nights pass (20/11 04:17: peak 14.6 GB, 25.9 min). Remedy 2 would end (b); without it (b) recurs whenever a run
  meets the download's sixth hour, but with remedy 1 the site keeps its file. Before all this, the way back:
  `857cdb2` (`git revert 94e4dfd`) deployed on the owner's «ανέβασε την επιστροφή» (pushed 10:04:19 UTC, run
  `44716070185`), products again from 10:31:46 UTC, none from 09:12; merged into the work branch (`5f13349`).
  `94e4dfd`'s change (parts and accessories before the thing they serve) is off on the site and the work branch
  ("kettle" shows a paint kettle and a kettle lead again); it comes back by reverting `857cdb2`, on the owner's
  «ανέβασε». `prepare-runs.yml` runs on a push of its two files to `claude/prepare-runs-2026-11-20`, or by hand
  once on `main`.
- **The AI's shelves, the trial of 1,000 (owner, 20/11: «Ναι κάνε καί τά 2»), done: run `44708919103`**
  (`bff970a`; `picwise_ai/shelves.py`, `deployment/server/measure_shelves.py`, `.github/workflows/ai-shelves-trial.yml`,
  off again after it). The night's catalogue of 20/11 04:33 (397,635 products): 20 calls of 50, **$0.0696 in
  all, $0.07 for 1,000**; the cached tree 77,287 tokens (under the 100,000 that cost five times), 13.3 s a call.
  The whole catalogue at that price ~$27.68, ~$13.84 through the Batch API. **A** (500 of the first link, the
  shop's own Google line hidden): a line for 399, "none fits" 4, **refused 97** (number and name not agreeing);
  of the 399, the same category as the shop's (the cap's two levels) 86.0%, the same line 73.9%. **B** (500 of
  the second link): a line for 444, refused 54; deeper on the same path 40.1%, the same 16.0%, another branch
  21.8%, another department 22.1%; 2.4 levels now on average, 3.7 the AI's. The second link's products in that
  catalogue were from `02e0ac5`'s rules, which kept every row's category words, so B is not only broad shelves.
  Next: read the log's 40 disagreements of A and the 60 of B (who is right), cut the refusals (most likely a
  number miscopied: take the line by its name inside the branch, or ask for the full line), then the owner's
  daily cap before any run over the catalogue.
- **NEXT, step 3 of the series, the brands' list (owner, 19/11 23:46; taken up on 20/11: «PicWise:
  συνέχισε το βήμα 3, τη λίστα brands, όπως γράφει το handoff»): (1) measured, (2) put to the owner (20/11
  ~00:30 Athens), waiting for the answer; then (3) build.** All of it on the branch
  `claude/brands-2026-11-20` (from `d1513e8`), never on the work branch until finished and tested:
  `deployment/server/print_brands.py` (tests 11) and `.github/workflows/brands-measure.yml` (the server's file
  copied as `search-audit.yml` does, nothing on the server or the site changed; `if: true` for one run). Run
  `44626133872`, the catalogue of 19/11 21:32 UTC (403,545 products, 137 shops): 99.1% carry a brand; 7,424
  brands, 3,876 of 3 products or more (some are shops' own names the rule misses: Swadesi, DIY Refurb); 95
  written several ways (8,436 products: "Black and Decker"/"Black & Decker"; broken letters "PokÃ©mon").
  **Dyson: 8 products, all parts.** Samsung 2,046 (televisions 332, monitors 153, chargers 65, headphones 49,
  phones 37...; 1,178 of no kind read). 151 brands are read alone as a kind (razer -> electric shaver,
  motorola -> engine oil, draper -> nappies); 306 are English words (Apple, Canon, Brother); "apple" and
  "nike" alone answer nothing, by the early stage's guards, which hold "bosch" too
  (`category_detector._OVERMATCH_SINGLE_TOKEN_GUARDS`, `broad_query_suggestions._UNSAFE_BROAD_QUERY_TERMS`). A slip of 2,019 of the 3,480 names of 5 letters or more
  reads as it alone; 607 are one slip from another brand or a word (Canon ~ cannon). The 120 largest brands:
  alone, 90 "not sure", 4 nothing, 19 the brand's product first; with their largest kind, 105 of 112 right
  ("samsung tv" works); misspelled alone, 86 of 101 nothing; misspelled with the kind, 29 of 94 the brand's
  first. The kinds' choices inherit the kinds' reading ("belt" for Bosch Professional's sanding belts).
  **Put to the owner:** a brand alone (a question "What kind of Samsung product?" with its kinds and its
  products below, or its products only); a misspelled brand (corrected when only it is that close, else "Did
  you mean"). **The build, after the answer:** a list of brands made each night from the feeds (spellings
  joined, broken letters mended), read by the search: a brand alone, a brand never corrected into a kind, a
  slip read as the brand; the old guards and `brand_resolver` replaced; measured again with the same
  workflow, before and after; a picture to the owner before any wording; then into the work branch.
  **Safety (owner, 19/11: «Είναι ασφαλές ή θα συγκρουστεί?»):** two conversations share the work branch and
  every deployment takes all of it, so the brands' work stays on its branch until finished and tested;
  before any push to the site branch, what else rides along is checked and the owner asked; measures on
  GitHub's runner (the server is at 19.8 of its 20 GB at night).
- **NEXT (owner, 19/11 night): the AI to give every product its Google shelf** («εκτός από τον bot.... Μπλέξουμε και
  το ai για να ταξινομήσουμε όλο τον κατάλογο»). In order: (1) `search-audit.yml`, right answers per feed, the
  before; (2) a trial on 1,000 products, under $1: title and the shop's own category in, a line of Google's
  taxonomy out (an answer outside it refused), the real cost and accuracy measured; (3) the whole catalogue, each
  product asked once and kept on the server, the night's new ones after, under a daily cap the owner sets. First
  the second link's broad shelves (Tooled Up's 163,000 «DIY»), then the first link's ~900,000 rows held for no
  category (mostly InStock UK), which could become products. The AI sets only the shelf
  (`google_product_category`); every rule stays as it is. The families service (`picwise-families`, $5 a day) is
  the model: about $0.0015 a job of 25; estimated $20-40 once for all, cents a day after.
- **19/11 evening: both Awin links live** (`6c5d6b5`, 363,689 products from 138 shops; preparation 14.1 GB,
  21.8 min; site 5.6 GB with 3 workers; 19.8 GB at night, limit 20). **Next, the search's accuracy with the new
  shops:** a word in a title is not enough when the row's aisle disagrees with the kind searched (kettle -> paint
  kettle, kettle lead; car tyres -> printer feed tyres; router -> modem lead, router collet nut). Read the second
  link's aisle (`awin_categories`) against the kind's department, as the Google shelf is read for the first link.
- **NEXT (owner, 19/11: «Θα υλοποιηθεί η διαδικασία σε άλλη συζήτηση»): the second Awin link, road 1, cut the
  preparation's memory.** Built and on `main` and the work branch, nothing on the server or the site:
  `catalogue_balance.cap_limits` (`PICWISE_CAP_SHARE` 0.15, `PICWISE_CAP_CATEGORY_MAX` 12,000, in
  `picwise-prepare.service`); `awin_adapter.second_feed_config_from_env`/`merge_feeds` (`AWIN_FEED_URL_AWIN` or
  `AWIN_FEED_FILE_AWIN`, a shop in both read from the first by advertiser id); `awin_categories` (each Awin-format
  row's aisle from its category words); `.github/workflows/trial-prepare.yml` + `.github/scripts/print_trial.py`
  (by hand: the first link alone and both, each category, the shops added, peak memory). The trial of 19/11
  (run `44561166923`): both links 347,018 products from 138 shops, peak 15.4 GB, 14.9 min; the first alone with the
  new limit 167,583, 9.0 GB. With the site at about 10 GB that is about 25 GB at night of the server's 24 (limit 18).
  **The step:** drop the second link's rows that can never show before they become products (not in pounds, no
  price, out of stock, no category words, a shop the first link has, Luxefashion/Aussui-like rows), read row by
  row, then run `trial-prepare.yml` again and compare the peak. If still too high, the owner chooses: a lower
  `PICWISE_CAP_CATEGORY_MAX` (smaller site, same preparation) or a larger server. Only then, on the owner's «ναι»:
  `AWIN_FEED_URL_AWIN` into the server's settings (`server-deploy.yml` writes `/etc/picwise/picwise.env`, as it does
  `AWIN_FEED_URL`) and a deployment. The new limit cuts the first link alone to 167,583: deploy it with the second
  link, never alone. Also asked by the owner: commission from every shop (the owner joins programmes through Claude
  in Chrome); describe PicWise to shops as a shopping search, never «price comparison».
- **Awin-format feeds again (owner, 19/11), the decision of 20/10 changed:** «Όταν είχα βάλει αυτόν τον κανόνα δεν
  είχαμε αναπτύξει έξυπνο search.. εφόσον το σετ μπορεί να υποστηρίξει την υποδομή της awin προχωράμε πρέπει να
  παίρνουμε προμήθεια από όλους». Awin puts the two formats in separate links («You can only select advertisers that
  use the same datafeed format»; 213 feeds in Awin's format are offered): a second link, in the secret
  `AWIN_FEED_URL_AWIN`, read beside `AWIN_FEED_URL` once measured (shops, rows, pounds, categories, size, memory).
  Commission only from programmes that accepted the owner (Joined): the owner to join every programme of both feeds.
- **19/11 afternoon, one card per product, the owner's lasting rules: the AI's families built and
  deployed (this record's push; the owner: «Ανέβασε προοδευτικά να τελειώσουμε τις εργασίες», then «Το
  όριο του ai μπορεί να ανέβει για την ώρα δεν θα περιμένω τη νύχτα για να κάνει το σκανάρισμα θα το
  κάνουμε τώρα»).** The owner's three rules (Decision Contract, "One card per product", 4): (1) a page with
  the variants, one card; (2) a shop listing each variant as a product, one card, the AI deciding the
  doubtful; (3) another shop's cheaper variant marked on the grouped card. Built for (2):
  `product_variants.title_parts` (own words and variant words), the words' tie
  (`sizes_apart_key`: one shop and brand, the same own words, only sizes or amounts apart: joined at
  search time, no AI), and for a colour or a number apart the AI: `family_jobs.py` (as `picwise`, after
  each preparation and at each deployment) writes the sets, each page and each size-only listing once, at
  most 20 a set, those not answered; `picwise-families` (as `picwise-assist`, its key) asks Claude Haiku
  5.5, 25 sets a call, at most **$5.00 a day of its own** and 20 calls a minute; answers checked (each
  listing in exactly one group), kept in `answers/families.json` (the site reads it,
  `PICWISE_FAMILIES_FILE`) and `answers/sets.json` (titles, for the sample). Sets by the name the titles
  begin with (`head_key`), so prints are asked too. **To check the AI's work:** `server-health.yml` by
  hand prints the last sets written, today's spend, the jobs waiting, the last calls and a sample of 60
  sets joined or kept apart (`print_families.py`). First scan (13:21 UTC): 6,162 sets, 247 jobs, ~7
  calls a minute, ~$0.0013 a call; live, "alienware aw420k keyboard" one card. Then (16:xx Athens) the card
  names its variants ("Colours at the shop: …", `variant_names.variant_values`), a picture sent first;
  then rule 3 (`_cheaper_elsewhere`): another shop's cheaper variant a card of its own, marked on the
  family's card ("White, Size 9 is £35.00 at Other Shoes"), deployed 15:47 UTC (`1aebe8c`). Open:
  `catalogue_cap` counts rows. **The next push to the site branch also deploys the other session's cap
  limits (`d3c5b49`, "Not deployed"), merged into the work branch: ask the owner first.** Next: the card listing the variants (as drawn for the owner), then rule 3, then
  `catalogue_cap` counting products; then the series' steps 2-4.
- **19/11 afternoon, the owner's series of work, step 1 of 4 deployed: one card per product** (the owner:
  «Ανέβασε προοδευτικά να τελειώσουμε τις εργασίες»; the series agreed on 19/11 at night: 1. one card per
  product, sizes and colours chosen at the shop; 2. accessory or main product, the doubtful ones judged by
  the AI at night; 3. a list of brands from the feeds, their kinds counted; 4. the ~254,000 products with
  no kind, by the same night's work). Deployed today: at 10:33 UTC `782b029` (the sale prices' night
  count and the daily session's rows past the header left out: «Ανέβασε»), at 11:18 UTC `e9aa85a` (one
  card per product), then the size words' refinement (this record's push). The feed names a group,
  colour or size on almost no row, so the tie is the shop's product page (`product_variants.page_key`,
  `titles_close`; `search_selection._join_variants`). Measured (`feed-compare.yml` by hand from the work
  branch, runs `44508614034`, `44509788194`, `44511198948`): 929,143 rows would join a row of their
  product. Checked live: "tracksuit" no longer shows "Dominate Tracksuit - 2XL" and "- S" both. Open:
  the cap still counts rows (`catalogue_cap`), so variants still take places in the prepared catalogue;
  a shop with a page per colour (Geepas' kettles) is not tied. Next: step 2, accessories.
- **19/11 noon, the daily session: why no product stood at a sale price, measured; and rows read with
  their fields out of place, left out (built, tested, pushed to the work branch; NOT deployed: waits for
  «ανέβασε»).** `feed-compare.yml` by hand from the work branch (runs `44501037362`, `44502112273`; the
  run's red is the known "new link lacks 5 shops", not the measure): of 1,683,586 rows of the feed in use,
  **154 carry a `sale_price`, 153 of them InStock UK's, 1 Back to the Office's**; by the site's rule 19 in
  force, 38 not lower, 22 dates unread, 75 price unread. The unread ones read "Union Jack", "in_stock" and
  pieces of JSON: **202 rows carry more fields than the header (201 of InStock UK's 1,033,769, 1 of Back to
  the Office's)**, and the site read them field by field, so a field could stand under another's name (a
  price from another column). Fixed at the cause (`awin_adapter._parse_csv_stream`): a row with a filled
  field past the header is left out whole; empty ones past it (a trailing comma) change nothing. So the
  first night's 0 is mostly the shops' choice: the feed gives almost no sale prices. Whether the 19 are
  among the products the search keeps: the late morning's night count (`sale_prices`) says after a
  deployment. `print_search_reading.py` byte for byte the same; 316 modules, 314 pass, 2 fail as known.
- **19/11 noon, the daily session: the feed's sale prices counted today, without a deployment.** The
  read-only `feed-compare.yml` (by hand, from the work branch) now counts, for the feed in use, the rows
  with a `sale_price`, those the site's rule takes tonight and each reason for the rest
  (`normalization.sale_price_reading`, the late morning's function), the shapes of unreadable values
  (digits as 9) and the 15 shops with the most; numbers and shop names only. The morning's checks: the
  night's note `prepared: true` (08:59 UTC, the deployment's), 255,564 products, 78 shops, nothing
  shrunk or gone; `server-health.yml` by hand (`44499092746`): within every limit, searches 0.15-0.48 s
  the server's part.
- **19/11 late morning, the sale prices counted (built, tested, pushed to the work branch; NOT deployed:
  waits for «ανέβασε»).** The owner, offered a count of why the first night read no sale price and a look
  at the new pages, answered «Ναι». `normalization.sale_price_reading` names why a row's `sale_price` is
  or is not its price (used, price unread, not lower, other currency, dates unread, not begun, ended,
  ending within 24 h; `sale_price_in_force` now reads through it, the rule unchanged); the memory's
  summary gives `sale_prices` (how many give one, the readings, the 8 shops giving the most), printed by
  `print_shops.py` under the memory's line ("sale prices: ...") and by `prepare_catalogue.py`. Read it in
  the deployment's "Each shop of the prepared catalogue". The look at the pages: the session's fetch of
  the site needs the owner's approval on their screen, unanswered twice (09:1x and 09:37 UTC).
- **19/11, the shop's own price: DEPLOYED 09:08 UTC on the owner's «Ανέβασε» (10:51 Athens)**: `512ebf2`
  pushed to `ccr-1361f1a7-dcpo60` at 08:52 UTC, a fast-forward from `82f2f49` (it carried only one more
  record line, of the wording's deployment); run `44491367174`, release `20261119T085257Z-512ebf2`.
  Preparation 821 s, 9.43 GB at its peak; health ok; 15 of 15 pages the same live and on the server;
  offers fetched again (101 live, of 32 shops). **The memory's first night of sale prices: 0 of 255,564
  products at the shop's sale price, so no history restarted.** The feed has 69 columns
  (`feed-compare.yml`, 18/11), so `sale_price` is likely among them but empty, or filled in a way the
  rule leaves (not lower, other currency, dates not read or not live): not known which; a count of the
  rows with a `sale_price` and why each is left would say (a change: the owner's yes, then «ανέβασε»).
  Seen in the deployment's check: `kettle` shows one Geepas kettle in three colours as three cards (the
  owner's wish of 19/11: one card per product, sizes and colours at the shop), `tv` shows TV units and
  dongles (the accessory step). The record below, as written before the deployment:
- **19/11 night, the shop's own price (built, tested, pushed to the work branch; NOT deployed: waits
  for the owner's «ανέβασε»).** The owner: «Θα ήθελα να αποφύγουμε τους υπολογισμούς τιμής», then «Στην
  έκπτωση τραβά στην τιμή της έκπτωσης». (1) No price after an offer: `product_offers.price_after_offer`
  removed with its tests; the order, the Recommended, the price bar and the cards read the shop's own
  price; the offer stays on the card in the shop's words; the heading says "cheapest first". This also
  ends a fault found that night: the cheapest shop of one product was chosen before offers, so a shop
  whose offer made it the cheapest was dropped. (2) The shop's sale price: Google's `sale_price` was never
  read (`_PRICE_KEYS` took `price` first), so a product on sale showed its usual price. Now
  `normalization.sale_price_in_force`: lower than `price`, same currency, live by
  `sale_price_effective_date`, not ending within 24 h; unreadable dates leave the usual price. (3) The
  memory: on the first night of sale prices (`meta.sale_prices_read_from`) a product the sale price
  changes starts its price history again (no ▼ nobody can date). How many rows carry a sale price is
  not known (no feed here): the night's note now says `on_sale_tonight` and
  `history_restarted_tonight`; read them after the deployment, whose own preparation (`deploy.sh`)
  is the first night of sale prices.
  Rules, contract ("The shop's own price"), README, MISSION, LANDING and AI specs, legal pages
  (Last updated 19 November 2026) changed with it.
- **19/11, the records of the order brought to the rule** (owner, 19/11: «Η προσφορές βγαίνουν πρώτα μόνο αν είναι
  φθηνότερες», the rule of 15/11 said again): `README.md`, `docs/MISSION.md`, this file's rules,
  `docs/PICWISE_DECISION_CONTRACT.md` (rule 4 of "Price first", the complex search's order, the price bar),
  `docs/LANDING_PAGE_SPEC.md` ("More") and `docs/PICWISE_AI_LAYER_SPEC.md` still said "offers first". Records
  only: the site has ordered so since 15/11; nothing deployed. The claude.ai Project "PicWise" now holds a short
  overview of the stable facts (`claude/PicWise-overview.md`; the repository wins where they differ).
- **In the owner's plans, not built (18/11):** a price-drop alert for a favourite («Αυτή τη στιγμή δεν στέλνουμε
  ειδοποίηση τιμής... Το έχω στο σχέδιο μου»). It needs email from the site and a place for each visitor's favourites
  (today they stay in the browser): to be discussed with the owner first. Until then nothing says PicWise alerts.
- **How PicWise is described to shops and networks (owner, 18/11):** never «price comparison» («Δεν θέλω να λέμε
  ότι είμαστε σύγκριση τιμών ... δεν λέει και την αλήθεια»). PicWise is a shopping search that helps the buyer buy:
  a search's range from the lowest price (an offer counted where it surely applies), one product at the category's
  middle price, the price's history, favourites and their price falls, the shops' offers; shops are not compared with
  one another (for an exact model, its cheapest shop first, then the rest). Currys (Awin) refused the owner's application
  on 18/11: «Site does not complement advertiser brand»; the big names again once the site has visitors from Google.
- **18/11 evening: offers back, further photos measured.** New Awin token (90 days, to about 16/02/2027; renew before)
  in `AWIN_API_TOKEN`, carried to the server by re-running the last deployment: 101 offers from 32 shops, within every
  limit. `feed-compare.yml` (now by hand from `main`): the feed in use **already has** `additional_image_link`; only
  634 of 1.68 million rows fill it, so few cards can show further photos, by the shops' choice. The owner's new link
  (`AWIN_FEED_URL_NEW`) lacks five shops and adds nothing: `AWIN_FEED_URL` stays. The memory worry for the column is gone.
- **18/11, the conversation of the daily work's checks again** (owner: «Υπάρχει κάτι σε αυτή τη συζήτηση
  που δεν έχει κλείσει ή δεν έχει ανέβει?», then «Main ίδιο με το site», «Διόρθωση ώρας ελέγχου», «Σβήσε την
  προεπισκόπηση»). GitHub started `server-health.yml`'s schedule (08:07 UTC) 9 to 10 hours late, after the
  daily session (16/11 18:20, 17/11 17:32, 18/11 17:09 UTC): the session now starts it by hand at its start
  and reads that run (`docs/PICWISE_DAILY_WORK.md`, step 2); the schedule stays as the evening's second look.
  `main` brought to the site and its records by a fast-forward (it was 6 commits behind: the first run's
  record and the 16/11 daily session's five, live since that day). The private preview of 15/11 deleted.
  The daily task of 18/11 did not run ("usage limit reached" at 09:43 UTC; no email that day). The last
  health run (18/11 17:09 UTC): only the offers over the limit (15.5 days; Awin 401); the site 7.3 GB, at
  night 16.2 GB of the 18 GB limit, so the `additional_image_link` column (about +1.5 GB) is measured first;
  173 visitors' searches in 7 days, 84 different.
- **16/11, the daily session (12:00 Greek time).** Read at 09:44 UTC: the night's note `prepared: true`,
  prepared 04:25 UTC, 254,756 products, 78 shops, nothing shrunk, gone or new; `price_notes` 0 ▼, 0 ▲ (first
  chips about 19/11). `server-health.yml`: today's run is the one by hand at 07:33 UTC (`43824703638`); the
  schedule of 08:07 UTC did not run, the workflow having reached `main` at 07:32 (look again tomorrow); only the
  offers over the limit (Awin 401, the owner's token). The Sunday tidy-up: its first scheduled run is 22/11.
  **Step 11's list read for the first time** (`c93be3c` live since 15/11): it is in `prepared.json` under
  `shop_catalogues.words_to_learn` (not `balance`, which stays empty by design), 100 types, 41,109 rows held
  whose type names no kind. Reviewed: **no type learned.** Most rows are Back to the Office's office and IT
  accessories, kinds PicWise does not have (tablet enclosures 2,936, privacy filters 1,983, mounts, UPS
  batteries): a lexicon proposal, which is the search's accuracy (the owner, 12/11: later). Where the type
  names a kind PicWise has, the row's title contradicts it, by the rule a doubtful row held ("Laptops" 200,
  "PCs/Workstations" 493: their titles read "Mobile Workstation" as `desktop_pc`, "256 GB SSD" as
  `storage_drive`; accuracy, not touched). Only Homespace Direct's "Made-to-Measure" 487 (curtains) and
  Finediam's "Sidestone" 126 (rings) could be learned, but a learned type names the kind of every row of it
  whatever its title says (`search_selection._product_concepts`), and two titles cannot show that all its rows
  are one kind (blinds among the curtains). **Built (measured only, nothing a search shows changes):** with each
  type to review, what each of its rows' titles reads as alone, the most first (`title_reads`, at most 4; the
  server's report: "titles read: curtains 470, none 17"); about 2.5 s more at night for 41,000 rows. The search's
  reading byte for byte the same (`print_search_reading.py`, only its time line differs); 315 modules, 313
  pass, 2 fail as known. To go on the site with the next deployment; then learn by review the types whose
  titles read one kind.
- **16/11, the daily work's checks (session branch `ccr-d4dcbe0e-4y2sjf`, `c67fd5c`): on `main` and the work
  branch on the owner's «Ναι, ανέβασέ το».** The owner chose «Εβδομαδιαία σύνοψη Κυριακής», «Έλεγχος προσφορών,
  ταχύτητας και πόρων», «Ήσυχες μέρες: μία γραμμή»: `.github/workflows/server-health.yml` (read-only, 08:07 UTC
  daily; `deployment/server/print_health.py`, its limits; `count_searches.py`, numbers only) and
  `docs/PICWISE_DAILY_WORK.md` steps 2 and 4 (a scheduled workflow runs only from `main`). First run by hand,
  `43824703638`: only the offers over the limit (not fetched since 03/11, Awin answers 401: a new token, the
  owner's). **The server's room, measured now:** the site 6.8 GB once its workers have the catalogue (the
  deployment's 4.1 GB was read while they still loaded it), the preparation 9.0 GB at its peak; 15.8 GB at night
  of 22.9 GB, the limit 18 GB. The `additional_image_link` column, estimated at +0.5 GB and +1 GB, would bring
  the night near 17.3 GB: measure it (`feed-compare.yml`) before taking it in.
  The owner's open items: a new Awin token (no offers fetched since 03/11, 401); `additional_image_link` in
  Create-a-Feed and the secret `AWIN_FEED_URL_NEW`; a private way to show the searches' words, if wanted
  (to propose on 22/11).
- **15/11, the conversation on photos, offers and the price bar (session branch
  `ccr-d4dcbe0e-4y2sjf`, from the work line's `7e297d1`): four changes built, tested,
  pushed, not deployed** (no «ανέβασε» yet). The owner's words, 15/11: «1. Η προσφορές δεν
  πρέπει να βγαίνουν πάνω από το φθηνότερο προϊόν. 2. Ο χρήστης μπορεί να διαλέξει στο
  φίλτρο τιμής από έως. 3. Ο χρήστης μπορεί να έχει τη δυνατότητα η εικόνα του προϊόντος
  να μεγαλώνει. 4. Ο μηχανισμός διακύμανσης τιμής θέλω να φανεί στις κάρτες». `ad00848`
  the price's history on every card from the first night (no arrow until a price is kept
  7 nights); `5bc3a4f` the price bar from and to (`max`); `50eba46` the order at the price
  after each offer where it surely applies (`product_offers.price_after_offer`), no
  offers-first block; `407483b` the photo opened large, with up to three further photos
  from `additional_image_link`. Then, on the owner's private preview link: the history
  telling the shop's price, an offer naming a kind for new customers kept to that kind,
  48 px taps on a phone, a title never cut through when a phone sets text larger, and the
  Recommended the middle price, on offer or not (owner: «Το προτεινόμενο πρέπει να
  εξακολουθεί να δείχνει τι μέση τιμή»). **Deployed 13:26 UTC, release
  `20261115T130949Z-410be36`, with `c93be3c` (owner: «Ναι, μαζί»).** Next: no live card
  has a further photo; the owner to add `additional_image_link` to the Create-a-Feed
  link's columns and put the new link in `AWIN_FEED_URL_NEW` (then `feed-compare.yml`).
  The ▼/▲ chips from about 19/11, as before. Then, deployed 14:44 UTC (`9a5cf3f`): a
  card in its place at once, a grey frame with a turning sign while its photo loads
  (Google's layout shift 0 with photos slowed to 2 s, from 0.87 on a phone). **Left for
  later (owner, 15/11: «Το αφήνουμε για αργότερα»):** keep only the first 3 links of
  `additional_image_link` in the prepared catalogue, to be done with the new column. The
  server's room, from the deployment of 15/11: the site 4.1 GB, the catalogue's
  preparation 9.4 GB at its peak and 800 s, of 24 GB; the column estimated at about
  +0.5 GB for the site and +1 GB for the preparation (not measured: `feed-compare.yml`
  will). The
  grouping of a product's sizes (S/M/L) into one card, proposed, was not asked for and
  not built.
- **15/11, the daily session:** the night's note read at 09:44 UTC: `prepared: true`, prepared 04:25 UTC, 254,711 products, 78 shops, nothing shrunk, gone or new; the memory's fourth night (256,368 known, 330 new, 383 prices changed, 521 gone since 14/11); `price_notes` 0, as expected (first chips about 19/11); `balance.words_to_learn` still empty, as expected (`c93be3c` not deployed). `/health` 200; `kettle`, `sofa`, `office chair`, `tablet` 4 cards each, 0.41 to 0.73 s. No new run since 13/11; "Tests" green on `d10c53f` and `c93be3c`. No code changed, for the same reasons as 14/11. Asked again: deploy the work branch's head (`c93be3c` with it); no answer from the owner on 14/11.
- **14/11, the daily session:** the night's note read at 09:44 UTC: `prepared: true`, prepared 04:25 UTC, 254,787 products, 78 shops, nothing shrunk, gone or new; the memory's third night (256,038 known, 630 new, 1,988 prices changed, 703 gone since 13/11); `price_notes` 0, as expected; `balance.words_to_learn` still empty, as expected (`c93be3c` not deployed). `/health` 200; `kettle`, `sofa`, `office chair`, `tablet` 4 cards each, 0.41 to 0.73 s. GitHub's "Tests" green on `d10c53f` (run `43409039192`; the head adds records only). No code changed: step 11's mapping needs the list `c93be3c` writes, and the reading of kinds is the search's accuracy, which the owner put off (12/11). Asked again: deploy the work branch's head (`c93be3c` with it).
- **Next (owner, 13/11): «Πάμε σε άλλη συζήτηση για να με κατευθύνεις για τα google
  ads».** Guide the owner, step by step and in plain Greek, to a Google Ads account whose
  only use is Keyword Planner's data: the month's ten ("Most popular in the UK",
  `picwise_surface.trends`) and the keywords of the first pages for Google
  (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, "Keywords"). What is known (31/10 and 13/11; read
  Google's own help again before each step, it changes): no subscription and no ads, the
  owner's wish («δεν θέλω να πληρώσω ... συνδρομητικά»): create the account in Expert
  mode, without a campaign ("create an account without a campaign"), never start a
  campaign; the business is the owner's (seat in Greece), the market measured is the
  United Kingdom, English; without spending on ads Keyword Planner gives ranges
  ("100–1K") rather than exact numbers, enough for the keywords of few searches, coarse
  for ranking the ten (Google Trends, free, can order products within a range). The data
  comes as a file the owner downloads from Keyword Planner ("Discover new keywords" from
  a few seed words, or "Get search volume and forecasts" for a list) and sends in the
  chat: a file of keyword figures holds no secret; a login, password or key never goes
  into the chat (an API's key, if ever, into GitHub's secrets). The seed words: the kinds
  of the keywords' step 1 (three shops or more, products of £80 or more), drawn from the
  catalogue once the owner says yes; for the ten, broad shopping words of the UK. Nothing
  of Google's numbers is shown on the site: the ten show no number of searches.
- **13/11, the conversation "Top 10 commercial products" (session branch
  `ccr-f213d01e-zos3xz`, from the work branch's `5eb1bbb`): the price chips live since
  10:40 UTC** (owner: «Ανέβασε για τα σήματα..»; `ed2f6ac`, run `43409019580`, release
  `20261113T102609Z-ed2f6ac`; deployed without the daily session's `c93be3c`, which waits
  for the owner; the work branch holds both since the merge `d10c53f`). On the site: 0
  notes tonight, as expected; **check about 19/11 that the first chips show** (the night's
  note, `price_notes`; a search with `curl`). The owner's plan: apply to
  more shops once the site shows it does more than a search: the month's ten and the
  price's movement («πριν από αυτό πρέπει η σελίδα να είναι έτοιμη»).
  - **The price chips** (owner, to the pictures: «Συμφωνώ με το σχεδιασμό»; the 7 nights
    explained to the owner, who asked): on every card a green ▼ "£40 since 6 Dec", a red
    ▲, a grey "Same price for N nights", a tap opening the last 30 nights. Today's price
    against the last price the shop kept 7 nights seen; at least £1 and 1%; within 30
    nights. The memory now keeps which nights each product was seen on (`seen_nights`;
    the server's memory of 12-13/11 gets the column at the first preparation of the new
    code); `price_notes.json.gz` beside the prepared catalogue each night; a worker shows
    a note only beside the catalogue of the same preparation. The first chips about
    19/11. `docs/PICWISE_DECISION_CONTRACT.md`, "The price's history on the cards".
    Commits `f876c31` to `9a3045d`. After the deployment: read the preparation's line
    "the price notes: …" and `prepared.json`'s `price_notes`, then a search with `curl`
    (no chip until a price was kept 7 nights: none expected before about 19/11).
  - **The month's ten** (still hidden, no source): "Most popular in the UK", no number of
    searches, rows PicWise's shops lack kept (owner: «Τα 10 πιο διαδεδομένα προϊόντα»,
    «Δεν θέλουμε να δείξουμε τον αριθμό των αναζητήσεων», «Δεν μας ενδιαφέρει να τα έχουμε
    όλα»). Its source and the keywords' are one Google Ads Keyword Planner file: the
    owner's free account (no ads) is the first step; Search Console only measures the
    pages after they reach Google. Told honestly: the UK's ten (iPhone, PlayStation,
    AirPods) are mostly not in the shops ("iphone 17" answers 31 cases).
  - **Keywords** (owner: few searches, little competition, many keywords a page, a first
    batch of about 10 pages of kinds of £80 or more): agreed and written as a plan,
    `docs/PICWISE_GOOGLE_PAGES_SPEC.md`, "Keywords"; its step 1 (kinds with three shops or
    more and enough products of £80 or more, from the catalogue) proposed, no yes yet.
    Furniture is where the catalogue compares shops; monitors, memory, saunas and rings
    come from one shop each.
  - **Waiting for the owner:** the Google Ads account; the new
    Awin token (offers not fetched since 03/11; «προσφορά εάν υπάρχει» means never until
    then); the domain to keep before Google; the yes to the keywords' step 1.
- **12/11, the design: its first part live since 15:45 UTC** (owner: «Ανέβασε»; release
  `20261112T153132Z-79f106b`, run `43248689369`; the work branch fast-forwarded to
  `79f106b` with it). Built on `ccr-9953c583-wz6sfv`
  (the owner, in the conversation on the design: the site «μοιάζει πιο πολύ με εφημερίδα
  και όχι με search αγορών πρέπει να γράψουμε λιγότερα»; to the design proposed «Έχεις
  δίκιο για αυτά»; the heading kept, «3», since a heading of price comparison «θα κλείσουν
  πολλές πόρτες» and PicWise «στηρίζεται στην αξιοπιστία της πληροφορίας»; the loading
  screen «φτιάξε απλά ένα όμορφο φόρτωμα»). Commits `33c7165` to `0418f4a`, on top of the
  work branch's `db66ab7` (a fast-forward for it): a plain loading screen, the PicWise
  mark turning, no number (the scanning screen's wrong count gone with it); the home
  page with its heading, the box and three facts ("250,000+ products from 80 UK shops",
  counted from what the search keeps after the cap; "In stock only, updated every
  night"; "Never ranked by commission"), no paragraph, no boxes, no tagline; calmer
  colours, "What is PicWise?" white, the box's line grey and blue while typing, plain
  footer links; the month's most searched panel made simpler and folded to four rows
  ("Show all 10", "Show fewer"; still hidden, no source); the font Inter served by the
  site itself (48 KB); then, on the owner's word, "not verified by PicWise" off every
  card, "from the shops connected to PicWise" off the results pages, and the sentence of
  the order under the heading left to the heading («Β»). Pictures were shown to the
  owner before each step. The home page reads "250,000+ products from 75 UK shops": 75
  are the shops whose products the search holds (the morning's note said 80, the feed's
  shops before the selection, five of them with nothing in the search).
  `docs/LANDING_PAGE_SPEC.md`, "The Home Page (2026-11-12)".
  **The price bar, live since 17:00 UTC the same day** (owner: «Να μπει ένα φίλτρο με τη
  μορφή μπάρας ...», then «Ανέβασε»; release `20261112T164645Z-a43aa96`, run
  `43262330800`): above the cards of an answer of more than four products, from its lowest
  price to its highest; `?min=150` starts the answer from that price by the same rules
  (`docs/PICWISE_DECISION_CONTRACT.md`, "The price bar"). On the site: "tablet" shows iPad
  cases at £7.99 after its Recommended; from £100, Lenovo tablets. Since 23:51 UTC (owner:
  «Ανέβασε τα»; release of `7e3faf5`, run `43330121662`): with a price chosen there is no
  Recommended (owner: «Το recommendit πρέπει να ακιρονετε όταν χρησιμοποιεί φίλτρο»), and
  no empty place stays between the cards on a phone (a card whose photo failed had kept
  its place, unseen, under the phone's grid; a slow photo's card now gives its place up
  after 1.2 s).
  On 13/11 (owner: «Τι περιμένεις?»), built on `ccr-9953c583-wz6sfv`: the empty pages
  for buyers ("No products found for “…”." and two searches to try) and the shop's name
  as a buyer knows it ("View at Geepas"); live since 08:25 UTC on 13/11 (owner:
  «Ανέβασε»; `0da3a9e`, run `43390882800`). "Shopping Ads: Google &
  Bing", a shop of the feed whose name names no shop, is for the owner to ask Awin about.
  **What waited before 13/11, one at a time, a picture first:** the empty pages, written for a
  developer ("PicWise safely shows no product cards until intent confidence ...",
  "Detected category: ...") and leading nowhere (proposed to the owner: "No products
  found for "…"" and "Try the name or the kind of the product, for example …", no answer
  yet); the product card (the owner's next subject); the shop's name as Awin writes it
  on the button ("View at Geepas Partner Program"); the phone layout of 12/11 (one
  product a row) seen on no real phone yet. Done the same day, on the owner's word («Όχι
  not verified by ... είναι σαν να τον διώχνεις ... βγάλ' το εντελώς»): "Price and stock
  as the shop lists them, not verified by PicWise" is on no card, the page saying it
  once above the cards and once under them. The design of
  31/10 and its labels are the owner's (`docs/PICWISE_DECISION_CONTRACT.md`): every
  wording a visitor reads changes on the owner's word only; show the owner a picture
  first (render the page offline, never a script on the live site). The page's markup:
  `src/picwise_surface/reference.py`, its style sheet `page_styles.py`, its script
  `search_script.py`, the font `fonts.py`, the month's panel `trends.py`; the
  cards' classes are pinned by tests (the gotchas below).
- **12/11, the owner: the search's accuracy later.** Asked whether to measure the cards
  again on the server (about $0.25) and go on fixing by cause toward the bar of 98%
  right: «Όχι ακόμα με έχει κουράσει αυτή η απασφαλμάτωση αργότερα». So no measure, no
  fix and no question about the search's accuracy until the owner brings it up; the
  daily session reports and does the rest. Where it stands: last measured on 08/11, 78%
  of the first cards right, 153 absurd (run `42474826414`).
- **12/11: the owner's plan and approval.** The plan: more shops, added by the owner,
  and the mechanism that brings their products in made the best it can be («Το πλάνο
  είναι να προστεθούν καταστήματα φούτευοποιηθεί ο μηχανισμός»); nothing declared to
  Google yet («Δεν θέλω να δηλωθεί τίποτα στην google ακόμα»). Approved, with the
  deployment: «Ναι, προχώρα με όλα, και ανέβασε», to this list, in this order:
  - **A. Clean-up first** (changes nothing a visitor sees): A1 these continuity files
    made short, the history archived; A2 the code of May that nothing live uses taken
    out with its tests, after tracing what the site, the night's jobs and the
    deployment import; A3 one table of routes for `api/index.py` and the local server;
    A4 the largest files (`search_selection.py`, `concept_understanding.py`,
    `reference.py`) split, every search answering the same (`tools/bench_search.py
    --compare`).
  - **B. The catalogue's memory**: an SQLite file on the server, per product its first
    and last night seen, its price and the price's changes, per shop its rows each
    night. The feed carries no date of update and no stock quantity for any product.
  - **C. The shops' words to kinds**: each night the shops' own types that name no
    kind, with counts and examples; a mapping file takes only those that plainly name a
    kind PicWise has, measured before and after (not learning by itself: the owner's
    bar of 98% right cards).
  - **D. The shops that give nothing**: named by the deployment of 12/11 06:39: every
    row of NORVEXA ADVISORY LTD (13,227), Frenzy Clothings (5,398), Beauti Outlet
    (4,421), myCord | Bracelet Lab (1,816), Handbags Infinity Fashion (1,186) and Wilna
    Kitchen (206) is out of stock by the feed, as well as without a category. A whole
    shop out of stock is unlikely. Built: the note names the column and reading that said
    so (`without_category.out_of_stock_by`, printed beside each shop that gives nothing);
    read it the night after the deployment, then fix by cause (a flag constant across
    one shop's rows read as unknown, as the feed's constant flags are; or the bot reading
    their stock), a rule of stock, said to the owner first.
  The steps of the mechanism in full, with the night's numbers of 12/11:
  `docs/PICWISE_AUDIT_FIXES.md`, section 4, group E.
- **13/11, the night's note read, the mechanism's numbers in hand.** `db200ca` and what
  followed went live on 13/11 with `0da3a9e` (08:25 UTC), so the night of 13/11
  (prepared 08:16 UTC, written 08:23) carries B, C, D's measure and steps 12 and 15.
  Read from `https://picwise.subby.cloud/prepared.json` at 09:44 UTC on 13/11:
  `prepared: true`, 254,800 products, 78 shops; `intake_change` nothing shrunk, gone or
  new; the memory's second night, 255,408 products known, 254,841 seen, 2,690 new, 311
  prices changed, 567 gone since 12/11; `balance.by_shop` (InStock UK 147,331 products,
  39,924 with a kind, 68,460 with a barcode, 249 sold by another shop too; Finediam
  27,911 with 2 barcodes; Lets Buy Books 4,549 with no kind at all);
  `shared_by_brand_and_part` 798 products of 228,090 sold by two shops or more, 505 of
  them not joined by a barcode; D's column: every silent shop's rows are out of stock by
  `availability: explicit_out_of_stock` (NORVEXA 0 — its rows are held for no category,
  13,227 of them with no type from the bot either), and the bot could not read Frenzy
  Clothings, Beauti Outlet, myCord and Handbags Infinity at all (`robots.txt 423`).
  **Done the same day:** step 11's list, which was empty for the second night, written
  where the rows are counted (`shop_catalogue`, `words_to_learn`; the cause: it was drawn
  from the kept products, and such a row is held, so it was never among them). `c93be3c`,
  built, **not deployed, waiting for the owner's «ναι»** (asked in the report of 13/11,
  12:00 Greek time). The search's reading byte for byte the same before and after
  (`print_search_reading.py`, the whole lexicon, identical file); tests, the local run of
  every fast module, 311 modules, 309 pass, 2 fail as known; GitHub's "Tests" on
  `c93be3c` started 09:56 UTC (run `43405250793`), to be read before any deployment.
  **D (step 10), the silent shops' causes, from the same note:** Wilna Kitchen is no
  longer silent, 15 products shown (the bot's "in stock" over the feed, live since
  13/11); NORVEXA ADVISORY LTD's 13,227 rows are all held for `missing_category_text`,
  and the bot read its catalogue (1,319 products) but its store writes no type for any of
  them, so nothing can give those rows a kind (their titles name one for 4,906 rows, and
  a title alone never decides, the owner's rule of 2026-10-26); Frenzy Clothings, Beauti
  Outlet, myCord | Bracelet Lab and Handbags Infinity Fashion answer the bot's robots.txt
  with 423, so their catalogues cannot be read at all, and their feeds call every row out
  of stock. The first two are for the owner to answer (the report of 13/11). So Divine's
  81 rows are held as `shop_left_out`, by rule, not a fault.
  **Next, in this order:** deploy that list (it needs the owner's «ναι», it only writes
  the note) and read it the night after, then map by review the types it names
  ("Tablet Security Enclosures" 2,661, "Display Privacy Filters" 1,981, "Power Adapters
  & Inverters" 1,438, "PCs/Workstations" 490, "Brooches" 433, "Photo Paper" 375 —
  "Sold Out" 2,209 and "Warranty & Support Extensions" 842 are no product and are never
  mapped); then D's fix (four shops the bot is refused by `robots.txt 423` — a fact of
  their sites, for the owner; and NORVEXA's 13,227 rows with neither category nor type).
- **Live since 12/11** (owner: «Ανεβασε», then «ανέβασε»): the audit's fixes (`70baa78`,
  04:07 UTC): a search about five times faster on the server's side, each worker
  keeping the catalogue loaded (proven at the night's change), phones one product a
  row, security headers, canonical addresses, the night's note on shrunk feeds, kinds
  few shops sell, products several shops sell; then `c1e0d1f` (run `43167979054`):
  nothing declared to Google (no sitemap, no `Sitemap:` line, no structured data) and
  the shops that give nothing named with every reason (release `20261112T062508Z-c1e0d1f`,
  06:38 UTC).
- **Waiting for the owner:** a new Awin token (the offers are not fetched since 03/11:
  401); Search Console and the first batch for Google, both after the owner's word that
  something may be declared; the phone layout and the security policy seen on a real
  phone.
- **Not done, on purpose** (`docs/PICWISE_AUDIT_FIXES.md`, section 4, group C): a memory
  of searches' answers, a faster words search, "More" without a new page. No measure
  asks for them.

## Branches and deployment

- **Work:** `ccr-4f47068a-99ikwe`. Every session starts from it and pushes there
  (`docs/PICWISE_DAILY_WORK.md`; the daily task's prompt names it). Brought on 15/11 to
  the day's work (`ccr-d4dcbe0e-4y2sjf`), by a fast-forward. `ccr-99b47f03-l8t4dj` carried
  the audit's fixes; it is the head of pull request #23, so it stays.
- **Kept on GitHub (15/11, owner: «Ναι θέλω να τα κάνεις», to a tidy-up proposed):**
  `main`, `ccr-1361f1a7-dcpo60` (the site), `ccr-4f47068a-99ikwe` (work),
  `ccr-99b47f03-l8t4dj` (#23, merged that day when `main` was brought level, its branch
  kept on the owner's word: «Ναι, αλλά κράτα τον #23»; on 16/11 the owner let it go with
  the Sunday run of 22/11: «Να τον βάλεις στη λίστα της κυριακής»), `archive-2026-11-15` and the
  session's branch of the day. The other 30 were deleted at 22:55 UTC by the workflow
  `.github/workflows/tidy-branches.yml` (run `43771874892`), after two trials the owner
  saw: a session here may push branches but neither delete one nor push a tag (HTTP 403),
  and the owner did not want to delete them by hand. Nothing of them is lost:
  `archive-2026-11-15` (main's files; a merge whose parents reach the older lines of
  work, some from a history begun again) keeps every commit of all 30 reachable.
- **The tidy-up from now on** (owner: «Ναι, το εγκρίνω»): `tidy-branches.yml` runs every
  Sunday at 03:17 UTC and deletes a branch only when every commit of it is in `main`, the
  work branch or an `archive-*` branch, and it was not changed within 72 hours; `main`,
  the site's branch, the work branch, open pull requests' heads and `archive-*` always
  stay (#23's branch no longer, from 16/11: it should go on 22/11; check it did); a branch with a commit found nowhere else is kept and named.
  Run by hand (Actions, "Tidy branches") it is a trial unless `dry_run` is turned off.
  A session's own branch therefore goes the Sunday after its work reached the work
  branch.
- **The server:** a push to `ccr-1361f1a7-dcpo60` deploys that commit
  (`.github/workflows/server-deploy.yml`, `deployment/server/deploy.sh`): only on the
  owner's «ανέβασε» for it, by a fast-forward. The deployment prepares the catalogue
  only when the change concerns it (20/11; with both links 22-26 minutes, peak about 14.6 GB) and restarts
  the site, only if the new release reads the catalogue in place; each worker loads the
  catalogue in the background (`state.keep_prepared_catalogue_loaded`). A rollback is
  a push of a revert commit, never a force push.
- **`main`:** what is live plus its records, moved only on the owner's yes, by a
  fast-forward; brought level with the site and its records on 15/11 (it had been 88
  commits behind since 09/11). A push to `main` makes Vercel build the backup. Pull request #23 (from `ccr-99b47f03-l8t4dj`) is the owner's; leave it.
- **Tests:** `python tools/run_test_modules.py --skip-slow` (every module in its own
  process, about 6 minutes on 4 cores); `.github/workflows/tests.yml` runs it on each
  push of code, the two slow modules in a job of their own. Two modules fail as known
  (`README.md`), each with its one test.
- **The live site** is read with `curl` only (no script, so no visitor's search is
  logged), never `/out/...`, never a shop's link. The night's public note:
  `https://picwise.subby.cloud/prepared.json`.

## The owner

Not a programmer. Write to them in **Greek**, plain words, short ("όχι κατεβατά").
Honest numbers, what was not done and why; never overclaim. They decide what the site
shows, what reaches Google, and every deployment.

## Rules that do not change

Read in this order: `PROJECT_RULES.md` (first, it wins), `docs/MISSION.md`,
`concept.picwise.txt`, `docs/` contracts, this file, the last entries of `PROGRESS.md`.
A conflict between them: stop and say it (`PROJECT_RULES.md` 1.4).

- Every purchase-intent search: only the kind asked for, only in stock; 4 choices, 1
  Recommended (the middle price), "More" by four; cheapest first, each at the shop's own
  price, its sale price where the shop's feed gives one: PicWise works out no price, an
  offer is a note in the shop's words, and comes first only when it is cheaper (owner,
  15/11 and 19/11); commission never a criterion (`PROJECT_RULES.md` 2 and 5,
  `docs/PICWISE_DECISION_CONTRACT.md`).
- No invented data anywhere; a synthetic catalogue is for measuring speed only.
- Small closed steps, each with its tests and measures, each a commit; look before
  changing; never skip, weaken or delete a test to get green; a module taken out with
  the code it tests is taken out whole, and said so.
- The repository is public: no key, token, feed file or feed link, ever.
- Nothing is declared to Google until the owner says so (`PROJECT_RULES.md` 13;
  `picwise_surface.seo.DECLARE_TO_GOOGLE`).
- Wording a visitor reads, and any decision of the owner's, changes only on their word.
- Amazon is permanently removed; Awin is the network.

## Map of the code that matters

| What | Where |
|---|---|
| The server's entry point; static files; the keeper started per worker | `deployment/server/wsgi_server.py` |
| The routes, one table for the server and the local server | `src/picwise_app/routes.py` (`api/index.py` is the entry point) |
| A search, end to end | `src/picwise_search/live_search_resolver.py` |
| What a search means: kinds, typing slips, "Did you mean" | `src/picwise_nlu/concept_understanding.py`, `product_concepts.py`, `category_detector.py` |
| Which products, in what order, the Recommended; the kind index | `src/picwise_providers/search_selection.py` |
| The catalogue in memory, its keeper, the prepared file | `src/picwise_providers/state.py`, `prepared_catalogue.py` |
| The night's preparation and its public note | `tools/prepare_catalogue.py`, `src/picwise_providers/feed_intake.py`, `catalogue_balance.py`, `catalogue_cap.py` |
| The catalogue's memory (SQLite on the server: first and last night seen, prices, shops' rows per night) | `src/picwise_providers/catalogue_memory.py` |
| The shops' own words learned as kinds (reviewed table); the night's list to review (`balance.words_to_learn`) | `src/picwise_providers/shop_words.py` |
| A card's price note: the 7-night rule, the night's `price_notes.json.gz`, its loading per worker | `src/picwise_providers/price_history.py` |
| The price chip under a card's price and its 30 nights | `src/picwise_surface/price_notes.py` |
| The feed gate and the card gate | `src/picwise_providers/eligibility.py`, `offer_health.py` |
| The shops' catalogue bot (03:40 UTC) | `deployment/bot/shop_catalogue_bot.py` |
| The pages: search, home, info pages, phones | `src/picwise_surface/reference.py` (its style sheet `page_styles.py`, its script `search_script.py`), `legal.py`, `seo.py` |
| Security headers | `src/picwise_app/app.py` (`SECURITY_HEADERS`) |
| The AI layer (complex searches, at most $1 a day) | `src/picwise_ai/`, `docs/PICWISE_AI_LAYER_SPEC.md` |
| The server's units and deployment | `deployment/server/` |
| The deployment's report of the night's note | `deployment/server/print_shops.py`, `print_kinds.py` |
| Speed measure | `tools/bench_make_feed.py`, `tools/bench_search.py` (`docs/PICWISE_AUDIT_FIXES.md`, section 7) |

## Working gotchas

- A change under `src/picwise_providers` or `src/picwise_nlu` changes the prepared
  file's code fingerprint: the next deployment prepares again (it always does), and a
  running site refuses a file written by other code and keeps the one it holds.
- Tests rewrite `src/picwise_search_memory/artifacts/search_runtime_v1.json.gz`
  (`built_at` only): `git checkout --` it before a commit.
- `test_picwise_search_graph_contracts_stage1db1` fails while `app.py`,
  `live_search_resolver.py` or `reference.py` have uncommitted changes: run the suite on
  the commit.
- Changing a file listed in `search_runtime_artifact.get_fingerprint_source_paths()`
  requires rebuilding the search artifact (`tools/build_picwise_search_artifact.py`).
- The cards' markup is read by tests and by `deployment/server/compare_with_vercel.py`:
  `<article class="pw-card" data-choice-id=...>` or `class="pw-card pw-card-recommended"`,
  `pw-card-title`, `pw-role-label`, `pw-price`, `pw-card-shop`, `pw-card-stock`,
  `pw-card-note`. The phone rules live inside `@media (max-width:699px)`; the rules
  outside it are pinned by older tests.
- The prepared file leaves out the Awin columns no rule reads
  (`prepared_catalogue.LEFT_OUT_COLUMNS`): a rule that comes to read one must take it
  off that list.
- Availability: a stock word decides wherever it appears; a bare flag only where its
  column varies across the feed; one `feed_ctx` for the whole feed, passed on.
- Product identity: GTIN, else brand + MPN; never merge on a model name.
- The kind of a feed row: only the words before the first purpose word ("for", "with")
  name the product; weak names (cap, ball, ring, screen...) never classify a feed row
  alone; a category breadcrumb is read shelf by shelf
  (`tests/test_picwise_feed_kind_truth.py`).
- A test that renders an empty query schedules a 0.75 s warm-up: reset it
  (`search_warmup._reset_search_warmup_for_tests`).
- A new test module that needs another module's helpers imports the module and
  subclasses (`import test_x as x`); importing the class by name runs its tests twice.
- A session reaches `picwise.subby.cloud` and the package registries; the server only
  through the deployment's run and the read-only workflows.
- `pkill -f` or `grep` patterns that match their own command line kill the shell.
- A session's fetch tool may answer with an old copy of a site page (20/11: `/private-beta-readiness` said
  "other_code" at 11:20 UTC while the server said "in_use"; "kettle" showed cards of days before): read the
  live site through a workflow on GitHub's runner or on the server (`prepare-runs.yml` asks the site itself).
