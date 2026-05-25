# Stage 1D-B1 — Search Entity Graph Contracts

## Scope

Stage 1D-B1 defines the Search Entity Graph contract foundation as a new upstream semantic layer.
This stage is contract-only: dataclasses, validators, manifest, and tests.

The graph describes product-world structure for future search intelligence.
It does not change live search runtime behavior.

## Module

- Package: `src/picwise_search_graph/`
- Stage ID: `1D-B1`

## Position in Pipeline

- The graph sits **upstream of search memory**.
- The live search resolver remains thin orchestration and is **not replaced**.
- Graph export into `canonical_registry` is planned for **Stage 1D-B2**.
- Ranking / 4+1 pipeline integration is planned for **Stage 1D-B6**.
- Provider and feed integration is planned for **Stage 8A**.

## Entity Types

- `MegaCategoryEntity`
- `SubcategoryEntity`
- `ProductFamilyEntity`
- `BrandEntity`
- `ProductOfferEntity` (graph entity only; does not imply UI cards or provider connection)
- `SpecEntity`
- `QueryAlias`
- `SuggestionCandidate`
- `EntityEdge`
- `SearchEntityGraphEnvelope`

## Safety Boundaries

- Brand-only terms must not become product-card triggers.
- `BrandEntity.standalone_behavior` forbids `product_cards`.
- Feed products must not automatically become eligible cards.
- `ProductOfferEntity.eligibility_status` tracks graph import state only; `eligible` does not mean UI card output.
- No runtime resolver integration in this stage.
- No autocomplete UI in this stage.
- No provider connection in this stage.
- No ranking / 4+1 logic in this stage.
- No artifact rebuild in this stage.

## Non-goals in Stage 1D-B1

- No changes to `live_search_resolver.py`
- No changes to search index builder or runtime artifact paths
- No UI or route changes
- No provider behavior changes
- No production seed data
- No commit of runtime wiring

## Future Stages

| Stage | Purpose |
| --- | --- |
| 1D-B2 | Graph export into canonical registry / search memory |
| 1D-B6 | Ranking / 4+1 pipeline integration |
| 8A | Provider and feed integration |
