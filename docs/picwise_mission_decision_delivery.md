# PicWise Mission Decision Delivery

Closes the gap between what the concept promises for a purchase-intent query and what
the running app actually delivered on the provider-feed path.

## What was missing

Verified by running the app against a connected feed, not by reading code. With
`AWIN_FEED_FILE` set, `/search?q=laptop` already produced 4 cards, 1 recommended, short
rationale on the recommended card, a CTA and a redirect. Four contract items were still
unmet:

| # | Gap | Contract item |
|---|---|---|
| 1 | `/?q=<intent>` ignored the query and rendered the empty landing | concept: a visitor from Google must not land on an empty search page |
| 2 | Every Awin product was labelled `Geekbuying via Awin` from a hardcoded map | item 8, no fake data |
| 3 | Feed card CTAs linked the raw product URL, emitting no tracking event | item 7, tracking event payloads |
| 4 | The committed search artifact was stale, so every cold start rebuilt the index live | PROJECT_RULES section 9 |
| 5 | Outbound clicks exceeded the latency budget once a real-size feed was used | PROJECT_RULES section 9 |

## 1. Inbound query on the landing route

`root_landing_html()` hardcoded an empty query, so `/?q=laptop` returned the plain
landing. It now passes the query through and resolves it exactly as `/search` does.
With no query the landing is unchanged.

The fix is applied in both route tables: `src/picwise_app/app.py` (local server) and
`api/index.py` (the deployed WSGI entrypoint). These dispatch separately, so a route
added to one does not exist in the other.

`/demo` is deliberately left alone: it is an informational page by design, asserted as
such in `tests/test_surface_stages_10_to_15.py`.

## 2. Merchant attribution comes from the feed

`_PROVIDER_STORE_LABELS = {"awin": "Geekbuying via Awin"}` mapped a provider key to a
single shop name. A provider key names the affiliate **network**; one Awin feed carries
many merchants, so every product from every merchant was attributed to Geekbuying.

Now:

- `picwise_providers.normalization.extract_merchant_name()` reads the merchant from the
  feed row (`merchant_name`, `merchant`, `advertiser_name`, `retailer`, `store`,
  `seller`, `vendor`, …).
- `provider_product_to_backend_dict()` exports it as `merchant_name`.
- The surface renders `"<merchant> via <network>"`, or, when the row names no merchant,
  `"<network> provider feed (merchant not named in feed)"`.

An absent merchant is reported as absent. It is never replaced with a guess, because a
wrong merchant name misattributes who the buyer is paying.

## 3. Tracked outbound redirect

New route `GET /out/feed?pid=<product id>&q=<query>&src=<page>&rec=<0|1>`, mirroring the
existing `/out/amazon` pattern, in both route tables. It:

1. re-resolves the product from the provider feed by id,
2. re-checks card eligibility, so an offer that has gone out of stock, been
   discontinued or been verified unbuyable since render is **refused**, not redirected,
3. validates the target is an http(s) URL,
4. records the click, then redirects `302`.

Event names follow `docs/TRACKING_EVENTS_SPEC.md`: `recommended_click` /
`non_recommended_click`, plus `redirect_success`, or `redirect_failure` when the offer
is refused. Fields PicWise does not have are written with the missing-data enum rather
than invented values — `session_id` is `not_connected`, and `conversion_value` and
`revenue_value` are `not_applicable`. No revenue or conversion is ever recorded here.

A refused click renders a plain "this option is no longer available" page with a route
back to results. It does not fabricate a reason.

## 4. Stale search runtime artifact

The committed artifact at `src/picwise_search_memory/artifacts/search_runtime_v1.json.gz`
was being rejected at load with `source_fingerprint_mismatch`: a fingerprint source file
had changed without the artifact being rebuilt. Every process start therefore fell back
to the live index builder, and the first request paid for building 38,216 index entries.

Measured on the 19-row fixture, so feed size is not a factor: the first request cost
**8,798 ms** against a 1,500 ms target. Rebuilding the artifact with
`python tools/build_picwise_search_artifact.py` brings it to **945 ms**. On a serverless
deployment this was being paid on every cold start.

The rebuilt artifact is committed. It has the same schema and comparable size
(1,207,973 bytes); only the fingerprint and the regenerated contents differ.

## 5. Latency

Measured through the deployed WSGI entrypoint (`wsgi.py`), on the 19-row in-repo fixture
and on a generated 50,000-row gzipped feed (generated in scratch, not committed):

| Stage | Feed | Before | After | Target |
|---|---|---|---|---|
| First request after process start | fixture | 8,798 ms | **945 ms** | < 1,500 ms |
| First request after process start | 50k rows | 13,371 ms | 5,534 ms | < 1,500 ms |
| Subsequent render | fixture | 78 ms | **78 ms** | < 1,500 ms |
| Subsequent render | 50k rows | 4,997 ms | **993 ms** | < 1,500 ms |
| Click → redirect | fixture | 0.7 ms | **0.1 ms** | < 300 ms |
| Click → redirect | 50k rows | 3,241 ms | **23 ms** | < 300 ms |

Every figure meets its target except the first request on a 50,000-row feed, which still
pays the one-off feed parse and eligibility sweep. That one is called out under "Still
open" rather than claimed as met.

Three changes, all performance-only — no decision, eligibility or truth logic changed:

