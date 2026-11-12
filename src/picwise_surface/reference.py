from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import quote

from picwise_providers.decision_labels import (
    UNVERIFIED_RISK,
    VERIFIED_RISK,
    build_fact_based_choice_labels,
    format_price_display,
    non_new_condition,
)
from picwise_search import LiveSearchResolution
from picwise_search.live_search_resolver import MAX_SHOWN_PRODUCTS
from .browser_lists import (
    BROWSER_LISTS_SCRIPT,
    BROWSER_LISTS_STYLES,
    HEAD_SCRIPT,
    favourite_button_html,
    header_buttons_html,
    panels_html,
)
from .assist import ASSIST_SCRIPT, ASSIST_STYLES, AssistView, assist_block_html, fit_line_html
from .fonts import FONT_PRELOAD_HTML
from .page_styles import _PAGE_STYLES
from .search_script import _SEARCH_SCRIPT
from .legal import render_public_footer
from .seo import (
    NOINDEX_META,
    SITE_LANGUAGE,
    declares_to_google,
    home_structured_data_html,
    icon_links_html,
    indexable_head_html,
    search_page_title,
)
from .trends import TRENDS_SCRIPT, TRENDS_STYLES, load_trends_panel, render_trends_panel


_SAFE_DISCLAIMER_BY_STATE = {
    "understood_provider_not_connected": "PicWise understood this search, but no safe provider is connected yet.",
    "not_understood": "PicWise could not understand this search safely.",
    "low_confidence_manual_review": "PicWise found weak product signals, but confidence is too low.",
    "blocked_or_unsafe": "PicWise cannot safely process this search.",
}

_FEED_CONNECTED_NO_FOUR_MESSAGE = (
    "PicWise understood this search, but the connected product feed has no four "
    "products it can show for it."
)
# Price first shows fewer than four as they are, so only an empty answer has nothing.
_FEED_CONNECTED_NO_PRODUCTS_MESSAGE = (
    "PicWise understood this search, but the connected product feed has no products "
    "it can show for it."
)

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
    # What separated the recommended choice from the rest; always listed first.
    "closer_search_match": "Matches your search more closely than the other choices",
    # A specification decides before the price does, where the kind of product has one
    # whose direction no buyer would dispute and at least two of the four state it.
    # The wording says "that state it" because some of the four may not have.
    "better_storage": "More storage than the other choices that state theirs",
    "better_battery": "Larger battery than the other choices that state theirs",
    "better_playtime": "Longer stated battery life than the other choices that state theirs",
    # Not readable from a feed yet, and labelled now so that the day one is, the card
    # has words for it rather than falling silent.
    "better_warranty": "Longer warranty than the other choices that state theirs",
    "better_efficiency_class": "Better energy rating than the other choices that state theirs",
    "price_tie_breaker": "Lowest price among the choices that match your search equally",
    "tie_on_search_match_and_price": (
        "Matches your search as closely as another choice, at the same price; "
        "PicWise has no further fact to separate them"
    ),
    "requested_condition_match": (
        "Listed by the feed in the condition you asked for, unlike other choices here"
    ),
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
# Affiliate network display names. A provider key names the NETWORK, never the
# shop: one Awin feed carries many merchants, so the merchant must come from the
# feed row. Never map a provider key to a single merchant name here.
_PROVIDER_NETWORK_LABELS = {
    "awin": "Awin",
}
_FEED_DISCLOSURE = (
    "Selected real products from a connected provider feed. "
    "PicWise recommends one option from these four by how closely it matches your "
    "search, then by price when they match equally — "
    "not independent review or market-wide ranking."
)
_FEED_SAFE_NOTE = "Recommended from these 4. Prices and availability come directly from the feed."

# Price first (owner, 2026-10-15 and 2026-10-16; docs/picwise_price_first_plan_2026-10-15.md).
# The card wording is the owner's: "Recommended" with "Mid-priced for this category"
# under it, and "Lowest price" on the cheap cards, "Lowest price of N shops" when one
# product is sold by several shops.
_PRICE_FIRST_RECOMMENDED_BADGE = "&#9733; Recommended"
_PRICE_FIRST_RECOMMENDED_LABEL = "Mid-priced for this category"
_PRICE_FIRST_LOWEST_LABEL = "Lowest price"
_PRICE_FIRST_SHOPS_LABEL = "Lowest price of {shops} shops"
# "From the shops connected to PicWise" said by none of them since 2026-11-12 (owner:
# «Αυτό εννοείται και είναι περιττό παίρνει χώρο και κατεβάζει τις κάρτες χαμηλά»).
_PRICE_FIRST_SORTED = "Sorted by price, lowest first."
# Owner, 2026-11-01: «Ένα προϊόν με προσφορά θα μπαίνει πρώτα από το φθηνότερο». A page
# whose answer has products on offer says so where it says how it is sorted.
_PRICE_FIRST_SORTED_WITH_OFFERS = (
    "Products a current shop offer covers come first, then the rest by price, lowest first."
)
_OFFER_LABEL = "Offer"
# Owner, 2026-11-01: «Εάν υπάρχει προσφορά να προτείνει την προσφορά». A Recommended
# chosen for its offer is not "mid-priced for this category", and says what it is.
_PRICE_FIRST_RECOMMENDED_OFFER_LABEL = "On offer"
_RECOMMENDED_MID_PRICED = "The Recommended is mid-priced for this category."
_RECOMMENDED_ON_OFFER = (
    "The Recommended is on offer: of the products on offer, the one nearest the middle of their prices."
)
_OFFERS_NOTE = "Offers are the shops' own, as they state them through Awin: check them on the shop's site."
_PRICE_FIRST_FEED_NOTE = "Prices and stock are as the shops list them."
# The products that fit a complex search first (owner, 2026-11-06; the Decision Contract,
# "The products that fit a complex search first"). A Recommended chosen among them is the
# middle of those, not of the category.
_PRICE_FIRST_RECOMMENDED_FITTING_LABEL = "Mid-priced of those that fit"
_PRICE_FIRST_SORTED_WITH_FITTING = (
    "Products whose own words show they fit your search come first, then the rest, each by price, "
    "lowest first."
)
_PRICE_FIRST_SORTED_WITH_FITTING_AND_OFFERS = (
    "Products whose own words show they fit your search come first, then the rest; in each, products "
    "a current shop offer covers come first, then by price, lowest first."
)
_RECOMMENDED_AMONG_FITTING = "The Recommended is mid-priced of those that fit."
_RECOMMENDED_AMONG_FITTING_ON_OFFER = (
    "The Recommended is on offer: of the products that fit and are on offer, the one nearest the middle "
    "of their prices."
)
_NO_RECOMMENDED_TOO_FEW = "No Recommended here: these products have no middle price to pick."
_NO_RECOMMENDED_NO_CODE = (
    "No Recommended here: no mid-priced product carries a barcode number (EAN), which PicWise needs "
    "to check that it is not cheaper in another shop."
)
_NO_RECOMMENDED_TOO_FEW_FITTING = "No Recommended here: too few products say they fit to have a middle price."
_NO_RECOMMENDED_NO_CODE_FITTING = (
    "No Recommended here: no mid-priced product of those that fit carries a barcode number (EAN), "
    "which PicWise needs to check that it is not cheaper in another shop."
)
_PRICE_FIRST_DISCLOSURES = {
    "recommended": (
        f"{_PRICE_FIRST_SORTED} The Recommended is mid-priced for this category. "
        f"{_PRICE_FIRST_FEED_NOTE}"
    ),
    # Owner, 2026-10-16: without an EAN/GTIN PicWise cannot know that the same
    # product is not cheaper elsewhere, so it recommends none.
    "no_recommendation_without_product_code": (
        f"{_PRICE_FIRST_SORTED} No Recommended here: no mid-priced product carries a "
        "barcode number (EAN), which PicWise needs to check that it is not cheaper in "
        f"another shop. {_PRICE_FIRST_FEED_NOTE}"
    ),
    "no_recommendation_too_few_products": (
        f"{_PRICE_FIRST_SORTED} No Recommended here: these products have no middle "
        f"price to pick. {_PRICE_FIRST_FEED_NOTE}"
    ),
}
_PRICE_FIRST_PAGE_NOTE = (
    "Real products from the shops' feeds, cheapest first. Prices and stock are as the shops "
    "list them, read again every night: check them on the shop's site before you buy."
)

