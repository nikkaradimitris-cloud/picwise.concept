# PicWise — session handoff

Current state for whoever picks the project up next. Updated 2026-10-16.
`PROGRESS.md` is the chronological log; this file is the "where are we now".

## Start here (2026-10-16)

- **New direction: price first, no ratings** (owner, 2026-10-15). Read
  `docs/picwise_price_first_plan_2026-10-15.md` before anything else. In short: only
  the kind asked for; never out of stock; cheapest first; the same product once, from
  its cheapest in-stock shop; the first four are a "Recommended" at the middle of the
  price range plus the three cheapest, with "4 of 45"; "more" again and again. The old
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
  **Next: step 2, English over greeklish ("patio").** The rest is not built: the
  engine still runs the superseded rules (price zones, specification ranking, see-more
  for `fit` only, `more_choices` capped at 4).
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
  - brand + MPN counts as the same product.

  The last three are for step 3.
- **Open owner decisions:**
  - the labels on the three cheapest cards ("Lowest price" proposed);
  - the line under Recommended ("Mid-priced for this category" proposed).

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

## Map of the code that matters now

| Area | Where |
|---|---|
| Product concept lexicon (278 kinds, EN + GR names, mega category, `broader`, preference words) | `src/picwise_nlu/product_concepts.py` |
| Understanding: phonetic keys, typo correction with safety fences, specs, product annotation (incl. accessory guard), "did you mean" | `src/picwise_nlu/concept_understanding.py` |
| Selection of the four (concept path, token path with relaxation, family guard, condition gate) | `src/picwise_providers/search_selection.py` |
| Whether the feed says a product is not new (one rule for the gate and the cards) | `src/picwise_providers/product_condition.py` |
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
- Test suite, last full run **2026-10-12** after the description rule, the spec reader
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
  `test_picwise_search_index_blind_evaluation_stage6a` runs over an hour (not run).
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
   a session can check the real feed.

## Next engineering steps, in order

0. **Price-first plan** (`docs/picwise_price_first_plan_2026-10-15.md`): the founding
   files were changed to it on 2026-10-16. Measured on the third feed, and built in
   small tested steps in the order recorded there. **Step 1, only the kind asked for,
   is done** (section "Step 1 built"; `tests/test_picwise_strict_kind_reading.py`).
   Next is step 2, English over greeklish ("patio" read as «πάτοι»), then step 3, the
   price-first engine. Step 3 also replaces the old decision step behind the empty
   pages ("3 seater sofa grey", "gas bbq with 4 burners") and makes the other words of
   a search narrow the kind ("ceiling fan with light"). The plan's "engineering,
   later" section lists what it will need: `custom_6` for tyres, a category for Living
   and Home, and a store refreshed daily.

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
  `_restrict_to_one_currency` keeps the best-ranked currency that can fill the four;
  no currency with four means no four.
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
  and is never matched against feed text. Asked for: those come first, free slots fill
  with new ones, the page says "μεταχειρισμενο (2 of 4)" (none at all: "could not
  match"), and the recommendation comes from the condition asked for. The text scan
  sits behind a substring pre-filter for speed (38 ms for 15,000 products, worst case);
  a vocabulary word added without its hint would stop being read, which
  `test_picwise_condition_request` guards.
- Which four are shown (superseded by the price-first plan of 2026-10-15, not yet
  built; what the code does today) (owner decision, 2026-10-08, confirmed with its details and
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
