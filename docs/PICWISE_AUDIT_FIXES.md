# PicWise — the audit's fixes: what is built, what is left, how it is checked

Written 2026-11-11 for the session that continues this work (owner, 11/11: «Πρέπει να
φτιάξεις ένα αρχαίο με τις διορθώσεις που πρέπει να γίνουν ... θέλω το νέο μοντέλο ... να
διαβάσει αυτό τα αρχείο σε νέα συζήτηση και να ξεκινήσει τις διορθώσεις. Από κει που το
άφησες. Μετά θα σου δώσω εντολή ... να εποπτεύσεις κατά πόσων η δουλειά ... είναι σωστή»).
A later session reviews what is done from here on against section 6.

Για τον ιδιοκτήτη, με δυο λόγια: το αρχείο λέει τι χτίστηκε μετά τον έλεγχο της 10/11
(ενότητα 2), τι μένει να γίνει με σειρά (ενότητα 4), ποιες αποφάσεις είναι δικές σας
(ενότητα 5) και με ποια κριτήρια θα ελεγχθεί η δουλειά (ενότητα 6). Τίποτα δεν έχει
ανέβει στο site.

## 1. Start here

1. Read, in this order: `PROJECT_RULES.md`, `README.md`, the first section of
   `docs/picwise_session_handoff.md`, this file. `PROJECT_RULES.md` wins over everything.
