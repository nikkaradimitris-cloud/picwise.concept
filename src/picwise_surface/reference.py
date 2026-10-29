from __future__ import annotations

from html import escape
from urllib.parse import quote

from picwise_providers.decision_labels import (
    build_fact_based_choice_labels,
    format_price_display,
    non_new_condition,
)
from picwise_search import LiveSearchResolution
from picwise_search.live_search_resolver import MAX_SHOWN_PRODUCTS
from .legal import render_public_footer
from .seo import NOINDEX_META


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
_PRICE_FIRST_SORTED = "Sorted by price, lowest first, from the shops connected to PicWise."
_PRICE_FIRST_FEED_NOTE = "Prices and stock are as the shops list them."
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
_PRICE_FIRST_PAGE_NOTE = "Real products from the shops' feeds, cheapest first."

# The search box (owner, 2026-10-17). "What are you looking for?" promises nothing a
# shop reviewing PicWise for its affiliate programme could object to; "What is
# PicWise?" says what price first does.
_SEARCH_PLACEHOLDER = "What are you looking for?"
_WHAT_IS_PICWISE = (
    "PicWise finds the product you want in the shops it is connected to, shows what the "
    "shops list as in stock, cheapest first, and marks one mid-priced Recommended."
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

# Step 4 (owner, 2026-10-16): the scanning screen, suggestions as the buyer types, and
# the microphone. Plain JavaScript, no library, and only additions: without it the box
# is a plain form and the search works as before (docs/LANDING_PAGE_SPEC.md).
# - The scanning screen shows on a search or on "More", with the counts the server
#   wrote into the page, and says nothing the browser cannot see happening.
# - The suggestions are fetched once, on the first focus, and matched in the browser.
# - The microphone shows only where the browser can listen; the search starts when
#   the buyer stops speaking (owner, 2026-10-17).
_SEARCH_SCRIPT = r"""
(function(){
"use strict";
var form=document.querySelector(".pw-search-shell");
if(!form){return;}
var input=form.querySelector(".pw-search-input");
var list=document.getElementById("pw-suggest-list");
var ghostTyped=document.getElementById("pw-ghost-typed");
var ghostRest=document.getElementById("pw-ghost-rest");
var scan=document.getElementById("pw-scan");
var scanText=document.getElementById("pw-scan-text");
var mic=document.getElementById("pw-mic");
if(!input||!list||!ghostTyped||!ghostRest){return;}
function scanFor(q){
  if(!scan||!scanText||!q){return;}
  var products=scan.getAttribute("data-products");
  var shops=scan.getAttribute("data-shops");
  var quoted="\u201c"+q+"\u201d";
  scanText.textContent=(products&&shops)
    ?"Searching "+products+(products==="1"?" product":" products")+" from "+shops+(shops==="1"?" shop":" shops")+" for "+quoted+"\u2026"
    :"Searching the shops connected to PicWise for "+quoted+"\u2026";
  scan.hidden=false;
}
window.addEventListener("pageshow",function(){if(scan){scan.hidden=true;}});
form.addEventListener("submit",function(){
  var q=input.value.trim();
  closeList();
  if(q){scanFor(q);}
});
var more=document.querySelector(".pw-more-button");
if(more){more.addEventListener("click",function(){scanFor(input.defaultValue.trim());});}
function norm(s){
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase()
    .replace(/\u03c2/g,"\u03c3").replace(/\s+/g," ");
}
var words=null,keys=null,loading=false,shown=[],active=-1;
function load(){
  if(words||loading||!window.fetch){return;}
  loading=true;
  fetch("/suggest.json").then(function(r){return r.ok?r.json():{};}).then(function(d){
    words=(d&&d.suggestions)||[];
    keys=words.map(norm);
    if(document.activeElement===input){update();}
  }).catch(function(){words=[];keys=[];});
}
function setGhost(typed,rest){
  ghostTyped.textContent=typed;
  ghostRest.textContent=rest;
}
function closeList(){
  list.hidden=true;
  list.textContent="";
  shown=[];
  active=-1;
  input.setAttribute("aria-expanded","false");
  input.removeAttribute("aria-activedescendant");
}
function update(){
  var raw=input.value;
  var q=norm(raw).replace(/^ /,"");
  setGhost("","");
  if(!words||!q.trim()){closeList();return;}
  var starts=[],inner=[];
  for(var i=0;i<words.length&&starts.length<8;i++){
    if(keys[i].indexOf(q)===0){starts.push(i);}
    else if(inner.length<8&&keys[i].indexOf(" "+q)>=0){inner.push(i);}
  }
  shown=starts.concat(inner).slice(0,8);
  if(!shown.length){closeList();return;}
  list.textContent="";
  shown.forEach(function(index,pos){
    var item=document.createElement("li");
    item.id="pw-suggest-"+pos;
    item.className="pw-suggest-item";
    item.setAttribute("role","option");
    item.setAttribute("aria-selected","false");
    item.textContent=words[index];
    item.addEventListener("mousedown",function(e){e.preventDefault();});
    item.addEventListener("click",function(){choose(words[index]);});
    list.appendChild(item);
  });
  active=-1;
  list.hidden=false;
  input.setAttribute("aria-expanded","true");
  if(starts.length&&raw.charAt(0)!==" "&&input.selectionStart===raw.length){
    setGhost(raw,words[starts[0]].slice(raw.length));
  }
}
function accept(){
  var rest=ghostRest.textContent;
  if(!rest){return false;}
  input.value=input.value+rest;
  update();
  return true;
}
function choose(text){
  input.value=text;
  closeList();
  setGhost("","");
  if(form.requestSubmit){form.requestSubmit();}else{scanFor(text);form.submit();}
}
input.addEventListener("focus",load);
input.addEventListener("input",update);
input.addEventListener("blur",function(){setTimeout(closeList,150);setGhost("","");});
input.addEventListener("keydown",function(e){
  if(e.key==="ArrowDown"||e.key==="ArrowUp"){
    if(!shown.length){return;}
    e.preventDefault();
    active=e.key==="ArrowDown"?(active+1)%shown.length:(active<=0?shown.length-1:active-1);
    Array.prototype.forEach.call(list.children,function(item,pos){
      item.classList.toggle("is-active",pos===active);
      item.setAttribute("aria-selected",pos===active?"true":"false");
    });
    input.setAttribute("aria-activedescendant","pw-suggest-"+active);
  }else if(e.key==="Enter"&&active>=0){
    e.preventDefault();
    choose(words[shown[active]]);
  }else if(e.key==="Escape"){
    closeList();
    setGhost("","");
  }else if((e.key==="Tab"&&!e.shiftKey)||e.key==="ArrowRight"){
    if(input.selectionStart===input.value.length&&ghostRest.textContent){
      e.preventDefault();
      accept();
    }
  }
});
ghostRest.addEventListener("mousedown",function(e){e.preventDefault();accept();});
var Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
if(mic&&Recognition){
  mic.hidden=false;
  var recognition=null;
  var resting=input.getAttribute("placeholder");
  var stopListening=function(){
    recognition=null;
    mic.classList.remove("is-listening");
    mic.setAttribute("aria-pressed","false");
    input.setAttribute("placeholder",resting);
  };
  mic.addEventListener("click",function(){
    if(recognition){recognition.stop();return;}
    var heard="";
    recognition=new Recognition();
    recognition.lang=navigator.language||"en-GB";
    recognition.interimResults=true;
    recognition.maxAlternatives=1;
    recognition.onresult=function(e){
      var spoken="";
      heard="";
      for(var i=0;i<e.results.length;i++){
        if(e.results[i].isFinal){heard+=e.results[i][0].transcript;}
        else{spoken+=e.results[i][0].transcript;}
      }
      input.value=(heard+spoken).trim();
    };
    recognition.onerror=function(){heard="";};
    recognition.onend=function(){
      stopListening();
      var q=heard.trim();
      if(q){choose(q);}
    };
    closeList();
    setGhost("","");
    mic.classList.add("is-listening");
    mic.setAttribute("aria-pressed","true");
    input.setAttribute("placeholder","Listening\u2026");
    try{recognition.start();}catch(err){stopListening();}
  });
}
})();
"""


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


def _scanning_screen_html(catalogue: tuple[int, int] | None) -> str:
    """The scanning screen, hidden until a search starts (`_SEARCH_SCRIPT`).

    It carries the counts as the server last loaded them: the products a search looks
    through and the shops they come from. Without them it names no number.
    """
    counts = ""
    if catalogue and catalogue[0] > 0 and catalogue[1] > 0:
        products, shops = catalogue
        counts = f' data-products="{products:,}" data-shops="{shops:,}"'
    return (
        f'<div class="pw-scan" id="pw-scan" role="status" aria-live="polite"{counts} hidden>'
        '<div class="pw-scan-card"><span class="pw-scan-dot" aria-hidden="true"></span>'
        '<p class="pw-scan-text" id="pw-scan-text"></p></div></div>'
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


def _build_price_first_cards(
    *,
    resolution: LiveSearchResolution,
    source_page: str = "search",
) -> list[dict[str, object]]:
    """The cards of a price-first answer, in the order shown.

    The first page holds the Recommended, when there is one, and then the cheapest;
    after it come the products "More" has opened. Only the Recommended carries a
    recommendation: nothing "More" opens is recommended (owner, 2026-10-15), and every
    other click is tracked with `rec=0`.
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
    cards: list[dict[str, object]] = []
    for index, product in enumerate(products):
        label = labels[index] if index < len(labels) else None
        product_id = str(product.get("provider_product_id") or "").strip()
        is_recommended = index == 0 and bool(recommended_id) and product_id == recommended_id
        shop_count = int(shops.get(product_id, 1) or 1)
        shops_label = (
            _PRICE_FIRST_SHOPS_LABEL.format(shops=shop_count) if shop_count > 1 else ""
        )
        if is_recommended:
            role_label = _PRICE_FIRST_RECOMMENDED_LABEL
        elif product_id in cheapest:
            role_label = shops_label or _PRICE_FIRST_LOWEST_LABEL
        else:
            # A dearer product on a short first page, or one "More" opened: it is not
            # the lowest price of the answer, only of the shops selling it.
            role_label = shops_label
        # The price is on the card in large type; the reasons say what else is known.
        bullets = [
            reason
            for reason in (label.key_reasons if label else ())
            if not reason.startswith("Feed price:")
        ]
        if is_recommended and shops_label:
            bullets.append(shops_label)
        store_label = _provider_store_label(
            str(product.get("provider_key") or "").strip(),
            str(product.get("merchant_name") or ""),
        )
        cards.append(
            {
                "badge": "REAL FEED",
                "badge_class": "pw-badge-value",
                "name": str(product.get("title") or "").strip(),
                "role_label": role_label,
                "choice_id": product_id,
                "anchor_id": f"pw-choice-{index + 1}",
                "description": _price_place_line(
                    places.get(product_id), total, condition=non_new_condition(product)
                ),
                "rating": "",
                "reviews": "",
                "price": format_price_display(product),
                "meta": _provider_feed_card_meta(product, store_label=store_label),
                "bullets": bullets,
                "warning": label.risk_or_limitation if label else "",
                "cta": "View in Store",
                "image": str(product.get("image_url") or "").strip(),
                "recommended": is_recommended,
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


def _render_choice_card(card: dict[str, object], idx: int) -> str:
    """One choice card's HTML. Used for the four and for the second four alike,
    so a card behind "see more" cannot drift from a card in front of it."""
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
    role_label_html = (
        f'<p class="pw-role-label">{escape(str(card.get("role_label")))}</p>'
        if str(card.get("role_label") or "")
        else ""
    )
    cta = (
        f'<a class="pw-card-cta pw-card-cta-link" href="{escape(str(card["href"]), quote=True)}" rel="nofollow sponsored noopener">{escape(str(card["cta"]))}</a>'
        if card.get("href")
        else f'<button class="pw-card-cta" type="submit">{escape(str(card["cta"]))}</button>'
    )
    # Where "More" opens the page: the first card it added.
    anchor = (
        f'<span class="pw-anchor" id="{escape(str(card["anchor_id"]), quote=True)}"></span>'
        if card.get("anchor_id")
        else ""
    )
    return (
        f'<article class="pw-card{rec_class}" data-choice-id="{escape(str(card.get("choice_id") or f"fixed-{idx}"), quote=True)}">'
        f"{anchor}"
        f"{rec_header}"
        f'<span class="pw-badge {escape(str(card["badge_class"]), quote=True)}">{escape(str(card["badge"]))}</span>'
        f"{role_label_html}"
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
) -> str:
    """The search page. `catalogue` is (products, shops) a search reads, when the server
    has the feed loaded, for the scanning screen; None makes it name no number.

    Only the home page without a search is `indexable`. Every other page this draws is
    the site's own search, which Google is told not to index (owner, 2026-10-23: «βάλε
    το noindex στο /search και προστάτεψε το site από την google όσο το χτίζουμε»);
    the pages meant for Google are in `docs/PICWISE_GOOGLE_PAGES_SPEC.md`.
    """
    display_query = str(query or "")
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
            )
            if price_first_cards:
                card_specs = price_first_cards
                has_live_results = True
                feed_results = True
                price_first_page = True
                disclosure = _PRICE_FIRST_DISCLOSURES[
                    str(resolution.provider_feed_decision_status)
                ]
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
                query_line = f"Results for: {display_query}, cheapest first"
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

    card_html = [_render_choice_card(card, idx) for idx, card in enumerate(card_specs, start=1)]
    more_nav_html = (
        _price_first_more_html(
            resolution=resolution,
            display_query=display_query,
            shown_cards=len(card_specs),
            source_page=source_page,
        )
        if price_first_page and resolution is not None
        else ""
    )

    if show_demo_note:
        # The provider feed is the only source of cards, so has_live_results implies
        # feed_results.
        page_note = _PRICE_FIRST_PAGE_NOTE if price_first_page else (
            "Selected real products from connected provider feed. Recommended from these 4."
        )
        note_or_empty_html = f'<p class="pw-demo-note">&#9432; {escape(page_note)}</p>'
    else:
        note_or_empty_html = (
            '<section class="pw-empty-state">PicWise safely shows no product cards until intent confidence '
            "and provider availability are both verified.</section>"
        )
    safe_note_html = f'<p class="pw-reference-disclaimer">{escape(safe_note_line)}</p>' if safe_note_line else ""
    kind_choices_html = (
        _kind_choices_html(resolution) if price_first_page and resolution is not None else ""
    )

    html = (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{'' if indexable else NOINDEX_META}"
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
        ".pw-role-label{margin:6px 0 0;font-size:12px;font-weight:700;letter-spacing:.01em;color:#1a4fb7;line-height:1.3;}"
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
        ".pw-more{display:flex;flex-direction:column;align-items:center;gap:10px;width:100%;max-width:1190px;margin:24px auto 0;}"
        ".pw-kind-choices{display:flex;flex-wrap:wrap;align-items:center;gap:8px;width:100%;max-width:760px;margin:-28px auto 28px;}"
        ".pw-kind-choices-ask{font-size:15px;font-weight:600;color:#1a3d6b;margin-right:4px;}"
        ".pw-kind-choice{display:inline-flex;align-items:center;height:32px;padding:0 13px;border-radius:999px;border:1px solid #ccdbf2;background:#fff;color:#1d3a63;font-size:14px;font-weight:600;text-decoration:none;}"
        ".pw-kind-choice:hover{background:#eef4ff;}"
        ".pw-kind-choice:focus-visible{outline:2px solid #2a6deb;outline-offset:3px;}"
        ".pw-counter{margin:0;font-size:14px;font-weight:600;color:#3c5f8a;}"
        ".pw-more-button{display:inline-flex;align-items:center;justify-content:center;height:42px;padding:0 30px;border-radius:999px;background:#1f6dff;color:#fff;font-size:15px;font-weight:700;text-decoration:none;}"
        ".pw-more-button:focus-visible{outline:2px solid #2a6deb;outline-offset:3px;}"
        ".pw-search-wrap{position:relative;}"
        ".pw-input-wrap{position:relative;flex:1;display:flex;align-items:center;min-width:0;height:100%;}"
        ".pw-input-wrap .pw-search-input{width:100%;padding:0;font-family:inherit;letter-spacing:normal;}"
        ".pw-ghost{position:absolute;left:0;top:0;bottom:0;display:flex;align-items:center;font-family:inherit;font-size:19px;font-weight:500;letter-spacing:normal;white-space:pre;overflow:hidden;pointer-events:none;max-width:100%;}"
        ".pw-ghost-typed{visibility:hidden;}"
        ".pw-ghost-rest{color:#bccbe0;pointer-events:auto;cursor:pointer;}"
        ".pw-mic-button{width:42px;height:42px;border-radius:999px;border:1px solid #dbe8fb;background:#fff;color:#4f6f9c;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;flex:0 0 auto;padding:0;}"
        ".pw-mic-button[hidden]{display:none;}"
        ".pw-mic-button.is-listening{background:#ffecec;border-color:#f0b3b3;color:#c43c3c;}"
        ".pw-mic-button:focus-visible{outline:2px solid #2a6deb;outline-offset:3px;}"
        ".pw-suggest{position:absolute;left:0;right:0;top:calc(100% + 6px);margin:0;padding:6px 0;list-style:none;background:#fff;border:1px solid #dbe8fb;border-radius:16px;z-index:5;text-align:left;}"
        ".pw-suggest[hidden]{display:none;}"
        ".pw-suggest-item{padding:9px 18px;font-size:16px;color:#112849;cursor:pointer;}"
        ".pw-suggest-item.is-active,.pw-suggest-item:hover{background:#eef4ff;}"
        ".pw-scan{position:fixed;top:0;right:0;bottom:0;left:0;background:rgba(248,251,255,.94);display:flex;align-items:flex-start;justify-content:center;padding:22vh 16px 0;z-index:20;}"
        ".pw-scan[hidden]{display:none;}"
        ".pw-scan-card{display:flex;align-items:center;gap:12px;background:#fff;border:1px solid #dbe8fb;border-radius:16px;padding:16px 20px;max-width:560px;}"
        ".pw-scan-dot{width:12px;height:12px;border-radius:999px;background:#1f6dff;flex:0 0 auto;animation:pw-pulse 1s ease-in-out infinite alternate;}"
        "@keyframes pw-pulse{from{opacity:.35;}to{opacity:1;}}"
        ".pw-scan-text{margin:0;font-size:16px;color:#112849;line-height:1.45;}"
        "@media (prefers-reduced-motion:reduce){.pw-scan-dot{animation:none;}}"
        "@media (max-width:1099px){.pw-grid{grid-template-columns:repeat(2,minmax(0,1fr));max-width:760px;}.pw-topbar{height:auto;gap:10px;}}"
        "@media (max-width:640px){.pw-grid{grid-template-columns:1fr;max-width:420px;}}"
        "@media (max-width:699px){.pw-reference-frame{padding:14px 12px 20px;}.pw-topbar{flex-direction:column;align-items:center;margin-bottom:20px;}.pw-actions{width:100%;justify-content:center;gap:8px;}.pw-brand-wrap{margin:0 0 24px;}.pw-brand-name{font-size:33px;}.pw-search-wrap{height:auto;}.pw-search-shell{height:52px;padding:0 8px 0 14px;}.pw-search-input{height:50px;font-size:16px;}.pw-ghost{font-size:16px;}.pw-mic-button{width:38px;height:38px;}.pw-query-line{font-size:14px;margin:0 auto 36px;}.pw-grid{grid-template-columns:1fr;max-width:360px;}.pw-card{max-width:360px;}.pw-tooltip{width:min(430px,calc(100% - 8px));}}"
        ".pw-reference-viewport *,.pw-reference-viewport *::before,.pw-reference-viewport *::after{box-shadow:none!important;text-shadow:none!important;filter:none!important;}"
        "</style></head><body>"
        '<main class="pw-reference-viewport">'
        '<div class="pw-reference-scale-shell" id="pw-reference-scale-shell">'
        '<div class="pw-reference-frame" id="pw-reference-frame">'
        '<header class="pw-topbar">'
        '<div class="pw-actions"><button class="pw-topbar-control pw-login-btn" type="button">Login</button><a class="pw-topbar-control pw-register" href="#">Register</a><section class="pw-info-wrap" id="pw-info-wrap"><button class="pw-topbar-control pw-info-link" id="pw-info-button" type="button" aria-label="What is PicWise?" aria-expanded="false" aria-controls="pw-tooltip">What is PicWise?</button><div class="pw-tooltip" id="pw-tooltip">'
        f"{escape(_WHAT_IS_PICWISE)}"
        '</div></section></div>'
        "</header>"
        '<section class="pw-brand-wrap" aria-label="PicWise brand">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">'
        '<span class="pw-logo" aria-hidden="true"></span>'
        '<span class="pw-brand-text"><span class="pw-brand-name">picwise</span><span class="pw-brand-tagline">shopping decision assistant</span></span>'
        "</a>"
        "</section>"
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
        f'<p class="pw-query-line">{escape(query_line)}</p>'
        f"{kind_choices_html}"
        f'<p class="pw-reference-disclaimer">{escape(disclaimer_line)}</p>'
        f"{safe_note_html}"
        f'<section class="pw-grid" data-card-count="{len(card_html)}">'
        f"{''.join(card_html)}"
        "</section>"
        f"{more_nav_html}"
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
        f"{_scanning_screen_html(catalogue)}"
        f"<script>{_SEARCH_SCRIPT}</script>"
        "</main>"
        "</body></html>"
    )
    proof_text = "LIVE RENDERER " + "PROOF V1"
    proof_comment = "picwise-reference-live-renderer-" + "proof-v1"
    html = html.replace(proof_text, "")
    html = html.replace(f"<!-- {proof_comment} -->", "")
    return html
