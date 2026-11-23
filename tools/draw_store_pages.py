"""The pictures of the store's parts that are not built yet (docs/PICWISE_HOME_STORE_SPEC.md, 7.6).

Task H2 (2026-11-24) showed the owner a picture of every part of the home page as a store
that he had not seen: a department, all departments, the offers, an offer on a whole shop,
an offer's products, the four new pages, the search's page under the store's header, the
phone strip's sheet, the month's ten opened and the home page on a computer. This draws
them again: each is a page with the site's own header, footer and styles
(`picwise_surface.home_store`) and, for a search, the site's own search page over a small
feed of the site's real kettles of that day. What is new, and for the builder of Parts B to
F (task H4) to write into the site, is `PROTO_STYLES` and the markup of the functions below.

Pictures, not the site's code: nothing here is served by the site, and no test reads it.
The offers' words stand in square brackets (no shop's offer is read here), the products'
photos are drawings, and the three pages ending in `_el` are the owner's own reading in
Greek, never the site's.

usage: python tools/draw_store_pages.py OUT      then: python -m http.server -d OUT
"""
import csv, html, importlib.util, os, re, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[1])
for path in (REPO + "/tests", REPO, REPO + "/src"):
    if path not in sys.path:
        sys.path.insert(0, path)

from picwise_surface import home_store as hs  # noqa: E402
from picwise_surface.home_store import HomeFacts, OfferCard, Pick  # noqa: E402
from picwise_surface.browser_lists import BROWSER_LISTS_SCRIPT, BROWSER_LISTS_STYLES, HEAD_SCRIPT, panels_html  # noqa: E402
from picwise_surface.fonts import FONT_PRELOAD_HTML  # noqa: E402
from picwise_surface.page_styles import _PAGE_STYLES  # noqa: E402
from picwise_surface.shop_names import shop_display_name  # noqa: E402
from picwise_surface.trends import load_trends_panel  # noqa: E402

ALL = frozenset({"departments", "offers", "pages"})
E = html.escape
ART = "/assets/home/art/"
PHOTO = "/proto/"          # stand-ins for the shops' photos (drawings), this picture's only
LISTS = hs.load_home_lists()
DEPT = {d.slug: d for d in LISTS.departments}

# ---- what is new: styles of the parts not built yet (H4 writes the site's own) ----
PROTO_STYLES = (
    ".pw-hs-nav a.is-on{color:#fff;box-shadow:inset 0 -3px 0 var(--hs-gold);}"
    ".pw-hs-page-head{padding:18px 16px 4px;}"
    ".pw-hs-page-head .pw-hs-h1{margin:6px 0 0;}"
    ".pw-hs-page-line{margin:8px 0 0;font-size:15px;line-height:1.45;color:var(--hs-muted);}"
    ".pw-hs-crumb{display:inline-flex;align-items:center;min-height:48px;margin:0 0 -8px;color:var(--hs-acc);font-size:14px;font-weight:700;text-decoration:none;}"
    ".pw-hs-tile-meta{margin-top:-4px;font-size:13px;line-height:1.3;color:var(--hs-muted);}"
    ".pw-hs-list{margin-top:12px;padding:14px 16px 6px;background:#fff;}"
    ".pw-hs-rows{list-style:none;margin:12px 0 0;padding:0 0 10px;display:flex;flex-direction:column;gap:8px;}"
    ".pw-hs-row{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:56px;padding:6px 14px;border-radius:14px;background:var(--hs-cream);text-decoration:none;color:var(--hs-ink);}"
    ".pw-hs-row-text{display:flex;flex-direction:column;gap:2px;min-width:0;}"
    ".pw-hs-row-name{font-size:15px;line-height:1.25;font-weight:600;}"
    ".pw-hs-row-meta{font-size:13px;line-height:1.3;color:var(--hs-muted);}"
    ".pw-hs-row svg{flex:0 0 auto;color:var(--hs-muted);}"
    ".pw-hs-group{padding:20px 16px 0;}"
    ".pw-hs-group-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 12px;margin-top:12px;}"
    ".pw-hs-group .pw-hs-dept{flex:none;}"
    ".pw-hs-group .pw-hs-dept-pic{height:auto;aspect-ratio:1/1;}"
    ".pw-hs-group .pw-hs-art{width:82%;height:auto;}"
    ".pw-hs-shopblock{margin:12px 16px 0;padding:16px 16px 4px;border-radius:18px;background:#fff;border:1px solid var(--hs-line);}"
    ".pw-hs-shopblock-name{margin:0;font-size:18px;line-height:1.2;font-weight:800;color:var(--hs-ink);}"
    ".pw-hs-of{padding:12px 0 4px;border-top:1px solid var(--hs-line);margin-top:12px;}"
    ".pw-hs-of-title{margin:0;font-size:15px;line-height:1.35;font-weight:700;color:var(--hs-ink);}"
    ".pw-hs-of-meta{margin:4px 0 0;font-size:13px;line-height:1.4;color:var(--hs-muted);}"
    ".pw-hs-of-code{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;letter-spacing:.04em;color:var(--hs-ink);}"
    ".pw-hs-of-terms{margin:0;font-size:13px;color:var(--hs-muted);}"
    ".pw-hs-of-terms summary{display:flex;align-items:center;min-height:48px;cursor:pointer;color:var(--hs-acc);font-weight:600;}"
    ".pw-hs-offerbox{margin:12px 16px 0;padding:14px 16px 6px;border-radius:18px;background:var(--hs-pale);}"
    ".pw-hs-offerbox .pw-hs-eyebrow{color:#5c4300;}"
    ".pw-hs-offerbox .pw-hs-of-title{margin-top:6px;font-size:17px;}"
    ".pw-hs-offerbox .pw-hs-of-meta{color:#5c4300;}"
    ".pw-hs-offerbox .pw-hs-of-terms summary{color:#5c4300;}"
    ".pw-hs-oneshop{margin:10px 16px 0;font-size:14px;line-height:1.45;color:var(--hs-muted);}"
    ".pw-hs-oneshop a{display:inline-flex;align-items:center;min-height:48px;color:var(--hs-acc);font-weight:700;text-decoration:none;}"
    ".pw-hs-note{margin:16px 16px 0;font-size:13px;line-height:1.5;color:var(--hs-muted);}"
    ".pw-hs-doc{margin:16px 16px 0;padding:22px 18px 14px;border-radius:20px;background:#fff;border:1px solid var(--hs-line);}"
    ".pw-hs-doc .pw-hs-h1{margin:6px 0 0;font-size:26px;}"
    ".pw-hs-doc-intro{margin:12px 0 0;font-size:16px;line-height:1.55;color:var(--hs-ink);}"
    ".pw-hs-doc h2{margin:22px 0 0;font-size:18px;line-height:1.25;font-weight:800;letter-spacing:-.2px;color:var(--hs-ink);}"
    ".pw-hs-doc p{margin:8px 0 0;font-size:15px;line-height:1.6;color:#33425c;}"
    ".pw-hs-doc ul{margin:8px 0 0;padding:0 0 0 20px;color:#33425c;}"
    ".pw-hs-doc li{margin:6px 0 0;font-size:15px;line-height:1.55;}"
    ".pw-hs-doc a{color:var(--hs-acc);font-weight:600;}"
    ".pw-hs-doc-step{display:flex;align-items:center;gap:10px;}"
    ".pw-hs-doc-updated{margin:18px 0 0;font-size:13px;color:var(--hs-muted);}"
    ".pw-hs-doc .pw-hs-shoplist{list-style:none;margin:6px 0 0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 16px;}"
    ".pw-hs-doc .pw-hs-shoplist li{margin:0;padding:8px 0;font-size:14px;line-height:1.3;color:var(--hs-ink);border-top:1px solid var(--hs-line);}"
    ".pw-hs-letter{margin:18px 0 0;font-size:14px;font-weight:800;letter-spacing:.08em;color:var(--hs-acc);}"
    # the owner's own reading of a page, in Greek: never on the site
    ".pw-hs-el-band{margin:0;padding:10px 16px;background:#fdf0cc;color:#5c4300;font-size:13px;line-height:1.4;font-weight:700;}"
    # the install sheet
    ".pw-hs-veil{position:fixed;top:0;right:0;bottom:0;left:0;background:rgba(15,36,66,.5);z-index:60;}"
    ".pw-hs-sheet{position:fixed;left:0;right:0;bottom:0;z-index:61;background:#fff;border-radius:22px 22px 0 0;padding:10px 20px 24px;box-shadow:0 -10px 30px rgba(15,36,66,.25);}"
    ".pw-hs-sheet-grip{width:44px;height:5px;border-radius:3px;background:#d3d0c8;margin:0 auto 14px;}"
    ".pw-hs-sheet-head{display:flex;align-items:center;gap:12px;}"
    ".pw-hs-sheet-title{margin:0;font-size:20px;line-height:1.2;font-weight:800;letter-spacing:-.3px;color:var(--hs-ink);}"
    ".pw-hs-sheet-steps{list-style:none;margin:18px 0 0;padding:0;display:flex;flex-direction:column;gap:14px;}"
    ".pw-hs-sheet-step{display:flex;align-items:center;gap:12px;font-size:16px;line-height:1.35;color:var(--hs-ink);}"
    ".pw-hs-sheet-step b{font-weight:700;}"
    ".pw-hs-sheet-ico{display:inline-flex;vertical-align:-5px;margin:0 2px;color:var(--hs-acc);}"
    ".pw-hs-sheet-ok{margin-top:22px;display:flex;align-items:center;justify-content:center;width:100%;height:52px;border:0;border-radius:999px;background:var(--hs-ink);color:#fff;font:inherit;font-size:16px;font-weight:700;}"
    # a search page under the store's header: the page's own column, the store's footer
    ".pw-hs-search .pw-reference-frame{padding-top:14px;}"
    # on the store's ground the page's notes take the store's grey (5.6:1; today's is 4.3:1),
    # and "Listed as available" a green that reads on white (4.9:1; today's is 4.4:1)
    ".pw-hs-search .pw-reference-disclaimer,.pw-hs-search .pw-demo-note,.pw-hs-search .pw-counter{color:var(--hs-muted);}"
    ".pw-hs-search .pw-stock-listed,.pw-hs-search .pw-stock-verified{color:#187a44;}"
    ".pw-hs-search .pw-hs-offerbox{margin:0 0 14px;}"
    ".pw-hs-search .pw-hs-oneshop{margin:0 0 12px;}"
    ".pw-hs-search .pw-hs-oneshop a{display:flex;}"
)

