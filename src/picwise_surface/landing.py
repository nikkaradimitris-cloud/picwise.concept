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
        role_class = f" pw-role-{escape(choice.role.value)}"
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
                f'<p class="pw-role-pill{role_class}">{escape(choice.role.value)}</p>'
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
        ":root{color-scheme:light dark;--bg:#f7faff;--surface:#ffffff;--surface-alt:#f6f9ff;--text:#1f2e46;"
        "--muted:#607396;--line:#dbe5f3;--line-strong:#9cb5d7;--accent:#1e68ff;--accent-strong:#0f58e0;"
        "--button-text:#ffffff;--ring:#4c89f0;--footer:#f2f6fd;}"
        "body[data-theme='dark']{--bg:#0f1725;--surface:#162233;--surface-alt:#1b2a40;--text:#e8f1ff;--muted:#b4c6de;"
        "--line:#30435e;--line-strong:#51729f;--accent:#79b1ff;--accent-strong:#9cc6ff;--button-text:#091427;--ring:#8ebcff;--footer:#111b2a;}"
        "*{box-sizing:border-box;}html,body{min-height:100%;}"
        "body{margin:0;padding:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.45;display:flex;flex-direction:column;}"
        ".pw-shell{position:relative;max-width:1200px;margin:0 auto;padding:max(14px,env(safe-area-inset-top)) 22px 22px;flex:1;width:100%;}"
        ".pw-bg-network-left,.pw-bg-circuit-right{position:absolute;pointer-events:none;z-index:0;}"
        ".pw-bg-network-left{left:-64px;top:88px;width:320px;height:340px;opacity:.23;background:"
        "radial-gradient(circle at 72px 66px,rgba(80,123,181,.25) 0 2px,transparent 3px),"
        "radial-gradient(circle at 170px 104px,rgba(80,123,181,.25) 0 2px,transparent 3px),"
        "radial-gradient(circle at 114px 188px,rgba(80,123,181,.25) 0 2px,transparent 3px),"
        "linear-gradient(122deg,transparent 44%,rgba(115,152,203,.24) 45% 45.8%,transparent 46.8%),"
        "linear-gradient(88deg,transparent 39%,rgba(115,152,203,.22) 40% 40.8%,transparent 41.8%),"
        "linear-gradient(58deg,transparent 58%,rgba(115,152,203,.17) 59% 59.6%,transparent 60.6%);}"
        ".pw-bg-circuit-right{right:-58px;top:96px;width:330px;height:360px;opacity:.2;background:"
        "linear-gradient(178deg,transparent 16%,rgba(97,141,199,.28) 16% 16.7%,transparent 16.7% 34%,rgba(97,141,199,.24) 34% 34.7%,transparent 34.7% 57%,rgba(97,141,199,.2) 57% 57.6%,transparent 57.6%),"
        "linear-gradient(90deg,transparent 14%,rgba(97,141,199,.24) 14% 14.7%,transparent 14.7% 61%,rgba(97,141,199,.22) 61% 61.7%,transparent 61.7%),"
        "radial-gradient(circle at 247px 86px,rgba(97,141,199,.28) 0 2px,transparent 3px),"
        "radial-gradient(circle at 224px 214px,rgba(97,141,199,.24) 0 2px,transparent 3px);}"
        ".pw-topbar{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 17px;padding:0;min-height:44px;}"
        ".pw-brand{display:flex;align-items:center;gap:12px;font-size:2rem;font-weight:800;color:var(--text);text-transform:lowercase;letter-spacing:-.022em;line-height:1;}"
        ".pw-logo-mark{position:relative;width:42px;height:42px;border-radius:14px;background:linear-gradient(165deg,#38a1ff,#1e68ff 61%,#0d57db);box-shadow:inset 0 0 0 1px rgba(255,255,255,.28),0 6px 14px rgba(15,88,224,.22);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:1.72rem;font-weight:900;line-height:1;}"
        ".pw-logo-mark::before{content:'';position:absolute;width:22px;height:22px;border:3px solid #fff;border-right-width:4px;border-radius:999px;left:8px;top:8px;opacity:.96;}"
        ".pw-logo-mark::after{content:'';position:absolute;width:8px;height:8px;background:#fff;border-radius:50%;right:8px;bottom:10px;opacity:.97;}"
        ".pw-nav{display:flex;align-items:center;gap:14px;}"
        ".pw-nav a{text-decoration:none;color:var(--muted);font-size:.9rem;font-weight:600;}"
        ".pw-nav a:hover{text-decoration:underline;}"
        ".pw-theme-toggle-wrap{display:flex;flex-direction:column;align-items:center;gap:2px;}"
        ".pw-theme-toggle{border:1px solid var(--line);border-radius:999px;background:linear-gradient(180deg,#ffffff,#f4f8ff);padding:4px 6px;min-width:154px;height:42px;display:grid;grid-template-columns:1fr 1.6fr 1fr;align-items:center;cursor:pointer;box-shadow:inset 0 0 0 1px rgba(255,255,255,.68);}"
        ".pw-theme-slot{display:flex;justify-content:center;align-items:center;color:#8c9fbe;font-size:1.15rem;line-height:1;}"
        ".pw-theme-knob{position:relative;height:26px;border-radius:999px;background:#d6e3f8;padding:2px;display:flex;align-items:center;transition:background .2s ease;}"
        ".pw-theme-knob::after{content:'';width:22px;height:22px;border-radius:50%;background:var(--accent);box-shadow:0 4px 9px rgba(30,104,255,.36);transition:transform .2s ease,background .2s ease;}"
        ".pw-theme-toggle[data-current='dark'] .pw-theme-knob::after{transform:translateX(16px);}"
        ".pw-theme-toggle[data-current='dark'] .pw-theme-knob{background:#d0d9ea;}"
        ".pw-theme-label{font-size:.74rem;font-weight:700;color:#7a92b6;line-height:1;}"
        ".pw-hero{position:relative;z-index:1;text-align:center;max-width:1060px;margin:0 auto 12px;padding-top:0;}"
        ".pw-hero h1{margin:0 0 8px;font-size:clamp(1.4rem,2.15vw,2.08rem);line-height:1.16;letter-spacing:-.013em;font-weight:700;}"
        ".pw-hero p{margin:0 auto;color:var(--muted);font-size:.95rem;max-width:640px;}"
        ".pw-search-shell{position:relative;z-index:1;max-width:804px;margin:0 auto 8px;display:flex;align-items:center;gap:10px;background:var(--surface);"
        "border:1px solid #d5e1f1;border-radius:999px;padding:7px 8px 7px 16px;box-shadow:0 10px 24px rgba(16,32,56,0.06);}"
        ".pw-search-icon,.pw-search-button-icon{position:relative;display:inline-block;width:14px;height:14px;color:currentColor;}"
        ".pw-search-icon::before,.pw-search-button-icon::before{content:'';position:absolute;left:0;top:0;width:9px;height:9px;border:2px solid currentColor;border-radius:50%;}"
        ".pw-search-icon::after,.pw-search-button-icon::after{content:'';position:absolute;width:7px;height:2px;background:currentColor;right:-1px;bottom:1px;transform:rotate(45deg);transform-origin:right center;border-radius:2px;}"
        ".pw-search-shell input{flex:1;min-width:170px;border:0;outline:none;background:transparent;color:var(--text);font-size:.95rem;text-align:center;font-weight:600;}"
        ".pw-search-button{border:0;border-radius:999px;height:38px;min-width:52px;padding:0 16px;background:var(--accent);color:var(--button-text);font-weight:800;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;box-shadow:0 5px 14px rgba(30,104,255,.28);}"
        ".pw-search-button:hover{background:var(--accent-strong);}"
        ".pw-query{position:relative;z-index:1;text-align:center;color:var(--muted);font-size:.88rem;margin:0 0 13px;}"
        ".pw-grid{position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:17px;}"
        ".pw-card{position:relative;background:var(--surface);border:1px solid #dde8f5;border-radius:20px;padding:15px 14px;display:flex;flex-direction:column;min-height:338px;gap:8px;box-shadow:0 9px 22px rgba(20,44,83,.055);}"
        ".pw-card-recommended{border:2px solid var(--ring);background:linear-gradient(180deg,#ffffff,#f7fbff 78%);box-shadow:0 15px 36px rgba(27,83,185,0.13);}"
        ".pw-rec-badge{display:inline-block;max-width:max-content;background:linear-gradient(180deg,#1f71ff,#0f58e0);color:var(--button-text);font-weight:700;font-size:.79rem;padding:6px 12px;border-radius:999px;letter-spacing:.004em;}"
        ".pw-rec-badge::before{content:'★';display:inline-block;margin-right:6px;font-size:.8em;vertical-align:1px;}"
        ".pw-rec-bubble-top,.pw-rec-bubble-bottom{position:absolute;border:2px solid rgba(76,137,240,.64);border-radius:999px;pointer-events:none;}"
        ".pw-rec-bubble-top{top:-11px;right:-11px;width:46px;height:46px;border-left-color:transparent;border-bottom-color:transparent;}"
        ".pw-rec-bubble-bottom{bottom:-11px;left:-11px;width:40px;height:40px;border-right-color:transparent;border-top-color:transparent;}"
        ".pw-rec-pulse-1,.pw-rec-pulse-2,.pw-rec-pulse-3{position:absolute;border:1px solid rgba(76,137,240,.55);border-radius:24px;pointer-events:none;animation:pwPulse 2.8s ease-out infinite;}"
        ".pw-rec-pulse-1{inset:-6px;animation-delay:0s;}"
        ".pw-rec-pulse-2{inset:-10px;opacity:.68;animation-delay:.35s;}"
        ".pw-rec-pulse-3{inset:-14px;opacity:.56;animation-delay:.7s;}"
        "@keyframes pwPulse{0%{opacity:.42;}55%{opacity:.2;}100%{opacity:.42;}}"
        ".pw-role-pill{margin:0;display:inline-block;max-width:max-content;border-radius:999px;padding:4px 8px;font-size:.74rem;text-transform:uppercase;letter-spacing:.052em;font-weight:700;line-height:1;color:#627aa0;background:#edf3ff;}"
        ".pw-role-budget{color:#5880cb;background:#edf3ff;}"
        ".pw-role-value{color:#2d9b53;background:#eaf8ef;}"
        ".pw-role-best_overall{color:#7051d8;background:#f0ecff;}"
        ".pw-role-premium{color:#5f79ba;background:#ebf1ff;}"
        ".pw-card-title{margin:0;font-size:1.15rem;line-height:1.24;font-weight:700;letter-spacing:-.01em;}"
        ".pw-card-subtitle{margin:0;color:var(--text);font-weight:600;font-size:.89rem;line-height:1.25;}"
        ".pw-divider{height:1px;background:var(--line);}"
        ".pw-price-meta{margin:0;color:var(--muted);font-size:.84rem;line-height:1.36;font-weight:600;}"
        ".pw-reasons{margin:0;padding:0;list-style:none;display:grid;gap:4px;}"
        ".pw-reason-row,.pw-risk-row{margin:0;display:flex;gap:7px;align-items:flex-start;color:#4b6390;font-size:.83rem;line-height:1.36;font-weight:600;}"
        ".pw-icon{display:inline-flex;justify-content:center;min-width:18px;font-weight:800;line-height:1.1;font-size:.9rem;}"
        ".pw-icon-check{color:#3d7cff;}.pw-icon-warn{color:#6581b8;}.pw-icon-star{color:var(--accent);}"
        ".pw-cta{display:inline-block;margin-top:auto;padding:10px 11px;border-radius:11px;text-decoration:none;text-align:center;font-weight:700;background:transparent;color:#2b69da;border:2px solid #93b7fc;font-size:.93rem;}"
        ".pw-cta:hover{border-color:#2b69da;background:rgba(29,110,255,.05);}"
        ".pw-card-recommended .pw-cta{background:linear-gradient(180deg,#1f71ff,#0f58e0);border:0;color:#ffffff;box-shadow:0 7px 16px rgba(30,104,255,.3);}"
        ".pw-card-recommended .pw-cta:hover{background:linear-gradient(180deg,#2a7aff,#115de5);}"
        ".pw-more{position:relative;z-index:1;margin-top:14px;padding:12px 14px;border:1px dashed var(--line-strong);border-radius:12px;background:var(--surface);}"
        ".pw-more h3{margin:0 0 7px;font-size:.95rem;color:var(--muted);} .pw-more ul{margin:0;padding-left:18px;color:var(--muted);}"
        ".pw-demo-note{max-width:1200px;margin:8px auto 0;padding:0 22px 10px;color:var(--muted);font-size:.8rem;}"
        ".pw-footer{margin-top:auto;border-top:1px solid var(--line);background:var(--footer);}"
        ".pw-footer-inner{max-width:1200px;margin:0 auto;padding:10px 22px 11px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}"
        ".pw-footer-left,.pw-footer-right{display:flex;gap:13px;flex-wrap:wrap;align-items:center;}"
        ".pw-footer a,.pw-footer span{text-decoration:none;color:var(--muted);font-size:.82rem;}"
        ".pw-footer a:hover{text-decoration:underline;}"
        ".pw-sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;}"
        "@media (max-width:1060px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}"
        "@media (max-width:1140px){.pw-card-title{font-size:1.06rem;}.pw-card-subtitle{font-size:.84rem;}.pw-price-meta,.pw-reason-row,.pw-risk-row,.pw-cta{font-size:.8rem;}}"
        "@media (max-width:840px){.pw-topbar{flex-direction:column;align-items:flex-start;}.pw-nav{flex-wrap:wrap;}.pw-brand{font-size:1.62rem;}.pw-logo-mark{width:38px;height:38px;}.pw-theme-toggle-wrap{align-self:flex-end;}}"
        "@media (max-width:620px){.pw-grid{grid-template-columns:1fr;}.pw-search-shell{padding:7px 7px 7px 12px;}.pw-search-button{height:36px;min-width:44px;padding:0 12px;}.pw-theme-toggle{min-width:136px;height:40px;}.pw-theme-toggle[data-current='dark'] .pw-theme-knob::after{transform:translateX(14px);}.pw-footer-inner{flex-direction:column;align-items:flex-start;}}"
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
        '<div class="pw-theme-toggle-wrap">'
        '<button id="theme-toggle" class="pw-theme-toggle" type="button" aria-label="Toggle day/night theme" aria-pressed="false" data-current="light">'
        '<span class="pw-theme-slot pw-theme-day" aria-hidden="true">☼</span>'
        '<span class="pw-theme-knob" aria-hidden="true"></span>'
        '<span class="pw-theme-slot pw-theme-night" aria-hidden="true">☾</span>'
        "</button>"
        '<span class="pw-theme-label">Day / Night</span>'
        "</div>"
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
