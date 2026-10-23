# PicWise — session handoff

Current state for whoever picks the project up next. Updated 2026-10-23.
`PROGRESS.md` is the chronological log; this file is the "where are we now".

## Next conversation: the server; nothing left out of what is kept (owner, 2026-10-23) -- start here

The owner opened a new conversation for a smaller kept file, then the server («Θέλω να
ανοίξουμε νέα συζήτηση γιατί αυτή έχει βαρύνει και το φτιάχνουμε εκεί»). The smaller
file was then stopped by the owner's rule below.

- **Where the work is:** the branch `ccr-baaad713-r3uvvs`, which took in
  `ccr-c30938cf-v749ay`'s notes. Its code is `main`'s (last merge `7b9624c`, 23/10 16:08
  UTC); it is ahead only by notes (PROGRESS and this file). Bring it into the next
  session's branch first.
- **Owner's rule (2026-10-23): nothing that may serve the pages Google indexes is left
  out of what PicWise keeps.** In their words: «Δεν πρέπει να διαγράψεις τίποτα που θα
  επηρεάσει την ποιότητα χαρακτηριστικά seo ... Τα προϊόντα που θα καλούνται από την
  google μέσω λέξεων κλειδιών θα πρέπει να χτίζουν ένα πεδίο το οποίο να είναι πλήρες
  και να προσθέτει υπεραξία στη σελίδα με βάση τα δεδομένα και τα κριτήρια που έχει η
  google ... Δεν πρέπει να υπάρχουν επιπτώσεις στην κατάταξη ... αν αυτή η ενέργεια που
  ετοιμάζεσαι να κάνεις θα φέρει κακά αποτελέσματα στο μέλλον τότε σταμάτησε την».
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
- **Open, put to the owner on 23/10, not decided:** the `/search` pages carry no
  `noindex` and the site has no `robots.txt` (`/robots.txt` answers 404), while Google
  advises keeping URLs that generate search results from being crawled; the pages meant
  for Google are the `/best/...` buying pages behind their quality gate, which publish
  nothing yet.
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
  below); its last run is `39141651716`.
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

Docs: `docs/picwise_misspelling_understanding.md`, `docs/awin_feed_setup_el.md` (Greek
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
