"""The store's pages other than the home page (`docs/PICWISE_HOME_STORE_SPEC.md`, section 7;
task H4): built behind the home page's switch (`home_store.home_store_on`), each drawn only
once it is in `home_store.PARTS_BUILT`.

The owner decided them on 2026-11-24 («Ναι σε όλα»), to the pictures on his canvas, which
`tools/draw_store_pages.py` draws again: their words and look are this module's reference.

- Part B, the departments (7.1): `/departments`, all of them in four groups; and
  `/department/<name>`, a department's kinds, their Recommended, every kind as a row. A
  department of one kind has no page: it leads to that kind's search.
- Part D, the four pages (7.3): "How PicWise works", "How we choose the Recommended",
  "Our checks", word for word as approved; "Our shops", every shop with a product shown
  tonight, A to Z. **"Our checks" says what the checks do on the day it goes live: each of
  its sentences is read against the server before the «ανέβασε» (the specification, 9).**

- Part C, the offers (7.2): `/offers`, every offer covering products shown tonight, a
  shop after another, in the shop's own words; `/offers/<id>`, an offer: to its kind's
  products when it covers one kind, else "Which kind are you looking for?"; and an
  offer's products, the search's own page narrowed to the shop's products it covers
  (`?offer=<id>`): no Recommended, no "Lowest price", no place among the prices, the offer
  once above the cards, a link to the kind in every shop.

- Part F, the other pages (7.4): the search's page and the info pages under the store's
  header (without the departments' row) and over its footer, on its ground; on the
  search's page two colours a little darker, so that they read (5.12).

Every page is kept out of Google (`noindex`): nothing of the store is declared (section 2).
What a page knows of the catalogue is worked out once a night (`home_store_facts`), never
while it is drawn; what is not known yet is left out, never filled.
"""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from html import escape
from html import unescape as html_unescape
from itertools import groupby
from typing import Any
from urllib.parse import quote

from . import home_store as hs
from .home_store_facts import DepartmentsFacts, KindFacts, current_home_facts, current_kind_facts
from .home_store import Department, DeptKind, HomeFacts, OfferCard, Pick

DEPARTMENTS_TITLE = "All departments"
DEPARTMENTS_LINE = "From UK shops, in stock only."
DEPARTMENT_EYEBROW = "DEPARTMENT"
KINDS_TITLE = "All kinds in {name}"
KIND_META = "{count} products from {low}"
KIND_META_ONE = "1 product from {low}"
# The band of a department: its kinds' Recommended, the most products first, 8 at most.
BAND_MOST = 8

_CHEVRON = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>'
)

