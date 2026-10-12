# Where the ratings come from

Owner question (2026-10-12): whatever information the existing feed does not give --
say where we will collect **ratings** from.

Answered by research, not by preference, and the short version is uncomfortable and
useful: **no one sells aggregate product ratings to a site like PicWise.** The big
comparison sites did not buy theirs. They collected them. What *can* be licensed
cleanly is the other thing the owner's rule asks for -- the shop's reliability.

## What the owner's rule needs, and which part has a source today

The order is the owner's, from 2026-10-12: the product's rating first, then
availability, then the shop's reliability.

| Criterion | Source | State |
| --- | --- | --- |
| 1. The product's rating | no third-party API exists; four routes below | **the open problem** |
| 2. Availability | the affiliate feed itself | **already have it** -- `in_stock`, `stock_status`, `delivery_time` |
| 3. The shop's reliability | Trustpilot's public Business Units API, or Trusted Shops | **buildable now** |

So two of the three are solved or solvable immediately, and the whole difficulty sits
on the first.

## What the industry actually does, which settles the question

Idealo is the closest thing to PicWise at scale, and it says plainly that it does not
scrape prices: it takes CSV feeds and APIs from the shops themselves and matches them
to **its own product database** with fuzzy matching, AI and human quality control.
That is the architecture the owner chose on the same day -- the feed is an offer
source, the database is the product source.

And on ratings, Idealo's answer is the one that matters here: **its product reviews
are its own**, collected on its own product pages, while **merchant** ratings come from
a Trusted Shops integration. Kelkoo and PriceRunner publish nothing about licensing
review data either.

That is the market's answer. Product ratings are not a thing you buy; they are a thing
a comparison site owns. Which makes route 4 below the real long-term answer and the
first three the bridge to it.

## Route 1 -- ask the shops to fill the column they already have

The cheapest route, with no legal exposure and no scraping at all.

Awin's feed already carries `average_rating` and `rating`. Its own column reference
calls them "sometimes used" and "seldom used", and in the feed PicWise has, 127 of
11,573 rows carry one and every value is `0`. But the shops that run a review widget
-- Judge.me, Loox, Yotpo, Okendo, Reviews.io, all common on Shopify, and most of the
shops PicWise keeps are Shopify -- **already hold the number**. Putting it in the feed
is a small change on their side.

The owner is their publisher through Awin and can ask. The ask is narrow: fill
`average_rating` and the review count. For the shops worth keeping that is six or
seven messages, not a project.

- **Cost**: nothing.
- **Risk**: none. A shop says yes or no.
- **Coverage**: unknown until asked, and asking is the measurement.

## Route 2 -- read the number the shops already publish for Google

A shop that collects reviews publishes them on its product pages as schema.org
`AggregateRating` in JSON-LD, deliberately, because that is what search engines read
to show stars. Reading that is the route the owner named, and it has conditions worth
stating before anything is built:

- **Each shop's terms and robots.txt govern it, shop by shop.** Some forbid automated
  access outright. This is not decided once for all of them.
- **Volume.** Restricted to the shops PicWise keeps, that is roughly 6,500 products
  across eight domains -- a rate limit, a cache and a refresh policy, not a crawl.
- **A scraped rating carries its source and its date**, and the card says so: "4.3
  from 128 reviews at <shop>, read on <date>". Without those it is an unattributed
  claim, which `ANTI_FAKE_TRUST_RULES` forbids exactly as it forbids an invented one.
- **Two shops' ratings for two different products are not directly comparable.**
  Different audiences, different sample sizes, different prompts. A minimum review
  count, and the rule for a four where one product has no rating, are decisions the
  owner has to take before any ranking uses them.

**Measuring whether the shops publish it at all is the cheapest next step** -- about
twenty pages per shop -- and it is blocked: this environment's network policy denies
the merchant hosts, so the measurement cannot run here yet. The hosts are listed in
`docs/picwise_rating_source_plan.md`.

## Route 3 -- pay someone else to read it

