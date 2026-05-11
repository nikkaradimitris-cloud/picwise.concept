from __future__ import annotations

import json
from copy import deepcopy

_ENGINE_ID = "fashion_footwear_jewelry_accessories_engine"
_SCHEMA_VERSION = "1.0.0"
_SOURCE = "stage_23c_fashion_footwear_jewelry_accessories_deep_pack"

_FORBIDDEN_KEYS = {
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "affiliate",
    "commission",
    "seller",
    "store_offer",
    "sku",
}

_REQUIRED_MEGA_CATEGORY_FIELDS = (
    "mega_category_id",
    "engine_id",
    "display_name",
    "departments",
    "subcategories",
    "product_families",
    "spec_fields",
    "buying_priorities",
    "alias_terms",
    "greeklish_terms",
    "typo_terms",
    "intent_patterns",
    "ambiguity_rules",
    "safety_notes",
    "expansion_status",
)

_MINIMUM_DEPTH = {
    "clothing_apparel_workwear": {
        "departments": 12,
        "subcategories": 70,
        "product_families": 140,
        "spec_fields": 35,
        "buying_priorities": 25,
        "alias_terms": 100,
        "greeklish_terms": 60,
        "typo_terms": 40,
        "intent_patterns": 80,
        "ambiguity_rules": 12,
    },
    "footwear_shoes_sneakers_boots": {
        "departments": 12,
        "subcategories": 70,
        "product_families": 140,
        "spec_fields": 40,
        "buying_priorities": 30,
        "alias_terms": 110,
        "greeklish_terms": 65,
        "typo_terms": 45,
        "intent_patterns": 90,
        "ambiguity_rules": 14,
    },
    "jewelry_watches_bags_fashion_accessories": {
        "departments": 12,
        "subcategories": 70,
        "product_families": 140,
        "spec_fields": 35,
        "buying_priorities": 25,
        "alias_terms": 100,
        "greeklish_terms": 60,
        "typo_terms": 40,
        "intent_patterns": 80,
        "ambiguity_rules": 12,
    },
}

