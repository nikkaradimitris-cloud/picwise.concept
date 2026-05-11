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

_STAGE_TITLE = "Stage 26A — Auto / Moto / Mobility Deep Pack"
_STAGE_CODE = "stage_26a"
_ENGINE_ID = "auto_moto_mobility_engine"
_SCHEMA_VERSION = "1.0.0"
_SOURCE = "phase_c_stage_26a_auto_moto_mobility"
_EXPECTED_MEGA_CATEGORIES = [
    "car_parts_service_maintenance",
    "tyres_wheels_car_accessories",
    "moto_bicycle_mobility_gear",
]
_MINIMUM_TOTALS = {
    "departments": 3,
    "subcategories": 9,
    "product_families": 30,
    "aliases": 40,
    "spec_fields": 15,
    "intent_patterns": 15,
}


def _car_parts_record() -> dict:
    departments = [
        "συντήρηση αυτοκινήτου",
        "service consumables and lubricants",
        "engine filters and service kits",
        "car batteries and electrical support",
    ]
    subcategories = [
        "λάδια κινητήρα",
        "φίλτρα λαδιού",
        "φίλτρα αέρα κινητήρα",
        "φίλτρα καμπίνας",
        "μπαταρίες αυτοκινήτου",
        "service kits by mileage",
        "ανταλλακτικά πέδησης",
        "ανταλλακτικά ανάρτησης",
        "diagnostic maintenance tools",
        "wiper and visibility maintenance",
        "coolant and antifreeze fluids",
        "timing service components",
    ]
    product_families = expand_product_families(
        base=[
            "car maintenance fluid families",
            "vehicle oil filter family lines",
            "vehicle air filter family lines",
            "cab filter family lines",
            "agm battery family lines",
            "efb battery family lines",
            "brake pad family lines",
            "suspension service family lines",
            "coolant family lines",
            "timing maintenance family lines",
        ],
        variants=["daily-use", "city-drive", "long-trip", "premium"],
        contexts=["taxonomy families", "compatibility sets", "maintenance sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "αυτοκίνητο service",
            "ανταλλακτικά αυτοκινήτου",
            "car maintenance",
            "vehicle service parts",
            "λάδια αυτοκινήτου",
            "φίλτρα αυτοκινήτου",
            "μπαταρία αυτοκινήτου",
            "auto service essentials",
            "garage maintenance taxonomy",
            "spare parts for car upkeep",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "autokinito service",
            "ladia kinitira",
            "filtra ladiou",
            "filtra aera",
            "filtra kabinas",
            "mpataria autokinitou",
            "antallaktika frenon",
            "antallaktika anartisis",
            "service kit km",
            "diagnostiko maintenance",
        ],
        contexts=["gia autokinito", "gia service", "proliptiki syntirisi"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "vehicle_fitment_scope",
        "engine_code_compatibility",
        "oil_viscosity_grade",
        "service_interval_km",
        "battery_capacity_ah",
        "cold_cranking_amps",
        "filter_media_type",
        "certification_standard",
        "temperature_range_c",
        "installation_complexity_level",
        "brake_material_class",
        "coolant_specification",
        "wiper_length_mm",
        "warranty_scope",
        "maintenance_profile",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo λαδια κινητήρα gia routine service",
            "psaxno φίλτρα λαδιού me fitment asfaleia",
            "thelo μπαταρίες αυτοκινήτου gia xeimoniaki xrhsh",
            "psaxno ανταλλακτικά gia service kilometron",
            "thelo φίλτρα και λάδια se ena service set",
        ],
        targets=subcategories,
        situations=[
            "proliptiki syntirisi",
            "taxidi megalis apostasis",
            "daily commute",
            "xeimones synthikes",
            "epanakinisi service plan",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="car_parts_service_maintenance",
        display_name="Car Parts / Service / Maintenance",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "fitment_accuracy",
            "service_interval_alignment",
            "durability_in_daily_use",
            "compatibility_confidence",
            "safety_critical_priority",
            "maintenance_cost_over_time",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "differentiate vehicle battery from electronics battery intent",
            "separate generic service request from parts-specific request",
            "route oil terms by viscosity and engine type context",
        ],
        source_references=[
            "engine_registry:auto_moto_mobility_engine",
            "mega_category_registry:car_parts_service_maintenance",
            "coverage_plan:car_parts_service_maintenance",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _tyres_accessories_record() -> dict:
    departments = [
        "λάστιχα και ζάντες",
        "car accessory safety and utility",
        "dash cams and driving visibility gear",
        "child seat and family ride support",
    ]
    subcategories = [
        "λάστιχα καλοκαιρινά",
        "λάστιχα χειμερινά",
        "λάστιχα all season",
        "ζάντες αλουμινίου",
        "tpms and tyre monitoring",
        "dash cams",
        "car interior organizers",
        "παιδικά καθίσματα",
        "booster child seats",
        "wheel care and balancing accessories",
        "traction chains",
        "car mount and holder accessories",
    ]
    product_families = expand_product_families(
        base=[
            "touring tyre family lines",
            "winter tyre family lines",
            "all-season tyre family lines",
            "alloy wheel family lines",
            "tpms family lines",
            "dash cam family lines",
            "child seat family lines",
            "booster seat family lines",
            "interior organizer family lines",
            "traction chain family lines",
        ],
        variants=["city", "touring", "comfort", "premium"],
        contexts=["taxonomy families", "compatibility sets", "safety sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "λάστιχα αυτοκινήτου",
            "ζάντες αυτοκινήτου",
            "car tyres and wheels",
            "car accessories",
            "dash cam για αυτοκίνητο",
            "παιδικό κάθισμα αυτοκινήτου",
            "driving visibility accessories",
            "family car ride safety",
            "wheel and tyre setup",
            "mobility car accessory taxonomy",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "lastixa autokinitou",
            "zantes alouminiou",
            "all season lastixa",
            "xeimoniatika lastixa",
            "tpms systima",
            "dash cam autokinitou",
            "paidiko kathisma autokinitou",
            "booster kathisma",
            "organosi esoterikou autokinitou",
            "alysides xionioy",
        ],
        contexts=["gia asfaleia", "gia taxidi", "gia kathimerini xrhsh"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "tyre_size_code",
        "load_index",
        "speed_rating",
        "seasonal_class",
        "wheel_diameter_inch",
        "rim_width",
        "offset_et",
        "tpms_support",
        "camera_resolution_profile",
        "night_vision_support",
        "child_seat_group",
        "isofix_support",
        "max_child_weight_kg",
        "mounting_profile",
        "vehicle_segment_compatibility",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo λάστιχα για xeimoniaki asfaleia",
            "psaxno dash cams me kalo night view",
            "thelo παιδικά καθίσματα me isofix",
            "psaxno zantes kai lastixa me fitment akriveia",
            "thelo family car accessory setup gia taxidia",
        ],
        targets=subcategories,
        situations=[
            "xeimoniaki odigisi",
            "daily city commute",
            "family rides",
            "long-distance travel",
            "safety-first setup",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="tyres_wheels_car_accessories",
        display_name="Tyres / Wheels / Car Accessories",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "road_grip_and_safety",
            "fitment_precision",
            "weather_suitability",
            "family_travel_readiness",
            "installation_clarity",
            "durability_and_wear_profile",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate tyre size lookup from wheel style-only query",
            "disambiguate dash cam from action camera intent",
            "route child seat requests by age/weight group first",
        ],
        source_references=[
            "engine_registry:auto_moto_mobility_engine",
            "mega_category_registry:tyres_wheels_car_accessories",
            "coverage_plan:tyres_wheels_car_accessories",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _moto_bike_mobility_record() -> dict:
    departments = [
        "μηχανή και moto commuting",
        "ποδήλατα και e-bikes",
        "πατίνια και ηλεκτρικά πατίνια",
        "mobility gear and rider safety",
    ]
    subcategories = [
        "μηχανή ανταλλακτικά βασικής συντήρησης",
        "moto helmets and protection",
        "ποδήλατα πόλης",
        "mountain bikes",
        "e-bikes",
        "πατίνια",
        "ηλεκτρικά πατίνια",
        "mobility safety lights",
        "mobility locks and anti-theft",
        "bike child transport accessories",
        "rider bags and cargo carriers",
        "moto commuting gloves and jackets",
    ]
    product_families = expand_product_families(
        base=[
            "urban moto family lines",
            "moto safety helmet family lines",
            "city bike family lines",
            "mtb family lines",
            "e-bike family lines",
            "scooter family lines",
            "electric scooter family lines",
            "mobility light family lines",
            "mobility lock family lines",
            "rider cargo family lines",
        ],
        variants=["urban", "commuter", "daily", "long-range"],
        contexts=["taxonomy families", "usage sets", "safety sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "μηχανή accessories",
            "moto gear",
            "ποδήλατα",
            "e-bike",
            "πατίνι",
            "ηλεκτρικό πατίνι",
            "mobility gear",
            "rider commuting setup",
            "urban mobility taxonomy",
            "bike and scooter safety equipment",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "mixani antallaktika",
            "kranos moto",
            "podilato polis",
            "mountain bike",
            "e bike",
            "patini",
            "ilektriko patini",
            "fota asfaleias mobility",
            "kleidaria podilatou",
            "tsanta rider cargo",
        ],
        contexts=["gia commute", "gia asfaleia", "gia kathimerini metakinisi"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "vehicle_type_compatibility",
        "helmet_certification",
        "frame_size_range",
        "wheel_size_inch",
        "motor_power_watts",
        "battery_capacity_wh",
        "range_km_estimate",
        "max_supported_weight_kg",
        "brake_system_type",
        "folding_support",
        "lighting_visibility_profile",
        "water_resistance_level",
        "lock_security_class",
        "cargo_load_capacity_kg",
        "commute_profile",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo e-bikes gia daily commute",
            "psaxno ηλεκτρικά πατίνια me asfaleia",
            "thelo ποδήλατα πόλης me anthiktiko setup",
            "psaxno moto gear gia kentriki metakinisi",
            "thelo mobility locks kai lights se ena set",
        ],
        targets=subcategories,
        situations=[
            "urban commute",
            "daily city routes",
            "mixed weather usage",
            "family transport support",
            "anti-theft protection",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="moto_bicycle_mobility_gear",
        display_name="Moto / Bicycle / Mobility Gear",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "rider_safety_priority",
            "commute_reliability",
            "range_and_charge_needs",
            "portability_and_storage",
            "weather_readiness",
            "anti_theft_confidence",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate kick scooter from electric scooter intent",
            "disambiguate e-bike from e-scooter based on frame and ride cues",
            "route moto safety terms independently from bicycle-only equipment",
        ],
        source_references=[
            "engine_registry:auto_moto_mobility_engine",
            "mega_category_registry:moto_bicycle_mobility_gear",
            "coverage_plan:moto_bicycle_mobility_gear",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


_AUTO_MOTO_MOBILITY_PACK = {
    "stage_title": _STAGE_TITLE,
    "engine_id": _ENGINE_ID,
    "schema_version": _SCHEMA_VERSION,
    "source": _SOURCE,
    "mega_categories": [
        _car_parts_record(),
        _tyres_accessories_record(),
        _moto_bike_mobility_record(),
    ],
}


def get_auto_moto_mobility_pack() -> dict:
    return deep_copy_pack(_AUTO_MOTO_MOBILITY_PACK)


def get_auto_moto_mobility_mega_category_pack(mega_category_id: str) -> dict | None:
    for record in _AUTO_MOTO_MOBILITY_PACK["mega_categories"]:
        if record["mega_category_id"] == mega_category_id:
            return deep_copy_pack(record)
    return None


def summarize_auto_moto_mobility_pack() -> dict:
    summary = summarize_pack(get_auto_moto_mobility_pack())
    validation = validate_auto_moto_mobility_pack()
    summary["validation_summary"] = {
        "valid": validation["valid"],
        "stage_title_exact": validation["stage_title_exact"],
        "engine_id_exact": validation["engine_id_exact"],
        "all_mega_categories_mapped_to_engine": validation["all_mega_categories_mapped_to_engine"],
    }
    return summary


def validate_auto_moto_mobility_pack() -> dict:
    return validate_pack(
        pack=get_auto_moto_mobility_pack(),
        expected_stage_title=_STAGE_TITLE,
        expected_engine_id=_ENGINE_ID,
        expected_mega_category_ids=_EXPECTED_MEGA_CATEGORIES,
        minimum_totals=_MINIMUM_TOTALS,
    )
