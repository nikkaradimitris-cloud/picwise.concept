from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .normalizer import normalize_query
from .vocabulary_source import load_clean_vocab_by_mega_category

_TIRE_SIZE_PATTERN = re.compile(r"(?<!\d)(\d{3})/(\d{2})\s*[Rr](\d{2})(?!\d)")
_TIRE_SIZE_SPACED_PATTERN = re.compile(r"(?<!\d)(\d{3})\s+(\d{2})\s+(\d{2})(?!\d)")
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
_LOWER_LEVEL_PROVIDER_RULES: dict[str, tuple[str, ...]] = {
    "power_banks": (
        "power bank",
        "power banks",
        "powerbank",
        "power pack",
        "portable charger",
        "battery pack",
    ),
    "chargers": (
        "charger",
        "usb c",
        "usb-c",
        "iphone charger",
        "fast charger",
        "wall charger",
        "φορτιστης",
    ),
    "calculators": (
        "calculator",
        "fx 991",
        "fx-991",
        "casio",
        "κομπιουτερακι",
        "πανελληνιες",
    ),
    "car_tyres": (
        "lastixa",
        "winter tyres",
        "wintre tyres",
        "car tyres",
        "car tires",
    ),
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
_HEALTH_SIGNAL_TERMS = {"blood", "pressure", "monitor", "oximeter", "pulse"}
_POWER_HEAD_TERMS = {"power"}
_BANK_TAIL_TERMS = {"bank"}


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return normalize_query(value)
    return ""


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def _is_ascii_term(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9/\-\s]*", value))


def _canonicalize_vocab_term(value: str) -> str:
    return normalize_query(value).replace("/", " ")


def _expand_us_uk_variants(term: str) -> set[str]:
    variants = {term}
    replacements = (
        (" tyre ", " tire "),
        (" tyres ", " tires "),
        (" tire ", " tyre "),
        (" tires ", " tyres "),
    )
    padded = f" {term} "
    for source, target in replacements:
        if source in padded:
            variants.add(padded.replace(source, target).strip())
    return {item for item in variants if item}


def _damerau_levenshtein(left: str, right: str, max_distance: int) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > max_distance:
        return max_distance + 1

    left_len = len(left)
    right_len = len(right)
    matrix = [[0] * (right_len + 1) for _ in range(left_len + 1)]
    for i in range(left_len + 1):
        matrix[i][0] = i
    for j in range(right_len + 1):
        matrix[0][j] = j

    for i in range(1, left_len + 1):
        row_min = max_distance + 1
        for j in range(1, right_len + 1):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            deletion = matrix[i - 1][j] + 1
            insertion = matrix[i][j - 1] + 1
            substitution = matrix[i - 1][j - 1] + cost
            value = min(deletion, insertion, substitution)
            if (
                i > 1
                and j > 1
                and left[i - 1] == right[j - 2]
                and left[i - 2] == right[j - 1]
            ):
                value = min(value, matrix[i - 2][j - 2] + 1)
            matrix[i][j] = value
            if value < row_min:
                row_min = value
        if row_min > max_distance:
            return max_distance + 1
    return matrix[left_len][right_len]


@lru_cache(maxsize=1)
def _build_vocab_index() -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    vocab_by_category = load_clean_vocab_by_mega_category()
    for mega_category_id, values in list(vocab_by_category.items()):
        filtered: set[str] = set()
        for raw_term in values:
            normalized = _canonicalize_vocab_term(raw_term)
            if not normalized or not _is_ascii_term(normalized):
                continue
            if len(normalized.split()) > 4:
                continue
            for variant in _expand_us_uk_variants(normalized):
                filtered.add(variant)
        vocab_by_category[mega_category_id] = filtered
    token_lexicon: set[str] = set()
    for terms in vocab_by_category.values():
        for term in terms:
            for token in term.split():
                if len(token) >= 3 and re.fullmatch(r"[a-z0-9]+", token):
                    token_lexicon.add(token)
    for terms in _FALLBACK_CATEGORY_RULES.values():
        for term in terms:
            for token in term.split():
                if len(token) >= 3 and re.fullmatch(r"[a-z0-9]+", token):
                    token_lexicon.add(token)
    for terms in _LOWER_LEVEL_PROVIDER_RULES.values():
        for term in terms:
            for token in term.split():
                if len(token) >= 3 and re.fullmatch(r"[a-z0-9]+", token):
                    token_lexicon.add(token)
    frozen_vocab = {key: tuple(sorted(values)) for key, values in vocab_by_category.items()}
    return frozen_vocab, tuple(sorted(token_lexicon))


def _best_token_match(token: str, token_lexicon: tuple[str, ...]) -> tuple[str, float]:
    if token in token_lexicon or len(token) < 3 or not token.isalpha():
        return token, 1.0

    max_distance = 1 if len(token) <= 5 else 2
    best_candidate = ""
    best_distance = max_distance + 1
    tie = False
    for candidate in token_lexicon:
        if abs(len(candidate) - len(token)) > max_distance:
            continue
        distance = _damerau_levenshtein(token, candidate, max_distance=max_distance)
        if distance > max_distance:
            continue
        if distance < best_distance:
            best_candidate = candidate
            best_distance = distance
            tie = False
        elif distance == best_distance and candidate != best_candidate:
            tie = True
    if tie or not best_candidate:
        return token, 0.0
    confidence = 1.0 - (best_distance / max(len(token), len(best_candidate)))
    return best_candidate, round(confidence, 2)


def _has_neighbor(tokens: list[str], idx: int, allowed_terms: set[str]) -> bool:
    left = tokens[idx - 1].lower() if idx - 1 >= 0 else ""
    right = tokens[idx + 1].lower() if idx + 1 < len(tokens) else ""
    return left in allowed_terms or right in allowed_terms


def _apply_context_token_corrections(tokens: list[str]) -> list[str]:
    if not tokens:
        return []
    corrected = list(tokens)
    for idx, token in enumerate(tokens):
        lowered = token.lower()
        if lowered in _BANK_TAIL_TERMS and _has_neighbor(tokens, idx, _POWER_HEAD_TERMS):
            corrected[idx] = "bank"
            continue
        if lowered in _POWER_HEAD_TERMS and _has_neighbor(tokens, idx, _BANK_TAIL_TERMS):
            corrected[idx] = "power"
            continue
    return corrected


def _normalize_noisy_tokens(text: str, token_lexicon: tuple[str, ...]) -> tuple[list[str], float]:
    raw_tokens = [token for token in text.split(" ") if token]
    if not raw_tokens:
        return [], 0.0
    normalized_tokens: list[str] = []
    confidences: list[float] = []
    token_set = set(token_lexicon)
    for token in raw_tokens:
        best_token, confidence = _best_token_match(token, token_lexicon)
        if best_token == token and confidence == 0.0 and len(token) >= 8:
            split_applied = False
            for split_idx in range(3, len(token) - 2):
                left = token[:split_idx]
                right = token[split_idx:]
                if left in token_set and right in token_set:
                    normalized_tokens.extend((left, right))
                    confidences.append(0.85)
                    split_applied = True
                    break
            if split_applied:
                continue
        normalized_tokens.append(best_token)
        confidences.append(confidence)
    normalized_tokens = _apply_context_token_corrections(normalized_tokens)
    average_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    return normalized_tokens, average_confidence


def _detect_lower_level_category(text: str) -> tuple[str | None, int]:
    best_key = None
    best_score = 0
    safe_text = text.strip().lower()
    token_set = set(safe_text.split())
    for key, keywords in _LOWER_LEVEL_PROVIDER_RULES.items():
        score = sum(1 for keyword in keywords if _contains_term(text, keyword))
        if key == "power_banks":
            if "power" in token_set and "bank" in token_set:
                score += 2
            if "battery" in token_set and "pack" in token_set:
                score += 1
        if key == "calculators":
            if "casio" in token_set and not any(term in token_set for term in {"calculator", "fx", "991", "κομπιουτερακι", "πανελληνιες"}):
                score = 0
        if score > best_score:
            best_key = key
            best_score = score
    return best_key, best_score


def _detect_mega_category(text: str) -> tuple[str | None, float, bool]:
    vocab_by_category, token_lexicon = _build_vocab_index()
    normalized_tokens, token_confidence = _normalize_noisy_tokens(text, token_lexicon)
    if not normalized_tokens:
        return None, 0.0, False
    normalized_text = " ".join(normalized_tokens)

    scores: dict[str, float] = {}
    for mega_category_id, keywords in vocab_by_category.items():
        score = 0.0
        for keyword in keywords:
            if _contains_term(normalized_text, keyword):
                score += 1.0 + (0.2 * (len(keyword.split()) - 1))
        if mega_category_id == "tyres_wheels_car_accessories" and (
            _TIRE_SIZE_PATTERN.search(normalized_text) or _TIRE_SIZE_SPACED_PATTERN.search(normalized_text)
        ):
            score += 2.0
        if score > 0.0:
            scores[mega_category_id] = score

    token_set = set(normalized_tokens)
    if len(token_set.intersection(_HEALTH_SIGNAL_TERMS)) >= 2:
        scores["health_wellness_safety_devices"] = scores.get("health_wellness_safety_devices", 0.0) + 1.2

    if not scores:
        return None, 0.0, False
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_key, best_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0
    ambiguous = second_score > 0 and (best_score - second_score) < 0.75
    confidence = min(0.95, 0.4 + (best_score * 0.11))
    if token_confidence < 0.5:
        confidence = min(confidence, 0.49)
    return best_key, round(confidence, 2), ambiguous


def _legacy_category_for_mega(mega_category_id: str, safe_text: str) -> str:
    if mega_category_id == "tyres_wheels_car_accessories":
        return "car_tyres"
    if mega_category_id == "computers_office_peripherals" and _contains_term(safe_text, "calculator"):
        return "calculators"
    if mega_category_id == "phones_mobile_accessories" and _contains_term(safe_text, "charger"):
        return "chargers"
    return mega_category_id


_FALLBACK_CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "home_appliances_laundry_climate": (
        "washing machine",
        "air conditioner",
        "airconditioner",
    ),
    "kitchen_cooking_household": ("air fryer", "airfryer", "coffee maker", "blender"),
    "furniture_living_storage_smart_home": (
        "office chair",
        "officechair",
        "storage cabinet",
        "smart bulb",
    ),
    "phones_mobile_accessories": (
        "wireless charger",
        "screen protector",
        "phonecase",
        "iphone charger",
        "wall charger",
        "cable",
        "usb cable",
        "charging cable",
    ),
    "computers_office_peripherals": ("laptop", "wireless mouse", "desktoppc", "printer"),
    "audio_video_gaming_cameras": (
        "wireless headphones",
        "gaming headset",
        "bluetoothspeaker",
        "action camera",
    ),
    "car_parts_service_maintenance": ("brake pads", "brakepad", "oil filter", "wiper blades"),
    "tyres_wheels_car_accessories": ("car tyres", "car tires", "car tyre", "car tire", "winter tyres", "allseasontires"),
    "moto_bicycle_mobility_gear": (
        "motorcycle helmet",
        "motorbike helmet",
        "bicycle lock",
        "bikehelmet",
        "bike lights",
    ),
    "power_tools_workshop": ("drill", "cordlessdrill", "angle grinder"),
    "hand_tools_consumables_measuring": ("screwdriver set", "screwdriverset", "digital caliper"),
    "garden_outdoor_repair_building": ("garden hose", "gardenhose", "leaf blower"),
    "health_wellness_safety_devices": (
        "blood pressure monitor",
        "bloodpressure monitor",
        "pulse oximeter",
    ),
    "beauty_grooming_personal_care": ("hair dryer", "hairdryer", "beard trimmer"),
    "baby_kids_pets_sports_outdoor": ("baby stroller", "babystroller", "pet leash"),
    "clothing_apparel_workwear": ("mens jacket", "workwear trousers", "workpants", "rain jacket"),
    "footwear_shoes_sneakers_boots": ("running shoes", "hiking boots", "trailshoes", "all season tires"),
    "jewelry_watches_bags_fashion_accessories": ("wrist watch", "wristwatch", "handbag"),
}


