# PicWise: the AI layer (spec)

Written on 2026-11-05 for the owner's approval, before anything is built
(`PROJECT_RULES.md` section 4: no implementation before its spec). **Nothing in it is
built.** Status: the owner, the same day, «παμε για το απι κευ»: going ahead with the
account and the key (4.6), taken as a yes to this spec, which the owner was told.

The architecture is the owner's of 05/11: «Εντάξει, πάμε σε άλλη συζήτηση συμφωνώ με την
αρχιτεκτονική και την εγκατάσταση Haiku», then «Σταματάμε εδώ αυτή τη λογική της
απασφαλμάτωσης είδος με είδος θέλω να προχωρήσουμε στην υλοποίηση της ένταξης του
συστήματος ai». How it came about is in `docs/picwise_session_handoff.md` (first section,
"Approved by the owner 05/11"). This spec says how each of its three parts works, what it
may never do, how it is measured before it counts, and what the owner decides at each
step.

## Σύνοψη για τον ιδιοκτήτη

- **Τρία κομμάτια, αυτά που συμφωνήσαμε.** Κανένα δεν αλλάζει τη σειρά των προϊόντων,
  το Recommended, το «μόνο ό,τι έχει απόθεμα» ή το «μόνο το είδος που ζητήθηκε».
- **(α) Ένας δικός μας «δεύτερος κριτής» για τα αμφίβολα προϊόντα, χωρίς AI και χωρίς
  κόστος.** Κάθε βράδυ μαθαίνει από τα προϊόντα που το ίδιο το κατάστημα λέει τι είδος
  είναι (περίπου 96.000) και κρίνει τα αμφίβολα (περίπου 35.000): ποιο από τα είδη που
  γράφουν τα λόγια τους είναι, ή κανένα. Δεν πηγαίνει ποτέ κόντρα στον κανόνα του
  διαδρόμου: τα χάπια δεν γίνονται tablets. Πρώτα μετράμε τι θα άλλαζε και σου το
  δείχνουμε· μπαίνει στο site μόνο με το «ανέβασε» σου.
- **(β) Μία πρόταση σύνοψης από τα δικά μας νούμερα, χωρίς AI.** Π.χ. «40 power banks σε
  9 καταστήματα, από £9,99 έως £89· τα 12 γράφουν iPhone, από £14,99». Κάθε αριθμός
  βγαίνει από τα προϊόντα της απάντησης. Είναι το πιο μικρό, γι' αυτό προτείνω να γίνει
  πρώτο.
- **(γ) Το Claude Haiku 5.5, μόνο όταν η μηχανή μας δεν μπορεί να ταιριάξει κάποιες
  λέξεις** (η σελίδα ήδη γράφει «could not match»): «tablet για 10χρονο», «αθόρυβο
  πλυντήριο». Διαβάζει τους τίτλους έως 30 προϊόντων που έχουμε ήδη ελέγξει και γράφει
  μία πρόταση: πόσα ταιριάζουν και από ποια τιμή. Ο κώδικας ελέγχει κάθε αριθμό και κάθε
  όνομα· αν κάτι δεν στέκει, δεν δείχνεται τίποτα. Η σελίδα δεν περιμένει ποτέ το AI: η
  πρόταση έρχεται λίγο μετά, και γράφει ότι είναι από AI.
- **Κόστος του (γ):** περίπου 0,05 σεντς του δολαρίου ανά αναζήτηση, δηλαδή περίπου
  2.000 αναζητήσεις με 1 $ (εκτίμηση· η δοκιμή θα δώσει το πραγματικό). Ημερήσιο όριο
  μέσα στον κώδικα (προτείνω 1 $ τη μέρα) και προπληρωμένη πίστωση στον λογαριασμό. Η
  ίδια αναζήτηση την ίδια μέρα δεν πληρώνεται δεύτερη φορά.