_CHEV = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>')


def header(*, nav=True, current="", query=""):
    out = hs._header_html(LISTS, ALL if nav else frozenset({"offers", "pages"}))
    if current:
        target = f'<a href="/department/{current}">'
        assert out.count(target) == 1, current
        out = out.replace(target, f'<a class="is-on" aria-current="page" href="/department/{current}">')
    if query:
        marker = 'name="q" value=""'
        assert out.count(marker) == 1
        out = out.replace(marker, f'name="q" value="{E(query, quote=True)}"')
    return out


def shell(title, main_html, *, nav=True, current="", query="", body_class="", extra_styles="", overlay=""):
    return (
        "<!doctype html><html lang=\"en-GB\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{E(title)}</title>{FONT_PRELOAD_HTML}"
        f"<script>{HEAD_SCRIPT}</script>"
        f"<style>{_PAGE_STYLES}{BROWSER_LISTS_STYLES}{hs.HOME_STORE_STYLES}{extra_styles}{PROTO_STYLES}</style>"
        f'</head><body class="pw-hs-body {body_class}">'
        '<main class="pw-reference-viewport pw-hs">'
        f"{header(nav=nav, current=current, query=query)}{panels_html()}"
        f'<div class="pw-hs-main">{main_html}</div>'
        f"{hs._footer_html(ALL)}"
        f"<script>{BROWSER_LISTS_SCRIPT}</script><script>{hs.HOME_STORE_SCRIPT}</script>"
        f"</main>{overlay}</body></html>"
    )


def tile(name, query, drawing, meta="", *, ground="sand", layer="soft", size=144):
    meta_html = f'<span class="pw-hs-tile-meta">{E(meta)}</span>' if meta else ""
    return (
        f'<a class="pw-hs-tile" href="/search?q={query.replace(" ", "%20")}">'
        f'<span class="pw-hs-tile-pic pw-hs-{ground}">{hs._background(layer)}{hs._drawing(drawing, size)}</span>'
        f'<span class="pw-hs-tile-name">{E(name)}</span>{meta_html}</a>'
    )


def row(name, meta, href):
    return (
        f'<li><a class="pw-hs-row" href="{E(href, quote=True)}"><span class="pw-hs-row-text">'
        f'<span class="pw-hs-row-name">{E(name)}</span><span class="pw-hs-row-meta">{E(meta)}</span></span>{_CHEV}</a></li>'
    )


# ---- the Kitchen department, with the site's own numbers of 2026-11-24 (read on the site) ----
# (name, the words searched, drawing, products, from, the Recommended: title, price, shop)
KITCHEN = (
    ("Kettles", "kettle", "kettle", 89, "£12.74", ("1.7L 'Fluted' Cordless Rapid Boil Electric Kettle 3000W - Black", "£34.99", "Geepas")),
    ("Coffee machines", "coffee machine", "coffee_machine", 76, "£6.35", ("1.5L Filter Coffee Machine & 2-Slice Toaster Matching Set", "£79.99", "Geepas")),
    ("Toasters", "toaster", "toaster", 55, "£14.99", ("2 Slice Bread Toaster & 1.7L 2200W Electric Kettle Set", "£34.99", "Geepas")),
    ("Microwaves", "microwave", "microwave", 20, "£55.24", ("Aurora Black and Rose Gold 3-In-1 Microwave, Kettle & Toaster Set", "£123.24", "Geepas")),
    ("Blenders", "blender", "blender", 19, "£3.84", ("2-In-1 Ice Crushing Jug Blender and Smoothie Maker White", "£25.49", "Geepas")),
    ("Air fryers", "air fryer", "air_fryer", 15, "£35.00", ("HOMCOM Dual Air Fryer 8.5L Family Size, Double Basket Digital Air Fryer Oven with Smart Finish & 8 Presets", "£75.99", "Aosom UK")),
    ("Mixers", "mixer", "", 13, "£14.99", ("HOMCOM 1300W Kitchen Stand Mixer with Dough Hook, Whisk and Beater, 4.5L Bowl, Blue", "£59.99", "Aosom UK")),
    ("Food processors", "food processor", "", 6, "£14.44", ("Rose Gold 500ml Mini Multi-Functional Food Processor", "£21.24", "Geepas")),
)
PREPARED = datetime(2026, 11, 23, 17, 3, tzinfo=timezone.utc)


