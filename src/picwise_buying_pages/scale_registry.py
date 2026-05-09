from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .models import ApprovalStatus, BuyingPage, FAQItem, IndexStatus, ProductSlot, RefreshMetadata, RefreshStatus
from .slugging import normalize_keyword_text

SCALE_100K_TARGET_DISTRIBUTION: tuple[tuple[str, int, bool, tuple[str, ...]], ...] = (
    (
        "electronics/gadgets",
        25_000,
        True,
        (
            "power bank 20000mah for iphone",
            "noise cancelling earbuds for commuting",
            "bluetooth speaker for balcony evenings",
            "wireless charger stand for pixel phones",
            "smartwatch for swimming and workouts",
        ),
    ),
    (
        "home/appliances",
        20_000,
        True,
        (
            "air fryer for small kitchen families",
            "robot vacuum for pet hair cleaning",
            "dehumidifier for apartment humidity control",
            "espresso machine for home office mornings",
            "silent blender for baby food prep",
        ),
    ),
    (
        "car/taxi/accessories",
        15_000,
        True,
        (
            "dash cam gia taxi",
            "phone mount for taxi windshield safety",
            "seat cushion for long driving shifts",
            "usb c car charger for ride share",
            "car vacuum cleaner for daily interior care",
        ),
    ),
    (
        "tools/DIY",
        15_000,
        True,
        (
            "kompiouteraki casio gia panellinies",
            "cordless drill for apartment repairs",
            "laser level for kitchen renovation",
            "tool set for beginner diy projects",
            "soldering kit for electronics hobby",
        ),
    ),
    (
        "beauty/fitness/lifestyle",
        10_000,
        True,
        (
            "hair dryer for curly hair care",
            "fitness tracker for calorie monitoring",
            "massage gun for post workout recovery",
            "yoga mat non slip for hot yoga",
            "straightener for thick frizzy hair",
        ),
    ),
    (
        "baby/pet",
        10_000,
        True,
        (
            "baby monitor with night vision audio",
            "stroller for city sidewalks compact fold",
            "pet water fountain for multiple cats",
            "automatic pet feeder with app timer",
            "baby carrier ergonomic for newborn walks",
        ),
    ),
    (
        "software/programs",
        3_000,
        False,
        (
            "crm software for freelance sales teams",
            "invoice software for taxi drivers",
            "project management software for remote teams",
            "photo editing program for beginners",
            "password manager for small businesses",
        ),
    ),
    (
        "insurance/lead-gen",
        2_000,
        False,
        (
            "car insurance plans for new drivers",
            "travel insurance offers for europe trips",
            "health insurance comparison for freelancers",
            "pet insurance providers for senior dogs",
            "home insurance quotes for apartments",
        ),
    ),
)

SCALE_100K_TOTAL_TARGET = sum(row[1] for row in SCALE_100K_TARGET_DISTRIBUTION)


@dataclass(frozen=True)
class ScalePageDescriptor:
    ordinal: int
    category: str
    category_ordinal: int
    main_keyword: str
    price_band_applicable: bool
    candidate_only: bool


def get_100k_distribution() -> dict[str, int]:
    return {category: count for category, count, _price_band, _stems in SCALE_100K_TARGET_DISTRIBUTION}


def _project_distribution(total_pages: int) -> tuple[tuple[str, int, bool, tuple[str, ...]], ...]:
    if total_pages <= 0:
        return tuple()
    if total_pages == SCALE_100K_TOTAL_TARGET:
        return SCALE_100K_TARGET_DISTRIBUTION

    projected: list[list[object]] = []
    assigned = 0
    remainders: list[tuple[int, int]] = []
    for idx, (category, count_100k, price_band, stems) in enumerate(SCALE_100K_TARGET_DISTRIBUTION):
        scaled_raw = (total_pages * count_100k) / SCALE_100K_TOTAL_TARGET
        scaled_floor = int(scaled_raw)
        projected.append([category, scaled_floor, price_band, stems])
        assigned += scaled_floor
        fractional = int(round((scaled_raw - scaled_floor) * 1_000_000))
        remainders.append((fractional, idx))

    missing = total_pages - assigned
    for _fractional, idx in sorted(remainders, key=lambda row: (-row[0], row[1]))[:missing]:
        projected[idx][1] = int(projected[idx][1]) + 1

    return tuple(
        (str(category), int(count), bool(price_band), tuple(stems))
        for category, count, price_band, stems in projected
        if int(count) > 0
    )


