from __future__ import annotations

import re
from typing import Any

_POWER_BANK_KEYWORDS = {
    "power bank",
    "powerbank",
    "battery pack",
    "portable charger",
    "φορητος φορτιστης",
    "φορητοσ φορτιστησ",
    "εξωτερικη μπαταρια",
    "μπαταρια κινητου",
    "φορτιστης χωρις πριζα",
    "externe batterie",
    "externe baterie",
    "tragbares ladegerat",
    "handy akku",
    "handyakku",
    "akku pack",
    "akku pak",
}
_TIRE_SIZE_PATTERN = re.compile(r"(?<!\d)(\d{3})/(\d{2})\s*[Rr](\d{2})(?!\d)")
_TIRE_SIZE_SPACED_PATTERN = re.compile(r"(?<!\d)(\d{3})\s+(\d{2})\s+(\d{2})(?!\d)")
_TYRE_KEYWORDS = {
    "lastixa",
    "λαστιχα",
    "tyres",
    "tires",
    "tyre",
    "tire",
}
_TYRE_STRONG_TERMS = {
    "goodyear",
    "bridgestone",
    "michelin",
    "continental",
    "efficientgrip",
    "turanza",
}
_CALCULATOR_KEYWORDS = {
    "κομπιουτερακι",
    "κομπιουτερακια",
    "calculator",
}
_CALCULATOR_CONTEXT_KEYWORDS = {
    "calculator",
    "κομπιουτερακι",
    "κομπιουτερακια",
    "exam",
    "exams",
    "πανελληνιες",
    "εξετασεις",
    "σχολειο",
    "casio",
    "fx 991",
}
_CHARGER_KEYWORDS = {
    "charger",
    "φορτιστης",
    "fortistis",
    "usb c",
    "usb-c",
    "usbc",
}
_NON_RETAIL_VERTICAL_TERMS = {
    "saas",
    "erp",
    "crm",
    "accounting software",
    "bookkeeping software",
    "banking",
    "bank account",
    "loan",
    "loans",
    "credit card",
    "credit cards",
    "insurance",
    "mortgage",
}
_OVERMATCH_SINGLE_TOKEN_GUARDS = {
    "bank",
    "charger",
    "apple",
    "galaxy",
    "bosch",
    "nike",
}
_CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "home_appliances_laundry_climate": (
        "washing machine",
        "washng machine",
        "washingmachne",
        "washng machine",
        "tumble dryer",
        "air conditioner",
        "airconditioner",
        "air conditoner",
        "dehumidifier",
        "vacuum cleaner",
    ),
    "kitchen_cooking_household": (
        "air fryer",
        "airfryer",
        "air frayer",
        "blender",
        "blnder",
        "toaster",
        "microwave oven",
        "coffee maker",
        "cofee maker",
        "electric kettle",
    ),
    "furniture_living_storage_smart_home": (
        "office chair",
        "officechair",
        "ofice chair",
        "ergonomic chair",
        "storage cabinet",
        "storage cabnet",
        "bookshelf",
        "wardrobe",
        "smart bulb",
        "smart plug",
    ),
    "phones_mobile_accessories": (
        "phone case",
        "phonecase",
        "screen protector",
        "screen protecter",
        "wireless charger",
        "wireles charger",
        "wall charger",
        "iphone charger",
        "usb c cable",
        "phone holder",
        "magsafe charger",
    ),
    "computers_office_peripherals": (
        "laptop",
        "laptpo",
        "desktop pc",
        "desktoppc",
        "computer monitor",
        "pc monitor",
        "keyboard",
        "wireless mouse",
        "wirless mouse",
        "printer",
        "ssd",
    ),
    "audio_video_gaming_cameras": (
        "wireless headphones",
        "wireless headfones",
        "bluetooth speaker",
        "bluetoothspeaker",
        "soundbar",
        "gaming headset",
        "gamming headset",
        "action camera",
        "mirrorless camera",
        "game controller",
        "webcam",
    ),
    "car_parts_service_maintenance": (
        "brake pads",
        "brakepad",
        "brak pads",
        "oil filter",
        "oil fillter",
        "wiper blades",
        "spark plug",
        "car battery",
        "engine oil",
        "timing belt",
    ),
    "tyres_wheels_car_accessories": (
        "car tyres",
        "car tires",
        "car tyers",
        "winter tyres",
        "wintre tyres",
        "all season tires",
        "allseasontires",
        "wheel cover",
        "alloy wheels",
        "rim protector",
    ),
    "moto_bicycle_mobility_gear": (
        "motorcycle helmet",
        "motorbike helmet",
        "motorcyle helmet",
        "bicycle lock",
        "bicyle lock",
        "bike lights",
        "bikehelmet",
        "scooter helmet",
        "cycling gloves",
        "bike pump",
    ),
    "power_tools_workshop": (
        "cordless drill",
        "cordlessdrill",
        "cordles drill",
        "impact driver",
        "angle grinder",
        "angle grnder",
        "circular saw",
        "jigsaw",
        "rotary hammer",
    ),
    "hand_tools_consumables_measuring": (
        "screwdriver set",
        "screwdriverset",
        "screwdrver set",
        "wrench set",
        "socket set",
        "pliers",
        "drill bits",
        "measuring tape",
        "digital caliper",
        "digital calper",
    ),
    "garden_outdoor_repair_building": (
        "garden hose",
        "gardenhose",
        "gardan hose",
        "lawn mower",
        "leaf blower",
        "leaf blwer",
        "pruning shears",
        "paint roller",
        "cement mixer",
        "extension ladder",
    ),
    "health_wellness_safety_devices": (
        "blood pressure monitor",
        "bloodpressure monitor",
        "blood presure monitor",
        "pulse oximeter",
        "pulse oxymeter",
        "digital thermometer",
        "first aid kit",
        "nebulizer",
        "tens unit",
    ),
    "beauty_grooming_personal_care": (
        "hair dryer",
        "hairdryer",
        "hair dryier",
        "hair straightener",
        "electric shaver",
        "beard trimmer",
        "beard trimer",
        "epilator",
        "facial cleansing brush",
    ),
    "baby_kids_pets_sports_outdoor": (
        "baby stroller",
        "babystroller",
        "baby stroler",
        "baby car seat",
        "pet leash",
        "pet leesh",
        "dog harness",
        "camping tent",
        "kids scooter",
        "yoga mat",
    ),
    "clothing_apparel_workwear": (
        "men jacket",
        "mens jacket",
        "mens jaket",
        "workwear trousers",
        "workwear trousres",
        "work pants",
        "workpants",
        "rain jacket",
        "hoodie",
        "safety vest",
        "cotton tshirt",
    ),
    "footwear_shoes_sneakers_boots": (
        "running shoes",
        "runing shoes",
        "sneakers",
        "hiking boots",
        "hiking bots",
        "work boots",
        "trailshoes",
        "trail shoes",
        "football boots",
    ),
    "jewelry_watches_bags_fashion_accessories": (
        "wrist watch",
        "wristwatch",
        "wrist watc",
        "smart analog watch",
        "backpack",
        "handbag",
        "handbg",
        "wallet",
        "necklace",
        "earrings",
    ),
}
_LOWER_LEVEL_PROVIDER_RULES: dict[str, tuple[str, ...]] = {
    "power_banks": tuple(sorted(_POWER_BANK_KEYWORDS | {"10000mahpowerbank"})),
}
_CATEGORY_TO_MEGA: dict[str, str] = {
    "power_banks": "phones_mobile_accessories",
    "chargers": "phones_mobile_accessories",
    "car_tyres": "tyres_wheels_car_accessories",
    "calculators": "computers_office_peripherals",
}
_CATEGORY_TO_DISPLAY_NAME: dict[str, str] = {
    "home_appliances_laundry_climate": "Home Appliances / Laundry / Climate",
    "kitchen_cooking_household": "Kitchen / Cooking / Household",
    "furniture_living_storage_smart_home": "Furniture / Living / Storage / Smart Home",
    "phones_mobile_accessories": "Phones / Mobile / Accessories",
    "computers_office_peripherals": "Computers / Office / Peripherals",
    "audio_video_gaming_cameras": "Audio / Video / Gaming / Cameras",
    "car_parts_service_maintenance": "Car Parts / Service / Maintenance",
    "tyres_wheels_car_accessories": "Tyres / Wheels / Car Accessories",
    "moto_bicycle_mobility_gear": "Moto / Bicycle / Mobility Gear",
    "power_tools_workshop": "Power Tools / Workshop",
    "hand_tools_consumables_measuring": "Hand Tools / Consumables / Measuring",
    "garden_outdoor_repair_building": "Garden / Outdoor / Repair / Building",
    "health_wellness_safety_devices": "Health / Wellness / Safety Devices",
    "beauty_grooming_personal_care": "Beauty / Grooming / Personal Care",
    "baby_kids_pets_sports_outdoor": "Baby / Kids / Pets / Sports / Outdoor",
    "clothing_apparel_workwear": "Clothing / Apparel / Workwear",
    "footwear_shoes_sneakers_boots": "Footwear / Shoes / Sneakers / Boots",
    "jewelry_watches_bags_fashion_accessories": "Jewelry / Watches / Bags / Fashion Accessories",
}


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return ""


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if _contains_term(text, keyword))


