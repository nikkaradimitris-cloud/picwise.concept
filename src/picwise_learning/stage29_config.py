from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stage29GenerationConfig:
    deterministic_seed: int = 29
    languages: tuple[str, ...] = ("el", "el_gr", "en", "de")
    intent_phrase_types: tuple[str, ...] = ("compare", "best_for", "find_specific")
    noise_types: tuple[str, ...] = (
        "case_mix",
        "missing_letters",
        "swapped_letters",
        "extra_letters",
        "wrong_spaces",
        "wrong_separators",
        "brand_model_spec_typos",
        "partial_query",
        "bad_typing",
    )
    variants_per_seed: int = 3
    chunk_size: int = 1000
    offline_only: bool = True
    test_mode: bool = True
    metadata: dict[str, str] = field(default_factory=dict)


def build_default_stage29_config() -> Stage29GenerationConfig:
    return Stage29GenerationConfig()