Scraper-as-a-service exists for exactly these widgets: ready-made actors for Judge.me,
Loox, Yotpo, Stamped, Okendo and Reviews.io, which take a shop domain or a product
handle and return each review with its rating, and some of which detect the widget and
return a weighted average and a count.

What this buys is time, not permission. The work moves off PicWise; the shop's terms
still apply, and the data still has to be attributed and dated. Worth it only if route
2's measurement shows the ratings are there and the reading is more work than it looks.

- **Cost**: per run, per shop.
- **Risk**: the same as route 2, with a supplier in the middle.

## Route 4 -- PicWise collects its own, which is what the comparison sites did

Every product page PicWise publishes can ask the buyer who clicked through whether the
product was good. That is slow, it needs traffic PicWise does not have yet, and it is
the only route that ends with PicWise owning the signal its whole decision rests on,
with no shop's terms and no supplier in the way. It is also what Idealo did.

Worth starting early precisely because it is slow: the click events already exist in
the tracking contract, and a rating asked after a click is the one review nobody can
revoke. It needs the durable store the project has been putting off -- the Supabase
decision the owner has twice deferred -- because a rating in a per-process list is
lost on the next deploy.

## What is a dead end, so nobody spends a week on it

- **Feefo, Reviews.io and the other review platforms' APIs are merchant-scoped.** They
  answer for the account that collected the reviews. Feefo's product ratings endpoint
  takes a SKU within a Feefo hub account; it is not a public lookup, and a publisher
  cannot query another shop's products. Unless a shop grants its own access, this is
  closed.
- **No GTIN-to-rating API.** The GTIN lookup services return product attributes. The
  two that return reviews resolve a barcode into a marketplace item -- eBay or Amazon
  -- with licensing limits on storing and redistributing them, and Amazon is already
  out of PicWise's decision path by `docs/picwise_amazon_removed_from_decision_path.md`.
- **Google's product review data is not readable.** The reviews feed goes *into*
  Merchant Center from the merchant; there is no public read.
- **Icecat carries editorial content and awards, not user ratings.** It is the right
  answer for specifications and the wrong one for this.

## The shop's reliability belongs to the shop, not to the feed

Owner point, raised on reading the above: Trustpilot rates the shop -- but that shop
is on Awin today and on whatever network PicWise works with next.

So the reliability of a shop is stored against the shop's own **domain**, never
against a feed row or a network's name for a merchant. `picwise_providers.merchant_identity`
reads it, and three things follow:

- **Trustpilot's public Business Units API is itself keyed by domain**, so the key
  PicWise stores is the key the lookup already needs. Nothing is translated.
- **A shop joined through two networks is one shop.** It is rated once, and a second
  network's feed inherits every reliability fact already collected rather than
  starting the shop again from nothing.
- **Two storefronts of one brand stay apart.** `ie.plusshop.com` and `uk.plusshop.com`
  are two shops with two reputations; the merchant name alone would have merged them.

The domain is read from the merchant's own link and never from the network's redirect:
every row of the Awin feed carries an `aw_deep_link` on `awin1.com`, which names the
network. A row that carries only a redirect does not identify a shop, and PicWise says
so rather than hanging a rating on a shop it cannot name. On the real feed all 11,573
rows resolve, to 26 shop domains.

## Recommended order

1. **Trustpilot's public Business Units API for the shop's reliability** (criterion 3).
   It returns a trust score and review count per domain for an API key, and PicWise has
   26 merchant domains from the feed. This is the one piece that is clean, cheap and
   needs nobody's permission.
2. **Ask the kept shops to fill `average_rating`** (route 1). Six or seven messages,
   no exposure, and the answer is itself the measurement.
3. **Measure whether their pages publish `AggregateRating`** (route 2), which needs
   the environment's network policy opened first. If they do, read it with source and
   date, under a per-shop terms check.
4. **Start collecting PicWise's own ratings** (route 4) as soon as there is traffic,
   because it is the only one that ends.

Specifications are a separate and easier question, answered in
`docs/picwise_rating_source_plan.md`: Icecat, free, keyed by the GTIN on 59% of the
feed's rows and the brand-plus-part-code on 63%.
