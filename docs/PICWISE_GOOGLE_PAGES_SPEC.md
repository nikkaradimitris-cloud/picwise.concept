# Pages for Google: specification

Written on 2026-10-23 at the owner's word: «Ναι, γράψ' το ως προδιαγραφή μόνο εάν είναι
ο βέλτιστος τρόπος ... μόνο εάν αυτό είναι πλήρως συμβατό με τις προδιαγραφές της
google». Nothing in it is built. Each part is built in small steps, each told to the
owner first, and reaches `main` only on the owner's yes.

Google's pages were read through web-search summaries of them, because
`developers.google.com` cannot be opened from the session. Before a part is built, its
rules are read again at the source: Google changes them.

## Σύνοψη για τον ιδιοκτήτη

- Η Google απαγορεύει ξεχωριστή σελίδα για κάθε διατύπωση μιας αναζήτησης (οδηγός της,
  Μάιος 2026). Γι' αυτό κάθε σελίδα αντιστοιχεί σε ένα **διαφορετικό σύνολο προϊόντων**
  (κατηγορία, είδος, είδος με ένα χαρακτηριστικό) ή σε ένα **προϊόν**. Τις μικρές
  λέξεις-κλειδιά τις αντιστοιχίζει η ίδια η Google σε αυτές τις σελίδες.
- Η Google βλέπει μόνο σελίδες που περνούν έλεγχο ποιότητας. Οι υπόλοιπες υπάρχουν για
  τους επισκέπτες, αλλά λένε στη Google να μην τις καταχωρίσει.
- Κανόνας του ιδιοκτήτη (29/10, `PROJECT_RULES.md` §13): το PicWise στήνεται ολόκληρο,
  και όλα τα προϊόντα βρίσκονται στη δική μας αναζήτηση. Στη Google δίνουμε τμηματικά
  μόνο όσα διαλέγει ο ιδιοκτήτης και περνούν το όριο του είδους τους: αρκετά προϊόντα,
  από αρκετά καταστήματα, ελεγμένα. Ένα είδος μπορεί να έχει 15.000 προϊόντα στην
  αναζήτηση και η Google να βλέπει τις σελίδες 100 ελεγμένων.
- Τρία είδη σελίδων: η σελίδα λέξης-κλειδιού (4 προϊόντα, σύγκριση, τιμές), η σελίδα
  προϊόντος από πολλά καταστήματα (όλες οι τιμές) και η σελίδα προϊόντος από ένα
  κατάστημα (ελεγμένο κείμενο AI, παρόμοια προϊόντα).
- Ο κατάλογος του server κρατά μόνο ζωντανά προϊόντα. Ένα προϊόν που χάνεται μένει 30
  μέρες ως «προσωρινά μη διαθέσιμο» και μετά σβήνεται.
- Οι σελίδες βγαίνουν σε δόσεις, και κάθε δόση μετριέται στο Search Console πριν βγει η
  επόμενη.
- Καμία εγγύηση κατάταξης: η Google κρίνει την αξία κάθε σελίδας και όλου του site.

## 1. The rule that shapes everything: a page per distinct thing, never per wording

Google's guide to generative AI features in Search (15 May 2026) says that creating
separate content for every variation of how people might search, primarily to
manipulate rankings, violates its scaled content abuse policy, and does not work: "a
high quantity of pages doesn't make a website higher quality or more relevant to
users". Its systems match a query to a page without the exact wording, so a site need
not capture every long-tail variation. The spam policies add two more limits:

- **doorway abuse**: "substantially similar pages that are closer to search results
  than a clearly defined, browseable hierarchy";
- **scaled content abuse**: "scraping feeds, search results, or other content to
  generate many pages ... where little value is provided to users".

So PicWise has one page for each distinct thing a buyer can look for:

- **a product**: one page, whichever shops sell it. Identity by GTIN, else brand and MPN
  (`_product_identity_key`). Its variants (`item_group_id`) share that one page.
- **a kind of product** (`power bank`) and the **categories** above it (`Electronics`).
- **a kind with a property that gives it its own set of products** (`power bank
  20000mAh`, `3 seater sofa`): the facet page, called "the keyword page" below.

