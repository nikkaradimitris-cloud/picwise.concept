from __future__ import annotations

from dataclasses import dataclass

from .repository import BuyingPagesRepository
from .slugging import normalize_keyword_text, slugify_keyword

MAX_ALIASES_PER_CANDIDATE = 10


@dataclass(frozen=True)
class KeywordSeed:
    category: str
    product: str
    brand: str | None = None
    specs: tuple[str, ...] = ()
    price_band_applicable: bool = True


@dataclass(frozen=True)
class KeywordClusterCandidate:
    slug: str
    main_keyword: str
    keyword_aliases: tuple[str, ...]
    category: str
    price_band_applicable: bool
    generation_trace: tuple[str, ...]


def _dedupe_aliases(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = normalize_keyword_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return tuple(deduped)


def generate_keyword_aliases(seed: KeywordSeed) -> tuple[str, ...]:
    product = normalize_keyword_text(seed.product)
    category = normalize_keyword_text(seed.category)
    brand = normalize_keyword_text(seed.brand or "")
    specs = tuple(normalize_keyword_text(spec) for spec in seed.specs if normalize_keyword_text(spec))

    alias_candidates: list[str] = [
        f"best {product}",
        f"{product} buying guide",
        f"{product} for {category}",
        f"top {product} picks",
        f"{product} comparison",
        f"{product} buyer intent",
    ]
    if brand:
        alias_candidates.extend(
            (
                f"{brand} {product}",
                f"{brand} {product} alternatives",
                f"{brand} {product} comparison",
            )
        )
    for spec in specs:
        alias_candidates.extend(
            (
                f"{product} {spec}",
                f"{product} with {spec}",
            )
        )
    return _dedupe_aliases(tuple(alias_candidates))


def _is_conflicting_alias(alias: str, published_repository: BuyingPagesRepository | None) -> bool:
    if published_repository is None:
        return False
    return published_repository.get_by_keyword(alias) is not None


def build_keyword_clusters(
    seeds: tuple[KeywordSeed, ...],
    published_repository: BuyingPagesRepository | None = None,
) -> tuple[KeywordClusterCandidate, ...]:
    clusters: list[KeywordClusterCandidate] = []
    for seed in seeds:
        if published_repository is not None and published_repository.get_by_keyword(seed.product) is not None:
            # Keep candidates isolated from intents already covered by published pages.
            continue
        generated = generate_keyword_aliases(seed)
        non_conflicting = tuple(
            alias for alias in generated if not _is_conflicting_alias(alias, published_repository)
        )
        if not non_conflicting:
            continue

        aliases = non_conflicting[:MAX_ALIASES_PER_CANDIDATE]
        main_keyword = aliases[0]
        slug = slugify_keyword(main_keyword)
        if published_repository is not None and published_repository.get_by_slug(slug) is not None:
            continue

        clusters.append(
            KeywordClusterCandidate(
                slug=slug,
                main_keyword=main_keyword,
                keyword_aliases=aliases,
                category=seed.category,
                price_band_applicable=seed.price_band_applicable,
                generation_trace=(
                    f"product={normalize_keyword_text(seed.product)}",
                    f"category={normalize_keyword_text(seed.category)}",
                    f"brand={normalize_keyword_text(seed.brand or '')}",
                    f"spec_count={len(seed.specs)}",
                ),
            )
        )
    return tuple(clusters)