2. The work is on one line, held since 12/11 by two branches at the same commit: the
   work's branch **`ccr-4f47068a-99ikwe`**, from which every session starts, as before
   (`docs/PICWISE_DAILY_WORK.md`), and `ccr-99b47f03-l8t4dj`, on which the audit's
   fixes were built and reviewed. The owner, asked on 12/11 whether to bring the work's
   branch onto this line before the daily session, which did not know this work: «Ναι
   ολοκλήρωσε» (a fast-forward from `214f4b9`). The line holds the audit's fixes, group
   A of section 4 (built by another session on `audit-group-a-2026-11-11`, reviewed)
   and the review's own fix. The branches `audit-group-a-2026-11-11` and
   `audit-group-a-2026-11-12` hold nothing more: do not start from them. `main` is
   behind, at `8c093ca`. Start your own branch from the work's branch:
   `git fetch origin ccr-4f47068a-99ikwe && git checkout -B <your branch> origin/ccr-4f47068a-99ikwe`.
   If the two branches are no longer at the same commit, the work's branch is the line
   (sessions push there); if neither holds the other, stop and tell the owner.
   A pull request from `ccr-99b47f03-l8t4dj` to `main` is open (#23, opened from the
   owner's account on 11/11). Do not merge it, close it or open another: `main` moves
   only on the owner's yes, by a fast-forward.
3. **Nothing of this is deployed.** The live site is still `ace8468`
   (`ccr-1361f1a7-dcpo60`). A push to that branch deploys: never without the owner's
   «ανέβασε» for that commit.
4. The rules that bite most often:
   - the repository is public: no key, no token, no feed file, no feed link;
   - never fetch or click a shop's Awin link; the live site is read with `curl` only;
   - no invented data on a page; a synthetic catalogue is for measuring speed only;
   - one small step at a time, each with its tests, each a commit; measure before and
     after; write what was done in `PROGRESS.md` (a dated line at the end) and at the
     top of the handoff's first section;
   - wording a visitor reads, and anything that changes a decision of the owner, is put
     to the owner first (in Greek) and built on their word.

## 2. What is built (2026-11-10 and 11, from `214f4b9`)

The audit's report is a Claude doc, "Picwise — Πλήρης έκθεση ελέγχου"
(https://claude.ai/artifact/NG1r5CuzPr5nJbE5aaXxHo, the owner's; its last section lists
every proposal). The owner then asked for the fixes: «Ζητώ διόρθωση και βελτίωση των
σημείων που εντόπισσες σχετικά με το μηχανισμό των κώδικα στη ορατότητα σε κινητές
συσκευές την ταχύτητα την ασφάλεια τις προδιαγραφές google».

| Commit | What | Where | Tests |
| --- | --- | --- | --- |
| `8cbef96` | each term's pattern compiled once (a search compiled about 1,400) | `picwise_nlu/category_detector.py` | `test_picwise_term_patterns` |
| `25dc479` | a kind index per catalogue: a search for a kind reads only the products that may be of it | `picwise_providers/search_selection.py` (`_KindIndex`, `_kind_index`, `members_for`) | `test_picwise_kind_index` |
| `ed07a1a` | each worker keeps the prepared catalogue loaded: loads it at start, brings the night's new one in beside the old, one process at a time | `picwise_providers/state.py` (`keep_prepared_catalogue_loaded`, `refresh_prepared_catalogue`), `deployment/server/wsgi_server.py` | `test_picwise_catalogue_keeper` |
| `2ef37c0` | phones (under 700 px): one product a row, photo beside the words, price and button in one row; nothing to tap under 44 px, no text under 12 px | `picwise_surface/reference.py`, `browser_lists.py`, `legal.py` | `test_picwise_phone_layout` |
| `565e8a6` | the seven indexable pages say their one address (`canonical`), `/sitemap.xml`, icons and manifest, `Organization` and `WebSite` on the home page, a search's own `<title>` and `<h1>`, `en-GB` | `picwise_surface/seo.py`, `assets/picwise/` | `test_picwise_google_basics` |
| `e04ba8b` | five security headers on every answer (a content security policy among them), what may be cached, the server's note kept out of Google | `picwise_app/app.py` (`SECURITY_HEADERS`), `api/index.py`, `wsgi_server.py` | `test_picwise_security_headers` |
| `249cc06` | the night's note says which shops' feeds came with fewer than half the rows, and which kinds one or two shops sell | `tools/prepare_catalogue.py` (`_intake_change`), `picwise_providers/catalogue_balance.py`, `deployment/server/print_shops.py` | `test_picwise_feed_shrink_note` |
| `d412b28` | the tests run on each push of code: every module in its own process | `tools/run_test_modules.py`, `.github/workflows/tests.yml` | `test_picwise_run_test_modules` |
| `619f963` | the offers test reads the same on GitHub's runner; the speed measure's two scripts kept | `tests/test_picwise_awin_offers.py`, `tools/bench_make_feed.py`, `tools/bench_search.py` | |
| `56aefb3` | a newer push never cancels the slow modules' job; the measure times the page too and compares two runs | `.github/workflows/tests.yml`, `tools/bench_search.py` | `test_picwise_run_test_modules` |
| `a145201` | the first card's photo asked for first (`fetchpriority="high"`, on no other) | `picwise_surface/reference.py` | `test_picwise_first_photo_priority` |
| `abd2225` | the night's note counts the products two or more shops sell, by barcode, in all and per category | `picwise_providers/catalogue_balance.py`, `deployment/server/print_shops.py` | `test_picwise_shared_products` |
| `f587ba7` | the daily session reads the night's note and reports first a failed night, a file over 30 hours old, a feed that shrank | `docs/PICWISE_DAILY_WORK.md` | `test_picwise_daily_night_check` |
| `52a9f20` | the blind evaluation's broad negative terms are the eleven its test expects (nine since 21/05: section 3, point 1); "Tests" also on branches named `claude/...` and `audit-...` | `picwise_search_memory/blind_evaluation.py`, `.github/workflows/tests.yml` | `test_picwise_blind_negative_terms` |

Measured, offline, on a synthetic catalogue of 242,400 products (about the live size
after the cap; `tools/bench_search.py`, 33 searches):

- a search, the median: 558 ms at `214f4b9`, 67 ms now; all 99 answers and pages the
  same, product for product;
- through `wsgi_server` with the keeper: a worker ready 7.3 s after it starts, a
  visitor's first search 56 to 68 ms (live on 10/11: 5.4 to 5.7 s for the first request
  of a worker after the night's file, 2.9 to 3.2 s for its first search of the day);
- 60 searches answered while the catalogue was being changed, the slowest 0.9 s;
- on a machine doing nothing else, `619f963`: a search for a kind 15 to 170 ms; a search
  read as no kind or as unsure ("keepsake piece", "giftware", "bth rugs", "laptop bag")
  60 to 240 ms; the whole page a visitor gets 13 to 175 ms.

Phones, rendered offline in Chromium at 360x640 and 390x664: a card 265 to 281 px tall;
the Recommended and its button on the first screen. The layout at 700 px and wider is
untouched.

Tests on `52a9f20`, each module in its own process: 307 modules, 2,693 tests; 305
pass, 2 fail as known (`README.md` names them), 0 fail otherwise, here and on GitHub's
runner (run `43116890274`). The two slow modules (`SLOW` in the tool) pass in full on
that commit, here and there: both jobs of that run are green.

## 3. Not yet proven: check before anyone relies on it

1. **The slow modules: closed on 11/11, nothing left to read.** Until that day the two
   slow modules had finished nowhere. `test_picwise_learning_stage7b` passed, and
   `test_picwise_search_index_blind_evaluation_stage6a` finished for the first time
   (3,256 to 4,020 s) and failed one test of 13,
   `test_negative_broad_terms_are_included`, alike on `619f963`, `56aefb3` and `925f211`
   (runs `43068207518`, `43071701101`, `43081356387`). The cause, found in the review:
   since 2026-05-21 (`6944f94`) that test expects eleven broad terms among the
   generated cases and the generator's list held nine ("amazon" and "galaxy" were put
   into the test and into the unsafe broad queries, not into the list). It could never
   pass; nobody saw it, the module never having been run to its end. Neither the
   audit's fixes nor group A touch those files. Fixed in `52a9f20`: the two terms in
   the list, and `tests/test_picwise_blind_negative_terms.py`, which says the same in
   20 seconds on every push. On that commit both slow modules pass in full, here and on
   GitHub: run `43116890274`, both jobs green at 23:53 UTC of 11/11, the first green
   "Tests" run there has been. From here on a red job is a new fault: say which test
   and what it printed, in `PROGRESS.md` and to the owner, and change nothing for it
   until its cause is known. Never skip a module.
