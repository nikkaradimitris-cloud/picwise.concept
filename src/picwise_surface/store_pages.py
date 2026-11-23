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

Every page is kept out of Google (`noindex`): nothing of the store is declared (section 2).
What a page knows of the catalogue is worked out once a night (`home_store_facts`), never
while it is drawn; what is not known yet is left out, never filled.
"""
from __future__ import annotations

from html import escape
from itertools import groupby
from typing import Any

from . import home_store as hs
from .home_store_facts import DepartmentsFacts, KindFacts, current_home_facts, current_kind_facts
from .home_store import Department, DeptKind, HomeFacts, Pick

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
    "@media (min-width:700px){"
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