def _fallback_detect_mega_category(safe: str) -> tuple[str | None, float]:
    _, token_lexicon = _build_vocab_index()
    normalized_tokens, _ = _normalize_noisy_tokens(safe, token_lexicon)
    normalized_safe = " ".join(normalized_tokens)
    best_key = None
    best_score = 0
    for mega_category_id, terms in _FALLBACK_CATEGORY_RULES.items():
        score = sum(1 for term in terms if _contains_term(safe, term) or _contains_term(normalized_safe, term))
        if mega_category_id == "tyres_wheels_car_accessories" and (
            _TIRE_SIZE_PATTERN.search(safe) or _TIRE_SIZE_SPACED_PATTERN.search(safe) or _TIRE_SIZE_PATTERN.search(normalized_safe) or _TIRE_SIZE_SPACED_PATTERN.search(normalized_safe)
        ):
            score += 2
        if score > best_score:
            best_key = mega_category_id
            best_score = score
    if best_key is None:
        return None, 0.0
    confidence = min(0.88, 0.45 + (best_score * 0.1))
    return best_key, round(confidence, 2)


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

    _, token_lexicon = _build_vocab_index()
    normalized_tokens, _ = _normalize_noisy_tokens(safe, token_lexicon)
    normalized_safe = " ".join(normalized_tokens)

    lower_level_category, lower_level_score = _detect_lower_level_category(safe)
    normalized_lower_level_category, normalized_lower_level_score = _detect_lower_level_category(normalized_safe)
    if normalized_lower_level_score > lower_level_score:
        lower_level_category = normalized_lower_level_category
        lower_level_score = normalized_lower_level_score

    mega_category, mega_confidence, ambiguous = _detect_mega_category(safe)
    fallback_mega, fallback_confidence = _fallback_detect_mega_category(safe)

    if lower_level_category and lower_level_score >= 1:
        reason_codes.append(f"category_signal_lower_level_{lower_level_category}")
        resolved_mega = _CATEGORY_TO_MEGA.get(lower_level_category, mega_category)
        if lower_level_category in {"chargers", "calculators", "car_tyres"}:
            return {
                "category": lower_level_category,
                "mega_category_id": resolved_mega,
                "lower_level_provider_category": None,
                "display_name": _CATEGORY_TO_DISPLAY_NAME.get(str(resolved_mega), "Unknown category"),
                "confidence": 0.9,
                "reason_codes": reason_codes + [f"category_selected_{lower_level_category}"],
            }
        return {
            "category": lower_level_category,
            "mega_category_id": resolved_mega,
            "lower_level_provider_category": lower_level_category,
            "display_name": _CATEGORY_TO_DISPLAY_NAME.get(str(resolved_mega), "Unknown category"),
            "confidence": 0.92,
            "reason_codes": reason_codes + [f"category_selected_{lower_level_category}"],
        }
    if "charger" in tokens and len(tokens) <= 2 and all(term in {"charger", "usb", "c"} for term in tokens):
        return {
            "category": None,
            "confidence": 0.05,
            "reason_codes": ["overmatch_guard_single_token"],
        }

    if ambiguous and fallback_mega is None:
        return {
            "category": None,
            "confidence": 0.2,
            "reason_codes": ["ambiguous_category_signals"],
        }
    if ambiguous and fallback_mega is not None:
        mega_category = fallback_mega
        mega_confidence = max(mega_confidence, fallback_confidence)
        ambiguous = False

    if (
        mega_category
        and fallback_mega
        and fallback_mega != mega_category
        and fallback_confidence >= mega_confidence
    ):
        mega_category = fallback_mega
        mega_confidence = max(mega_confidence, fallback_confidence)
        reason_codes.append(f"category_signal_fallback_override_{fallback_mega}")

    if mega_category:
        legacy_category = _legacy_category_for_mega(mega_category, safe)
        reason_codes.append(f"category_signal_mega_{mega_category}")
        return {
            "category": legacy_category,
            "mega_category_id": mega_category,
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME.get(mega_category, "Unknown category"),
            "confidence": mega_confidence,
            "reason_codes": reason_codes + [f"category_selected_{legacy_category}"],
        }

    if fallback_mega:
        legacy_category = _legacy_category_for_mega(fallback_mega, safe)
        reason_codes.append(f"category_signal_fallback_{fallback_mega}")
        if fallback_mega == "footwear_shoes_sneakers_boots" and _contains_term(safe, "all season tires"):
            fallback_mega = "tyres_wheels_car_accessories"
            legacy_category = _legacy_category_for_mega(fallback_mega, safe)
        return {
            "category": legacy_category,
            "mega_category_id": fallback_mega,
            "lower_level_provider_category": None,
            "display_name": _CATEGORY_TO_DISPLAY_NAME.get(fallback_mega, "Unknown category"),
            "confidence": fallback_confidence,
            "reason_codes": reason_codes + [f"category_selected_{legacy_category}"],
        }

    return {
        "category": None,
        "confidence": 0.0,
        "reason_codes": ["no_clear_category_signal"],
    }
