"""The search page's style sheet, written into each page (`reference._PAGE_STYLES`);
moved here word for word from `reference.py` in the clean-up of 2026-11-12."""
from __future__ import annotations

from .fonts import FONT_FACE_CSS

# The page's styles, after the design of 2026-10-31. Every card of a row is as tall as
# the others; the photo is square and shown whole (`object-fit:contain`) at a size fixed
# before it loads, and the role, title and shop lines have fixed heights, so the prices
# and the buttons of a row line up and nothing moves while the page loads.
_PAGE_STYLES = (
    FONT_FACE_CSS +
    # Colours of 2026-11-12 (owner: «κράτα το απλό σοβαρό και αξιόπιστο»): one blue for
    # what is tapped, neutral greys for words and lines instead of bluish ones.
    ":root{--blue:#1a4fb7;--blue-2:#1f5fd6;--ink:#0f2442;--ink-2:#3d4f66;--muted:#66768c;--line:#e1e7ef;--bg:#f6f8fb;--card:#fff;--green:#1d8a4e;}"
    "*{box-sizing:border-box;}html,body{min-height:100%;}"
    "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:var(--ink);background:var(--bg);-webkit-text-size-adjust:100%;}"
    ".pw-reference-viewport{min-height:100vh;display:flex;flex-direction:column;}"
    ".pw-topbar{position:relative;background:#fff;border-bottom:1px solid var(--line);z-index:20;}"
    ".pw-topbar-inner{max-width:1190px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;justify-content:space-between;gap:12px;}"
    ".pw-brand{display:flex;align-items:center;gap:9px;text-decoration:none;color:var(--ink);min-width:0;}"
    ".pw-logo{width:34px;height:34px;border-radius:11px;background:linear-gradient(160deg,#30a0ff 0%,#1f6cff 70%);position:relative;flex:0 0 auto;}"
    ".pw-logo::before{content:'';position:absolute;left:7px;top:7px;width:13px;height:13px;border:3px solid #fff;border-right-color:transparent;border-radius:999px;}"
    ".pw-logo::after{content:'';position:absolute;right:7px;bottom:7px;width:6px;height:6px;background:#fff;border-radius:999px;}"
    ".pw-brand-text{display:flex;flex-direction:column;line-height:1;}"
    ".pw-brand-name{font-size:26px;font-weight:800;letter-spacing:-.04em;text-transform:lowercase;}"
    ".pw-actions{display:flex;align-items:center;gap:8px;}"
    ".pw-topbar-control{display:inline-flex;align-items:center;justify-content:center;height:36px;padding:0 13px;border-radius:999px;font:inherit;font-size:14px;font-weight:600;line-height:1;border:1px solid transparent;white-space:nowrap;cursor:pointer;}"
    ".pw-info-link{background:#fff;color:var(--ink-2);border-color:var(--line);}"
    ".pw-info-link:hover,.pw-info-link[aria-expanded=true]{background:#eef4ff;border-color:#c9daf8;color:var(--blue);}"
    ".pw-info-link:focus-visible{outline:2px solid var(--blue);outline-offset:3px;}"
    ".pw-info-icon{display:none;font-weight:800;}"
    ".pw-info-wrap{position:relative;display:inline-flex;}"
    ".pw-tooltip{position:absolute;top:calc(100% + 10px);right:0;width:min(400px,calc(100vw - 24px));background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:0 16px 40px rgba(16,40,80,.16);padding:12px 14px;font-size:14px;line-height:1.5;color:var(--ink);text-align:left;display:none;z-index:40;}"
    ".pw-info-wrap.is-open .pw-tooltip{display:block;}"
    ".pw-reference-frame{width:100%;max-width:1190px;margin:0 auto;padding:22px 22px 10px;flex:1;}"
    ".pw-home{padding-top:56px;}"
    ".pw-hero-home{text-align:center;margin:0 auto 24px;max-width:760px;}"
    ".pw-hero-title{margin:0;font-size:38px;line-height:1.15;letter-spacing:-.025em;color:var(--ink);text-wrap:balance;}"
    ".pw-search-wrap{position:relative;width:100%;max-width:700px;margin:0 auto 18px;}"
    ".pw-search-shell{display:flex;align-items:center;gap:10px;width:100%;height:56px;background:#fff;border:1.5px solid #c9d5e6;border-radius:999px;padding:0 6px 0 18px;box-shadow:0 6px 22px rgba(15,36,66,.08);}"
    ".pw-search-shell:focus-within{border-color:var(--blue-2);box-shadow:0 0 0 4px rgba(31,95,214,.12);}"
    ".pw-search-icon,.pw-search-button-icon{position:relative;width:16px;height:16px;display:inline-block;color:#7c93b7;flex:0 0 auto;}"
    ".pw-search-icon::before,.pw-search-button-icon::before{content:'';position:absolute;left:0;top:0;width:10px;height:10px;border:2px solid currentColor;border-radius:999px;}"
    ".pw-search-icon::after,.pw-search-button-icon::after{content:'';position:absolute;right:1px;bottom:2px;width:7px;height:2px;background:currentColor;border-radius:2px;transform:rotate(45deg);transform-origin:right center;}"
    ".pw-input-wrap{position:relative;flex:1;display:flex;align-items:center;min-width:0;height:100%;}"
    ".pw-search-input{flex:1;width:100%;height:52px;padding:0;border:0;background:transparent;outline:none;font-family:inherit;font-size:18px;color:var(--ink);font-weight:500;letter-spacing:normal;}"
    ".pw-search-input::placeholder{color:#8ea2c0;}"
    ".pw-ghost{position:absolute;left:0;top:0;bottom:0;display:flex;align-items:center;font-family:inherit;font-size:18px;font-weight:500;letter-spacing:normal;white-space:pre;overflow:hidden;pointer-events:none;max-width:100%;}"
    ".pw-ghost-typed{visibility:hidden;}"
    ".pw-ghost-rest{color:#bccbe0;pointer-events:auto;cursor:pointer;}"
    ".pw-search-button{width:44px;height:44px;border-radius:999px;border:0;background:var(--blue-2);display:inline-flex;align-items:center;justify-content:center;cursor:pointer;flex:0 0 auto;}"
    ".pw-search-button .pw-search-button-icon{color:#fff;}"
    ".pw-mic-button{width:42px;height:42px;border-radius:999px;border:1px solid var(--line);background:#fff;color:#4f6f9c;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;flex:0 0 auto;padding:0;}"
    ".pw-mic-button[hidden]{display:none;}"
    ".pw-mic-button.is-listening{background:#ffecec;border-color:#f0b3b3;color:#c43c3c;}"
    ".pw-mic-button:focus-visible,.pw-search-button:focus-visible{outline:2px solid var(--blue);outline-offset:3px;}"
    ".pw-suggest{position:absolute;left:0;right:0;top:calc(100% + 6px);margin:0;padding:6px 0;list-style:none;background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:0 16px 40px rgba(16,40,80,.12);z-index:25;text-align:left;}"
    ".pw-suggest[hidden]{display:none;}"
    ".pw-suggest-item{padding:9px 18px;font-size:16px;color:var(--ink);cursor:pointer;}"
    ".pw-suggest-item.is-active,.pw-suggest-item:hover{background:#eef4ff;}"
    ".pw-results-head{display:flex;align-items:center;justify-content:space-between;gap:8px 12px;flex-wrap:wrap;margin:8px 0 2px;}"
    ".pw-query-line{margin:0;font-size:15px;color:#1a3d6b;font-weight:600;line-height:1.4;}"
    ".pw-results-count{margin:0;font-size:13px;font-weight:700;color:var(--ink-2);background:#fff;border:1px solid var(--line);border-radius:999px;padding:4px 12px;white-space:nowrap;}"
    ".pw-reference-disclaimer{margin:4px 0 14px;font-size:13px;line-height:1.5;color:var(--muted);}"
    ".pw-reference-disclaimer a{color:var(--blue);font-weight:600;}"
    # A search with nothing to show: its message is the page's answer, so it reads as one.
    '.pw-reference-frame:has(.pw-grid[data-card-count="0"]) .pw-reference-disclaimer{max-width:760px;margin:10px auto 0;font-size:16px;line-height:1.55;color:var(--ink);text-align:center;}'
    ".pw-kind-choices{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:10px 0 4px;}"
    ".pw-kind-choices-ask{font-size:14px;font-weight:700;color:var(--ink);margin-right:4px;}"
    ".pw-kind-choice{display:inline-flex;align-items:center;height:32px;padding:0 13px;border-radius:999px;background:#eaf1ff;color:var(--blue);font-size:13px;font-weight:600;text-decoration:none;}"
    ".pw-kind-choice:hover{background:#dce8ff;}"
    ".pw-kind-choice:focus-visible{outline:2px solid var(--blue-2);outline-offset:3px;}"
    ".pw-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;align-items:stretch;width:100%;margin:0 auto;}"
    '.pw-grid[data-card-count="2"],.pw-grid[data-card-count="3"]{grid-template-columns:repeat(auto-fit,minmax(0,280px));justify-content:center;}'
    ".pw-card{position:relative;display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px;min-width:0;}"
    ".pw-card-recommended{border:2px solid var(--blue-2);box-shadow:0 10px 26px rgba(47,111,228,.14);padding:11px;}"
    ".pw-anchor{position:absolute;top:-80px;}"
    ".pw-product-image-wrap{position:relative;aspect-ratio:1/1;width:100%;border-radius:12px;background:#fff;border:1px solid #edf2fa;display:flex;align-items:center;justify-content:center;overflow:hidden;}"
    ".pw-product-image{display:block;width:100%;height:100%;object-fit:contain;color:transparent;}"
    # A card is seen only once its photo has loaded, and one whose photo fails never
    # (HEAD_SCRIPT marks them; owner, 2026-11-01). Its place is kept while the photo
    # loads, so nothing moves when it appears.
    ".pw-photo-guard .pw-card{visibility:hidden;opacity:0;}"
    ".pw-photo-guard .pw-card.pw-photo-ok{visibility:visible;opacity:1;transition:opacity .15s ease-out;}"
    ".pw-card.pw-no-photo{display:none;}"
    ".pw-card-body{display:flex;flex-direction:column;flex:1;min-width:0;}"
    ".pw-role{display:flex;flex-direction:column;align-items:flex-start;gap:4px;height:46px;margin:10px 0 4px;overflow:hidden;}"
    ".pw-rec-badge{display:inline-flex;align-items:center;height:24px;padding:0 10px;border-radius:999px;background:var(--blue-2);color:#fff;font-size:11px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap;}"
    ".pw-role-label{margin:0;display:inline-flex;align-items:center;max-width:100%;height:22px;padding:0 9px;border-radius:999px;background:#eef3fb;color:var(--ink-2);font-size:11px;font-weight:800;letter-spacing:.03em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
    ".pw-card-recommended .pw-role-label{height:auto;padding:0;background:none;color:var(--blue);font-size:12px;letter-spacing:0;text-transform:none;}"
    ".pw-card-title{margin:0;font-size:15px;line-height:1.35;font-weight:650;color:var(--ink);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;height:4.05em;}"
    ".pw-card-shop{margin:6px 0 0;font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
    ".pw-price{margin:8px 0 2px;font-size:24px;line-height:1.15;font-weight:800;letter-spacing:-.02em;color:var(--ink);}"
    ".pw-card-stock{margin:0;font-size:13px;font-weight:650;line-height:1.35;}"
    ".pw-stock-listed,.pw-stock-verified{color:var(--green);}"
    ".pw-stock-unconfirmed{color:var(--muted);}"
    ".pw-card-description{margin:2px 0 0;font-size:12px;line-height:1.35;color:var(--muted);min-height:16px;}"
    ".pw-card-extra{margin:2px 0 0;font-size:12px;font-weight:650;color:var(--blue);}"
    ".pw-meta{margin:4px 0 0;font-size:12px;line-height:1.4;color:var(--muted);}"
    ".pw-feature-list{margin:6px 0 0;padding:0;list-style:none;display:grid;gap:4px;}"
    ".pw-feature-item{display:flex;align-items:flex-start;gap:7px;font-size:12px;color:var(--ink-2);line-height:1.35;}"
    ".pw-feature-dot{width:7px;height:7px;border-radius:999px;background:#5b8ce5;flex:0 0 auto;margin-top:4px;}"
    ".pw-warning{margin:6px 0 0;font-size:11px;color:#5a7498;line-height:1.35;display:flex;gap:6px;}"
    ".pw-warning-icon{font-size:10px;color:#6f86ad;line-height:1.2;margin-top:1px;}"
    ".pw-rec-note{margin:6px 0 0;font-size:11px;line-height:1.35;color:#2e4c7d;background:#eef4ff;border-radius:8px;padding:6px 8px;}"
    ".pw-card-note{margin:8px 0 0;font-size:11.5px;line-height:1.4;color:#7b8ba3;}"
    ".pw-role-label[data-offer]{background:#fff1e6;color:#b4471f;}"
    ".pw-card-offer{margin:6px 0 0;padding:7px 9px;border-radius:10px;background:#fff7f0;border:1px solid #f6d9c2;}"
    ".pw-offer-title{margin:0;font-size:12.5px;font-weight:700;line-height:1.35;color:#9a3b12;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}"
    ".pw-offer-meta{margin:2px 0 0;font-size:11.5px;color:#8a5a3c;}"
    ".pw-offer-code{font-family:ui-monospace,Menlo,Consolas,monospace;letter-spacing:.04em;color:#9a3b12;}"
    ".pw-offer-terms{margin:4px 0 0;font-size:11px;color:#8a5a3c;}"
    ".pw-offer-terms summary{cursor:pointer;}"
    ".pw-offer-terms p{margin:4px 0 0;line-height:1.4;}"
    ".pw-card-body>:nth-last-child(2){margin-bottom:12px;}"
    ".pw-card-cta{margin-top:auto;display:block;width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--blue-2);color:var(--blue-2);background:#fff;font:inherit;font-size:14px;font-weight:700;text-align:center;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;}"
    ".pw-card-cta:hover{background:#eef4ff;}"
    ".pw-card-recommended .pw-card-cta{background:var(--blue-2);color:#fff;}"
    ".pw-card-recommended .pw-card-cta:hover{background:var(--blue);}"
    ".pw-card-cta:focus-visible{outline:2px solid var(--blue);outline-offset:2px;}"
    '.pw-grid[data-layout="single"]{display:block;max-width:980px;}'
    '.pw-grid[data-layout="single"] .pw-card{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:26px;padding:20px;border-radius:18px;}'
    '.pw-grid[data-layout="single"] .pw-role{height:auto;margin:0 0 6px;}'
    '.pw-grid[data-layout="single"] .pw-role:empty{display:none;}'
    '.pw-grid[data-layout="single"] .pw-card-title{font-size:22px;line-height:1.3;height:auto;-webkit-line-clamp:4;}'
    '.pw-grid[data-layout="single"] .pw-price{font-size:32px;margin-top:12px;}'
    '.pw-grid[data-layout="single"] .pw-card-cta{display:inline-block;width:auto;max-width:100%;align-self:flex-start;padding:12px 28px;background:var(--blue-2);color:#fff;}'
    '.pw-grid[data-layout="single"] .pw-card-cta:hover{background:var(--blue);}'
    ".pw-single-only{margin:0 0 12px;padding:10px 12px;background:#f0f5ff;border:1px solid #d6e3fb;border-radius:10px;color:var(--ink-2);font-size:14px;line-height:1.45;}"
    ".pw-single-facts{list-style:none;margin:14px 0 0;padding:0;font-size:14px;color:var(--ink-2);}"
    ".pw-single-facts li{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #eef2f8;}"
    ".pw-fact-name{color:var(--muted);min-width:120px;}"
    ".pw-more{display:flex;flex-direction:column;align-items:center;gap:10px;margin:24px auto 0;}"
    ".pw-counter{margin:0;font-size:14px;font-weight:600;color:var(--ink-2);}"
    ".pw-more-button{display:inline-flex;align-items:center;justify-content:center;height:44px;padding:0 34px;border-radius:999px;background:#fff;border:1px solid var(--blue-2);color:var(--blue-2);font-size:15px;font-weight:700;text-decoration:none;}"
    ".pw-more-button:hover{background:#eef4ff;}"
    ".pw-more-button:focus-visible{outline:2px solid var(--blue);outline-offset:3px;}"
    ".pw-demo-note{text-align:center;font-size:12px;line-height:1.5;color:var(--muted);margin:18px auto 0;max-width:760px;}"
    ".pw-empty-state{max-width:760px;margin:12px auto 0;background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;color:var(--ink-2);font-size:14px;line-height:1.6;text-align:left;}"
    ".pw-facts{list-style:none;display:flex;justify-content:center;flex-wrap:wrap;gap:10px 28px;max-width:820px;margin:20px auto 0;padding:0;}"
    ".pw-fact{display:flex;align-items:center;gap:8px;font-size:14px;line-height:1.4;color:var(--ink-2);}"
    ".pw-fact b{color:var(--ink);font-weight:700;}"
    ".pw-fact svg{width:19px;height:19px;flex:0 0 auto;color:var(--blue-2);}"
    ".pw-footer{margin-top:48px;padding:18px max(22px,calc((100% - 1146px) / 2));background:#fff;border-top:1px solid var(--line);}"
    ".pw-footer-links{display:flex;flex-wrap:wrap;gap:0 20px;}"
    ".pw-footer-link{display:inline-flex;align-items:center;padding:6px 0;font-size:13px;color:var(--ink-2);text-decoration:none;white-space:nowrap;}"
    ".pw-footer-link:hover{color:var(--ink);text-decoration:underline;}"
    ".pw-footer-disclosure{margin:10px 0 0;font-size:12px;line-height:1.5;color:var(--muted);max-width:820px;}"
    ".pw-footer-meta{margin:6px 0 0;font-size:12px;color:var(--muted);}"
    # The loading screen (owner, 2026-11-12: «φτιάξε απλά ένα όμορφο φόρτωμα»): a calm
    # veil over the page and the PicWise mark in a turning ring. It fades in after a
    # moment, so an answer that comes at once shows no flash.
    ".pw-scan{position:fixed;top:0;right:0;bottom:0;left:0;background:rgba(246,248,251,.86);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:16px;z-index:50;animation:pw-scan-in .2s ease-out .12s both;}"
    ".pw-scan[hidden]{display:none;}"
    "@keyframes pw-scan-in{from{opacity:0;}to{opacity:1;}}"
    ".pw-loader{position:relative;width:68px;height:68px;display:flex;align-items:center;justify-content:center;}"
    ".pw-loader-ring{position:absolute;top:0;right:0;bottom:0;left:0;border-radius:999px;border:3px solid #dfe6f0;border-top-color:var(--blue-2);animation:pw-spin .8s linear infinite;}"
    "@keyframes pw-spin{to{transform:rotate(360deg);}}"
    ".pw-scan-text{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0;}"
    "@keyframes pw-breathe{from{opacity:.35;}to{opacity:1;}}"
    "@media (prefers-reduced-motion:reduce){.pw-scan{animation:none;}.pw-loader-ring{animation:pw-breathe 1.2s ease-in-out infinite alternate;}}"
    "@media (max-width:1099px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}"
    "@media (max-width:760px){"
    '.pw-grid[data-layout="single"] .pw-card{grid-template-columns:1fr;gap:14px;padding:14px;}'
    "}"
    "@media (max-width:699px){"
    ".pw-topbar-inner{padding:10px 14px;}"
    ".pw-brand-name{font-size:22px;}"
    ".pw-logo{width:30px;height:30px;border-radius:10px;}"
    ".pw-logo::before{left:6px;top:6px;width:11px;height:11px;}"
    ".pw-logo::after{right:6px;bottom:6px;width:5px;height:5px;}"
    ".pw-actions{gap:6px;}"
    ".pw-info-txt{display:none;}"
    ".pw-info-icon{display:inline;}"
    # A phone (the audit, 2026-11-10; owner, the same day: «Ζητώ διόρθωση και βελτίωση ...
    # στη ορατότητα σε κινητές συσκευές»). Measured at 360 and 390 px with two cards a
    # row: no "View" button on the first screen, the four cards 2.5 screens long, words
    # at 10 to 13 px, "Mid-priced for this catego" cut, buttons 36 to 40 px. Now one
    # product a row, its photo beside its words, so the Recommended and its button are
    # on the first screen; no word under 12 px; whatever is tapped at least 44 px.
    ".pw-info-link{width:44px;height:44px;padding:0;}"
    ".pw-brand{min-height:44px;}"
    ".pw-reference-frame{padding:12px 12px 8px;}"
    ".pw-home{padding-top:28px;}"
    ".pw-hero-home{margin-bottom:18px;}"
    ".pw-hero-title{font-size:28px;line-height:1.2;}"
    ".pw-facts{flex-direction:column;align-items:flex-start;gap:9px;margin:18px 6px 0;}"
    ".pw-search-wrap{margin-bottom:12px;}"
    ".pw-search-shell{height:56px;padding:0 6px 0 14px;}"
    ".pw-search-input{height:52px;font-size:16px;}"
    ".pw-ghost{font-size:16px;}"
    ".pw-mic-button{width:44px;height:44px;}"
    ".pw-search-button{width:44px;height:44px;}"
    ".pw-suggest-item{padding:12px 18px;}"
    ".pw-results-head{margin:4px 0 2px;}"
    ".pw-query-line{font-size:14px;}"
    ".pw-reference-disclaimer{margin:2px 0 10px;line-height:1.45;}"
    # "Did you mean: bath mat?": the link takes the taps around it, the sentence unmoved.
    ".pw-reference-disclaimer a{position:relative;}"
    ".pw-reference-disclaimer a::after{content:'';position:absolute;top:-13px;right:-8px;bottom:-13px;left:-8px;}"
    ".pw-kind-choice{height:44px;padding:0 15px;font-size:14px;}"
    ".pw-grid,.pw-grid[data-card-count]{grid-template-columns:minmax(0,1fr);gap:10px;}"
    # The photo beside the words that say what the product is; under them, across the
    # card, its limitation, then the price with the button beside it. The card's words
    # stay in their order for a screen reader; only their places on the screen change.
    # A product alone keeps its own layout.
    '.pw-grid:not([data-layout="single"]) .pw-card{display:grid;grid-template-columns:96px minmax(0,1fr);column-gap:12px;row-gap:0;align-items:start;padding:10px;border-radius:14px;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-recommended{padding:9px;}'
    '.pw-grid:not([data-layout="single"]) .pw-product-image-wrap{grid-column:1;grid-row:1 / span 16;border-radius:10px;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body{display:contents;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body>*{grid-column:2;min-width:0;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body>.pw-card-offer{grid-column:1 / -1;grid-row:17;margin-top:8px;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body>.pw-rec-note{grid-column:1 / -1;grid-row:18;margin-top:8px;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body>.pw-card-note{grid-column:1 / -1;grid-row:19;margin:8px 0 0;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body>.pw-price{grid-column:1 / -1;grid-row:20;align-self:center;margin:10px 0 0;font-size:24px;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body>.pw-card-cta{grid-column:1 / -1;grid-row:20;justify-self:end;width:52%;min-width:140px;margin:10px 0 0;}'
    '.pw-grid:not([data-layout="single"]) .pw-card-body>:nth-last-child(2){margin-bottom:0;}'
    ".pw-role{flex-direction:row;flex-wrap:wrap;align-items:center;gap:4px 8px;height:auto;margin:0 0 5px;overflow:visible;}"
    ".pw-rec-badge,.pw-role-label{height:22px;padding:0 8px;font-size:12px;letter-spacing:.02em;}"
    ".pw-role-label{white-space:normal;}"
    ".pw-card-recommended .pw-role-label{height:auto;padding:0;font-size:13px;}"
    ".pw-card-title{font-size:15px;line-height:1.3;-webkit-line-clamp:2;height:auto;max-height:2.6em;}"
    ".pw-card-shop{margin-top:4px;font-size:13px;white-space:normal;}"
    ".pw-card-stock{margin-top:4px;font-size:13px;}"
    ".pw-card-description,.pw-card-extra,.pw-meta,.pw-feature-item{font-size:13px;}"
    ".pw-warning,.pw-rec-note,.pw-offer-meta,.pw-offer-terms{font-size:12px;}"
    ".pw-card-note{font-size:12px;}"
    ".pw-cta-at{display:none;}"
    ".pw-card-cta{display:flex;align-items:center;justify-content:center;min-height:44px;padding:0 12px;font-size:15px;}"
    '.pw-grid[data-layout="single"] .pw-card-cta{display:flex;width:100%;}'
    ".pw-more-button{height:48px;}"
    ".pw-demo-note{font-size:13px;}"
    ".pw-footer{padding:16px 14px;}"
    ".pw-footer-link{min-height:44px;padding:0;font-size:14px;}"
    ".pw-footer-disclosure,.pw-footer-meta{font-size:13px;}"
    "}"
)