2. **The keeper has never run on the server**, with gunicorn and the real catalogue.
   At the night's change each worker builds the new catalogue beside the old one, one
   worker at a time: the service's memory (3,816 MB on 09/11; ceiling 11 GB) rises by
   about one catalogue for that time. To be read after the first night.
   `PICWISE_CATALOGUE_KEEPER=off` puts loading back as it was.
3. **The phone layout changes a decision of the owner** (31/10: "Phones: two cards a
   row"). It was seen in offline renders only, on no real phone. The owner must see it
   and say yes before it is deployed; if no, `2ef37c0` is reverted alone.
4. **The home page's structured data and the icons** were written from this
   repository's spec, not checked in Google's own tools (a session cannot open them).
5. **The content security policy** was tried in a browser offline, the shops' photos
   replaced by local ones. On the site: photos show, the microphone works, favourites
   and recently viewed work, the AI layer's sentence arrives.
6. A deployment prepares the catalogue again (the code's fingerprint changed): as usual.

When the owner says «ανέβασε» for a commit: push it to `ccr-1361f1a7-dcpo60` by a
fast-forward, read the deployment's run, then with `curl` only: `curl -sI` on `/`,
`/search?q=kettle`, `/prepared.json` (the five headers; `X-Robots-Tag: noindex` on the
search and the JSON); `/robots.txt` (its `Sitemap:` line) and `/sitemap.xml` (seven
addresses); the first search after the deployment and the first after the next night's
file (both under a second); the memory, from the deployment's and the read-only
workflows' output; `prepared.json` the morning after (`intake_change`,
`kinds_from_few_shops`).

## 4. What is left, in order

Each step: look first, change little, tests with it, measure, record.

**Re-examined on 2026-11-11** (owner: «Εξέταση πάλι το κείμενο που μου δίνεις είναι σωστό
για αυτό που θέλουμε να κάνουμε?»), each step against the code and a measure on a quiet
machine. The first version of this section asked for two speed steps the numbers do not
ask for, and a third that was mostly in place. Group C says which and why, so that
nobody builds them on the strength of the first version.

### A. Built on 11/11 by another session; reviewed on 12/11: correct

**The review, against section 6.** Each step is one commit with its tests in it
(`a145201`, `abd2225`, `f587ba7`); no test was weakened (the one changed,
`test_picwise_server_print_shops`, now checks one line more, word for word); every
module but the slow ones passes on `925f211`, here in a clean copy and on GitHub (run
`43081356387`, started by hand: the branch's name started none by itself); nothing a
visitor reads changed, nothing was deployed, `main` and #23 were not touched, the log
and the handoff were written. Read against the live site's note (11/11 22:49 UTC, with
`curl`): its keys are those step 3 names (`prepared`, `prepared_at`, `written_at`); the
balance is measured over the 244,494 products the cap keeps, so step 2's count is too;
the server's report runs on that note without a fault. Three notes, none a fault: on a
page "More" drew, the photo asked for first is the first card's while the visitor lands
on the fifth (the first is already in the browser from the page before); step 2 counts
by barcode alone, so products the site joins by brand and part number are not in it:
the number is a floor; the session ran the suite on each commit, not before it, for the
reason section 7 now gives. The steps as they were asked for:


1. **The first card's photo asked for first** (tiny). `fetchpriority="high"` on the
   first card's `<img>` and on no other (`picwise_surface/reference.py`, where
   `loading` is chosen). The rest is already there: a 400x400 box, the first row
   `eager`, the others `lazy`, `decoding="async"`. Test: one photo of a page carries
   it, the first card's. The rule "a card is seen only once its photo has loaded"
   stays. Asking a Shopify shop's server for a smaller photo (`width=` in the address)
   is **not** to be built: it is proven on no real address, and a session cannot reach
   a shop.