def _build_keyword(stems: tuple[str, ...], category: str, category_ordinal: int) -> str:
    stem = stems[category_ordinal % len(stems)]
    variant = category_ordinal // len(stems) + 1
    category_tag = normalize_keyword_text(category).replace(" ", "-")
    return f"{stem} scale-{category_tag}-{variant:05d}"


def _build_aliases(main_keyword: str, ordinal: int) -> tuple[str, ...]:
    serial = f"s{ordinal + 1:06d}"
    alias_candidates = (
        f"{main_keyword} best options {serial}",
        f"{main_keyword} comparison {serial}",
        f"{main_keyword} buyer intent {serial}",
        f"{main_keyword} top picks {serial}",
        f"{main_keyword} shortlist {serial}",
        f"{main_keyword} buying page {serial}",
        f"{main_keyword} practical guide {serial}",
        f"{main_keyword} value picks {serial}",
        f"{main_keyword} trusted choices {serial}",
        f"{main_keyword} route demo {serial}",
        f"{main_keyword} route demo {serial}",
        f"{main_keyword} shortlist {serial}",
    )
    deduped: list[str] = []
    seen: set[str] = set()
    for alias in alias_candidates:
        normalized = normalize_keyword_text(alias)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
        if len(deduped) == 10:
            break
    return tuple(deduped)


def _build_products(slug: str, category: str, ordinal: int, price_band_applicable: bool) -> tuple[ProductSlot, ...]:
    products: list[ProductSlot] = []
    for slot in range(4):
        serial = ordinal * 4 + slot + 1
        product_id = f"scale-{serial:07d}"
        if price_band_applicable:
            price = float(80 + ((ordinal * 13 + slot * 29) % 171))
        else:
            price = float(19 + ((ordinal * 11 + slot * 17) % 181))
        products.append(
            ProductSlot(
                product_id=product_id,
                title=f"{category.split('/')[0].title()} Option {slot + 1}",
                brand="Picwise Scale Fixture",
                price=price,
                currency="EUR",
                image_url=f"https://assets.example.com/picwise/{slug}-{slot + 1}.jpg",
                product_url=f"https://example.com/best/{slug}/option-{slot + 1}",
                affiliate_url=f"https://affiliate.example.com/best/{slug}/option-{slot + 1}",
                rating=4.0 + (slot * 0.2),
                reviews_count=120 + ordinal + slot * 11,
                availability="in_stock",
                reason_summary="Deterministic scale batch option suitable for comparison pages.",
                buying_reason="Generated from the deterministic scale registry for predictable testing.",
            )
        )
    return tuple(products)


