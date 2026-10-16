# Advertisers to look for, UK and US

> **2026-10-16:** the owner dropped ratings (`docs/picwise_price_first_plan_2026-10-15.md`),
> so the priority below, which ranks shops by whether they can supply a rating, is
> superseded. Kept as the record of the search.

Owner decision (2026-10-13): PicWise is for the **UK and the US**. They asked for one
large advertiser per mega-category, to search for on the Awin platform, preferring
programmes that need no approval.

**What is verified and what is not.** The two facts at the top are researched. The
advertiser names are candidates from knowledge, to be searched for in Awin's own
directory -- this session cannot see the platform, and which programmes auto-approve
changes constantly and per publisher. Treat the list as a search list, not a roster.

## Two facts that change the plan

**One account covers both markets.** ShareASale closed on 6 October 2025 and merged
into Awin; its accounts moved across. So US advertisers are reachable from the Awin
account the owner already has, and the "second network" question is answered for the
US: there is nothing to join.

**Best Buy's official API returns the rating.** Its Products API carries
`customerReviewAverage` and `customerReviewCount`, and they can be used as filters --
its own documentation shows a query for products scoring at least 4 with more than 100
reviews. That is the first clean, official product-rating source found in this whole
search, and it is independent of any affiliate feed. Key access needs checking at
`developer.bestbuy.com`: sources disagree between free registration and an approved
application, and commercial use may need a partner agreement.

It covers electronics, appliances, computers, audio, video, cameras and phones -- which
is most of what `comparison_rules` puts in the `spec` and `rating` classes.

## Priority: the seven categories where a rating is the only signal

These are `rating` class in `docs/picwise_comparison_rules.md`: quality is real and no
feed number measures it, so without a rating PicWise cannot honestly pick a best.

| Mega-category | UK | US |
| --- | --- | --- |
| `home_appliances_laundry_climate` | **AO.com**, Currys, Appliances Direct | **Best Buy**, Home Depot, Lowe's, AJ Madison |
| `kitchen_cooking_household` | **Lakeland**, ProCook, Robert Dyas | **Williams Sonoma**, Sur La Table, Wayfair |
| `computers_office_peripherals` | **Ebuyer**, Scan, Box.co.uk | **Newegg**, B&H, Dell, Lenovo |
| `audio_video_gaming_cameras` | **Richer Sounds**, Wex Photo | **B&H**, Adorama, Crutchfield |
| `power_tools_workshop` | **Screwfix**, Toolstation, Machine Mart | **Acme Tools**, Northern Tool, Zoro |
| `health_wellness_safety_devices` | **Holland & Barrett**, Boots | **Walgreens**, CVS, iHerb, Vitacost |
| `beauty_grooming_personal_care` | **Lookfantastic**, Cult Beauty | **Ulta**, Dermstore, Sephora |

## The other eight that carry a best

| Mega-category | UK | US |
| --- | --- | --- |
| `phones_mobile_accessories` | Currys, Samsung UK | Best Buy, Motorola, Verizon |
| `car_parts_service_maintenance` | **Euro Car Parts**, Halfords, GSF | **AutoZone**, Advance Auto Parts, CarParts.com |
| `tyres_wheels_car_accessories` | **Blackcircles**, Kwik Fit | **Tire Rack**, SimpleTire, Discount Tire |
| `moto_bicycle_mobility_gear` | Tredz, Evans Cycles, SportsBikeShop | **REI**, Jenson USA, Backcountry |
| `hand_tools_consumables_measuring` | Screwfix, Toolstation, RS Components | **Zoro**, Grainger, Northern Tool |
| `garden_outdoor_repair_building` | **B&Q**, Wickes, Crocus | **Home Depot**, Lowe's, Tractor Supply |
| `baby_kids_pets_sports_outdoor` | **Decathlon**, Pets at Home, JoJo Maman Bébé | **Chewy**, Petco, Dick's Sporting Goods |
| `furniture_living_storage_smart_home` | Wayfair, Dunelm, Furniture Village | Wayfair, Overstock, Home Depot |

## The three that are not urgent

`clothing_apparel_workwear`, `footwear_shoes_sneakers_boots` and
`jewelry_watches_bags_fashion_accessories` are `fit` class: there is no best pair of
shoes and no best bag, so a rating changes nothing there. PicWise shows four different
answers and a "see more" button. Next and M&S, Schuh and Clarks, H Samuel and Watch
Shop in the UK; Macy's and Nordstrom, Zappos and DSW, Blue Nile in the US -- when
there is time, not first.

## What to expect on approvals

Large advertisers almost always need approval; the programmes that take anyone are
usually small shops -- which is exactly the kind this feed already proved has no
ratings. So the waiting is probably not avoidable. Applying to all of them at once and
waiting in parallel costs nothing.

## The cheapest decisive test

Three applications, not eighteen: **AO.com**, **Screwfix** and **Decathlon** for the
UK, or **Best Buy**, **Home Depot** and **Chewy** for the US. Each is large, each has
thousands of product reviews on its own site, and the three cover three different
engines. If none of them sends `average_rating` in its Awin feed, then Awin does not
pass ratings through at all, and that is established with three applications instead
of eighteen. `tools/check_awin_feed.py` answers it in one run: its VERDICT block says
on the first line whether any shop in the feed sends a rating.

## What is still open after this

Even a feed full of ratings leaves two decisions the owner has to take, recorded here
so they are not discovered late:

- **The minimum review count.** A 5.0 from two buyers is not better than a 4.6 from
  nine hundred, and ranking by the average alone would prefer it.
- **A four where one product has no rating.** Ranking needs a rule for it, and
  `ANTI_FAKE_TRUST_RULES` requires the gap be declared rather than filled.
