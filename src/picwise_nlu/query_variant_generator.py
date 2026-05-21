from __future__ import annotations

import json
from typing import Any
import re

from .vocabulary_source import load_clean_vocab_by_mega_category

_PARTIAL_EXPECTED_KEYS = {
    "category",
    "brand_candidates",
    "model_candidates",
    "specs",
    "buying_priority",
    "status",
    "expected_status",
    "needs_review",
}

_FORBIDDEN_KEYS = {
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "prices",
    "affiliate",
    "affiliate_url",
}

_DEFAULT_TRAINING_SEEDS: list[dict[str, Any]] = [
    {
        "seed_id": "stage19_tyre_goodyear_exact",
        "case_id": "stage19_tyre_goodyear_exact_seed",
        "family": "car_tyre_exact_product",
        "input": "Goodyear EfficientGrip Performance 2 195/65 R15 comfort",
        "expected": {
            "category": "car_tyres",
            "brand_candidates": ["Goodyear"],
            "model_candidates": ["EfficientGrip Performance 2"],
            "specs": {"width": "195", "profile": "65", "rim": "R15"},
            "buying_priority": ["comfort"],
            "status": "specific_product_resolved",
            "needs_review": False,
        },
    },
    {
        "seed_id": "stage19_tyre_bridgestone_exactish",
        "case_id": "stage19_tyre_bridgestone_exactish_seed",
        "family": "car_tyre_exactish_product",
        "input": "Bridgestone Turanza 195/65 R15 low noise",
        "expected": {
            "category": "car_tyres",
            "brand_candidates": ["Bridgestone"],
            "model_candidates": ["Turanza"],
            "specs": {"width": "195", "profile": "65", "rim": "R15"},
            "buying_priority": ["low_noise"],
            "status": "specific_product_resolved",
            "needs_review": False,
        },
    },
    {
        "seed_id": "stage19_tyre_general_octavia",
        "case_id": "stage19_tyre_general_octavia_seed",
        "family": "car_tyre_general_intent",
        "input": "comfortable tyres 195/65 R15 for Octavia",
        "expected": {
            "category": "car_tyres",
            "specs": {"width": "195", "profile": "65", "rim": "R15"},
            "buying_priority": ["comfort"],
            "status": "general_intent_resolved",
        },
    },
    {
        "seed_id": "stage19_calculator_exam_casio",
        "case_id": "stage19_calculator_exam_casio_seed",
        "family": "calculator_exam_intent",
        "input": "Casio fx-991 calculator for Panellinies exams",
        "expected": {
            "category": "calculators",
            "brand_candidates": ["Casio"],
            "model_candidates": ["fx-991"],
            "buying_priority": ["exam_approved"],
            "status": "specific_product_resolved",
            "needs_review": False,
        },
    },
    {
        "seed_id": "stage19_powerbank_iphone",
        "case_id": "stage19_powerbank_iphone_seed",
        "family": "powerbank_iphone_intent",
        "input": "power bank iphone 20000mah fast charge",
        "expected": {
            "category": "power_banks",
            "specs": {"capacity_mah": "20000"},
            "buying_priority": ["fast_charging"],
            "status": "general_intent_resolved",
        },
    },
    {
        "seed_id": "stage19_charger_fast_iphone",
        "case_id": "stage19_charger_fast_iphone_seed",
        "family": "charger_fast_charging_intent",
        "input": "fast charger iphone USB-C",
        "expected": {
            "category": "chargers",
            "buying_priority": ["fast_charging"],
            "status": "general_intent_resolved",
        },
    },
    {
        "seed_id": "stage19_ambiguous_unknown",
        "case_id": "stage19_ambiguous_unknown_seed",
        "family": "ambiguous_unknown",
        "input": "kati kalo gia to aftokinito",
        "expected": {
            "expected_status": "ambiguous_needs_review",
            "needs_review": True,
        },
    },
]