def department_page():
    picks = tuple(
        Pick(query=q, kind=name[:-1] if name.endswith("s") else name, link=f"See {name.lower()}", title=rec[0], price=rec[1],
             shop=rec[2], image=f"{ART}{drawing}.svg")
        for name, q, drawing, _n, _f, rec in KITCHEN if drawing
    )[:6]
    band = hs._band_html(HomeFacts(prepared_at=PREPARED, picks=picks), ALL)
    tiles = "".join(
        tile(name, q, drawing, f"{n} products from {low}")
        for name, q, drawing, n, low, _rec in KITCHEN if drawing
    )
    rows = "".join(row(name, f"{n} products from {low}", f"/search?q={q.replace(' ', '%20')}") for name, q, _d, n, low, _r in KITCHEN)
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        '<p class="pw-hs-eyebrow">DEPARTMENT</p>'
        '<h1 class="pw-hs-h1" id="pw-hs-h1">Kitchen</h1>'
        '<p class="pw-hs-page-line">From UK shops, in stock only.</p></section>'
        f'<section class="pw-hs-sec" aria-label="Kitchen"><div class="pw-hs-grid" style="margin-top:0">{tiles}</div></section>'
        f"{band}"
        '<section class="pw-hs-list" aria-labelledby="pw-hs-all">'
        '<h2 class="pw-hs-h2" id="pw-hs-all">All kinds in Kitchen</h2>'
        f'<ul class="pw-hs-rows">{rows}</ul></section>'
        f'<a class="pw-hs-back" href="#top">{hs._UP}{E(hs.BACK_TO_TOP)}</a>'
    )
    return shell("Kitchen — PicWise", main, current="kitchen")


GROUPS = (
    ("home-kitchen", "Home & kitchen", ("kitchen", "home-appliances", "furniture", "lighting", "garden")),
    ("tech-tools", "Tech & tools", ("computers", "tools", "car-tyres")),
    ("fashion", "Fashion", ("fashion", "jewellery-watches", "perfume")),
    ("play-sport", "Play & sport", ("toys-games", "sports")),
)


def departments_page():
    groups = ""
    for anchor, name, slugs in GROUPS:
        tiles = "".join(
            f'<a class="pw-hs-dept" href="/department/{slug}">'
            f'<span class="pw-hs-dept-pic pw-hs-mist">{hs._background("soft")}{hs._drawing(DEPT[slug].drawing, 96)}</span>'
            f'<span class="pw-hs-dept-name">{E(DEPT[slug].name)}</span></a>'
            for slug in slugs
        )
        groups += (
            f'<section class="pw-hs-group" id="{anchor}" aria-labelledby="g-{anchor}">'
            f'<h2 class="pw-hs-h2" id="g-{anchor}">{E(name)}</h2><div class="pw-hs-group-grid">{tiles}</div></section>'
        )
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        '<h1 class="pw-hs-h1" id="pw-hs-h1">All departments</h1>'
        '<p class="pw-hs-page-line">From UK shops, in stock only.</p></section>'
        f"{groups}"
        f'<a class="pw-hs-back" href="#top">{hs._UP}{E(hs.BACK_TO_TOP)}</a>'
    )
    return shell("All departments — PicWise", main)


# ---- the offers: the shops' own words stand in square brackets (none is read here) ----
def offer_lines(title, until, code="", terms=True, link=""):
    code_html = f' · Code: <span class="pw-hs-of-code">{E(code)}</span>' if code else ""
    terms_html = '<details class="pw-hs-of-terms"><summary>Offer terms</summary><p>[The offer\'s terms, in the shop\'s own words]</p></details>' if terms else ""
    link_html = f'<a class="pw-hs-link" href="{link}">See the products ›</a>' if link else ""
    return (
        f'<p class="pw-hs-of-title">{E(title)}</p>'
        f'<p class="pw-hs-of-meta">until {E(until)}{code_html}</p>{terms_html}{link_html}'
    )


def offers_page():
    blocks = ""
    for shop, offers in (
        ("InStock UK", (("[The shop's offer, in its own words]", "30 Nov", "", "o1"),)),
        ("Geepas", (("[An offer on one kind, in the shop's own words]", "4 Dec", "[CODE]", "o2"),
                    ("[An offer on the whole shop, in its own words]", "31 Dec", "", "o3"))),
        ("Aosom UK", (("[The shop's offer, in its own words]", "1 Dec", "[CODE]", "o4"),)),
    ):
        inner = "".join(
            f'<div class="pw-hs-of">{offer_lines(title, until, code, link=f"/offers/{oid}")}</div>'
            for title, until, code, oid in offers
        )
        blocks += f'<section class="pw-hs-shopblock"><h2 class="pw-hs-shopblock-name">{E(shop)}</h2>{inner}</section>'
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        '<p class="pw-hs-eyebrow">SHOP OFFERS</p>'
        '<h1 class="pw-hs-h1" id="pw-hs-h1">Offers from the shops</h1>'
        f'<p class="pw-hs-page-line">{E(hs.OFFERS_SUB)}</p></section>'
        f"{blocks}"
        '<p class="pw-hs-note">Offers are the shops\' own, as they state them through Awin: check them on the shop\'s site.</p>'
        f'<a class="pw-hs-back" href="#top">{hs._UP}{E(hs.BACK_TO_TOP)}</a>'
    )
    return shell("Offers from the shops — PicWise", main, nav=False)


# The kinds of a shop an offer covers, with the site's own numbers of 2026-11-24 (Geepas).
GEEPAS = (("Kettles", "kettle", 50, "£12.74"), ("Toasters", "toaster", 46, "£14.99"), ("Microwaves", "microwave", 16, "£55.24"),
          ("Blenders", "blender", 13, "£23.78"), ("Air fryers", "air fryer", 7, "£42.49"))


def offer_box(scope_line):
    return (
        '<section class="pw-hs-offerbox" aria-label="The offer">'
        f'<p class="pw-hs-eyebrow">{E(scope_line)}</p>'
        f'{offer_lines("[An offer on the whole shop, in its own words]", "31 Dec", "[CODE]")}'
        "</section>"
    )


