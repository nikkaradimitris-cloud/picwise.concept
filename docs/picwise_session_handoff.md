# PicWise — session handoff

Current state for whoever picks the project up next. Updated 2026-10-08.
`PROGRESS.md` is the chronological log; this file is the "where are we now".

## Where the work is

- Repository: `nikkaradimitris-cloud/picwise.concept`
- **Everything is on `main`.** PR #2 was merged on 2026-10-08 (merge commit `148a552`,
  a normal merge, by the owner's instruction). It carried all of PR #1, so GitHub marked
  PR #1 as merged too; the owner chose this knowing it. `main` holds the 4+1 Awin path,
  the misspelling understanding, the mission truth audit of 2026-10-08 and its fixes
  (`docs/picwise_mission_truth_audit_2026-10-08.md`). Start new work from `main`.
- **Production deployment of `148a552`: NOT VERIFIED.** The session environment blocks
  `picwise.subby.cloud` and `*.vercel.app`, and the GitHub tools do not show Vercel's
  production status. Check: `/sitemap-buying-pages.xml` must list nothing and a former
  fixture page such as `/best/power-bank-20000mah-for-iphone` must return 404 (audit D1).
- Hosting: Vercel project `subbycloud/picwise-concept`; domain `picwise.subby.cloud`.
  Entry point `api/index.py` (see `vercel.json`).

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

- every purchase-intent query: exactly 4 choices + 1 recommended, decision labels, CTA,
  direct redirect, tracking event
- no fake data of any kind; no commission-based ranking; missing data uses the enum
  (`not_connected`, `data_not_yet`, `not_applicable`, `unknown`)
- small, closed, tested steps; do not invent business logic (flag a TODO instead)
- section 9 performance: first render < 1.5 s, interactive < 2 s, click → redirect < 300 ms
- stages 23–25 stay `NEEDS_*` until real live proof exists; local fixtures are never live
  proof
- **Amazon is permanently removed** — do not reintroduce it. Awin is the affiliate network.

## Map of the code that matters now

| Area | Where |
|---|---|
| Product concept lexicon (278 kinds, EN + GR names, mega category, `broader`, preference words) | `src/picwise_nlu/product_concepts.py` |
| Understanding: phonetic keys, typo correction with safety fences, specs, product annotation (incl. accessory guard), "did you mean" | `src/picwise_nlu/concept_understanding.py` |
| Selection of the four (concept path, token path with relaxation, family guard) | `src/picwise_providers/search_selection.py` |
| Resolver | `src/picwise_search/live_search_resolver.py` |
| Page text ("Understood as", "Only some of the four match: X (n of 4)", "could not match") | `src/picwise_surface/reference.py` |
| Did-you-mean / broad-suggestion injection, impression events, query log hook | `src/picwise_app/app.py` (`api/index.py` delegates to it) |
| Awin feed loading (`AWIN_FEED_URL` with 6 h reuse, `AWIN_FEED_FILE`) | `src/picwise_providers/awin_adapter.py` |
| Query log for NLU training (inactive until configured) | `src/picwise_app/query_log_sink.py`, `deployment/supabase_query_log.sql` |

Tools:

- `python tools/nlu_misspelling_benchmark.py` — 706 misspelled queries end to end
- `python tools/check_awin_feed.py --url "<feed link>"` — what a real feed will do
- `python tools/nlu_mistake_report.py queries.txt` or `--from-query-log` — lexicon review queue
- `python tools/build_picwise_search_artifact.py` — rebuild the search artifact

Docs: `docs/picwise_misspelling_understanding.md`, `docs/awin_feed_setup_el.md` (Greek
guide for the owner), `docs/picwise_query_understanding.md`,
`docs/picwise_mission_decision_delivery.md`.

## Current numbers (local fixtures only)

- Misspelling benchmark: **96.0% pass, 0 wrong kind of product shown** (was 25.2% / 19);
  unchanged after the audit fixes.
- Test suite, last full run 2026-10-08 after the F3/F4 fixes (224 modules, every module
  except the two hour-long ones, one process per module): **1,810 tests, 2 failures,
  48 skipped** (skips need the operator's private feeds). The two failures predate all
  of this work and fail identically on `4475192` (checked in a clean worktree):
  `test_picwise_canonical_vocabulary_registry_stage2`,
  `test_picwise_search_index_generated_blind_stage4` (graph-alias leet records in the
  registry). `test_picwise_learning_stage7b` passes in about 41 min;
  `test_picwise_search_index_blind_evaluation_stage6a` runs over an hour (not run).
- Cold start through `api/index.py`, 19-row fixture: first request 677–724 ms, import plus
  first request 1,045–1,078 ms (target 1,500 ms). A real feed adds its download and parse.

## Waiting on the owner

The owner said on 2026-10-08 to make **no change yet** for items 1 and 2; they will
decide later. Do not set anything in Vercel or Supabase, and create no tables, until
they do.

1. **Awin**: create the feed link (Toolbox → Create-a-Feed), set it in Vercel as
   `AWIN_FEED_URL`, redeploy. Guide: `docs/awin_feed_setup_el.md` (now also asks for
   `ean, product_GTIN, mpn, condition, is_for_sale, pre_order, valid_from, valid_to`).
2. **Supabase project for the query log — and for click/decision events.** Click and
   impression events live only in a per-process list today (audit D5), so production
   records no click durably. None of the account's three projects is PicWise's (one
   inactive, `taxi-chat` belongs to another app, `mysubby.cloud@gmail.com`). Do not
   create tables in them without the owner saying which; a new project may cost money,
   so ask first.
3. Optional: allow `productdata.awin.com` in the cloud environment's network settings so
   a session can check the real feed.

## Next engineering steps, in order

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
- Which four are shown (owner decision, 2026-10-08, confirmed with its details and
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