The long tail comes from the number of products and of real facets, never from pages
per wording. A keyword maps to the page whose products answer it, and its variations
("cheap 20000mah power bank", "power bank 20000 mah") map to that same page. A facet
page exists only when its set of products differs from its parent's. A property that
leaves the set as it is makes no page.

**Conflict raised with the owner (PROJECT_RULES 1.4):** `concept.picwise.txt` section
17 and `docs/SEO_WAVES_SPEC.md` speak of thousands of landings, each targeting one
long-tail query. Under Google's rule, each landing is one distinct set of products,
never one wording. The wording of those files changes only on the owner's yes.

## 2. The index: which pages exist and which ones Google sees

| Page | Address (UK; each market has its own prefix) | For Google |
|---|---|---|
| Home | `/uk/` | indexed |
| Category, kind | `/uk/electronics/`, `/uk/power-banks/` | indexed once past the gate |
| Facet (keyword page) | `/uk/power-banks/20000mah/` | indexed once past the gate |
| Product | `/uk/p/<name>-<id>/` | indexed once past the gate |
| Product unavailable (up to 30 days) | the same address | indexed, marked unavailable |
| Product gone (after 30 days) | the same address | 410 |
| The site's own search | `/search?q=...`, `/results`, `/picwise-reference`, `/?q=...` | `noindex`; `Disallow` too, once Google has dropped them |
| The demo (a preview) | `/demo` | `noindex` |
| The redirect to the shop, and routes that act when called | `/out/...`, `/subby-proof`, `/cron/...` | `Disallow` in `robots.txt` |
| JSON routes | `/health`, `/suggest.json`, `/private-beta-readiness` | `X-Robots-Tag: noindex` |
| Sorted or filtered variants | address parameters | canonical to the page without them; never in a sitemap |
| A facet or kind with no products | — | 404, never an empty page with 200 (a soft 404) |

The order for `/search` matters. A page blocked by `robots.txt` is never fetched, so
Google never sees its `noindex` and can still index the bare address. So `noindex`
comes first, and `Disallow` only after Google has dropped those pages.

**The gate**, for every page type (and `PROJECT_RULES.md`, section 13, owner, 2026-10-29:
built whole, given to Google part by part, the parts the owner chooses):

- real data only;
- products of the kind on a list page, with no minimum: even one, shown on a layout of
  its own, never as one small card in the middle (owner, 2026-10-31; before, at least 4,
  `docs/pickwise_roadmap_step6_quality_index_gate.md`);
- the kind's bar: products read as the right kind and checked (kind, price, stock); no
  minimum of shops (owner, 2026-10-31: «Καταργείται το όριο των τριών καταστημάτων ανά
  είδος»); further numbers are the owner's to set (TODO);
