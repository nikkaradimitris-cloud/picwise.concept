from __future__ import annotations

from .stage26_common import (
    deep_copy_pack,
    expand_aliases,
    expand_greeklish,
    expand_intents,
    expand_product_families,
    make_record,
    summarize_pack,
    typo_variants,
    validate_pack,
)

_STAGE_TITLE = "Stage 26B — Home / Living / Appliances Deep Pack"
_STAGE_CODE = "stage_26b"
_ENGINE_ID = "home_living_appliances_engine"
_SCHEMA_VERSION = "1.0.0"
_SOURCE = "phase_c_stage_26b_home_living_appliances"
_EXPECTED_MEGA_CATEGORIES = [
    "home_appliances_laundry_climate",
    "kitchen_cooking_household",
    "furniture_living_storage_smart_home",
]
_MINIMUM_TOTALS = {
    "departments": 3,
    "subcategories": 9,
    "product_families": 30,
    "aliases": 40,
    "spec_fields": 15,
    "intent_patterns": 15,
}


def _home_appliances_record() -> dict:
    departments = [
        "πλυντήρια και στεγνωτήρια",
        "ψυγεία και ψύξη",
        "κλιματιστικά και αφυγραντήρες",
        "household floor care appliances",
    ]
    subcategories = [
        "πλυντήρια ρούχων",
        "στεγνωτήρια",
        "πλυντήρια πιάτων",
        "ψυγεία",
        "ψυγειοκαταψύκτες",
        "κλιματιστικά inverter",
        "αφυγραντήρες",
        "σκούπες",
        "robot vacuum cleaners",
        "air purifying climate combos",
        "steam floor care",
        "laundry combo units",
    ]
    product_families = expand_product_families(
        base=[
            "laundry appliance family lines",
            "dishwasher family lines",
            "refrigeration family lines",
            "climate control family lines",
            "dehumidifier family lines",
            "vacuum family lines",
            "robot vacuum family lines",
            "steam cleaner family lines",
            "air treatment family lines",
            "integrated appliance family lines",
        ],
        variants=["compact", "family-size", "quiet", "energy-focused"],
        contexts=["taxonomy families", "home setup sets", "lifecycle sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "λευκές συσκευές",
            "πλυντήρια και ψυγεία",
            "home appliances",
            "laundry systems",
            "climate appliances",
            "floor care appliances",
            "οικιακές συσκευές ψύξης",
            "energy efficient home appliances",
            "household cleaning appliance taxonomy",
            "major appliance decision set",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "plintirio rouxon",
            "stegnotirio",
            "plintirio piaton",
            "psigeio",
            "psigiokatapsiktis",
            "klimatistiko inverter",
            "afygrantiras",
            "skoupa",
            "robot skoupa",
            "air treatment spiti",
        ],
        contexts=["gia spiti", "gia oikogeneia", "xamili katanalosi"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "capacity_liters",
        "load_capacity_kg",
        "energy_class",
        "annual_kwh_consumption",
        "noise_level_db",
        "program_count",
        "spin_speed_rpm",
        "cooling_volume_liters",
        "heating_cooling_btu",
        "coverage_area_m2",
        "dehumidification_rate_l_day",
        "dust_collection_type",
        "smart_connectivity_support",
        "dimensions_mm",
        "installation_type",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo πλυντήρια ρούχων gia kathimerini xrhsh",
            "psaxno ψυγεία me xamili katanalosi",
            "thelo κλιματιστικά kai αφυγραντήρες gia ygrasia",
            "psaxno σκούπες gia pet hair cleanup",
            "thelo πλυντήρια πιάτων me hsyxhi leitourgia",
        ],
        targets=subcategories,
        situations=[
            "small apartment setup",
            "family home workload",
            "energy efficiency focus",
            "quiet night usage",
            "seasonal climate control",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="home_appliances_laundry_climate",
        display_name="Home Appliances / Laundry / Climate",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "energy_efficiency",
            "household_size_fit",
            "noise_sensitivity",
            "maintenance_simplicity",
            "installation_constraints",
            "long_term_reliability",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate dehumidifier intent from air conditioner intent using humidity cues",
            "route robot vacuum queries apart from upright vacuum workflows",
            "disambiguate washer-dryer combo from dedicated washer or dryer intent",
        ],
        source_references=[
            "engine_registry:home_living_appliances_engine",
            "mega_category_registry:home_appliances_laundry_climate",
            "coverage_plan:home_appliances_laundry_climate",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _kitchen_household_record() -> dict:
    departments = [
        "κουζίνες και φούρνοι",
        "small kitchen prep appliances",
        "coffee and beverage systems",
        "household food prep and cleaning helpers",
    ]
    subcategories = [
        "κουζίνες",
        "φούρνοι",
        "air fryer",
        "μίξερ",
        "μίνι πίμερ",
        "καφετιέρες",
        "multi-cook countertop devices",
        "kitchen prep blenders",
        "food processor systems",
        "household dish prep tools",
        "toaster and kettle devices",
        "compact kitchen essentials",
    ]
    product_families = expand_product_families(
        base=[
            "oven family lines",
            "cooker family lines",
            "air fryer family lines",
            "mixer family lines",
            "mini blender family lines",
            "coffee machine family lines",
            "food processor family lines",
            "kettle family lines",
            "toaster family lines",
            "countertop multi-cook family lines",
        ],
        variants=["compact", "family", "fast-prep", "easy-clean"],
        contexts=["taxonomy families", "meal prep sets", "countertop sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "κουζίνα συσκευές",
            "φούρνοι κουζίνας",
            "air fryer συσκευές",
            "kitchen appliances",
            "μικροσυσκευές κουζίνας",
            "καφετιέρα για σπίτι",
            "μίξερ ζύμης",
            "food prep appliances",
            "home kitchen setup taxonomy",
            "countertop cooking ecosystem",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "kouzina syskeves",
            "fournos",
            "air fryer",
            "mixer zymis",
            "mini pimer",
            "kafetiera",
            "food processor",
            "blender kouzinas",
            "toaster",
            "kettle",
        ],
        contexts=["gia spiti", "taxeia proetoimasia", "easy clean"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "power_watts",
        "capacity_liters",
        "temperature_range_celsius",
        "preset_program_count",
        "bowl_capacity_liters",
        "blade_material_type",
        "pressure_cooking_support",
        "steam_support",
        "coffee_brew_type",
        "grinder_support",
        "countertop_footprint_mm",
        "dishwasher_safe_parts",
        "material_grade",
        "food_contact_certification",
        "cleaning_complexity_level",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo air fryer gia grigoro mageirema",
            "psaxno καφετιέρες me xamili syntirisi",
            "thelo μίξερ gia zymes kai glyka",
            "psaxno μίνι πίμερ gia soupes",
            "thelo φούρνοι kai κουζίνες me family capacity",
        ],
        targets=subcategories,
        situations=[
            "daily meal prep",
            "small kitchen space",
            "family cooking routine",
            "easy clean workflow",
            "coffee-at-home routine",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="kitchen_cooking_household",
        display_name="Kitchen / Cooking / Household",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "workflow_speed",
            "counter_space_fit",
            "cleaning_ease",
            "multi_use_versatility",
            "food_safety_support",
            "durability_in_daily_use",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate mixer kitchen intent from audio equipment mixer intent",
            "route oven and cooker intents by installation vs countertop cues",
            "disambiguate mini blender from full-size blender by capacity context",
        ],
        source_references=[
            "engine_registry:home_living_appliances_engine",
            "mega_category_registry:kitchen_cooking_household",
            "coverage_plan:kitchen_cooking_household",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _living_storage_smart_record() -> dict:
    departments = [
        "έπιπλα και living setup",
        "φωτισμός εσωτερικού χώρου",
        "smart home systems",
        "storage and space organization",
    ]
    subcategories = [
        "έπιπλα σαλονιού",
        "έπιπλα υπνοδωματίου",
        "storage organizers",
        "modular shelving systems",
        "lighting fixtures",
        "smart lighting controls",
        "smart home hubs",
        "smart sensors",
        "home automation starters",
        "room space-saving furniture",
        "wardrobe organization systems",
        "desk and office living furniture",
    ]
    product_families = expand_product_families(
        base=[
            "living room furniture family lines",
            "bedroom furniture family lines",
            "storage organizer family lines",
            "modular shelf family lines",
            "lighting fixture family lines",
            "smart lighting family lines",
            "home hub family lines",
            "sensor family lines",
            "automation starter family lines",
            "space-saving furniture family lines",
        ],
        variants=["compact", "family", "connected", "modular"],
        contexts=["taxonomy families", "room sets", "organization sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "έπιπλα σπιτιού",
            "home furniture",
            "φωτισμός",
            "smart home",
            "storage λύσεις",
            "room organization",
            "living setup taxonomy",
            "connected home controls",
            "space saving furniture",
            "smart living accessories",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "epipla saloniou",
            "epipla ypnodwmatiou",
            "fwtismos spiti",
            "smart home",
            "smart hub",
            "smart sensor",
            "storage organizer",
            "modular rafia",
            "home automation",
            "xwros exoikonomisi",
        ],
        contexts=["gia spiti", "small apartment", "connected setup"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "room_compatibility",
        "dimensions_mm",
        "load_capacity_kg",
        "material_finish",
        "assembly_complexity_level",
        "lighting_lumen_output",
        "color_temperature_k",
        "wireless_protocol_support",
        "voice_assistant_support",
        "sensor_type_profile",
        "automation_scene_support",
        "storage_volume_liters",
        "mounting_profile",
        "expandability_level",
        "ecosystem_compatibility",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo έπιπλα gia small apartment",
            "psaxno φωτισμός me smart controls",
            "thelo smart home hub kai sensors",
            "psaxno storage lyseis gia mikrous xorous",
            "thelo room setup me furniture kai automation",
        ],
        targets=subcategories,
        situations=[
            "small space optimization",
            "family living room upgrade",
            "home office setup",
            "connected smart routines",
            "declutter and storage planning",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="furniture_living_storage_smart_home",
        display_name="Furniture / Living / Storage / Smart Home",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "space_optimization",
            "comfort_and_ergonomics",
            "storage_efficiency",
            "ecosystem_interoperability",
            "expandability_over_time",
            "maintenance_simplicity",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate smart sensor intent from camera/security-only intent",
            "route furniture queries by room context first",
            "disambiguate lighting décor intent from smart control automation intent",
        ],
        source_references=[
            "engine_registry:home_living_appliances_engine",
            "mega_category_registry:furniture_living_storage_smart_home",
            "coverage_plan:furniture_living_storage_smart_home",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


_HOME_LIVING_APPLIANCES_PACK = {
    "stage_title": _STAGE_TITLE,
    "engine_id": _ENGINE_ID,
    "schema_version": _SCHEMA_VERSION,
    "source": _SOURCE,
    "mega_categories": [
        _home_appliances_record(),
        _kitchen_household_record(),
        _living_storage_smart_record(),
    ],
}


def get_home_living_appliances_pack() -> dict:
    return deep_copy_pack(_HOME_LIVING_APPLIANCES_PACK)


def get_home_living_appliances_mega_category_pack(mega_category_id: str) -> dict | None:
    for record in _HOME_LIVING_APPLIANCES_PACK["mega_categories"]:
        if record["mega_category_id"] == mega_category_id:
            return deep_copy_pack(record)
    return None


def summarize_home_living_appliances_pack() -> dict:
    summary = summarize_pack(get_home_living_appliances_pack())
    validation = validate_home_living_appliances_pack()
    summary["validation_summary"] = {
        "valid": validation["valid"],
        "stage_title_exact": validation["stage_title_exact"],
        "engine_id_exact": validation["engine_id_exact"],
        "all_mega_categories_mapped_to_engine": validation["all_mega_categories_mapped_to_engine"],
    }
    return summary


def validate_home_living_appliances_pack() -> dict:
    return validate_pack(
        pack=get_home_living_appliances_pack(),
        expected_stage_title=_STAGE_TITLE,
        expected_engine_id=_ENGINE_ID,
        expected_mega_category_ids=_EXPECTED_MEGA_CATEGORIES,
        minimum_totals=_MINIMUM_TOTALS,
    )
