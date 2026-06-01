from __future__ import annotations

from html import escape
from urllib.parse import quote

from picwise_offers import AmazonManualMatchStatus, match_manual_amazon_affiliates
from picwise_search import LiveSearchResolution
from .legal import render_public_footer


_SAFE_DISCLAIMER_BY_STATE = {
    "understood_provider_not_connected": "PicWise understood this search, but no safe provider is connected yet.",
    "not_understood": "PicWise could not understand this search safely.",
    "low_confidence_manual_review": "PicWise found weak product signals, but confidence is too low.",
    "blocked_or_unsafe": "PicWise cannot safely process this search.",
}

_REAL_FEED_PROVIDER_KEYS = frozenset({"awin"})
_FAKE_FEED_PROVIDER_KEYS = frozenset({"demo", "fake", "sample", "test"})
_REQUIRED_FEED_PRODUCT_FIELDS = (
    "title",
    "price_text",
    "availability_text",
    "image_url",
    "product_url",
    "provider_product_id",
)
_FEED_RECOMMENDATION_REASON_LABELS = {
    "strong_query_title_fit": "Strong match to your search",
    "all_query_tokens_in_title": "Contains the key search terms",
    "query_phrase_in_title": "Search phrase appears in the product title",
    "product_type_phrase_in_title": "Matches the product type",
    "category_alignment": "Fits the product category",
    "main_product_not_accessory": "Main product, not an accessory",
    "complete_product_fields": "Has price, image and required feed fields",
}
_UI_BLOCKING_PURCHASABILITY_STATES = frozenset(
    {
        "out_of_stock",
        "discontinued",
        "missing_buy_button",
        "invalid_page",
        "redirect_suspect",
    }
)
_UI_BLOCKING_AVAILABILITY_STATES = frozenset({"out_of_stock", "discontinued"})
_RECOMMENDATION_CONFIDENCE_REC_NOTE = {
    "strong": "Recommended from these 4.",
    "limited": "Suggested pick from these 4 (limited confidence).",
    "weak": "Suggested from these 4 (low confidence).",
    "unknown": "Suggested from these 4 (purchase availability not verified).",
}
_RECOMMENDATION_CONFIDENCE_BADGE = {
    "strong": "&#9733; Recommended by PicWise",
    "limited": "Suggested by PicWise",
    "weak": "Suggested by PicWise",
    "unknown": "Suggested by PicWise",
}
_PROVIDER_STORE_LABELS = {
    "awin": "Geekbuying via Awin",
}
_FEED_DISCLOSURE = (
    "Selected real products from a connected provider feed. "
    "PicWise recommends one option from these four based on search fit — "
    "not independent review or market-wide ranking."
)
_FEED_SAFE_NOTE = "Recommended from these 4. Prices and availability come directly from the feed."


