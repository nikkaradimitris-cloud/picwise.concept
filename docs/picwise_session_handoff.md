# PicWise — session handoff

Current state for whoever picks the project up next. Updated 2026-11-07 (**next: a big
general debugging of the search, category by category, asked by the owner on 07/11
(«ζητάω μία μεγάλη γενική απασφαλμάτωση»: the site not yet trusted as a production page;
«μπαταρία» read as boots); its method, its bar and about $3 of AI audit approved («Ναι σε
όλα, πάμε σε νέα συζήτηση»); first the full measure of all 18 categories: its step 1, the
search read offline, measured on 07/11 (`print_search_reading.py`, `57e8050`: 280 of
89,540 searches read as a kind of another category, six causes); then, on the owner's word
(«Ναι σε όλα, κλείσε και τα δύο»), built and tested, not deployed, **waiting for the
owner's «ανέβασε»**: Greek and greeklish closed, the searches' text kept on the server,
each name read in both numbers, no word spelt right corrected, "Did you mean ...?" where a
word means the search is not for the kind read (`828d15f`..`8db74c2`); next its steps 2
and 3 on the server's catalogue; the AI fixes kept in a list go in the first build**; **the AI layer live since 2026-11-06 20:41 UTC, run `42287840883`,
`75fd3d0` (owner: «ανέβασε το 75fd3d0»): in a complex search the products the AI reads as
fitting first and marked, one euro a day, the privacy text naming no company; its spend
after a day or a week**;
**item 2 live
since 2026-11-05 12:54 UTC, run `42028878547`: a shelf's kind read against its aisle,
doubtful products found by their words; searches of a kind with a wrong card 31 -> 7 of
the 284 measured**; the end-to-end check of the words that
confuse the search done, run `41940401157`; **live since 2026-11-05 10:50 UTC, run `42011735026`: "tablet" without
pills, the main kind only everywhere, with the narrower aisles**; **the offers not fetched
since 2026-11-03 05:05 UTC: Awin answers 401** (a new token: not now, the owner); live since 2026-11-01 16:22 UTC, run `41324998201`: products whose photo is gone
left out, a card seen only once its photo has loaded, the offer recommended even without a
barcode; live before: offers first and the
Recommended on offer since 10:06 UTC, run `41295172671`; vouchers without their code no
longer shown since 12:21 UTC, run `41305061462`; also live: the design of 31/10 and the pages, run `41215460767`, and the
nightly offers fetch, run `41289100060`; picwise.subby.cloud answers from the server since
2026-10-31 10:03 UTC, HTTPS by Caddy; Vercel kept as the backup).
`PROGRESS.md` is the chronological log; this file is the "where are we now".

## Next conversation (from 2026-11-06): pick up here -- start here

- **The daily work (owner, 2026-11-07):** every day at about 12:00 Greek time a scheduled
  task starts a new session that follows `docs/PICWISE_DAILY_WORK.md`: the next step of
  this section, its tests and measures, a report in Greek by email, and the site changed
  only after the owner's «ναι» to that day's report. The AI at most $2 a day.
  **The site seen (08/11):** on the owner's «στείλε το», the cloud environment
  «picwise.concept» (personal; it allows only `picwise.subby.cloud`, the package
  managers and the MCP servers) was created and this session moved onto it; the daily
  task runs on it: the owner picked it in the task's settings (General, Cloud
  environment) at 00:17 UTC. Read with `curl` (no script, so no search kept as a visitor's), never a
  shop's link. The live site, rules `75fd3d0`, 08/11 00:00 UTC: the home page 0.8 s; a
  search 2.3-2.5 s ("kettle" again, "fire pots"), 6.2 s ("kettle" the first time) and
  6.4 s ("laptop bag"), against the 4-second aim.

- **Daily session 2026-11-08 (noon): first step of the speed work, built and tested, not deployed, not yet measured on the server.** `_select_products_by_words` built every product's search text on each search; now `_catalogue_haystacks` builds it once per catalogue and keeps it (`tests/test_picwise_words_search_cache.py`; the unsure-reading, search-catalogue, English-only and live-resolver modules pass). Offline, on 597,270 synthetic products: 0.65 s the first time, 0.000005 s after. That is a small part of the 8-9 s: what is left is the regex scan of every word over all haystacks (`_search_head_word`, `_carries`, `carrying_all`), to be replaced by a word lookup built once with the catalogue, then measured on the server (cards only, about $0.25). The AI today: $0.
- **START HERE (08/11, evening): the cap of 15% in the search too, built and tested; it goes
  with everything below in one deployment, waiting for the owner's «ανέβασε».** The owner:
  «Το 15% που είχα πει αφορούσε ένα πλαφόν ησος πρέπει να ισχύει για όλα τα καταστήματα
  έτσι ώστε να μην μπει κάποιο κατάστημα με έναν τεράστιο όγκο και αλλάξει την ταυτότητα
  του site ... μπορούμε να κρατήσουμε αυτόν τον κανόνα και για το search έτσι ώστε να
  επιτυγχάνουμε καλύτερες ταχύτητες αργότερα με την ανάπτυξη αν καταφέρουμε να βγάλουμε
  λεφτά από αυτό το project θα αναβαθμίσουμε και το server». Built: each night the
  preparation works the cap out once (`tools/prepare_catalogue.py`, `_Cap`), the night
  before's pool its starting point, and the prepared catalogue, its suggestions and its
  choices hold only the products it keeps (`state.prepare_feed_catalogue(cap=...)`); the
  same products are the pool Google may be given from; a cap that fails keeps every
  product in the search. `PROJECT_RULES.md` §13 now says so, with the owner's words. The
  cap per category as chosen on 27/10 (the first two levels of the shop's Google shelf). On
  30/10 it kept 168,730 of 527,911 (jewellery 381,204 -> 25,309, clothing 28,595 ->
  25,309); the deployment's preparation prints today's. Tests: the preparation's 25
  (one new: the search holds only what the cap keeps), the cap's, the choices on the page,
  the daily renewal, the server tools' (82 in all). **To put to the owner with it:** the
  scanning screen names the feed's eligible products (about 730,000), the search will hold
  about 170,000-200,000: `PROJECT_RULES.md` §9 wants the screen to state only true facts.
- **Before (08/11, afternoon): fast and right, put to the owner: waiting for «ανέβασε»**
  (then push the newest commit of `ccr-4f47068a-99ikwe`, its tests passed, to the deploying
  branch `ccr-1361f1a7-dcpo60`; `src/picwise_nlu` changed since `75fd3d0`, so the deployment
  prepares the catalogue again). Run `42474826414` (`71e9bab`, the cards only, $0.25; the
  catalogue of 08/11 04:25, 597,275 products): a search, the rules deployed -> this branch,
  1.98 -> 1.97 s in the middle, 2.56 -> 2.14 s at the 90th in 100, 18 -> 10 over 4 s (the
  "ring" searches 8 to 11 s with both: the ring kind's 200,000 products; "washing machine"
  7.2 s, "laptop bas" 6.6 s). The cards: right 64.8% -> 78.0%; absurd 1,226 -> 153, in
  every category as few as the site's or fewer but CL (12 -> 13); no card 125 -> 346, 231
  asking "Did you mean", 230 of them offering the kind searched for (the audit's new
  section); those offering nothing are mostly kinds the catalogue lacks (dishwasher, oil
  filter, alloy wheels, blood pressure monitor, high chair...). The searches made worse, 61
  (93 better): mostly typing slips now asking "Did you mean" with the right offer; wrong
  cards: "mirrrs" 12 microphones (a one-word correction to another kind), "pen dries" a
  dry-wipe pen ("dries" read as "dry"), "work pans" a cookbook, "t shorts" cargo shorts.
  The word lookup (`74f04f6`): `search_selection._word_lookup`, built in the background for
  each catalogue (`warm_word_lookup`, from `state.py`), numbers alone and words of one or
  two letters left out; the daily session's cache of every product's text (`6a6680d`)
  dropped (each of the four workers would have held about 300 MB). Tests: all 296 modules
  on `74f04f6` but stage 6a (skipped, as before): 294 OK, the 2 that fail on the base too
  (stage2 registry, stage4 blind index). The AI so far $1.30 of the $3. Deploying puts on
  the site everything built since `75fd3d0`: English only, the searches' words kept on the
  server with the privacy page's "Searches" section (its words put to the owner in the
  report of 08/11 afternoon), each name in both numbers, no word spelt right corrected,
  "Did you mean" where the reading is unsure, every word kept by a words answer, the word
  lookup. **After it:** follow the deployment's run, check the site with `curl` (the
  environment «picwise.concept»), then the wrong cards above, the weekly measure of the
  kept searches, and the ring gap (2,873 of 10,000 products with no kind are rings).
  **The agenda for 09/11, as told to the owner (08/11):** 1. if the owner has said
  «ανέβασε», check the deployment (its run, the site with `curl`, the speed of a few
  searches); if not, ask again in the report; 2. the wrong cards, by cause: "mirrrs" (a
  one-word correction to another kind), "pen dries" ("dries" read as "dry"), "work pans"
  (a cookbook), "t shorts" (cargo shorts); 3. the ring gap: why 2,873 of 10,000 products
  with no kind are rings no rule reads; 4. the kinds holding most products not theirs
  (storage_drive 174, dinnerware 155, watch 124, battery 118 of those judged); 5. the
  "ring" searches' 8 to 11 s. Each with its tests and a measure (the cards only, about
  $0.25; the AI at most $2 a day); the report and its notification at the end of the day.
- **Before (08/11, morning): the fix measured (run `42427367069`, `be77d8d`, the cards
  only, the AI $0.25): right enough, too slow, so nothing deployed: speed first.** Of the
  first 12 cards judged, the rules deployed -> this branch: right 65.1% -> 78.4%; absurd
  1,229 -> 160; searches with no card 125 -> 346 (231 asking "Did you mean"). No category
  has more absurd cards than the site but CL, by one (12 -> 13: "work pans" with a
  cookbook); FU 35 -> 35, TY 0 -> 0, GA 156 -> 0, BK 519 -> 96, CO 114 -> 1. Right per
  category, deployed -> new: HA 72.1 -> 76.1; KI 67.9 -> 72.1; FU 71.0 -> 75.3; PH 63.9
  -> 92.4; CO 70.0 -> 80.1; AV 77.8 -> 84.6; CP 91.4 -> 91.4; TY 29.6 -> 29.6; MO 39.1 ->
  64.0; PT 59.2 -> 81.7; HT 69.4 -> 85.9; GA 56.2 -> 70.0; HE 45.8 -> 80.9; BE 68.2 ->
  72.2; BK 36.3 -> 67.1; CL 80.3 -> 87.3; FO 82.8 -> 93.1; JW 75.4 -> 86.1 (the AI's
  verdicts on the same cards vary by a few points from run to run: the deployed rules' CL
  78.3% in run `42390049201`, 80.3% here). The searches made worse, 64 (93 better): mostly
  typing slips the site guesses right that now ask "Did you mean" ("sof bed", "sd cars",
  "pen dive", "phone cas", "plan pot", "flag iron", "laptop bats": the owner chose asking
  over guessing; the audit does not yet print what is offered); a few wrong cards:
  "mirrrs" 12 microphones (a one-word correction to another kind, known since step 1),
  "pen dries" a dry-wipe pen ("dries" read as "dry"), "work pans" a cookbook, "t shorts"
  cargo shorts. **Too slow:** a search 1.71 s in the middle (1.76 s with the rules
  deployed), but 6.56 s at the 90th in 100 against 2.36 s, and 254 searches over 4 s
  against 15: the unsure path, 8 to 9 s ("bah rugs", "bth rugs", "laptop bas", "case fas",
  "dishwasher pos", "pc fns", "laptop sleees", "wall mirrr"), the words search over the
  whole catalogue (`_select_products_by_words` builds every product's text on each
  search). "ring" takes 9 to 10 s with both (the ring kind's 200,000 products). The live
  site (rules `75fd3d0`): "laptop bag" 6.4 s. **Next:** make the unsure path fast (find
  the products carrying every word without building every product's text on each search,
  e.g. a word lookup built once with the search catalogue), print the "Did you mean"
  offered with the searches made worse, measure again (the cards only, about $0.25), and
  ask the owner's «ανέβασε» once nothing comes out slower or worse. The AI so far $1.05 of
  the $3.
  **Put to the owner (08/11):** (1) for an obvious typing slip the site guesses right
  ("sof bed"), "Showing results for: sofa bed" rather than only "Did you mean"? **Answered
  08/11, 10:5x UTC: «Στο α η απάντηση μου είναι ότι το ευρετήριο προτείνει τη σωστή
  διατύπωση.. οπότε δεν χρειάζεται»: kept as it is, "Did you mean ...?" with the right
  wording, no results shown for a guess.** So what is offered must be right: the audit to
  print the "Did you mean" offered for every search with no card, and a wrong offer is a
  fault to fix. (2) The scanning screen's count (about 730,000 named, 597,270 a card can
  show): **answered 08/11: «αυτό θα φτιαχτεί όταν ασχοληθούμε με τον design»: left as it
  is until the design work, where it is to be fixed.**
- **Before (08/11, night): the debugging's steps 2 and 3 measured on the server's
  catalogue (run `42390049201`): better on the whole, worse in three categories, so
  nothing deployed; one cause found and fixed; the next run measures the cards again.**
  The owner had said «Ανέβασε μετά τη μέτρηση..», told: deployed if the new rules come
  out better and break nothing, else stop and ask. The measure,
  `deployment/server/audit_search.py` (`1d22739`, its tests in
  `tests/test_picwise_server_audit_search.py`) run by `.github/workflows/search-audit.yml`
  (`c7110cc` against the rules deployed, `75fd3d0`; turned off by the daily session's
  `236937a`, recorded in `d995e56`): the
  server's catalogue prepared 07/11 04:25, 597,270 products a card can show; 1,338
  searches (807 names, 265 brands, 266 read as another kind offline); the AI $0.80 of
  the $3. Of the first 12 cards judged, right 65.0% -> 73.2%; absurd 1,233 -> 778; right
  cards 7,627 -> 7,438; searches with no card 125 -> 258, 143 of them asking "Did you
  mean". Right and absurd per category, deployed -> new: HA 75.6% 25 -> 79.8% 1; KI 68.5%
  38 -> 71.7% 28; FU 70.3% 35 -> 72.5% 40; PH 62.4% 0 -> 93.3% 0; CO 69.4% 114 -> 78.8%
  13; AV 79.0% 38 -> 81.6% 24; CP 93.1% 0 -> 93.1% 0; TY 29.6% 0 -> 20.5% 12; MO 38.7% 0
  -> 63.5% 0; PT 60.0% 36 -> 82.9% 0; HT 70.6% 64 -> 83.6% 2; GA 55.6% 156 -> 56.3% 125;
  HE 45.8% 72 -> 80.0% 1; BE 69.1% 36 -> 73.1% 0; BK 35.8% 523 -> 44.8% 480; CL 78.3% 12
  -> 76.0% 52; FO 86.8% 0 -> 97.6% 0; JW 75.7% 84 -> 87.6% 0. Worse: CL, TY and FU in
  absurd cards; GA and CO in right cards (CO 1,471 -> 1,321).
  **Found and fixed** (the commit after `d995e56`, with a test in
  `tests/test_picwise_unsure_reading.py`): an unsure reading was answered by a words
  search that had dropped a word ("fire pots" with pen pots, "desk lam" with a horse feed,
  "electric fire bowl" with a spice grinder): `_unsure_reading_selection` now takes the
  words answer only when it keeps every word, else "Did you mean ...?", as its own
  docstring said. **The time:** 1.96 s a search in the middle, as before (1.95 s), but
  4,172 s in all against 2,797 s: the likely cost is the unsure path, a words search over
  the whole catalogue (`_select_products_by_words` builds each product's text on every
  search), against the 4-second aim; the next run prints the time per search and the
  slowest searches, each with why it was answered so (`audit_search.search_times`).
  **The next run** (the commit after that one, the cards only, at most $1, `--cards-only`):
  the cards with this fix and, per category, the searches it makes worse than the rules
  deployed, each with why it was answered so and its first wrong card
  (`audit_search._worse_searches`). **Then:** fix those causes (CL, TY, FU, GA, CO), make
  the unsure path fast, measure again; the owner's «ανέβασε» asked only when nothing
  comes out worse. **Also found:** the scanning screen names the feed's eligible products
  (`prepared.eligible_count`, the about 730,000 the owner saw), while a card can show
  597,270 (`len(prepared.products)`): to put to the owner. Of 10,000 products with no
  kind, the AI read 2,873 as rings (a gap in the ring kind, JW: to find why), 59 as
  cables, 37 phone cases, 26 trainers, 26 t-shirts. The kinds holding most products not
  of them (of those judged): storage_drive 174, dinnerware 155, watch 124, battery 118,
  software 91, football 78, cookware 68, garden_hose 62 (the run's log lists them, with
  five examples each).
