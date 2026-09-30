# PicWise: Understanding Misspelled Buyer Queries

Buyers in Greece type product searches the way people actually type: Greek without
accents, the wrong vowel for a sound, greeklish under whatever transliteration habit
they have, Greek with the English keyboard layout still on, English with a slipped key.
The promise is unchanged by any of that: four suitable products of the kind asked for,
one recommended, the product rules of that category applied.

## Measured, before and after

`python tools/nlu_misspelling_benchmark.py` runs 706 queries end to end through the
real resolver and the real render gate, against the local coverage fixture feed
(33 product types, 18 mega categories). A case passes only if four cards render, one is
recommended, and every card is the expected kind of product.

| | Before | After |
|---|---|---|
| Pass | 25.2% | **96.2%** |
| Wrong kind of product shown | 19 | **0** |
| Greek | 0.0% | **98.1%** |
| Greeklish | 3.9% | **96.5%** |
| English | 63.7% | **92.2%** |
| Hand-written held-out queries (104) | 16.4% | **100%** |
| Non-product searches refused (7) | 100% | 100% |

The 27 remaining failures are deliberate refusals: 3-4 letter words with a letter
missing (`dsk`, `tres`, `muse`, `τοερ`) and consonant-only skeletons (`mntr`, `prntr`).
A word that short, corrected, is as likely to be a different ordinary word as the
product; PicWise shows nothing rather than a guess. A wrong product is the worst
outcome, so it is the number held at zero.

How honest these numbers are: the fixture feed is local test data and says nothing about
what a real feed contains. The generated cases come from the same kinds of rules the
matcher uses, so they measure coverage of known error types. The 104 held-out queries
were written by hand before the lexicon, as a buyer would type them; they are the
independent check. They were written by the same author as the lexicon, so real traffic
remains the real test -- see "Training loop" below.

## How it works

### 1. A lexicon of product concepts (`src/picwise_nlu/product_concepts.py`)

220 concepts -- washing machine, power bank, κράνος ποδηλάτου... -- each with its
ordinary English and Greek names, singular and plural, and exactly one of the 18 mega
categories. Through the mega category each concept is tied to the deep packs' product
rules: `spec_fields_for_mega_category()` reads the category's `spec_fields` from the
packs, so a spec the buyer types is linked to a field of the rules (`8 κιλά` ->
`load_capacity_kg` for washing machines).

Only correctly spelled names are listed. Misspellings are the matcher's job; a lexicon
of typos would understand only the typos someone thought to write down.

`broader` links narrower concepts to general ones (robot vacuum -> vacuum cleaner,
bicycle helmet -> helmet). A buyer asking for a helmet can be shown bicycle helmets; one
asking for a bicycle helmet cannot be shown motorcycle helmets.

### 2. Reading by sound (`src/picwise_nlu/concept_understanding.py`)

Greek and greeklish are both reduced to one phonetic key where every spelling of a sound
is the same letter: η ι υ ει οι -> i, ο ω -> o, ε αι -> e, ου -> u, μπ -> b, ντ -> d,
γκ -> g. So `πλυντήριο`, `πλιντηριο`, `plyntirio`, `plintirio` share one key, and the
most common Greek spelling mistake -- the wrong vowel for a sound -- costs nothing.

Latin text is also read as the Greek it would be if typed with the Greek layout on
(`cygeio` -> `ψυγειο`), and in English.

### 3. Correcting typos

What remains -- a missing, extra, swapped or neighbouring letter -- is corrected by
Damerau-Levenshtein distance: 1 edit for words up to 7 letters, 2 beyond, found through a
deletion index (a few dictionary lookups, not a scan). Measured: about 0.5 ms per query.

Corrections are where wrong answers come from, so they are fenced:

- a correction needs another correctly typed word of the same name (`pawer bank`), or a
  single word long enough (6+ letters in Greek, 5+ in Latin) that one slip cannot make it
  a different ordinary word. `κρασί` is one letter from `κράνη`; `παιδιά` one from
  `πέδιλα`.
- a misspelling equally close to two unrelated products names neither.
- everyday words (food, places, people, finance) are never corrected into products;
  non-retail words (`δάνειο`, `τράπεζα`, `ασφάλεια`) are never matched at all.
- a corrected single word among several unknown words is not trusted:
  `wedding cake topper` is not a toner.
- **every corrected reading is stated on the page**: "Understood as: laptop". A wrong
  correction that gets through is therefore visible to the buyer, never silent.

### 4. Which product, and what else was asked

- the longest name wins: `φούρνος μικροκυμάτων` is a microwave, `μπαταρία αυτοκινήτου`
  a car battery, `εξωτερική μπαταρία` a power bank
- the product bought is the one before `για / for / with / με`: `τόνερ για εκτυπωτή`
  is toner, `webcam για laptop` a webcam
