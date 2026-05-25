from __future__ import annotations

import re

from picwise_taxonomy.mega_category_registry import get_mega_category_registry
from picwise_taxonomy.nlu_export.exporter import build_taxonomy_nlu_export

from .contracts import (
    EntityEdge,
    GRAPH_SCHEMA_VERSION,
    MegaCategoryEntity,
    ProductFamilyEntity,
    QueryAlias,
    SearchEntityGraphEnvelope,
    SearchEntityGraphEntities,
    SubcategoryEntity,
)
from .export import GraphSearchMemoryTerm, export_graph_search_memory_terms

_GRAPH_BUILDER_SOURCE = "taxonomy_source_builder"
_MIN_TERM_LENGTH = 3
_MAX_TERM_LENGTH = 80
_MAX_TOKEN_COUNT = 8
_TERM_RE = re.compile(r"^[a-z0-9 ]+$")
_OUT_OF_SCOPE_KEYWORDS = {"saas", "erp", "finance", "insurance", "loan", "broker", "banking"}
_UNMAPPED_SUBCATEGORY_PREFIX = "sub_unmapped_"
_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]+")


def _normalize_term(value: object) -> str:
    compact = " ".join(str(value or "").split()).strip().lower()
    return _NORMALIZE_RE.sub(" ", compact).strip()


def _known_mega_category_ids() -> set[str]:
    return {
        str(row.get("mega_category_id", "")).strip()
        for row in get_mega_category_registry()
        if str(row.get("mega_category_id", "")).strip()
    }


def _slug(value: str) -> str:
    normalized = _normalize_term(value)
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "na"


def _is_clean_retail_term(term: str, mega_category_id: str, known_categories: set[str]) -> bool:
    if mega_category_id not in known_categories:
        return False
    if not term or len(term) < _MIN_TERM_LENGTH or len(term) > _MAX_TERM_LENGTH:
        return False
    if len(term.split()) > _MAX_TOKEN_COUNT:
        return False
    if not _TERM_RE.fullmatch(term):
        return False
    if not _OUT_OF_SCOPE_KEYWORDS.isdisjoint(set(term.split())):
        return False
    return True


def _quality_flags(*flags: str, subcategory_missing: bool = False) -> tuple[str, ...]:
    merged = {"graph_derived", "taxonomy_source", "validated_retail"}
    merged.update(flag for flag in flags if flag)
    if subcategory_missing:
        merged.add("subcategory_mapping_missing")
    return tuple(sorted(merged))


def _unmapped_subcategory_id(mega_category_id: str) -> str:
    return f"{_UNMAPPED_SUBCATEGORY_PREFIX}{mega_category_id}"


def _export_taxonomy_bridge_terms():
    from picwise_search_memory.taxonomy_search_memory_bridge import export_taxonomy_search_memory_terms

    return export_taxonomy_search_memory_terms()


