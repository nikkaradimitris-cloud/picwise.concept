# PicWise — session handoff

Where the project is now and how to work on it; short on purpose. Updated 2026-11-12.
`PROGRESS.md` is the dated log. The history before 12/11 is kept whole in
`docs/archive/picwise_session_handoff_until_2026-11-12.md` (this file as it was, 3,959
lines) and `docs/archive/PROGRESS_log_until_2026-11-08.md`; read them only to trace how
a decision came about.

## Next conversation: start here

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
    shop out of stock is unlikely: find which column and value say so (a flag a shop
    never fills?), then fix by cause or have the shops' catalogue bot read their stock.
  The steps of the mechanism in full, with the night's numbers of 12/11:
  `docs/PICWISE_AUDIT_FIXES.md`, section 4, group E.
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
| The feed gate and the card gate | `src/picwise_providers/eligibility.py`, `offer_health.py` |
| The shops' catalogue bot (03:40 UTC) | `deployment/bot/shop_catalogue_bot.py` |
| The pages: search, home, info pages, phones | `src/picwise_surface/reference.py`, `legal.py`, `seo.py` |
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
