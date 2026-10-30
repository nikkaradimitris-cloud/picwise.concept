# PicWise on its own server: architecture blueprint

Written on 2026-10-23 at the owner's request, which was sent in English: the database and
search engine for 0.8-1M products, the URL and international routing, the store
validation bot, and text generated from the feed's data. **Nothing in it is built.** Each
part is built in small steps, each told to the owner first, and reaches `main` only on the
owner's yes.

It builds on `docs/PICWISE_GOOGLE_PAGES_SPEC.md`, which decides which pages exist, which
ones Google may see, and the server catalogue's rule of live products only. Facts about
Google, Cloudflare and the hosting providers were read through web search on 2026-10-23,
because the providers' own pages cannot be opened from the session. They are to be
checked again at the source before each part is built.

## Σύνοψη για τον ιδιοκτήτη

- **Βάση δεδομένων:** μόνο PostgreSQL. Ούτε Meilisearch ούτε Redis: η αναζήτησή μας
  ψάχνει «είδος + φθηνότερο πρώτα», και αυτό η PostgreSQL το κάνει σε χιλιοστά του
  δευτερολέπτου με τα σωστά ευρετήρια. Ένα δεύτερο σύστημα θα έτρωγε μνήμη και θα έπρεπε
  να συγχρονίζεται κάθε βράδυ.
- **Ταχύτητα κάτω από 100 ms:** επιτυγχάνεται για τις σελίδες που βλέπει η Google, γιατί
  φτιάχνονται μία φορά τη νύχτα και τις σερβίρει το Cloudflare από κοντά στον
  επισκέπτη. Ο στόχος της Google για το «γρήγορο» είναι το κύριο περιεχόμενο σε 2,5
  δευτερόλεπτα, και εκεί μετράνε κυρίως οι φωτογραφίες των καταστημάτων.
- **Διευθύνσεις:** ένα domain, με φάκελο ανά αγορά (`/uk/`, `/us/`) και σήμανση
  `hreflang` μεταξύ τους. Καμία αυτόματη ανακατεύθυνση με βάση τη χώρα του επισκέπτη: η
  Google το αποθαρρύνει.
- **Bot ελέγχου:** επισκέπτεται μόνο τη σελίδα του ίδιου του καταστήματος, ποτέ τον
  σύνδεσμο affiliate (αλλιώς θα μετρούσε ψεύτικα κλικ). Τηρεί το robots.txt, πηγαίνει
  αργά και γράφει σε δικούς του πίνακες, ώστε να μη μπλοκάρει το site.
- **Όριο του bot:** 200 τυχαίοι έλεγχοι μετράνε πόσο αξιόπιστο είναι ένα κατάστημα, αλλά
  δεν καθαρίζουν όλα τα «φαντάσματα». Γι' αυτό ελέγχει και τα προϊόντα που βλέπει πρώτα ο
  κόσμος.
- **Κείμενα:** κάθε πρόταση λέει ένα πραγματικό στοιχείο που υπολόγισε η σελίδα. Όπου
  λείπει στοιχείο, δεν μπαίνει πρόταση. Κείμενο που απλώς ξαναγράφει το ίδιο με άλλες
  λέξεις η Google το θεωρεί spam.
- **Διορθώσεις στην αρχική περιγραφή:**
  - η Hetzner ΗΠΑ ακρίβυνε περίπου 3 φορές και τα φθηνά πακέτα της δεν πωλούνται·
  - για 1 εκατομμύριο προϊόντα και το bot χρειάζονται τουλάχιστον 16 GB μνήμη·
  - στις 22/10 είχες πει 80 ελέγχους ανά κατάστημα, τώρα 200: είναι μία ρύθμιση και
    αλλάζει με μία λέξη.

## 0. Corrections to the brief, read first

- **Hetzner US East.** On 15 June 2026 Hetzner raised CPX prices, with CPX31 in the USA
  going from €20.99 to €62.49 a month. Since September its cost-optimised CX and CAX
  plans are reported unavailable to new orders. So it is no longer the cheap option. The
  candidates put to the owner the same day were OVHcloud's VPS range (for this scope
  VPS-4: 8 vCores,
  24 GB, 200 GB NVMe, unlimited traffic, daily backup, about $23 a month; OVHcloud also
  sells in the US, locations to be checked on the order page) and DigitalOcean. With pages cached at Cloudflare's edge
  (section 1.6), the origin's location matters only for cache misses and the site's own
  search, so Europe and US East both work.
- **Size.** 0.8-1M products, the bot and two markets need **16 GB of memory at least**
  (section 1.7). 8 GB was enough only for the smaller catalogue put to the owner before.