def offer_kinds_page():
    rows = "".join(row(name, f"{n} products from {low}", f"/search?q={q.replace(' ', '%20')}&offer=o3") for name, q, n, low in GEEPAS)
    main = (
        '<section class="pw-hs-page-head" aria-labelledby="pw-hs-h1">'
        '<a class="pw-hs-crumb" href="/offers">‹ All offers</a>'
        '<h1 class="pw-hs-h1" id="pw-hs-h1">Geepas</h1></section>'
        f'{offer_box("OFFER AT GEEPAS")}'
        '<section class="pw-hs-list" aria-labelledby="pw-hs-which">'
        '<h2 class="pw-hs-h2" id="pw-hs-which">Which kind are you looking for?</h2>'
        f'<ul class="pw-hs-rows">{rows}</ul></section>'
        '<p class="pw-hs-note">Offers are the shops\' own, as they state them through Awin: check them on the shop\'s site.</p>'
        f'<a class="pw-hs-back" href="#top">{hs._UP}{E(hs.BACK_TO_TOP)}</a>'
    )
    return shell("Geepas: offer — PicWise", main, nav=False)


# ---- the four pages (their words: docs/PICWISE_HOME_STORE_SPEC.md, 7.3) ----
def doc(title, eyebrow, intro, body, updated="24 November 2026"):
    main = (
        '<article class="pw-hs-doc">'
        f'<p class="pw-hs-eyebrow">{E(eyebrow)}</p>'
        f'<h1 class="pw-hs-h1">{E(title)}</h1>'
        f'<p class="pw-hs-doc-intro">{intro}</p>{body}'
        f'<p class="pw-hs-doc-updated">Last updated: {E(updated)}</p>'
        "</article>"
        f'<a class="pw-hs-back" href="#top">{hs._UP}{E(hs.BACK_TO_TOP)}</a>'
    )
    return shell(f"{title} — PicWise", main, nav=False)


def step_h2(number, name, gold=False):
    cls = "pw-hs-step-n pw-hs-step-n-gold" if gold else "pw-hs-step-n"
    return f'<h2 class="pw-hs-doc-step"><span class="{cls}">{number}</span>{E(name)}</h2>'


def how_it_works_page():
    body = (
        f'{step_h2("1", "Search")}'
        "<p>Type the product you want, or pick a department. PicWise shows only that kind of product: "
        "a search for a coffee machine shows coffee machines, not filters for coffee machines.</p>"
        f'{step_h2("2", "See")}'
        "<p>Four choices, cheapest first, each at the shop's own price: its sale price where the shop gives one. "
        "Only what the shop lists as in stock. “More” opens the next four, as often as you ask.</p>"
        "<p>An offer is the shop's own, shown in its words with its end date. PicWise works out no price after it.</p>"
        f'{step_h2("3", "Decide", gold=True)}'
        "<p>One of the four is marked Recommended: the product in the middle of the prices, so neither the cheapest "
        'nor the dearest decides it.</p><a class="pw-hs-link" href="/how-we-choose">How we choose the Recommended \u203a</a>'
        "<p>The button then takes you to the shop. PicWise is not a shop: every purchase is made on the shop's own "
        "website, under the shop's terms.</p>"
        "<h2>Where prices and stock come from</h2>"
        "<p>From the shops' own product feeds, received through the Awin affiliate network and read again every night. "
        'PicWise also checks products on the shops\' own websites.</p><a class="pw-hs-link" href="/our-checks">Our checks \u203a</a>'
        "<h2>How PicWise earns</h2>"
        "<p>A commission from some shops, through Awin, when you buy after following a PicWise link. The price you pay "
        'is the same, and the commission never changes the order.</p><a class="pw-hs-link" href="/affiliate-disclosure">Affiliate disclosure \u203a</a>'
    )
    intro = "PicWise is a product search for shoppers in the United Kingdom who already know what they want to buy. It works in three steps."
    return doc("How PicWise works", "ABOUT PICWISE", intro, body)


def how_we_choose_page():
    body = (
        "<h2>The middle price</h2>"
        "<p>PicWise lists every product of the kind you asked for that the shops list as in stock, cheapest first. "
        "The Recommended is the product in the middle of that list: of 45 products, the 23rd. Not the cheapest, not the "
        "dearest. Its card says so: “Mid-priced for this category”.</p>"
        "<h2>Two safeguards</h2><ul>"
        "<li>One extreme price does not move the middle: a product that costs at least twice the next dearest is left out of the count.</li>"
        "<li>The Recommended carries a barcode number (EAN), which PicWise needs to check that the same product is not cheaper "
        "in another shop. If the middle product has none, PicWise takes the nearest one that has.</li></ul>"
        "<h2>When there is no Recommended</h2><ul>"
        "<li>When too few products match to have a middle price.</li>"
        "<li>When no mid-priced product carries a barcode number.</li>"
        "<li>When you choose a price on the price bar, or look at one shop's offer: the choice is then yours.</li></ul>"
        "<p>The page says so each time.</p>"
        "<h2>What never counts</h2>"
        "<p>Commission. The Recommended is chosen by the same rule in shops that pay PicWise and in shops that pay it nothing. "
        "An offer does not count either: the Recommended is the middle price, on offer or not.</p>"
        "<h2>What it is not</h2>"
        "<p>A recommendation is information to help you decide, not a guarantee that a product is the best, the cheapest or "
        'the most suitable for you.</p><a class="pw-hs-link" href="/terms">Terms of Use \u203a</a>'
    )
    intro = "Every search shows four choices, and one of them is marked Recommended. This is the whole rule."
    return doc("How we choose the Recommended", "ABOUT PICWISE", intro, body)


def our_checks_page():
    body = (
        "<h2>What is checked</h2><ul>"
        "<li>The product's page opens, and it is the same product.</li>"
        "<li>The shop lists it as in stock.</li>"
        "<li>The price on the shop's page. Where PicWise can read it reliably and it differs from the shop's feed, "
        "PicWise shows the page's price.</li>"
        "<li>Its photo loads.</li>"
        "<li>It is in a category PicWise covers.</li></ul>"
        "<h2>When a check fails</h2><ul>"
        "<li>The product leaves PicWise that night, whatever the reason. It is checked again and comes back when it passes.</li>"
        "<li>A new product is shown only once it has passed.</li>"
        "<li>A product not checked for three days is not shown until it is checked again.</li>"
        "<li>A shop whose website PicWise cannot check is given three days. After that its products are not shown until it can be checked.</li></ul>"
        "<h2>What a check is not</h2>"
        "<p>A promise. Shops change prices and stock at any time, also after PicWise last looked. Check the details on the "
        "shop's website before you buy.</p>"
    )
    intro = "A wrong price or a product that is gone wastes your time. PicWise checks products on the shops' own websites, all day, every day."
    return doc("Our checks", "ABOUT PICWISE", intro, body)


