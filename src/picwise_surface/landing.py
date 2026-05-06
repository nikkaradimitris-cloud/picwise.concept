from __future__ import annotations

from html import escape

from picwise_contracts import ContractValidationError, DecisionOutput


def render_landing_surface(decision_output: DecisionOutput) -> str:
    """Render a lightweight HTML landing surface from a validated decision output."""
    choices = decision_output.choices
    if len(choices) != 4:
        raise ContractValidationError("Landing UI requires exactly 4 primary choices.")

    recommended_count = sum(1 for choice in choices if choice.is_recommended)
    if recommended_count != 1:
        raise ContractValidationError("Landing UI requires exactly 1 recommended primary choice.")

    cards_html = []
    for choice in choices:
        recommended_header = ""
        if choice.is_recommended:
            recommended_header = (
                '<div class="recommended-top">'
                '<p class="recommended-badge">Recommended by Picwise</p>'
                '<div class="recommended-bubbles" aria-hidden="true">'
                '<span class="bubble-chip">Best fit</span>'
                '<span class="bubble-chip">Fast decision</span>'
                "</div>"
                "</div>"
            )

        recommendation_reason = ""
        if choice.is_recommended:
            reason = str(choice.tracking_metadata.get("recommendation_reason", "")).strip()
            recommendation_reason = (
                f'<p class="recommendation-reason">{escape(reason)}</p>' if reason else ""
            )

        key_reasons_html = "".join(f"<li>{escape(reason)}</li>" for reason in choice.key_reasons[:3])
        risk_html = (
            f'<p class="risks">{escape(choice.risks_or_limitations)}</p>'
            if str(choice.risks_or_limitations).strip()
            else ""
        )
        card_class = "choice-card recommended" if choice.is_recommended else "choice-card"
        cards_html.append(
            (
                f'<article class="{card_class}" data-choice-id="{escape(choice.product_id)}">'
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
        ":root{color-scheme:light dark;--bg:#f4f7fc;--surface:#ffffff;--surface-alt:#f8fbff;"
        "--text:#122034;--muted:#425c78;--line:#d5e1f0;--line-strong:#9cb5d4;--accent:#1667d9;"
        "--accent-strong:#0f4ea9;--button-text:#ffffff;--chip-bg:#eef4ff;--chip-text:#1d4f8f;}"
        "body[data-theme='dark']{--bg:#0e1520;--surface:#141f2e;--surface-alt:#1a2a3f;--text:#e6eef9;"
        "--muted:#a8bdd9;--line:#2d425f;--line-strong:#4e6f99;--accent:#6ea5ff;--accent-strong:#93bcff;"
        "--button-text:#07101f;--chip-bg:#223850;--chip-text:#c8e0ff;}"
        "*{box-sizing:border-box;}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);"
        "color:var(--text);line-height:1.45;}"
        ".picwise-landing{max-width:1140px;margin:0 auto;padding:24px 18px 28px;}"
        ".top-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;}"
        "h1{margin:0;font-size:1.55rem;letter-spacing:-.01em;}"
        ".theme-toggle{border:1px solid var(--line);background:var(--surface);color:var(--text);padding:8px 12px;"
        "border-radius:999px;font-weight:600;cursor:pointer;}"
        ".search-form{display:flex;gap:10px;align-items:center;margin:10px 0 14px;}"
        ".search-form input{flex:1;min-width:180px;border:1px solid var(--line);border-radius:12px;padding:12px 14px;"
        "font-size:.96rem;background:var(--surface);color:var(--text);}"
        ".search-form button{border:0;border-radius:12px;padding:12px 16px;background:var(--accent);"
        "color:var(--button-text);font-weight:700;cursor:pointer;}"
        ".query-confirmation{margin:0 0 16px;color:var(--muted);}"
        ".primary-choices{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:16px;}"
        ".choice-card{position:relative;overflow:visible;background:var(--surface);border:1px solid var(--line);"
        "border-radius:16px;padding:14px;display:flex;flex-direction:column;gap:10px;min-height:270px;}"
        ".choice-card.recommended{border:2px solid var(--accent);background:var(--surface-alt);}"
        ".choice-card.recommended::after{content:'';position:absolute;inset:-6px;border:2px solid var(--accent);"
        "border-radius:20px;opacity:0;pointer-events:none;animation:recommendedPulse 2.4s ease-out 3;}"
        "@keyframes recommendedPulse{0%{transform:scale(1);opacity:.52;}70%{transform:scale(1.03);opacity:0;}"
        "100%{transform:scale(1.03);opacity:0;}}"
        ".recommended-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;}"
        ".recommended-badge{display:inline-block;margin:0;background:var(--accent);color:var(--button-text);"
        "border-radius:999px;padding:4px 10px;font-size:.75rem;font-weight:700;}"
        ".recommended-bubbles{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;}"
        ".bubble-chip{display:inline-flex;padding:3px 8px;border-radius:999px;background:var(--chip-bg);"
        "color:var(--chip-text);font-size:.7rem;font-weight:600;border:1px solid var(--line);}"
        ".role-badge{margin:0;font-size:.76rem;font-weight:700;letter-spacing:.04em;color:var(--chip-text);"
        "text-transform:uppercase;}"
        "h2{margin:0;font-size:1.02rem;}"
        ".decision-label{margin:0;font-weight:700;color:var(--text);}"
        ".subtitle{margin:0;color:var(--muted);font-size:.9rem;}"
        ".key-reasons{margin:0;padding-left:18px;color:var(--text);}"
        ".risks,.recommendation-reason{margin:0;font-size:.88rem;color:var(--muted);}"
        ".cta{display:inline-block;margin-top:auto;padding:10px 12px;border-radius:10px;text-decoration:none;"
        "font-weight:700;background:var(--accent-strong);color:var(--button-text);text-align:center;"
        "border:1px solid transparent;}"
        ".more-section{margin-top:18px;background:var(--surface);border:1px dashed var(--line-strong);"
        "border-radius:14px;padding:12px 14px;}"
        ".more-section h3{margin:0 0 8px;font-size:.98rem;color:var(--muted);}"
        ".more-section ul{margin:0;padding-left:18px;color:var(--muted);}"
        ".bottom-bar{margin-top:18px;border:1px solid var(--line);background:transparent;border-radius:12px;"
        "padding:10px 12px;text-align:center;color:var(--muted);font-size:.88rem;}"
        ".demo-metadata{margin-top:12px;color:var(--muted);font-size:.84rem;}"
        ".sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;"
        "clip:rect(0,0,0,0);white-space:nowrap;border:0;}"
        "@media (max-width:700px){.top-row{align-items:flex-start;flex-direction:column;}.theme-toggle{width:auto;}"
        ".search-form{flex-direction:column;}.search-form input,.search-form button{width:100%;}}"
        "</style>"
        "</head><body>"
        '<main class="picwise-landing">'
        '<header class="page-header"><div class="top-row">'
        f"<h1>{escape(decision_output.page_title)}</h1>"
        '<button id="theme-toggle" class="theme-toggle" type="button" aria-label="Toggle day/night theme">Night mode</button>'
        "</div>"
        '<form class="search-form" action="/demo" method="get">'
        '<label class="sr-only" for="query-input">Search query</label>'
        f'<input id="query-input" type="search" name="q" value="{escape(decision_output.query)}"'
        ' placeholder="Search a purchase intent query" autocomplete="off">'
        '<button type="submit">Search</button>'
        "</form>"
        f'<p class="query-confirmation">Showing 4 decision-ready options for: '
        f"{escape(decision_output.query)}</p>"
        "</header>"
        '<section class="primary-choices" data-card-count="4">'
        f"{''.join(cards_html)}"
        "</section>"
        f"{more_section}"
        '<footer class="bottom-bar">Designed by Subby.cloud</footer>'
        "<script>"
        "(function(){var root=document.body;var key='picwise_theme';var btn=document.getElementById('theme-toggle');"
        "if(!btn){return;}var setTheme=function(theme){var isDark=theme==='dark';root.setAttribute('data-theme',isDark?'dark':'light');"
        "btn.textContent=isDark?'Day mode':'Night mode';btn.setAttribute('aria-pressed',isDark?'true':'false');};"
        "var saved='';try{saved=window.localStorage.getItem(key)||'';}catch(e){saved='';}"
        "if(saved==='dark'||saved==='light'){setTheme(saved);}else{setTheme('light');}"
        "btn.addEventListener('click',function(){var next=root.getAttribute('data-theme')==='dark'?'light':'dark';setTheme(next);"
        "try{window.localStorage.setItem(key,next);}catch(e){}});})();"
        "</script>"
        "</main>"
        "</body></html>"
    )