- **"< 100 ms".** It is reachable as time to first byte for pages served from
  Cloudflare's cache, since those pages are rendered once a night. A page built on
  request takes the server about 50-150 ms (to be measured). Google's Core Web Vitals
  target is different: the main content (LCP) within 2.5 s on phones at the 75th
  percentile, where the shops' images weigh most.
- **"100% data integrity" from 200 random checks per merchant.** A random sample
  *measures* a shop's ghost rate; it does not *find* every ghost. The bot therefore splits
  its checks between products people actually see (the four cards of indexed pages) and a
  random sample, and the catalogue already drops what the feed says is out of stock
  (section 3.1).
- **A page per long-tail keyword.** Google's guide of May 2026 says separate content for
  every variation of how people search, made primarily to rank, violates its scaled
  content abuse policy. The long tail comes from many products and real facets, one page
  each (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 1).
- **"Each product page features 4 comparison cards."** Kept, read as follows:
  - a product's own page shows its offers (every shop's price, or one shop's);
  - its **4 cards are the alternatives of its kind**: the Recommended and the 3
    cheapest. That is the comparison Google counts as value, above all for a product only
    one shop sells.
- **Checks per merchant.** The owner's note of 22/10 says 80, this brief says 200. It is
  a setting (section 3.9).
- **Domain.** `picwise.subby.cloud` is a sub-domain of another business. A domain of
  PicWise's own (one `.com` holding `/uk/` and `/us/`) is best taken **before** Google
  indexes any page, because a later move costs ranking for a time.

## 1. Database and search

### 1.1 Recommendation: PostgreSQL, and nothing else for now

A PicWise search is not free-text relevance. The query is understood by PicWise's own code
as a kind ("power bank") with filter words ("20000mah", "grey"), and the answer is the live
products of that kind carrying those words, cheapest first, each product once
(`search_selection.py`). That is an indexed, ordered lookup, which PostgreSQL answers in
milliseconds for millions of rows.

**Why not Meilisearch now:**

- its strength, typo-tolerant relevance ranking, is not how PicWise orders an answer:
  PicWise orders by price, and its own understanding already corrects typos (93.8% on the
  misspelling benchmark, 0 wrong kinds);
- it keeps a second index of the whole catalogue, several GB for 1M products with
  descriptions, memory-mapped and in competition with PostgreSQL for the same RAM;
- it must be kept in step with the database every night, and a missed sync would show
  products that are gone.

**Why not Redis now:**

- the pages Google sees are cached at Cloudflare's edge, which is the cache that counts;
- a small in-process cache per worker covers the site's own search;
- Redis would be one more service to run and to keep within memory, for no gain on one
  server.

**When to add them:**

- Meilisearch, if a free-text search over titles (model numbers, "as you type" over
  products, not kinds) is ever wanted;
- Redis, if a second web server is added and the workers need a shared cache.

### 1.2 What stays as it is

PicWise's understanding of a query (`src/picwise_nlu`), its reading of a product's kind
(`annotate_product_concepts`), its gates (availability, price, condition) and its
price-first rules (`search_selection.py`) are the product. They move to the server
unchanged. Only where the catalogue lives changes: rows in PostgreSQL instead of a file
loaded whole into memory.

The move is measured the way every change has been:

- the 118 searches of `tools/price_first_eval.py` before and after;
- the kinds of every product;
- the full test run;
- the misspelling benchmark.

### 1.3 Schema (sketch)

