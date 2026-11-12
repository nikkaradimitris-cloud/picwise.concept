# PROJECT_RULES.md

Mandatory operating rulebook for Picwise Production.

## 1) Source Of Truth Order

1. `PROJECT_RULES.md` is the first operating rulebook.
2. `concept.picwise.txt` (or the existing concept file in this repository) is the product concept source of truth.
3. `docs/` specs/contracts become implementation contracts once created.
4. If any conflict exists between these sources, do not guess, do not improvise, and do not continue implementation. Stop and report the conflict clearly.

## 2) Core Identity

Changed on 2026-10-16 by the owner: "price first" (`docs/picwise_price_first_plan_2026-10-15.md`). Changed again on 2026-11-01 by the owner: products a current shop offer covers come first (owner, 2026-11-01: «Ανά προϊόν... Όταν ψάχνει ένας πελάτης ένα προϊόν ή μία κατηγορία υπάρχει προσφορά σε αυτό το προϊόν ... προϊόντα με προσφορές πρώτα», and, asked whether that changes "cheapest first": «Ένα προϊόν με προσφορά θα μπαίνει πρώτα από το φθηνότερο»).

- Picwise finds the product the buyer asked for, shows only what is in stock, the products a current shop offer covers first and then cheapest first, and makes one honest pick.
- Picwise must reduce search-to-decision time.
- Every purchase-intent query must lead to 4 choices first, with exactly 1 honest recommended choice among them, and a "More" that opens the next 4 in that order as often as the buyer asks.
- Fewer than four right products are shown as they are (`docs/PICWISE_DECISION_CONTRACT.md`, 2026-10-16). Even one product is shown when there is no other, on a layout of its own, never as one small card in the middle (owner, 2026-10-31: «Το ευρετήριο μπορεί να εμφανίσει και ένα προϊόν εάν δεν υπάρχουν άλλα σε αυτή την περίπτωση το εμφανίζει διαφορετικά»).
- A product whose photo is gone is not shown, counted or recommended (owner, 2026-11-01: «Όταν το προϊόν δεν φέρνει φωτογραφία δεν πρέπει να εμφανίζεται... Στις περισσότερες περιπτώσεις είναι not found»): the server asks every photo each night (`deployment/server/check_photos.py`), only a link to nothing (HTTP 404, 410) is gone, and the site leaves those products out (`picwise_providers.product_photos`); in the visitor's browser a card is seen only once its photo has loaded, and one whose photo fails never (owner: «να μην μπορεί να εμφανιστεί ένα προϊόν αν δεν έχει φωτογραφία στο ui») (`docs/PICWISE_DECISION_CONTRACT.md`, "What a product must carry to be shown").
- In a complex search, one whose words of need no product of the kind carries in its title ("quiet washing machine", «σακίδιο για σχολείο»), the products whose own words show that they fit the need, as the AI layer reads them and code checks letter for letter, come first, the Recommended among them, each marked with a ✓ and its own words (owner, 2026-11-06: «Όταν η αναζήτηση είναι συνθετή και το ai έχει εμπλακεί στον ευρετηριασμό τα προϊόντα που υποδεικνύει πρέπει να έχουν λεκτική αναφορά αλλά και οπτική σημείωση καθώς πρέπει να κατατάσσονται και πρώτα», then «Ναι, συμφωνώ με όλα, προχώρα» to the order, the time and the mark proposed) (`docs/PICWISE_DECISION_CONTRACT.md`, "The products that fit a complex search first"; `docs/PICWISE_AI_LAYER_SPEC.md`, 4.4). The page never waits for the AI: it comes at once, and the products that fit move up when the answer comes.
- A search for a kind shows that kind, never another thing its word names (owner, 2026-11-03: «Στα tablets .. tablet... Βγάζει και χάπια... Εφόσον το κύριο είδος είναι tablet ... αυτό πρέπει να συμβαίνει γενικά παντού»): a product whose title alone names the kind is of that kind only where the aisle it is filed in may hold the kind's department, written per aisle of Google's (`concept_understanding._AISLE_HOLDS`), and per narrower aisle where Google's narrows it (`_SUB_AISLE_HOLDS`: jewellery holds jewellery only, owner, 2026-11-05); the aisle is read from a path of Google's, or from a shop's own shelf found among Google's shelves by its name (`_shelf_aisles`: "Vitamins & Supplements" is in Health & Beauty, which holds no computer); a kind the shop's type or shelf names is read against the aisle the same way ("Toners & Astringents" names no printer toner; owner, 2026-11-05: «Εντάξει, προχώρα με το βήμα 2»); a product whose kind is doubtful is still found by its words when a search's words are carried by none of its kind's products ("vitamin tablets") (`docs/PICWISE_DECISION_CONTRACT.md`, "The main kind only").

