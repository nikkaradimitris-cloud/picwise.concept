from __future__ import annotations

import re
from dataclasses import dataclass, field

from .contracts import (
    BrandEntity,
    ProductFamilyEntity,
    ProductOfferEntity,
    QueryAlias,
    SearchEntityGraphEnvelope,
    SuggestionCandidate,
)
from .validation import validate_search_entity_graph_envelope

_GRAPH_SOURCE = "search_entity_graph"
_MIN_TERM_LENGTH = 3
_MAX_TERM_LENGTH = 80
_MAX_TOKEN_COUNT = 8
_TERM_RE = re.compile(r"^[a-z0-9 ]+$")
_OUT_OF_SCOPE_KEYWORDS = {"saas", "erp", "finance", "insurance", "loan", "broker", "banking"}
_PROJECTION_TYPES = (
    "product_family_canonical",
    "query_alias",
    "brand_product_alias",
    "spec_product_alias",
    "subcategory_product_alias",
)


def _normalize_term(value: object) -> str:
    compact = " ".join(str(value or "").split()).strip().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", compact).strip()


def _is_safe_export_term(normalized_term: str) -> bool:
    if not normalized_term:
        return False
    if len(normalized_term) < _MIN_TERM_LENGTH:
        return False
    if len(normalized_term) > _MAX_TERM_LENGTH:
        return False
    if len(normalized_term.split()) > _MAX_TOKEN_COUNT:
        return False
    if not _TERM_RE.fullmatch(normalized_term):
        return False
    if not _OUT_OF_SCOPE_KEYWORDS.isdisjoint(set(normalized_term.split())):
        return False
    return True


@dataclass(frozen=True)
class GraphSearchMemoryTerm:
    canonical_term: str
    mega_category_id: str
    source: str
    source_file: str
    source_path: str
    status: str
    quality_flags: tuple[str, ...]
    aliases: tuple[str, ...] = field(default_factory=tuple)
    product_family: str = ""
    graph_entity_id: str = ""
    graph_entity_type: str = ""
    subcategory_id: str = ""
    brand_entity_id: str = ""
    projection_type: str = ""

    def to_dict(self) -> dict:
        payload = {
            "canonical_term": self.canonical_term,
            "mega_category_id": self.mega_category_id,
            "source": self.source,
            "source_file": self.source_file,
            "source_path": self.source_path,
            "status": self.status,
            "quality_flags": list(self.quality_flags),
            "aliases": list(self.aliases),
            "product_family": self.product_family,
            "graph_entity_id": self.graph_entity_id,
            "graph_entity_type": self.graph_entity_type,
            "subcategory_id": self.subcategory_id,
            "projection_type": self.projection_type,
        }
        if self.brand_entity_id:
            payload["brand_entity_id"] = self.brand_entity_id
        return payload


def _dedupe_aliases(values: tuple[str, ...], canonical_term: str) -> tuple[str, ...]:
    aliases = sorted({_normalize_term(value) for value in values if _normalize_term(value)})
    return tuple(
        alias
        for alias in aliases
        if alias != canonical_term and _is_safe_export_term(alias)
    )


def _make_term(
    *,
    canonical_term: str,
    mega_category_id: str,
    source_file: str,
    source_path: str,
    status: str,
    quality_flags: tuple[str, ...],
    projection_type: str,
    aliases: tuple[str, ...] = (),
    product_family: str = "",
    graph_entity_id: str = "",
    graph_entity_type: str = "",
    subcategory_id: str = "",
    brand_entity_id: str = "",
) -> GraphSearchMemoryTerm | None:
    normalized = _normalize_term(canonical_term)
    if not _is_safe_export_term(normalized):
        return None
    if projection_type not in _PROJECTION_TYPES:
        return None
    merged_flags = tuple(sorted(set(quality_flags + ("graph_derived", "search_entity_graph_export"))))
    return GraphSearchMemoryTerm(
        canonical_term=normalized,
        mega_category_id=mega_category_id,
        source=_GRAPH_SOURCE,
        source_file=source_file,
        source_path=source_path,
        status=status,
        quality_flags=merged_flags,
        aliases=_dedupe_aliases(aliases, normalized),
        product_family=_normalize_term(product_family) or normalized,
        graph_entity_id=graph_entity_id,
        graph_entity_type=graph_entity_type,
        subcategory_id=subcategory_id,
        brand_entity_id=brand_entity_id,
        projection_type=projection_type,
    )


