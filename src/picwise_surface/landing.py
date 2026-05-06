from __future__ import annotations

from html import escape

from picwise_contracts import ContractValidationError, DecisionOutput


def render_landing_surface(decision_output: DecisionOutput) -> str:
    """Render a polished HTML landing surface from a validated decision output."""
    choices = decision_output.choices
    if len(choices) != 4:
        raise ContractValidationError("Landing UI requires exactly 4 primary choices.")

    recommended_count = sum(1 for choice in choices if choice.is_recommended)
    if recommended_count != 1:
        raise ContractValidationError("Landing UI requires exactly 1 recommended primary choice.")

    cards_html = []
    for choice in choices:
        recommended_header = ""
        recommended_effects = ""
        if choice.is_recommended:
            recommended_header = (
                '<div class="recommended-top">'
                '<p class="recommended-badge">Recommended by Picwise</p>'
                "</div>"
            )
            recommended_effects = (
                '<span class="recommended-bubble recommended-bubble-top" aria-hidden="true"></span>'
                '<span class="recommended-bubble recommended-bubble-bottom" aria-hidden="true"></span>'
                '<span class="recommended-pulse recommended-pulse-1" aria-hidden="true"></span>'
                '<span class="recommended-pulse recommended-pulse-2" aria-hidden="true"></span>'
                '<span class="recommended-pulse recommended-pulse-3" aria-hidden="true"></span>'
            )

        recommendation_reason = ""
        if choice.is_recommended:
            reason = str(choice.tracking_metadata.get("recommendation_reason", "")).strip()
            recommendation_reason = (
                f'<p class="recommendation-reason"><span class="reason-icon">◎</span>{escape(reason)}</p>'
                if reason
                else ""
            )

        key_reasons_html = "".join(
            f'<li class="reason-item"><span class="reason-icon">✓</span>{escape(reason)}</li>'
            for reason in choice.key_reasons[:3]
        )
        risk_html = (
            f'<p class="risks"><span class="reason-icon">!</span>{escape(choice.risks_or_limitations)}</p>'
            if str(choice.risks_or_limitations).strip()
            else ""
        )
        card_class = "choice-card recommended" if choice.is_recommended else "choice-card"
        cards_html.append(
            (
                f'<article class="{card_class}" data-choice-id="{escape(choice.product_id)}">'
                f"{recommended_effects}"
                f"{recommended_header}"
                f'<p class="role-badge">{escape(choice.role.value)}</p>'
                f"<h2>{escape(choice.title)}</h2>"
                f'<p class="decision-label">{escape(choice.decision_label)}</p>'
                f'<p class="subtitle">{escape(choice.subtitle)}</p>'
                f'<ul class="key-reasons">{key_reasons_html}</ul>'
                f"{risk_html}"
                f"{recommendation_reason}"
                f'<a class="cta" href="{escape(choice.redirect_target)}">{escape(choice.cta_label)}</a>'
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
            '<section class="more-section secondary" aria-label="More alternatives">'
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
        ":root{color-scheme:light dark;--bg:#f6f9ff;--surface:#ffffff;--surface-alt:#f9fbff;--text:#102038;"
        "--muted:#4f6582;--line:#d8e3f2;--line-strong:#a9bfd9;--accent:#1f6fff;--accent-strong:#0e58d3;"
        "--button-text:#ffffff;--brand:#173968;--hero:#0f223e;--nav:#2a466c;--shadow:0 14px 30px rgba(16,32,56,0.06);"
        "--ring:#66a3ff;--tech:#89a8d4;}"
        "body[data-theme='dark']{--bg:#0e1725;--surface:#162233;--surface-alt:#1b2c42;--text:#e7f0ff;--muted:#afc1da;"
        "--line:#2f425d;--line-strong:#4e6f99;--accent:#73adff;--accent-strong:#9bc4ff;--button-text:#0a1528;"
        "--brand:#d8e8ff;--hero:#eff5ff;--nav:#c2d6f3;--shadow:0 16px 32px rgba(5,10,20,0.35);--ring:#8fc0ff;--tech:#5877a7;}"
        "*{box-sizing:border-box;}html,body{height:100%;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.45;"
        "display:flex;flex-direction:column;position:relative;overflow-x:hidden;}"
        "body::before,body::after{content:'';position:fixed;top:90px;bottom:100px;width:280px;pointer-events:none;opacity:.18;z-index:0;}"
        "body::before{left:-44px;background:"
        "radial-gradient(circle at 68px 74px,var(--tech) 0 2px,transparent 3px),"
        "radial-gradient(circle at 154px 116px,var(--tech) 0 2px,transparent 3px),"
        "linear-gradient(109deg,transparent 44%,var(--tech) 45% 46%,transparent 47%),"
        "linear-gradient(145deg,transparent 56%,var(--tech) 57% 58%,transparent 59%),"
        "linear-gradient(180deg,transparent 30%,var(--tech) 31% 32%,transparent 33%);}"
        "body::after{right:-58px;background:"
        "linear-gradient(180deg,transparent 0 18%,var(--tech) 18% 18.6%,transparent 18.6% 34%,var(--tech) 34% 34.6%,transparent 34.6%),"
        "linear-gradient(90deg,transparent 0 28%,var(--tech) 28% 28.8%,transparent 28.8% 62%,var(--tech) 62% 62.8%,transparent 62.8%),"
        "radial-gradient(circle at 188px 90px,var(--tech) 0 2px,transparent 3px),"
        "radial-gradient(circle at 110px 200px,var(--tech) 0 2px,transparent 3px);}"
        ".picwise-landing{position:relative;z-index:1;max-width:1160px;margin:0 auto;padding:26px 20px 34px;flex:1;width:100%;}"
        ".site-header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:36px;}"
        ".brand{font-size:1.3rem;font-weight:800;letter-spacing:-.02em;color:var(--brand);}"
        ".header-controls{display:flex;align-items:center;gap:16px;}"
        ".main-nav{display:flex;gap:14px;align-items:center;}"
        ".main-nav a{text-decoration:none;color:var(--nav);font-size:.92rem;font-weight:600;}"
        ".main-nav a:hover{text-decoration:underline;}"
        ".theme-toggle{border:1px solid var(--line-strong);background:var(--surface);color:var(--text);padding:5px 9px;"
        "border-radius:999px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:7px;font-size:.8rem;}"
        ".theme-toggle .mode{display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border-radius:999px;opacity:.55;}"
        ".theme-toggle[data-current='light'] .mode-light,.theme-toggle[data-current='dark'] .mode-dark{opacity:1;background:var(--surface-alt);}"
        ".hero{text-align:center;max-width:860px;margin:0 auto 26px;}"
        ".hero h1{margin:0 0 12px;font-size:clamp(1.8rem,3.8vw,2.9rem);line-height:1.16;color:var(--hero);letter-spacing:-.02em;}"
        ".hero p{margin:0 auto;color:var(--muted);font-size:1.03rem;max-width:660px;}"
        ".search-form{max-width:740px;margin:0 auto 10px;}"
        ".search-shell{display:flex;align-items:center;gap:10px;background:var(--surface);border:1px solid var(--line);"
        "border-radius:999px;padding:8px 8px 8px 14px;box-shadow:0 10px 24px rgba(16,32,56,0.06);}"
        ".search-icon{font-size:1rem;color:var(--muted);line-height:1;}"
        ".search-form input{flex:1;min-width:180px;border:0;outline:none;font-size:1rem;background:transparent;color:var(--text);}"
        ".search-form button{border:0;border-radius:999px;min-width:44px;height:44px;padding:0 16px;background:var(--accent);"
        "color:var(--button-text);font-weight:700;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;}"
        ".search-form button:hover{background:var(--accent-strong);}"
        ".query-confirmation{margin:0 0 24px;text-align:center;color:var(--muted);font-size:.93rem;}"
        ".primary-choices{display:grid;grid-template-columns:repeat(auto-fit,minmax(242px,1fr));gap:18px;}"
        ".choice-card{position:relative;overflow:visible;background:var(--surface);border:1px solid var(--line);border-radius:18px;"
        "padding:16px;display:flex;flex-direction:column;gap:11px;min-height:302px;box-shadow:var(--shadow);}"
        ".choice-card.recommended{border:1px solid var(--ring);background:var(--surface-alt);}"
        ".recommended-bubble{position:absolute;border:1px solid var(--ring);border-radius:999px;pointer-events:none;}"
        ".recommended-bubble-top{top:-10px;right:14px;width:32px;height:32px;}"
        ".recommended-bubble-bottom{left:-11px;bottom:28px;width:22px;height:22px;}"
        ".recommended-pulse{position:absolute;inset:-8px;border:1px solid var(--ring);border-radius:22px;opacity:0;pointer-events:none;}"
        ".recommended-pulse-1{animation:recommendedPulse 3.4s ease-out 3;}"
        ".recommended-pulse-2{animation:recommendedPulse 3.4s ease-out .8s 3;}"
        ".recommended-pulse-3{animation:recommendedPulse 3.4s ease-out 1.6s 3;}"
        "@keyframes recommendedPulse{0%{transform:scale(1);opacity:.5;}65%{transform:scale(1.03);opacity:0;}100%{transform:scale(1.03);opacity:0;}}"
        ".recommended-top{display:flex;align-items:flex-start;justify-content:space-between;min-height:24px;}"
        ".recommended-badge{display:inline-block;margin:0;background:var(--accent);color:var(--button-text);border-radius:999px;"
        "padding:5px 10px;font-size:.75rem;font-weight:700;}"
        ".role-badge{margin:0;font-size:.72rem;font-weight:700;letter-spacing:.06em;color:var(--muted);text-transform:uppercase;"
        "display:inline-block;padding:4px 9px;border:1px solid var(--line);border-radius:999px;background:var(--surface-alt);}"
        ".choice-card h2{margin:0;font-size:1.06rem;line-height:1.3;}"
        ".decision-label{margin:0;font-weight:700;color:var(--text);}"
        ".subtitle{margin:0;color:var(--muted);font-size:.9rem;}"
        ".key-reasons{margin:0;list-style:none;padding:0;display:grid;gap:7px;}"
        ".reason-item,.risks,.recommendation-reason{margin:0;font-size:.87rem;color:var(--muted);display:flex;gap:6px;align-items:flex-start;}"
        ".reason-icon{color:var(--accent-strong);font-weight:800;line-height:1.2;display:inline-block;min-width:12px;}"
        ".cta{display:inline-block;margin-top:auto;padding:10px 12px;border-radius:12px;text-decoration:none;font-weight:700;"
        "background:var(--accent-strong);color:var(--button-text);text-align:center;border:1px solid transparent;}"
        ".cta:hover{filter:brightness(1.05);}"
        ".more-section{margin-top:18px;background:var(--surface);border:1px dashed var(--line-strong);border-radius:14px;padding:12px 14px;}"
        ".more-section h3{margin:0 0 8px;font-size:.98rem;color:var(--muted);}"
        ".more-section ul{margin:0;padding-left:18px;color:var(--muted);}"
        ".demo-note{margin:14px auto 0;max-width:1160px;padding:0 20px 12px;color:var(--muted);font-size:.82rem;position:relative;z-index:1;}"
        ".site-footer{margin-top:auto;border-top:1px solid var(--line);background:transparent;position:relative;z-index:1;}"
        ".footer-inner{max-width:1160px;margin:0 auto;padding:10px 20px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;}"
        ".footer-links{display:flex;gap:14px;flex-wrap:wrap;align-items:center;}"
        ".footer-links a,.footer-links span{text-decoration:none;color:var(--muted);font-size:.82rem;}"
        ".footer-links a:hover{text-decoration:underline;}"
        ".sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;}"
        "@media (max-width:860px){.site-header{flex-direction:column;align-items:flex-start;gap:10px;}.header-controls{width:100%;justify-content:space-between;}"
        ".main-nav{gap:10px;flex-wrap:wrap;}.footer-inner{flex-direction:column;align-items:flex-start;}.footer-links{gap:10px;}}"
        "@media (max-width:620px){.search-shell{padding:6px 6px 6px 12px;}.search-form button{height:40px;min-width:40px;padding:0 13px;}}"
        "</style>"
        "</head><body>"
        '<main class="picwise-landing">'
        '<header class="site-header">'
        '<div class="brand">Picwise</div>'
        '<div class="header-controls">'
        '<nav class="main-nav" aria-label="Primary">'
        '<a href="#how">Πώς λειτουργεί</a>'
        '<a href="#faq">FAQ</a>'
        '<a href="#about">Σχετικά με</a>'
        "</nav>"
        '<button id="theme-toggle" class="theme-toggle" type="button" aria-label="Toggle day/night theme" aria-pressed="false" data-current="light">'
        '<span class="mode mode-light">☀ Day</span>'
        '<span class="mode mode-dark">☾ Night</span>'
        "</button>"
        "</div>"
        "</header>"
        '<section class="hero">'
        f"<h1>{escape(decision_output.page_title)}</h1>"
        "<p>Smart recommendations, side-by-side. Compare and choose with confidence.</p>"
        "</section>"
        '<form class="search-form" action="/demo" method="get">'
        '<label class="sr-only" for="query-input">Search query</label>'
        '<div class="search-shell">'
        '<span class="search-icon" aria-hidden="true">⌕</span>'
        f'<input id="query-input" type="search" name="q" value="{escape(decision_output.query)}" '
        'placeholder="Search a purchase intent query" autocomplete="off">'
        '<button type="submit" aria-label="Search">→</button>'
        "</div>"
        "</form>"
        f'<p class="query-confirmation">Showing 4 decision-ready options for: {escape(decision_output.query)}</p>'
        '<section class="primary-choices" data-card-count="4">'
        f"{''.join(cards_html)}"
        "</section>"
        f"{more_section}"
        "</main>"
        '<p class="demo-note">Demo data source: local_test_fixture (not_production_data).</p>'
        '<footer class="site-footer">'
        '<div class="footer-inner">'
        '<div class="footer-links footer-left">'
        '<a href="#about">Σχετικά με</a>'
        '<a href="#contact">Επικοινωνία</a>'
        '<a href="#how">Πώς λειτουργεί</a>'
        '<a href="#faq">FAQ</a>'
        "</div>"
        '<div class="footer-links footer-right">'
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
