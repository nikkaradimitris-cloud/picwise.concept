from __future__ import annotations

import json
from copy import deepcopy

_FORBIDDEN_COMMERCIAL_TERMS = [
    "product",
    "products",
    "sku",
    "offer",
    "offers",
    "price",
    "affiliate",
    "seller",
    "store",
    "stock",
    "checkout",
]

_ARCHITECTURE_LAYERS = {
    "engine_registry": {
        "status": "implemented",
        "path": "src/picwise_taxonomy/engine_registry.py",
        "role": (
            "Top-level six PickWise search engines. "
            "Source of truth for engine IDs."
        ),
        "source_of_truth": True,
        "blueprint_only": False,
        "curated_seed_data": False,
        "workbench_foundation": False,
        "importer_scope": "not_applicable",
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "mega_category_registry": {
        "status": "implemented",
        "path": "src/picwise_taxonomy/mega_category_registry.py",
        "role": (
            "Eighteen mega-categories (three per engine). "
            "Source of truth for mega-category IDs."
        ),
        "source_of_truth": True,
        "blueprint_only": False,
        "curated_seed_data": False,
        "workbench_foundation": False,
        "importer_scope": "not_applicable",
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "coverage_plan": {
        "status": "implemented",
        "path": "src/picwise_taxonomy/coverage_plan.py",
        "role": (
            "Blueprint for future taxonomy coverage across all 18 mega-categories. "
            "Not deep-taxonomy completion."
        ),
        "source_of_truth": False,
        "blueprint_only": True,
        "curated_seed_data": False,
        "workbench_foundation": False,
        "importer_scope": "not_applicable",
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "deep_packs": {
        "status": "implemented",
        "path": "src/picwise_taxonomy/deep_packs/",
        "role": (
            "Curated seed taxonomy packs for selected engine and mega-category areas. "
            "Current packs include Tools/DIY/Garden/Repair and "
            "Fashion/Footwear/Jewelry/Accessories."
        ),
        "source_of_truth": False,
        "blueprint_only": False,
        "curated_seed_data": True,
        "workbench_foundation": False,
        "importer_scope": "not_applicable",
        "taxonomy_seed_only": True,
        "final_source_of_truth": False,
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "workbench": {
        "status": "implemented",
        "path": "src/picwise_taxonomy/workbench/",
        "role": (
            "Workbench foundation for canonical schema, source items, gap registry, "
            "coverage matrix, and validation."
        ),
        "source_of_truth": False,
        "blueprint_only": False,
        "curated_seed_data": False,
        "workbench_foundation": True,
        "importer_scope": "not_applicable",
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "importers": {
        "status": "implemented",
        "path": "src/picwise_taxonomy/importers/",
        "role": (
            "Convert external or local structured taxonomy paths to workbench "
            "source_item records."
        ),
        "source_of_truth": False,
        "blueprint_only": False,
        "curated_seed_data": False,
        "workbench_foundation": True,
        "importer_scope": "source_item_producer_only",
        "maps_directly_to_runtime": False,
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "mapping_layer": {
        "status": "implemented",
        "path": "src/picwise_taxonomy/mapping/",
        "role": (
            "Map imported source_items into PickWise engines, mega-categories, "
            "departments, subcategories, and product families."
        ),
        "source_of_truth": False,
        "blueprint_only": False,
        "curated_seed_data": False,
        "workbench_foundation": True,
        "importer_scope": "not_applicable",
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "future_canonical_registry": {
        "status": "planned",
        "path": "src/picwise_taxonomy/canonical/",
        "role": (
            "Future normalized PickWise taxonomy registry built from approved "
            "source items, mappings, gap registry, and curated deep-pack seeds."
        ),
        "source_of_truth": False,
        "blueprint_only": False,
        "curated_seed_data": False,
        "workbench_foundation": True,
        "importer_scope": "not_applicable",
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
    "future_nlu_export": {
        "status": "planned",
        "path": "src/picwise_taxonomy/exports/",
        "role": (
            "Future export layer for aliases, greeklish, typo terms, spec fields, "
            "priority terms, and intent patterns to Local NLU."
        ),
        "source_of_truth": False,
        "blueprint_only": False,
        "curated_seed_data": False,
        "workbench_foundation": True,
        "importer_scope": "not_applicable",
        "changes_local_nlu_runtime_directly": False,
        "product_inventory_forbidden": True,
        "commercial_fields_forbidden": True,
    },
}

_EXPECTED_LAYER_NAMES = [
    "engine_registry",
    "mega_category_registry",
    "coverage_plan",
    "deep_packs",
    "workbench",
    "importers",
    "mapping_layer",
    "future_canonical_registry",
    "future_nlu_export",
]

_MANIFEST = {
    "stage_id": "24B",
    "stage_name": "taxonomy_mapping_gap_system",
    "taxonomy_scope": "taxonomy_architecture_only",
    "pickwise_is_e_shop": False,
    "keeps_owned_product_inventory": False,
    "uses_taxonomy_for_search_understanding": True,
    "uses_taxonomy_for_external_offer_discovery_later": True,
    "runtime_integration_in_this_stage": False,
    "forbidden_commercial_terms": _FORBIDDEN_COMMERCIAL_TERMS,
    "forbidden_responsibilities": {
        "product_inventory": True,
        "sku_management": True,
        "offer_pricing_logic": True,
        "seller_store_logic": True,
        "affiliate_link_logic": True,
    },
    "non_goals": {
        "scraping": True,
        "downloading_external_data": True,
        "live_llm_calls": True,
        "runtime_router_integration": True,
        "local_nlu_runtime_changes": True,
    },
    "dependency_boundaries": {
        "app_router_decision_machine_dependency_required": False,
        "local_nlu_runtime_dependency_required": False,
        "network_or_external_api_calls_required": False,
        "llm_provider_dependency_required": False,
    },
    "layers": _ARCHITECTURE_LAYERS,
    "flow_overview": [
        "source_taxonomy_files",
        "importers",
        "workbench_source_items",
        "mapping_layer",
        "gap_registry",
        "canonical_taxonomy_registry",
        "coverage_matrix",
        "nlu_exports",
        "search_runtime_integration_later",
    ],
}


def get_taxonomy_architecture_manifest() -> dict:
    """Return deterministic architecture manifest for taxonomy boundaries."""
    return deepcopy(_MANIFEST)


def validate_taxonomy_architecture_manifest() -> dict:
    """Validate structure and strict non-commercial architecture boundaries."""
    manifest = get_taxonomy_architecture_manifest()
    layer_names = sorted(manifest["layers"].keys())
    expected_layer_names = sorted(_EXPECTED_LAYER_NAMES)
    implemented_layers = sorted(
        name for name, payload in manifest["layers"].items() if payload["status"] == "implemented"
    )
    planned_layers = sorted(
        name for name, payload in manifest["layers"].items() if payload["status"] == "planned"
    )

    result = {
        "valid": True,
        "passed": True,
        "is_json_serializable": True,
        "required_layers_present": layer_names == expected_layer_names,
        "implemented_layers": implemented_layers,
        "planned_layers": planned_layers,
        "has_implemented_and_planned_layers": bool(implemented_layers) and bool(planned_layers),
        "engine_registry_is_source_of_truth_for_engines": manifest["layers"]["engine_registry"][
            "source_of_truth"
        ],
        "mega_category_registry_is_source_of_truth_for_mega_categories": manifest["layers"][
            "mega_category_registry"
        ]["source_of_truth"],
        "deep_packs_are_curated_seeds_not_final_source": (
            manifest["layers"]["deep_packs"]["curated_seed_data"]
            and manifest["layers"]["deep_packs"]["taxonomy_seed_only"]
            and not manifest["layers"]["deep_packs"]["final_source_of_truth"]
        ),
        "importers_are_source_item_producers_only": manifest["layers"]["importers"][
            "importer_scope"
        ]
        == "source_item_producer_only",
        "importers_not_runtime_mapping": not manifest["layers"]["importers"]["maps_directly_to_runtime"],
        "future_layers_are_planned_not_implemented": all(
            manifest["layers"][name]["status"] == "planned"
            for name in ("future_canonical_registry", "future_nlu_export")
        )
        and manifest["layers"]["mapping_layer"]["status"] == "implemented",
        "product_inventory_responsibility_forbidden": manifest["forbidden_responsibilities"][
            "product_inventory"
        ],
        "offer_price_affiliate_responsibility_forbidden": (
            manifest["forbidden_responsibilities"]["offer_pricing_logic"]
            and manifest["forbidden_responsibilities"]["affiliate_link_logic"]
        ),
        "forbidden_commercial_terms_declared": all(
            term in manifest["forbidden_commercial_terms"] for term in _FORBIDDEN_COMMERCIAL_TERMS
        ),
        "no_app_router_or_decision_machine_dependency_required": not manifest[
            "dependency_boundaries"
        ]["app_router_decision_machine_dependency_required"],
        "no_local_nlu_runtime_dependency_required": not manifest["dependency_boundaries"][
            "local_nlu_runtime_dependency_required"
        ],
        "no_network_or_external_api_calls_required": not manifest["dependency_boundaries"][
            "network_or_external_api_calls_required"
        ],
        "no_llm_provider_dependency_required": not manifest["dependency_boundaries"][
            "llm_provider_dependency_required"
        ],
        "no_scraping_or_external_downloads_or_live_llm": (
            manifest["non_goals"]["scraping"]
            and manifest["non_goals"]["downloading_external_data"]
            and manifest["non_goals"]["live_llm_calls"]
        ),
        "flow_overview_present": bool(manifest["flow_overview"]),
    }

    try:
        json.dumps(manifest, sort_keys=True)
    except (TypeError, ValueError):
        result["is_json_serializable"] = False

    result["valid"] = (
        result["is_json_serializable"]
        and result["required_layers_present"]
        and result["has_implemented_and_planned_layers"]
        and result["engine_registry_is_source_of_truth_for_engines"]
        and result["mega_category_registry_is_source_of_truth_for_mega_categories"]
        and result["deep_packs_are_curated_seeds_not_final_source"]
        and result["importers_are_source_item_producers_only"]
        and result["importers_not_runtime_mapping"]
        and result["future_layers_are_planned_not_implemented"]
        and result["product_inventory_responsibility_forbidden"]
        and result["offer_price_affiliate_responsibility_forbidden"]
        and result["forbidden_commercial_terms_declared"]
        and result["no_app_router_or_decision_machine_dependency_required"]
        and result["no_local_nlu_runtime_dependency_required"]
        and result["no_network_or_external_api_calls_required"]
        and result["no_llm_provider_dependency_required"]
        and result["no_scraping_or_external_downloads_or_live_llm"]
        and result["flow_overview_present"]
    )
    result["passed"] = result["valid"]
    return result
