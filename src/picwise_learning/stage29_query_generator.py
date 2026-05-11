from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable, Iterator

from .stage29_config import Stage29GenerationConfig
from .stage29_contracts import STAGE29_ID, Stage29GeneratedQueryRecord, Stage29SeedRecord
from .stage29_validation import validate_generated_query_record

_LANGUAGE_PREFIX = {
    "el": "σύγκριση",
    "el_gr": "sigrisi",
    "en": "compare",
    "de": "vergleich",
}

_INTENT_PHRASE_SUFFIX = {
    "compare": "options",
    "best_for": "best choice",
    "find_specific": "specific model",
}


def _stable_int(seed: int, *parts: str) -> int:
    payload = f"{seed}|{'|'.join(parts)}"
    return int(hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8], 16)


def _case_mix(text: str, rng: random.Random) -> str:
    return "".join(ch.upper() if rng.random() > 0.5 else ch.lower() for ch in text)


def _missing_letters(text: str, rng: random.Random) -> str:
    if len(text) < 5:
        return text
    idx = rng.randint(1, len(text) - 2)
    return text[:idx] + text[idx + 1 :]


def _swapped_letters(text: str, rng: random.Random) -> str:
    if len(text) < 5:
        return text
    idx = rng.randint(1, len(text) - 3)
    chars = list(text)
    chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
    return "".join(chars)


def _extra_letters(text: str, rng: random.Random) -> str:
    if len(text) < 4:
        return text
    idx = rng.randint(1, len(text) - 2)
    return text[:idx] + text[idx] + text[idx:]


def _wrong_spaces(text: str, rng: random.Random) -> str:
    compact = text.replace(" ", "")
    if len(compact) < 8:
        return compact
    idx = rng.randint(3, len(compact) - 3)
    return compact[:idx] + " " + compact[idx:]


def _wrong_separators(text: str, rng: random.Random) -> str:
    separator = "-" if rng.random() > 0.5 else "/"
    return text.replace(" ", separator)


def _brand_model_spec_typos(text: str, rng: random.Random) -> str:
    if " " not in text:
        return _swapped_letters(text, rng)
    tokens = text.split()
    idx = min(1, len(tokens) - 1)
    tokens[idx] = _swapped_letters(tokens[idx], rng)
    return " ".join(tokens)


def _partial_query(text: str, rng: random.Random) -> str:
    tokens = text.split()
    keep = max(2, len(tokens) // 2)
    return " ".join(tokens[:keep])


def _bad_typing(text: str, rng: random.Random) -> str:
    mutated = text
    for old, new in (("a", "s"), ("e", "w"), ("i", "u"), ("o", "p"), ("n", "m")):
        if old in mutated and rng.random() > 0.5:
            mutated = mutated.replace(old, new, 1)
    return mutated


_NOISE_HANDLERS = {
    "case_mix": _case_mix,
    "missing_letters": _missing_letters,
    "swapped_letters": _swapped_letters,
    "extra_letters": _extra_letters,
    "wrong_spaces": _wrong_spaces,
    "wrong_separators": _wrong_separators,
    "brand_model_spec_typos": _brand_model_spec_typos,
    "partial_query": _partial_query,
    "bad_typing": _bad_typing,
}


def _build_base_query(seed: Stage29SeedRecord, language: str, intent_phrase_type: str) -> str:
    prefix = _LANGUAGE_PREFIX.get(language, "compare")
    suffix = _INTENT_PHRASE_SUFFIX.get(intent_phrase_type, "options")
    return f"{prefix} {seed.canonical_query} {suffix}".strip()


def _make_record(
    seed: Stage29SeedRecord,
    config: Stage29GenerationConfig,
    language: str,
    noise_type: str,
    intent_phrase_type: str,
    variant_index: int,
) -> Stage29GeneratedQueryRecord:
    random_seed = _stable_int(
        config.deterministic_seed,
        seed.seed_id,
        language,
        noise_type,
        intent_phrase_type,
        str(variant_index),
    )
    rng = random.Random(random_seed)
    base_query = _build_base_query(seed, language, intent_phrase_type)
    query = _NOISE_HANDLERS[noise_type](base_query, rng)
    record_id = f"s29_q_{hashlib.sha1((seed.seed_id + query).encode('utf-8')).hexdigest()[:14]}"
    record = Stage29GeneratedQueryRecord(
        record_id=record_id,
        stage=STAGE29_ID,
        generated_query=query,
        canonical_query=seed.canonical_query,
        source_seed_id=seed.seed_id,
        language=language,
        vertical=seed.vertical,
        retail_engine=seed.retail_engine,
        category_bucket=seed.mega_category or seed.expected_nlu_target,
        mega_category=seed.mega_category,
        google_taxonomy_path=seed.google_taxonomy_path,
        saas_erp_contract_ref=seed.saas_erp_contract_ref,
        finance_insurance_contract_ref=seed.finance_insurance_contract_ref,
        expected_nlu_target=seed.expected_nlu_target,
        expected_intent=seed.expected_intent,
        noise_profile=noise_type,
        applied_noise_types=(noise_type,),
        intent_phrase_type=intent_phrase_type,
        deterministic_seed=random_seed,
        metadata={"variant_index": variant_index, "source_metadata": dict(seed.metadata)},
        offline_only=config.offline_only,
        test_mode=config.test_mode,
    )
    report = validate_generated_query_record(record)
    if not report["valid"]:
        raise ValueError(f"Invalid generated query record: {report['errors']}")
    return record


def generate_queries_stream(
    seeds: Iterable[Stage29SeedRecord],
    config: Stage29GenerationConfig,
) -> Iterator[Stage29GeneratedQueryRecord]:
    for seed in seeds:
        for language in config.languages:
            for intent_phrase_type in config.intent_phrase_types:
                for noise_type in config.noise_types:
                    for variant_index in range(config.variants_per_seed):
                        yield _make_record(
                            seed=seed,
                            config=config,
                            language=language,
                            noise_type=noise_type,
                            intent_phrase_type=intent_phrase_type,
                            variant_index=variant_index,
                        )


def chunk_generated_queries(
    generated_records: Iterable[Stage29GeneratedQueryRecord],
    chunk_size: int,
) -> Iterator[list[Stage29GeneratedQueryRecord]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    chunk: list[Stage29GeneratedQueryRecord] = []
    for record in generated_records:
        chunk.append(record)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
