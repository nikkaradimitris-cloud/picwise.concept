# PicWise: the categories the site shows, a switch for each (rules)

Written 2026-11-23 (afternoon, Athens), on the owner's «Ναι ξεκινάς». **In force from its
deployment of 23/11 (section 10), on his «Ανέβασε ότι έχεις φτιάξει στο site ανέβασε όλες τις
υλοποιήσεις» (18:25 Athens): the list's switch (`"on"` at the top of `data/category_switches.json`)
is true.** Turned off again only on his word.

Each rule names whose it is:

- **Owner**: his words, with the day.
- **Proposed**: written here so that his decisions work; his to change (section 3.2 lists
  them, each a line of the list he can turn).

## Σύνοψη για τον ιδιοκτήτη

- **Τι κάνει.** Ένα αρχείο με μία γραμμή για κάθε κατηγορία και υποκατηγορία της Google
  (419 γραμμές), με ελληνικό όνομα και ✅ ή ❌. Ένα προϊόν φαίνεται μόνο όταν η κατηγορία που
  του έδωσε το AI είναι ανοιχτή, μαζί με όλες όσες είναι από πάνω της. Αν κλείσεις μια
  κατηγορία, κλείνουν και όλες οι υποκατηγορίες της.
- **Τι μένει** (όσα αποφάσισες στις 22 και 23/11): σπίτι & κήπος (συσκευές, κουζίνα,
  φωτισμός, κήπος, ασφάλεια σπιτιού), έπιπλα, εργαλεία, τεχνολογία με τα κομμάτια
  υπολογιστή και τις βάσεις τηλεόρασης, φωτογραφικές, ρούχα και παπούτσια, κοσμήματα και
  ρολόγια, τσάντες, γυαλιά ηλίου, ζώνες, καπέλα, κασκόλ και γάντια, παιχνίδια, αθλητικά,
  βιντεοπαιχνίδια, αρώματα, λάστιχα αυτοκινήτου.
- **Μεγάλες κατηγορίες που δεν είχαμε συζητήσει** (23/11): σε ρώτησα για όλες. Άνοιξαν τα
  αθλητικά και, από το αυτοκίνητο, μόνο τα λάστιχα. Έμειναν κλειστά τα βιβλία, μουσική &
  ταινίες, τρόφιμα & ποτά, τέχνες & χόμπι, γραφική ύλη, επαγγελματικός εξοπλισμός,
  προϊόντα ενηλίκων και θρησκευτικά. Από εδώ και πέρα, καμία μεγάλη κατηγορία δεν κλείνει
  χωρίς να σε ρωτήσω.
- **Τι φεύγει:** όλα τα υπόλοιπα, και μέσα στις κατηγορίες που μένουν τα αξεσουάρ, τα
  αναλώσιμα και τα ανταλλακτικά (καλώδια, φορτιστές, μπαταρίες, θήκες, προστατευτικά οθόνης,
  τηλεχειριστήρια, μελάνια, λουράκια ρολογιών, εσώρουχα και κάλτσες, είδη τζόγου κ.λπ.).
- **Ελάχιστη τιμή (24/11):** κάθε κατηγορία έχει δικό της κατώτατο ποσό (πεδίο `min`, σε λίρες, 95 γραμμές:
  π.χ. αρώματα £10, καναπέδες £100, παπούτσια £15, κινητά £50; οθόνες £40 και καναπέδες £100 από £60 και £150 στις 24/11 το απόγευμα, αφού φάνηκαν πραγματικά προϊόντα κάτω από αυτά). Προϊόν κάτω από αυτό δεν φαίνεται πουθενά.
  Μια υποκατηγορία χωρίς δικό της ποσό παίρνει της κατηγορίας από πάνω της. Υπάρχει και στις κλειστές, για
  όταν ανοίξουν. Η αρχική σου λέξη, 23/11, ήταν «Κανένα όριο σε αυτό το επίπεδο»· στις 24/11: «κανένα προϊόν
  μέσα στα αρώματα δεν μπορεί να έχει λιγότερο από 10 λίρες ... όλες τις κατηγορίες και υποκατηγορίες ... ένα
  ελάχιστο ποσό», και στην πρόταση «Τα εγκρίνω όπως είναι».
- **Πού μπαίνει:** στην προετοιμασία της νύχτας, πριν από όλα τα άλλα όρια. Το όριο των
  20.000 ανά κατάστημα και το 15% ανά κατηγορία μετράνε μόνο όσα μένουν, και το bot δεν
  χάνει χρόνο σε προϊόντα που φεύγουν.
