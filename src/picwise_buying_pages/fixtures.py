from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from .models import (
    ApprovalStatus,
    BuyingPage,
    FAQItem,
    IndexStatus,
    ProductSlot,
    RefreshMetadata,
    RefreshStatus,
    SellerReliabilityStatus,
)
from .slugging import slugify_keyword

_FIXTURE_UPDATED_AT = datetime(2026, 5, 9, 8, 0, tzinfo=timezone.utc)
_FIXTURE_REFRESH = RefreshMetadata(
    refresh_status=RefreshStatus.FRESH,
    refresh_interval_hours=72,
    next_refresh_at=datetime(2026, 5, 12, 8, 0, tzinfo=timezone.utc),
    last_refresh_at=_FIXTURE_UPDATED_AT,
    refresh_reason="deterministic_seed_refresh",
)

_CATEGORY_BLUEPRINTS: tuple[tuple[str, bool, int, tuple[str, ...]], ...] = (
    (
        "electronics/gadgets",
        True,
        13,
        (
            "power bank 20000mah for iphone",
            "noise cancelling earbuds for commuting",
            "bluetooth speaker for balcony evenings",
            "wireless charger stand for pixel phones",
            "smartwatch for swimming and workouts",
            "gaming mouse for competitive fps",
            "portable monitor for laptop travel",
        ),
    ),
    (
        "home/appliances",
        True,
        13,
        (
            "air fryer for small kitchen families",
            "robot vacuum for pet hair cleaning",
            "dehumidifier for apartment humidity control",
            "espresso machine for home office mornings",
            "silent blender for baby food prep",
            "portable heater for winter desk setup",
            "dishwasher countertop model for studio",
        ),
    ),
    (
        "car/taxi/accessories",
        True,
        13,
        (
            "dash cam gia taxi",
            "phone mount for taxi windshield safety",
            "seat cushion for long driving shifts",
            "usb c car charger for ride share",
            "car vacuum cleaner for daily interior care",
            "gps tracker for fleet cars",
            "tire inflator for emergency roadside use",
        ),
    ),
    (
        "tools/DIY",
        True,
        13,
        (
            "kompiouteraki casio gia panellinies",
            "cordless drill for apartment repairs",
            "laser level for kitchen renovation",
            "tool set for beginner diy projects",
            "soldering kit for electronics hobby",
            "pressure washer for patio cleaning",
            "multimeter for home electrical checks",
        ),
    ),
    (
        "beauty/fitness/lifestyle",
        True,
        12,
        (
            "hair dryer for curly hair care",
            "fitness tracker for calorie monitoring",
            "massage gun for post workout recovery",
            "yoga mat non slip for hot yoga",
            "straightener for thick frizzy hair",
            "electric toothbrush for sensitive gums",
            "standing desk converter for home setup",
        ),
    ),
    (
        "baby/pet",
        True,
        12,
        (
            "baby monitor with night vision audio",
            "stroller for city sidewalks compact fold",
            "pet water fountain for multiple cats",
            "automatic pet feeder with app timer",
            "baby carrier ergonomic for newborn walks",
            "pet grooming kit for long hair dogs",
            "air purifier for nursery with pets",
        ),
    ),
    (
        "software/programs",
        False,
        12,
        (
            "crm software for freelance sales teams",
            "invoice software for taxi drivers",
            "project management software for remote teams",
            "photo editing program for beginners",
            "password manager for small businesses",
            "online booking software for salons",
            "accounting software for startups",
        ),
    ),
    (
        "insurance/lead-gen",
        False,
        12,
        (
            "car insurance plans for new drivers",
            "travel insurance offers for europe trips",
            "health insurance comparison for freelancers",
            "pet insurance providers for senior dogs",
            "home insurance quotes for apartments",
            "business liability insurance for consultants",
            "life insurance plans for young families",
        ),
    ),
)


def _iter_main_keywords() -> Iterable[tuple[str, str, bool]]:
    for category, price_band_applicable, expected_count, stems in _CATEGORY_BLUEPRINTS:
        for idx in range(expected_count):
            stem = stems[idx % len(stems)]
            variant = idx // len(stems)
            keyword = stem if variant == 0 else f"{stem} guide {variant + 1}"
            yield keyword, category, price_band_applicable


def _build_aliases(main_keyword: str, page_index: int) -> tuple[str, ...]:
    base = main_keyword
    serial = f"sample-{page_index + 1:03d}"
    return (
        f"{base} best options {serial}",
        f"{base} comparison {serial}",
        f"{base} buyer intent {serial}",
        f"{base} top picks {serial}",
        f"{base} practical shortlist {serial}",
        f"{base} buying page {serial}",
        f"{base} decision helper {serial}",
        f"{base} value picks {serial}",
        f"{base} trusted choices {serial}",
        f"{base} route demo {serial}",
    )