## 3) Required Output Contract (Always)

Every purchase-intent result must include all of the following:

- 4 choices
- 1 recommended
- decision labels
- clear CTA
- direct redirect
- tracking event
- a "More" for the next 4 cheapest
- no fake data
- no commission-first ranking

If any item is missing, the output is non-compliant.

## 4) Forbidden Behavior

The project must never:

- Turn Picwise into an e-shop.
- Turn Picwise into a marketplace.
- Turn Picwise into an affiliate blog.
- Show a product that is out of stock, or that is not the kind the buyer asked for.
- Add fake products, fake reviews, fake ratings, fake conversions, fake revenue, fake savings, fake urgency, or fake AI confidence.
- Use commission as a product ranking or recommendation criterion.
- Create frontend/backend implementation before required specs/contracts exist, unless explicitly instructed.
- Invent business logic when concept/spec is missing. Add a `TODO` and flag the gap.

## 5) Revenue Neutrality

- Picwise may earn through affiliate/referral/lead/conversion models.
- Commission is never part of recommendation logic.
- The order, after the kind asked for and availability: the Recommended first; then the products a current shop offer covers, cheapest first; then the rest, cheapest first (owner, 2026-11-01). In a complex search, the products that fit the buyer's need (section 2) come first, in that same order among them, then the rest in that order; the Recommended is chosen among those that fit, by the same rule (owner, 2026-11-06). Fitting a need the buyer typed is no commission criterion. An offer covers a product only where its own words leave no doubt: the whole shop, or the product's kind named in it, live now by its own dates, and, for a voucher, only with its code, which Awin gives for the programmes PicWise is joined to (`picwise_providers.product_offers`; `docs/PICWISE_DECISION_CONTRACT.md`, "Offers first"). PicWise is paid nothing to put an offer first; commission still never decides the order. When the answer holds three products or more and a current shop offer covers one of them, the Recommended is a product on offer: of those on offer, the one nearest the middle of their prices, one with an EAN/GTIN first (owner, 2026-11-01: «Εάν υπάρχει προσφορά να προτείνει την προσφορά», and «το recommended όταν υπάρχει προσφορά πρέπει να δείχνει την προσφορά»). Otherwise the Recommended is the middle product in price order, the median, with a dearest product costing at least twice the next one left out of the count (`docs/PICWISE_DECISION_CONTRACT.md`, "Price first"; changed on 2026-10-16 by the owner).
- A price the buyer chooses on the price bar above the cards starts the answer from it: the products below it leave the answer, and the order, the Recommended, "More" and the counter are those of the products from that price, by the same rules; the bar runs from the answer's lowest price to its highest (owner, 2026-11-12: «Να μπει ένα φίλτρο με τη μορφή μπάρας που να διαλέγει με την τιμή για να γλιτώσουμε το πρόβλημα που βγάζει τα φθηνότερα και μπορεί να είναι smartwatch και να δείχνει λουράκια μπορεί να είναι tablet και να βγάζει πρώτα θήκες ... βάζοντας ένα φίλτρο τιμής το οποίο να τερματίζει στην υψηλοτερή και να ξεκινάει από την χαμηλότερη κουνώντας μία μπίλια θα μπορεί αμέσως να φιλτράρει»; `docs/PICWISE_DECISION_CONTRACT.md`, "The price bar"). It is the buyer's choice, never PicWise's, and no commission criterion.
- Stock: a shop's own site, read by the shops' catalogue bot within the last three days, decides a product's stock before the feed, either way: its "sold out" hides a product the feed calls in stock, its "in stock" shows one the feed calls out of stock (owner, 2026-11-12: «να διαβάζει το bot το απόθεμα από τα sites τους και γενικά να επαληθεύει»). The bot asks every shop of the feed, the ones never read first; without a recent reading of the shop's site, the feed decides (`shop_catalogue.STOCK_DAYS`).
- A shop in several networks is one shop, known by its own site's domain. Its price and availability come from the freshest feed (the latest update date the network states) with a real stock state, never chosen by commission; only when the networks give the same offer is the link taken from the network that pays best, the highest commission first (`docs/PICWISE_DECISION_CONTRACT.md`, "One shop in several networks"; owner, 2026-10-22).

## 6) Brain Model

