# PicWise — session handoff

Where the project is now and how to work on it; short on purpose. Updated 2026-11-13.
`PROGRESS.md` is the dated log. The history before 12/11 is kept whole in
`docs/archive/picwise_session_handoff_until_2026-11-12.md` (this file as it was, 3,959
lines) and `docs/archive/PROGRESS_log_until_2026-11-08.md`; read them only to trace how
a decision came about.

## Next conversation: start here

- **Next (owner, 13/11 evening): «ΘΕΛΩ ΔΙΑΣΙΝΔΣΗ . Claude in Chrome, στον υπολογιστή
  ΜΟΥ».** The owner wants Claude to reach the Google Ads account and check it
  regularly. A login or password is never shared; this cloud session cannot reach the
  owner's computer (no computer folder offered), so **the next conversation runs from
  the Claude desktop app on the owner's computer, with Claude in Chrome**, in the owner's
  own signed-in Chrome, the owner watching. Its first work, in order: (1) the campaigns
  list empty, spend 0, billing showing no charge; (2) Keyword Planner opens (Tools →
  Planning → Keyword Planner, or `ads.google.com/aw/keywordplanner/home`); (3) the first
  file: United Kingdom, English, Google, the last 12 months, "Discover new keywords",
  downloaded as CSV and brought to a cloud conversation on this repository; (4) a monthly
  check, its day and hour asked of the owner. Never "New campaign", never "Apply" on
  Google's Recommendations, no Google tag on the site.
  - **The account, made 13/11** (the conversation "Google Ads", branch
    `claude/picwise-google-ads-setup-d6qm2i`, guided screen by screen from the owner's
    screenshots): no Expert-mode link appeared in Google's new sign-up; the linked
    accounts skipped (a phone number Google filled in itself removed); at the goal's
    screen «Δεν είστε έτοιμοι για μια καμπάνια; Μόνο ρύθμιση λογαριασμού», so **no
    campaign**; billing country Greece, time zone (GMT+02:00) Greece (neither changes
    later), payments profile individual, use "Business". Google opened nothing without a
    payment method (Keyword Planner's address sent back to the payment page), so on the
    owner's choice a card was added: a hold of €10 released within a week, nothing
    charged while there is no campaign, a prepaid or virtual card advised; told it is no
    subscription. The Google tag (GTM) Google offered at the end is **not** put on the
    site: no ads to measure, and UK visitors would need a cookies notice. Not seen yet:
    the campaigns list and Keyword Planner's page.
  - **What holds from before** (31/10 and 13/11; read Google's own help again before each
    step, it changes): without spending on ads Keyword Planner gives ranges ("100–1K"),
    enough for the keywords of few searches, coarse for ranking the ten (Google Trends,
    free, orders products within a range). A file of keyword figures holds no secret; a
    login, password or key never goes into a chat (an API's key into GitHub's secrets).
    The seed words: the kinds of the keywords' step 1 (three shops or more, products of
    £80 or more, `docs/PICWISE_GOOGLE_PAGES_SPEC.md`, "Keywords"), drawn from the
    catalogue once the owner says yes; for the ten ("Most popular in the UK",
    `picwise_surface.trends`), broad UK shopping words. Nothing of Google's numbers is
    shown on the site.
  - **The API, set aside for later** (an automatic monthly pull through GitHub Actions
    would make the checks need no one): since 9-10/09/2026 the developer tokens are
    retired and access levels belong to a Google Cloud project; the first level,
    Explorer, restricts keyword planning; Basic needs an application and brand
    verification and is often refused. From search results only: developers.google.com
    and support.google.com are outside this cloud session's network; read them again
    before any step.
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
  (`docs/PICWISE_DAILY_WORK.md`). `ccr-99b47f03-l8t4dj` carried the audit's fixes and
  is at the same commit.
- **The server:** a push to `ccr-1361f1a7-dcpo60` deploys that commit
  (`.github/workflows/server-deploy.yml`, `deployment/server/deploy.sh`): only on the
  owner's «ανέβασε» for it, by a fast-forward. The deployment prepares the catalogue
  (about 14 minutes, peak about 9.3 GB) and restarts the site; each worker loads the
  catalogue in the background (`state.keep_prepared_catalogue_loaded`). A rollback is
  a push of a revert commit, never a force push.
- **`main`:** what is live plus its records, moved only on the owner's yes, by a
  fast-forward; behind the site since 12/11. A push to `main` makes Vercel build the
  backup. Pull request #23 (from `ccr-99b47f03-l8t4dj`) is the owner's; leave it.
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
  Recommended, "More" by four; offers first, then the cheapest; commission never a
  criterion (`PROJECT_RULES.md` 2 and 5, `docs/PICWISE_DECISION_CONTRACT.md`).
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