STORE_PAGES_STYLES = (
    ".pw-hs-page-head{padding:18px 16px 4px;}"
    ".pw-hs-page-head .pw-hs-h1{margin:6px 0 0;}"
    ".pw-hs-page-line{margin:8px 0 0;font-size:15px;line-height:1.45;color:var(--hs-muted);}"
    ".pw-hs-crumb{display:inline-flex;align-items:center;min-height:48px;margin:0 0 -8px;color:var(--hs-acc);font-size:14px;font-weight:700;text-decoration:none;}"
    ".pw-hs-tile-meta{margin-top:-4px;font-size:13px;line-height:1.3;color:var(--hs-muted);}"
    ".pw-hs-kinds{padding:12px 16px 0;}"
    ".pw-hs-kinds .pw-hs-grid{margin-top:0;}"
    ".pw-hs-list{margin-top:12px;padding:14px 16px 6px;background:#fff;}"
    ".pw-hs-rows{list-style:none;margin:12px 0 0;padding:0 0 10px;display:flex;flex-direction:column;gap:8px;}"
    ".pw-hs-row{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:56px;padding:6px 14px;border-radius:14px;background:var(--hs-cream);text-decoration:none;color:var(--hs-ink);}"
    ".pw-hs-row-text{display:flex;flex-direction:column;gap:2px;min-width:0;}"
    ".pw-hs-row-name{font-size:15px;line-height:1.25;font-weight:600;}"
    ".pw-hs-row-meta{font-size:13px;line-height:1.3;color:var(--hs-muted);}"
    ".pw-hs-row svg{flex:0 0 auto;color:var(--hs-muted);}"
    ".pw-hs-group{padding:20px 16px 0;scroll-margin-top:12px;}"
    ".pw-hs-group-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 12px;margin-top:12px;}"
    ".pw-hs-group .pw-hs-dept{flex:none;}"
    ".pw-hs-group .pw-hs-dept-pic{height:auto;aspect-ratio:1/1;}"
    ".pw-hs-group .pw-hs-art{width:82%;height:auto;}"
    # the four pages
    ".pw-hs-doc{margin:16px 16px 0;padding:22px 18px 14px;border-radius:20px;background:#fff;border:1px solid var(--hs-line);}"
    ".pw-hs-doc .pw-hs-h1{margin:6px 0 0;font-size:26px;}"
    ".pw-hs-doc-intro{margin:12px 0 0;font-size:16px;line-height:1.55;color:var(--hs-ink);}"
    ".pw-hs-doc h2{margin:22px 0 0;font-size:18px;line-height:1.25;font-weight:800;letter-spacing:-.2px;color:var(--hs-ink);}"
    ".pw-hs-doc p{margin:8px 0 0;font-size:15px;line-height:1.6;color:#33425c;}"
    ".pw-hs-doc ul{margin:8px 0 0;padding:0 0 0 20px;color:#33425c;}"
    ".pw-hs-doc li{margin:6px 0 0;font-size:15px;line-height:1.55;}"
    ".pw-hs-doc-step{display:flex;align-items:center;gap:10px;}"
    ".pw-hs-doc-updated{margin:18px 0 0;font-size:13px;color:var(--hs-muted);}"
    ".pw-hs-doc .pw-hs-shoplist{list-style:none;margin:6px 0 0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 16px;}"
    ".pw-hs-doc .pw-hs-shoplist li{margin:0;padding:8px 0;font-size:14px;line-height:1.3;color:var(--hs-ink);border-top:1px solid var(--hs-line);}"
    ".pw-hs-letter{margin:18px 0 0;font-size:14px;font-weight:800;letter-spacing:.08em;color:var(--hs-acc);}"
    # the offers
    ".pw-hs-shopblock{margin:12px 16px 0;padding:16px 16px 4px;border-radius:18px;background:#fff;border:1px solid var(--hs-line);}"
    ".pw-hs-shopblock-name{margin:0;font-size:18px;line-height:1.2;font-weight:800;color:var(--hs-ink);}"
    ".pw-hs-of{padding:12px 0 4px;border-top:1px solid var(--hs-line);margin-top:12px;}"
    ".pw-hs-of-title{margin:0;font-size:15px;line-height:1.35;font-weight:700;color:var(--hs-ink);}"
    ".pw-hs-of-meta{margin:4px 0 0;font-size:13px;line-height:1.4;color:var(--hs-muted);}"
    ".pw-hs-of-code{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;letter-spacing:.04em;color:var(--hs-ink);}"
    ".pw-hs-of-terms{margin:0;font-size:13px;color:var(--hs-muted);}"
    ".pw-hs-of-terms summary{display:flex;align-items:center;min-height:48px;cursor:pointer;color:var(--hs-acc);font-weight:600;}"
    ".pw-hs-of-terms p{margin:0 0 8px;line-height:1.5;}"
    ".pw-hs-offerbox{margin:12px 16px 0;padding:14px 16px 6px;border-radius:18px;background:var(--hs-pale);}"
    ".pw-hs-offerbox .pw-hs-eyebrow{color:#5c4300;}"
    ".pw-hs-offerbox .pw-hs-of-title{margin-top:6px;font-size:17px;}"
    ".pw-hs-offerbox .pw-hs-of-meta{color:#5c4300;}"
    ".pw-hs-offerbox .pw-hs-of-terms summary{color:#5c4300;}"
    ".pw-hs-oneshop{margin:0 0 12px;font-size:14px;line-height:1.45;}"
    ".pw-hs-oneshop a{display:flex;align-items:center;min-height:48px;color:var(--hs-acc);font-weight:700;text-decoration:none;}"
    ".pw-reference-frame .pw-hs-offerbox{margin:0 0 14px;}"
    ".pw-hs-note{margin:16px 16px 0;font-size:13px;line-height:1.5;color:var(--hs-muted);}"
    "@media (min-width:700px){"
    ".pw-hs-shopblock,.pw-hs-offerbox,.pw-hs-note{margin-left:0;margin-right:0;}"
    ".pw-hs-doc{max-width:760px;margin:32px auto 0;padding:32px 36px 22px;}"
    ".pw-hs-doc .pw-hs-shoplist{grid-template-columns:repeat(3,minmax(0,1fr));}"
    ".pw-hs-page-head{padding:32px 0 8px;}"
    ".pw-hs-kinds{padding:16px 0 0;}"
    ".pw-hs-list{margin-top:20px;border-radius:20px;padding:20px 20px 10px;}"
    ".pw-hs-rows{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 12px;}"
    ".pw-hs-group{padding:26px 0 0;}"
    ".pw-hs-group-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:18px 16px;}"
    "}"
)


def _kind_meta(fact: KindFacts | None) -> str:
    if fact is None or fact.count <= 0 or not fact.low:
        return ""
    if fact.count == 1:
        return KIND_META_ONE.format(low=fact.low)
    return KIND_META.format(count=f"{fact.count:,}", low=fact.low)