```sql
-- One row per shop and market. A shop in several networks is one shop, known by its
-- domain (owner, 22/10).
CREATE TABLE merchant (
  id              bigserial PRIMARY KEY,
  market          text    NOT NULL CHECK (market IN ('uk', 'us')),
  network_id      text    NOT NULL,              -- Awin advertiser id
  name            text    NOT NULL,
  domain          text,
  feed_rows_last  integer,                       -- rows read on the last good night
  feed_ok_on      date,
  reliability     real,                          -- section 3.6
  reliability_n   integer,
  UNIQUE (market, network_id)
);

-- One row per offer: a feed row that passed the gates.
CREATE TABLE offer (
  id            bigserial PRIMARY KEY,
  market        text    NOT NULL,
  merchant_id   bigint  NOT NULL REFERENCES merchant,
  feed_id       text    NOT NULL,                -- the feed's own id
  product_id    bigint  NOT NULL,                -- section 1.4: same GTIN, or brand+MPN
  title         text    NOT NULL,
  price         numeric(12,2) NOT NULL CHECK (price > 0),
  currency      char(3) NOT NULL,
  shop_url      text    NOT NULL,                -- the shop's own page: the bot visits it
  tracked_url   text    NOT NULL,                -- aw_deep_link: only /out/ sends to it
  image_url     text    NOT NULL,
  non_new       text    NOT NULL DEFAULT '',
  search_text   text    NOT NULL,                -- as _product_search_fields builds it
  raw           jsonb   NOT NULL,                -- every column the feed sent (owner, 23/10)
  state         text    NOT NULL DEFAULT 'live', -- live | unavailable | hidden_by_check
  first_seen    date    NOT NULL,
  last_seen     date    NOT NULL,
  gone_since    date,                            -- deleted 30 days after (owner, 23/10)
  checked_at    timestamptz,
  check_verdict text,                            -- section 3.5
  UNIQUE (merchant_id, feed_id)
);

-- The kinds an offer was read as, one row each, so "kind X, cheapest first" is an
-- ordered index scan. Rows exist only for offers that are the kind (not an accessory
-- of it, not doubtful).
CREATE TABLE offer_kind (
  market    text          NOT NULL,
  kind      text          NOT NULL,
  price     numeric(12,2) NOT NULL,
  offer_id  bigint        NOT NULL REFERENCES offer ON DELETE CASCADE,
  PRIMARY KEY (market, kind, price, offer_id)
);

-- The pages: kind, facet, category, product; recomputed each night.
CREATE TABLE page (
  id           bigserial PRIMARY KEY,
  market       text    NOT NULL,
  path         text    NOT NULL UNIQUE,          -- /uk/power-banks/20000mah/
  page_type    text    NOT NULL,                 -- category | kind | facet | product
  kind         text,
  filters      text[]  NOT NULL DEFAULT '{}',
  offer_ids    bigint[] NOT NULL,                -- in price order
  total        integer NOT NULL,                 -- "4 of 45"
  recommended  bigint,
  facts        jsonb   NOT NULL,                 -- min, max, median, shops, specs (section 4)
  indexable    boolean NOT NULL,                 -- the gate of the spec, section 2
  gate_reasons text[]  NOT NULL DEFAULT '{}',
  content_hash text    NOT NULL,                 -- lastmod moves only when this does
  lastmod      date    NOT NULL,
  gone_since   date                              -- 410 after 30 days
);

-- The AI text of a one-shop product page (owner, 23/10), written once and again only
-- when its facts change; never published before the checks of section 4.4.
CREATE TABLE product_text (
  product_id   bigint PRIMARY KEY,
  market       text   NOT NULL,
  facts_hash   text   NOT NULL,
  body         text   NOT NULL,
  checked      boolean NOT NULL,
  written_at   timestamptz NOT NULL
);

-- The bot's own tables (section 3): append-only, so they never lock what the site reads.
CREATE TABLE validation_check (
  id            bigserial PRIMARY KEY,
  checked_at    timestamptz NOT NULL,
  merchant_id   bigint NOT NULL,
  offer_id      bigint,
  sample        text   NOT NULL,                 -- seen | random
  http_status   integer,
  feed_price    numeric(12,2),
  page_price    numeric(12,2),
  page_avail    text,                            -- as the page states it
  verdict       text   NOT NULL,                 -- section 3.5
  detail        text
);
CREATE INDEX ON validation_check (merchant_id, checked_at);
```

Indexes and settings that carry the speed:

- `offer_kind`'s primary key, `(market, kind, price, offer_id)`, is the "cheapest first" index;
- `CREATE INDEX ON offer (product_id) WHERE state = 'live'` gives a product's offers;
- `CREATE INDEX ON offer USING gin (search_text gin_trgm_ops)` lets SQL apply filter words
  (`pg_trgm`) once a kind is too large to filter in Python;
- `default_toast_compression = lz4` keeps the descriptions in `raw` compressed on disk.

### 1.4 The nightly load: live products only, shop by shop

This implements the owner's requirement of 23/10 and its 30 days. Each night, per market:

1. **Download and read.** The feed is downloaded and read row by row; the file itself is
   not kept. Rows are grouped by merchant, and each row goes through the existing rules
   (normalise, gates, kinds, condition, search fields).