- **Προϊόν χωρίς κατηγορία ακόμα:** δεν το αποφασίζει η λίστα. Το κρατούν οι έλεγχοι μέχρι
  να πάρει κατηγορία από το AI, όπως και σήμερα.
- **Όταν κάποιος ψάχνει κάτι που δεν καλύπτουμε:** κάτω από το «No products found» γράφει τι
  καλύπτει το PicWise.
- **Ο γενικός διακόπτης** είναι ανοιχτός από το «ανέβασε» σου της 23/11 (18:25). Κάθε βράδυ
  μετριέται πόσα προϊόντα έχει κάθε γραμμή.
- **Αν ξανακλείσει μετά το «ανέβασε»:** τα προϊόντα γυρίζουν σταδιακά, όσο τα ξαναελέγχει το
  bot, όχι την ίδια μέρα.
- **Μέχρι το διαχειριστικό:** κάθε αλλαγή στη λίστα περνάει με ένα «ανέβασε», όπως οι άλλοι
  διακόπτες.

## 1. What it is for

**Owner, 2026-11-22** (a conversation, "just talking, building nothing"): «Τι θα έλεγες άμα
κάναμε λίγο πιο συγκεκριμένες τις κατηγορίες για παράδειγμα αυτές που είναι που
προβληματικές τώρα ... να της αφαιρούσαμε τελείως». Which stay: «Σπίτι κήπος ...τεχνολογία ..ένδυση υπόδηση..
κρατάμε και τα δαχτυλίδια ρολόγια αξεσουάρ», then «Βάλε και παιχνίδια». The rule of the
subcategories: «Όλο το παιχνίδι είναι στις υπό κατηγορίες από κει μπορούμε να βγάλουμε
αρκετές οι οποίες έχουνε με κρίση [μικρής] αξίας προϊόντα ή προϊόντα τα οποία δεν μπορούν να
ταυτοποιηθούν εύκολα». Out: «Δεν θέλω τα βρεφικά»; «Και τα είδη pet shop έξω.. όπως και τα
είδη καλλωπισμού.. όλες αυτές οι αταξινόμοι της αηδίες έξω από το site»; «Καλώδια αντάπτορες
φορτιστές προστατευτικά οθόνες θήκες κινητών τηλεχειριστήρια μπαταρίες ραντάρ ... αηδίες
έξω». Agreed, line by line as proposed: furniture, tools and cameras in, luggage and baby out;
of home & garden appliances, kitchen, lighting, garden and home security in, cleaning and
consumables, decor, appliance parts, plants and seeds, smoking out; of electronics the
computer's parts (graphics cards, processors, SSDs, memory, keyboards, mice) in; of fashion
underwear and socks, baby clothes, costumes and shoe accessories out, watch straps, piercing,
key rings, hair accessories and small things out; of toys accessories, small toys and the
gambling Google files with games out; of furniture its accessories and baby furniture out; of
tools only the tools themselves («Ναι συμφωνώ»). Perfume kept from beauty: «Ωραία κρατάμε τα
αρώματα» (Claude had disagreed: perfume is the fourth of the UK's ten most searched, on the
home page's panel, and of high value with brands and barcodes).

**Owner, 2026-11-23**, asked of what had not been talked over: bedding, pools and hot tubs,
fireplaces and stoves, smoke and CO alarms out («Φεύγουν όλα αυτά»); video games, television
mounts, hats, scarves and gloves in, ink and toner out; no lowest price at this step
(«Κανένα όριο σε αυτό το επίπεδο»); and how: «Να δημιουργήσεις έναν διακόπτη για κάθε μία
κατηγορία και υποκατηγορία αυτής έτσι ώστε όταν φτιάξουμε το διαχειριστικό να μπορεί ένας
άνθρωπος με το χέρι να ανοίγει να κλείνει μία κατηγορία σκέψου έναν πρακτικό τρόπο χωρίς
πολλά μπερδέματα ή κώδικες». The way proposed (one file, a line a category, a Greek name, ✅
or ❌, one rule, every top line of Google's on it, each line's count each night, one switch
for the whole) and his «Ναι ξεκινάς».

**Owner, 2026-11-23, 18:16**, told after the look that car tyres left with the closed vehicles:
«Ποτέ δεν αποφασίσαμε ότι κλείνουμε τα λάστιχα και ποτέ δεν σου είπα εγώ κάτι τέτοιο». So it
was: the list kept only what he had named, and Claude had written "car" among "all the rest
leave" without asking of it apart. Asked then of every top category closed without being talked
over (18:20): of the vehicles «Μόνο τα λάστιχα»; sports opened («Αθλητικά»); media, food, arts and
hobbies, office supplies and business and industrial left closed («Καμία από αυτές»); mature and
religious, told and not asked, left closed. **From then: no top category is closed without his
word** (the rule the dashboard to come keeps too).

What it is not: the wrong products of a kind (tablets that are pills, watches that are straps
as a kind's search) are the kind's rules' (`PROJECT_RULES.md` 2, "The main kind only";
`docs/PICWISE_KIND_ITSELF_RULES.md`); asked on 22/11 whether a mechanism already did that, the
owner was told yes, and a lowest price per subcategory was kept for products of little value,
not for wrong ones. The owner, 22/11, on PicWise itself: it is not a price comparison site.

## 2. The list and its one rule

- **The file** (`data/category_switches.json`): `on`, the whole rule's switch (**Owner**,
  23/11: one switch over it all, false until his «ανέβασε»); `lines`, one line a category or
  subcategory of Google's taxonomy: `google` (the line, as Google writes it; the program reads
  it), `name` (in Greek, for the owner and the dashboard to come), `on` (true open, false
  closed), and on some lines `site` (the words a visitor is told). One line of the file a line
  of the list. **Proposed.**