_VARIANT_BLUEPRINTS: dict[str, list[dict[str, Any]]] = {
    "stage19_tyre_goodyear_exact": [
        {"variant_type": "clean", "input": "Goodyear EfficientGrip Performance 2 195/65 R15 comfort"},
        {"variant_type": "lowercase", "input": "goodyear efficientgrip performance 2 195/65 r15 comfort"},
        {"variant_type": "greeklish", "input": "goodyear efficientgrip performance 2 195 65 r15 pio aneto"},
        {
            "variant_type": "typo",
            "input": "goodyar eficiency grim 195 65 15 pio aneto",
            "expected_updates": {"model_candidates": ["EfficientGrip"]},
        },
        {
            "variant_type": "partial_model",
            "input": "goodyear efficientgrip 195/65 r15 comfort",
            "expected_updates": {"model_candidates": ["EfficientGrip"]},
        },
        {
            "variant_type": "missing_brand",
            "input": "efficientgrip performance 2 195/65 r15 comfort tyres",
            "expected_updates": {"brand_candidates": []},
        },
        {
            "variant_type": "missing_model",
            "input": "goodyear 195/65 r15 comfort tyres",
            "expected_updates": {"model_candidates": [], "status": "general_intent_resolved"},
        },
        {
            "variant_type": "mixed_greek_english",
            "input": "thelo Goodyear lastixa 195/65 R15 comfort",
            "expected_updates": {"model_candidates": [], "status": "general_intent_resolved"},
        },
        {
            "variant_type": "messy_spacing",
            "input": "  goodyear   efficientgrip   195 / 65   r15   comfort  ",
            "expected_updates": {"model_candidates": ["EfficientGrip"]},
        },
        {
            "variant_type": "messy_tire_size",
            "input": "goodyear efficientgrip 195-65-15 comfort",
            "expected_updates": {"model_candidates": ["EfficientGrip"]},
        },
        {
            "variant_type": "priority_only",
            "input": "aneta lastixa gia 195 65 15",
            "expected_updates": {"brand_candidates": [], "model_candidates": [], "status": "general_intent_resolved"},
        },
        {
            "variant_type": "category_only",
            "input": "car tyres 195/65 r15",
            "expected_updates": {
                "brand_candidates": [],
                "model_candidates": [],
                "buying_priority": [],
                "status": "general_intent_resolved",
            },
        },
    ],
    "stage19_tyre_bridgestone_exactish": [
        {"variant_type": "clean", "input": "Bridgestone Turanza 195/65 R15 low noise"},
        {"variant_type": "lowercase", "input": "bridgestone turanza 195/65 r15 low noise"},
        {"variant_type": "greeklish", "input": "bridgestone turanza 195 65 r15 pio isixa"},
        {
            "variant_type": "typo",
            "input": "brizestone touranza iparxi 195 65 r15",
            "expected_updates": {"buying_priority": []},
        },
        {
            "variant_type": "partial_model",
            "input": "bridgestone turan 195/65 r15 quiet",
            "expected_updates": {"model_candidates": ["Turanza"]},
        },
        {
            "variant_type": "missing_brand",
            "input": "turanza 195/65 r15 low noise tyres",
            "expected_updates": {"brand_candidates": []},
        },
    ],
    "stage19_tyre_general_octavia": [
        {"variant_type": "clean", "input": "comfortable tyres 195/65 R15 for Octavia"},
        {"variant_type": "greeklish", "input": "thelo aneta lastixa gia octavia 195 65 15"},
        {"variant_type": "messy_spacing", "input": " comfortable   tyres   195 / 65   r15   octavia "},
    ],
    "stage19_calculator_exam_casio": [
        {"variant_type": "clean", "input": "Casio fx-991 calculator for Panellinies exams"},
        {"variant_type": "lowercase", "input": "casio fx-991 calculator for panellinies"},
        {"variant_type": "greeklish", "input": "kompiouteraki panellinies casio fx 991"},
        {"variant_type": "typo", "input": "casio fz-991 kompiouteraki gia panelinies"},
        {
            "variant_type": "missing_brand",
            "input": "fx 991 calculator for panellinies",
            "expected_updates": {"brand_candidates": []},
        },
    ],
    "stage19_powerbank_iphone": [
        {"variant_type": "clean", "input": "power bank iphone 20000mah fast charge"},
        {"variant_type": "lowercase", "input": "power bank iphone 20000mah fast charge"},
        {
            "variant_type": "greeklish",
            "input": "power bank gia iphone megali bataria 20000mah",
            "expected_updates": {"buying_priority": ["battery_life"]},
        },
        {"variant_type": "typo", "input": "pwer bank iphone 20000 mah fast chrge"},
        {
            "variant_type": "missing_model",
            "input": "power bank iphone fast charging",
            "expected_updates": {"specs": {"capacity_mah": ""}},
        },
    ],
    "stage19_charger_fast_iphone": [
        {"variant_type": "clean", "input": "fast charger iphone USB-C"},
        {"variant_type": "lowercase", "input": "fast charger iphone usb-c"},
        {"variant_type": "greeklish", "input": "fortistis iphone grigoros usb c"},
        {"variant_type": "typo", "input": "fast chager iphone usbc"},
        {
            "variant_type": "category_only",
            "input": "charger iphone",
            "expected_updates": {"buying_priority": []},
        },
    ],
    "stage19_ambiguous_unknown": [
        {
            "variant_type": "ambiguous",
            "input": "kati kalo gia to aftokinito",
            "expected_updates": {"expected_status": "insufficient_data", "needs_review": True},
        },
        {
            "variant_type": "ambiguous",
            "input": "thelo kati kalo alla den ksero ti",
            "expected_updates": {"expected_status": "insufficient_data", "needs_review": True},
        },
        {
            "variant_type": "priority_only",
            "input": "na einai aplo kai kalo",
            "expected_updates": {"expected_status": "insufficient_data", "needs_review": True},
        },
    ],
}


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _compact_text(item)
        if text and text not in seen:
            items.append(text)
            seen.add(text)
    return items


