from __future__ import annotations

import json
from copy import deepcopy

_ENGINE_ID = "tools_diy_garden_repair_engine"
_SCHEMA_VERSION = "1.0.0"
_SOURCE = "stage_23b_tools_diy_garden_repair_deep_pack"

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
    "power_tools_workshop": {
        "departments": 10,
        "subcategories": 45,
        "product_families": 100,
        "spec_fields": 30,
        "buying_priorities": 20,
        "alias_terms": 80,
        "greeklish_terms": 40,
        "typo_terms": 30,
        "intent_patterns": 60,
        "ambiguity_rules": 10,
    },
    "hand_tools_consumables_measuring": {
        "departments": 12,
        "subcategories": 60,
        "product_families": 130,
        "spec_fields": 30,
        "buying_priorities": 20,
        "alias_terms": 90,
        "greeklish_terms": 50,
        "typo_terms": 35,
        "intent_patterns": 70,
        "ambiguity_rules": 10,
    },
    "garden_outdoor_repair_building": {
        "departments": 12,
        "subcategories": 60,
        "product_families": 130,
        "spec_fields": 30,
        "buying_priorities": 20,
        "alias_terms": 90,
        "greeklish_terms": 50,
        "typo_terms": 35,
        "intent_patterns": 70,
        "ambiguity_rules": 10,
    },
}

_REQUIRED_COVERAGE_MARKERS = {
    "power_tools_workshop": [
        "demolition hammers",
        "bench grinders",
        "table saws",
        "miter saws",
        "tile cutters",
        "polishers",
        "concrete mixers",
        "air tools",
        "battery platforms",
        "dust extraction",
        "workshop lighting",
        "tool organizers",
        "torque tools",
        "inspection cameras",
        "engraving tools",
        "sharpening tools",
        "pumps used in workshop context",
        "heavy duty professional tool lines as generic families only",
    ],
    "hand_tools_consumables_measuring": [
        "hex keys",
        "torx keys",
        "allen keys",
        "torque wrenches",
        "pipe wrenches",
        "adjustable wrenches",
        "crimping tools",
        "stripping tools",
        "soldering tools",
        "tap and die sets",
        "masonry drill bits",
        "metal drill bits",
        "wood drill bits",
        "hole saws",
        "router bits",
        "grinding wheels",
        "flap discs",
        "polishing pads",
        "staples",
        "rivets",
        "cable ties",
        "lubricants",
        "cleaning solvents",
        "threadlockers",
        "tapes",
        "ppe workwear accessories",
    ],
    "garden_outdoor_repair_building": [
        "robotic lawn mowers",
        "tillers",
        "cultivators",
        "garden sprayers",
        "irrigation timers",
        "drip irrigation",
        "garden hoses and reels",
        "outdoor power cables",
        "outdoor lighting",
        "patio cleaning",
        "drainage accessories",
        "gutters",
        "sealants for roof/walls",
        "waterproofing membranes",
        "plaster repair",
        "tile adhesives",
        "grout",
        "wall fillers",
        "electrical boxes",
        "cable conduits",
        "switches/sockets installation accessories",
        "plumbing fittings",
        "valves",
        "siphons",
        "pipe insulation",
        "ladders by type",
        "step ladders",
        "telescopic ladders",
        "work platforms",
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
                f"{department} solutions",
                f"{department} equipment",
                f"{universe_name} {department}",
            ]
        )
    for subcategory in subcategories:
        aliases.extend(
            [
                subcategory,
                f"{subcategory} tools",
                f"{subcategory} systems",
                f"{universe_name} {subcategory}",
            ]
        )
        if _trimmed_unique_count(aliases) >= minimum:
            return _dedupe(aliases)
    return _dedupe(aliases)


def _expand_greeklish(
    seeds: list[str],
    contexts: list[str],
    minimum: int,
) -> list[str]:
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
    )
    for term in base_terms:
        compact = term.replace(" ", "")
        typos.append(compact)
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