def department(slug: str) -> Department | None:
    """A department with a page of its own: on the home page's list, with more than one
    kind (a department of one kind leads to that kind's search)."""
    item = next((d for d in hs.load_home_lists().departments if d.slug == slug), None)
    if item is None or len(hs.load_departments().kinds.get(slug, ())) < 2:
        return None
    return item


def _shown_kinds(slug: str, facts: DepartmentsFacts | None) -> tuple[tuple[DeptKind, KindFacts | None], ...]:
    """A department's kinds: those with products tonight, the most first; all of them, in
    the file's order and with no numbers, while tonight's are not known."""
    kinds = hs.load_departments().kinds.get(slug, ())
    if facts is None:
        return tuple((kind, None) for kind in kinds)
    shown = [(kind, facts.kinds[kind.query]) for kind in kinds if kind.query in facts.kinds]
    order = {kind.query: index for index, kind in enumerate(kinds)}
    shown.sort(key=lambda pair: (-pair[1].count, order[pair[0].query]))
    return tuple(shown)


def render_department_page(slug: str, *, facts: DepartmentsFacts | None | Any = ..., parts: frozenset[str] | None = None) -> str | None:
    """A department's page, or None when it has none."""
    item = department(slug)
    if item is None:
        return None
    facts = current_kind_facts() if facts is ... else facts
    kinds = _shown_kinds(slug, facts)
    tiles = "".join(
        f'<a class="pw-hs-tile" href="{hs._search_href(kind.query)}">'
        f'<span class="pw-hs-tile-pic pw-hs-sand">{hs._background("soft")}{hs._drawing(kind.drawing, 144)}</span>'
        f'<span class="pw-hs-tile-name">{escape(kind.name)}</span>'
        + (f'<span class="pw-hs-tile-meta">{escape(_kind_meta(fact))}</span>' if _kind_meta(fact) else "")
        + "</a>"
        for kind, fact in kinds
        if kind.drawing
    )
    picks = tuple(fact.pick for _kind, fact in kinds if fact is not None and fact.pick is not None)[:BAND_MOST]
    band = hs._band_html(HomeFacts(prepared_at=facts.prepared_at, picks=picks), hs.PARTS_BUILT if parts is None else parts) if facts else ""
    rows = "".join(
        f'<li><a class="pw-hs-row" href="{hs._search_href(kind.query)}"><span class="pw-hs-row-text">'
        f'<span class="pw-hs-row-name">{escape(kind.name)}</span>'
        + (f'<span class="pw-hs-row-meta">{escape(_kind_meta(fact))}</span>' if _kind_meta(fact) else "")
        + f"</span>{_CHEVRON}</a></li>"
        for kind, fact in kinds
    )
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        f'<p class="pw-hs-eyebrow">{escape(DEPARTMENT_EYEBROW)}</p>'
        f'<h1 class="pw-hs-h1" id="pw-hs-h1">{escape(item.name)}</h1>'
        f'<p class="pw-hs-page-line">{escape(DEPARTMENTS_LINE)}</p></section>'
        + (f'<section class="pw-hs-kinds" aria-label="{escape(item.name, quote=True)}"><div class="pw-hs-grid">{tiles}</div></section>' if tiles else "")
        + band
        + (
            '<section class="pw-hs-list" aria-labelledby="pw-hs-all">'
            f'<h2 class="pw-hs-h2" id="pw-hs-all">{escape(KINDS_TITLE.format(name=item.name))}</h2>'
            f'<ul class="pw-hs-rows">{rows}</ul></section>'
            if rows
            else ""
        )
    )
    return hs.render_store_page(
        title=f"{item.name} — PicWise", main_html=main, styles=STORE_PAGES_STYLES, nav_row=True, current=slug, parts=parts
    )


def render_departments_page(*, parts: frozenset[str] | None = None) -> str:
    """All departments, in their four groups (the specification, 7.1)."""
    by_slug = {d.slug: d for d in hs.load_home_lists().departments}
    groups = ""
    for group in hs.load_departments().groups:
        tiles = "".join(
            f'<a class="pw-hs-dept" href="{hs._department_href(slug)}">'
            f'<span class="pw-hs-dept-pic pw-hs-mist">{hs._background("soft")}{hs._drawing(by_slug[slug].drawing, 96)}</span>'
            f'<span class="pw-hs-dept-name">{escape(by_slug[slug].name)}</span></a>'
            for slug in group.departments
            if slug in by_slug
        )
        if tiles:
            groups += (
                f'<section class="pw-hs-group" id="{escape(group.gid, quote=True)}" aria-labelledby="g-{escape(group.gid, quote=True)}">'
                f'<h2 class="pw-hs-h2" id="g-{escape(group.gid, quote=True)}">{escape(group.name)}</h2>'
                f'<div class="pw-hs-group-grid">{tiles}</div></section>'
            )
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        f'<h1 class="pw-hs-h1" id="pw-hs-h1">{escape(DEPARTMENTS_TITLE)}</h1>'
        f'<p class="pw-hs-page-line">{escape(DEPARTMENTS_LINE)}</p></section>'
        f"{groups}"
    )
    return hs.render_store_page(
        title=f"{DEPARTMENTS_TITLE} — PicWise", main_html=main, styles=STORE_PAGES_STYLES, nav_row=True, parts=parts
    )


