# PicWise — session handoff

Current state for whoever picks the project up next. Updated 2026-10-29 (item 1 measured).
`PROGRESS.md` is the chronological log; this file is the "where are we now".

## Next conversation (from 2026-10-28): finish 1, 2, 3 -- start here

The owner (28/10): «Θα ξεκινήσουμε με το 1 2 3 σε νέα συζήτηση», and **no deployment
until these three are finished**. The work is on `ccr-1361f1a7-dcpo60` (pushed; the
conversation's own branch `ccr-8eb9b420-958wtr` kept equal); bring it in first. Each is
measured on a copy of the server's catalogue and shown to the owner before it is built.
The owner's rules, unchanged: Greek, short, plain words; say what you found before
building anything; nothing on `main` without their explicit «ναι»; never ask for the
feed link (it holds the key); secrets only in GitHub's or Vercel's secrets; nothing in
Supabase without asking; never open an Awin tracked link from a session or a bot; never
propose contacting the shops; no second bot round the same day without their word;
commission never a criterion; no fake data; Amazon removed for good; the repository is
public, so no server name, address, host key or link in a log or a file.

1. **The 3,075 engagement rings read as accessories** (Finediam, its shelf of rings):
   **built and measured on 2026-10-29, nothing deployed; waiting for the owner's word on
   "For"** (section "Now (2026-10-29)" below). The English "with" (owner, 29/10: «Η
   διορθώσεις πρέπει να αφορούν αγγλικό λεξιλόγιο»: English words only, no «με») and the
   metals after a name make 2,303 of them rings; 772 stay accessories, 756 of them naming
   the ring after a "For" ("Eternal Single Row For Center Oval Diamond Engagement Ring"),
   which the rule leaves alone ("Filter for Coffee Machine"). Put to the owner: measure
   "for" too, only on a shelf that names the kind.
2. **Choices for a general word** (owner: «Το search όταν του βάζεις καλώδιο πρέπει να
   συμπληρώνει προτάσεις τι καλώδιο ζητάει: καλώδιο τηλεόρασης, καλώδιο φόρτισης,
   καλώδιο ίντερνετ ... το ίδιο με όλες αυτές τις γενικές λέξεις»; rules word by word lead
   nowhere). Built from the catalogue itself, each night, for every general word alike:
   the shops' shelves under it (Google's taxonomy) and the words titles put before it
   ("HDMI cable", "aerial cable"), only those that find products, the largest first; in
   the search box and above the results ("What kind of cable?"), in the buyer's language:
   the site is English for the UK and the US (`<html lang="en">`, en-GB/en-US), so the
   shelves' English names; Greek names (Google's `taxonomy-with-ids.el-GR.txt`, by id, not
   yet in `data/taxonomy_sources/google/`) only for a query in Greek. Today's pieces:
   `src/picwise_providers/suggestions.py` (the box's
   suggestions by prefix, from the catalogue, `/suggest.json`), the older
   `src/picwise_search_memory/broad_query_suggestions.py` (from the vocabulary, not the
   catalogue). The cables of 28/10: 3,853 now "cable" (3,270 fabric extension leads,
   coaxial and aerial, audio, 168 saying "USB"), 196 charging cables. **Measured on
   2026-10-29, not built into the search** (section "Now (2026-10-29): item 2" below;
   owner, 29/10: «η ίδια λογική ένας προγραμματισμός για όλες αυτές τις αναζητήσεις ...
   δεν θέλω να διορθώνουμε ένα-ένα λέξη κλειδί»): 81 of the 116 kinds of 50 or more
   products get choices; put to the owner: build it, measured again before any
   deployment.
3. **The cap of 15% applied:** `catalogue_cap.cap_catalogue(..., kept_before=...)` is
   built and measured (run `40762760684`: 164,144 kept, at most 24,621 a category), not
   called. To do: the nightly preparation (`tools/prepare_catalogue.py` ->
   `state.prepare_feed_catalogue`) calls it and keeps the kept keys on the server for the
   next night (`kept_before`); measured first.

Then the deployment (question 1: `server-deploy.yml`, the round and the setup take the
host key from a login's first step, as `server-night.yml`; editing it deploys, so the
owner may need to set "Accept edits"), then HTTPS and the domain. How to measure without
deploying: commit code with `[skip actions]` in the message (`src/**`,
`deployment/server/**` start `server-deploy.yml`), check no run started, then push a
change of `.github/workflows/server-cap.yml` alone, which copies the server's catalogue
to GitHub's runner and runs `print_cap.py`, `print_prices.py`, `print_kind_changes.py`.
To see one change of the rules on its own, list the commits before it in the workflow's
`RULES_STEPS` (each read from a worktree by `deployment/server/kinds_of.py`). Tests one
module at a time (`test_picwise_learning_stage7b` takes 27 minutes).

## Now (2026-10-29): item 2, the choices for a general word (measured)

The owner (29/10): one logic for every general word, never keyword by keyword; «Ναι» to
measuring it on the server's catalogue the same way as item 1. Built and measured, not
called by the search: `src/picwise_providers/kind_choices.py` (`measure_kind_choices`;
tests `tests/test_picwise_kind_choices.py`, 5), `deployment/server/print_choices.py`
(tests `tests/test_picwise_server_print_choices.py`, 2), a step of `server-cap.yml`.