# The design of 2026-10-31 (`docs/design/picwise_design_proposal_2026-10-31.html`,
# approved by the owner: «Υλοποίησε τα όλα»), made shorter on 2026-11-12 (owner: the
# site «μοιάζει πιο πολύ με εφημερίδα και όχι με search αγορών πρέπει να γράψουμε
# λιγότερα»; then «Έχεις δίκιο για αυτά», and the heading kept: «3»). The home page
# keeps its heading above the box and, under it, three short facts a buyer can hold it
# to, instead of a paragraph and three boxes of how it chooses; what PicWise does stays
# in "What is PicWise?" and the page's description. A search page goes straight to its
# products.
_HOME_HEADING = "Find the product you want in UK shops"
_HOME_TITLE = f"PicWise — {_HOME_HEADING}"
# Each true of every answer: only what the shops list in stock, read again every night;
# commission never a criterion (PROJECT_RULES.md 2 and 5). Before them, when the counts
# are known, the products and shops a search holds (`_home_facts_html`).
_HOME_FACTS = (
    ("night", "In stock only, updated every night"),
    ("fair", "Never ranked by commission"),
)
_FACT_ICONS = {
    "shop": '<path d="M4 9.5 5.5 4h13L20 9.5"/><path d="M4 9.5h16v1a3 3 0 0 1-5.33 1.9A3 3 0 0 1 12 13.5a3 3 0 0 1-2.67-1.1A3 3 0 0 1 4 10.5z"/><path d="M5.5 13v7h13v-7"/>',
    "night": '<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 4v5h-5"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "fair": '<path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6z"/><path d="m9 12 2 2 4-4"/>',
}


def _at_least(count: int) -> str:
    """A count as a buyer reads it and never more than it is: its first two figures,
    and a "+" for what was left off (251,235 reads "250,000+"; 39 reads "39"). A few of
    the products a search holds may be left out of an answer that night (a photo gone),
    so the exact figure could be a little more than a buyer can find."""
    count = max(int(count), 0)
    if count < 100:
        return f"{count:,}"
    step = 10 ** (len(str(count)) - 2)
    floor = count // step * step
    return f"{floor:,}" + ("+" if floor < count else "")


def _home_facts_html(catalogue: tuple[int, int] | None) -> str:
    """The home page's facts under the box: the products and shops a search holds when
    this process knows them (`state.peek_search_catalogue_counts`), then `_HOME_FACTS`."""
    items: list[tuple[str, str]] = []
    if catalogue and catalogue[0] > 0 and catalogue[1] > 0:
        products, shops = int(catalogue[0]), int(catalogue[1])
        items.append(
            (
                "shop",
                f"<b>{_at_least(products)}</b> {'product' if products == 1 else 'products'} from "
                f"<b>{shops:,}</b> UK {'shop' if shops == 1 else 'shops'}",
            )
        )
    items.extend((icon, escape(text)) for icon, text in _HOME_FACTS)
    return (
        '<ul class="pw-facts">'
        + "".join(
            '<li class="pw-fact"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f"{_FACT_ICONS[icon]}</svg><span>{text}</span></li>"
            for icon, text in items
        )
        + "</ul>"
    )

# The card's lines say whose word each fact is. The stock line rewords, for a shopper,
# the availability fact `decision_labels` states, and claims no more than it does: a
# reason it does not know reads as not confirmed.
_STOCK_LINES = (
    ("Purchase availability verified on the merchant page", "Checked available on the shop's page", "verified"),
    ("Listed as available by the provider feed, not verified", "Listed as available by the shop", "listed"),
)
_STOCK_NOT_CONFIRMED = ("Stock not confirmed by the shop's feed", "unconfirmed")
# A card states a limitation of its own (docs/LANDING_PAGE_SPEC.md, "Card Structure"; the
# Decision Contract's choice object keeps `risk_or_limitation` whole): what the feed says
# is not new, or gives no description, in its own words; a product checked on the shop's
# page says so. "Price and stock as the shop lists them, not verified by PicWise." is on
# no card since 2026-11-12 (owner: «Όχι not verified by ... είναι σαν να τον διώχνεις ...
# βγάλ' το εντελώς»): the page says once, above the cards, that prices and stock are as
# the shops list them (`_PRICE_FIRST_FEED_NOTE`), and each card's stock line whose word
# its stock is ("Listed as available by the shop").
_CARD_VERIFIED_NOTE = "Checked on the shop's page; the shop can still change price or stock."
_SINGLE_PRODUCT_LINE = "This is the only product PicWise found for this search in its shops."
_SINGLE_PRODUCT_DELIVERY = "See the shop's site"
# A price reads as UK shoppers write it, "£12.74": the sign carries the currency.
_CURRENCY_SIGNS = {"GBP": "£", "EUR": "€", "USD": "$"}
_NUMBER_AND_CODE = re.compile(r"^(\d[\d,]*(?:\.\d+)?) ([A-Z]{3})$")

# The search box (owner, 2026-10-17). "What are you looking for?" promises nothing a
# shop reviewing PicWise for its affiliate programme could object to; "What is
# PicWise?" says what price first does.
_SEARCH_PLACEHOLDER = "What are you looking for?"
_WHAT_IS_PICWISE = (
    "PicWise finds the product you want in the shops it is connected to, shows what the "
    "shops list as in stock, products on offer first and then cheapest first, and marks one "
    "Recommended: a product on offer where there is one, else a mid-priced one."
)
_MIC_TITLE = (
    "Search by voice. Your browser turns your words into text; in Chrome the audio is "
    "sent to Google for this."
)
_MIC_ICON = (
    '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"/>'
    "</svg>"
)



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


