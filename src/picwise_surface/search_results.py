from __future__ import annotations

from html import escape
from urllib.parse import quote

from picwise_offers import AmazonManualMatchStatus, match_manual_amazon_affiliates
from .legal import render_public_footer


def _normalize_query_for_display(query: str) -> str:
    collapsed = " ".join(str(query or "").strip().split())
    return collapsed or "(empty query)"


def _customer_friendly_category(raw_category: str) -> str:
    normalized = str(raw_category or "").strip().lower()
    if normalized == "power_banks":
        return "Power banks / portable chargers"
    return str(raw_category or "Unknown category")


def _why_copy_for_slot(slot_label: str) -> str:
    normalized = str(slot_label or "").strip().lower()
    reasons = {
        "everyday portable": (
            "Balanced everyday charging option for users who want a compact backup charger."
        ),
        "compact carry": "Smaller capacity option for light carry and quick phone top-ups.",
        "20000mah capacity": (
            "Higher-capacity option for longer days, travel, or multiple phone charges."
        ),
        "high capacity": (
            "Large-capacity option for users who prioritize maximum backup power."
        ),
    }
    return reasons.get(normalized, "General-purpose charging option for practical everyday use.")


def _render_safe_powerbank_visual(slot_label: str) -> str:
    visual_variant = (
        str(slot_label or "").strip().lower().replace(" ", "-").replace("/", "-")
    ) or "generic"
    return (
        '<div class="pw-safe-product-visual pw-powerbank-visual" '
        f'data-visual-slot="{escape(visual_variant, quote=True)}" '
        'aria-label="Generic power bank illustration" role="img">'
        '<svg viewBox="0 0 180 100" class="pw-safe-visual-svg" aria-hidden="true" focusable="false">'
        '<defs>'
        '<linearGradient id="pwCardBg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#edf4ff"/>'
        '<stop offset="100%" stop-color="#dfeaff"/>'
        "</linearGradient>"
        '<linearGradient id="pwBodyTone" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#4a82df"/>'
        '<stop offset="100%" stop-color="#2a5fbf"/>'
        "</linearGradient>"
        "</defs>"
        '<rect x="0" y="0" width="180" height="100" rx="14" fill="url(#pwCardBg)"/>'
        '<rect x="28" y="26" width="124" height="48" rx="10" fill="url(#pwBodyTone)"/>'
        '<rect x="36" y="36" width="42" height="8" rx="4" fill="#ffffff" fill-opacity="0.66"/>'
        '<rect x="36" y="50" width="58" height="8" rx="4" fill="#ffffff" fill-opacity="0.45"/>'
        '<circle cx="136" cy="50" r="10" fill="#10366f" fill-opacity="0.22"/>'
        '<circle cx="136" cy="50" r="4" fill="#ffffff" fill-opacity="0.72"/>'
        "</svg>"
        '<span class="pw-safe-visual-label">Generic placeholder visual</span>'
        "</div>"
    )


def _render_search_shell(query: str) -> str:
    escaped_query_attr = escape(query, quote=True)
    escaped_query_text = escape(query)
    return (
        '<header class="pw-search-shell-header">'
        '<div class="pw-search-shell-top">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">PicWise</a>'
        '<a class="pw-back-home" href="/">Back to home</a>'
        "</div>"
        '<form class="pw-search-form" action="/search" method="get" aria-label="Search products">'
        '<label for="pw-search-query" style="position:absolute;left:-9999px;">Search query</label>'
        f'<input id="pw-search-query" type="search" name="q" value="{escaped_query_attr}" '
        'placeholder="Search for a product, e.g. power bank" autocomplete="off">'
        '<button type="submit">Search</button>'
        "</form>"
        f'<p class="pw-current-query">Current query: <strong>{escaped_query_text}</strong></p>'
        "</header>"
    )


