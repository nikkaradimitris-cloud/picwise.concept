# Stage 1D-B2 — Search Entity Graph Export into Search Memory

## Scope

Stage 1D-B2 activates the Search Entity Graph as an upstream source layer for PicWise search memory.

This stage wires:

- graph export projection (`export.py`)
- conservative taxonomy graph source builder (`taxonomy_source.py`)
- canonical registry merge layer (`canonical_registry.py`)
- artifact fingerprint updates (`search_runtime_artifact.py`)
- rebuilt search runtime artifact

This stage does **not** change live resolver orchestration, UI, provider behavior, or ranking logic.

## Pipeline Position

```
taxonomy / future feeds
→ Search Entity Graph
→ graph export records
→ canonical_registry
→ index_builder
→ search_runtime_artifact
→ existing resolver
→ provider gate
→ UI
```

## New Modules

| Module | Purpose |
| --- | --- |
| `src/picwise_search_graph/export.py` | `GraphSearchMemoryTerm` projection and export rules |
| `src/picwise_search_graph/taxonomy_source.py` | Conservative graph builder from taxonomy/search sources |

## Export Rules

- `source` is always `search_entity_graph`
- Product families export as `product_family_canonical`
- Safe query aliases export as `query_alias` or `brand_product_alias` only when mapped to `ProductFamilyEntity`
- Brand-only aliases mapped to `BrandEntity` are rejected
- `ProductOfferEntity` and `SuggestionCandidate` do not export as canonical search terms
- Graph export does not imply provider connection or UI card eligibility

## Registry Wiring

`build_canonical_vocabulary_registry()` merges graph export terms after existing deep-pack, coverage, and taxonomy bridge layers.

Graph records use:

- `source = search_entity_graph`
- `status = active`
- quality flags include `graph_derived`, `validated_english_retail`, `offline_registry`

Dedupe uses existing `(mega_category_id, normalized_term)` signature logic.

## Artifact Fingerprint

`get_fingerprint_source_paths()` now includes all graph source files and `graph_schema_version` in the fingerprint payload.

## Safety Boundaries Preserved

- No UI changes
- No provider/feed adapter changes
- No resolver rewrite
- No fake/demo products
- Brand-only terms do not become product-card paths
- Broad-query and collision guards remain unchanged

## Tests

- `tests/test_picwise_search_graph_export_stage1db2.py`
- `tests/test_picwise_search_graph_registry_integration_stage1db2.py`
- `tests/test_picwise_search_graph_runtime_recognition_stage1db2.py`

## Next Stage

Stage 1D-B6 — ranking / 4+1 pipeline integration input from graph-enriched search memory.