def _build_power_tools_record() -> dict:
    departments = [
        "drilling and fastening systems",
        "cutting and sawing systems",
        "grinding and polishing systems",
        "routing and carving systems",
        "demolition and concrete tools",
        "pneumatic and air tool systems",
        "workshop utility and dust extraction",
        "battery platforms and charging ecosystems",
        "workshop lighting and electrical distribution",
        "tool organizers and mobile storage",
        "workshop diagnostics and inspection equipment",
        "professional heavy duty generic tool lines",
    ]
    subcategories = _dedupe(
        [
            "demolition hammers",
            "bench grinders",
            "table saws",
            "miter saws",
            "tile cutters",
            "polishers",
            "concrete mixers",
            "air tools",
            "battery platforms",
            "dust extraction",
            "workshop lighting",
            "tool organizers",
            "torque tools",
            "inspection cameras",
            "engraving tools",
            "sharpening tools",
            "pumps used in workshop context",
            "heavy duty professional tool lines as generic families only",
            "drill drivers",
            "impact drills",
            "rotary hammers",
            "sds plus hammers",
            "sds max hammers",
            "impact drivers",
            "electric screwdrivers",
            "angle grinders",
            "die grinders",
            "circular saws",
            "track saws",
            "jigsaws",
            "reciprocating saws",
            "orbital sanders",
            "belt sanders",
            "detail sanders",
            "routers",
            "oscillating multi tools",
            "heat guns",
            "nailers and staplers",
            "air compressors",
            "spray guns",
            "dust extractors",
            "shop vacuums",
            "workshop fans",
            "workbench vises",
            "tool chests",
            "modular organizer cases",
            "laser distance tools for workshop layout",
            "digital angle gauges",
            "battery chargers",
            "multi-port chargers",
            "battery diagnostics",
            "cable reels for workshop power",
            "portable workshop pumps",
            "metal cutting saws",
            "wood cutting saws",
            "stone cutting systems",
            "workshop flood lights",
            "inspection endoscopes",
            "magnetic pickup tools",
            "torque screwdrivers",
        ]
    )
    product_families = _expand_product_families(
        base_items=[
            "demolition hammer platforms",
            "bench grinder product lines",
            "table saw systems",
            "miter saw systems",
            "tile cutter systems",
            "polisher systems",
            "concrete mixer product lines",
            "air impact wrench families",
            "air ratchet families",
            "battery platform families",
            "dust extractor lines",
            "workshop led lighting systems",
            "tool organizer modular lines",
            "digital torque tool families",
            "inspection camera lines",
            "engraving tool lines",
            "sharpening station lines",
            "workshop transfer pump lines",
            "drill driver lines",
            "impact drill lines",
            "rotary hammer lines",
            "angle grinder lines",
            "circular saw lines",
            "track saw lines",
            "jigsaw lines",
            "reciprocating saw lines",
            "orbital sander lines",
            "belt sander lines",
            "router systems",
            "oscillating multi tool lines",
            "heat gun lines",
            "nailer lines",
            "compressor lines",
            "spray gun lines",
            "shop vacuum lines",
            "portable flood light lines",
            "battery charger lines",
            "tool chest lines",
        ],
        variants=["compact", "mid-duty", "high-output", "heavy-duty", "trade-grade", "pro workshop"],
        contexts=["families", "ranges", "platforms", "systems", "ecosystems"],
        minimum=_MINIMUM_DEPTH["power_tools_workshop"]["product_families"],
    )
    spec_fields = [
        "power_source",
        "voltage",
        "wattage",
        "battery_platform",
        "battery_capacity_ah",
        "charger_output_amps",
        "motor_type",
        "brushless",
        "no_load_speed_rpm",
        "impact_rate_bpm",
        "torque_nm",
        "max_drilling_diameter_mm",
        "chuck_size_mm",
        "sds_type",
        "blade_diameter_mm",
        "max_cut_depth_mm",
        "bevel_angle_range",
        "disc_diameter_mm",
        "spindle_thread",
        "oscillation_angle",
        "air_consumption_cfm",
        "working_pressure_bar",
        "tank_capacity_l",
        "airflow_m3h",
        "dust_collection_efficiency",
        "noise_level_db",
        "vibration_level",
        "weight_kg",
        "ip_rating",
        "cable_length_m",
        "led_lumen_output",
        "runtime_minutes",
        "duty_cycle_percent",
        "mounting_interface",
    ]
    buying_priorities = [
        "battery_platform_compatibility",
        "power_to_weight_ratio",
        "continuous_duty_reliability",
        "precision_and_runout_control",
        "cut_quality_consistency",
        "vibration_control",
        "dust_management_capability",
        "noise_management",
        "serviceability_and_spare_parts",
        "ergonomics_for_long_shift_use",
        "workshop_space_efficiency",
        "tooling_accessory_ecosystem_depth",
        "safety_feature_set",
        "calibration_and_accuracy_controls",
        "torque_repeatability",
        "material_specific_performance",
        "setup_speed",
        "transport_and_storage_readiness",
        "professional_line_upgrade_path",
        "platform_longevity",
        "maintenance_interval_simplicity",
        "cost_of_consumables_over_time",
    ]
    alias_terms = _expand_alias_terms(
        seeds=[
            "power tools",
            "professional workshop tools",
            "εργαλεια ρευματος",
            "εργαλεια μπαταριας",
            "εργαστηριακα εργαλεια",
            "εργαλεια συνεργειου",
            "demolition hammer tools",
            "bench grinder systems",
            "table saw systems",
            "miter saw systems",
        ],
        departments=departments,
        subcategories=subcategories,
        universe_name="workshop",
        minimum=_MINIMUM_DEPTH["power_tools_workshop"]["alias_terms"],
    )
    greeklish_terms = _expand_greeklish(
        seeds=[
            "drapanokatsavido 18v",
            "kroustiko drapano",
            "sfyriodrapano sds",
            "goniakos troxos",
            "pagkos priono",
            "faltsopriono",
            "plakokoptis",
            "gialistri",
            "miksaris mpetou",
            "aerokleido",
            "systima mpatarias",
            "anarrofitis skonis",
            "fota ergastiriou",
            "organotes ergaleion",
            "ergaleio ropis",
            "kamera epitheorisis",
            "charaktiko ergaleio",
            "systima troxismatos",
            "antlia ergastiriou",
            "tool line epaggelmatiko",
        ],
        contexts=[
            "gia synergeio",
            "gia ergastirio",
            "gia anakainisi",
            "pro xrhsh",
            "me mpataria",
            "me kabel",
        ],
        minimum=_MINIMUM_DEPTH["power_tools_workshop"]["greeklish_terms"],
    )
    typo_terms = _generate_typo_candidates(
        base_terms=greeklish_terms,
        minimum=_MINIMUM_DEPTH["power_tools_workshop"]["typo_terms"],
    )
    intent_patterns = _expand_intents(
        seeds=[
            "thelo demolition hammers gia skliro mpeton",
            "psaxno bench grinders me stathero troxismo",
            "thelo table saws gia akrivi kopes xylou",
            "psaxno miter saws gia gyriakes kopes",
            "thelo tile cutters gia plakakia me kathari tomi",
            "psaxno polishers gia fainomeni epifaneia",
            "thelo concrete mixers gia ergotaksiakes xriseis",
            "psaxno air tools gia synergeio",
            "thelo battery platforms me koini mpataria",
            "psaxno dust extraction gia katharo workshop",
        ],
        product_terms=subcategories[:24],
        jobs=[
            "epaggelmatiki xrhsh",
            "anakainisi spitiou",
            "kopes xylou",
            "kopes metallou",
            "ergasies mpeton",
            "kathimerini xrhsh synergeiou",
            "ergasies akriveias",
            "taxeia allagi ergaleion",
            "xamilo thorivo",
            "xamili skoni",
        ],
        minimum=_MINIMUM_DEPTH["power_tools_workshop"]["intent_patterns"],
    )
    ambiguity_rules = [
        "treat drill driver queries as ambiguous until material and impact needs are clarified",
        "separate power screwdriver intent from hand screwdriver intent",
        "route grinder intent by disc size, use material, and safety class",
        "distinguish miter saw and table saw workflows by cut style and stock handling",
        "split demolition hammer and rotary hammer intents through impact energy cues",
        "separate workshop dust extraction from domestic vacuum cleaning intent",
        "route battery and charger requests first through platform compatibility",
        "treat air tool terms as compressor-dependent flows unless source already defined",
        "differentiate polishing from grinding intent when finish quality is mentioned",
        "separate inspection camera intent from security camera consumer intent",
        "disambiguate workshop pumps from garden irrigation and plumbing pumps",
        "keep heavy duty professional lines as generic family intent, never product-level offers",
    ]
    return {
        "mega_category_id": "power_tools_workshop",
        "engine_id": _ENGINE_ID,
        "display_name": "Power Tools / Workshop",
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
            "taxonomy output is classification metadata and not operating guidance",
            "this pack does not include real products, skus, prices, sellers, stores, or affiliate links",
            "equipment suitability must be verified by official manuals and certified procedures",
            "heavy-duty families remain generic taxonomy families only",
        ],
        "expansion_status": "stage_23b_deep_pack_depth_override_v2",
    }