# ---- Part D: the four pages, word for word as the owner approved them (2026-11-24) ----
PAGES_EYEBROW = "ABOUT PICWISE"
PAGES_UPDATED = "Last updated: 24 November 2026"


def _doc(title: str, intro: str, body: str, *, parts: frozenset[str] | None) -> str:
    main = (
        '<article class="pw-hs-doc" aria-labelledby="pw-hs-h1">'
        f'<p class="pw-hs-eyebrow">{escape(PAGES_EYEBROW)}</p>'
        f'<h1 class="pw-hs-h1" id="pw-hs-h1">{escape(title)}</h1>'
        f'<p class="pw-hs-doc-intro">{escape(intro)}</p>{body}'
        f'<p class="pw-hs-doc-updated">{escape(PAGES_UPDATED)}</p>'
        "</article>"
    )
    return hs.render_store_page(title=f"{title} — PicWise", main_html=main, styles=STORE_PAGES_STYLES, parts=parts)


def _step(number: str, name: str, *, gold: bool = False) -> str:
    cls = "pw-hs-step-n pw-hs-step-n-gold" if gold else "pw-hs-step-n"
    return f'<h2 class="pw-hs-doc-step"><span class="{cls}">{number}</span>{escape(name)}</h2>'


def _p(text: str) -> str:
    return f"<p>{escape(text)}</p>"


def _ul(*items: str) -> str:
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _go(href: str, label: str) -> str:
    """A link on a line of its own, 48 px to tap, never inside a sentence."""
    return hs._link(href, label)


def render_how_picwise_works_page(*, parts: frozenset[str] | None = None) -> str:
    body = (
        _step("1", "Search")
        + _p("Type the product you want, or pick a department. PicWise shows only that kind of product: a search for a "
             "coffee machine shows coffee machines, not filters for coffee machines.")
        + _step("2", "See")
        + _p("Four choices, cheapest first, each at the shop's own price: its sale price where the shop gives one. Only what "
             "the shop lists as in stock. \u201cMore\u201d opens the next four, as often as you ask.")
        + _p("An offer is the shop's own, shown in its words with its end date. PicWise works out no price after it.")
        + _step("3", "Decide", gold=True)
        + _p("One of the four is marked Recommended: the product in the middle of the prices, so neither the cheapest nor "
             "the dearest decides it.")
        + _go(hs.PART_ADDRESSES["how_we_choose"], "How we choose the Recommended")
        + _p("The button then takes you to the shop. PicWise is not a shop: every purchase is made on the shop's own "
             "website, under the shop's terms.")
        + "<h2>Where prices and stock come from</h2>"
        + _p("From the shops' own product feeds, received through the Awin affiliate network and read again every night. "
             "PicWise also checks products on the shops' own websites.")
        + _go(hs.PART_ADDRESSES["our_checks"], "Our checks")
        + "<h2>How PicWise earns</h2>"
        + _p("A commission from some shops, through Awin, when you buy after following a PicWise link. The price you pay is "
             "the same, and the commission never changes the order.")
        + _go("/affiliate-disclosure", "Affiliate disclosure")
    )
    intro = ("PicWise is a product search for shoppers in the United Kingdom who already know what they want to buy. "
             "It works in three steps.")
    return _doc("How PicWise works", intro, body, parts=parts)


def render_how_we_choose_page(*, parts: frozenset[str] | None = None) -> str:
    body = (
        "<h2>The middle price</h2>"
        + _p("PicWise lists every product of the kind you asked for that the shops list as in stock, cheapest first. The "
             "Recommended is the product in the middle of that list: of 45 products, the 23rd. Not the cheapest, not the "
             "dearest. Its card says so: \u201cMid-priced for this category\u201d.")
        + "<h2>Two safeguards</h2>"
        + _ul("One extreme price does not move the middle: a product that costs at least twice the next dearest is left "
              "out of the count.",
              "The Recommended carries a barcode number (EAN), which PicWise needs to check that the same product is not "
              "cheaper in another shop. If the middle product has none, PicWise takes the nearest one that has.")
        + "<h2>When there is no Recommended</h2>"
        + _ul("When too few products match to have a middle price.",
              "When no mid-priced product carries a barcode number.",
              "When you choose a price on the price bar, or look at one shop's offer: the choice is then yours.")
        + _p("The page says so each time.")
        + "<h2>What never counts</h2>"
        + _p("Commission. The Recommended is chosen by the same rule in shops that pay PicWise and in shops that pay it "
             "nothing. An offer does not count either: the Recommended is the middle price, on offer or not.")
        + "<h2>What it is not</h2>"
        + _p("A recommendation is information to help you decide, not a guarantee that a product is the best, the cheapest "
             "or the most suitable for you.")
        + _go("/terms", "Terms of Use")
    )
    intro = "Every search shows four choices, and one of them is marked Recommended. This is the whole rule."
    return _doc("How we choose the Recommended", intro, body, parts=parts)