def build_buying_page_from_descriptor(descriptor: ScalePageDescriptor) -> BuyingPage:
    updated_at = datetime(2026, 5, 9, 8, 0, tzinfo=timezone.utc) + timedelta(
        minutes=descriptor.ordinal % 1440
    )
    slug = normalize_keyword_text(descriptor.main_keyword).replace(" ", "-")
    products = _build_products(
        slug=slug,
        category=descriptor.category,
        ordinal=descriptor.ordinal,
        price_band_applicable=descriptor.price_band_applicable,
    )
    refresh = RefreshMetadata(
        refresh_status=RefreshStatus.FRESH,
        refresh_interval_hours=72,
        next_refresh_at=updated_at + timedelta(hours=72),
        last_refresh_at=updated_at,
        refresh_reason="deterministic_scale_registry",
    )
    return BuyingPage(
        slug=slug,
        main_keyword=descriptor.main_keyword,
        keyword_aliases=_build_aliases(descriptor.main_keyword, descriptor.ordinal),
        category=descriptor.category,
        products=products,
        recommended_product_id=products[(descriptor.ordinal + 1) % 4].product_id,
        faq_items=(
            FAQItem(
                question=f"What matters most for {descriptor.main_keyword}?",
                answer="Prioritize fit, transparent terms, and reliable product availability.",
            ),
            FAQItem(
                question=f"How frequently is {descriptor.main_keyword} refreshed?",
                answer="Scale fixtures refresh deterministically on a fixed interval.",
            ),
        ),
        related_searches=(
            f"alternatives to {descriptor.main_keyword}",
            f"budget picks for {descriptor.main_keyword}",
            f"premium choices for {descriptor.main_keyword}",
        ),
        index_status=IndexStatus.NOINDEX if descriptor.candidate_only else IndexStatus.INDEXABLE,
        last_updated=updated_at,
        refresh_metadata=refresh,
        price_band_applicable=descriptor.price_band_applicable,
        target_price_min_eur=80.0 if descriptor.price_band_applicable else None,
        target_price_max_eur=250.0 if descriptor.price_band_applicable else None,
        approval_status=(
            ApprovalStatus.PENDING_REVIEW if descriptor.candidate_only else ApprovalStatus.APPROVED
        ),
    )


class ScaleRegistry:
    def __init__(self, *, total_pages: int, candidate_every: int = 11) -> None:
        if total_pages <= 0:
            raise ValueError("total_pages must be > 0.")
        if candidate_every <= 0:
            raise ValueError("candidate_every must be > 0.")
        self.total_pages = int(total_pages)
        self.candidate_every = int(candidate_every)
        self.distribution = _project_distribution(self.total_pages)
        self._ranges: list[tuple[int, int, str, bool, tuple[str, ...]]] = []
        cursor = 0
        for category, count, price_band, stems in self.distribution:
            end = cursor + count
            self._ranges.append((cursor, end, category, price_band, stems))
            cursor = end

    def descriptor_at(self, ordinal: int) -> ScalePageDescriptor:
        if ordinal < 0 or ordinal >= self.total_pages:
            raise IndexError(f"ordinal {ordinal} out of range 0..{self.total_pages - 1}")
        for start, end, category, price_band, stems in self._ranges:
            if start <= ordinal < end:
                category_ordinal = ordinal - start
                return ScalePageDescriptor(
                    ordinal=ordinal,
                    category=category,
                    category_ordinal=category_ordinal,
                    main_keyword=_build_keyword(stems, category, category_ordinal),
                    price_band_applicable=price_band,
                    candidate_only=((ordinal + 1) % self.candidate_every == 0),
                )
        raise RuntimeError("Unable to resolve category range for ordinal.")

    def iter_descriptors(self) -> Iterator[ScalePageDescriptor]:
        for ordinal in range(self.total_pages):
            yield self.descriptor_at(ordinal)

    def iter_pages(self, *, include_candidates: bool = True) -> Iterator[BuyingPage]:
        for descriptor in self.iter_descriptors():
            if not include_candidates and descriptor.candidate_only:
                continue
            yield build_buying_page_from_descriptor(descriptor)

    def list_pages(self, *, include_candidates: bool = True) -> tuple[BuyingPage, ...]:
        return tuple(self.iter_pages(include_candidates=include_candidates))


def build_registry_for_100k(*, candidate_every: int = 11) -> ScaleRegistry:
    return ScaleRegistry(total_pages=SCALE_100K_TOTAL_TARGET, candidate_every=candidate_every)


def iter_pages_from_registry(
    registry: ScaleRegistry,
    *,
    include_candidates: bool = True,
) -> Iterable[BuyingPage]:
    return registry.iter_pages(include_candidates=include_candidates)
