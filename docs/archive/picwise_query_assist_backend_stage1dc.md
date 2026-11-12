# PicWise Query Assist Backend — Stage 1D-C

## Purpose

Stage 1D-C adds a backend-only query assist / autocomplete suggestion mechanism on top of the Search Entity Graph envelope. It does not change live search resolver behavior, UI, routes, providers, or the search runtime artifact.

## Module

- `src/picwise_search_graph/suggestions.py`

## Public API

### `QueryAssistSuggestion`

Serializable suggestion result with:

- `suggestion_text` — normalized lowercase phrase
- `suggestion_type` — one of `product_family`, `brand_product`, `spec_product`, `broad_clarification`
- `target_entity_ids` — graph entity IDs referenced by the suggestion
- `score` — deterministic matching confidence (not popularity)
- `source` — graph entity source label
- `reason_codes` — explain match provenance (prefix, token prefix, fuzzy, graph seed type)

### `build_query_assist_suggestions(envelope, partial_query, *, max_suggestions=8)`

Builds ranked suggestions from a validated `SearchEntityGraphEnvelope`.

## Candidate sources (data-driven)

1. `SuggestionCandidate` entities
2. `ProductFamilyEntity.canonical_name`
3. `BrandEntity` + `ProductFamilyEntity` linked by `appears_in` edges
4. `QueryAlias.normalized_alias` mapped to product families (including brand/spec modifiers)

No Nike/Apple/Bosch or other brand names are hardcoded in production logic. Suggestions appear only when matching entities, aliases, edges, or suggestion candidates exist in the supplied envelope.

## Matching behavior

Partial queries are normalized (lowercase, punctuation stripped, whitespace collapsed).

Supported match modes, in descending score order:

1. **Exact prefix** — `"nike"` matches `"nike running shoes"`
2. **Token prefix** — `"bosch dr"` matches `"bosch drill"`
3. **Fuzzy token prefix** — `"appel tab"` matches `"apple tablet"` via per-token prefix / small edit distance

Results are deduplicated by `suggestion_text`, ordered by score (desc), then shorter text, then alphabetical. `max_suggestions` caps output.

## Brand-only safety

- Brand-only phrases (single token) are never emitted as suggestions.
- Brand prefix input (e.g. `"nik"`) may resolve to brand+product suggestions such as `"nike running shoes"` when the graph contains valid brand/product edges or candidates.
- Suggestions do not include provider keys, prices, URLs, popularity, or product-card eligibility fields.
- Suggestions are backend assist only; they do not imply provider connection or ranking/4+1 selection.

## Explicit non-goals (this stage)

- No autocomplete UI dropdown
- No resolver / index / artifact changes
- No provider or feed integration
- No fake products or popularity numbers
- No production hardcoded brand fixtures

## Tests

`tests/test_picwise_search_graph_query_assist_stage1dc.py` uses fixture-only graph data (including Nike/Apple/Bosch entities) to prove matching, brand safety, dedupe, and data-driven behavior.

## Recommended next stage

**Stage 1D-C UI** — wire query assist API endpoint and frontend dropdown, still without resolver/provider changes; or **Brand Graph Source stage** if real production brand suggestions from feed/curated data are required.