def _normalize_specs(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    safe_specs: dict[str, Any] = {}
    for key, raw in value.items():
        key_text = _compact_text(key)
        if not key_text:
            continue
        if isinstance(raw, (int, float, bool)) or raw is None:
            safe_specs[key_text] = raw
            continue
        text_value = _compact_text(raw)
        if text_value:
            safe_specs[key_text] = text_value
    return safe_specs


def _sanitize_expected(expected: Any) -> dict[str, Any]:
    payload = dict(expected or {}) if isinstance(expected, dict) else {}
    safe: dict[str, Any] = {}
    for key in _PARTIAL_EXPECTED_KEYS:
        if key not in payload:
            continue
        value = payload.get(key)
        if key in {"brand_candidates", "model_candidates", "buying_priority"}:
            safe[key] = _normalize_list(value)
        elif key == "specs":
            safe[key] = _normalize_specs(value)
        elif key in {"status", "expected_status", "category"}:
            text = _compact_text(value)
            if text:
                safe[key] = text
        elif key == "needs_review":
            safe[key] = bool(value)
    for forbidden in _FORBIDDEN_KEYS:
        safe.pop(forbidden, None)
    return safe


def _merge_expected(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        merged[key] = value
    return _sanitize_expected(merged)


def _seed_identity(seed: dict[str, Any], index: int) -> str:
    explicit = _compact_text(seed.get("seed_id"))
    if explicit:
        return explicit
    fallback = _compact_text(seed.get("case_id"))
    if fallback:
        return fallback
    return f"seed_{index}"


def get_default_training_seeds() -> list[dict]:
    return json.loads(json.dumps(_DEFAULT_TRAINING_SEEDS, ensure_ascii=True, sort_keys=True))


def normalize_variant_record(record: dict) -> dict:
    payload = dict(record or {})
    case_id = _compact_text(payload.get("case_id"))
    seed_id = _compact_text(payload.get("seed_id"))
    variant_type = _compact_text(payload.get("variant_type"))
    user_input = _compact_text(payload.get("input"))
    expected = _sanitize_expected(payload.get("expected"))

    normalized = {
        "case_id": case_id,
        "input": user_input,
        "expected": expected,
        "seed_id": seed_id,
        "variant_type": variant_type or "clean",
        "source": "local_variant_generator",
    }
    return json.loads(json.dumps(normalized, ensure_ascii=True, sort_keys=True))


def generate_variants_for_seed(seed: dict, max_variants: int = 200) -> list[dict]:
    if not isinstance(seed, dict):
        return []
    limit = max(0, int(max_variants))
    if limit == 0:
        return []
    seed_id = _compact_text(seed.get("seed_id"))
    if not seed_id:
        return []

    base_expected = _sanitize_expected(seed.get("expected"))
    blueprints = _VARIANT_BLUEPRINTS.get(seed_id, [])
    if not blueprints:
        clean_input = _compact_text(seed.get("input"))
        if clean_input:
            blueprints = [{"variant_type": "clean", "input": clean_input}]

    records: list[dict] = []
    dedupe_keys: set[tuple[str, str]] = set()
    for index, variant in enumerate(blueprints, start=1):
        if len(records) >= limit:
            break
        variant_type = _compact_text(variant.get("variant_type")) or "clean"
        user_input = _compact_text(variant.get("input"))
        if not user_input:
            continue
        expected_updates = variant.get("expected_updates", {})
        merged_expected = _merge_expected(base_expected, expected_updates if isinstance(expected_updates, dict) else {})
        signature = (variant_type.lower(), user_input.lower())
        if signature in dedupe_keys:
            continue
        dedupe_keys.add(signature)
        candidate = normalize_variant_record(
            {
                "case_id": f"{seed_id}_v{index:03d}",
                "input": user_input,
                "expected": merged_expected,
                "seed_id": seed_id,
                "variant_type": variant_type,
            }
        )
        records.append(candidate)
    return records


def generate_variants_for_training_pack(
    seeds: list[dict] | None = None,
    max_variants_per_seed: int = 200,
) -> list[dict]:
    source_seeds = seeds if isinstance(seeds, list) and seeds else get_default_training_seeds()
    normalized_seeds: list[dict[str, Any]] = []
    for index, seed in enumerate(source_seeds, start=1):
        if not isinstance(seed, dict):
            continue
        seed_id = _seed_identity(seed, index)
        normalized_seeds.append(
            {
                "seed_id": seed_id,
                "case_id": _compact_text(seed.get("case_id")) or f"{seed_id}_seed",
                "input": _compact_text(seed.get("input")),
                "expected": _sanitize_expected(seed.get("expected")),
                "family": _compact_text(seed.get("family")),
            }
        )

    pack: list[dict] = []
    for seed in normalized_seeds:
        pack.extend(generate_variants_for_seed(seed, max_variants=max_variants_per_seed))
    return json.loads(json.dumps(pack, ensure_ascii=True, sort_keys=True))


_GENERATOR_VERSION = "stage3_generic_en_v2"
_MIN_SAFE_TERM_LENGTH = 3
_ALPHA_RE = re.compile(r"[a-z]")
_TOKEN_RE = re.compile(r"[a-z]+")
_VOWELS = set("aeiou")
_US_UK_WORDS: dict[str, str] = {
    "tyre": "tire",
    "tire": "tyre",
    "colour": "color",
    "color": "colour",
    "favourite": "favorite",
    "favorite": "favourite",
    "centre": "center",
    "center": "centre",
}
_BROAD_SINGLE_TOKENS = {
    "car",
    "bike",
    "baby",
    "winter",
    "garden",
    "gaming",
}


def _canonicalize_english_term(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip().lower()
    if not text:
        return ""
    tokens = _TOKEN_RE.findall(text)
    return " ".join(tokens)


def _is_safe_variant_text(value: str, min_length: int) -> bool:
    if len(value) < min_length:
        return False
    if not _ALPHA_RE.search(value):
        return False
    tokens = value.split()
    if not tokens:
        return False
    if any(len(token) < 2 for token in tokens):
        return False
    return True


def _replace_char_at(value: str, index: int, char: str) -> str:
    return f"{value[:index]}{char}{value[index + 1:]}"


def _single_missing_letter_variant(term: str) -> str:
    tokens = term.split()
    for idx, token in enumerate(tokens):
        if len(token) < 4:
            continue
        remove_at = max(1, len(token) // 2 - 1)
        reduced = f"{token[:remove_at]}{token[remove_at + 1:]}"
        if len(reduced) >= 3:
            candidate_tokens = list(tokens)
            candidate_tokens[idx] = reduced
            return " ".join(candidate_tokens)
    return ""


def _single_extra_letter_variant(term: str) -> str:
    tokens = term.split()
    for idx, token in enumerate(tokens):
        if len(token) < 3:
            continue
        insert_at = min(len(token) - 1, len(token) // 2)
        extra_char = token[insert_at]
        expanded = f"{token[:insert_at]}{extra_char}{token[insert_at:]}"
        candidate_tokens = list(tokens)
        candidate_tokens[idx] = expanded
        return " ".join(candidate_tokens)
    return ""


def _single_swapped_letter_variant(term: str) -> str:
    tokens = term.split()
    for idx, token in enumerate(tokens):
        if len(token) < 4:
            continue
        preferred_start = max(1, len(token) // 2 - 1)
        positions = list(range(preferred_start, len(token) - 1)) + list(range(0, preferred_start))
        for swap_at in positions:
            if token[swap_at] == token[swap_at + 1]:
                continue
            swapped = list(token)
            swapped[swap_at], swapped[swap_at + 1] = swapped[swap_at + 1], swapped[swap_at]
            candidate_tokens = list(tokens)
            candidate_tokens[idx] = "".join(swapped)
            return " ".join(candidate_tokens)
    return ""


def _single_repeated_letter_variant(term: str) -> str:
    tokens = term.split()
    for idx, token in enumerate(tokens):
        if len(token) < 3:
            continue
        repeat_at = 1 if len(token) > 3 else 0
        repeated = f"{token[:repeat_at + 1]}{token[repeat_at]}{token[repeat_at + 1:]}"
        candidate_tokens = list(tokens)
        candidate_tokens[idx] = repeated
        return " ".join(candidate_tokens)
    return ""


def _single_joined_word_variant(term: str) -> str:
    tokens = term.split()
    if len(tokens) < 2:
        return ""
    return "".join(tokens)


def _single_vowel_drop_variant(term: str) -> str:
    tokens = term.split()
    for idx, token in enumerate(tokens):
        if len(token) < 5:
            continue
        drop_at = -1
        for pos in range(1, len(token) - 1):
            if token[pos] in _VOWELS:
                drop_at = pos
                break
        if drop_at == -1:
            continue
        shrunk = f"{token[:drop_at]}{token[drop_at + 1:]}"
        if len(shrunk) < 3:
            continue
        candidate_tokens = list(tokens)
        candidate_tokens[idx] = shrunk
        return " ".join(candidate_tokens)
    return ""


def _single_us_uk_variant(term: str) -> str:
    tokens = term.split()
    changed = False
    swapped_tokens: list[str] = []
    for token in tokens:
        replacement = _US_UK_WORDS.get(token, token)
        if replacement != token:
            changed = True
        swapped_tokens.append(replacement)
    if not changed:
        return ""
    return " ".join(swapped_tokens)


def _single_elery_spelling_family_variant(term: str) -> str:
    tokens = term.split()
    if len(tokens) != 1:
        return ""
    token = tokens[0]
    if token.endswith("elry") and len(token) >= 6:
        return token[:-2] + "ellery"
    if token.endswith("ellery") and len(token) >= 7:
        return token[:-3] + "ry"
    return ""


def _single_or_our_spelling_family_variant(term: str) -> str:
    tokens = term.split()
    if len(tokens) != 1:
        return ""
    token = tokens[0]
    if token.endswith("or") and len(token) >= 5:
        return token[:-2] + "our"
    if token.endswith("our") and len(token) >= 6:
        return token[:-3] + "or"
    return ""


def _single_consonant_skeleton_variant(term: str) -> str:
    tokens = term.split()
    if len(tokens) != 1:
        return ""
    token = tokens[0]
    if len(token) < 6:
        return ""
    skeleton = "".join(char for char in token if char not in _VOWELS)
    if len(skeleton) < 4 or skeleton == token:
        return ""
    return skeleton


def generate_noisy_variants_for_term(
    canonical_term: str,
    mega_category_id: str,
    *,
    source: str = "taxonomy_clean_vocabulary",
    generator_version: str = _GENERATOR_VERSION,
    min_variant_length: int = _MIN_SAFE_TERM_LENGTH,
) -> list[dict[str, str]]:
    term = _canonicalize_english_term(canonical_term)
    category = _compact_text(mega_category_id)
    if not term or not category:
        return []
    if len(term) < max(3, int(min_variant_length)):
        return []

    term_tokens = term.split()
    if len(term_tokens) == 1 and term_tokens[0] in _BROAD_SINGLE_TOKENS:
        return []

    builders: list[tuple[str, str]] = [
        ("missing_letter", _single_missing_letter_variant(term)),
        ("extra_letter", _single_extra_letter_variant(term)),
        ("swapped_adjacent_letters", _single_swapped_letter_variant(term)),
        ("repeated_letter", _single_repeated_letter_variant(term)),
        ("joined_words", _single_joined_word_variant(term)),
        ("vowel_drop", _single_vowel_drop_variant(term)),
        ("us_uk_spelling", _single_us_uk_variant(term)),
        ("spelling_family", _single_elery_spelling_family_variant(term)),
        ("spelling_family", _single_or_our_spelling_family_variant(term)),
        ("consonant_skeleton", _single_consonant_skeleton_variant(term)),
    ]

    output: list[dict[str, str]] = []
    seen: set[str] = set()
    safe_min_length = max(3, int(min_variant_length))
    for variant_type, variant in builders:
        if not variant:
            continue
        candidate = _canonicalize_english_term(variant)
        if candidate == term:
            continue
        if not _is_safe_variant_text(candidate, safe_min_length):
            continue
        signature = candidate.lower()
        if signature in seen:
            continue
        seen.add(signature)
        output.append(
            {
                "canonical_term": term,
                "variant": candidate,
                "mega_category_id": category,
                "variant_type": variant_type,
                "source": source,
                "generator_version": generator_version,
            }
        )
    return json.loads(json.dumps(output, ensure_ascii=True, sort_keys=True))


def generate_generic_english_noisy_variants(
    vocab_by_mega_category: dict[str, set[str]] | dict[str, list[str]] | None = None,
    *,
    source: str = "taxonomy_clean_vocabulary",
    generator_version: str = _GENERATOR_VERSION,
    min_variant_length: int = _MIN_SAFE_TERM_LENGTH,
) -> list[dict[str, str]]:
    vocab = vocab_by_mega_category if isinstance(vocab_by_mega_category, dict) else load_clean_vocab_by_mega_category()
    records: list[dict[str, str]] = []
    seen_signatures: set[tuple[str, str, str]] = set()

    for mega_category_id in sorted(vocab.keys()):
        terms = vocab.get(mega_category_id, [])
        iterable = terms if isinstance(terms, (set, list, tuple)) else []
        normalized_terms = sorted({_canonicalize_english_term(term) for term in iterable if _canonicalize_english_term(term)})
        for canonical_term in normalized_terms:
            term_records = generate_noisy_variants_for_term(
                canonical_term,
                mega_category_id,
                source=source,
                generator_version=generator_version,
                min_variant_length=min_variant_length,
            )
            for row in term_records:
                signature = (
                    row["canonical_term"].lower(),
                    row["variant"].lower(),
                    row["mega_category_id"].lower(),
                )
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                records.append(row)
    return json.loads(json.dumps(records, ensure_ascii=True, sort_keys=True))
