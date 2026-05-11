from __future__ import annotations

from html import escape

from picwise_buying_pages.seo_contracts import SEOIndexStatus, SEOBuyingPage


def _render_product_cards(page: SEOBuyingPage) -> str:
    cards: list[str] = []
    wise_id = page.wise_recommended_product.candidate_id if page.wise_recommended_product else None
    for slot in page.display_slots:
        recommended = bool(wise_id and slot.candidate_id == wise_id)
        badge = '<p class="pw-badge">Wise Recommended</p>' if recommended else ""
        price = f"{slot.currency} {slot.price:.2f}" if slot.price is not None and slot.currency else "price_not_connected"
        cards.append(
            "".join(
                (
                    '<article class="pw-card">',
                    badge,
                    f"<h2>{escape(slot.title)}</h2>",
                    f"<p><strong>Seller:</strong> {escape(slot.seller_name or 'not_connected')}</p>",
                    f"<p><strong>Price:</strong> {escape(price)}</p>",
                    f"<p><strong>Availability:</strong> {escape(slot.availability_status or 'not_available')}</p>",
                    f'<a href="{escape(slot.outbound_url or "#")}" rel="nofollow noopener">View option</a>',
                    "</article>",
                )
            )
        )
    return "".join(cards)


def render_buying_page_seo_surface(page: SEOBuyingPage) -> str:
    title = escape(str(page.metadata.get("title") or f"Best options for {page.main_keyword} | PickWise"))
    description = escape(
        str(
            page.metadata.get("description")
            or f"Compare eligible product options for {page.main_keyword} with deterministic PickWise data."
        )
    )
    robots = page.robots_meta
    canonical_url = f"https://picwise.subby.cloud{page.canonical_path}"
    noindex_notice = ""
    if page.index_status != SEOIndexStatus.INDEXABLE:
        reason = escape(str(page.noindex_reason or "not_ready"))
        noindex_notice = f'<section class="pw-state"><p>This page is not indexable yet: {reason}</p></section>'

    cards_html = _render_product_cards(page) if page.valid_product_count > 0 else ""
    if not cards_html:
        cards_html = (
            '<section class="pw-state">'
            "<p>No eligible product cards are published for this page yet.</p>"
            "</section>"
        )
    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title>"
        f'<meta name="description" content="{description}">'
        f'<meta name="robots" content="{robots}">'
        f'<link rel="canonical" href="{canonical_url}">'
        "</head><body>"
        "<main>"
        f"<h1>{escape(page.main_keyword)}</h1>"
        f"{noindex_notice}"
        f"{cards_html}"
        "</main></body></html>"
    )