- **Parsed-feed cache** (`awin_adapter`), keyed on feed file identity (path, mtime,
  size). URL-configured feeds are never cached, because remote content can change with
  no local signal.
- **Resolved-pipeline cache** (`state`), same key plus mega category and whether the
  graph projection was built. The pipeline result is a pure function of those:
  purchasability-cache enrichment is applied by callers *after* the pipeline, so it is
  not part of the key and cannot go stale through it.
- **Graph projection made opt-in.** Nothing in search, selection or redirect reads it,
  yet it cost about a second per render over a real feed. The default stays `True`;
  the request path passes `False`.

A cache that served a superseded feed would be a correctness bug, not a speed win, so
`tests/test_picwise_mission_decision_delivery.py` rewrites a feed file mid-test and
asserts that a product marked out of stock stops being redirectable.

The outbound redirect deliberately avoids the full pipeline: it needs one product, so it
parses the feed, enriches with the purchasability cache and evaluates eligibility for
that product only. The feed availability context is still built over the whole feed,
because feed-wide signals decide whether availability counts as weak.

## 6. Per-choice decision labels, from facts only

`docs/PICWISE_DECISION_CONTRACT.md` requires `role_label`, `decision_label`,
`key_reasons` and `risk_or_limitation` on each of the four choices. Only the recommended
card carried a rationale; the other three showed title, price and truth meta.

The vocabulary was an open product decision, since the contract leaves the ranking
formula as TODO and PROJECT_RULES section 4 forbids inventing business logic. The
decision taken was **fact-derived labels only**: every string restates the feed's own
numbers or the verifier's own evidence. `src/picwise_providers/decision_labels.py` builds
them; it is a pure function over the selected products and never reorders them or
influences which one is recommended.

`role_label` is the product's **price rank within the four**, which is arithmetic over
the prices and gives four distinct labels rather than two repeated ones:

| Card | Label |
|---|---|
| cheapest | `Lowest price of these four` |
| second | `2nd lowest price of these four` |
| third | `3rd lowest price of these four` |
| dearest | `Highest price of these four` |

`key_reasons` states the feed price, the brand (or product type when no brand), and
whether purchase availability was verified or merely claimed by the feed.
`risk_or_limitation` states the verification position outright, so an unverified offer
says so on its own card.

There is deliberately no "best for", "great value" or "premium" wording: PicWise holds no
reviews, benchmarks or fitness data that could support such a claim, so making one would
be fake data. A test asserts that no judgement word appears in any label.

A wrong rank would put a false "lowest price" badge on the dearest product, so the
comparison is parsed rather than guessed, and these cases are covered by tests:

- `1.299,50` and `1,299.50` both mean 1299.50. Whichever separator comes last is the
  decimal separator. Reading the first convention naively yields `1.299` and inverts the
  rank.
- Equal prices across all four report `Same price as the other choices`, never
  "lowest", which would imply the others are dearer.
- Tied cheapest products both report `Lowest price of these four`.
- An unparseable price reports `Price not comparable with the others` rather than a
  guessed position.
- **Mixed currencies are never ranked against each other.** 100 USD against 90 GBP would
  produce a false "lowest price", so when the priced rows disagree on currency every card
  reports `Price not comparable with the others`.
- A negative amount is treated as malformed, not as a cheap offer.

Known limitation: the price is read from the feed's price field, and the first number in
it is used. A price field containing prose such as `was 20.00 now 15.00` would be read as
20.00. Feed price fields are numeric in practice, so this is recorded rather than
guarded against.

## Still open
- ~~**Impression events** not emitted.~~ **Done.** `page_impression`, `query_served`,
  `choices_shown` and `recommended_shown` are now recorded on every decision render, via
  `PicwiseLocalApp.record_decision_impression()`. `choices_shown` and `recommended_shown`
  read the renderer's own gate (`provider_feed_cards_will_render`) rather than the backend
  selection, so an event never claims choices were shown on a page that refused to render
  them: `tv` has a backend selection the surface withholds, and its event reports
  `choice_count=0`. A page with no query emits no `query_served`. Missing fields use the
  enum (`session_id=not_connected`, `conversion_value`/`revenue_value=not_applicable`) and
  no conversion or revenue is ever recorded.
- ~~**Product-type coverage** limited to the query-intent map.~~ **This was wrong** and is
  corrected in `docs/picwise_product_type_coverage_matrix.md`: the claim was inferred from
  a fixture that held no printers or headphones, confusing missing inventory with missing
  capability. Measured with inventory present, 26 of 27 product types across all 18 mega
  categories deliver 4+1. What remains open there: `tv` is not recognised as a synonym of
  `television` (a vocabulary-layer gap), and the manually curated Amazon path renders four
  choices with no recommendation.
- **First request on a large feed.** With the search artifact fixed, the remaining cold
  cost is the feed itself: parsing 50,000 rows plus the eligibility sweep measured
  5,534 ms against the 1,500 ms target. Subsequent renders are 993 ms. A serverless
  deployment pays the cold cost per cold start, so a real feed needs either a prebuilt
  eligible-product artifact (the same trick the search index uses) or a feed slice
  narrowed before it reaches the request path.
- **Artifact staleness has no guard.** Nothing fails when the committed artifact stops
  matching its sources; the app silently falls back to the slow path and only a log line
  says so. A check that the artifact fingerprint matches would have caught this.

## Test command

```bash
python -m unittest tests.test_picwise_mission_decision_delivery
```
