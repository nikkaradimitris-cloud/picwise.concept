from __future__ import annotations

from html import escape

from picwise_offers import AmazonManualMatchStatus, match_manual_amazon_affiliates


def _normalize_query_for_display(query: str) -> str:
    collapsed = " ".join(str(query or "").strip().split())
    return collapsed or "(empty query)"


def render_controlled_search_results_page(query: str) -> str:
    displayed_query = _normalize_query_for_display(query)
    match_result = match_manual_amazon_affiliates(displayed_query)
    escaped_query = escape(displayed_query)
    if match_result.match_status == AmazonManualMatchStatus.ELIGIBLE and match_result.results:
        results_html = "".join(
            (
                '<article class="pw-option">'
                f'<p class="pw-line pw-title">{escape(safe_result.title)}</p>'
                f'<p class="pw-line">Slot: {escape(safe_result.slot_label)}</p>'
                f'<p class="pw-line">Category: {escape(safe_result.category)}</p>'
                f'<p class="pw-line">ASIN: {escape(safe_result.asin)}</p>'
                f'<a class="pw-btn" href="{escape(safe_result.affiliate_url, quote=True)}" target="_blank" rel="nofollow sponsored noopener">View on Amazon</a>'
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
            "<style>"
            "*{box-sizing:border-box;}"
            "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
            ".pw-wrap{max-width:860px;margin:0 auto;padding:32px 20px;}"
            ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
            ".pw-line{margin:12px 0 0;line-height:1.6;color:#355174;}"
            ".pw-tag{display:inline-flex;align-items:center;justify-content:center;padding:5px 10px;border-radius:999px;background:#eaf2ff;color:#2a6deb;font-size:12px;font-weight:700;margin-top:10px;}"
            ".pw-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-top:14px;}"
            ".pw-option{border:1px solid #dbe8fb;border-radius:12px;padding:12px;background:#f9fbff;}"
            ".pw-title{font-weight:700;color:#163a66;}"
            ".pw-btn{display:inline-flex;align-items:center;justify-content:center;height:42px;padding:0 18px;border-radius:999px;background:#1f6dff;border:1px solid #1f6dff;color:#fff;font-size:14px;font-weight:700;text-decoration:none;margin-top:16px;}"
            ".pw-disclosure{margin-top:16px;padding:11px 12px;border:1px solid #dbe8fb;border-radius:12px;background:#f7fbff;color:#24456f;font-size:14px;line-height:1.55;}"
            ".pw-safe-note{margin-top:10px;font-size:14px;line-height:1.6;color:#355174;}"
            "</style></head><body>"
            '<main class="pw-wrap"><section class="pw-card">'
            f'<h1 class="pw-line">Search results for: {escaped_query}</h1>'
            '<span class="pw-tag">Approved Amazon options</span>'
            f'<p class="pw-line">Matched query: {escaped_query}</p>'
            '<p class="pw-line">Manual affiliate results only</p>'
            f'<section class="pw-grid">{results_html}</section>'
            f'<p class="pw-disclosure">{escape(first_result.disclosure)}</p>'
            f'<p class="pw-safe-note">{escape(first_result.safe_note)}</p>'
            "</section></main></body></html>"
        )

    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PicWise Search Results</title>"
        '<meta name="robots" content="noindex, nofollow">'
        "<style>"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
        ".pw-wrap{max-width:860px;margin:0 auto;padding:32px 20px;}"
        ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
        ".pw-line{margin:12px 0 0;line-height:1.6;color:#355174;}"
        "</style></head><body>"
        '<main class="pw-wrap"><section class="pw-card">'
        f'<h1 class="pw-line">Search results for: {escaped_query}</h1>'
        '<p class="pw-line">No approved Amazon options are available for this query yet.</p>'
        '<p class="pw-line">PicWise only shows approved manual affiliate results at this stage.</p>'
        '<p class="pw-line">No fake product data is shown.</p>'
        "</section></main></body></html>"
    )