- a part of the site the owner has chosen to open;
- a set of products of its own;
- no adult products (the feed's `adult` column);
- for a product page, the conditions of its section below.

A page that fails the gate is still shown to visitors, carries `noindex` and stays out
of the sitemaps.

**Sitemaps:**

- one per page type and market, each with at most 50,000 addresses or 50 MB, all listed
  in a sitemap index;
- only canonical, indexable addresses;
- `lastmod` only when the page's content changed (price, availability, products), and
  left out where that is not known.

**How a page gets its products:** the nightly catalogue (section 7) holds every live
product by kind and property. A page reads its products from it by the search's own
rules (only the kind asked for, in stock, cheapest first), so a page and a search
never disagree.

The `/best/<slug>` pages, their gate and their sitemap (`src/picwise_buying_pages`,
stage 37) are the earlier start of this work. They publish nothing today, and their
gates are reused where they fit.

## 3. The keyword (facet) page, and the kind and category pages

**Above the fold** (`docs/LANDING_PAGE_SPEC.md`, unchanged):

- the heading is the thing searched ("20000mAh power banks");
- a line of facts ("45 in stock in 6 shops, from £12.99, prices of 23 Oct");
- the 4 (the Recommended and the 3 cheapest), each with image, name, price, shop,
  delivery cost and button;
- "4 of 45" and More.

**Below the fold:**

- **comparison**: the four's key properties side by side, from the feed's columns
  (only what the feed states, as PicWise reads it);
- **price summary**: cheapest, dearest, median, number of shops;
- **how PicWise chooses**: cheapest first, the Recommended is the middle price, no shop
  pays for its place; and PicWise earns from sales through its links;
- **links**: the path (Home > Electronics > Power banks > 20000mAh), related facets and
  the kind's page;
- **the full list**: numbered pages, each with its own address and linked in sequence,
  so every product page can be reached by plain links.

Every text on the page is written by PicWise from the data (counts, prices,
properties). A shop's description is never copied onto it.

**Structured data:** `BreadcrumbList` only. No `Product` markup on a list page: Google
gives product rich results only to a page about one product, and a category or list
page is not one. List carousels (`ItemList`) exist only as a beta in the EEA, through
the Comparison Shopping Services programme; they are for the euro markets, later.

## 4. The product page of a product two shops or more sell

- **Offers**: every shop's offer side by side, cheapest first, each with price,
  delivery cost, availability, shop and its own button.
- **Content**: the product's facts from the feed's columns, its images (the shops'
  links), the path, and similar products of its kind.
- **Structured data**: a `Product` with name, image, brand and GTIN/MPN, and an
  `AggregateOffer` (`lowPrice`, `highPrice`, `offerCount`, `priceCurrency`). This is
  Google's own example of a shopping aggregator page. Everything in the markup is shown
  on the page.
- **No rating or review markup**: PicWise has none and invents none.

## 5. The product page of a product one shop sells, with AI-curated text

Owner's decision (23/10): every product has a page, and a product only one shop sells
gets its own layout and a richer text curated by an AI system.

Google allows generated text that helps people. It forbids it when many pages are
generated without adding value, or when a feed is reworded. It asks that generated text
be checked for accuracy before publication, and that readers who would wonder how it
was made be told.

**The page's value** is what the shop's own page lacks:

- where its price stands among products of its kind ("among the 10% cheapest 20000mAh
  power banks in 6 shops");
- similar or cheaper products of the same kind from other shops. This is the comparison
  Google names, made with similar products because no other shop sells this one;
- its facts as a table, from the feed's columns;
- what to check before buying it, from its kind and its facts.

**The AI text:**

- is written only from the product's own data and the figures PicWise computed;
- never rewords the shop's description and never states a fact the data lacks;
- never claims a test, a review or a rating;
- is signed by PicWise, never by an invented person;
- is checked by code before publication: every number, unit, brand and model name in it
  is compared with the data, and a text that fails is not published.

The page says how its text is made ("written with AI from the shop's data, and checked
against it").

**Structured data:** a `Product` with one `Offer` (price, currency, availability, the
shop as seller).

**Layout:** images first; then name, price, shop, delivery cost, availability and the
button; then the facts table, the text, similar products and the path.

**Gate:** the page goes to Google only when its text has passed the check, it has
enough facts (the number is set on a sample) and at least 3 similar products are in
stock.

## 6. A product that is gone or out of stock

Owner's decision (23/10): it is kept for 30 days.

**During the 30 days:**

- its page stays at its address, says it is temporarily unavailable and shows similar
  products that are in stock. Google advises keeping a temporarily out-of-stock
  product's page, marked as such, rather than removing it;
- it is never in a search's answer or a page's four;
- its structured data says so: while the shop's feed still lists it as out of stock,
  its `Offer` carries `OutOfStock`; once the feed no longer lists it, the page carries
  no offer.

**After 30 days:**

- the page answers 410 and leaves the sitemaps;
- its data and its text are deleted;
- there is no redirect to another page: Google may read a redirect to something that
  is not the same product as a soft 404.

## 7. The catalogue on the server: live products only

Owner's requirement (23/10). Each night, shop by shop:

- the feed is read row by row, and the file itself is not kept;
- a new product is added, a changed one (price, availability, data) is updated, and an
  unchanged one is left as it is;
- a product absent from the feed or out of stock is marked gone (section 6), and one
  gone for 30 days is deleted with its text and its page;
- a shop whose feed fails, or comes much smaller than the day before (the share is to
  be set; half is the proposal), loses nothing that night and raises an alert.

**What is kept:** every column of a shown product (owner's rule of 23/10: nothing that
may serve these pages is left out). Images are never stored, only their links. Logs
and backups are kept for a set number of days.

**Room:** it follows the live products, at about 6-10 KB per product with its text and
indexes (estimated from the owner's file). That is about 4-6 GB for 600,000 products.
A morning report gives the live, added and deleted products and the room used against
the plan's limit, with an alert at 70%.

**AI text:** written once per product, and again only when its data changes.

## 8. Technical requirements on every page

- **Speed**, by Core Web Vitals at the 75th percentile, on phones and on computers:
  LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1. Image sizes are declared so nothing moves. The
  shops' images load from the shops' servers and decide the LCP, so they are measured
  first.
- **HTML from the server**: the content, the links and the structured data are all in
  the first HTML, and links are plain `<a href>`.
- **Links to shops** carry `rel="sponsored"`. They already do (`nofollow sponsored
  noopener`).
- **Markets**: one address per market (`/uk/`, `/us/`, later the euro countries), each
  with its own shops and prices. `hreflang` en-GB and en-US point to each other and to
  an `x-default`, both ways. A euro market's pages are written for that market (its
  shops, its prices, its language). Google lists automated translation that adds little
  value among its examples of scaled content abuse.
- **No interference with the back button**: a spam policy since June 2026. Nothing on
  the site interferes with it today.
- **Trust pages**: an About page, how PicWise chooses, that PicWise earns from sales
  (also required by the advertising rules of the UK and the US), contact, privacy.
- **Adult products** never appear on these pages.

## 9. Release in batches

Pages reach Google in batches, each one the owner chooses (`PROJECT_RULES.md`, section
13). First a small batch, a few hundred pages of one kind.
Then Search Console is read before the next batch goes out: pages indexed or refused,
impressions, clicks.

Google weighs the site as a whole: a high share of weak pages lowers the good ones too,
and recovery takes months. A batch Google does not keep is fixed or withdrawn before
more pages go out.

## 10. What no specification can promise

Google publishes rules, not a checklist that guarantees a place in its results. It
judges each page's value and the whole site's, and it changes its rules. This
specification follows every rule found. Whether a page ranks shows only in Search
Console, which is why section 9 exists.

## 11. Open, the owner's

- The wording of the founding documents on long-tail landings (section 1).
- The steps to build, in order:
  1. the site's own search out of Google, the smallest step and the one that protects
     the site today. **Built on the branch on 23/10** (owner: «Ναι, βάλε το noindex στο
     /search και προστάτεψε το site από την google όσο το χτίζουμε»): the rows of
     section 2 for the search, the demo, `robots.txt` and the JSON routes
     (`tests/test_picwise_google_protection.py`). **On `main` and live since 23/10
     18:15 UTC** (merge `47cd76b`, owner: «Ναι, να μπει στο main και κάνε τον
     έλεγχο»), seen by the live check at 18:16;
  2. the catalogue on the server;
  3. the pages.
- The AI system and its cost, measured on a sample.

## Sources (Google)

- [Spam policies](https://developers.google.com/search/docs/essentials/spam-policies)
- [Optimizing for generative AI features in Search](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
- [Generative AI content on your website](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)
- [Creating helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Ranking systems guide](https://developers.google.com/search/docs/appearance/ranking-systems-guide)
- [Product snippet structured data](https://developers.google.com/search/docs/appearance/structured-data/product-snippet)
- [Merchant listing structured data](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing)
- [Carousels (beta)](https://developers.google.com/search/docs/appearance/structured-data/carousels-beta)
- [Ecommerce site structure](https://developers.google.com/search/docs/specialty/ecommerce/help-google-understand-your-ecommerce-site-structure)
- [Pagination](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading)
- [URL structure](https://developers.google.com/search/docs/crawling-indexing/url-structure)
- [Faceted navigation](https://developers.google.com/crawling/docs/faceted-navigation)
- [Block indexing with noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing)
- [Sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [HTTP status codes and soft 404](https://developers.google.com/search/docs/advanced/crawling/soft-404-errors)
- [Pausing an online business (out-of-stock pages)](https://developers.google.com/search/docs/crawling-indexing/pause-online-business)
- [Qualify outbound links](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links)
- [Localized versions (hreflang)](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals)
- [Back button hijacking](https://developers.google.com/search/blog/2026/04/back-button-hijacking)