2. **How many products two or more shops sell** (small). Counted by barcode, over the
   products the prepared catalogue holds, in all and per category, in the night's note
   (`picwise_providers/catalogue_balance.py`, `prepared.json`) and in
   `deployment/server/print_shops.py`. Nobody knows the number today, and the product
   pages for Google start from those products. Tests with fixture rows: a barcode two
   shops carry counts once, one shop's twice-listed barcode does not count, no barcode
   never counts.
3. **Know when the night failed** (small). The site keeps answering from an old file
   and shows no product after 30 hours; nobody is told. The daily session reads
   `/prepared.json` with `curl` (`prepared_at`, `intake_change`) and puts first in its
   report a file older than 30 hours, or a shop whose feed shrank
   (`docs/PICWISE_DAILY_WORK.md`). An email from the server itself needs the owner's
   choice of address and sender: ask, do not build.

### B. After the deployment (only on the owner's «ανέβασε»; nothing of B before it)

4. **The deployment and its checks**: the end of section 3.
5. **The real speed, on the site.** With `curl` (it leaves no line in the searches'
   log), about 30 searches: kinds, typing slips, searches read as no kind, and the
   first search after the next night's file; the time to the first byte and in all,
   each written in `PROGRESS.md` beside 10/11's (a search 0.85 to 1.22 s; 2.9 to 3.2 s
   the first of a worker's day; 5.4 to 5.7 s the first after the night's file). Never
   a shop's link. The next speed step, if any, is chosen from these numbers.

### C. Not to build unless B's numbers ask for it