def _scanning_screen_html() -> str:
    """The loading screen, hidden until a search starts (`_SEARCH_SCRIPT`).

    The PicWise mark in a turning ring, and no words on the screen (owner, 2026-11-12:
    «δεν μου αρέσει να λέει ψάχνω από τόσα προϊόντα φτιάξε απλά ένα όμορφο φόρτωμα»).
    It names no number; only a screen reader is told what is searched for.
    """
    return (
        '<div class="pw-scan" id="pw-scan" role="status" aria-live="polite" hidden>'
        '<div class="pw-loader" aria-hidden="true"><span class="pw-loader-ring"></span>'
        '<span class="pw-logo"></span></div>'
        '<p class="pw-scan-text" id="pw-scan-text"></p></div>'
    )


def _price_first_display_allowed(resolution: LiveSearchResolution) -> bool:
    """May the page show a price-first answer? 1 to 4 products on the first page,
    every one complete and listed as in stock, and the Recommended, when there is one,
    first among them."""
    if resolution.provider_feed_selection_status != "selected":
        return False
    decision = str(resolution.provider_feed_decision_status or "")
    if decision not in _PRICE_FIRST_DISCLOSURES:
        return False
    products = resolution.provider_feed_selected_products
    if not 1 <= len(products) <= 4:
        return False
    if not all(_feed_product_dict_complete(product) for product in products):
        return False
    if any(_provider_feed_product_blocks_ui(product) for product in products):
        return False
    if decision == "recommended":
        recommended_id = str(resolution.provider_feed_recommended_product_id or "").strip()
        first_id = str(products[0].get("provider_product_id") or "").strip()
        if not recommended_id or recommended_id != first_id:
            return False
    return True


def _provider_feed_ui_display_allowed(resolution: LiveSearchResolution) -> bool:
    if getattr(resolution, "provider_feed_price_first", False):
        return _price_first_display_allowed(resolution)
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


def provider_feed_cards_will_render(resolution: LiveSearchResolution) -> bool:
    """Whether the surface will actually render provider-feed choice cards.

    Exposed so impression tracking can report what was shown rather than what the
    backend merely selected. Reading the same gate the renderer uses keeps the two
    from drifting: an event claiming choices were shown when the surface refused to
    render them would be exactly the kind of overclaim the runtime truth rules forbid.
    """
    if not _provider_feed_ui_display_allowed(resolution):
        return False
    for product in resolution.provider_feed_selected_products:
        if _provider_feed_product_blocks_ui(product):
            return False
    return True


def _feed_recommendation_reason_bullets(reason_codes: tuple[str, ...]) -> list[str]:
    bullets: list[str] = []
    for code in reason_codes:
        label = _FEED_RECOMMENDATION_REASON_LABELS.get(str(code).strip())
        if label:
            bullets.append(label)
    return bullets


def _provider_network_label(provider_key: str) -> str:
    normalized = str(provider_key or "").strip().lower()
    return _PROVIDER_NETWORK_LABELS.get(
        normalized,
        normalized.replace("_", " ").title() or "Provider feed",
    )


def _provider_store_label(provider_key: str, merchant_name: str = "") -> str:
    """Build the store line from what the feed actually says.

    With a merchant in the row: "<merchant> via <network>". Without one, name the
    network alone — inventing a merchant would misattribute the sale.
    """
    network = _provider_network_label(provider_key)
    merchant = " ".join(str(merchant_name or "").split()).strip()
    if merchant:
        return f"{merchant} via {network}"
    return f"{network} provider feed (merchant not named in feed)"


