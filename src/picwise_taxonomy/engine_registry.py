from __future__ import annotations

from copy import deepcopy

_SCHEMA_VERSION = "1.0.0"
_SOURCE = "stage_22b_taxonomy_lock"
_STATUS = "active"

_ENGINE_REGISTRY = [
    {
        "engine_id": "home_living_appliances_engine",
        "display_name": "Home / Living / Appliances",
        "description": "Large home decision universe spanning appliances, kitchen, furniture, and connected living.",
        "mega_category_ids": [
            "home_appliances_laundry_climate",
            "kitchen_cooking_household",
            "furniture_living_storage_smart_home",
        ],
        "status": _STATUS,
        "source": _SOURCE,
        "schema_version": _SCHEMA_VERSION,
    },
    {
        "engine_id": "tech_electronics_office_engine",
        "display_name": "Tech / Electronics / Office",
        "description": "Broad technology universe covering mobile, computing, office equipment, and media hardware.",
        "mega_category_ids": [
            "phones_mobile_accessories",
            "computers_office_peripherals",
            "audio_video_gaming_cameras",
        ],
        "status": _STATUS,
        "source": _SOURCE,
        "schema_version": _SCHEMA_VERSION,
    },
    {
        "engine_id": "auto_moto_mobility_engine",
        "display_name": "Auto / Moto / Mobility",
        "description": "Transportation ecosystem for cars, motorcycles, bikes, and mobility ownership needs.",
        "mega_category_ids": [
            "car_parts_service_maintenance",
            "tyres_wheels_car_accessories",
            "moto_bicycle_mobility_gear",
        ],
        "status": _STATUS,
        "source": _SOURCE,
        "schema_version": _SCHEMA_VERSION,
    },
    {
        "engine_id": "tools_diy_garden_repair_engine",
        "display_name": "Tools / DIY / Garden / Repair",
        "description": "Workshop and property-care universe for building, fixing, and maintenance tasks.",
        "mega_category_ids": [
            "power_tools_workshop",
            "hand_tools_consumables_measuring",
            "garden_outdoor_repair_building",
        ],
        "status": _STATUS,
        "source": _SOURCE,
        "schema_version": _SCHEMA_VERSION,
    },
    {
        "engine_id": "health_beauty_family_lifestyle_engine",
        "display_name": "Health / Beauty / Family / Lifestyle",
        "description": "Personal wellbeing and household lifestyle universe across health, care, and family life.",
        "mega_category_ids": [
            "health_wellness_safety_devices",
            "beauty_grooming_personal_care",
            "baby_kids_pets_sports_outdoor",
        ],
        "status": _STATUS,
        "source": _SOURCE,
        "schema_version": _SCHEMA_VERSION,
    },
    {
        "engine_id": "fashion_footwear_jewelry_accessories_engine",
        "display_name": "Fashion / Footwear / Jewelry / Accessories",
        "description": "Dedicated style universe for apparel, shoes, jewelry, watches, bags, and accessories.",
        "mega_category_ids": [
            "clothing_apparel_workwear",
            "footwear_shoes_sneakers_boots",
            "jewelry_watches_bags_fashion_accessories",
        ],
        "status": _STATUS,
        "source": _SOURCE,
        "schema_version": _SCHEMA_VERSION,
    },
]


def get_engine_registry() -> list[dict]:
    """Return a deep-copied deterministic search-engine registry."""
    return deepcopy(_ENGINE_REGISTRY)
