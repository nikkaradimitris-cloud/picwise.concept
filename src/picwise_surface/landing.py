from __future__ import annotations

from html import escape

from picwise_contracts import ContractValidationError, DecisionOutput
from .legal import render_public_footer


def render_review_safe_landing_page() -> str:
    """Render a review-safe public landing page without product claims."""
    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PicWise — Compare Product Options Before You Buy</title>"
        '<meta name="description" content="PicWise helps shoppers compare product options and make clearer buying decisions before visiting external stores.">'
        "<style>"
        "*{box-sizing:border-box;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#102744;background:linear-gradient(180deg,#f8fbff 0%,#f3f8ff 100%);}"
        ".pw-wrap{max-width:980px;margin:0 auto;padding:40px 20px 28px;}"
        ".pw-brand{font-size:30px;font-weight:800;letter-spacing:-.03em;text-transform:lowercase;color:#1a4fb7;}"
        ".pw-card{margin-top:20px;background:#fff;border:1px solid #d9e7fb;border-radius:16px;padding:24px;box-shadow:0 12px 28px rgba(20,56,112,.08);}"
        ".pw-title{margin:0;font-size:40px;line-height:1.14;letter-spacing:-.02em;color:#0f2442;}"
        ".pw-subtitle{margin:14px 0 0;font-size:18px;line-height:1.6;color:#2c4567;}"
        ".pw-body{margin:14px 0 0;font-size:16px;line-height:1.7;color:#355174;}"
        ".pw-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:20px;}"
        ".pw-section{background:#f6f9ff;border:1px solid #dfeafb;border-radius:12px;padding:14px 16px;}"
        ".pw-section h2{margin:0;font-size:16px;color:#173862;}"
        ".pw-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px;}"
        ".pw-btn{height:42px;padding:0 16px;border-radius:999px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;font-size:14px;}"
        ".pw-btn-primary{background:#1f6dff;color:#fff;border:1px solid #1f6dff;}"
        ".pw-btn-secondary{background:#fff;color:#1f6dff;border:1px solid #b9d1ff;}"
        ".pw-note{margin-top:16px;font-size:13px;color:#59779f;}"
        ".pw-footer{margin-top:18px;padding-top:14px;border-top:1px solid #dbe8fb;}"
        ".pw-footer-links{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}"
        ".pw-footer-link{display:inline-flex;align-items:center;justify-content:center;padding:6px 10px;border:1px solid #d8e6fb;border-radius:999px;background:#f7faff;font-size:13px;line-height:1.2;color:#335983;text-decoration:none;white-space:nowrap;}"
        ".pw-footer-link:hover{background:#eef5ff;border-color:#cddffc;color:#24496f;}"
        ".pw-footer-disclosure{margin:10px 0 0;font-size:12px;line-height:1.5;color:#5f7ea6;max-width:760px;}"
        ".pw-footer-meta{margin:6px 0 0;font-size:12px;color:#6b86ac;}"
        "@media (max-width:760px){.pw-title{font-size:31px;}.pw-grid{grid-template-columns:1fr;}}"
        "</style></head><body>"
        '<main class="pw-wrap">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">PicWise</a>'
        '<section class="pw-card">'
        '<h1 class="pw-title">PicWise helps you compare before you buy.</h1>'
        '<p class="pw-subtitle">Search for a product category, compare a focused set of options, and choose the best external store offer with more confidence.</p>'
        '<p class="pw-body">PicWise is being prepared as a product discovery and buying-decision assistant. Provider and affiliate integrations are currently being configured. Product listings shown in demo areas are previews only and are not live Amazon offers.</p>'
        '<section class="pw-grid" aria-label="Picwise capabilities and readiness">'
        '<article class="pw-section"><h2>Product comparison</h2></article>'
        '<article class="pw-section"><h2>Buying guides</h2></article>'
        '<article class="pw-section"><h2>External store offer discovery</h2></article>'
        '<article class="pw-section"><h2>Provider integrations in progress</h2></article>'
        "</section>"
        '<div class="pw-actions">'
        '<a class="pw-btn pw-btn-primary" href="/picwise-reference">View demo</a>'
        '<a class="pw-btn pw-btn-secondary" href="/demo#what-is-picwise">What is PicWise?</a>'
        "</div>"
        '<p class="pw-note">No live provider integration or real product availability is claimed on this page.</p>'
        "</section>"
        f"{render_public_footer()}"
        "</main></body></html>"
    )


