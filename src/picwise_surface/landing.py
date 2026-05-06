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
        recommended_badge = (
            '<p class="recommended-badge">Recommended by Picwise</p>'
            if choice.is_recommended
            else ""
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
                f"{recommended_badge}"
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
        "body{margin:0;font-family:Arial,sans-serif;background:#f5f8fc;color:#132238;line-height:1.45;}"
        ".picwise-landing{max-width:1100px;margin:0 auto;padding:28px 18px 36px;}"
        ".page-header{margin-bottom:18px;}"
        "h1{margin:0 0 8px;font-size:1.7rem;}"
        ".query-confirmation{margin:0;color:#2a4668;}"
        ".primary-choices{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;}"
        ".choice-card{background:#fff;border:1px solid #d5e1f0;border-radius:12px;padding:14px;"
        "box-shadow:0 3px 8px rgba(10,34,64,.06);display:flex;flex-direction:column;gap:9px;}"
        ".choice-card.recommended{border:2px solid #1667d9;box-shadow:0 8px 18px rgba(22,103,217,.18);"
        "background:linear-gradient(180deg,#f8fbff,#ffffff);}"
        ".recommended-badge{display:inline-block;margin:0;background:#1667d9;color:#fff;border-radius:999px;"
        "padding:4px 10px;font-size:.78rem;font-weight:700;}"
        ".role-badge{margin:0;font-size:.79rem;font-weight:700;letter-spacing:.02em;color:#1f4f8a;"
        "text-transform:uppercase;}"
        "h2{margin:0;font-size:1.04rem;}"
        ".decision-label{margin:0;font-weight:700;color:#0f3a6f;}"
        ".subtitle{margin:0;color:#304a66;font-size:.92rem;}"
        ".key-reasons{margin:0;padding-left:18px;color:#21354d;}"
        ".risks,.recommendation-reason{margin:0;font-size:.9rem;color:#37516d;}"
        ".cta{display:inline-block;margin-top:auto;padding:9px 12px;border-radius:8px;text-decoration:none;"
        "font-weight:700;background:#163f72;color:#fff;text-align:center;}"
        ".choice-card.recommended .cta{background:#1667d9;}"
        ".more-section{margin-top:18px;background:#fff;border:1px dashed #b8cae0;border-radius:12px;padding:12px 14px;}"
        ".more-section h3{margin:0 0 8px;font-size:1rem;color:#1f3f66;}"
        ".more-section ul{margin:0;padding-left:18px;color:#2a4563;}"
        "</style>"
        "</head><body>"
        '<main class="picwise-landing">'
        '<header class="page-header">'
        f"<h1>{escape(decision_output.page_title)}</h1>"
        f'<p class="query-confirmation">Showing 4 decision-ready options for: '
        f"{escape(decision_output.query)}</p>"
        "</header>"
        '<section class="primary-choices" data-card-count="4">'
        f"{''.join(cards_html)}"
        "</section>"
        f"{more_section}"
        "</main>"
        "</body></html>"
    )
