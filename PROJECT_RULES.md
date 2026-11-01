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
- A product whose photo is gone is not shown, counted or recommended (owner, 2026-11-01: «Όταν το προϊόν δεν φέρνει φωτογραφία δεν πρέπει να εμφανίζεται... Στις περισσότερες περιπτώσεις είναι not found»): the server asks every photo each night (`deployment/server/check_photos.py`), only a link to nothing (HTTP 404, 410) is gone, and the site leaves those products out (`picwise_providers.product_photos`); a card whose photo fails in the visitor's browser is hidden whole (`docs/PICWISE_DECISION_CONTRACT.md`, "What a product must carry to be shown").

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
- The order, after the kind asked for and availability: the Recommended first; then the products a current shop offer covers, cheapest first; then the rest, cheapest first (owner, 2026-11-01). An offer covers a product only where its own words leave no doubt: the whole shop, or the product's kind named in it, live now by its own dates, and, for a voucher, only with its code, which Awin gives for the programmes PicWise is joined to (`picwise_providers.product_offers`; `docs/PICWISE_DECISION_CONTRACT.md`, "Offers first"). PicWise is paid nothing to put an offer first; commission still never decides the order. When the answer holds three products or more and a current shop offer covers one of them, the Recommended is a product on offer: of those on offer, the one nearest the middle of their prices, one with an EAN/GTIN first (owner, 2026-11-01: «Εάν υπάρχει προσφορά να προτείνει την προσφορά», and «το recommended όταν υπάρχει προσφορά πρέπει να δείχνει την προσφορά»). Otherwise the Recommended is the middle product in price order, the median, with a dearest product costing at least twice the next one left out of the count (`docs/PICWISE_DECISION_CONTRACT.md`, "Price first"; changed on 2026-10-16 by the owner).
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
- Results behind the scanning screen within about 4 sec (owner, 2026-10-16). The
  screen states only true facts, the real number of shops and products and the steps
  actually taken, and results are never held back on purpose.

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

## 13) Google Rule

Set on 2026-10-29 by the owner: «Θα στήσουμε ολοκληρωμένα και θα δώσουμε στη Google αυτά που θέλουμε τμηματικά».

- PicWise is built whole: every product a card can show is in PicWise's own search, whether or not Google sees it.
- Google is given only what the owner chooses, part by part. Google indexes pages, not products: only the pages meant for Google (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 2), never the site's own search, whose pages carry `noindex`.
- A page opens to Google only when its kind passes the bar and the owner chooses its part. The bar: products of the kind read as the right kind and checked (kind, price, stock). No minimum of shops (owner, 2026-10-31: «Καταργείται το όριο των τριών καταστημάτων ανά είδος»), and no minimum of products: even one product, on a layout of its own. Further numbers of the bar are the owner's to set (TODO). A page that does not pass is still shown to visitors, carries `noindex` and stays out of the sitemaps.
- A page meant for Google may choose its products among all of its kind's products; whatever Google sees on it must be true.
- A visitor who comes from Google finds the whole catalogue through PicWise's own search: a kind may have 15,000 products while Google sees the pages of 100 checked ones.
- Parts go out one at a time, and a part Google does not keep is fixed or withdrawn before the next (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 9).

## Enforcement

These rules are mandatory for all Codex-assisted changes in this project, including code, docs, architecture, tests, UI, backend, routing, product, tracking, SEO, dashboard, and deployment work.