def _build_hand_tools_record() -> dict:
    departments = [
        "manual fastening and torque tools",
        "wrenches and spanner systems",
        "pliers and gripping systems",
        "cutting and stripping hand tools",
        "soldering and electrical bench tools",
        "threading and rethreading systems",
        "drill bits and hole-making consumables",
        "abrasives and finishing consumables",
        "fixings and assembly consumables",
        "repair chemistry and lubricants",
        "measurement and layout instruments",
        "ppe and workwear accessories",
        "storage and organization for hand-tool workflows",
    ]
    subcategories = _dedupe(
        [
            "hex keys",
            "torx keys",
            "allen keys",
            "torque wrenches",
            "pipe wrenches",
            "adjustable wrenches",
            "crimping tools",
            "stripping tools",
            "soldering tools",
            "tap and die sets",
            "masonry drill bits",
            "metal drill bits",
            "wood drill bits",
            "hole saws",
            "router bits",
            "grinding wheels",
            "flap discs",
            "polishing pads",
            "staples",
            "rivets",
            "cable ties",
            "lubricants",
            "cleaning solvents",
            "threadlockers",
            "tapes",
            "ppe workwear accessories",
            "socket sets",
            "ratchets",
            "combination wrenches",
            "insulated screwdrivers",
            "precision screwdrivers",
            "locking pliers",
            "needle nose pliers",
            "cutting pliers",
            "bolt cutters",
            "utility knives",
            "chisels",
            "files",
            "hand saws",
            "hammers",
            "clamps",
            "bench vises",
            "measuring tapes",
            "laser meters",
            "spirit levels",
            "squares and angle rulers",
            "multimeters",
            "test pens",
            "calipers",
            "feeler gauges",
            "screw assortments",
            "anchors and wall plugs",
            "nails",
            "washers",
            "threaded rods",
            "silicone sealants",
            "epoxy putty",
            "anti-seize compounds",
            "contact cleaners",
            "safety glasses",
            "work gloves",
            "dust masks",
            "hearing protection accessories",
            "knee pads",
            "tool pouches",
            "bit organizer cases",
            "consumable refill kits",
        ]
    )
    product_families = _expand_product_families(
        base_items=[
            "hex key set families",
            "torx key set families",
            "allen key set families",
            "torque wrench families",
            "pipe wrench families",
            "adjustable wrench families",
            "crimping plier families",
            "wire stripping tool families",
            "soldering station families",
            "tap and die set families",
            "masonry drill bit ranges",
            "metal drill bit ranges",
            "wood drill bit ranges",
            "hole saw kit families",
            "router bit kit families",
            "grinding wheel pack families",
            "flap disc pack families",
            "polishing pad families",
            "staple refill families",
            "rivet assortment families",
            "cable tie assortment families",
            "threadlocker families",
            "cleaning solvent families",
            "lubricant families",
            "repair tape families",
            "ppe accessory families",
            "socket set lines",
            "ratchet lines",
            "screwdriver lines",
            "plier lines",
            "clamp lines",
            "measuring tool lines",
            "multimeter lines",
            "fastener lines",
            "adhesive lines",
            "safety eyewear lines",
            "work glove lines",
            "tool pouch lines",
            "organization box lines",
        ],
        variants=["compact", "field", "trade", "industrial", "premium", "precision", "heavy-duty"],
        contexts=["families", "ranges", "systems", "kits", "collections"],
        minimum=_MINIMUM_DEPTH["hand_tools_consumables_measuring"]["product_families"],
    )
    spec_fields = [
        "material_grade",
        "alloy_type",
        "hardness_hrc",
        "coating_type",
        "corrosion_resistance",
        "length_mm",
        "width_mm",
        "diameter_mm",
        "bit_profile",
        "drive_size",
        "torque_range_nm",
        "jaw_opening_mm",
        "cutting_capacity_mm",
        "insulation_rating_v",
        "temperature_resistance_c",
        "thread_standard",
        "thread_pitch",
        "grit_rating",
        "disc_diameter_mm",
        "max_rpm_rating",
        "abrasive_material",
        "pack_quantity",
        "adhesive_cure_time",
        "viscosity_class",
        "chemical_base",
        "flammability_class",
        "measurement_range",
        "measurement_accuracy",
        "ip_rating",
        "calibration_support",
        "ppe_standard_class",
        "size_system",
        "fit_range",
        "shelf_life_months",
    ]
    buying_priorities = [
        "task_specific_fit",
        "torque_repeatability",
        "dimensional_accuracy",
        "edge_retention",
        "consumable_lifespan",
        "restock_availability",
        "material_compatibility",
        "corrosion_resistance",
        "chemical_compatibility",
        "safe_handling_profile",
        "electrical_insulation_requirements",
        "organization_and_portability",
        "maintenance_simplicity",
        "multi_use_flexibility",
        "precision_under_repeated_use",
        "fastener_standard_coverage",
        "surface_finish_quality",
        "workflow_speed",
        "field_repair_readiness",
        "ppe_fit_and_comfort",
        "total_consumable_cost_over_time",
        "storage_stability",
    ]
    alias_terms = _expand_alias_terms(
        seeds=[
            "hand tools",
            "manual tools",
            "εργαλεια χειρος",
            "αναλωσιμα συνεργειου",
            "μετρητικα εργαλεια",
            "υλικα στερεωσης",
            "υλικα επισκευης",
            "εργαλεια ροπης",
            "σετ κατσαβιδια",
            "σετ καρυδακια",
            "drill bit consumables",
            "repair chemistry supplies",
        ],
        departments=departments,
        subcategories=subcategories,
        universe_name="repair",
        minimum=_MINIMUM_DEPTH["hand_tools_consumables_measuring"]["alias_terms"],
    )
    greeklish_terms = _expand_greeklish(
        seeds=[
            "hex kleidia",
            "torx kleidia",
            "allen kleidia",
            "kleidi ropis",
            "swylenokleido",
            "rythmizomeno kleidi",
            "ergaleio krimparismatos",
            "ergaleio gymnosis kalodiou",
            "kolitiri",
            "set kolafzou",
            "tripania mpetou",
            "tripania metallou",
            "tripania xylou",
            "potirotrypano",
            "router bits",
            "troxoi leiansis",
            "flap diskoi",
            "pad gyalismatos",
            "syrraptika",
            "piritsinia",
            "detime kalodion",
            "lipantika",
            "katharistika dialytika",
            "threadlocker",
            "tainies episkevis",
            "ppe aksesouar",
        ],
        contexts=[
            "gia synergeio",
            "gia ilektrologika",
            "gia ydravlika",
            "gia metal",
            "gia xyla",
            "gia geniki episkevi",
            "pro xrhsh",
        ],
        minimum=_MINIMUM_DEPTH["hand_tools_consumables_measuring"]["greeklish_terms"],
    )
    typo_terms = _generate_typo_candidates(
        base_terms=greeklish_terms,
        minimum=_MINIMUM_DEPTH["hand_tools_consumables_measuring"]["typo_terms"],
    )
    intent_patterns = _expand_intents(
        seeds=[
            "thelo hex keys kai torx keys se ena complete set",
            "psaxno allen keys gia synarmologisi epiplon",
            "thelo torque wrenches me akriveia",
            "psaxno pipe wrenches kai adjustable wrenches gia ydravlika",
            "thelo crimping tools kai stripping tools gia kalodiaseis",
            "psaxno soldering tools gia mikres episkeves",
            "thelo tap and die sets gia epanakopimeno nima",
            "psaxno masonry drill bits gia toyvlo kai mpeto",
            "thelo metal drill bits kai wood drill bits gia synergeio",
            "psaxno hole saws kai router bits gia xylourgia",
        ],
        product_terms=subcategories[:30],
        jobs=[
            "ilektrologikes ergasies",
            "ydravlikes epemvaseis",
            "xylourgia akriveias",
            "metalikes episkeves",
            "anakainisi spitiou",
            "synergeiaki xrhsh",
            "restock analosimon",
            "safe xrhsh me ppe",
            "syndyastiki agora ergaleiwn",
            "synarmologisi kai statheropoiisi",
        ],
        minimum=_MINIMUM_DEPTH["hand_tools_consumables_measuring"]["intent_patterns"],
    )
    ambiguity_rules = [
        "distinguish allen, hex, and torx key intent as separate fastener geometries",
        "treat torque wrench and ratchet intent separately unless torque target is explicit",
        "map stripping tool versus cutting plier intent through conductor and insulation cues",
        "route soldering tool intent by electronics soldering versus plumbing soldering context",
        "separate masonry drill bits from metal drill bits and wood drill bits by substrate",
        "map hole saw and router bit terms to different shaping workflows",
        "separate grinding wheels, flap discs, and polishing pads by finish stage",
        "pair staples and rivets with tool availability checks when fastening method is unclear",
        "route cleaning solvents and lubricants through material compatibility filters first",
        "distinguish threadlocker and sealant intent by thread engagement versus gap filling",
        "keep ppe workwear accessories in safety branch, not in core fastening branch",
    ]
    return {
        "mega_category_id": "hand_tools_consumables_measuring",
        "engine_id": _ENGINE_ID,
        "display_name": "Hand Tools / Consumables / Measuring",
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
            "taxonomy output is classification metadata and not operating guidance",
            "this pack does not include real products, skus, prices, sellers, stores, or affiliate links",
            "consumable compatibility and ppe compliance must be verified against official specifications",
            "repair chemistry terms do not imply structural or electrical certification",
        ],
        "expansion_status": "stage_23b_deep_pack_depth_override_v2",
    }