2. **Stage.** A merchant's rows go to an unlogged staging table with `COPY`.
3. **Safety check.** If a merchant's feed failed, or came with fewer than half the rows
   of its last good night (the share is the owner's to set), that merchant is left as it
   was and an alert is raised. A broken feed never empties the catalogue.
4. **Upsert, in one short transaction per merchant.**
   - `INSERT ... ON CONFLICT (merchant_id, feed_id) DO UPDATE` sets `last_seen` to today
     and refreshes price, data and state.
   - Offers of that merchant not seen tonight turn `unavailable` with `gone_since`, and
     their `offer_kind` rows are removed.
   - An offer that comes back within 30 days keeps its row, its page and its text.
5. **Delete.** Offers gone for more than 30 days are deleted. Their pages answer 410 and
   leave the sitemaps.
6. **Pages, sitemaps and cache.** Pages are recomputed, each page's `content_hash`
   compared, sitemaps rewritten. Cloudflare's cache is then purged only for the pages
   that changed.

Each transaction is short and PostgreSQL never makes readers wait for writers (MVCC), so
the site answers throughout the load. After the load, `VACUUM (ANALYZE)` runs on the
touched tables.

**Product identity:** the same GTIN with a valid check digit, else the same brand and MPN
(`_product_identity_key`). It gives one product page however many shops sell the item.

### 1.5 One query, step by step

The site's own search, `/uk/search?q=power+bank+20000mah`:

1. PicWise's code reads the query: kind `power_bank`, filter `20000mah`, no condition
   asked. This needs no database: it runs in memory, as today.
2. `SELECT offer_id FROM offer_kind WHERE market='uk' AND kind='power_bank' ORDER BY
   price` is an index-only scan. Applied to the offers' `search_text`, the filter words
   leave the answer.
3. The existing price-first rules count the answer ("4 of 45"), keep each product once,
   pick the Recommended (the middle price, with a GTIN, extreme top prices left out) and
   the 3 cheapest.
4. Only the cards shown are read in full from `offer`.

For a kind of a few thousand offers this is expected to take a few tens of milliseconds;
it is to be measured on the real catalogue. A facet page does the same work once a
night, and its answer is stored in `page`.

### 1.6 Speed: pages rendered once a night and served by Cloudflare

- **Rendering.** Category, kind, facet and product pages change only when the catalogue
  does: once a night, or when the bot hides an offer. They are rendered after the load
  and served with `Cache-Control: public, s-maxage=86400` and a `Cache-Tag` per page,
  merchant and kind.
- **Cloudflare.** A Cache Rule caches HTML for those paths. Since April 2025 every
  Cloudflare plan, the free one included, can purge by tag, prefix, URL or host; on the
  free plan the limit is 5 purge requests a minute, each with up to 100 items. So the
  nightly load purges the tags of what changed, and the bot purges a page when it hides
  one of its offers.
- **Never cached:**
  - `/out/` (the redirect to the shop: `Cache-Control: no-store`; it records the click,
    then 302 to Awin's tracked link, so Awin's cookie is set as today);
  - the site's own search;
  - anything with a query string other than numbered pages.
- **No cookies, no personalisation** on these pages. Every visitor of a market gets the
  same page, which is what makes them cacheable.
- **Images.** They come from the shops' servers and decide the LCP. Measure first; if they
  are slow, serving them through the site's own domain lets Cloudflare cache them without
  storing them on disk (subject to Awin's and the shops' terms on images).
- **Measurement.** Core Web Vitals from real visitors (Search Console, Chrome UX Report)
  and PageSpeed Insights on a page of each type.

### 1.7 Memory and disk

| | 16 GB server (recommended) | 8 GB (not enough for 1M with the bot) |
|---|---|---|
| PostgreSQL `shared_buffers` | 4 GB | 2 GB |
| `effective_cache_size` | 10 GB | 5 GB |
| `work_mem` / `maintenance_work_mem` | 32 MB / 1 GB | 16 MB / 512 MB |
| Web workers (Gunicorn, PicWise's understanding in each) | 4 × about 300-400 MB | 2 × about 300-400 MB |
| Nightly load (streams the feed) | about 1-2 GB at its peak | the same, tight |
| Bot (async fetches; at most 2 headless browsers) | about 1-2 GB | too tight next to the load |

Every figure is an estimate, to be measured on the server. Further settings:

- `random_page_cost = 1.1` (NVMe disk);
- `max_connections = 50`;
- autovacuum left on, with `autovacuum_vacuum_scale_factor = 0.05` on `offer`.

**Disk:** 1M offers with every column compressed, the derived columns and indexes come
to about 4-8 GB. AI texts add about 1.5 KB each. The bot's checks add about 3 GB a year,
and checks older than 90 days are deleted. **100-200 GB is ample.**

### 1.8 Backups and the rest of the server

**Backups:**

- The catalogue is rebuilt every night from the feeds, so it needs no backup to survive.
- What cannot be rebuilt does: the AI texts, the bot's history, the click and decision
  events, and the shops' scores. These are dumped every night (`pg_dump` of those tables)
  to storage off the server.
- The provider's daily backup covers the rest.

**The rest of the server:**

- Ubuntu 24.04 LTS with automatic security updates.
- Caddy for HTTPS, behind Cloudflare in "Full (strict)" mode.
- The firewall lets the web in only on 80/443, and the database listens on the server
  alone.
- Secrets (the feed links, the keys) live in root-only environment files that a GitHub
  workflow writes from GitHub's secrets. They are never in the repository or the chat.
- Deploys and changes go through GitHub workflows, because the session reaches the
  internet only over HTTPS on port 443 and so cannot open SSH itself.

## 2. URLs and international routing

### 2.1 One domain, one folder per market

| Page | UK | US |
|---|---|---|
| Market home | `/uk/` | `/us/` |
| Category | `/uk/electronics/` | `/us/electronics/` |
| Kind | `/uk/power-banks/` | `/us/power-banks/` |
| Facet (keyword page) | `/uk/power-banks/20000mah/` | `/us/power-banks/20000mah/` |
| Product | `/uk/p/anker-powercore-20000-k3f9x2/` | `/us/p/anker-powercore-20000-k3f9x2/` |
| The site's own search | `/uk/search?q=...` (`noindex`) | `/us/search?q=...` (`noindex`) |
| Root | `/`: a chooser of market, `x-default` | |

**Rules for the addresses:**

- lowercase, hyphens, no trailing parameters;
- the last part of a product's address is a short code derived from its identity (GTIN,
  else brand and MPN), so the address stays the same night after night, and while the
  product is away for less than 30 days.

**Rules for the names:**

- slugs come from the kind's English name in PicWise's lexicon;
- the words follow the market, US spelling on `/us/` and UK spelling on `/uk/`
  ("color" and "colour"), as do units where shops differ.

### 2.2 `hreflang`

- **When a pair exists:** a UK page and a US page are alternates only when they are the
  same thing. That means the same kind or facet with a page passing the gate in both
  markets, or the same product (same GTIN) sold in both.
- **When it does not:** a page with no counterpart carries no `hreflang`.
- **Markup:** `<link rel="alternate" hreflang="en-GB" ...>`, `hreflang="en-US"`, each page
  naming itself and the other, both ways. An `x-default` points to the root chooser on
  the market homes.
- **One method only:** these HTML tags, not the sitemaps as well.

### 2.3 No redirects by country

Google warns that Googlebot mostly crawls from US addresses and sends no
`Accept-Language`, so pages adapted or redirected by the visitor's country may leave a
market uncrawled. Its advice is separate addresses, `hreflang`, and a banner that lets a
visitor choose: "You are viewing UK prices. See US prices". The banner is drawn in the
browser, so the cached page stays the same for everyone.

### 2.4 Currency and catalogue per market

- Each market has its own feeds, shops and catalogue: `/uk/` only GBP offers, `/us/`
  only USD offers.
- Prices are never converted. One currency per answer is already the rule.
- An offer in another currency than its market's is held back at the gate and counted in
  the build's note, as the zero prices are today.

### 2.5 Canonicals, numbered pages, parameters, sitemaps, `robots.txt`

- **Canonicals:** every indexable page names itself as canonical.
- **Numbered pages:** `?page=2` is its own address, canonical to itself, linked in
  sequence. It is crawlable, so every product page can be reached.
- **Sort and filter parameters** exist only on the site's own search, which carries
  `noindex`. Facets are paths chosen by the gate of the spec, never combinations made
  on request.
- **Sitemaps:** one sitemap index per market, split by page type, at most 50,000
  addresses each. `lastmod` moves only when `content_hash` does.
- **`robots.txt`:**
  - keeps crawlers off `/out/` and the routes that act when called (live since 23/10);
  - adds `Disallow` for the search only once Google has dropped those pages;
  - names the sitemap indexes.

### 2.6 Cloudflare

**Rules:**

- Cache everything on `/uk/*` and `/us/*` except `*/search*`.
- Bypass the cache on `/out/*`, on `/cron/*` and on the status routes.
- Always HTTPS.
- Bot Fight Mode **off** for the site's own pages, so no crawler is challenged by
  mistake; Cloudflare lets verified crawlers such as Googlebot through anyway.

**The cache key:** the default, by path. Caching must not vary by the visitor's country,
since pages do not.

## 3. The store validation bot

### 3.1 What it can and cannot prove

| | |
|---|---|
| **What it checks** | Whether a shop's own product page agrees with its feed: in stock, at that price. |
| **Random sample per shop** | Gives the shop's **reliability**: the share of its listings that are true. |
| **Products people see** | Checking the four cards of indexed pages catches the **ghosts that matter**. |
| **What it cannot do** | Prove 100% of a million listings true. |
| **What does the rest** | The catalogue already drops what the feed says is out of stock or has no price. |

### 3.2 Sampling

For each merchant, each night, `per_merchant` checks (200 in this brief; 80 in the
owner's note of 22/10):

- **half from the products people see:** offers on the four cards of indexed pages,
  the ones checked longest ago first;
- **half uniform random** over the merchant's live offers, for an unbiased reliability
  score.

An offer found false is checked again 3 days later.

### 3.3 Fetching politely

- **Only the shop's own page** (`link` in the Google format). **Never** `aw_deep_link` or
  any tracked address: that would count as a click in Awin and on the shop's statistics.
- **`robots.txt` respected**, read once a day per host. It is parsed with Protego, which
  understands the `*` and `$` patterns. A disallowed page is not fetched and is counted
  as `not_allowed`.
- **An honest name:** `PicWiseBot/1.0 (+https://<domain>/bot)`, a page that says what it
  does and how a shop asks to be left out.
- **A gentle pace:**
  - one request at a time per shop, at least 8 seconds apart, or the shop's
    `Crawl-delay` if longer;
  - many shops in parallel;
  - in a set window of night hours (owner, 18/10).
- **Blocked means blocked:** a 403, a 429, a challenge page or a CAPTCHA is recorded as
  `blocked` and counts neither for nor against the shop. The bot never tries to get
  around a block: no rotating addresses, no disguised browsers, no CAPTCHA solving. A
  shop that blocks it is reported to the owner.

### 3.4 Reading a page, cheapest method first

1. **HTML only.** First the page's JSON-LD `Product` and `Offer` (`availability`, `price`,
   `priceCurrency`), which most shops publish for Google. Then microdata, then the
   `product:availability` and `og:price` meta tags.
2. **A headless browser,** at most 2 at a time, only when the HTML states none of these.
3. **Unreadable.** A page that states nothing readable is `unknown`. No guessing from
   page text such as "Add to basket".

### 3.5 Verdicts

| Verdict | When | What it changes |
|---|---|---|
| `ok` | in stock, price within 1% (or 1 penny) of the feed | `checked_at` |
| `ghost` | the page says out of stock, discontinued or pre-order | offer `hidden_by_check` at once; its pages re-rendered and purged |
| `price_mismatch` | in stock, another price | offer hidden until the feed agrees (to be decided by the owner) |
| `gone` | 404 or 410, or a redirect to a home or category page | as `ghost` |
| `blocked`, `not_allowed`, `unknown` | as above | nothing; reported |

### 3.6 Reliability score

**How it is computed:**

- For each merchant: the Wilson lower bound (95%) of the share of `ok` among the decided
  verdicts of the last 14 days.
- Decided means `ok`, `ghost`, `price_mismatch` and `gone`.
- It is stored with its count.
- A shop with few decided checks has a low bound until the evidence grows, so a shop is
  never judged on a handful of pages.

**What a score does is the owner's to decide** (PROJECT_RULES: no business logic
invented). Until then it is reported, not acted on: a morning list of shops by score, with
their ghosts and blocks.