- **How:** every kind of 50 or more products (by this checkout's rules) is grouped three
  ways: the words its titles name it with -- the word right before the noun of its name
  and that noun as written ("hdmi cable", "sofa bed" under sofas, "zip-up hoodie"),
  weak names read too since the kind is known; its narrower kinds; its shops' narrowest
  shelves. A word before the nouns of 8 kinds or more says how a product is, not which
  kind ("gaming", "knitted", "football" on 29/10), and is no choice; nor a number, the
  brand or a connective. A choice from 20 products, whatever its share (first run
  `40868599997` asked 5% of the kind, and "cable" got no choice: one shop's fabric
  extension leads are 81% of cables). General: 2 choices of one way.
- **What it found (run `40869626869`, the catalogue of 29/10 04:21 UTC):** of 116 kinds
  of 50+ products, 81 general (57 by words, 62 by shelves). Cable: extension 3,291,
  charger 67, charging 56, braided 54, HDMI 42, audio 38, LAN 26, USB 24 (and shelves
  HDMI, Network, Audio Cables). Table: side 774, coffee 496, console 273, dining 257,
  dressing 61, nesting 48. Lamp: pendant light 716, table lamp 472, floor lamp 125,
  ceiling light 124, wall light 90, chandeliers. Dress: midi, mini, maxi; earrings:
  stud, hoop, diamond, drop; bracelet: tennis, link, chain; camera: mirrorless,
  compact, instant, digital; curtains: eyelet, pleat, blackout; socks, mattresses,
  beds, sofas, hats, gloves, saunas alike. Noise, mostly clothes with prints and
  shops' own words: "do shirt" 764, "funny shirt", "rude shirt", "robertson hoodie",
  "cup shirt", "color ring" 3,906, misspellings ("engagment ring" 504); the singular
  cut short ("caravan mattresse", "wine glasse": `_singular` strips one "s"). The
  shelves of several shops name one thing twice ("Dog Food", "Non-prescription Dog
  Food"), so as choices they are weaker than the words. Not general: keyboard, mouse,
  desk, backpack, perfume, motherboard, wall clock and others with one group.
- **Wrong kinds the shelves showed (to fix, told first):** vitamin and toothpaste tablets
  ("Vitamins & Supplements", "Toothpaste" shelves) and tablet cases read as tablet
  computers; basketball hoops (67) read as footballs.
- **Proposed next (owner's word first):** build it into the search -- the choices of the
  buyer's kind above the results ("What kind of cable?") and in the box's suggestions,
  the largest six, each a search that finds products -- computed each night with the
  catalogue, in English (Greek names only for a Greek query, from Google's Greek
  taxonomy); measured on the server's catalogue again before any deployment.

## Now (2026-10-29): item 1, the engagement rings

The owner: «Ξεκινάμε με το 1»; then «Ναι» to pushing to `ccr-1361f1a7-dcpo60` for the
measure (code with `[skip actions]`, then `server-cap.yml` alone; no run but the measure
started, checked each time). This conversation's own branch `ccr-4f9ef4ee-j1nafx` is
kept equal by merges (a force-push of it was refused; the work branch stays linear).
The work branch had moved to `31e2ee4` (the previous conversation's docs commit on item
2's language), so this work sits on it.

- **Built** (`src/picwise_nlu/concept_understanding.py`, tests
  `tests/test_picwise_kinds_named_after_with.py`, 5): a title that names no kind before
  its first "with" (or "w/") is the kind it names after it, past one "with" or more,
  when the shop's narrowest shelf names that kind too (`_cut_past_with`, read only by
  `_title_named_head`, i.e. when neither the type nor the category gives a kind); after
  "for", after an accessory's noun before the kind, or on no such shelf it is still an
  accessory. English only (owner, 29/10). Metals right after a product's name
  (platinum, palladium, titanium, tungsten, sterling; `_METAL_TAIL_WORDS`) describe it,
  as gold and silver did; read only there, since elsewhere a metal names a line ("Dr John
  Titanium 15KG", dog food, became doubtful when they were read everywhere).
- **The measure** (`deployment/server/kinds_of.py`; `print_kind_changes.py --step`, whole
  titles, and the word after a kind's name for the accessories on its shelf; tests
  `tests/test_picwise_server_print_kind_changes.py`, 3; runs `40858411220`,
  `40862093722`, `40862883104`, the catalogue of 29/10 04:21 UTC, 525,386 shown): **the
  "with" rule alone 2,329 (0.44%)**: 2,271 Finediam engagement rings accessory -> ring;
  42 Finediam pendants "with Diamond Accents Necklace (Without Chain)" accessory ->
  necklace (the lexicon has "pendant" as a name of necklace, and they sit on its
  necklaces shelf; told to the owner); 7 Geepas mixer grinders -> mixer; 6 baby tees ->
  t_shirt; 2 pendant lights -> lamp; 1 utensil set with a knife set -> knife_set.
  **The metals 1,891 (0.36%), all Finediam rings**: 1,823 doubtful -> ring ("... 3 Stone
  Engagement Ring Platinum - Sterling Silver / 0.50 Carat"), 36 of no kind -> ring, 32
  accessories -> ring. Rings 143,860 -> 148,022 in all. Of the 3,075: 2,303 rings, 772
  still accessories on the ring shelf, the word after the ring's name "9k/18k" 756 —
  these name it after a "For" ("Refined Solitaire For Peg Head Round Diamond Engagement
  Ring — 9K/18K Gold & Platinum"). The far prices with the kinds read so: 7,104 (ring
  5,284, Finediam's luxury and cheap ends as before). Every change since the deployment
  of 26/10: 9,406 (1.79%).
- **Tried and left out (probed on the measure's titles, not measured):** the noun before
  "with" as the product ("Pendant with ... Necklace") would not keep the pendants out
  (pendant is the necklace's own word) and would cost the mixer grinders and the
  pendant lights.
- **Checks:** the kind-related modules one at a time (116 pass; the two known failures,
  `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`, fail on `cb40587` too); the
  misspelling benchmark the same (93.8%, 0 wrong); `actionlint` could not be fetched
  here (refused), the workflow was parsed and its kind steps run locally instead.

## Now (2026-10-27/28): the server's host key, the cap, the far prices, the kinds

The owner's «Ναι» (26/10, evening) to two things: writing straight to `ccr-1361f1a7-dcpo60`
(this session's own branch, `ccr-8eb9b420-958wtr`, is kept equal to it), and a small
read-only look at the night's round. Owner's rules unchanged (section below).

- **The look, built:** `.github/workflows/server-night.yml`, run when it is pushed to
  `ccr-1361f1a7-dcpo60`: from each timer's last start (`LastTriggerUSec`, kept across a
  reboot), the result and times of `picwise-shops.service` and `picwise-prepare.service`,
  the bot's own lines and the preparation's summary; then `print_shops.py` and
  `print_kinds.py`, as after a deployment. It starts no round and changes nothing. Its
  script goes to the server on stdin (`ssh picwise 'bash -s' <<'EOF'`), so no quote in it
  can close the command. Checked here: `actionlint` 1.7.12, `bash -n`, a dry run with
  stand-in commands; its connection step and its last three are `server-shops.yml`'s,
  unchanged. To read another night: change its "Night read" date line and push.
- **What it found (the owner's «στείλτο», 27/10 09:00 UTC, commit `bde4cdd`, run
  `40477603160`): nothing of the night.** Its first step stopped at the identity check:
  "the server does NOT match the pin (reinstalled, or not our server)". The pin it
  computed is not `.github/server-host-key.pin` (taken 25/10); the deployment of 26/10
  (run `40355492889`, connected at 16:04 UTC, done 16:16) still matched it. The step
  stopped before any login: nothing was sent to the server. The night's round of 27/10
  is unread, and whether it ran is not known.
- **What it can be:** the VPS reinstalled, or booted in rescue mode (both change the host
  key); the `SERVER_SSH_KEY` secret changed (the pin is an HMAC under a key derived from
  it, so a new deploy key changes the pin of the same host key); `SERVER_HOST` changed;
  or another machine at the address.
- **What the owner checked (27/10, screenshots; the server's name and address are in
  them and are written nowhere):** the VPS page says Status "Active", Boot "LOCAL" (not
  rescue), "Ubuntu 24.04", VPS-4 2027, London; no OVHcloud email of a reinstall or rescue.
  One OVHcloud email, "Notification of connection to your OVHcloud account", dated
  2026-10-26 14:09:47 (OVHcloud's clock), before the deployment that still matched the
  pin; the owner does not remember logging in, and was advised to change the OVHcloud
  password and turn on two-step verification (My account → Security). In GitHub's
  secrets, `SERVER_HOST` and `SERVER_SSH_KEY` were last changed "2 days ago" (25/10), so
  they are not the cause.
- **The proof, built (owner's «Ναι», 27/10):** `server-night.yml`, which sends the
  server no secret, no longer stops at a changed pin: it asks the server to seal a random
  nonce under the feed link (`.github/scripts/feed_seal.py`, HMAC-SHA256; GitHub from the
  `AWIN_FEED_URL` secret, the server from `/etc/picwise/picwise.env`); only the nonce goes
  and only the seal comes back. A server whose seal is GitHub's is read: why its key
  changed (boots, the host keys' dates, cloud-init, the updates' reboots), the SSH logins
  since 26/10 16:00 UTC without addresses, then the night. Any other is not read, and the
  failure is sorted without printing the server's words. The deployment and the round
  keep the strict pin. Tests: `tests/test_picwise_server_feed_seal.py` (5); dry runs of
  every case with stand-in commands; `actionlint`.
- **What the proof found (runs `40489651144` and `40489927183`, 10:35-10:37 UTC): not
  read.** The new key's pin is the same in all three runs (the key is stable since 09:00).
  Port 22 says `SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.20`, an Ubuntu 24.04. But the login
  for the seal was shown **another key than the one the same address had shown a second
  before** ("Host key verification failed"), so it stopped before logging in. At least
  two different host keys answer at the server's address: two machines on it (an address
  conflict at OVHcloud), or something in between. A reboot alone would give one new key,
  not two.
- **The look that never logs in (owner's «Ναι»; `.github/workflows/server-keys.yml`, run
  `40501323803`, 12:07 UTC): our server is there.** Four tries, the order changed each
  time: **a key scan (`ssh-keyscan`) is shown the morning's key every time, and a login's
  first step (an `ssh` client offering no key or password) is shown our pinned key of
  25/10 every time.** Not two machines taking turns: the key depends on how the address
  is asked. Whoever shows the pinned key holds its private half, made on our server on
  25/10, so real logins reach our server. Yesterday's deployment was shown the pinned key
  by `ssh-keyscan` too, so what answers a key scan with another key began in the night:
  not explained yet (something on the server since the night's updates, or on the way).
  Every workflow takes the key to compare with the pin from `ssh-keyscan`, so each stops
  there although a login would reach our server.
- **Built (owner's «ναι κάνε»):** `server-night.yml` takes the key from a login's first
  step and compares it with the same pin (as strict: every connection then accepts that
  key only); a key scan's key is only reported; when it differs, the server is asked what
  answers a key scan. The deployment (`server-deploy.yml`), the round
  (`server-shops.yml`) and the setup still compare `ssh-keyscan`'s key, so **they stop at
  their first step until they take the key the same way** (put to the owner; editing
  `server-deploy.yml` deploys).
- **What it found (run `40504119821`, 12:29 UTC): our server is untouched.** It matched
  the pin; a key scan was shown the morning's key again. From inside: up since
  2026-10-25 11:04:58 UTC (no reboot since the setup); the host keys written 25/10 09:37
  by cloud-init, the same instance-id since, no regeneration; the ed25519 key on disk is
  the pinned one; one `sshd` (socket-activated) on 0.0.0.0:22 and [::]:22; no rewrite of
  port 22 (nftables holds ufw's rules and fail2ban's reject set only); the night's only
  update `libbrotli1` (27/10 06:23); since 26/10 16:00 UTC 13 SSH logins, all with the
  deploy key, none on the console. So what shows a key scan another key is not on our
  server: something on the way answers that kind of connection (not known what; it gets
  no secret, and a login with any other key than the pinned one is refused by every
  workflow). The server's nightly work does not need GitHub: the timers run on it.
- **The night's round of 27/10 (the first by collections):** the bot 03:40:00-03:53:35
  UTC, success: 54 shops, 413 requests; the file knows 65,031 products (59,996 with a
  type, 29,460 sold out; 58,728 / 53,699 / 25,041 on 26/10). Back to the Office: its
  catalogue to the page limit again (about 100 of its 200 requests), then **collections
  38 of 1,338**: 30,282 of its 95,050 products known; at this pace a whole pass takes
  about 35 nights (put to the owner: page the catalogue's first 25,000 less often, or
  more requests for it). Finediam: Shopify answers 500 at page 23 again (5,500 known).
  Juicy Couture UK: no shop address in its rows. Pro Espresso: its robots.txt redirects to
  another site, so it is not read. The preparation 04:17:02-04:27:41 UTC, success:
  1,124,205 rows, **524,335 shown** (+885), 81 shops, peak memory 7.9 GB, 640 s. Back to
  the Office **6,135 shown** (5,252 on 26/10); rows given their shop's type with its kind
  **24,974** (20,402), naming none 13,218; by barcode 1,128 (InStock UK 1,061); the
  shop's sold-out holds 43,509 (the feed called 142 of them in stock). The cap,
  measured: by shop Finediam 68.7%, InStock UK 17.8%; by aisle jewellery 72.7%; by kind
  ring 57.7%; kinds from at least 3 shops 94 of 256. The kinds' check: of 249,225
  products shown as a kind, the title names none of its kinds for 12,731.
- **The owner's word (27/10, afternoon):** the deployment, the round and the setup stay
  as they are for now («Το αφήνουμε όπως είναι»); no 400 requests for Back to the Office
  («δεν θέλω αυτή τη στιγμή 400 ελέγχους»). **The cap, decided in its aim:** a kind of
  like products (rings, watches) never more than 15% of all products, so that no shop
  makes the site look like one kind of shop to Google, the server's room is not spent
  on a few kinds but spreads to others little by little, and each search looks complete;
  «πρώτα από όλα να έχει καθαρή και ποιοτική πληροφορία», a satisfying volume, not a
  huge one. Put to the owner how it counts: each product under its kind, or its shop's
  narrowest shelf when it has none (275,110 shown have no kind, most jewellery among
  them); within a group over the cap the clean rows first (barcode or brand + model code,
  an image, real stock), those sold by more than one shop first, spread over the price
  range, the same ones each night; measured with that rule before anything is cut. It
  reaches the server only by a deployment, which needs the change the owner left for now.
- **The cap, chosen (owner, 27/10, after «βοήθησέ με γιατί έχω μπερδευτεί»):** 15% **per
  category**, the first two levels of the shop's Google shelf ("apparel & accessories >
  jewelry", watches included), not per department (too coarse: it would cut clothes and
  shoes with the jewellery) nor per kind (many jewellery kinds of 15% each could still
  make the site half jewellery). The size is worked out at once so that no category
  keeps more than 15% of what all keep, each night from every product a card can show
  (the owner asked whether it would keep cutting: it does not); the night before's kept
  ones are the next night's starting point (owner: «κοιτώντας πάντα το χθεσινό σαν
  αφετηρία»), more products a larger cap, fewer a smaller one in proportion. Built:
  `src/picwise_providers/catalogue_cap.py` (inside a category its places shared fairly
  over its kinds, a shelf for a product without one; inside a kind the clean ones first,
  those in more than one shop first, spread over the prices; tests
  `tests/test_picwise_catalogue_cap.py`, 12), `deployment/server/print_cap.py` (tests
  `tests/test_picwise_server_print_cap.py`, 3), `read_prepared_catalogue_to_measure`, and
  `.github/workflows/server-cap.yml`, which measures a copy of the server's catalogue on
  GitHub's runner. **Not called by the preparation: nothing shown changes.** The code was
  pushed with `[skip actions]` (commit `efc5ac0`), since `src/**` and
  `deployment/server/**` would start a deployment, which the owner left as it is.
- **What the cap would keep (run `40511286783`, the catalogue of 27/10 04:21 UTC):** of
  524,335 in 171 categories, **164,176**, at most **24,626** a category; over it only
  jewellery (380,984) and clothing (28,427). After it: clothing 15.0%, jewellery 15.0%,
  decor 6.6%, food 5.3%, shoes 4.7%, vehicle parts 4.3%, hobbies 4.1%, the shops' own
  categories 3.9%. Inside jewellery about 3,185 each for the shelf "rings" (products with
  no kind), ring, earrings, the shelf "body jewellery", bracelet, necklace and the shelf
  "charms & pendants"; all 1,725 watches; prices kept 0.99-109,787.50 (all 0.50-112,137.50),
  middle 1,108.50 (1,566.43). Clothing: t-shirts 7,266 -> 4,142, socks 4,818 -> 4,141, the
  rest whole. Of the 49,252 kept in the two, 48,796 with an identity, an image and a stock
  state that varies; 218 sold by more than one shop. By shop: Finediam 360,127 -> 18,891
  (11.5%), **InStock UK 93,406 -> 91,219, 55.6% of what is kept**, MonsterPiercing 16,030
  -> 3,278. Found: rings count twice (the kind and the shelf of rings the kind reading
  leaves without one), so they take two shares; to be one group before the cap is
  applied. Put to the owner: a limit per shop as well (InStock UK would be over half).
- **No limit per shop (owner, 27/10: «Να μην εφαρμοστεί πλαφόν ανά κατάστημα»).** The owner
  then asked about price: what commission a 99p product leaves, whether it is poor or a
  piece of a pack, and that about 100,000 is too much. Answered: commission never enters
  a choice (PROJECT_RULES §4, concept §14) and the cookie earns on the whole basket; no
  price ban; proposed trimming each kind's cheapest and dearest 2% inside the cap, after
  a measure. **The measure (owner: «Κάνε τη μέτρηση»; `deployment/server/print_prices.py`,
  tests `tests/test_picwise_server_print_prices.py` (2), run `40533880205` in
  `server-cap.yml`):** of 524,335 (GBP 523,978, EUR 327, USD 28, DKK 2), under 1.00: 220
  (0.04%; hobbies 58, books 49, food 41; InStock UK 167, Lets Buy Books 48; 13 name a
  pack; penny sweets "10p each", stickers); 1.00-2.00: 1,165 (InStock UK 1,121; party
  invitations, mini bath bombs; 82 name a pack); 10,000 and over: 28,436 (5.4%; Finediam
  28,212, then Steam & Oak 108, SafeFort 75, Back to the Office 33); 50,000 and over: 106
  (diamond necklaces to 112,137.50; network software licences to 125,474.99). Far from
  their kind's middle price (516 kinds and shelves of 20 or more): under a tenth 4,888
  (cheap bracelets against a middle of 3,099 the diamonds set), over ten times 7,229,
  among them wrong kinds ("Okemia Mirror" 1,929 read as a toy; "Satin Bag Diamond
  Earring" read as a bag; a full pallet of AdBlue). Inside the cap the cheapest 2% of
  rings run to 358.60 and of bracelets to 125: trimming them would cut the ordinary
  affordable jewellery, since Finediam sets the prices. Put to the owner: no price rule
  and no trim; the ends are few and real; a price far from the kind's middle used as a
  check for wrong kinds.
- **The owner's «Ναι» to no price rule, no trim, and a far price as a check for wrong
  kinds; rings as one group (run `40535514183`, code `0958bd9` with `[skip actions]`):**
  `catalogue_cap.joined_parts` puts a shelf whose last level names a kind of the same
  category under that kind. The cap's totals are unchanged (164,176; 24,626 a category);
  inside jewellery 14 groups, ring 310,572 -> 3,770 (one share, not two), earrings,
  bracelet, necklace, the shelves "body jewellery" and "charms & pendants" 3,770 each,
  all 1,741 watches; kept prices 0.99 / 1,050.00 / 109,787.50; 48,820 of 49,252 kept with
  all three clean signs. `print_prices.py` now lists the products priced far outside
  their kind's usual prices (beyond 1.5 times the middle half's spread on a ratio scale,
  and ten times off the middle price): **9,174 in 130 of 504 kinds and shelves**; real
  wrong kinds among the furthest (Harvia sauna stones 60 read as "sauna"; Living with
  Luxury's cabinets 1,872-4,103 on its shelf of "cabinet doors"; children's snap bands
  0.50-1.50 as "bracelet"; balloons on a balloon shelf whose middle is 99; tablecloths on
  a "kitchen & dining" shelf whose middle is 1,170); but noisy where a kind mixes cheap and
  luxury shops: 5,755 are rings (usual 147.67-18,357.94, set by Finediam), earrings 913,
  bracelets 344; and "charging_cable" has a middle of 95 (phone and car charging cables
  read as one kind). Put to the owner: compare within the same shop to cut the noise,
  then fix the reading rules for what it finds, each fix told first.
- **The check compares within the shop too (owner's «Ναι», 27/10; code `bc8485a` with
  `[skip actions]`, run `40536481871`):** a product is listed when its price is far
  outside its kind's usual prices and its own shop's for that kind, when the shop has 10
  or more; counted by shop and kind too. **7,143 in 110 kinds** (9,174 before); InStock
  UK's cheap rings no longer listed. Most are real luxury or cheap ends, not errors:
  Finediam's rings 5,304 (to 61,447.50), necklaces 91, pendants 52; MonsterPiercing's gold
  body jewellery 462; penny sweets 194; Lets Buy Books at 0.49 51; Off-White Nikes at
  5,100.20. **Wrong kinds found, fixes put to the owner:** earring backs read as
  "earrings" (Finediam 113, "LOX Locking Earring Backs"); aerial and satellite coaxial
  cables as "charging_cable" (InStock UK 265, "Maplin F Type Connector ... Coaxial
  Cable"); sauna stones as "sauna" (Steam & Oak); photo frames with a mirror as "mirror"
  (InStock UK 19). Also the shop's own category: Living with Luxury's cabinets on its
  "cabinet doors" shelf (not ours to change).
- **The four rules fixed (owner, 27/10: «Διόρθω τους κανόνες και άντε να δούμε πού θα
  καταλήξουμε τελικά»; code `7354a52` with `[skip actions]`, nothing deployed):** "backs",
  "backing(s)" end a title's lead as an accessory's noun (`_LEAD_ACCESSORY_NOUNS`: earring
  backs filed under "Earrings"); a plain "cable" is a new, broader kind `cable` (καλώδιο),
  and `charging_cable` only what a title or a shelf names as a charging, charger, USB,
  USB-C, Type-C, Lightning or iPhone cable, a cable too («καλώδιο» and "cable" find every
  cable, «καλώδιο φόρτισης» and "usb cable" only those); "stones" right after a kind's
  name make it something for it (`_MODIFIER_TAIL_WORDS`: sauna stones; not "stone", a
  colour as often); a new kind `photo_frame` (photo or picture frame, κορνίζα), named last
  in a title (`_NAMED_LAST_KINDS`: "Glass & Mirror 6x4 Photo Frame" is a frame); `cable`
  and `photo_frame` compare as charging cables and mirrors did (length, size; no best).
  Tests: `tests/test_picwise_kinds_from_the_far_prices.py` (10, failing on the old
  rules); one changed (`test_the_first_shelf_that_names_a_product_decides`: a shelf
  "cables" gives a cable); the kind, query, search and catalogue modules pass one at a
  time (`test_picwise_learning_stage7b` takes 20 minutes); the misspelling benchmark the
  same (93.8%).
- **Where it ends (runs `40759989550`, `40761504364`, `40762760684`, the catalogue of 28/10
  04:22 UTC, 524,436 shown; `deployment/server/print_kind_changes.py`, tests
  `tests/test_picwise_server_print_kind_changes.py` (2): each product read again with this
  commit's rules against the kind stored, the words each change's titles share, then the
  check of far prices again):** **5,148 change kind (0.98%)**: 3,853 are no charging
  cables but cables (InStock UK 3,730: 3,270 Lola's Leads fabric extension leads, Maplin's
  coaxial and aerial cables, 150 liquorice "cables" among the sweets; Back to the Office
  122: audio and fan cables; 168 say "USB", some perhaps phone cables now only "cable");
  charging cables 4,049 -> 196; 1,254 photo frames (1,238 had no kind: Kenro, Walther);
  Finediam's 18 LOX earring backs an accessory (doubtful before); Steam & Oak's sauna
  stones an accessory; 6 mirrors photo frames; 16 frame "collections" doubtful, 6
  accessories (a frame "on Stand", a photo mount, a frame clock). The far prices: 7,141
  -> 6,995; charging cables 265 -> none (the same cheap cables now far below all cables'
  middle of 102, set by the extension leads: 273, no wrong kind); mirrors 21 -> 15; the
  sauna stones out; Finediam's earrings 113 -> 95, the furthest now a 46,319.00 diamond
  earring.
- **Found on the way:** the earring backs never answered a search for earrings (doubtful);
  the cap counted them as earrings by their shelf (`catalogue_cap.joined_parts`), and the
  check with it. The check now leaves an accessory on its shelf (`b2ce892`, `337047c`); the
  cap still joins it, as chosen: with a share of their own, the accessories on Finediam's
  shelf of rings would all be kept. **And those 3,075 "accessories" are engagement rings**
  ("2.00 Ct Lab Grown 3 Stone With Side Halo Diamond Engagement Ring Platinum"): the
  title says "With" before the ring's name, and a kind named only after a purpose word is
  read as an accessory of it (`_head_of_text`, meant for "filter for coffee machine"), so
  no search for a ring shows them (before 27/10 too). Put to the owner: after "with" (not
  "for"), a kind the title names when nothing before names one is the product, measured
  first. A few more accessories are real products (4 microphones with a "mount", 3
  bedside tables "Storage Organiser"). The rules reach the server only with a deployment
  (question 1).
- **The owner's answers (29/10) to an honest assessment** (asked: «πες την αλήθεια»): the
  catalogue's gaps -> other affiliate networks will be added; the decision rests on the
  middle price; the kind reading is finished when every kind defined has products and has
  been debugged once; what users do does not matter now (there are none), what Google does
  at launch does; there is a domain of our own, and the rules leave no room for breaking
  Google's rules or data quality; the system is to keep itself up to date; everything in,
  debugged in bulk (not a few kinds first); the creed: volume, quality of information,
  truth, an architecture right for SEO. Answered: the middle price is a sound basis if it
  is the median of a kind read right, from several shops, per size where size matters
  (the rings' middle is Finediam's, the cables' the extension leads', the charging cables'
  the EV cables'); keep everything in the search, but let Google index only the kinds that
  pass a bar (enough products, shops, debugged); Search Console from the first day; an
  alarm when a night fails, before launch. **Decided (owner, 29/10): «Θα στήσουμε
  ολοκληρωμένα και θα δώσουμε στη Google αυτά που θέλουμε τμηματικά»**: everything is
  built whole and in the search; Google is given what the owner chooses, part by part.
  The gate for it exists for the buying pages (`src/picwise_buying_pages/index_gate.py`,
  `docs/pickwise_roadmap_step6_quality_index_gate.md`: index, noindex, hold for review);
  what it needs is a bar per kind (products, shops, checked) and the owner's choice of each
  part.
- **The owner's word (28/10): no deployment until what was started is finished** («Δεν
  προχωράμε σε ανάπτυξη μέχρι να ολοκληρώσουμε αυτά που έχουμε ξεκινήσει»). Also: rules
  word by word lead nowhere; a general word ("καλώδιο") should be answered with choices of
  what it means (TV, charging, internet cable), for every general word alike. Started,
  in this order, each measured on a copy of the server's catalogue before it is built:
  1. the 3,075 engagement rings read as accessories (a kind named after "with" read as
     the product); 2. choices for a general word, from the catalogue itself (the shops'
     shelves, in Greek from Google's Greek taxonomy, and the words titles put before it),
     in the search box and above the results; 3. the cap of 15% called by the nightly
     preparation, the night before's kept list kept on the server. Then the deployment
     (question 1), then HTTPS and the domain.
- **Rules that hold:** the pin stays as it is (our server still holds that key; no new
  pin is needed); a workflow logs in only after a login's first step showed the pinned
  key; `server-check.yml` logs in with `accept-new` whatever the pin, so it is not run;
  the deployment, the round and the setup stop at their first step until they take the
  key from a login's first step too (the owner's word first).
- **Not affected:** the live site on Vercel (`picwise.subby.cloud`) does not depend on the
  server; the server's own site listens on 127.0.0.1 only.
- **Still waiting for the owner's word, as before:** the cap; the next kinds (mattresses,
  whiteboards, safety footwear, handheld mobile computers); HTTPS and the domain; the
  repository private; query logging from the server; 80 or 200 bot checks per shop.
  New (28/10): question 1 (the deployment, the round and the setup taking the key from a
  login's first step, so the fixed rules reach the server); a kind named after "with"
  read as the product (the 3,075 engagement rings).

## Before (2026-10-26, evening): the bot runs each night on the server

The owner ended the conversation of 26/10 with «Πάμε σε άλλη συζήτηση». Owner's rules,
unchanged: Greek, short, plain words; say what you found before building anything;
nothing on `main` without their explicit «ναι»; never ask for the feed link (it holds the
key); secrets only in GitHub's or Vercel's secrets; nothing in Supabase without asking;
never open an Awin tracked link from a session or a bot; never propose contacting the
shops.

- **Where the work is:** the branch `ccr-1361f1a7-dcpo60` (pushed, last `a6d4318`): bring it
  in first. `main` is still at `3608da0`: nothing of 25-26/10's server work is on it; pull
  requests #13 (this branch), #12 and #11 to `main` are open; merge none without the
  owner's «ναι».
- **The server deploys from this branch** (`server-deploy.yml`, on a push touching the
  site, the server files or `deployment/bot/**`). A session on another branch moves that
  trigger to its own; in the session's Auto mode the safety check refuses that change and
  its push as a production deploy, so ask the owner to switch the mode to "Accept edits"
  (the menu under the message box) and approve the push.
- **On the server now** (run `40355492889`, `9872f42` code): 523,450 products shown; So
  Divine out; the barcode brings in about 1,100 rows (InStock UK about 1,050); the bot
  (`picwise-shops.timer`, 03:40 UTC) feeds the preparation (`picwise-prepare.timer`, 04:17
  UTC) the shops' types and stock; Back to the Office 5,252 shown (782 before); 20,402 rows
  given their shop's type with its kind.
- **First thing to do:** read the night's round of 27/10, the first to read Back to the
  Office by its collections. Nothing prints it by itself: a deployment prints
  `print_shops.py` (the note's `shop_catalogues`, `balance`); the bot's own lines are in
  the server's journal (`journalctl -u picwise-shops.service --since today`), read
  through a small read-only workflow (as `server-shops.yml`, without starting a round) or
  by editing `server-shops.yml` to only print. Do not run a second round the same day
  without the owner's word.
- **Waiting for the owner's word:** the cap (measured only: by shop Finediam 68.9%, by
  aisle jewellery 72.9%; a 15% cap would keep about 97,000-162,000 of 523,450; the owner
  has not chosen a number or a grouping); the next kinds the shops' types name (mattresses,
  whiteboards, safety footwear, handheld mobile computers); HTTPS and the domain; the
  repository private; query logging from the server; 80 or 200 bot checks per shop.
  Decided: InStock UK only with its right rows (no second look); (a) "safe" as a number not
  needed (no title decides alone); Gigbain cancelled.

## Before (2026-10-26, later): the bot and So Divine built, then put on the server

The owner's answers to the three changes (26/10, later): «Γ ο κανόνας ισχύει μόνο για
προϊόντα που το κατάστημα δεν τους έδωσε καμία κατηγορία» (addition (c) agreed: the 275,000
shown with a shelf but no kind stay); «Θα κάνεις το 2 και το 3» (the bot for the shops
without a category, So Divine out); «το in stock συμμετέχει μόνο με τα προϊόντα που έχει
σωστά» (change 1, the second look at InStock UK, dropped: its rows without a category stay
out unless a barcode gives them one, and the bot never asks it); «Στα θέματα αντιστοίχισης
είχες αναφέρει για barcode ... για shopify φτιάξε τους μηχανισμούς σε αυτή τη βάση και ό,τι
έρθει σωστό ήρθε». Additions (a) "safe" as a number and (b) "enough" were not answered.
Owner's rules unchanged (see the section below).

- **Where the work is:** the branch `ccr-1361f1a7-dcpo60` (pushed): `claude/bold-allen-ljj9d7`
  brought in, plus this conversation's commits. `main` is at `3608da0`; nothing of this is
  on `main`, nor on the server.
- **Built and tested on the branch:**
  1. **So Divine out:** `eligibility.LEFT_OUT_SHOPS` (by the rows' merchant name, spaces
     and case aside); the feed gate blocks every row (`shop_left_out`, in the note per shop).
  2. **The shops' catalogues and the barcodes, applied** (`src/picwise_providers/shop_catalogue.py`,
     in `state._resolve_provider_feed_pipeline_uncached` before any row is judged): for a
     shop the bot's file knows (`PICWISE_SHOP_CATALOGUES`), its sold-out (all variants, or
     the one the address names; seen at most `STOCK_DAYS` = 3 days ago) holds a row as out
     of stock (`shop_stock`, read by `offer_health` with the feed's columns), never the
     other way; a row with no category from the feed takes its shop's type as type and
     category **only when the reading gives a kind the type names by itself** (the title
     may narrow it, "Vacuum Cleaners" + "Robot Vacuum Cleaner"; it never decides alone:
     "Designer", a type naming no kind, a title contradicting the type all leave the row
     held, as before). Then any row still without a category takes the category most
     rows with its barcode write, under the same rule (a barcode on more than 50 rows is
     ignored); this needs no file. Counted per shop in the note (`shop_catalogues`),
     printed by `print_shops.py`. A row with a category keeps its own.
  3. **The bot** (`deployment/bot/shop_catalogue_bot.py`, reusing the test's robots.txt
     reading and asking): `picwise-shops.service` by `picwise-shops.timer` at 03:40 UTC;
     `picwise-prepare.service` is ordered after it and reads its file. Shops: the note's
     with rows showable but for a category, plus those its file knows (so a shop whose
     rows got a category is asked again), never InStock UK or a left-out shop. Per shop:
     robots.txt, then `/products.json?limit=250&page=N`, 3 s apart or its crawl-delay, at
     most 200 requests a shop a round, 4 shops at a time, 25 minutes; a larger catalogue
     goes on next round where it stopped (a catalogue as large as Finediam's ~367,000 rows
     takes about 7 nights, Back to the Office's ~95,000 two). Kept on the server only
     (`/srv/picwise/shared/shops/catalogues.json.gz`, never Supabase), for the feed's
     products only: type, stock, sold-out variants, day seen; forgotten after 30 days.
     Prints shop names and counts, never an address; always exits 0.
  4. `deploy.sh` creates `/srv/picwise/shared/shops`, installs the two units and enables
     the timer; a deployment never asks the shops itself.
- **The server, from this branch (the owner's «Ναι», 26/10):** `server-deploy.yml` now
  runs on pushes to `ccr-1361f1a7-dcpo60` (also on `deployment/bot/**`) and prints the
  shops' timer; a session on another branch moves it to its own. In Auto mode the
  session's safety check refused that change twice as a production deploy, so the owner
  switched the session to "Accept edits" (the menu under the message box, "Auto") and
  the push went through (`a0d00ee`, run `40328993620`). The first round of the bot:
  `.github/workflows/server-shops.yml` (on a push of itself: `systemctl start
  picwise-shops.service`, then `picwise-prepare.service`, then `print_shops.py` and
  `print_kinds.py`), pushed only after a deployment ended, since both share the
  `server-setup` group in no set order. The nightly round runs at 03:40 UTC.
- **Pull request #13** (`ccr-1361f1a7-dcpo60` to `main`, opened by the app at 12:31 under an
  older title) is open, like #12 and #11: nothing is merged without the owner's «ναι».
- **On the server (26/10, 13:15-13:45 UTC):** deployment run `40328993620` (`a0d00ee`; its
  step "What runs on the server" failed on an apostrophe inside the quoted command, fixed
  in `1b2c4d9`): 1,123,995 rows, **518,108 shown**; So Divine 0 of 81 (`shop_left_out`);
  **the barcode brought in 1,081 rows** (InStock UK 1,041); peak memory 7.8 GB. **First
  round**, run `40329354654`: 54 shops, 331 requests, 8 minutes; the file knows 58,728
  products (53,699 with a type, 25,041 sold out). Then the preparation: **521,698 shown**
  (+3,590); Back to the Office 782 -> 3,973 shown. Of the 574,171 rows of those shops,
  124,265 found in their catalogue; **sold out by the shop 39,072, and the feed already said
  so for all but 188**: these shops' feed stock is nearly always right. Without a category
  121,574: **given their shop's type with its kind 14,395** (Back to the Office 11,651,
  Viaduct Clothing 2,148), many of them sold out; the type names no kind 18,176 ("Sold
  Out" 2,209, "PCs/Workstations" 795, "Network Switches" 708, "Network Media Converters"
  590, "Made-to-Measure" 454, "Network Cards" 378, "Security Software" 361, "Outdoor
  Sauna" 336, "Networking Software" 328, "Video Games" 291); no type 3,261; not in the
  catalogue 85,742. **Back to the Office: Shopify pages a catalogue only to page 100**
  (25,000 products; page 101 answered 400), so 24,739 of its 95,050 products were read and
  69,205 rows not found; the bot now ends the catalogue there and starts again from page 1
  (`b4ba417`). Finediam's catalogue answered 500 at page 20 (goes on tonight).
- **The owner's «Ναι» to both proposals (26/10, read as one yes for the two):** (1) a shop
  whose catalogue stops at Shopify's page limit is read on by its collections
  (`deployment/bot/shop_catalogue_bot.py`: `page_limit` kept, so the catalogue is paged
  only that far again; then `/collections.json` and each collection's
  `/collections/<name>/products.json`, one after another from a cursor kept across rounds,
  within the same 200 requests, 3 s and robots.txt; "all" and a collection said to hold more
  than 25,000 products are skipped; the list is read again after each whole pass). The
  first collections come with the night's round, 03:40 UTC. (2) The vocabulary
  (`src/picwise_nlu/product_concepts.py`): "workstation" a desktop PC; new kinds
  `network_switch`, `media_converter`, `network_card`, `software` (only its full names,
  "security software", "antivirus", "networking software", ...: a bare "software" stays
  not understood, as `test_live_search_resolver` pins "accounting software"), `video_game`,
  `sauna`. Tests: `tests/test_picwise_kinds_from_the_shops_types.py`;
  `test_picwise_strict_kind_reading`'s unknown label "Networking Software" became "KVM
  Switches". Misspelling benchmark unchanged (93.8%, 0 wrong). The note now lists 30
  types naming no kind. **On the server** (run `40351335007`, `a701306`, the bot's file of
  13:27): 522,733 shown (+1,035); given their shop's type with its kind 18,325 (+3,930),
  naming none 14,246; Back to the Office 4,572 shown (782 in the morning). The types left
  naming no kind, the most first: "Sold Out" 2,209, "Made-to-Measure" 454, "Bedding" 274,
  "Smart Wearable Accessories" 262, "Power Distribution Units (PDUs)" 195, "Power Adapters &
  Inverters" 194, "Console Servers" 193, "Labret Lip Rings" 190, "Servers" 184, "Video Cable
  Adapters" 178, "Ring Binders" 175, "PCs/Workstations" 168 (titles naming another kind),
  "Network Switch Components" 145, "TV Mounts & Stands" 138, "Monitor Mounts & Stands"
  135, "Hardware Firewalls" 129, "Wireless Access Points" 128, "Memory Cards" 112, "Tablet
  Cases" 111, then folders, power supplies, batteries, "Carbon Offset", sweatshirts, pens,
  privacy filters, markers. Mounts, cases and parts are accessories and stay out; memory
  cards, servers, access points, firewalls, batteries, bedding, sweatshirts and pens are
  kinds the vocabulary could learn next (put to the owner).
- **The second list of kinds (owner: «Ναι παίρνω και αυτά τα είδη», 26/10):** new kinds
  `memory_card`, `server` (a bare "server" too; "Salad Servers" on a kitchen shelf stay
  doubtful by the aisle rule), `access_point`, `firewall`, `battery` (full names; a bare
  "battery" is weak, and no bare Greek "μπαταρία", which is also a tap), `pen` (a bare
  "pen" is weak: "pen drive"), `marker`, `folder`, and `bedding`, now broader than bed
  linen, duvets, pillows and bedspreads ("bedding" finds them all); "sweatshirts" and
  "power supply units" added to their kinds. Why they were out, told to the owner: their
  shops send no category to Awin, a row without one is not shown, and the type the bot
  found named a kind the vocabulary did not know. Tests:
  `tests/test_picwise_kinds_from_the_shops_types.py` (5);
  `test_picwise_kinds_from_the_build_list` expects a duvet and a bedspread to be bedding
  too. Full run: only the two that failed before fail; misspelling benchmark unchanged.
  On the server (run `40355492889`, `9872f42`): **523,450 shown** (+717); Back to the
  Office **5,252** (782 in the morning); given their shop's type with its kind 20,402
  (+2,077), naming none 12,169; kinds with products from at least 3 shops 94 of 257 (84 in
  the morning). Left naming no kind, besides accessories and parts: "Safety Footwear" 90,
  "Handheld Mobile Computers" 87, "Diamond Ring" 84, "Mattresses" 83, "Whiteboards" 83,
  "UPS Batteries" 81, "Laptops" 76 (titles naming another kind), "Electric Converters" 75.
- **Why so few electronics (owner, 26/10):** the feed holds only the 85 programmes the
  owner joined and was accepted to, mostly small fashion, jewellery and home shops; no
  large electronics shop. Electronics shown: 9,087 (1.8%), plus what Back to the Office's
  types now bring. Gigbain accepted the owner, but it is not in the feed: the link keeps
  the shops chosen when it was made (`docs/awin_feed_setup_el.md`), so a new link with it
  would go into the `AWIN_FEED_URL` secret, then a deployment. **The owner cancelled it
  («Άκυρο για το συγκεκριμένο κατάστημα gigbain», 26/10): Gigbain stays out; do not ask
  again.**
- **The cap, measured (the owner's «Ναι» read as also for "measure first"):**
  `src/picwise_providers/catalogue_balance.py`, the note's `balance`, printed last by
  `print_shops.py`: per department and aisle (the top and two levels of Google's shelf,
  British names read as US; the shops' own categories one group), per shop and per
  narrowest kind, the largest groups and their shares, and what a 15% cap keeps (each
  group at most C, the largest C with no group over 15% of what all keep; none with fewer
  than 7 groups); and (b) "enough": kinds with products from at least 3 shops. Nothing
  shown changes. Its numbers come with the first deployment.
- **The owner's proposal of a cap (26/10):** no kind more than about 15% of all products,
  so that a shop of 100,000 watches does not make PicWise "a watch site", which also
  helps the checks. Analysis given: right, and needed now (Finediam, jewellery, is 70% of
  the server's 518,041 shown); count it **per department** (from the shop's shelf: most
  jewellery has no PicWise kind, so a per-kind cap would not see it) **and per shop**;
  when cutting keep first the products sold in more than one shop, then a fair share per
  kind and per price band, cheapest first within each (not only the cheapest, or an
  expensive search finds nothing); stable from night to night (Google); the share is of
  the total after the cut, which needs at least 7 departments of some size, else a
  floor; today it would cut most of the jewellery and leave under half the total; it
  does not fix "too few of another kind" (only new shops or networks do). Recommended:
  **measure first, nothing shown changed**: built (below the deployment's block).
- **Open, the owner's, from before:** HTTPS and the domain; the repository private; query
  logging from the server (ask first); 80 or 200 bot checks per shop and what a low score
  does; (a) and (b) above.

## Before (2026-10-26): the rows without a category, after the shop test

The owner ended the conversation of 25-26/10 with «Θα προχωρήσουμε αυτές τις αλλαγές σε
άλλη συζήτηση»: the three changes below wait for their «ναι», each on its own. Owner's
rules, unchanged: Greek, short, plain words; say what you found before building
anything; nothing on `main` without their explicit «ναι»; never ask for the feed link
(it holds the key); secrets only in GitHub's or Vercel's secrets, never in the
repository, a log or the chat; nothing in Supabase without asking; the truth test is a
bot's, never the owner's by hand; never open an Awin tracked link from a session or a
bot; never propose contacting the shops («δεν στηρίζομαι σε αυτούς»).

- **Where the work is:** the branch `claude/bold-allen-ljj9d7` (pushed; bring it in
  first). `main` is at `3608da0` (the two kind fixes, live); the branch's server files,
  measurements and the shop test are not on `main`. Pull requests #12 (this branch) and
  #11 (`ccr-baaad713-r3uvvs`) to `main` are open; nothing goes to `main` without the
  owner's «ναι». `server-shop-test.yml`, like `server-deploy.yml`, runs on pushes to
  this branch; a session on another branch moves those triggers to its own.
- **The owner's direction (26/10):** rows that can be mapped safely and sorted rightly
  join the catalogue; rows no category can be given, also after the bot's check, stay
  out (today's state already: the prepared catalogue keeps only the feed's eligible
  rows); if too few products are left, another network joins (CJ or any other).
  «Βρέθηκαν επίσης» is dropped. Three additions wait for their word: "safe" as a number
  (a title's kind alone only for the kinds measured right 99% on rows with a shelf),
  "enough" counted as kinds with products from at least 3 shops, and the rule only for
  rows with no category from the shop (the about 275,000 shown with a shelf but no kind
  yet stay).
- **What the shop test found** (run `40309611314`; details in the bullet "The shop
  catalogue test, run once" below): 53 of the 56 shops publish Shopify's catalogue,
  with each product's stock and, for 33 shops (32,306 rows), a type on nearly every
  product; paging past 5,000 works; **InStock UK (353,023 of the 388,813 rows) answers
  500** on its catalogue, and the one row of it asked has no type.
- **The three changes put to the owner (each on its own «ναι»):**
  1. **A second, small look at InStock UK only** (about 10 requests, under the same
     script's rules: robots.txt first, 3 s apart, never an Awin link): its
     `/collections.json`, one or two collections' `/collections/<name>/products.json`,
     and a few more of its rows' `/products/<name>.js`, to see whether a category is
     anywhere. If none, its rows have the title only, under the "safe" rule above.
  2. **The bot for the 55 other shops**, each night after the feed: per shop its
     robots.txt, then its Shopify catalogue (250 products a request, at most 200
     requests a shop a round): the shop's own type and each product's stock, matched
     to the feed's rows by the product name in the address; what it learned kept on
     the server (never in Supabase), so a round asks only for what is new; a row whose
     type reads as a kind joins the catalogue, else the title decides (Finediam reads
     worse with its type), else it stays out. User agent `PicWiseBot/0.1
     (+https://picwise.subby.cloud)`.
  3. **So Divine out:** it sells adult products and the server shows 72 of its 81
     rows; the site has no adult rule.
- **Open, the owner's, from before:** HTTPS and the domain (own domain recommended
  before any indexing); the repository private; query logging from the server (ask
  first); 80 or 200 bot checks per shop and what a low score does.

## Before (2026-10-25, later, to 2026-10-26): every Google-format shop on the server; the kind problem on it

The owner put the link with every Google-format shop in GitHub's secrets («ετοιμο»,
25/10); the server reads it, and the deployment now names each shop of the feed.

- **Where the work is:** the branch `claude/bold-allen-ljj9d7` (pushed): the branch
  `ccr-baaad713-r3uvvs` brought in, plus this conversation's commits. Bring it in first.
  `server-deploy.yml` now runs on pushes to this branch; a session on another branch
  moves that trigger to its own. `server-setup.yml` and `server-check.yml` still name
  `ccr-baaad713-r3uvvs`: move their trigger only when they are needed (moving setup's
  runs the setup, which may reboot). The pull request from `ccr-baaad713-r3uvvs` to
  `main` (#11) is open and lacks this branch's commits; nothing goes to `main` without
  the owner's «ναι».
- **The server works** (OVHcloud VPS-4, London, Ubuntu 24.04.5, 8 vCores, 22 GiB usable,
  191 GB free; renewal automatic monthly, next 24/11): secured (updates daily with a
  reboot at 03:30 UTC when needed, SSH by key only, ufw 22/80/443, fail2ban); the site
  under gunicorn on 127.0.0.1:8016 only (nothing from the internet, so Google cannot
  see it); the catalogue prepared at each deployment and nightly at 04:17 UTC. A session
  cannot open SSH: everything goes through GitHub workflows (read their logs with the
  GitHub tools). Secrets are sent only to a server whose host key matches the pin.
- **Now on the server: every Google-format shop** (re-run of run `40189917132`, attempt 2,
  and run `40192893502`, both success): **1,123,857 rows from 85 shops; 518,041 products
  shown, from 77 shops; 605,816 rows held** (mostly no category: InStock UK 384,393,
  Back to the Office 93,662; then out of stock). The preparation: peak memory 7.4 GB
  (ceiling 16 GB), 6.8-8.5 min, a 47.5 MB file; the site 3.1, 4.5 and 5.8 GB after three
  deployments (ceiling 12 GB; likely each worker that served a search holds the
  catalogue, about 1.3 GB each, not measured per worker: to watch after a nightly
  reload). So it fits without the PostgreSQL change. **`AKKO UK`, `EMOKO BIKE`, `Sinocare` and `World
  Businesses for Sale` are not in the feed** (read by the bot in the shop list:
  `deployment/server/print_shops.py`, step "Each shop of the prepared catalogue").
  `Finediam` (jewellery) has 360,067 of the 518,041 shown (70%), so the suggestions are
  full of rings and watches; `InStock UK` brings 509,939 rows (45% of the feed). 8 shops
  show nothing: NORVEXA ADVISORY LTD, Frenzy Clothings, Beauti Outlet, myCord | Bracelet
  Lab, Handbags Infinity Fashion, Purr and Mutt, Bluebells Flora Florist, Wilna Kitchen.
  Two names do not read as shops, for a bot to check what they sell: `Shopping Ads:
  Google & Bing` (6,798 shown) and `NORVEXA ADVISORY LTD` (13,227 rows, none shown).
  No adult shop; `Affiliates - Spoiled Brat` is a Glasgow clothing shop, kept
  (Companies House showed overdue accounts and a strike-off proposal: for the shop
  checks later).
- **The 12 searches against live: 0 of 12 the same, many the wrong kind.** "vacuum
  cleaner": Colleen Hoover books (Lets Buy Books); "mouse": chocolate mice; "tv": a
  "DEATH BY TV" hoody and Islamic digital learning packs; "speaker": banana plug
  connectors; "camera": a camera module among the cheapest. The kind problem of 23/10
  (section below), much larger with many shops.
- **The two measures, built and read (owner: «Να προχωρήσουμε τις δύο μετρήσεις», and
  how not to lose so many products without a category; also: a feed may not tell the
  truth about stock, «για αυτό χρειαζόμαστε τους ελέγχους»).** On the branch only, in the
  public note and printed by the deployment (steps "Each shop of the prepared catalogue"
  and "Kinds that may be wrong in the prepared catalogue"); run `40200815389`, release of
  `85f0a4a`. Measured only: nothing shown changed.
  - **Rows without a category: 532,610**, 532,593 held for that alone. **None carries the
    shop's own category (`product_type`)**, so reading that column would bring in
    nothing. Passing today's other checks (in stock by the feed's word, a price, an
    image), **388,781 could be shown if the title alone gave the kind**: the title reads
    204,124 as a kind, 22,350 as an accessory, 51,430 as doubtful, 110,877 as nothing.
    InStock UK is 353,023 of them (193,233 with a kind), Back to the Office 23,807.
  - **Kinds of the 518,041 shown** (411,717 with a kind): the title names none of its
    kinds on 176,239, and **"watch" alone holds 169,271, of which 167,551 are not
    watches** (piercing oil and ear expanders of MonsterPiercing on "Body Jewellery",
    Finediam's jewellery). Most likely cause, reproduced locally, not yet seen in the
    server's own category text: a shelf like "Jewellery & Watches > Body Jewellery"
    whose narrowest part names no kind, so the code reads the parent "Jewellery &
    Watches" as watches. The title alone names the kind, not the type or shelf, on
    6,518: right for hoodies and jumpers, wrong for "Chocolate Mice" (mouse), "Giant
    Apple Cable" sweets (charging cable), "Voice Tablets" sweets (tablet), a "Rat &
    Mouse" bait (mouse), the book "Make Your Bed" (bed), a model paint's "Protective
    Coat" (jacket), incontinence "Pants" (trousers).
- **The watch error fixed on the branch** (owner: «ναι, ξεκίνα με το ρολόι»; commit
  `6aff4fe`, run `40205899827`; **not on `main`**). The server's shelves are Google's
  British taxonomy: "clothing & accessories > jewellery & watches > body jewellery".
  An aisle listing a kind with something PicWise has no kind for now gives that kind
  only when the title names it, otherwise the narrower shelf decides; the narrowest
  shelf keeps its kind ("Skillets & Frying Pans" stay cookware). Of Google's 5,595
  shelves read with no title, two change (access points and network bridges under
  "Bridges & Routers" are no routers). On the server: products shown as a kind
  411,717 -> 243,908, titles naming none of their kinds 176,239 -> 10,865, "watch"
  169,271 -> 1,751 products (31 suspects); the 12 searches show the same cards as
  before. The kind lists now give each kind's three whole shelves. Left, seen in the
  same list: titles alone giving a kind on another department's shelf, "barbell" 951
  (piercing barbells on "body jewellery", were watches), "bag" 448 (291 on "sweets &
  chocolate"), "bed" 212 (149 on "pet supplies"), chocolate mice as mice.
- **A title alone on another department's aisle, fixed on the branch** (owner: «ναι,
  προχώρα στο επόμενο λάθος»; commits `55a5477`, `45ab1d7`, `772855b`, `00ebb22`; **not on
  `main`**). When no shelf names a kind and the title decides
  (`concept_understanding._title_fallback_head`), the title's kind is now doubtful if the
  category is an aisle of Google's taxonomy whose shelves name no kind of that
  department (`mega_category_id`, or a broader kind's: a smartwatch is a watch);
  `_aisle_departments` gathers them once from `taxonomy.en-US.txt`, each shelf read as it
  is and in the singular; the two-level aisle counts, or its top when it names no kind;
  an aisle whose name names the kind holds it ("Toys & Games"); British aisle names map
  to the US ones (`_BRITISH_AISLE_NAMES`). Doubtful products are still found by their
  words. The note lists what the rule doubted (`kinds_before_the_aisle_rule`), and the
  deployment's comparison prints each server card's shelf and kinds (it copies the
  prepared catalogue to the runner). **On the server** (run `40216310561`): 1,860 shown
  products doubted, nearly all rightly: 941 piercing barbells, 291 sweets as bags, 85
  chocolate mice, sweets as cables, tablets, belts and watches, books (Colleen Hoover,
  slow cooker and air fryer cookbooks), model kits ("Retro Scooter - Model Kit"), pet
  clothes, incontinence pants, tumbler cases as phone cases. Wrongly: 6 smartwatches
  InStock UK files under "Electronics > Video > Video Multiplexers", 8 baby hooded
  towels, 2 baby brush sets. The first version (`55a5477`) also doubted dining sets, sofa
  suites, futon beds, tote bags, toys and every electric massager (2,062 in all); the
  last one keeps them. The 12 searches: "vacuum cleaner" shows real vacuum cleaners,
  "mouse" no chocolate mice, "tv" no hoodie; still wrong on "mouse": a craft stamp set
  "Squeak the Mouse" and a "Self Tan Mousse" (coarse departments; "mousse" read as
  mouse).
- **Both fixes on `main` and live** (owner: «Ναι», 25/10): commit `3608da0` on `main`
  holds only `concept_understanding.py` and the two test files, not the server's files;
  the 107 related test modules (1,138 tests) pass on `main` but the two failing there
  before. Vercel deployed it ("Deployment has completed"); the live site prepared at
  18:50:06 UTC, and its 12 searches show the same cards as before (the errors were in
  the server's larger feed, not in the live 20 shops). `main` is merged into this branch.
- **The title alone against the shelf, measured** (owner: «Ναι»; commit `62fbf93`, run
  `40223470414`; note key `title_alone`, printed by `print_kinds.py`): of 81,601 shown
  products whose type and shelf alone give a kind, the title alone gives one to 52,024
  (63.8%), **the shelf's own kind for 50,445 (97.0% of those)**, another for 1,579; none
  for the rest (doubtful 11,681, nothing 17,174, an accessory 722). **InStock UK: 70.0%
  get a kind, 94.6% of them the shelf's**; Finediam 100%; "Shopping Ads: Google & Bing"
  (it sells Nike trainers) 1.6%: "Iron Grey" read as an iron, "Football Grey" as a
  football. Of the disagreements, about half are the title being right where the
  lexicon links no two kinds (bedside tables on "Bedside Tables" read as tables, dash
  cams, heat pumps, lunch boxes, bracelets on InStock UK's bare "Jewellery & Watches"
  shelf), half title errors (suit -> trousers 623, mattress -> bed 176 by the brand
  "Starlight Beds", boxer shorts -> shorts, bean bag chairs -> bag, mixer grinder ->
  angle grinder). For the 388,781 rows without a category this means about 204,000
  could get a kind from their title, most of them right, a few thousand wrong, and
  about 185,000 none (found by their words only).
- **Rows without a category: the owner's direction (26/10)** «Ο στόχος είναι να λύσεις
  αυτό το πρόβλημα»; **no contact with the shops** («δεν στηρίζομαι σε αυτούς»; never
  propose it again); rows that cannot be mapped stay **outside the price logic** (shown,
  not compared); the shop-check bot has a **double role**: check the feed's stock and
  give category information, within its 200 checks per shop. The owner cancelled
  showing them on the server with the title's kind («Σταμάτα», «Ακυρώ») before that.
- **Where else a category hides, measured** (commits `d5693cb`, `bb0d8f8`; runs
  `40298361738`, `40300435259`): of the 388,813 rows a search could show by their title,
  **no column names a category** (they fill advertiser_id, advertiser_name,
  availability, aw_deep_link, brand, condition, description, id, image_link, link,
  price, title, identifier_exists, mpn, gtin: no custom label, no product type); **the
  shop's address names only "products"** (`.../products/<name>`, Shopify's form; read
  from the Awin link's `ued` as text, never opened); **a barcode** on 63,359, another row
  with a category for only 620 (a kind for 137, 28 where the title gives none); **the
  description's first sentence** gives a kind to 2,424 of the 184,675 the title gives
  none (on rows with a shelf: 5.5%, 93.3% agreeing). So from the feed only the title
  maps them: about 204,000, of which about 95% right (InStock UK 94.6%); about 185,000
  cannot be mapped from the feed.
- **The owner's proposal (26/10), replacing «Βρέθηκαν επίσης»:** rows that can be mapped
  safely and sorted rightly in search join the catalogue; rows no category can be
  given, also after the bot's check, are dropped («πόσες μετατροπές μπορείς να κάνεις
  σε προϊόντα τα οποία είναι κρυφά ... το μόνο που κάνουν είναι να πιάνουν χώρο»); if
  the products left are not enough, another network joins (CJ or any other);
  «Αρκετά ασχοληθήκαμε». So **«Βρέθηκαν επίσης» is dropped**, nothing to build for it.
  Asked for an evaluation; given: right, and today's state already (rows held for no
  category are not in the prepared catalogue, only counted in the note; each night's
  preparation lets a shop's row in once it has a category); three additions put to
  the owner, **waiting for their word**: (a) "safe" as a number: a title's kind
  accepted alone only for the kinds whose title reading measured right nearly always
  (99%) on rows with a shelf, the rest only when the bot confirms them; (b) "enough"
  measured in comparisons, not products: how many kinds have products from at least 3
  shops (Finediam is 70% of what is shown); a new network passes the same gates by
  itself; (c) the rule is for rows with **no category from the shop** only: the about
  275,000 shown with a shelf but no PicWise kind yet (more than half jewellery: "ring"
  gives none) stay, and the vocabulary grows. The bot (stock and category, 200 checks a
  shop, never an Awin link) asks pages of the shops' sites: only on the owner's «ναι».
- **The shop catalogue test, run once** (owner: «ναι, ξεκίνα τη δοκιμή στα 56
  καταστήματα»; commit `364654e`, run `40309611314`, 11 minutes, 217 requests from the
  server as `PicWiseBot/0.1`; `deployment/bot/shop_catalogue_test.py`, run by
  `.github/workflows/server-shop-test.yml` on a push of either file; it reads the
  feed's copy in the download cache, so no key). Of the 56 shops with rows a search
  could show but for a category: **53 publish Shopify's catalogue** (`/products.json`);
  every robots.txt allowed what was asked, none set a crawl-delay; the catalogue says
  each product's stock, and its product names match the feed's addresses (Back to the
  Office: 239 of 250 in the feed). **Paging past 5,000 works** (Back to the Office and
  Finediam gave 250 products on page 21). **Back to the Office** (23,825 rows): a type
  on every product, real ones ("Windows Laptops", "Chromebooks", "Televisions", "Toner
  Cartridges"); a kind from type and title for 70.4% against 52.4% from the title
  alone. 33 shops (32,306 rows) give a type to at least 80% of their first page; some
  types name no kind ("Designer", "Everyday", "Consumable", "Crystal Art"), so a type
  that gives none must leave the title to decide (Finediam: 54.0% with its type, 72.4%
  from the title alone). **InStock UK (353,023 rows, 91%) is not solved by it**: Shopify
  (its product page answered), but its catalogue answers 500 (pages 1 and 21), and the
  one row asked has no type (a mirror, which its title names). Not asked: Juicy Couture
  UK (no shop address in its rows), Pro Espresso (its robots.txt redirects to another
  site). **Seen by the way: So Divine sells adult products** (vibrators, bondage), and
  the server shows 72 of its 81 rows: the site has no adult rule, the Google spec wants
  none on Google's pages, and the owner's plan of 22/10 left adult content out of the
  feed link (the handoff's "no adult shop" above was read from names only). Put to the
  owner, **waiting for their word**: (1) a second, small look at InStock UK only (its
  collections and a few more rows); (2) the bot for the 55 other shops (category and
  stock from their catalogues); (3) So Divine out.
- **Before, put to the owner:** (2) before any row
  without a category is shown by its title, measure how often the title alone agrees
  with the shelf on the rows that have one (per shop: InStock UK has both); (3) ask
  Awin or the two largest shops (InStock UK, Back to the Office) for their categories;
  (4) then the shop checks the owner planned (set hours, 200 checks per shop, the
  shop's own link, robots.txt, a gentle pace), which say whether a feed's stock is
  true. Code goes to `main` only on their «ναι».
- **Open, the owner's:** HTTPS and the domain (own domain recommended before any
  indexing); the repository private (logs are public; nothing secret is in them);
  query logging to Supabase from the server (ask first); 80 or 200 bot checks per shop
  and what a low score does.

## The conversation of 2026-10-23: the server; nothing left out of what is kept

The owner opened a new conversation for a smaller kept file, then the server («Θέλω να
ανοίξουμε νέα συζήτηση γιατί αυτή έχει βαρύνει και το φτιάχνουμε εκεί»). The smaller
file was then stopped by the owner's rule below.

- **Where the work is:** the branch `ccr-baaad713-r3uvvs`, which took in
  `ccr-c30938cf-v749ay`'s notes. Its code is `main`'s (last merge `7b9624c`, 23/10 16:08
  UTC); it is ahead only by notes (PROGRESS and this file). Bring it into the next
  session's branch first.
- **The server: bought, reachable, checked (25/10).** OVHcloud VPS-4 2027 in London
  (Erith): Ubuntu 24.04.4, 8 vCores, 24 GB, 200 GB NVMe, €23.49 a month, no
  commitment; renewal automatic every month (set 25/10; next 24/11). Login by the
  owner's ed25519 key only, user `ubuntu`. The owner set the GitHub Actions secrets
  `SERVER_HOST`, `SERVER_USER` and `SERVER_SSH_KEY`; `AWIN_FEED_URL` not yet (made
  again in Awin's Create-a-Feed when the site moves). The repository is public: the
  server's address never goes into it or into a log (GitHub masks secrets). The session
  cannot open SSH (only HTTPS on 443), so the server is worked through GitHub
  workflows; the read-only `.github/workflows/server-check.yml` (this branch only)
  logged in on 25/10 (PROGRESS, 25/10). **Set up for security on 25/10** (owner's
  «ναι»): up to date (Ubuntu 24.04.5), daily security updates with a reboot at 03:30
  UTC when needed, SSH by key only and no root login, ufw letting in 22, 80 and 443
  only, fail2ban; `deployment/server/base_setup.sh`, run by
  `.github/workflows/server-setup.yml` (this branch only; a rollback undoes SSH and
  firewall in 10 minutes unless a fresh login cancels it; the log masks the server's
  names), run `40187243206`. **The site runs there since 25/10** (owner's «ναι»), with
  today's code and no feed yet (the owner has no link ready): gunicorn on 127.0.0.1:8016
  only (nothing from the internet, so Google cannot see it), the catalogue prepared at
  each deployment and nightly at 04:17 UTC; `deployment/server/deploy.sh` by
  `.github/workflows/server-deploy.yml` (this branch only), which then compares 15
  pages with the live site: 11 the same, the 4 others differ only by the feed (run
  `40188479854`). **With a feed since 25/10:** the owner's `AWIN_FEED_URL` (a
  new-style Awin link with 2 feeds; Vercel reads 20 shops), sent only to the server
  whose host key matches `.github/server-host-key.pin` (an HMAC under the deploy key,
  `.github/scripts/host_key_pin.py`); 1,040 products prepared; of the 12 searches,
  `camera` shares three of four cards with live, the rest differ by the shops (run
  `40189276811`, PROGRESS 25/10). Next, the owner's: the same 20 shops or a larger
  link; then HTTPS and the domain, only on the owner's word. The owner's guide:
  `docs/ovhcloud_server_setup_el.md`.
- **Owner's rule (2026-10-23): nothing that may serve the pages Google indexes is left
  out of what PicWise keeps.** In their words: «Δεν πρέπει να διαγράψεις τίποτα που θα
  επηρεάσει την ποιότητα χαρακτηριστικά seo ... Τα προϊόντα που θα καλούνται από την
  google μέσω λέξεων κλειδιών θα πρέπει να χτίζουν ένα πεδίο το οποίο να είναι πλήρες
  και να προσθέτει υπεραξία στη σελίδα με βάση τα δεδομένα και τα κριτήρια που έχει η
  google ... Δεν πρέπει να υπάρχουν επιπτώσεις στην κατάταξη ... αν αυτή η ενέργεια που
  ετοιμάζεσαι να κάνεις θα φέρει κακά αποτελέσματα στο μέλλον τότε σταμάτησε την».
- **The specification: `docs/PICWISE_GOOGLE_PAGES_SPEC.md`** (owner, 23/10: «Ναι,
  γράψ' το ως προδιαγραφή μόνο εάν είναι ο βέλτιστος τρόπος ... μόνο εάν αυτό είναι
  πλήρως συμβατό με τις προδιαγραφές της google»). Written after checking each part
  against Google's published rules; nothing in it is built. One correction to what was
  put to the owner before: no page per keyword. Google's guide of May 2026 calls
  separate content for every wording of a search scaled content abuse, so a page stands
  for one distinct set of products (category, kind, kind with a property) or one
  product, and a keyword's variations map to that page. That conflicts with the
  founding documents' long-tail landings (raised; "Known doc conflict" below). Read the
  specification first.
- **Its first step, on `main` since 23/10 18:15 UTC and seen live** (merge `47cd76b`,
  owner: «Ναι, να μπει στο main και κάνε τον έλεγχο»; live check run `40001929114` at
  18:16, PROGRESS 23/10). Built on the owner's «Ναι, βάλε το noindex
  στο /search και προστάτεψε το site από την google όσο το χτίζουμε»: `noindex` on
  every page that shows a search (`/search`, `/results`, `/picwise-reference`, `/?q=`;
  the home page without a search stays indexable) and on `/demo`; a `robots.txt`
  keeping crawlers off `/out/` (the redirect to the shops records a click),
  `/subby-proof` and `/cron/`, not off `/search` yet (Google reads `noindex` only on a
  page it may fetch); `X-Robots-Tag: noindex` on the JSON routes. Both route tables;
  `tests/test_picwise_google_protection.py`. The live check now prints all of this
  (`.github/workflows/live-check.yml` on `ccr-fd5dc1bc-4vgsgl`, `39665da`, owner's
  leave): it waits for a deployment that serves `/robots.txt`, then prints it, the
  robots tag of each page and the JSON routes' header. Next, from the specification:
  `Disallow: /search` once Google has dropped those pages (needs Search Console to see
  it), then the catalogue on the server.
- **The server's architecture: `docs/PICWISE_SERVER_ARCHITECTURE.md`** (owner's request
  of 23/10, in English: database and search for 0.8-1M products, URLs and markets, the
  store validation bot, text from the data). Nothing built. In short: PostgreSQL only (no
  Meilisearch, no Redis), PicWise's own understanding and price-first rules kept as they
  are; pages rendered each night and cached at Cloudflare; `/uk/` and `/us/` on one
  domain with `hreflang`, no redirect by country; the bot visits only the shop's own
  `link` (never `aw_deep_link`), keeps `robots.txt`, never evades a block, writes its own
  tables, runs by a systemd timer after the load; text only from computed facts. It
  corrects the brief: Hetzner US East is about three times dearer since June and its
  cheap plans are not sold; 1M products and the bot need 16 GB at least (OVHcloud VPS-4,
  24 GB, about $23 a month, put to the owner); 80 or 200 checks per shop is the owner's
  setting; a domain of PicWise's own before indexing. Open, the owner's: provider and
  size, domain, the checks per shop, what a shop's score changes.
- **Owner's direction (2026-10-23): the business runs on Google.** «Η αρχιτεκτονική
  πρέπει να τηρεί αυστηρά την υψηλότερη ποιότητα και απαιτήσεις της google... Το
  business τρέχει γύρω από το seo... adwords ή διάδοση μέσα από social media
  δευτερεύουσας σημασίας... στοχεύει κυρίως σε χαμηλής επισκεψιμότητας keyword εκεί που
  ανταγωνισμός είναι μικρός... σε μεγάλες αγορές με μεγάλο όγκο προϊόντων... ένας
  χρήστης ζητάει μία λέξη κλειδί θα δώσει μία σελίδα όπου θα δει 4 προϊόντα κι όλα τα
  υπόλοιπα στοιχεία που ζητάει η google». Put to the owner the same day, not decided
  (PROGRESS, 23/10, "The page for a Google keyword, put to the owner"): `/search` kept
  out of Google; one fixed page per chosen keyword, in a browseable hierarchy, indexed
  only past a quality gate; its contents; Google's three risks (doorways, scaled
  content, thin affiliation); and, since Google gives product rich results only to a
  page about one product, a page per product with every shop's price.
- **Owner's decision (2026-10-23): every product gets a page, not only those two shops
  sell.** «Άν ενα προϊόν δεν μπορεί να συγκριθεί με άλλον πωλητή τότε θα εμφανίζεται
  μόνο του σε αυτή την περίπτωση θα έχει πιο πλούσια περιγραφή η οποία θα προστίθεται
  από κάποιο σύστημα Ai το οποίο θα επιμελείται το περιεχόμενο.. η σελίδα θα έχει
  διαφορετική δομή... Σε κάθε άλλη περίπτωση θα χάσουμε τεράστιο όγκο προϊόντων». So an
  AI system curates the content of a one-shop product page (the owner's call, which the
  earlier "code first, AI only if code cannot" leaves to them). Put to the owner, not
  decided: the conditions Google's guidance sets (PROGRESS, 23/10, "A page for every
  product").
- **Owner's requirement for the server's catalogue (2026-10-23):** «το αρχείο που
  μαζεύεται στο server με τα προϊόντα θα πρέπει να έχει τέτοιο μηχανισμό έτσι ώστε
  τμηματικά να κρατάει αυτά που πρέπει να διαγράφει αυτά που πρέπει και τελικά η
  χωρητικότητα να υπολογίζεται με βάση τα ζωντανά πραγματικά είδη ώστε να μπορέσουμε να
  παραμείνουμε στο version εννοείται σε κάποιο πακέτο του». Put to the owner, not
  decided (PROGRESS, 23/10, "The server's catalogue keeps only live products"): each
  night shop by shop, added, updated, or marked gone; deleted with its text and page
  after a number of days (30 proposed); a failed or much smaller feed deletes nothing;
  room only for live products, about 6-10 KB each with everything; a morning report
  against the plan's limit. **Decided by the owner the same day:** 30 days, and
  meanwhile the product's page stays, says it is temporarily unavailable and suggests
  similar products, as Google advises («30μερες»; «η σελίδα δείχνει προσωρινά μη
  διαθέσιμο και προτείνει άλλα παρόμοια προϊόντα όπως προτείνει ο κανονισμός της
  google»). The rest of the mechanism is not decided yet.
- **The smaller kept file: stopped, nothing built** (PROGRESS, 23/10, "The smaller kept
  file stopped"). It would have left out the 46 Google-format columns no rule reads and
  descriptions over 500 characters (the search never matches them), with the same
  searches. Google calls affiliate pages that copy the shop's description "thin
  affiliation" and names price information, comparisons, testing and navigation as the
  value; the future pages for Google need exactly those columns (specs, sizes, colours,
  dimensions, energy class, extra images, delivery cost, unit price, pack size, the adult
  flag, variants) and the full description as material to read facts from, never to
  copy. Today's pages show none of them, so what Google sees today would not have
  changed. Instead (put to the owner, not decided): keep everything, and solve the size
  on the server, with every product's full row on disk and in memory only what the
  search reads.
- **Then the server** (not decided, nothing bought or built): the owner will bring in
  every Awin shop (a Product Count of about 1,300,000, from memory) for the UK and the US
  first, later every euro country, on a server the owner buys. Put to the owner: one VPS
  near London (8 GB of memory and 80 GB of disk to start; the full rows of 150,000-600,000
  shown products are about 0.6-2.5 GB unpacked at the owner's file's 4.1 KB a row, the
  20-90 MB said before assumed the smaller file), a free CDN in front; the site served by
  the same server; each night the feed downloaded and read row by row (about 0.4 GB
  gzipped), every shown product's full row written to a database on disk, by kind, and
  only what the search reads held in memory; the bot on the same server later. Memory
  is to be measured when this is built. The same workflow: the session's branch, the
  owner's yes, `main`, a GitHub workflow that deploys to the server with a key the owner
  keeps in GitHub's secrets (never in the chat); the live site checked through GitHub,
  or directly if the owner adds the server's address to the environment's allowed
  domains. A catalogue per market (GBP, USD, EUR). The site stays on Vercel until the
  server is ready.
- **Answered 23/10: the Awin format does not matter** (owner: «Εμείς δουλεύουμε με
  google feed... Awin feed δεν μας ενδιαφέρει και αν πιάνει χώρο πέτα το»). The
  Awin-format `LEFT_OUT_COLUMNS` (on `main` since 20/10) stays as it is: none of its
  names is one of the 62 Google-format columns, so it leaves nothing of the Google feed
  out, and nothing of the Awin format takes room in what the live site keeps (its feed
  is Google-format). Nothing was changed.
- **Answered 23/10:** the `/search` pages carried no `noindex` and the site had no
  `robots.txt` (`/robots.txt` answered 404); the owner said to keep the search out of
  Google, built on the branch (above).
- **The kind work** is on `main` (merges `9429bca`, `95d0961`, `7b9624c`), and the owner
  stopped it here («Δεν θέλω να ασχοληθώ άλλο με αυτή τη διαδικασία»). The build's own
  list of suspects (`/prepared.json`, `kinds`) is how to comb later; its open points are
  in PROGRESS, 23/10 ("The fixes from the first list to `main`").
- **The owner's files** of 23/10 (Pro-Camera and SafeFort, Google format) reached only
  the earlier session: ask for a file again when one is needed, never for the link. A Google-format
  feed cannot be made with chosen columns in Create-a-Feed, and a file of Back to the
  Office is too large to upload.

## Before: the kind problem (owner, 2026-10-23)

The owner moves the work on product kinds (a search that shows a product of another
kind) to a new conversation: «Αυτό το πρόβλημα θα το λύσουμε σε άλλη συζήτηση».

- **Where the work is:** commit `964fbdf` ("Read a product's kind against the noun its
  title ends with"), **on `main` since 2026-10-23** (owner: «Ναι για το main»; merged
  from the branch `claude/tender-einstein-6nbbs8`), so a new session has it. What the
  live site shows since: PROGRESS, 23/10.
- **Live since 23/10 08:09 UTC, and not enough.** The live check at 08:16 shows "camera"
  4 of 159 (196 before) and "phone charger" 4 of 6 (29 before), yet both first pages
  are still the wrong kind: four Canon and Nikon lenses, and SafeFort's Batteryguard
  charging safes. Three causes, read locally on the live titles: (1) SafeFort names
  the product only after a bar ("Batteryguard L-10 HE VDMA 24994 Certified |
  Lithium-Ion Battery Charging Safe") and the lead before it names none, so the shelf
  decides; (2) in "Nikon AF-S DX 35mm f/1.8G Lens" the number before "Lens" reads as a
  count of lenses (like "11-Fin"), so the noun is passed over; (3) the Canon lenses
  read doubtful on a cameras shelf, so their live rows carry something else, most
  likely a `product_type` that names cameras, whose authority the rule keeps by design.
  These come first; the 7-column file below shows (3).
- **What it does:** the kind-rule bullet of "Now (2026-10-22)" below, and PROGRESS
  22/10. Code: `src/picwise_nlu/concept_understanding.py` (`_product_nouns`,
  `_lead_noun_index`, `_lead_names_another_product`, `_noun_after_kind`,
  `_kind_named_before_another_product`, used by `_title_lead_verdict` when the kind
  comes from a category shelf). Tests: `tests/test_picwise_title_names_another_product.py`.
- **Open, in this order.** Each is measured and told to the owner first, then built.
  1. **The rule on every live product.** No session holds the live rows. The owner was
     asked for a Create-a-Feed file of the same 20 shops with 7 columns only:
     `advertiser_name, id, title, google_product_category, product_type, availability,
     price`. With no link or image column no row passes the shown gate, so read each
     row's kinds the way the search does: `normalize_feed_row_to_provider_product`,
     then `search_selection._product_concepts(product, _product_search_fields(product))`,
     once on the code before the rule (`f86f4e4`) and once on today's. List the rows
     whose kind changes and the wrong kinds left, by shop and by search; look for
     SafeFort's safes on "phone charger" and Pro-Camera's lenses and propellers on
     "camera".
  2. **A title that names no product** ("Batteryguard S-6 HE VDMA 24994 230V - UK -
     KEY LOCK"): its shelf still decides. Nothing decided; the shop's `product_type` or
     description may say what it is.
  3. **"Charger":** the lexicon's `phone_charger` (`src/picwise_nlu/product_concepts.py`)
     takes every charger, so a "Battery Chargers" shelf reads as phone chargers.
  4. **The kind within a kind:** "dining table" still shows a dressing table, a kitchen
     prep table and a shop press's "Working Table": the answer is the kind (table), not
     the table asked for.
  5. **Back to the Office:** 93,639 of its 95,075 live rows carry no
     `google_product_category` and are held. The same file shows whether
     `product_type` carries their category; reading it as the category when the Google
     one is empty is a change in `normalization._CATEGORY_KEYS`, for the owner to approve.
     Since 23/10 `/prepared.json` shows it for every shop (owner's yes for `main`, merge
     `27dd1a1`): `intake.shops[].product_type` gives the rows that write one, how many of
     them have no category, and the five most frequent values. Measured only. **Answered
     live (09:38 UTC): Back to the Office sends no `product_type`** (1 of 95,161 rows,
     "French"; none of the 93,726 without a category), so reading it would bring none in.
     Only Pro-Camera fills it, on all 433 rows: its own path ending in the product's name
     ("Accessories > Flashes > Canon > Canon MR-14EX II Macro Ring Lite Flash"), which
     bears on (3) above.

  Accepted loss of the rule: 42 cushions on a throw-pillow shelf no longer answer
  "pillow" (they still answer "cushion").

  Found on 23/10 (second conversation), on titles with plausible shelves, nothing built:
  (a) "body" is a product noun (Google's "Bath & Body"), so since `964fbdf` a camera body
  on a cameras shelf with no product type ("Canon EOS R6 Mark II Body") is doubtful: a
  real camera lost; (b) in the Nikon case "1.8G" reads as a weight (`_MEASUREMENT_RE`);
  (c) a product type "Camera Lenses" or "DSLR Lenses" makes a lens a camera (the type's
  own noun is not read); (d) a product type is split at "/" (`_TYPE_LIST_SPLIT_RE`), so a
  Pro-Camera path ending in "f/1.4L II USM Lens" reads "Lens" as a kind label of its
  own; (e) every charger shelf, battery chargers included, is the lexicon's phone
  charger (item 3). Which of these the live rows meet: measured the same day on the
  owner's file of Pro-Camera and SafeFort (PROGRESS, 23/10): lenses are cameras by
  Pro-Camera's type "... DSLR Lenses ..." (43), 111 of its 224 real cameras are hidden
  (63 "+ mount adapter" types, 35 "Body", 13 "Camera Kit"), and 6 safes stay on "phone
  charger" by their title's bar. **Fixed (`5de684e`, owner's «Ναι»), on `main` since
  23/10 12:49 UTC (merge `9429bca`; live: "camera" 4 of 226, all cameras; "phone
  charger" no products):** "Body", a type's "+", "Camera Kit", a type naming a
  kind only before another product's noun, a title read on after a bar; on the file 160
  rows change as intended (PROGRESS, 23/10). Left: "camera lens" reads as camera (no
  lens kind), the "1.8G" weight reading, item 2 ("... 230V - UK - KEY LOCK", no bar), the
  lexicon's plain "case" (lock cases on "phone case") and the "Document Wallet".
- **Since 23/10 the build lists suspects by itself** (on `main`, merge `95d0961`):
  `/prepared.json` `kinds`, per kind the shown products whose title does not name it, the
  cheapest first. Read it after each morning's build to find new title patterns from every
  shop without asking for a file. The first list (PROGRESS, 23/10) shows wrong kinds (RAM
  as a processor, a punchbag as a bag, a garden set as a heater, a subscription as a coffee
  machine, bedspreads as duvets) and look-alikes first (bath mats as rugs, bedside cabinets
  as tables, stools as chairs); fixed the same day (merge `7b9624c`): 290 suspects left
  of 438. Next, from the list of 16:09: bedside tables under "Tables > Bedside Tables"
  (the first shelf wins), PVC flooring as a rug; stools, ventilation units and changing
  units wait for the owner's word.
- **How to measure, before and after any change:** `tools/price_first_eval.py <feed>
  <out.json> --compare <before.json>` (the 118 searches: 19 pages changed on the owner's
  third Google file, each by wrong kinds leaving; 0 on fictional Awin-format feeds); the
  kinds of every shown product (`prepare_feed_catalogue()`: `.products` with `.kinds`)
  on both codes; `tools/nlu_misspelling_benchmark.py` (93.8%, 0 wrong, unchanged); the
  full run per module (Working gotchas): 243 of 245 pass, the two known failures
  `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`. The owner's files reached only the
  old session: ask for a file again when one is needed, never for the link.
- **The live site** is seen through the live check ("How a session sees the live site",
  below); its last run is `40001929114` (23/10 18:16 UTC; re-run it to look again).
- **The owner's words for this work** (2026-10-20): «Μην αλλάξεις τίποτα στο live site
  και μη χτίσεις τίποτα πριν μου πεις τι βρήκες. Τίποτα στο main χωρίς το ρητό μου
  «ναι». Μη μου ζητήσεις τον σύνδεσμο του feed, γιατί έχει το κλειδί. Γράψε μου στα
  ελληνικά, σύντομα, με απλά λόγια.» Never open an Awin tracked link from a session (it
  counts as a click). The truth test is a bot's, never the owner's by hand.

## Now (2026-10-22) -- read this first

- **Google-format reading is built and on `main`** (merge `c147fda`, owner's
  «πέρασε στο main», 22/10; seen live at 12:21 UTC, the Awin-format pages as before): the category from
  `google_product_category`, the currency split off the price ("39.99 GBP"), and a price
  of 0 or below never shown (`price_zero_or_negative`). On the owner's third
  Google-format file: 4,621 products shown of 13,071, 6 shops; on fictional Awin-format
  feeds 0 of the 118 search pages change; full run 242 of 244 modules pass (the two
  known failures). Details in PROGRESS, 22/10. **Open, the owner's:** make the final
  Create-a-Feed link (advertiser-based, no categories, no AKKO UK) and put it in Vercel
  (`AWIN_FEED_URL`);
  the steps are in `docs/awin_feed_setup_el.md`, "Feed σε μορφή Google". Only the owner
  can paste it (it holds the API key). Until then the live site runs on the
  Awin-format link.
- **Owner's plan (22/10, after the merge):** one Create-a-Feed link with every
  Google-format advertiser, joined or open, so the link is not redone per shop; the shop
  evaluation and the map of shops per category from what it brings in; then Vercel for
  the volume; then the truth-test bot (the owner pays a subscription; **80 checks per
  shop**, not 200); then Awin closes and CJ opens. **Before that link goes into Vercel:**
  the owner reads its Product Count (about 250,000 is what was measured to fit; the
  download stops at 300 MB), leaves adult content out. **The UK for now** (owner, 22/10);
  a GBP-only rule in the site was put to the owner, not decided. Proposed, not built: each shop's categories in `/prepared.json`.
- **Live since 22/10 13:34 UTC: the Google-format link** (20 UK shops, 119,720 rows):
  12,204 products shown from 19 shops. Back to the Office shows 771 of 95,075: 93,639
  of its rows carry no `google_product_category` (whether they carry `product_type` is
  not seen yet). First pages showed wrong kinds ("phone charger": charging safes;
  "camera": propellers, lenses).
- **The kind rule, reworked** (owner's yes, 22/10; **on `main` since 23/10**, owner:
  «Ναι για το main»): the noun a title's lead ends with is read against the
  product nouns of Google's taxonomy, and a shelf no longer gives its kind to a lens, a
  safe, a stool or a keyboard plate. Measured: 19 of 118 pages change on the owner's
  Google file, each by wrong kinds leaving; 0 on fictional Awin-format feeds; full run
  243 of 245 modules (the two known failures). Not fixed: a title that names no product ("Batteryguard S-6 ... KEY
  LOCK") and the lexicon's "charger" = phone charger; qualifiers inside a kind ("dining
  table" shows a dressing table). Details in PROGRESS, 22/10.
- **New rule (owner, 22/10): one shop in several networks** is one shop, known by its
  site's domain; its price and stock from the freshest feed (the latest update date
  the network states) with a real stock state,
  never chosen by commission; only for the same offer is the link taken from the
  network that pays best (the highest commission first, owner 22/10). In `PROJECT_RULES.md` section 5, the decision contract and the
  concept (Revenue Rule). Not built (one network today).
- **Owner decisions of 22/10:** AKKO UK out (prices in EUR; done in the feed selection,
  not in code); the truth test (what the feed says against the shop's own page) is done
  by a bot, never by the user by hand. Nothing of the bot is built; where it runs is
  open (not on Vercel: its fair-use page lists scrapers as never allowed, a function
  stops at 300 s, Hobby runs a scheduled job once a day).
- **Shops (owner's screenshots, 22/10):** joined Living and Home, Back to the Office,
  Game Over, PCHUB.UK, Tyres UK, Gardenista, Aosom UK, brickzonehub (no feed). With a
  Google-format feed: Living and Home, Game Over, Gardenista, Back to the Office (about
  88,000 products; its file did not download); Tyres UK has none; Aosom UK does not show.
  Open advertisers (not joined, yet in Create-a-Feed) are credited for sales through
  their feed, per Awin's help pages ("soft membership", auto-join): Geepas and Homespace
  Direct were in the third file; Car Audio Centre was not shown in the selector on
  22/10. PCHUB.UK's format is not known yet. Missing kinds: TV and audio, tools. Every
  search page has one shop's products today: no real comparison yet.
- **Flagged to the owner, not decided:** Vercel's Hobby plan is for non-commercial use
  only, and Vercel names a site whose primary purpose is affiliate links as commercial;
  this applies to the live site now. Ask Vercel, or plan for Pro.
- **The Google format has no listing date** (the Awin format had `last_updated`), so
  stale listings cannot be told by date; `product_type` and `sale_price` were empty in
  all three files and are not read.

## Before (2026-10-20)

- **Start here: Google-format feeds (owner decision, 20/10).** «Θα εστιάσουμε στα
  google feed δεν θα ξανασχοληθούμε με awin feed». The reading put to the owner, not
  contradicted, to confirm first: Awin stays as the network (links, commission), and
  only Awin's Google-format feeds are used (a publisher gets them only through
  Create-a-Feed). **First step:** the owner uploads a Google-format file (the file,
  never the link); measure it (columns, how many say `out_of_stock`, the price with its
  currency, the category columns, whether the product link is Awin's tracked link),
  then build the reader on it. PicWise does not read the format yet; until it does,
  the live site runs on its current Awin-format link. Details in PROGRESS, 20/10.
- **On `main` since 20/10** (merge `3c2c4cd`, the owner's «Πέρασε το στο main»): the
  work of this conversation (`ccr-9015e891-xt29ld`) and the notes of 18/10. **Seen
  live** through GitHub at 12:52 UTC: the feed prepared by the new code at 12:48 UTC,
  `prepared_feed` `in_use`, the 12 searches of the live check showing the same cards
  as in the morning, and the per-shop intake in `/prepared.json` (143 of 11,191 rows
  held back as not for sale; 4x4 Predator's 109 rows all held).
- **The owner's update of 18/10** (sent 20/10) restates the direction recorded on
  18/10: no checks of shops' pages now; first many shops, with whatever each feed
  sends; then the evaluation mechanism (set hours, 200 checks per shop, the shop's own
  link only, robots.txt, a gentle pace, one Vercel job a day, the feed link only in
  Vercel). Nothing of the mechanism is built.
- **Live** (through GitHub, 20/10 09:47 UTC): the morning renewal works (prepared 04:59
  UTC); 11,048 products, 25 shops; Boxed2me still fills the cheapest pages; one shop is
  "Monsterpub Sex Toy" (the link takes in adult content).
- **Built for many shops, on the branch** (details in the plan file, "Many shops: what
  the free plan carries"): the feed read as a stream, a lean prepared file (format 2,
  `LEFT_OUT_COLUMNS`), and per shop what each feed brings in (`/prepared.json`,
  `intake`). The server's ceiling on Vercel's free plan moves from about 110,000 real
  products to about 250,000 (measured on fictional feeds); 0 of the 118 pages changed.
  A cold server's first search still grows with the catalogue (about 11 s on Vercel at
  92,000 products): the regular visit that keeps the server awake (owner's idea,
  2026-10-17) is the answer, not built.
- **The owner's steps for many shops** are in `docs/awin_feed_setup_el.md`, first
  section (Greek): join programmes; one new link by category with every category;
  all columns kept, `merchant_deep_link` above all; watch `products` in
  `/prepared.json` against about 250,000.
- **Not decided (20/10): whether the catalogue may be held in the server's memory.**
  The owner said never, then withdrew it the same day («Άκυρο θα συζητηθεί άλλη
  φορά»). Nothing changes until it is discussed. Options put for that discussion: (A)
  SQLite inside each deployment, free, about 150,000 to 250,000 products (Vercel's 500
  MB per Python function); (B) a hosted database. Also proposed, not decided: a daily
  check of what the first pages show (about 2,600 product pages a day) next to the 200
  checks per shop; no production jobs on GitHub (its terms, as remembered; check them
  before stage 2).
- **Open, the owner's:** the yes for `main`; keep or drop Boxed2me; adult content in or
  out; which shops to join. For a later discussion: the catalogue in memory or in a store.

## Before (end of the conversation of 2026-10-17/18)

- **Live = `main`:** price first (steps 1-4), the search page, and step 5: every
  deployment's build prepares the feed (`vercel.json` build command), a Vercel
  scheduled job a day (`17 4 * * *` UTC) asks for a new deployment through the Deploy
  Hook, so each day has its own prepared feed. The owner set the keys in Vercel on
  2026-10-18 (`PICWISE_DEPLOY_HOOK_URL`, `CRON_SECRET`; Production, Secret). Also live:
  products without a description are shown with a note (owner), and `/prepared.json`
  carries `freshness` (listing ages, stock columns, per shop).
- **Seen live** (through GitHub, below, 2026-10-18 11:59 UTC): `prepared_feed`
  `in_use`; 11,423 products, 25 shops; searches 0.3-0.9 s; "tv" 4 of 23.
  **Not seen yet:** the first morning renewal. Look on 2026-10-19 after about 05:00
  UTC: `/prepared.json` `prepared_at` of that morning means it works.
- **How a session sees the live site:** its own network cannot reach
  `picwise.subby.cloud`. A push to `ccr-fd5dc1bc-4vgsgl` runs
  `.github/workflows/live-check.yml`, which prints `/prepared.json`,
  `/private-beta-readiness` and the cards of 12 searches; or re-run its last run with
  the GitHub tools (`actions_run_trigger`, `rerun_workflow_run`) and read the log
  (`get_job_logs`). Never ask the owner to copy pages by hand if this works.
- **The branch** is ahead of `main` only by notes and that workflow; its code is the
  same as `main` (the shop-page sample was reverted).
- **Owner decisions of 2026-10-18:** a description is not required (note on the
  card); no checking of shops' pages now; the order from here: (1) many more shops,
  (2) then an evaluation mechanism at set hours, 200 checks per shop, giving a list
  of reliable and unreliable shops (constraints in PROGRESS). **Code first:** that
  mechanism and the fix of the kind rule are written in plain code; an AI system is
  discussed with the owner only if code is shown not to reach the results wanted,
  and is not proposed before that.
- **Open, the owner's:** keep or drop Boxed2me (3,474 products, a clearance shop that
  fills the cheapest-first pages for headphones, chargers, cameras, speakers, at
  prices such as £0.99, the likeliest "ghosts"); which shops to add in Awin.
- **Open, engineering, held until more shops are in:** the rule that reads a
  product's kind lets wrong kinds onto first pages ("camera": a chime, a siren, a
  shotgun microphone; "phone charger": an IEC plug), to be fixed once on all cases;
  Xiaomi RO's TVs priced "EUR" 849-3,799 (likely Romanian lei); Geekbuying prices
  shown with three decimals ("14.990 USD"); laptop, kettle, mouse and keyboard find
  nothing in this feed (data, not understanding).
- **Rules:** nothing to `main` without the owner's explicit yes; keys only in Vercel;
  nothing changed in Supabase without asking; Greek, short, plain words.

## Start here (2026-10-17)

- **2026-10-18: steps 1 to 5 are on `main`** (merge `e52339d`, a normal merge of
  `ccr-fd5dc1bc-4vgsgl`, by the owner's yes «Ναι, τώρα», told beforehand that it puts
  all of them live). Production NOT VERIFIED from the session, which cannot reach
  Vercel or the domain: the owner looks at `picwise.subby.cloud`, its
  `/private-beta-readiness` (`prepared_feed` should read `in_use` with today's time)
  and `/prepared.json`, then Settings, Cron Jobs, Run, once. If the site misbehaves:
  Vercel's Instant Rollback to the previous production deployment (`3b02aeb`), or a
  revert of the merge. The notes below that say "nothing is on `main`" predate this.
  **Seen live by the owner the same day:** the home page opens with the new box
  ("What are you looking for?"); `/prepared.json` reads `prepared: true`, 9,935
  products, 25 shops, prepared 10:32:56 UTC (the production build read the real feed
  and prepared it); `/private-beta-readiness` reports `provider_feed_ready`; a search
  "was fast" (owner). Not checked, and the owner asked not to be asked again: the
  `prepared_feed` line, and a run of the daily job (it runs by itself each morning).
  A later session can tell from `/prepared.json`: a `prepared_at` of that morning means
  the renewal works. The session itself cannot open the site.
- **2026-10-18, after the merge: products without a description are shown, with a
  note** (owner: «Ναι, με σημείωση»; Decision Contract, "What a product must carry to
  be shown"). "tv" found nothing live because the feed's televisions come only from
  shops that send no description. On `main` since the same day (merge `6050315`, the
  owner's yes); live result NOT VERIFIED from the session ("tv" should now show
  televisions, with the note). The microphone is hidden in Firefox (no speech recognition there);
  the owner uses Firefox.
- **2026-10-18: "we show ghosts"** (owner): most products shown are out of stock on
  the shop's page, old listings. Measuring first, by the owner's choice: the build
  writes listing ages and stock quantities into `/prepared.json` (`freshness`;
  `src/picwise_providers/feed_freshness.py`); the owner copies it, then chooses a rule.
  Details in PROGRESS. Not a rule yet: nothing shown changes. The feed carries no
  dates and no out-of-stock state at all. **Owner decision, 2026-10-18: no checking of
  shops' pages**, not even a few-day sample (built, then reverted on the branch,
  never on `main`); do not propose it again unless the owner raises it. **The
  owner's order, the same day:** first many more shops; then an evaluation mechanism
  at set hours, 200 checks per shop, giving a list of reliable and unreliable shops
  (constraints in PROGRESS). Left meanwhile: which shops to keep (Boxed2me fills the
  cheapest-first pages for several kinds); the wrong-kind cases wait for more shops. The
  live check (`.github/workflows/live-check.yml`, on each push to the branch; re-run
  to look again) reads PicWise's own public pages through GitHub, no shop's.
- **Step 5 is begun** (2026-10-17, on the branch; nothing of steps 1 to 5 is on
  `main`). A search takes about 0.34 s (5 s before), a cold server reading the feed
  reaches the first page in 22-24 s (38-40 s), and one given a **prepared file**
  (`tools/prepare_catalogue.py`, `src/picwise_providers/prepared_catalogue.py`) in
  about 4 s, without reading the feed; 0 of the 118 pages changed. Details and what
  keeps a prepared file honest: the plan file, "Step 5, first part built".
  **Second part built too** (2026-10-17, on the branch, not checked on Vercel): every
  deployment's build prepares the feed (`vercel.json` build command, no more `builds`),
  a deployment never fails because of the feed (`--keep-going`), one Vercel scheduled
  job a day calls `/cron/renew-prepared-feed`, which with `CRON_SECRET` posts to the
  Deploy Hook in `PICWISE_DEPLOY_HOOK_URL` (both keys only in Vercel), and
  `/private-beta-readiness` says under `"prepared_feed"` whether the server answers from
  the file. Checked with Vercel's own CLI (`vercel build`) on a fictional feed; details
  in the plan file, "Step 5, second part built". **Waits on the owner, in Vercel**
  (Greek steps: `docs/vercel_daily_feed_setup_el.md`): the Deploy Hook, the two keys,
  `AWIN_FEED_URL` for Preview on this branch for the test, a look at the test
  deployment, then the word for `main`. This conversation had no Vercel connection
  either; none is needed for these steps, the owner does them in the dashboard.
  **Owner, 2026-10-18:** the steps are hard to do now; the Vercel way stays, later
  («Με τη Vercel, αργότερα»), and the site stays as it is until then. Offered instead
  and not chosen: a scheduled GitHub workflow making one small automatic commit to
  `main` each morning (no keys, no Vercel steps; a push to `main` makes Vercel build,
  and the build prepares the feed). Do not build it unless the owner asks.
  **Later the same day the owner did it, guided screen by screen:** a Deploy Hook
  `daily-feed` for `main`; `PICWISE_DEPLOY_HOOK_URL` and `CRON_SECRET`, both
  Production and Secret (six variables now). Not done: `AWIN_FEED_URL` for Preview. A
  Secret cannot be read back, and its Edit form shows the value empty, so saving it
  with Preview added risked erasing the Production feed link: cancelled, and the test
  ran without the feed. **Seen on Vercel by the owner:** the preview builds of the new
  config (`e715771`, `f530240`, `cfbf683`) are all Ready, and `/prepared.json` on the
  preview reads `prepared: false, reason: feed_not_readable` (right without the feed):
  the build step runs on Vercel and its note is served. **Not checked:** the preview's
  pages served by the Python function (`/`, `/private-beta-readiness`); the owner
  stopped there («τελείωσα εγώ, κάνε εσύ»), and the session cannot reach Vercel or
  the live site. **Left:** the owner's explicit yes for `main`, which puts steps 1 to 5
  live, not only the prepared feed; then one look at `picwise.subby.cloud` and its
  `/private-beta-readiness` (`prepared_feed`: `in_use`); then Settings, Cron Jobs, Run,
  once. On
  Google Cloud Run, were PicWise moved there, the same tool and file serve
  (`PICWISE_PREPARED_CATALOGUE_FILE`); only the schedule and the hook are Vercel's.
  **Next after that:** the regular visit that keeps the server awake (below), its
  interval measured on the live site. **Decided by the owner, 2026-10-17:** a file prepared once a day is fresh
  enough («Ναι φορά τη μέρα μου αρκεί»), and a regular visit keeps the server awake
  (the owner's idea, "every hour"; plan file, "Step 5, first part built").
  The owner does not pay $20 a month for Vercel Pro (2026-10-17); Vercel's terms, as
  remembered and not checked from here, keep the free plan for non-commercial use;
  Google Cloud Run's free tier was proposed, nothing decided; build so it runs on either.
  The owner also wants all projects under SUBBY CLOUD and the GitHub account renamed
  "subbycloud"; steps given, nothing done by Claude.
- **Picking up in a new conversation.** Everything is pushed to `ccr-fd5dc1bc-4vgsgl`.
  To measure a change that should only be faster:
  - the owner uploads the feed file (Awin, download, then upload here; never the
    link). Copy it into its own empty directory;
  - before the change: `python -I tools/price_first_eval.py <feed.csv.gz> before.json`
    (118 searches, a few minutes); after it: `python -I tools/price_first_eval.py
    <feed.csv.gz> after.json --compare before.json`, which lists every page that
    changed and the time per search before and after; `--prepared <file>` answers
    from a prepared file;
  - tests per module: `PYTHONPATH=.:src python3 -m unittest tests.<module>`, a few
    at a time, and `PYTHONPATH=.:src python3 tools/nlu_misspelling_benchmark.py
    --failures 60`. Known failures on unchanged code are in "Current numbers" below;
    the rest of the gotchas at the end of this file.
- **New direction: price first, no ratings** (owner, 2026-10-15). Read
  `docs/picwise_price_first_plan_2026-10-15.md` before anything else. In short: only
  the kind asked for; never out of stock; cheapest first; the same product once, from
  its cheapest in-stock shop; the first four are a "Recommended", the middle product in
  price order, plus the three cheapest, with "4 of 45"; "more" again and again. The old
  instruction, "build nothing until a feed with ratings arrives", is over, and the
  search for ratings stops.
- **The founding files now say the same as the plan.** It contradicted them (no endless
  list, not a search engine); on 2026-10-16 the owner chose to change them, and
  `concept.picwise.txt`, `docs/MISSION.md`, `PROJECT_RULES.md` and
  `docs/LANDING_PAGE_SPEC.md` were changed. Each changed passage in the concept carries
  a dated note. Services (insurance, energy, banking, software) were not decided and
  keep their old rules.
- **Step 1 of the build order is built** (2026-10-16, on the branch): only the kind
  asked for. A product answers a kind only when its type, its shop's category path or
  its title's lead says so plainly. Doubtful products (11,187 of 42,076) are found
  only by their own words, and pet and camping products answer only searches that
  name them. Of the same 118 English searches, 95 now show four right products (80
  before) and none shows the wrong kind (21 before). What price order would list
  first is now the product, not its accessory: "laptop" opens with a £125.99 HP Stream
  instead of a £3.99 adapter. Details and what is left: the plan file, "Step 1 built".
  **Step 2 is built too** (English before greeklish: "patio set" shows garden
  furniture, not insoles). **Step 3 is built too** (2026-10-16): the price-first engine,
  for every search whose product is understood. Cheapest first, each product once; the
  Recommended is the middle product by price with a valid EAN/GTIN, never the cheapest
  or the dearest; "Lowest price" on the cheap cards; "4 of 677" and a "More" that opens
  the next four as often as asked (`/search?q=...&shown=8`); fewer than four as they
  are. A search's other words now decide what is in the answer, read in each product's
  title, type and brand. Graded refurbished titles are read as not new, and USB sticks,
  bookcases and fire pits are their own kinds. Of the 118 searches, 100 show a right
  first page, 12 a card that misses a word, 1 a wrong card, 5 nothing. Details,
  including where a rule needed reading, in the plan file, "Step 3 built". The owner
  accepted those readings on 2026-10-17 and decided that without a Recommended
  "Lowest price" goes only up to the middle price (built the same day). **Part 3b is
  built too** (2026-10-17): a search whose product is not understood ("cat tree", "dog
  crate", "network switch") is answered by its words on the same price-first page,
  with its own kind test (no hutch covers for "rabbit hutch"), a model name answered
  as the kind its products are ("lenovo thinkpad 16gb ram": laptops), and a one-word
  search that names several kinds asking which ("switch", "tree", "machine"). Details
  in the plan file, "Part 3b built". **Step 4 is built too** (2026-10-17): the box
  reads "What are you looking for?" (owner); a scanning screen with the real counts
  as a search starts; suggestions as the buyer types (kind names in English and
  Greek, brand with kind, the shops' own names, only those that find products,
  fetched once from `/suggest.json`); a microphone where the browser can listen, the
  search starting when the buyer stops (owner). Details in the plan file, "Step 4
  built". **Next: step 5, data prepared once a day** (the first speed-up: stop judging
  every product's eligibility again on every search).
- **Measured on 2026-10-16** on a new feed (Back to the Office, Aosom UK, Living and
  Home; 42,076 rows). Results are in the plan file, "Measured on the third feed":
  - cheapest first puts accessories on top ("laptop" opens with docking stations);
  - the middle of the range recommends the top end (a £4,809.99 MacBook Pro);
  - no shop sends a real stock state;
  - no product is in two shops;
  - a search takes 4 to 16 seconds.

  **Decided by the owner, 2026-10-16:** the Recommended is the median (the middle
  product in price order), and the feed's "in stock" is trusted (no shop page is
  checked). **First engineering step:** a strict yes/no test that a product is the kind
  asked for. **English understanding, tested the same day:** 118 queries with
  misspellings and phrasings; the right kind understood for 109 (92%), but only 80
  showed four right products. Kind-reading errors (tablet casings, desk trays, label
  makers) account for most of the rest; also "patio" is read as greeklish «πάτοι»
  (insoles), and queries with numbers show empty pages through the old recommendation
  step. Details in the plan file, "Search understanding, English".
- **The owner's additions (2026-10-16), in the plan file:**
  - suggestions as the buyer types (faint completion plus a word list from the first
    letter);
  - a microphone in the search box;
  - trends below the box, true to their source;
  - many more shops (every Awin programme with a feed, then CJ and others);
  - extreme top prices (at least twice the next) do not count for the Recommended;
  - no Recommended for services in this phase.

  - PicWise as a phone app, later in the Play Store;
  - a truthful scanning screen that lets results take about 4 s (concept section 18
    and PROJECT_RULES section 9 changed).

  Proposed build order:
  1. strict kind test;
  2. English over greeklish;
  3. the price-first engine;
  4. the search page (scanning screen, suggestions, microphone);
  5. data prepared daily (needed before going live);
  6. trends;
  7. the app;
  8. other networks.

  The owner restated the extreme-price rule for step 3 (2026-10-16: «όταν το
  ακριβότερο είναι δύο φορές ακριβότερο από το προηγούμενο φθηνότερο να εξαιρείται
  από το μέσο όρο»), which matches the recorded reading, and did not object to the
  order; step 1 is built.
- **Decided by the owner on 2026-10-16:**
  - "smartphone" shows smartphones; "mobile phone", "phone" and «κινητό» show only
    basic phones. This is built, on the branch;
  - no Recommended when no product has an EAN/GTIN;
  - fewer than four results are shown as they are ("2 of 2");
  - brand + MPN counts as the same product;
  - the three cheapest cards say "Lowest price" ("Lowest price of N shops" when
    offers are joined), and the line under Recommended is "Mid-priced for this
    category".

  All are built (steps 1 and 3).
- **Open owner decisions:** none on the plan. Put to the owner with step 3:
  - ~~the search box wording~~: chosen on 2026-10-17 ("What are you looking for?") and
    built in step 4;
  - a check on implausible prices (£0.99 headsets lead "headphones");
  - whether a word after "for" ("printer for home") should narrow the answer;
  - ~~the readings made to build rule 7~~: accepted on 2026-10-17 («Οκ σε όλους»).

  The marketing proposals in the plan file are proposals; none is approved.
- **Branch, not `main`.** `ccr-fd5dc1bc-4vgsgl` is ahead of `main`; count the commits
  with `git rev-list --count origin/main..origin/ccr-fd5dc1bc-4vgsgl`. Merge
  to `main` only when the owner says so explicitly. A session may be set up to push to
  another branch (on 2026-10-16 it was `claude/vibrant-cerf-b2afyt`). The owner works
  on `ccr-fd5dc1bc-4vgsgl`, so ask before writing anywhere else.
- **Both real feeds measured carry zero ratings and zero sales counts**, checked over
  every row: the first (11,573 UK electronics) and the second (51,630: Tyres UK, Aosom
  UK, Living and Home). Two facts from the second that the plan depends on:
  - Tyres UK (39,403 rows) writes its description in `custom_6`, so no tyre passes the
    description rule until that column is read;
  - Living and Home (2,255 rows) sends no category, so all its rows are held at the
    feed gate.
- **Awin Google format:** it cannot be mixed with Awin-format feeds in one file (Game
  Over offers only Google format). Whether it carries ratings no longer matters.
- **Awin status (owner's screenshots, 2026-10-14):** Joined -- Living and Home, Back
  to the Office, Game Over, Tyres UK, Aosom UK. Pending -- Gtech, Songmics, Mstore,
  Hoxton Macs, Road Angel, Boots.com, Currys, Euroffice. Rejected -- Beldray, Mattress
  Online, SharkNinja UK (advised not to re-apply now). Markets: UK and US.
- **When a new feed file arrives:** copy it into its own empty directory, run
  `python -I tools/check_awin_feed.py <file>` and measure it against the price-first
  rules. Report in Greek, short. Never ask the owner to paste a feed link (it holds the
  API key): they download and upload the file.
- **Homepage** still reads "Buying Decision Preview" / "Live safe mode" and `/about` is
  404; likely hurting Awin approvals. The owner declined a fix on 2026-10-14, before the
  plan changed. The marketing analysis proposes a new homepage sentence.

## Where the work is

- Repository: `nikkaradimitris-cloud/picwise.concept`
- **Stale, see "Start here" above:** the branch is ahead of `main` again. The condition work (non-new products only when the buyer
  asks) was merged on 2026-10-11 by the owner's instruction: merge commit `b28da32`, a
  normal merge of `ccr-fd5dc1bc-4vgsgl`, no pull request. Its deployment is NOT VERIFIED
  from a session. Earlier: PR #2 was merged on 2026-10-08 (merge commit `148a552`,
  a normal merge, by the owner's instruction). It carried all of PR #1, so GitHub marked
  PR #1 as merged too; the owner chose this knowing it. `main` holds the 4+1 Awin path,
  the misspelling understanding, the mission truth audit of 2026-10-08 and its fixes
  (`docs/picwise_mission_truth_audit_2026-10-08.md`). Start new work from `main`.
- **Production: the audit fixes are deployed.** On 2026-10-08, after the merge, the owner
  checked that `/best/power-bank-20000mah-for-iphone` on `picwise.subby.cloud` returns
  404; it used to show a fabricated page (audit D1). Not checked live: whether
  `/sitemap-buying-pages.xml` lists nothing, and anything that needs a real feed (none
  is connected). The session environment blocks `picwise.subby.cloud` and
  `*.vercel.app`, so a session cannot check the live site itself; ask the owner.
- Hosting: Vercel project `subbycloud/picwise-concept` (Hobby account "SUBBY CLOUD";
  since 2026-10-10 its only login is the owner's `mysubby.cloud@gmail.com`, email and
  Google; no Git login is linked to it). Domain `picwise.subby.cloud`. Entry point
  `api/index.py` (see `vercel.json`). Deployments come from pushes to `main` through
  the Vercel GitHub app. A manual **Redeploy** from the dashboard fails with "Git
  information retrieval failed" (no Git login on the account); to roll out an
  environment change, merge a commit to `main` instead.

## The owner

Not a programmer. Write to them in **Greek**, plain words, short. Explain choices in
everyday terms, give honest numbers, and say plainly what was not done and why. Never
overclaim.

## Rules that do not change

Read in this order before touching anything, every session:

1. `PROJECT_RULES.md` — the operating rulebook, first in the source-of-truth order
2. `docs/MISSION.md` — the mission lock: what every purchase-intent query owes the
   buyer, the product promise ("Enter confused. Leave decided."), the identity PicWise
   must never drift into, and the trust/neutrality commitments. **Every piece of work
   is measured against this file.** Its "First Phase Boundary" section is stale (it
   predates the live app) — see "Known doc conflict" below.
3. `concept.picwise.txt` — the product concept source of truth
4. `docs/` contracts and specs — implementation contracts
5. this file, then the last entries of `PROGRESS.md`

If these layers conflict, do not guess: stop and raise it (PROJECT_RULES section 1.4).

In short:

- every purchase-intent query: only the kind asked for, only in stock, cheapest first;
  4 choices first (1 Recommended, the middle product in price order, + the 3 cheapest),
  then "More" for the next 4 as often as asked; decision labels, CTA, direct redirect,
  tracking event (price first, 2026-10-16)
- no fake data of any kind; no commission-based ranking; missing data uses the enum
  (`not_connected`, `data_not_yet`, `not_applicable`, `unknown`)
- small, closed, tested steps; do not invent business logic (flag a TODO instead)
- section 9 performance: first render < 1.5 s, interactive < 2 s, click → redirect < 300 ms
- stages 23–25 stay `NEEDS_*` until real live proof exists; local fixtures are never live
  proof
- **Amazon is permanently removed** — do not reintroduce it. Awin is the affiliate network.
- nothing that may serve the pages Google indexes is left out of what PicWise keeps, and
  nothing may hurt their quality or ranking (owner, 2026-10-23; first section above); a
  change that would, is stopped and told to the owner
- the business runs on Google search, Ads and social media second (owner, 2026-10-23):
  low-volume, low-competition keywords in large markets with many products; every page
  meant for Google meets Google's own published requirements end to end

## Map of the code that matters now

| Area | Where |
|---|---|
| Product concept lexicon (278 kinds, EN + GR names, mega category, `broader`, preference words) | `src/picwise_nlu/product_concepts.py` |
| Understanding: phonetic keys, typo correction with safety fences, specs, product annotation (incl. accessory guard), "did you mean" | `src/picwise_nlu/concept_understanding.py` |
| Price-first selection: the kind test, cheapest first, the same product once, the Recommended, "4 of 45"; the concept path (`_select_products_for_concept`), the word path for kinds not understood (`_select_products_by_words`), the question when a word names several kinds; the condition gate | `src/picwise_providers/search_selection.py` |
| The catalogue a search reads, judged once per feed load (`SearchCatalogue`); the counts on the scanning screen; the suggestions | `src/picwise_providers/state.py`, `src/picwise_providers/suggestions.py` |
| The prepared feed: written by `tools/prepare_catalogue.py`, read instead of the feed when fresh and written by the same code | `src/picwise_providers/prepared_catalogue.py`, `state.py` (`prepare_feed_catalogue`, `_active_prepared_catalogue`, `prepared_catalogue_status`) |
| On Vercel: the build that prepares the feed, the daily scheduled job, the renewal route (`CRON_SECRET`, Deploy Hook) | `vercel.json`, `src/picwise_app/prepared_renewal.py`, `api/index.py` |
| Whether the feed says a product is not new (one rule for the gate and the cards) | `src/picwise_providers/product_condition.py` |
| Per shop, what each feed brings in and why the rest is held back (the build's note, `intake`) | `src/picwise_providers/feed_intake.py`, `state.measure_configured_feed_intake` |
| Resolver | `src/picwise_search/live_search_resolver.py` |
| Page text ("Understood as", "Only some of the four match: X (n of 4)", "could not match") | `src/picwise_surface/reference.py` |
| Did-you-mean / broad-suggestion injection, impression events, query log hook | `src/picwise_app/app.py` (`api/index.py` delegates to it) |
| Awin feed loading (`AWIN_FEED_URL` with 6 h reuse, `AWIN_FEED_FILE`) | `src/picwise_providers/awin_adapter.py` |
| Query log for NLU training (inactive until configured) | `src/picwise_app/query_log_sink.py`, `deployment/supabase_query_log.sql` |

Tools:

- `python -I tools/price_first_eval.py <feed.csv.gz> out.json [--cards] [--compare earlier.json]`
  — 118 buyer searches on a real feed file: what each page shows, and how long it took
- `python tools/prepare_catalogue.py [--feed-file F] [--out PATH] [--keep-going]
  [--static-dir DIR]` — the feed prepared once (step 5); a server reads it with
  `PICWISE_PREPARED_CATALOGUE_FILE`, a Vercel deployment from its own build
- `python tools/nlu_misspelling_benchmark.py` — 706 misspelled queries end to end
- `python tools/check_awin_feed.py --url "<feed link>"` — what a real feed will do
- `python tools/nlu_mistake_report.py queries.txt` or `--from-query-log` — lexicon review queue
- `python tools/build_picwise_search_artifact.py` — rebuild the search artifact

Docs: `docs/PICWISE_GOOGLE_PAGES_SPEC.md` (the pages for Google, the index, the server's
catalogue; 2026-10-23), `docs/picwise_misspelling_understanding.md`, `docs/awin_feed_setup_el.md` (Greek
guide for the owner), `docs/vercel_daily_feed_setup_el.md` (Greek: the prepared feed on
Vercel, every day), `docs/picwise_query_understanding.md`,
`docs/picwise_mission_decision_delivery.md`.

## Current numbers (local fixtures only)

- Misspelling benchmark: **93.8% pass, 0 wrong kind of product shown** (2026-10-17,
  after part 3b; 96.0% until 2026-10-16). It fell to 93.9% with the owner's rule that
  "mobile phone" and «κινητό» show basic phones, because 15 of its cases expect
  smartphones; those cases were left as they are so the number shows the rule.
- Test suite, last full run **2026-10-17** for step 5's second part (all modules but
  the two hour-long ones, one process per module, four at a time, after the commit):
  **238 of 240 pass**, 2,082 tests, 48 skipped; the two that fail are the same two as
  below. Misspelling benchmark unchanged (93.8%, 0 wrong).
- Before it, the same day for step 5's first part (all modules but the two
  hour-long ones, one process per module): **237 of 239 pass** with the contracts test
  run after the commit. The two that fail fail the same on the code before this work:
  `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`. At `deab42a` (step 4)
  `test_picwise_search_index_blind_evaluation_stage6a` failed one of its 13 tests, as
  before step 3 (about 43 min; run it on its own, as `test_picwise_learning_stage7b`,
  about 41 min, which passes).
- Older, kept for the history: full run **2026-10-12** after the description rule, the spec reader
  and the fixture updates (228 modules, every module except the two hour-long ones,
  one process per module, `PYTHONPATH=.`): **226 modules pass, 2 fail**, and both
  failures are the two that already predated this work. One module failed during the
  run and was fixed inside it -- `test_picwise_product_type_coverage_matrix`, whose
  weak-feed-opportunity case wrote a 47-character description, below the 120 the
  owner's rule requires, so its four rows stopped being showable; it passes on
  `9ac4bb8`. Two things to know before running it: the modules must be run with
  `PYTHONPATH=.` (several import `from src.picwise_...`, which fails when a module is
  run as a script from `tests/`), and `tests/` has no `__init__.py`, so
  `unittest discover` cannot load it -- run one process per module.
  Older note, kept for the history: full run 2026-10-08 after the F3/F4 fixes (224
  modules): **1,810 tests, 2 failures, 48 skipped** (skips need the operator's private
  feeds). The two failures predate all of this work and fail identically on `4475192`
  (checked in a clean worktree):
  `test_picwise_canonical_vocabulary_registry_stage2`,
  `test_picwise_search_index_generated_blind_stage4` (graph-alias leet records in the
  registry). `test_picwise_learning_stage7b` passes in about 41 min;
  `test_picwise_search_index_blind_evaluation_stage6a` takes about 43 min and, run on
  2026-10-16, fails one of its 13 tests ("amazon" and "galaxy" missing from its broad
  terms), the same on the code before step 3.
- Cold start through `api/index.py`, 19-row fixture: first request 677–724 ms, import plus
  first request 1,045–1,078 ms (target 1,500 ms). A real feed adds its download and parse.

## Waiting on the owner

1. ~~**Awin: link set, live result NOT VERIFIED.**~~ **Verified live on 2026-10-11**: a
   new feed (11,573 UK electronics products, category-based, Electronics only) is set
   in Vercel, `/private-beta-readiness` reports `provider_feed_ready`, and
   `/search?q=ακουστικα` returns four real headphones with one suggested, all in GBP.
   The owner's manual Redeploy works again (the GitHub App is installed), so an
   environment change no longer needs a commit. Older note, kept for the history: On 2026-10-10 the owner created a
   Create-a-Feed link (Legacy format, CSV, comma, gzip, a handful of UK advertisers in
   "Awin" datafeed format, about 15,000 products, GBP prices) and set it in Vercel as
   `AWIN_FEED_URL` (Production only, Secret). Next: check
   `/private-beta-readiness` shows `provider_feed_loaded`, then searches on the live
   site. Most of those advertisers sell kinds the concept lexicon does not know yet
   (flowers, wine, perfume, fashion), so many searches will truthfully show no four.
   `tools/check_awin_feed.py` now also reports how much of the feed is not new ("Not
   new (shown only when asked for): n of m eligible"), worth reading on the real feed.
1b. **Shops, not feed settings, decide what data PicWise has.** The owner asked on
   2026-10-12 whether the thin feed was a Create-a-Feed misconfiguration -- a
   reasonable guess, and it is answered: no. The feed arrives with **all 149 Awin
   columns**, nothing was left unchecked, and `specifications` is filled by three of
   its shops (Baccus 100%, 4x4 Predator 79%, LIKA 100%), so the column works and the
   emptiness is each merchant's own upload. Awin passes a merchant's file through
   unchanged, so no setting on the owner's side can make a shop send descriptions or
   specifications. What each shop sends, measured:

   | Shop | Rows | Description | Specs | product_type | Brand | EAN |
   | --- | --- | --- | --- | --- | --- | --- |
   | Boxed2me | 3,474 | 97% (median 598 chars) | 0% | 99% | 100% | 94% |
   | Aperturee | 1,802 | 100% (298) | 0% | 0% | 100% | 0% |
   | TV Cables | 1,745 | 81% (258) | 0% | 0% | 100% | 0% |
   | **Geekbuying** | **877** | **0% (column empty)** | 0% | 0% | 0% | 0% |
   | Cerqular | 672 | 97% | 0% | 100% | 100% | 11% |
   | Tooled Up | 423 | 98% | 0% | 0% | 100% | 100% |
   | 4x4 Predator | 109 | 100% | **79%** | 100% | 0% | 42% |
   | Baccus (UK) | 18 | 100% | **100%** | 100% | 0% | 0% |

   Two shops are worth naming. **Geekbuying** (877 products: the televisions, TV
   boxes, vacuum cleaners, robot vacuums and treadmills) sends a title, a price and
   nothing else -- no description, no product type, no brand, no EAN. **Xiaomi RO**
   (66 products) does send a `description`, but it is the product's own name repeated
   ("Xiaomi TV S Pro Mini LED 55'' 2026", median 27 characters), which is exactly the
   case `product_description.product_description_text` rejects. So the owner's lever
   is which shops go into the feed, and `tools/check_awin_feed.py` now prints this
   table for any feed so the decision can be made on measurement.

2. ~~**A feed that carries real product ratings.**~~ **Dropped by the owner on
   2026-10-15** (price first, see "Start here"). Kept as the record. The owner decided on 2026-10-11 that
   the recommendation must follow a product's rating rather than its price, and the
   current feed has none at all (`check_awin_feed.py` now reports this as "Products
   with a real rating"). Nothing changes in the ranking until such a feed exists:
   inventing a rating is forbidden. The owner is looking for Awin advertisers whose
   feed fills `rating` / `average_rating`; the way to tell is to build a feed with
   them and run the tool over it.

   What that feed does send was measured on 2026-10-11 over all 149 of its columns
   (11,573 electronics products), because the question "is a quality signal available
   at all?" cannot be answered by reading one column:

   | What | Filled |
   | --- | --- |
   | `description` (long text) | 92% |
   | `brand_name` | 83% · `mpn` 67% · `ean` 34% · `product_GTIN` 26% |
   | `aw_image_url` | 100% · `alternate_image` 37% |
   | `condition` | 63% |
   | `delivery_cost` 31% · `delivery_time` | 23% |
   | `stock_status` 23% · `stock_quantity` | 13% (`in_stock` is 100% but constant) |
   | `rrp_price` 10% · `saving` | 1% |
   | `product_short_description` 16% · `specifications` | 1% |
   | `keywords` 13% · `colour` | 7% |
   | **`rating` / `average_rating`** | **1%, every value "0"** |

   So the feed has no ratings and no usable specification column, but it does carry a
   description for nearly every product, and specifications are often written inside
   it. Measured per kind, products carrying at least one readable number (inches, W,
   Hz, mAh, GB, hours, metres) in title only vs. in title or description:
   headphones 19% -> 75%, speaker 49% -> 75%, camera 5% -> 47%, amplifier 69% -> 91%,
   microphone 0% -> 27%, charging_cable 96% -> 98%, television 78% (unchanged),
   projector 15% -> 24%, tv_box 32% (unchanged). And the kinds that stay empty either
   way: watch and smartwatch 9%, vacuum_cleaner 3%, backpack and phone_case 2%.

   Two things follow. Reading specifications from the description, not only the title,
   is the one route to a real quality signal from this feed -- and it is marketing
   copy, so a number found there needs to be tied to the product rather than to an
   accessory or a comparison ("better than 32 inch models"). And for whole kinds there
   is nothing to read at all, which is a decision for the owner, not a gap to paper
   over: their rule is that price must not decide, and ANTI_FAKE forbids inventing a
   quality signal, so those kinds can only show four and declare that no ranking
   signal exists.
3. **Supabase project for the query log — and for click/decision events.** Click and
   impression events live only in a per-process list today (audit D5), so production
   records no click durably. None of the account's three projects is PicWise's (one
   inactive, `taxi-chat` belongs to another app, `mysubby.cloud@gmail.com`). Do not
   create tables in them without the owner saying which; a new project may cost money,
   so ask first. The owner said on 2026-10-08 to decide this later: create nothing.
4. Optional: allow `productdata.awin.com` in the cloud environment's network settings so
   a session can check the real feed, and `picwise.subby.cloud` so a session can check
   the live site itself (the owner asked on 2026-10-18 why Claude does not look itself:
   this conversation could not reach the site, DNS refused by the network policy, and
   had no Vercel connection). Steps: the cloud environment menu in the session's title
   bar, Edit, Network access, Allowed domains
   (https://code.claude.com/docs/en/cloud-environments#network-access). A Vercel
   connection for SUBBY CLOUD (claude.ai/customize/connectors) may let a session read
   the builds; both take effect in a new session.

## Next engineering steps, in order

0. **Price-first plan** (`docs/picwise_price_first_plan_2026-10-15.md`): the founding
   files were changed to it on 2026-10-16. Measured on the third feed, and built in
   small tested steps in the order recorded there. **Step 1, only the kind asked for,
   is done** (section "Step 1 built"; `tests/test_picwise_strict_kind_reading.py`), and
   so is **step 2, English before greeklish** (section "Step 2 built";
   `tests/test_picwise_english_over_greeklish.py`). **Step 3, the price-first
   engine, part 3b and step 4, the search page, are done too** (sections "Step 3
   built", "Part 3b built", "Step 4 built"; `tests/test_picwise_price_first.py`,
   `tests/test_picwise_search_page.py`). Next is step 5, data prepared daily (see
   "Start here" for its first speed-up). The plan's "engineering, later" section lists
   what is still needed: `custom_6` for tyres, a category for Living and Home, and a
   store refreshed daily.

0. ~~Every product shown carries availability, a price, an image and a description.~~
   **Done, 2026-10-12** (owner rule; recorded in `docs/PICWISE_DECISION_CONTRACT.md`,
   section "What a product must carry to be shown"). The first three were already
   required for a card; the description is new, lives in
   `picwise_providers.product_description`, and is read by both the card gate and
   `tools/check_awin_feed.py`. It costs 1,495 of the real feed's 11,573 products, and
   the cost is per shop, not per kind: Geekbuying (877) and Xiaomi RO (66) send no
   descriptions at all, so the kinds only they carry -- televisions, TV boxes, vacuum
   cleaners, robot vacuums, treadmills, and nearly all watches, smartwatches and
   projectors -- no longer appear. The owner was told before it went in. The feed tool
   prints it per shop so the choice (ask the shop, or drop it from the feed) is visible.
   Two gotchas found while doing it, both now fixed: `tools/check_awin_feed.py` was
   reporting the **feed** eligibility gate under the name of the **card** gate, so it
   claimed 11,573 of 11,573 showable when the real number is 9,954; and every provider
   fixture in `tests/` needed a description, which `tests/fixture_support.py` now
   supplies in text that names no product, because a description is a field the search
   ranks on and fixture text mentioning the product would hand each row free evidence
   for its own kind.
   `tests/test_picwise_product_description_rule.py` (14 tests).

0. ~~Refurbished / used products must appear only when the buyer asks for them.~~
   **Done, 2026-10-10, on `main` since 2026-10-11** (owner decision; recorded in `docs/PICWISE_DECISION_CONTRACT.md`,
   section "Item Condition"). A product the feed calls not new is no longer a candidate
   at all unless the query asks for that condition; when it is asked for, those come
   first, missing slots fill with new products, and the page says how many of the four
   are the condition asked for. `tests/test_picwise_condition_request.py` (22 tests).
   Still open from the same list: the ranking formula with scores
   (`Ranking formula weights: TODO` in the Decision Contract) — the owner decides the
   weights, do not invent them.
1. When the real feed is available: run `check_awin_feed.py`, add concepts for the feed
   types it does not recognise (correctly spelled names only), add held-out cases for
   them, rerun the benchmark — wrong answers must stay at 0. Also check, on the real
   feed, how `in_stock` / `stock_status` / `is_for_sale` are populated: a flag column
   that is identical on every row is treated as unpopulated, a varying one is read.
   Re-run the audit's runtime probes against it (open items in the audit's status table).
2. Cold start on a large feed: every serverless cold start downloads and parses the
   whole feed once. Build a prebuilt eligible-product artifact and measure against
   section 9.
3. Once the query log is connected: review `nlu_mistake_report.py --from-query-log`
   regularly.
4. Merge the word-level NLU (`build_local_nlu_intent`, still `insufficient_data` for
   Greek) and the concept reading into one layer.
5. Investigate the two pre-existing registry failures.

## Known doc conflict (unresolved, owner's call)

**Settled on 2026-10-16:** the price-first plan contradicted `concept.picwise.txt`,
`docs/MISSION.md` and `PROJECT_RULES.md`; the owner chose to change them, and they
were changed (details in `docs/picwise_price_first_plan_2026-10-15.md`).

**Raised on 2026-10-23, the owner's call:** `concept.picwise.txt` section 17 ("SEO
Strategy — Waves Model") and `docs/SEO_WAVES_SPEC.md` ("Each landing targets a specific
purchase-intent query") speak of thousands of landings, one per long-tail query.
Google's guide to generative AI features (May 2026) calls separate content for every
wording of a search scaled content abuse. `docs/PICWISE_GOOGLE_PAGES_SPEC.md` follows
Google: one page per distinct set of products, never per wording. The two files are
unchanged until the owner says so.

Older, and still open:

Three files still describe the project as being in the documentation-only phase:

- `docs/MISSION.md` → "First Phase Boundary": no frontend, no backend implementation
- `PROJECT_RULES.md` section 12 → "Do not build live product UI until mission docs and
  contracts are created and reviewed"
- `docs/IMPLEMENTATION_ROADMAP.md` → "Current Phase: mission/spec/contracts foundation"

Reality: the app is built and deployed (`PROGRESS.md` stages 16-26, stage 22 live on
`picwise.subby.cloud`). So this text is out of date, not a live instruction to stop.
Every other part of `MISSION.md` — the 4+1 contract, the identity rules, the trust and
neutrality commitments — is current and binding. Nothing was changed in these three
files: correcting the phase wording is the owner's decision, not the engineer's.

## Working gotchas

- Run tests **per module**, a few in parallel; never the whole suite in one process
  (out of memory, hours).
- The prepared file leaves out the Awin columns no rule reads
  (`prepared_catalogue.LEFT_OUT_COLUMNS`). A rule that comes to read one of them must
  take it off that list: answered from the file, it would see the column empty. A test
  in `tests/test_picwise_prepared_catalogue.py` fails while a listed column is named in
  the code that reads feed products.
- A prepared feed file is tied to the code that wrote it: any change to a file under
  `src/picwise_providers` or `src/picwise_nlu` makes old files unusable (the server then
  reads the feed). Prepare again after such a change. Outside Vercel a server reads one
  only when `PICWISE_PREPARED_CATALOGUE_FILE` names it, so tests never pick one up.
- `vercel.json`: a `builds` key makes Vercel skip the build command, so the file would
  silently stop being built; the rewrites point at `/api/index` (the function's name
  without `builds`); Vercel refuses an empty `outputDirectory`, which is why the build
  writes `public/prepared.json`. To see what a change does to a deployment without
  Vercel: `npm install vercel` in a scratch folder, a copy of the repository with a
  hand-written `.vercel/project.json` (`{"projectId":"x","orgId":"y","settings":
  {"framework":null}}`) and `.vercel/.env.production.local` naming a feed file, then
  `vercel build --prod --yes`, and read `.vercel/output` (no login needed).
- The daily renewal is a new production deployment each morning. After an Instant
  Rollback, Vercel stops putting new deployments live until one is promoted by hand
  (as remembered, not checked from here): the renewal would then build every day and
  never go live, and the live file would pass its 30 hours. `prepared_feed` on
  `/private-beta-readiness` shows it (`too_old`).
- Tests rewrite `src/picwise_search_memory/artifacts/search_runtime_v1.json.gz`
  (`built_at` only). `git restore` it before committing.
- `test_picwise_search_graph_contracts_stage1db1` fails while `app.py`,
  `live_search_resolver.py` or `reference.py` have uncommitted changes (it diffs the
  working tree against HEAD); it passes after the commit.
- Changing a file listed in `search_runtime_artifact.get_fingerprint_source_paths()`
  requires rebuilding the artifact, or every cold start rebuilds the index live.
- Two route tables: `src/picwise_app/app.py` (local server) and `api/index.py` (Vercel).
- The cloud environment blocks `productdata.awin.com`, `ui.awin.com`, `api.awin.com` and
  `picwise.subby.cloud`.
- A `pkill -f` or `grep` pattern that matches its own command line kills the shell.
- Fixtures use fictional brands, `.invalid` URLs and `data_provenance=local_test_fixture`.
- Secrets: the Awin link contains the account API key; the Supabase `service_role` key.
  Only as Vercel environment variables — never in the repository, a log or a chat.
- `picwise_buying_pages/fixtures.py` (`load_seed_buying_pages`) is fabricated test data
  (formula prices and ratings, "Picwise Demo" products). It must never back a public
  route; `/best/<slug>` and the sitemap publish nothing until pages are built from real
  feed data. `test_picwise_no_fabricated_public_pages` guards this.
- Availability (`offer_health`): every column is read; a stock **word** ("out of stock",
  "OutOfStock", "discontinued", "pre-order") decides wherever it appears; a bare **flag**
  (0/1) decides only where its column varies across the feed. Selection, card fields,
  recommendation and redirect share one context built over the whole feed — pass it on
  (`feed_ctx`) rather than building a new one from a subset.
- Product identity is GTIN, else brand + MPN (`_product_identity_key`); count products,
  not offers, anywhere a "four" is decided.
- Kind of product (`annotate_product_concepts`): only the words before the first purpose
  word ("for", "with", "για", "με") name the product. Text that names a product only after
  one ("Accessories for Laptops", "Filter for Coffee Machine") is an accessory of it and
  is marked `__accessory__` — never left unread, because a row naming no kind can still
  join a concept by its own words. Accessory words after "with" are what comes in the
  box. Audit finding F4, `test_picwise_product_kind_reading`.
- Accessory penalty (`_title_accessory_penalty`): for a product already verified as the
  kind asked for, accessory words before or inside its name are its type ("Filter Coffee
  Machine", "Battery Lawn Mower", "Stand Mixer"); a part word anywhere, an accessory word
  after the name, a name only after "for", or a Greek name keep the full penalty.
- **What kind of product a feed row is** (`concept_understanding.annotate_product_concepts`),
  tightened on the first real feed, where it answered searches with the wrong kind
  (899 table runners under "τραπέζι", lens caps under "καπέλο", disco balls under
  "μπάλα", USB cables under "οθόνη"). Four rules, each pinned by
  `tests/test_picwise_feed_kind_truth.py`:
  (1) **weak names** (`~word` in the concept table: cap, ball, ring, screen, desktop,
  pc, tripod, controller, mixer, cover) are read from a query but never classify a feed
  product, because in feed text they are almost always part of something else;
  (2) **tail words** (`_MODIFIER_TAIL_WORDS`: runner, mats, ties, clip, ball, light,
  restore…) turn the name before them into a description: "table runner", "cable ties";
  (3) a **category breadcrumb** is read shelf by shelf — the first shelf that names a
  product wins ("Electronics > Cables > Monitor" is cables), any shelf of accessories
  decides for the whole crumb, a shelf naming a product only in passing ("Power banks
  and batteries") names nothing, and a shelf of two kinds is decided by the title
  ("Fans & Heaters");
  (4) when **only a title** says what the product is, a word PicWise cannot read right
  after the name voids it ("Truck Bed Tailgate Extender"), while a colour, spec or pack
  word does not ("Smartwatch Black Dial"). Also: a product type that names what the
  product plugs into ("Smartphone USB-C" on a microphone) gives way when the title and
  the category agree on another kind.
- One currency per answer (owner decision, 2026-10-11, in the Decision Contract):
  `_price_first_products` keeps the currency most of the answer's products are priced
  in, since prices in two currencies cannot be put in one order.
- Condition (`product_condition.py`, one rule for the gate and the cards): a product
  the feed calls not new is shown only when the query asks for that condition. "Not
  new" = a condition column carrying a word from the vocabulary ("Used - Very Good",
  "Refurbished Grade A", "gebraucht"), or such a word in the product's own text
  ("Refurbished Dell"; "used" and "renewed" are read from the column only, not from
  marketing copy). Wording the vocabulary does not hold ("A-stock", "Nuovo", "n/a", a
  bare code) is unknown, not non-new, and stays visible — the reverse would empty a
  whole feed in silence. `check_awin_feed.py` lists the condition values it could not
  read; a real one that means "used" belongs in `product_condition.py`. The request is read from the
  query by `read_condition_request` (Greek, greeklish, English, with typo correction)
  and is never matched against feed text. Asked for, under price first: the answer
  is the products in that condition; when the feed has none, it is the new ones and the
  page says the condition was not matched. The text scan
  sits behind a substring pre-filter for speed (38 ms for 15,000 products, worst case);
  a vocabulary word added without its hint would stop being read, which
  `test_picwise_condition_request` guards.
- Which four are shown: **replaced by price first** (steps 3 and 3b, built
  2026-10-16/17, for every search). Kept as the record of the old rule (owner decision, 2026-10-08, confirmed with its details and
  recorded in the Decision Contract): groups of substantially equivalent products in
  relevance order; a group too big for the free slots is spread across its price range
  (four slots: cheapest, two between, dearest; two: cheapest and dearest; one: the
  middle). All equivalent: the cheapest is recommended and the card says why.
  Merchant free text (keywords, description) never makes a product "more relevant" —
  not for the four, not for the recommendation. `test_picwise_price_range_diversity`.
- A test that renders an empty query schedules a 0.75 s background warm-up; reset it
  (`search_warmup._reset_search_warmup_for_tests`) or it can land in a later test.
- Probe the real path with the deployed entrypoint (`api.index.app`) in-process; the
  audit's probe and adversarial-feed scripts are described in its "Reproduction" note.