# The shops of 2026-11-23 (the site's public note), as a buyer knows them; a name that names no
# shop ("Shopping Ads: Google & Bing") is left off the list (the specification, 7.3).
SHOPS_RAW = """Tooled Up|InStock UK|GamingKit|PCHUB.UK|Aosom UK|Finediam|Luxe Mattress Affiliation|Back to the Office|Plusshop UK|Bazta UK|Living with Luxury|MoreThisWay|Dream Interiors|Cheap Furniture Warehouse|Living and Home|Simply LED|Tirendo UK|Fila UK|Tyres UK|Lightsin UK|Doctor Blooms|Homespace Direct|The Foam People|Starlight Beds|Workout For Less|eFans Direct|The Sleep People|SafeFort (UK)|WATCH & WATCH|Bad Shirt Club|Juicy Couture UK|Cufflinks Gift Hub (UK)|Geepas Partner Program|Sport and Leisure UK|Viaduct Clothing|Pro-Camera|MOH|Affiliates - Spoiled Brat|Extreme Comfort|Watch Enclave Affiliate Programme|Angel Barocco|Ready Steady Bed|Webbs Motorcycles|ANCHOR & CREW|Needs No Label|MonsterPiercing -Quality Piercing Jewellery|Dean Morris Cards|Harfi|Laud Sleep|Red Run|TV Cables|Susan Caplan|Santoro Milan|Mint Outdoor|Macian|Pixie Dixie|Elixir Garden Supplies|Game Over|Opulensi Perfumes Lattafa Sapil Anfar|Lets Buy Books|SUNJOY UK|Cadbury Gifts Direct|Greenera (UK)|EXG Pro|Pro Espresso|Craft Buddy Shop|King & Country|Mr Farts|Gardenista|Stattics|Fitness Options|The Brush & Broom|Doulton|Cottsbury|Steam & Oak|Natkina|The Gerry Anderson Store|Kuishi|My Mini Maker|Wilna Kitchen|Five Star Direct|Happy Days Factory Flowers|Baccus (UK)|Bunches.co.uk|Optimum Nutrition UK|Bluebells Flora Florist|8wines UK|FLOWERFIX|THEGATHER|Cut Plastic Sheeting|Gains Nutrition|WAU|Spacelift Creators|Custom Splashbacks|aZengear|Silver Cloud Beauty|Boogie Bounce Fitness Rebounders|Atenai London Affiliation Marketing|Scottish Fine Soaps UK|Curo Skin|All Oils|Truthbrush|sitre|Purr and Mutt|BioGaia|Flowers & Plants Co.|DAME|Modmo"""


def our_shops_page():
    from itertools import groupby

    names = sorted({shop_display_name(n) for n in SHOPS_RAW.split("|")}, key=lambda n: n.lower())
    letter = lambda name: name[0].upper() if name[0].isalpha() else "0\u20139"
    groups = "".join(
        f'<p class="pw-hs-letter">{E(first)}</p><ul class="pw-hs-shoplist">' + "".join(f"<li>{E(name)}</li>" for name in group) + "</ul>"
        for first, group in groupby(names, key=letter)
    )
    body = (
        "<p>The shops on PicWise run a programme with Awin. PicWise earns a commission only from the shops that have accepted "
        "it into their programme; the others are shown by the same rule, and PicWise earns nothing from them.</p>"
        f"<h2>A to Z</h2>{groups}"
    )
    intro = f"PicWise shows products from {len(names)} UK shops tonight."
    return doc("Our shops", "ABOUT PICWISE", intro, body), len(names)


# ---- the three long pages in Greek, for the owner's own reading: never on the site ----
def greek(title, intro, body):
    main = (
        '<p class="pw-hs-el-band">ΜΕΤΑΦΡΑΣΗ ΓΙΑ ΣΕΝΑ \u00b7 δεν μπαίνει στο site</p>'
        '<article class="pw-hs-doc">'
        f'<h1 class="pw-hs-h1" style="margin:0">{E(title)}</h1>'
        f'<p class="pw-hs-doc-intro">{intro}</p>{body}'
        '<p class="pw-hs-doc-updated">Τελευταία ενημέρωση: 24 Νοεμβρίου 2026</p>'
        '</article><div style="height:20px"></div>'
    )
    return (
        "<!doctype html><html lang=\"el\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{E(title)}</title>{FONT_PRELOAD_HTML}"
        f"<style>{_PAGE_STYLES}{hs.HOME_STORE_STYLES}{PROTO_STYLES}</style>"
        f'</head><body class="pw-hs-body"><main class="pw-hs"><div class="pw-hs-main">{main}</div></main></body></html>'
    )


def _fake_link(text):
    return f'<p style="margin:10px 0 0;color:var(--hs-acc);font-weight:700;font-size:15px">{E(text)} \u203a</p>'


def how_it_works_el():
    body = (
        f'{step_h2("1", "Search = Αναζήτηση")}'
        "<p>Γράψε το προϊόν που θέλεις ή διάλεξε τμήμα. Το PicWise δείχνει μόνο αυτό το είδος: η αναζήτηση για καφετιέρα "
        "δείχνει καφετιέρες, όχι φίλτρα για καφετιέρες.</p>"
        f'{step_h2("2", "See = Δες")}'
        "<p>Τέσσερις επιλογές, από το φθηνότερο, η καθεμία στην τιμή του καταστήματος: στην τιμή προσφοράς του, όπου το "
        "κατάστημα δίνει τέτοια. Μόνο όσα το κατάστημα δηλώνει διαθέσιμα. Το «More» ανοίγει τις επόμενες τέσσερις, όσες φορές ζητήσεις.</p>"
        "<p>Η προσφορά είναι του καταστήματος και φαίνεται με τα δικά του λόγια και την ημερομηνία λήξης της. "
        "Το PicWise δεν υπολογίζει καμία τιμή μετά την προσφορά.</p>"
        f'{step_h2("3", "Decide = Απόφαση", gold=True)}'
        "<p>Μία από τις τέσσερις έχει τη σήμανση Recommended: το προϊόν στη μέση των τιμών, ώστε να μην την καθορίζει "
        "ούτε το φθηνότερο ούτε το ακριβότερο.</p>"
        f'{_fake_link("Πώς διαλέγουμε το Recommended")}'
        "<p>Μετά το κουμπί σε πηγαίνει στο κατάστημα. Το PicWise δεν είναι κατάστημα: κάθε αγορά γίνεται στο site του "
        "καταστήματος, με τους όρους του καταστήματος.</p>"
        "<h2>Από πού έρχονται οι τιμές και η διαθεσιμότητα</h2>"
        "<p>Από τα αρχεία προϊόντων (feeds) των ίδιων των καταστημάτων, που φτάνουν μέσω του δικτύου συνεργατών Awin και "
        "διαβάζονται ξανά κάθε βράδυ. Το PicWise ελέγχει επίσης προϊόντα στα site των καταστημάτων.</p>"
        f'{_fake_link("Οι έλεγχοί μας")}'
        "<h2>Πώς βγάζει χρήματα το PicWise</h2>"
        "<p>Προμήθεια από ορισμένα καταστήματα, μέσω του Awin, όταν αγοράσεις αφού ακολουθήσεις έναν σύνδεσμο του PicWise. "
        "Η τιμή που πληρώνεις είναι η ίδια, και η προμήθεια δεν αλλάζει ποτέ τη σειρά.</p>"
        f'{_fake_link("Δήλωση συνεργασιών (Affiliate disclosure)")}'
    )
    intro = ("Το PicWise είναι αναζήτηση προϊόντων για αγοραστές στο Ηνωμένο Βασίλειο που ξέρουν ήδη τι θέλουν να αγοράσουν. "
             "Δουλεύει σε τρία βήματα.")
    return greek("Πώς δουλεύει το PicWise", intro, body)