### 3.7 Not locking the database

- The bot writes only its own `validation_check` rows (append-only, in batches of 100)
  and two columns of the offers it checked, one short transaction at a time.
- PostgreSQL readers never wait for writers. The bot's connection sets
  `lock_timeout = '2s'` and retries later rather than wait behind the nightly load.
- It runs after the load, never during it. If the load overruns, the bot waits for its
  lock file.
- It runs under its own database role (it can write only its tables and those two
  columns) and its own system user. Its resources are capped (below), so it can never
  starve the web server.

### 3.8 Scheduling: a systemd timer (or cron)

```ini
# /etc/systemd/system/picwise-validate.service
[Unit]
Description=PicWise store validation bot
After=network-online.target postgresql.service picwise-load.service
Wants=network-online.target

[Service]
Type=oneshot
User=picwise-bot
WorkingDirectory=/srv/picwise/app
EnvironmentFile=/etc/picwise/bot.env
ExecStart=/srv/picwise/venv/bin/python -m picwise_bot.run --config /etc/picwise/bot.toml
Nice=10
IOSchedulingClass=idle
CPUWeight=20
MemoryMax=2G
TimeoutStartSec=6h

# /etc/systemd/system/picwise-validate.timer
[Unit]
Description=Run the PicWise store validation bot each night

[Timer]
OnCalendar=*-*-* 03:30:00 Europe/London
RandomizedDelaySec=10m
Persistent=true

[Install]
WantedBy=timers.target
```

