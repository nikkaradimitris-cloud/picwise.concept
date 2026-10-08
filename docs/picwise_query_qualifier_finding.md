# Finding: One Unmatched Qualifier Word Empties The Result Set

> **CLOSED.** Fixed in `docs/picwise_query_understanding.md`. The operator's answer was
> "whatever is needed so the service understands what the user is asking". Selection now
> looks for the largest set of the buyer's words that four products satisfy, keeps the
> product family fixed, refuses genuinely ambiguous queries, and states whatever it could
> not match. The original finding is kept below for the record.

Open finding, not a change. Surfaced while routing power banks through the provider-feed
engine. It needs a product decision before any code moves, because it is the relevance
formula the Decision Contract leaves as TODO.

## What happens

`src/picwise_providers/search_selection.py`, in `_score_product_for_tokens`:

```python
if matched_tokens < len(tokens):
    return None
```

Every query token must match somewhere in the product's title, product type, category,
brand, keywords or description, or the product is discarded outright. One qualifier word
that does not appear literally in the feed text therefore removes **every** candidate.

Measured against the coverage fixture, which holds four products for each type:

| Query | Matched | Cards shown |
|---|---|---|
| `power bank` | 4 | 4 |
| `power bank for iphone` | 0 | **0** |
| `coffee machine` | 4 | 4 |
| `coffee machine for office` | 0 | **0** |
| `office chair` | 4 | 4 |
| `comfortable office chair` | 0 | **0** |
| `running shoes` | 4 | 4 |
| `running shoes for men` | 0 | **0** |
| `drill` | 4 | 4 |
| `cordless drill for home` | 0 | **0** |
| `lawn mower` | 4 | 4 |
| `quiet lawn mower` | 0 | **0** |

## Why it matters

Real buyers type qualifiers. The concept's own flagship example is
`power bank 20000mah για iphone`, and the README documents
`/demo?q=power+bank+20000mah+for+iphone` as the demo URL. That query currently returns
nothing, because no power bank title contains the word "iphone".

The mission is "μπαίνεις μπερδεμένος, βγαίνεις αποφασισμένος". A buyer who adds detail to
describe their need currently gets less than one who types a bare noun, which inverts the
promise.

Note `20000mah` behaves differently and correctly: only one fixture product is 20000mAh, so
`20000mah power bank` matches one product and PicWise refuses rather than padding the four
with products that do not match. That refusal is right. The problem is specifically the
qualifier that describes a *need* ("for iphone", "for office", "comfortable", "quiet")
rather than a *property present in the feed text*.

## Why it is not fixed here

Relaxing the rule is the ranking formula, which
`docs/PICWISE_DECISION_CONTRACT.md` explicitly lists as undefined:

```
## Undefined Details
- Ranking formula weights: TODO
- Tie-break protocol between close candidates: TODO
```

PROJECT_RULES section 4 forbids inventing business logic where the concept or spec is
missing. Removing the hard filter naively also costs real precision: with `power bank`
scoring only on `power`, a product typed `Power Drills` becomes a candidate — which is
exactly what the filter protects against today.

So the decision needed is a product one: **how strict should matching be?** Some options,
with their trade-offs:

1. **Drop connective stopwords only** (`for`, `with`, `the`, `my`). Purely linguistic, no
   judgement. Fixes nothing on its own: `for iphone` still leaves `iphone` unmatched.
2. **Require the head noun plus a minimum share of tokens**, letting unmatched qualifiers
   lose points instead of excluding. Fixes the table above. Needs a threshold nobody has
   specified, and English qualifier order ("power bank for iphone") makes "head noun"
   ambiguous to detect.
3. **Treat unmatched tokens as score penalties only**, with the existing accessory and
   product-type penalties carrying precision. Most permissive; highest risk of loose
   matches, and would need the canary set re-run to see what degrades.
4. **Map need-qualifiers to compatibility facts** (`for iphone` → USB-C / Lightning
   output). Most correct for buyers, and the only option that answers the actual question
   asked, but it needs compatibility data the feed does not currently carry.

## Suggested next step

Option 2 or 3, decided deliberately, then measured against the coverage matrix before and
after so any precision lost is visible rather than assumed. The matrix exists for exactly
this: it will show which product types degrade.

## How to reproduce

```bash
AWIN_FEED_FILE=tests/fixtures/provider_feed_coverage_matrix_fixture.csv \
python -c "
import sys; sys.path.insert(0,'src')
from picwise_providers.state import resolve_search_provider_feed_product_selection as sel
for q in ('power bank', 'power bank for iphone', 'comfortable office chair'):
    s = sel(query=q)
    print(q, s.status, s.matched_count)
"
```
