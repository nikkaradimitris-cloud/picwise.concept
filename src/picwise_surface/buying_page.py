from __future__ import annotations

from html import escape

from picwise_buying_pages import BuyingPage, evaluate_index_gate


def _build_card_html(page: BuyingPage) -> str:
    cards: list[str] = []
    for product in page.products:
        recommended = product.product_id == page.recommended_product_id
        recommended_badge = (
            '<p class="pw-rec-badge">Recommended by PickWise</p>' if recommended else ""
        )
        rating = f"{product.rating:.1f}" if product.rating is not None else "N/A"
        reviews = str(product.reviews_count) if product.reviews_count is not None else "-"
        brand = escape(product.brand or "Unknown")
        cards.append(
            "".join(
                (
                    f'<article class="pw-card{" pw-card-recommended" if recommended else ""}">',
                    recommended_badge,
                    f'<p class="pw-card-brand">{brand}</p>',
                    f'<h2 class="pw-card-title">{escape(product.title)}</h2>',
                    f'<p class="pw-price">{escape(product.currency)} {product.price:.2f}</p>',
                    f'<p class="pw-rating">Rating: {escape(rating)} ({escape(reviews)} reviews)</p>',
                    f'<p class="pw-summary">{escape(product.reason_summary)}</p>',
                    f'<p class="pw-reason">{escape(product.buying_reason)}</p>',
                    f'<a class="pw-cta" href="{escape(product.product_url)}" rel="nofollow noopener">View option</a>',
                    "</article>",
                )
            )
        )
    return "".join(cards)


def render_buying_page_surface(page: BuyingPage) -> str:
    gate = evaluate_index_gate(page)
    robots = gate.robots_meta_value
    canonical_url = f"https://picwise.subby.cloud/best/{page.slug}"
    main_keyword = escape(page.main_keyword)
    faq_html = "".join(
        (
            "<details class=\"pw-faq-item\">"
            f"<summary>{escape(item.question)}</summary>"
            f"<p>{escape(item.answer)}</p>"
            "</details>"
        )
        for item in page.faq_items
    )
    related_html = "".join(
        f'<li><a href="/best/{escape(page.slug)}?q={escape(search)}">{escape(search)}</a></li>'
        for search in page.related_searches
    )
    card_html = _build_card_html(page)
    index_marker = "indexable" if gate.indexable else "noindex"
    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Best options for {main_keyword} | PickWise</title>"
        f'<meta name="description" content="Compare 4 curated options for {main_keyword} on PickWise.">'
        f'<meta name="robots" content="{robots}">'
        f'<link rel="canonical" href="{canonical_url}">'
        "<style>"
        "*{box-sizing:border-box;}body{margin:0;background:#f6f8fc;color:#15233f;font-family:Inter,Segoe UI,Arial,sans-serif;}"
        ".pw-shell{max-width:1180px;margin:0 auto;padding:16px 18px 24px;}"
        ".pw-topbar{display:flex;justify-content:flex-end;gap:12px;margin-bottom:18px;}"
        ".pw-topbar a{border:1px solid #d3dced;border-radius:999px;padding:8px 14px;color:#1a3766;text-decoration:none;font-size:14px;}"
        ".pw-brand{text-align:center;margin-bottom:16px;}"
        ".pw-brand-logo{font-size:34px;font-weight:800;letter-spacing:-0.02em;text-transform:lowercase;}"
        ".pw-brand-sub{font-size:12px;color:#4a638f;}"
        ".pw-search{max-width:760px;margin:0 auto 14px;display:flex;border:1px solid #d3dced;border-radius:999px;background:#fff;overflow:hidden;}"
        ".pw-search input{flex:1;border:0;padding:14px 16px;font-size:16px;outline:none;background:transparent;}"
        ".pw-search button{border:0;background:#1f6dff;color:#fff;padding:0 18px;font-weight:700;}"
        ".pw-query{text-align:center;margin:10px 0 18px;color:#2a4166;}"
        ".pw-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;}"
        ".pw-card{background:#fff;border:1px solid #d9e2f2;border-radius:14px;padding:14px;display:flex;flex-direction:column;min-height:330px;}"
        ".pw-card-recommended{border-color:#1f6dff;}"
        ".pw-rec-badge{margin:0 0 8px;color:#1f6dff;font-size:12px;font-weight:700;}"
        ".pw-card-brand{margin:0 0 6px;font-size:12px;color:#5a6d8f;}"
        ".pw-card-title{margin:0 0 8px;font-size:20px;line-height:1.2;}"
        ".pw-price{margin:0 0 8px;font-weight:700;color:#1f6dff;}"
        ".pw-rating,.pw-summary,.pw-reason{margin:0 0 8px;font-size:13px;line-height:1.35;color:#32496f;}"
        ".pw-cta{margin-top:auto;border:1px solid #1f6dff;border-radius:10px;padding:10px 12px;text-align:center;text-decoration:none;color:#1f6dff;font-weight:700;}"
        ".pw-meta{margin-top:14px;font-size:12px;color:#5b6b86;text-align:center;}"
        ".pw-block{margin-top:20px;background:#fff;border:1px solid #d9e2f2;border-radius:14px;padding:16px;}"
        ".pw-block h3{margin:0 0 10px;font-size:18px;}"
        ".pw-faq-item{border-top:1px solid #e4eaf5;padding:8px 0;}"
        ".pw-faq-item:first-of-type{border-top:0;padding-top:0;}"
        ".pw-faq-item summary{cursor:pointer;font-weight:600;}"
        ".pw-related{margin:0;padding-left:18px;}"
        ".pw-related li{margin:6px 0;}"
        ".pw-related a{color:#1f6dff;text-decoration:none;}"
        "@media (max-width:1024px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}"
        "@media (max-width:640px){.pw-grid{grid-template-columns:1fr;}}"
        "</style></head><body>"
        f'<main class="pw-shell" data-index-status="{index_marker}">'
        '<header class="pw-topbar">'
        '<a href="#">Login</a>'
        '<a href="#">Register</a>'
        '<a href="#pw-about">What is Picwise</a>'
        "</header>"
        '<section class="pw-brand" id="pw-about">'
        '<div class="pw-brand-logo">picwise</div>'
        '<div class="pw-brand-sub">shopping assistant</div>'
        "</section>"
        '<form class="pw-search" method="get" action="/best">'
        f'<input type="search" name="q" value="{main_keyword}" placeholder="Search your product here">'
        '<button type="submit">Search</button>'
        "</form>"
        f'<p class="pw-query">Showing 4 options for: {main_keyword}</p>'
        f'<section class="pw-grid" data-card-count="{len(page.products)}">{card_html}</section>'
        '<section class="pw-block"><h3>FAQ</h3>'
        f"{faq_html}</section>"
        '<section class="pw-block"><h3>Related searches</h3>'
        f'<ul class="pw-related">{related_html}</ul></section>'
        f'<p class="pw-meta">Last updated: {page.last_updated.date().isoformat()}</p>'
        f'<p class="pw-meta">Index status: {index_marker}</p>'
        "</main></body></html>"
    )