- **Από εσένα, όταν φτάσουμε στο (γ):** λογαριασμός στην Anthropic και πίστωση για το
  API (αν η συνδρομή σου είναι Max, Ultra ή Team, έχει ήδη δωρεάν μηνιαία πίστωση για το
  API), ένα κλειδί (API key) που θα το βάλεις μόνος σου στα μυστικά του GitHub, ποτέ στη
  συζήτηση. Πριν ανέβει, βλέπεις τα αποτελέσματα σε περίπου 150 δοκιμαστικές
  αναζητήσεις, ελληνικά και αγγλικά.
- **Τι σου ζητάω τώρα:** μόνο να εγκρίνεις το σχέδιο ή να μου πεις τι αλλάζει. Τα
  υπόλοιπα (πόσο αυστηρός ο κριτής, το όριο κόστους) τα αποφασίζεις όταν δεις τα νούμερα
  (ενότητα 6).

## 1. Rules every part keeps

1. **The answer stays the owner's.** No part changes the order (the Recommended, then the
   products a current shop offer covers, then the rest, each cheapest first), the
   Recommended's rule, "in stock only" or "the kind asked for only" (`PROJECT_RULES.md`
   sections 2, 3 and 5; `docs/PICWISE_DECISION_CONTRACT.md`). Part (a) can only settle
   the kind of a product the rules left doubtful, never against the aisle rule; parts (b)
   and (c) only add a sentence.
2. **Nothing fake** (`PROJECT_RULES.md` section 4; `concept.picwise.txt` section 20):
   every number on the page is computed from the products of the answer. A sentence
   written with AI says so, states no confidence or score, and is checked by code before
   it is shown; one that fails is not shown.
3. **Commission never counts**, in any part.
4. **The page never waits** (`PROJECT_RULES.md` section 9: first render under 1.5 s):
   (a) runs at night; (b) is computed with the answer; (c) comes after the page is shown
   and never holds a worker of the site.
5. **Google.** The site's own search pages carry `noindex` (`PROJECT_RULES.md` section
   13); (b) and (c) appear only there. The text of the pages meant for Google is another
   piece of work (`docs/PICWISE_GOOGLE_PAGES_SPEC.md` section 5,
   `docs/PICWISE_SERVER_ARCHITECTURE.md` section 4). Part (a) changes kinds, and with them
   what a kind's page may show: its measure lists those changes too (2.5).
6. **The understanding stays local.** No language model is called from `src/picwise_nlu`;
   the tests that pin this (`test_local_nlu_*`: no "claude", "anthropic", "api_key",
   "live_llm") stay as they are. Part (c) is a package of its own, `src/picwise_ai/`, and
   the site itself stays on the standard library: the Anthropic SDK is installed only for
   the small service that calls the API (4.5, 4.6).
7. **Secrets.** The API key exists only as a GitHub secret, written by the deployment to
   a file only the calling service reads; never in the repository, a log, a page or the
   chat.
8. **Measured before it counts; live only on the owner's word**, naming the commit and
   the branch, as every deployment (`docs/picwise_session_handoff.md`, first section).
9. **Tests with every step** (`PROJECT_RULES.md` section 11), on fixtures with fictional
   brands and `.invalid` links. No test calls the API.

## 2. Part (a): a classifier of our own, a second opinion on the doubtful products

### 2.1 What it is for

The rules (`concept_understanding.annotate_product_concepts`) leave a product's kind
doubtful (`UNCERTAIN_MARKER`) when its own words disagree: a title naming another kind
than its shelf ("3 Seater Sofa" filed under "Chairs > Chaises"), a type naming a kind
PicWise does not know ("Temperature & Humidity Sensors") under a title that names one, a
type listing several kinds the title does not settle, a title naming a kind only in
passing. A doubtful product is never found by its kind, only by its words (the decision
contract, "The main kind only", point 7). On the catalogue of 05/11: 37,998 doubtful
products, 3,160 of them made doubtful by their aisle (the deployment's kind report, run
`42028878547`), so about 35,000 for the other reasons (the measure counts them exactly).