- **Daily session 2026-11-08: the search audit read (run `42390049201`, on `c7110cc`, success, 2 h 19 min, the AI 1,845 calls, 34 without an answer, $0.7972 of the $3).** The workflow is off again (`if: false`). The cards a visitor sees, first 12 of each search, judged by Haiku, the rules deployed (`75fd3d0`) -> this branch (`8db74c2`): right 75.6% -> 79.8% HA; 68.5 -> 71.7 KI; 70.3 -> 72.5 FU; 62.4 -> 93.3 PH; 69.4 -> 78.8 CO; 79.0 -> 81.6 AV; 38.7 -> 63.5 MO; 60.0 -> 82.9 PT; 70.6 -> 83.6 HT; 55.6 -> 56.3 GA; 45.8 -> 80.0 HE; 69.1 -> 73.1 BE; 35.8 -> 44.8 BK; 86.8 -> 97.6 FO; 75.7 -> 87.6 JW; CP the same 93.1. **Worse: CL 78.3 -> 76.0 (absurd cards 12 -> 52), TY 29.6 -> 20.5 (absurd 0 -> 12), FU absurd 35 -> 40.** Searches with no card rise (PH 9->36, CO 6->42: the "Did you mean" asks, by design). Left on both: BK 480 absurd cards of 1,117, GA 125 of 744; the Geepas kettle-and-toaster sets under "toaster"/"kettle"; 11 gardenista cushion covers under "pillow"; "electric fire pit" read as a heater. Gaps: 5,962 of 9,242 sampled products with no kind read as none (rings 2,873 judged as the ring kind, clothing and shoes with the kind in the variant only). **Because CL, TY and FU came out worse, nothing goes on the site until they are read and fixed.**
- **Built (07/11, later): the rules by cause built on the owner's word, tested, not
  deployed: waiting for the owner's «ανέβασε»** (push `8db74c2`, or what is newest on
  `ccr-4f47068a-99ikwe`, to the deploying branch `ccr-1361f1a7-dcpo60`: `src/picwise_nlu`
  changed, so the deployment prepares the catalogue again). How it came: told step 1's
  causes, the owner: «αυτά που μου προτείνεις είναι πολύ συγκεκριμένα από αυτά θα
  βγάλουμε άλλες λέξεις και ούτω καθεξής... Εξήγησέ μου με ποια λογική πιστεύεις ότι
  μπορείς να έχεις ένα search το οποίο να δουλεύει σωστά»; told, in Greek: words are
  endless, causes few: one rule per cause for every word; the catalogue (595,751 titles)
  and the names as the dictionary, a word spelt right never corrected; every word of a
  search accounted for by the products shown; when unsure, no guess but "Did you mean
  ...?" or the products carrying all the words; everything measured before and after,
  each error a test; no search understands everything, the aims being no absurd card and
  more searches right week by week, best measured on visitors' real searches, which the
  site did not keep. Then the owner: «Μήπως να αφαιρούσαμε τα ελληνικά και τα greeklish
  διότι το site είναι για αγγλία...» (measured in a scratch run: English searches read as
  another category's kind 164 -> 138, words spelt right corrected into another product
  244 -> 204, with greeklish off), and «Ναι σε όλα, κλείσε και τα δύο»: Greek and
  greeklish closed, "Did you mean ...?" rather than a guess, the server keeping the text of
  visitors' searches (no IP) to measure them each week. Built, each with its tests:
  1. `828d15f` (and `555ec22`): **the search reads English only**
     (`concept_understanding.greek_search_on`, `PICWISE_GREEK_SEARCH`, off unless "on"): a
     word in Greek letters names nothing, one in Latin letters is never read as greeklish
     or as Greek typed on the English layout; a search in Greek letters is answered by
     "PicWise searches in English. Please type the product's name in English." and nothing
     else (`live_search_resolver.searches_in_greek_letters`); with the shops' products
     connected, an older vocabulary's category alone ("psygeio") is no longer said to be
     understood; the search box offers no Greek name; the 9 test modules that test Greek
     turn it on for themselves (`tests/greek_search_switch.py`); the print tools follow
     (`print_search_choices` skips the Greek names). The AI layer: a Greek complex search
     ("σακίδιο για σχολείο") is no longer understood, so no longer asked (the owner should
     try "school backpack"); `ai_measure_searches.txt` still lists Greek searches.
  2. `e464846`: **the searches' words kept on the server** (`picwise_app.search_log`): the
     search page's script reports a search's first page once loaded in a browser
     (`/searched?q=`, 204, no-store), so crawlers, "More" and the AI's refresh add nothing;
     one line `{"q": ...}` in the day's file under `PICWISE_SEARCH_LOG_DIR`
     (`/srv/picwise/shared/searches`, set in `picwise-web.service`, made by `deploy.sh`);
     no time of day, IP, browser or cookie; a day's file stops at 20 MB; files older than
     12 months deleted. The privacy page's new "Searches" section, its legal basis and
     how long (12 months), "Last updated: 7 November 2026" (wording not yet shown to the
     owner). The weekly measure of them is not built: a workflow copying the files read
     only, printing counts and only searches seen often (the repository and its logs are
     public), once a week of searches is there.
  3. `ac74857`: **each name in both numbers, no word spelt right corrected, judgement
     words set aside** (`picwise_nlu.english_number`; `is_known_english_word`): every
     English name read in both numbers as a form only a search reads (a weak name keeps
     one number; feed products classified as before); a word of the names, of Google's
     taxonomy or of the packs (each in both numbers) never corrected ("iphone" was read
     as an IP desk phone through "ip phone", "rubber" as router, "boxes" as boxers);
     "Did you mean" asks about such a word only with a word typed exactly; "pones" read
     (a dropped h after a first p); "best", "cheap", "deals", "uk" and the like set aside,
     never filters, never "could not match".
  4. `8db74c2`: **"Did you mean ...?" where a word means the search is not for the kind
     read** (`search_selection._unexplained_words`, `_unsure_reading_selection`; the
     reading's `need_words`, `words_after_name`, `product_words`): a word no product of
     the kind carries, and which is no preference, spec, number, size, describing word
     (`_DESCRIBING_WORDS`), brand of the catalogue (three products or more) or need
     (after "for"/"with"), means another product when it stands after the kind's name
     (English names the product last: "tv stand", "table saw", "laptop bgs") or, before
     it, is a word of another kind's name ("coffee grinder", "garden chair") or makes
     with it a name close to another kind's ("gme table"); the answer is then the
     products all the words name (the words search of part 3b), else none, the page
     asking "Did you mean: laptop bag?" without "Understood as". A word before the name
     that the vocabulary lacks is a need ("comfortable office chair"), not a slip.
  **The measure after** (`print_search_reading.py`, English): the names as written or in
  the other number 97.7% -> 99.4% (the 10 left: weak names in the other number:
  "stoves", "covers", "screens"); words spelt right read as another product by a
  correction 176 -> 0; Google's shelves read as a kind their aisle may not hold 422 ->
  301; typing slips read as another category's kind 126 -> 138, of which, by an offline
  estimate (each one's word is one no product of the kind read would carry), 133 of the
  142 absurd readings no longer reach a card; the 9 left are one-word corrections to
  another kind ("mirrr" as a microphone, "kettleell" as a kettle, "bikii" as a bicycle,
  "bby monitor": the doubled b collapses in the key). New finds on the way: "iphone",
  "airpods", "macbook", "kindle", "samsung galaxy" name no kind (product lines to add,
  per kind); "used iphone" was read as a desk phone.
  **Tests:** every test module run on its own, six at a time, on `828d15f` (292 modules)
  and on `8db74c2` (295): only the two that fail on the session's first commit `d761ddb`
  too fail (`test_picwise_canonical_vocabulary_registry_stage2`,
  `test_picwise_search_index_generated_blind_stage4`, the same tests);
  `test_picwise_learning_stage7b` passes alone in 1,106 s; and
  `test_picwise_search_index_blind_evaluation_stage6a` does not finish in 20 minutes, as
  before. **Next:** the owner's «ανέβασε»; then the debugging's steps 2 and 3 on the
  server's catalogue with these rules (the method below), the weekly measure of the kept
  searches, and the gaps per kind (product lines; missing kinds: table saw, tile cutter,
  reciprocating saw, polisher...).
- **The debugging's step 1 measured (07/11), the search read, offline; next its steps 2
  and 3 on the server's catalogue (the bullet but one: their workflow, `if: false`
  until the owner's word, about $3).** `deployment/server/print_search_reading.py`
  (`57e8050`; 15 tests in `tests/test_picwise_server_print_search_reading.py`; `python3
  deployment/server/print_search_reading.py [--category XX] [--json file]`, 19 s, no
  network, the same searches read the same way each time): per kind, every English name
  and its other number, with the words buyers add (two brands, a size, a word before, a
  need after, "best", "cheap": `CATEGORY_WORDS`), every typing slip (a letter left out,
  doubled, two swapped, a neighbouring key; never a word's first letter); every Greek name,
  a one-word one in its other number, its slips; the packs' 591 subcategories and their
  families without the generated tails; every word of the names, of Google's taxonomy and
  of the packs, alone; every shelf of Google's, read against its aisle (`_aisle_may_hold`).
  **89,540 searches; the names as written or in the other number 97.6% right (9 read as
  another category's kind, 27 as nothing); with the words added 99.8%; the slips 96.4% (151
  another category, 1,681 nothing); Greek 92.1% (116 another category); 280 searches in all
  read as a kind of another category, the absurd; 244 words spelt right read by a
  correction as a kind none of whose names holds them (51 of another category's words);
  450 of Google's shelves read as a kind their aisle may not hold; of the packs' 1,084
  names, 443 read as nothing (kinds missing) and 80 as another category's kind.** Per
  category, English right, absurd, nothing | Greek right, absurd: HA 98.3%, 2, 68 | 93.6%,
  2; KI 97.6%, 8, 103 | 93.6%, 1; FU 96.2%, 6, 173 | 91.5%, 9; PH 94.9%, 29, 244 | 90.0%, 7;
  CO 98.0%, 10, 235 | 93.1%, 7; AV 99.0%, 3, 30 | 94.2%, 7; CP 98.5%, 2, 16 | 87.4%, 8; TY
  93.5%, 6, 67 | 94.6%, 4; MO 95.7%, 0, 45 | 93.4%, 6; PT 98.6%, 4, 24 | 94.5%, 0; HT 97.0%,
  10, 34 | 89.8%, 2; GA 97.1%, 16, 145 | 91.5%, 15; HE 98.2%, 7, 31 | 93.8%, 6; BE 97.5%, 3,
  56 | 93.1%, 3; BK 95.7%, 50, 179 | 92.8%, 17; CL 92.6%, 1, 129 | 85.4%, 0; FO 95.5%, 0, 35
  | 93.7%, 2; JW 94.6%, 7, 94 | 84.5%, 20. **The causes, each to be fixed by a rule where
  one can say it (the fixes on the owner's word, each error a test):**
  1. *A slip in one word of a two-word name leaves the other word read as its own kind*
     (a word of three letters is never corrected, `_max_distance`): "laptop bgs" as
     laptop, "desk pone" as desk, "hat pump" as hat, "bby monitor" as monitor, "hgh chair"
     as chair, "gme table" as table, "drill bts" as drill, "pc gme" as a desktop PC.
  2. *A name's other number missing from the lexicon*: "drill bit" read as drill,
     "dishwasher pod" as dishwasher, "external batteries" and "vehicle batteries" as AA
     batteries; "boot", "sock", "sneaker", "nappy", "hair brushes", "settees", "buggies",
     "tees", "mics", "paints" as nothing.
  3. *A word spelt right corrected into another product's word*: "boxes" as boxers
     (underwear: "tool boxes", "lunch boxes", "litter boxes"), "chains" as chairs, "plants"
     as pants, "sports" as shorts, "tools" as toys, "pulse" as purse (wallets), "laser" as
     ladder, "receiver" as recliner, "protector" as projector, "types" as tires,
     "electrical" as a fan; «μπαταρία» as «μποτάκια» (boots), «πλάτης» as plates, «σκόνες»
     as «σκηνές» (tents).
  4. *English read as greeklish*: "pones" as «πάνες» (nappies: "mobile pones"), "couches"
     as «κούκλες» (dolls), "labels" as «λάμπες», "pati" as «πάτοι» (insoles).
  5. *A word that names two things, read as the kind's*: Google's shelves "Coffee
     Grinders" and "Spice Grinders" as angle grinders, "Decorative Fans" as fans, "Nail
     Drills" and "Drill Chucks" as drills, "Jigsaw Puzzles" as jigsaws, "Curling Irons" as
     irons, "Washers" as washing machines.
  6. *A kind missing*: the packs' "table saws" read as tables, "concrete mixers" as
     mixers, "nailers and staplers" as strollers, "workbench vises" as taps; "tile
     cutters", "reciprocating saws", "polishers", "spray guns" as nothing.
  Not in step 1: the shops' own shelf names (in the server's catalogue: step 2). Told to
  the owner in Greek, short, with the numbers per category.
- **The big general debugging of the search, its method approved (owner, 07/11:
  «Ναι σε όλα, πάμε σε νέα συζήτηση»): the method, the bar (no absurd card, at least 98%
  of the first page's cards right) and about $3 for the AI audit; the method is the next
  bullet but one.** Begin with the full measure of all 18 categories, the map of errors:
  step 1 offline first (free: build the searches per kind and read them with
  `understand_product_query`, a table per category), then steps 2 and 3 on the server's
  catalogue through a workflow of their own, built as `ai-measure.yml` is (the key from
  GitHub's secrets, the catalogue copied read only as `server-confusions.yml` does, `if:
  false` until it runs, a budget in code that stops at about $3); tell the owner before a
  run that spends, then read it by hand and give the owner the numbers per category,
  short, in Greek; then the worst category first. The "did you mean" rule is still the
  owner's to decide when it comes. How it started, the owner's words:
  «Θα πάμε σε άλλες συζήτηση έχω κάνει και άλλα τεστ βέβαια είναι στα ελληνικά που δεν με
  ενδιαφέρουνε αλαφαντάζομαι ότι και στα αγγλικά θα υπάρχουν παράδειγμα μπαταρίες 3α
  βγάζει μπότες δεν μπορώ να εμπιστευτώ ακόμα αυτό το service για production σελίδα..
  ζητάω μία μεγάλη γενική απασφαλμάτωση». Read: Greek searches matter less to the owner
  (the site is in English, for the UK); the owner expects the same faults in English; the
  site is not yet trusted as a production page. **The example, traced on 07/11** with
  `picwise_nlu.concept_understanding.understand_product_query`: «μπαταρίες 3α» and
  «Μπαταρίες 3Α» (plural) are read rightly as `battery`; the singular «μπαταρία» or
  «μπαταρια» (with "3α", with "aaa" or alone) as `boots`: no kind holds the word, and the
  fuzzy match takes it for «μποτάκια» (two letters off), the page saying "could not match:
  μπαταρια". The engine's reading is the same since `a7539b9` (`src/picwise_nlu` and
  `src/picwise_taxonomy` unchanged), so the boots came before the AI, which only reads the
  products the engine chose. In English "battery", "aaa battery", "aa battery" and "battery
  aaa" are read rightly; a like fault in English seen before: "rubber gloves" read as
  router (05/11). The method: the next bullet, proposed to the owner on 07/11.
  **The scope** (the owner asked, 07/11: «Πόσες κατηγορίες και υποκατηγορίες έχει?»): 18
  categories (`product_concepts._MEGA`), 312 kinds (278 main, 34 narrower, two levels at
  most), 1,263 English and 762 Greek names; of the 595,751 products of 06/11, 279,619
  carry a kind. The design-time packs (`picwise_taxonomy.deep_packs`: 128 departments,
  591 subcategories, 1,140 product families) are not read by the search.
- **The debugging method proposed to the owner (07/11)**, after «Η απασφαλμάτωση πρέπει να
  είναι στοχευμένη ανακατηγορία και εκτενέστερη.. κάθε φορά βρίσκουμε λάθη και κενά...
  Πρότεινε τον καλύτερο τρόπο απασφαλμάτωσης για το βέλτιστο.» ("ανακατηγορία": per
  category; this replaces the owner's 05/11 "no more kind-by-kind fixes" with a planned
  sweep). **Approved** («Ναι σε όλα, πάμε σε νέα συζήτηση», 07/11): the method, the bar
  and the AI audit's cost, about $3.
  - **Category by category**, the 18 of `product_concepts._MEGA`, English first (Greek
    only where it is cheap), each checked at the three places errors are born:
    1. *The search read* (free, offline, `understand_product_query`): for every kind, each
       of its names in singular and plural, with common typos (a letter missing, doubled,
       swapped, a neighbouring key) and with a brand, a size or a need added; also the
       design-time packs' 591 subcategories and 1,140 product families and the shops' own
       shelf names, each with the category it belongs to. Listed: every search read as
       another kind, or sent by a fuzzy guess to a kind of another category, or read as
       nothing (a gap).
    2. *The products put in each kind* (the server's catalogue, through a workflow as
       `server-confusions.yml` does): every product the reports flag (the title names none
       of the kind's words, 16,987 on 06/11; only the title names it, 10,352; doubted by
       the aisle, 3,496; accessory words such as "case", "cover", "strap", "replacement",
       "compatible", "for"; a price far from the kind's) and 60 unflagged ones per kind,
       judged offline by Haiku ("is this a <kind>?"); about 10,000 of the 316,000 products
       with no kind, Haiku naming one of the 312 or none (the gaps). About $3 in all, at
       the measures' $0.0011 a call of 30 products; the AI's verdicts checked by hand on a
       sample.
    3. *What the visitor sees* (the server's catalogue): about 2,000 searches, several per
       kind; the first 12 cards of each judged by their kind and the AI's verdicts: the
       share right, the absurd cards (boots for batteries), the searches with nothing or
       "could not match".
  - **Fixed by cause** where a rule can say it (an accessory for X is not X; a fuzzy guess
    on a real word, or to a kind of another category, not trusted: "did you mean ...?"
    rather than wrong products, the owner's decision when it comes), else per kind (a
    missing name or kind).
  - **Nothing comes back:** each error found becomes a test (searches with their kind,
    titles with theirs), run with every change; the scoreboard printed by every deploy.
  - **A scoreboard per category**, before and after: searches read right, cards right on
    the first page, products with no kind, absurd cards. A category is ready when it
    passes the owner's bar (proposed: no absurd card, at least 98% of the first page's
    cards right).
  - **Order:** one full measure of all 18 first (the map of errors), then the worst
    category first unless the owner chooses, each deployed on the owner's «ανέβασε»; the
    three AI fixes kept go with the first build. Several conversations.
- **The AI layer live (06/11), and the owner's first try.** Deployed on 06/11 on the
  owner's «ανέβασε το 75fd3d0»: `75fd3d0` pushed to `ccr-1361f1a7-dcpo60` (a fast-forward
  from `a7539b9`), run `42287840883`, success; release `20261106T202256Z-75fd3d0`, the site
  on it since 20:41:34 UTC. Its log: "Anthropic key: set", "anthropic 2.6.0", "assist:
  active", "answering the jobs of /srv/picwise/assist; at most $1.00 a day", "AI layer
  (picwise-assist): active, jobs folder: on", "AI spend today: none"; 595,751 products
  from 80 shops prepared again (1,057.65 s, peak 10.08 GB); 15 of 15 pages and 12 of 12
  searches the same as Vercel's; the site's memory 6,969 MB; the offers still not fetched
  (401). A session cannot reach picwise.subby.cloud (the proxy answers 403): the owner was
  asked to try a complex search («σακίδιο για σχολείο», "quiet washing machine") and say
  whether, a few seconds after the page, a sentence appears and the products that fit
  move up with a ✓, and whether the same search again comes at once that way. **The
  owner's first try** (07/11, 09:47 UTC, a phone's screenshot of «σακίδιο για σχολείο»):
  "Results for: σακίδιο για σχολείο, those that fit first, then cheapest first · PicWise
  could not match: σχολειο", 12 of 251; the sentence "2 of these 30 backpacks say they
  suit school days or heading to school, lowest price 8.99 GBP." with "Checked against the
  shops' own words"; first a Disney Cars "junior School Backpack" (✓ "School Backpack",
  £8.99, 5th cheapest) and "Backpack Stay Cool & Stylish on the Go" (✓ "heading to a
  picnic, school, work", £9.99, 6th), a cooler bag: weak but true; "No Recommended here:
  too few products say they fit to have a middle price." Told to the owner: it works as
  built; the cooler bag; the AI reads only the first 30 of the 251; the sentence writes
  "8.99 GBP" where the cards write "£8.99"; asked whether it came a few seconds after the
  page, at once the second time, and "quiet washing machine". If nothing
  comes, the first place to look is the service's own log on the server (`journalctl -u
  picwise-assist`; no workflow prints it yet) and the files of `/srv/picwise/assist`.
  Then the spend on the Console after a day or a week (the spec, 5: "after a week, its use
  and cost to the owner"); each deploy's "AI spend today" line reads the day's file in
  `/srv/picwise/assist/spend/`. The decisions behind it (06/11): the products the AI reads
  as fitting marked and first, a cap of one euro a day, the privacy text naming no
  company, then «Ναι, συμφωνώ με όλα, προχώρα» to the order, the time, the mark and the
  wording; written into `PROJECT_RULES.md` (2 and 5), `docs/MISSION.md` and the Decision
  Contract ("The products that fit a complex search first").
- **Fixes kept, to be built all together** (owner, 07/11: «Κράτα τη διόρθωση και θα κάνουμε
  και άλλες όλες μαζί»): nothing built; add each fix the owner's tries show, then build
  them in one go on the owner's word (a change to the AI's request needs a measure before
  it is deployed). So far, from «σακίδιο για σχολείο»:
  1. A product made for something else, whose words name the need only among other uses,
     read as fitting: "Backpack Stay Cool & Stylish on the Go", a cooler bag, ✓ "heading
     to a picnic, school, work". To tighten in `picwise_ai.request.SYSTEM_PROMPT`.
  2. The AI reads only the first 30 products of the usual order (mostly the cheapest), here
     of 251 backpacks: dearer products that fit are never seen.
  3. The sentence writes "8.99 GBP" where the cards write "£8.99".
- **What was built on 06/11** (the spec, 4.5): the selection puts the products a stored
  answer read as fitting first, the Recommended among them ("Mid-priced of those that
  fit"), found by a signature of the 30 products the AI reads; the page writes a draft
  that becomes a job only when its script asks, so a bot costs nothing; `picwise-assist`
  (own user, own key, at most $1.00 a day and 30 calls a minute) answers it; a stored
  answer draws the products that fit first with a ✓ and their own words, the sentence and
  "Checked against the shops' own words"; the shops' words as searches with their counts;
  the privacy page's "Complex searches"; the deployment that installs it all, and leaves
  the site as before when GitHub holds no key. **Every test module run on its own** (290, six at a
  time, 20 minutes each at most): 287 pass with the final code (two performance modules,
  whose mock of the search the build had bypassed, fixed and passing; the slow
  `test_picwise_learning_stage7b` passing alone in 1,161 s, as on the deployed code,
  1,171 s); `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4` fail, as they do on `a7539b9`;
  `test_picwise_search_index_blind_evaluation_stage6a` does not finish in 20 minutes on
  either. When the owner asked what "the button" was
  (the shops' words of 05/11), it was told, and fixed: the shops' words never come from a
  product answered `no` (the fourth run's "Skinguard (1)" came from a manual razor).
- **What the fourth run found** (the catalogue of 06/11 04:24 UTC, 595,688 products, as
  the third; the spec, 4.8, has it all): 118 asked; a sentence for 57 (52 in the third; 27
  of them for Greek searches), the shops' words for 10 (14 words), nothing for 50, withheld
  1; `yes` 231, 1 unproved; `no` 261 (the products of another kind on the pages: manual
  razors, washers and pegs, iPad cases); $0.1278, $0.00108 a search; 5.2 s in the middle,
  11.1 s at most. No sentence wrong; the third run's three right now. Doubtful: "mattress
  for back pain" and «στρώμα για πόνο στη μέση» (two "Kids Spring Mattress" saying they
  "improve spinal alignment"). Weak but true: a 350 ml cafetière "made for brewing at
  work"; "1 of these 3 sofas says it suits your living space". Twice 15 blenders counted
  where 16 say smoothies. Lost: "router for a large house" (withheld for the price of an
  unproved `yes`). Buttons: "Skinguard (1)" for "electric shaver for sensitive skin"
  doubtful (the word of a manual razor the AI answered `no`); "Cordless" for a travel iron
  and "Ryzen AI 5 · Core i7" for video editing loose.
- **Built since the fourth run:** the shops' words only from the titles of products not
  answered `no` (`picwise_ai.checks.shop_words_that_pass`, given the verdicts), which
  drops "Skinguard"; a test; not measured again (a fifth measure only if the owner wants
  one).
- **Built for the fourth run** (`afa7e53`, owner: «Προχώρα»): in
  `picwise_ai.request.SYSTEM_PROMPT`, a product not of the kind shown is `no`; an age the
  title states decides, whatever the description says; "suitable for all skin types" shows
  no need; the kind in the plural and a plain clause after "say", "This <kind> says" when
  one product was given. In `picwise_ai.checks._proved`, a `yes` whose words are pieces
  joined by ";" or an ellipsis is read piece by piece. 39 tests. The preflight (`7ad7bf1`,
  run `42197118744`, four requests on fictional products) read each rule right.
- **The runs before:** the third (`42192705450`): a sentence for 52, three not right (a
  manual razor called an electric shaver, "all skin types" counted as dry skin, "1 - 2
  Years" backpacks for school); the second (`42120003523`): a sentence for 39, withheld 11;
  the first (`42112519518`, titles only, "none" sentences): 23 sentences with products.
- **What it measures, and how to run it again** (from `0631666`): each `yes` must give the
  words of its product's title or description that show it, counted only when they stand
  there letter for letter (in one run or in pieces); numbers and names of a description
  allowed; the shops' words must name what serves the need. A run is one commit that
  changes only `if: false` to `if: true` in `.github/workflows/ai-measure.yml`, pushed to
  `ccr-4f47068a-99ikwe` (it copies the server's prepared catalogue read only, with the
  deploy key and the host key's pin, as `server-confusions.yml` does; 163 searches; a
  budget of $1), then one commit that turns it off again and records the run in the
  file's lines. A push of that file with `if: false` runs nothing (the job is skipped).
  The session's stop hook asks for every commit to be pushed: so the "on" commit is made
  only with the owner's word.
- **How to read it:** `get_job_logs` with `return_content` and `tail_lines` 20000 saves the
  log as JSON to a file; take its `logs_content`, strip each line's time stamp, then read
  the "IN SHORT" totals and every search: SHOWN, BUTTONS, NOTHING or WITHHELD, each `yes`
  with "its words" (now checkable by eye), the "unproved" ones, the shops' words proposed
  and answered by the catalogue. Read every sentence, every `yes` and every button by hand.
- **The mark on the cards** was what the owner asked about on 05/11 («ΕΥΡΕΤΗΡΙΑΖΟΝΤΑΙ
  ΚΑΛΥΤΕΡΑ ΤΑ ΠΡΟΙΟΝΤΑ ΤΩΡΑ ΕΙΔΙΚΑ ΣΤΙΣ ΣΥΝΘΕΤΕΣ ΑΝΑΖΗΤΗΣΕΙΣ»), decided on 06/11 and built:
  the products that fit come first, marked. Write to the owner in Greek, plain and short
  (the owner said «?» to a long message).
- **Not yet built, for later:** a fifth measure, if the owner wants one, to see the new
  order on the server's catalogue (the measure prints the AI's answers, not the page's
  order); the doubtful sentences of the fourth run (kids' mattresses for back pain) and
  the loose buttons ("Cordless" for a travel iron, processor names for video editing),
  which the owner has not ruled on.
- **The account** (05/11): the Claude Console, an Individual organisation («Νικος's
  Individual Org»), $10 of credit bought with a European VAT number, auto-reload off (the
  dashboard showed «Turn on auto-reload»), the Start tier ($500 a month cap); the key
  `picwise-server`, never expiring, Default workspace, linked to the owner, in GitHub's
  secrets as `ANTHROPIC_API_KEY` (the first key, which expired on 5 December, deleted).
  Spent: the preflights a fraction of a cent each, the first measure $0.0623, the second
  $0.1111, the third $0.1236, the fourth $0.1278: about $0.43 in all.
- **Branches:** `ccr-4f47068a-99ikwe` holds all of `ccr-f9cf1b70-rzslft` (fast-forwarded)
  and this work; start from it. The conversation of 07/11 (step 1) worked on its own
  `ccr-8aef8908-2u46pb`, fast-forwarded from `c59ec8a` of `ccr-4f47068a-99ikwe`; its
  commits are pushed to `ccr-4f47068a-99ikwe` too (the owner, 07/11: «Ναι» to keeping it
  up to date). The deploying branch `ccr-1361f1a7-dcpo60` holds
  `75fd3d0` (the AI layer, live), and the working branch only the records written after
  it. No workflow runs on a push to the working branch but
  `ai-key-check.yml` and `ai-measure.yml`, each only when its own file changes. The two
  run only on `ccr-4f47068a-99ikwe`, whatever a conversation's own branch is: the
  conversation of 06/11 worked on its own `ccr-c4267777-9czn99`, kept equal to it (each
  commit pushed to both; no workflow names that branch).
- **The owner's order** (05/11): the AI part (c) first, then (a) the classifier, then (b)
  the sentence from the counts (the spec, section 5).
- **Seen through the AI's `no` answers** (the kind items stay parked, the owner's word):
  products of another kind on a kind's page (a fridge magnet among fridges, cake pans and a
  play set among frying pans, dummy AirPods among headphones, iPad cases among tablets,
  galvanised iron plates among irons, manual razors among electric shavers, a filter washer
  among the 3 washing machines); kinds with no product (dishwasher, air purifier, child car
  seat, high chair); English "best" and "cheap" read as words to match. Material for (a).
  On the third run's pages: titles that say "Used- very good" shown as new (a curly-hair
  dryer, board games), since the condition is read from its column only. The fourth run's
  `no` answers name more: 27 manual razors among electric shavers, 21 washers and weed
  pegs among washing machines, 16 iPad cases and stands among tablets, PC case fans among
  fans, cake pans, milk pans and saucepans among frying pans, earring backs among watches.
- Small notes: `actions/setup-python@v5` warns that Node 20 is deprecated (it runs on
  Node 24); the lexicon holds 312 kinds (the map below says 278).

## Before (2026-11-05): the AI layer's spec, the key, its core and two measures

- **Latest (05/11, about 22:45 UTC): the second measure run and read** (owner: «Ναι»; run
  `42120003523`; off again): 119 asked, a sentence for 39 (23 before), the shops' words
  for 11, nothing for 58, withheld 11 (10 for "This kettle says"); `yes` 208 (87 before);
  $0.00093 a search. Many `yes` come from descriptions that could not be checked by eye.
  **Built since, not yet measured:** each `yes` must quote the product's own words, and
  counts only when they stand in its title or description; "This <kind> says" accepted;
  numbers of a description allowed; stricter shops' words (the spec, 4.8). 37 tests.
  **Next:** a third run, on the owner's word.
- **Latest (05/11, about 22:00 UTC): the smarter answer built (owner: «ΣΩΣΤΑ»), the
  preflight passed; the second measure waits for the owner's word.** `5b91f71`: the AI
  reads each product's description too (`complex_search.description_of`, 400 characters,
  markup removed); no sentence when nothing fits, but up to 3 shops' words from the given
  titles (`checks.shop_words_that_pass`: no brand, judgement or the kind's name), each
  offered only when its own search finds products of a kind with every word honoured,
  with that count (`shop_words.verified_shop_words`); with neither, nothing; a stricter
  `yes`; "rated for" allowed; one product as "This ... says". 34 tests. Preflight run
  `42116311350`: "quiet washing machine" found the one saying "low noise 49 dB" only in its
  description (3 of 6, the sentence passed); "washing machine for a small kitchen" read
  the two "Compact" titles as fitting ("2 of these 4 washing machines say compact, ...",
  passed), so the shops' words were not reached there; the second call read the cached
  instructions (1,230 tokens at a tenth of the price).
- **Latest (05/11, about 22:00 UTC): the owner, of the "none" sentences: «ΟΤΑΝ ΔΕΝ ΒΡΙΣΚΕΙ
  ΚΑΤΙ ΝΑ ΜΗΝ ΛΕΕΙ ΔΕΝ ΒΡΕΘΗΚΕ ΣΚΕΨΟΥ ΚΑΤΙ ΠΙΟ ΕΞΥΠΝΟ».** Proposed (not built): (1) the AI
  reads each product's own description too, not the title alone (the prepared catalogue
  keeps it, capped, in the search fields; the engine's filters read only title, type and
  brand, `_FILTER_FIELDS`), so a need stated there ("low noise 49 dB", "ages 6-10") is
  found; (2) when none fits, no sentence: the words the shops use for that need, from the
  kind's own titles, as buttons that narrow the search, each with the count the catalogue
  gives (never the AI's); (3) with neither, nothing. To be measured on the same 163
  searches, on the owner's word, before anything reaches the site.
- **Latest (05/11, about 21:45 UTC): the AI measure run, read by hand; the measure off
  again** (owner: «ΝΑΙ» to turning it on; run `42112519518`, the catalogue of 05/11 12:44
  UTC, the server matched the pin, nothing changed on it). 163 searches: 119 asked (the 15
  controls none), **117 sentences shown, 23 naming products that fit (15 of them Greek
  searches: «τροφή σκύλου για κουτάβια», «μπότες για χιόνι», «σαμπουάν για πιτυρίδα»), 94
  "none of these say"**, 2 withheld (one rightly, one wrongly: "rated for 20°F"). None
  read false; one overstated ("Sensi" razors), one loose (toys "for children" for a
  3-year-old). `yes` 87 (81 plainly right), `no` 64 (mostly products of another kind on
  the page: a fridge magnet among fridges, cake pans among frying pans, dummy AirPods,
  bicycle and polo helmets for a motorcycle), `unclear` 2,354. **$0.0623 in all,
  $0.00052 a search; 3.5 s an answer in the middle, 7.5 s at most** (time-out 8 s). The
  spec, 4.8, holds the details. **Put to the owner:** show the sentence only when some
  products fit (the "none" ones add little to the page's "could not match"); the small
  fixes; then wire it to the site (the service, the page, the key to the server), each
  step on the owner's word.
- **Latest (05/11, 21:20 UTC): the AI layer's core built and tested, one request proved end
  to end; the measure ready, not run** (branch `ccr-4f47068a-99ikwe`, nothing on the site
  or the deploying branch). `src/picwise_ai/`: `complex_search` (asked only when a search
  for a kind is answered and some words are matched by no product of it, or a narrower kind
  fell back; never for judgements, English ones too, a condition, no kind, or an answer
  found by words; up to 30 products in the page's order, prices as shown), `request`
  (Haiku 5.5, effort low, a JSON schema, products numbered, no links), `checks` (counts,
  prices, numbers, names, forbidden words, links, Greek, one sentence, 30 words), `client`
  (SDK imported only in `make_client`; cost from usage; any failure shows nothing).
  `deployment/server/requirements-ai.txt`: anthropic 2.6.0 and 15 packages, every hash,
  for Python 3.12. Tests: `tests/test_picwise_ai_layer.py` (25, the API faked; a dry run
  on a small prepared catalogue); the 31 NLU, catalogue and boundary modules still pass.
  **Preflight** (`ai_preflight.py`, run `42111149372`): the layer's own request on six
  fictional washing machines: the two quiet ones "yes", the four others "unclear", the
  sentence "2 of these 6 washing machines say they are quiet, the lowest price among them
  being 499.00 GBP." passed the checks; 374 tokens in, 147 out, 936 cached; $0.000228;
  2.0 s. **Next:** the measure (`.github/workflows/ai-measure.yml`, 163 searches, a budget of
  $1): it copies the server's catalogue as the audit does (the deploy key, read only), so
  it is pushed only with the owner's word naming the commit and the branch.
- **Latest (05/11, about 21:00 UTC): the owner chose the AI part (c) first** («ΝΑΙ», to
  «Να ξεκινήσω να το φτιάχνω;», after asking whether products are now indexed better,
  especially in complex searches: not yet, nothing changed on the site). The order is
  now (c), (a), (b) (the spec, section 5). First milestone: the offline measure of about
  150 complex searches (the spec, 4.8), shown to the owner before anything is wired to
  the site.
- **Latest (05/11, 20:40 UTC): the Anthropic API key is in GitHub's secrets and works.**
  The owner made a Console account (Individual, «Νικος's Individual Org»), bought $10 of
  credit with auto-reload turned off (the dashboard then showed $10.00 and «Turn on
  auto-reload»; the tier's cap $500 a month), entered a European VAT number at the
  purchase, and made a key with «Get API key», which asked for no name, workspace or
  expiry: **it expires on 2026-12-05 at 20:37 UTC** (30 days; the owner read it on the
  Console), so the owner was asked to make a new one with no expiry («Create key» on the
  API keys page), update the GitHub secret and delete the old key. Done (owner: «OK»):
  `picwise-server`, never expiring, linked to the owner, Default workspace; the check
  run again (run `42105499951`, attempt 2, 20:49 UTC) passed the same way. Then the
  owner deleted the old key on the Console («EGINE»), and attempt 3 (20:53 UTC) passed:
  HTTP 200, "ready", 18 tokens in and 4 out. **So the secret holds the new,
  never-expiring key, and it works.** The first key was put in
  GitHub's secrets
  as `ANTHROPIC_API_KEY`. Checked by `.github/workflows/ai-key-check.yml` (this branch
  only, run when its own file changes; never prints the key): run `42105499951`, the
  secret 106 characters starting `sk-ant-`, HTTP 200, `claude-haiku-5-5` answered
  "ready", 18 tokens in and 4 out (well under a cent), in about 0.8 s from GitHub's
  runner. Nothing on the server or the site touched; the deployment does not yet pass
  the key to the server (part (c), the spec 4.6). **Next:** the owner's yes to start (b).
- **Latest (05/11, later): the AI layer's spec written, waiting for the owner's approval**
  (`docs/PICWISE_AI_LAYER_SPEC.md`; nothing built, nothing pushed to the deploying
  branch). It holds the three parts as approved, what each may never do, how each is
  measured before it counts, and the owner's decisions, each with a proposal (its section
  6), with a summary in Greek for the owner. Its choices beyond the approval: (b) first,
  the smallest; (a) a naive Bayes classifier, standard library, that judges a doubtful
  product only between the kinds its own words name and its aisle may hold, and "none"
  (never against the aisle rule; the 3,160 made doubtful by their aisle are only
  reported), in the shade until the owner's «ανέβασε»; (c) asked only when the page says
  "PicWise could not match" (not for the buyer's judgements, not when no kind is
  understood), through a separate service `picwise-assist` that alone holds the key and
  the SDK, so the page and the site's workers never wait; about $0.0005 a search at Haiku
  5.5's prices (read on Anthropic's pricing page on 05/11: $0.10 / $0.50 per million
  tokens, prompts up to 100,000), a cap of $1 a day proposed. Found while writing it: the
  lexicon holds 312 kinds (the map below still says 278); English "best", "cheap" are
  read as words to match, not as judgements (only the Greek ones are,
  `_JUDGEMENT_QUALIFIERS`). **Then the owner: «παμε για το απι κευ»**, taken as a yes to
  the spec (told to the owner). Given the steps (the spec, 4.6): an account on the Claude
  Console (`platform.claude.com`), $10 of credit with reload off, a spend limit of $30 a
  month on the Billing page, a workspace "PicWise", a key linked to the owner
  and scoped to that workspace (a key not scoped to one must name the workspace on
  every request), no expiry, put in GitHub's secrets as `ANTHROPIC_API_KEY`, never in the
  chat. **Then the owner: «εχω ηδη συνδρομη στο anthropic claud σε αυτο που μιλαμε»:**
  told that the plan pays for Claude and Claude Code, not for the API, but that Max, Ultra
  and Team plans carry a monthly API credit ($100, $200, $20-100 a seat up to $500;
  claimed on claude.ai, Settings > Billing, "API credits", by linking a Console
  organization, one per plan, not changeable later without support; no card; the API
  stops when it runs out, nothing charged to the plan; none on Pro or Enterprise). **The owner's plan is Pro** («ειναι προ»): no API
  credit. So the steps: a Console account, $10 of credit bought ("Buy credits"), auto-reload
  left off, so the $10 is the ceiling (credit expires a year after purchase; when it runs
  out the API refuses until more is added), a workspace "PicWise", the key scoped to it,
  the GitHub secret (the spec, 4.6). **Next:** the owner's word that the
  secret is in GitHub (never the key itself); meanwhile (b), if the owner says yes, then
  (c) with the API faked. **Branch:**
  `ccr-4f47068a-99ikwe` holds all of `ccr-f9cf1b70-rzslft` (fast-forwarded) and the spec;
  start from it.
- **START HERE: the AI layer, its implementation.** The owner, 05/11, after item 2 went
  live: «Σταματάμε εδώ αυτή τη λογική της απασφαλμάτωσης είδος με είδος θέλω να
  προχωρήσουμε στην υλοποίηση της ένταξης του συστήματος ai και αυτό θέλω να γίνει σε άλλη
  συζήτηση». So: **no more kind-by-kind fixes**; the open kind items below are parked
  unless the owner raises them. The architecture the owner approved («συμφωνώ με την
  αρχιτεκτονική και την εγκατάσταση Haiku», the bullet "Approved by the owner 05/11"
  below): (a) a classifier of our own, standard library only like the rest of the site,
  trained each night on the products whose type or shelf names their kind, a second
  opinion on the doubtful ones, measured by the audit before it counts; (b) the summary
  sentence written from the engine's own counts, no AI; (c) Haiku 5.5 only for what those
  cannot do (a need no title states), with a daily cap in code and prepaid credits,
  measured offline first. **Order:** a short spec in `docs/` first (PROJECT_RULES section 4:
  no implementation before its spec), for the owner's approval; then (a) and (b); then
  (c), for which the owner opens an Anthropic account and an API key, kept only as a
  GitHub secret passed to the server (never in the repository, a log or the chat), the SDK
  pinned with its hash in `requirements-server.txt` beside gunicorn (the site's first
  library), and an offline measure of about 150 complex searches, Greek and English, shown
  to the owner before anything goes live.
  - **What the engine already gives the AI layer (05/11):** the doubtful products
    (`UNCERTAIN_MARKER`: 37,998 on the catalogue of 05/11, the classifier's work list);
    the products whose type or shelf names their kind, read against the aisle
    (`_annotate_kinds`, the decision contract "The main kind only", points 1 to 7: the
    training set, cleaner since item 2); the signals of a complex search: words no
    product of the kind carries ("could not match", `_select_products_for_concept`), an
    answer found by words (`_doubtful_products_by_words`, reason `product_named_by_words`,
    `live_search_resolver.answered_by_words`), a fall-back to a broader kind
    (`fallback_concept_id`). The audit to measure it: `deployment/server/print_confusions.py`
    and `server-confusions.yml` (parts "kinds", "searches", "live", "compare"; 320 kinds'
    names, the owner's words and 21 products' own names, `NAME_SEARCHES`).
  - **The server's room:** 8 vCores, 24 GB, no GPU; the nightly preparation peaks at
    9.8 GB and takes about 15 minutes (04:17 UTC), the site holds 6.7 GB; a search took
    1.18 s on GitHub's runner (05/11).
  - **Parked kind items** (the owner's word above): question (3), the broader kind shown
    when the narrower has none (`electric bike`, `motorcycle helmet`, `robotic lawn mower`,
    tyres); 22 paint pots and tins InStock UK files as craft paint (one line,
    `_SUB_AISLE_HOLDS` for "art & craft paint" holding GA); 5 art marker sets; tool
    backpacks and belts; "rubber gloves" read as router; `bed sheets` (duvet covers with
    a pillow case as pillows); `sandals` (flip flops as slippers); "kids tablet" (the
    owner: the search box's suggestions). Also: the two old test failures
    (`test_picwise_search_index_generated_blind_stage4`,
    `test_picwise_search_index_blind_evaluation_stage6a`: "amazon" and "galaxy"), and the
    offers' token (Awin 401; the owner: «Δεν με ενδιαφέρει το νέο token τώρα»).
  - **Branches:** start from `ccr-4f47068a-99ikwe` (05/11, later: all of
    `ccr-f9cf1b70-rzslft`, today's work and records, and the AI layer's spec). The
    deploying branch `ccr-1361f1a7-dcpo60` is at `a7539b9`, deployed. A push there needs
    the owner's word naming the commit and the branch, every time (the session's safety
    check stops it otherwise, read-only workflows too).
- **Latest (05/11, 12:57 UTC): item 2 deployed** (owner: «Ναι, στείλε το a7539b9 στο
  ccr-1361f1a7-dcpo60 για να ανέβει στο site»). Run `42028878547`, success: release
  `20261105T123843Z-a7539b9`, the site on it since 12:54:15 UTC, health ok; 577,670
  products from 80 shops prepared at 12:44:51 UTC (891 s, peak 9.8 GB); 15 of 15 pages and
  12 of 12 searches the same; the log now says truly what listens (Caddy on 80 and 443).
  The kind report: **274,821 products shown as a kind** (the measure's own number); made
  doubtful by their aisle 3,160 (2,639 in the morning): `washing_machine` 141 doubted, 3
  still of the kind; `toner` 161 and 155; `paint` 59 and 10; `bag` 586 and 1,393. The
  offers: still 401 (the owner: not now). **Not done after it:** a live read
  (`server-confusions.yml`, parts "searches" and "live": a push of the workflow alone,
  with the owner's word); offered to the owner. **Next, the order agreed:** the AI layer's
  spec (`docs/`, PROJECT_RULES section 4) for the owner's approval; open: question (3)
  (the broader kind when the narrower has none), the paint pots filed as craft paint (one
  line: `_SUB_AISLE_HOLDS` for "art & craft paint" holding GA), "rubber gloves" read as
  router, `bed sheets` (duvet covers with a pillow case read as pillows), `sandals` (flip
  flops as slippers).
- **Before (05/11, 12:45 UTC): item 2 measured; waiting for the owner's «ανέβασε».** Run
  `42025667252` (the catalogue of 05/11 10:41 UTC, 577,676 products; against the rules
  deployed, `7b55cf8`; pushed with the owner's word «Ναι, στείλε το 19d564e και μετά το
  6975029 στο ccr-1361f1a7-dcpo60 για τη μέτρηση», `19d564e` with `[skip actions]`: no run).
  **527 products read otherwise, all to doubtful, none gains a kind**: bags 165 (gift,
  food-storage, rubbish, lunch, nappy wet bags), washers 139, face toners 88, health
  monitors 26 (fertility, biometric, ovulation, one blood-pressure), markers 23 (18 golf
  ball markers; **5 "Ohuhu" art marker sets, wrongly**), paints 22 (**InStock UK's "Paint
  (All Colours)" test pots and 5 L tins filed as "Art & Craft Paint", most likely real
  paint, wrongly**; an eye-shadow primer), face mirrors 16 (make-up and Hollywood mirrors;
  a 60x80 cm "Crystal Pro Mirror Portrait" perhaps wrongly), life jackets 10, lunch and
  tool bags as handbags 8, cake servers 7, rubber gloves 4, digital downloads 4, ropes 3,
  pet food containers 3, tool backpacks 2 and tool belts 2 (debatable), light therapy
  lamps 2, a nail drill, an OBD2 scanner, a storage tin. Riding gloves kept (6). Part 4
  (a type's or shelf's kind on an aisle that may not hold it): 527 -> 0. **Searches of a
  kind with a wrong product among their first 12: 31 of 284 -> 7 of 275** (9 now answered
  by their words); left: item 3's 5 (`electric bike` 12, `motorcycle helmet` 12, `robotic
  lawn mower` 10, `summer tyres`, `winter tyres` 1), `bed sheets` 4 (duvet covers with a
  pillow case read as pillows), `sandals` 1 (flip flops as slippers). `washing machine`
  142 -> 3 products, `toner` 229 -> 151, `bag` 1,483 -> 1,323, `paint` 32 -> 10, `server`
  59 -> 52, `tv` 43 -> 39, `monitor` 821 -> 802, `mirror` 411 -> 395. **By their words**
  (this commit's search): vitamin tablets 17, electrolyte tablets 1, sugar mice 1, lash
  fans 36, life jacket 2, face toner 24, golf ball marker 24, cake server 2, gift bag 60,
  lunch bag 23, tool backpack 2, tool belt 1, nail drill 1, craft paint 5; kids tablet 1
  (a children's probiotic: the owner's accepted case). **Found, not item 2:** "rubber
  gloves" is read as router (56 routers, a typo correction), "blood pressure monitor"
  finds none, "light therapy lamp" lists 812 lamps. A search on GitHub's runner: 1,180 ms
  against 1,110 (+6%). **To deploy:** the code is on the deploying branch already, so a
  push deploys only if it touches `server-deploy.yml`'s paths: the next commit carries a
  one-line fix of a stale line of the deployment's log ("nothing on 80 or 443", while
  Caddy serves both since 31/10), pushed only with the owner's word naming it.
- **Before (05/11, 12:15 UTC): item 2 built and tested, not deployed, not yet measured**
  (owner: «Εντάξει, προχώρα με το βήμα 2»; commit `fbe16d4`). (a) A kind the shop's type or
  shelf names is read against the aisle as a title's is (`_annotate_kinds`, `aisle_rule`):
  when the aisle may not hold it, the title decides under the same rule
  (`_title_fallback_head`), else doubtful; riding clothing holds JW too (riding gloves).
  (b) **Found by the live check below, a side effect of the rule deployed today:** a
  search for the products it set aside, by their own name ("vitamin tablets", "sugar
  mice", "lash fans"), showed the main kind ("could not match: vitamin"), where before it
  found them by accident; step 2 alone would add "life jacket" (a puffer jacket), "tool
  backpack". Fixed in the same commit (`search_selection._doubtful_products_by_words`):
  when a search for a kind has words besides the kind's name that none of the kind's
  products carry, the doubtful products carrying them and a name of the kind in their
  title or type are the answer; the page names no kind ("Results for: vitamin tablets", no
  "Understood as", `live_search_resolver.answered_by_words`); the query log keeps the
  reading. The owner, of "kids tablet" (kids' vitamins if no tablet says "kids"): «Όταν
  κάποιος γράψει kids. Το ευρετήριο θα προτείνει την επόμενη συμπλήρωση λέξεις ...εκεί
  λοιπόν γίνεται η διόρθωση κατά τη χρήση του χρήστη.. δεν χρειάζεται να το παιδεύουμε
  άλλο... Πιστεύω ότι υποδομή είναι επαρκής... Με δεδομένο ότι θα μπει και το άλλο σύστημα
  ai..». The decision contract, "The main kind only", points 6 and 7; PROJECT_RULES section
  2. Tests: `tests/test_picwise_shelf_kind_on_another_aisle.py` (6; 16 checks fail on the
  deployed code); the 133 modules that read kinds, the search or the app: all pass (1,403
  tests, the learning one included). The audit (`print_confusions.py`) searches 21
  products by their own name too (`NAME_SEARCHES`) and reads an answer found by words as
  such. **Next:** the measure on the server's catalogue (`server-confusions.yml`, parts
  "kinds", "searches", "compare" against `7b55cf8`): code pushed with `[skip actions]`,
  then the workflow alone, each push only with the owner's word naming commit and branch;
  then «ανέβασε».
- **The live check after the deployment** (run `42016489822`, the catalogue the deployment
  prepared): the live site shows the copy's cards, card for card, on 320 of 320 pages (all
  answered). Searches of a kind with a wrong product among their first 12: **21 of 270**
  (38 of 269 on 04/11). Left: item 2's 14 (`washing machine` 12: the first cards TIMCO
  washers from £0.81, read as washing machines off their shelf "Washers", as before
  today's deployment, now flagged by the narrower aisle; `toner` 11, `bag` 10, `server` 7,
  `paint` 5, `tv` 4, `handbag` 3, `belt` 2, `gloves` 2, `monitor` 2, `drill`, `mirror`,
  `scanner`, `skirt` 1); item 3's 5 (`electric bike`, `motorcycle helmet`, `robotic lawn
  mower` 10, `summer tyres`, `winter tyres`: the broader kind); not looked at yet: `bed
  sheets` 4, `sandals` 1.
- **Before (05/11, 10:53 UTC): the main kind only deployed** (owner: «Ναι, ανέβασε»; the
  session's safety check stopped the push as a production deploy, then the owner: «Ναι,
  στείλε το 7b55cf8 στο ccr-1361f1a7-dcpo60 για να ανέβει στο site»). `7b55cf8` pushed to
  `ccr-1361f1a7-dcpo60` at 10:33 UTC; run `42011735026`, success: release
  `20261105T103355Z-7b55cf8`, the site on it since 10:50:50 UTC, health ok; 577,676
  products from 80 shops prepared at 10:41:40 UTC (973 s, peak 9.8 GB; the deploy step 17
  minutes, against 11 on 01/11); 15 of 15 pages and 12 of 12 searches the same. The
  deployment's kind report: 275,348 products shown as a kind; **2,639 made doubtful by their
  aisle**: barbells on body jewellery 1,030, bags on sweets and party favours 411, phone
  cases 137 (jewellery holders, pencil cases), jackets 116 (cat treats "Skin&Coat"), tablets
  93 (fish food, electrolytes, sweets), ink cartridges 92 (extension cords "Ink - Lola's
  Leads", a vest "Sonic Ink"), toners 73, fans 66 (eyelashes), dresses 57 (Finediam's
  "Band Dress" rings), mice 57 (sugar mice, rat poison). Still there (item 2): `tv` shows
  3 digital downloads among its first 4 (shelf "Film & Television Digital Downloads").
  **The read-only check after it** (`394b86b` on this branch: `server-confusions.yml`,
  parts "searches" and "live") **was stopped too by the session's safety check as a
  production deploy: not pushed, the owner asked.**
- **New (05/11): the offers are not fetched.** During the deployment, «offers: not fetched
  (Awin's accounts call answered 401); the last file kept»: Awin refuses the token. The
  offers file is the one fetched 2026-11-03 05:05 UTC (93 live, of 31 of the 84 shops), so
  the nightly fetches of 04/11 and 05/11 wrote none either (their reason not read). The
  site keeps showing an offer only while its own dates say it is live, so the ones that end
  drop out and new ones do not come in. Told to the owner (a new API token in Awin, put in
  GitHub's secret `AWIN_API_TOKEN`, never in the chat; it reaches the server with the next
  deployment, `server-deploy.yml` writes the secrets). **The owner: «Δεν με ενδιαφέρει το
  νέο token τώρα»**: not now; the offers stay as they are until the owner says otherwise.
- **Before (05/11, morning): the owner's answer «Πρώτα το 1 μετά το 2»** (first fix the
  main-kind rule's few wrong results and deploy it, then the same check for a kind the
  shelf names), and «Ναι στείλε τη μέτρηση». **Built and measured, not deployed:** the
  narrower aisles of Google's (`_SUB_AISLE_HOLDS`, `_shelf_paths`; the decision contract,
  "The main kind only", point 5; tests `tests/test_picwise_main_kind_only.py`, 6). Measured
  against the rule as first built (`print_confusions.py --part compare`, run
  `41998750052`, the catalogue of 05/11, 577,686 products): 89 products read otherwise,
  81 rightly (56 Finediam rings no dresses, 8 charms no shoes, 2 riding T-shirts kept,
  fixings, blade sets and washers no tools); one socket set on "Tool Accessories" goes
  wrongly. Two entries were measured and left out (Baby & Toddler holding bags: 7 right,
  7 wrong; water-sport clothing: wetsuits as suits). Against the rules deployed, on that
  catalogue: 500 products lose their kind, 202 gain one (the run's version still held the
  Baby & Toddler entry: 14 of those gains are gone in the code). **Deployed 05/11 10:50 UTC
  (above)**; then a live read (`server-confusions.yml`, parts "searches" and "live",
  waiting for the owner's word for the push); then item 2.
- **The full test run of the final code (`32f0c93`) was stopped half-way** when the owner
  moved to a new conversation («Πάμε σε άλλη συζήτηση»): 243 of the 284 modules run, one
  process each, four at a time, from `tests/`. All pass but
  `test_picwise_canonical_vocabulary_registry_stage2` (fails as before this work) and the 8
  `test_local_nlu_*`, which fail only when run from `tests/` (from the repository root they
  pass: `python3 -m unittest tests.test_local_nlu_brand_resolver`, checked). **The rest, run
  to the end on 05/11** (branch `ccr-f9cf1b70-rzslft`, the code of `32f0c93`: only docs
  after it): the 72 modules from `test_picwise_performance_stage1c` on, alphabetically (the
  "41" left could not be told apart, so all 72), one process each, three at a time, from the
  repository root with `tests/` on the path (`python3 -m unittest discover -s tests -t tests
  -p <file>`), and `test_picwise_learning_stage7b` alone (808 s): **71 pass** (814 tests, 30
  skipped); **2 fail, each the same on the live code `4b5497b`**, neither on the kind
  reader: `test_picwise_search_index_generated_blind_stage4` (known: 32 of 184 misspelled
  variants of the registry's terms, "act on caera", "xea", find nothing) and
  `test_picwise_search_index_blind_evaluation_stage6a` (31 minutes, earlier left
  unfinished: 1 of 13, `test_negative_broad_terms_are_included` expects "amazon" and
  "galaxy" among the broad words; `blind_evaluation._NEGATIVE_BROAD_TERMS` never held them,
  since the first commit `69aa5c7`, 25/05). The owner: «Ναι, ανέβασε αν περάσουν όλα», then,
  told of the first, «Ναι, ανέβασε όταν περάσουν τα δύο αργά»; the second slow one failed,
  so nothing was pushed and the owner was asked again: «Ναι, ανέβασε». Deployed (above).
- **Approved by the owner 05/11 (below): an AI layer for complex searches** («σε έναν
  κατάλογο που συνεχώς ανανεώνεται θα προκύπτουν πάντα νέες κατηγορίες... αλγόριθμος να
  πιάνει τις σύνθετες αναζητήσεις (π.χ. από το μήκος του query ή λέξεις όπως "για", "στη")
  και τότε μόνο να ενεργοποιεί τοπικά το AI πάνω στους 20-30 επαληθευμένους τίτλους...
  παράγοντας τη "μία πρόταση" σύνοψης»). Proposed in chat: (a) first, AI each night only
  on the products the rules leave doubtful (Message Batches, half price; measured by
  `print_confusions.py` before anything ships); (b) at search time, AI only when the
  engine's own signals say the search is complex (words it could not match, a relation
  word with something after it, a fall-back to a broader kind, mixed kinds), on up to 30
  verified candidates, after the page is shown (never delaying it), with a structured
  answer (per candidate fits / no / unclear, one sentence), checked by code (ids exist,
  every number in the sentence is in the data), cached 24 h per search. The Recommended
  stays the owner's rule; the NLU stays local (tests pin no live LLM there: AI as a layer
  of its own); a spec first (PROJECT_RULES section 4); an Anthropic API key as a secret
  only; Claude Opus 5.5 for the measurement, a cheaper model the owner's choice after the
  numbers. **Then the owner:** «Μήπως είναι καλύτερα να αναπτύξουμε custom για να μην
  μπλέξουμε με χρεώσεις.. αν επέλεγα κάποιον θα έλεγα το Haiku 5.5». Proposed: no language
  model of our own on the VPS (8 vCores, 24 GB, no GPU: slow, weaker in Greek, competing
  with the nightly preparation's ~8 GB); custom where it pays: (a) a classifier of our own,
  standard library only like the rest of the site, trained each night on the products
  whose type or shelf names their kind, a second opinion on the doubtful ones, measured by
  the audit before it counts; (b) the summary sentence written from the engine's own counts
  ("12 of 40 power banks say iPhone; from £14.99"), no AI; (c) Claude Haiku 5.5 only for
  what those cannot do (a need no title states: "for a 10-year-old", "quiet"), with a daily
  cap in code and prepaid credits (to confirm on the account), measured offline first.
  **The owner: «Εντάξει, πάμε σε άλλη συζήτηση συμφωνώ με την αρχιτεκτονική και την
  εγκατάσταση Haiku»** (approved: the architecture (a), (b), (c) and Claude Haiku 5.5).
  Order: item 1 (the remaining tests, then the owner's «ανέβασε», still not given), item 2,
  then this: a spec first (`docs/`, PROJECT_RULES section 4) for the owner's approval; (a)
  and (b); then (c): the owner opens an Anthropic account and an API key, the key only as a
  GitHub secret passed to the server, never in the repository, a log or the chat; the
  Anthropic SDK pinned with its hash beside gunicorn (`requirements-server.txt`), the
  site's first library; a daily cap; the offline measure (about 150 complex searches,
  Greek and English) shown to the owner before anything goes live.
- **A push to the deploying branch needs the owner's word in the conversation, for that
  push:** on 05/11 the session's safety check stopped one as a production deploy, though it
  carried `[skip actions]`; after the owner's «Ναι στείλε τη μέτρηση» it went through. Later
  that day it stopped the deployment after a plain «Ναι, ανέβασε», and passed it after the
  owner named the commit and the branch; it stopped a read-only workflow's push too. Ask
  first, say what the push does, name the commit and the branch.
- **Which branch.** `ccr-f9cf1b70-rzslft` (05/11, later) holds all of
  `ccr-5b36715a-qh6d95` (fast-forwarded), the deployment's records and item 2 (`fbe16d4`);
  start from it. Before it, `ccr-5b36715a-qh6d95` held all of `ccr-9826870f-qkgl6s`
  (fast-forwarded) and this work. **The deploying branch `ccr-1361f1a7-dcpo60` is at
  `a7539b9`, deployed** (run `42028878547`: item 2, `fbe16d4`, on the main-kind rule
  `cdd1eb3`, `92fd939` and the narrower aisles `5ac3f1e`, `32f0c93`); this branch has the
  records after it. A push there that
  touches `src/**`, `deployment/server/**` and the rest of `server-deploy.yml`'s paths
  deploys, unless its head commit says `[skip actions]` (then nothing runs); one that
  touches only `server-confusions.yml` runs the read-only audit.
- **The owner's word (04/11).** «Θέλω να μάθω ποια προϊόντα δημιουργούν μπέρδεμα στην
  αναζήτηση.. όπως τα tablets... Banks...κτλ ... θέλω έναν ολοκληρωμένο έλεγχο από άκρη σε
  άκρη», then «Ναι, προχώρα με τον έλεγχο» (to a read-only check pushed to the deploying
  branch without deploying).
- **Built** (`deployment/server/print_confusions.py`, tests
  `tests/test_picwise_server_print_confusions.py` (5); `.github/workflows/server-confusions.yml`,
  one job a part, each with its own log): every product of the server's prepared catalogue
  read with the kinds the server stored (the rules deployed) and with this branch's (the
  main kind only); where each kind comes from (the type or the shelf, or the title alone:
  the reader's fall-back on the title, `_title_fallback_head`, recorded as it runs), and for
  the title alone whether the aisle may hold the kind (`_aisle_may_hold`); per kind by
  shelf; what the rule takes away and gives; kinds from a shelf on an aisle that may not
  hold them; the words of the kinds' names that titles carry, by aisle; every kind's search
  (320 words: the owner's and each kind's English name) on the copy with both sets of
  kinds, the first 12 cards flagged (another aisle, another kind, no kind); and the same
  searches on the live site, matched to the copy by product id (`data-choice-id`). Each part
  ends in short. To read again: change the "Read:" line of the workflow and push it alone.
- **What it found** (the catalogue of 04/11 04:24 UTC, **576,196 products**; run
  `41940401157`):
  - **The live site shows the copy's cards, card for card, on 317 of 317 pages read**; 3
    of 320 pages did not answer within 60 s (`tablets`, `mouse`, `toner`, about 00:27 UTC;
    not explained yet, the rest answered).
  - **Searches whose first 12 cards hold a wrong product: 38 of 269 today, 20 with the
    main-kind rule.** Fixed by it: `tablet` 11 → 0 (pills; 165 → 110 products), `case` and
    `phone case` 10 → 0 (pencil, glasses, toothbrush cases), `fan` 7 → 0 (false eyelashes),
    `angle grinder` 6 → 0 (pepper mills), `mirror` 5 → 1, `mouse` 2 → 0, and `iron`, `rug`,
    `wallet`, `bracelet`, `duvet`, `lamp`, `towel`, `ladder`, `football`, `doll`, `hair
    brush`.
  - **The rule changes 513 products** (all to doubtful; 0 on an aisle that may not hold
    their kind remain from the title alone), almost all rightly: pills and toothpaste
    tablets, face toners (73), gift and treat bags (79), eyelash "fans" (66), make-up
    "paint"/"primer", lip pencils "Red Carpet", pencil cases, salad servers, "DIM"
    supplements as RAM, sanitary towels, wax heaters, curling irons. **Wrongly:** 6 kids'
    backpacks on "Baby & Toddler", 5 swimsuits on "Wetsuits", 2 T-shirts on riding
    clothing (sporting goods holds no clothing read off a title), a gift-set necklace and
    earrings. **It also gives a kind to 272 doubtful products**, mostly rightly (86 safety
    shoes, 14 trainers, 13 boots on "Work Safety", kids' cutlery, gazebo curtains, a PC
    fan), some wrongly: **Finediam rings titled "... Band Dress" become dresses** (57
    dresses gained; costumes "Fancy Dress" too), "Plasterboard Hammer-In Fixings" a hammer,
    jigsaw blades a jigsaw, a baby comforter a duvet, an agility ladder a ladder.
  - **Not fixed by the rule: a kind the shop's own shelf names in another sense, on an
    aisle that may not hold it: 388 products in 19 kinds**: `bag` 165 (gift bags from
    £0.60, nappy wet bags, storage bags), `toner` 88 (face toners on Google's "Toners &
    Astringents"; the search `toner` shows 11 of 12 face toners even with the rule),
    `monitor` 26 (blood-pressure and fertility monitors; 2 of the first 4 of `monitor`),
    `marker` 23 (golf ball markers), `paint` 22, `mirror` 16 (shaving mirrors), `jacket`
    10 (life jackets), `handbag` 8 (lunch bags), `server` 7 (cake servers: 7 of the first
    12 of `server`), `gloves` 4 (rubber gloves), `television` 4 (digital downloads: 3 of
    the first 4 of `tv`), `cable` 3 (rope), `drill` 1 (a nail drill), `scanner` 1 (a car
    code reader), `skirt` 1, and tool backpacks and belts (rightly kinds).
  - **Not fixed either: when no product of the narrower kind exists, the search answers
    with the broader kind** (`_select_products_for_concept`, `fallback_concept_id`; the
    page says «PicWise could not match: motorcycle»): `motorcycle helmet` 12 of 12 are
    cycling and **construction safety helmets from £3.68**, `electric bike` 12 of 12 kids'
    bicycles, `robotic lawn mower` 10 of 10 corded mowers, `summer tyres` and `winter
    tyres` a boat trailer's jockey wheel.
  - The owner's words: `banks` asks «which do you mean: power banks, water banks, money
    banks, vibes banks, piggy banks, river banks»; `bank` shows nothing (too broad);
    `power bank` 38, `ring` 141,615 and `watch` 1,853: no wrong card among the first 12;
    `cable`, `bed`, `suit`, `charger`, `speaker`, `light` alike; of 104 titles carrying
    "bank", 30 are "Banks" T-shirts and 28 piggy banks, none shown as a power bank.
  - In the whole catalogue, 177,380 products take their kind from the title alone, 96,330
    from the type or the shelf, 253,620 have none; 97.5% sit on a path of Google's, 1,156
    on a shelf Google has no name for.
  - **What the check cannot see:** a wrong product on an aisle that may hold its kind (the
    fixings read as a hammer, a baby comforter as a duvet) is flagged by nothing; such
    ones show only in the examples of what the rule changes.
- **Put to the owner 05/11:** (1) deploy the main-kind rule as it is, or first fix its
  few wrong ones (kids' backpacks, swimsuits, rings as dresses); (2) the same rule for a
  kind the shelf names (388 products, measured above); (3) when the narrower kind has no
  product (motorcycle helmet), show none instead of the broader kind. Answered «Πρώτα το 1
  μετά το 2» (above); (3) not answered yet.
- **How the logs were read:** `get_job_logs` with `return_content` and a `tail_lines`
  above the log's length saves the whole log to a file when it is long
  (`/root/.claude/projects/.../tool-results/`); the logs' own host
  (`results-receiver.actions.githubusercontent.com`) is blocked from a session.

## Before (2026-11-03/04): the main kind only, built; the owner asked for the end-to-end check

- **Which branch.** Start from the session's branch `ccr-9826870f-qkgl6s`. Deployed: all
  up to `4b5497b` (run `41324998201`). **Committed, not deployed** (deploying is the
  owner's word, a push to `ccr-1361f1a7-dcpo60`; it prepares the catalogue again): the
  main kind only (`concept_understanding.py`), with its tests and these notes. The live
  check (`live-photos.yml`, session's branch only) now also reads "tablet" and the search
  box's suggestions.
- **The owner's word (03/11).** «Στα tablets .. tablet... Βγάζει και χάπια... Εφόσον το κύριο
  είδος είναι tablet ... αυτό πρέπει να συμβαίνει γενικά παντού» (read as: a search for
  tablets must not show pills; the main kind only, everywhere), and «έλεγξε αν υπάρχουν
  προτάσεις κατά την πληκτρολόγηση». Also asked: is `AWIN_PUBLISHER_ID` still needed? No:
  the account is found from the token (`fetch_offers.find_publisher`), unless the token
  reaches more than one publisher account.
- **Read on the live site** (run `41621931827`): "tablet", "tablets", "ipad", "android
  tablet" and "vitamin tablets" gave the same 131 products: one tablet (Hannspree Lumo,
  the Recommended) and eleven InStock UK pills among the first twelve (toothpaste,
  mouthwash, electrolyte, chromium, green tea, biotin tablets). **The search box's
  suggestions work**: `/suggest.json` holds 1,978 names; "tab" lists table, table lamp,
  tablet, table legs, tablet screen protectors...; "κα" καλώδιο, καρέκλα, κάλτσες...; the
  list and the ghost completion show on desktop and phone (local preview, Chromium). 261
  of 261 photos loaded.
- **Why** (the server's kind report): 72 of the 190 tablets got their kind from their title
  alone; their shop's shelf ("Vitamins & Supplements", "Mouthwash", "Toothpaste", "Fish
  Food") names nothing PicWise has a kind for. The aisle rule of 2026-10-25 read only
  categories starting with an aisle of Google's, and computed the departments an aisle
  holds from Google's shelves, where homonyms put computers in every aisle ("Toners",
  "Highlighters", "Fertility Tests & Monitors", every "Cases" as phone cases).
- **Built** (`docs/PICWISE_DECISION_CONTRACT.md`, "The main kind only"): `_AISLE_HOLDS`,
  the departments each of Google's 21 aisles may hold, written down; `_shelf_aisles`, a
  shop's own shelf found among Google's shelves by its name (US spelling), or by its last
  word when it has two or more; `_aisle_may_hold` reads both. Checked against Google's
  file: only 32 homonym shelves are refused. Seen on titles: the pills of the live site
  are doubtful; tablets on "Tablets", "Computers & Tablets", "E-Readers", "Electronics",
  Google's "Tablet Computers" or with no category keep their kind; a security camera on
  Home & Garden too (AV added there). Changed with it: body jewellery is no barbell (a
  test that pinned the opposite was rewritten).
- **Not measured**: how many products of each kind the rule takes away on the server's
  catalogue. The deployment's log prints it ("Kinds that may be wrong in the prepared
  catalogue": "made doubtful by their aisle, per kind"); read it after the deployment, and
  the live check again ("tablet").
- **Tests.** `tests/test_picwise_main_kind_only.py` (4), `tests/test_picwise_title_on_another_aisle.py`
  (8). Every module but the 54-minute one: 280 pass; `test_picwise_kinds_from_the_shops_types` failed once (a sauna suit read as a suit: the table had clothing in sporting goods) and passes after `92fd939`; two fail as before this work (`..._canonical_vocabulary_registry_stage2`, `..._search_index_generated_blind_stage4`); `test_picwise_learning_stage7b` stopped at the 20-minute limit (it loads none of the changed code). After `92fd939` the 8 modules that read kinds pass.
- **The owner's next request (04/11), the first thing of the next conversation**: «Θέλω να
  μάθω ποια προϊόντα δημιουργούν μπέρδεμα στην αναζήτηση.. όπως τα tablets... Banks...κτλ
  δηλαδή που μπορεί να μπερδευτεί το ευρετήριο και να βγάζει ακατάλληλα προϊόντα.. θέλω
  έναν ολοκληρωμένο έλεγχο από άκρη σε άκρη». Asked before whether all categories had been
  checked: only Google's 5,595 categories and subcategories were (the table refuses 32
  homonym shelves, nothing else); the 528,518 real products, which only the server holds,
  were not. Proposed to the owner, not yet approved: a read-only check on a copy of the
  server's prepared catalogue, on GitHub's runner (as `server-cap.yml` did; it needs a push
  of a workflow to `ccr-1361f1a7-dcpo60`, so the owner's word first; nothing on the site
  changes). What it should print, with the main-kind rule of `cdd1eb3`/`92fd939` and
  without it: per kind, the products whose kind comes from the title alone, grouped by
  the shop's shelf, with examples; the products the rule takes away; the words that name
  more than one thing ("tablet" pills, "bank" (power bank, piggy bank, money bank),
  "mouse", "monitor", "toner", "case", "cable", "bed", "suit", "pad", "charger", "stand",
  "light", "speaker", "watch", "ring", "chain", "drill"...), each with the shelves its
  products come from; and, for every kind's search, its first page on the live site
  (`live-photos.yml` can read every kind's search). Then the owner decides what to fix,
  and whether to deploy the main-kind rule (not deployed yet).
- **Next, in order**: the audit above; the owner's word to deploy the main-kind rule; then
  the deployment's kind report and the live check. Then as before: "bean bag" as a kind,
  the Awin applications, the trending searches' source.

## Before (2026-11-01, afternoon): photos, the offer Recommended without a barcode

- **Which branch.** Start from the session's branch `ccr-9826870f-qkgl6s`. **Deployed:
  all up to `4b5497b`** (owner: «Ναι ανέβασε τα στο server»): run `41324998201`, success,
  16:11-16:24 UTC, release `20261101T161114Z-4b5497b`; 528,518 products from 81 shops
  prepared again (peak memory 7.9 GB, 619 s); offers fetched again (94, of 30 shops, joined
  to 2, 2 codes); the photo check started in the background ("photo check now:
  activating", "photos gone: not checked yet"), its timer next at 04:40 UTC; the site
  active since 16:22:14 UTC, its memory 5,393 MB; 15 of 15 pages and 12 of 12 searches
  answered (none of the 12 with an offer, as before). `4511a44` (a read-only check of the
  live site) runs only on the session's branch.
- **Seen on the live site after the first photo check** (the read again, run
  `41331736477`, 17:29 UTC): **237 of 237 photos load** (before: 19 of 244 failed;
  InStock UK 87 of 87, before 82 of 100). The 27 searches show 585 fewer products, 2.0%
  (29,073 to 28,488), almost all InStock UK's: "bag" 843 to 648, "camera" 401 to 276,
  "craft bag" 30 to 5, "bedding" 755 to 740; "bag" now recommends another product (the
  one of the owner's screenshot, whose photo was gone, is out). **"garden furniture" and
  "diamond earrings" now show an "On offer" Recommended** (Gardenista's £143.97 bundle;
  Finediam's £897 earrings, from "FineDiam Diamond Jewellery - Flat 23% OFF", to 02/11).
  How many photos the server found gone in all, and how long the check took, are not
  known here: the next deployment's log prints its summary lines and "photos gone".
- **What the owner saw (01/11, on the phone).** «bean bag»: no offer, and a broken photo
  on the Recommended («έχω παρατηρήσει ότι και σε άλλα προϊόντα η εικόνα είναι χαλασμένη»);
  «το recommended όταν υπάρχει προσφορά πρέπει να δείχνει την προσφορά»; then, of the
  broken ones: «Όταν το προϊόν δεν φέρνει φωτογραφία δεν πρέπει να εμφανίζεται... Στις
  περισσότερες περιπτώσεις είναι not found» (the shop's page said "Page not found").
- **Read on the live site** (`.github/workflows/live-photos.yml` →
  `.github/scripts/live_photos.py`, GitHub's runner, run `41313109104`; read-only; to read
  again, change its "Read:" line and push to the session's branch). 27 searches, 12 cards
  each: 244 photos, **19 gone (HTTP 404, with or without a Referer: links to nothing):
  18 of InStock UK's 100, 1 of Lets Buy Books'**; every other shop's loaded; all on
  cdn.shopify.com. Offers show and the Recommended reads "On offer" in "bean bag chair"
  (Ready Steady Bed), "garden cushion", "outdoor cushion", "pillow" (Gardenista), "bedding"
  (Cottsbury); **not in "garden furniture" and "diamond earrings"**, where the products on
  offer carry no EAN/GTIN. «bean bag» reads only "bag" ("PicWise could not match: bean"):
  PicWise's kinds have no "bean bag" (Google's taxonomy has "Bean Bag Chairs"), so no bean
  bag was in its results. Also seen: "bedding" shows Gardenista's cushion covers on offer
  (a kind read wrong, older than offers, put forward by them).
- **Built (not deployed):**
  - **The offer Recommended without a barcode** (`2dfce17`): of the products on offer,
    the one nearest the middle of their prices, one with an EAN/GTIN first, and when none
    has one, the nearest of them all. Fewer than three products: still none.
  - **Products whose photo is gone are not shown** (`e69b2ed`):
    `deployment/server/check_photos.py`, run by `picwise-photos.service` every night at
    04:40 UTC (`picwise-photos.timer`) and by each deployment in the background, asks every
    photo of the prepared catalogue (HEAD over kept-open connections, a GET of one byte
    where HEAD is refused, redirects followed; at most an hour a night; never asked first,
    then unread, gone ones again after a week, the rest after two weeks; 16 at a time),
    keeps the answers in `/srv/picwise/shared/photos/photos.sqlite3` and writes the gone
    ones (HTTP 404 or 410 only; no answer, refused, 429 or 5xx are asked again, never
    called gone) to `/srv/picwise/shared/photos/gone.json`. The site reads it
    (`PICWISE_GONE_PHOTOS_FILE` in `picwise-web.service`; `picwise_providers.product_photos`,
    looked at every 60 s) and both search catalogue paths (`state._prepared_search_catalogue`,
    `state._search_catalogue`) leave those products out: not shown, counted or recommended.
    The preparation keeps every product (`prepare_feed_catalogue` builds its catalogue
    with `leave_out_gone_photos=False`), so the check can ask again.
  - **In the browser, a card is seen only once its photo has loaded** (owner, after the
    first build: «από σκανάρισμα σε σκανάρισμα μπορεί να υπάρξει στο ενδιάμεσο αλλαγές ...
    να μην μπορεί να εμφανιστεί ένα προϊόν αν δεν έχει φωτογραφία στο ui»):
    `browser_lists.HEAD_SCRIPT` sets load and error listeners before any photo exists;
    cards are `visibility:hidden` under `pw-photo-guard` until `pw-photo-ok`, and
    `display:none` with `pw-no-photo` (a 404, or a photo of no size). Their place is kept
    while the photos load. Seen in Chromium on the local preview with photos answering
    after 1.5 s and one 404: all four hidden while loading, three shown, the 404 one never.
    A browser without JavaScript, or without `closest`, shows the cards as before. The deployment log prints the photo timer, whether a check is running,
    its last summary lines, and "photos gone: N of M" once the file exists.
  - Not measured yet: how long the first check of ~528,000 photos takes on the server, and
    whether Shopify's CDN slows it (429s are asked again the next night). After the
    deployment, read the live site again (the check above) to see InStock UK's dead photos
    gone, and the next deployment's log for the photo summary. The first search in each
    worker after a new list is written rebuilds the search catalogue (some seconds), once
    a night.
- **Tests.** `tests/test_picwise_product_photos.py` (17), `tests/test_picwise_offers_first.py`
  (19), `tests/test_picwise_live_photos.py` (4). Every module but the 54-minute one, on
  `e69b2ed`: 279 pass, two fail as before this work (`..._canonical_vocabulary_registry_stage2`,
  `..._search_index_generated_blind_stage4`), `test_picwise_learning_stage7b` stopped at the
  20-minute limit (it passed in 1,147 s earlier the same day; it loads none of the changed
  code: `picwise_learning` reads no provider or page module). With the browser guard after it, the 10 modules that read the
  pages, photos or offers pass.
- **Next, in order**: "bean bag" as a kind
  (a vocabulary change, `picwise_nlu`), the application text and Awin applications, the
  trending searches' source, the first search after a restart.

## Before (2026-11-01, morning to midday): offers first deployed, then the voucher fix

- **Which branch.** Start from the session's branch `ccr-9826870f-qkgl6s`. Offers first
  and the Recommended on offer (`6836bbe`, `1d1c880`, `3bf18d8`, `9f6e3c4`, with these
  notes `d4c2a40`) are **deployed** (owner: «Ναι ανέβασε στο server»): run `41295172671`,
  success, 09:55-10:08 UTC, release `20261101T095518Z-d4c2a40`; the catalogue prepared
  again, 528,524 products from 81 shops, peak memory 7.9 GB, 620 s; the site active since
  10:06:16 UTC, its memory 6,212 MB; offers fetched again: 94 live, of 30 of the 85 shops,
  joined to 2, 2 voucher codes; 15 of 15 pages and 12 of 12 searches answered. **The
  voucher fix** (below, `7e1cbce`, with these notes `001b2d8`) **is deployed too** (owner:
  «Ναι ανέβασε το στο server»): run `41305061462`, success, 12:08-12:24 UTC, release
  `20261101T120852Z-001b2d8`; 528,518 products from 81 shops prepared again (peak memory
  7.9 GB, 736 s); the site active since 12:21:45 UTC, its memory 6,210 MB; offers fetched
  again (94, of 30 shops, joined to 2, 2 codes); 15 of 15 pages and 12 of 12 searches
  answered, **none of the 12 showing an offer now**: "kettle" and "mouse" have the cards of
  before. Offers now show only for the shops whose offers remain (Gardenista, Game Over,
  Ready Steady Bed, Cottsbury, a few Finediam and Optimum Nutrition products), none of
  which the 12 searches reach. Nothing is waiting to be deployed.
- **What the deployment showed, and the fix.** Of the 12 searches the deployment prints,
  two show offers. "kettle": the Recommended reads "On offer", Geepas's "1.7L Electric
  Kettle & 4 Slice Bread Toaster Vintage Set Retrovive" at £109.99, then three Geepas
  kettle-and-toaster sets at £22.99, £28.49 and £29.99 ("Offer"), all from Geepas's "Kettle &
  Toaster Set 10 OFF" (before: the Recommended was Geepas's "Opus Collection" set at £33.99,
  "Mid-priced", then kettles from £12.74). "mouse": Craft Buddy's "Squeak the Mouse A6 Stamp
  Set" reads "Offer" (it was there before as "Lowest price": a wrong product for "mouse",
  older than this work). **Geepas's offer is a voucher Awin gave without its code**, as for
  every programme the account is not joined to: a shopper could not have the discount. The
  offers check of 01/11 (run `41289100066`, up to 3 offers a shop) shows it was most of
  them: of the 53 offers printed, 32 covered products as deployed, 23 of those vouchers
  without their code. **The fix** (`product_offers.py`): a voucher covers a product only
  with its code; a promotion needs none. Of the 53, 9 still cover products: Game Over's and
  Gardenista's vouchers with their codes, the "10% off your first order" promotions of Game
  Over, Gardenista and Ready Steady Bed, Cottsbury's "15% off everything", Finediam's
  "Diamond Jewellery - Flat 23% OFF" (to 02/11), an Optimum Nutrition bundle, Game Over's
  "Pick 2". With it, "kettle" goes back to the order of before. Left out with the rest:
  Susan Caplan's voucher, whose title names its code ("using code SC15OFF"); reading a code
  from a title could be a later step. More codes come with each programme that accepts
  PicWise.
- **The owner's word (01/11).** «Ανά προϊόν... Όταν ψάχνει ένας πελάτης ένα προϊόν ή μία
  κατηγορία υπάρχει προσφορά σε αυτό το προϊόν ... προϊόντα με προσφορές πρώτα»; asked
  whether that changes "cheapest first": «Ένα προϊόν με προσφορά θα μπαίνει πρώτα από το
  φθηνότερο»; then «Μήπως θα ήταν πιο σωστό το recommended να προτείνει το offer?», and,
  given three choices with the advice to keep the Recommended neutral: «Εάν υπάρχει
  προσφορά να προτείνει την προσφορά».
- **What is built** (`docs/PICWISE_DECISION_CONTRACT.md`, "Offers first"; PROJECT_RULES §5):
  - **Which offer covers a product** (`src/picwise_providers/product_offers.py`): one of
    the product's own shop (the feed's `merchant_id`), live now by its own dates, stating a
    discount (a percentage, "£15 off", "10 off", half price, buy one get one...), not addressed to publishers (commission),
    and either on the whole shop ("15% off everything", "10% off your first order") or on a
    kind every word of which is in the product's title ("10% off kettles"). "Up to" and
    "selected" cover nothing: which products, the offer does not say. Free delivery covers
    nothing (no price stated off the product). Checked on Awin's real titles of 31/10.
  - **The order**: the Recommended; then the products on offer, cheapest first; then the
    rest, cheapest first; "More" goes on in that order. Without offers, as before.
  - **The Recommended**: when the answer holds three products or more and a product on
    offer carries an EAN/GTIN, the product on offer with a code nearest the middle of the
    offer products' prices (`_offer_recommendation`); its card reads "On offer" (not
    "Mid-priced for this category", which would not be true) and the page says "The
    Recommended is on offer: of the products on offer, the one nearest the middle of their
    prices." Otherwise as before; fewer than three products still have none. "Lowest
    price" is then measured against the middle price of the whole answer.
  - **The card**: "Offer" instead of "Lowest price"; the offer in the shop's words, "until
    31 Dec", its code where Awin gives one (joined programmes only: 2 of the 30 shops with
    offers), "Offer terms". The query line says "offers first, then cheapest first".
  - **The pages**: the home page's words and "how PicWise chooses", About, the Affiliate
    Disclosure (an "Offers" section: PicWise is paid nothing to show an offer or to put it
    first; and "Which shops" made true: a commission only from the shops that accepted
    PicWise into their programme, the others shown by the same rule).
  - **The site reads the offers file** through `PICWISE_OFFERS_FILE`
    (`deployment/server/picwise-web.service`, installed by every deployment), the file
    `fetch_offers.py` writes every night; it looks again for a new one every 60 s. Without
    the file, no offers and the order of before. Measured: 91 ms at most over 100,000
    products, about 2 ms over 2,000.
- **Tests.** `tests/test_picwise_offers_first.py` (16) pins the offer rules, the order, the
  Recommended on offer, its fallback without a code, one product on offer, an answer of two
  products and the pages; with the voucher fix, 18. All 281 modules run one by one, four
  at a time, on `9f6e3c4`: 277 pass, and `test_picwise_search_graph_contracts_stage1db1`
  too once committed (it fails only while `reference.py` has uncommitted changes); two fail
  as before this work (`test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`, the same way on the code before it);
  `test_picwise_search_index_blind_evaluation_stage6a` did not finish within 20 minutes (54
  minutes alone last time, 12 of 13, the old mismatch of the section below); it loads none
  of the changed code. The voucher fix changes only how the offers file is read: the 14
  modules that read offers or the pages pass with it.
- **Seen on the local preview** (fictional shops): "kettle", Store Two's "10% off kettles"
  on its three kettles: the Recommended is its £19.99 kettle ("On offer"), then its £12.74
  and £33.99 ones ("Offer"), then the cheapest of the rest ("Lowest price").
- **Next, in order**, as before: the application text and the Awin applications (the offers' codes come only from
  joined programmes), the trending searches' source, the first search after a restart.

## Before (2026-10-31, night, to 2026-11-01 morning): the design deployed, the offers fetched

The design of 31/10 is built and deployed with the pages (owner, 31/10: «Υλοποίησε τα όλα
και ανέβασέ τα στο server και θα κάνω τους λογαριασμούς αργότερα»).

- **Which branch.** `ccr-1361f1a7-dcpo60`, the branch the server deploys from, now holds
  everything: the pages (`6ba081d`, `b7adf77`), the design proposal (`578bc49`,
  `1b83d18`) and the design built (`f529b6f`, `901bfb3`, `ce8ba74`), pushed together and
  deployed by run `41215460767` (success, 15:34-15:48 UTC: release
  `20261031T153406Z-ce8ba74`; the catalogue prepared again with the new code, 528,134
  products from 81 shops, peak memory 7.9 GB, 718 s; the site healthy at 15:46:14; its
  memory 6,187 MB; 15 of 15 pages answered with no failure and the 12 searches show the
  new cards, through https://picwise.subby.cloud as from the server itself). Since then,
  **deployed on 01/11 by run `41289100060`** (owner: «Ναι ανέβασέ το»; release
  `20261101T083000Z-ca01c61`, success: 528,524 products prepared, the site healthy at
  08:40 UTC, 15 of 15 pages and 12 of 12 searches answered): the trends panel's
  rewording (`aef1ff7`), the Awin offers check and **the nightly fetch of the offers**
  (`ca01c61`). **Start the next conversation from the session's branch
  `ccr-9826870f-qkgl6s`**: it holds all of that and these notes (documents only after
  `ca01c61`). `ccr-60773189-pesaft` is behind both; nothing is waiting on it.
- **What the site shows now** (`src/picwise_surface/reference.py`, `browser_lists.py`,
  `trends.py`; pinned by `tests/test_picwise_design_2026_10_31.py`, 30 tests):
  - **Cards, symmetric**: a square photo shown whole (`object-fit:contain`, 400×400 set
    before it loads: no layout shift, measured CLS 0), then the role, a title of at most
    three lines and the shop line at fixed heights, so every card of a row is as tall as
    the others and the prices and buttons line up. The price reads "£12.74"
    (`_display_price`: GBP, EUR, USD signs; any other text keeps its code). The button
    names the shop ("View at <shop>"; "View" on phones). The stock line rewords the
    labels' own fact for a shopper ("Listed as available by the shop"; never "in stock"
    for a flag that is the same on every row), and every card states its limitation
    ("... not verified by PicWise", after a not-new or no-description note in the
    labels' words). The owner's labels stay ("Recommended", "Mid-priced for this
    category", "Lowest price"). "4 of 45" also above the cards. Phones: two cards a row.
  - **One product alone** (owner, 31/10): the same card laid out on its own, "This is
    the only product PicWise found for this search in its shops.", with Shop, Brand,
    Product code (barcode, else the maker's part number, read from the shop's row by
    `picwise_app.app.single_product_code`) only when the shop gives them, and Delivery
    "See the shop's site" (PicWise holds no delivery data: the prepared file leaves it
    out). No "Lowest price" label, no "More".
  - **History and Favourites** instead of Login and Register: local storage only
    (`picwise.favourites.v1`, `picwise.history.v1`, `picwise.history.on`), no request,
    lines drawn as text; the buttons show only where JavaScript and storage work (a
    head script that only reads). **The history is off until the visitor chooses
    «Keep my searches»** in its panel, and «Stop keeping history» forgets it: a list
    kept on a device that the visitor did not ask for needs consent under UK PECR and the
    EU's ePrivacy rules, and asking first needs no banner. Favourites are kept by the
    heart on a photo, open through `/out/feed?...&src=favourites&rec=0`, and show the
    price "when saved". The privacy and cookie pages say all this.
  - **Home page**: "Find the product you want in UK shops", the "What is PicWise?" words,
    the box, and three lines on how PicWise chooses. **The trends panel is built and
    shows nothing**: `load_trends_panel()` returns None (`TRENDS_SOURCE_STATUS =
    "not_connected"`) until a real source writes its rows; tested on fictional rows.
  - **Footer**: About in, Demo and PicWise Reference out (the routes still answer).
- **Tests.** All 278 modules run one by one, four at a time: 273 pass. Two did not
  finish within 20 minutes under that load and were run again alone:
  `test_picwise_learning_stage7b` passes (10 tests, 23.5 minutes);
  `test_picwise_search_index_blind_evaluation_stage6a` (54 minutes) passes 12 of 13:
  `test_negative_broad_terms_are_included` expects "amazon" and "galaxy" among the broad
  terms that must match nothing, which `picwise_search_memory/blind_evaluation.py`
  (`_NEGATIVE_BROAD_TERMS`, unchanged since 25/05) does not hold: a mismatch older than
  this work, in files it did not touch; left as it is. Three fail, none because of this
  work: `test_picwise_canonical_vocabulary_registry_stage2`
  (`test_live_search_provider_and_surface_files_unchanged_in_this_stage`) and
  `test_picwise_search_index_generated_blind_stage4` fail the same way on the code
  before it; `test_picwise_search_graph_contracts_stage1db1` fails only while
  `reference.py` has uncommitted changes, as the gotchas say, and passes once committed.
  One more was already failing since 31/10 and is fixed: the truth test for weak
  availability read the home page's new description (the "What is PicWise?" words) as a
  stock claim; it now leaves the description out, as it does the tooltip.
- **The owner's word after the deployment (31/10, evening).** The trends are **searches,
  not sales** («μπορούμε να λέμε trend αναζητήσεις και όχι πωλήσεις»): the panel says
  "Trending searches in the UK this month" (`aef1ff7`, on the session's branch only, not
  deployed: the panel shows nothing yet, so it waits for the next deployment), and its
  source is Google's search data, not Merchant Center's best sellers (which Google gives
  to shops that sell, and whose terms limit showing it). Awin's offers are to be pulled
  now («πρέπει να τις τραβήξουμε»); **which product an offer is for is a later talk**
  («αυτό είναι άλλη συζήτηση»).
- **Waiting for the owner:**
  1. ~~The Awin token~~ **in GitHub's secrets since 31/10** (`AWIN_API_TOKEN`; the account's
     number is found from it, `AWIN_PUBLISHER_ID` not needed). **First read** (run
     `41226304997`): Awin answers `{data, pagination: {page, pageSize, total}}`, an offer
     `{promotionId, type, advertiser: {id, name, joined}, title, description, terms,
     startDate, endDate, status, url, urlTracking, dateAdded, campaign, regions: {all},
     categories, voucher: {code, exclusive, attributable}}`; 20,000 live offers read (the
     check's most; 7,571 vouchers, 12,429 promotions; 4,463 advertisers); **28 of
     PicWise's 85 shops have offers** (Geepas: mixer grinders, kettle and toaster set, air
     fryers; Finediam 23% off; Angel Barocco, EXG Pro, Craft Buddy Shop, Mint Outdoor,
     Optimum Nutrition, Game Over, Gardenista...), but **Awin calls the account joined to
     only 2 of them (Game Over, Gardenista), the only ones whose voucher codes it gives**:
     the applications to the shops matter for the offers too. Next: a nightly fetch on the
     server, asked only for PicWise's shops by their advertiser ids (the feed's
     `merchant_id`), so it is complete and quick; showing offers on the site, and which
     product an offer is for, is the owner's later talk.
     **Built and deployed (01/11, owner: «Οκ να φέρνει τις προσφορές των δικών μας
     καταστημάτων»):** `deployment/server/fetch_offers.py` (tests 12) run by
     `picwise-offers.service`, every night at 05:05 UTC (`picwise-offers.timer`) and once
     by each deployment; `AWIN_API_TOKEN` written to the server's environment file by
     `server-deploy.yml` (the site's own service never reads it). It writes
     `/srv/picwise/shared/offers/offers.json`, served to no one: per shop with an offer, its
     name, whether the account is joined, and its offers live now by their own dates, with a
     code and a tracking link only where Awin gives them. **First fetch: 94 live offers, of
     30 of the 85 shops in the feed, joined to 2 of them, 2 voucher codes.** Next, the
     owner's: how offers show on the site, and which product an offer is for.
  2. **A source for the trending searches**: Google Ads (free without a campaign) with a
     manager account and an API developer token with Basic access, by application
     (Keyword Planner's monthly searches; Explorer access excludes keyword planning), or
     the Google Trends API (alpha, by application, often unanswered). Search Console is
     still worth making for the site.
- **Next, in order** (each shown to the owner before it is built on):
  1. The Awin offers check, as soon as the secrets exist; then the nightly fetch.
  2. The application text (`docs/awin_application_message.md`) and the presentation of
     the business: the site is live with its pages and design now.
  3. The trending searches' real source, once the owner's Google access exists:
     `trends.load_trends_panel`.
  4. Structured data (price range and number of shops, no ratings) on the pages given to
     Google, when the first of them is built (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`).
  Then the owner applies again to the 6 Awin advertisers that rejected them (SharkNinja,
  Beldray, Gtech, Boots, Road Angel, Mattress Online).
- **Still open**: the first search after a restart (16.5 s, so after every deployment;
  not touched here: loading the catalogue in every worker at once could pass the site's
  memory ceiling, and that needs measuring on the server first); the deployment's line
  "nothing on 80 or 443" and `compare_with_vercel.py` (the server against itself);
  Vercel's previews (PR #13); a key scan still shown another host key (reported only).

## Before (2026-10-31, evening): the handover to the conversation that built the design

The owner moved to a new conversation, this one having grown long and slow («μεγαλώσει
και τραβάει πολύ»). Read this, then the section below (the owner's plan of 31/10).

- **Which branch.** `ccr-1361f1a7-dcpo60` is the work branch the server deploys from: at
  `b966aa1` plus this note, which is what the site runs. `ccr-60773189-pesaft` holds the
  same **plus 4 commits not deployed, by the owner's word** («όλο μαζί θα ανέβει»):
  `6ba081d` and `b7adf77` (the pages: terms, privacy, cookies, affiliate, contact, a new
  About page, the operator, the home page's title and description; tests pass) and
  `578bc49`, `1b83d18` (the design proposal, a document only). Start from
  `ccr-60773189-pesaft` and keep new work on the session's own branch. Push nothing under
  the deploy paths (`src/**`, `api/**`, `tools/**`, `assets/**`, `data/**`, `wsgi.py`, ...)
  to `ccr-1361f1a7-dcpo60` until the owner says everything goes up; then it all goes in
  one push, and the deployment runs.
- **The last thing done: how the owner makes the accounts without a subscription**
  (owner: «Ωραίο γράψε μου πώς φτιάχνω τους λογαριασμούς αλλά δεν θέλω να πληρώσω θέλω να
  πω συνδρομητικά»; the «Ωραίο» was for the redone trends panel). Sent, in this order:
  1. **Google Search Console** (free, no card): a Domain property `picwise.subby.cloud`,
     its TXT record added in Vercel's DNS (subby.cloud's name servers are Vercel's; name
     `picwise`, as for the A record), then Verify.
  2. **Google Merchant Center** (free, no card): business "PicWise", country Greece (the
     owner's seat), the site; true details only (PicWise sells nothing itself). Then look
     for "Best sellers" (Growth, or Analytics → Market insights) and say whether it shows.
     Told honestly: Google gives that report to retailers in free listings or Shopping
     ads, so a comparison site may not get it; Google's terms are to be checked before
     its figures are shown on the site.
  3. **Google Ads, only for the number of searches** (no subscription; it charges only for
     ads run): Keyword Planner's numbers usually need a payment method on file, ranges
     ("100–1,000") without one; Expert mode, "create an account without a campaign",
     manual payments if offered, never a campaign. The manager account and the API's
     developer token (Basic access, by application) later, if the owner decides.
  4. **Google Trends API**: interest 0–100, no numbers; alpha, by application.
  Proposed: 1 and 2 now, Ads later. Whatever key or code the owner is given goes into
  GitHub's secrets, never into the chat. **Waiting for the owner:** the accounts, and
  whether Merchant Center shows Best sellers.
- **Next, in order** (each shown to the owner before it is built on):
  1. Ask whether to build the design (`docs/design/picwise_design_proposal_2026-10-31.html`;
     the owner said «Ωραίο» to the redone panel and nothing against the rest); then build
     it in code on the session's branch: symmetric cards, the single product's own layout,
     History and Favourites in the browser instead of Login/Register, the trends panel
     (shown only from a real source: no invented rows on the site), the footer.
  2. The application text (`docs/awin_application_message.md`: the site is live now) and
     the presentation of the business.
  3. The trends' real source, once the accounts exist.
  4. Awin's offers on the cards: needs an Awin API token in GitHub's secrets; only offers
     valid by Awin's own end date.
  5. One deployment of everything, when the owner says.
  Then the owner applies again to the **6 Awin advertisers that rejected them earlier**
  (tab "Rejected", "+ Join"; owner's screenshot of 31/10): SharkNinja, Beldray, Gtech,
  Boots, Road Angel, Mattress Online. Each sends a product feed and fills a gap the
  measurement found; the reason was not shown, likely the site then still being built.
- **Still open from the move** (section "Next conversation (from 2026-10-30)" below): the
  first search after a restart (16.5 s); the deployment's line "nothing on 80 or 443" and
  `compare_with_vercel.py` (now the server against itself); Vercel's previews (PR #13, no
  answer yet); a key scan still shown another host key (reported only).

## Now (2026-10-31, afternoon): the owner's plan after the move

The site is live from the server (below). The owner's decisions of 31/10:

- **The catalogue stays as it is**, «ποιοτικός και εξακριβωμένος»; no new network for now
  (Shopify's catalogue pays no commission; a title cannot safely give the held rows a
  kind, measured; another network's similar titles would not either).
- **No minimum of shops per kind, and none of products**: «Καταργείται το όριο των τριών
  καταστημάτων ανά είδος. Το ευρετήριο μπορεί να εμφανίσει και ένα προϊόν εάν δεν
  υπάρχουν άλλα σε αυτή την περίπτωση το εμφανίζει διαφορετικά (δεν θα βγει μία καρτούλα
  στη μέση.)». Written into `PROJECT_RULES.md` (§2, §13), the Google pages spec (the
  gate) and the Decision Contract; the single product's own layout comes with the new
  design.
- **Before applying to shops or networks** («Για να κάνουμε αιτήσεις θα πρέπει να
  έχουμε»): (a) a design, (b) a UI wholly compatible with Google's standards, (c) cards
  laid out symmetrically, with what Google asks of each product; every page filled in
  (terms of use, what the site is, the operator); an application text and a
  presentation of the business; then Awin's offers (vouchers, promotions) in a field of
  the card; the month's 10 trending purchases under the home page's search box, from a
  Google channel (true to its source, as decided on 16/10); favourites and search
  history **without a login, kept in the visitor's browser** (owner: «συμφωνώ στο 6»).
- **The operator, given by the owner for the pages:** their sole business in Piraeus,
  Greece, with its VAT number; the contact stays `contact.picwise@subby.cloud` (owner's
  choice, 31/10; their Gmail address never on the site, as the tests pin).
- **Nothing is deployed until everything goes up together** (owner, 31/10: «Δεν θα
  ανεβάσεις τίποτα ακόμα όλο μαζί θα ανέβει»). So the code since `6ba081d` (the pages,
  written, tests passing, shown to the owner: «πολύ ωραία γράψαμε τους όρους») is
  **only on `ccr-60773189-pesaft`**, never pushed to `ccr-1361f1a7-dcpo60`, where a push
  of `src/**` deploys. Login: put to the owner what it would add (favourites and history
  on every device, price alerts by email) and cost (personal data, GDPR, security);
  their answer: search history yes, no login for now.
- **The design proposal, sent to the owner (31/10; `docs/design/picwise_design_proposal_2026-10-31.html`,
  for approval, nothing built):** symmetric cards (same height, a square photo that is
  not cut, at most 3 lines of title, price and button on one line) instead of today's
  84-pixel photo strip; History and Favourites (in the visitor's browser) instead of
  the Login and Register buttons, which do nothing; the month's 10 trends under the
  search box, empty until a real Google source is found; one product on a layout of its
  own; the footer without "Demo" and "PicWise Reference", with "About"; a table of what
  Google asks of a product and what is missing (structured data with the price range and
  the number of shops for the pages given to Google; brand and code on the single
  product's layout; the 16 s first search after a restart). The examples are the
  server's real "kettle" cards (4 of 75).
- **The trends, redone (owner, 31/10: «Αυτό το φτωχό που έχεις κάνει με τα κουμπάκια δεν
  βοηθάει πουθενά φτιάξε ένα ωραίο πάνελ ... δημοφιλείς αγορές για αυτό το μήνα παράδειγμα
  apple iphone ... Philips air fryer ... αν μπορείς να αντλείς και αριθμό αναζητήσεων»):** a
  panel "Popular in the UK this month" in the same file: rank, a coloured icon per
  category, Google's relative demand as a 5-step scale, rising/falling/new against last
  month, searches a month, and PicWise's offers ("27 offers · from £699", or "Not in our
  shops yet", never an empty search); invented numbers, labelled as an example. Real
  sources found: **Google Merchant Center's best sellers** (Merchant API Reports v1:
  product clusters such as "Google Pixel 7" ranked by estimated units sold on Google,
  per country and category, weekly or monthly, with relative demand, previous rank and
  the change), **Google Ads Keyword Planner** (approximate monthly searches; ranges
  without ad spend, by third-party accounts; needs an account with a payment method and
  a developer token with Basic access), **Google Trends API** (alpha, by application).
  Both need accounts of the owner's; none created yet.
- **Order put to the owner and worked through:** the pages (true and complete, a page
  "About PicWise", the home page's title and description, which still said "Reference
  — Buying Decision Preview" and "provider integrations are being configured"), shown
  to the owner before any deployment; then the design proposal; then the presentation;
  the trends' source; Awin's offers; favourites and history.

## Next conversation (from 2026-10-30): move the site to the real server -- start here

**The owner (30/10): «2 μεταφορά του site στον κανονικό server και πάμε να ξεκινήσουμε από
άλλη συζήτηση».** Before it: «Να προχωρήσεις με το 3 και να σταματήσουμε εκεί μετά την
υλοποίηση του δεν με ενδιαφέρει επιπλέον απασφαλμάτωση το επόμενο βήμα θα είναι να
προσθέσουμε επιπλέον καταστήματα από άλλο δίκτυο και να περάσουμε το site στο κανονικό
server». So: **first the site moved to the real server, then the shops of another
affiliate network.** Items 1, 2 and 3 are built and measured, nothing deployed (below); no
more debugging for now: the reading errors found on 29-30/10 (section "After the buyer's
view", 4) stay as they are.

- **Where the work is:** `ccr-1361f1a7-dcpo60` (the conversation of 29-30/10 pushed its
  last commit there; its own branch `ccr-4f9ef4ee-j1nafx` holds the same files). Bring it
  in first. A push to it needs the session in **"Accept edits"** (the mode menu beside the
  message box): "Auto" refuses it as a deployment, `[skip actions]` notwithstanding.
  A push there of anything in `server-deploy.yml`'s `paths` (`src/**`, `tools/**`,
  `api/**`, `assets/**`, `data/**`, `wsgi.py`, `deployment/server/**`,
  `deployment/bot/**`, the pin, the workflow itself) **deploys**, unless the head commit
  says `[skip actions]`; a push of `server-shops.yml` runs the shops' round at once (a
  second round the same day only on the owner's word).
- **Where things stand:** the live site is still Vercel's (`picwise.subby.cloud`). The
  server (OVHcloud VPS-4, London, Ubuntu 24.04) runs the site under gunicorn on
  `127.0.0.1:8016` only, so nothing reaches it from the internet; ufw lets 22, 80 and 443
  in. Its code is the deployment of 26/10 (run `40355492889`); the shops' round and the
  catalogue's preparation (04:17 UTC) run each night; the measures read its catalogue
  through `server-cap.yml`.
- **The steps, each on the owner's word:**
  1. **Question 1:** `server-deploy.yml` and `server-shops.yml` compare the key a key
     scan (`ssh-keyscan`) is shown with the pin, and a key scan has been shown another
     key since 27/10 (section "Now (2026-10-27/28)"), so they stop at their first step;
     `server-setup.yml` (run from `ccr-baaad713-r3uvvs` only) logs in with `accept-new`,
     checking no pin. `server-night.yml` and `server-cap.yml` check the key a login's
     first step is shown against the pin, and work: the same check to the three. Editing
     `server-deploy.yml` deploys the work branch, so that edit is the deployment itself
     and waits for the owner's «ναι».
     **Prepared (30/10, the conversation of `ccr-60773189-pesaft`; owner: «Ξεκινάμε με
     τη μεταφορά του site στον κανονικό server»), not yet on the work branch:** the three
     take the key a login's first step is shown and compare it with the same pin,
     strictly (no seal: the deployment sends the feed link); a key scan's key is only
     reported. `server-setup.yml` still runs from `ccr-baaad713-r3uvvs` only. Checked:
     `actionlint` 1.7.12 with shellcheck, clean; a dry run of the three connection steps
     with stand-in `ssh` and `ssh-keyscan` (the pinned key with a key scan showing the
     same key, another, or none; another key; no key), 15 cases as expected. Two commits,
     to reach the work branch **in two pushes**, so that only the deployment runs: first
     the round's and the setup's change with these notes (`[skip actions]`), alone; then
     the commit changing `server-deploy.yml` alone, without the skip, which deploys. One
     push of both would also start a round of the shops (its file is in the push's
     changes), a second one the same day. Both wait for the owner's «ναι» and the session
     in "Accept edits".
  2. **The deployment:** items 1-3 and everything since 26/10 reach the server; the
     night's preparation then also keeps the pool Google may be given from
     (`google_pool.json.gz`). After it: the deployment's own comparison of pages, and
     `server-night.yml` the next morning.
     **Done (owner's «ναι», 30/10; `0a48f1f` pushed alone with `[skip actions]`, no run;
     then `2584a8f` alone, run `41046682097`, 11:14-11:29 UTC, success):** the login's
     first step showed the pinned key; a key scan still the key of 27/10 (pin
     `59e8bfb6`). Release `20261030T111452Z-2584a8f`; the preparation 751.6 s, peak memory
     7.9 GB: 527,894 products, 81 shops; the pool Google may be given from 168,710 (25,306
     a category; none kept the night before, the first night). The site active, its
     memory 6,212 MB; disk 305 MB used, 191 GB free. Against Vercel: 10 of 15 pages the
     same, the server failed none; `/`, `/suggest.json`, `/search?q=kettle`,
     `/private-beta-readiness`, `/prepared.json` differ as expected (the new code, the
     larger catalogue); 0 of 12 searches show the same cards (the server's catalogue has
     every shop and the bot's types). Vercel adds `cache-control: public, max-age=0,
     must-revalidate`, the server none. Vercel also built a preview of the pushed commit
     (PR #13 is open from this branch to `main`), as for every push since 26/10; the live
     site was not touched. The owner, asked, did not answer whether to stop the previews.
  3. **The site public on the server: HTTPS and the domain.** A web server in front of
     gunicorn (TLS from Let's Encrypt); the domain of PicWise's own (the owner's to choose
     and to point at the server's address at the registrar; the address never in the
     repository); Vercel's `picwise.subby.cloud` until the switch. By `PROJECT_RULES.md`
     §13: the site's own search stays `noindex`; Search Console from the first day.
     **The owner (30/10): the domain stays `picwise.subby.cloud`** («domain name subby.cloud
     και ειναι υποτομεας το picwise μπορει να αλλαξει ονομα αν αντιμετωπισουμε προβλημα»;
     §8 holds), `subby.cloud` bought at **Papaki**; «Θέλω να βλέπω live το site από το
     καινούργιο server». They meant to change the name servers: advised not to (they
     carry the whole `subby.cloud`, the Subby site and its email); only the record
     `picwise` changes, to an A record with the server's IPv4, typed by the owner at
     Papaki, never in the chat or a file. **Built:** `deployment/web/Caddyfile` (Caddy in
     front of gunicorn: the certificate from Let's Encrypt by itself, http:// to https://,
     HSTS of two years, HTTP/3 off since ufw keeps UDP 443 closed),
     `deployment/web/web_setup.sh` (`install`: Caddy from Ubuntu's own archive, 2.6.2,
     whose security updates unattended-upgrades applies; stopped while the domain points
     elsewhere; the Caddyfile checked by `caddy validate` before anyone touches the DNS;
     `open`; `status`, the certificate's log lines only, no visitor's address) and
     `.github/workflows/server-web.yml` (runs on a push of itself or `deployment/web/`;
     waits up to 60 minutes for the record, asking the zone's own name servers every
     20 s; then opens the site and checks it over HTTPS from outside: the certificate,
     the pages and their robots tags, http:// to https://, and who answers the runner's
     own resolver, Caddy or Vercel). Checked: `actionlint` with shellcheck, clean; dry
     runs with stand-ins: the wait 7 cases, `web_setup.sh` 13 checks. **First run
     (`41064935444`, 13:38-14:39 UTC):** Caddy 2.6.2 installed, stopped, its file
     accepted; the record never changed in the hour: **the name servers of `subby.cloud`
     are Vercel's (`ns1.vercel-dns.com`, `ns2.vercel-dns.com`)**, so the zone's records
     are kept at Vercel and a change at Papaki does nothing; `picwise` answered with two
     of Vercel's addresses throughout. So: the owner adds the A record in Vercel's DNS
     (team Domains, `subby.cloud`) and removes `picwise.subby.cloud` from the project
     `picwise-concept`; never `subby.cloud` itself. The way back there: the A record
     deleted and the domain added back to the project. The workflow now first runs a
     short job (`look`) whose log is readable at once, and reads the name servers from
     the `.cloud` registry each time (`deployment/web/dns_state.sh`), so a change of name
     servers is seen too; dry runs 11 cases. **Live (31/10, run `41190899316`):** the
     owner added at Vercel (Domains, `subby.cloud`, DNS Records) the A record `picwise`
     with the server's IPv4, TTL 60, at about 10:02 UTC; the domain was **not** removed
     from the project: Vercel answers the record added by hand instead of its own. The
     wait saw it at 10:03:05, Caddy started, and at 10:03:25 HTTPS answered from the
     server with a valid certificate (Let's Encrypt `YE2`, 31/10/2026 to 29/01/2027,
     renewed by Caddy). From outside: `/` 200, `/health` 200 (X-Robots-Tag noindex),
     `/robots.txt` 200, `/search?q=kettle` 200 with `<meta name="robots"
     content="noindex">` but **16.5 s** (the first search after the restart; to measure),
     `/suggest.json` 200 noindex, `/no-such-page` 404, http:// 308 to https://, the
     runner's own resolver answered by the server. Every answer carries two `Server`
     headers (Caddy's and gunicorn's). `subby.cloud`'s other records (ImprovMX's MX and
     SPF for its email) untouched. **The way back to Vercel:** the A record `picwise`
     deleted at Vercel (within a minute, TTL 60). Earlier note, **the way back:**
     the old record put back at Papaki (Vercel still serves the site). Left for after the
     switch: `server-deploy.yml`'s line "nothing on 80 or 443" (editing it deploys);
     `compare_with_vercel.py` compares with `https://picwise.subby.cloud`, which is then
     the server itself; Search Console; Vercel's previews and its daily renewal.
  4. Then the shops of another affiliate network.
     **31/10, after the site went live:** the owner asked about registering with Shopify;
     Shopify's Global Catalog (UCP; open to every developer since its Spring '26 Edition,
     cross-merchant products and offers) pays no commission, Shopify Collabs is for
     creators applying brand by brand: **not taken** (owner: «Χωρίς προμήθεια τι να το
     κάνω?»); the bot's checks of Shopify shops need no account. Then, asked which
     network next («Ναι»), read from the networks' own pages and others (shopify.dev,
     caddyserver.com and DNS-over-HTTPS are blocked in this session): **Webgains** first
     for the UK (feeds in Google Shopping's format, as Awin's: id, title, link,
     image_link, availability, price, google_product_category, shipping; by URL or API;
     it names price comparison publishers among its own: Pricerunner, Lyst, uSwitch;
     such publishers are expected to meet merchants' minimum CPA); **CJ** when the US
     market opens (GraphQL product search, products of joined advertisers only); Impact
     (catalogues per joined brand, FTP or API) the alternative; Rakuten hand-picks its
     publishers. Not found: each network's count of UK advertisers; which shops and
     kinds each brings shows only to a registered publisher. A shop in two networks is
     one shop (`PROJECT_RULES.md` §5).
     **The gaps, measured (owner: «Ναι, κάνε τη μέτρηση»; `deployment/server/print_gaps.py`,
     tests 3; `server-cap.yml` with `MEASURE: gaps`, run `41193055282`, the catalogue of
     31/10 04:23 UTC: 528,173 products from 76 shops, 257,437 with a kind):** of the 312
     kinds defined, 94 from 3+ shops, 63 from two, 101 from one, 54 with none. Covered:
     jewellery (196,441), clothing (19,932), furniture (14,420). Short, by mega-category
     (3+ / two / one / none of the kinds; products; shops): computers 7/11/17/3, 6,213,
     9 (Back to the Office alone for laptops 650, monitors 760, RAM 1,157); audio-video
     5/7/2/2, 1,275 (TVs 52 from two shops); phones 5/5/2/2, 5,402; home appliances
     3/2/8/4, 440 (washing machines 2, fridges 5, no dishwasher, air conditioner, air
     purifier); kitchen 5/7/11/2, 1,106 (toasters 55 from Geepas alone); power tools
     0/2/5/6, 23; hand tools 1/2/9/3, 352; car parts 0/0/3/6, 169 (engine oil from All
     Oils alone); tyres 0/2/2/5, 9 (no tyre); health devices 2/1/2/6, 33; baby, pets,
     sports 3/5/15/7, 2,948 (dog food 368 from InStock UK alone); garden 5/3/11/3, 2,280;
     bicycles 0/2/4/2, 124.
     **More shops into the Awin feed, safely (owner, 31/10: the link in use was made with
     no category chosen, any language and every shop with a Google feed; «πως θα ξέρω οτι
     συμπεριλαμβάνονται και τα παλιότερα μέσα στο καινούργιο?»):** `.github/workflows/
     feed-compare.yml` with `.github/scripts/compare_feeds.py` (tests
     `tests/test_picwise_feed_compare.py`, 5) downloads on GitHub's runner the link in use
     and the new one (secret `AWIN_FEED_URL_NEW`), counts each one's shops by advertiser,
     names those the new one lacks (and fails) and those it adds; read-only, links never
     printed. First run (`41193779710`, the link in use alone, 1 min 46 s): **85 shops,
     1,125,253 rows**, InStock UK 509,939, Finediam 367,758, Back to the Office 94,875
     first. The way: the owner joins programmes (the gaps above), makes a new link as
     before (every shop with a Google feed), saves it as `AWIN_FEED_URL_NEW`; the compare
     runs; only when it lacks none does the owner put it in `AWIN_FEED_URL`, and a
     deployment takes it to the server (`deploy.sh` writes it to
     `/etc/picwise/picwise.env`; the preparation reads it).
     **A title's safety, measured (owner, 31/10: «Ναι, κάνε τη μέτρηση»; "safe" as 99%,
     put to them on 26/10; `deployment/server/print_title_safety.py`, tests 3;
     `server-cap.yml` with `MEASURE: title`, run `41196508034`, the server's feed of 31/10
     judged as the preparation judges it):** on the rows shown with a shelf the title
     alone gives a kind to 58,352, agreeing with the shelf for 96.5%. Of the 201,024 rows
     held for want of a category whose title gives a kind, the 27 kinds at 99% (100+ rows
     to tell by) would bring in **11,067** (InStock UK 10,293), and **no kind more from 3
     shops (94 before and after)**. And the 99% does not carry over: among those 27,
     HDMI cables read as jackets, tripods as cameras, shoe racks and camera shoe mounts
     as shoes, monitor arms as monitors. Under 99%: 22 kinds, 159,564 rows, **151,312 of
     them read as phone cases** (69.1% right on the rows with a shelf: "case" in laptop
     bags, earbuds, cables); too few rows to tell: 224 kinds, 30,393 rows. Told to the
     owner: by their title these rows cannot be shown safely; the reliable witness is
     the shop's category.
     **The owner (31/10): another network, even a US one, to borrow categories by similar
     titles** («υπάρχουνε ίδια είδη ... από το άλλο feed θα μπορέσουμε να αντλήσουμε την
     κατηγορία»). Answered: a category can be borrowed only for the same product (barcode
     or brand + model), as tried in our own feed (516 of about 380,000); InStock UK's held
     rows mostly carry no barcode (46,775 of 352,963); a similar title is a guess from the
     title again. Another network's value is its own shops, with categories.
- **The owner's rules, unchanged** (the list in "Items 1, 2, 3" below, with nothing on
  `main` without their explicit «ναι», and never a server name, address, host key or link
  in a log or a file).

### Items 1, 2, 3 (from 2026-10-28)

The owner (28/10): «Θα ξεκινήσουμε με το 1 2 3 σε νέα συζήτηση», and **no deployment
until these three are finished**. The work is on `ccr-1361f1a7-dcpo60` (pushed; the
conversation's own branch `ccr-8eb9b420-958wtr` kept equal); bring it in first. Each is
measured on a copy of the server's catalogue and shown to the owner before it is built.
The owner's rules, unchanged: Greek, short, plain words; say what you found before
building anything; nothing on `main` without their explicit «ναι»; never ask for the
feed link (it holds the key); secrets only in GitHub's or Vercel's secrets; nothing in
Supabase without asking; never open an Awin tracked link from a session or a bot; never
propose contacting the shops; no second bot round the same day without their word;
commission never a criterion; no fake data; Amazon removed for good; the repository is
public, so no server name, address, host key or link in a log or a file.

1. **The 3,075 engagement rings read as accessories** (Finediam, its shelf of rings):
   **built and measured on 2026-10-29, nothing deployed; waiting for the owner's word on
   "For"** (section "Now (2026-10-29)" below). The English "with" (owner, 29/10: «Η
   διορθώσεις πρέπει να αφορούν αγγλικό λεξιλόγιο»: English words only, no «με») and the
   metals after a name make 2,303 of them rings; 772 stay accessories, 756 of them naming
   the ring after a "For" ("Eternal Single Row For Center Oval Diamond Engagement Ring"),
   which the rule leaves alone ("Filter for Coffee Machine"). Put to the owner: measure
   "for" too, only on a shelf that names the kind.
2. **Choices for a general word** (owner: «Το search όταν του βάζεις καλώδιο πρέπει να
   συμπληρώνει προτάσεις τι καλώδιο ζητάει: καλώδιο τηλεόρασης, καλώδιο φόρτισης,
   καλώδιο ίντερνετ ... το ίδιο με όλες αυτές τις γενικές λέξεις»; rules word by word lead
   nowhere). Built from the catalogue itself, each night, for every general word alike:
   the shops' shelves under it (Google's taxonomy) and the words titles put before it
   ("HDMI cable", "aerial cable"), only those that find products, the largest first; in
   the search box and above the results ("What kind of cable?"), in the buyer's language:
   the site is English for the UK and the US (`<html lang="en">`, en-GB/en-US), so the
   shelves' English names; Greek names (Google's `taxonomy-with-ids.el-GR.txt`, by id, not
   yet in `data/taxonomy_sources/google/`) only for a query in Greek. Today's pieces:
   `src/picwise_providers/suggestions.py` (the box's
   suggestions by prefix, from the catalogue, `/suggest.json`), the older
   `src/picwise_search_memory/broad_query_suggestions.py` (from the vocabulary, not the
   catalogue). The cables of 28/10: 3,853 now "cable" (3,270 fabric extension leads,
   coaxial and aerial, audio, 168 saying "USB"), 196 charging cables. **Built into the
   search and measured on 2026-10-29, nothing deployed** (owner, 29/10: «η ίδια λογική
   ένας προγραμματισμός για όλες αυτές τις αναζητήσεις ... δεν θέλω να διορθώνουμε
   ένα-ένα λέξη κλειδί», then «Ναι προχώρα, βάλ' το στο search»; section "Now
   (2026-10-29): item 2" below): on the server's catalogue 43 kinds ask which one is
   meant, each choice finding products of its kind. Found and put to the owner: the
   vocabulary's older "too broad" answers "chair", "bag", "jacket", "charger" and
   "bicycle" with no products (as before this work); noise among the choices (halves of
   phrases, one shop's words, choices that keep almost the whole kind); good choices
   lost because the search reads "pendant light" as every lamp. The owner (29/10): «εσύ
   πρέπει να αποφασίσεις ποιος είναι ο βέλτιστος τρόπος»: the order is chosen here.
   **Built and measured five times on 30/10, nothing deployed** (section below, "After
   the buyer's view"): a kind's own name reaches the feed ("chair", "bag", "jacket",
   "charger", "bicycle", "shorts"); seven rules keep the choices true; on the catalogue
   of 30/10 41 kinds ask, «καλώδιο» with "extension cable, charging cable, hdmi cable,
   audio cable, braided cable, data cable, network cables". A push to the work branch
   needs the session in "Accept edits": "Auto" classes it as a deployment, `[skip
   actions]` notwithstanding (refused twice on 29/10; the owner switched on 30/10).
3. **The cap of 15%: built and measured on 30/10, nothing deployed** (section "Now
   (2026-10-30): item 3" below). The owner, asked how the cap meets the rule of 29/10
   (every product in PicWise's own search, `PROJECT_RULES.md` §13): «Όλα στο search».
   So the cap cuts nothing from the search: each night it chooses the pool Google may be
   given from (168,730 of 527,911 on the catalogue of 30/10), the night before's pool its
   starting point, kept on the server beside the prepared catalogue.

Then the deployment (question 1: `server-deploy.yml`, the round and the setup take the
host key from a login's first step, as `server-night.yml`; editing it deploys, so the
owner may need to set "Accept edits"), then HTTPS and the domain. How to measure without
deploying: commit code with `[skip actions]` in the message (`src/**`,
`deployment/server/**` start `server-deploy.yml`), check no run started, then push a
change of `.github/workflows/server-cap.yml` alone, which copies the server's catalogue
to GitHub's runner and runs `print_cap.py`, `print_prices.py`, `print_kind_changes.py`.
To see one change of the rules on its own, list the commits before it in the workflow's
`RULES_STEPS` (each read from a worktree by `deployment/server/kinds_of.py`). Tests one
module at a time (`test_picwise_learning_stage7b` takes 27 minutes).

## Now (2026-10-29): item 2, the choices for a general word (built, measured, not deployed)

The owner (29/10): one logic for every general word, never keyword by keyword; «Ναι» to
measuring it on the server's catalogue the same way as item 1; then «Ναι προχώρα, βάλ'
το στο search». The measure: `src/picwise_providers/kind_choices.py`
(`measure_kind_choices`; tests `tests/test_picwise_kind_choices.py`),
`deployment/server/print_choices.py` (tests `tests/test_picwise_server_print_choices.py`,
2), a step of `server-cap.yml`.

- **Built (commits `c2b45c5`, `992a59a`, `8ea237b`, all `[skip actions]`):** each night
  the preparation works out the choices of every general kind with the catalogue
  (`kind_choices.build_kind_choices`: the narrower kinds and the words the titles name
  it with, not already covered by an offered narrower kind, the largest first, at most
  6, each kept only if the search reads it as narrowing the kind -- a narrower kind or a
  filter word, `_narrows`; a kind asks when 2 are left) and keeps them in the prepared
  file (`PreparedCatalogue.choices`; an older file carries none, and nothing is asked).
  A search naming only the kind (no filter, no spec) shows above its results "What kind
  of cable?" with each choice a link to its search (`LiveSearchResolution.kind_choices`,
  `reference._kind_choices_html`), in English, for a Greek query too; the box's list
  offers the choices (`build_search_suggestions(..., choices=)`), so typing "cable"
  lists them. Where the catalogue asks, the vocabulary's older "This search is too
  broad. Try: usb cable, hdmi cable, lightning cable" no longer asks too
  (`picwise_app.app`, found on the measure's page for "cable": two questions, one from
  words the catalogue may not have). The preparation's summary counts the kinds that
  ask. Tests: `tests/test_picwise_kind_choices_on_the_page.py` (6, through `api/index.py`
  on a feed file), `tests/test_picwise_server_print_search_choices.py` (2). The modules
  nearest the change pass; the full run of this code before the last fix (272 modules,
  one process each): 269 pass, the 3 that fail fail the same before this work
  (`test_picwise_canonical_vocabulary_registry_stage2`,
  `test_picwise_search_index_generated_blind_stage4`, and
  `test_picwise_search_index_blind_evaluation_stage6a`'s "amazon" and "galaxy" broad
  terms).
- **What a buyer would see (run `40911685093`, the catalogue of 29/10 04:21 UTC, 525,386
  products, prepared again on GitHub's runner with this code and searched there;
  `deployment/server/print_search_choices.py`):** 43 kinds ask (of the 81 the measure
  calls general; the others keep fewer than 2 choices the search reads as narrowing).
  Cable, 4,077: extension cable 3,296, charging cable 196, hdmi cable 80, audio cable 65,
  braided cable 57, lan cable 26. Table: side, coffee, dining, dressing, nesting. Dress:
  midi, mini, maxi, midaxi, jersey. Curtains: eyelet, pleat, blackout. Bracelet: tennis,
  link, chain, diamond, station, line. Monitor: hd, qhd, touchscreen, uhd. The choices of
  the 30 largest were each searched: every one finds products of the kind. «καλώδιο»
  finds the same 4,077 and asks the same. The box: 1,898 suggestions, 173 of them
  choices, 35 KB. About 0.9 s a search on the runner.
- **Found, put to the owner (nothing fixed yet):**
  1. "chair", "bag", "jacket", "charger" and "bicycle" show no products: one-word
     searches with 5 or more of the vocabulary's suggestions get its older "This search
     is too broad. Try: baby feeding chair, office chair, shower chair ..." instead of the
     feed (`broad_query_suggestions.should_offer_broad_query_suggestions`,
     `_HIGHLY_AMBIGUOUS_BROAD_SUGGESTION_COUNT = 5` in the resolver), as before this work;
     the server has 1,822 chairs, 996 jackets, 865 bags. «καρέκλα» reaches the feed and
     asks. 25 more kind names get those suggestions too, with the feed's products
     (cable, lamp, bed, mattress, hat ...); the page does not show them. Proposed: the
     catalogue decides, one logic: a search the kinds' reading understands goes to the
     feed, and asks with the catalogue's choices.
  2. Noise among the choices: halves of phrases ("piece suit" of "3 Piece Suit", "fit
     suit" of "Slim Fit", "size bed" of "King Size", "leg trouser" of "Wide Leg", "neck
     sweater" of "Crew Neck", "door wardrobe" of "2 Door"); one shop's words ("robertson
     hoodie", "makasi rug", "eng ring", "remount ring", "color ring", "do tee", "cup
     shirt", "horse toy"); choices keeping almost the whole kind ("diamond ring" 134,488
     of 141,635 rings, "diamond earring" 18,742 of 19,972, "hat glove" all 424 gloves);
     "caravan mattresse" (the plural cut by one "s"); "men-s watch". Proposed, each
     measured first: a choice from 2 shops or more; the whole phrase when the word
     before the noun is mostly half of one; no choice finding 80% of its kind or more;
     English plurals in "-sses", "-ches", "-shes", "-xes" lose "es".
  3. Good choices lost: "pendant light" 716, "ceiling light", "wall light", "mirrorless
     camera" 186, "engagement ring": the search reads each as the whole kind with no
     filter (a name of the kind in the vocabulary), so a buyer searching "pendant light"
     sees every lamp, as before this work. Proposed: a name of a kind that only part of
     its titles carry narrows the search to them.

- **How:** every kind of 50 or more products (by this checkout's rules) is grouped three
  ways: the words its titles name it with -- the word right before the noun of its name
  and that noun as written ("hdmi cable", "sofa bed" under sofas, "zip-up hoodie"),
  weak names read too since the kind is known; its narrower kinds; its shops' narrowest
  shelves. A word before the nouns of 8 kinds or more says how a product is, not which
  kind ("gaming", "knitted", "football" on 29/10), and is no choice; nor a number, the
  brand or a connective. A choice from 20 products, whatever its share (first run
  `40868599997` asked 5% of the kind, and "cable" got no choice: one shop's fabric
  extension leads are 81% of cables). General: 2 choices of one way.
- **What it found (run `40869626869`, the catalogue of 29/10 04:21 UTC):** of 116 kinds
  of 50+ products, 81 general (57 by words, 62 by shelves). Cable: extension 3,291,
  charger 67, charging 56, braided 54, HDMI 42, audio 38, LAN 26, USB 24 (and shelves
  HDMI, Network, Audio Cables). Table: side 774, coffee 496, console 273, dining 257,
  dressing 61, nesting 48. Lamp: pendant light 716, table lamp 472, floor lamp 125,
  ceiling light 124, wall light 90, chandeliers. Dress: midi, mini, maxi; earrings:
  stud, hoop, diamond, drop; bracelet: tennis, link, chain; camera: mirrorless,
  compact, instant, digital; curtains: eyelet, pleat, blackout; socks, mattresses,
  beds, sofas, hats, gloves, saunas alike. Noise, mostly clothes with prints and
  shops' own words: "do shirt" 764, "funny shirt", "rude shirt", "robertson hoodie",
  "cup shirt", "color ring" 3,906, misspellings ("engagment ring" 504); the singular
  cut short ("caravan mattresse", "wine glasse": `_singular` strips one "s"). The
  shelves of several shops name one thing twice ("Dog Food", "Non-prescription Dog
  Food"), so as choices they are weaker than the words. Not general: keyboard, mouse,
  desk, backpack, perfume, motherboard, wall clock and others with one group.
- **Wrong kinds the shelves showed (to fix, told first):** vitamin and toothpaste tablets
  ("Vitamins & Supplements", "Toothpaste" shelves) and tablet cases read as tablet
  computers; basketball hoops (67) read as footballs.
- **Proposed next (owner's word first), before it was built:** build it into the search
  -- the choices of the buyer's kind above the results ("What kind of cable?") and in the
  box's suggestions, the largest six, each a search that finds products -- computed each
  night with the catalogue, in English; measured on the server's catalogue again before
  any deployment. Done the same day (above).

## Now (2026-10-30): item 3, the pool Google may be given from (built, measured, not deployed)

The owner (30/10): «Να προχωρήσεις με το 3»; then, between the cap of 27/10 (no category
over 15% of the products shown) and the rule of 29/10 (`PROJECT_RULES.md` §13: every
product a card can show stays in PicWise's own search), «Όλα στο search».

- **Built** (code `411f328`, `[skip actions]`): `tools/prepare_catalogue.py`, after
  writing the prepared catalogue, runs `catalogue_cap.cap_catalogue` on every product a
  card can show, with the night before's pool as `kept_before`, and keeps the new pool
  beside the catalogue (`google_pool.json.gz`: the kept rows' keys, `write_google_pool`,
  `read_google_pool`, `google_pool_path`; on the server
  `/srv/picwise/shared/prepared/google_pool.json.gz`, never in the public folder). The
  search reads none of it: every product stays in the search. The pages meant for Google
  (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, not built) are to choose their products from it.
  A failure keeps the night before's pool and prints "the pool Google may be given from
  failed (...)"; a night that cannot read the feed leaves it as it is. The run's line
  ("prepare_catalogue: the pool Google may be given from: N of M products ...") reaches
  the night's log; the public note (`prepared.json`) counts it under `google_pool`,
  without a row's id. Tests: `tests/test_picwise_catalogue_cap.py` (17),
  `tests/test_picwise_prepared_catalogue.py` (24), `tests/test_picwise_server_print_cap.py`
  (3); the modules that run the tool pass.
- **Measured (run `41040939695`, the catalogue of 30/10, 527,911 products, 171
  categories):** the pool 168,730, at most 25,309 a category; over the cap only
  jewellery (381,204 -> 25,309: rings 310,572 -> 3,887, earrings, body jewellery,
  bracelets, necklaces, charms & pendants about 3,887 each, all 1,724 watches) and
  clothing (28,595 -> 25,309: t-shirts 7,292 -> 4,433, socks 4,859 -> 4,432, the rest
  whole). After it: clothing and jewellery 15.0% each, decor 6.8%, the shops' own
  categories 5.2%, food 5.1%, shoes 4.6%. By shop: Finediam 360,113 -> 18,850, InStock UK
  93,406 -> 91,571 (54.3% of the pool; no limit per shop, owner 27/10). Of the 50,618 in
  the pool from the two categories over the cap, 50,168 have an identity, an image and a
  stock state that varies; 204 are sold by more than one shop. **The next night, on the
  same products with the pool as its starting point: 168,730, every one the same**
  (`print_cap.py`'s last line).

### After the buyer's view (29-30/10, the order chosen here): built, measured, not deployed

The owner (29/10): «εσύ πρέπει να αποφασίσεις ποιος είναι ο βέλτιστος τρόπος». Each step
measured on a copy of the server's catalogue of 30/10 (527,911 products) before the next:
runs `41028398470`, `41031539622`, `41034288478`, `41036545617`, `41038004324`
(`deployment/server/print_choice_rules.py`: what each rule leaves out and lets in on
its own; `print_search_choices.py`: what a buyer would see).

1. **A kind's own name reaches the feed** (`2d4ea2e`, `f25284a`): a one-word search the
   kinds' reading finds to be a kind's own name, exactly (`ConceptReading.exact`), is
   searched in the feed whatever the vocabulary suggests (5+ suggestions stopped it) and
   however close the index sets it to another word ("shorts" near "short"; the three
   such names: shorts, cot, doll); the catalogue asks where it has several kinds of it.
   A word read as a kind only by correcting it keeps the vocabulary's list alone:
   "chain" reads as chair, "protector" as projector, "tools" as toy, "bots" as boots.
   Where the feed's products show, the older "too broad" list no longer replaces the
   page's note (`picwise_app.app`); it stays for a broad word with nothing to show. The
   tests of stages 8b and 8c that pinned "charger" to the list now pin "protector",
   "chain" and "tools" to it and "charger" to the feed. Measured: chair 1,867 products,
   bag 843, jacket 1,006, charger 126, bicycle 92, shorts 690 (none before).
2. **The rules that keep the choices true** (`kind_choices.CHOICE_RULES`, each can be
   left out; the module's docstring says each with the run that showed why):
   - `RULE_SHOPS`: a choice by the words is named so by 2 shops, or its word is used by
     other shops before some noun; one shop's own words go ("robertson hoodie", "eng
     ring", "remount ring", "do tee", "cup shirt"). Asking 2 shops of the phrase itself
     (first run) also lost "lan cable", "thermal socks", "barrel sauna", "qhd monitor".
   - `RULE_PHRASES`: a word three quarters of whose titles put a number, or a word the
     two make one modifier with before other nouns too, before it is read whole ("3
     piece suit", "3 seater sofa", "long sleeve shirt", "bean bag chair", "straight leg
     trousers"), unless that word names the kind alone too ("Diamond Bracelet": a
     diamond tennis bracelet is a tennis bracelet). The second run's reading (any word
     mostly after the same few) made one shop's lines choices ("britain unisex hoodie").
   - `RULE_WHOLE_KIND`: no choice whose search keeps 90% of the kind ("diamond ring",
     139,693 of 141,636 rings).
   - `RULE_WRITTEN`: the noun as the titles write it ("bootcut jeans", which the search
     reads; "bootcut jean" it does not).
   - `RULE_SAME_SEARCH`: no two choices the search reads the same ("diamond cross
     pendant", "diamond cross necklace").
   - `RULE_SHELVES`: a shop's narrowest shelf naming one word before the kind's noun is
     a choice too ("Network Cables": the owner's «καλώδιο ίντερνετ», named "LAN",
     "Cat6", "Ethernet" by titles, none from 20 of two shops); a shelf of two shelves
     ("Charms & Pendants") is none.
   - Every choice is weighed by what its own search keeps of the kind (as the
     price-first search reads its words, `_KindSearch`), from 20 ("End Tables" stood on
     800 products and its search found 7), the largest first, at most 8 (six left
     "network cables" seventh).
3. **What a buyer would see (run `41038004324`):** 41 kinds ask. Cable: extension cable,
   charging cable, hdmi cable, audio cable, braided cable, data cable, network cables.
   Socks: thermal, bamboo, cotton, wool, hiking, grip, bed socks. Bracelet: diamond,
   tennis, link, chain, station, halo. Sofa: 3 seater, sofa bed, 2 seater, corner,
   recliner, chesterfield. Chair: velvet, office, dining, back, gaming, bean bag, swivel,
   bar. Every choice of every kind finds products of its kind. The box: 1,892
   suggestions, 171 choices, 35 KB. Left as they are, each small: the jeweller's own
   words on rings ("color rings", "fashion ring", "center ring", "cut ring"), "size bed",
   "back chair", "2 edition trainers", "shape earrings", "letter bracelet" (its search
   finds 11), "chesterfield sofa" (14).
4. **Found on the way, not fixed (each to measure, the owner told first):** English
   words read as other kinds: "skinny jeans" reads as a tent ("skinny" as the greeklish
   σκηνή, ahead of the English "jeans"), "patch cables" as insoles; a title naming its
   kind only by a weak name reads as no kind even on a shelf naming it ("Diamond Ring",
   "Emerald Ring", "Ruby Ring" on a Rings shelf; "Gold Ring" reads); "pendant light",
   "ceiling light", "mirrorless camera", "engagement ring" search as the whole kind.
5. Tests: `tests/test_picwise_kind_choices.py` (14), `tests/test_picwise_kind_choices_on_the_page.py`
   (10), `tests/test_picwise_server_print_choice_rules.py` (2),
   `tests/test_picwise_server_print_search_choices.py` (2); the 31 modules through the
   resolver and the choices pass.

## Now (2026-10-29): item 1, the engagement rings

The owner: «Ξεκινάμε με το 1»; then «Ναι» to pushing to `ccr-1361f1a7-dcpo60` for the
measure (code with `[skip actions]`, then `server-cap.yml` alone; no run but the measure
started, checked each time). This conversation's own branch `ccr-4f9ef4ee-j1nafx` is
kept equal by merges (a force-push of it was refused; the work branch stays linear).
The work branch had moved to `31e2ee4` (the previous conversation's docs commit on item
2's language), so this work sits on it.

- **Built** (`src/picwise_nlu/concept_understanding.py`, tests
  `tests/test_picwise_kinds_named_after_with.py`, 5): a title that names no kind before
  its first "with" (or "w/") is the kind it names after it, past one "with" or more,
  when the shop's narrowest shelf names that kind too (`_cut_past_with`, read only by
  `_title_named_head`, i.e. when neither the type nor the category gives a kind); after
  "for", after an accessory's noun before the kind, or on no such shelf it is still an
  accessory. English only (owner, 29/10). Metals right after a product's name
  (platinum, palladium, titanium, tungsten, sterling; `_METAL_TAIL_WORDS`) describe it,
  as gold and silver did; read only there, since elsewhere a metal names a line ("Dr John
  Titanium 15KG", dog food, became doubtful when they were read everywhere).
- **The measure** (`deployment/server/kinds_of.py`; `print_kind_changes.py --step`, whole
  titles, and the word after a kind's name for the accessories on its shelf; tests
  `tests/test_picwise_server_print_kind_changes.py`, 3; runs `40858411220`,
  `40862093722`, `40862883104`, the catalogue of 29/10 04:21 UTC, 525,386 shown): **the
  "with" rule alone 2,329 (0.44%)**: 2,271 Finediam engagement rings accessory -> ring;
  42 Finediam pendants "with Diamond Accents Necklace (Without Chain)" accessory ->
  necklace (the lexicon has "pendant" as a name of necklace, and they sit on its
  necklaces shelf; told to the owner); 7 Geepas mixer grinders -> mixer; 6 baby tees ->
  t_shirt; 2 pendant lights -> lamp; 1 utensil set with a knife set -> knife_set.
  **The metals 1,891 (0.36%), all Finediam rings**: 1,823 doubtful -> ring ("... 3 Stone
  Engagement Ring Platinum - Sterling Silver / 0.50 Carat"), 36 of no kind -> ring, 32
  accessories -> ring. Rings 143,860 -> 148,022 in all. Of the 3,075: 2,303 rings, 772
  still accessories on the ring shelf, the word after the ring's name "9k/18k" 756 —
  these name it after a "For" ("Refined Solitaire For Peg Head Round Diamond Engagement
  Ring — 9K/18K Gold & Platinum"). The far prices with the kinds read so: 7,104 (ring
  5,284, Finediam's luxury and cheap ends as before). Every change since the deployment
  of 26/10: 9,406 (1.79%).
- **Tried and left out (probed on the measure's titles, not measured):** the noun before
  "with" as the product ("Pendant with ... Necklace") would not keep the pendants out
  (pendant is the necklace's own word) and would cost the mixer grinders and the
  pendant lights.
- **Checks:** the kind-related modules one at a time (116 pass; the two known failures,
  `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`, fail on `cb40587` too); the
  misspelling benchmark the same (93.8%, 0 wrong); `actionlint` could not be fetched
  here (refused), the workflow was parsed and its kind steps run locally instead.

## Now (2026-10-27/28): the server's host key, the cap, the far prices, the kinds

The owner's «Ναι» (26/10, evening) to two things: writing straight to `ccr-1361f1a7-dcpo60`
(this session's own branch, `ccr-8eb9b420-958wtr`, is kept equal to it), and a small
read-only look at the night's round. Owner's rules unchanged (section below).

- **The look, built:** `.github/workflows/server-night.yml`, run when it is pushed to
  `ccr-1361f1a7-dcpo60`: from each timer's last start (`LastTriggerUSec`, kept across a
  reboot), the result and times of `picwise-shops.service` and `picwise-prepare.service`,
  the bot's own lines and the preparation's summary; then `print_shops.py` and
  `print_kinds.py`, as after a deployment. It starts no round and changes nothing. Its
  script goes to the server on stdin (`ssh picwise 'bash -s' <<'EOF'`), so no quote in it
  can close the command. Checked here: `actionlint` 1.7.12, `bash -n`, a dry run with
  stand-in commands; its connection step and its last three are `server-shops.yml`'s,
  unchanged. To read another night: change its "Night read" date line and push.
- **What it found (the owner's «στείλτο», 27/10 09:00 UTC, commit `bde4cdd`, run
  `40477603160`): nothing of the night.** Its first step stopped at the identity check:
  "the server does NOT match the pin (reinstalled, or not our server)". The pin it
  computed is not `.github/server-host-key.pin` (taken 25/10); the deployment of 26/10
  (run `40355492889`, connected at 16:04 UTC, done 16:16) still matched it. The step
  stopped before any login: nothing was sent to the server. The night's round of 27/10
  is unread, and whether it ran is not known.
- **What it can be:** the VPS reinstalled, or booted in rescue mode (both change the host
  key); the `SERVER_SSH_KEY` secret changed (the pin is an HMAC under a key derived from
  it, so a new deploy key changes the pin of the same host key); `SERVER_HOST` changed;
  or another machine at the address.
- **What the owner checked (27/10, screenshots; the server's name and address are in
  them and are written nowhere):** the VPS page says Status "Active", Boot "LOCAL" (not
  rescue), "Ubuntu 24.04", VPS-4 2027, London; no OVHcloud email of a reinstall or rescue.
  One OVHcloud email, "Notification of connection to your OVHcloud account", dated
  2026-10-26 14:09:47 (OVHcloud's clock), before the deployment that still matched the
  pin; the owner does not remember logging in, and was advised to change the OVHcloud
  password and turn on two-step verification (My account → Security). In GitHub's
  secrets, `SERVER_HOST` and `SERVER_SSH_KEY` were last changed "2 days ago" (25/10), so
  they are not the cause.
- **The proof, built (owner's «Ναι», 27/10):** `server-night.yml`, which sends the
  server no secret, no longer stops at a changed pin: it asks the server to seal a random
  nonce under the feed link (`.github/scripts/feed_seal.py`, HMAC-SHA256; GitHub from the
  `AWIN_FEED_URL` secret, the server from `/etc/picwise/picwise.env`); only the nonce goes
  and only the seal comes back. A server whose seal is GitHub's is read: why its key
  changed (boots, the host keys' dates, cloud-init, the updates' reboots), the SSH logins
  since 26/10 16:00 UTC without addresses, then the night. Any other is not read, and the
  failure is sorted without printing the server's words. The deployment and the round
  keep the strict pin. Tests: `tests/test_picwise_server_feed_seal.py` (5); dry runs of
  every case with stand-in commands; `actionlint`.
- **What the proof found (runs `40489651144` and `40489927183`, 10:35-10:37 UTC): not
  read.** The new key's pin is the same in all three runs (the key is stable since 09:00).
  Port 22 says `SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.20`, an Ubuntu 24.04. But the login
  for the seal was shown **another key than the one the same address had shown a second
  before** ("Host key verification failed"), so it stopped before logging in. At least
  two different host keys answer at the server's address: two machines on it (an address
  conflict at OVHcloud), or something in between. A reboot alone would give one new key,
  not two.
- **The look that never logs in (owner's «Ναι»; `.github/workflows/server-keys.yml`, run
  `40501323803`, 12:07 UTC): our server is there.** Four tries, the order changed each
  time: **a key scan (`ssh-keyscan`) is shown the morning's key every time, and a login's
  first step (an `ssh` client offering no key or password) is shown our pinned key of
  25/10 every time.** Not two machines taking turns: the key depends on how the address
  is asked. Whoever shows the pinned key holds its private half, made on our server on
  25/10, so real logins reach our server. Yesterday's deployment was shown the pinned key
  by `ssh-keyscan` too, so what answers a key scan with another key began in the night:
  not explained yet (something on the server since the night's updates, or on the way).
  Every workflow takes the key to compare with the pin from `ssh-keyscan`, so each stops
  there although a login would reach our server.
- **Built (owner's «ναι κάνε»):** `server-night.yml` takes the key from a login's first
  step and compares it with the same pin (as strict: every connection then accepts that
  key only); a key scan's key is only reported; when it differs, the server is asked what
  answers a key scan. The deployment (`server-deploy.yml`), the round
  (`server-shops.yml`) and the setup still compare `ssh-keyscan`'s key, so **they stop at
  their first step until they take the key the same way** (put to the owner; editing
  `server-deploy.yml` deploys).
- **What it found (run `40504119821`, 12:29 UTC): our server is untouched.** It matched
  the pin; a key scan was shown the morning's key again. From inside: up since
  2026-10-25 11:04:58 UTC (no reboot since the setup); the host keys written 25/10 09:37
  by cloud-init, the same instance-id since, no regeneration; the ed25519 key on disk is
  the pinned one; one `sshd` (socket-activated) on 0.0.0.0:22 and [::]:22; no rewrite of
  port 22 (nftables holds ufw's rules and fail2ban's reject set only); the night's only
  update `libbrotli1` (27/10 06:23); since 26/10 16:00 UTC 13 SSH logins, all with the
  deploy key, none on the console. So what shows a key scan another key is not on our
  server: something on the way answers that kind of connection (not known what; it gets
  no secret, and a login with any other key than the pinned one is refused by every
  workflow). The server's nightly work does not need GitHub: the timers run on it.
- **The night's round of 27/10 (the first by collections):** the bot 03:40:00-03:53:35
  UTC, success: 54 shops, 413 requests; the file knows 65,031 products (59,996 with a
  type, 29,460 sold out; 58,728 / 53,699 / 25,041 on 26/10). Back to the Office: its
  catalogue to the page limit again (about 100 of its 200 requests), then **collections
  38 of 1,338**: 30,282 of its 95,050 products known; at this pace a whole pass takes
  about 35 nights (put to the owner: page the catalogue's first 25,000 less often, or
  more requests for it). Finediam: Shopify answers 500 at page 23 again (5,500 known).
  Juicy Couture UK: no shop address in its rows. Pro Espresso: its robots.txt redirects to
  another site, so it is not read. The preparation 04:17:02-04:27:41 UTC, success:
  1,124,205 rows, **524,335 shown** (+885), 81 shops, peak memory 7.9 GB, 640 s. Back to
  the Office **6,135 shown** (5,252 on 26/10); rows given their shop's type with its kind
  **24,974** (20,402), naming none 13,218; by barcode 1,128 (InStock UK 1,061); the
  shop's sold-out holds 43,509 (the feed called 142 of them in stock). The cap,
  measured: by shop Finediam 68.7%, InStock UK 17.8%; by aisle jewellery 72.7%; by kind
  ring 57.7%; kinds from at least 3 shops 94 of 256. The kinds' check: of 249,225
  products shown as a kind, the title names none of its kinds for 12,731.
- **The owner's word (27/10, afternoon):** the deployment, the round and the setup stay
  as they are for now («Το αφήνουμε όπως είναι»); no 400 requests for Back to the Office
  («δεν θέλω αυτή τη στιγμή 400 ελέγχους»). **The cap, decided in its aim:** a kind of
  like products (rings, watches) never more than 15% of all products, so that no shop
  makes the site look like one kind of shop to Google, the server's room is not spent
  on a few kinds but spreads to others little by little, and each search looks complete;
  «πρώτα από όλα να έχει καθαρή και ποιοτική πληροφορία», a satisfying volume, not a
  huge one. Put to the owner how it counts: each product under its kind, or its shop's
  narrowest shelf when it has none (275,110 shown have no kind, most jewellery among
  them); within a group over the cap the clean rows first (barcode or brand + model code,
  an image, real stock), those sold by more than one shop first, spread over the price
  range, the same ones each night; measured with that rule before anything is cut. It
  reaches the server only by a deployment, which needs the change the owner left for now.
- **The cap, chosen (owner, 27/10, after «βοήθησέ με γιατί έχω μπερδευτεί»):** 15% **per
  category**, the first two levels of the shop's Google shelf ("apparel & accessories >
  jewelry", watches included), not per department (too coarse: it would cut clothes and
  shoes with the jewellery) nor per kind (many jewellery kinds of 15% each could still
  make the site half jewellery). The size is worked out at once so that no category
  keeps more than 15% of what all keep, each night from every product a card can show
  (the owner asked whether it would keep cutting: it does not); the night before's kept
  ones are the next night's starting point (owner: «κοιτώντας πάντα το χθεσινό σαν
  αφετηρία»), more products a larger cap, fewer a smaller one in proportion. Built:
  `src/picwise_providers/catalogue_cap.py` (inside a category its places shared fairly
  over its kinds, a shelf for a product without one; inside a kind the clean ones first,
  those in more than one shop first, spread over the prices; tests
  `tests/test_picwise_catalogue_cap.py`, 12), `deployment/server/print_cap.py` (tests
  `tests/test_picwise_server_print_cap.py`, 3), `read_prepared_catalogue_to_measure`, and
  `.github/workflows/server-cap.yml`, which measures a copy of the server's catalogue on
  GitHub's runner. **Not called by the preparation: nothing shown changes.** The code was
  pushed with `[skip actions]` (commit `efc5ac0`), since `src/**` and
  `deployment/server/**` would start a deployment, which the owner left as it is.
- **What the cap would keep (run `40511286783`, the catalogue of 27/10 04:21 UTC):** of
  524,335 in 171 categories, **164,176**, at most **24,626** a category; over it only
  jewellery (380,984) and clothing (28,427). After it: clothing 15.0%, jewellery 15.0%,
  decor 6.6%, food 5.3%, shoes 4.7%, vehicle parts 4.3%, hobbies 4.1%, the shops' own
  categories 3.9%. Inside jewellery about 3,185 each for the shelf "rings" (products with
  no kind), ring, earrings, the shelf "body jewellery", bracelet, necklace and the shelf
  "charms & pendants"; all 1,725 watches; prices kept 0.99-109,787.50 (all 0.50-112,137.50),
  middle 1,108.50 (1,566.43). Clothing: t-shirts 7,266 -> 4,142, socks 4,818 -> 4,141, the
  rest whole. Of the 49,252 kept in the two, 48,796 with an identity, an image and a stock
  state that varies; 218 sold by more than one shop. By shop: Finediam 360,127 -> 18,891
  (11.5%), **InStock UK 93,406 -> 91,219, 55.6% of what is kept**, MonsterPiercing 16,030
  -> 3,278. Found: rings count twice (the kind and the shelf of rings the kind reading
  leaves without one), so they take two shares; to be one group before the cap is
  applied. Put to the owner: a limit per shop as well (InStock UK would be over half).
- **No limit per shop (owner, 27/10: «Να μην εφαρμοστεί πλαφόν ανά κατάστημα»).** The owner
  then asked about price: what commission a 99p product leaves, whether it is poor or a
  piece of a pack, and that about 100,000 is too much. Answered: commission never enters
  a choice (PROJECT_RULES §4, concept §14) and the cookie earns on the whole basket; no
  price ban; proposed trimming each kind's cheapest and dearest 2% inside the cap, after
  a measure. **The measure (owner: «Κάνε τη μέτρηση»; `deployment/server/print_prices.py`,
  tests `tests/test_picwise_server_print_prices.py` (2), run `40533880205` in
  `server-cap.yml`):** of 524,335 (GBP 523,978, EUR 327, USD 28, DKK 2), under 1.00: 220
  (0.04%; hobbies 58, books 49, food 41; InStock UK 167, Lets Buy Books 48; 13 name a
  pack; penny sweets "10p each", stickers); 1.00-2.00: 1,165 (InStock UK 1,121; party
  invitations, mini bath bombs; 82 name a pack); 10,000 and over: 28,436 (5.4%; Finediam
  28,212, then Steam & Oak 108, SafeFort 75, Back to the Office 33); 50,000 and over: 106
  (diamond necklaces to 112,137.50; network software licences to 125,474.99). Far from
  their kind's middle price (516 kinds and shelves of 20 or more): under a tenth 4,888
  (cheap bracelets against a middle of 3,099 the diamonds set), over ten times 7,229,
  among them wrong kinds ("Okemia Mirror" 1,929 read as a toy; "Satin Bag Diamond
  Earring" read as a bag; a full pallet of AdBlue). Inside the cap the cheapest 2% of
  rings run to 358.60 and of bracelets to 125: trimming them would cut the ordinary
  affordable jewellery, since Finediam sets the prices. Put to the owner: no price rule
  and no trim; the ends are few and real; a price far from the kind's middle used as a
  check for wrong kinds.
- **The owner's «Ναι» to no price rule, no trim, and a far price as a check for wrong
  kinds; rings as one group (run `40535514183`, code `0958bd9` with `[skip actions]`):**
  `catalogue_cap.joined_parts` puts a shelf whose last level names a kind of the same
  category under that kind. The cap's totals are unchanged (164,176; 24,626 a category);
  inside jewellery 14 groups, ring 310,572 -> 3,770 (one share, not two), earrings,
  bracelet, necklace, the shelves "body jewellery" and "charms & pendants" 3,770 each,
  all 1,741 watches; kept prices 0.99 / 1,050.00 / 109,787.50; 48,820 of 49,252 kept with
  all three clean signs. `print_prices.py` now lists the products priced far outside
  their kind's usual prices (beyond 1.5 times the middle half's spread on a ratio scale,
  and ten times off the middle price): **9,174 in 130 of 504 kinds and shelves**; real
  wrong kinds among the furthest (Harvia sauna stones 60 read as "sauna"; Living with
  Luxury's cabinets 1,872-4,103 on its shelf of "cabinet doors"; children's snap bands
  0.50-1.50 as "bracelet"; balloons on a balloon shelf whose middle is 99; tablecloths on
  a "kitchen & dining" shelf whose middle is 1,170); but noisy where a kind mixes cheap and
  luxury shops: 5,755 are rings (usual 147.67-18,357.94, set by Finediam), earrings 913,
  bracelets 344; and "charging_cable" has a middle of 95 (phone and car charging cables
  read as one kind). Put to the owner: compare within the same shop to cut the noise,
  then fix the reading rules for what it finds, each fix told first.
- **The check compares within the shop too (owner's «Ναι», 27/10; code `bc8485a` with
  `[skip actions]`, run `40536481871`):** a product is listed when its price is far
  outside its kind's usual prices and its own shop's for that kind, when the shop has 10
  or more; counted by shop and kind too. **7,143 in 110 kinds** (9,174 before); InStock
  UK's cheap rings no longer listed. Most are real luxury or cheap ends, not errors:
  Finediam's rings 5,304 (to 61,447.50), necklaces 91, pendants 52; MonsterPiercing's gold
  body jewellery 462; penny sweets 194; Lets Buy Books at 0.49 51; Off-White Nikes at
  5,100.20. **Wrong kinds found, fixes put to the owner:** earring backs read as
  "earrings" (Finediam 113, "LOX Locking Earring Backs"); aerial and satellite coaxial
  cables as "charging_cable" (InStock UK 265, "Maplin F Type Connector ... Coaxial
  Cable"); sauna stones as "sauna" (Steam & Oak); photo frames with a mirror as "mirror"
  (InStock UK 19). Also the shop's own category: Living with Luxury's cabinets on its
  "cabinet doors" shelf (not ours to change).
- **The four rules fixed (owner, 27/10: «Διόρθω τους κανόνες και άντε να δούμε πού θα
  καταλήξουμε τελικά»; code `7354a52` with `[skip actions]`, nothing deployed):** "backs",
  "backing(s)" end a title's lead as an accessory's noun (`_LEAD_ACCESSORY_NOUNS`: earring
  backs filed under "Earrings"); a plain "cable" is a new, broader kind `cable` (καλώδιο),
  and `charging_cable` only what a title or a shelf names as a charging, charger, USB,
  USB-C, Type-C, Lightning or iPhone cable, a cable too («καλώδιο» and "cable" find every
  cable, «καλώδιο φόρτισης» and "usb cable" only those); "stones" right after a kind's
  name make it something for it (`_MODIFIER_TAIL_WORDS`: sauna stones; not "stone", a
  colour as often); a new kind `photo_frame` (photo or picture frame, κορνίζα), named last
  in a title (`_NAMED_LAST_KINDS`: "Glass & Mirror 6x4 Photo Frame" is a frame); `cable`
  and `photo_frame` compare as charging cables and mirrors did (length, size; no best).
  Tests: `tests/test_picwise_kinds_from_the_far_prices.py` (10, failing on the old
  rules); one changed (`test_the_first_shelf_that_names_a_product_decides`: a shelf
  "cables" gives a cable); the kind, query, search and catalogue modules pass one at a
  time (`test_picwise_learning_stage7b` takes 20 minutes); the misspelling benchmark the
  same (93.8%).
- **Where it ends (runs `40759989550`, `40761504364`, `40762760684`, the catalogue of 28/10
  04:22 UTC, 524,436 shown; `deployment/server/print_kind_changes.py`, tests
  `tests/test_picwise_server_print_kind_changes.py` (2): each product read again with this
  commit's rules against the kind stored, the words each change's titles share, then the
  check of far prices again):** **5,148 change kind (0.98%)**: 3,853 are no charging
  cables but cables (InStock UK 3,730: 3,270 Lola's Leads fabric extension leads, Maplin's
  coaxial and aerial cables, 150 liquorice "cables" among the sweets; Back to the Office
  122: audio and fan cables; 168 say "USB", some perhaps phone cables now only "cable");
  charging cables 4,049 -> 196; 1,254 photo frames (1,238 had no kind: Kenro, Walther);
  Finediam's 18 LOX earring backs an accessory (doubtful before); Steam & Oak's sauna
  stones an accessory; 6 mirrors photo frames; 16 frame "collections" doubtful, 6
  accessories (a frame "on Stand", a photo mount, a frame clock). The far prices: 7,141
  -> 6,995; charging cables 265 -> none (the same cheap cables now far below all cables'
  middle of 102, set by the extension leads: 273, no wrong kind); mirrors 21 -> 15; the
  sauna stones out; Finediam's earrings 113 -> 95, the furthest now a 46,319.00 diamond
  earring.
- **Found on the way:** the earring backs never answered a search for earrings (doubtful);
  the cap counted them as earrings by their shelf (`catalogue_cap.joined_parts`), and the
  check with it. The check now leaves an accessory on its shelf (`b2ce892`, `337047c`); the
  cap still joins it, as chosen: with a share of their own, the accessories on Finediam's
  shelf of rings would all be kept. **And those 3,075 "accessories" are engagement rings**
  ("2.00 Ct Lab Grown 3 Stone With Side Halo Diamond Engagement Ring Platinum"): the
  title says "With" before the ring's name, and a kind named only after a purpose word is
  read as an accessory of it (`_head_of_text`, meant for "filter for coffee machine"), so
  no search for a ring shows them (before 27/10 too). Put to the owner: after "with" (not
  "for"), a kind the title names when nothing before names one is the product, measured
  first. A few more accessories are real products (4 microphones with a "mount", 3
  bedside tables "Storage Organiser"). The rules reach the server only with a deployment
  (question 1).
- **The owner's answers (29/10) to an honest assessment** (asked: «πες την αλήθεια»): the
  catalogue's gaps -> other affiliate networks will be added; the decision rests on the
  middle price; the kind reading is finished when every kind defined has products and has
  been debugged once; what users do does not matter now (there are none), what Google does
  at launch does; there is a domain of our own, and the rules leave no room for breaking
  Google's rules or data quality; the system is to keep itself up to date; everything in,
  debugged in bulk (not a few kinds first); the creed: volume, quality of information,
  truth, an architecture right for SEO. Answered: the middle price is a sound basis if it
  is the median of a kind read right, from several shops, per size where size matters
  (the rings' middle is Finediam's, the cables' the extension leads', the charging cables'
  the EV cables'); keep everything in the search, but let Google index only the kinds that
  pass a bar (enough products, shops, debugged); Search Console from the first day; an
  alarm when a night fails, before launch. **Decided (owner, 29/10): «Θα στήσουμε
  ολοκληρωμένα και θα δώσουμε στη Google αυτά που θέλουμε τμηματικά»**: everything is
  built whole and in the search; Google is given what the owner chooses, part by part.
  The gate for it exists for the buying pages (`src/picwise_buying_pages/index_gate.py`,
  `docs/pickwise_roadmap_step6_quality_index_gate.md`: index, noindex, hold for review);
  what it needs is a bar per kind (products, shops, checked) and the owner's choice of each
  part. **Saved as a rule (owner, 29/10: «να το αποθηκεύσεις έτσι ώστε να είναι κανόνας»):
  `PROJECT_RULES.md`, section 13 "Google Rule"**, and in `docs/PICWISE_GOOGLE_PAGES_SPEC.md`
  (the gate of section 2, the batches of section 9, the owner's summary). The bar's numbers
  are the owner's to set.
- **The owner's word (28/10): no deployment until what was started is finished** («Δεν
  προχωράμε σε ανάπτυξη μέχρι να ολοκληρώσουμε αυτά που έχουμε ξεκινήσει»). Also: rules
  word by word lead nowhere; a general word ("καλώδιο") should be answered with choices of
  what it means (TV, charging, internet cable), for every general word alike. Started,
  in this order, each measured on a copy of the server's catalogue before it is built:
  1. the 3,075 engagement rings read as accessories (a kind named after "with" read as
     the product); 2. choices for a general word, from the catalogue itself (the shops'
     shelves, in Greek from Google's Greek taxonomy, and the words titles put before it),
     in the search box and above the results; 3. the cap of 15% called by the nightly
     preparation, the night before's kept list kept on the server. Then the deployment
     (question 1), then HTTPS and the domain.
- **Rules that hold:** the pin stays as it is (our server still holds that key; no new
  pin is needed); a workflow logs in only after a login's first step showed the pinned
  key; `server-check.yml` logs in with `accept-new` whatever the pin, so it is not run;
  the deployment, the round and the setup stop at their first step until they take the
  key from a login's first step too (the owner's word first).
- **Not affected:** the live site on Vercel (`picwise.subby.cloud`) does not depend on the
  server; the server's own site listens on 127.0.0.1 only.
- **Still waiting for the owner's word, as before:** the cap; the next kinds (mattresses,
  whiteboards, safety footwear, handheld mobile computers); HTTPS and the domain; the
  repository private; query logging from the server; 80 or 200 bot checks per shop.
  New (28/10): question 1 (the deployment, the round and the setup taking the key from a
  login's first step, so the fixed rules reach the server); a kind named after "with"
  read as the product (the 3,075 engagement rings).

## Before (2026-10-26, evening): the bot runs each night on the server

The owner ended the conversation of 26/10 with «Πάμε σε άλλη συζήτηση». Owner's rules,
unchanged: Greek, short, plain words; say what you found before building anything;
nothing on `main` without their explicit «ναι»; never ask for the feed link (it holds the
key); secrets only in GitHub's or Vercel's secrets; nothing in Supabase without asking;
never open an Awin tracked link from a session or a bot; never propose contacting the
shops.

- **Where the work is:** the branch `ccr-1361f1a7-dcpo60` (pushed, last `a6d4318`): bring it
  in first. `main` is still at `3608da0`: nothing of 25-26/10's server work is on it; pull
  requests #13 (this branch), #12 and #11 to `main` are open; merge none without the
  owner's «ναι».
- **The server deploys from this branch** (`server-deploy.yml`, on a push touching the
  site, the server files or `deployment/bot/**`). A session on another branch moves that
  trigger to its own; in the session's Auto mode the safety check refuses that change and
  its push as a production deploy, so ask the owner to switch the mode to "Accept edits"
  (the menu under the message box) and approve the push.
- **On the server now** (run `40355492889`, `9872f42` code): 523,450 products shown; So
  Divine out; the barcode brings in about 1,100 rows (InStock UK about 1,050); the bot
  (`picwise-shops.timer`, 03:40 UTC) feeds the preparation (`picwise-prepare.timer`, 04:17
  UTC) the shops' types and stock; Back to the Office 5,252 shown (782 before); 20,402 rows
  given their shop's type with its kind.
- **First thing to do:** read the night's round of 27/10, the first to read Back to the
  Office by its collections. Nothing prints it by itself: a deployment prints
  `print_shops.py` (the note's `shop_catalogues`, `balance`); the bot's own lines are in
  the server's journal (`journalctl -u picwise-shops.service --since today`), read
  through a small read-only workflow (as `server-shops.yml`, without starting a round) or
  by editing `server-shops.yml` to only print. Do not run a second round the same day
  without the owner's word.
- **Waiting for the owner's word:** the cap (measured only: by shop Finediam 68.9%, by
  aisle jewellery 72.9%; a 15% cap would keep about 97,000-162,000 of 523,450; the owner
  has not chosen a number or a grouping); the next kinds the shops' types name (mattresses,
  whiteboards, safety footwear, handheld mobile computers); HTTPS and the domain; the
  repository private; query logging from the server; 80 or 200 bot checks per shop.
  Decided: InStock UK only with its right rows (no second look); (a) "safe" as a number not
  needed (no title decides alone); Gigbain cancelled.

## Before (2026-10-26, later): the bot and So Divine built, then put on the server

The owner's answers to the three changes (26/10, later): «Γ ο κανόνας ισχύει μόνο για
προϊόντα που το κατάστημα δεν τους έδωσε καμία κατηγορία» (addition (c) agreed: the 275,000
shown with a shelf but no kind stay); «Θα κάνεις το 2 και το 3» (the bot for the shops
without a category, So Divine out); «το in stock συμμετέχει μόνο με τα προϊόντα που έχει
σωστά» (change 1, the second look at InStock UK, dropped: its rows without a category stay
out unless a barcode gives them one, and the bot never asks it); «Στα θέματα αντιστοίχισης
είχες αναφέρει για barcode ... για shopify φτιάξε τους μηχανισμούς σε αυτή τη βάση και ό,τι
έρθει σωστό ήρθε». Additions (a) "safe" as a number and (b) "enough" were not answered.
Owner's rules unchanged (see the section below).

- **Where the work is:** the branch `ccr-1361f1a7-dcpo60` (pushed): `claude/bold-allen-ljj9d7`
  brought in, plus this conversation's commits. `main` is at `3608da0`; nothing of this is
  on `main`, nor on the server.
- **Built and tested on the branch:**
  1. **So Divine out:** `eligibility.LEFT_OUT_SHOPS` (by the rows' merchant name, spaces
     and case aside); the feed gate blocks every row (`shop_left_out`, in the note per shop).
  2. **The shops' catalogues and the barcodes, applied** (`src/picwise_providers/shop_catalogue.py`,
     in `state._resolve_provider_feed_pipeline_uncached` before any row is judged): for a
     shop the bot's file knows (`PICWISE_SHOP_CATALOGUES`), its sold-out (all variants, or
     the one the address names; seen at most `STOCK_DAYS` = 3 days ago) holds a row as out
     of stock (`shop_stock`, read by `offer_health` with the feed's columns), never the
     other way; a row with no category from the feed takes its shop's type as type and
     category **only when the reading gives a kind the type names by itself** (the title
     may narrow it, "Vacuum Cleaners" + "Robot Vacuum Cleaner"; it never decides alone:
     "Designer", a type naming no kind, a title contradicting the type all leave the row
     held, as before). Then any row still without a category takes the category most
     rows with its barcode write, under the same rule (a barcode on more than 50 rows is
     ignored); this needs no file. Counted per shop in the note (`shop_catalogues`),
     printed by `print_shops.py`. A row with a category keeps its own.
  3. **The bot** (`deployment/bot/shop_catalogue_bot.py`, reusing the test's robots.txt
     reading and asking): `picwise-shops.service` by `picwise-shops.timer` at 03:40 UTC;
     `picwise-prepare.service` is ordered after it and reads its file. Shops: the note's
     with rows showable but for a category, plus those its file knows (so a shop whose
     rows got a category is asked again), never InStock UK or a left-out shop. Per shop:
     robots.txt, then `/products.json?limit=250&page=N`, 3 s apart or its crawl-delay, at
     most 200 requests a shop a round, 4 shops at a time, 25 minutes; a larger catalogue
     goes on next round where it stopped (a catalogue as large as Finediam's ~367,000 rows
     takes about 7 nights, Back to the Office's ~95,000 two). Kept on the server only
     (`/srv/picwise/shared/shops/catalogues.json.gz`, never Supabase), for the feed's
     products only: type, stock, sold-out variants, day seen; forgotten after 30 days.
     Prints shop names and counts, never an address; always exits 0.
  4. `deploy.sh` creates `/srv/picwise/shared/shops`, installs the two units and enables
     the timer; a deployment never asks the shops itself.
- **The server, from this branch (the owner's «Ναι», 26/10):** `server-deploy.yml` now
  runs on pushes to `ccr-1361f1a7-dcpo60` (also on `deployment/bot/**`) and prints the
  shops' timer; a session on another branch moves it to its own. In Auto mode the
  session's safety check refused that change twice as a production deploy, so the owner
  switched the session to "Accept edits" (the menu under the message box, "Auto") and
  the push went through (`a0d00ee`, run `40328993620`). The first round of the bot:
  `.github/workflows/server-shops.yml` (on a push of itself: `systemctl start
  picwise-shops.service`, then `picwise-prepare.service`, then `print_shops.py` and
  `print_kinds.py`), pushed only after a deployment ended, since both share the
  `server-setup` group in no set order. The nightly round runs at 03:40 UTC.
- **Pull request #13** (`ccr-1361f1a7-dcpo60` to `main`, opened by the app at 12:31 under an
  older title) is open, like #12 and #11: nothing is merged without the owner's «ναι».
- **On the server (26/10, 13:15-13:45 UTC):** deployment run `40328993620` (`a0d00ee`; its
  step "What runs on the server" failed on an apostrophe inside the quoted command, fixed
  in `1b2c4d9`): 1,123,995 rows, **518,108 shown**; So Divine 0 of 81 (`shop_left_out`);
  **the barcode brought in 1,081 rows** (InStock UK 1,041); peak memory 7.8 GB. **First
  round**, run `40329354654`: 54 shops, 331 requests, 8 minutes; the file knows 58,728
  products (53,699 with a type, 25,041 sold out). Then the preparation: **521,698 shown**
  (+3,590); Back to the Office 782 -> 3,973 shown. Of the 574,171 rows of those shops,
  124,265 found in their catalogue; **sold out by the shop 39,072, and the feed already said
  so for all but 188**: these shops' feed stock is nearly always right. Without a category
  121,574: **given their shop's type with its kind 14,395** (Back to the Office 11,651,
  Viaduct Clothing 2,148), many of them sold out; the type names no kind 18,176 ("Sold
  Out" 2,209, "PCs/Workstations" 795, "Network Switches" 708, "Network Media Converters"
  590, "Made-to-Measure" 454, "Network Cards" 378, "Security Software" 361, "Outdoor
  Sauna" 336, "Networking Software" 328, "Video Games" 291); no type 3,261; not in the
  catalogue 85,742. **Back to the Office: Shopify pages a catalogue only to page 100**
  (25,000 products; page 101 answered 400), so 24,739 of its 95,050 products were read and
  69,205 rows not found; the bot now ends the catalogue there and starts again from page 1
  (`b4ba417`). Finediam's catalogue answered 500 at page 20 (goes on tonight).
- **The owner's «Ναι» to both proposals (26/10, read as one yes for the two):** (1) a shop
  whose catalogue stops at Shopify's page limit is read on by its collections
  (`deployment/bot/shop_catalogue_bot.py`: `page_limit` kept, so the catalogue is paged
  only that far again; then `/collections.json` and each collection's
  `/collections/<name>/products.json`, one after another from a cursor kept across rounds,
  within the same 200 requests, 3 s and robots.txt; "all" and a collection said to hold more
  than 25,000 products are skipped; the list is read again after each whole pass). The
  first collections come with the night's round, 03:40 UTC. (2) The vocabulary
  (`src/picwise_nlu/product_concepts.py`): "workstation" a desktop PC; new kinds
  `network_switch`, `media_converter`, `network_card`, `software` (only its full names,
  "security software", "antivirus", "networking software", ...: a bare "software" stays
  not understood, as `test_live_search_resolver` pins "accounting software"), `video_game`,
  `sauna`. Tests: `tests/test_picwise_kinds_from_the_shops_types.py`;
  `test_picwise_strict_kind_reading`'s unknown label "Networking Software" became "KVM
  Switches". Misspelling benchmark unchanged (93.8%, 0 wrong). The note now lists 30
  types naming no kind. **On the server** (run `40351335007`, `a701306`, the bot's file of
  13:27): 522,733 shown (+1,035); given their shop's type with its kind 18,325 (+3,930),
  naming none 14,246; Back to the Office 4,572 shown (782 in the morning). The types left
  naming no kind, the most first: "Sold Out" 2,209, "Made-to-Measure" 454, "Bedding" 274,
  "Smart Wearable Accessories" 262, "Power Distribution Units (PDUs)" 195, "Power Adapters &
  Inverters" 194, "Console Servers" 193, "Labret Lip Rings" 190, "Servers" 184, "Video Cable
  Adapters" 178, "Ring Binders" 175, "PCs/Workstations" 168 (titles naming another kind),
  "Network Switch Components" 145, "TV Mounts & Stands" 138, "Monitor Mounts & Stands"
  135, "Hardware Firewalls" 129, "Wireless Access Points" 128, "Memory Cards" 112, "Tablet
  Cases" 111, then folders, power supplies, batteries, "Carbon Offset", sweatshirts, pens,
  privacy filters, markers. Mounts, cases and parts are accessories and stay out; memory
  cards, servers, access points, firewalls, batteries, bedding, sweatshirts and pens are
  kinds the vocabulary could learn next (put to the owner).
- **The second list of kinds (owner: «Ναι παίρνω και αυτά τα είδη», 26/10):** new kinds
  `memory_card`, `server` (a bare "server" too; "Salad Servers" on a kitchen shelf stay
  doubtful by the aisle rule), `access_point`, `firewall`, `battery` (full names; a bare
  "battery" is weak, and no bare Greek "μπαταρία", which is also a tap), `pen` (a bare
  "pen" is weak: "pen drive"), `marker`, `folder`, and `bedding`, now broader than bed
  linen, duvets, pillows and bedspreads ("bedding" finds them all); "sweatshirts" and
  "power supply units" added to their kinds. Why they were out, told to the owner: their
  shops send no category to Awin, a row without one is not shown, and the type the bot
  found named a kind the vocabulary did not know. Tests:
  `tests/test_picwise_kinds_from_the_shops_types.py` (5);
  `test_picwise_kinds_from_the_build_list` expects a duvet and a bedspread to be bedding
  too. Full run: only the two that failed before fail; misspelling benchmark unchanged.
  On the server (run `40355492889`, `9872f42`): **523,450 shown** (+717); Back to the
  Office **5,252** (782 in the morning); given their shop's type with its kind 20,402
  (+2,077), naming none 12,169; kinds with products from at least 3 shops 94 of 257 (84 in
  the morning). Left naming no kind, besides accessories and parts: "Safety Footwear" 90,
  "Handheld Mobile Computers" 87, "Diamond Ring" 84, "Mattresses" 83, "Whiteboards" 83,
  "UPS Batteries" 81, "Laptops" 76 (titles naming another kind), "Electric Converters" 75.
- **Why so few electronics (owner, 26/10):** the feed holds only the 85 programmes the
  owner joined and was accepted to, mostly small fashion, jewellery and home shops; no
  large electronics shop. Electronics shown: 9,087 (1.8%), plus what Back to the Office's
  types now bring. Gigbain accepted the owner, but it is not in the feed: the link keeps
  the shops chosen when it was made (`docs/awin_feed_setup_el.md`), so a new link with it
  would go into the `AWIN_FEED_URL` secret, then a deployment. **The owner cancelled it
  («Άκυρο για το συγκεκριμένο κατάστημα gigbain», 26/10): Gigbain stays out; do not ask
  again.**
- **The cap, measured (the owner's «Ναι» read as also for "measure first"):**
  `src/picwise_providers/catalogue_balance.py`, the note's `balance`, printed last by
  `print_shops.py`: per department and aisle (the top and two levels of Google's shelf,
  British names read as US; the shops' own categories one group), per shop and per
  narrowest kind, the largest groups and their shares, and what a 15% cap keeps (each
  group at most C, the largest C with no group over 15% of what all keep; none with fewer
  than 7 groups); and (b) "enough": kinds with products from at least 3 shops. Nothing
  shown changes. Its numbers come with the first deployment.
- **The owner's proposal of a cap (26/10):** no kind more than about 15% of all products,
  so that a shop of 100,000 watches does not make PicWise "a watch site", which also
  helps the checks. Analysis given: right, and needed now (Finediam, jewellery, is 70% of
  the server's 518,041 shown); count it **per department** (from the shop's shelf: most
  jewellery has no PicWise kind, so a per-kind cap would not see it) **and per shop**;
  when cutting keep first the products sold in more than one shop, then a fair share per
  kind and per price band, cheapest first within each (not only the cheapest, or an
  expensive search finds nothing); stable from night to night (Google); the share is of
  the total after the cut, which needs at least 7 departments of some size, else a
  floor; today it would cut most of the jewellery and leave under half the total; it
  does not fix "too few of another kind" (only new shops or networks do). Recommended:
  **measure first, nothing shown changed**: built (below the deployment's block).
- **Open, the owner's, from before:** HTTPS and the domain; the repository private; query
  logging from the server (ask first); 80 or 200 bot checks per shop and what a low score
  does; (a) and (b) above.

## Before (2026-10-26): the rows without a category, after the shop test

The owner ended the conversation of 25-26/10 with «Θα προχωρήσουμε αυτές τις αλλαγές σε
άλλη συζήτηση»: the three changes below wait for their «ναι», each on its own. Owner's
rules, unchanged: Greek, short, plain words; say what you found before building
anything; nothing on `main` without their explicit «ναι»; never ask for the feed link
(it holds the key); secrets only in GitHub's or Vercel's secrets, never in the
repository, a log or the chat; nothing in Supabase without asking; the truth test is a
bot's, never the owner's by hand; never open an Awin tracked link from a session or a
bot; never propose contacting the shops («δεν στηρίζομαι σε αυτούς»).

- **Where the work is:** the branch `claude/bold-allen-ljj9d7` (pushed; bring it in
  first). `main` is at `3608da0` (the two kind fixes, live); the branch's server files,
  measurements and the shop test are not on `main`. Pull requests #12 (this branch) and
  #11 (`ccr-baaad713-r3uvvs`) to `main` are open; nothing goes to `main` without the
  owner's «ναι». `server-shop-test.yml`, like `server-deploy.yml`, runs on pushes to
  this branch; a session on another branch moves those triggers to its own.
- **The owner's direction (26/10):** rows that can be mapped safely and sorted rightly
  join the catalogue; rows no category can be given, also after the bot's check, stay
  out (today's state already: the prepared catalogue keeps only the feed's eligible
  rows); if too few products are left, another network joins (CJ or any other).
  «Βρέθηκαν επίσης» is dropped. Three additions wait for their word: "safe" as a number
  (a title's kind alone only for the kinds measured right 99% on rows with a shelf),
  "enough" counted as kinds with products from at least 3 shops, and the rule only for
  rows with no category from the shop (the about 275,000 shown with a shelf but no kind
  yet stay).
- **What the shop test found** (run `40309611314`; details in the bullet "The shop
  catalogue test, run once" below): 53 of the 56 shops publish Shopify's catalogue,
  with each product's stock and, for 33 shops (32,306 rows), a type on nearly every
  product; paging past 5,000 works; **InStock UK (353,023 of the 388,813 rows) answers
  500** on its catalogue, and the one row of it asked has no type.
- **The three changes put to the owner (each on its own «ναι»):**
  1. **A second, small look at InStock UK only** (about 10 requests, under the same
     script's rules: robots.txt first, 3 s apart, never an Awin link): its
     `/collections.json`, one or two collections' `/collections/<name>/products.json`,
     and a few more of its rows' `/products/<name>.js`, to see whether a category is
     anywhere. If none, its rows have the title only, under the "safe" rule above.
  2. **The bot for the 55 other shops**, each night after the feed: per shop its
     robots.txt, then its Shopify catalogue (250 products a request, at most 200
     requests a shop a round): the shop's own type and each product's stock, matched
     to the feed's rows by the product name in the address; what it learned kept on
     the server (never in Supabase), so a round asks only for what is new; a row whose
     type reads as a kind joins the catalogue, else the title decides (Finediam reads
     worse with its type), else it stays out. User agent `PicWiseBot/0.1
     (+https://picwise.subby.cloud)`.
  3. **So Divine out:** it sells adult products and the server shows 72 of its 81
     rows; the site has no adult rule.
- **Open, the owner's, from before:** HTTPS and the domain (own domain recommended
  before any indexing); the repository private; query logging from the server (ask
  first); 80 or 200 bot checks per shop and what a low score does.

## Before (2026-10-25, later, to 2026-10-26): every Google-format shop on the server; the kind problem on it

The owner put the link with every Google-format shop in GitHub's secrets («ετοιμο»,
25/10); the server reads it, and the deployment now names each shop of the feed.

- **Where the work is:** the branch `claude/bold-allen-ljj9d7` (pushed): the branch
  `ccr-baaad713-r3uvvs` brought in, plus this conversation's commits. Bring it in first.
  `server-deploy.yml` now runs on pushes to this branch; a session on another branch
  moves that trigger to its own. `server-setup.yml` and `server-check.yml` still name
  `ccr-baaad713-r3uvvs`: move their trigger only when they are needed (moving setup's
  runs the setup, which may reboot). The pull request from `ccr-baaad713-r3uvvs` to
  `main` (#11) is open and lacks this branch's commits; nothing goes to `main` without
  the owner's «ναι».
- **The server works** (OVHcloud VPS-4, London, Ubuntu 24.04.5, 8 vCores, 22 GiB usable,
  191 GB free; renewal automatic monthly, next 24/11): secured (updates daily with a
  reboot at 03:30 UTC when needed, SSH by key only, ufw 22/80/443, fail2ban); the site
  under gunicorn on 127.0.0.1:8016 only (nothing from the internet, so Google cannot
  see it); the catalogue prepared at each deployment and nightly at 04:17 UTC. A session
  cannot open SSH: everything goes through GitHub workflows (read their logs with the
  GitHub tools). Secrets are sent only to a server whose host key matches the pin.
- **Now on the server: every Google-format shop** (re-run of run `40189917132`, attempt 2,
  and run `40192893502`, both success): **1,123,857 rows from 85 shops; 518,041 products
  shown, from 77 shops; 605,816 rows held** (mostly no category: InStock UK 384,393,
  Back to the Office 93,662; then out of stock). The preparation: peak memory 7.4 GB
  (ceiling 16 GB), 6.8-8.5 min, a 47.5 MB file; the site 3.1, 4.5 and 5.8 GB after three
  deployments (ceiling 12 GB; likely each worker that served a search holds the
  catalogue, about 1.3 GB each, not measured per worker: to watch after a nightly
  reload). So it fits without the PostgreSQL change. **`AKKO UK`, `EMOKO BIKE`, `Sinocare` and `World
  Businesses for Sale` are not in the feed** (read by the bot in the shop list:
  `deployment/server/print_shops.py`, step "Each shop of the prepared catalogue").
  `Finediam` (jewellery) has 360,067 of the 518,041 shown (70%), so the suggestions are
  full of rings and watches; `InStock UK` brings 509,939 rows (45% of the feed). 8 shops
  show nothing: NORVEXA ADVISORY LTD, Frenzy Clothings, Beauti Outlet, myCord | Bracelet
  Lab, Handbags Infinity Fashion, Purr and Mutt, Bluebells Flora Florist, Wilna Kitchen.
  Two names do not read as shops, for a bot to check what they sell: `Shopping Ads:
  Google & Bing` (6,798 shown) and `NORVEXA ADVISORY LTD` (13,227 rows, none shown).
  No adult shop; `Affiliates - Spoiled Brat` is a Glasgow clothing shop, kept
  (Companies House showed overdue accounts and a strike-off proposal: for the shop
  checks later).
- **The 12 searches against live: 0 of 12 the same, many the wrong kind.** "vacuum
  cleaner": Colleen Hoover books (Lets Buy Books); "mouse": chocolate mice; "tv": a
  "DEATH BY TV" hoody and Islamic digital learning packs; "speaker": banana plug
  connectors; "camera": a camera module among the cheapest. The kind problem of 23/10
  (section below), much larger with many shops.
- **The two measures, built and read (owner: «Να προχωρήσουμε τις δύο μετρήσεις», and
  how not to lose so many products without a category; also: a feed may not tell the
  truth about stock, «για αυτό χρειαζόμαστε τους ελέγχους»).** On the branch only, in the
  public note and printed by the deployment (steps "Each shop of the prepared catalogue"
  and "Kinds that may be wrong in the prepared catalogue"); run `40200815389`, release of
  `85f0a4a`. Measured only: nothing shown changed.
  - **Rows without a category: 532,610**, 532,593 held for that alone. **None carries the
    shop's own category (`product_type`)**, so reading that column would bring in
    nothing. Passing today's other checks (in stock by the feed's word, a price, an
    image), **388,781 could be shown if the title alone gave the kind**: the title reads
    204,124 as a kind, 22,350 as an accessory, 51,430 as doubtful, 110,877 as nothing.
    InStock UK is 353,023 of them (193,233 with a kind), Back to the Office 23,807.
  - **Kinds of the 518,041 shown** (411,717 with a kind): the title names none of its
    kinds on 176,239, and **"watch" alone holds 169,271, of which 167,551 are not
    watches** (piercing oil and ear expanders of MonsterPiercing on "Body Jewellery",
    Finediam's jewellery). Most likely cause, reproduced locally, not yet seen in the
    server's own category text: a shelf like "Jewellery & Watches > Body Jewellery"
    whose narrowest part names no kind, so the code reads the parent "Jewellery &
    Watches" as watches. The title alone names the kind, not the type or shelf, on
    6,518: right for hoodies and jumpers, wrong for "Chocolate Mice" (mouse), "Giant
    Apple Cable" sweets (charging cable), "Voice Tablets" sweets (tablet), a "Rat &
    Mouse" bait (mouse), the book "Make Your Bed" (bed), a model paint's "Protective
    Coat" (jacket), incontinence "Pants" (trousers).
- **The watch error fixed on the branch** (owner: «ναι, ξεκίνα με το ρολόι»; commit
  `6aff4fe`, run `40205899827`; **not on `main`**). The server's shelves are Google's
  British taxonomy: "clothing & accessories > jewellery & watches > body jewellery".
  An aisle listing a kind with something PicWise has no kind for now gives that kind
  only when the title names it, otherwise the narrower shelf decides; the narrowest
  shelf keeps its kind ("Skillets & Frying Pans" stay cookware). Of Google's 5,595
  shelves read with no title, two change (access points and network bridges under
  "Bridges & Routers" are no routers). On the server: products shown as a kind
  411,717 -> 243,908, titles naming none of their kinds 176,239 -> 10,865, "watch"
  169,271 -> 1,751 products (31 suspects); the 12 searches show the same cards as
  before. The kind lists now give each kind's three whole shelves. Left, seen in the
  same list: titles alone giving a kind on another department's shelf, "barbell" 951
  (piercing barbells on "body jewellery", were watches), "bag" 448 (291 on "sweets &
  chocolate"), "bed" 212 (149 on "pet supplies"), chocolate mice as mice.
- **A title alone on another department's aisle, fixed on the branch** (owner: «ναι,
  προχώρα στο επόμενο λάθος»; commits `55a5477`, `45ab1d7`, `772855b`, `00ebb22`; **not on
  `main`**). When no shelf names a kind and the title decides
  (`concept_understanding._title_fallback_head`), the title's kind is now doubtful if the
  category is an aisle of Google's taxonomy whose shelves name no kind of that
  department (`mega_category_id`, or a broader kind's: a smartwatch is a watch);
  `_aisle_departments` gathers them once from `taxonomy.en-US.txt`, each shelf read as it
  is and in the singular; the two-level aisle counts, or its top when it names no kind;
  an aisle whose name names the kind holds it ("Toys & Games"); British aisle names map
  to the US ones (`_BRITISH_AISLE_NAMES`). Doubtful products are still found by their
  words. The note lists what the rule doubted (`kinds_before_the_aisle_rule`), and the
  deployment's comparison prints each server card's shelf and kinds (it copies the
  prepared catalogue to the runner). **On the server** (run `40216310561`): 1,860 shown
  products doubted, nearly all rightly: 941 piercing barbells, 291 sweets as bags, 85
  chocolate mice, sweets as cables, tablets, belts and watches, books (Colleen Hoover,
  slow cooker and air fryer cookbooks), model kits ("Retro Scooter - Model Kit"), pet
  clothes, incontinence pants, tumbler cases as phone cases. Wrongly: 6 smartwatches
  InStock UK files under "Electronics > Video > Video Multiplexers", 8 baby hooded
  towels, 2 baby brush sets. The first version (`55a5477`) also doubted dining sets, sofa
  suites, futon beds, tote bags, toys and every electric massager (2,062 in all); the
  last one keeps them. The 12 searches: "vacuum cleaner" shows real vacuum cleaners,
  "mouse" no chocolate mice, "tv" no hoodie; still wrong on "mouse": a craft stamp set
  "Squeak the Mouse" and a "Self Tan Mousse" (coarse departments; "mousse" read as
  mouse).
- **Both fixes on `main` and live** (owner: «Ναι», 25/10): commit `3608da0` on `main`
  holds only `concept_understanding.py` and the two test files, not the server's files;
  the 107 related test modules (1,138 tests) pass on `main` but the two failing there
  before. Vercel deployed it ("Deployment has completed"); the live site prepared at
  18:50:06 UTC, and its 12 searches show the same cards as before (the errors were in
  the server's larger feed, not in the live 20 shops). `main` is merged into this branch.
- **The title alone against the shelf, measured** (owner: «Ναι»; commit `62fbf93`, run
  `40223470414`; note key `title_alone`, printed by `print_kinds.py`): of 81,601 shown
  products whose type and shelf alone give a kind, the title alone gives one to 52,024
  (63.8%), **the shelf's own kind for 50,445 (97.0% of those)**, another for 1,579; none
  for the rest (doubtful 11,681, nothing 17,174, an accessory 722). **InStock UK: 70.0%
  get a kind, 94.6% of them the shelf's**; Finediam 100%; "Shopping Ads: Google & Bing"
  (it sells Nike trainers) 1.6%: "Iron Grey" read as an iron, "Football Grey" as a
  football. Of the disagreements, about half are the title being right where the
  lexicon links no two kinds (bedside tables on "Bedside Tables" read as tables, dash
  cams, heat pumps, lunch boxes, bracelets on InStock UK's bare "Jewellery & Watches"
  shelf), half title errors (suit -> trousers 623, mattress -> bed 176 by the brand
  "Starlight Beds", boxer shorts -> shorts, bean bag chairs -> bag, mixer grinder ->
  angle grinder). For the 388,781 rows without a category this means about 204,000
  could get a kind from their title, most of them right, a few thousand wrong, and
  about 185,000 none (found by their words only).
- **Rows without a category: the owner's direction (26/10)** «Ο στόχος είναι να λύσεις
  αυτό το πρόβλημα»; **no contact with the shops** («δεν στηρίζομαι σε αυτούς»; never
  propose it again); rows that cannot be mapped stay **outside the price logic** (shown,
  not compared); the shop-check bot has a **double role**: check the feed's stock and
  give category information, within its 200 checks per shop. The owner cancelled
  showing them on the server with the title's kind («Σταμάτα», «Ακυρώ») before that.
- **Where else a category hides, measured** (commits `d5693cb`, `bb0d8f8`; runs
  `40298361738`, `40300435259`): of the 388,813 rows a search could show by their title,
  **no column names a category** (they fill advertiser_id, advertiser_name,
  availability, aw_deep_link, brand, condition, description, id, image_link, link,
  price, title, identifier_exists, mpn, gtin: no custom label, no product type); **the
  shop's address names only "products"** (`.../products/<name>`, Shopify's form; read
  from the Awin link's `ued` as text, never opened); **a barcode** on 63,359, another row
  with a category for only 620 (a kind for 137, 28 where the title gives none); **the
  description's first sentence** gives a kind to 2,424 of the 184,675 the title gives
  none (on rows with a shelf: 5.5%, 93.3% agreeing). So from the feed only the title
  maps them: about 204,000, of which about 95% right (InStock UK 94.6%); about 185,000
  cannot be mapped from the feed.
- **The owner's proposal (26/10), replacing «Βρέθηκαν επίσης»:** rows that can be mapped
  safely and sorted rightly in search join the catalogue; rows no category can be
  given, also after the bot's check, are dropped («πόσες μετατροπές μπορείς να κάνεις
  σε προϊόντα τα οποία είναι κρυφά ... το μόνο που κάνουν είναι να πιάνουν χώρο»); if
  the products left are not enough, another network joins (CJ or any other);
  «Αρκετά ασχοληθήκαμε». So **«Βρέθηκαν επίσης» is dropped**, nothing to build for it.
  Asked for an evaluation; given: right, and today's state already (rows held for no
  category are not in the prepared catalogue, only counted in the note; each night's
  preparation lets a shop's row in once it has a category); three additions put to
  the owner, **waiting for their word**: (a) "safe" as a number: a title's kind
  accepted alone only for the kinds whose title reading measured right nearly always
  (99%) on rows with a shelf, the rest only when the bot confirms them; (b) "enough"
  measured in comparisons, not products: how many kinds have products from at least 3
  shops (Finediam is 70% of what is shown); a new network passes the same gates by
  itself; (c) the rule is for rows with **no category from the shop** only: the about
  275,000 shown with a shelf but no PicWise kind yet (more than half jewellery: "ring"
  gives none) stay, and the vocabulary grows. The bot (stock and category, 200 checks a
  shop, never an Awin link) asks pages of the shops' sites: only on the owner's «ναι».
- **The shop catalogue test, run once** (owner: «ναι, ξεκίνα τη δοκιμή στα 56
  καταστήματα»; commit `364654e`, run `40309611314`, 11 minutes, 217 requests from the
  server as `PicWiseBot/0.1`; `deployment/bot/shop_catalogue_test.py`, run by
  `.github/workflows/server-shop-test.yml` on a push of either file; it reads the
  feed's copy in the download cache, so no key). Of the 56 shops with rows a search
  could show but for a category: **53 publish Shopify's catalogue** (`/products.json`);
  every robots.txt allowed what was asked, none set a crawl-delay; the catalogue says
  each product's stock, and its product names match the feed's addresses (Back to the
  Office: 239 of 250 in the feed). **Paging past 5,000 works** (Back to the Office and
  Finediam gave 250 products on page 21). **Back to the Office** (23,825 rows): a type
  on every product, real ones ("Windows Laptops", "Chromebooks", "Televisions", "Toner
  Cartridges"); a kind from type and title for 70.4% against 52.4% from the title
  alone. 33 shops (32,306 rows) give a type to at least 80% of their first page; some
  types name no kind ("Designer", "Everyday", "Consumable", "Crystal Art"), so a type
  that gives none must leave the title to decide (Finediam: 54.0% with its type, 72.4%
  from the title alone). **InStock UK (353,023 rows, 91%) is not solved by it**: Shopify
  (its product page answered), but its catalogue answers 500 (pages 1 and 21), and the
  one row asked has no type (a mirror, which its title names). Not asked: Juicy Couture
  UK (no shop address in its rows), Pro Espresso (its robots.txt redirects to another
  site). **Seen by the way: So Divine sells adult products** (vibrators, bondage), and
  the server shows 72 of its 81 rows: the site has no adult rule, the Google spec wants
  none on Google's pages, and the owner's plan of 22/10 left adult content out of the
  feed link (the handoff's "no adult shop" above was read from names only). Put to the
  owner, **waiting for their word**: (1) a second, small look at InStock UK only (its
  collections and a few more rows); (2) the bot for the 55 other shops (category and
  stock from their catalogues); (3) So Divine out.
- **Before, put to the owner:** (2) before any row
  without a category is shown by its title, measure how often the title alone agrees
  with the shelf on the rows that have one (per shop: InStock UK has both); (3) ask
  Awin or the two largest shops (InStock UK, Back to the Office) for their categories;
  (4) then the shop checks the owner planned (set hours, 200 checks per shop, the
  shop's own link, robots.txt, a gentle pace), which say whether a feed's stock is
  true. Code goes to `main` only on their «ναι».
- **Open, the owner's:** HTTPS and the domain (own domain recommended before any
  indexing); the repository private (logs are public; nothing secret is in them);
  query logging to Supabase from the server (ask first); 80 or 200 bot checks per shop
  and what a low score does.

## The conversation of 2026-10-23: the server; nothing left out of what is kept

The owner opened a new conversation for a smaller kept file, then the server («Θέλω να
ανοίξουμε νέα συζήτηση γιατί αυτή έχει βαρύνει και το φτιάχνουμε εκεί»). The smaller
file was then stopped by the owner's rule below.

- **Where the work is:** the branch `ccr-baaad713-r3uvvs`, which took in
  `ccr-c30938cf-v749ay`'s notes. Its code is `main`'s (last merge `7b9624c`, 23/10 16:08
  UTC); it is ahead only by notes (PROGRESS and this file). Bring it into the next
  session's branch first.
- **The server: bought, reachable, checked (25/10).** OVHcloud VPS-4 2027 in London
  (Erith): Ubuntu 24.04.4, 8 vCores, 24 GB, 200 GB NVMe, €23.49 a month, no
  commitment; renewal automatic every month (set 25/10; next 24/11). Login by the
  owner's ed25519 key only, user `ubuntu`. The owner set the GitHub Actions secrets
  `SERVER_HOST`, `SERVER_USER` and `SERVER_SSH_KEY`; `AWIN_FEED_URL` not yet (made
  again in Awin's Create-a-Feed when the site moves). The repository is public: the
  server's address never goes into it or into a log (GitHub masks secrets). The session
  cannot open SSH (only HTTPS on 443), so the server is worked through GitHub
  workflows; the read-only `.github/workflows/server-check.yml` (this branch only)
  logged in on 25/10 (PROGRESS, 25/10). **Set up for security on 25/10** (owner's
  «ναι»): up to date (Ubuntu 24.04.5), daily security updates with a reboot at 03:30
  UTC when needed, SSH by key only and no root login, ufw letting in 22, 80 and 443
  only, fail2ban; `deployment/server/base_setup.sh`, run by
  `.github/workflows/server-setup.yml` (this branch only; a rollback undoes SSH and
  firewall in 10 minutes unless a fresh login cancels it; the log masks the server's
  names), run `40187243206`. **The site runs there since 25/10** (owner's «ναι»), with
  today's code and no feed yet (the owner has no link ready): gunicorn on 127.0.0.1:8016
  only (nothing from the internet, so Google cannot see it), the catalogue prepared at
  each deployment and nightly at 04:17 UTC; `deployment/server/deploy.sh` by
  `.github/workflows/server-deploy.yml` (this branch only), which then compares 15
  pages with the live site: 11 the same, the 4 others differ only by the feed (run
  `40188479854`). **With a feed since 25/10:** the owner's `AWIN_FEED_URL` (a
  new-style Awin link with 2 feeds; Vercel reads 20 shops), sent only to the server
  whose host key matches `.github/server-host-key.pin` (an HMAC under the deploy key,
  `.github/scripts/host_key_pin.py`); 1,040 products prepared; of the 12 searches,
  `camera` shares three of four cards with live, the rest differ by the shops (run
  `40189276811`, PROGRESS 25/10). Next, the owner's: the same 20 shops or a larger
  link; then HTTPS and the domain, only on the owner's word. The owner's guide:
  `docs/ovhcloud_server_setup_el.md`.
- **Owner's rule (2026-10-23): nothing that may serve the pages Google indexes is left
  out of what PicWise keeps.** In their words: «Δεν πρέπει να διαγράψεις τίποτα που θα
  επηρεάσει την ποιότητα χαρακτηριστικά seo ... Τα προϊόντα που θα καλούνται από την
  google μέσω λέξεων κλειδιών θα πρέπει να χτίζουν ένα πεδίο το οποίο να είναι πλήρες
  και να προσθέτει υπεραξία στη σελίδα με βάση τα δεδομένα και τα κριτήρια που έχει η
  google ... Δεν πρέπει να υπάρχουν επιπτώσεις στην κατάταξη ... αν αυτή η ενέργεια που
  ετοιμάζεσαι να κάνεις θα φέρει κακά αποτελέσματα στο μέλλον τότε σταμάτησε την».
- **The specification: `docs/PICWISE_GOOGLE_PAGES_SPEC.md`** (owner, 23/10: «Ναι,
  γράψ' το ως προδιαγραφή μόνο εάν είναι ο βέλτιστος τρόπος ... μόνο εάν αυτό είναι
  πλήρως συμβατό με τις προδιαγραφές της google»). Written after checking each part
  against Google's published rules; nothing in it is built. One correction to what was
  put to the owner before: no page per keyword. Google's guide of May 2026 calls
  separate content for every wording of a search scaled content abuse, so a page stands
  for one distinct set of products (category, kind, kind with a property) or one
  product, and a keyword's variations map to that page. That conflicts with the
  founding documents' long-tail landings (raised; "Known doc conflict" below). Read the
  specification first.
- **Its first step, on `main` since 23/10 18:15 UTC and seen live** (merge `47cd76b`,
  owner: «Ναι, να μπει στο main και κάνε τον έλεγχο»; live check run `40001929114` at
  18:16, PROGRESS 23/10). Built on the owner's «Ναι, βάλε το noindex
  στο /search και προστάτεψε το site από την google όσο το χτίζουμε»: `noindex` on
  every page that shows a search (`/search`, `/results`, `/picwise-reference`, `/?q=`;
  the home page without a search stays indexable) and on `/demo`; a `robots.txt`
  keeping crawlers off `/out/` (the redirect to the shops records a click),
  `/subby-proof` and `/cron/`, not off `/search` yet (Google reads `noindex` only on a
  page it may fetch); `X-Robots-Tag: noindex` on the JSON routes. Both route tables;
  `tests/test_picwise_google_protection.py`. The live check now prints all of this
  (`.github/workflows/live-check.yml` on `ccr-fd5dc1bc-4vgsgl`, `39665da`, owner's
  leave): it waits for a deployment that serves `/robots.txt`, then prints it, the
  robots tag of each page and the JSON routes' header. Next, from the specification:
  `Disallow: /search` once Google has dropped those pages (needs Search Console to see
  it), then the catalogue on the server.
- **The server's architecture: `docs/PICWISE_SERVER_ARCHITECTURE.md`** (owner's request
  of 23/10, in English: database and search for 0.8-1M products, URLs and markets, the
  store validation bot, text from the data). Nothing built. In short: PostgreSQL only (no
  Meilisearch, no Redis), PicWise's own understanding and price-first rules kept as they
  are; pages rendered each night and cached at Cloudflare; `/uk/` and `/us/` on one
  domain with `hreflang`, no redirect by country; the bot visits only the shop's own
  `link` (never `aw_deep_link`), keeps `robots.txt`, never evades a block, writes its own
  tables, runs by a systemd timer after the load; text only from computed facts. It
  corrects the brief: Hetzner US East is about three times dearer since June and its
  cheap plans are not sold; 1M products and the bot need 16 GB at least (OVHcloud VPS-4,
  24 GB, about $23 a month, put to the owner); 80 or 200 checks per shop is the owner's
  setting; a domain of PicWise's own before indexing. Open, the owner's: provider and
  size, domain, the checks per shop, what a shop's score changes.
- **Owner's direction (2026-10-23): the business runs on Google.** «Η αρχιτεκτονική
  πρέπει να τηρεί αυστηρά την υψηλότερη ποιότητα και απαιτήσεις της google... Το
  business τρέχει γύρω από το seo... adwords ή διάδοση μέσα από social media
  δευτερεύουσας σημασίας... στοχεύει κυρίως σε χαμηλής επισκεψιμότητας keyword εκεί που
  ανταγωνισμός είναι μικρός... σε μεγάλες αγορές με μεγάλο όγκο προϊόντων... ένας
  χρήστης ζητάει μία λέξη κλειδί θα δώσει μία σελίδα όπου θα δει 4 προϊόντα κι όλα τα
  υπόλοιπα στοιχεία που ζητάει η google». Put to the owner the same day, not decided
  (PROGRESS, 23/10, "The page for a Google keyword, put to the owner"): `/search` kept
  out of Google; one fixed page per chosen keyword, in a browseable hierarchy, indexed
  only past a quality gate; its contents; Google's three risks (doorways, scaled
  content, thin affiliation); and, since Google gives product rich results only to a
  page about one product, a page per product with every shop's price.
- **Owner's decision (2026-10-23): every product gets a page, not only those two shops
  sell.** «Άν ενα προϊόν δεν μπορεί να συγκριθεί με άλλον πωλητή τότε θα εμφανίζεται
  μόνο του σε αυτή την περίπτωση θα έχει πιο πλούσια περιγραφή η οποία θα προστίθεται
  από κάποιο σύστημα Ai το οποίο θα επιμελείται το περιεχόμενο.. η σελίδα θα έχει
  διαφορετική δομή... Σε κάθε άλλη περίπτωση θα χάσουμε τεράστιο όγκο προϊόντων». So an
  AI system curates the content of a one-shop product page (the owner's call, which the
  earlier "code first, AI only if code cannot" leaves to them). Put to the owner, not
  decided: the conditions Google's guidance sets (PROGRESS, 23/10, "A page for every
  product").
- **Owner's requirement for the server's catalogue (2026-10-23):** «το αρχείο που
  μαζεύεται στο server με τα προϊόντα θα πρέπει να έχει τέτοιο μηχανισμό έτσι ώστε
  τμηματικά να κρατάει αυτά που πρέπει να διαγράφει αυτά που πρέπει και τελικά η
  χωρητικότητα να υπολογίζεται με βάση τα ζωντανά πραγματικά είδη ώστε να μπορέσουμε να
  παραμείνουμε στο version εννοείται σε κάποιο πακέτο του». Put to the owner, not
  decided (PROGRESS, 23/10, "The server's catalogue keeps only live products"): each
  night shop by shop, added, updated, or marked gone; deleted with its text and page
  after a number of days (30 proposed); a failed or much smaller feed deletes nothing;
  room only for live products, about 6-10 KB each with everything; a morning report
  against the plan's limit. **Decided by the owner the same day:** 30 days, and
  meanwhile the product's page stays, says it is temporarily unavailable and suggests
  similar products, as Google advises («30μερες»; «η σελίδα δείχνει προσωρινά μη
  διαθέσιμο και προτείνει άλλα παρόμοια προϊόντα όπως προτείνει ο κανονισμός της
  google»). The rest of the mechanism is not decided yet.
- **The smaller kept file: stopped, nothing built** (PROGRESS, 23/10, "The smaller kept
  file stopped"). It would have left out the 46 Google-format columns no rule reads and
  descriptions over 500 characters (the search never matches them), with the same
  searches. Google calls affiliate pages that copy the shop's description "thin
  affiliation" and names price information, comparisons, testing and navigation as the
  value; the future pages for Google need exactly those columns (specs, sizes, colours,
  dimensions, energy class, extra images, delivery cost, unit price, pack size, the adult
  flag, variants) and the full description as material to read facts from, never to
  copy. Today's pages show none of them, so what Google sees today would not have
  changed. Instead (put to the owner, not decided): keep everything, and solve the size
  on the server, with every product's full row on disk and in memory only what the
  search reads.
- **Then the server** (not decided, nothing bought or built): the owner will bring in
  every Awin shop (a Product Count of about 1,300,000, from memory) for the UK and the US
  first, later every euro country, on a server the owner buys. Put to the owner: one VPS
  near London (8 GB of memory and 80 GB of disk to start; the full rows of 150,000-600,000
  shown products are about 0.6-2.5 GB unpacked at the owner's file's 4.1 KB a row, the
  20-90 MB said before assumed the smaller file), a free CDN in front; the site served by
  the same server; each night the feed downloaded and read row by row (about 0.4 GB
  gzipped), every shown product's full row written to a database on disk, by kind, and
  only what the search reads held in memory; the bot on the same server later. Memory
  is to be measured when this is built. The same workflow: the session's branch, the
  owner's yes, `main`, a GitHub workflow that deploys to the server with a key the owner
  keeps in GitHub's secrets (never in the chat); the live site checked through GitHub,
  or directly if the owner adds the server's address to the environment's allowed
  domains. A catalogue per market (GBP, USD, EUR). The site stays on Vercel until the
  server is ready.
- **Answered 23/10: the Awin format does not matter** (owner: «Εμείς δουλεύουμε με
  google feed... Awin feed δεν μας ενδιαφέρει και αν πιάνει χώρο πέτα το»). The
  Awin-format `LEFT_OUT_COLUMNS` (on `main` since 20/10) stays as it is: none of its
  names is one of the 62 Google-format columns, so it leaves nothing of the Google feed
  out, and nothing of the Awin format takes room in what the live site keeps (its feed
  is Google-format). Nothing was changed.
- **Answered 23/10:** the `/search` pages carried no `noindex` and the site had no
  `robots.txt` (`/robots.txt` answered 404); the owner said to keep the search out of
  Google, built on the branch (above).
- **The kind work** is on `main` (merges `9429bca`, `95d0961`, `7b9624c`), and the owner
  stopped it here («Δεν θέλω να ασχοληθώ άλλο με αυτή τη διαδικασία»). The build's own
  list of suspects (`/prepared.json`, `kinds`) is how to comb later; its open points are
  in PROGRESS, 23/10 ("The fixes from the first list to `main`").
- **The owner's files** of 23/10 (Pro-Camera and SafeFort, Google format) reached only
  the earlier session: ask for a file again when one is needed, never for the link. A Google-format
  feed cannot be made with chosen columns in Create-a-Feed, and a file of Back to the
  Office is too large to upload.

## Before: the kind problem (owner, 2026-10-23)

The owner moves the work on product kinds (a search that shows a product of another
kind) to a new conversation: «Αυτό το πρόβλημα θα το λύσουμε σε άλλη συζήτηση».

- **Where the work is:** commit `964fbdf` ("Read a product's kind against the noun its
  title ends with"), **on `main` since 2026-10-23** (owner: «Ναι για το main»; merged
  from the branch `claude/tender-einstein-6nbbs8`), so a new session has it. What the
  live site shows since: PROGRESS, 23/10.
- **Live since 23/10 08:09 UTC, and not enough.** The live check at 08:16 shows "camera"
  4 of 159 (196 before) and "phone charger" 4 of 6 (29 before), yet both first pages
  are still the wrong kind: four Canon and Nikon lenses, and SafeFort's Batteryguard
  charging safes. Three causes, read locally on the live titles: (1) SafeFort names
  the product only after a bar ("Batteryguard L-10 HE VDMA 24994 Certified |
  Lithium-Ion Battery Charging Safe") and the lead before it names none, so the shelf
  decides; (2) in "Nikon AF-S DX 35mm f/1.8G Lens" the number before "Lens" reads as a
  count of lenses (like "11-Fin"), so the noun is passed over; (3) the Canon lenses
  read doubtful on a cameras shelf, so their live rows carry something else, most
  likely a `product_type` that names cameras, whose authority the rule keeps by design.
  These come first; the 7-column file below shows (3).
- **What it does:** the kind-rule bullet of "Now (2026-10-22)" below, and PROGRESS
  22/10. Code: `src/picwise_nlu/concept_understanding.py` (`_product_nouns`,
  `_lead_noun_index`, `_lead_names_another_product`, `_noun_after_kind`,
  `_kind_named_before_another_product`, used by `_title_lead_verdict` when the kind
  comes from a category shelf). Tests: `tests/test_picwise_title_names_another_product.py`.
- **Open, in this order.** Each is measured and told to the owner first, then built.
  1. **The rule on every live product.** No session holds the live rows. The owner was
     asked for a Create-a-Feed file of the same 20 shops with 7 columns only:
     `advertiser_name, id, title, google_product_category, product_type, availability,
     price`. With no link or image column no row passes the shown gate, so read each
     row's kinds the way the search does: `normalize_feed_row_to_provider_product`,
     then `search_selection._product_concepts(product, _product_search_fields(product))`,
     once on the code before the rule (`f86f4e4`) and once on today's. List the rows
     whose kind changes and the wrong kinds left, by shop and by search; look for
     SafeFort's safes on "phone charger" and Pro-Camera's lenses and propellers on
     "camera".
  2. **A title that names no product** ("Batteryguard S-6 HE VDMA 24994 230V - UK -
     KEY LOCK"): its shelf still decides. Nothing decided; the shop's `product_type` or
     description may say what it is.
  3. **"Charger":** the lexicon's `phone_charger` (`src/picwise_nlu/product_concepts.py`)
     takes every charger, so a "Battery Chargers" shelf reads as phone chargers.
  4. **The kind within a kind:** "dining table" still shows a dressing table, a kitchen
     prep table and a shop press's "Working Table": the answer is the kind (table), not
     the table asked for.
  5. **Back to the Office:** 93,639 of its 95,075 live rows carry no
     `google_product_category` and are held. The same file shows whether
     `product_type` carries their category; reading it as the category when the Google
     one is empty is a change in `normalization._CATEGORY_KEYS`, for the owner to approve.
     Since 23/10 `/prepared.json` shows it for every shop (owner's yes for `main`, merge
     `27dd1a1`): `intake.shops[].product_type` gives the rows that write one, how many of
     them have no category, and the five most frequent values. Measured only. **Answered
     live (09:38 UTC): Back to the Office sends no `product_type`** (1 of 95,161 rows,
     "French"; none of the 93,726 without a category), so reading it would bring none in.
     Only Pro-Camera fills it, on all 433 rows: its own path ending in the product's name
     ("Accessories > Flashes > Canon > Canon MR-14EX II Macro Ring Lite Flash"), which
     bears on (3) above.

  Accepted loss of the rule: 42 cushions on a throw-pillow shelf no longer answer
  "pillow" (they still answer "cushion").

  Found on 23/10 (second conversation), on titles with plausible shelves, nothing built:
  (a) "body" is a product noun (Google's "Bath & Body"), so since `964fbdf` a camera body
  on a cameras shelf with no product type ("Canon EOS R6 Mark II Body") is doubtful: a
  real camera lost; (b) in the Nikon case "1.8G" reads as a weight (`_MEASUREMENT_RE`);
  (c) a product type "Camera Lenses" or "DSLR Lenses" makes a lens a camera (the type's
  own noun is not read); (d) a product type is split at "/" (`_TYPE_LIST_SPLIT_RE`), so a
  Pro-Camera path ending in "f/1.4L II USM Lens" reads "Lens" as a kind label of its
  own; (e) every charger shelf, battery chargers included, is the lexicon's phone
  charger (item 3). Which of these the live rows meet: measured the same day on the
  owner's file of Pro-Camera and SafeFort (PROGRESS, 23/10): lenses are cameras by
  Pro-Camera's type "... DSLR Lenses ..." (43), 111 of its 224 real cameras are hidden
  (63 "+ mount adapter" types, 35 "Body", 13 "Camera Kit"), and 6 safes stay on "phone
  charger" by their title's bar. **Fixed (`5de684e`, owner's «Ναι»), on `main` since
  23/10 12:49 UTC (merge `9429bca`; live: "camera" 4 of 226, all cameras; "phone
  charger" no products):** "Body", a type's "+", "Camera Kit", a type naming a
  kind only before another product's noun, a title read on after a bar; on the file 160
  rows change as intended (PROGRESS, 23/10). Left: "camera lens" reads as camera (no
  lens kind), the "1.8G" weight reading, item 2 ("... 230V - UK - KEY LOCK", no bar), the
  lexicon's plain "case" (lock cases on "phone case") and the "Document Wallet".
- **Since 23/10 the build lists suspects by itself** (on `main`, merge `95d0961`):
  `/prepared.json` `kinds`, per kind the shown products whose title does not name it, the
  cheapest first. Read it after each morning's build to find new title patterns from every
  shop without asking for a file. The first list (PROGRESS, 23/10) shows wrong kinds (RAM
  as a processor, a punchbag as a bag, a garden set as a heater, a subscription as a coffee
  machine, bedspreads as duvets) and look-alikes first (bath mats as rugs, bedside cabinets
  as tables, stools as chairs); fixed the same day (merge `7b9624c`): 290 suspects left
  of 438. Next, from the list of 16:09: bedside tables under "Tables > Bedside Tables"
  (the first shelf wins), PVC flooring as a rug; stools, ventilation units and changing
  units wait for the owner's word.
- **How to measure, before and after any change:** `tools/price_first_eval.py <feed>
  <out.json> --compare <before.json>` (the 118 searches: 19 pages changed on the owner's
  third Google file, each by wrong kinds leaving; 0 on fictional Awin-format feeds); the
  kinds of every shown product (`prepare_feed_catalogue()`: `.products` with `.kinds`)
  on both codes; `tools/nlu_misspelling_benchmark.py` (93.8%, 0 wrong, unchanged); the
  full run per module (Working gotchas): 243 of 245 pass, the two known failures
  `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`. The owner's files reached only the
  old session: ask for a file again when one is needed, never for the link.
- **The live site** is seen through the live check ("How a session sees the live site",
  below); its last run is `40001929114` (23/10 18:16 UTC; re-run it to look again).
- **The owner's words for this work** (2026-10-20): «Μην αλλάξεις τίποτα στο live site
  και μη χτίσεις τίποτα πριν μου πεις τι βρήκες. Τίποτα στο main χωρίς το ρητό μου
  «ναι». Μη μου ζητήσεις τον σύνδεσμο του feed, γιατί έχει το κλειδί. Γράψε μου στα
  ελληνικά, σύντομα, με απλά λόγια.» Never open an Awin tracked link from a session (it
  counts as a click). The truth test is a bot's, never the owner's by hand.

## Now (2026-10-22) -- read this first

- **Google-format reading is built and on `main`** (merge `c147fda`, owner's
  «πέρασε στο main», 22/10; seen live at 12:21 UTC, the Awin-format pages as before): the category from
  `google_product_category`, the currency split off the price ("39.99 GBP"), and a price
  of 0 or below never shown (`price_zero_or_negative`). On the owner's third
  Google-format file: 4,621 products shown of 13,071, 6 shops; on fictional Awin-format
  feeds 0 of the 118 search pages change; full run 242 of 244 modules pass (the two
  known failures). Details in PROGRESS, 22/10. **Open, the owner's:** make the final
  Create-a-Feed link (advertiser-based, no categories, no AKKO UK) and put it in Vercel
  (`AWIN_FEED_URL`);
  the steps are in `docs/awin_feed_setup_el.md`, "Feed σε μορφή Google". Only the owner
  can paste it (it holds the API key). Until then the live site runs on the
  Awin-format link.
- **Owner's plan (22/10, after the merge):** one Create-a-Feed link with every
  Google-format advertiser, joined or open, so the link is not redone per shop; the shop
  evaluation and the map of shops per category from what it brings in; then Vercel for
  the volume; then the truth-test bot (the owner pays a subscription; **80 checks per
  shop**, not 200); then Awin closes and CJ opens. **Before that link goes into Vercel:**
  the owner reads its Product Count (about 250,000 is what was measured to fit; the
  download stops at 300 MB), leaves adult content out. **The UK for now** (owner, 22/10);
  a GBP-only rule in the site was put to the owner, not decided. Proposed, not built: each shop's categories in `/prepared.json`.
- **Live since 22/10 13:34 UTC: the Google-format link** (20 UK shops, 119,720 rows):
  12,204 products shown from 19 shops. Back to the Office shows 771 of 95,075: 93,639
  of its rows carry no `google_product_category` (whether they carry `product_type` is
  not seen yet). First pages showed wrong kinds ("phone charger": charging safes;
  "camera": propellers, lenses).
- **The kind rule, reworked** (owner's yes, 22/10; **on `main` since 23/10**, owner:
  «Ναι για το main»): the noun a title's lead ends with is read against the
  product nouns of Google's taxonomy, and a shelf no longer gives its kind to a lens, a
  safe, a stool or a keyboard plate. Measured: 19 of 118 pages change on the owner's
  Google file, each by wrong kinds leaving; 0 on fictional Awin-format feeds; full run
  243 of 245 modules (the two known failures). Not fixed: a title that names no product ("Batteryguard S-6 ... KEY
  LOCK") and the lexicon's "charger" = phone charger; qualifiers inside a kind ("dining
  table" shows a dressing table). Details in PROGRESS, 22/10.
- **New rule (owner, 22/10): one shop in several networks** is one shop, known by its
  site's domain; its price and stock from the freshest feed (the latest update date
  the network states) with a real stock state,
  never chosen by commission; only for the same offer is the link taken from the
  network that pays best (the highest commission first, owner 22/10). In `PROJECT_RULES.md` section 5, the decision contract and the
  concept (Revenue Rule). Not built (one network today).
- **Owner decisions of 22/10:** AKKO UK out (prices in EUR; done in the feed selection,
  not in code); the truth test (what the feed says against the shop's own page) is done
  by a bot, never by the user by hand. Nothing of the bot is built; where it runs is
  open (not on Vercel: its fair-use page lists scrapers as never allowed, a function
  stops at 300 s, Hobby runs a scheduled job once a day).
- **Shops (owner's screenshots, 22/10):** joined Living and Home, Back to the Office,
  Game Over, PCHUB.UK, Tyres UK, Gardenista, Aosom UK, brickzonehub (no feed). With a
  Google-format feed: Living and Home, Game Over, Gardenista, Back to the Office (about
  88,000 products; its file did not download); Tyres UK has none; Aosom UK does not show.
  Open advertisers (not joined, yet in Create-a-Feed) are credited for sales through
  their feed, per Awin's help pages ("soft membership", auto-join): Geepas and Homespace
  Direct were in the third file; Car Audio Centre was not shown in the selector on
  22/10. PCHUB.UK's format is not known yet. Missing kinds: TV and audio, tools. Every
  search page has one shop's products today: no real comparison yet.
- **Flagged to the owner, not decided:** Vercel's Hobby plan is for non-commercial use
  only, and Vercel names a site whose primary purpose is affiliate links as commercial;
  this applies to the live site now. Ask Vercel, or plan for Pro.
- **The Google format has no listing date** (the Awin format had `last_updated`), so
  stale listings cannot be told by date; `product_type` and `sale_price` were empty in
  all three files and are not read.

## Before (2026-10-20)

- **Start here: Google-format feeds (owner decision, 20/10).** «Θα εστιάσουμε στα
  google feed δεν θα ξανασχοληθούμε με awin feed». The reading put to the owner, not
  contradicted, to confirm first: Awin stays as the network (links, commission), and
  only Awin's Google-format feeds are used (a publisher gets them only through
  Create-a-Feed). **First step:** the owner uploads a Google-format file (the file,
  never the link); measure it (columns, how many say `out_of_stock`, the price with its
  currency, the category columns, whether the product link is Awin's tracked link),
  then build the reader on it. PicWise does not read the format yet; until it does,
  the live site runs on its current Awin-format link. Details in PROGRESS, 20/10.
- **On `main` since 20/10** (merge `3c2c4cd`, the owner's «Πέρασε το στο main»): the
  work of this conversation (`ccr-9015e891-xt29ld`) and the notes of 18/10. **Seen
  live** through GitHub at 12:52 UTC: the feed prepared by the new code at 12:48 UTC,
  `prepared_feed` `in_use`, the 12 searches of the live check showing the same cards
  as in the morning, and the per-shop intake in `/prepared.json` (143 of 11,191 rows
  held back as not for sale; 4x4 Predator's 109 rows all held).
- **The owner's update of 18/10** (sent 20/10) restates the direction recorded on
  18/10: no checks of shops' pages now; first many shops, with whatever each feed
  sends; then the evaluation mechanism (set hours, 200 checks per shop, the shop's own
  link only, robots.txt, a gentle pace, one Vercel job a day, the feed link only in
  Vercel). Nothing of the mechanism is built.
- **Live** (through GitHub, 20/10 09:47 UTC): the morning renewal works (prepared 04:59
  UTC); 11,048 products, 25 shops; Boxed2me still fills the cheapest pages; one shop is
  "Monsterpub Sex Toy" (the link takes in adult content).
- **Built for many shops, on the branch** (details in the plan file, "Many shops: what
  the free plan carries"): the feed read as a stream, a lean prepared file (format 2,
  `LEFT_OUT_COLUMNS`), and per shop what each feed brings in (`/prepared.json`,
  `intake`). The server's ceiling on Vercel's free plan moves from about 110,000 real
  products to about 250,000 (measured on fictional feeds); 0 of the 118 pages changed.
  A cold server's first search still grows with the catalogue (about 11 s on Vercel at
  92,000 products): the regular visit that keeps the server awake (owner's idea,
  2026-10-17) is the answer, not built.
- **The owner's steps for many shops** are in `docs/awin_feed_setup_el.md`, first
  section (Greek): join programmes; one new link by category with every category;
  all columns kept, `merchant_deep_link` above all; watch `products` in
  `/prepared.json` against about 250,000.
- **Not decided (20/10): whether the catalogue may be held in the server's memory.**
  The owner said never, then withdrew it the same day («Άκυρο θα συζητηθεί άλλη
  φορά»). Nothing changes until it is discussed. Options put for that discussion: (A)
  SQLite inside each deployment, free, about 150,000 to 250,000 products (Vercel's 500
  MB per Python function); (B) a hosted database. Also proposed, not decided: a daily
  check of what the first pages show (about 2,600 product pages a day) next to the 200
  checks per shop; no production jobs on GitHub (its terms, as remembered; check them
  before stage 2).
- **Open, the owner's:** the yes for `main`; keep or drop Boxed2me; adult content in or
  out; which shops to join. For a later discussion: the catalogue in memory or in a store.

## Before (end of the conversation of 2026-10-17/18)

- **Live = `main`:** price first (steps 1-4), the search page, and step 5: every
  deployment's build prepares the feed (`vercel.json` build command), a Vercel
  scheduled job a day (`17 4 * * *` UTC) asks for a new deployment through the Deploy
  Hook, so each day has its own prepared feed. The owner set the keys in Vercel on
  2026-10-18 (`PICWISE_DEPLOY_HOOK_URL`, `CRON_SECRET`; Production, Secret). Also live:
  products without a description are shown with a note (owner), and `/prepared.json`
  carries `freshness` (listing ages, stock columns, per shop).
- **Seen live** (through GitHub, below, 2026-10-18 11:59 UTC): `prepared_feed`
  `in_use`; 11,423 products, 25 shops; searches 0.3-0.9 s; "tv" 4 of 23.
  **Not seen yet:** the first morning renewal. Look on 2026-10-19 after about 05:00
  UTC: `/prepared.json` `prepared_at` of that morning means it works.
- **How a session sees the live site:** its own network cannot reach
  `picwise.subby.cloud`. A push to `ccr-fd5dc1bc-4vgsgl` runs
  `.github/workflows/live-check.yml`, which prints `/prepared.json`,
  `/private-beta-readiness` and the cards of 12 searches; or re-run its last run with
  the GitHub tools (`actions_run_trigger`, `rerun_workflow_run`) and read the log
  (`get_job_logs`). Never ask the owner to copy pages by hand if this works.
- **The branch** is ahead of `main` only by notes and that workflow; its code is the
  same as `main` (the shop-page sample was reverted).
- **Owner decisions of 2026-10-18:** a description is not required (note on the
  card); no checking of shops' pages now; the order from here: (1) many more shops,
  (2) then an evaluation mechanism at set hours, 200 checks per shop, giving a list
  of reliable and unreliable shops (constraints in PROGRESS). **Code first:** that
  mechanism and the fix of the kind rule are written in plain code; an AI system is
  discussed with the owner only if code is shown not to reach the results wanted,
  and is not proposed before that.
- **Open, the owner's:** keep or drop Boxed2me (3,474 products, a clearance shop that
  fills the cheapest-first pages for headphones, chargers, cameras, speakers, at
  prices such as £0.99, the likeliest "ghosts"); which shops to add in Awin.
- **Open, engineering, held until more shops are in:** the rule that reads a
  product's kind lets wrong kinds onto first pages ("camera": a chime, a siren, a
  shotgun microphone; "phone charger": an IEC plug), to be fixed once on all cases;
  Xiaomi RO's TVs priced "EUR" 849-3,799 (likely Romanian lei); Geekbuying prices
  shown with three decimals ("14.990 USD"); laptop, kettle, mouse and keyboard find
  nothing in this feed (data, not understanding).
- **Rules:** nothing to `main` without the owner's explicit yes; keys only in Vercel;
  nothing changed in Supabase without asking; Greek, short, plain words.

## Start here (2026-10-17)

- **2026-10-18: steps 1 to 5 are on `main`** (merge `e52339d`, a normal merge of
  `ccr-fd5dc1bc-4vgsgl`, by the owner's yes «Ναι, τώρα», told beforehand that it puts
  all of them live). Production NOT VERIFIED from the session, which cannot reach
  Vercel or the domain: the owner looks at `picwise.subby.cloud`, its
  `/private-beta-readiness` (`prepared_feed` should read `in_use` with today's time)
  and `/prepared.json`, then Settings, Cron Jobs, Run, once. If the site misbehaves:
  Vercel's Instant Rollback to the previous production deployment (`3b02aeb`), or a
  revert of the merge. The notes below that say "nothing is on `main`" predate this.
  **Seen live by the owner the same day:** the home page opens with the new box
  ("What are you looking for?"); `/prepared.json` reads `prepared: true`, 9,935
  products, 25 shops, prepared 10:32:56 UTC (the production build read the real feed
  and prepared it); `/private-beta-readiness` reports `provider_feed_ready`; a search
  "was fast" (owner). Not checked, and the owner asked not to be asked again: the
  `prepared_feed` line, and a run of the daily job (it runs by itself each morning).
  A later session can tell from `/prepared.json`: a `prepared_at` of that morning means
  the renewal works. The session itself cannot open the site.
- **2026-10-18, after the merge: products without a description are shown, with a
  note** (owner: «Ναι, με σημείωση»; Decision Contract, "What a product must carry to
  be shown"). "tv" found nothing live because the feed's televisions come only from
  shops that send no description. On `main` since the same day (merge `6050315`, the
  owner's yes); live result NOT VERIFIED from the session ("tv" should now show
  televisions, with the note). The microphone is hidden in Firefox (no speech recognition there);
  the owner uses Firefox.
- **2026-10-18: "we show ghosts"** (owner): most products shown are out of stock on
  the shop's page, old listings. Measuring first, by the owner's choice: the build
  writes listing ages and stock quantities into `/prepared.json` (`freshness`;
  `src/picwise_providers/feed_freshness.py`); the owner copies it, then chooses a rule.
  Details in PROGRESS. Not a rule yet: nothing shown changes. The feed carries no
  dates and no out-of-stock state at all. **Owner decision, 2026-10-18: no checking of
  shops' pages**, not even a few-day sample (built, then reverted on the branch,
  never on `main`); do not propose it again unless the owner raises it. **The
  owner's order, the same day:** first many more shops; then an evaluation mechanism
  at set hours, 200 checks per shop, giving a list of reliable and unreliable shops
  (constraints in PROGRESS). Left meanwhile: which shops to keep (Boxed2me fills the
  cheapest-first pages for several kinds); the wrong-kind cases wait for more shops. The
  live check (`.github/workflows/live-check.yml`, on each push to the branch; re-run
  to look again) reads PicWise's own public pages through GitHub, no shop's.
- **Step 5 is begun** (2026-10-17, on the branch; nothing of steps 1 to 5 is on
  `main`). A search takes about 0.34 s (5 s before), a cold server reading the feed
  reaches the first page in 22-24 s (38-40 s), and one given a **prepared file**
  (`tools/prepare_catalogue.py`, `src/picwise_providers/prepared_catalogue.py`) in
  about 4 s, without reading the feed; 0 of the 118 pages changed. Details and what
  keeps a prepared file honest: the plan file, "Step 5, first part built".
  **Second part built too** (2026-10-17, on the branch, not checked on Vercel): every
  deployment's build prepares the feed (`vercel.json` build command, no more `builds`),
  a deployment never fails because of the feed (`--keep-going`), one Vercel scheduled
  job a day calls `/cron/renew-prepared-feed`, which with `CRON_SECRET` posts to the
  Deploy Hook in `PICWISE_DEPLOY_HOOK_URL` (both keys only in Vercel), and
  `/private-beta-readiness` says under `"prepared_feed"` whether the server answers from
  the file. Checked with Vercel's own CLI (`vercel build`) on a fictional feed; details
  in the plan file, "Step 5, second part built". **Waits on the owner, in Vercel**
  (Greek steps: `docs/vercel_daily_feed_setup_el.md`): the Deploy Hook, the two keys,
  `AWIN_FEED_URL` for Preview on this branch for the test, a look at the test
  deployment, then the word for `main`. This conversation had no Vercel connection
  either; none is needed for these steps, the owner does them in the dashboard.
  **Owner, 2026-10-18:** the steps are hard to do now; the Vercel way stays, later
  («Με τη Vercel, αργότερα»), and the site stays as it is until then. Offered instead
  and not chosen: a scheduled GitHub workflow making one small automatic commit to
  `main` each morning (no keys, no Vercel steps; a push to `main` makes Vercel build,
  and the build prepares the feed). Do not build it unless the owner asks.
  **Later the same day the owner did it, guided screen by screen:** a Deploy Hook
  `daily-feed` for `main`; `PICWISE_DEPLOY_HOOK_URL` and `CRON_SECRET`, both
  Production and Secret (six variables now). Not done: `AWIN_FEED_URL` for Preview. A
  Secret cannot be read back, and its Edit form shows the value empty, so saving it
  with Preview added risked erasing the Production feed link: cancelled, and the test
  ran without the feed. **Seen on Vercel by the owner:** the preview builds of the new
  config (`e715771`, `f530240`, `cfbf683`) are all Ready, and `/prepared.json` on the
  preview reads `prepared: false, reason: feed_not_readable` (right without the feed):
  the build step runs on Vercel and its note is served. **Not checked:** the preview's
  pages served by the Python function (`/`, `/private-beta-readiness`); the owner
  stopped there («τελείωσα εγώ, κάνε εσύ»), and the session cannot reach Vercel or
  the live site. **Left:** the owner's explicit yes for `main`, which puts steps 1 to 5
  live, not only the prepared feed; then one look at `picwise.subby.cloud` and its
  `/private-beta-readiness` (`prepared_feed`: `in_use`); then Settings, Cron Jobs, Run,
  once. On
  Google Cloud Run, were PicWise moved there, the same tool and file serve
  (`PICWISE_PREPARED_CATALOGUE_FILE`); only the schedule and the hook are Vercel's.
  **Next after that:** the regular visit that keeps the server awake (below), its
  interval measured on the live site. **Decided by the owner, 2026-10-17:** a file prepared once a day is fresh
  enough («Ναι φορά τη μέρα μου αρκεί»), and a regular visit keeps the server awake
  (the owner's idea, "every hour"; plan file, "Step 5, first part built").
  The owner does not pay $20 a month for Vercel Pro (2026-10-17); Vercel's terms, as
  remembered and not checked from here, keep the free plan for non-commercial use;
  Google Cloud Run's free tier was proposed, nothing decided; build so it runs on either.
  The owner also wants all projects under SUBBY CLOUD and the GitHub account renamed
  "subbycloud"; steps given, nothing done by Claude.
- **Picking up in a new conversation.** Everything is pushed to `ccr-fd5dc1bc-4vgsgl`.
  To measure a change that should only be faster:
  - the owner uploads the feed file (Awin, download, then upload here; never the
    link). Copy it into its own empty directory;
  - before the change: `python -I tools/price_first_eval.py <feed.csv.gz> before.json`
    (118 searches, a few minutes); after it: `python -I tools/price_first_eval.py
    <feed.csv.gz> after.json --compare before.json`, which lists every page that
    changed and the time per search before and after; `--prepared <file>` answers
    from a prepared file;
  - tests per module: `PYTHONPATH=.:src python3 -m unittest tests.<module>`, a few
    at a time, and `PYTHONPATH=.:src python3 tools/nlu_misspelling_benchmark.py
    --failures 60`. Known failures on unchanged code are in "Current numbers" below;
    the rest of the gotchas at the end of this file.
- **New direction: price first, no ratings** (owner, 2026-10-15). Read
  `docs/picwise_price_first_plan_2026-10-15.md` before anything else. In short: only
  the kind asked for; never out of stock; cheapest first; the same product once, from
  its cheapest in-stock shop; the first four are a "Recommended", the middle product in
  price order, plus the three cheapest, with "4 of 45"; "more" again and again. The old
  instruction, "build nothing until a feed with ratings arrives", is over, and the
  search for ratings stops.
- **The founding files now say the same as the plan.** It contradicted them (no endless
  list, not a search engine); on 2026-10-16 the owner chose to change them, and
  `concept.picwise.txt`, `docs/MISSION.md`, `PROJECT_RULES.md` and
  `docs/LANDING_PAGE_SPEC.md` were changed. Each changed passage in the concept carries
  a dated note. Services (insurance, energy, banking, software) were not decided and
  keep their old rules.
- **Step 1 of the build order is built** (2026-10-16, on the branch): only the kind
  asked for. A product answers a kind only when its type, its shop's category path or
  its title's lead says so plainly. Doubtful products (11,187 of 42,076) are found
  only by their own words, and pet and camping products answer only searches that
  name them. Of the same 118 English searches, 95 now show four right products (80
  before) and none shows the wrong kind (21 before). What price order would list
  first is now the product, not its accessory: "laptop" opens with a £125.99 HP Stream
  instead of a £3.99 adapter. Details and what is left: the plan file, "Step 1 built".
  **Step 2 is built too** (English before greeklish: "patio set" shows garden
  furniture, not insoles). **Step 3 is built too** (2026-10-16): the price-first engine,
  for every search whose product is understood. Cheapest first, each product once; the
  Recommended is the middle product by price with a valid EAN/GTIN, never the cheapest
  or the dearest; "Lowest price" on the cheap cards; "4 of 677" and a "More" that opens
  the next four as often as asked (`/search?q=...&shown=8`); fewer than four as they
  are. A search's other words now decide what is in the answer, read in each product's
  title, type and brand. Graded refurbished titles are read as not new, and USB sticks,
  bookcases and fire pits are their own kinds. Of the 118 searches, 100 show a right
  first page, 12 a card that misses a word, 1 a wrong card, 5 nothing. Details,
  including where a rule needed reading, in the plan file, "Step 3 built". The owner
  accepted those readings on 2026-10-17 and decided that without a Recommended
  "Lowest price" goes only up to the middle price (built the same day). **Part 3b is
  built too** (2026-10-17): a search whose product is not understood ("cat tree", "dog
  crate", "network switch") is answered by its words on the same price-first page,
  with its own kind test (no hutch covers for "rabbit hutch"), a model name answered
  as the kind its products are ("lenovo thinkpad 16gb ram": laptops), and a one-word
  search that names several kinds asking which ("switch", "tree", "machine"). Details
  in the plan file, "Part 3b built". **Step 4 is built too** (2026-10-17): the box
  reads "What are you looking for?" (owner); a scanning screen with the real counts
  as a search starts; suggestions as the buyer types (kind names in English and
  Greek, brand with kind, the shops' own names, only those that find products,
  fetched once from `/suggest.json`); a microphone where the browser can listen, the
  search starting when the buyer stops (owner). Details in the plan file, "Step 4
  built". **Next: step 5, data prepared once a day** (the first speed-up: stop judging
  every product's eligibility again on every search).
- **Measured on 2026-10-16** on a new feed (Back to the Office, Aosom UK, Living and
  Home; 42,076 rows). Results are in the plan file, "Measured on the third feed":
  - cheapest first puts accessories on top ("laptop" opens with docking stations);
  - the middle of the range recommends the top end (a £4,809.99 MacBook Pro);
  - no shop sends a real stock state;
  - no product is in two shops;
  - a search takes 4 to 16 seconds.

  **Decided by the owner, 2026-10-16:** the Recommended is the median (the middle
  product in price order), and the feed's "in stock" is trusted (no shop page is
  checked). **First engineering step:** a strict yes/no test that a product is the kind
  asked for. **English understanding, tested the same day:** 118 queries with
  misspellings and phrasings; the right kind understood for 109 (92%), but only 80
  showed four right products. Kind-reading errors (tablet casings, desk trays, label
  makers) account for most of the rest; also "patio" is read as greeklish «πάτοι»
  (insoles), and queries with numbers show empty pages through the old recommendation
  step. Details in the plan file, "Search understanding, English".
- **The owner's additions (2026-10-16), in the plan file:**
  - suggestions as the buyer types (faint completion plus a word list from the first
    letter);
  - a microphone in the search box;
  - trends below the box, true to their source;
  - many more shops (every Awin programme with a feed, then CJ and others);
  - extreme top prices (at least twice the next) do not count for the Recommended;
  - no Recommended for services in this phase.

  - PicWise as a phone app, later in the Play Store;
  - a truthful scanning screen that lets results take about 4 s (concept section 18
    and PROJECT_RULES section 9 changed).

  Proposed build order:
  1. strict kind test;
  2. English over greeklish;
  3. the price-first engine;
  4. the search page (scanning screen, suggestions, microphone);
  5. data prepared daily (needed before going live);
  6. trends;
  7. the app;
  8. other networks.

  The owner restated the extreme-price rule for step 3 (2026-10-16: «όταν το
  ακριβότερο είναι δύο φορές ακριβότερο από το προηγούμενο φθηνότερο να εξαιρείται
  από το μέσο όρο»), which matches the recorded reading, and did not object to the
  order; step 1 is built.
- **Decided by the owner on 2026-10-16:**
  - "smartphone" shows smartphones; "mobile phone", "phone" and «κινητό» show only
    basic phones. This is built, on the branch;
  - no Recommended when no product has an EAN/GTIN;
  - fewer than four results are shown as they are ("2 of 2");
  - brand + MPN counts as the same product;
  - the three cheapest cards say "Lowest price" ("Lowest price of N shops" when
    offers are joined), and the line under Recommended is "Mid-priced for this
    category".

  All are built (steps 1 and 3).
- **Open owner decisions:** none on the plan. Put to the owner with step 3:
  - ~~the search box wording~~: chosen on 2026-10-17 ("What are you looking for?") and
    built in step 4;
  - a check on implausible prices (£0.99 headsets lead "headphones");
  - whether a word after "for" ("printer for home") should narrow the answer;
  - ~~the readings made to build rule 7~~: accepted on 2026-10-17 («Οκ σε όλους»).

  The marketing proposals in the plan file are proposals; none is approved.
- **Branch, not `main`.** `ccr-fd5dc1bc-4vgsgl` is ahead of `main`; count the commits
  with `git rev-list --count origin/main..origin/ccr-fd5dc1bc-4vgsgl`. Merge
  to `main` only when the owner says so explicitly. A session may be set up to push to
  another branch (on 2026-10-16 it was `claude/vibrant-cerf-b2afyt`). The owner works
  on `ccr-fd5dc1bc-4vgsgl`, so ask before writing anywhere else.
- **Both real feeds measured carry zero ratings and zero sales counts**, checked over
  every row: the first (11,573 UK electronics) and the second (51,630: Tyres UK, Aosom
  UK, Living and Home). Two facts from the second that the plan depends on:
  - Tyres UK (39,403 rows) writes its description in `custom_6`, so no tyre passes the
    description rule until that column is read;
  - Living and Home (2,255 rows) sends no category, so all its rows are held at the
    feed gate.
- **Awin Google format:** it cannot be mixed with Awin-format feeds in one file (Game
  Over offers only Google format). Whether it carries ratings no longer matters.
- **Awin status (owner's screenshots, 2026-10-14):** Joined -- Living and Home, Back
  to the Office, Game Over, Tyres UK, Aosom UK. Pending -- Gtech, Songmics, Mstore,
  Hoxton Macs, Road Angel, Boots.com, Currys, Euroffice. Rejected -- Beldray, Mattress
  Online, SharkNinja UK (advised not to re-apply now). Markets: UK and US.
- **When a new feed file arrives:** copy it into its own empty directory, run
  `python -I tools/check_awin_feed.py <file>` and measure it against the price-first
  rules. Report in Greek, short. Never ask the owner to paste a feed link (it holds the
  API key): they download and upload the file.
- **Homepage** still reads "Buying Decision Preview" / "Live safe mode" and `/about` is
  404; likely hurting Awin approvals. The owner declined a fix on 2026-10-14, before the
  plan changed. The marketing analysis proposes a new homepage sentence.

## Where the work is

- Repository: `nikkaradimitris-cloud/picwise.concept`
- **Stale, see "Start here" above:** the branch is ahead of `main` again. The condition work (non-new products only when the buyer
  asks) was merged on 2026-10-11 by the owner's instruction: merge commit `b28da32`, a
  normal merge of `ccr-fd5dc1bc-4vgsgl`, no pull request. Its deployment is NOT VERIFIED
  from a session. Earlier: PR #2 was merged on 2026-10-08 (merge commit `148a552`,
  a normal merge, by the owner's instruction). It carried all of PR #1, so GitHub marked
  PR #1 as merged too; the owner chose this knowing it. `main` holds the 4+1 Awin path,
  the misspelling understanding, the mission truth audit of 2026-10-08 and its fixes
  (`docs/picwise_mission_truth_audit_2026-10-08.md`). Start new work from `main`.
- **Production: the audit fixes are deployed.** On 2026-10-08, after the merge, the owner
  checked that `/best/power-bank-20000mah-for-iphone` on `picwise.subby.cloud` returns
  404; it used to show a fabricated page (audit D1). Not checked live: whether
  `/sitemap-buying-pages.xml` lists nothing, and anything that needs a real feed (none
  is connected). The session environment blocks `picwise.subby.cloud` and
  `*.vercel.app`, so a session cannot check the live site itself; ask the owner.
- Hosting: Vercel project `subbycloud/picwise-concept` (Hobby account "SUBBY CLOUD";
  since 2026-10-10 its only login is the owner's `mysubby.cloud@gmail.com`, email and
  Google; no Git login is linked to it). Domain `picwise.subby.cloud`. Entry point
  `api/index.py` (see `vercel.json`). Deployments come from pushes to `main` through
  the Vercel GitHub app. A manual **Redeploy** from the dashboard fails with "Git
  information retrieval failed" (no Git login on the account); to roll out an
  environment change, merge a commit to `main` instead.

## The owner

Not a programmer. Write to them in **Greek**, plain words, short. Explain choices in
everyday terms, give honest numbers, and say plainly what was not done and why. Never
overclaim.

## Rules that do not change

Read in this order before touching anything, every session:

1. `PROJECT_RULES.md` — the operating rulebook, first in the source-of-truth order
2. `docs/MISSION.md` — the mission lock: what every purchase-intent query owes the
   buyer, the product promise ("Enter confused. Leave decided."), the identity PicWise
   must never drift into, and the trust/neutrality commitments. **Every piece of work
   is measured against this file.** Its "First Phase Boundary" section is stale (it
   predates the live app) — see "Known doc conflict" below.
3. `concept.picwise.txt` — the product concept source of truth
4. `docs/` contracts and specs — implementation contracts
5. this file, then the last entries of `PROGRESS.md`

If these layers conflict, do not guess: stop and raise it (PROJECT_RULES section 1.4).

In short:

- every purchase-intent query: only the kind asked for, only in stock, cheapest first;
  4 choices first (1 Recommended, the middle product in price order, + the 3 cheapest),
  then "More" for the next 4 as often as asked; decision labels, CTA, direct redirect,
  tracking event (price first, 2026-10-16)
- no fake data of any kind; no commission-based ranking; missing data uses the enum
  (`not_connected`, `data_not_yet`, `not_applicable`, `unknown`)
- small, closed, tested steps; do not invent business logic (flag a TODO instead)
- section 9 performance: first render < 1.5 s, interactive < 2 s, click → redirect < 300 ms
- stages 23–25 stay `NEEDS_*` until real live proof exists; local fixtures are never live
  proof
- **Amazon is permanently removed** — do not reintroduce it. Awin is the affiliate network.
- nothing that may serve the pages Google indexes is left out of what PicWise keeps, and
  nothing may hurt their quality or ranking (owner, 2026-10-23; first section above); a
  change that would, is stopped and told to the owner
- the business runs on Google search, Ads and social media second (owner, 2026-10-23):
  low-volume, low-competition keywords in large markets with many products; every page
  meant for Google meets Google's own published requirements end to end

## Map of the code that matters now

| Area | Where |
|---|---|
| Product concept lexicon (278 kinds, EN + GR names, mega category, `broader`, preference words) | `src/picwise_nlu/product_concepts.py` |
| Understanding: phonetic keys, typo correction with safety fences, specs, product annotation (incl. accessory guard), "did you mean" | `src/picwise_nlu/concept_understanding.py` |
| Price-first selection: the kind test, cheapest first, the same product once, the Recommended, "4 of 45"; the concept path (`_select_products_for_concept`), the word path for kinds not understood (`_select_products_by_words`), the question when a word names several kinds; the condition gate | `src/picwise_providers/search_selection.py` |
| The catalogue a search reads, judged once per feed load (`SearchCatalogue`); the counts on the scanning screen; the suggestions | `src/picwise_providers/state.py`, `src/picwise_providers/suggestions.py` |
| The prepared feed: written by `tools/prepare_catalogue.py`, read instead of the feed when fresh and written by the same code | `src/picwise_providers/prepared_catalogue.py`, `state.py` (`prepare_feed_catalogue`, `_active_prepared_catalogue`, `prepared_catalogue_status`) |
| On Vercel: the build that prepares the feed, the daily scheduled job, the renewal route (`CRON_SECRET`, Deploy Hook) | `vercel.json`, `src/picwise_app/prepared_renewal.py`, `api/index.py` |
| Whether the feed says a product is not new (one rule for the gate and the cards) | `src/picwise_providers/product_condition.py` |
| Per shop, what each feed brings in and why the rest is held back (the build's note, `intake`) | `src/picwise_providers/feed_intake.py`, `state.measure_configured_feed_intake` |
| Resolver | `src/picwise_search/live_search_resolver.py` |
| Page text ("Understood as", "Only some of the four match: X (n of 4)", "could not match") | `src/picwise_surface/reference.py` |
| Did-you-mean / broad-suggestion injection, impression events, query log hook | `src/picwise_app/app.py` (`api/index.py` delegates to it) |
| Awin feed loading (`AWIN_FEED_URL` with 6 h reuse, `AWIN_FEED_FILE`) | `src/picwise_providers/awin_adapter.py` |
| Query log for NLU training (inactive until configured) | `src/picwise_app/query_log_sink.py`, `deployment/supabase_query_log.sql` |

Tools:

- `python -I tools/price_first_eval.py <feed.csv.gz> out.json [--cards] [--compare earlier.json]`
  — 118 buyer searches on a real feed file: what each page shows, and how long it took
- `python tools/prepare_catalogue.py [--feed-file F] [--out PATH] [--keep-going]
  [--static-dir DIR]` — the feed prepared once (step 5); a server reads it with
  `PICWISE_PREPARED_CATALOGUE_FILE`, a Vercel deployment from its own build
- `python tools/nlu_misspelling_benchmark.py` — 706 misspelled queries end to end
- `python tools/check_awin_feed.py --url "<feed link>"` — what a real feed will do
- `python tools/nlu_mistake_report.py queries.txt` or `--from-query-log` — lexicon review queue
- `python tools/build_picwise_search_artifact.py` — rebuild the search artifact

Docs: `docs/PICWISE_GOOGLE_PAGES_SPEC.md` (the pages for Google, the index, the server's
catalogue; 2026-10-23), `docs/picwise_misspelling_understanding.md`, `docs/awin_feed_setup_el.md` (Greek
guide for the owner), `docs/vercel_daily_feed_setup_el.md` (Greek: the prepared feed on
Vercel, every day), `docs/picwise_query_understanding.md`,
`docs/picwise_mission_decision_delivery.md`.

## Current numbers (local fixtures only)

- Misspelling benchmark: **93.8% pass, 0 wrong kind of product shown** (2026-10-17,
  after part 3b; 96.0% until 2026-10-16). It fell to 93.9% with the owner's rule that
  "mobile phone" and «κινητό» show basic phones, because 15 of its cases expect
  smartphones; those cases were left as they are so the number shows the rule.
- Test suite, last full run **2026-10-17** for step 5's second part (all modules but
  the two hour-long ones, one process per module, four at a time, after the commit):
  **238 of 240 pass**, 2,082 tests, 48 skipped; the two that fail are the same two as
  below. Misspelling benchmark unchanged (93.8%, 0 wrong).
- Before it, the same day for step 5's first part (all modules but the two
  hour-long ones, one process per module): **237 of 239 pass** with the contracts test
  run after the commit. The two that fail fail the same on the code before this work:
  `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`. At `deab42a` (step 4)
  `test_picwise_search_index_blind_evaluation_stage6a` failed one of its 13 tests, as
  before step 3 (about 43 min; run it on its own, as `test_picwise_learning_stage7b`,
  about 41 min, which passes).
- Older, kept for the history: full run **2026-10-12** after the description rule, the spec reader
  and the fixture updates (228 modules, every module except the two hour-long ones,
  one process per module, `PYTHONPATH=.`): **226 modules pass, 2 fail**, and both
  failures are the two that already predated this work. One module failed during the
  run and was fixed inside it -- `test_picwise_product_type_coverage_matrix`, whose
  weak-feed-opportunity case wrote a 47-character description, below the 120 the
  owner's rule requires, so its four rows stopped being showable; it passes on
  `9ac4bb8`. Two things to know before running it: the modules must be run with
  `PYTHONPATH=.` (several import `from src.picwise_...`, which fails when a module is
  run as a script from `tests/`), and `tests/` has no `__init__.py`, so
  `unittest discover` cannot load it -- run one process per module.
  Older note, kept for the history: full run 2026-10-08 after the F3/F4 fixes (224
  modules): **1,810 tests, 2 failures, 48 skipped** (skips need the operator's private
  feeds). The two failures predate all of this work and fail identically on `4475192`
  (checked in a clean worktree):
  `test_picwise_canonical_vocabulary_registry_stage2`,
  `test_picwise_search_index_generated_blind_stage4` (graph-alias leet records in the
  registry). `test_picwise_learning_stage7b` passes in about 41 min;
  `test_picwise_search_index_blind_evaluation_stage6a` takes about 43 min and, run on
  2026-10-16, fails one of its 13 tests ("amazon" and "galaxy" missing from its broad
  terms), the same on the code before step 3.
- Cold start through `api/index.py`, 19-row fixture: first request 677–724 ms, import plus
  first request 1,045–1,078 ms (target 1,500 ms). A real feed adds its download and parse.

## Waiting on the owner

1. ~~**Awin: link set, live result NOT VERIFIED.**~~ **Verified live on 2026-10-11**: a
   new feed (11,573 UK electronics products, category-based, Electronics only) is set
   in Vercel, `/private-beta-readiness` reports `provider_feed_ready`, and
   `/search?q=ακουστικα` returns four real headphones with one suggested, all in GBP.
   The owner's manual Redeploy works again (the GitHub App is installed), so an
   environment change no longer needs a commit. Older note, kept for the history: On 2026-10-10 the owner created a
   Create-a-Feed link (Legacy format, CSV, comma, gzip, a handful of UK advertisers in
   "Awin" datafeed format, about 15,000 products, GBP prices) and set it in Vercel as
   `AWIN_FEED_URL` (Production only, Secret). Next: check
   `/private-beta-readiness` shows `provider_feed_loaded`, then searches on the live
   site. Most of those advertisers sell kinds the concept lexicon does not know yet
   (flowers, wine, perfume, fashion), so many searches will truthfully show no four.
   `tools/check_awin_feed.py` now also reports how much of the feed is not new ("Not
   new (shown only when asked for): n of m eligible"), worth reading on the real feed.
1b. **Shops, not feed settings, decide what data PicWise has.** The owner asked on
   2026-10-12 whether the thin feed was a Create-a-Feed misconfiguration -- a
   reasonable guess, and it is answered: no. The feed arrives with **all 149 Awin
   columns**, nothing was left unchecked, and `specifications` is filled by three of
   its shops (Baccus 100%, 4x4 Predator 79%, LIKA 100%), so the column works and the
   emptiness is each merchant's own upload. Awin passes a merchant's file through
   unchanged, so no setting on the owner's side can make a shop send descriptions or
   specifications. What each shop sends, measured:

   | Shop | Rows | Description | Specs | product_type | Brand | EAN |
   | --- | --- | --- | --- | --- | --- | --- |
   | Boxed2me | 3,474 | 97% (median 598 chars) | 0% | 99% | 100% | 94% |
   | Aperturee | 1,802 | 100% (298) | 0% | 0% | 100% | 0% |
   | TV Cables | 1,745 | 81% (258) | 0% | 0% | 100% | 0% |
   | **Geekbuying** | **877** | **0% (column empty)** | 0% | 0% | 0% | 0% |
   | Cerqular | 672 | 97% | 0% | 100% | 100% | 11% |
   | Tooled Up | 423 | 98% | 0% | 0% | 100% | 100% |
   | 4x4 Predator | 109 | 100% | **79%** | 100% | 0% | 42% |
   | Baccus (UK) | 18 | 100% | **100%** | 100% | 0% | 0% |

   Two shops are worth naming. **Geekbuying** (877 products: the televisions, TV
   boxes, vacuum cleaners, robot vacuums and treadmills) sends a title, a price and
   nothing else -- no description, no product type, no brand, no EAN. **Xiaomi RO**
   (66 products) does send a `description`, but it is the product's own name repeated
   ("Xiaomi TV S Pro Mini LED 55'' 2026", median 27 characters), which is exactly the
   case `product_description.product_description_text` rejects. So the owner's lever
   is which shops go into the feed, and `tools/check_awin_feed.py` now prints this
   table for any feed so the decision can be made on measurement.

2. ~~**A feed that carries real product ratings.**~~ **Dropped by the owner on
   2026-10-15** (price first, see "Start here"). Kept as the record. The owner decided on 2026-10-11 that
   the recommendation must follow a product's rating rather than its price, and the
   current feed has none at all (`check_awin_feed.py` now reports this as "Products
   with a real rating"). Nothing changes in the ranking until such a feed exists:
   inventing a rating is forbidden. The owner is looking for Awin advertisers whose
   feed fills `rating` / `average_rating`; the way to tell is to build a feed with
   them and run the tool over it.

   What that feed does send was measured on 2026-10-11 over all 149 of its columns
   (11,573 electronics products), because the question "is a quality signal available
   at all?" cannot be answered by reading one column:

   | What | Filled |
   | --- | --- |
   | `description` (long text) | 92% |
   | `brand_name` | 83% · `mpn` 67% · `ean` 34% · `product_GTIN` 26% |
   | `aw_image_url` | 100% · `alternate_image` 37% |
   | `condition` | 63% |
   | `delivery_cost` 31% · `delivery_time` | 23% |
   | `stock_status` 23% · `stock_quantity` | 13% (`in_stock` is 100% but constant) |
   | `rrp_price` 10% · `saving` | 1% |
   | `product_short_description` 16% · `specifications` | 1% |
   | `keywords` 13% · `colour` | 7% |
   | **`rating` / `average_rating`** | **1%, every value "0"** |

   So the feed has no ratings and no usable specification column, but it does carry a
   description for nearly every product, and specifications are often written inside
   it. Measured per kind, products carrying at least one readable number (inches, W,
   Hz, mAh, GB, hours, metres) in title only vs. in title or description:
   headphones 19% -> 75%, speaker 49% -> 75%, camera 5% -> 47%, amplifier 69% -> 91%,
   microphone 0% -> 27%, charging_cable 96% -> 98%, television 78% (unchanged),
   projector 15% -> 24%, tv_box 32% (unchanged). And the kinds that stay empty either
   way: watch and smartwatch 9%, vacuum_cleaner 3%, backpack and phone_case 2%.

   Two things follow. Reading specifications from the description, not only the title,
   is the one route to a real quality signal from this feed -- and it is marketing
   copy, so a number found there needs to be tied to the product rather than to an
   accessory or a comparison ("better than 32 inch models"). And for whole kinds there
   is nothing to read at all, which is a decision for the owner, not a gap to paper
   over: their rule is that price must not decide, and ANTI_FAKE forbids inventing a
   quality signal, so those kinds can only show four and declare that no ranking
   signal exists.
3. **Supabase project for the query log — and for click/decision events.** Click and
   impression events live only in a per-process list today (audit D5), so production
   records no click durably. None of the account's three projects is PicWise's (one
   inactive, `taxi-chat` belongs to another app, `mysubby.cloud@gmail.com`). Do not
   create tables in them without the owner saying which; a new project may cost money,
   so ask first. The owner said on 2026-10-08 to decide this later: create nothing.
4. Optional: allow `productdata.awin.com` in the cloud environment's network settings so
   a session can check the real feed, and `picwise.subby.cloud` so a session can check
   the live site itself (the owner asked on 2026-10-18 why Claude does not look itself:
   this conversation could not reach the site, DNS refused by the network policy, and
   had no Vercel connection). Steps: the cloud environment menu in the session's title
   bar, Edit, Network access, Allowed domains
   (https://code.claude.com/docs/en/cloud-environments#network-access). A Vercel
   connection for SUBBY CLOUD (claude.ai/customize/connectors) may let a session read
   the builds; both take effect in a new session.

## Next engineering steps, in order

0. **Price-first plan** (`docs/picwise_price_first_plan_2026-10-15.md`): the founding
   files were changed to it on 2026-10-16. Measured on the third feed, and built in
   small tested steps in the order recorded there. **Step 1, only the kind asked for,
   is done** (section "Step 1 built"; `tests/test_picwise_strict_kind_reading.py`), and
   so is **step 2, English before greeklish** (section "Step 2 built";
   `tests/test_picwise_english_over_greeklish.py`). **Step 3, the price-first
   engine, part 3b and step 4, the search page, are done too** (sections "Step 3
   built", "Part 3b built", "Step 4 built"; `tests/test_picwise_price_first.py`,
   `tests/test_picwise_search_page.py`). Next is step 5, data prepared daily (see
   "Start here" for its first speed-up). The plan's "engineering, later" section lists
   what is still needed: `custom_6` for tyres, a category for Living and Home, and a
   store refreshed daily.

0. ~~Every product shown carries availability, a price, an image and a description.~~
   **Done, 2026-10-12** (owner rule; recorded in `docs/PICWISE_DECISION_CONTRACT.md`,
   section "What a product must carry to be shown"). The first three were already
   required for a card; the description is new, lives in
   `picwise_providers.product_description`, and is read by both the card gate and
   `tools/check_awin_feed.py`. It costs 1,495 of the real feed's 11,573 products, and
   the cost is per shop, not per kind: Geekbuying (877) and Xiaomi RO (66) send no
   descriptions at all, so the kinds only they carry -- televisions, TV boxes, vacuum
   cleaners, robot vacuums, treadmills, and nearly all watches, smartwatches and
   projectors -- no longer appear. The owner was told before it went in. The feed tool
   prints it per shop so the choice (ask the shop, or drop it from the feed) is visible.
   Two gotchas found while doing it, both now fixed: `tools/check_awin_feed.py` was
   reporting the **feed** eligibility gate under the name of the **card** gate, so it
   claimed 11,573 of 11,573 showable when the real number is 9,954; and every provider
   fixture in `tests/` needed a description, which `tests/fixture_support.py` now
   supplies in text that names no product, because a description is a field the search
   ranks on and fixture text mentioning the product would hand each row free evidence
   for its own kind.
   `tests/test_picwise_product_description_rule.py` (14 tests).

0. ~~Refurbished / used products must appear only when the buyer asks for them.~~
   **Done, 2026-10-10, on `main` since 2026-10-11** (owner decision; recorded in `docs/PICWISE_DECISION_CONTRACT.md`,
   section "Item Condition"). A product the feed calls not new is no longer a candidate
   at all unless the query asks for that condition; when it is asked for, those come
   first, missing slots fill with new products, and the page says how many of the four
   are the condition asked for. `tests/test_picwise_condition_request.py` (22 tests).
   Still open from the same list: the ranking formula with scores
   (`Ranking formula weights: TODO` in the Decision Contract) — the owner decides the
   weights, do not invent them.
1. When the real feed is available: run `check_awin_feed.py`, add concepts for the feed
   types it does not recognise (correctly spelled names only), add held-out cases for
   them, rerun the benchmark — wrong answers must stay at 0. Also check, on the real
   feed, how `in_stock` / `stock_status` / `is_for_sale` are populated: a flag column
   that is identical on every row is treated as unpopulated, a varying one is read.
   Re-run the audit's runtime probes against it (open items in the audit's status table).
2. Cold start on a large feed: every serverless cold start downloads and parses the
   whole feed once. Build a prebuilt eligible-product artifact and measure against
   section 9.
3. Once the query log is connected: review `nlu_mistake_report.py --from-query-log`
   regularly.
4. Merge the word-level NLU (`build_local_nlu_intent`, still `insufficient_data` for
   Greek) and the concept reading into one layer.
5. Investigate the two pre-existing registry failures.

## Known doc conflict (unresolved, owner's call)

**Settled on 2026-10-16:** the price-first plan contradicted `concept.picwise.txt`,
`docs/MISSION.md` and `PROJECT_RULES.md`; the owner chose to change them, and they
were changed (details in `docs/picwise_price_first_plan_2026-10-15.md`).

**Raised on 2026-10-23, the owner's call:** `concept.picwise.txt` section 17 ("SEO
Strategy — Waves Model") and `docs/SEO_WAVES_SPEC.md` ("Each landing targets a specific
purchase-intent query") speak of thousands of landings, one per long-tail query.
Google's guide to generative AI features (May 2026) calls separate content for every
wording of a search scaled content abuse. `docs/PICWISE_GOOGLE_PAGES_SPEC.md` follows
Google: one page per distinct set of products, never per wording. The two files are
unchanged until the owner says so.

Older, and still open:

Three files still describe the project as being in the documentation-only phase:

- `docs/MISSION.md` → "First Phase Boundary": no frontend, no backend implementation
- `PROJECT_RULES.md` section 12 → "Do not build live product UI until mission docs and
  contracts are created and reviewed"
- `docs/IMPLEMENTATION_ROADMAP.md` → "Current Phase: mission/spec/contracts foundation"

Reality: the app is built and deployed (`PROGRESS.md` stages 16-26, stage 22 live on
`picwise.subby.cloud`). So this text is out of date, not a live instruction to stop.
Every other part of `MISSION.md` — the 4+1 contract, the identity rules, the trust and
neutrality commitments — is current and binding. Nothing was changed in these three
files: correcting the phase wording is the owner's decision, not the engineer's.

## Working gotchas

- The cards' markup is read by tests and by `deployment/server/compare_with_vercel.py`
  (design of 31/10): `<article class="pw-card" data-choice-id=...>` or `class="pw-card
  pw-card-recommended"` exactly, no other class on the article; `pw-card-title`,
  `pw-role-label`, `pw-card-description` (the price's place), `pw-price`, `pw-card-shop`,
  `pw-card-stock`, `pw-card-note`. A product alone is the same article inside
  `<section class="pw-grid" data-card-count="1" data-layout="single">`. The search
  page's CSS is `reference._PAGE_STYLES`; two tests pin its `@media (max-width:1099px)`
  rule for the grid.
- Run tests **per module**, a few in parallel; never the whole suite in one process
  (out of memory, hours).
- The prepared file leaves out the Awin columns no rule reads
  (`prepared_catalogue.LEFT_OUT_COLUMNS`). A rule that comes to read one of them must
  take it off that list: answered from the file, it would see the column empty. A test
  in `tests/test_picwise_prepared_catalogue.py` fails while a listed column is named in
  the code that reads feed products.
- A prepared feed file is tied to the code that wrote it: any change to a file under
  `src/picwise_providers` or `src/picwise_nlu` makes old files unusable (the server then
  reads the feed). Prepare again after such a change. Outside Vercel a server reads one
  only when `PICWISE_PREPARED_CATALOGUE_FILE` names it, so tests never pick one up.
- `vercel.json`: a `builds` key makes Vercel skip the build command, so the file would
  silently stop being built; the rewrites point at `/api/index` (the function's name
  without `builds`); Vercel refuses an empty `outputDirectory`, which is why the build
  writes `public/prepared.json`. To see what a change does to a deployment without
  Vercel: `npm install vercel` in a scratch folder, a copy of the repository with a
  hand-written `.vercel/project.json` (`{"projectId":"x","orgId":"y","settings":
  {"framework":null}}`) and `.vercel/.env.production.local` naming a feed file, then
  `vercel build --prod --yes`, and read `.vercel/output` (no login needed).
- The daily renewal is a new production deployment each morning. After an Instant
  Rollback, Vercel stops putting new deployments live until one is promoted by hand
  (as remembered, not checked from here): the renewal would then build every day and
  never go live, and the live file would pass its 30 hours. `prepared_feed` on
  `/private-beta-readiness` shows it (`too_old`).
- Tests rewrite `src/picwise_search_memory/artifacts/search_runtime_v1.json.gz`
  (`built_at` only). `git restore` it before committing.
- `test_picwise_search_graph_contracts_stage1db1` fails while `app.py`,
  `live_search_resolver.py` or `reference.py` have uncommitted changes (it diffs the
  working tree against HEAD); it passes after the commit.
- Changing a file listed in `search_runtime_artifact.get_fingerprint_source_paths()`
  requires rebuilding the artifact, or every cold start rebuilds the index live.
- Two route tables: `src/picwise_app/app.py` (local server) and `api/index.py` (Vercel).
- The cloud environment blocks `productdata.awin.com`, `ui.awin.com`, `api.awin.com` and
  `picwise.subby.cloud`.
- A `pkill -f` or `grep` pattern that matches its own command line kills the shell.
- Fixtures use fictional brands, `.invalid` URLs and `data_provenance=local_test_fixture`.
- Secrets: the Awin link contains the account API key; the Supabase `service_role` key.
  Only as Vercel environment variables — never in the repository, a log or a chat.
- `picwise_buying_pages/fixtures.py` (`load_seed_buying_pages`) is fabricated test data
  (formula prices and ratings, "Picwise Demo" products). It must never back a public
  route; `/best/<slug>` and the sitemap publish nothing until pages are built from real
  feed data. `test_picwise_no_fabricated_public_pages` guards this.
- Availability (`offer_health`): every column is read; a stock **word** ("out of stock",
  "OutOfStock", "discontinued", "pre-order") decides wherever it appears; a bare **flag**
  (0/1) decides only where its column varies across the feed. Selection, card fields,
  recommendation and redirect share one context built over the whole feed — pass it on
  (`feed_ctx`) rather than building a new one from a subset.
- Product identity is GTIN, else brand + MPN (`_product_identity_key`); count products,
  not offers, anywhere a "four" is decided.
- Kind of product (`annotate_product_concepts`): only the words before the first purpose
  word ("for", "with", "για", "με") name the product. Text that names a product only after
  one ("Accessories for Laptops", "Filter for Coffee Machine") is an accessory of it and
  is marked `__accessory__` — never left unread, because a row naming no kind can still
  join a concept by its own words. Accessory words after "with" are what comes in the
  box. Audit finding F4, `test_picwise_product_kind_reading`.
- Accessory penalty (`_title_accessory_penalty`): for a product already verified as the
  kind asked for, accessory words before or inside its name are its type ("Filter Coffee
  Machine", "Battery Lawn Mower", "Stand Mixer"); a part word anywhere, an accessory word
  after the name, a name only after "for", or a Greek name keep the full penalty.
- **What kind of product a feed row is** (`concept_understanding.annotate_product_concepts`),
  tightened on the first real feed, where it answered searches with the wrong kind
  (899 table runners under "τραπέζι", lens caps under "καπέλο", disco balls under
  "μπάλα", USB cables under "οθόνη"). Four rules, each pinned by
  `tests/test_picwise_feed_kind_truth.py`:
  (1) **weak names** (`~word` in the concept table: cap, ball, ring, screen, desktop,
  pc, tripod, controller, mixer, cover) are read from a query but never classify a feed
  product, because in feed text they are almost always part of something else;
  (2) **tail words** (`_MODIFIER_TAIL_WORDS`: runner, mats, ties, clip, ball, light,
  restore…) turn the name before them into a description: "table runner", "cable ties";
  (3) a **category breadcrumb** is read shelf by shelf — the first shelf that names a
  product wins ("Electronics > Cables > Monitor" is cables), any shelf of accessories
  decides for the whole crumb, a shelf naming a product only in passing ("Power banks
  and batteries") names nothing, and a shelf of two kinds is decided by the title
  ("Fans & Heaters");
  (4) when **only a title** says what the product is, a word PicWise cannot read right
  after the name voids it ("Truck Bed Tailgate Extender"), while a colour, spec or pack
  word does not ("Smartwatch Black Dial"). Also: a product type that names what the
  product plugs into ("Smartphone USB-C" on a microphone) gives way when the title and
  the category agree on another kind.
- One currency per answer (owner decision, 2026-10-11, in the Decision Contract):
  `_price_first_products` keeps the currency most of the answer's products are priced
  in, since prices in two currencies cannot be put in one order.
- Condition (`product_condition.py`, one rule for the gate and the cards): a product
  the feed calls not new is shown only when the query asks for that condition. "Not
  new" = a condition column carrying a word from the vocabulary ("Used - Very Good",
  "Refurbished Grade A", "gebraucht"), or such a word in the product's own text
  ("Refurbished Dell"; "used" and "renewed" are read from the column only, not from
  marketing copy). Wording the vocabulary does not hold ("A-stock", "Nuovo", "n/a", a
  bare code) is unknown, not non-new, and stays visible — the reverse would empty a
  whole feed in silence. `check_awin_feed.py` lists the condition values it could not
  read; a real one that means "used" belongs in `product_condition.py`. The request is read from the
  query by `read_condition_request` (Greek, greeklish, English, with typo correction)
  and is never matched against feed text. Asked for, under price first: the answer
  is the products in that condition; when the feed has none, it is the new ones and the
  page says the condition was not matched. The text scan
  sits behind a substring pre-filter for speed (38 ms for 15,000 products, worst case);
  a vocabulary word added without its hint would stop being read, which
  `test_picwise_condition_request` guards.
- Which four are shown: **replaced by price first** (steps 3 and 3b, built
  2026-10-16/17, for every search). Kept as the record of the old rule (owner decision, 2026-10-08, confirmed with its details and
  recorded in the Decision Contract): groups of substantially equivalent products in
  relevance order; a group too big for the free slots is spread across its price range
  (four slots: cheapest, two between, dearest; two: cheapest and dearest; one: the
  middle). All equivalent: the cheapest is recommended and the card says why.
  Merchant free text (keywords, description) never makes a product "more relevant" —
  not for the four, not for the recommendation. `test_picwise_price_range_diversity`.
- A test that renders an empty query schedules a 0.75 s background warm-up; reset it
  (`search_warmup._reset_search_warmup_for_tests`) or it can land in a later test.
- Probe the real path with the deployed entrypoint (`api.index.app`) in-process; the
  audit's probe and adversarial-feed scripts are described in its "Reproduction" note.