def how_we_choose_el():
    body = (
        "<h2>Η μεσαία τιμή</h2>"
        "<p>Το PicWise βάζει στη σειρά, από το φθηνότερο, κάθε προϊόν του είδους που ζήτησες και που τα καταστήματα δηλώνουν "
        "διαθέσιμο. Το Recommended είναι το προϊόν στη μέση αυτής της λίστας: από 45 προϊόντα, το 23ο. Ούτε το φθηνότερο ούτε το "
        "ακριβότερο. Η κάρτα του το γράφει: «Mid-priced for this category» (μεσαία τιμή για την κατηγορία).</p>"
        "<h2>Δύο δικλίδες</h2><ul>"
        "<li>Μία ακραία τιμή δεν μετακινεί τη μέση: προϊόν που κοστίζει τουλάχιστον τα διπλά από το αμέσως επόμενο ακριβότερο "
        "μένει έξω από το μέτρημα.</li>"
        "<li>Το Recommended έχει αριθμό barcode (EAN), που το PicWise χρειάζεται για να ελέγξει ότι το ίδιο προϊόν δεν είναι "
        "φθηνότερο σε άλλο κατάστημα. Αν το μεσαίο προϊόν δεν έχει, το PicWise παίρνει το κοντινότερο που έχει.</li></ul>"
        "<h2>Πότε δεν υπάρχει Recommended</h2><ul>"
        "<li>Όταν ταιριάζουν πολύ λίγα προϊόντα για να υπάρχει μεσαία τιμή.</li>"
        "<li>Όταν κανένα προϊόν μεσαίας τιμής δεν έχει αριθμό barcode.</li>"
        "<li>Όταν διαλέγεις τιμή στη μπάρα τιμών ή βλέπεις την προσφορά ενός καταστήματος: τότε η επιλογή είναι δική σου.</li></ul>"
        "<p>Η σελίδα το γράφει κάθε φορά.</p>"
        "<h2>Τι δεν μετράει ποτέ</h2>"
        "<p>Η προμήθεια. Το Recommended διαλέγεται με τον ίδιο κανόνα στα καταστήματα που πληρώνουν το PicWise και σε όσα δεν "
        "του πληρώνουν τίποτα. Ούτε η προσφορά μετράει: το Recommended είναι η μεσαία τιμή, με προσφορά ή χωρίς.</p>"
        "<h2>Τι δεν είναι</h2>"
        "<p>Μια σύσταση είναι πληροφορία για να σε βοηθήσει να αποφασίσεις, όχι εγγύηση ότι ένα προϊόν είναι το καλύτερο, "
        "το φθηνότερο ή το πιο κατάλληλο για σένα.</p>"
        f'{_fake_link("Όροι χρήσης (Terms of Use)")}'
    )
    intro = "Κάθε αναζήτηση δείχνει τέσσερις επιλογές, και μία από αυτές έχει τη σήμανση Recommended. Αυτός είναι όλος ο κανόνας."
    return greek("Πώς διαλέγουμε το Recommended", intro, body)


def our_checks_el():
    body = (
        "<h2>Τι ελέγχεται</h2><ul>"
        "<li>Η σελίδα του προϊόντος ανοίγει και είναι το ίδιο προϊόν.</li>"
        "<li>Το κατάστημα το δηλώνει διαθέσιμο.</li>"
        "<li>Η τιμή στη σελίδα του καταστήματος. Όπου το PicWise μπορεί να τη διαβάσει αξιόπιστα και διαφέρει από το feed του "
        "καταστήματος, το PicWise δείχνει την τιμή της σελίδας.</li>"
        "<li>Η φωτογραφία του φορτώνει.</li>"
        "<li>Ανήκει σε κατηγορία που καλύπτει το PicWise.</li></ul>"
        "<h2>Όταν ένας έλεγχος αποτύχει</h2><ul>"
        "<li>Το προϊόν φεύγει από το PicWise το ίδιο βράδυ, όποιος κι αν είναι ο λόγος. Ελέγχεται ξανά και επιστρέφει όταν περάσει.</li>"
        "<li>Ένα νέο προϊόν εμφανίζεται μόνο αφού περάσει τον έλεγχο.</li>"
        "<li>Προϊόν που δεν ελέγχθηκε για τρεις μέρες δεν εμφανίζεται μέχρι να ελεγχθεί ξανά.</li>"
        "<li>Σε κατάστημα που το PicWise δεν μπορεί να ελέγξει το site του δίνονται τρεις μέρες. Μετά, τα προϊόντα του δεν "
        "εμφανίζονται μέχρι να μπορεί να ελεγχθεί.</li></ul>"
        "<h2>Τι δεν είναι ο έλεγχος</h2>"
        "<p>Υπόσχεση. Τα καταστήματα αλλάζουν τιμές και διαθεσιμότητα οποιαδήποτε στιγμή, και μετά την τελευταία ματιά του "
        "PicWise. Έλεγξε τα στοιχεία στο site του καταστήματος πριν αγοράσεις.</p>"
    )
    intro = ("Μια λάθος τιμή ή ένα προϊόν που δεν υπάρχει πια σου τρώει χρόνο. Το PicWise ελέγχει προϊόντα στα site των ίδιων "
             "των καταστημάτων, όλη μέρα, κάθε μέρα.")
    return greek("Οι έλεγχοί μας", intro, body)


# ---- the phone strip and what "Add" opens on an iPhone ----
_SHARE = ('<svg class="pw-hs-sheet-ico" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
          'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Share"><path d="M12 15V4M8 7.5 12 3.5l4 4"/><path d="M7 11H6a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-1"/></svg>')


def home_page(*, strip=False, open_popular=False, facts=None):
    page = hs.render_home_store_page(catalogue=(118048, 109), indexable=True, trends=load_trends_panel(), facts=facts, parts=ALL)
    if strip:
        marker = '<div class="pw-hs-strip" id="pw-hs-strip" hidden>'
        assert page.count(marker) == 1
        page = page.replace(marker, '<div class="pw-hs-strip" id="pw-hs-strip">')
    if open_popular:
        marker = '<section class="pw-hs-pop" id="pw-trends"'
        assert page.count(marker) == 1
        page = page.replace(marker, '<section class="pw-hs-pop is-open" id="pw-trends"')
        page = page.replace('aria-expanded="false" aria-controls="pw-tp-list" data-more="Show all 10" data-less="Show fewer"><span>Show all 10</span>',
                            'aria-expanded="true" aria-controls="pw-tp-list" data-more="Show all 10" data-less="Show fewer"><span>Show fewer</span>')
    return page.replace("</style>", PROTO_STYLES + "</style>", 1)