The cron equivalent, if cron is preferred, as a line of `/etc/cron.d/picwise` (with the
user field), with a lock so two runs never overlap:

```cron
30 3 * * * picwise-bot flock -n /run/picwise/bot.lock nice -n 10 ionice -c3 /srv/picwise/venv/bin/python -m picwise_bot.run --config /etc/picwise/bot.toml >> /var/log/picwise/bot.log 2>&1
```

A timer is the better choice:

- its runs are logged;
- it never overlaps itself;
- it catches up after a reboot;
- it caps memory and CPU.

### 3.9 Configuration

```toml
# /etc/picwise/bot.toml
[sample]
per_merchant = 200             # 80 in the owner's note of 22/10
share_seen = 0.5               # from the four cards of indexed pages
recheck_false_after_days = 3

[fetch]
user_agent = "PicWiseBot/1.0 (+https://<domain>/bot)"
url_field = "link"             # the shop's own page, never aw_deep_link
per_host_concurrency = 1
min_delay_seconds = 8          # or the shop's Crawl-delay, if longer
hosts_in_parallel = 40
timeout_seconds = 20
retries = 1
window = "03:30-08:00"         # the market's local time
respect_robots = true
robots_cache_hours = 24

[read]
headless = "fallback"          # only when the HTML states nothing
max_headless = 2
price_tolerance = 0.01         # 1%, or one penny or cent

[score]
window_days = 14
confidence = 0.95
```