All implementation must respect these 5 product brains:

1. Tech / Specs / Electronics
2. Software / Programs / SaaS
3. Physical Products / Home / Machines
4. Financial / Utility / Contract Products
5. High-Trust / Risk / Sensitive Decisions

## 7) Decision Depth Model

All implementation must respect these 3 decision depths:

1. Fast Decision
2. Considered Purchase
3. High-Stakes / High-Trust

## 8) Domain Rule

- Primary launch domain: `picwise.subby.cloud`
- Do not use `picwise.cloud` as primary domain.
- `picwise.cloud` is optional future standalone brand domain only.

## 9) Performance Targets

Mandatory targets:

- First render < 1.5 sec
- Full interactive < 2 sec
- Click to redirect < 300 ms
- Results behind the loading screen within about 4 sec (owner, 2026-10-16), and never
  held back on purpose. The screen states nothing untrue: since 2026-11-12 it names no
  number and no step, only the PicWise mark turning (owner: «δεν μου αρέσει να λέει ψάχνω από τόσα προϊόντα φτιάξε απλά ένα όμορφο φόρτωμα»).

Do not ship changes that knowingly violate these targets without explicit approval.

## 10) Dashboard / Subby Compatibility

- Picwise must be designed to send operational/business events to Subby dashboard later.
- Missing data must be represented as `not_connected`, `data_not_yet`, `not_applicable`, or `unknown`.
- Never fake dashboard metrics.

## 11) Workflow Rule

Before and during every change:

- Inspect current files before modifying them.
- Do not overwrite existing files blindly.
- Make small, closed, testable steps.
- Every implementation step must include relevant tests.
- Do not claim completion without proof (tests, checks, or concrete evidence).

## 12) First Project Phase Rule

- First phase is docs/spec/contracts foundation.
- Do not build live product UI until mission docs and contracts are created and reviewed.
- Met on 2026-05-06: the mission docs and contracts were created and their review passed (`PROGRESS.md`); the app has been built since and is live on `picwise.subby.cloud`.

## 13) Google Rule

Set on 2026-10-29 by the owner: «Θα στήσουμε ολοκληρωμένα και θα δώσουμε στη Google αυτά που θέλουμε τμηματικά».

- Nothing is declared to Google until the owner says so (2026-11-12, after a deployment that had put on the site a sitemap, its line in `robots.txt` and the home page's structured data: «Δεν θέλω να δηλωθεί τίποτα στην google ακόμα»): no sitemap, no `Sitemap:` line, no structured data, nothing given to Google's own tools. The seven pages Google could already index (owner, 23/10) stay as they were, each naming its own address (`picwise_surface.seo.DECLARE_TO_GOOGLE`).

- PicWise is built whole within its cap: every product a card can show and the cap of 15% a category keeps is in PicWise's own search, whether or not Google sees it (owner, 2026-11-08: «Το 15% που είχα πει αφορούσε ένα πλαφόν ... έτσι ώστε να μην μπει κάποιο κατάστημα με έναν τεράστιο όγκο και αλλάξει την ταυτότητα του site ... μπορούμε να κρατήσουμε αυτόν τον κανόνα και για το search έτσι ώστε να επιτυγχάνουμε καλύτερες ταχύτητες»; `picwise_providers.catalogue_cap`; until then, 2026-10-30: «Όλα στο search»). As shops are added, 15% of more is more; the server is upgraded as the project earns.
- Google is given only what the owner chooses, part by part. Google indexes pages, not products: only the pages meant for Google (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 2), never the site's own search, whose pages carry `noindex`.
- A page opens to Google only when its kind passes the bar and the owner chooses its part. The bar: products of the kind read as the right kind and checked (kind, price, stock). No minimum of shops (owner, 2026-10-31: «Καταργείται το όριο των τριών καταστημάτων ανά είδος»), and no minimum of products: even one product, on a layout of its own. Further numbers of the bar are the owner's to set (TODO). A page that does not pass is still shown to visitors, carries `noindex` and stays out of the sitemaps.
- A page meant for Google may choose its products among all of its kind's products; whatever Google sees on it must be true.
- A visitor who comes from Google finds the whole kept catalogue through PicWise's own search: a kind may have 15,000 products while Google sees the pages of 100 checked ones.
- Parts go out one at a time, and a part Google does not keep is fixed or withdrawn before the next (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 9).

## Enforcement

These rules are mandatory for all Codex-assisted changes in this project, including code, docs, architecture, tests, UI, backend, routing, product, tracking, SEO, dashboard, and deployment work.