Part (a) settles the ones it can: of the kinds the product's own words name, which one it
is, or none.

### 2.2 What it learns from

Each night, from the catalogue just prepared:

- **each kind:** the products whose type or shelf names their kind, read against the
  aisle (the decision contract, "The main kind only", points 1 to 7): about 96,000 on
  04/11, cleaner since item 2;
- **"none":** the products whose type or shelf PicWise reads and which name no kind it
  knows ("Vitamins & Supplements", "Temperature & Humidity Sensors"). Without it the
  classifier could only choose among kinds, and a vitamin tablet would have to be one.

Products whose kind comes from the title alone (about 177,000 on 04/11) do not teach it:
their kind is the rules' reading, not the shop's.

### 2.3 How it reads

A naive Bayes classifier, standard library only: it counts, per kind and for "none", the
words of the title, the words of the shop's type and shelf, the aisle of Google's and the
brand, and scores a product by the words it carries. Chosen because it trains in one pass
over the catalogue, its counts can be read ("these words decided"), and it needs no
library.

For a doubtful product it compares only:

- the kinds its own title, type or shelf names, **of those its aisle may hold**
  (`_aisle_may_hold`): it never goes against the aisle rule, so a vitamin tablet can
  never become a tablet;
- and "none".

The kind with the highest score is taken only when it passes the bar (2.5); otherwise the
product stays doubtful, as today. A product the rules read as a kind, or as an accessory,
is never touched.

### 2.4 What it changes once switched on

A doubtful product the classifier reads as a kind past the bar becomes a product of that
kind, with its broader kinds, as if the rules had read it: it is found by the kind's
searches and ordered and recommended by the same rules as every other. Nothing else
changes.

Until the owner switches it on, it runs in the shade: the nightly preparation records its
readings in its note (counts per kind, examples), and the search does not use them. When a
night's training falls below the bar for a kind (2.5, point 1), that kind's readings are
not used that night; the rules alone decide, and the note says so.

Its code joins the prepared file's fingerprint (`prepared_catalogue.code_fingerprint`), as
the rules' code does: a change to it prepares the catalogue again.

### 2.5 The measure

Before it counts, on the server's catalogue, through the audit
(`deployment/server/print_confusions.py`, `server-confusions.yml`, a new part
"classifier"):

1. **Held out:** trained on 90% of its examples, read on the other 10%: per kind, how often
   it is right at the bar. This shows that it learned the shops' own readings; it does not
   show that it is right on the doubtful products, which are harder by definition.
2. **The doubtful products:** how many it would give a kind, per kind, with examples, read
   by hand as item 2's 527 were; how many it leaves doubtful; and, for the 3,160 made
   doubtful by their aisle, what it would say if it were allowed to (reported only).
3. **The searches:** the 320 kinds' searches and the 21 products' own names
   (`NAME_SEARCHES`), with and without it: the wrong products among the first 12 must not
   rise.
4. **The pages meant for Google:** what it would change in the products they may show.
5. **The night:** the preparation's time and peak memory with it (today about 15 minutes
   and 9.8 GB, under a ceiling of 16 GB).

**The bar is the owner's** (section 6), set with these numbers in hand. Proposed: a kind
takes part only where the held-out reading is right at least 99 times in 100, and only if
point 3 shows no rise.

### 2.6 Limits

- It knows only the kinds PicWise defines (312 in `product_concepts.py` on 05/11); a new
  kind still needs its name written there.
- It does not read the products with no kind at all (about 254,000 on 04/11), nor take a
  kind away from a product the rules gave one: each would be a step of its own, measured
  the same way.
- A shop that files products wrongly teaches it wrong. That is why it learns only from
  type and shelf read against the aisle, and why a kind takes part only past the bar.

## 3. Part (b): one sentence from the engine's own counts, no AI

### 3.1 What it says