### 3.10 Capacity

- **One shop:** 200 checks at one per 8 seconds take about 27 minutes.
- **One night:** with 40 shops in parallel and a 4.5-hour window, that is about 400 shops
  and 80,000 checks, about 12 GB of pages at about 150 KB each.
- **More shops:** with more than 400 shops, each is checked every second night, or the
  number of shops in parallel goes up (it is the shops' pace that limits, not the
  server).

## 4. Text from the data

### 4.1 Rules

Google judges text by the value it adds, not by how it was made. Its scaled content abuse
policy names pages generated from feeds with little value, and feeds reworded "through
automated transformations like synonymizing". So:

1. **Every sentence carries a fact the page computed:** a count, a price, a share, a
   property, a shop.
2. **A sentence is rendered only when all its facts exist** and pass their thresholds;
   otherwise nothing. No filler.
3. **No synonym rotation, no spinning.** Two pages differ because their data differ.
4. **Only what the feed states, as PicWise reads it.** No adjectives of quality ("best",
   "premium"), no claim of testing, rating or review.
5. **A shop's description is never copied as the page's text.** It is the material facts
   are read from (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`).
6. **Market language:** UK or US spelling, and units as the shops of the market write
   them.

Each template below is a sentence with its condition. `{…}` is a computed value.

### 4.2 Facet and kind pages

| Text | Shown when |
|---|---|
| H1: "{Facet name} {kind plural}" (for example "20000mAh power banks") | always |
| "{count} in stock at {shops} UK shops today, from {min_price} to {max_price}." | count ≥ 4 |
| "Half cost less than {median_price}." | count ≥ 8 |
| "{n_brands} brands; the most listed is {top_brand} ({top_brand_count})." | n_brands ≥ 3 |
| "The cheapest, {cheapest_title}, is {cheapest_price} at {shop}." | always |
| "Recommended: {title}, the middle price of the {count}, with a barcode, so it is the same item wherever it is sold." | a Recommended exists |
| Comparison of the four: one row per property stated by at least two of them (capacity, output, weight, dimensions, material, colour) | a property stated by 2 or more |
| "{n} of the four state a {property}; the highest is {value} ({title})." | the property ranks (storage, battery, playtime) |
| "Prices as listed by the shops on {date}." | always |

### 4.3 The product page of a product two shops or more sell

| Text | Shown when |
|---|---|
| H1: the product's name as its shops write it (the most common title among its offers) | always |
| "Sold by {n} shops, from {min_price} to {max_price}." | n ≥ 2 |
| "The cheapest is {shop} at {price}, {diff} less than the dearest." | n ≥ 2 |
| "With delivery: from {min_total} ({shop})." | the feed states delivery for at least two shops |
| The facts table: every property the feed states (size, colour, material, dimensions, weight, energy class, product details) | at least one property |
| "Compared with {count} {kind plural}: cheaper than {pct}%." | count ≥ 20 |
| The 4 cards of its kind (Recommended and 3 cheapest), headed "Other {kind plural}" | always |

### 4.4 The product page of a product one shop sells: the AI text

The owner's decision of 23/10 and its conditions (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`,
section 5).