def _is_http_url(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _feed_product_dict_complete(product: dict[str, object]) -> bool:
    for field_name in _REQUIRED_FEED_PRODUCT_FIELDS:
        if not str(product.get(field_name) or "").strip():
            return False
    if not _is_http_url(str(product.get("product_url") or "")):
        return False
    if not _is_http_url(str(product.get("image_url") or "")):
        return False
    provider_key = str(product.get("provider_key") or "").strip().lower()
    if not provider_key or provider_key in _FAKE_FEED_PROVIDER_KEYS:
        return False
    if provider_key not in _REAL_FEED_PROVIDER_KEYS:
        return False
    return True


def _provider_feed_product_blocks_ui(product: dict[str, object]) -> bool:
    purch_state = str(product.get("purchasability_state") or "").strip().lower()
    if purch_state in _UI_BLOCKING_PURCHASABILITY_STATES:
        return True
    availability_state = str(product.get("availability_state") or "").strip().lower()
    if availability_state in _UI_BLOCKING_AVAILABILITY_STATES:
        return True
    if product.get("card_eligible") is False:
        return True
    return False


def _provider_feed_card_meta(product: dict[str, object], *, store_label: str) -> str:
    meta_parts: list[str] = []
    availability_state = str(product.get("availability_state") or "").strip().lower()
    purch_state = str(product.get("purchasability_state") or "").strip().lower()
    if availability_state not in _UI_BLOCKING_AVAILABILITY_STATES:
        meta_parts.append("Availability not verified")
    if purch_state == "purchasability_unknown":
        meta_parts.append("Purchase availability not verified")
    elif purch_state == "purchasable" and not product.get("verified_purchasable"):
        meta_parts.append("Purchase availability not verified")
    meta_parts.append(f"Provider: {store_label}")
    return "  ·  ".join(meta_parts)


def _provider_feed_ui_display_allowed(resolution: LiveSearchResolution) -> bool:
    if resolution.provider_feed_selection_status != "selected":
        return False
    if resolution.provider_feed_decision_status != "recommended":
        return False
    if not resolution.provider_feed_recommended_product_id:
        return False
    if not resolution.provider_feed_recommendation_reason_codes:
        return False
    products = resolution.provider_feed_selected_products
    if len(products) != 4:
        return False
    selected_ids = {
        str(product.get("provider_product_id") or "").strip() for product in products
    }
    if resolution.provider_feed_recommended_product_id not in selected_ids:
        return False
    if not all(_feed_product_dict_complete(product) for product in products):
        return False
    if any(_provider_feed_product_blocks_ui(product) for product in products):
        return False
    recommended = next(
        (
            product
            for product in products
            if str(product.get("provider_product_id") or "").strip()
            == str(resolution.provider_feed_recommended_product_id or "").strip()
        ),
        None,
    )
    if recommended is None or _provider_feed_product_blocks_ui(recommended):
        return False
    return True


def _feed_recommendation_reason_bullets(reason_codes: tuple[str, ...]) -> list[str]:
    bullets: list[str] = []
    for code in reason_codes:
        label = _FEED_RECOMMENDATION_REASON_LABELS.get(str(code).strip())
        if label:
            bullets.append(label)
    return bullets


def _provider_store_label(provider_key: str) -> str:
    normalized = str(provider_key or "").strip().lower()
    return _PROVIDER_STORE_LABELS.get(normalized, normalized.replace("_", " ").title() or "Provider feed")


def _build_provider_feed_result_cards(
    *,
    resolution: LiveSearchResolution,
) -> tuple[list[dict[str, object]], bool, str, str]:
    if not _provider_feed_ui_display_allowed(resolution):
        return ([], False, "", "")

    recommended_id = str(resolution.provider_feed_recommended_product_id or "").strip()
    recommendation_confidence = str(
        getattr(resolution, "provider_feed_recommendation_confidence", None) or "limited"
    ).strip().lower()
    if recommendation_confidence not in _RECOMMENDATION_CONFIDENCE_REC_NOTE:
        recommendation_confidence = "limited"
    reason_bullets = _feed_recommendation_reason_bullets(
        resolution.provider_feed_recommendation_reason_codes
    )
    cards: list[dict[str, object]] = []
    for product in resolution.provider_feed_selected_products:
        if _provider_feed_product_blocks_ui(product):
            return ([], False, "", "")
        product_id = str(product.get("provider_product_id") or "").strip()
        provider_key = str(product.get("provider_key") or "").strip()
        is_recommended = product_id == recommended_id
        store_label = _provider_store_label(provider_key)
        cards.append(
            {
                "badge": "REAL FEED",
                "badge_class": "pw-badge-value",
                "name": str(product.get("title") or "").strip(),
                "description": "Selected real product (purchase not verified)",
                "rating": "",
                "reviews": "",
                "price": str(product.get("price_text") or "").strip(),
                "meta": _provider_feed_card_meta(product, store_label=store_label),
                "bullets": reason_bullets if is_recommended else [],
                "warning": "",
                "cta": "View product",
                "image": str(product.get("image_url") or "").strip(),
                "recommended": is_recommended,
                "rec_note": (
                    _RECOMMENDATION_CONFIDENCE_REC_NOTE[recommendation_confidence]
                    if is_recommended
                    else ""
                ),
                "rec_badge_html": (
                    _RECOMMENDATION_CONFIDENCE_BADGE[recommendation_confidence]
                    if is_recommended
                    else ""
                ),
                "href": str(product.get("product_url") or "").strip(),
            }
        )

    if len(cards) != 4:
        return ([], False, "", "")
    if sum(1 for card in cards if bool(card["recommended"])) != 1:
        return ([], False, "", "")

    safe_note = _RECOMMENDATION_CONFIDENCE_REC_NOTE.get(
        recommendation_confidence,
        _FEED_SAFE_NOTE,
    )
    return cards, True, _FEED_DISCLOSURE, safe_note


def _build_result_cards(
    *,
    resolution: LiveSearchResolution,
    source_page: str,
) -> tuple[list[dict[str, object]], bool, str, str]:
    if not resolution.result_allowed:
        return ([], False, "", "")
    if resolution.provider_key != "manual_amazon_affiliate":
        return ([], False, "", "")

    match_result = match_manual_amazon_affiliates(resolution.canonical_query)
    if match_result.match_status != AmazonManualMatchStatus.ELIGIBLE:
        return ([], False, "", "")
    if not match_result.results:
        return ([], False, "", "")

    cards: list[dict[str, object]] = []
    for result in match_result.results:
        cards.append(
            {
                "badge": "LIVE OPTION",
                "badge_class": "pw-badge-value",
                "name": result.title,
                "description": f"Manual reviewed match for {result.category.replace('_', ' ')}",
                "rating": "",
                "reviews": "",
                "price": "See Amazon details",
                "meta": f"ASIN: {result.asin}  ·  Provider: {resolution.provider_key}",
                "bullets": [
                    "Approved manual affiliate option",
                    "No fake commerce metrics shown",
                    "Redirect validated through /out/amazon",
                ],
                "warning": "",
                "cta": "View on Amazon",
                "image": "/assets/picwise/product-3.svg",
                "recommended": False,
                "rec_note": "",
                "href": (
                    f"/out/amazon?asin={escape(result.asin, quote=True)}"
                    f"&q={quote(resolution.display_query, safe='')}"
                    f"&src={escape(source_page, quote=True)}"
                ),
            }
        )
    return cards, True, match_result.results[0].disclosure, match_result.results[0].safe_note


def render_picwise_reference_surface(
    query: str = "",
    *,
    resolution: LiveSearchResolution | None = None,
    source_page: str = "search",
) -> str:
    display_query = str(query or "")
    query_line = ""
    disclaimer_line = (
        "Live safe mode — no Amazon API, no scraping, and no fake live commerce claims."
    )
    safe_note_line = ""
    show_demo_note = False

    feed_results = False
    if resolution is None:
        card_specs: list[dict[str, object]] = []
    else:
        card_specs, has_live_results, disclosure, safe_note = _build_result_cards(
            resolution=resolution,
            source_page=source_page,
        )
        if not has_live_results:
            feed_cards, feed_live, feed_disclosure, feed_safe_note = _build_provider_feed_result_cards(
                resolution=resolution,
            )
            if feed_live:
                card_specs = feed_cards
                has_live_results = True
                feed_results = True
                disclosure = feed_disclosure
                safe_note = feed_safe_note
        if display_query.strip():
            if has_live_results and feed_results:
                query_line = f"Showing 4 selected real products for: {display_query}"
            elif has_live_results:
                query_line = f"Showing {len(card_specs)} options for: {display_query}"
            else:
                query_line = ""
        if has_live_results and disclosure:
            disclaimer_line = disclosure
            safe_note_line = safe_note
        elif display_query.strip():
            base_message = _SAFE_DISCLAIMER_BY_STATE.get(
                resolution.resolver_state,
                "PicWise could not understand this search safely.",
            )
            detected_category = resolution.display_name or resolution.mega_category_id or resolution.canonical_category
            if resolution.resolver_state == "understood_provider_not_connected" and detected_category:
                human_category = str(detected_category).replace("_", " ")
                disclaimer_line = f"{base_message} Detected category: {human_category}"
            else:
                disclaimer_line = base_message
        show_demo_note = has_live_results
        if has_live_results and not feed_results:
            query_line = f"Showing {len(card_specs)} options for: {display_query}"

    if resolution is None:
        query_line = ""
        disclaimer_line = (
            "Search to see provider-safe results. PicWise shows no fallback products when confidence or provider availability is not sufficient."
        )
        card_specs = []

    if not card_specs:
        card_specs = []

    card_html = []
    for idx, card in enumerate(card_specs, start=1):
        rec_class = " pw-card-recommended" if bool(card["recommended"]) else ""
        rec_header = (
            f'<div class="pw-rec-badge">{card.get("rec_badge_html") or "Suggested by PicWise"}</div>'
            if bool(card["recommended"])
            else ""
        )
        reasons = "".join(
            f'<li class="pw-feature-item"><span class="pw-feature-dot" aria-hidden="true"></span><span>{escape(str(reason))}</span></li>'
            for reason in list(card["bullets"])
        )
        warning_html = (
            f'<p class="pw-warning"><span class="pw-warning-icon" aria-hidden="true">&#9651;</span>{escape(str(card["warning"]))}</p>'
            if str(card["warning"])
            else ""
        )
        rec_note = (
            f'<p class="pw-rec-note">{escape(str(card["rec_note"]))}</p>' if str(card["rec_note"]) else ""
        )
        cta = (
            f'<a class="pw-card-cta pw-card-cta-link" href="{escape(str(card["href"]), quote=True)}" rel="nofollow sponsored noopener">{escape(str(card["cta"]))}</a>'
            if card.get("href")
            else f'<button class="pw-card-cta" type="submit">{escape(str(card["cta"]))}</button>'
        )
        card_html.append(
            (
                f'<article class="pw-card{rec_class}" data-choice-id="fixed-{idx}">'
                f"{rec_header}"
                f'<span class="pw-badge {escape(str(card["badge_class"]), quote=True)}">{escape(str(card["badge"]))}</span>'
                f'<h2 class="pw-card-title">{escape(str(card["name"]))}</h2>'
                f'<p class="pw-card-description">{escape(str(card["description"]))}</p>'
                f'<div class="pw-product-image-wrap"><img class="pw-product-image" src="{escape(str(card["image"]), quote=True)}" alt="{escape(str(card["name"]))} product image"></div>'
                f'<p class="pw-price">{escape(str(card["price"]))}</p>'
                f'<p class="pw-meta">{escape(str(card["meta"]))}</p>'
                f'<ul class="pw-feature-list">{reasons}</ul>'
                f"{warning_html}"
                f"{rec_note}"
                f"{cta}"
                "</article>"
            )
        )

    if show_demo_note:
        if feed_results:
            note_or_empty_html = (
                '<p class="pw-demo-note">&#9432; Selected real products from connected provider feed. '
                "Recommended from these 4.</p>"
            )
        else:
            note_or_empty_html = (
                '<p class="pw-demo-note">&#9432; Safe connected provider mode: approved manual Amazon records only.</p>'
            )
    else:
        note_or_empty_html = (
            '<section class="pw-empty-state">PicWise safely shows no product cards until intent confidence '
            "and provider availability are both verified.</section>"
        )
    safe_note_html = f'<p class="pw-reference-disclaimer">{escape(safe_note_line)}</p>' if safe_note_line else ""

    html = (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>PicWise Reference — Buying Decision Preview</title>"
        '<meta name="description" content="Preview how PicWise supports product comparison and buying decisions while provider integrations are being configured.">'
        "<style>"
        "*{box-sizing:border-box;}html,body{height:100%;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#0f1f3a;background:#f8fbff;}"
        ".pw-reference-viewport{min-height:100vh;padding:12px;display:flex;justify-content:center;align-items:flex-start;}"
        ".pw-reference-scale-shell{position:relative;display:flex;justify-content:center;width:100%;}"
        ".pw-reference-frame{width:100%;max-width:1280px;padding:18px 24px 26px;position:relative;background:#f8fbff;}"
        ".pw-topbar{display:flex;justify-content:flex-end;align-items:center;height:52px;margin-bottom:18px;}"
        ".pw-brand{display:flex;align-items:flex-start;justify-content:center;gap:10px;text-decoration:none;color:#0f1f3a;width:max-content;margin:0 auto;}"
        ".pw-brand-text{display:flex;flex-direction:column;align-items:flex-start;line-height:1;}"
        ".pw-logo{width:42px;height:42px;border-radius:13px;background:linear-gradient(160deg,#30a0ff 0%,#1f6cff 70%);position:relative;box-shadow:none;filter:none;margin-top:1px;}"
        ".pw-logo::before{content:'';position:absolute;left:9px;top:9px;width:16px;height:16px;border:3px solid #fff;border-right-color:transparent;border-radius:999px;}"
        ".pw-logo::after{content:'';position:absolute;right:9px;bottom:9px;width:7px;height:7px;background:#fff;border-radius:999px;}"
        ".pw-brand-name{display:block;font-size:42px;line-height:1;font-weight:800;letter-spacing:-.04em;text-transform:lowercase;}"
        ".pw-brand-tagline{display:block;margin-top:5px;font-size:12px;letter-spacing:.02em;color:#3c5f8a;line-height:1.2;}"
        ".pw-actions{display:flex;align-items:center;gap:8px;padding-top:0;flex-wrap:wrap;justify-content:flex-end;row-gap:8px;}"
        ".pw-topbar-control{display:inline-flex;align-items:center;justify-content:center;height:32px;padding:0 13px;border-radius:999px;font-size:13px;font-weight:600;line-height:1;border:1px solid transparent;white-space:nowrap;}"
        ".pw-login-btn{background:#fff;color:#1d3a63;border-color:#ccdbf2;box-shadow:none;filter:none;cursor:pointer;}"
        ".pw-register{background:#1f6dff;color:#fff;border-color:#1f6dff;text-decoration:none;box-shadow:none;filter:none;}"
        ".pw-brand-wrap{margin:0 0 26px;display:flex;justify-content:center;}"
        ".pw-search-wrap{width:100%;max-width:760px;height:58px;margin:0 auto 24px;}"
        ".pw-search-shell{display:flex;align-items:center;gap:10px;width:100%;height:58px;background:#fff;border:1px solid #dbe8fb;border-radius:999px;padding:0 10px 0 18px;box-shadow:none;filter:none;}"
        ".pw-search-icon,.pw-search-button-icon{position:relative;width:16px;height:16px;display:inline-block;color:#7c93b7;flex:0 0 auto;}"
        ".pw-search-icon::before,.pw-search-button-icon::before{content:'';position:absolute;left:0;top:0;width:10px;height:10px;border:2px solid currentColor;border-radius:999px;}"
        ".pw-search-icon::after,.pw-search-button-icon::after{content:'';position:absolute;right:1px;bottom:2px;width:7px;height:2px;background:currentColor;border-radius:2px;transform:rotate(45deg);transform-origin:right center;}"
        ".pw-search-input{flex:1;height:56px;border:0;background:transparent;outline:none;font-size:19px;color:#95a8c7;font-weight:500;}"
        ".pw-search-button{width:42px;height:42px;border-radius:999px;border:0;background:#1f6dff;display:inline-flex;align-items:center;justify-content:center;box-shadow:none;filter:none;}"
        ".pw-search-button .pw-search-button-icon{color:#fff;}"
        ".pw-info-wrap{position:relative;display:inline-flex;flex-direction:column;align-items:stretch;gap:0;z-index:3;}"
        ".pw-info-link{background:#2d79f5;color:#fff;border-color:#2d79f5;cursor:pointer;box-shadow:none;filter:none;}"
        ".pw-info-link:focus-visible{outline:2px solid #2a6deb;outline-offset:3px;}"
        ".pw-tooltip{position:absolute;top:calc(100% + 8px);left:50%;transform:translateX(-50%);width:min(430px,calc(100vw - 24px));background:#fff;border:1px solid #dbe6f8;border-radius:12px;box-shadow:none;text-shadow:none;filter:none;padding:12px 14px;font-size:14px;line-height:1.5;color:#112849;text-align:left;display:none;z-index:2;}"
        ".pw-tooltip::before{content:'';position:absolute;left:50%;top:-7px;transform:translateX(-50%) rotate(45deg);width:14px;height:14px;background:#fff;border-left:1px solid #dbe6f8;border-top:1px solid #dbe6f8;}"
        ".pw-info-wrap.is-open .pw-tooltip{display:block;}"
        ".pw-query-line{width:100%;max-width:760px;margin:0 auto 44px;text-align:left;font-size:15px;color:#1a3d6b;font-weight:500;min-height:18px;}"
        ".pw-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;align-items:start;width:100%;max-width:1190px;margin:0 auto;justify-items:center;}"
        ".pw-card{position:relative;background:#fff;border:1px solid #dbe8fb;border-radius:18px;box-shadow:none;text-shadow:none;filter:none;padding:14px 14px 12px;display:flex;flex-direction:column;min-height:472px;width:100%;max-width:284px;}"
        ".pw-card-recommended{border:2px solid #2f78ff;box-shadow:none;text-shadow:none;filter:none;}"
        ".pw-rec-badge{display:inline-block;background:#2a70f1;color:#fff;font-size:12px;font-weight:700;padding:6px 11px;border-radius:999px;margin-bottom:9px;height:26px;line-height:14px;}"
        ".pw-badge{display:inline-block;align-self:flex-start;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.05em;margin-bottom:8px;height:21px;line-height:13px;}"
        ".pw-badge-budget,.pw-badge-premium{background:#eaf2ff;color:#3f72c4;}"
        ".pw-badge-value{background:#e8f8ec;color:#2f9b57;}"
        ".pw-badge-best{background:#f0ecff;color:#6e57cc;}"
        ".pw-card-title{margin:0;font-size:24px;line-height:1.08;color:#112649;letter-spacing:-.03em;min-height:58px;}"
        ".pw-card-description{margin:4px 0 8px;font-size:12px;color:#5c7397;line-height:1.35;min-height:32px;}"
        ".pw-product-image-wrap{height:84px;margin:0 0 10px;display:flex;align-items:center;justify-content:center;}"
        ".pw-product-image{display:block;width:252px;height:84px;border-radius:12px;border:1px solid #dbe6f6;object-fit:cover;background:#eef3fb;}"
        ".pw-price{margin:0;font-size:20px;line-height:1.1;font-weight:800;color:#2a70e6;letter-spacing:-.02em;min-height:26px;}"
        ".pw-meta{margin:3px 0 8px;font-size:12px;color:#6f88ac;min-height:16px;}"
        ".pw-feature-list{margin:0;padding:0;list-style:none;display:grid;gap:4px;min-height:56px;}"
        ".pw-feature-item{display:flex;align-items:flex-start;gap:7px;font-size:12px;color:#304b70;line-height:1.35;}"
        ".pw-feature-dot{width:8px;height:8px;border-radius:999px;background:#5b8ce5;flex:0 0 auto;margin-top:4px;}"
        ".pw-warning{margin:7px 0 0;font-size:11px;color:#5a7498;line-height:1.3;display:flex;gap:6px;min-height:29px;}"
        ".pw-warning-icon{font-size:10px;color:#6f86ad;line-height:1.2;margin-top:1px;}"
        ".pw-rec-note{margin:8px 0 0;font-size:11px;line-height:1.35;color:#2e4c7d;background:#eef4ff;border-radius:8px;padding:6px 8px;min-height:42px;}"
        ".pw-card-cta{margin-top:auto;width:100%;height:40px;border-radius:11px;border:1px solid #2e75ee;color:#2e75ee;background:#fff;font-size:16px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;}"
        ".pw-card-recommended .pw-card-cta{background:#1f6dff;color:#fff;border-color:#1f6dff;}"
        ".pw-empty-state{max-width:760px;margin:0 auto;background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:14px 16px;color:#2d4f7c;font-size:14px;line-height:1.6;text-align:left;}"
        ".pw-demo-note{text-align:center;font-size:12px;color:#7389ac;margin:16px 0 10px;}"
        ".pw-reference-disclaimer{margin:0 auto 16px;max-width:900px;padding:10px 12px;border:1px solid #dbe8fb;border-radius:12px;background:#f6f9ff;color:#284a76;font-size:14px;line-height:1.6;text-align:center;}"
        ".pw-footer{text-align:center;padding:6px 0 10px;font-size:12px;color:#6e83a3;}"
        ".pw-footer a{color:#6e83a3;text-decoration:none;margin-left:22px;}"
        "@media (min-width:1100px){.pw-reference-viewport{padding:8px;}.pw-reference-frame{padding:12px 20px 16px;}.pw-topbar{height:46px;margin-bottom:16px;}.pw-brand-wrap{margin:0 0 24px;}.pw-search-wrap{height:52px;margin:0 auto 20px;}.pw-query-line{margin:0 auto 40px;}.pw-card{padding:12px 12px 10px;min-height:444px;}.pw-product-image-wrap{height:74px;margin:0 0 8px;}.pw-product-image{width:228px;height:74px;}}"
        "@media (max-width:1099px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));max-width:760px;}.pw-topbar{height:auto;gap:10px;}}"
        "@media (max-width:640px){.pw-grid{grid-template-columns:1fr;max-width:420px;}}"
        "@media (max-width:699px){.pw-reference-frame{padding:14px 12px 20px;}.pw-topbar{flex-direction:column;align-items:center;margin-bottom:20px;}.pw-actions{width:100%;justify-content:center;gap:8px;}.pw-brand-wrap{margin:0 0 24px;}.pw-brand-name{font-size:33px;}.pw-search-wrap{height:auto;}.pw-search-shell{height:52px;padding:0 8px 0 14px;}.pw-search-input{height:50px;font-size:16px;}.pw-query-line{font-size:14px;margin:0 auto 36px;}.pw-grid{grid-template-columns:1fr;max-width:360px;}.pw-card{max-width:360px;}.pw-tooltip{width:min(430px,calc(100% - 8px));}}"
        ".pw-reference-viewport *,.pw-reference-viewport *::before,.pw-reference-viewport *::after{box-shadow:none!important;text-shadow:none!important;filter:none!important;}"
        "</style></head><body>"
        '<main class="pw-reference-viewport">'
        '<div class="pw-reference-scale-shell" id="pw-reference-scale-shell">'
        '<div class="pw-reference-frame" id="pw-reference-frame">'
        '<header class="pw-topbar">'
        '<div class="pw-actions"><button class="pw-topbar-control pw-login-btn" type="button">Login</button><a class="pw-topbar-control pw-register" href="#">Register</a><section class="pw-info-wrap" id="pw-info-wrap"><button class="pw-topbar-control pw-info-link" id="pw-info-button" type="button" aria-label="What is PicWise?" aria-expanded="false" aria-controls="pw-tooltip">What is PicWise?</button><div class="pw-tooltip" id="pw-tooltip">PicWise compares products for what you want to buy, recommends the 4 best matches, saves you time, and helps you choose faster.</div></section></div>'
        "</header>"
        '<section class="pw-brand-wrap" aria-label="PicWise brand">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">'
        '<span class="pw-logo" aria-hidden="true"></span>'
        '<span class="pw-brand-text"><span class="pw-brand-name">picwise</span><span class="pw-brand-tagline">shopping decision assistant</span></span>'
        "</a>"
        "</section>"
        '<section class="pw-search-wrap" aria-label="Search">'
        '<form class="pw-search-shell" action="/search" method="get">'
        '<span class="pw-search-icon" aria-hidden="true"></span>'
        f'<input class="pw-search-input" type="search" name="q" value="{escape(display_query, quote=True)}" placeholder="See the 4 best products before you buy" aria-label="See the 4 best products before you buy" autocomplete="off">'
        '<button class="pw-search-button" type="submit" aria-label="Search">'
        '<span class="pw-search-button-icon" aria-hidden="true"></span>'
        "</button></form></section>"
        f'<p class="pw-query-line">{escape(query_line)}</p>'
        f'<p class="pw-reference-disclaimer">{escape(disclaimer_line)}</p>'
        f"{safe_note_html}"
        f'<section class="pw-grid" data-card-count="{len(card_html)}">'
        f"{''.join(card_html)}"
        "</section>"
        f"{note_or_empty_html}"
        f"{render_public_footer()}"
        "</div>"
        "</div>"
        '<script>'
        '(function(){'
        'var infoWrap=document.getElementById("pw-info-wrap");'
        'var infoButton=document.getElementById("pw-info-button");'
        'if(!infoWrap||!infoButton){return;}'
        'var setOpen=function(isOpen){'
        'infoWrap.classList.toggle("is-open",isOpen);'
        'infoButton.setAttribute("aria-expanded",isOpen?"true":"false");'
        '};'
        'setOpen(false);'
        'infoButton.addEventListener("click",function(event){'
        'event.stopPropagation();'
        'setOpen(!infoWrap.classList.contains("is-open"));'
        '});'
        'document.addEventListener("click",function(event){'
        'if(!infoWrap.contains(event.target)){setOpen(false);}'
        '});'
        'document.addEventListener("keydown",function(event){'
        'if(event.key==="Escape"){setOpen(false);}'
        '});'
        '})();'
        "</script>"
        "</main>"
        "</body></html>"
    )
    proof_text = "LIVE RENDERER " + "PROOF V1"
    proof_comment = "picwise-reference-live-renderer-" + "proof-v1"
    html = html.replace(proof_text, "")
    html = html.replace(f"<!-- {proof_comment} -->", "")
    return html
