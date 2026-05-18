from __future__ import annotations

"""Offline English retail canonical product-intent vocabulary coverage.

Clean canonical terms only — no typo probes, no provider or commercial fields.
Merged into the offline canonical registry by ``canonical_registry``.
"""

_SCHEMA_VERSION = "1.0.0"
_SOURCE = "offline_canonical_vocabulary_coverage"
_SOURCE_FILE = "canonical_vocabulary_coverage.py"
_SOURCE_PATH = "src/picwise_search_memory/canonical_vocabulary_coverage.py"
_LANGUAGE = "english"
_STATUS = "offline_source_only"

# At least 10 product-intent terms per retail mega category (18 categories).
_COVERAGE_BY_MEGA_CATEGORY: dict[str, tuple[str, ...]] = {
    "home_appliances_laundry_climate": (
        "vacuum cleaner",
        "washing machine",
        "tumble dryer",
        "air conditioner",
        "dehumidifier",
        "chest freezer",
        "heat pump unit",
        "radiator heater",
        "dishwasher",
        "laundry basket",
        "clothes iron",
    ),
    "kitchen_cooking_household": (
        "coffee grinder",
        "electric kettle",
        "toaster oven",
        "rice cooker",
        "food processor",
        "cutting board",
        "frying pan",
        "kitchen knife set",
        "dish rack",
        "spice grinder",
        "mixing bowl set",
    ),
    "furniture_living_storage_smart_home": (
        "bookshelf unit",
        "sofa bed",
        "dining table",
        "wardrobe closet",
        "mattress topper",
        "smart thermostat",
        "motion sensor light",
        "storage ottoman",
        "desk lamp",
        "curtain rod",
        "wall shelf bracket",
    ),
    "phones_mobile_accessories": (
        "usb cable",
        "phone case",
        "screen protector",
        "wireless charger",
        "power bank",
        "car mount holder",
        "sim card adapter",
        "phone stand",
        "mobile gimbal",
        "tempered glass protector",
        "earbud tips pack",
    ),
    "computers_office_peripherals": (
        "gaming mouse",
        "mechanical keyboard",
        "usb hub",
        "monitor arm",
        "laptop stand",
        "webcam cover",
        "ethernet adapter",
        "graphics tablet",
        "ergonomic chair mat",
        "docking station",
        "external hard drive enclosure",
    ),
    "audio_video_gaming_cameras": (
        "bluetooth speaker",
        "noise cancelling headphones",
        "gaming headset",
        "soundbar subwoofer",
        "action camera",
        "mirrorless camera lens",
        "hdmi cable",
        "microphone arm",
        "portable projector",
        "turntable needle",
        "streaming capture card",
    ),
    "car_parts_service_maintenance": (
        "car battery",
        "brake pads set",
        "engine oil filter",
        "windshield wipers",
        "spark plugs kit",
        "cabin air filter",
        "headlight bulb",
        "coolant antifreeze",
        "serpentine belt",
        "oil drain pan",
        "jack stand pair",
    ),
    "tyres_wheels_car_accessories": (
        "summer tyres set",
        "winter tyres set",
        "alloy wheels",
        "wheel nuts kit",
        "tyre pressure gauge",
        "car floor mats",
        "roof cargo box",
        "seat covers set",
        "jump starter pack",
        "tyre repair kit",
        "wheel alignment tool",
    ),
    "moto_bicycle_mobility_gear": (
        "bike helmet",
        "cycling gloves",
        "bicycle pump",
        "bike lock chain",
        "scooter helmet",
        "motorcycle jacket",
        "bicycle lights set",
        "pedal wrench tool",
        "cycling jersey",
        "bike rack carrier",
        "kick scooter deck",
    ),
    "power_tools_workshop": (
        "cordless drill",
        "circular saw",
        "impact driver",
        "angle grinder",
        "bench grinder",
        "workbench vice",
        "orbital sander",
        "jigsaw blades pack",
        "tool storage cabinet",
        "dust extractor",
        "router bit set",
    ),
    "hand_tools_consumables_measuring": (
        "screwdriver set",
        "claw hammer",
        "tape measure",
        "spirit level",
        "adjustable wrench",
        "pliers set",
        "sandpaper sheets",
        "wall anchors pack",
        "safety goggles",
        "utility knife",
        "hex key set",
    ),
    "garden_outdoor_repair_building": (
        "lawn mower",
        "garden hose",
        "pruning shears",
        "leaf blower",
        "patio furniture set",
        "outdoor grill",
        "pressure washer",
        "wheelbarrow",
        "fence panels",
        "plant pots set",
        "garden trowel",
    ),
    "health_wellness_safety_devices": (
        "blood pressure monitor",
        "pulse oximeter",
        "digital thermometer",
        "first aid kit",
        "knee support brace",
        "massage gun",
        "bedroom humidifier",
        "air purifier filter",
        "walking stick",
        "hearing aid batteries",
        "compression socks pair",
    ),
    "beauty_grooming_personal_care": (
        "electric toothbrush",
        "hair dryer",
        "beard trimmer",
        "face moisturizer",
        "shampoo bottle",
        "nail clipper set",
        "makeup mirror",
        "sunscreen lotion",
        "hair straightener",
        "body wash",
        "facial cleansing brush",
    ),
    "baby_kids_pets_sports_outdoor": (
        "baby car seat",
        "stroller pushchair",
        "baby monitor",
        "pet food bowl",
        "dog leash harness",
        "football ball",
        "camping tent",
        "hiking backpack",
        "kids scooter",
        "yoga mat",
        "tennis racket",
    ),
    "clothing_apparel_workwear": (
        "winter jacket",
        "rain coat",
        "denim jeans",
        "cotton t shirt",
        "hooded sweatshirt",
        "work safety vest",
        "thermal underwear set",
        "dress shirt",
        "running shorts",
        "wool sweater",
        "cargo work pants",
    ),
    "footwear_shoes_sneakers_boots": (
        "running sneakers",
        "hiking boots",
        "leather dress shoes",
        "sandals flip flops",
        "walking shoes",
        "steel toe boots",
        "kids school shoes",
        "slip on loafers",
        "waterproof wellies",
        "sports cleats",
        "trail running shoes",
    ),
    "jewelry_watches_bags_fashion_accessories": (
        "wrist watch",
        "leather belt",
        "sunglasses case",
        "crossbody bag",
        "travel backpack",
        "pearl earrings",
        "silver necklace",
        "wallet card holder",
        "wool scarf",
        "baseball cap",
        "watch strap band",
    ),
}