def _build_provider_feed_result_cards(
    *,
    resolution: LiveSearchResolution,
    source_page: str = "search",
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
    selected_products = list(resolution.provider_feed_selected_products)
    # Decision Contract items 3 and 4: every choice carries a role label, a decision
    # label, key reasons and a stated limitation. All are derived from feed and verifier
    # facts only -- see picwise_providers/decision_labels.
    choice_labels = build_fact_based_choice_labels(selected_products)
    cards: list[dict[str, object]] = []
    for card_index, product in enumerate(selected_products):
        if _provider_feed_product_blocks_ui(product):
            return ([], False, "", "")
        labels = (
            choice_labels[card_index] if card_index < len(choice_labels) else None
        )
        product_id = str(product.get("provider_product_id") or "").strip()
        provider_key = str(product.get("provider_key") or "").strip()
        is_recommended = product_id == recommended_id
        store_label = _provider_store_label(
            provider_key,
            str(product.get("merchant_name") or ""),
        )
        cards.append(
            {
                "badge": "REAL FEED",
                "badge_class": "pw-badge-value",
                "name": str(product.get("title") or "").strip(),
                "role_label": labels.role_label if labels else "",
                "choice_id": product_id,
                "description": (
                    labels.decision_label
                    if labels and labels.decision_label
                    else "Selected real product (purchase not verified)"
                ),
                "rating": "",
                "reviews": "",
                # The currency belongs with the number: "749.00" alone reads as euros
                # to a Greek buyer whatever the feed's currency is.
                "price": format_price_display(product),
                "meta": _provider_feed_card_meta(product, store_label=store_label),
                "bullets": (
                    list(labels.key_reasons) + (reason_bullets[:3] if is_recommended else [])
                    if labels
                    else (reason_bullets if is_recommended else [])
                ),
                "warning": labels.risk_or_limitation if labels else "",
                "cta": "View in Store",
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
                # Route the CTA through /out/feed so the click is recorded and the
                # target is re-validated at click time, instead of linking the raw
                # product URL and losing the tracking event the contract requires.
                "href": (
                    f"/out/feed?pid={quote(product_id, safe='')}"
                    f"&q={quote(str(resolution.display_query or ''), safe='')}"
                    f"&src={quote(source_page, safe='')}"
                    f"&rec={'1' if is_recommended else '0'}"
                ),
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



def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        return f"{number}th"
    return f"{number}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th') }"


def _price_place_line(place: int | None, total: int, *, condition: str = "") -> str:
    """Where a product sits in the whole answer by price: "3rd cheapest of 45".

    Arithmetic over the prices of the answer, nothing else; products at one price share
    a place. A product that is not new says so next to it, where the buyer reads the
    price: a place between a refurbished item and new ones compares different things.
    """
    if not place or total <= 0:
        line = ""
    elif total == 1:
        line = "The only product found"
    elif place == 1:
        line = f"Cheapest of {total}"
    else:
        line = f"{_ordinal(place)} cheapest of {total}"
    if condition:
        line = f"{line} · condition: {condition}" if line else f"Condition: {condition}"
    return line


def _display_price(product: dict[str, object]) -> str:
    """The price as a shopper reads it: "£12.74" for "12.74" in GBP.

    Only a plain number with the feed's currency code is rewritten; any other text the
    feed gave keeps the form `format_price_display` gives it, code and all.
    """
    shown = format_price_display(product)
    match = _NUMBER_AND_CODE.match(shown)
    if not match or match.group(2) not in _CURRENCY_SIGNS:
        return shown
    try:
        amount = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return shown
    number = f"{amount:,.2f}" if amount != amount.to_integral_value() or "." in match.group(1) else f"{amount:,.0f}"
    return f"{_CURRENCY_SIGNS[match.group(2)]}{number}"


def _stock_line(label: object | None) -> tuple[str, str]:
    """The card's stock line and its state: "verified", "listed" or "unconfirmed"."""
    reasons = tuple(getattr(label, "key_reasons", ()) or ())
    for reason, line, state in _STOCK_LINES:
        if reason in reasons:
            return line, state
    return _STOCK_NOT_CONFIRMED


def _card_note(label: object | None) -> str:
    """The card's own limitation, or "" when it has none.

    What is particular to the product (not new, no description) in the labels' own
    words. Of the general sentence they end with, only a product checked on the shop's
    page keeps a line, in fewer words; that a product was not checked is said on no card
    (owner, 2026-11-12), the page saying once that prices and stock are the shops'. A
    limitation in other words is shown whole.
    """
    risk = " ".join(str(getattr(label, "risk_or_limitation", "") or "").split())
    if risk.endswith(VERIFIED_RISK):
        return " ".join(part for part in (risk[: -len(VERIFIED_RISK)].strip(), _CARD_VERIFIED_NOTE) if part)
    if risk.endswith(UNVERIFIED_RISK):
        return risk[: -len(UNVERIFIED_RISK)].strip()
    return risk


def _build_price_first_cards(
    *,
    resolution: LiveSearchResolution,
    source_page: str = "search",
    fit_words: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    """The cards of a price-first answer, in the order shown.

    The first page holds the Recommended, when there is one, and then the cheapest;
    after it come the products "More" has opened. Only the Recommended carries a
    recommendation: nothing "More" opens is recommended (owner, 2026-10-15), and every
    other click is tracked with `rec=0`.

    `fit_words` are the own words of the products the AI layer read as fitting a complex
    search, by product id, which the search put first (owner, 2026-11-06): each gets a ✓
    and its words, and every card of the page the line for them.
    """
    if not _price_first_display_allowed(resolution):
        return []
    first_page = list(resolution.provider_feed_selected_products)
    opened = [
        product
        for product in (getattr(resolution, "provider_feed_more_products", ()) or ())
        if _feed_product_dict_complete(product) and not _provider_feed_product_blocks_ui(product)
    ]
    recommended_id = (
        str(resolution.provider_feed_recommended_product_id or "").strip()
        if resolution.provider_feed_decision_status == "recommended"
        else ""
    )
    cheapest = set(getattr(resolution, "provider_feed_cheapest_product_ids", ()) or ())
    shops = dict(getattr(resolution, "provider_feed_shop_counts", ()) or ())
    places = dict(getattr(resolution, "provider_feed_price_ranks", ()) or ())
    total = int(getattr(resolution, "provider_feed_total_count", 0) or 0)
    products = first_page + opened
    labels = build_fact_based_choice_labels(products)
    offers = dict(getattr(resolution, "provider_feed_offers", ()) or ())
    cards: list[dict[str, object]] = []
    for index, product in enumerate(products):
        label = labels[index] if index < len(labels) else None
        product_id = str(product.get("provider_product_id") or "").strip()
        is_recommended = index == 0 and bool(recommended_id) and product_id == recommended_id
        shop_count = int(shops.get(product_id, 1) or 1)
        shops_label = (
            _PRICE_FIRST_SHOPS_LABEL.format(shops=shop_count) if shop_count > 1 else ""
        )
        offer = offers.get(product_id)
        if is_recommended:
            role_label = (
                _PRICE_FIRST_RECOMMENDED_OFFER_LABEL
                if offer
                else _PRICE_FIRST_RECOMMENDED_FITTING_LABEL
                if fit_words and getattr(resolution, "provider_feed_recommended_among_fitting", False)
                else _PRICE_FIRST_RECOMMENDED_LABEL
            )
        elif offer:
            role_label = _OFFER_LABEL
        elif product_id in cheapest:
            role_label = shops_label or _PRICE_FIRST_LOWEST_LABEL
        else:
            # A dearer product on a short first page, or one "More" opened: it is not
            # the lowest price of the answer, only of the shops selling it.
            role_label = shops_label
        # The design of 2026-10-31: the card names the shop, the price, what the shop
        # says of its stock and where the price stands in the answer, each on its own
        # line, and the button names the shop it goes to.
        provider_key = str(product.get("provider_key") or "").strip()
        shop = " ".join(str(product.get("merchant_name") or "").split()).strip()
        stock_line, stock_state = _stock_line(label)
        cards.append(
            {
                "name": str(product.get("title") or "").strip(),
                "role_label": role_label,
                "choice_id": product_id,
                "anchor_id": f"pw-choice-{index + 1}",
                "description": _price_place_line(
                    places.get(product_id), total, condition=non_new_condition(product)
                ),
                "price": _display_price(product),
                "shop": shop,
                # The merchant from the feed row, never invented (`_provider_store_label`).
                "shop_line": _provider_store_label(provider_key, shop),
                "brand": str(product.get("brand") or "").strip(),
                "stock_line": stock_line,
                "stock_state": stock_state,
                "extra_line": shops_label if is_recommended or (offer and shops_label) else "",
                "offer": offer or None,
                "note": _card_note(label),
                "meta": "",
                "bullets": [],
                "warning": "",
                "cta": f"View at {shop}" if shop else "View in Store",
                "image": str(product.get("image_url") or "").strip(),
                "recommended": is_recommended,
                "fit_slot": bool(fit_words),
                "fit": (fit_words or {}).get(product_id, ""),
                "rec_note": "",
                "rec_badge_html": _PRICE_FIRST_RECOMMENDED_BADGE if is_recommended else "",
                "href": (
                    f"/out/feed?pid={quote(product_id, safe='')}"
                    f"&q={quote(str(resolution.display_query or ''), safe='')}"
                    f"&src={quote(source_page, safe='')}"
                    f"&rec={'1' if is_recommended else '0'}"
                ),
            }
        )
    return cards


def _fitting_disclosure(
    disclosure: str, cards: list[dict[str, object]], resolution: LiveSearchResolution
) -> str:
    """How the page is sorted and how its Recommended was chosen, when the products that
    fit a complex search were put first (owner, 2026-11-06): said of those, truly."""
    with_offers = any(card.get("offer") for card in cards)
    text = disclosure.replace(
        _PRICE_FIRST_SORTED,
        _PRICE_FIRST_SORTED_WITH_FITTING_AND_OFFERS if with_offers else _PRICE_FIRST_SORTED_WITH_FITTING,
    )
    recommended = next((card for card in cards if card.get("recommended")), None)
    if recommended is not None and getattr(resolution, "provider_feed_recommended_among_fitting", False):
        text = text.replace(
            _RECOMMENDED_MID_PRICED,
            _RECOMMENDED_AMONG_FITTING_ON_OFFER if recommended.get("offer") else _RECOMMENDED_AMONG_FITTING,
        )
    text = text.replace(_NO_RECOMMENDED_TOO_FEW, _NO_RECOMMENDED_TOO_FEW_FITTING)
    return text.replace(_NO_RECOMMENDED_NO_CODE, _NO_RECOMMENDED_NO_CODE_FITTING)


def _price_first_more_html(
    *,
    resolution: LiveSearchResolution,
    display_query: str,
    shown_cards: int,
    source_page: str,
) -> str:
    """The counter under the cards, "4 of 45", and the "More" button.

    "More" opens the next four cheapest, as often as the buyer asks, until the list
    ends (owner, 2026-10-15). It is a link the buyer presses, not a scroll that loads
    on its own, and it works with no JavaScript: the page is drawn again holding four
    more, and opens at the first of them.
    """
    total = max(int(getattr(resolution, "provider_feed_total_count", 0) or 0), shown_cards)
    requested = len(resolution.provider_feed_selected_products) + len(
        getattr(resolution, "provider_feed_more_products", ()) or ()
    )
    counter = f'<p class="pw-counter">{shown_cards} of {total}</p>'
    button = ""
    if requested < total and requested < MAX_SHOWN_PRODUCTS:
        path = "/results" if source_page == "results" else "/search"
        href = (
            f"{path}?q={quote(display_query, safe='')}"
            f"&shown={min(requested + 4, MAX_SHOWN_PRODUCTS)}#pw-choice-{shown_cards + 1}"
        )
        button = (
            f'<a class="pw-more-button" href="{escape(href, quote=True)}" rel="nofollow">'
            "More</a>"
        )
    return f'<nav class="pw-more" aria-label="More products">{counter}{button}</nav>'


def _offer_until(end: object) -> str:
    """"until 31 Dec", with the year when it is not this year's."""
    try:
        moment = datetime.fromisoformat(str(end or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    year = "" if moment.year == datetime.now(timezone.utc).year else f" {moment.year}"
    return f"until {moment.day} {moment:%b}{year}"


def _offer_html(offer: dict[str, object]) -> str:
    """The shop's offer on a card, in the shop's own words, its end, its code where the
    shop gives one, and its terms."""
    title = escape(str(offer.get("title") or ""))
    facts = [_offer_until(offer.get("end"))]
    code = str(offer.get("code") or "").strip()
    meta = escape(" · ".join(part for part in facts if part))
    code_html = (
        f'{" · " if meta else ""}Code: <strong class="pw-offer-code">{escape(code)}</strong>' if code else ""
    )
    terms = str(offer.get("terms") or "").strip()
    terms_html = (
        f'<details class="pw-offer-terms"><summary>Offer terms</summary><p>{escape(terms)}</p></details>'
        if terms
        else ""
    )
    return (
        '<div class="pw-card-offer">'
        f'<p class="pw-offer-title">{title}</p>'
        f'<p class="pw-offer-meta">{meta}{code_html}</p>'
        f"{terms_html}"
        "</div>"
    )


def _single_product_facts_html(card: dict[str, object], *, product_code: str) -> str:
    """What a product shown alone says of itself, each line only when its shop gives it
    (the design's single product: shop, brand, product code, delivery). PicWise holds no
    delivery details, so that line sends the buyer to the shop, and nothing is filled in."""
    facts = [("Shop", str(card.get("shop_line") or ""))]
    if str(card.get("brand") or "").strip():
        facts.append(("Brand", str(card["brand"]).strip()))
    if product_code.strip():
        facts.append(("Product code", product_code.strip()))
    facts.append(("Delivery", _SINGLE_PRODUCT_DELIVERY))
    rows = "".join(
        f'<li><span class="pw-fact-name">{escape(name)}</span><span class="pw-fact-value">{escape(value)}</span></li>'
        for name, value in facts
        if value
    )
    return f'<ul class="pw-single-facts">{rows}</ul>'


def _render_choice_card(
    card: dict[str, object], idx: int, *, single: bool = False, product_code: str = ""
) -> str:
    """One choice card's HTML. Used for the four and for the second four alike,
    so a card behind "see more" cannot drift from a card in front of it.

    The design of 2026-10-31: a square photo that is never cut, then the card's role,
    a title of at most three lines, the shop, the price, the stock and the price's place,
    the limitation, and the button at the foot, so that every card of a row has the same
    height and its price and button sit on the same line as the others'. A product shown
    alone (`single`) is the same card laid out on its own, with its facts listed.
    """
    recommended = bool(card["recommended"])
    rec_class = " pw-card-recommended" if recommended else ""
    name = str(card["name"])
    choice_id = str(card.get("choice_id") or f"fixed-{idx}")
    rec_header = (
        f'<div class="pw-rec-badge">{card.get("rec_badge_html") or "Suggested by PicWise"}</div>'
        if recommended
        else ""
    )
    # A product shown alone is not "the lowest price" of anything: its own line says it
    # is the only one.
    offer = card.get("offer") if isinstance(card.get("offer"), dict) else None
    role_label_html = ""
    if str(card.get("role_label") or "") and not single:
        # The offer's mark comes before the class, so that what reads the cards by their
        # classes (tests, the deployment's comparison) reads this label as any other.
        offer_mark = ' data-offer="1"' if offer and str(card.get("role_label")) == _OFFER_LABEL else ""
        role_label_html = f'<p{offer_mark} class="pw-role-label">{escape(str(card.get("role_label")))}</p>'
    reasons = "".join(
        f'<li class="pw-feature-item"><span class="pw-feature-dot" aria-hidden="true"></span><span>{escape(str(reason))}</span></li>'
        for reason in list(card.get("bullets") or ())
    )
    lines = []
    if str(card.get("shop_line") or ""):
        lines.append(f'<p class="pw-card-shop">{escape(str(card["shop_line"]))}</p>')
    lines.append(f'<p class="pw-price">{escape(str(card["price"]))}</p>')
    if str(card.get("stock_line") or ""):
        lines.append(
            f'<p class="pw-card-stock pw-stock-{escape(str(card.get("stock_state") or "unconfirmed"), quote=True)}">'
            f'{escape(str(card["stock_line"]))}</p>'
        )
    if offer:
        lines.append(_offer_html(offer))
    lines.append(f'<p class="pw-card-description">{escape(str(card["description"]))}</p>')
    if str(card.get("extra_line") or ""):
        lines.append(f'<p class="pw-card-extra">{escape(str(card["extra_line"]))}</p>')
    if str(card.get("meta") or ""):
        lines.append(f'<p class="pw-meta">{escape(str(card["meta"]))}</p>')
    if reasons:
        lines.append(f'<ul class="pw-feature-list">{reasons}</ul>')
    if str(card.get("warning") or ""):
        lines.append(
            f'<p class="pw-warning"><span class="pw-warning-icon" aria-hidden="true">&#9651;</span>{escape(str(card["warning"]))}</p>'
        )
    if str(card.get("rec_note") or ""):
        lines.append(f'<p class="pw-rec-note">{escape(str(card["rec_note"]))}</p>')
    if single:
        lines.append(_single_product_facts_html(card, product_code=product_code))
    if str(card.get("note") or ""):
        lines.append(f'<p class="pw-card-note">{escape(str(card["note"]))}</p>')
    shop = str(card.get("shop") or "")
    if card.get("href"):
        label = (
            f'View<span class="pw-cta-at"> at {escape(shop)}</span>'
            if shop and str(card["cta"]) == f"View at {shop}"
            else escape(str(card["cta"]))
        )
        cta = (
            f'<a class="pw-card-cta pw-card-cta-link" href="{escape(str(card["href"]), quote=True)}" '
            f'rel="nofollow sponsored noopener">{label}</a>'
        )
    else:
        cta = f'<button class="pw-card-cta" type="submit">{escape(str(card["cta"]))}</button>'
    # Where "More" opens the page: the first card it added.
    anchor = (
        f'<span class="pw-anchor" id="{escape(str(card["anchor_id"]), quote=True)}"></span>'
        if card.get("anchor_id")
        else ""
    )
    heart = (
        favourite_button_html(
            product_id=choice_id,
            title=name,
            price=str(card["price"]),
            shop=shop,
            image=str(card["image"]),
        )
        if card.get("href") and card.get("choice_id")
        else ""
    )
    # The first row's photos load at once; the rest as the page is scrolled to them.
    loading = "eager" if idx <= 4 else "lazy"
    # The first card's photo is asked for before the page's other photos: the browser
    # shows a card only once its photo has loaded, so the first card waits on it
    # (docs/PICWISE_AUDIT_FIXES.md, section 4, A.1). One photo a page, never more.
    priority = ' fetchpriority="high"' if idx == 1 else ""
    single_line = f'<p class="pw-single-only">{escape(_SINGLE_PRODUCT_LINE)}</p>' if single else ""
    return (
        f'<article class="pw-card{rec_class}" data-choice-id="{escape(choice_id, quote=True)}">'
        f"{anchor}"
        '<div class="pw-product-image-wrap">'
        f'<img class="pw-product-image" src="{escape(str(card["image"]), quote=True)}" '
        f'alt="{escape(name)} product image" width="400" height="400" loading="{loading}"{priority} decoding="async">'
        f"{heart}</div>"
        '<div class="pw-card-body">'
        f"{single_line}"
        f'<div class="pw-role">{rec_header}{role_label_html}</div>'
        f'<h2 title="{escape(name, quote=True)}" class="pw-card-title">{escape(name)}</h2>'
        f"{fit_line_html(str(card.get('fit') or '')) if card.get('fit_slot') else ''}"
        f"{''.join(lines)}"
        f"{cta}"
        "</div>"
        "</article>"
    )


def _kind_choices_html(resolution: LiveSearchResolution) -> str:
    """The question above the results of a search naming only a general kind, with the
    searches that narrow it as links: "What kind of cable? extension cable, hdmi cable"
    (owner, 2026-10-28: the search asks which cable is meant; `kind_choices.py`)."""
    choices = tuple(str(text) for text in getattr(resolution, "kind_choices", ()) or () if str(text).strip())
    name = str(getattr(resolution, "kind_choices_name", "") or "").strip()
    if not choices or not name:
        return ""
    question = f"What kind of {name}?"
    links = "".join(
        f'<a class="pw-kind-choice" href="/search?q={quote(text, safe="")}">{escape(text)}</a>'
        for text in choices
    )
    return (
        f'<nav class="pw-kind-choices" aria-label="{escape(question, quote=True)}">'
        f'<span class="pw-kind-choices-ask">{escape(question)}</span>{links}</nav>'
    )




def render_picwise_reference_surface(
    query: str = "",
    *,
    resolution: LiveSearchResolution | None = None,
    source_page: str = "search",
    catalogue: tuple[int, int] | None = None,
    indexable: bool = False,
    single_product_code: str = "",
    assist: AssistView | None = None,
) -> str:
    """The search page. `catalogue` is (products, shops) a search reads, when the server
    has the feed loaded, for the scanning screen; None makes it name no number.

    Only the home page without a search is `indexable`. Every other page this draws is
    the site's own search, which Google is told not to index (owner, 2026-10-23: «βάλε
    το noindex στο /search και προστάτεψε το site από την google όσο το χτίζουμε»);
    the pages meant for Google are in `docs/PICWISE_GOOGLE_PAGES_SPEC.md`.

    `single_product_code` is the barcode or maker's code of the one product of an answer
    that has only one, as its shop gives it, for that product's own layout.

    `assist` is the AI layer's part of a complex search (`picwise_surface.assist`): its
    sentence and the fitting products' own words, when the search put those first
    (owner, 2026-11-06); the shops' words; or, while the answer is awaited, the key the
    page's script asks about. None draws the page as before the layer.
    """
    display_query = str(query or "")
    fitting_ids = tuple(getattr(resolution, "provider_feed_fitting_product_ids", ()) or ()) if resolution else ()
    fit_words = (
        {product_id: str((assist.fit_words or {}).get(product_id, "")) for product_id in fitting_ids}
        if assist is not None and assist.sentence and fitting_ids
        else {}
    )
    query_line = ""
    disclaimer_line = (
        "Live safe mode — no marketplace API, no scraping, and no fake live commerce claims."
    )
    safe_note_line = ""
    show_demo_note = False

    feed_results = False
    price_first_page = False
    if resolution is None:
        card_specs: list[dict[str, object]] = []
    else:
        # Amazon has been removed from the project, so the provider feed is the only
        # source of choice cards.
        card_specs = []
        has_live_results = False
        disclosure = ""
        safe_note = ""
        if getattr(resolution, "provider_feed_price_first", False):
            price_first_cards = _build_price_first_cards(
                resolution=resolution,
                source_page=source_page,
                fit_words=fit_words or None,
            )
            if price_first_cards:
                card_specs = price_first_cards
                has_live_results = True
                feed_results = True
                price_first_page = True
                disclosure = _PRICE_FIRST_DISCLOSURES[
                    str(resolution.provider_feed_decision_status)
                ]
                if fit_words:
                    disclosure = _fitting_disclosure(disclosure, price_first_cards, resolution)
                if any(card.get("offer") for card in price_first_cards):
                    disclosure = disclosure.replace(_PRICE_FIRST_SORTED, _PRICE_FIRST_SORTED_WITH_OFFERS)
                if any(card.get("offer") and card.get("recommended") for card in price_first_cards):
                    disclosure = disclosure.replace(_RECOMMENDED_MID_PRICED, _RECOMMENDED_ON_OFFER)
        else:
            feed_cards, feed_live, feed_disclosure, feed_safe_note = (
                _build_provider_feed_result_cards(
                    resolution=resolution,
                    source_page=source_page,
                )
            )
            if feed_live:
                card_specs = feed_cards
                has_live_results = True
                feed_results = True
                disclosure = feed_disclosure
                safe_note = feed_safe_note
        unmatched_terms = tuple(
            str(term).strip()
            for term in getattr(resolution, "provider_feed_unmatched_query_terms", ())
            or ()
            if str(term).strip()
        )
        ambiguous_families = tuple(
            str(name).strip()
            for name in getattr(resolution, "provider_feed_ambiguous_product_families", ())
            or ()
            if str(name).strip()
        )
        if display_query.strip():
            if has_live_results and price_first_page:
                with_offers = any(card.get("offer") for card in card_specs)
                query_line = (
                    f"Results for: {display_query}, offers first, then cheapest first"
                    if with_offers
                    else f"Results for: {display_query}, cheapest first"
                )
                if fit_words:
                    query_line = (
                        f"Results for: {display_query}, those that fit first, then offers, then cheapest first"
                        if with_offers
                        else f"Results for: {display_query}, those that fit first, then cheapest first"
                    )
                understood_name = str(getattr(resolution, "understood_concept_name", "") or "")
                if understood_name and getattr(resolution, "understood_by_correction", False):
                    query_line += f"  ·  Understood as: {understood_name}"
                total = int(getattr(resolution, "provider_feed_total_count", 0) or 0)
                partial_terms = tuple(
                    getattr(resolution, "provider_feed_partially_matched_terms", ()) or ()
                )
                if partial_terms:
                    # No product carries every word of the search together; these are
                    # carried by part of the answer, which does not require them.
                    query_line += "  ·  Only some match: " + ", ".join(
                        f"{term} ({count} of {total})" for term, count in partial_terms
                    )
                if unmatched_terms:
                    query_line += "  ·  PicWise could not match: " + ", ".join(unmatched_terms)
            elif has_live_results and feed_results:
                query_line = f"Showing 4 selected real products for: {display_query}"
                understood_name = str(getattr(resolution, "understood_concept_name", "") or "")
                if understood_name and getattr(resolution, "understood_by_correction", False):
                    # The query was read through a typo correction. Say what it was
                    # read as, so a wrong correction is visible instead of silent.
                    query_line += f"  ·  Understood as: {understood_name}"
                partial_terms = tuple(
                    getattr(resolution, "provider_feed_partially_matched_terms", ()) or ()
                )
                if partial_terms:
                    # Some, not all, of the four carry these; they are ranked first.
                    query_line += "  ·  Only some of the four match: " + ", ".join(
                        f"{term} ({count} of 4)" for term, count in partial_terms
                    )
                if unmatched_terms:
                    # Say what PicWise could not filter by. Without this the buyer would
                    # read four products as an answer to their whole request, when part
                    # of it could not be matched against the connected feed.
                    query_line += (
                        "  ·  PicWise could not match: "
                        + ", ".join(unmatched_terms)
                    )
            elif has_live_results:
                query_line = f"Showing {len(card_specs)} options for: {display_query}"
            else:
                query_line = ""
        if has_live_results and disclosure:
            disclaimer_line = disclosure
            safe_note_line = safe_note
        elif display_query.strip() and ambiguous_families:
            disclaimer_line = (
                "PicWise is not sure which product you mean. This search matches "
                + " and ".join(ambiguous_families[:3])
                + ". Add a word that names the product you want."
            )
        elif display_query.strip():
            base_message = _SAFE_DISCLAIMER_BY_STATE.get(
                resolution.resolver_state,
                "PicWise could not understand this search safely.",
            )
            if (
                resolution.resolver_state == "understood_provider_not_connected"
                and getattr(resolution, "provider_feed_status", None) == "provider_feed_ready"
            ):
                # The state name predates the feed: a feed is connected here, it just has
                # no products to show. "No provider is connected" would be false.
                base_message = (
                    _FEED_CONNECTED_NO_PRODUCTS_MESSAGE
                    if getattr(resolution, "provider_feed_price_first", False)
                    else _FEED_CONNECTED_NO_FOUR_MESSAGE
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

    is_home = not display_query.strip()
    total_found = int(getattr(resolution, "provider_feed_total_count", 0) or 0) if resolution is not None else 0
    # One product with no other: its own layout, never one small card in the middle
    # (owner, 2026-10-31; PROJECT_RULES §2).
    single_layout = price_first_page and len(card_specs) == 1 and total_found <= 1
    card_html = [
        _render_choice_card(
            card,
            idx,
            single=single_layout,
            product_code=single_product_code if single_layout else "",
        )
        for idx, card in enumerate(card_specs, start=1)
    ]
    more_nav_html = (
        _price_first_more_html(
            resolution=resolution,
            display_query=display_query,
            shown_cards=len(card_specs),
            source_page=source_page,
        )
        if price_first_page and resolution is not None and not single_layout
        else ""
    )

    if show_demo_note:
        # The provider feed is the only source of cards, so has_live_results implies
        # feed_results.
        page_note = _PRICE_FIRST_PAGE_NOTE if price_first_page else (
            "Selected real products from connected provider feed. Recommended from these 4."
        )
        if price_first_page and fit_words:
            page_note = page_note.replace(
                "cheapest first.", "those that say they fit your search first, then cheapest first.", 1
            )
        if price_first_page and any(card.get("offer") for card in card_specs):
            page_note = page_note.replace(
                "cheapest first.", "products on offer first, then cheapest first.", 1
            )
            page_note = f"{page_note} {_OFFERS_NOTE}"
        note_or_empty_html = f'<p class="pw-demo-note">&#9432; {escape(page_note)}</p>'
    elif is_home:
        note_or_empty_html = ""
    else:
        note_or_empty_html = (
            '<section class="pw-empty-state">PicWise safely shows no product cards until intent confidence '
            "and provider availability are both verified.</section>"
        )
    safe_note_html = f'<p class="pw-reference-disclaimer">{escape(safe_note_line)}</p>' if safe_note_line else ""
    kind_choices_html = (
        _kind_choices_html(resolution) if price_first_page and resolution is not None else ""
    )
    # The count above the cards, so that "4 of 45" is seen with them
    # (docs/LANDING_PAGE_SPEC.md, above the fold); the one under them goes with "More".
    results_count_html = (
        f'<p class="pw-results-count">{len(card_specs)} of {max(total_found, len(card_specs))}</p>'
        if price_first_page and card_specs
        else ""
    )
    hero_html = (
        '<section class="pw-hero-home">'
        f'<h1 class="pw-hero-title">{escape(_HOME_HEADING)}</h1>'
        "</section>"
        if is_home
        else ""
    )
    home_facts_html = _home_facts_html(catalogue) if is_home else ""
    home_after_search_html = render_trends_panel(load_trends_panel()) if is_home else ""
    # The AI layer's part: its checked sentence when the products that fit were put first,
    # the shops' words, or the empty place its script fills (owner, 2026-11-06).
    assist_html = (
        assist_block_html(
            AssistView(
                sentence=assist.sentence if fit_words else "",
                buttons=assist.buttons,
                pending_key=assist.pending_key,
            )
        )
        if assist is not None and price_first_page and card_specs
        else ""
    )
    results_html = (
        ""
        if is_home
        else (
            '<div class="pw-results-head">'
            # The page's heading when the search has an answer: what was searched and how
            # the answer is ordered. With none, the message under it is the page's answer.
            + (
                f'<h1 class="pw-query-line">{escape(query_line)}</h1>'
                if query_line
                else '<p class="pw-query-line"></p>'
            )
            + f"{results_count_html}"
            "</div>"
            f"{kind_choices_html}"
            f'<p class="pw-reference-disclaimer">{escape(disclaimer_line)}</p>'
            f"{safe_note_html}"
            f"{assist_html}"
            f'<section class="pw-grid" data-card-count="{len(card_html)}"'
            f'{" data-layout=" + chr(34) + "single" + chr(34) if single_layout else ""}>'
            f"{''.join(card_html)}"
            "</section>"
            f"{more_nav_html}"
        )
    )

    if assist is not None and results_html:
        # One place the page's script can put the answer's results in, drawing no box.
        results_html = f'<div class="pw-results" id="pw-results">{results_html}</div>'
    # A search's page is named after the search; the home page keeps the site's title.
    page_title = (not is_home and search_page_title(display_query)) or _HOME_TITLE
    html = (
        "<!doctype html>"
        f'<html lang="{SITE_LANGUAGE}"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{'' if indexable else NOINDEX_META}"
        f"<title>{escape(page_title)}</title>"
        # What PicWise does, in the owner's own words of 2026-10-17 ("What is PicWise?"),
        # for Google to show under the home page (owner, 2026-10-31: the pages true).
        f'<meta name="description" content="{escape(_WHAT_IS_PICWISE)}">'
        f"{icon_links_html()}"
        f"{FONT_PRELOAD_HTML}"
        # Only the page Google may index says where it lives; who publishes it, only once
        # the site declares itself to Google (`seo.DECLARE_TO_GOOGLE`, off: owner, 12/11).
        + (
            indexable_head_html("/", title=_HOME_TITLE, description=_WHAT_IS_PICWISE)
            + (home_structured_data_html() if declares_to_google() else "")
            if indexable and is_home
            else ""
        )
        + f"<script>{HEAD_SCRIPT}</script>"
        f"<style>{_PAGE_STYLES}{BROWSER_LISTS_STYLES}{TRENDS_STYLES if home_after_search_html else ''}"
        f"{ASSIST_STYLES if assist is not None else ''}</style>"
        "</head><body>"
        '<main class="pw-reference-viewport">'
        '<header class="pw-topbar">'
        '<div class="pw-topbar-inner">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">'
        '<span class="pw-logo" aria-hidden="true"></span>'
        '<span class="pw-brand-text"><span class="pw-brand-name">picwise</span></span>'
        "</a>"
        '<div class="pw-actions">'
        f"{header_buttons_html()}"
        '<section class="pw-info-wrap" id="pw-info-wrap"><button class="pw-topbar-control pw-info-link" id="pw-info-button" type="button" aria-label="What is PicWise?" aria-expanded="false" aria-controls="pw-tooltip"><span class="pw-info-txt">What is PicWise?</span><span class="pw-info-icon" aria-hidden="true">?</span></button><div class="pw-tooltip" id="pw-tooltip">'
        f"{escape(_WHAT_IS_PICWISE)}"
        "</div></section></div>"
        "</div>"
        "</header>"
        f"{panels_html()}"
        f'<div class="pw-reference-frame{" pw-home" if is_home else ""}" id="pw-reference-frame">'
        f"{hero_html}"
        '<section class="pw-search-wrap" aria-label="Search">'
        '<form class="pw-search-shell" action="/search" method="get" role="search">'
        '<span class="pw-search-icon" aria-hidden="true"></span>'
        '<span class="pw-input-wrap">'
        f'<input class="pw-search-input" type="search" name="q" value="{escape(display_query, quote=True)}" placeholder="{escape(_SEARCH_PLACEHOLDER, quote=True)}" aria-label="{escape(_SEARCH_PLACEHOLDER, quote=True)}" autocomplete="off" spellcheck="false" autocapitalize="off" enterkeyhint="search" role="combobox" aria-autocomplete="both" aria-controls="pw-suggest-list" aria-expanded="false">'
        '<span class="pw-ghost" aria-hidden="true"><span class="pw-ghost-typed" id="pw-ghost-typed"></span><span class="pw-ghost-rest" id="pw-ghost-rest"></span></span>'
        "</span>"
        f'<button class="pw-mic-button" id="pw-mic" type="button" aria-label="Search by voice" aria-pressed="false" title="{escape(_MIC_TITLE, quote=True)}" hidden>{_MIC_ICON}</button>'
        '<button class="pw-search-button" type="submit" aria-label="Search">'
        '<span class="pw-search-button-icon" aria-hidden="true"></span>'
        "</button></form>"
        '<ul class="pw-suggest" id="pw-suggest-list" role="listbox" aria-label="Suggestions" hidden></ul>'
        "</section>"
        f"{home_facts_html}"
        f"{home_after_search_html}"
        f"{results_html}"
        f"{note_or_empty_html}"
        "</div>"
        f"{render_public_footer()}"
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
        f"{_scanning_screen_html()}"
        f"<script>{_SEARCH_SCRIPT}</script>"
        f"<script>{BROWSER_LISTS_SCRIPT}</script>"
        f"{'<script>' + TRENDS_SCRIPT + '</script>' if home_after_search_html else ''}"
        f"{'<script>' + ASSIST_SCRIPT + '</script>' if assist is not None and assist.pending_key else ''}"
        "</main>"
        "</body></html>"
    )
    proof_text = "LIVE RENDERER " + "PROOF V1"
    proof_comment = "picwise-reference-live-renderer-" + "proof-v1"
    html = html.replace(proof_text, "")
    html = html.replace(f"<!-- {proof_comment} -->", "")
    return html