def install_sheet_page(facts):
    sheet = (
        '<div class="pw-hs-veil"></div>'
        '<div class="pw-hs-sheet" role="dialog" aria-labelledby="pw-hs-sheet-title">'
        '<div class="pw-hs-sheet-grip"></div>'
        '<div class="pw-hs-sheet-head"><span class="pw-logo" aria-hidden="true"></span>'
        '<h2 class="pw-hs-sheet-title" id="pw-hs-sheet-title">Add PicWise to your home screen</h2></div>'
        '<ol class="pw-hs-sheet-steps">'
        f'<li class="pw-hs-sheet-step"><span class="pw-hs-step-n">1</span><span>Tap the Share button {_SHARE} in your browser\'s bar.</span></li>'
        '<li class="pw-hs-sheet-step"><span class="pw-hs-step-n">2</span><span>Choose <b>Add to Home Screen</b>.</span></li>'
        '<li class="pw-hs-sheet-step"><span class="pw-hs-step-n pw-hs-step-n-gold">3</span><span>Tap <b>Add</b>.</span></li>'
        "</ol>"
        '<button class="pw-hs-sheet-ok" type="button">Got it</button>'
        "</div>"
    )
    page = home_page(strip=True, facts=facts)
    return page.replace("</main></body>", f"</main>{sheet}</body>")


# ---- a search under the store's header (Part F), and an offer's products (Part C) ----
def _ean(number):
    body = str(number).zfill(12)
    total = sum(int(ch) * (3 if i % 2 else 1) for i, ch in enumerate(body))
    return body + str((10 - total % 10) % 10)