def render_demo_info_page() -> str:
    """Render a review-safe informational demo page without commerce cards."""
    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PicWise Demo — Buying Decision Preview</title>"
        '<meta name="description" content="Preview how PicWise supports product comparison and buying decisions while provider integrations are being configured.">'
        "<style>"
        "*{box-sizing:border-box;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#102744;background:linear-gradient(180deg,#f8fbff 0%,#f3f8ff 100%);}"
        ".pw-wrap{max-width:940px;margin:0 auto;padding:40px 20px 28px;}"
        ".pw-brand{font-size:30px;font-weight:800;letter-spacing:-.03em;text-transform:lowercase;color:#1a4fb7;text-decoration:none;}"
        ".pw-card{margin-top:20px;background:#fff;border:1px solid #d9e7fb;border-radius:16px;padding:24px;box-shadow:0 12px 28px rgba(20,56,112,.08);}"
        ".pw-title{margin:0;font-size:36px;line-height:1.16;letter-spacing:-.02em;color:#0f2442;}"
        ".pw-body{margin:14px 0 0;font-size:16px;line-height:1.7;color:#355174;}"
        ".pw-note{margin:16px 0 0;padding:12px 14px;border:1px solid #dbe8fb;border-radius:12px;background:#f6f9ff;color:#24456f;font-size:15px;line-height:1.6;}"
        ".pw-list-wrap{margin-top:18px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}"
        ".pw-item{background:#f6f9ff;border:1px solid #dfeafb;border-radius:12px;padding:14px 16px;}"
        ".pw-item h2{margin:0;font-size:16px;color:#173862;}"
        ".pw-item p{margin:8px 0 0;font-size:14px;line-height:1.55;color:#355174;}"
        ".pw-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px;}"
        ".pw-btn{height:42px;padding:0 16px;border-radius:999px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;font-size:14px;}"
        ".pw-btn-primary{background:#1f6dff;color:#fff;border:1px solid #1f6dff;}"
        ".pw-btn-secondary{background:#fff;color:#1f6dff;border:1px solid #b9d1ff;}"
        ".pw-footer{margin-top:18px;padding-top:14px;border-top:1px solid #dbe8fb;}"
        ".pw-footer-links{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}"
        ".pw-footer-link{display:inline-flex;align-items:center;justify-content:center;padding:6px 10px;border:1px solid #d8e6fb;border-radius:999px;background:#f7faff;font-size:13px;line-height:1.2;color:#335983;text-decoration:none;white-space:nowrap;}"
        ".pw-footer-link:hover{background:#eef5ff;border-color:#cddffc;color:#24496f;}"
        ".pw-footer-disclosure{margin:10px 0 0;font-size:12px;line-height:1.5;color:#5f7ea6;max-width:760px;}"
        ".pw-footer-meta{margin:6px 0 0;font-size:12px;color:#6b86ac;}"
        "@media (max-width:760px){.pw-title{font-size:30px;}.pw-list-wrap{grid-template-columns:1fr;}}"
        "</style></head><body>"
        '<main class="pw-wrap">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">PicWise</a>'
        '<section class="pw-card">'
        '<h1 class="pw-title">How PicWise will help shoppers decide.</h1>'
        '<p class="pw-body">PicWise is being prepared as a buying-decision assistant. Users will be able to search for a product category, compare a small set of relevant options, and follow external store offers once provider integrations are configured.</p>'
        '<p class="pw-note" id="what-is-picwise"><strong>Important note:</strong> This demo page is informational only. It does not display live Amazon offers, real product availability, affiliate links, prices, or ratings.</p>'
        '<section class="pw-list-wrap" aria-label="Informational demo sections">'
        '<article class="pw-item"><h2>Search by product need</h2><p>Users will start from a category or buying need, not from a live offer feed.</p></article>'
        '<article class="pw-item"><h2>Compare focused choices</h2><p>PicWise will present a short comparison view once integrations are fully configured.</p></article>'
        '<article class="pw-item"><h2>Understand trade-offs</h2><p>Guidance will help users evaluate practical pros, limits, and suitability.</p></article>'
        '<article class="pw-item"><h2>External provider integrations in progress</h2><p>Provider and affiliate integrations are being configured. No live Amazon offers are currently claimed.</p></article>'
        "</section>"
        '<div class="pw-actions">'
        '<a class="pw-btn pw-btn-primary" href="/">Back to home</a>'
        "</div>"
        "</section>"
        f"{render_public_footer()}"
        "</main></body></html>"
    )