Under the search line of a search answered with products, one sentence built from the
answer itself (the products of the kind asked for, in stock), by the rules of
`docs/PICWISE_SERVER_ARCHITECTURE.md` section 4.1: every number computed, a clause written
only when its facts exist, no word of quality, the site's English.

| Clause | Written when |
|---|---|
| "{n} {kind plural} in stock at {s} shops, from {min} to {max}" | n ≥ 2 |
| "; {k} of them say {word}, from {min_k}" | a word of the search only some of them carry ("Only some match" today) |
| "; {m} on a current shop offer" | m ≥ 1 |

For example: "40 power banks in stock at 9 shops, from £9.99 to £89.00; 12 of them say
iPhone, from £14.99." For an answer found by its words, where the page names no kind:
"{n} products that say {words}, in stock at {s} shops, from {min} to {max}."

### 3.2 What it does not do

It does not replace the search line ("Results for:", "Understood as", "PicWise could not
match") or the note on how the order is made; it says nothing those numbers do not; it is
not written for an answer of one product, which has its own layout. One currency per
answer, as today.

### 3.3 Where it lives

`src/picwise_surface/reference.py` (the page), from figures the selection already has or
adds (the cheapest and dearest of the whole answer, its shops), in an element of its own
(`pw-summary`), so the cards' markup that the tests and `compare_with_vercel.py` read is
unchanged.

## 4. Part (c): Claude Haiku 5.5, only for what (a) and (b) cannot do

### 4.1 When it is asked

Only when a search for a kind is answered with products **and the page says "PicWise
could not match"**: words of the search that no product of the kind carries ("tablet for
a 10 year old", "quiet washing machine"), or a narrower kind with no product that fell
back to the broader one ("motorcycle helmet"). These are the engine's own signals
(`unmatched_query_terms`, `fallback_concept_id`). A long search the engine understood whole
needs no AI, and a short one it could not honour does: so the search's length, or words
like "for" and "για", decide nothing on their own.

Not asked for:

- the buyer's judgements, which PicWise answers with its own order and Recommended: the
  Greek ones the engine already sets apart («φθηνό», «καλύτερο», «ποιοτικό»:
  `_JUDGEMENT_QUALIFIERS`), and the same in English ("best", "cheap", "good"), which the
  engine reads today as words to match, so the layer keeps its own list of them;
- a condition PicWise could not match ("refurbished"), which has its own rule;
- searches whose kind was not understood ("gift for a 10-year-old": there are no verified
  products to read) and answers found by their words (their products are doubtful, not
  verified). Each could be a later step.

### 4.2 What it is given and asked

Given:

- the search as typed, and the words the engine could not match;
- up to 30 products of the answer, in the page's order, each with a short number (1 to
  30), its title, brand, price and currency, shop and kind.

Nothing about the visitor: no address, cookie or session.

Asked, as structured output (`output_config.format`, a JSON schema):

- for each product: does its title show that it fits the words the engine could not
  match: `yes`, `no` or `unclear`;
- one sentence of at most 30 words: how many fit and from what price, from the titles
  alone, with no "best" and no score.

The model is `claude-haiku-5-5`, at effort `low` (a reading task; the measure checks it,
4.8). The shops' titles are data to it, never instructions; what any title could make it
say is bounded by the checks.

### 4.3 Checked by code before it is shown

- every short number is one that was sent, each once, and the counts in the sentence equal
  its own `yes` answers;
- every price in the sentence is the price of a product it answered `yes` (the lowest of
  them where it says "from");
- every word with a capital letter or a digit is in the search or in the products' data;
- no word of quality, testing, rating or urgency (a list, as in
  `docs/PICWISE_SERVER_ARCHITECTURE.md` section 4.4), no link, e-mail or number that is
  not in the data;
- one sentence, at most 30 words.

A failed check, a refusal (`stop_reason: "refusal"`; Haiku 5.5 has no server-side
fallback), no answer within 8 s, or the day's cap reached: nothing is shown, the page
stays as it is, and the service's log says why.

### 4.4 What the page shows