def render_our_checks_page(*, parts: frozenset[str] | None = None) -> str:
    body = (
        "<h2>What is checked</h2>"
        + _ul("The product's page opens, and it is the same product.",
              "The shop lists it as in stock.",
              "The price on the shop's page. Where PicWise can read it reliably and it differs from the shop's feed, "
              "PicWise shows the page's price.",
              "Its photo loads.",
              "It is in a category PicWise covers.")
        + "<h2>When a check fails</h2>"
        + _ul("The product leaves PicWise that night, whatever the reason. It is checked again and comes back when it "
              "passes.",
              "A new product is shown only once it has passed.",
              "A product not checked for three days is not shown until it is checked again.",
              "A shop whose website PicWise cannot check is given three days. After that its products are not shown until "
              "it can be checked.")
        + "<h2>What a check is not</h2>"
        + _p("A promise. Shops change prices and stock at any time, also after PicWise last looked. Check the details on "
             "the shop's website before you buy.")
    )
    intro = ("A wrong price or a product that is gone wastes your time. PicWise checks products on the shops' own websites, "
             "all day, every day.")
    return _doc("Our checks", intro, body, parts=parts)


def _letter(name: str) -> str:
    return name[:1].upper() if name[:1].isalpha() else "0\u20139"


def render_our_shops_page(*, facts: HomeFacts | None | Any = ..., parts: frozenset[str] | None = None) -> str:
    """Every shop with a product shown tonight, A to Z under its letter; the list and its
    count left out while tonight's are not known."""
    facts = current_home_facts() if facts is ... else facts
    names = tuple(facts.shop_names) if facts is not None else ()
    groups = "".join(
        f'<p class="pw-hs-letter">{escape(first)}</p><ul class="pw-hs-shoplist">'
        + "".join(f"<li>{escape(name)}</li>" for name in group)
        + "</ul>"
        for first, group in groupby(names, key=_letter)
    )
    body = _p("The shops on PicWise run a programme with Awin. PicWise earns a commission only from the shops that have "
              "accepted it into their programme; the others are shown by the same rule, and PicWise earns nothing from them.")
    if groups:
        body += f"<h2>A to Z</h2>{groups}"
    count = len(names)
    intro = (
        f"PicWise shows products from {count:,} UK shop{'s' if count != 1 else ''} tonight."
        if count
        else "PicWise shows products from UK shops."
    )
    return _doc("Our shops", intro, body, parts=parts)


# ---- Part C: the offers (the specification, 7.2) ----
OFFERS_EYEBROW = "SHOP OFFERS"
OFFERS_PAGE_TITLE = "Offers from the shops"
OFFERS_NOTE = "Offers are the shops' own, as they state them through Awin: check them on the shop's site."
OFFERS_NONE = "No shop has an offer on the products shown tonight."
OFFER_AT = "OFFER AT {shop}"
OFFER_ALL = "All offers"
OFFER_WHICH = "Which kind are you looking for?"
OFFER_SEE = "See the products"
OFFER_HEADING = "Results for: {query}, at {shop}, cheapest first"
OFFER_ONLY = "{shop}'s {kinds} only, so there is no Recommended here."
OFFER_EVERY_SHOP = "See {kinds} from every shop"


def _until(end: datetime) -> str:
    now = datetime.now(end.tzinfo or timezone.utc)
    year = "" if end.year == now.year else f" {end.year}"
    return f"until {end.day} {end:%b}{year}"


def _offer_lines(card: OfferCard, *, link: str = "") -> str:
    code = f' \u00b7 Code: <span class="pw-hs-of-code">{escape(card.code)}</span>' if card.code else ""
    terms = (
        f'<details class="pw-hs-of-terms"><summary>Offer terms</summary><p>{escape(card.terms)}</p></details>'
        if card.terms
        else ""
    )
    go = hs._link(link, OFFER_SEE) if link else ""
    return (
        f'<p class="pw-hs-of-title">{escape(card.title)}</p>'
        f'<p class="pw-hs-of-meta">{escape(_until(card.end))}{code}</p>{terms}{go}'
    )


def offer_box(card: OfferCard) -> str:
    """The offer, once, in the shop's own words, above what it covers."""
    return (
        '<section class="pw-hs-offerbox" aria-label="The offer">'
        f'<p class="pw-hs-eyebrow">{escape(OFFER_AT.format(shop=card.shop.upper()))}</p>'
        f"{_offer_lines(card)}</section>"
    )


