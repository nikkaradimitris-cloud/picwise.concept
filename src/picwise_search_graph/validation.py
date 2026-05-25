from __future__ import annotations

import re

from .contracts import (
    ALIAS_TYPES,
    BrandEntity,
    EDGE_TYPES,
    ELIGIBILITY_STATUSES,
    EntityEdge,
    FORBIDDEN_STANDALONE_BEHAVIORS,
    GRAPH_SCHEMA_VERSION,
    MegaCategoryEntity,
    ProductFamilyEntity,
    ProductOfferEntity,
    QueryAlias,
    SearchEntityGraphEnvelope,
    SearchEntityGraphEntities,
    SpecEntity,
    STANDALONE_BEHAVIORS,
    SubcategoryEntity,
    SUGGESTION_TYPES,
    SuggestionCandidate,
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_FORBIDDEN_UI_ELIGIBILITY_FIELDS = {
    "ui_eligible",
    "show_product_card",
    "product_card_eligible",
    "card_eligible",
}


def _validate_common_fields(
    *,
    entity_id: str,
    source: str,
    quality_flags: tuple[str, ...],
    prefix: str,
) -> list[str]:
    reasons: list[str] = []
    if not entity_id.strip():
        reasons.append(f"{prefix}:entity_id_empty")
    elif _UUID_RE.match(entity_id.strip()):
        reasons.append(f"{prefix}:entity_id_looks_like_random_uuid")
    if not source.strip():
        reasons.append(f"{prefix}:source_empty")
    if not isinstance(quality_flags, tuple):
        reasons.append(f"{prefix}:quality_flags_not_tuple")
    else:
        for index, flag in enumerate(quality_flags):
            if not str(flag).strip():
                reasons.append(f"{prefix}:quality_flag_empty:{index}")
    return reasons


def validate_mega_category_entity(entity: MegaCategoryEntity) -> list[str]:
    reasons = _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="mega_category",
    )
    if not entity.mega_category_id.strip():
        reasons.append("mega_category:mega_category_id_empty")
    return reasons


def validate_subcategory_entity(entity: SubcategoryEntity) -> list[str]:
    reasons = _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="subcategory",
    )
    if not entity.mega_category_id.strip():
        reasons.append("subcategory:mega_category_id_empty")
    if not entity.subcategory_id.strip():
        reasons.append("subcategory:subcategory_id_empty")
    if not entity.display_name.strip():
        reasons.append("subcategory:display_name_empty")
    return reasons


def validate_product_family_entity(entity: ProductFamilyEntity) -> list[str]:
    reasons = _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="product_family",
    )
    if not entity.product_family_id.strip():
        reasons.append("product_family:product_family_id_empty")
    if not entity.canonical_name.strip():
        reasons.append("product_family:canonical_name_empty")
    if not entity.mega_category_id.strip():
        reasons.append("product_family:mega_category_id_empty")
    if not entity.subcategory_id.strip():
        reasons.append("product_family:subcategory_id_empty")
    return reasons


def validate_brand_entity(entity: BrandEntity) -> list[str]:
    reasons = _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="brand",
    )
    if not entity.normalized_brand_name.strip():
        reasons.append("brand:normalized_brand_name_empty")
    if entity.standalone_behavior in FORBIDDEN_STANDALONE_BEHAVIORS:
        reasons.append("brand:standalone_behavior_product_cards_forbidden")
    elif entity.standalone_behavior not in STANDALONE_BEHAVIORS:
        reasons.append("brand:standalone_behavior_not_allowed")
    if entity.standalone_behavior == "product_cards":
        reasons.append("brand:brand_alone_must_not_imply_product_card_eligibility")
    return reasons


def product_offer_implies_ui_eligibility(entity: ProductOfferEntity) -> bool:
    payload_keys = {key.lower() for key in entity.to_dict().keys()}
    if not _FORBIDDEN_UI_ELIGIBILITY_FIELDS.isdisjoint(payload_keys):
        return True
    return False


def validate_product_offer_entity(entity: ProductOfferEntity) -> list[str]:
    reasons = _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="product_offer",
    )
    if not entity.title.strip():
        reasons.append("product_offer:title_empty")
    if not entity.provider_key.strip():
        reasons.append("product_offer:provider_key_empty")
    if entity.eligibility_status not in ELIGIBILITY_STATUSES:
        reasons.append("product_offer:eligibility_status_not_allowed")
    if entity.eligibility_status in {"eligible", "blocked"} and not entity.provider_product_id.strip():
        reasons.append("product_offer:provider_product_id_required_for_status")
    if product_offer_implies_ui_eligibility(entity):
        reasons.append("product_offer:must_not_imply_ui_eligibility")
    return reasons


def validate_spec_entity(entity: SpecEntity) -> list[str]:
    return _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="spec",
    )


def validate_query_alias(entity: QueryAlias) -> list[str]:
    reasons = _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="query_alias",
    )
    if not entity.normalized_alias.strip():
        reasons.append("query_alias:normalized_alias_empty")
    if not entity.target_entity_id.strip():
        reasons.append("query_alias:target_entity_id_empty")
    if not entity.target_entity_type.strip():
        reasons.append("query_alias:target_entity_type_empty")
    if entity.alias_type not in ALIAS_TYPES:
        reasons.append("query_alias:alias_type_not_allowed")
    return reasons


