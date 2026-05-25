from __future__ import annotations

from dataclasses import dataclass, field

GRAPH_SCHEMA_VERSION = "1.0.0"

STANDALONE_BEHAVIORS = ("suggestions_only", "safe_broad", "blocked")
FORBIDDEN_STANDALONE_BEHAVIORS = ("product_cards",)

ELIGIBILITY_STATUSES = ("imported", "needs_review", "eligible", "blocked")

ALIAS_TYPES = (
    "canonical",
    "synonym",
    "typo_seed",
    "brand_modifier",
    "spec_modifier",
    "feed_derived",
)

SUGGESTION_TYPES = (
    "product_family",
    "brand_product",
    "spec_product",
    "broad_clarification",
)

EDGE_TYPES = (
    "belongs_to",
    "appears_in",
    "has_brand",
    "maps_to_product_family",
    "maps_to_subcategory",
    "maps_to_brand",
    "refines",
    "combines",
)


def _quality_flags_to_list(flags: tuple[str, ...]) -> list[str]:
    return list(flags)


def _quality_flags_from_data(data: object) -> tuple[str, ...]:
    return tuple(str(flag) for flag in (data or ()) if str(flag).strip())


@dataclass(frozen=True)
class MegaCategoryEntity:
    entity_id: str
    mega_category_id: str
    display_name: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "mega_category_id": self.mega_category_id,
            "display_name": self.display_name,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> MegaCategoryEntity:
        return cls(
            entity_id=str(data["entity_id"]),
            mega_category_id=str(data["mega_category_id"]),
            display_name=str(data["display_name"]),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class SubcategoryEntity:
    entity_id: str
    mega_category_id: str
    subcategory_id: str
    display_name: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "mega_category_id": self.mega_category_id,
            "subcategory_id": self.subcategory_id,
            "display_name": self.display_name,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SubcategoryEntity:
        return cls(
            entity_id=str(data["entity_id"]),
            mega_category_id=str(data["mega_category_id"]),
            subcategory_id=str(data["subcategory_id"]),
            display_name=str(data["display_name"]),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class ProductFamilyEntity:
    entity_id: str
    mega_category_id: str
    subcategory_id: str
    product_family_id: str
    canonical_name: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "mega_category_id": self.mega_category_id,
            "subcategory_id": self.subcategory_id,
            "product_family_id": self.product_family_id,
            "canonical_name": self.canonical_name,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProductFamilyEntity:
        return cls(
            entity_id=str(data["entity_id"]),
            mega_category_id=str(data["mega_category_id"]),
            subcategory_id=str(data["subcategory_id"]),
            product_family_id=str(data["product_family_id"]),
            canonical_name=str(data["canonical_name"]),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class BrandEntity:
    entity_id: str
    normalized_brand_name: str
    display_name: str
    aliases: tuple[str, ...]
    standalone_behavior: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "normalized_brand_name": self.normalized_brand_name,
            "display_name": self.display_name,
            "aliases": list(self.aliases),
            "standalone_behavior": self.standalone_behavior,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> BrandEntity:
        return cls(
            entity_id=str(data["entity_id"]),
            normalized_brand_name=str(data["normalized_brand_name"]),
            display_name=str(data["display_name"]),
            aliases=tuple(str(alias) for alias in data.get("aliases") or ()),
            standalone_behavior=str(data["standalone_behavior"]),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class ProductOfferEntity:
    entity_id: str
    provider_key: str
    provider_product_id: str
    title: str
    brand_entity_id: str
    product_family_id: str
    subcategory_id: str
    mega_category_id: str
    url: str
    image_url: str
    price_text: str
    availability_text: str
    source: str
    eligibility_status: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "provider_key": self.provider_key,
            "provider_product_id": self.provider_product_id,
            "title": self.title,
            "brand_entity_id": self.brand_entity_id,
            "product_family_id": self.product_family_id,
            "subcategory_id": self.subcategory_id,
            "mega_category_id": self.mega_category_id,
            "url": self.url,
            "image_url": self.image_url,
            "price_text": self.price_text,
            "availability_text": self.availability_text,
            "source": self.source,
            "eligibility_status": self.eligibility_status,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProductOfferEntity:
        return cls(
            entity_id=str(data["entity_id"]),
            provider_key=str(data["provider_key"]),
            provider_product_id=str(data.get("provider_product_id") or ""),
            title=str(data["title"]),
            brand_entity_id=str(data["brand_entity_id"]),
            product_family_id=str(data["product_family_id"]),
            subcategory_id=str(data["subcategory_id"]),
            mega_category_id=str(data["mega_category_id"]),
            url=str(data.get("url") or ""),
            image_url=str(data.get("image_url") or ""),
            price_text=str(data.get("price_text") or ""),
            availability_text=str(data.get("availability_text") or ""),
            source=str(data["source"]),
            eligibility_status=str(data["eligibility_status"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class SpecEntity:
    entity_id: str
    spec_name: str
    spec_value: str
    unit: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "spec_name": self.spec_name,
            "spec_value": self.spec_value,
            "unit": self.unit,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SpecEntity:
        return cls(
            entity_id=str(data["entity_id"]),
            spec_name=str(data["spec_name"]),
            spec_value=str(data["spec_value"]),
            unit=str(data.get("unit") or ""),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class QueryAlias:
    entity_id: str
    normalized_alias: str
    target_entity_id: str
    target_entity_type: str
    alias_type: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "normalized_alias": self.normalized_alias,
            "target_entity_id": self.target_entity_id,
            "target_entity_type": self.target_entity_type,
            "alias_type": self.alias_type,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> QueryAlias:
        return cls(
            entity_id=str(data["entity_id"]),
            normalized_alias=str(data["normalized_alias"]),
            target_entity_id=str(data["target_entity_id"]),
            target_entity_type=str(data["target_entity_type"]),
            alias_type=str(data["alias_type"]),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class SuggestionCandidate:
    entity_id: str
    suggestion_text: str
    target_entity_ids: tuple[str, ...]
    suggestion_type: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "suggestion_text": self.suggestion_text,
            "target_entity_ids": list(self.target_entity_ids),
            "suggestion_type": self.suggestion_type,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SuggestionCandidate:
        return cls(
            entity_id=str(data["entity_id"]),
            suggestion_text=str(data["suggestion_text"]),
            target_entity_ids=tuple(str(entity_id) for entity_id in data.get("target_entity_ids") or ()),
            suggestion_type=str(data["suggestion_type"]),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class EntityEdge:
    edge_id: str
    from_entity_id: str
    to_entity_id: str
    edge_type: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "from_entity_id": self.from_entity_id,
            "to_entity_id": self.to_entity_id,
            "edge_type": self.edge_type,
            "source": self.source,
            "quality_flags": _quality_flags_to_list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> EntityEdge:
        return cls(
            edge_id=str(data["edge_id"]),
            from_entity_id=str(data["from_entity_id"]),
            to_entity_id=str(data["to_entity_id"]),
            edge_type=str(data["edge_type"]),
            source=str(data["source"]),
            quality_flags=_quality_flags_from_data(data.get("quality_flags")),
        )


@dataclass(frozen=True)
class SearchEntityGraphEntities:
    mega_categories: tuple[MegaCategoryEntity, ...] = field(default_factory=tuple)
    subcategories: tuple[SubcategoryEntity, ...] = field(default_factory=tuple)
    product_families: tuple[ProductFamilyEntity, ...] = field(default_factory=tuple)
    brands: tuple[BrandEntity, ...] = field(default_factory=tuple)
    product_offers: tuple[ProductOfferEntity, ...] = field(default_factory=tuple)
    specs: tuple[SpecEntity, ...] = field(default_factory=tuple)
    query_aliases: tuple[QueryAlias, ...] = field(default_factory=tuple)
    suggestions: tuple[SuggestionCandidate, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "mega_categories": [entity.to_dict() for entity in self.mega_categories],
            "subcategories": [entity.to_dict() for entity in self.subcategories],
            "product_families": [entity.to_dict() for entity in self.product_families],
            "brands": [entity.to_dict() for entity in self.brands],
            "product_offers": [entity.to_dict() for entity in self.product_offers],
            "specs": [entity.to_dict() for entity in self.specs],
            "query_aliases": [entity.to_dict() for entity in self.query_aliases],
            "suggestions": [entity.to_dict() for entity in self.suggestions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchEntityGraphEntities:
        return cls(
            mega_categories=tuple(
                MegaCategoryEntity.from_dict(entity) for entity in data.get("mega_categories") or ()
            ),
            subcategories=tuple(SubcategoryEntity.from_dict(entity) for entity in data.get("subcategories") or ()),
            product_families=tuple(
                ProductFamilyEntity.from_dict(entity) for entity in data.get("product_families") or ()
            ),
            brands=tuple(BrandEntity.from_dict(entity) for entity in data.get("brands") or ()),
            product_offers=tuple(
                ProductOfferEntity.from_dict(entity) for entity in data.get("product_offers") or ()
            ),
            specs=tuple(SpecEntity.from_dict(entity) for entity in data.get("specs") or ()),
            query_aliases=tuple(QueryAlias.from_dict(entity) for entity in data.get("query_aliases") or ()),
            suggestions=tuple(
                SuggestionCandidate.from_dict(entity) for entity in data.get("suggestions") or ()
            ),
        )


@dataclass(frozen=True)
class SearchEntityGraphEnvelope:
    graph_schema_version: str
    source: str
    entities: SearchEntityGraphEntities
    edges: tuple[EntityEdge, ...]
    export_notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "graph_schema_version": self.graph_schema_version,
            "source": self.source,
            "entities": self.entities.to_dict(),
            "edges": [edge.to_dict() for edge in self.edges],
            "export_notes": list(self.export_notes),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchEntityGraphEnvelope:
        return cls(
            graph_schema_version=str(data["graph_schema_version"]),
            source=str(data["source"]),
            entities=SearchEntityGraphEntities.from_dict(data.get("entities") or {}),
            edges=tuple(EntityEdge.from_dict(edge) for edge in data.get("edges") or ()),
            export_notes=tuple(str(note) for note in data.get("export_notes") or ()),
        )