The sentence, under part (b)'s, followed by "Written with AI from the shops' titles, and
checked against them." The cards, their order and the Recommended stay as they are.

Whether the cards it reads as fitting may carry a mark, or the ones it reads as not
fitting be left out, is the owner's (section 6). Proposed: the sentence alone first, since
a mark would put an AI reading on a product, and leaving products out changes the answer.

### 4.5 Never delaying the page

- The site's worker answers the search as today. For a complex search it writes a small
  job (the search and its candidates) to a folder on the server, and puts on the page an
  empty line and a small script.
- A separate service, `picwise-assist` (systemd, like the server's other services, under
  a system user of its own), reads the jobs, calls the API, checks the answer and writes
  the result.
- The script asks the site for the result for up to 10 s; the site reads a file, never the
  API. A page whose result does not come shows nothing more.

So the site's four workers never wait for the API, only that service holds the key, and
only it has the SDK. A visitor whose browser runs no script, as most bots, costs nothing.

### 4.6 The account, the key, the library

- **The credit.** The owner's Claude plan (the owner, 05/11: «εχω ηδη συνδρομη στο
  anthropic claud σε αυτο που μιλαμε», then «ειναι προ»: Pro) pays for Claude and
  Claude Code, not for the API. But Max, Ultra and Team plans carry a monthly API credit
  (Anthropic's page "API credits for Max, Ultra, and Team plans", read on 2026-11-05):
  - $100 a month on Max, $200 on Ultra, on Team $20 or $100 a seat, pooled up to $500;
    renewed each billing cycle, expired at its end, never carried over; claimable after 7
    days on the plan; none on Pro or Enterprise;
  - claimed on claude.ai, Settings > Billing (on Team: Organization settings > Billing),
    section "API credits", by linking a Console organization to the plan (made there, or
    at the Console first). One organization per plan, which only support can change
    later: it should be the one PicWise is built in;
  - no payment method is needed; when the credit runs out and none was bought, the API
    stops until the next month's credit arrives, and nothing is charged to the plan.

  On a plan without it, the owner buys credit instead (below).
- **The owner**, on the Claude Console (`platform.claude.com`; Anthropic's pages on
  authentication and on rate limits, read on 2026-11-05):
  - opens an account (or uses the one linked to the plan); without the plan's credit,
    buys credit on the Billing page ("Buy credits"; Anthropic's Help Center, "How do I
    pay for my Claude API usage?", read on 2026-11-05: the API is paid with credit
    bought in advance, which expires a year after its purchase; when it runs out the
    API refuses every request until more is added). Automatic reload stays off (the
    page's "Set up auto-reload" is not pressed), so the credit bought is the ceiling;
  - may set a monthly spend limit on the Billing page as well, below the tier's own cap
    (the Start tier's is $500 a month; a new organization may start lower, in an
    evaluation tier); past the limit the API refuses every request until the next
    month. With the reload off it is not needed;
  - creates a workspace "PicWise", the key's home (a workspace may carry a spend limit
    of its own; the account's is enough here);
  - creates an API key linked to themselves, **scoped to that workspace** (a key not
    scoped to one must name the workspace on every request), with no expiry, since it is
    kept in GitHub's secrets and changed by hand; a key that leaks is disabled or deleted
    at once on the Console's API keys page, and a new one put in GitHub;
  - puts it in GitHub's secrets as `ANTHROPIC_API_KEY`, never in the chat;
  - reads in the account's terms how long Anthropic keeps what it is sent.
- **The deployment** (`server-deploy.yml`) writes the key to a file only `picwise-assist`
  reads (`/etc/picwise/assist.env`, mode 0600): not to `picwise.env`, not to the site's
  service.
- **The library:** the Anthropic SDK for Python, as agreed on 05/11, pinned with its hash
  and with the hash of every package it needs (`pip --require-hashes` asks it of all), in
  a requirements file and a virtual environment of its own. The site's
  `requirements-server.txt` keeps gunicorn alone.

### 4.7 Cost and the cap

Haiku 5.5 costs $0.10 per million tokens read and $0.50 per million written, for prompts
up to 100,000 tokens (Anthropic's pricing page, read on 2026-11-05; to read again on the
account). A complex search sends about 2,000 tokens and gets about 500 back: **about
$0.0005 a search, some 2,000 searches for $1** (an estimate; the measure takes the real
figure from each answer's `usage`).

- **The cap, in code:** the service adds up each answer's cost (its `usage` at the listed
  prices) per UTC day, and stops asking at the cap; and it asks at most 30 times a minute,
  so a burst cannot spend a day's cap in minutes. The amount is the owner's (section 6).
  Proposed: $1 a day.
- **The cache:** the same search with the same products (their ids and prices) is
  answered from the first answer for 24 hours: the second visitor costs nothing.
- **The prepaid credit** is the ceiling above the code's.
- The fixed part of each request (the instructions and the schema) is cached by the API,
  and read again at a tenth of the price.

### 4.8 The offline measure, before anything goes live

About 150 complex searches, Greek and English, written for it into the repository, each
marked with the signal it exercises (words not matched, a broader kind), run on the
server's catalogue through a workflow (pushed with the owner's word), with the real key.
For each: the candidates, the AI's answers, the sentence, the checks, the time and the
cost. Every `yes` and `no` is read against the titles by hand. Then the owner sees how many
sentences were right, wrong or withheld, the cost of a search and its time.

**The bar to go live is the owner's** (section 6). Proposed: no wrong sentence among those
that pass the checks. The query log is not configured on the server, so there are no
logged searches to draw from; whether the text of real searches in the site's access log
may be used too is the owner's.

### 4.9 Tests

The checks, the cap, the cache, the jobs and results, and the page's script and endpoint,
with the API faked: no test reaches the network. The NLU's guard tests stay and pass.

## 5. Order of work

Each step is told to the owner, and goes live only on the owner's word naming the commit
and the branch.

1. **This spec:** the owner approves it, or changes it.
2. **(b) the sentence from the counts:** the smallest. Built and tested, shown to the
   owner on the audit's searches, then deployed.
3. **(a) the classifier, in the shade:** built and tested; measured on the server's
   catalogue (2.5); the numbers to the owner, who sets the bar; switched on with
   «ανέβασε».
4. **(c) Haiku:** the owner opens the account and puts the key in GitHub; built and
   tested; the offline measure (4.8) to the owner; live with the cap on the owner's word;
   after a week, its use and cost to the owner.

## 6. The owner's decisions

| When | Decision | Proposed |
|---|---|---|
| now | approve this spec | — |
| (a), with its numbers | the bar | right at least 99 times in 100 held out, and no rise of wrong cards in the 320 searches |
| (a), with its numbers | may the classifier ever go against the aisle rule | no |
| (b) | a Greek sentence for a Greek search | no: the site is in English |
| (c), at the account | the credit, and the account's spend limit | the owner's plan is Pro, which carries no API credit: $10 bought, reload off, which is then the ceiling; a spend limit is not needed |
| (c), before it is built | the daily cap in code | $1 a day |
| (c), with the measure | the bar to go live | no wrong sentence among those shown |
| (c), with the measure | marks on the cards, or products left out | the sentence alone |
| (c), with the measure | real searches from the access log for the measure | written searches only |
| (c), before it goes live | the privacy note: searches may be sent to Anthropic | wording and place, the owner's |

## 7. Not in this spec

- products with no kind at all, and taking a kind away from a product the rules gave one
  (2.6);
- new kinds (2.6);
- searches whose kind was not understood, and answers found by their words (4.1);
- the AI text of the product pages meant for Google
  (`docs/PICWISE_SERVER_ARCHITECTURE.md` section 4.4);
- the kind items parked on 05/11 (`docs/picwise_session_handoff.md`, first section), which
  stay parked unless the owner raises them.