- **A memory of searches' answers** (the first version's step 1). Little to gain at
  the times above, and a real way to go wrong: an answer depends on more than the
  search and the catalogue. A stored answer of the AI layer arrives after the first
  page and must then put the fitting products first
  (`provider_feed_fitting_product_ids`); the offers' file, the photos' file and the
  date change it too. A memory that misses one of them shows yesterday's cards. If it
  is ever built: all of them in its key, a switch that turns it off, and the measure
  timing the answer worked out, not the one remembered.
- **A faster words search** (the first version's step 2). No measure shows it slow.
  The 2 to 4 s of run `42474826414` were on 597,270 products, before the cap (242,817
  now) and before the kind index; and my 2.9 s for "keepsake piece" was taken with
  other work running on the machine: alone, it is 0.1 to 0.25 s.
- **"More" without a new page** (the first version's step 4). The link already lands
  on the first new card (`#pw-choice-N`), and the page now takes about a tenth of a
  second to make. With the design work, if the owner wants it.

### D. Larger, each on the owner's word

6. **A shop's feed that came broken keeps last night's rows** (medium; the owner's yes
   first: for one night the site would show a shop's products of the night before).
   The note of `249cc06` only says it. Needs the night before's rows per shop kept on
   the server. Write the design, put it to the owner, then build.
7. **One table of routes; May's packages that serve no page set aside** (medium, no
   change a visitor sees). `picwise_app/app.py` (the local server) and `api/index.py`
   (the deployment) each list the routes; the tests of both must pass unchanged. List
   first what nothing imports. Only when nothing else is waiting.
8. **The pages for Google** (large; `docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 11:
   step 1 done, next step 2). In order: the catalogue's memory in a database on the
   server (first seen, last seen, price history: the 30-day rule and a true `lastmod`);
   the kinds' pages written each night as finished HTML, by the same rules as the
   search, so a page and a search never disagree; the hierarchy home, categories,
   kinds, products with `BreadcrumbList`; product pages first for what two or more
   shops sell (`Product`, `AggregateOffer`; never a rating or review that does not
   exist); a sitemap per kind of page. Every batch on the owner's word, measured two to
   four weeks in Search Console before the next. This is where the project earns: it
   lives on search engines alone, and today Google may index seven pages. It waits for
   the owner's decisions 6 and 7 of section 5.

Also open from before the audit, in the handoff's first section: the ring gap, "pen
dries", "work pans" (wrong cards): they need the server's catalogue, a read-only
workflow, after the deployment.

## 5. The owner's decisions

Asked or to be asked, in Greek, one short question each; build only on the answer.

| # | Question | State |
| --- | --- | --- |
| 1 | The domain | Answered 11/11: «Το πλάνο είναι το site να βγει σε υπό τομέα subby.Cloud». So `picwise.subby.cloud` stays the one address (`seo.DEFAULT_CANONICAL_ORIGIN`; `PICWISE_CANONICAL_ORIGIN` changes it without code). Told to the owner: Google indexes a subdomain like any site; the cost comes only if it moves later |
| 2 | More shops | Answered 11/11: «Θα προσθέσουμε καταστήματα με ετίματα στις κατηγορίες που λείπουν». The night's note lists the kinds one or two shops sell (`kinds_from_few_shops`): give the owner that list, largest first, when asked which shops to apply to |
| 3 | The phone layout of `2ef37c0` | To be seen by the owner (section 3, point 3) |
| 4 | «ανέβασε» for this branch | Waiting |
| 5 | A new Awin token | The offers are not fetched since 03/11 (401); "offers first" has nothing to work on |
| 6 | Search Console (and Bing) for `picwise.subby.cloud`, the sitemap given there | The owner's account; nothing is measured without it |
| 7 | The first batch for Google: only kinds three or more shops sell? | 90 of 265 kinds on 10/11 |
| 8 | A cap per shop beside the 15% a category | One shop was 61% of the catalogue on 10/11 |
| 9 | Ask InStock UK for a category in its feed | Up to 768,930 of its rows are cut for having none; only together with 8 |
| 10 | The words of the empty pages; the shop's name as a buyer knows it ("View at Geepas", not "Geepas Partner Program"); the price-and-stock line once a page instead of on every card | Wording and the Decision Contract: propose the exact text, wait |
| 11 | A lasting record of clicks to shops, and `clickref` on the link | Changes the privacy page's text |
| 12 | A limit of requests per visitor; closing `/subby-proof` and `/private-beta-readiness` | The first counts by address for a moment (privacy); the second touches May's proof pages and their tests |
| 13 | The scanning screen's count | The owner: with the design work |
| 14 | An email from the server itself when the night's preparation fails (4.A.3) | To be asked: which address it goes to and who sends it; until then the daily session reports it first (`docs/PICWISE_DAILY_WORK.md`, step 2) |

## 6. How the work is checked

The reviewing session will hold each step to this:

- one step, one commit, its tests in it; the message says what and why;
- `python tools/run_test_modules.py --skip-slow` ends 0 on the last commit (about 8
  minutes), and GitHub's "Tests" run is green; no test skipped, weakened or deleted to
  get there (the two known failures stay known, each with its one test);
- a step that claims speed has its numbers before and after, by the same measure, on a
  machine doing nothing else, and the answers compared: `tools/bench_search.py` writes
  what each search answered and `--compare` must find no difference between two
  commits' files, unless the step says which answers change and why;
- a step taken for speed names the measure that asks for it (section 4, C);
- nothing a visitor reads, and no rule, changed without the owner's words quoted in
  `PROGRESS.md`;
- at 700 px and wider the pages are as they were, unless the step is about them;
- nothing deployed and `main` not moved without the owner's word; no key, token, feed
  or feed link in the repository; no shop's link fetched;
- `PROGRESS.md` and the handoff say what was done, what was measured and what was not.

## 7. Practical notes

- The speed measure (never the site, never real products):
  `python tools/bench_make_feed.py . <folder>/feed.csv`, then
  `python tools/prepare_catalogue.py --feed-file <folder>/feed.csv --out <folder>/catalogue.json.gz`,
  then `python tools/bench_search.py . <folder>/catalogue.json.gz <folder>/answers.json`.
  For the commit before: `git worktree add <folder>/base <commit>` and give that
  checkout as the first argument; then
  `python tools/bench_search.py --compare <one answers.json> <the other>`. Keep
  `<folder>` outside the repository, and run nothing else on the machine meanwhile:
  no test run, no second measure.
- Running tests rewrites `src/picwise_search_memory/artifacts/search_runtime_v1.json.gz`:
  `git checkout --` it before a commit.
- Run the whole suite on the commit, with nothing uncommitted, and push only when it
  ends 0: `test_picwise_search_graph_contracts_stage1db1` reads `git diff HEAD` and
  fails while some files (`picwise_surface/reference.py` among them) have an edit not
  yet committed (found by the session of 11/11).
- GitHub's "Tests" starts by itself on a push of code to a branch named `ccr-...`,
  `claude/...` or `audit-...`; on any other name, start it by hand on the last commit.
- A new test module that needs another module's helpers imports the module and
  subclasses (`import test_x as x`; `class Mine(x.Base)`); importing the class by name
  runs its tests twice.
- The phone rules live inside `@media (max-width:699px)`; the rules outside it are
  pinned by older tests.
- The policy of `SECURITY_HEADERS` refuses any script, style or font from another
  site: a page asks only for its own.
- A change under `src/picwise_providers` or `src/picwise_nlu` changes the code's
  fingerprint: the next deployment prepares the catalogue again (about 17 minutes).
- A session reaches `picwise.subby.cloud` and nothing else; the server is read through
  the deployment's run and the read-only workflows the handoff names.