_COLUMNS = ("aw_product_id", "product_name", "brand_name", "product_type", "merchant_category", "aw_deep_link",
            "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "description", "data_provenance", "ean", "mpn")
# The site's own kettles of 2026-11-24, the first page of "kettle" and what "More" opens.
REAL = (
    ("k-rec", "1.7L 'Fluted' Cordless Rapid Boil Electric Kettle 3000W - Black", "34.99", "Geepas Partner Program", "kettle_black"),
    ("k-1", "1.7L Fast-Boil Cordless Beige Electric Kettle", "12.74", "Geepas Partner Program", "kettle_beige"),
    ("k-2", "1.7L Rapid-Boil Cordless White Electric Kettle", "12.74", "Geepas Partner Program", "kettle_white"),
    ("k-3", "1.7L Red Cordless Electric Rapid-Boil Kettle 2200W", "12.74", "Geepas Partner Program", "kettle_red"),
    ("k-4", "1.8L Matte Black Stainless Steel Electric Kettle 1800W", "12.74", "Geepas Partner Program", "kettle_black"),
    ("k-5", "1.8L Matte Cream Electric Stainless Steel Kettle 1800W", "12.74", "Geepas Partner Program", "kettle_beige"),
    ("k-6", "1.8L Stainless Steel Jug Kettle With LED Indicator", "12.74", "Geepas Partner Program", "kettle_steel"),
    ("k-7", "Stainless Steel 1 Litre Whistling Kettle | Zion", "12.95", "InStock UK", "kettle_steel"),
)


def _rows(total, *, only_geepas=False, port=8765):
    """`total` kettles: the real ones above and others, never on the first page, that only
    make the count and leave the real Recommended where the site has it (the 44th of 89:
    the dearest costs twice the next, so it is left out of the count)."""
    rows = []
    real = [r for r in REAL if not (only_geepas and r[3] != "Geepas Partner Program")]
    for index, (pid, title, price, shop, photo) in enumerate(real):
        rows.append((pid, title, price, shop, photo, _ean(500000100000 + index)))
    n = 0
    if only_geepas:
        for i in range(total - len(rows)):
            n += 1
            rows.append((f"g-{n}", f"Geepas Electric Kettle {n}", f"{13.24 + i * 1.1:.2f}", "Geepas Partner Program", "kettle_steel", _ean(500000300000 + n)))
        return rows
    cheaper = 43 - (len(real) - 1)
    for i in range(cheaper):                      # dearer than the cheapest, cheaper than the Recommended
        n += 1
        rows.append((f"f-{n}", f"Electric Kettle {n}", f"{13.49 + i * 0.55:.2f}", "InStock UK", "kettle_steel", _ean(500000200000 + n)))
    dearer = total - len(rows) - 1
    for i in range(dearer):
        n += 1
        rows.append((f"f-{n}", f"Electric Kettle {n}", f"{35.49 + i * 1.9:.2f}", "InStock UK", "kettle_steel", _ean(500000200000 + n)))
    n += 1
    rows.append((f"f-{n}", f"Electric Kettle {n}", "289.00", "InStock UK", "kettle_steel", _ean(500000200000 + n)))
    return rows


def _search_html(rows, query, *, min_price=None, max_price=None, port=8765):
    from fixture_support import fixture_description
    from picwise_app.app import PicwiseLocalApp
    from picwise_providers.awin_adapter import clear_awin_feed_parse_cache
    from picwise_providers.state import clear_provider_feed_pipeline_cache

    path = os.path.join(tempfile.mkdtemp(), "feed.csv")
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_COLUMNS)
        for pid, title, price, shop, photo, ean in rows:
            writer.writerow([pid, title, "Geepas" if "Geepas" in shop else "Zion", "Kettles", "Kitchen Appliances",
                             f"https://shop.example.invalid/p/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                             price, "GBP", "1", shop, fixture_description(), "local_test_fixture", ean, ""])
    os.environ["AWIN_FEED_FILE"] = path
    clear_awin_feed_parse_cache()
    clear_provider_feed_pipeline_cache()
    try:
        page = PicwiseLocalApp().picwise_reference_html(query, min_price=min_price, max_price=max_price)
        for pid, _title, _price, _shop, photo, _ean_ in rows:
            page = page.replace(f"https://fixture.example.invalid/img/{pid}.jpg", f"{PHOTO}{photo}.svg")
        return page
    finally:
        os.environ.pop("AWIN_FEED_FILE", None)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()


def _under_store_header(page, query):
    """The site's search page with the store's header (no departments: the cards stay on
    the first screen) and footer in the place of its own."""
    top = re.search(r'<header class="pw-topbar">.*?</header>', page, flags=re.S)
    box = re.search(r'<section class="pw-search-wrap".*?</section>', page, flags=re.S)
    foot = re.search(r'<footer class="pw-footer">.*?</footer>', page, flags=re.S)
    assert top and box and foot
    page = page.replace(box.group(0), "", 1)
    page = page.replace(top.group(0), header(nav=False, query=query), 1)
    page = page.replace(foot.group(0), hs._footer_html(ALL), 1)
    page = page.replace('<main class="pw-reference-viewport">', '<main class="pw-reference-viewport pw-hs pw-hs-search">', 1)
    page = page.replace("<body>", '<body class="pw-hs-body">', 1)
    # the store's styles after the page's own
    return page.replace("</style>", hs.HOME_STORE_STYLES + PROTO_STYLES + "</style>", 1)


def search_page(port=8765):
    return _under_store_header(_search_html(_rows(89, port=port), "kettle", port=port), "kettle")


def offer_products_page(port=8765):
    """An offer's products: the search's page for the kind, the shop's products the offer
    covers only. No Recommended (owner, 2026-11-15: a filter cancels it) and, proposed, no
    "Lowest price" and no place among the prices: they would compare inside one shop."""
    rows = _rows(51, only_geepas=True, port=port)
    top = max(float(row[2]) for row in rows)
    page = _search_html(rows, "kettle", max_price=top - 0.5, port=port)       # the dearest left out: 50, no Recommended
    plain = _search_html(rows[:-1] if float(rows[-1][2]) == top else rows, "kettle", port=port)
    bar = re.compile(r'<form class="pw-pricebar".*?</form>', flags=re.S)
    assert bar.search(page) and bar.search(plain)
    page = page.replace(bar.search(page).group(0), bar.search(plain).group(0), 1)
    head = re.search(r'<h1 class="pw-query-line">.*?</h1>', page, flags=re.S)
    assert head and "4 of 50" in page
    page = page.replace(head.group(0), '<h1 class="pw-query-line">Results for: kettle, at Geepas, cheapest first</h1>', 1)
    note = re.search(r'<p class="pw-reference-disclaimer">.*?</p>', page, flags=re.S)
    page = page.replace(
        note.group(0),
        '<p class="pw-reference-disclaimer">Geepas\'s kettles only, so there is no Recommended here. '
        "Prices and stock are as the shops list them.</p>"
        '<p class="pw-hs-oneshop"><a href="/search?q=kettle">See kettles from every shop \u203a</a></p>', 1)
    page, roles = re.subn(r'<div class="pw-role"><p class="pw-role-label">Lowest price</p></div>', "", page)
    page, places = re.subn(r'<p class="pw-card-description">(?:Cheapest|\d+\w\w cheapest) of \d+</p>', "", page)
    assert roles == 4 and places == 4, (roles, places)
    page = page.replace("&amp;max=60", "").replace("&amp;max=61", "")
    page = _under_store_header(page, "kettle")
    frame = '<div class="pw-reference-frame" id="pw-reference-frame">'
    assert page.count(frame) == 1
    box = (
        '<section class="pw-hs-offerbox" aria-label="The offer">'
        '<p class="pw-hs-eyebrow">OFFER AT GEEPAS</p>'
        f'{offer_lines("[An offer on one kind, in the shop\'s own words]", "4 Dec", "[CODE]")}'
        "</section>"
    )
    return page.replace(frame, frame + box, 1)


# The home page's facts for its pictures: the site's own Recommended of 2026-11-24, the
# eight shops with the most products, and three offers whose words are not read here.
_PICKS = {
    "drill": ("Bosch GBH 240 SDS Plus Hammer Drill", "£157.95", "Tooled Up"),
    "air fryer": ("HOMCOM Dual Air Fryer 8.5L Family Size, Double Basket Digital Air Fryer Oven with Smart Finish & 8 Presets", "£75.99", "Aosom UK"),
    "printer": ("HP Laser 179fnw Wireless Multifunction Color Printer, Copier, Scanner; Duplex", "£367.99", "Back to the Office"),
    "robot vacuum": ("Karcher RCV 3 Cordless Robotic Vacuum Cleaner and Mop", "£346.95", "Tooled Up"),
    "lawn mower": ("Greenworks 24v Cordless Brushless Lawnmower 330mm and Grass Trimmer 250mm", "£209.95", "Tooled Up"),
    "dehumidifier": ("Sealey SDH102 Dehumidifier", "£151.95", "Tooled Up"),
}
_TOP_SHOPS = ("Tooled Up", "InStock UK", "GamingKit", "PCHUB.UK", "Aosom UK", "Finediam", "Luxe Mattress Affiliation", "Back to the Office")


def picture_facts():
    day = lambda month, number: datetime(2026, month, number, tzinfo=timezone.utc)
    return HomeFacts(
        prepared_at=PREPARED,
        picks=tuple(
            Pick(query=k.query, kind=k.kind, link=k.link, title=_PICKS[k.query][0], price=_PICKS[k.query][1],
                 shop=_PICKS[k.query][2], image=f"{ART}{k.drawing}.svg")
            for k in LISTS.recommended
        ),
        tiles_with_products=None,
        shops=tuple(shop_display_name(name) for name in _TOP_SHOPS),
        shop_count=109,
        offers=(
            OfferCard(shop="InStock UK", offer_id="o1", title="[The shop's offer, in its own words]", end=day(11, 30), products=40),
            OfferCard(shop="Geepas", offer_id="o2", title="[An offer on one kind, in the shop's own words]", end=day(12, 4), products=12),
            OfferCard(shop="Aosom UK", offer_id="o4", title="[The shop's offer, in its own words]", end=day(12, 1), products=9),
        ),
    )


def photo_stand_ins():
    """The kettle's drawing in the colours the real kettles' titles name: {file name: svg}."""
    spec = importlib.util.spec_from_file_location("draw_home_art", REPO + "/tools/draw_home_art.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    def kettle(colour):
        return m.svg(
            m.r(54, 154, 92, 12, 6) + m.s("M132 74 Q174 80 160 142", m.DK, 11) + m.p("M68 82 L38 70 L44 86 L64 102 Z", colour)
            + m.p("M68 64 H132 L144 156 H56 Z", colour) + m.r(80, 92, 8, 44, 4, m.W, 'fill-opacity="0.55"')
            + m.r(74, 54, 52, 12, 6) + m.r(92, 46, 16, 10, 4)
        )

    colours = {"kettle_black": "#2f3642", "kettle_beige": "#e2d2b4", "kettle_white": "#eef0f3", "kettle_red": "#c2473d", "kettle_steel": "#b7c0cb"}
    return {name + ".svg": kettle(colour) for name, colour in colours.items()}


def all_pages(port=8765):
    """{name: html} of every picture; `home_computer` is for a screen 1,280 px wide, the rest for a phone."""
    facts = picture_facts()
    pages = {
        "department": department_page(),
        "departments": departments_page(),
        "offers": offers_page(),
        "offer_kinds": offer_kinds_page(),
        "offer_products": offer_products_page(port),
        "how_picwise_works": how_it_works_page(),
        "how_picwise_works_el": how_it_works_el(),
        "how_we_choose": how_we_choose_page(),
        "how_we_choose_el": how_we_choose_el(),
        "our_checks": our_checks_page(),
        "our_checks_el": our_checks_el(),
        "our_shops": our_shops_page()[0],
        "search": search_page(port),
        "home_strip_sheet": install_sheet_page(facts),
        "home_popular_open": home_page(open_popular=True, facts=facts),
        "home_computer": home_page(facts=facts),
    }
    return pages


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = sys.argv[1]
    os.makedirs(os.path.join(out, "proto"), exist_ok=True)
    for name, text in photo_stand_ins().items():
        with open(os.path.join(out, "proto", name), "w", encoding="utf-8") as handle:
            handle.write(text)
    if not os.path.lexists(os.path.join(out, "assets")):
        os.symlink(REPO + "/assets", os.path.join(out, "assets"))
    for name, text in all_pages().items():
        with open(os.path.join(out, name + ".html"), "w", encoding="utf-8") as handle:
            handle.write(text)
    print(f"{len(os.listdir(out)) - 2} pages in {out}")
