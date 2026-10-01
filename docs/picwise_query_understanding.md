# Understanding The Request However It Is Phrased

Replaces the finding in `docs/picwise_query_qualifier_finding.md`, which is now closed.
Operator instruction: whatever is needed so the service understands what the user is
asking, by any means.

## What was wrong

`_score_product_for_tokens` discarded any product unless **every** query word appeared in
its feed text. One word that did not appear emptied the result set:

| Query | Cards before |
|---|---|
| `power bank` | 4 |
| `power bank for iphone` | **0** |
| `comfortable office chair` | **0** |
| `running shoes for men` | **0** |
| `quiet lawn mower` | **0** |

The concept's own flagship example, `power bank 20000mah για iphone`, and the README's
documented demo URL both returned nothing. A buyer who described their need got less than
one who typed a bare noun, which inverts "μπαίνεις μπερδεμένος, βγαίνεις αποφασισμένος".

## What it does now

Selection asks a different question: **what is the largest set of the buyer's words that
four products all satisfy?** The inventory decides which words are filters, rather than a
hand-written list of qualifier words.

```
power bank 20000mah for iphone
  → required: power, bank          (4 power banks satisfy these)
  → could not match: 20000mah, iphone
  → 4 cards, 1 recommended, and the page says what it could not match
```

Three properties keep that safe, each with tests:

**1. A word the inventory can filter by is never dropped.** With four 20000mAh power
banks in stock, `20000mah` stays a filter. Relaxation only happens where the alternative
is a blank page.

**2. Relaxing never changes the product family.** The fullest reading names the product,
even when it matches too few items. `laptop bag` matches one bag, so relaxing to `laptop`
would answer with laptops — that is refused, and `laptop bag` stays safely empty. Every
relaxed query in the tests still returns a single family: `power bank for iphone` returns
Power Banks, `coffee machine for office` returns Coffee Machines, never office chairs.

**3. Words that point at two different families are not guessed at.** `smartphone with
good battery` matches mobile phones through one word and car batteries through another.
Rather than pick one, PicWise says: *"PicWise is not sure which product you mean. This
search matches car batteries and mobile phones. Add a word that names the product you
want."* Showing car batteries to someone asking about a smartphone is worse than showing
nothing.

## Saying what could not be matched

Four products for a partly-matched request are honest only if the page says so. The query
line now reads:

> Showing 4 selected real products for: power bank 20000mah for iphone · **PicWise could
> not match: 20000mah, iphone**

Without that line the buyer would read four products as an answer to their whole request.
`unmatched_query_terms` is carried on the selection result, through the resolution, to the
surface; it is never silently discarded.

## Ambiguous terms narrowed by a product word

`is_unsafe_broad_query` matched its term list per token, so **any** query containing
`bank`, `apple`, `nike`, `bosch`, `galaxy`, `insurance`, `loan` or `software` was treated
as too broad to act on. That blocked some of the most ordinary things a buyer types:

- `power bank for iphone`
- `nike running shoes`
- `bosch drill`
- `apple laptop`
- `galaxy smartphone`

The list is right about those words **on their own**: `bank` alone is a financial
institution, `apple` alone is ambiguous. So the rule now applies only when nothing in the
query names a product. `bank` stays unsafe; `power bank` does not. Every single-term
safety case the existing tests assert is unchanged.

## Grammatical connectives

`for`, `with`, `of`, `the`, `my` and the Greek `για`, `και`, `με`, `σε` carry no product
signal, so they are never required. They were previously held against products like any
other word.

## Cost

Measured through `wsgi.py` on a generated 50,000-row feed. The relaxation pass only runs
when the strict reading cannot fill four cards, so a fully-matched query pays nothing
extra:

| Stage | Cost |
|---|---|
| Feed selection, `laptop` (no relaxation) | 831 ms |
| Feed selection, `laptop for gaming` (relaxed) | 1,034 ms |
| Feed selection, 6-word query (relaxed) | 1,110 ms |

So relaxation adds roughly 200–280 ms on a 50,000-row feed. The relaxation pass uses one
joined text per product rather than six separate fields, since it only asks whether a word
appears at all.

**Separate pre-existing cost, found while measuring this:** the search index's fuzzy
lookup dominates multi-word queries — 6 ms for `laptop`, 675 ms for `laptop for gaming`,
1,297 ms for a six-word query, from `_levenshtein_distance` in
`src/picwise_search_memory/index_lookup.py`. Multi-word queries on a large feed therefore
exceed the PROJECT_RULES section 9 render target for reasons that predate this change.
That is the next performance target, not something this change introduced.

## Still open

- **`tv` synonym.** `tv` is still not recognised as `television`; see
  `docs/picwise_product_type_coverage_matrix.md`.
- **Need-qualifiers are reported, not answered.** `for iphone` is stated as unmatched
  rather than resolved into a compatibility fact (USB-C, Lightning). Doing that properly
  needs compatibility data the feed does not carry.
- **Fuzzy index lookup latency** on multi-word queries, above.

## Test command

```bash
python -m unittest tests.test_picwise_query_understanding
```
