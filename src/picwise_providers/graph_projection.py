from __future__ import annotations

import re

from picwise_search_graph.contracts import (
    BrandEntity,
    EntityEdge,
    ProductFamilyEntity,
    ProductOfferEntity,
    QueryAlias,
)

from .contracts import ProviderEligibilityResult, ProviderGraphProjectionResult

_GRAPH_SOURCE = "provider_feed_projection"
_UNMAPPED_SUBCATEGORY_PREFIX = "sub_unmapped_provider_"
_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]+")


def _normalize_text(value: object) -> str:
    compact = " ".join(str(value or "").split()).strip().lower()
    return _NORMALIZE_RE.sub(" ", compact).strip()


def _slug(value: str) -> str:
    normalized = _normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "na"


def _graph_eligibility_status(provider_status: str) -> str:
    if provider_status == "eligible":
        return "eligible"
    if provider_status == "needs_review":
        return "needs_review"
    return "blocked"


def project_provider_products_to_graph(
    eligibility_results: tuple[ProviderEligibilityResult, ...],
    *,
    mega_category_id: str = "",
) -> ProviderGraphProjectionResult:
    product_offers: list[ProductOfferEntity] = []
    brands: list[BrandEntity] = []
    product_families: list[ProductFamilyEntity] = []
    query_aliases: list[QueryAlias] = []
    edges: list[EntityEdge] = []
    reason_codes: list[str] = []

    brand_ids: dict[str, str] = {}
    family_ids: dict[str, str] = {}
    safe_mega_category = str(mega_category_id or "unmapped_provider_category").strip()
    unmapped_subcategory_id = f"{_UNMAPPED_SUBCATEGORY_PREFIX}{_slug(safe_mega_category)}"

    for result in eligibility_results:
        if result.status == "blocked":
            reason_codes.append("skipped_blocked_product")
            continue

        product = result.product
        provider_product_id = product.provider_product_id or result.derived_provider_product_id
        offer_entity_id = f"offer_{_slug(product.provider_key)}_{_slug(provider_product_id)}"
        graph_status = _graph_eligibility_status(result.status)

        brand_entity_id = ""
        normalized_brand = _normalize_text(product.brand)
        if normalized_brand:
            brand_entity_id = brand_ids.get(normalized_brand)
            if brand_entity_id is None:
                brand_entity_id = f"brand_{_slug(normalized_brand)}"
                brand_ids[normalized_brand] = brand_entity_id
                brands.append(
                    BrandEntity(
                        entity_id=brand_entity_id,
                        normalized_brand_name=normalized_brand,
                        display_name=product.brand.strip(),
                        aliases=tuple(),
                        standalone_behavior="suggestions_only",
                        source=_GRAPH_SOURCE,
                        quality_flags=("provider_feed_derived", "feed_brand"),
                    )
                )

        product_family_id = ""
        family_entity_id = ""
        normalized_category = _normalize_text(product.category_text)
        if normalized_category:
            product_family_id = f"pf_provider_{_slug(normalized_category)}"
            family_entity_id = family_ids.get(product_family_id)
            if family_entity_id is None:
                family_entity_id = f"pfentity_{product_family_id}"
                family_ids[product_family_id] = family_entity_id
                product_families.append(
                    ProductFamilyEntity(
                        entity_id=family_entity_id,
                        mega_category_id=safe_mega_category,
                        subcategory_id=unmapped_subcategory_id,
                        product_family_id=product_family_id,
                        canonical_name=normalized_category,
                        source=_GRAPH_SOURCE,
                        quality_flags=("provider_feed_derived", "category_text_only", "needs_taxonomy_review"),
                    )
                )
                reason_codes.append("product_family_from_category_text_only")

        offer_flags = ("provider_feed_derived", "no_ui_card_eligibility", "no_canonical_search_term")
        if result.status == "needs_review":
            offer_flags = (*offer_flags, "needs_review")

        product_offers.append(
            ProductOfferEntity(
                entity_id=offer_entity_id,
                provider_key=product.provider_key,
                provider_product_id=provider_product_id,
                title=product.title,
                brand_entity_id=brand_entity_id,
                product_family_id=product_family_id,
                subcategory_id=unmapped_subcategory_id,
                mega_category_id=safe_mega_category,
                url=product.product_url,
                image_url=product.image_url,
                price_text=product.price_text,
                availability_text=product.availability_text,
                source=_GRAPH_SOURCE,
                eligibility_status=graph_status,
                quality_flags=offer_flags,
            )
        )

        if family_entity_id and brand_entity_id:
            alias_text = _normalize_text(f"{normalized_brand} {normalized_category}".strip())
            if alias_text and len(alias_text.split()) >= 2:
                alias_id = f"qa_provider_{_slug(alias_text)}"
                query_aliases.append(
                    QueryAlias(
                        entity_id=alias_id,
                        normalized_alias=alias_text,
                        target_entity_id=family_entity_id,
                        target_entity_type="ProductFamilyEntity",
                        alias_type="feed_derived",
                        source=_GRAPH_SOURCE,
                        quality_flags=("provider_feed_derived", "needs_taxonomy_review"),
                    )
                )
                edges.append(
                    EntityEdge(
                        edge_id=f"edge_{alias_id}_maps_{product_family_id}",
                        from_entity_id=alias_id,
                        to_entity_id=family_entity_id,
                        edge_type="maps_to_product_family",
                        source=_GRAPH_SOURCE,
                        quality_flags=("provider_feed_derived",),
                    )
                )
                if brand_entity_id:
                    edges.append(
                        EntityEdge(
                            edge_id=f"edge_{alias_id}_maps_brand_{brand_entity_id}",
                            from_entity_id=alias_id,
                            to_entity_id=brand_entity_id,
                            edge_type="maps_to_brand",
                            source=_GRAPH_SOURCE,
                            quality_flags=("provider_feed_derived",),
                        )
                    )

    if product_offers:
        reason_codes.append("product_offer_entities_created")
    else:
        reason_codes.append("no_projectable_products")

    return ProviderGraphProjectionResult(
        product_offers=tuple(product_offers),
        brands=tuple(brands),
        product_families=tuple(product_families),
        query_aliases=tuple(query_aliases),
        edges=tuple(edges),
        reason_codes=tuple(sorted(set(reason_codes))),
    )
