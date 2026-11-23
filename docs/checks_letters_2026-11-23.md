# Letters to the shops the checks cannot check — 2026-11-23 (their day 1)

The checks' rules 5.6.2 and `docs/PICWISE_CHECKS_LETTER.md`: the morning after a shop's
first night of "cannot be checked", the daily report names the shop and why, with the letter
filled in **for the owner to send through Awin, under his own name**. Nothing is sent for
him; no session writes to a shop.

Read from the health run of 2026-11-23 09:33 UTC (run 45148116992), the checks' first real
night: nine shops cannot be checked, each on day 1. **A shop leaves the site on its day 4**
(26/11) if nothing changes. One of the nine gets no letter: Pro-Camera's pages are read but
not understood, which is ours to mend (a recipe, rule 4.5.3), not the shop's to allow.

Before sending, put your own name in place of `OWNER'S NAME`.

| Shop | Why, in plain words | Letter |
|---|---|---|
| Aosom UK | its robots.txt does not let the bot read product pages | B |
| Bazta UK | its protection against bots shows the bot a check page | A |
| Elixir Garden Supplies | its protection against bots shows the bot a check page | A |
| InterRose | its robots.txt does not let the bot read product pages | B |
| Juicy Couture UK | its feed gives only Awin's link, not the product's own page | D |
| Luxe Mattress Affiliation | its protection against bots shows the bot a check page | A |
| Plusshop UK | its protection against bots shows the bot a check page | A |
| TV Cables | its robots.txt does not let the bot read product pages | B |
| Pro-Camera | its pages are read but not understood — ours to mend, no letter | — |

---

## Letter A — Bazta UK, Elixir Garden Supplies, Luxe Mattress Affiliation, Plusshop UK

Στα ελληνικά, μία γραμμή: ζητάει από το κατάστημα να αφήσει το bot μας να διαβάζει τις
σελίδες των προϊόντων του, γιατί η προστασία του από bots το σταματά.

**Subject:** Letting PicWiseBot check your products

Hello SHOP team,

I run PicWise (https://picwise.subby.cloud), a UK shopping search that lists your products
from your Awin product feed.

Before a product is shown, a small bot checks it on your own site: that its page opens, that
it is the same product, and its current price and stock. It reads only the product pages in
your Awin feed, follows your robots.txt, asks for one page at a time and waits at least
3 seconds between pages. It never clicks Awin links and never adds anything to a basket. It
names itself as:

`PicWiseBot/0.1 (+https://picwise.subby.cloud)`

Right now your site's protection against bots stops it: it is shown a check page instead of
the product. Could you let this user agent through?

Without that, we cannot check your products, and they come off PicWise in a few days. With
it, they stay listed with the prices your site shows.

Thank you,
OWNER'S NAME
PicWise

*(Put the shop's name in place of SHOP: Bazta UK, Elixir Garden Supplies, Luxe Mattress
Affiliation, Plusshop UK.)*

---

## Letter B — Aosom UK, InterRose, TV Cables

Στα ελληνικά, μία γραμμή: ζητάει από το κατάστημα να επιτρέψει στο robots.txt του να
διαβάζει το bot μας τις σελίδες των προϊόντων.

**Subject:** Letting PicWiseBot check your products

Hello SHOP team,

I run PicWise (https://picwise.subby.cloud), a UK shopping search that lists your products
from your Awin product feed.

Before a product is shown, a small bot checks it on your own site: that its page opens, that
it is the same product, and its current price and stock. It reads only the product pages in
your Awin feed, follows your robots.txt, asks for one page at a time and waits at least
3 seconds between pages. It never clicks Awin links and never adds anything to a basket. It
names itself as:

`PicWiseBot/0.1 (+https://picwise.subby.cloud)`

Right now your robots.txt does not let it read product pages. Could you allow it there
(`User-agent: picwisebot`, `Allow: /`)?

Without that, we cannot check your products, and they come off PicWise in a few days. With
it, they stay listed with the prices your site shows.

Thank you,
OWNER'S NAME
PicWise

*(Put the shop's name in place of SHOP: Aosom UK, InterRose, TV Cables.)*

---

## Letter D — Juicy Couture UK

Στα ελληνικά, μία γραμμή: ζητάει από το κατάστημα να βάλει στο feed του τη διεύθυνση της
σελίδας κάθε προϊόντος στο δικό του site, γιατί τώρα δίνει μόνο τον σύνδεσμο της Awin.

**Subject:** Letting PicWiseBot check your products

Hello Juicy Couture UK team,

I run PicWise (https://picwise.subby.cloud), a UK shopping search that lists your products
from your Awin product feed.

Before a product is shown, a small bot checks it on your own site: that its page opens, that
it is the same product, and its current price and stock. It reads only the product pages in
your Awin feed, follows your robots.txt, asks for one page at a time and waits at least
3 seconds between pages. It never clicks Awin links and never adds anything to a basket. It
names itself as:

`PicWiseBot/0.1 (+https://picwise.subby.cloud)`

Right now your Awin feed gives each product only Awin's link, not the address of its page on
your site, and the bot never clicks Awin links. Could you add each product's own page address
to the feed (Awin's `merchant_deep_link` column)?

Without that, we cannot check your products, and they come off PicWise in a few days. With
it, they stay listed with the prices your site shows.

Thank you,
OWNER'S NAME
PicWise
