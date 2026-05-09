from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    BuyingPage,
    FAQItem,
    IndexStatus,
    ProductSlot,
    RefreshMetadata,
    RefreshStatus,
)
from .slugging import slugify_keyword


def _faq(question: str, answer: str) -> FAQItem:
    return FAQItem(question=question, answer=answer)


def _product(
    product_id: str,
    title: str,
    *,
    price: float,
    currency: str,
    summary: str,
    reason: str,
    brand: str | None = None,
) -> ProductSlot:
    return ProductSlot(
        product_id=product_id,
        title=title,
        brand=brand,
        price=price,
        currency=currency,
        image_url=f"https://cdn.picwise.dev/products/{product_id}.jpg",
        product_url=f"https://example.com/products/{product_id}",
        affiliate_url=f"https://affiliate.example.com/go/{product_id}",
        rating=4.5,
        reviews_count=250,
        availability="in_stock",
        reason_summary=summary,
        buying_reason=reason,
    )


def load_seed_buying_pages() -> tuple[BuyingPage, ...]:
    updated_at = datetime(2026, 5, 8, 18, 0, tzinfo=timezone.utc)
    refresh = RefreshMetadata(
        refresh_status=RefreshStatus.FRESH,
        refresh_interval_hours=72,
        next_refresh_at=datetime(2026, 5, 11, 18, 0, tzinfo=timezone.utc),
        last_refresh_at=datetime(2026, 5, 8, 18, 0, tzinfo=timezone.utc),
        refresh_reason="seed_refresh",
    )

    page_power_bank = BuyingPage(
        slug=slugify_keyword("power bank 20000mah for iphone"),
        main_keyword="power bank 20000mah for iphone",
        keyword_aliases=(
            "best 20000mah powerbank iphone",
            "iphone power bank 20k mah",
        ),
        category="electronics",
        products=(
            _product(
                "pb-1",
                "Anker 20K Power Bank",
                brand="Anker",
                price=89.0,
                currency="EUR",
                summary="Reliable battery and fast USB-C output.",
                reason="Balanced specs with strong compatibility.",
            ),
            _product(
                "pb-2",
                "INIU 20000mAh Charger",
                brand="INIU",
                price=99.0,
                currency="EUR",
                summary="Compact body with pass-through charging.",
                reason="Great value for daily iPhone use.",
            ),
            _product(
                "pb-3",
                "UGREEN 20K Fast Charge",
                brand="UGREEN",
                price=129.0,
                currency="EUR",
                summary="High-output charging for newer iPhones.",
                reason="Faster top-ups when commuting.",
            ),
            _product(
                "pb-4",
                "Belkin BoostCharge 20K",
                brand="Belkin",
                price=149.0,
                currency="EUR",
                summary="Premium finish with known safety profile.",
                reason="Best for users prioritizing brand trust.",
            ),
        ),
        recommended_product_id="pb-2",
        faq_items=(
            _faq("Is 20000mAh enough for travel?", "Yes, usually multiple full iPhone charges."),
            _faq("Can I carry this on a flight?", "Yes, these capacities are usually cabin-allowed."),
        ),
        related_searches=(
            "best usb c power bank for iphone",
            "lightweight power bank for iphone",
        ),
        index_status=IndexStatus.INDEXABLE,
        last_updated=updated_at,
        refresh_metadata=refresh,
        price_band_applicable=True,
        target_price_min_eur=80.0,
        target_price_max_eur=250.0,
    )

    page_casio = BuyingPage(
        slug=slugify_keyword("kompiouteraki casio gia panellinies"),
        main_keyword="kompiouteraki casio gia panellinies",
        keyword_aliases=(
            "casio calculator panellinies",
            "best casio for panellinies exams",
        ),
        category="education_tools",
        products=(
            _product(
                "cs-1",
                "Casio fx-991EX",
                brand="Casio",
                price=82.0,
                currency="EUR",
                summary="Exam-friendly model with broad function support.",
                reason="Safe and widely used exam choice.",
            ),
            _product(
                "cs-2",
                "Casio fx-82ES Plus",
                brand="Casio",
                price=88.0,
                currency="EUR",
                summary="Simple interface and clear display.",
                reason="Easy to use under time pressure.",
            ),
            _product(
                "cs-3",
                "Casio fx-570ES Plus",
                brand="Casio",
                price=95.0,
                currency="EUR",
                summary="Useful scientific functions for practice sets.",
                reason="Good bridge between school and exam prep.",
            ),
            _product(
                "cs-4",
                "Casio ClassWiz fx-991CW",
                brand="Casio",
                price=119.0,
                currency="EUR",
                summary="Modern ClassWiz interface with speed improvements.",
                reason="Best for students wanting latest UI.",
            ),
        ),
        recommended_product_id="cs-1",
        faq_items=(
            _faq("Are Casio calculators allowed?", "Check the latest ministry-approved model list."),
            _faq("Should I buy a backup unit?", "A backup is useful during intensive exam prep."),
        ),
        related_searches=(
            "panellinies calculator rules",
            "casio exam approved list greece",
        ),
        index_status=IndexStatus.INDEXABLE,
        last_updated=updated_at,
        refresh_metadata=refresh,
        price_band_applicable=True,
        target_price_min_eur=80.0,
        target_price_max_eur=250.0,
    )

    page_dashcam = BuyingPage(
        slug=slugify_keyword("dash cam gia taxi"),
        main_keyword="dash cam gia taxi",
        keyword_aliases=(
            "best dash cam for taxi drivers",
            "dash camera professional taxi",
        ),
        category="automotive",
        products=(
            _product(
                "dc-1",
                "70mai A500S Pro Plus+",
                brand="70mai",
                price=109.0,
                currency="EUR",
                summary="Front and rear recording with GPS support.",
                reason="Solid all-around setup for city taxi shifts.",
            ),
            _product(
                "dc-2",
                "Viofo A129 Duo",
                brand="Viofo",
                price=139.0,
                currency="EUR",
                summary="Good low-light clarity and dual-channel capture.",
                reason="Reliable evidence quality in night traffic.",
            ),
            _product(
                "dc-3",
                "Nextbase 422GW",
                brand="Nextbase",
                price=189.0,
                currency="EUR",
                summary="Emergency SOS features and clear app workflow.",
                reason="Useful feature set for professional drivers.",
            ),
            _product(
                "dc-4",
                "Garmin Dash Cam 57",
                brand="Garmin",
                price=229.0,
                currency="EUR",
                summary="Compact unit with strong lens quality.",
                reason="Premium option for compact windshield setups.",
            ),
        ),
        recommended_product_id="dc-2",
        faq_items=(
            _faq("Do taxi dash cams need night vision?", "Yes, low-light clarity is essential."),
            _faq("Is rear recording useful for taxis?", "Yes, it helps in rear-impact disputes."),
        ),
        related_searches=(
            "taxi dash cam legal greece",
            "best dual dash cam for urban driving",
        ),
        index_status=IndexStatus.NOINDEX,
        last_updated=updated_at,
        refresh_metadata=refresh,
        price_band_applicable=False,
        target_price_min_eur=None,
        target_price_max_eur=None,
    )

    return (page_power_bank, page_casio, page_dashcam)
