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
        f"<title>{escape(decision_output.page_title)}</title>"
        "</head><body>"
        '<main class="picwise-landing">'
        f"<h1>{escape(decision_output.page_title)}</h1>"
        f'<p class="query-confirmation">Showing 4 decision-ready options for: '
        f"{escape(decision_output.query)}</p>"
        '<section class="primary-choices" data-card-count="4">'
        f"{''.join(cards_html)}"
        "</section>"
        f"{more_section}"
        "</main>"
        "</body></html>"
    )