def _build_products(slug: str, category: str, page_index: int, price_band_applicable: bool) -> tuple[ProductSlot, ...]:
    products: list[ProductSlot] = []
    for slot_index in range(4):
        product_serial = page_index * 4 + slot_index + 1
        product_id = f"pw-{product_serial:04d}"
        if price_band_applicable:
            price = float(80 + ((page_index * 17 + slot_index * 31) % 171))
            currency = "EUR"
            title = f"{category.split('/')[0].title()} Option {slot_index + 1}"
            reason_summary = "Balanced physical product fit for this buying intent."
            buying_reason = "Within the target 80-250 EUR range and suitable for quick comparison."
        else:
            price = float(19 + ((page_index * 11 + slot_index * 19) % 181))
            currency = "EUR"
            title = f"{category.split('/')[0].title()} Offer {slot_index + 1}"
            reason_summary = "Representative plan/provider offer for this non-physical intent."
            buying_reason = "Valid offer slot for demo evaluation where physical price band is not required."

        products.append(
            ProductSlot(
                product_id=product_id,
                title=title,
                brand="Picwise Demo",
                price=price,
                currency=currency,
                image_url=f"https://assets.example.com/picwise/{slug}-{slot_index + 1}.jpg",
                product_url=f"https://example.com/best/{slug}/option-{slot_index + 1}",
                affiliate_url=f"https://affiliate.example.com/best/{slug}/option-{slot_index + 1}",
                rating=4.1 + (slot_index * 0.2),
                reviews_count=80 + page_index * 3 + slot_index * 17,
                availability="in_stock",
                reason_summary=reason_summary,
                buying_reason=buying_reason,
                short_description=f"{title} shortlist pick for {slug}.",
                specifications=(
                    f"Category: {category}",
                    f"Variant: option-{slot_index + 1}",
                    "Renderer-safe image and pricing metadata",
                ),
                model_code=f"PW-{slug.upper()}-{slot_index + 1}",
                seller_name=f"PickWise Partner {((page_index + slot_index) % 5) + 1}",
                seller_id=f"seller-{(page_index % 37) + 1:03d}",
                seller_reliability_status=(
                    SellerReliabilityStatus.TRUSTED
                    if slot_index in (0, 2)
                    else SellerReliabilityStatus.ACCEPTABLE
                ),
                seller_rating=4.2 + (slot_index * 0.15),
                seller_reviews_count=140 + page_index * 2 + slot_index * 9,
                return_policy_available=True,
                shipping_info_available=True,
                comparison_family=f"{slug}-family",
                comparison_useful=True,
            )
        )
    return tuple(products)


def _build_page(main_keyword: str, category: str, page_index: int, price_band_applicable: bool) -> BuyingPage:
    slug = slugify_keyword(main_keyword)
    products = _build_products(slug, category, page_index, price_band_applicable)
    recommended_product_id = products[(page_index + 1) % 4].product_id
    index_status = IndexStatus.NOINDEX if (page_index + 1) % 19 == 0 else IndexStatus.INDEXABLE
    faq_items = (
        FAQItem(
            question=f"What should I prioritize for {main_keyword}?",
            answer="Prioritize reliability, transparent pricing, and clear fit to your use case.",
        ),
        FAQItem(
            question=f"How often is this {main_keyword} page refreshed?",
            answer="Fixture pages refresh on a deterministic schedule for testing and demos.",
        ),
    )
    related_searches = (
        f"alternatives to {main_keyword}",
        f"budget picks for {main_keyword}",
        f"premium choices for {main_keyword}",
    )
    return BuyingPage(
        slug=slug,
        main_keyword=main_keyword,
        keyword_aliases=_build_aliases(main_keyword, page_index),
        category=category,
        products=products,
        recommended_product_id=recommended_product_id,
        faq_items=faq_items,
        related_searches=related_searches,
        index_status=index_status,
        last_updated=_FIXTURE_UPDATED_AT,
        refresh_metadata=_FIXTURE_REFRESH,
        price_band_applicable=price_band_applicable,
        target_price_min_eur=80.0 if price_band_applicable else None,
        target_price_max_eur=250.0 if price_band_applicable else None,
        approval_status=ApprovalStatus.APPROVED,
    )


def load_seed_buying_pages() -> tuple[BuyingPage, ...]:
    pages = tuple(
        _build_page(main_keyword, category, page_index, price_band_applicable)
        for page_index, (main_keyword, category, price_band_applicable) in enumerate(_iter_main_keywords())
    )
    if len(pages) != 100:
        raise RuntimeError(f"Expected deterministic 100 pages, got {len(pages)}.")
    return pages
