from __future__ import annotations

from html import escape

from picwise_mvp.private_beta import PickWiseMVPSearchFlow


def _render_slot_cards(flow: PickWiseMVPSearchFlow) -> str:
    cards: list[str] = []
    wise_id = flow.recommendation_set.wise_recommended_product.candidate_id if flow.recommendation_set.wise_recommended_product else None
    for slot in flow.recommendation_set.display_slots:
        recommended = slot.candidate_id == wise_id
        badge = '<p class="pw-badge">Wise Recommended</p>' if recommended else ""
        reasons = ", ".join(reason.value for reason in slot.reason_codes) if slot.reason_codes else "not_available"
        price = f"{slot.currency} {slot.price:.2f}" if slot.price is not None and slot.currency else "price_not_connected"
        cta = ""
        if slot.outbound_url:
            cta = (
                f'<a class="pw-cta" href="{escape(slot.outbound_url)}" '
                'rel="nofollow noopener" target="_blank">View offer</a>'
            )
        cards.append(
            "".join(
                (
                    f'<article class="pw-card{" pw-card-recommended" if recommended else ""}">',
                    badge,
                    f"<h2>{escape(slot.title)}</h2>",
                    f"<p><strong>Seller:</strong> {escape(slot.seller_name or 'not_connected')}</p>",
                    f"<p><strong>Price:</strong> {escape(price)}</p>",
                    f"<p><strong>Availability:</strong> {escape(slot.availability_status or 'not_available')}</p>",
                    f"<p><strong>Reason:</strong> {escape(reasons)}</p>",
                    cta,
                    "</article>",
                )
            )
        )
    return "".join(cards)


def render_mvp_search_results_surface(flow: PickWiseMVPSearchFlow) -> str:
    cards_html = _render_slot_cards(flow)
    intent_category = str(flow.local_nlu_intent.get("category") or "unknown")
    safe_recommended = flow.recommendation_set.wise_recommended_product
    recommended_html = ""
    if safe_recommended is not None:
        recommended_html = (
            '<section class="pw-highlight">'
            "<h2>Wise Recommended Product</h2>"
            f"<p><strong>{escape(safe_recommended.title)}</strong></p>"
            f"<p>{escape(safe_recommended.explanation)}</p>"
            "</section>"
        )
    no_result_html = ""
    if not flow.recommendation_set.display_slots:
        no_result_html = (
            '<section class="pw-empty">'
            f"<p>No result state: <strong>{escape(flow.state)}</strong></p>"
            "<p>PickWise could not produce safe display candidates yet. Source may be not_connected or needs_data.</p>"
            "</section>"
        )
    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PickWise Search Results</title>"
        '<meta name="robots" content="noindex, nofollow">'
        "<style>"
        "body{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;background:#f6f8fc;color:#132849;}"
        ".pw-shell{max-width:1100px;margin:0 auto;padding:24px 16px;}"
        ".pw-state{background:#fff;border:1px solid #d9e3f2;border-radius:12px;padding:14px;margin-bottom:12px;}"
        ".pw-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}"
        ".pw-card{background:#fff;border:1px solid #d9e3f2;border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:8px;}"
        ".pw-card-recommended{border-color:#1f6dff;}"
        ".pw-badge{display:inline-block;background:#1f6dff;color:#fff;border-radius:999px;padding:4px 8px;font-size:12px;margin:0;}"
        ".pw-cta{margin-top:auto;text-decoration:none;border:1px solid #1f6dff;border-radius:8px;padding:8px 10px;color:#1f6dff;font-weight:700;display:inline-block;}"
        ".pw-highlight,.pw-empty{background:#fff;border:1px solid #d9e3f2;border-radius:12px;padding:12px;margin-bottom:12px;}"
        "@media(max-width:760px){.pw-grid{grid-template-columns:1fr;}}"
        "</style></head><body>"
        '<main class="pw-shell">'
        '<section class="pw-state">'
        f"<h1>PickWise MVP Search</h1>"
        f"<p><strong>Query:</strong> {escape(flow.query)}</p>"
        f"<p><strong>Detected intent/category:</strong> {escape(intent_category)}</p>"
        f"<p><strong>Search route:</strong> {escape(flow.search_decision.route_type)}</p>"
        f"<p><strong>Expected vertical:</strong> {escape(flow.expected_vertical)}</p>"
        f"<p><strong>Flow state:</strong> {escape(flow.state)}</p>"
        "</section>"
        f"{recommended_html}"
        f"{no_result_html}"
        '<section class="pw-grid">'
        f"{cards_html}"
        "</section>"
        '<section class="pw-state">'
        f"<p><strong>Recommendation status:</strong> {escape(flow.recommendation_set.status.value)}</p>"
        f"<p><strong>Explanation:</strong> {escape(flow.recommendation_set.recommendation_explanation)}</p>"
        f"<p><strong>Tradeoff summary:</strong> {escape(flow.recommendation_set.tradeoff_summary)}</p>"
        f"<p><strong>Outbound contract:</strong> {escape(flow.outbound_link_contract.status)}</p>"
        "</section>"
        "</main></body></html>"
    )