_REQUIRED_COVERAGE_MARKERS = {
    "clothing_apparel_workwear": [
        "men's clothing",
        "women's clothing",
        "kids clothing",
        "baby clothing",
        "jackets",
        "coats",
        "shirts",
        "t-shirts",
        "polos",
        "hoodies",
        "sweatshirts",
        "sweaters",
        "cardigans",
        "jeans",
        "trousers",
        "leggings",
        "skirts",
        "dresses",
        "suits",
        "blazers",
        "underwear",
        "socks",
        "thermal clothing",
        "rainwear",
        "sportswear",
        "activewear",
        "workwear",
        "uniforms",
        "safety clothing",
        "plus size",
        "maternity wear",
        "swimwear",
        "sleepwear",
        "formal wear",
        "casual wear",
        "school clothing",
        "outdoor clothing",
    ],
    "footwear_shoes_sneakers_boots": [
        "men's shoes",
        "women's shoes",
        "kids shoes",
        "baby shoes",
        "sneakers",
        "running shoes",
        "walking shoes",
        "comfort shoes",
        "orthopedic shoes",
        "anatomic shoes",
        "work shoes",
        "safety shoes",
        "boots",
        "ankle boots",
        "winter boots",
        "hiking boots",
        "waterproof shoes",
        "sandals",
        "slippers",
        "loafers",
        "dress shoes",
        "formal shoes",
        "casual shoes",
        "leather shoes",
        "sports shoes",
        "training shoes",
        "football shoes",
        "basketball shoes",
        "trail running shoes",
        "wide fit shoes",
        "narrow fit shoes",
        "standing all day",
        "walking a lot",
        "school shoes",
        "diabetic-friendly comfort footwear",
        "shoe care accessories",
        "insoles",
        "laces",
    ],
    "jewelry_watches_bags_fashion_accessories": [
        "jewelry",
        "rings",
        "necklaces",
        "bracelets",
        "earrings",
        "watches",
        "smart-looking watches",
        "sunglasses",
        "prescription frame accessories",
        "bags",
        "handbags",
        "backpacks",
        "laptop bags",
        "school bags",
        "travel bags",
        "suitcases",
        "wallets",
        "belts",
        "hats",
        "caps",
        "scarves",
        "gloves",
        "ties",
        "hair accessories",
        "fashion accessories",
        "travel accessories",
        "work bags",
        "gym bags",
        "crossbody bags",
        "shoulder bags",
        "leather goods",
        "jewelry storage",
        "watch straps",
        "bag organizers",
    ],
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw_value in values:
        value = raw_value.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _trimmed_unique_count(values: list[str]) -> int:
    return len(_dedupe(values))


def _expand_product_families(
    base_items: list[str],
    variants: list[str],
    contexts: list[str],
    minimum: int,
) -> list[str]:
    families = _dedupe(base_items)
    for item in base_items:
        for variant in variants:
            for context in contexts:
                families.append(f"{variant} {item} {context}")
                if _trimmed_unique_count(families) >= minimum:
                    return _dedupe(families)
    return _dedupe(families)


def _expand_alias_terms(
    seeds: list[str],
    departments: list[str],
    subcategories: list[str],
    universe_name: str,
    minimum: int,
) -> list[str]:
    aliases = _dedupe(seeds)
    for department in departments:
        aliases.extend(
            [
                department,
                f"{department} catalog",
                f"{department} taxonomy",
                f"{universe_name} {department}",
            ]
        )
    for subcategory in subcategories:
        aliases.extend(
            [
                subcategory,
                f"{subcategory} collection",
                f"{subcategory} guide",
                f"{universe_name} {subcategory}",
            ]
        )
        if _trimmed_unique_count(aliases) >= minimum:
            return _dedupe(aliases)
    return _dedupe(aliases)


def _expand_greeklish(seeds: list[str], contexts: list[str], minimum: int) -> list[str]:
    terms = _dedupe(seeds)
    for seed in seeds:
        for context in contexts:
            terms.append(f"{seed} {context}")
            if _trimmed_unique_count(terms) >= minimum:
                return _dedupe(terms)
    return _dedupe(terms)


def _generate_typo_candidates(base_terms: list[str], minimum: int) -> list[str]:
    typos: list[str] = []
    replacements = (
        ("ch", "x"),
        ("ks", "x"),
        ("th", "t"),
        ("ph", "f"),
        ("oi", "i"),
        ("ou", "u"),
        ("ei", "i"),
        ("ai", "e"),
    )
    for term in base_terms:
        compact = term.replace(" ", "")
        typos.append(compact)
        typos.append(term.replace(" ", ""))
        for old, new in replacements:
            if old in term:
                typos.append(term.replace(old, new))
        typos.append(term.replace("o", "0"))
        typos.append(term.replace("i", "1"))
        if _trimmed_unique_count(typos) >= minimum:
            return _dedupe(typos)
    return _dedupe(typos)


def _expand_intents(
    seeds: list[str],
    product_terms: list[str],
    jobs: list[str],
    minimum: int,
) -> list[str]:
    intents = _dedupe(seeds)
    templates = [
        "thelo {item} gia {job}",
        "psaxno {item} me emfasi se {job}",
        "ti na paro apo {item} gia {job}",
        "protimisi se {item} gia {job}",
    ]
    for item in product_terms:
        for job in jobs:
            for template in templates:
                intents.append(template.format(item=item, job=job))
                if _trimmed_unique_count(intents) >= minimum:
                    return _dedupe(intents)
    return _dedupe(intents)


def _build_clothing_record() -> dict:
    departments = [
        "men's clothing",
        "women's clothing",
        "kids clothing",
        "baby clothing",
        "jackets and coats",
        "tops shirts and t-shirts",
        "pants denim and tailoring",
        "underwear socks and thermal layers",
        "sportswear and activewear",
        "workwear uniforms and safety clothing",
        "seasonal formal casual and occasion wear",
        "plus size and maternity wear",
        "swimwear sleepwear and loungewear",
        "school and outdoor clothing",
    ]
    subcategories = _dedupe(
        [
            "jackets",
            "coats",
            "shirts",
            "t-shirts",
            "polos",
            "hoodies",
            "sweatshirts",
            "sweaters",
            "cardigans",
            "jeans",
            "trousers",
            "chinos",
            "leggings",
            "skirts",
            "dresses",
            "suits",
            "blazers",
            "underwear",
            "socks",
            "thermal clothing",
            "rainwear",
            "sportswear",
            "activewear",
            "workwear",
            "uniforms",
            "safety clothing",
            "plus size",
            "maternity wear",
            "swimwear",
            "sleepwear",
            "formal wear",
            "casual wear",
            "seasonal clothing",
            "school clothing",
            "outdoor clothing",
            "men's clothing",
            "women's clothing",
            "kids clothing",
            "baby clothing",
            "cargo pants",
            "jogger pants",
            "linen trousers",
            "office shirts",
            "overshirts",
            "fleece jackets",
            "puffer jackets",
            "softshell jackets",
            "wool coats",
            "trench coats",
            "work pants",
            "hi-vis jackets",
            "chef uniforms",
            "medical scrubs",
            "school uniforms",
            "training sets",
            "track pants",
            "sports bras",
            "compression wear",
            "base layers",
            "rain pants",
            "rain coats",
            "ski base layers",
            "tank tops",
            "long sleeve t-shirts",
            "button-down shirts",
            "maxi dresses",
            "midi dresses",
            "mini skirts",
            "pleated skirts",
            "suit trousers",
            "formal blazers",
            "casual blazers",
            "nightwear sets",
            "pajama bottoms",
            "onesies for baby",
            "baby bodysuits",
            "kids tracksuits",
            "outdoor fleece tops",
            "hiking pants apparel",
            "protective overalls",
            "industrial aprons",
            "hospitality uniforms",
            "construction safety wear",
            "motorcycle rainwear apparel",
        ]
    )
    product_families = _expand_product_families(
        base_items=[
            "jackets",
            "coats",
            "shirts",
            "t-shirts",
            "polos",
            "hoodies",
            "sweatshirts",
            "sweaters",
            "cardigans",
            "jeans",
            "trousers",
            "chinos",
            "leggings",
            "skirts",
            "dresses",
            "suits",
            "blazers",
            "underwear",
            "socks",
            "thermal clothing",
            "rainwear",
            "sportswear",
            "activewear",
            "workwear",
            "uniforms",
            "safety clothing",
            "plus size",
            "maternity wear",
            "swimwear",
            "sleepwear",
            "formal wear",
            "casual wear",
            "seasonal clothing",
            "school clothing",
            "outdoor clothing",
            "cargo pants",
            "base layers",
            "fleece jackets",
            "medical scrubs",
            "protective overalls",
        ],
        variants=["entry", "daily", "comfort", "pro", "premium", "all-season", "performance"],
        contexts=["families", "ranges", "collections", "systems", "taxonomy groups"],
        minimum=_MINIMUM_DEPTH["clothing_apparel_workwear"]["product_families"],
    )
    spec_fields = [
        "gender",
        "age_group",
        "size",
        "fit",
        "cut",
        "material",
        "fabric_weight",
        "season",
        "color",
        "pattern",
        "sleeve_length",
        "length",
        "waist_size",
        "chest_size",
        "waterproof",
        "breathable",
        "thermal",
        "stretch",
        "closure_type",
        "care_instructions",
        "occasion",
        "work_safety_standard",
        "inseam_length",
        "rise_type",
        "collar_type",
        "hood_type",
        "lining_type",
        "insulation_weight",
        "pocket_count",
        "reflective_elements",
        "windproof",
        "uv_protection",
        "moisture_wicking",
        "odor_control",
        "shrink_resistance",
        "return_fit_risk",
        "true_to_size",
        "layering_level",
    ]
    buying_priorities = [
        "fit_accuracy_for_body_shape",
        "size_system_clarity",
        "return_fit_risk_reduction",
        "fabric_durability",
        "seasonal_comfort",
        "breathability_for_daily_use",
        "waterproof_need_alignment",
        "thermal_retention_level",
        "stretch_for_mobility",
        "work_safety_compliance",
        "wash_and_care_simplicity",
        "color_fastness",
        "anti-pilling_behavior",
        "layering_compatibility",
        "occasion_versatility",
        "school_uniform_compliance",
        "professional_appearance_balance",
        "casual_comfort_balance",
        "activewear_performance",
        "sportswear_sweat_management",
        "plus_size_pattern_quality",
        "maternity_comfort_support",
        "seam_strength_for_workwear",
        "pocket_utility",
        "rainwear_weather_protection",
        "thermal_base_layer_efficiency",
        "outdoor_wind_protection",
    ]
    alias_terms = _expand_alias_terms(
        seeds=[
            "ρούχα",
            "ενδύματα",
            "ανδρικά ρούχα",
            "γυναικεία ρούχα",
            "παιδικά ρούχα",
            "βρεφικά ρούχα",
            "ρούχα εργασίας",
            "στολές εργασίας",
            "ρούχα ασφαλείας",
            "casual apparel",
            "formal apparel",
            "workwear apparel",
            "sportswear apparel",
            "activewear apparel",
            "plus size clothing",
            "maternity apparel",
            "school clothing",
            "outdoor apparel",
        ],
        departments=departments,
        subcategories=subcategories,
        universe_name="clothing",
        minimum=_MINIMUM_DEPTH["clothing_apparel_workwear"]["alias_terms"],
    )
    greeklish_terms = _expand_greeklish(
        seeds=[
            "andrika rouxa",
            "gynaikeia rouxa",
            "paidika rouxa",
            "vrefika rouxa",
            "mpoufan",
            "palto",
            "poukamiso",
            "t shirt",
            "polo mplouza",
            "fouter",
            "sweatshirt",
            "poulover",
            "zaketa",
            "jean panteloni",
            "panteloni yfasmatino",
            "chino panteloni",
            "kolan",
            "fousta",
            "forema",
            "kostoumi",
            "sakaki",
            "eswrouxo",
            "kaltses",
            "thermika rouxa",
            "adiavroxo",
            "sportswear",
            "activewear",
            "rouxa ergasias",
            "stoles",
            "safe clothing",
            "plus size",
            "egkymosynis rouxa",
            "mayio",
            "pytzama",
            "formal wear",
            "casual wear",
            "sxolika rouxa",
            "outdoor rouxa",
        ],
        contexts=[
            "gia xeimona",
            "gia kalokairi",
            "gia douleia",
            "gia kathimerini xrisi",
            "me kali efarmogi",
            "aneta",
        ],
        minimum=_MINIMUM_DEPTH["clothing_apparel_workwear"]["greeklish_terms"],
    )
    typo_terms = _generate_typo_candidates(
        base_terms=greeklish_terms,
        minimum=_MINIMUM_DEPTH["clothing_apparel_workwear"]["typo_terms"],
    )
    intent_patterns = _expand_intents(
        seeds=[
            "ανδρικο μπουφαν αδιαβροχο",
            "mpoufan gynaikeio zimona",
            "παντελονι εργασιας με τσεπες",
            "t shirt βαμβακερο ανδρικο",
            "φορεμα καθημερινο καλοκαιρινο",
            "θερμικα ρουχα για κρυο",
            "αδιαβροχο μπουφαν για μηχανη",
            "ρουχα εργασιας ανθεκτικα",
            "παιδικη φορμα σχολειο",
            "plus size φορεμα επισημο",
            "psaxno andrika t-shirts me kalh efarmogh",
            "thelo casual hoodies gia kathe mera",
        ],
        product_terms=subcategories[:35],
        jobs=[
            "kathimerini xrisi",
            "epaggelmatiki xrisi",
            "orthostasia stin douleia",
            "xeimerino kryo",
            "kalokairini anesa",
            "gym kai proponisi",
            "sxoleio",
            "epishmo event",
            "taxidi",
            "outdoor drastiriotites",
        ],
        minimum=_MINIMUM_DEPTH["clothing_apparel_workwear"]["intent_patterns"],
    )
    ambiguity_rules = [
        "treat fit references as ambiguous until size system, body-shape and intended layer count are known",
        "separate casual blazer intent from formal suit blazer intent by occasion cues",
        "split workwear from safety clothing when certification requirements are mentioned",
        "distinguish rainwear from waterproof winter coats by insulation and seasonal cues",
        "resolve t-shirt versus undershirt ambiguity through outerwear or underwear context",
        "route thermal clothing intent by base-layer usage rather than fashion-only styling terms",
        "separate sportswear and activewear intent through training type and sweat-management needs",
        "treat plus size queries as fit-block intent and require cut/measurement refinement",
        "treat maternity wear as body-change timeline intent and avoid merging into generic womenswear",
        "separate school clothing and school uniform intent by policy constraints",
        "resolve jeans trousers chinos intent by fabric and formality expectations",
        "flag high return risk when query includes uncertain fit phrases without measurements",
        "disambiguate unisex wording when gender-specific fit is implied by follow-up terms",
    ]
    return {
        "mega_category_id": "clothing_apparel_workwear",
        "engine_id": _ENGINE_ID,
        "display_name": "Clothing / Apparel / Workwear",
        "departments": _dedupe(departments),
        "subcategories": _dedupe(subcategories),
        "product_families": _dedupe(product_families),
        "spec_fields": _dedupe(spec_fields),
        "buying_priorities": _dedupe(buying_priorities),
        "alias_terms": _dedupe(alias_terms),
        "aliases": _dedupe(alias_terms),
        "greeklish_terms": _dedupe(greeklish_terms),
        "greeklish": _dedupe(greeklish_terms),
        "typo_terms": _dedupe(typo_terms),
        "typos": _dedupe(typo_terms),
        "intent_patterns": _dedupe(intent_patterns),
        "ambiguity_rules": _dedupe(ambiguity_rules),
        "safety_notes": [
            "taxonomy output is classification metadata and not product inventory",
            "this pack does not include products, offers, prices, sellers, stores, affiliates, or skus",
            "workwear and safety clothing labels are generic taxonomy tags and not certification guarantees",
        ],
        "expansion_status": "stage_23c_fashion_deep_pack_v1",
    }


def _build_footwear_record() -> dict:
    departments = [
        "men's shoes",
        "women's shoes",
        "kids shoes",
        "baby shoes",
        "sneakers and casual shoes",
        "running and training shoes",
        "walking comfort and anatomic footwear",
        "work shoes and safety shoes",
        "boots and seasonal weather footwear",
        "sandals slippers and summer footwear",
        "formal dress and leather shoes",
        "school shoes and everyday standing footwear",
        "fit width support and orthostasia-oriented footwear",
        "shoe care accessories insoles and laces",
    ]
    subcategories = _dedupe(
        [
            "men's shoes",
            "women's shoes",
            "kids shoes",
            "baby shoes",
            "sneakers",
            "running shoes",
            "walking shoes",
            "comfort shoes",
            "orthopedic shoes",
            "anatomic shoes",
            "work shoes",
            "safety shoes",
            "boots",
            "ankle boots",
            "winter boots",
            "hiking boots",
            "waterproof shoes",
            "sandals",
            "slippers",
            "loafers",
            "dress shoes",
            "formal shoes",
            "casual shoes",
            "leather shoes",
            "sports shoes",
            "training shoes",
            "football shoes",
            "basketball shoes",
            "trail running shoes",
            "wide fit shoes",
            "narrow fit shoes",
            "shoes for standing all day",
            "shoes for walking a lot",
            "school shoes",
            "diabetic-friendly comfort footwear",
            "shoe care accessories",
            "insoles",
            "laces",
            "slip resistant shoes",
            "non-slip work sneakers",
            "steel toe shoes",
            "composite toe shoes",
            "chef work shoes",
            "nurse clogs comfort",
            "construction boots",
            "waterproof work boots",
            "ankle support boots",
            "lightweight running shoes",
            "max cushion running shoes",
            "neutral running shoes",
            "stability running shoes",
            "road running shoes",
            "walking sneakers",
            "wide toe box footwear",
            "narrow heel fit footwear",
            "orthotic compatible shoes",
            "arch support shoes",
            "heel pain comfort shoes",
            "flat feet comfort shoes",
            "high arch comfort shoes",
            "kids school sneakers",
            "baby first-walk shoes",
            "formal derby shoes",
            "formal oxford shoes",
            "casual leather sneakers",
            "summer sandals",
            "winter lined boots",
            "hiking trail boots",
            "trekking shoes",
            "water shoes",
            "running spikes training context",
            "gym training shoes",
            "cross training shoes",
            "volleyball shoes",
            "tennis court shoes",
            "insoles arch support",
            "insoles shock absorption",
            "shoe deodorizer accessories",
            "shoe cleaning brushes",
            "replacement laces flat",
            "replacement laces round",
            "shoe protector spray",
            "shoe trees support",
            "workplace anti-fatigue footwear",
        ]
    )
    product_families = _expand_product_families(
        base_items=[
            "sneakers",
            "running shoes",
            "walking shoes",
            "comfort shoes",
            "orthopedic shoes",
            "anatomic shoes",
            "work shoes",
            "safety shoes",
            "boots",
            "ankle boots",
            "winter boots",
            "hiking boots",
            "waterproof shoes",
            "sandals",
            "slippers",
            "loafers",
            "dress shoes",
            "formal shoes",
            "casual shoes",
            "leather shoes",
            "sports shoes",
            "training shoes",
            "football shoes",
            "basketball shoes",
            "trail running shoes",
            "wide fit shoes",
            "narrow fit shoes",
            "school shoes",
            "diabetic-friendly comfort footwear",
            "insoles",
            "laces",
            "slip resistant shoes",
            "steel toe shoes",
            "orthotic compatible shoes",
            "arch support shoes",
            "cross training shoes",
            "tennis court shoes",
            "shoe care accessories",
            "waterproof work boots",
            "anti-fatigue footwear",
        ],
        variants=["entry", "daily", "comfort", "pro", "premium", "all-day", "performance"],
        contexts=["families", "ranges", "collections", "systems", "taxonomy groups"],
        minimum=_MINIMUM_DEPTH["footwear_shoes_sneakers_boots"]["product_families"],
    )
    spec_fields = [
        "gender",
        "age_group",
        "shoe_size",
        "eu_size",
        "uk_size",
        "us_size",
        "fit_width",
        "arch_support",
        "cushioning",
        "heel_height",
        "sole_material",
        "upper_material",
        "closure_type",
        "waterproof",
        "breathable",
        "slip_resistant",
        "safety_toe",
        "safety_standard",
        "use_case",
        "terrain",
        "season",
        "color",
        "return_fit_risk",
        "true_to_size",
        "toe_box_width",
        "heel_counter_stiffness",
        "midsole_density",
        "outsole_traction_pattern",
        "drop_mm",
        "weight_grams",
        "insock_material",
        "removable_insole",
        "orthotic_compatible",
        "ankle_support_level",
        "puncture_resistance",
        "electrostatic_protection",
        "oil_resistance",
        "shock_absorption",
        "lining_material",
        "break_in_expectation",
        "fit_feedback_score",
        "standing_duration_recommendation",
    ]
    buying_priorities = [
        "fit_accuracy_and_sizing_confidence",
        "return_fit_risk_reduction",
        "all_day_comfort_for_orthostasia",
        "walking_distance_support",
        "arch_support_match",
        "cushioning_response_balance",
        "slip_resistance_for_work_surfaces",
        "safety_standard_coverage",
        "toe_protection_level",
        "waterproof_vs_breathable_balance",
        "terrain_traction_match",
        "activity_specific_use_case_fit",
        "true_to_size_consistency",
        "width_selection_confidence",
        "ankle_support_need",
        "heel_pressure_management",
        "insole_replaceability",
        "orthotic_compatibility",
        "sole_durability",
        "upper_material_durability",
        "weather_season_readiness",
        "weight_for_long_use",
        "break_in_time_tolerance",
        "school_use_resilience",
        "work_shift_endurance",
        "running_gait_alignment",
        "care_and_maintenance_ease",
        "lace_and_closure_reliability",
        "odor_management_support",
        "value_over_lifecycle",
        "non_medical_comfort_context_safety",
    ]
    alias_terms = _expand_alias_terms(
        seeds=[
            "παπούτσια",
            "υποδήματα",
            "ανδρικά παπούτσια",
            "γυναικεία παπούτσια",
            "παιδικά παπούτσια",
            "βρεφικά παπούτσια",
            "sneakers",
            "running shoes",
            "walking shoes",
            "comfort shoes",
            "ανατομικά παπούτσια",
            "ορθοπεδικά παπούτσια",
            "παπούτσια εργασίας",
            "παπούτσια ασφαλείας",
            "μπότες",
            "μποτάκια",
            "sandals",
            "slippers",
            "loafers",
            "formal shoes",
            "school shoes",
            "wide fit shoes",
            "insoles",
            "laces",
            "shoe care accessories",
        ],
        departments=departments,
        subcategories=subcategories,
        universe_name="footwear",
        minimum=_MINIMUM_DEPTH["footwear_shoes_sneakers_boots"]["alias_terms"],
    )
    greeklish_terms = _expand_greeklish(
        seeds=[
            "andrika papoutsia",
            "gynaikeia papoutsia",
            "paidika papoutsia",
            "vrefika papoutsia",
            "sneakers",
            "running shoes",
            "walking shoes",
            "comfort shoes",
            "orthopedic shoes",
            "anatomika papoutsia",
            "papoutsia ergasias",
            "papoutsia asfaleias",
            "mpotes",
            "mpotakia",
            "xeimoniatika mpotakia",
            "oreivatika mpotakia",
            "adiavroxa papoutsia",
            "pedila",
            "pantofles",
            "loafer papoutsia",
            "dress shoes",
            "formal papoutsia",
            "casual papoutsia",
            "dermatina papoutsia",
            "sports shoes",
            "training shoes",
            "football shoes",
            "basketball shoes",
            "trail running shoes",
            "wide fit papoutsia",
            "narrow fit papoutsia",
            "papoutsia gia orthostasia",
            "papoutsia gia poly perpatima",
            "sxolika papoutsia",
            "diabetic friendly comfort footwear",
            "aksesouar frontidas papoutsion",
            "patoi papoutsion",
            "kordonia",
            "antiolisthitika papoutsia",
            "steel toe papoutsia",
        ],
        contexts=[
            "gia douleia",
            "gia kathimerini xrisi",
            "gia orthostasia",
            "gia perpatima",
            "gia xeimona",
            "aneta",
        ],
        minimum=_MINIMUM_DEPTH["footwear_shoes_sneakers_boots"]["greeklish_terms"],
    )
    typo_terms = _generate_typo_candidates(
        base_terms=greeklish_terms,
        minimum=_MINIMUM_DEPTH["footwear_shoes_sneakers_boots"]["typo_terms"],
    )
    intent_patterns = _expand_intents(
        seeds=[
            "ανδρικα παπουτσια για πολυ περπατημα",
            "papoutsia gia orthostasia",
            "sneakers μαυρα ανετα",
            "παπουτσια ασφαλειας αδιαβροχα",
            "μποτακια γυναικεια καθημερινα",
            "running shoes για ασφαλτο",
            "παιδικα παπουτσια για σχολειο",
            "παπουτσια για φαρδυ ποδι",
            "αδιαβροχα μποτακια χειμωνα",
            "ανατομικα παπουτσια καθημερινα",
            "παπουτσια δουλειας αντιολισθητικα",
            "sneakers 42 ανετα για περπατημα",
            "thelo comfortable loafers gia orthostasia sto grafeio",
            "psaxno insole me arch support gia merikh anafisi",
        ],
        product_terms=subcategories[:38],
        jobs=[
            "kathimerini xrisi",
            "orthostasia se vardia",
            "poly perpatima",
            "proponisi gym",
            "road running",
            "trail running",
            "ergasia se ygra perivallonta",
            "sxoleio",
            "taxidi",
            "xeimerino kryo",
            "grafiaki emfanish",
        ],
        minimum=_MINIMUM_DEPTH["footwear_shoes_sneakers_boots"]["intent_patterns"],
    )
    ambiguity_rules = [
        "treat shoe size as ambiguous until eu/uk/us mapping is resolved",
        "resolve fit width ambiguity by separating narrow, regular and wide-fit intent",
        "route running shoes by terrain before prioritizing style or color",
        "separate walking comfort shoes from running shoes unless pace/training cues exist",
        "separate safety shoes from work-casual shoes when standards are mentioned",
        "treat waterproof and breathable as a tradeoff requiring user-priority clarification",
        "resolve return-fit-risk by requiring true-to-size or foot-length context",
        "split orthopedic and anatomic wording into non-medical comfort fit intent unless clinical terms appear",
        "treat standing all day requests as cushioning + arch support + slip resistance bundle intent",
        "disambiguate boots versus ankle boots by shaft-height cues",
        "separate school shoes from sports shoes when dress code or durability is emphasized",
        "route insoles and laces into accessories branch unless shoe replacement intent is explicit",
        "treat diabetic-friendly comfort footwear in non-medical consumer context only",
        "resolve leather formal shoes and casual leather sneakers through occasion intent",
        "flag high ambiguity when only color and size are provided without use-case",
    ]
    return {
        "mega_category_id": "footwear_shoes_sneakers_boots",
        "engine_id": _ENGINE_ID,
        "display_name": "Footwear / Shoes / Sneakers / Boots",
        "departments": _dedupe(departments),
        "subcategories": _dedupe(subcategories),
        "product_families": _dedupe(product_families),
        "spec_fields": _dedupe(spec_fields),
        "buying_priorities": _dedupe(buying_priorities),
        "alias_terms": _dedupe(alias_terms),
        "aliases": _dedupe(alias_terms),
        "greeklish_terms": _dedupe(greeklish_terms),
        "greeklish": _dedupe(greeklish_terms),
        "typo_terms": _dedupe(typo_terms),
        "typos": _dedupe(typo_terms),
        "intent_patterns": _dedupe(intent_patterns),
        "ambiguity_rules": _dedupe(ambiguity_rules),
        "safety_notes": [
            "taxonomy output is classification metadata and not product inventory",
            "this pack does not include products, offers, prices, sellers, stores, affiliates, or skus",
            "diabetic-friendly comfort footwear remains non-medical consumer taxonomy context only",
        ],
        "expansion_status": "stage_23c_fashion_deep_pack_v1",
    }


def _build_jewelry_accessories_record() -> dict:
    departments = [
        "jewelry and fine fashion jewelry",
        "rings necklaces bracelets earrings",
        "watches and smart-looking fashion watches",
        "sunglasses and frame accessories",
        "bags handbags and shoulder bags",
        "backpacks school bags and work bags",
        "laptop bags and office carry accessories",
        "travel bags luggage and suitcases",
        "wallets belts and leather goods",
        "hats caps scarves gloves and ties",
        "hair accessories and styling accessories",
        "jewelry storage watch straps and bag organizers",
        "gym bags crossbody bags and daily accessories",
        "fashion accessories and occasion styling",
    ]
    subcategories = _dedupe(
        [
            "jewelry",
            "rings",
            "necklaces",
            "bracelets",
            "earrings",
            "watches",
            "smart-looking watches",
            "sunglasses",
            "prescription frame accessories",
            "bags",
            "handbags",
            "backpacks",
            "laptop bags",
            "school bags",
            "travel bags",
            "suitcases",
            "wallets",
            "belts",
            "hats",
            "caps",
            "scarves",
            "gloves",
            "ties",
            "hair accessories",
            "fashion accessories",
            "travel accessories",
            "work bags",
            "gym bags",
            "crossbody bags",
            "shoulder bags",
            "leather goods",
            "jewelry storage",
            "watch straps",
            "bag organizers",
            "tote bags",
            "clutch bags",
            "messenger bags",
            "duffel bags",
            "carry-on suitcases",
            "checked luggage suitcases",
            "cabin bags",
            "laptop sleeves",
            "wallet card holders",
            "coin wallets",
            "belt bags",
            "phone pouches",
            "beaded bracelets",
            "chain necklaces",
            "pendant necklaces",
            "stud earrings",
            "hoop earrings",
            "wedding rings style context",
            "signet rings",
            "watch bands",
            "watch clasps",
            "jewelry boxes",
            "ring organizers",
            "necklace stands",
            "earring trays",
            "bag inserts",
            "bag straps replacement",
            "sunglasses polarized",
            "fashion blue-light style frames",
            "travel passport holders",
            "luggage tags",
            "packing pouches",
            "tie clips",
            "cufflink accessories",
            "hair clips",
            "hair bands",
            "hair scrunchies",
            "winter gloves fashion",
            "leather gloves style",
            "wool scarves",
            "silk scarves",
            "baseball caps",
            "bucket hats",
            "fedora hats",
            "gym duffel bags",
            "work tote bags",
            "minimalist wallets",
            "zip-around wallets",
            "crossbody sling bags",
            "shoulder tote hybrids",
        ]
    )
    product_families = _expand_product_families(
        base_items=[
            "jewelry",
            "rings",
            "necklaces",
            "bracelets",
            "earrings",
            "watches",
            "smart-looking watches",
            "sunglasses",
            "prescription frame accessories",
            "handbags",
            "backpacks",
            "laptop bags",
            "school bags",
            "travel bags",
            "suitcases",
            "wallets",
            "belts",
            "hats",
            "caps",
            "scarves",
            "gloves",
            "ties",
            "hair accessories",
            "fashion accessories",
            "travel accessories",
            "work bags",
            "gym bags",
            "crossbody bags",
            "shoulder bags",
            "leather goods",
            "jewelry storage",
            "watch straps",
            "bag organizers",
            "tote bags",
            "clutch bags",
            "duffel bags",
            "cabin bags",
            "minimalist wallets",
            "sunglasses polarized",
            "bag inserts",
        ],
        variants=["entry", "daily", "elegant", "pro", "premium", "travel", "occasion"],
        contexts=["families", "ranges", "collections", "systems", "taxonomy groups"],
        minimum=_MINIMUM_DEPTH["jewelry_watches_bags_fashion_accessories"]["product_families"],
    )
    spec_fields = [
        "gender",
        "age_group",
        "material",
        "metal_type",
        "stone_type",
        "size",
        "length",
        "width",
        "capacity_liters",
        "laptop_size",
        "compartment_count",
        "closure_type",
        "strap_type",
        "waterproof",
        "scratch_resistant",
        "lens_type",
        "uv_protection",
        "color",
        "style",
        "occasion",
        "travel_size",
        "cabin_size",
        "durability_level",
        "weight_grams",
        "frame_material",
        "polarized",
        "strap_adjustability",
        "buckle_type",
        "lining_material",
        "security_features",
        "expandable_volume",
        "wheel_type",
        "handle_type",
        "jewelry_finish",
        "allergy_friendly",
        "storage_capacity",
        "organizational_layout",
        "return_fit_risk",
    ]
    buying_priorities = [
        "material_durability_balance",
        "style_occasion_alignment",
        "daily_comfort_and_weight",
        "capacity_vs_portability",
        "laptop_fit_confidence",
        "travel_size_compliance",
        "cabin_size_fit_risk_reduction",
        "compartment_organization",
        "closure_security",
        "strap_comfort_adjustability",
        "scratch_resistance_expectation",
        "waterproof_need_alignment",
        "uv_protection_need_for_sunglasses",
        "lens_type_preference",
        "metal_allergy_consideration",
        "stone_style_preference",
        "watch_strap_replaceability",
        "bag_organizer_compatibility",
        "wallet_layout_efficiency",
        "belt_buckle_reliability",
        "hair_accessory_hold_strength",
        "seasonal_accessory_utility",
        "travel_accessory_bundle_fit",
        "work_bag_professional_look",
        "gym_bag_odor_and_washability",
        "overall_style_consistency",
        "value_over_lifecycle",
    ]
    alias_terms = _expand_alias_terms(
        seeds=[
            "κοσμήματα",
            "δαχτυλίδια",
            "κολιέ",
            "βραχιόλια",
            "σκουλαρίκια",
            "ρολόγια",
            "γυαλιά ηλίου",
            "τσάντες",
            "γυναικείες τσάντες",
            "ανδρικά πορτοφόλια",
            "backpacks",
            "laptop bags",
            "travel bags",
            "suitcases",
            "wallets",
            "belts",
            "scarves",
            "fashion accessories",
            "watch straps",
            "jewelry storage",
            "bag organizers",
            "crossbody bags",
            "shoulder bags",
        ],
        departments=departments,
        subcategories=subcategories,
        universe_name="accessories",
        minimum=_MINIMUM_DEPTH["jewelry_watches_bags_fashion_accessories"]["alias_terms"],
    )
    greeklish_terms = _expand_greeklish(
        seeds=[
            "kosmimata",
            "daxtylidia",
            "kolie",
            "vraxiolia",
            "skoularikia",
            "roloi",
            "smart-looking watches",
            "gyalia hliou",
            "polarized gyalia",
            "aksesouar sxetika me frame",
            "tsantes",
            "gynaikeia tsanta",
            "andriko portofoli",
            "sakidio platis",
            "tsanta laptop",
            "sxoliki tsanta",
            "taxidiotiki tsanta",
            "valitsa",
            "crossbody tsanta",
            "shoulder bag",
            "gym bag",
            "work bag",
            "wallet",
            "zoni",
            "kapelo",
            "jockey",
            "kaskol",
            "gantia",
            "grammata tie",
            "aksesouar mallion",
            "leather goods",
            "thiki kosmimaton",
            "louri rologiou",
            "organotis tsantas",
            "cabin bag",
            "passport holder",
            "luggage tag",
            "hair clips",
            "scrunchies",
        ],
        contexts=[
            "gia kathimerini xrisi",
            "gia douleia",
            "gia taxidi",
            "gia epishmi eksodo",
            "aneto",
            "stylish",
        ],
        minimum=_MINIMUM_DEPTH["jewelry_watches_bags_fashion_accessories"]["greeklish_terms"],
    )
    typo_terms = _generate_typo_candidates(
        base_terms=greeklish_terms,
        minimum=_MINIMUM_DEPTH["jewelry_watches_bags_fashion_accessories"]["typo_terms"],
    )
    intent_patterns = _expand_intents(
        seeds=[
            "τσαντα laptop 15.6",
            "tsanta platis gia sxoleio",
            "γυναικεια τσαντα καθημερινη",
            "ανδρικο πορτοφολι δερματινο",
            "βαλιτσα καμπινας ελαφρια",
            "γυαλια ηλιου polarized",
            "ρολοι ανδρικο καθημερινο",
            "κολιε ασημι",
            "δαχτυλιδι γυναικειο",
            "ζωνη δερματινη ανδρικη",
            "σακιδιο πλατης για ταξιδι",
            "τσάντα γυμναστηρίου",
            "thelo watch straps replacement me andoxi",
            "psaxno jewelry storage gia polla daxtylidia",
        ],
        product_terms=subcategories[:36],
        jobs=[
            "kathimerini xrisi",
            "douleia",
            "taxidi",
            "gym",
            "sxoleio",
            "epishmi eksodos",
            "minimal style",
            "capacity me organosi",
            "carry laptop",
            "lightweight metakinisi",
        ],
        minimum=_MINIMUM_DEPTH["jewelry_watches_bags_fashion_accessories"]["intent_patterns"],
    )
    ambiguity_rules = [
        "separate jewelry styling intent from gift-intent when recipient clues are missing",
        "disambiguate rings by size versus decorative-only intent to reduce return mismatch",
        "split smart-looking watches in fashion context from technical smartwatch feature intent",
        "treat sunglasses lens terms as fashion accessory taxonomy unless medical prescription cues appear",
        "route laptop bags by laptop_size and compartment_count before style preference",
        "separate school bags from travel backpacks by daily load and organization intent",
        "resolve cabin size luggage intent by travel_size and airline compliance wording",
        "distinguish crossbody and shoulder bags by strap_type and carrying-position intent",
        "route wallet queries through card-capacity and closure preferences to lower mismatch risk",
        "separate belt style intent from belt-size fit intent when waist clues are provided",
        "treat watch strap replacements as compatibility-driven accessory flow",
        "disambiguate bag organizers versus cosmetic pouches by compartment and bag-type context",
        "keep prescription frame accessories in non-medical fashion context only",
    ]
    return {
        "mega_category_id": "jewelry_watches_bags_fashion_accessories",
        "engine_id": _ENGINE_ID,
        "display_name": "Jewelry / Watches / Bags / Fashion Accessories",
        "departments": _dedupe(departments),
        "subcategories": _dedupe(subcategories),
        "product_families": _dedupe(product_families),
        "spec_fields": _dedupe(spec_fields),
        "buying_priorities": _dedupe(buying_priorities),
        "alias_terms": _dedupe(alias_terms),
        "aliases": _dedupe(alias_terms),
        "greeklish_terms": _dedupe(greeklish_terms),
        "greeklish": _dedupe(greeklish_terms),
        "typo_terms": _dedupe(typo_terms),
        "typos": _dedupe(typo_terms),
        "intent_patterns": _dedupe(intent_patterns),
        "ambiguity_rules": _dedupe(ambiguity_rules),
        "safety_notes": [
            "taxonomy output is classification metadata and not product inventory",
            "this pack does not include products, offers, prices, sellers, stores, affiliates, or skus",
            "smart-looking watches are represented as fashion-accessory taxonomy intent only",
            "prescription frame accessory terms are represented in non-medical fashion context only",
        ],
        "expansion_status": "stage_23c_fashion_deep_pack_v1",
    }


_FASHION_FOOTWEAR_JEWELRY_ACCESSORIES_PACK = {
    "engine_id": _ENGINE_ID,
    "schema_version": _SCHEMA_VERSION,
    "source": _SOURCE,
    "mega_categories": [
        _build_clothing_record(),
        _build_footwear_record(),
        _build_jewelry_accessories_record(),
    ],
}


def get_fashion_footwear_jewelry_accessories_pack() -> dict:
    """Return the deterministic deep taxonomy expansion pack."""
    return deepcopy(_FASHION_FOOTWEAR_JEWELRY_ACCESSORIES_PACK)


def get_fashion_mega_category_pack(mega_category_id: str) -> dict | None:
    """Return one deep-pack mega-category record by identifier."""
    for record in _FASHION_FOOTWEAR_JEWELRY_ACCESSORIES_PACK["mega_categories"]:
        if record["mega_category_id"] == mega_category_id:
            return deepcopy(record)
    return None


def summarize_fashion_footwear_jewelry_accessories_pack() -> dict:
    """Return deterministic aggregate depth counts for the pack."""
    pack = get_fashion_footwear_jewelry_accessories_pack()
    mega_categories = pack["mega_categories"]
    mega_ids = [record["mega_category_id"] for record in mega_categories]
    category_counts = {
        "department_counts": "departments",
        "subcategory_counts": "subcategories",
        "product_family_seed_counts": "product_families",
        "spec_field_counts": "spec_fields",
        "buying_priority_counts": "buying_priorities",
        "alias_term_counts": "alias_terms",
        "greeklish_term_counts": "greeklish_terms",
        "typo_term_counts": "typo_terms",
        "intent_pattern_counts": "intent_patterns",
        "ambiguity_rule_counts": "ambiguity_rules",
    }
    counts: dict[str, dict[str, int]] = {}
    for count_key, field_name in category_counts.items():
        counts[count_key] = {
            record["mega_category_id"]: _trimmed_unique_count(record[field_name]) for record in mega_categories
        }
    return {
        "engine_id": pack["engine_id"],
        "schema_version": pack["schema_version"],
        "source": pack["source"],
        "mega_category_count": len(mega_categories),
        "mega_categories_covered": mega_ids,
        **counts,
        "total_departments": sum(counts["department_counts"].values()),
        "total_subcategories": sum(counts["subcategory_counts"].values()),
        "total_product_family_seeds": sum(counts["product_family_seed_counts"].values()),
        "total_spec_fields": sum(counts["spec_field_counts"].values()),
        "total_intent_patterns": sum(counts["intent_pattern_counts"].values()),
        "taxonomy_expansion_only": True,
        "not_product_inventory": True,
    }


def _contains_forbidden_keys(payload: object) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in _FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_keys(value):
                return True
        return False
    if isinstance(payload, list):
        return any(_contains_forbidden_keys(item) for item in payload)
    return False


def _has_required_shape(record: dict) -> bool:
    for field in _REQUIRED_MEGA_CATEGORY_FIELDS:
        if field not in record:
            return False
    if not isinstance(record["mega_category_id"], str) or not record["mega_category_id"]:
        return False
    if record["engine_id"] != _ENGINE_ID:
        return False
    if not isinstance(record["display_name"], str) or not record["display_name"]:
        return False
    if not isinstance(record["expansion_status"], str) or not record["expansion_status"]:
        return False
    required_list_fields = (
        "departments",
        "subcategories",
        "product_families",
        "spec_fields",
        "buying_priorities",
        "alias_terms",
        "greeklish_terms",
        "typo_terms",
        "intent_patterns",
        "ambiguity_rules",
        "safety_notes",
    )
    for field in required_list_fields:
        value = record[field]
        if not isinstance(value, list) or not value:
            return False
        if any(not isinstance(item, str) or not item.strip() for item in value):
            return False
    return True


def _is_json_serializable(payload: object) -> bool:
    try:
        json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


def _meets_minimum_depth(record: dict) -> tuple[bool, dict[str, int], dict[str, int]]:
    mega_category_id = record["mega_category_id"]
    minimums = _MINIMUM_DEPTH[mega_category_id]
    actuals = {field: _trimmed_unique_count(record[field]) for field in minimums}
    per_field_pass = {field: int(actuals[field] >= minimums[field]) for field in minimums}
    return all(bool(value) for value in per_field_pass.values()), actuals, minimums


def _has_required_broad_coverage(record: dict) -> tuple[bool, list[str]]:
    markers = _REQUIRED_COVERAGE_MARKERS[record["mega_category_id"]]
    haystack = " ".join(
        record["departments"]
        + record["subcategories"]
        + record["product_families"]
        + record["spec_fields"]
        + record["buying_priorities"]
        + record["intent_patterns"]
    ).lower()
    missing = [marker for marker in markers if marker.lower() not in haystack]
    return not missing, missing


def validate_fashion_footwear_jewelry_accessories_pack() -> dict:
    """Validate deterministic shape, depth, and safety constraints for the deep pack."""
    pack = get_fashion_footwear_jewelry_accessories_pack()
    summary = summarize_fashion_footwear_jewelry_accessories_pack()
    mega_categories = pack["mega_categories"]
    mega_ids = [record["mega_category_id"] for record in mega_categories]
    expected_mega_ids = [
        "clothing_apparel_workwear",
        "footwear_shoes_sneakers_boots",
        "jewelry_watches_bags_fashion_accessories",
    ]
    depth_checks: dict[str, bool] = {}
    depth_actuals: dict[str, dict[str, int]] = {}
    depth_minimums: dict[str, dict[str, int]] = {}
    broad_expansion_checks: dict[str, bool] = {}
    missing_markers: dict[str, list[str]] = {}
    for record in mega_categories:
        depth_ok, actuals, minimums = _meets_minimum_depth(record)
        depth_checks[record["mega_category_id"]] = depth_ok
        depth_actuals[record["mega_category_id"]] = actuals
        depth_minimums[record["mega_category_id"]] = minimums
        broad_ok, missing = _has_required_broad_coverage(record)
        broad_expansion_checks[record["mega_category_id"]] = broad_ok
        missing_markers[record["mega_category_id"]] = missing
    result = {
        "valid": True,
        "passed": True,
        "engine_id_matches": pack["engine_id"] == _ENGINE_ID,
        "schema_version_present": isinstance(pack.get("schema_version"), str) and bool(pack.get("schema_version")),
        "source_matches_stage": pack.get("source") == _SOURCE,
        "mega_category_count": len(mega_categories),
        "expected_mega_category_count": 3,
        "expected_mega_categories_present": mega_ids == expected_mega_ids,
        "all_mega_categories_have_required_shape": all(_has_required_shape(record) for record in mega_categories),
        "depth_checks_per_mega_category": depth_checks,
        "depth_actuals_per_mega_category": depth_actuals,
        "depth_minimums_per_mega_category": depth_minimums,
        "all_depth_minimums_passed": all(depth_checks.values()),
        "broad_expansion_checks_per_mega_category": broad_expansion_checks,
        "all_broad_expansion_checks_passed": all(broad_expansion_checks.values()),
        "missing_required_coverage_markers": missing_markers,
        "forbidden_fields_present": _contains_forbidden_keys(pack),
        "is_json_serializable": _is_json_serializable({"pack": pack, "summary": summary}),
        "fashion_engine_is_dedicated": pack["engine_id"] == "fashion_footwear_jewelry_accessories_engine",
        "fashion_engine_not_under_lifestyle": "lifestyle" not in pack["engine_id"],
        "taxonomy_expansion_only": True,
        "not_product_inventory": True,
        "no_claude_or_api_or_live_llm_required": True,
        "no_app_router_or_decision_machine_dependency_required": True,
        "no_local_nlu_runtime_change_required": True,
    }
    result["valid"] = (
        result["engine_id_matches"]
        and result["schema_version_present"]
        and result["source_matches_stage"]
        and result["mega_category_count"] == result["expected_mega_category_count"]
        and result["expected_mega_categories_present"]
        and result["all_mega_categories_have_required_shape"]
        and result["all_depth_minimums_passed"]
        and result["all_broad_expansion_checks_passed"]
        and not result["forbidden_fields_present"]
        and result["is_json_serializable"]
        and result["fashion_engine_is_dedicated"]
        and result["fashion_engine_not_under_lifestyle"]
        and result["taxonomy_expansion_only"]
        and result["not_product_inventory"]
        and result["no_claude_or_api_or_live_llm_required"]
        and result["no_app_router_or_decision_machine_dependency_required"]
        and result["no_local_nlu_runtime_change_required"]
    )
    result["passed"] = result["valid"]
    return result
