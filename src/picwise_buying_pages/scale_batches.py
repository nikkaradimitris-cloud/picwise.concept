from __future__ import annotations

import math
from dataclasses import dataclass

from .google_quality_gate import evaluate_google_quality_gate
from .models import BuyingPage
from .scale_registry import ScaleRegistry, build_buying_page_from_descriptor, build_registry_for_100k

FIRST_SCALE_BATCH_SIZE = 1_000
SECOND_SCALE_BATCH_SIZE = 10_000


@dataclass(frozen=True)
class ScaleBatch:
    name: str
    requested_published_pages: int
    published_pages: tuple[BuyingPage, ...]
    candidate_pages: tuple[BuyingPage, ...]
    rejected_pages: tuple[BuyingPage, ...]


def generate_scale_batch(
    *,
    name: str,
    published_target: int,
    candidate_target: int,
    candidate_every: int = 11,
) -> ScaleBatch:
    if published_target <= 0:
        raise ValueError("published_target must be > 0.")
    if candidate_target < 0:
        raise ValueError("candidate_target must be >= 0.")
    if candidate_every <= 1:
        raise ValueError("candidate_every must be > 1.")

    minimum_for_published = math.ceil(published_target * candidate_every / (candidate_every - 1))
    minimum_for_candidates = candidate_target * candidate_every
    registry_size = max(minimum_for_published, minimum_for_candidates, 1_000) + candidate_every

    registry = ScaleRegistry(total_pages=registry_size, candidate_every=candidate_every)
    collected_published: list[BuyingPage] = []
    collected_candidates: list[BuyingPage] = []
    rejected_pages: list[BuyingPage] = []
    for descriptor in registry.iter_descriptors():
        page = build_buying_page_from_descriptor(descriptor)
        quality_result = evaluate_google_quality_gate(
            page,
            economic_score_passed=not descriptor.candidate_only,
        )
        if not quality_result.quality_passed:
            rejected_pages.append(page)
            continue
        if descriptor.candidate_only:
            if len(collected_candidates) < candidate_target:
                collected_candidates.append(page)
        else:
            if not quality_result.publication_ready:
                rejected_pages.append(page)
                continue
            if len(collected_published) < published_target:
                collected_published.append(page)
        if len(collected_published) >= published_target and len(collected_candidates) >= candidate_target:
            break

    return ScaleBatch(
        name=name,
        requested_published_pages=published_target,
        published_pages=tuple(collected_published),
        candidate_pages=tuple(collected_candidates),
        rejected_pages=tuple(rejected_pages),
    )


def generate_first_scale_batch() -> ScaleBatch:
    return generate_scale_batch(
        name="first_scale_batch",
        published_target=FIRST_SCALE_BATCH_SIZE,
        candidate_target=120,
        candidate_every=11,
    )


def generate_second_scale_batch() -> ScaleBatch:
    return generate_scale_batch(
        name="second_scale_batch",
        published_target=SECOND_SCALE_BATCH_SIZE,
        candidate_target=1_200,
        candidate_every=11,
    )


def build_100k_registry() -> ScaleRegistry:
    return build_registry_for_100k(candidate_every=11)