def _build_garden_record() -> dict:
    departments = [
        "robotic and powered lawn systems",
        "soil preparation and cultivation systems",
        "watering and irrigation control systems",
        "outdoor water transport and drainage systems",
        "outdoor power distribution and lighting systems",
        "patio cleaning and surface restoration systems",
        "roof and facade sealing systems",
        "tile and plaster repair systems",
        "plumbing repair and fitting systems",
        "electrical installation accessories for outdoor and repair workflows",
        "ladders and elevated access systems",
        "work platforms and safe support systems",
        "building envelope repair materials",
    ]
    subcategories = _dedupe(
        [
            "robotic lawn mowers",
            "tillers",
            "cultivators",
            "garden sprayers",
            "irrigation timers",
            "drip irrigation",
            "garden hoses and reels",
            "outdoor power cables",
            "outdoor lighting",
            "patio cleaning",
            "drainage accessories",
            "gutters",
            "sealants for roof/walls",
            "waterproofing membranes",
            "plaster repair",
            "tile adhesives",
            "grout",
            "wall fillers",
            "electrical boxes",
            "cable conduits",
            "switches/sockets installation accessories",
            "plumbing fittings",
            "valves",
            "siphons",
            "pipe insulation",
            "ladders by type",
            "step ladders",
            "telescopic ladders",
            "work platforms",
            "lawn mowers",
            "brush cutters",
            "hedge trimmers",
            "chainsaws",
            "leaf blowers",
            "garden pumps",
            "pressure washers",
            "surface scrubbers",
            "driveway cleaners",
            "roof coating systems",
            "exterior primers",
            "masonry repair mortars",
            "concrete crack fillers",
            "fence repair kits",
            "decking protectors",
            "outdoor extension reels",
            "junction boxes",
            "weatherproof connectors",
            "water timers",
            "sprinkler heads",
            "drip emitters",
            "hose connectors",
            "drain channels",
            "inspection drain caps",
            "pipe clips",
            "pipe sleeves",
            "pvc fittings",
            "brass fittings",
            "ball valves",
            "check valves",
            "bottle traps",
            "floor traps",
            "wall repair mesh",
            "render repair compounds",
            "tile leveling accessories",
            "spacers and wedges",
            "outdoor bollard lights",
            "garden wall lights",
            "portable work lights",
        ]
    )
    product_families = _expand_product_families(
        base_items=[
            "robotic lawn mower families",
            "tiller and cultivator families",
            "garden sprayer families",
            "irrigation timer families",
            "drip irrigation kit families",
            "garden hose and reel families",
            "outdoor power cable families",
            "outdoor lighting families",
            "patio cleaning system families",
            "drainage accessory families",
            "gutter maintenance families",
            "roof wall sealant families",
            "waterproofing membrane families",
            "plaster repair families",
            "tile adhesive families",
            "grout families",
            "wall filler families",
            "electrical box families",
            "cable conduit families",
            "switch socket install accessory families",
            "plumbing fitting families",
            "valve families",
            "siphon families",
            "pipe insulation families",
            "step ladder families",
            "telescopic ladder families",
            "work platform families",
            "garden pump families",
            "pressure washer families",
            "fence repair families",
            "decking treatment families",
            "outdoor connector families",
            "drain channel families",
            "weatherproof connector families",
            "masonry repair families",
            "concrete repair families",
            "render repair families",
            "tile leveling families",
            "outdoor extension reel families",
        ],
        variants=["compact", "home", "property", "trade", "heavy-duty", "weatherproof", "pro repair"],
        contexts=["families", "ranges", "systems", "kits", "lines"],
        minimum=_MINIMUM_DEPTH["garden_outdoor_repair_building"]["product_families"],
    )
    spec_fields = [
        "power_source",
        "battery_platform",
        "runtime_minutes",
        "coverage_area_m2",
        "cutting_width_cm",
        "cutting_height_range_mm",
        "tilling_depth_cm",
        "tank_capacity_l",
        "spray_pressure_bar",
        "hose_length_m",
        "water_flow_lh",
        "timer_program_count",
        "ip_rating",
        "cable_cross_section",
        "cable_length_m",
        "lumen_output",
        "color_temperature_k",
        "beam_angle",
        "max_working_pressure_bar",
        "surface_material_compatibility",
        "uv_resistance",
        "waterproof_class",
        "temperature_range_c",
        "cure_time_hours",
        "open_time_minutes",
        "adhesion_class",
        "joint_width_mm",
        "fitting_standard",
        "pipe_diameter_mm",
        "valve_type",
        "ladder_height_m",
        "load_capacity_kg",
        "platform_width_cm",
        "slip_resistance_class",
    ]
    buying_priorities = [
        "property_size_fit",
        "seasonal_workload_alignment",
        "water_efficiency",
        "runtime_and_recharge_cycle",
        "weather_resilience",
        "surface_compatibility",
        "installation_simplicity",
        "serviceability",
        "replacement_parts_availability",
        "repair_speed",
        "finish_quality",
        "long_term_maintenance_effort",
        "drainage_reliability",
        "electrical_safety_compatibility",
        "plumbing_standard_compatibility",
        "waterproofing_lifecycle",
        "load_safety_for_access_equipment",
        "storage_and_transport",
        "noise_profile",
        "workflow_completeness_for_outdoor_repairs",
        "multi-project_flexibility",
        "total_cost_of_ownership",
    ]
    alias_terms = _expand_alias_terms(
        seeds=[
            "garden tools",
            "outdoor repair tools",
            "building repair supplies",
            "εργαλεια κηπου",
            "υλικα επισκευης εξωτερικου χωρου",
            "δομικα υλικα επισκευης",
            "υδραυλικα και ηλεκτρολογικα υλικα",
            "robotic lawn systems",
            "irrigation and drainage",
            "ladder and access systems",
            "roof and wall sealing systems",
            "tile and plaster repair kits",
        ],
        departments=departments,
        subcategories=subcategories,
        universe_name="outdoor",
        minimum=_MINIMUM_DEPTH["garden_outdoor_repair_building"]["alias_terms"],
    )
    greeklish_terms = _expand_greeklish(
        seeds=[
            "robotiko xlookoptiko",
            "freza kipou",
            "kalliergitis xomatos",
            "psekastiras kipou",
            "xronodiakoptis potismatos",
            "drip potisma",
            "solinas kai anemela",
            "kalodio exoterikou xorou",
            "fotismos exoterikou",
            "katharismos patio",
            "aksesouar aporrois",
            "ylika ydroorofis",
            "steganotiko stegis",
            "memvrani monosis",
            "episkevi sovada",
            "kolla plakidion",
            "armos plakidion",
            "stokos toixou",
            "ilektrologiko kouti",
            "kanali kalodion",
            "aksesouar diakopton prizwn",
            "ydravlika exartimata",
            "valvida",
            "sifoni",
            "monosi solina",
            "skala typou",
            "skala diplomeni",
            "tilekopiki skala",
            "platforma ergasias",
        ],
        contexts=[
            "gia avli",
            "gia kipou",
            "gia exoterikes episkeves",
            "gia ydravlika",
            "gia ilektrologika",
            "gia domikes ergasies",
            "pro xrhsh",
        ],
        minimum=_MINIMUM_DEPTH["garden_outdoor_repair_building"]["greeklish_terms"],
    )
    typo_terms = _generate_typo_candidates(
        base_terms=greeklish_terms,
        minimum=_MINIMUM_DEPTH["garden_outdoor_repair_building"]["typo_terms"],
    )
    intent_patterns = _expand_intents(
        seeds=[
            "thelo robotic lawn mowers gia megali avli",
            "psaxno tillers kai cultivators gia xoma me petres",
            "thelo garden sprayers kai irrigation timers gia oikonomiko potisma",
            "psaxno drip irrigation me hoses kai reels",
            "thelo outdoor power cables kai outdoor lighting gia kipou",
            "psaxno patio cleaning me pressure systems",
            "thelo drainage accessories kai gutters gia vroxes",
            "psaxno sealants for roof/walls kai waterproofing membranes",
            "thelo plaster repair tile adhesives grout kai wall fillers",
            "psaxno electrical boxes cable conduits kai switches/sockets installation accessories",
        ],
        product_terms=subcategories[:30],
        jobs=[
            "episkevi exoterikou xorou",
            "diatirisi kipou",
            "anakainisi patios",
            "domiki prostasia apo ygrasia",
            "ydravlikes epemvaseis",
            "ilektrologiki egkatastasi exoterikou",
            "safe prosvasi se ypsos",
            "taxeia episkevi toixon",
            "tile finishing ergasia",
            "syndyastiki agora gia olokliro project",
        ],
        minimum=_MINIMUM_DEPTH["garden_outdoor_repair_building"]["intent_patterns"],
    )
    ambiguity_rules = [
        "separate robotic lawn mowers from ride-on and manual mowing intents",
        "split tiller and cultivator intent by depth and soil-prep objective",
        "route garden sprayer terms by liquid type and pressure requirement",
        "differentiate irrigation timers from generic smart home timers",
        "disambiguate drip irrigation components from plumbing indoor fittings",
        "separate outdoor power cables from indoor extension cable requests",
        "split patio cleaning from indoor floor-cleaning intent families",
        "route roof wall sealants by substrate and weather exposure level",
        "differentiate tile adhesive, grout, and wall filler by repair stage",
        "separate electrical boxes and cable conduits by installation context and protection class",
        "route plumbing fittings, valves, and siphons through pipe standard compatibility",
        "differentiate ladders by type, step ladders, telescopic ladders, and work platforms by load and reach",
    ]
    return {
        "mega_category_id": "garden_outdoor_repair_building",
        "engine_id": _ENGINE_ID,
        "display_name": "Garden / Outdoor / Repair / Building",
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
            "taxonomy output is classification metadata and not installation guidance",
            "this pack does not include real products, skus, prices, sellers, stores, or affiliate links",
            "structural, electrical, and plumbing suitability must follow certified standards and official manuals",
            "waterproofing and repair chemistry outcomes depend on substrate and certified application procedures",
        ],
        "expansion_status": "stage_23b_deep_pack_depth_override_v2",
    }


