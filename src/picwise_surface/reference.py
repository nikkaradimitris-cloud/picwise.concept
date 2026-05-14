from __future__ import annotations

from html import escape

from .legal import render_public_brand_header, render_public_footer


def render_picwise_reference_surface() -> str:
    card_specs = [
        {
            "badge": "BUDGET",
            "badge_class": "pw-badge-budget",
            "name": "TravelCore 20K",
            "description": "Budget pick for occasional travel charging",
            "rating": "4.4",
            "reviews": "(1,248)",
            "price": "EUR 29-34",
            "meta": "Lightweight  ·  Basic reliability",
            "bullets": [
                "Compact size",
                "Simple cable setup",
                "Widely available",
            ],
            "warning": "Lower sustained output under heavy load.",
            "cta": "Preview option",
            "image": "/assets/picwise/product-1.svg",
            "recommended": False,
            "rec_note": "",
        },
        {
            "badge": "VALUE",
            "badge_class": "pw-badge-value",
            "name": "DailyBalance PD20",
            "description": "Value pick with stable everyday compatibility",
            "rating": "4.6",
            "reviews": "(2,317)",
            "price": "EUR 37-45",
            "meta": "USB-C PD  ·  Lower mismatch risk",
            "bullets": [
                "Balanced output",
                "Reliable compatibility",
                "Solid build quality",
            ],
            "warning": "Slightly heavier than compact alternatives.",
            "cta": "Preview option",
            "image": "/assets/picwise/product-2.svg",
            "recommended": False,
            "rec_note": "",
        },
        {
            "badge": "BEST OVERALL",
            "badge_class": "pw-badge-best",
            "name": "EverydaySure 22.5W",
            "description": "Best overall fit for frequent charging routines",
            "rating": "4.7",
            "reviews": "(3,891)",
            "price": "EUR 44-52",
            "meta": "Strong output  ·  Better long-run reliability",
            "bullets": [
                "Consistent charging speed",
                "Good cable support",
                "Trusted warranty terms",
            ],
            "warning": "Price sits above entry-level options.",
            "cta": "Preview recommendation",
            "image": "/assets/picwise/product-3.svg",
            "recommended": False,
            "rec_note": "",
        },
        {
            "badge": "PREMIUM",
            "badge_class": "pw-badge-premium",
            "name": "PowerMax Elite 25K",
            "description": "Premium pick for heavy and multi-device usage",
            "rating": "4.8",
            "reviews": "(5,214)",
            "price": "EUR 59-69",
            "meta": "Higher capacity  ·  Better sustained output",
            "bullets": [
                "High capacity headroom",
                "Premium thermal design",
                "Extended accessory kit",
                "Higher price and larger carry footprint.",
            ],
            "warning": "",
            "cta": "Preview option",
            "image": "/assets/picwise/product-4.svg",
            "recommended": True,
            "rec_note": (
                "Recommended for stronger overall fit: High capacity headroom, "
                "Premium thermal design."
            ),
        },
    ]

    card_html = []
    for idx, card in enumerate(card_specs, start=1):
        rec_class = " pw-card-recommended" if card["recommended"] else ""
        rec_header = (
            '<div class="pw-rec-badge">&#9733; Recommended by PicWise</div>'
            if card["recommended"]
            else ""
        )
        reasons = "".join(
            f'<li class="pw-feature-item"><span class="pw-feature-dot" aria-hidden="true"></span><span>{escape(reason)}</span></li>'
            for reason in card["bullets"]
        )
        warning_html = (
            f'<p class="pw-warning"><span class="pw-warning-icon" aria-hidden="true">&#9651;</span>{escape(card["warning"])}</p>'
            if card["warning"]
            else ""
        )
        rec_note = (
            f'<p class="pw-rec-note">{escape(card["rec_note"])}</p>' if card["rec_note"] else ""
        )
        card_html.append(
            (
                f'<article class="pw-card{rec_class}" data-choice-id="fixed-{idx}">'
                f"{rec_header}"
                f'<span class="pw-badge {card["badge_class"]}">{escape(card["badge"])}</span>'
                f'<h2 class="pw-card-title">{escape(card["name"])}</h2>'
                f'<p class="pw-card-description">{escape(card["description"])}</p>'
                '<p class="pw-rating-row"><span class="pw-rating-number">'
                f'{escape(card["rating"])}</span><span class="pw-stars" aria-hidden="true">&#9733;&#9733;&#9733;&#9733;&#9734;</span>'
                f'<span class="pw-reviews">{escape(card["reviews"])}</span></p>'
                f'<div class="pw-product-image-wrap"><img class="pw-product-image" src="{escape(card["image"])}" alt="{escape(card["name"])} product image"></div>'
                f'<p class="pw-price">{escape(card["price"])}</p>'
                f'<p class="pw-meta">{escape(card["meta"])}</p>'
                f'<ul class="pw-feature-list">{reasons}</ul>'
                f"{warning_html}"
                f"{rec_note}"
                f'<button class="pw-card-cta" type="button">{escape(card["cta"])}</button>'
                "</article>"
            )
        )

    html = (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PicWise Reference — Buying Decision Preview</title>"
        '<meta name="description" content="Preview how PicWise supports product comparison and buying decisions while provider integrations are being configured.">'
        "<style>"
        "*{box-sizing:border-box;}html,body{height:100%;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#0f1f3a;background:#f8fbff;}"
        ".pw-reference-viewport{min-height:100vh;padding:12px;display:flex;justify-content:center;align-items:flex-start;}"
        ".pw-reference-scale-shell{position:relative;display:flex;justify-content:center;width:100%;}"
        ".pw-reference-frame{width:100%;max-width:1280px;padding:18px 24px 26px;position:relative;background:#f8fbff;}"
        ".pw-public-brand-header{display:flex;align-items:flex-start;margin:0 0 26px;}"
        ".pw-public-brand-link{display:inline-flex;align-items:flex-start;gap:10px;color:#1a4fb7;text-decoration:none;}"
        ".pw-public-brand-mark{width:26px;height:26px;display:block;object-fit:contain;margin-top:2px;flex:0 0 auto;}"
        ".pw-public-brand-text{display:flex;flex-direction:column;align-items:flex-start;line-height:1;}"
        ".pw-public-brand-wordmark{font-size:30px;font-weight:800;letter-spacing:-.03em;color:#1a4fb7;}"
        ".pw-public-brand-tagline{margin-top:4px;font-size:12px;letter-spacing:.02em;color:#3a5f8e;line-height:1.2;}"
        ".pw-search-wrap{width:100%;max-width:760px;height:58px;margin:0 auto 24px;}"
        ".pw-search-shell{display:flex;align-items:center;gap:10px;width:100%;height:58px;background:#fff;border:1px solid #dbe8fb;border-radius:999px;padding:0 10px 0 18px;box-shadow:none;filter:none;}"
        ".pw-search-icon,.pw-search-button-icon{position:relative;width:16px;height:16px;display:inline-block;color:#7c93b7;flex:0 0 auto;}"
        ".pw-search-icon::before,.pw-search-button-icon::before{content:'';position:absolute;left:0;top:0;width:10px;height:10px;border:2px solid currentColor;border-radius:999px;}"
        ".pw-search-icon::after,.pw-search-button-icon::after{content:'';position:absolute;right:1px;bottom:2px;width:7px;height:2px;background:currentColor;border-radius:2px;transform:rotate(45deg);transform-origin:right center;}"
        ".pw-search-input{flex:1;height:56px;border:0;background:transparent;outline:none;font-size:19px;color:#95a8c7;font-weight:500;}"
        ".pw-search-button{width:42px;height:42px;border-radius:999px;border:0;background:#1f6dff;display:inline-flex;align-items:center;justify-content:center;box-shadow:none;filter:none;}"
        ".pw-search-button .pw-search-button-icon{color:#fff;}"
        ".pw-query-line{width:100%;max-width:760px;margin:0 auto 44px;text-align:left;font-size:15px;color:#1a3d6b;font-weight:500;}"
        ".pw-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;align-items:start;width:100%;max-width:1190px;margin:0 auto;justify-items:center;}"
        ".pw-card{position:relative;background:#fff;border:1px solid #dbe8fb;border-radius:18px;box-shadow:none;text-shadow:none;filter:none;padding:14px 14px 12px;display:flex;flex-direction:column;min-height:472px;width:100%;max-width:284px;}"
        ".pw-card-recommended{border:2px solid #2f78ff;box-shadow:none;text-shadow:none;filter:none;}"
        ".pw-rec-badge{display:inline-block;background:#2a70f1;color:#fff;font-size:12px;font-weight:700;padding:6px 11px;border-radius:999px;margin-bottom:9px;height:26px;line-height:14px;}"
        ".pw-badge{display:inline-block;align-self:flex-start;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.05em;margin-bottom:8px;height:21px;line-height:13px;}"
        ".pw-badge-budget,.pw-badge-premium{background:#eaf2ff;color:#3f72c4;}"
        ".pw-badge-value{background:#e8f8ec;color:#2f9b57;}"
        ".pw-badge-best{background:#f0ecff;color:#6e57cc;}"
        ".pw-card-title{margin:0;font-size:30px;line-height:1.03;color:#112649;letter-spacing:-.03em;height:62px;}"
        ".pw-card-description{margin:4px 0 8px;font-size:12px;color:#5c7397;line-height:1.35;height:32px;}"
        ".pw-rating-row{margin:0 0 10px;display:flex;align-items:center;gap:5px;font-size:12px;color:#112649;height:14px;}"
        ".pw-stars{font-size:11px;color:#f5b435;letter-spacing:1px;}"
        ".pw-reviews{color:#6f88ac;}"
        ".pw-product-image-wrap{height:84px;margin:0 0 10px;display:flex;align-items:center;justify-content:center;}"
        ".pw-product-image{display:block;width:252px;height:84px;border-radius:12px;border:1px solid #dbe6f6;object-fit:cover;background:#eef3fb;}"
        ".pw-price{margin:0;font-size:26px;line-height:1;font-weight:800;color:#2a70e6;letter-spacing:-.03em;height:30px;}"
        ".pw-meta{margin:3px 0 8px;font-size:12px;color:#6f88ac;height:16px;}"
        ".pw-feature-list{margin:0;padding:0;list-style:none;display:grid;gap:4px;min-height:56px;}"
        ".pw-feature-item{display:flex;align-items:flex-start;gap:7px;font-size:12px;color:#304b70;line-height:1.35;}"
        ".pw-feature-dot{width:8px;height:8px;border-radius:999px;background:#5b8ce5;flex:0 0 auto;margin-top:4px;}"
        ".pw-warning{margin:7px 0 0;font-size:11px;color:#5a7498;line-height:1.3;display:flex;gap:6px;min-height:29px;}"
        ".pw-warning-icon{font-size:10px;color:#6f86ad;line-height:1.2;margin-top:1px;}"
        ".pw-rec-note{margin:8px 0 0;font-size:11px;line-height:1.35;color:#2e4c7d;background:#eef4ff;border-radius:8px;padding:6px 8px;min-height:42px;}"
        ".pw-card-cta{margin-top:auto;width:100%;height:40px;border-radius:11px;border:1px solid #2e75ee;color:#2e75ee;background:#fff;font-size:16px;font-weight:700;}"
        ".pw-card-recommended .pw-card-cta{background:#1f6dff;color:#fff;border-color:#1f6dff;}"
        ".pw-demo-note{text-align:center;font-size:12px;color:#7389ac;margin:16px 0 10px;}"
        ".pw-reference-disclaimer{margin:0 auto 16px;max-width:900px;padding:10px 12px;border:1px solid #dbe8fb;border-radius:12px;background:#f6f9ff;color:#284a76;font-size:14px;line-height:1.6;text-align:center;}"
        "@media (min-width:1100px){.pw-reference-viewport{padding:8px;}.pw-reference-frame{padding:12px 20px 16px;}.pw-public-brand-header{margin:0 0 24px;}.pw-search-wrap{height:52px;margin:0 auto 20px;}.pw-query-line{margin:0 auto 40px;}.pw-card{padding:12px 12px 10px;min-height:444px;}.pw-product-image-wrap{height:74px;margin:0 0 8px;}.pw-product-image{width:228px;height:74px;}}"
        "@media (max-width:1099px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));max-width:760px;}}"
        "@media (max-width:699px){.pw-reference-frame{padding:14px 12px 20px;}.pw-public-brand-header{margin:0 0 24px;}.pw-search-wrap{height:auto;}.pw-search-shell{height:52px;padding:0 8px 0 14px;}.pw-search-input{height:50px;font-size:16px;}.pw-query-line{font-size:14px;margin:0 auto 36px;}.pw-grid{grid-template-columns:1fr;max-width:360px;}.pw-card{max-width:360px;}}"
        ".pw-reference-viewport *,.pw-reference-viewport *::before,.pw-reference-viewport *::after{box-shadow:none!important;text-shadow:none!important;filter:none!important;}"
        "</style></head><body>"
        '<main class="pw-reference-viewport">'
        '<div class="pw-reference-scale-shell" id="pw-reference-scale-shell">'
        '<div class="pw-reference-frame" id="pw-reference-frame">'
        f"{render_public_brand_header()}"
        '<section class="pw-search-wrap" aria-label="Search">'
        '<div class="pw-search-shell">'
        '<span class="pw-search-icon" aria-hidden="true"></span>'
        '<input class="pw-search-input" type="search" placeholder="See the 4 best products before you buy" aria-label="See the 4 best products before you buy" autocomplete="off">'
        '<button class="pw-search-button" type="button" aria-label="Search">'
        '<span class="pw-search-button-icon" aria-hidden="true"></span>'
        "</button></div></section>"
        '<p class="pw-query-line">Showing 4 options for: power bank 20000mah for iphone</p>'
        '<p class="pw-reference-disclaimer">Demo preview only — not live Amazon, Linkwise, SaaS, finance, insurance, or provider offers. Product cards, prices, ratings, and store actions shown here are for visual demonstration only.</p>'
        '<section class="pw-grid" data-card-count="4">'
        f"{''.join(card_html)}"
        "</section>"
        '<p class="pw-demo-note">&#9432; Demo data source: local_test_fixture (not_production_data).</p>'
        f"{render_public_footer()}"
        "</div>"
        "</div>"
        "</main>"
        "</body></html>"
    )
    proof_text = "LIVE RENDERER " + "PROOF V1"
    proof_comment = "picwise-reference-live-renderer-" + "proof-v1"
    html = html.replace(proof_text, "")
    html = html.replace(f"<!-- {proof_comment} -->", "")
    return html