def _offers_tonight(facts: HomeFacts | None) -> tuple[OfferCard, ...]:
    return tuple(facts.all_offers) if facts is not None else ()


def find_offer(offer_id: str, facts: HomeFacts | None | Any = ...) -> OfferCard | None:
    facts = current_home_facts() if facts is ... else facts
    return next((card for card in _offers_tonight(facts) if card.offer_id == offer_id), None)


def _offer_products_href(query: str, offer_id: str) -> str:
    return f"/search?q={quote(query, safe='')}&offer={quote(offer_id, safe='')}"


def render_offers_page(*, facts: HomeFacts | None | Any = ..., parts: frozenset[str] | None = None) -> str:
    """Every offer covering products shown tonight, a shop after another (7.2)."""
    facts = current_home_facts() if facts is ... else facts
    blocks = ""
    for shop, cards in groupby(_offers_tonight(facts), key=lambda card: card.shop):
        inner = "".join(
            f'<div class="pw-hs-of">{_offer_lines(card, link=hs.offer_href(card))}</div>' for card in cards
        )
        blocks += f'<section class="pw-hs-shopblock"><h2 class="pw-hs-shopblock-name">{escape(shop)}</h2>{inner}</section>'
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        f'<p class="pw-hs-eyebrow">{escape(OFFERS_EYEBROW)}</p>'
        f'<h1 class="pw-hs-h1" id="pw-hs-h1">{escape(OFFERS_PAGE_TITLE)}</h1>'
        f'<p class="pw-hs-page-line">{escape(hs.OFFERS_SUB)}</p></section>'
        + (blocks or f'<p class="pw-hs-note">{escape(OFFERS_NONE)}</p>')
        + f'<p class="pw-hs-note">{escape(OFFERS_NOTE)}</p>'
    )
    return hs.render_store_page(title=f"{OFFERS_PAGE_TITLE} — PicWise", main_html=main, styles=STORE_PAGES_STYLES, parts=parts)


def _kind_name(query: str) -> str:
    for kinds in hs.load_departments().kinds.values():
        for kind in kinds:
            if kind.query == query:
                return kind.name
    return query[:1].upper() + query[1:]


def offer_page(
    offer_id: str, *, facts: HomeFacts | None | Any = ..., kinds: DepartmentsFacts | None | Any = ...,
    parts: frozenset[str] | None = None,
) -> tuple[str, str] | None:
    """An offer: ("redirect", its kind's products) when it covers products of one kind
    tonight; else ("page", the page that asks which kind); None when it is no offer of
    tonight's."""
    card = find_offer(offer_id, facts)
    if card is None:
        return None
    kinds = current_kind_facts() if kinds is ... else kinds
    covered = tuple(kinds.offer_kinds.get(offer_id, ())) if kinds is not None else ()
    if len(covered) == 1:
        return "redirect", _offer_products_href(covered[0].query, offer_id)
    rows = "".join(
        f'<li><a class="pw-hs-row" href="{escape(_offer_products_href(kind.query, offer_id), quote=True)}">'
        f'<span class="pw-hs-row-text"><span class="pw-hs-row-name">{escape(_kind_name(kind.query))}</span>'
        f'<span class="pw-hs-row-meta">{escape(_kind_meta(KindFacts(count=kind.count, low=kind.low, pick=None)))}</span>'
        f"</span>{_CHEVRON}</a></li>"
        for kind in covered
    )
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        f'<a class="pw-hs-crumb" href="{hs.PART_ADDRESSES["offers"]}">\u2039 {escape(OFFER_ALL)}</a>'
        f'<h1 class="pw-hs-h1" id="pw-hs-h1">{escape(card.shop)}</h1></section>'
        f"{offer_box(card)}"
        + (
            '<section class="pw-hs-list" aria-labelledby="pw-hs-which">'
            f'<h2 class="pw-hs-h2" id="pw-hs-which">{escape(OFFER_WHICH)}</h2>'
            f'<ul class="pw-hs-rows">{rows}</ul></section>'
            if rows
            else ""
        )
        + f'<p class="pw-hs-note">{escape(OFFERS_NOTE)}</p>'
    )
    page = hs.render_store_page(title=f"{card.shop}: offer — PicWise", main_html=main, styles=STORE_PAGES_STYLES, parts=parts)
    return "page", page


def _plural_words(query: str) -> str:
    """The kind's name as a sentence says it: "kettles", "TVs"."""
    name = _kind_name(query)
    return name if len(name) > 1 and name[1].isupper() else name[:1].lower() + name[1:]