def _detect_lower_level_category(text: str) -> tuple[str | None, int]:
    best_key = None
    best_score = 0
    for key, keywords in _LOWER_LEVEL_PROVIDER_RULES.items():
        score = _keyword_score(text, keywords)
        if score > best_score:
            best_key = key
            best_score = score
    return best_key, best_score


def _detect_mega_category(text: str) -> tuple[str | None, int]:
    best_key = None
    best_score = 0
    for mega_category_id, keywords in _CATEGORY_RULES.items():
        score = _keyword_score(text, keywords)
        if mega_category_id == "tyres_wheels_car_accessories" and _TIRE_SIZE_PATTERN.search(text):
            score += 2
        if score > best_score:
            best_key = mega_category_id
            best_score = score
    return best_key, best_score


def detect_category(text: str) -> dict:
    safe = _safe_text(text).lower()
    if not safe:
        return {"category": None, "confidence": 0.0, "reason_codes": ["empty_input"]}

    reason_codes: list[str] = []
    tokens = [token for token in safe.split(" ") if token]

    if any(_contains_term(safe, term) for term in _NON_RETAIL_VERTICAL_TERMS):
        return {
            "category": None,
            "confidence": 0.05,
            "reason_codes": ["out_of_scope_non_retail_vertical"],
        }
    if len(tokens) == 1 and tokens[0] in _OVERMATCH_SINGLE_TOKEN_GUARDS:
        return {
            "category": None,
            "confidence": 0.05,
            "reason_codes": ["overmatch_guard_single_token"],
        }

    legacy_reason_codes: list[str] = []
    tyre_context = any(_contains_term(safe, term) for term in _TYRE_KEYWORDS)
    has_tire_size = bool(_TIRE_SIZE_PATTERN.search(safe) or _TIRE_SIZE_SPACED_PATTERN.search(safe))
    if "lastixa" in safe:
        tyre_context = True
    has_tyre_strong_term = any(_contains_term(safe, term) for term in _TYRE_STRONG_TERMS)
    if (tyre_context and (has_tire_size or has_tyre_strong_term)) or (has_tire_size and has_tyre_strong_term):
        legacy_reason_codes.append("category_signal_legacy_car_tyres")
        return {
            "category": "car_tyres",
            "mega_category_id": "tyres_wheels_car_accessories",
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME["tyres_wheels_car_accessories"],
            "confidence": 0.86,
            "reason_codes": legacy_reason_codes + ["category_selected_car_tyres"],
        }
    if has_tire_size:
        return {
            "category": "car_tyres",
            "mega_category_id": "tyres_wheels_car_accessories",
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME["tyres_wheels_car_accessories"],
            "confidence": 0.72,
            "reason_codes": ["category_signal_legacy_car_tyres", "category_selected_car_tyres"],
        }
    if _contains_term(safe, "lastixa") and not has_tire_size:
        return {
            "category": "car_tyres",
            "mega_category_id": "tyres_wheels_car_accessories",
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME["tyres_wheels_car_accessories"],
            "confidence": 0.62,
            "reason_codes": ["category_signal_legacy_car_tyres", "category_selected_car_tyres"],
        }
    calculator_context = any(_contains_term(safe, term) for term in _CALCULATOR_CONTEXT_KEYWORDS)
    if any(_contains_term(safe, term) for term in _CALCULATOR_KEYWORDS) and calculator_context:
        return {
            "category": "calculators",
            "mega_category_id": "computers_office_peripherals",
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME["computers_office_peripherals"],
            "confidence": 0.82,
            "reason_codes": ["category_signal_legacy_calculators", "category_selected_calculators"],
        }
    if any(_contains_term(safe, term) for term in _CHARGER_KEYWORDS) and any(
        _contains_term(safe, term) for term in {"fast", "γρηγορη", "grigoros", "iphone"}
    ):
        return {
            "category": "chargers",
            "mega_category_id": "phones_mobile_accessories",
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME["phones_mobile_accessories"],
            "confidence": 0.74,
            "reason_codes": ["category_signal_legacy_chargers", "category_selected_chargers"],
        }

    lower_level_category, lower_level_score = _detect_lower_level_category(safe)
    mega_category, mega_score = _detect_mega_category(safe)

    if lower_level_category and lower_level_score >= 1:
        reason_codes.append(f"category_signal_lower_level_{lower_level_category}")
        resolved_mega = _CATEGORY_TO_MEGA.get(lower_level_category, mega_category)
        return {
            "category": lower_level_category,
            "mega_category_id": resolved_mega,
            "lower_level_provider_category": lower_level_category,
            "display_name": _CATEGORY_TO_DISPLAY_NAME.get(str(resolved_mega), "Unknown category"),
            "confidence": 0.92,
            "reason_codes": reason_codes + [f"category_selected_{lower_level_category}"],
        }

    if mega_category and mega_score >= 1:
        reason_codes.append(f"category_signal_mega_{mega_category}")
        confidence = min(0.9, 0.42 + (mega_score * 0.12))
        return {
            "category": mega_category,
            "mega_category_id": mega_category,
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME.get(mega_category, "Unknown category"),
            "confidence": round(confidence, 2),
            "reason_codes": reason_codes + [f"category_selected_{mega_category}"],
        }

    return {
        "category": None,
        "confidence": 0.0,
        "reason_codes": ["no_clear_category_signal"],
    }
