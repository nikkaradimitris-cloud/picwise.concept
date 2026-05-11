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

_STAGE_TITLE = "Stage 26D — Health / Beauty / Family / Lifestyle Deep Pack"
_STAGE_CODE = "stage_26d"
_ENGINE_ID = "health_beauty_family_lifestyle_engine"
_SCHEMA_VERSION = "1.0.0"
_SOURCE = "phase_c_stage_26d_health_beauty_family_lifestyle"
_EXPECTED_MEGA_CATEGORIES = [
    "health_wellness_safety_devices",
    "beauty_grooming_personal_care",
    "baby_kids_pets_sports_outdoor",
]
_MINIMUM_TOTALS = {
    "departments": 3,
    "subcategories": 9,
    "product_families": 30,
    "aliases": 40,
    "spec_fields": 15,
    "intent_patterns": 15,
}


def _health_wellness_record() -> dict:
    departments = [
        "health devices and monitoring",
        "wellness and recovery support",
        "safety devices for household",
        "family daily prevention routines",
    ]
    subcategories = [
        "health devices",
        "πιεσόμετρα",
        "thermometers",
        "pulse oximeters",
        "smart wellness trackers",
        "safety detectors",
        "fall alert devices",
        "sleep monitoring support",
        "air quality wellness monitors",
        "mobility support devices",
        "home first-aid organization",
        "wellness routine accessories",
    ]
    product_families = expand_product_families(
        base=[
            "blood pressure monitor family lines",
            "thermometer family lines",
            "oximeter family lines",
            "wellness tracker family lines",
            "safety detector family lines",
            "fall alert family lines",
            "sleep monitor family lines",
            "air monitor family lines",
            "mobility support family lines",
            "home care organizer family lines",
        ],
        variants=["daily", "family", "connected", "easy-read"],
        contexts=["taxonomy families", "care sets", "routine sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "health devices",
            "συσκευές υγείας",
            "wellness monitors",
            "safety devices",
            "family prevention tools",
            "home health support",
            "sleep wellness devices",
            "household safety monitoring",
            "preventive wellness taxonomy",
            "daily health routine support",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "piesometro",
            "thermometro",
            "oximetro",
            "tracker ygeias",
            "anixneftis asfaleias",
            "fall alert",
            "sleep monitor",
            "air quality monitor",
            "boithima kinisis",
            "first aid organizer",
        ],
        contexts=["gia spiti", "gia oikogeneia", "daily routine"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "measurement_scope",
        "accuracy_class",
        "readability_profile",
        "battery_life_hours",
        "sync_support",
        "alert_threshold_support",
        "calibration_profile",
        "display_type",
        "use_context_profile",
        "certification_markings",
        "portability_level",
        "caregiver_support_mode",
        "safety_alert_type",
        "environment_compatibility",
        "maintenance_requirements",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo health devices gia daily check",
            "psaxno safety devices gia spiti",
            "thelo wellness trackers me eukoli xrhsh",
            "psaxno sleep monitor gia routine",
            "thelo family health support setup",
        ],
        targets=subcategories,
        situations=[
            "daily monitoring",
            "family readability needs",
            "preventive wellness",
            "home safety alerts",
            "low-maintenance routine",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="health_wellness_safety_devices",
        display_name="Health / Wellness / Safety Devices",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "measurement_reliability",
            "ease_of_use",
            "readability",
            "maintenance_simplicity",
            "safety_alert_clarity",
            "daily_routine_fit",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate wellness support queries from clinical diagnosis intent",
            "route safety detector intent apart from smart-home automation-only requests",
            "disambiguate activity trackers from medical measurement devices",
        ],
        source_references=[
            "engine_registry:health_beauty_family_lifestyle_engine",
            "mega_category_registry:health_wellness_safety_devices",
            "coverage_plan:health_wellness_safety_devices",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _beauty_grooming_record() -> dict:
    departments = [
        "beauty routines and skincare",
        "grooming devices and tools",
        "hair care and styling",
        "daily personal care essentials",
    ]
    subcategories = [
        "beauty",
        "grooming",
        "skincare cleansers",
        "serums and treatments",
        "hair care shampoos",
        "hair styling devices",
        "electric shavers and trimmers",
        "oral care devices",
        "body care essentials",
        "sensitive skin routines",
        "travel grooming kits",
        "daily hygiene support",
    ]
    product_families = expand_product_families(
        base=[
            "skincare family lines",
            "treatment serum family lines",
            "haircare family lines",
            "hair styling family lines",
            "trimmer family lines",
            "shaver family lines",
            "oral care family lines",
            "body care family lines",
            "sensitive skin family lines",
            "travel grooming family lines",
        ],
        variants=["daily", "gentle", "sensitive", "routine-focused"],
        contexts=["taxonomy families", "care sets", "daily sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "beauty",
            "grooming",
            "προσωπική φροντίδα",
            "skincare",
            "hair care",
            "daily self care",
            "grooming tools",
            "sensitive skin support",
            "beauty routine taxonomy",
            "personal care essentials",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "beauty routine",
            "grooming set",
            "katharistiko prosopou",
            "serum",
            "shampoo",
            "styling syskevi",
            "xyristiki mixani",
            "trimmer",
            "ilektriki vourtsa dention",
            "body care",
        ],
        contexts=["daily xrhsh", "sensitive skin", "travel kit"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "skin_type_profile",
        "hair_type_profile",
        "active_ingredient_profile",
        "dermatology_tested",
        "runtime_minutes",
        "blade_or_head_type",
        "water_resistance_level",
        "sensitivity_mode_support",
        "routine_frequency_profile",
        "travel_size_compliance",
        "cleaning_profile",
        "material_safety_profile",
        "compatibility_with_sensitive_use",
        "daily_usage_intensity",
        "maintenance_requirements",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo beauty routine gia daily use",
            "psaxno grooming device gia sensitive skin",
            "thelo hair care kai styling setup",
            "psaxno travel grooming kit",
            "thelo personal care me low maintenance",
        ],
        targets=subcategories,
        situations=[
            "daily routine consistency",
            "sensitive use profile",
            "travel-friendly setup",
            "quick morning workflow",
            "low-effort care maintenance",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="beauty_grooming_personal_care",
        display_name="Beauty / Grooming / Personal Care",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "routine_compatibility",
            "gentle_daily_use",
            "hygiene_and_cleanability",
            "portability",
            "durability",
            "long_term_care_consistency",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate grooming device intent from health-monitoring device intent",
            "route skincare terms by skin-type context when present",
            "disambiguate styling device intent from grooming trimmer intent",
        ],
        source_references=[
            "engine_registry:health_beauty_family_lifestyle_engine",
            "mega_category_registry:beauty_grooming_personal_care",
            "coverage_plan:beauty_grooming_personal_care",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _family_lifestyle_record() -> dict:
    departments = [
        "baby and kids care essentials",
        "pets daily care and support",
        "sports and outdoor lifestyle",
        "family mobility and wellness routines",
    ]
    subcategories = [
        "baby/kids",
        "pets",
        "sports",
        "outdoor",
        "baby transport essentials",
        "kids school routine tools",
        "pet feeding systems",
        "pet grooming support",
        "home sports training kits",
        "outdoor activity gear",
        "family weekend activity sets",
        "safety accessories for active family life",
    ]
    product_families = expand_product_families(
        base=[
            "baby essentials family lines",
            "kids routine family lines",
            "pet feeding family lines",
            "pet care family lines",
            "sports training family lines",
            "outdoor activity family lines",
            "family activity family lines",
            "mobility support family lines",
            "safety accessory family lines",
            "weekend lifestyle family lines",
        ],
        variants=["daily", "family", "active", "outdoor-ready"],
        contexts=["taxonomy families", "routine sets", "activity sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "baby/kids essentials",
            "pets care",
            "sports and outdoor",
            "οικογενειακά είδη δραστηριοτήτων",
            "family lifestyle",
            "active family gear",
            "kids and pets routines",
            "outdoor family support",
            "sports wellness taxonomy",
            "family care and activity setup",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "baby kids",
            "pet care",
            "sports set",
            "outdoor gear",
            "karotsi moro",
            "kids school routine",
            "taistra katoikidiou",
            "pet grooming set",
            "home training kit",
            "family weekend outdoor",
        ],
        contexts=["gia oikogeneia", "daily routine", "active lifestyle"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "age_or_size_range",
        "safety_certification_scope",
        "material_safety_profile",
        "load_capacity_kg",
        "portability_weight",
        "weather_readiness_profile",
        "activity_intensity_fit",
        "care_cleaning_requirements",
        "storage_footprint",
        "routine_support_profile",
        "pet_size_compatibility",
        "family_use_context",
        "outdoor_surface_profile",
        "comfort_duration_profile",
        "maintenance_requirements",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo baby/kids essentials gia kathimerini routine",
            "psaxno pets care setup gia spiti",
            "thelo sports kai outdoor set gia oikogeneia",
            "psaxno family activity gear gia savvatokyriako",
            "thelo active lifestyle support me safety focus",
        ],
        targets=subcategories,
        situations=[
            "daily family routine",
            "weekend outdoor activities",
            "home sports training",
            "pet-friendly household flow",
            "active and safe lifestyle",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="baby_kids_pets_sports_outdoor",
        display_name="Baby / Kids / Pets / Sports / Outdoor",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "family_safety",
            "daily_comfort",
            "durability_for_active_use",
            "easy_cleaning",
            "portability",
            "multi_use_flexibility",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate pets-care queries from baby-care requests when care terms overlap",
            "route sports equipment intent apart from outdoor leisure-only accessories",
            "disambiguate family safety accessories from medical safety device intents",
        ],
        source_references=[
            "engine_registry:health_beauty_family_lifestyle_engine",
            "mega_category_registry:baby_kids_pets_sports_outdoor",
            "coverage_plan:baby_kids_pets_sports_outdoor",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


_HEALTH_BEAUTY_FAMILY_LIFESTYLE_PACK = {
    "stage_title": _STAGE_TITLE,
    "engine_id": _ENGINE_ID,
    "schema_version": _SCHEMA_VERSION,
    "source": _SOURCE,
    "mega_categories": [
        _health_wellness_record(),
        _beauty_grooming_record(),
        _family_lifestyle_record(),
    ],
}


def get_health_beauty_family_lifestyle_pack() -> dict:
    return deep_copy_pack(_HEALTH_BEAUTY_FAMILY_LIFESTYLE_PACK)


def get_health_beauty_family_lifestyle_mega_category_pack(mega_category_id: str) -> dict | None:
    for record in _HEALTH_BEAUTY_FAMILY_LIFESTYLE_PACK["mega_categories"]:
        if record["mega_category_id"] == mega_category_id:
            return deep_copy_pack(record)
    return None


def summarize_health_beauty_family_lifestyle_pack() -> dict:
    summary = summarize_pack(get_health_beauty_family_lifestyle_pack())
    validation = validate_health_beauty_family_lifestyle_pack()
    summary["validation_summary"] = {
        "valid": validation["valid"],
        "stage_title_exact": validation["stage_title_exact"],
        "engine_id_exact": validation["engine_id_exact"],
        "all_mega_categories_mapped_to_engine": validation["all_mega_categories_mapped_to_engine"],
    }
    return summary


def validate_health_beauty_family_lifestyle_pack() -> dict:
    return validate_pack(
        pack=get_health_beauty_family_lifestyle_pack(),
        expected_stage_title=_STAGE_TITLE,
        expected_engine_id=_ENGINE_ID,
        expected_mega_category_ids=_EXPECTED_MEGA_CATEGORIES,
        minimum_totals=_MINIMUM_TOTALS,
    )