**The model's input** is a structured record, never the shop's description alone:

- the product's facts (the columns it states, specs read from its description);
- its price position among its kind ("cheaper than 72% of 340 power banks");
- its kind's what-to-check list;
- 3 similar products in stock, with their facts.

**The model is asked for** 80-150 words that help a buyer decide between this product
and those similar ones, using only those facts.

**Checked by code before publication:**

- every number with its unit, every brand and every model name in the text must be in
  the record;
- no word of quality or testing (a list of forbidden words);
- no run of more than 8 words in a row taken from the shop's description;
- a text that fails is not published, and the page stays out of Google (gate of the
  spec).

**The page says how the text was made:** "Written with AI from the shop's data, and
checked against it."

**The kind's what-to-check list** is written once per kind and reviewed before use (for
example, power banks: the capacity against the phone's battery, the output in watts,
airlines' 100 Wh limit for carry-on). It is short, so the page's own facts stay the main
content.

### 4.5 A product that is unavailable for now (up to 30 days)

- "{shop} listed this product as unavailable on {date}." when the feed still lists it as
  out of stock. If the feed no longer lists it: "{shop} no longer lists this product
  (since {date})."
- Then the 4 cards of its kind, headed "In stock now".
- No price in the structured data (section 6 of the spec), and no button to the shop.

### 4.6 Titles and headings

- **`<title>`:**
  - a facet or kind page: "{H1}: {count} in stock from {min_price} | PicWise UK";
  - a product page: "{name}: {min_price} at {n} shops | PicWise UK", or "… at {shop}"
    when one shop sells it.
- **H1:** the thing itself, never a phrase written to rank ("best cheap power bank
  2026").
- **Meta description:** two of the page's facts, for example the count and price range,
  then the shops. The owner has said the search results page is another piece of work;
  these are only what the page itself carries.

### 4.7 Never on a page

- ratings, reviews, "tested" or "expert" without real ones;
- countdowns or "only 2 left" unless the shop states the stock;
- a price older than the last load;
- the same paragraph on more than a handful of pages (the what-to-check lists stay
  short, so they never become the page);
- FAQ blocks written to fill space.

## 5. Order of work

Each step is told to the owner first and reaches `main` on the owner's yes.

1. **The server:** the owner buys it and puts the keys and feed links in GitHub's
   secrets. A GitHub workflow sets it up (Ubuntu, Caddy, PostgreSQL, firewall,
   updates), and the site runs on it with today's code and today's feed, compared with
   Vercel.
2. **Domain and Cloudflare,** on the owner's word. Vercel is kept until then.
3. **The catalogue in PostgreSQL:**
   - the nightly load of section 1.4, the search reading from it;
   - the same 118 searches and kinds before and after;
   - memory measured.
4. **Every shop of the UK feed,** then the US feed.
5. **The pages of the spec,** in batches, read in Search Console between batches.
6. **The bot,** reporting only, until the owner decides what a score changes.
7. **The AI text** for one-shop products, starting with a sample whose cost is measured.

## Sources

- [Hetzner: price adjustment of 15 June 2026](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
- [Hetzner CX and CAX unavailable (2026)](https://stackvaluelab.com/hetzner-cx-cax-unavailable/)
- [OVHcloud: the VPS 2027 range](https://blog.ovhcloud.com/en/posts/vps-2027/)
- [Cloudflare: all purge methods for all plans](https://developers.cloudflare.com/changelog/post/2025-04-01-purge-for-all/)
- [Cloudflare: purge cache (limits)](https://developers.cloudflare.com/cache/how-to/purge-cache/index.md)
- [Cloudflare: Cache Rules](https://developers.cloudflare.com/cache/how-to/cache-rules/)
- [Google: how Google crawls locale-adaptive pages](https://developers.google.com/search/docs/specialty/international/locale-adaptive-pages)
- [Google: managing multi-regional and multilingual sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)
- [Google: localized versions (hreflang)](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google: spam policies](https://developers.google.com/search/docs/essentials/spam-policies)
- [Google: optimizing for generative AI features in Search](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
- [Google: Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals)
- [Protego, a robots.txt parser](https://github.com/scrapy/protego)
