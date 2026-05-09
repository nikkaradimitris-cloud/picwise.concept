from __future__ import annotations

from .economic_scoring import ScoredCandidate, score_candidate
from .keyword_clusters import KeywordSeed, build_keyword_clusters
from .repository import BuyingPagesRepository
from .slugging import normalize_keyword_text


def _deterministic_signal(base_text: str, *, offset: int = 0) -> float:
    checksum = sum(ord(ch) for ch in normalize_keyword_text(base_text)) + int(offset)
    return ((checksum % 71) + 15) / 100.0


def _price_target_fit(seed: KeywordSeed) -> float:
    if seed.price_band_applicable:
        return 0.78
    return 0.42


def run_candidate_pipeline(
    seeds: tuple[KeywordSeed, ...],
    *,
    published_repository: BuyingPagesRepository,
) -> tuple[ScoredCandidate, ...]:
    clusters = build_keyword_clusters(seeds, published_repository=published_repository)
    scored: list[ScoredCandidate] = []
    for idx, cluster in enumerate(clusters):
        base = f"{cluster.main_keyword}|{cluster.category}|{idx}"
        scored.append(
            score_candidate(
                cluster,
                buying_intent_strength=_deterministic_signal(base, offset=5),
                product_availability=_deterministic_signal(base, offset=17),
                price_target_fit=_price_target_fit(seeds[idx % len(seeds)]),
                commission_potential=_deterministic_signal(base, offset=29),
                estimated_traffic=_deterministic_signal(base, offset=37),
                competition_inverse=_deterministic_signal(base, offset=43),
                expected_revenue=_deterministic_signal(base, offset=53),
            )
        )
    return tuple(scored)
