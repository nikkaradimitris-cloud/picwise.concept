from __future__ import annotations

from html import escape

from picwise_contracts import ContractValidationError, DecisionOutput


def render_landing_surface(decision_output: DecisionOutput) -> str:
    """Render approved mockup-aligned HTML landing surface."""
    choices = decision_output.choices
    if len(choices) != 4:
        raise ContractValidationError("Landing UI requires exactly 4 primary choices.")

    recommended_count = sum(1 for choice in choices if choice.is_recommended)
    if recommended_count != 1:
        raise ContractValidationError("Landing UI requires exactly 1 recommended primary choice.")

    standard_choices = [choice for choice in choices if not choice.is_recommended]
    recommended_choice = next(choice for choice in choices if choice.is_recommended)
    ordered_choices = [*standard_choices, recommended_choice]

    cards_html = []
    for choice in ordered_choices:
        recommended_header = ""
        recommended_effects = ""
        recommended_class = ""
        if choice.is_recommended:
            recommended_class = " pw-card-recommended"
            recommended_header = (
                '<div class="pw-rec-badge">Recommended by Picwise</div>'
            )
            recommended_effects = (
                '<span class="pw-rec-bubble-top" aria-hidden="true"></span>'
                '<span class="pw-rec-bubble-bottom" aria-hidden="true"></span>'
                '<span class="pw-rec-pulse-1" aria-hidden="true"></span>'
                '<span class="pw-rec-pulse-2" aria-hidden="true"></span>'
                '<span class="pw-rec-pulse-3" aria-hidden="true"></span>'
            )

        key_reasons_html = "".join(
            f'<li class="pw-reason-row"><span class="pw-icon pw-icon-check" aria-hidden="true">✓</span>'
            f'<span>{escape(reason)}</span></li>'
            for reason in choice.key_reasons[:3]
        )
        risk_html = (
            '<p class="pw-risk-row"><span class="pw-icon pw-icon-warn" aria-hidden="true">!</span>'
            f"<span>{escape(choice.risks_or_limitations)}</span></p>"
            if str(choice.risks_or_limitations).strip()
            else ""
        )
        recommendation_reason = ""
        if choice.is_recommended:
            reason = str(choice.tracking_metadata.get("recommendation_reason", "")).strip()
            recommendation_reason = (
                '<p class="pw-reason-row pw-recommendation-reason">'
                '<span class="pw-icon pw-icon-star" aria-hidden="true">◎</span>'
                f"<span>{escape(reason)}</span>"
                "</p>"
                if reason
                else ""
            )

        cards_html.append(
            (
                f'<article class="pw-card{recommended_class}" data-choice-id="{escape(choice.product_id)}">'
                f"{recommended_effects}"
                f"{recommended_header}"
                f'<p class="pw-role-pill">{escape(choice.role.value)}</p>'
                f'<h2 class="pw-card-title">{escape(choice.title)}</h2>'
                f'<p class="pw-card-subtitle">{escape(choice.decision_label)}</p>'
                '<div class="pw-divider" aria-hidden="true"></div>'
                f'<p class="pw-price-meta">{escape(choice.subtitle)}</p>'
                f'<ul class="pw-reasons">{key_reasons_html}</ul>'
                f"{risk_html}"
                f"{recommendation_reason}"
                f'<a class="pw-cta" href="{escape(choice.redirect_target)}">{escape(choice.cta_label)}</a>'
                "</article>"
            )
        )

    more_section = ""
    if decision_output.more_choices:
        limited_more = decision_output.more_choices[:4]
        more_items = "".join(
            (
                f'<li data-choice-id="{escape(choice.product_id)}">'
                f"{escape(choice.title)} - {escape(choice.decision_label)}"
                "</li>"
            )
            for choice in limited_more
        )
        more_section = (
            '<section class="pw-more" aria-label="More alternatives">'
            "<h3>If you want more options</h3>"
            f"<ul>{more_items}</ul>"
            "</section>"
        )

    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(decision_output.page_title)} | Picwise</title>"
        "<style>"
        ":root{color-scheme:light dark;--bg:#f7faff;--surface:#ffffff;--surface-alt:#f6f9ff;--text:#102038;"
        "--muted:#506480;--line:#d8e2f0;--line-strong:#9cb3cf;--accent:#1d6eff;--accent-strong:#115bd7;"
        "--button-text:#ffffff;--ring:#4e87da;--footer:#eef4fc;}"
        "body[data-theme='dark']{--bg:#0f1725;--surface:#162233;--surface-alt:#1b2a40;--text:#e8f1ff;--muted:#b4c6de;"
        "--line:#30435e;--line-strong:#51729f;--accent:#79b1ff;--accent-strong:#9cc6ff;--button-text:#091427;--ring:#8ebcff;--footer:#111b2a;}"
        "*{box-sizing:border-box;}html,body{min-height:100%;}"
        "body{margin:0;padding:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.45;display:flex;flex-direction:column;}"
        ".pw-shell{position:relative;max-width:1180px;margin:0 auto;padding:max(12px,env(safe-area-inset-top)) 20px 20px;flex:1;width:100%;}"
        ".pw-bg-network-left,.pw-bg-circuit-right{position:absolute;pointer-events:none;opacity:.11;z-index:0;}"
        ".pw-bg-network-left{left:-30px;top:68px;width:250px;height:250px;background:"
        "radial-gradient(circle at 50px 58px,var(--line-strong) 0 2px,transparent 3px),"
        "radial-gradient(circle at 150px 90px,var(--line-strong) 0 2px,transparent 3px),"
        "linear-gradient(140deg,transparent 50%,var(--line-strong) 51% 52%,transparent 53%),"
        "linear-gradient(108deg,transparent 46%,var(--line-strong) 47% 48%,transparent 49%);}"
        ".pw-bg-circuit-right{right:-36px;top:96px;width:260px;height:260px;background:"
        "linear-gradient(180deg,transparent 12%,var(--line-strong) 12% 12.8%,transparent 12.8% 30%,var(--line-strong) 30% 30.8%,transparent 30.8%),"
        "linear-gradient(90deg,transparent 10%,var(--line-strong) 10% 10.7%,transparent 10.7% 62%,var(--line-strong) 62% 62.7%,transparent 62.7%),"
        "radial-gradient(circle at 194px 74px,var(--line-strong) 0 2px,transparent 3px);}"
        ".pw-topbar{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 20px;padding:2px 0;min-height:40px;}"
        ".pw-brand{display:flex;align-items:center;gap:10px;font-size:1.18rem;font-weight:800;color:var(--text);text-transform:lowercase;letter-spacing:-.01em;}"
        ".pw-logo-mark{position:relative;width:34px;height:34px;border-radius:11px;background:linear-gradient(160deg,#2f86ff,#1d6eff 60%,#1458c9);box-shadow:inset 0 0 0 1px rgba(255,255,255,.25);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:1.15rem;font-weight:900;line-height:1;}"
        ".pw-nav{display:flex;align-items:center;gap:14px;}"
        ".pw-nav a{text-decoration:none;color:var(--muted);font-size:.9rem;font-weight:600;}"
        ".pw-nav a:hover{text-decoration:underline;}"
        ".pw-theme-toggle{border:1px solid var(--line);border-radius:999px;background:var(--surface);padding:4px;display:inline-flex;gap:4px;cursor:pointer;}"
        ".pw-theme-mode{display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:999px;font-size:.78rem;font-weight:700;color:var(--muted);}"
        ".pw-theme-toggle[data-current='light'] .pw-theme-day,.pw-theme-toggle[data-current='dark'] .pw-theme-night{background:var(--surface-alt);color:var(--text);}"
        ".pw-hero{position:relative;z-index:1;text-align:center;max-width:1120px;margin:0 auto 14px;padding-top:0;}"
        ".pw-hero h1{margin:0 0 8px;font-size:clamp(1.65rem,3.25vw,2.55rem);line-height:1.1;letter-spacing:-.02em;}"
        ".pw-hero p{margin:0 auto;color:var(--muted);font-size:1rem;max-width:680px;}"
        ".pw-search-shell{position:relative;z-index:1;max-width:880px;margin:0 auto 8px;display:flex;align-items:center;gap:10px;background:var(--surface);"
        "border:1px solid #d3dfef;border-radius:999px;padding:9px 9px 9px 16px;box-shadow:0 8px 20px rgba(16,32,56,0.07);}"
        ".pw-search-icon,.pw-search-button-icon{position:relative;display:inline-block;width:14px;height:14px;color:currentColor;}"
        ".pw-search-icon::before,.pw-search-button-icon::before{content:'';position:absolute;left:0;top:0;width:9px;height:9px;border:2px solid currentColor;border-radius:50%;}"
        ".pw-search-icon::after,.pw-search-button-icon::after{content:'';position:absolute;width:7px;height:2px;background:currentColor;right:-1px;bottom:1px;transform:rotate(45deg);transform-origin:right center;border-radius:2px;}"
        ".pw-search-shell input{flex:1;min-width:170px;border:0;outline:none;background:transparent;color:var(--text);font-size:.97rem;text-align:center;}"
        ".pw-search-button{border:0;border-radius:999px;height:40px;min-width:46px;padding:0 15px;background:var(--accent);color:var(--button-text);font-weight:800;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;}"
        ".pw-search-button:hover{background:var(--accent-strong);}"
        ".pw-query{position:relative;z-index:1;text-align:center;color:var(--muted);font-size:.9rem;margin:0 0 12px;}"
        ".pw-grid{position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;}"
        ".pw-card{position:relative;background:var(--surface);border:1px solid #d7e3f1;border-radius:18px;padding:14px 13px;display:flex;flex-direction:column;min-height:316px;gap:8px;box-shadow:0 8px 20px rgba(16,32,56,0.065);}"
        ".pw-card-recommended{border-color:var(--ring);background:var(--surface-alt);box-shadow:0 14px 34px rgba(27,83,185,0.14);}"
        ".pw-rec-badge{display:inline-block;max-width:max-content;background:var(--accent);color:var(--button-text);font-weight:700;font-size:.73rem;padding:5px 9px;border-radius:999px;}"
        ".pw-rec-bubble-top,.pw-rec-bubble-bottom{position:absolute;border:2px solid var(--ring);border-radius:999px;pointer-events:none;opacity:.54;}"
        ".pw-rec-bubble-top{top:-10px;right:-9px;width:44px;height:44px;}"
        ".pw-rec-bubble-bottom{bottom:-10px;left:-11px;width:36px;height:36px;}"
        ".pw-rec-pulse-1,.pw-rec-pulse-2,.pw-rec-pulse-3{position:absolute;border:1px solid var(--ring);border-radius:20px;pointer-events:none;opacity:.34;}"
        ".pw-rec-pulse-1{inset:-5px;}"
        ".pw-rec-pulse-2{inset:-8px;opacity:.22;}"
        ".pw-rec-pulse-3{inset:-11px;opacity:.14;}"
        ".pw-role-pill{margin:0;display:inline-block;max-width:max-content;border:1px solid var(--line);border-radius:999px;padding:3px 8px;font-size:.69rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);}"
        ".pw-card-title{margin:0;font-size:1rem;line-height:1.24;}"
        ".pw-card-subtitle{margin:0;color:var(--text);font-weight:700;font-size:.89rem;line-height:1.22;}"
        ".pw-divider{height:1px;background:var(--line);}"
        ".pw-price-meta{margin:0;color:var(--muted);font-size:.84rem;line-height:1.28;}"
        ".pw-reasons{margin:0;padding:0;list-style:none;display:grid;gap:4px;}"
        ".pw-reason-row,.pw-risk-row{margin:0;display:flex;gap:6px;align-items:flex-start;color:var(--muted);font-size:.82rem;line-height:1.28;}"
        ".pw-icon{display:inline-flex;justify-content:center;min-width:14px;font-weight:800;line-height:1.2;}"
        ".pw-icon-check{color:var(--accent-strong);}.pw-icon-warn{color:#c4862f;}.pw-icon-star{color:var(--accent);}"
        ".pw-cta{display:inline-block;margin-top:auto;padding:9px 11px;border-radius:11px;text-decoration:none;text-align:center;font-weight:700;background:transparent;color:var(--accent-strong);border:1px solid #bfd2ef;}"
        ".pw-cta:hover{border-color:var(--accent-strong);background:rgba(29,110,255,.06);}"
        ".pw-more{position:relative;z-index:1;margin-top:14px;padding:12px 14px;border:1px dashed var(--line-strong);border-radius:12px;background:var(--surface);}"
        ".pw-more h3{margin:0 0 7px;font-size:.95rem;color:var(--muted);} .pw-more ul{margin:0;padding-left:18px;color:var(--muted);}"
        ".pw-demo-note{max-width:1180px;margin:10px auto 0;padding:0 20px 10px;color:var(--muted);font-size:.82rem;}"
        ".pw-footer{margin-top:auto;border-top:1px solid var(--line);background:var(--footer);}"
        ".pw-footer-inner{max-width:1180px;margin:0 auto;padding:12px 20px 13px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;}"
        ".pw-footer-left,.pw-footer-right{display:flex;gap:14px;flex-wrap:wrap;align-items:center;}"
        ".pw-footer a,.pw-footer span{text-decoration:none;color:var(--muted);font-size:.82rem;}"
        ".pw-footer a:hover{text-decoration:underline;}"
        ".pw-sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;}"
        "@media (max-width:1060px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}"
        "@media (max-width:840px){.pw-topbar{flex-direction:column;align-items:flex-start;}.pw-nav{flex-wrap:wrap;}}"
        "@media (max-width:620px){.pw-grid{grid-template-columns:1fr;}.pw-search-shell{padding:7px 7px 7px 12px;}.pw-search-button{height:38px;min-width:38px;padding:0 12px;}.pw-footer-inner{flex-direction:column;align-items:flex-start;}}"
        "</style>"
        "</head><body>"
        '<main class="pw-shell">'
        '<div class="pw-bg-network-left" aria-hidden="true"></div>'
        '<div class="pw-bg-circuit-right" aria-hidden="true"></div>'
        '<header class="pw-topbar">'
        '<div class="pw-brand"><span class="pw-logo-mark" aria-hidden="true">p</span><span>picwise</span></div>'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<nav class="pw-nav" aria-label="Primary">'
        '<a href="#how">Πώς λειτουργεί</a>'
        '<a href="#faq">FAQ</a>'
        '<a href="#about">Σχετικά με</a>'
        "</nav>"
        '<button id="theme-toggle" class="pw-theme-toggle" type="button" aria-label="Toggle day/night theme" aria-pressed="false" data-current="light">'
        '<span class="pw-theme-mode pw-theme-day">☀ Day</span>'
        '<span class="pw-theme-mode pw-theme-night">☾ Night</span>'
        "</button>"
        "</div>"
        "</header>"
        '<section class="pw-hero">'
        f"<h1>4 decision-ready options for {escape(decision_output.query)}</h1>"
        "<p>Smart recommendations, side-by-side. Compare and choose with confidence.</p>"
        "</section>"
        '<form action="/demo" method="get" aria-label="Search purchase intent">'
        '<label class="pw-sr-only" for="query-input">Search query</label>'
        '<div class="pw-search-shell">'
        '<span class="pw-search-icon" aria-hidden="true"></span>'
        f'<input id="query-input" type="search" name="q" value="{escape(decision_output.query)}" '
        'placeholder="Search a purchase intent query" autocomplete="off">'
        '<button class="pw-search-button" type="submit" aria-label="Search">'
        '<span class="pw-search-button-icon" aria-hidden="true"></span>'
        '<span class="pw-sr-only">Search</span>'
        "</button>"
        "</div>"
        "</form>"
        f'<p class="pw-query">Showing 4 decision-ready options for: {escape(decision_output.query)}</p>'
        '<section class="pw-grid" data-card-count="4">'
        f"{''.join(cards_html)}"
        "</section>"
        f"{more_section}"
        "</main>"
        '<p class="pw-demo-note">Demo data source: local_test_fixture (not_production_data).</p>'
        '<footer class="pw-footer">'
        '<div class="pw-footer-inner">'
        '<div class="pw-footer-left">'
        '<a href="#about">Σχετικά με</a>'
        '<a href="#contact">Επικοινωνία</a>'
        '<a href="#how">Πώς λειτουργεί</a>'
        '<a href="#faq">FAQ</a>'
        "</div>"
        '<div class="pw-footer-right">'
        '<a href="#terms">Όροι</a>'
        '<a href="#settings">Ρυθμίσεις</a>'
        "<span>Design by subby.cloud</span>"
        "</div>"
        "</div>"
        "</footer>"
        "<script>"
        "(function(){var root=document.body;var key='picwise_theme';var btn=document.getElementById('theme-toggle');"
        "if(!btn){return;}var setTheme=function(theme){var isDark=theme==='dark';root.setAttribute('data-theme',isDark?'dark':'light');"
        "btn.setAttribute('aria-pressed',isDark?'true':'false');btn.setAttribute('data-current',isDark?'dark':'light');};"
        "var saved='';try{saved=window.localStorage.getItem(key)||'';}catch(e){saved='';}"
        "if(saved==='dark'||saved==='light'){setTheme(saved);}else{setTheme('light');}"
        "btn.addEventListener('click',function(){var next=root.getAttribute('data-theme')==='dark'?'light':'dark';setTheme(next);"
        "try{window.localStorage.setItem(key,next);}catch(e){}});})();"
        "</script>"
        "</body></html>"
    )