def _entity_maps(
    envelope: SearchEntityGraphEnvelope,
) -> tuple[
    dict[str, ProductFamilyEntity],
    dict[str, BrandEntity],
    dict[str, ProductOfferEntity],
    dict[str, SuggestionCandidate],
]:
    product_families = {entity.entity_id: entity for entity in envelope.entities.product_families}
    brands = {entity.entity_id: entity for entity in envelope.entities.brands}
    product_offers = {entity.entity_id: entity for entity in envelope.entities.product_offers}
    suggestions = {entity.entity_id: entity for entity in envelope.entities.suggestions}
    return product_families, brands, product_offers, suggestions


def export_graph_search_memory_terms(
    envelope: SearchEntityGraphEnvelope,
) -> tuple[GraphSearchMemoryTerm, ...]:
    validation = validate_search_entity_graph_envelope(envelope)
    if not validation["valid"]:
        reasons = ", ".join(str(reason) for reason in validation["reasons"])
        raise ValueError(f"Search entity graph envelope validation failed: {reasons}")

    product_families, brands, _product_offers, _suggestions = _entity_maps(envelope)
    exported: list[GraphSearchMemoryTerm] = []
    seen: set[tuple[str, str, str]] = set()

    def _append(term: GraphSearchMemoryTerm | None) -> None:
        if term is None:
            return
        signature = (term.mega_category_id, term.canonical_term, term.projection_type)
        if signature in seen:
            return
        seen.add(signature)
        exported.append(term)

    for entity in envelope.entities.product_families:
        flags = tuple(sorted(set(entity.quality_flags + ("taxonomy_source",))))
        _append(
            _make_term(
                canonical_term=entity.canonical_name,
                mega_category_id=entity.mega_category_id,
                source_file="export.py",
                source_path=f"graph_entity:{entity.entity_id}",
                status="active",
                quality_flags=flags,
                projection_type="product_family_canonical",
                product_family=entity.canonical_name,
                graph_entity_id=entity.entity_id,
                graph_entity_type="ProductFamilyEntity",
                subcategory_id=entity.subcategory_id,
            )
        )

    for alias in envelope.entities.query_aliases:
        if alias.target_entity_type == "BrandEntity":
            continue
        if alias.target_entity_type != "ProductFamilyEntity":
            continue
        target = product_families.get(alias.target_entity_id)
        if target is None:
            continue

        projection_type = "query_alias"
        brand_entity_id = ""
        if alias.alias_type == "brand_modifier":
            projection_type = "brand_product_alias"
            for edge in envelope.edges:
                if edge.edge_type != "maps_to_brand" or edge.from_entity_id != alias.entity_id:
                    continue
                brand_entity_id = edge.to_entity_id
                if brand_entity_id not in brands:
                    brand_entity_id = ""
                break
            if not brand_entity_id:
                continue
        elif alias.alias_type == "spec_modifier":
            projection_type = "spec_product_alias"

        flags = tuple(sorted(set(alias.quality_flags + target.quality_flags + ("taxonomy_source",))))
        _append(
            _make_term(
                canonical_term=alias.normalized_alias,
                mega_category_id=target.mega_category_id,
                source_file="export.py",
                source_path=f"graph_alias:{alias.entity_id}",
                status="active",
                quality_flags=flags,
                projection_type=projection_type,
                product_family=target.canonical_name,
                aliases=(target.canonical_name,),
                graph_entity_id=alias.entity_id,
                graph_entity_type="QueryAlias",
                subcategory_id=target.subcategory_id,
                brand_entity_id=brand_entity_id,
            )
        )

    ordered = tuple(
        sorted(
            exported,
            key=lambda row: (row.mega_category_id, row.canonical_term, row.projection_type),
        )
    )
    return ordered