_REQUIRED_ANCHOR_TERMS: tuple[tuple[str, str], ...] = (
    ("coffee grinder", "kitchen_cooking_household"),
    ("vacuum cleaner", "home_appliances_laundry_climate"),
    ("bluetooth speaker", "audio_video_gaming_cameras"),
    ("gaming mouse", "computers_office_peripherals"),
    ("car battery", "car_parts_service_maintenance"),
    ("bike helmet", "moto_bicycle_mobility_gear"),
    ("winter jacket", "clothing_apparel_workwear"),
    ("baby car seat", "baby_kids_pets_sports_outdoor"),
    ("usb cable", "phones_mobile_accessories"),
)


def coverage_metadata() -> dict[str, str]:
    return {
        "source": _SOURCE,
        "source_file": _SOURCE_FILE,
        "source_path": _SOURCE_PATH,
        "language": _LANGUAGE,
        "status": _STATUS,
        "schema_version": _SCHEMA_VERSION,
    }


def load_offline_canonical_coverage_by_mega_category() -> dict[str, set[str]]:
    vocab: dict[str, set[str]] = {}
    for mega_category_id in sorted(_COVERAGE_BY_MEGA_CATEGORY.keys()):
        terms = _COVERAGE_BY_MEGA_CATEGORY[mega_category_id]
        bucket = vocab.setdefault(mega_category_id, set())
        for term in terms:
            normalized = " ".join(term.split()).strip().lower()
            if not normalized:
                continue
            bucket.add(normalized)
    return vocab


def required_anchor_terms() -> tuple[tuple[str, str], ...]:
    return _REQUIRED_ANCHOR_TERMS