def render_landing_surface(decision_output: DecisionOutput) -> str:
    """Render pixel-faithful Picwise landing/results UI from deterministic mock cards."""
    choices = decision_output.choices
    if len(choices) != 4:
        raise ContractValidationError("Landing UI requires exactly 4 primary choices.")
    recommended_count = sum(1 for choice in choices if choice.is_recommended)
    if recommended_count != 1:
        raise ContractValidationError("Landing UI requires exactly 1 recommended primary choice.")

    query = escape(decision_output.query.strip() or "power bank 20000mah for iphone")
    card_specs = [
        {
            "badge": "BUDGET",
            "badge_class": "pw-badge-budget",
            "name": "TravelCore 20K",
            "description": "Budget pick for occasional travel charging",
            "rating": "4.4",
            "reviews": "(1,248)",
            "price": "EUR 29\u201334",
            "meta": "Lightweight  \u00b7  Basic reliability",
            "bullets": [
                "Compact size",
                "Simple cable setup",
                "Widely available",
            ],
            "warning": "Lower sustained output under heavy load.",
            "cta": "View in Store",
            "image_class": "pw-product-black",
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
            "price": "EUR 37\u201345",
            "meta": "USB-C PD  \u00b7  Lower mismatch risk",
            "bullets": [
                "Balanced output",
                "Reliable compatibility",
                "Solid build quality",
            ],
            "warning": "Slightly heavier than compact alternatives.",
            "cta": "Go to Store",
            "image_class": "pw-product-dark",
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
            "price": "EUR 44\u201352",
            "meta": "Strong output  \u00b7  Better long-run reliability",
            "bullets": [
                "Consistent charging speed",
                "Good cable support",
                "Trusted warranty terms",
            ],
            "warning": "Price sits above entry-level options.",
            "cta": "View Details and Buy",
            "image_class": "pw-product-navy",
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
            "price": "EUR 59\u201369",
            "meta": "Higher capacity  \u00b7  Better sustained output",
            "bullets": [
                "High capacity headroom",
                "Premium thermal design",
                "Extended accessory kit",
                "Higher price and larger carry footprint.",
            ],
            "warning": "",
            "cta": "View in Store",
            "image_class": "pw-product-silver",
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
            '<span class="pw-rec-ring-a" aria-hidden="true"></span>'
            '<span class="pw-rec-ring-b" aria-hidden="true"></span>'
            '<span class="pw-rec-ring-c" aria-hidden="true"></span>'
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
                f'<div class="pw-product-image {card["image_class"]}" aria-hidden="true"></div>'
                f'<p class="pw-price">{escape(card["price"])}</p>'
                f'<p class="pw-meta">{escape(card["meta"])}</p>'
                f'<ul class="pw-feature-list">{reasons}</ul>'
                f"{warning_html}"
                f"{rec_note}"
                f'<a class="pw-card-cta" href="/local-safe-redirect?target=demo">{escape(card["cta"])}</a>'
                "</article>"
            )
        )

    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(decision_output.page_title)} | PicWise</title>"
        "<style>"
        "*{box-sizing:border-box;}html,body{min-height:100%;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#0f1f3a;background:linear-gradient(180deg,#f9fcff 0%,#f5f9ff 48%,#f9fcff 100%);}"
        ".pw-page{max-width:1260px;margin:0 auto;min-height:100vh;padding:16px 22px 20px;position:relative;display:flex;flex-direction:column;}"
        ".pw-bg-left,.pw-bg-right{position:absolute;pointer-events:none;z-index:0;opacity:.38;}"
        ".pw-bg-left{left:-78px;top:172px;width:296px;height:280px;background:radial-gradient(circle at 40px 42px,rgba(52,111,213,.27) 0 2px,transparent 3px),radial-gradient(circle at 102px 92px,rgba(52,111,213,.2) 0 2px,transparent 3px),radial-gradient(circle at 170px 58px,rgba(52,111,213,.25) 0 2px,transparent 3px),linear-gradient(122deg,transparent 38%,rgba(91,136,216,.2) 39% 40%,transparent 41%),linear-gradient(90deg,transparent 48%,rgba(91,136,216,.16) 49% 50%,transparent 51%);}"
        ".pw-bg-right{right:-82px;top:196px;width:320px;height:340px;background:radial-gradient(circle at 246px 66px,rgba(62,126,228,.24) 0 3px,transparent 4px),radial-gradient(circle at 218px 154px,rgba(62,126,228,.2) 0 2px,transparent 3px),linear-gradient(180deg,transparent 12%,rgba(88,143,228,.2) 13% 14%,transparent 15% 41%,rgba(88,143,228,.16) 42% 43%,transparent 44%),linear-gradient(90deg,transparent 18%,rgba(88,143,228,.18) 19% 20%,transparent 21% 78%,rgba(88,143,228,.16) 79% 80%,transparent 81%);}"
        ".pw-topbar{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;}"
        ".pw-brand{display:flex;align-items:flex-start;gap:10px;text-decoration:none;color:#0f1f3a;}"
        ".pw-logo{width:34px;height:34px;border-radius:12px;background:linear-gradient(160deg,#30a0ff 0%,#1f6cff 70%);position:relative;box-shadow:0 9px 18px rgba(31,108,255,.2);margin-top:2px;}"
        ".pw-logo::before{content:'';position:absolute;left:8px;top:8px;width:14px;height:14px;border:3px solid #fff;border-right-color:transparent;border-radius:999px;}"
        ".pw-logo::after{content:'';position:absolute;right:8px;bottom:8px;width:6px;height:6px;background:#fff;border-radius:999px;}"
        ".pw-brand-name{font-size:34px;line-height:1;font-weight:800;letter-spacing:-.04em;text-transform:lowercase;}"
        ".pw-brand-tagline{margin-top:1px;font-size:11px;color:#304768;line-height:1.2;letter-spacing:.02em;}"
        ".pw-actions{display:flex;align-items:center;gap:18px;padding-top:3px;}"
        ".pw-login{font-size:16px;color:#1d2d4a;text-decoration:none;font-weight:600;}"
        ".pw-register{display:inline-flex;align-items:center;justify-content:center;height:40px;padding:0 24px;border-radius:999px;background:#1f6dff;color:#fff;font-size:16px;font-weight:700;text-decoration:none;box-shadow:0 10px 22px rgba(31,109,255,.28);}"
        ".pw-hero{position:relative;z-index:1;text-align:center;margin-top:2px;}"
        ".pw-hero-glow{position:absolute;left:50%;top:-26px;transform:translateX(-50%);width:min(660px,90%);height:86px;border-radius:999px;background:radial-gradient(ellipse at center,rgba(117,164,255,.35) 0%,rgba(117,164,255,.16) 32%,rgba(117,164,255,0) 72%);animation:pwShine 2.8s ease-out 2;pointer-events:none;}"
        "@keyframes pwShine{0%{opacity:0;transform:translateX(-50%) scale(.92);}24%{opacity:.8;}100%{opacity:.26;transform:translateX(-50%) scale(1);}}"
        ".pw-hero h1{margin:8px 0 18px;font-size:43px;font-weight:700;letter-spacing:-.02em;color:#0f1f3a;line-height:1.1;}"
        ".pw-search-wrap{position:relative;z-index:1;max-width:760px;margin:0 auto;}"
        ".pw-search-shell{display:flex;align-items:center;gap:10px;height:58px;background:#fff;border:1px solid #dbe8fb;border-radius:999px;padding:0 10px 0 18px;box-shadow:0 14px 32px rgba(18,47,95,.09);}"
        ".pw-search-icon,.pw-search-button-icon{position:relative;width:16px;height:16px;display:inline-block;color:#7c93b7;flex:0 0 auto;}"
        ".pw-search-icon::before,.pw-search-button-icon::before{content:'';position:absolute;left:0;top:0;width:10px;height:10px;border:2px solid currentColor;border-radius:999px;}"
        ".pw-search-icon::after,.pw-search-button-icon::after{content:'';position:absolute;right:1px;bottom:2px;width:7px;height:2px;background:currentColor;border-radius:2px;transform:rotate(45deg);transform-origin:right center;}"
        ".pw-search-input{flex:1;min-width:120px;border:0;background:transparent;outline:none;font-size:19px;color:#12284a;font-weight:500;}"
        ".pw-search-input::placeholder{color:#95a8c7;}"
        ".pw-search-button{width:42px;height:42px;border-radius:999px;border:0;background:#1f6dff;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 8px 18px rgba(31,109,255,.3);}"
        ".pw-search-button .pw-search-button-icon{color:#fff;}"
        ".pw-info-wrap{position:relative;z-index:1;text-align:center;margin-top:9px;min-height:106px;}"
        ".pw-info-link{display:inline-block;border:0;background:transparent;color:#2a6deb;font-size:15px;cursor:pointer;padding:0;text-decoration:none;}"
        ".pw-tooltip{position:absolute;left:50%;transform:translateX(-50%);top:28px;width:min(430px,92vw);background:#fff;border:1px solid #dbe6f8;border-radius:12px;box-shadow:0 14px 30px rgba(16,39,77,.12);padding:12px 14px;font-size:14px;line-height:1.5;color:#112849;text-align:left;display:none;}"
        ".pw-tooltip::before{content:'';position:absolute;left:50%;top:-7px;transform:translateX(-50%) rotate(45deg);width:14px;height:14px;background:#fff;border-left:1px solid #dbe6f8;border-top:1px solid #dbe6f8;}"
        ".pw-info-wrap[data-open='true'] .pw-tooltip{display:block;}"
        ".pw-query{position:relative;z-index:1;text-align:center;margin:5px 0 16px;font-size:18px;color:#253a59;}"
        ".pw-query-keyword{color:#2a6deb;}"
        ".pw-grid{position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;align-items:stretch;}"
        ".pw-card{position:relative;background:#fff;border:1px solid #dbe8fb;border-radius:18px;box-shadow:0 9px 24px rgba(17,44,91,.08);padding:14px 14px 12px;display:flex;flex-direction:column;min-height:472px;}"
        ".pw-card-recommended{border:2px solid #2f78ff;box-shadow:0 16px 36px rgba(34,94,198,.2);}"
        ".pw-rec-badge{display:inline-block;background:#2a70f1;color:#fff;font-size:12px;font-weight:700;padding:6px 11px;border-radius:999px;margin-bottom:9px;}"
        ".pw-rec-ring-a,.pw-rec-ring-b,.pw-rec-ring-c{position:absolute;border:2px solid rgba(53,124,242,.32);border-radius:999px;pointer-events:none;}"
        ".pw-rec-ring-a{right:-40px;top:18px;width:86px;height:86px;}"
        ".pw-rec-ring-b{right:-26px;top:36px;width:58px;height:58px;}"
        ".pw-rec-ring-c{right:-49px;top:62px;width:106px;height:106px;border-color:rgba(53,124,242,.22);}"
        ".pw-badge{display:inline-block;align-self:flex-start;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.05em;margin-bottom:8px;}"
        ".pw-badge-budget,.pw-badge-premium{background:#eaf2ff;color:#3f72c4;}"
        ".pw-badge-value{background:#e8f8ec;color:#2f9b57;}"
        ".pw-badge-best{background:#f0ecff;color:#6e57cc;}"
        ".pw-card-title{margin:0;font-size:30px;line-height:1.03;color:#112649;letter-spacing:-.03em;}"
        ".pw-card-description{margin:4px 0 8px;font-size:12px;color:#5c7397;line-height:1.35;min-height:32px;}"
        ".pw-rating-row{margin:0 0 10px;display:flex;align-items:center;gap:5px;font-size:12px;color:#112649;}"
        ".pw-stars{font-size:11px;color:#f5b435;letter-spacing:1px;}"
        ".pw-reviews{color:#6f88ac;}"
        ".pw-product-image{height:84px;border-radius:13px;margin:0 0 10px;position:relative;align-self:center;width:95%;background:linear-gradient(180deg,#f9fbff,#edf3fd);}"
        ".pw-product-image::before{content:'';position:absolute;left:50%;top:18px;transform:translateX(-50%) rotate(-14deg);width:124px;height:46px;border-radius:8px;box-shadow:0 8px 16px rgba(14,28,54,.22);}"
        ".pw-product-image::after{content:'';position:absolute;left:58%;top:26px;transform:translateX(-50%) rotate(-14deg);width:14px;height:4px;border-radius:5px;background:#1f6dff;opacity:.85;}"
        ".pw-product-black::before{background:linear-gradient(160deg,#20252f,#0e1118);}"
        ".pw-product-dark::before{background:linear-gradient(160deg,#2b3340,#11161f);}"
        ".pw-product-navy::before{background:linear-gradient(160deg,#334c78,#18243b);}"
        ".pw-product-silver::before{background:linear-gradient(160deg,#b4becd,#7f8998);}"
        ".pw-price{margin:0;font-size:26px;line-height:1;font-weight:800;color:#2a70e6;letter-spacing:-.03em;}"
        ".pw-meta{margin:3px 0 8px;font-size:12px;color:#6f88ac;}"
        ".pw-feature-list{margin:0;padding:0;list-style:none;display:grid;gap:4px;}"
        ".pw-feature-item{display:flex;align-items:flex-start;gap:7px;font-size:12px;color:#304b70;line-height:1.35;}"
        ".pw-feature-dot{width:8px;height:8px;border-radius:999px;background:#5b8ce5;flex:0 0 auto;margin-top:4px;}"
        ".pw-warning{margin:7px 0 0;font-size:11px;color:#5a7498;line-height:1.3;display:flex;gap:6px;}"
        ".pw-warning-icon{font-size:10px;color:#6f86ad;line-height:1.2;margin-top:1px;}"
        ".pw-rec-note{margin:8px 0 0;font-size:11px;line-height:1.35;color:#2e4c7d;background:#eef4ff;border-radius:8px;padding:6px 8px;}"
        ".pw-card-cta{margin-top:auto;height:40px;border-radius:11px;border:1px solid #2e75ee;color:#2e75ee;background:#fff;font-size:16px;font-weight:700;text-decoration:none;display:flex;align-items:center;justify-content:center;}"
        ".pw-card-recommended .pw-card-cta{background:#1f6dff;color:#fff;border-color:#1f6dff;}"
        ".pw-demo-note{position:relative;z-index:1;text-align:center;font-size:12px;color:#7389ac;margin:15px 0 8px;}"
        ".pw-footer{position:relative;z-index:1;text-align:center;padding:4px 0 9px;font-size:12px;color:#6e83a3;}"
        ".pw-footer a{color:#6e83a3;text-decoration:none;margin-left:22px;}"
        "@media (max-width:1200px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.pw-card-recommended{transform:none;}.pw-rec-ring-a,.pw-rec-ring-b,.pw-rec-ring-c{display:none;}.pw-hero h1{font-size:36px;}}"
        "@media (max-width:700px){.pw-page{padding:14px 14px 16px;}.pw-topbar{align-items:center;}.pw-brand-name{font-size:30px;}.pw-query{font-size:15px;}.pw-grid{grid-template-columns:1fr;}.pw-search-input{font-size:17px;}.pw-hero h1{font-size:30px;}.pw-footer a{margin-left:12px;}}"
        "</style></head><body>"
        '<main class="pw-page">'
        '<div class="pw-bg-left" aria-hidden="true"></div>'
        '<div class="pw-bg-right" aria-hidden="true"></div>'
        '<header class="pw-topbar">'
        '<a class="pw-brand" href="/" aria-label="Picwise home">'
        '<span class="pw-logo" aria-hidden="true"></span>'
        '<span><span class="pw-brand-name">picwise</span><span class="pw-brand-tagline">shopping assistant</span></span>'
        "</a>"
        '<div class="pw-actions"><a class="pw-login" href="#">Login</a><a class="pw-register" href="#">Register</a></div>'
        "</header>"
        '<section class="pw-hero">'
        '<span class="pw-hero-glow" aria-hidden="true"></span>'
        "<h1>See the 4 best products before you buy.</h1>"
        "</section>"
        '<form action="/demo" method="get" class="pw-search-wrap" aria-label="Search">'
        '<label for="query-input" style="position:absolute;left:-9999px;">Search query</label>'
        '<div class="pw-search-shell">'
        '<span class="pw-search-icon" aria-hidden="true"></span>'
        f'<input class="pw-search-input" id="query-input" type="search" name="q" value="{query}" placeholder="Search your product here" autocomplete="off">'
        '<button class="pw-search-button" type="submit" aria-label="Search">'
        '<span class="pw-search-button-icon" aria-hidden="true"></span>'
        "</button></div></form>"
        '<section class="pw-info-wrap" id="pw-info-wrap" data-open="true">'
        '<button type="button" class="pw-info-link" id="pw-info-link" aria-expanded="true" aria-controls="pw-tooltip">&#9432; What is PicWise?</button>'
        '<div class="pw-tooltip" id="pw-tooltip">PicWise is your shopping assistant. It compares products for what you want to buy, recommends the 4 best matches, saves you time, and helps you choose faster.</div>'
        "</section>"
        f'<p class="pw-query">Showing 4 options for: <span class="pw-query-keyword">{query}</span></p>'
        '<section class="pw-grid" data-card-count="4">'
        f"{''.join(card_html)}"
        "</section>"
        '<p class="pw-demo-note">&#9432; Demo data source: local_test_fixture (not_production_data).</p>'
        '<footer class="pw-footer">&copy; 2024 Picwise. All rights reserved.<a href="#">Privacy</a><a href="#">Terms</a><a href="#">Contact</a></footer>'
        "</main>"
        "<script>"
        "(function(){var wrap=document.getElementById('pw-info-wrap');var btn=document.getElementById('pw-info-link');"
        "if(!wrap||!btn){return;}btn.addEventListener('click',function(){var open=wrap.getAttribute('data-open')==='true';"
        "wrap.setAttribute('data-open',open?'false':'true');btn.setAttribute('aria-expanded',open?'false':'true');});"
        "btn.addEventListener('mouseenter',function(){wrap.setAttribute('data-open','true');btn.setAttribute('aria-expanded','true');});})();"
        "</script>"
        "</body></html>"
    )
