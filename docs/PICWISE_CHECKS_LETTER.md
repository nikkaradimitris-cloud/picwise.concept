# A letter to a shop the checks cannot check

The checks' rules, 5.6.2: the morning after a shop's first night of "cannot be checked",
the daily report names the shop and why, with a letter **for the owner to send it through
Awin** when it refuses the bot. The owner sends it himself, under his own name; nothing is
sent for him. The daily session fills in the shop's name and the paragraph of its reason,
and gives the letter as it is, in English, with one line in Greek saying what it asks.

Which paragraph, by the reason the health run prints ("checks, cannot be checked: SHOP:
REASON, day N"):

| Reason | Paragraph |
|---|---|
| refuses the bot | A |
| robots.txt refused, robots.txt disallows its product pages | B |
| asks for a crawl-delay over 60 s | C |
| no address of its own | D |
| its pages are not read | none: a recipe is made (4.5.3), no letter |

---

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

PARAGRAPH

Without that, we cannot check your products, and they come off PicWise in a few days. With
it, they stay listed with the prices your site shows.

Thank you,
OWNER'S NAME
PicWise

---

**A** (refuses the bot): Right now your site's protection against bots stops it: it is
shown a check page instead of the product. Could you let this user agent through?

**B** (robots.txt): Right now your robots.txt does not let it read product pages. Could you
allow it there (`User-agent: picwisebot`, `Allow: /`)?

**C** (crawl-delay): Your robots.txt asks for more than 60 seconds between pages, so it
could check only a few of your products a day. Could you allow it a shorter pause (it never
asks faster than one page every 3 seconds)?

**D** (no address): Your Awin feed gives each product only Awin's link, not the address of
its page on your site, and the bot never clicks Awin links. Could you add each product's own
page address to the feed (Awin's `merchant_deep_link` column)?

In Greek, for the owner (one line, with the letter): «Τους ζητάμε να αφήσουν το bot μας να
ελέγχει τα προϊόντα τους· αλλιώς βγαίνουν από το PicWise σε λίγες μέρες.»