def _base_styles() -> str:
    return (
        "*{box-sizing:border-box;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
        ".pw-wrap{max-width:1120px;margin:0 auto;padding:24px 20px 20px;}"
        ".pw-search-shell-header{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:16px 16px 14px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
        ".pw-search-shell-top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;}"
        ".pw-brand{font-size:26px;font-weight:800;letter-spacing:-.03em;color:#1a4fb7;text-decoration:none;}"
        ".pw-back-home{display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border:1px solid #b9d1ff;border-radius:999px;background:#fff;color:#1f6dff;text-decoration:none;font-size:14px;font-weight:700;}"
        ".pw-search-form{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px;}"
        ".pw-search-form input{flex:1 1 320px;min-width:220px;height:42px;padding:0 14px;border:1px solid #cddffc;border-radius:999px;background:#fff;color:#102744;font-size:14px;}"
        ".pw-search-form input:focus{outline:none;border-color:#1f6dff;box-shadow:0 0 0 3px rgba(31,109,255,.15);}"
        ".pw-search-form button{height:42px;padding:0 16px;border-radius:999px;background:#1f6dff;color:#fff;border:1px solid #1f6dff;font-size:14px;font-weight:700;cursor:pointer;}"
        ".pw-current-query{margin:10px 0 0;font-size:14px;line-height:1.5;color:#355174;}"
        ".pw-card{margin-top:14px;background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
        ".pw-line{margin:12px 0 0;line-height:1.6;color:#355174;}"
        ".pw-tag{display:inline-flex;align-items:center;justify-content:center;padding:5px 10px;border-radius:999px;background:#eaf2ff;color:#2a6deb;font-size:12px;font-weight:700;margin-top:10px;}"
        ".pw-search-results-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px auto 0;max-width:1040px;}"
        ".pw-option{border:1px solid #dbe8fb;border-radius:12px;padding:12px;background:#f9fbff;display:flex;flex-direction:column;min-height:100%;}"
        ".pw-title{font-weight:700;color:#163a66;}"
        ".pw-safe-product-visual{border:1px solid #d4e4fb;border-radius:10px;background:#f2f7ff;padding:8px 8px 6px;display:flex;flex-direction:column;align-items:center;gap:6px;}"
        ".pw-safe-visual-svg{width:100%;height:auto;display:block;max-width:180px;}"
        ".pw-safe-visual-label{font-size:11px;color:#4a688f;}"
        ".pw-btn{display:inline-flex;align-items:center;justify-content:center;height:42px;padding:0 18px;border-radius:999px;background:#1f6dff;border:1px solid #1f6dff;color:#fff;font-size:14px;font-weight:700;text-decoration:none;margin-top:16px;}"
        ".pw-disclosure{margin-top:16px;padding:11px 12px;border:1px solid #dbe8fb;border-radius:12px;background:#f7fbff;color:#24456f;font-size:14px;line-height:1.55;}"
        ".pw-safe-note{margin-top:10px;font-size:14px;line-height:1.6;color:#355174;}"
        ".pw-footer{margin-top:18px;padding-top:14px;border-top:1px solid #dbe8fb;}"
        ".pw-footer-links{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}"
        ".pw-footer-link{display:inline-flex;align-items:center;justify-content:center;padding:6px 10px;"
        "border:1px solid #d8e6fb;border-radius:999px;background:#f7faff;font-size:13px;"
        "line-height:1.2;color:#335983;text-decoration:none;white-space:nowrap;}"
        ".pw-footer-link:hover{background:#eef5ff;border-color:#cddffc;color:#24496f;}"
        ".pw-footer-disclosure{margin:10px 0 0;font-size:12px;line-height:1.5;color:#5f7ea6;max-width:760px;}"
        ".pw-footer-meta{margin:6px 0 0;font-size:12px;color:#6b86ac;}"
        "@media (max-width:1040px){.pw-search-results-grid{grid-template-columns:repeat(2,minmax(0,1fr));max-width:740px;}}"
        "@media (max-width:640px){.pw-wrap{padding:18px 14px 14px;}.pw-brand{font-size:24px;}.pw-search-results-grid{grid-template-columns:1fr;max-width:420px;}.pw-card{padding:16px;}}"
    )


def render_controlled_search_results_page(query: str, *, source_page: str = "search") -> str:
    displayed_query = _normalize_query_for_display(query)
    match_result = match_manual_amazon_affiliates(displayed_query)
    escaped_query = escape(displayed_query)
    page_shell = _render_search_shell(displayed_query)
    page_footer = render_public_footer()
    normalized_source_page = source_page if source_page in {"search", "results"} else "search"
    if match_result.match_status == AmazonManualMatchStatus.ELIGIBLE and match_result.results:
        normalized_query_param = quote(displayed_query, safe="")
        results_html = "".join(
            (
                '<article class="pw-option">'
                f"{_render_safe_powerbank_visual(safe_result.slot_label)}"
                f'<p class="pw-line pw-title">{escape(safe_result.title)}</p>'
                f'<p class="pw-line"><strong>Slot:</strong> {escape(safe_result.slot_label)}</p>'
                f'<p class="pw-line"><strong>Category:</strong> {escape(_customer_friendly_category(safe_result.category))}</p>'
                f'<p class="pw-line">ASIN: {escape(safe_result.asin)}</p>'
                f'<p class="pw-line"><strong>Why this option:</strong> {escape(_why_copy_for_slot(safe_result.slot_label))}</p>'
                f'<a class="pw-btn" href="/out/amazon?asin={escape(safe_result.asin, quote=True)}&q={normalized_query_param}&src={escape(normalized_source_page, quote=True)}" rel="nofollow sponsored noopener">View on Amazon</a>'
                "</article>"
            )
            for safe_result in match_result.results
        )
        first_result = match_result.results[0]
        return (
            "<!doctype html>"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>PicWise Search Results</title>"
            '<meta name="robots" content="noindex, nofollow">'
            f"<style>{_base_styles()}</style></head><body>"
            '<main class="pw-wrap">'
            f"{page_shell}"
            '<section class="pw-card">'
            f'<h1 class="pw-line">Search results for: {escaped_query}</h1>'
            '<span class="pw-tag">Approved Amazon options</span>'
            f'<p class="pw-line">Matched query: {escaped_query}</p>'
            '<p class="pw-line">Approved manual Amazon affiliate options</p>'
            '<p class="pw-line">Only manually reviewed active options are shown.</p>'
            f'<section class="pw-search-results-grid">{results_html}</section>'
            f'<p class="pw-disclosure">{escape(first_result.disclosure)}</p>'
            f'<p class="pw-safe-note">{escape(first_result.safe_note)}</p>'
            "</section>"
            f"{page_footer}"
            "</main></body></html>"
        )

    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PicWise Search Results</title>"
        '<meta name="robots" content="noindex, nofollow">'
        f"<style>{_base_styles()}</style></head><body>"
        '<main class="pw-wrap">'
        f"{page_shell}"
        '<section class="pw-card">'
        f'<h1 class="pw-line">Search results for: {escaped_query}</h1>'
        '<p class="pw-line">No approved Amazon options are available for this query yet.</p>'
        '<p class="pw-line">PicWise only shows approved manual affiliate results at this stage.</p>'
        '<p class="pw-line">No fake product data is shown.</p>'
        "</section>"
        f"{page_footer}"
        "</main></body></html>"
    )