def build_search_entity_graph_from_taxonomy() -> SearchEntityGraphEnvelope:
    known_categories = _known_mega_category_ids()
    mega_categories: list[MegaCategoryEntity] = []
    subcategories: list[SubcategoryEntity] = []
    product_families: list[ProductFamilyEntity] = []
    query_aliases: list[QueryAlias] = []
    edges: list[EntityEdge] = []

    subcategory_ids: set[str] = set()
    product_family_ids: set[str] = set()
    alias_ids: set[str] = set()

    for row in get_mega_category_registry():
        mega_category_id = str(row.get("mega_category_id", "")).strip()
        if mega_category_id not in known_categories:
            continue
        entity_id = f"mc_{mega_category_id}"
        mega_categories.append(
            MegaCategoryEntity(
                entity_id=entity_id,
                mega_category_id=mega_category_id,
                display_name=str(row.get("display_name", mega_category_id)).strip(),
                source=_GRAPH_BUILDER_SOURCE,
                quality_flags=_quality_flags("offline_registry"),
            )
        )
        unmapped_id = _unmapped_subcategory_id(mega_category_id)
        if unmapped_id not in subcategory_ids:
            subcategory_ids.add(unmapped_id)
            subcategories.append(
                SubcategoryEntity(
                    entity_id=f"sub_{unmapped_id}",
                    mega_category_id=mega_category_id,
                    subcategory_id=unmapped_id,
                    display_name="Unmapped Subcategory Placeholder",
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=_quality_flags("subcategory_mapping_missing"),
                )
            )
            edges.append(
                EntityEdge(
                    edge_id=f"edge_{unmapped_id}_belongs_{mega_category_id}",
                    from_entity_id=f"sub_{unmapped_id}",
                    to_entity_id=entity_id,
                    edge_type="belongs_to",
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=_quality_flags("subcategory_mapping_missing"),
                )
            )

    nlu_export = build_taxonomy_nlu_export()
    for record in nlu_export.records:
        mega_category_id = record.mega_category_id
        if mega_category_id not in known_categories:
            continue

        subcategory_name = _normalize_term(record.subcategory)
        subcategory_missing = not subcategory_name
        if subcategory_name:
            subcategory_id = f"sub_{mega_category_id}_{_slug(subcategory_name)}"
            subcategory_entity_id = f"subentity_{subcategory_id}"
            if subcategory_id not in subcategory_ids:
                subcategory_ids.add(subcategory_id)
                subcategories.append(
                    SubcategoryEntity(
                        entity_id=subcategory_entity_id,
                        mega_category_id=mega_category_id,
                        subcategory_id=subcategory_id,
                        display_name=record.subcategory.strip() or subcategory_id,
                        source=_GRAPH_BUILDER_SOURCE,
                        quality_flags=_quality_flags(),
                    )
                )
                edges.append(
                    EntityEdge(
                        edge_id=f"edge_{subcategory_id}_belongs_{mega_category_id}",
                        from_entity_id=subcategory_entity_id,
                        to_entity_id=f"mc_{mega_category_id}",
                        edge_type="belongs_to",
                        source=_GRAPH_BUILDER_SOURCE,
                        quality_flags=_quality_flags(),
                    )
                )
        else:
            subcategory_id = _unmapped_subcategory_id(mega_category_id)
            subcategory_entity_id = f"sub_{subcategory_id}"

        product_family_name = _normalize_term(record.product_family)
        primary_alias = next(
            (
                _normalize_term(alias)
                for alias in record.aliases
                if _is_clean_retail_term(_normalize_term(alias), mega_category_id, known_categories)
            ),
            "",
        )
        canonical_name = primary_alias or product_family_name
        if not _is_clean_retail_term(canonical_name, mega_category_id, known_categories):
            continue

        product_family_id = f"pf_{mega_category_id}_{_slug(canonical_name)}"
        if product_family_id not in product_family_ids:
            product_family_ids.add(product_family_id)
            pf_entity_id = f"pfentity_{product_family_id}"
            pf_flags = _quality_flags(subcategory_missing=subcategory_missing)
            product_families.append(
                ProductFamilyEntity(
                    entity_id=pf_entity_id,
                    mega_category_id=mega_category_id,
                    subcategory_id=subcategory_id,
                    product_family_id=product_family_id,
                    canonical_name=canonical_name,
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=pf_flags,
                )
            )
            edges.append(
                EntityEdge(
                    edge_id=f"edge_{product_family_id}_belongs_{subcategory_id}",
                    from_entity_id=pf_entity_id,
                    to_entity_id=subcategory_entity_id,
                    edge_type="belongs_to",
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=pf_flags,
                )
            )

        pf_entity_id = f"pfentity_{product_family_id}"
        for alias in (*record.signals.aliases, *record.signals.typo_variants):
            normalized_alias = _normalize_term(alias)
            if not _is_clean_retail_term(normalized_alias, mega_category_id, known_categories):
                continue
            if normalized_alias == canonical_name:
                continue
            alias_id = f"qa_{mega_category_id}_{_slug(normalized_alias)}"
            if alias_id in alias_ids:
                continue
            alias_ids.add(alias_id)
            query_aliases.append(
                QueryAlias(
                    entity_id=alias_id,
                    normalized_alias=normalized_alias,
                    target_entity_id=pf_entity_id,
                    target_entity_type="ProductFamilyEntity",
                    alias_type="typo_seed" if normalized_alias in record.signals.typo_variants else "synonym",
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=_quality_flags(subcategory_missing=subcategory_missing),
                )
            )
            edges.append(
                EntityEdge(
                    edge_id=f"edge_{alias_id}_maps_{product_family_id}",
                    from_entity_id=alias_id,
                    to_entity_id=pf_entity_id,
                    edge_type="maps_to_product_family",
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=_quality_flags(subcategory_missing=subcategory_missing),
                )
            )

    for bridge_term in _export_taxonomy_bridge_terms():
        mega_category_id = bridge_term.mega_category_id
        canonical_name = _normalize_term(bridge_term.canonical_term)
        if not _is_clean_retail_term(canonical_name, mega_category_id, known_categories):
            continue
        product_family_id = f"pf_{mega_category_id}_{_slug(canonical_name)}"
        if product_family_id in product_family_ids:
            continue
        product_family_ids.add(product_family_id)
        subcategory_id = _unmapped_subcategory_id(mega_category_id)
        subcategory_entity_id = f"sub_{subcategory_id}"
        pf_entity_id = f"pfentity_{product_family_id}"
        pf_flags = _quality_flags("taxonomy_bridge", subcategory_missing=True)
        product_families.append(
            ProductFamilyEntity(
                entity_id=pf_entity_id,
                mega_category_id=mega_category_id,
                subcategory_id=subcategory_id,
                product_family_id=product_family_id,
                canonical_name=canonical_name,
                source=_GRAPH_BUILDER_SOURCE,
                quality_flags=pf_flags,
            )
        )
        edges.append(
            EntityEdge(
                edge_id=f"edge_{product_family_id}_belongs_{subcategory_id}",
                from_entity_id=pf_entity_id,
                to_entity_id=subcategory_entity_id,
                edge_type="belongs_to",
                source=_GRAPH_BUILDER_SOURCE,
                quality_flags=pf_flags,
            )
        )
        for alias in bridge_term.aliases:
            normalized_alias = _normalize_term(alias)
            if not _is_clean_retail_term(normalized_alias, mega_category_id, known_categories):
                continue
            if normalized_alias == canonical_name:
                continue
            alias_id = f"qa_{mega_category_id}_{_slug(normalized_alias)}"
            if alias_id in alias_ids:
                continue
            alias_ids.add(alias_id)
            query_aliases.append(
                QueryAlias(
                    entity_id=alias_id,
                    normalized_alias=normalized_alias,
                    target_entity_id=pf_entity_id,
                    target_entity_type="ProductFamilyEntity",
                    alias_type="synonym",
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=pf_flags,
                )
            )
            edges.append(
                EntityEdge(
                    edge_id=f"edge_{alias_id}_maps_{product_family_id}",
                    from_entity_id=alias_id,
                    to_entity_id=pf_entity_id,
                    edge_type="maps_to_product_family",
                    source=_GRAPH_BUILDER_SOURCE,
                    quality_flags=pf_flags,
                )
            )

    entities = SearchEntityGraphEntities(
        mega_categories=tuple(sorted(mega_categories, key=lambda row: row.entity_id)),
        subcategories=tuple(sorted(subcategories, key=lambda row: row.entity_id)),
        product_families=tuple(sorted(product_families, key=lambda row: row.entity_id)),
        query_aliases=tuple(sorted(query_aliases, key=lambda row: row.entity_id)),
    )
    ordered_edges = tuple(sorted(edges, key=lambda row: row.edge_id))
    return SearchEntityGraphEnvelope(
        graph_schema_version=GRAPH_SCHEMA_VERSION,
        source=_GRAPH_BUILDER_SOURCE,
        entities=entities,
        edges=ordered_edges,
        export_notes=("conservative_taxonomy_projection", "no_provider_connection", "no_ui_card_eligibility"),
    )


def export_graph_search_memory_terms_from_taxonomy() -> tuple[GraphSearchMemoryTerm, ...]:
    envelope = build_search_entity_graph_from_taxonomy()
    return export_graph_search_memory_terms(envelope)