def _is_brand_only_suggestion_text(text: str) -> bool:
    tokens = [token for token in text.strip().lower().split() if token]
    return len(tokens) < 2


def validate_suggestion_candidate(entity: SuggestionCandidate) -> list[str]:
    reasons = _validate_common_fields(
        entity_id=entity.entity_id,
        source=entity.source,
        quality_flags=entity.quality_flags,
        prefix="suggestion",
    )
    if not entity.suggestion_text.strip():
        reasons.append("suggestion:suggestion_text_empty")
    if not entity.target_entity_ids:
        reasons.append("suggestion:target_entity_ids_empty")
    if entity.suggestion_type not in SUGGESTION_TYPES:
        reasons.append("suggestion:suggestion_type_not_allowed")
    if entity.suggestion_type == "brand_product" and _is_brand_only_suggestion_text(entity.suggestion_text):
        reasons.append("suggestion:brand_product_must_not_be_brand_only")
    return reasons


def validate_entity_edge(edge: EntityEdge) -> list[str]:
    reasons: list[str] = []
    if not edge.edge_id.strip():
        reasons.append("edge:edge_id_empty")
    elif _UUID_RE.match(edge.edge_id.strip()):
        reasons.append("edge:edge_id_looks_like_random_uuid")
    if not edge.from_entity_id.strip():
        reasons.append("edge:from_entity_id_empty")
    if not edge.to_entity_id.strip():
        reasons.append("edge:to_entity_id_empty")
    if edge.edge_type not in EDGE_TYPES:
        reasons.append("edge:edge_type_not_allowed")
    if not edge.source.strip():
        reasons.append("edge:source_empty")
    for index, flag in enumerate(edge.quality_flags):
        if not str(flag).strip():
            reasons.append(f"edge:quality_flag_empty:{index}")
    return reasons


def _collect_entity_ids(entities: SearchEntityGraphEntities) -> tuple[list[str], list[str]]:
    entity_ids: list[str] = []
    reasons: list[str] = []

    for collection_name, collection in (
        ("mega_categories", entities.mega_categories),
        ("subcategories", entities.subcategories),
        ("product_families", entities.product_families),
        ("brands", entities.brands),
        ("product_offers", entities.product_offers),
        ("specs", entities.specs),
        ("query_aliases", entities.query_aliases),
        ("suggestions", entities.suggestions),
    ):
        for entity in collection:
            entity_ids.append(entity.entity_id)
            if not entity.entity_id.strip():
                reasons.append(f"entities:{collection_name}:entity_id_empty")

    seen: set[str] = set()
    for entity_id in entity_ids:
        if entity_id in seen:
            reasons.append(f"entities:duplicate_entity_id:{entity_id}")
        seen.add(entity_id)

    return entity_ids, reasons


def validate_search_entity_graph_entities(entities: SearchEntityGraphEntities) -> list[str]:
    reasons: list[str] = []
    for entity in entities.mega_categories:
        reasons.extend(validate_mega_category_entity(entity))
    for entity in entities.subcategories:
        reasons.extend(validate_subcategory_entity(entity))
    for entity in entities.product_families:
        reasons.extend(validate_product_family_entity(entity))
    for entity in entities.brands:
        reasons.extend(validate_brand_entity(entity))
    for entity in entities.product_offers:
        reasons.extend(validate_product_offer_entity(entity))
    for entity in entities.specs:
        reasons.extend(validate_spec_entity(entity))
    for entity in entities.query_aliases:
        reasons.extend(validate_query_alias(entity))
    for entity in entities.suggestions:
        reasons.extend(validate_suggestion_candidate(entity))
    _, duplicate_reasons = _collect_entity_ids(entities)
    reasons.extend(duplicate_reasons)
    return reasons


def validate_search_entity_graph_envelope(envelope: SearchEntityGraphEnvelope) -> dict[str, object]:
    reasons: list[str] = []

    if envelope.graph_schema_version != GRAPH_SCHEMA_VERSION:
        reasons.append("envelope:graph_schema_version_must_be_1_0_0")
    if not envelope.source.strip():
        reasons.append("envelope:source_empty")
    if envelope.entities is None:
        reasons.append("envelope:entities_missing")
    else:
        reasons.extend(validate_search_entity_graph_entities(envelope.entities))
    if envelope.edges is None:
        reasons.append("envelope:edges_missing")
    else:
        seen_edge_ids: set[str] = set()
        for edge in envelope.edges:
            reasons.extend(validate_entity_edge(edge))
            if edge.edge_id in seen_edge_ids:
                reasons.append(f"envelope:duplicate_edge_id:{edge.edge_id}")
            seen_edge_ids.add(edge.edge_id)

    valid = len(reasons) == 0
    return {
        "valid": valid,
        "reasons": tuple(sorted(set(reasons))),
        "graph_schema_version": envelope.graph_schema_version,
        "contract_only": True,
        "runtime_integration": False,
    }
