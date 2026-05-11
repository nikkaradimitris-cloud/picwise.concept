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

_STAGE_TITLE = "Stage 26C — Tech / Electronics / Office Deep Pack"
_STAGE_CODE = "stage_26c"
_ENGINE_ID = "tech_electronics_office_engine"
_SCHEMA_VERSION = "1.0.0"
_SOURCE = "phase_c_stage_26c_tech_electronics_office"
_EXPECTED_MEGA_CATEGORIES = [
    "phones_mobile_accessories",
    "computers_office_peripherals",
    "audio_video_gaming_cameras",
]
_MINIMUM_TOTALS = {
    "departments": 3,
    "subcategories": 9,
    "product_families": 30,
    "aliases": 40,
    "spec_fields": 15,
    "intent_patterns": 15,
}


def _phones_mobile_record() -> dict:
    departments = [
        "κινητά και mobile ecosystem",
        "φορτιστές καλώδια και power banks",
        "mobile protection and accessories",
        "connected daily communication devices",
    ]
    subcategories = [
        "κινητά",
        "smartphones",
        "power banks",
        "φορτιστές",
        "καλώδια",
        "wireless chargers",
        "phone cases",
        "screen protection",
        "car mobile mounts",
        "mobile audio companions",
        "portable hotspots",
        "mobile travel charging kits",
    ]
    product_families = expand_product_families(
        base=[
            "smartphone family lines",
            "power bank family lines",
            "fast charger family lines",
            "cable family lines",
            "wireless charger family lines",
            "case family lines",
            "screen guard family lines",
            "mount family lines",
            "hotspot family lines",
            "travel charging family lines",
        ],
        variants=["entry", "daily", "travel", "fast-charge"],
        contexts=["taxonomy families", "compatibility sets", "usage sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "κινητό",
            "κινητά τηλέφωνα",
            "mobile phones",
            "power bank",
            "φορτιστής κινητού",
            "καλώδιο φόρτισης",
            "mobile accessories",
            "portable charging ecosystem",
            "phone protection essentials",
            "mobile daily setup taxonomy",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "kinito",
            "smartphone",
            "power bank",
            "fortistis kinhtou",
            "kalodio fortisis",
            "wireless fortisi",
            "thiki kinhtou",
            "prostateytiko othonis",
            "base kinhtou autokinito",
            "travel charging kit",
        ],
        contexts=["gia kathimerini xrhsh", "gia taxidi", "fast charging"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "display_size_inches",
        "chipset_generation",
        "ram_gb",
        "storage_gb",
        "battery_capacity_mah",
        "charging_protocol_support",
        "fast_charge_watts",
        "wireless_charging_support",
        "port_type",
        "cable_length_m",
        "durability_profile",
        "ip_rating",
        "compatibility_scope",
        "travel_readiness_profile",
        "ecosystem_integration_level",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo κινητά me dynati mpataria",
            "psaxno power banks gia taxidia",
            "thelo φορτιστές me fast charging",
            "psaxno καλώδια me andoxi",
            "thelo mobile setup me thiki kai protectors",
        ],
        targets=subcategories,
        situations=[
            "daily heavy use",
            "travel mobility",
            "quick charging workflow",
            "device protection",
            "multi-device compatibility",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="phones_mobile_accessories",
        display_name="Phones / Mobile / Accessories",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "battery_life",
            "charging_speed",
            "compatibility_confidence",
            "portability_and_travel_use",
            "device_protection",
            "ecosystem_fit",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate charger intent for phones from laptop-only charger intent",
            "route cable requests by connector standard before generic commercial wording",
            "disambiguate power bank from stationary backup power station intent",
        ],
        source_references=[
            "engine_registry:tech_electronics_office_engine",
            "mega_category_registry:phones_mobile_accessories",
            "coverage_plan:phones_mobile_accessories",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _computers_office_record() -> dict:
    departments = [
        "laptops and desktop productivity",
        "monitors printers and office tech",
        "routers and network office setup",
        "peripherals and workstation accessories",
    ]
    subcategories = [
        "laptops",
        "desktop pcs",
        "monitors",
        "printers",
        "routers",
        "office docks and hubs",
        "keyboards",
        "mice and pointing devices",
        "webcams and conferencing tools",
        "office calculators and utility tech",
        "scanner and document systems",
        "workstation ergonomics peripherals",
    ]
    product_families = expand_product_families(
        base=[
            "laptop family lines",
            "desktop family lines",
            "monitor family lines",
            "printer family lines",
            "router family lines",
            "dock family lines",
            "keyboard family lines",
            "mouse family lines",
            "webcam family lines",
            "scanner family lines",
        ],
        variants=["entry", "office", "pro", "hybrid-work"],
        contexts=["taxonomy families", "workflow sets", "compatibility sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "laptops",
            "γραφείο τεχνολογία",
            "office tech",
            "monitors και printers",
            "routers office use",
            "computer peripherals",
            "workstation setup",
            "hybrid office devices",
            "productivity hardware taxonomy",
            "remote-work tech setup",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "laptop",
            "desktop pc",
            "monitor",
            "printer",
            "router",
            "dock station",
            "pliktrologio",
            "pontiki",
            "webcam",
            "scanner eggrafon",
        ],
        contexts=["gia grafeio", "gia work from home", "daily productivity"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "cpu_class",
        "memory_gb",
        "storage_type",
        "screen_resolution",
        "refresh_rate_hz",
        "print_speed_ppm",
        "duplex_support",
        "wireless_standard",
        "port_selection",
        "keyboard_layout",
        "mouse_sensor_type",
        "camera_resolution_profile",
        "network_coverage_profile",
        "desk_compatibility_profile",
        "expandability_level",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo laptops gia hybrid office",
            "psaxno monitors kai keyboards gia workstation",
            "thelo printers me grigoro output",
            "psaxno routers gia stathero office diktyo",
            "thelo office setup me peripherals complete",
        ],
        targets=subcategories,
        situations=[
            "work from home",
            "daily admin workload",
            "multi-device office setup",
            "stable networking needs",
            "document-heavy workflow",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="computers_office_peripherals",
        display_name="Computers / Office / Peripherals",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "productivity_performance",
            "connectivity_flexibility",
            "workflow_reliability",
            "ergonomics",
            "serviceability",
            "expandability",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate printer intent from scanner-only requirement",
            "route monitor queries by productivity vs gaming use context",
            "disambiguate office router setup from home smart hub intent",
        ],
        source_references=[
            "engine_registry:tech_electronics_office_engine",
            "mega_category_registry:computers_office_peripherals",
            "coverage_plan:computers_office_peripherals",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


def _av_gaming_camera_record() -> dict:
    departments = [
        "TV and home video",
        "audio and listening systems",
        "gaming hardware and accessories",
        "cameras and content capture",
    ]
    subcategories = [
        "TV",
        "audio speakers",
        "soundbars",
        "gaming consoles",
        "gaming accessories",
        "cameras",
        "mirrorless cameras",
        "action cameras",
        "streaming microphones",
        "capture cards",
        "creator lighting kits",
        "home cinema receivers",
    ]
    product_families = expand_product_families(
        base=[
            "tv family lines",
            "speaker family lines",
            "soundbar family lines",
            "gaming console family lines",
            "gaming accessory family lines",
            "camera family lines",
            "mirrorless family lines",
            "action camera family lines",
            "streaming microphone family lines",
            "capture card family lines",
        ],
        variants=["entry", "media", "creator", "performance"],
        contexts=["taxonomy families", "setup sets", "workflow sets"],
        minimum=30,
    )
    aliases = expand_aliases(
        seed_terms=[
            "TV",
            "audio systems",
            "gaming setup",
            "camera gear",
            "creator hardware",
            "home cinema",
            "video and audio ecosystem",
            "content capture accessories",
            "media entertainment taxonomy",
            "streaming setup essentials",
        ],
        departments=departments,
        subcategories=subcategories,
        minimum=45,
    )
    greeklish = expand_greeklish(
        seeds=[
            "tileorasi",
            "ixeia",
            "soundbar",
            "gaming console",
            "gaming accessories",
            "kamera",
            "mirrorless",
            "action camera",
            "mikrofono streaming",
            "capture card",
        ],
        contexts=["gia spiti", "gaming setup", "creator workflow"],
        minimum=22,
    )
    typos = typo_variants(greeklish, minimum=20)
    spec_fields = [
        "display_resolution",
        "panel_technology",
        "refresh_rate_hz",
        "audio_channel_profile",
        "wireless_audio_support",
        "latency_profile_ms",
        "camera_sensor_class",
        "video_recording_profile",
        "stabilization_support",
        "mount_type_profile",
        "capture_interface_standard",
        "streaming_workflow_support",
        "room_coverage_profile",
        "creator_portability_profile",
        "ecosystem_compatibility",
    ]
    intent_patterns = expand_intents(
        seeds=[
            "thelo TV kai audio gia saloni",
            "psaxno gaming setup me accessories",
            "thelo cameras gia content creation",
            "psaxno capture cards kai mikrofono streaming",
            "thelo home cinema setup me soundbar",
        ],
        targets=subcategories,
        situations=[
            "living-room entertainment",
            "low-latency gaming",
            "video creation workflow",
            "live streaming setup",
            "hybrid media usage",
        ],
        minimum=20,
    )
    return make_record(
        mega_category_id="audio_video_gaming_cameras",
        display_name="Audio / Video / Gaming / Cameras",
        engine_id=_ENGINE_ID,
        departments=departments,
        subcategories=subcategories,
        product_families=product_families,
        spec_fields=spec_fields,
        buying_priorities=[
            "media_quality",
            "latency_responsiveness",
            "creator_workflow_fit",
            "compatibility_across_devices",
            "setup_simplicity",
            "long_term_upgrade_path",
        ],
        aliases=aliases,
        greeklish=greeklish,
        typos=typos,
        intent_patterns=intent_patterns,
        ambiguity_rules=[
            "separate tv viewing intent from monitor productivity intent",
            "route creator camera terms away from security camera contexts",
            "disambiguate gaming accessory requests by console vs pc setup cues",
        ],
        source_references=[
            "engine_registry:tech_electronics_office_engine",
            "mega_category_registry:audio_video_gaming_cameras",
            "coverage_plan:audio_video_gaming_cameras",
            "mapping:google_stage24d + gap_report_stage24e",
            "canonical:registry_builder + deduplication",
        ],
        stage_code=_STAGE_CODE,
    )


_TECH_ELECTRONICS_OFFICE_PACK = {
    "stage_title": _STAGE_TITLE,
    "engine_id": _ENGINE_ID,
    "schema_version": _SCHEMA_VERSION,
    "source": _SOURCE,
    "mega_categories": [
        _phones_mobile_record(),
        _computers_office_record(),
        _av_gaming_camera_record(),
    ],
}


def get_tech_electronics_office_pack() -> dict:
    return deep_copy_pack(_TECH_ELECTRONICS_OFFICE_PACK)


def get_tech_electronics_office_mega_category_pack(mega_category_id: str) -> dict | None:
    for record in _TECH_ELECTRONICS_OFFICE_PACK["mega_categories"]:
        if record["mega_category_id"] == mega_category_id:
            return deep_copy_pack(record)
    return None


def summarize_tech_electronics_office_pack() -> dict:
    summary = summarize_pack(get_tech_electronics_office_pack())
    validation = validate_tech_electronics_office_pack()
    summary["validation_summary"] = {
        "valid": validation["valid"],
        "stage_title_exact": validation["stage_title_exact"],
        "engine_id_exact": validation["engine_id_exact"],
        "all_mega_categories_mapped_to_engine": validation["all_mega_categories_mapped_to_engine"],
    }
    return summary


def validate_tech_electronics_office_pack() -> dict:
    return validate_pack(
        pack=get_tech_electronics_office_pack(),
        expected_stage_title=_STAGE_TITLE,
        expected_engine_id=_ENGINE_ID,
        expected_mega_category_ids=_EXPECTED_MEGA_CATEGORIES,
        minimum_totals=_MINIMUM_TOTALS,
    )
