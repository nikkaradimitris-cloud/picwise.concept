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
2. The work is on the branch **`ccr-99b47f03-l8t4dj`**. `main` and the work's branch
   `ccr-4f47068a-99ikwe` are behind it, at `214f4b9`. Start your own branch from it:
   `git fetch origin ccr-99b47f03-l8t4dj && git checkout -B <your branch> origin/ccr-99b47f03-l8t4dj`.
   A pull request from it to `main` is open (#23, opened from the owner's account on
   11/11). Do not merge it, close it or open another: `main` moves only on the owner's
   yes, by a fast-forward.
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
| this commit | the offers test reads the same on GitHub's runner; the speed measure's two scripts kept | `tests/test_picwise_awin_offers.py`, `tools/bench_make_feed.py`, `tools/bench_search.py` | |

Measured, offline, on a synthetic catalogue of 242,400 products (about the live size
after the cap; `tools/bench_search.py`, 33 searches):

- a search, the median: 558 ms at `214f4b9`, 67 ms now; all 99 answers and pages the
  same, product for product;
- through `wsgi_server` with the keeper: a worker ready 7.3 s after it starts, a
  visitor's first search 56 to 68 ms (live on 10/11: 5.4 to 5.7 s for the first request
  of a worker after the night's file, 2.9 to 3.2 s for its first search of the day);
- 60 searches answered while the catalogue was being changed, the slowest 0.9 s.

Phones, rendered offline in Chromium at 360x640 and 390x664: a card 265 to 281 px tall;
the Recommended and its button on the first screen. The layout at 700 px and wider is
untouched.

Tests on `d412b28`, each module in its own process: 303 modules, 2,671 tests; 301 pass,
2 fail as known (`README.md` names them), 0 fail otherwise. The two slow modules
(`SLOW` in the tool) were not finished here: GitHub's run says.

## 3. Not yet proven: check before anyone relies on it

1. **GitHub's "Tests" run on the branch's last commit.** The first run (`43063549262`,
   on `d412b28`) was red for one old test that failed only on GitHub's runner
   (`test_picwise_awin_offers`: the runner sets `GITHUB_ACTIONS`, the tool then prints a
   mask line); fixed in this file's commit. Read the next run: both jobs. If a slow
   module does not finish in its 7,200 s, say so in `PROGRESS.md`; do not skip it.
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

Each step: look first, change little, tests with it, measure, record. Steps 1 to 6 need
no decision of the owner to be built (they change no wording and no rule); like
everything, they reach the site only on «ανέβασε».

1. **Remember a search's answer** (small). The same search asked twice works twice.
   Keep, per worker, the answers of the last few hundred searches, the key being the
   catalogue in memory (its identity, as `_KIND_INDEXES` does), the offers' state, the
   search as typed, `shown` and every other argument of `resolve_live_search`; drop them
   all when the catalogue changes (`state._put_in_place`,
   `clear_provider_feed_pipeline_cache`). Not for `/out/...`, not for the AI layer's
   jobs, and the searches' log must still get its line each time. Test: the same answer
   with and without it; nothing kept across a catalogue change; bounded size.
   Then `Cache-Control` for a search's page only if the test of
   `test_picwise_security_headers` ("a search's page never says so") is changed with a
   reason: a browser's copy must not outlive the catalogue. Ask the owner first if in
   doubt; leaving the HTML uncached is fine.
2. **The words search** (medium). A search read as no kind, or unsure, goes through
   `_select_products_by_words` (`search_selection.py`) and `_word_lookup`; on the server
   such searches took 2 to 4 s (run `42474826414`). Measure with
   `tools/bench_search.py` ("giftware", "blue ornament", "keepsake piece", "bundle 42"
   are of this path), profile, and bring it under a second without changing an answer
   (compare the answers file with the one of the commit before).
3. **Photos** (small). In `reference.py`: the first card's photo with
   `fetchpriority="high"` and not lazy, the rest `loading="lazy" decoding="async"`
   (check what is there first), and a fixed box so the page does not jump when a photo
   arrives. The rule "a card is seen only once its photo has loaded" stays. Asking a
   Shopify shop's server for a smaller photo (`width=` in the address) is **not** to be
   built until it is proven on real addresses from the server (the nightly photo check
   is the place; a session cannot reach a shop).
4. **"More" brings the next four cards only** (small to medium). Today it loads the
   whole page again. A route that answers the next cards as HTML, asked by the page's
   script and added under the others; the link stays and works without a script; the
   same cards in the same order as today's full page (test both ways); `noindex`; it is
   not a new search for the searches' log.
5. **How many products two or more shops sell** (small). Counted by barcode in the
   night's note (`catalogue_balance.py`, `prepared.json`), per category. Nobody knows
   the number today, and the product pages for Google start from those.
6. **Know when the night failed** (small). The site keeps answering from an old file
   and shows no product after 30 hours; nobody is told. Smallest step: the daily
   session reads `/prepared.json` with `curl` and says in its report when the file is
   older than a day (`docs/PICWISE_DAILY_WORK.md`). An email from the server itself
   needs the owner's choice of address and sender: ask.
7. **A shop's feed that came broken keeps last night's rows** (medium; the owner's yes
   first: for one night the site would show a shop's products of the night before).
   The note of `249cc06` only says it. Needs the night before's rows per shop kept on
   the server. Write the design, put it to the owner, then build.
8. **One table of routes** (medium, no change a visitor sees). `picwise_app/app.py`
   (the local server) and `api/index.py` (the deployment) each list the routes; the
   tests of both must pass unchanged. Only when nothing else is waiting.
9. **The pages for Google** (large; `docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 11:
   step 1 done, next step 2). In order: the catalogue's memory in a database on the
   server (first seen, last seen, price history: the 30-day rule and a true `lastmod`);
   the kinds' pages written each night as finished HTML, by the same rules as the
   search, so a page and a search never disagree; the hierarchy home, categories,
   kinds, products with `BreadcrumbList`; product pages first for what two or more
   shops sell (`Product`, `AggregateOffer`; never a rating or review that does not
   exist); a sitemap per kind of page. Every batch on the owner's word, measured two to
   four weeks in Search Console before the next. This is where the project earns: it
   lives on search engines alone, and today Google may index seven pages.

Also open from before the audit, in the handoff's first section: the ring gap, "pen
dries", "work pans" (wrong cards from the words search: step 2 touches the same code,
measure them together on the server's catalogue).

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

## 6. How the work is checked

The reviewing session will hold each step to this:

- one step, one commit, its tests in it; the message says what and why;
- `python tools/run_test_modules.py --skip-slow` ends 0 on the last commit (about 8
  minutes), and GitHub's "Tests" run is green; no test skipped, weakened or deleted to
  get there (the two known failures stay known, each with its one test);
- a step that claims speed has its numbers before and after, by the same measure, and
  the answers compared: `tools/bench_search.py` writes what each search answered; two
  commits' files must be equal unless the step says which answers change and why;
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
  checkout as the first argument. Keep `<folder>` outside the repository.
- Running tests rewrites `src/picwise_search_memory/artifacts/search_runtime_v1.json.gz`:
  `git checkout --` it before a commit.
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