- **The rule** (**Proposed**, his «Ναι ξεκινάς»): a product is shown only when the line the AI
  gave it (`ai_shelves`; the checks' rules 5.5) is under a top line of the list and no line
  of the list above it, its own included, is closed. A closed category closes everything
  under it; a level the list does not name takes its parent's word; a top line not on the
  list is closed (every top line of Google's is on it). Spaces and case do not count.
- **What the list does not decide**: a product the AI has given no line yet, a line "no line
  fits", a refusal, or a slip (`ai_shelves.SLIP_LINES`): the checks hold a new one at their
  gate until it has its line, and cut one with none (their rules 5.5). With no answers of the
  AI at all, or a list that cannot be read (a line twice, an `on` neither true nor false),
  nothing is decided and the night's note says why. The list never stops a night: should it
  fail, every product stays and the note gives the error's kind (`settle_or_keep`). **Proposed.**
- **Which line counts**: the AI's, for every product of either link (the same rule for both
  feeds, owner, 20/11), not the shop's own: the AI's line is the one the checks and the kinds'
  lists read.
- **Every subcategory listed where some are**: where the owner kept part of a category, every
  subcategory of it is a line of its own, so that the dashboard to come shows each one; one
  exception, a single line under the 80 tools (`Hardware > Tools > Lighters & Matches`).

## 3. What is closed

### 3.1 The owner's decisions

Read from the list itself; its test (`tests/test_picwise_category_scope.py`,
`test_the_owners_decisions_line_by_line`) pins them with the switch read as on.

- Open top lines: Home & Garden, Furniture, Hardware (its Tools only), Electronics, Cameras &
  Optics, Apparel & Accessories, Toys & Games, Sporting Goods (23/11), Software (Video Game
  Software only), Health & Beauty (Perfume & Cologne only), Vehicles & Parts (Motor Vehicle
  Tires only, 23/11).
- Closed top lines, by his words: Baby & Toddler («Δεν θέλω τα βρεφικά»), Animals & Pet
  Supplies («τα είδη pet shop έξω»), Luggage & Bags (22/11, read as out with the baby items and
  not contested since); asked on 23/11 18:20 and left closed: Media, Food, Beverages & Tobacco,
  Arts & Entertainment, Office Supplies, Business & Industrial; told then and left closed:
  Mature, Religious & Ceremonial.
- Inside the open ones, closed as he decided: the accessories, consumables and parts named in
  section 1, and the lines of 23/11.

### 3.2 Proposed, each a line he can turn

Lines his words did not name, set to follow them:

- In: camera lenses (of the cameras' accessories, the rest out); motherboards (Google files
  them under circuit boards, whose other lines are out); television mounts with every video
  accessory; uniforms and sleepwear among clothes; toy blasters, bath toys and ball pits among
  toys; dice and card games among games; every line of audio but its accessories; the
  communication lines but their accessories.
- Out: light bulbs (named with the consumables on 22/11) and lighting accessories; kitchen
  appliance accessories and food storage accessories; tool accessories; lighters and matches
  under tools; laptop, tablet and e-reader parts, input device accessories, USB hubs and
  server racks under computer components; development boards (Arduino and the like); GPS,
  marine electronics, radar, toll devices and arcade machines; computer software and digital
  goods; the photography studio and darkroom; weapon scopes; tripods; earmuffs, neck gaiters,
  balaclavas, neckties, cufflinks and the other small clothing accessories.

## 4. Where it stands in the night

- In the preparation (`state.prepare_feed_catalogue`), on every product a card can show,
  before anything counts products: the answers to "is it the kind itself", how many of a
  shop's products pass, the cap of a category, the bot's candidates and the AI's next
  questions see only what the list lets through. So a shop's 20,000 and a category's 15%
  are counted over the products that may be shown. **Proposed.**
- The cut products the feed still lists, which the bot asks again on their schedule (the
  checks' rules 8.1), are not those of a closed category (`category_scope.passing`): the
  bot's time goes to what may be shown. **Proposed.**
- Frozen with the code (`prepared_catalogue._FROZEN_FILES`): a change to the list prepares the
  catalogue again at the next deployment, as every switch does.
- With the switch off nothing leaves, and the night still counts (section 6).
- With it turned off after being on, what it closed comes back through the checks' gate, as
  candidates the bot asks, not at once (as for the shops' rule, the checks' rules 20.7.5).

## 5. What the site says

Under "No products found", after the two searches to try (owner, 13/11), with the switch on:
"PicWise covers home & garden, furniture, tools, electronics, cameras, fashion, jewellery &
watches, toys & games, sports & outdoors, video games, perfume and car tyres." Made of the `site` words of the open lines,
a line's left out where a line above it already says it, in the list's order
(`category_scope.site_words`). **Proposed** (the owner, 22/11, agreed to an honest line in
place of an empty page; the words are his to change). With the switch off, nothing changes.

## 6. The night's note and the health run

- The public note of the preparation (`prepared.json`, `categories`): whether applied; of the
  products a card can show, how many open, closed (or, the switch off, that it would close),
  with no line from the AI; each line of the list with how many products a card can show are
  under it and whether it is open; the shops it closes most of. The dashboard to come reads
  its counts here.
- The preparation's log: one line, `prepare_catalogue: the categories' list: ...`.
- The health run (`deployment/server/print_health.py`): one line, `categories: ...`.

## 7. The look before the «ανέβασε»

`.github/workflows/server-look-category-switches.yml`, run by pushing the work branch's head to
`claude/category-switches-look`; read-only, no shop asked, no AI. The catalogue prepared on
GitHub's runner from copies of what the server prepared from, the list's switch off (as the
site runs) and on, each with the two nights after (every candidate taken as asked and passed);
`deployment/server/look_shop_rule.py compare` sets them side by side (products per shop,
category and kind, the kinds that fall under 4, 24 and 100, every kind's own search and the 40
searches' first cards, the time and the memory); `deployment/server/look_category_switches.py`
prints each line of the list with its count and, of what the site shows today, what the list
would close, by line and by shop. What it found: section 9, once it has run.

## 8. What is built (2026-11-23)

- `data/category_switches.json`: the list, 419 lines (385 until 23/11 18:20), its switch false.
- `src/picwise_providers/category_scope.py`: the list read (again when it changes), the rule,
  the night (`settle`, `settle_or_keep`), the bot's cut products (`passing`), the site's words (`site_words`).
- `src/picwise_providers/state.py`: the list applied in the preparation.
- `tools/prepare_catalogue.py`: the cut products for the bot, the note's `categories`, the log's
  line.
- `src/picwise_providers/prepared_catalogue.py`: the list among the frozen files.
- `src/picwise_surface/reference.py`: the words under "No products found".
- `deployment/server/print_health.py`: the health run's line.
- `deployment/server/look_category_switches.py` and the look's workflow.
- `tests/test_picwise_category_scope.py`.

**Not built**: a lowest price per subcategory (the owner, 23/11: none at this step); the
dashboard, which will turn these same lines (until then a change is a commit and an
«ανέβασε»); the 15% and the 12,000 a category, which stay as they are until the look's
numbers say whether they should move.

## 9. What the look found

**The first look was of the list before the owner's answers of 23/11 18:20 (sports and tyres
closed then); the look of the list as it is now follows it (9.2).**

### 9.1 The list as built at `08c9dcc`

Run 45199357636 (`claude/category-switches-look` at `32f2478`, the list as built at `08c9dcc`),
23/11 from 14:55 UTC; read-only, no shop asked, no AI; the catalogue prepared on GitHub's runner
from the server's copies of 23/11, the list's switch off (as the site runs) and on.

- **Of what the site shows today**: of the 199,770 products, the list would close 86,745 and
  keep 113,010 (15 have no line from the AI). Of the 1,608,044 products a card can show,
  320,669 closed, 483,993 open, 803,382 with no line from the AI (not decided by the list: the
  checks hold them, 5.5).
- **The site, night by night**: the first night with the list on 113,026 products of 104 shops
  (199,770 of 132 with it off); the night after, every candidate taken as asked and passed,
  147,245 (215,873 off); two nights after 148,201 of 105 shops (219,962 of 134 off): about a
  third fewer than without it, once the bot has filled the places the list frees.
- **Closed most of what the site shows**: media 7,479, decor 6,345, ink and toner 4,566,
  vehicles (mostly tyres) 4,540, household supplies 4,165, food 3,894, arts and hobbies 3,145,
  office supplies 3,125, pet supplies 3,066, sports 2,857, mobile phone accessories 2,520, power
  2,017; each line's count is printed in the run's log ("each line of the list").
- **Shops**: 29 have no product two nights after (Tyres UK, Tirendo UK, and small shops of
  beauty, food and health); closed most: PCHUB.UK 9,391 (keeps 10,577), Plusshop UK 8,735,
  GamingKit 8,279, Bazta UK 8,036, InStock UK 6,583, MoreThisWay 5,341, Lets Buy Books 4,318
  (keeps 38).
- **The cap of a category**: 12,000 the most before and after; the 15% cut nothing more (what
  Claude had feared on 22/11 did not happen).
- **The kinds**: with no product 0 and 78, under 4 products 19 and 103, under 100 116 and 162,
  all of closed categories (tyres, cables, ink, bedding, backpacks, shampoo...); gaining:
  printer 172 to 1,058, headphones 1,914 to 2,737, camera 1,015 to 1,664, monitors, earrings,
  routers, televisions.
- **The 40 searches**: those of open categories the same or more (earrings 773 to 1,071,
  monitor +93, watches +55, smartphone +23); those of closed ones empty (car tyres, phone
  charger, shampoo, dog bed, backpack, suitcase).
- **Perfume**: 152 to 154; its first cards are body sprays at £0.95 to £2.49 (Plusshop UK,
  Bazta UK), the owner's own example of 22/11 (a deodorant among the colognes). A lowest price
  for perfume (£15, proposed on 22/11) would take them away; none at this step, his word.
- **Saunas** (979 to 16, under pools and spas) and **car tyres** (8,193 to 0): products of high
  value that leave by lines he closed; each opens again with its line.
- **The preparation**: 12.7 minutes and 13.87 GB with the list on (13.8 and 14.19 off).

### 9.2 The list with sports and tyres open

Not looked at, on the owner's word (23/11, 18:23): «Σταμάτα τη μέτρηση για οικονομία χρόνου δεν
με ενδιαφέρει». Its run (45215601358) was cancelled and nothing of it read. The numbers of 9.1
are of the list with sports and tyres closed: with them open the site keeps more of both.

## 10. The «ανέβασε» (23/11)

The owner, 23/11 18:25 Athens, after he had stopped the second look: «Ανέβασε ότι έχεις φτιάξει
στο site ανέβασε όλες τις υλοποιήσεις». The list's switch true (with `set` and `by`), the test
that pinned it off now pinning his word; deployed with what else waited on the work branch for his
«ανέβασε»: the mend of the places a full shop's own copies hold (the checks' rules 20.9). Two
deployments, for the server's memory (as on 22/11 and 23/11): first one that restarts the site
and prepares nothing, then the one that prepares. Task 6's switch stays false: its own look is not
built; he was told.

- **Tests before it**: every fast module on its own with the switch true, 356 modules, 3,422
  tests: 354 pass, 2 fail as known.
- **The restart** (`1d72786` on the site's branch, run 45216959687, 16:28 UTC): "not prepared
  again: the change does not concern the catalogue", the site restarted on the file in place.
- **The deployment** (`64ec701`, run 45219096369, release `20261123T164018Z-64ec701`): the bot
  stopped, the catalogue prepared in 30.6 minutes, peak 14.48 GB; the site restarted 17:13 UTC on
  it, 2.9 GB; 15 of 15 pages the same on the server and live, 12 of 12 searches the same cards.
- **The catalogue: 118,048 products of 109 shops** (199,771 of 132 that morning; the look of the
  list with sports and tyres closed had said 113,026 for the first night). The places the list
  frees fill as the bot checks its candidates, night by night.