_TOOLS_DIY_GARDEN_REPAIR_PACK = {
    "engine_id": _ENGINE_ID,
    "schema_version": _SCHEMA_VERSION,
    "source": _SOURCE,
    "mega_categories": [
        _build_power_tools_record(),
        _build_hand_tools_record(),
        _build_garden_record(),
    ],
}


def get_tools_diy_garden_repair_pack() -> dict:
    """Return the deterministic deep taxonomy expansion pack."""
    return deepcopy(_TOOLS_DIY_GARDEN_REPAIR_PACK)


def get_tools_diy_mega_category_pack(mega_category_id: str) -> dict | None:
    """Return one deep-pack mega-category record by identifier."""
    for record in _TOOLS_DIY_GARDEN_REPAIR_PACK["mega_categories"]:
        if record["mega_category_id"] == mega_category_id:
            return deepcopy(record)
    return None


def summarize_tools_diy_garden_repair_pack() -> dict:
    """Return deterministic aggregate depth counts for the pack."""
    pack = get_tools_diy_garden_repair_pack()
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


def validate_tools_diy_garden_repair_pack() -> dict:
    """Validate deterministic shape, depth, and safety constraints for the deep pack."""
    pack = get_tools_diy_garden_repair_pack()
    summary = summarize_tools_diy_garden_repair_pack()
    mega_categories = pack["mega_categories"]
    mega_ids = [record["mega_category_id"] for record in mega_categories]
    expected_mega_ids = [
        "power_tools_workshop",
        "hand_tools_consumables_measuring",
        "garden_outdoor_repair_building",
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
        and result["taxonomy_expansion_only"]
        and result["not_product_inventory"]
        and result["no_claude_or_api_or_live_llm_required"]
        and result["no_app_router_or_decision_machine_dependency_required"]
        and result["no_local_nlu_runtime_change_required"]
    )
    result["passed"] = result["valid"]
    return result
