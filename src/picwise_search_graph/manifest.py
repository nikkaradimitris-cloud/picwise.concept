from __future__ import annotations

import json
from copy import deepcopy

_MANIFEST = {
    "stage_id": "1D-B1",
    "stage_name": "picwise_search_entity_graph_contracts",
    "purpose": (
        "Define upstream Search Entity Graph contracts for product-world semantic structure. "
        "This module is contract-only and does not change live search runtime behavior."
    ),
    "module_path": "src/picwise_search_graph/",
    "position_in_pipeline": {
        "upstream_of_search_memory": True,
        "does_not_replace_resolver": True,
        "resolver_remains_thin_orchestration": True,
    },
    "graph_capabilities_future": [
        "query_autocomplete_and_suggestions",
        "brand_and_product_understanding",
        "subcategory_and_product_family_mapping",
        "feed_derived_product_understanding",
        "future_graph_export_into_search_memory_index",
        "future_ranking_and_4_plus_1_pipeline_input",
    ],
    "explicit_non_goals": {
        "does_not_show_product_cards": True,
        "does_not_rank_products": True,
        "does_not_connect_providers": True,
        "brand_only_terms_do_not_trigger_product_cards": True,
        "feed_products_do_not_automatically_become_eligible_cards": True,
        "no_runtime_resolver_integration_in_this_stage": True,
        "no_autocomplete_ui_in_this_stage": True,
        "no_artifact_rebuild_in_this_stage": True,
    },
    "future_stages": {
        "stage_1d_b2": "graph export into canonical_registry / search memory",
        "stage_1d_b6": "ranking / 4+1 pipeline integration",
        "stage_8a": "provider and feed integration",
    },
    "entity_types": [
        "MegaCategoryEntity",
        "SubcategoryEntity",
        "ProductFamilyEntity",
        "BrandEntity",
        "ProductOfferEntity",
        "SpecEntity",
        "QueryAlias",
        "SuggestionCandidate",
        "EntityEdge",
        "SearchEntityGraphEnvelope",
    ],
}


def get_search_entity_graph_manifest() -> dict:
    """Return deterministic Stage 1D-B1 Search Entity Graph manifest."""
    return deepcopy(_MANIFEST)


def validate_search_entity_graph_manifest() -> dict:
    """Validate Stage 1D-B1 manifest boundaries and serialization."""
    manifest = get_search_entity_graph_manifest()
    result = {
        "valid": True,
        "passed": True,
        "is_json_serializable": True,
        "stage_id_is_1d_b1": manifest["stage_id"] == "1D-B1",
        "upstream_of_search_memory": manifest["position_in_pipeline"]["upstream_of_search_memory"],
        "does_not_replace_resolver": manifest["position_in_pipeline"]["does_not_replace_resolver"],
        "does_not_show_product_cards": manifest["explicit_non_goals"]["does_not_show_product_cards"],
        "does_not_rank_products": manifest["explicit_non_goals"]["does_not_rank_products"],
        "does_not_connect_providers": manifest["explicit_non_goals"]["does_not_connect_providers"],
        "future_export_stage_is_1d_b2": manifest["future_stages"]["stage_1d_b2"].startswith("graph export"),
        "future_ranking_stage_is_1d_b6": "ranking" in manifest["future_stages"]["stage_1d_b6"],
        "future_provider_stage_is_8a": manifest["future_stages"]["stage_8a"].startswith("provider"),
        "has_all_entity_types": len(manifest["entity_types"]) == 10,
        "no_runtime_integration_flag": manifest["explicit_non_goals"]["no_runtime_resolver_integration_in_this_stage"],
    }

    try:
        json.dumps(manifest, sort_keys=True)
    except (TypeError, ValueError):
        result["is_json_serializable"] = False

    result["valid"] = all(
        [
            result["is_json_serializable"],
            result["stage_id_is_1d_b1"],
            result["upstream_of_search_memory"],
            result["does_not_replace_resolver"],
            result["does_not_show_product_cards"],
            result["does_not_rank_products"],
            result["does_not_connect_providers"],
            result["future_export_stage_is_1d_b2"],
            result["future_ranking_stage_is_1d_b6"],
            result["future_provider_stage_is_8a"],
            result["has_all_entity_types"],
            result["no_runtime_integration_flag"],
        ]
    )
    result["passed"] = result["valid"]
    return result
