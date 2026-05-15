from __future__ import annotations

from html import escape

from picwise_offers import AmazonManualMatchStatus, match_manual_amazon_affiliate


def render_amazon_affiliate_proof_page() -> str:
    """Render a controlled public proof for one approved manual Amazon result."""
    matched_query = "power bank"
    match_result = match_manual_amazon_affiliate(matched_query)
    if match_result.match_status != AmazonManualMatchStatus.ELIGIBLE or match_result.result is None:
        return (
            "<!doctype html>"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>PicWise — Amazon affiliate proof</title>"
            "<style>"
            "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
            ".pw-wrap{max-width:820px;margin:0 auto;padding:32px 20px;}"
            ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:18px 20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
            ".pw-note{margin:10px 0 0;line-height:1.6;color:#355174;}"
            "</style></head><body><main class=\"pw-wrap\"><section class=\"pw-card\">"
            "<h1>Manual Amazon affiliate proof</h1>"
            "<p class=\"pw-note\">Matched query: power bank</p>"
            "<p class=\"pw-note\">Approved result is temporarily unavailable for public proof.</p>"
            "</section></main></body></html>"
        )

    safe_result = match_result.result
    affiliate_url = escape(safe_result.affiliate_url, quote=True)
    title = escape(safe_result.title)
    asin = escape(safe_result.asin)
    disclosure = escape(safe_result.disclosure)
    safe_note = escape(safe_result.safe_note)

    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PicWise — Amazon affiliate proof</title>"
        "<style>"
        "*{box-sizing:border-box;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#102744;background:linear-gradient(180deg,#f8fbff 0%,#f3f8ff 100%);}"
        ".pw-wrap{max-width:860px;margin:0 auto;padding:34px 20px 28px;}"
        ".pw-card{background:#fff;border:1px solid #d9e7fb;border-radius:16px;padding:24px;box-shadow:0 12px 28px rgba(20,56,112,.08);}"
        ".pw-title{margin:0;font-size:32px;line-height:1.2;letter-spacing:-.02em;color:#0f2442;}"
        ".pw-line{margin:12px 0 0;font-size:16px;line-height:1.65;color:#355174;}"
        ".pw-tag{display:inline-flex;align-items:center;justify-content:center;padding:5px 10px;border-radius:999px;background:#eaf2ff;color:#2a6deb;font-size:12px;font-weight:700;margin-top:10px;}"
        ".pw-btn{display:inline-flex;align-items:center;justify-content:center;height:42px;padding:0 18px;border-radius:999px;background:#1f6dff;border:1px solid #1f6dff;color:#fff;font-size:14px;font-weight:700;text-decoration:none;margin-top:16px;}"
        ".pw-disclosure{margin-top:16px;padding:11px 12px;border:1px solid #dbe8fb;border-radius:12px;background:#f7fbff;color:#24456f;font-size:14px;line-height:1.55;}"
        ".pw-safe-note{margin-top:10px;font-size:14px;line-height:1.6;color:#355174;}"
        "@media (max-width:760px){.pw-title{font-size:28px;}}"
        "</style></head><body>"
        '<main class="pw-wrap"><section class="pw-card">'
        '<h1 class="pw-title">Manual Amazon affiliate proof</h1>'
        '<p class="pw-line">Matched query: power bank</p>'
        '<span class="pw-tag">Approved Amazon result</span>'
        f'<p class="pw-line">{title}</p>'
        '<p class="pw-line">Power bank / portable charger category</p>'
        f'<p class="pw-line">ASIN: {asin}</p>'
        f'<a class="pw-btn" href="{affiliate_url}" target="_blank" rel="nofollow sponsored noopener">View on Amazon</a>'
        f'<p class="pw-disclosure">{disclosure}</p>'
        f'<p class="pw-safe-note">{safe_note}</p>'
        "</section></main></body></html>"
    )
