# Application message for Awin advertisers

Owner asked (2026-10-13) what to write when applying to the large advertisers on the
shortlist, then corrected the first draft on two commercial points that were both
right:

- **It did not say we send them customers.** That is the only thing an affiliate
  manager is reading for. The first draft led with what PicWise is, which interests
  nobody on the other side of the form.
- **The comparison wording works against us.** A merchant reads "comparison" as "they
  will put my product next to a cheaper competitor". Leading with it invites a no.

So the message below leads with the referral and drops comparison from the pitch.

Two things are deliberately **not** changed, and the reason matters more than the
wording:

- **No traffic numbers.** An application that overstates its audience is a false claim
  on a commercial form. A manager who checks rejects and remembers.
- **No claim that PicWise shows only their products.** It does not, and a merchant who
  feels misled after approving closes the account and tells the network why. Losing a
  programme after approval is worse than a slower yes. "A small, curated selection"
  is honest and still reads well.

Keep it short. These are read in about twenty seconds.

---

## The message

> **PicWise — qualified buyer referrals (UK & US)**
>
> We send ready-to-buy customers straight to your product pages.
>
> PicWise answers shoppers who already know what they want and need to settle on
> which one to buy. We put a small, curated selection in front of them and send them
> directly to the retailer's own product page to complete the purchase — no basket of
> ours, no interstitial, no second chance to lose them.
>
> **What we are not:** not a coupon, voucher or cashback site. We publish no discount
> codes, run no incentivised clicks and do not bid on brand terms. No margin erosion,
> no code leakage, no cannibalised sales you would have made anyway.
>
> **Why your programme:** your catalogue covers [CATEGORY], and your product data is
> complete — accurate titles, identifiers, product detail and customer ratings. We
> choose retailers on data quality, because we can only present a product well if the
> retailer describes it well.
>
> **What we need:** product feed access, including the product rating and review count
> fields where your platform provides them.
>
> We are early-stage and building category by category, and we would rather start with
> a retailer whose data lets us present its products accurately than chase volume.
>
> Site: picwise.subby.cloud

---

## Why each paragraph is there

- **First line is the offer**, not the product. "Ready-to-buy customers straight to
  your product pages" is what the manager is scanning for.
- **"No basket of ours, no interstitial"** answers a fear managers have about
  comparison and aggregator sites: traffic that gets intercepted, re-sold or lost
  between the click and the checkout.
- **The "what we are not" paragraph does the heaviest work.** Coupon, voucher and
  cashback publishers are the ones programme managers are tired of, because they
  take credit for sales the retailer had already won and cost margin on top. Saying
  plainly that PicWise is none of those puts the application in a different pile.
  Every clause in it is true of the project today.
- **"We choose retailers on data quality"** turns the application around: it is a
  compliment, and it is also exactly what PicWise does, measurably — see
  `tools/check_awin_feed.py`, which keeps or rejects a shop on whether its products
  can be identified and described.
- **The rating ask is in from the first contact**, so there is no second conversation
  after a feed arrives without them, which is what happened with the first feed.

## For a short form

> PicWise sends ready-to-buy customers straight to retailers' product pages. We are
> not a coupon, voucher or cashback site — no discount codes, no incentivised clicks,
> no brand-term bidding. We are applying because your product data is complete enough
> for us to present your products accurately, including customer ratings.

## If a programme rejects you

Ask one question back, because the answer is useful either way: whether the rejection
is about traffic volume or about fit. A volume rejection is worth re-applying to in a
few months. A fit rejection means the category is wrong and waiting changes nothing.

## A separate message to every advertiser who approves you

The feed may still arrive without ratings, as the first one did. One message to the
programme manager:

> Does your Awin product feed populate `average_rating` and the review count? Our
> product pages show your customer ratings alongside your products, and your site
> collects them already. If those fields are not currently in the feed, is it possible
> to include them?

A reasonable ask rather than a favour: the shop holds the number, the column exists in
the Awin specification, and a retailer whose good ratings are visible benefits from
them being there.

## One line kept from the first draft, and why

The first draft said commission never influences the ranking. That is true, it is
written in `docs/MISSION.md` and `docs/REVENUE_NEUTRALITY_RULES.md`, and it is worth
saying -- but to a merchant it can read as "I cannot buy position", which is not what
you want them weighing during an application. It is better said **after** approval, if
a manager asks how placement works, where it reads as integrity rather than a
limitation.