def offer_answer(resolution: Any, offer_id: str, *, shown: int = 0) -> Any | None:
    """A search's answer narrowed to the products this offer covers, cheapest first,
    four a page as "More" opens them; no Recommended, no "Lowest price", no place among
    the prices (owner, 2026-11-24). None when it covers none of them."""
    offers = dict(getattr(resolution, "provider_feed_offers", ()) or ())
    products = tuple(resolution.provider_feed_selected_products) + tuple(
        getattr(resolution, "provider_feed_more_products", ()) or ()
    )
    if str(resolution.provider_feed_decision_status or "") == "recommended" and products:
        # The Recommended stands first; among the offer's products it is one more, in its
        # place by price: the search's own places in the price order.
        places = dict(getattr(resolution, "provider_feed_price_ranks", ()) or ())
        order = {id(product): index for index, product in enumerate(products)}
        products = tuple(
            sorted(
                products,
                key=lambda product: (
                    places.get(str(product.get("provider_product_id") or "").strip(), 10**9),
                    order[id(product)],
                ),
            )
        )
    kept = tuple(
        product
        for product in products
        if str((offers.get(str(product.get("provider_product_id") or "").strip()) or {}).get("offer_id") or "") == offer_id
    )
    if not kept:
        return None
    page = max(4, (int(shown or 0) // 4) * 4)
    return replace(
        resolution,
        provider_feed_selected_products=kept[:4],
        provider_feed_more_products=kept[4:page],
        provider_feed_total_count=len(kept),
        provider_feed_decision_status="no_recommendation_price_chosen",
        provider_feed_recommended_product_id="",
        provider_feed_cheapest_product_ids=(),
        provider_feed_price_ranks=(),
        provider_feed_offers=(),
        provider_feed_fitting_product_ids=(),
    )


def dress_offer_products(page: str, *, query: str, card: OfferCard) -> str:
    """The search's page of an offer's products, as approved: the offer above the cards,
    the heading names the shop, the line under it says it is one shop's, a link to the
    kind in every shop, no price bar (it would choose among every shop's prices), and
    "More" keeps the offer."""
    kinds = _plural_words(query)
    page = re.sub(r'<form class="pw-pricebar".*?</form>', "", page, count=1, flags=re.S)
    page, headed = re.subn(
        r'<h1 class="pw-query-line">.*?</h1>',
        f'<h1 class="pw-query-line">{escape(OFFER_HEADING.format(query=query, shop=card.shop))}</h1>',
        page,
        count=1,
        flags=re.S,
    )
    line = (
        f'<p class="pw-reference-disclaimer">{escape(OFFER_ONLY.format(shop=card.shop, kinds=kinds))} '
        "Prices and stock are as the shops list them.</p>"
        f'<p class="pw-hs-oneshop"><a href="/search?q={quote(query, safe="")}">'
        f"{escape(OFFER_EVERY_SHOP.format(kinds=kinds))} \u203a</a></p>"
    )
    page, lined = re.subn(r'<p class="pw-reference-disclaimer">.*?</p>', line, page, count=1, flags=re.S)
    frame = '<div class="pw-reference-frame" id="pw-reference-frame">'
    if not (headed and lined and page.count(frame) == 1):
        return ""
    page = page.replace(frame, frame + offer_box(card), 1)
    more = f'href="/search?q={quote(query, safe="")}&amp;shown='
    page = page.replace(more, f'href="/search?q={quote(query, safe="")}&amp;offer={quote(card.offer_id, safe="")}&amp;shown=')
    return page


def render_offer_products(query: str, offer_id: str, *, shown: int = 0) -> str | None:
    """The search's page of an offer's products, or None (no offer of tonight's by that
    id, or none of its products in this search): then the search is drawn as ever."""
    from picwise_providers.state import peek_search_catalogue_counts
    from picwise_search import resolve_live_search
    from picwise_search.live_search_resolver import MAX_SHOWN_PRODUCTS

    from .reference import provider_feed_cards_will_render, render_picwise_reference_surface

    card = find_offer(offer_id)
    if card is None or not str(query or "").strip():
        return None
    resolution = resolve_live_search(query, shown=MAX_SHOWN_PRODUCTS)
    if not provider_feed_cards_will_render(resolution):
        return None
    narrowed = offer_answer(resolution, offer_id, shown=shown)
    if narrowed is None:
        return None
    page = render_picwise_reference_surface(
        query=query, resolution=narrowed, source_page="search", catalogue=peek_search_catalogue_counts(), indexable=False
    )
    page = dress_offer_products(page, query=query, card=card)
    return dress_search_page(page, query) if page else None


# ---- Part F: the other pages under the store's header and footer (7.4) ----
SEARCH_PAGE_STYLES = (
    ".pw-hs-search .pw-reference-frame{padding-top:14px;}"
    # On the store's ground the page's notes take the store's grey (5.6:1; today's is
    # 4.35:1), and "Listed as available" a green that reads on a card (5.4:1; 4.38:1).
    ".pw-hs-search .pw-reference-disclaimer,.pw-hs-search .pw-demo-note,.pw-hs-search .pw-counter{color:var(--hs-muted);}"
    ".pw-hs-search .pw-stock-listed,.pw-hs-search .pw-stock-verified{color:#187a44;}"
)
INFO_PAGE_STYLES = (
    ".pw-hs-doc .pw-emphasis{padding:12px 14px;border:1px solid var(--hs-line);border-radius:12px;background:var(--hs-cream);}"
    ".pw-hs-doc a{color:var(--hs-acc);font-weight:600;}"
    ".pw-hs-doc p a{display:inline-block;min-height:24px;}"
)


def dress_search_page(page: str, query: str) -> str:
    """A search's page under the store's header (no departments' row, so that the
    Recommended and its button stay on the first screen) and over its footer; the page
    as it was when it is not drawn as expected."""
    top = re.search(r'<header class="pw-topbar">.*?</header>', page, flags=re.S)
    box = re.search(r'<section class="pw-search-wrap".*?</section>', page, flags=re.S)
    foot = re.search(r'<footer class="pw-footer">.*?</footer>', page, flags=re.S)
    main = '<main class="pw-reference-viewport">'
    if not (top and box and foot) or page.count(main) != 1 or page.count("<body>") != 1:
        return page
    header = hs._header_html(hs.load_home_lists(), hs.PARTS_BUILT, nav_row=False)
    marker = 'name="q" value=""'
    if header.count(marker) != 1:
        return page
    header = header.replace(marker, f'name="q" value="{escape(str(query or ""), quote=True)}"')
    page = page.replace(box.group(0), "", 1)
    page = page.replace(top.group(0), header, 1)
    page = page.replace(foot.group(0), hs._footer_html(hs.PARTS_BUILT), 1)
    page = page.replace(main, '<main class="pw-reference-viewport pw-hs pw-hs-search">', 1)
    page = page.replace("<body>", '<body class="pw-hs-body">', 1)
    return page.replace("</style>", hs.HOME_STORE_STYLES + STORE_PAGES_STYLES + SEARCH_PAGE_STYLES + "</style>", 1)


STRIP_SECTION = "The \u201cPicWise on your phone\u201d strip"


def dress_info_page(page: str, *, strip_line: bool = False) -> str:
    """An info page (About, Contact, Terms, Privacy, Cookies, Affiliate disclosure) under
    the store's header and over its footer, its words and its head as they are; the page
    as it was when it is not drawn as expected."""
    head = re.search(r"<head>(.*?)<style>", page, flags=re.S)
    card = re.search(r'<section class="pw-card pw-legal">(.*)</section>\s*<footer class="pw-footer">', page, flags=re.S)
    if not (head and card):
        return page
    inner = card.group(1)
    inner, titled = re.subn(r'<h1 class="pw-title">', '<h1 class="pw-hs-h1" id="pw-hs-h1">', inner, count=1)
    if not titled:
        return page
    inner = inner.replace('<p class="pw-intro">', '<p class="pw-hs-doc-intro">', 1)
    if strip_line and hs.strip_shown():
        # While the phone strip is shown, the Cookies and Privacy pages say its "×" is
        # kept on the device (owner, 2026-11-24; the specification, 8.4).
        inner += f"<h2>{escape(STRIP_SECTION)}</h2><p>{escape(hs.STRIP_PRIVACY_LINE)}</p>"
    own_head = re.sub(r'<meta charset="utf-8">|<meta name="viewport"[^>]*>', "", head.group(1))
    title = re.search(r"<title>(.*?)</title>", own_head, flags=re.S)
    return hs.render_store_page(
        title=html_unescape(title.group(1)) if title else "PicWise",
        main_html=f'<article class="pw-hs-doc" aria-labelledby="pw-hs-h1">{inner}</article>',
        styles=STORE_PAGES_STYLES + INFO_PAGE_STYLES,
        head=own_head,
    )


_PAGES = {
    "how_picwise_works": render_how_picwise_works_page,
    "how_we_choose": render_how_we_choose_page,
    "our_checks": render_our_checks_page,
    "our_shops": render_our_shops_page,
}


def store_page(path: str, *, parts: frozenset[str] | None = None) -> str | None:
    """The page of the store at `path`, or None: not one of its pages, or its part not
    built (`home_store.PARTS_BUILT`)."""
    parts = hs.PARTS_BUILT if parts is None else frozenset(parts)
    if "offers" in parts:
        if path == hs.PART_ADDRESSES["offers"]:
            return render_offers_page(parts=parts)
    if "pages" in parts:
        for name, render in _PAGES.items():
            if path == hs.PART_ADDRESSES[name]:
                return render(parts=parts)
    if "departments" in parts:
        if path == hs.PART_ADDRESSES["departments"]:
            return render_departments_page(parts=parts)
        prefix = "/department/"
        if path.startswith(prefix) and path.count("/") == 2:
            return render_department_page(path[len(prefix):], parts=parts)
    return None