- the rest becomes filters, in the feed's own words: specs fused and unit-normalised in
  Greek, greeklish and English (`8 κιλα` -> `8kg`, `55 ιντσες` -> `55inch`,
  `5 λιτρα` -> `5l`, `12000 btu`, `70ah`, `16gb`), preferences translated
  (`ασύρματο` -> `wireless`), anything else kept as typed (brands, models)
- judgements (`φθηνό`, `καλό`) are understood but never filters: no feed field can
  confirm them, so the page reports them as not matched

### 5. Products carry the same concepts (`annotate_product_concepts`)

Each feed product is annotated from its own product type (the authority), else its
category, else its title -- exactly, never fuzzily, since feed text is spelled correctly
and a fuzzy match there would invent concepts. The title can refine the type into a
narrower concept of the same kind (a "Vacuum Cleaners" product titled "Robot Vacuum
Cleaner" is also a robot vacuum) but never change it: a laptop whose title mentions its
SSD is still only a laptop. `Laptop Cases & Bags` is a laptop bag, never a laptop.

Feed text is accent-stripped and its specs fused (`8 kg` -> `8kg`) so it meets the query
in the same form.

### 6. Selection by concept (`search_selection._select_products_for_concept`)

When the concept is understood, the product name is no longer a text filter. Candidates
are the products annotated with the concept, so `πλυντηριο`, `plintirio` and
`washing machine` reach the same products whether the feed is written in English or in
Greek. The filters then go through the existing largest-satisfiable-subset relaxation,
among those candidates only. **Relaxing a filter can therefore never change the kind of
product shown** -- which is exactly what produced all 19 wrong answers before (a typo'd
word was dropped and the remaining word matched another family: `air` -> air
conditioners and air fryers, `machine` -> coffee and washing machines).

When too few products of a narrow concept exist, the broader concept answers and the
narrowing word is reported (`σκούπα ρομπότ` with one robot vacuum in stock: four vacuum
cleaners, "could not match: ρομποτ").

Words the page could not honour are quoted as the buyer typed them (`ασυρματο`, not the
feed-language `wireless` it became).

Queries with no understood concept take the previous path unchanged, with one added
guard: if the four products it would show are of different kinds, it asks instead
(`machine`).

## Latency

The pre-existing search-index fuzzy lookup computed a full edit-distance matrix against
tens of thousands of index entries for every multi-word query: 2,570 ms for
`pawer bank 20000 gia iphone`. Every caller only acts on distances up to a small cap, so
the distance now stops once the cap is exceeded -- results identical, the index lookup
is not in the search artifact's fingerprint, so the committed artifact stays valid.

| Query (coverage fixture, warm) | Before | After |
|---|---|---|
| `pawer bank 20000 gia iphone` | 2,570 ms | 232 ms |
| `plintirio` | 1,255 ms | 345 ms |
| `wedding cake topper` | 1,923 ms | 350 ms |
| `πλυντηριο ρουχων 8 κιλα` | 167 ms | 138 ms |

## Training loop

The NLU is taught by adding the names buyers use, not by retraining a model:

1. `query_served` tracking events now carry `understood_concept`,
   `understood_by_correction` and `choices_rendered`
2. `python tools/nlu_mistake_report.py queries.txt` lists what was not understood and
   what was understood only through a correction
3. add missing names to the lexicon; add a wrong correction's word to `_COMMON_WORDS`
4. rerun the benchmark; wrong answers must stay at 0

Running it once over sample queries already found a real gap: `αντλία θερμότητας`
(heat pump) was being read as a water pump through its first word. Heat pumps and water
heaters are now concepts of their own.

Events are held in memory only (the last 400); persisting them needs the analytics
connection, which is `not_connected`.

## Tests

```bash
python -m unittest tests.test_picwise_concept_understanding   # the matcher and annotator
python -m unittest tests.test_picwise_misspelled_queries_deliver  # end to end, English and Greek feeds
python -m unittest tests.test_picwise_nlu_misspelling_variants  # the error generators
python tools/nlu_misspelling_benchmark.py
```

`tests/fixtures/provider_feed_greek_titles_fixture.csv` is a local fixture whose
products are titled and typed in Greek, because Greek merchants' feeds are. Fictional
brands, `.invalid` URLs, `data_provenance=local_test_fixture`.

## Still open

- Short words with a typo are refused rather than guessed. A "did you mean" suggestion
  would recover them without risking a wrong answer.
- A filter satisfied by some but not all four products is reported as not matched, even
  though the products carrying it rank first. The wording could say "2 of 4".
- The lexicon covers 220 kinds of product. Real traffic will show which are missing;
  that is what the training loop is for.
- The word-level NLU (`build_local_nlu_intent`) still reports Greek queries as
  `insufficient_data`; the resolver now takes the concept reading instead, but the two
  NLU layers are not yet merged into one.
