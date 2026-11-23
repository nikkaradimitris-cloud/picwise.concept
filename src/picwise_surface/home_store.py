"""The home page as a store (`docs/PICWISE_HOME_STORE_SPEC.md`, section 5; task H3).

The owner, 2026-11-23: the home page «μοιάζει σαν 100% μηχανή πρέπει να γίνει πιο
κατάστημα πρόσεξε όχι e-shop»; of the fifth picture proposed, «Κράτα αυτό και ανέβασε το»;
then «Όλα μαζί», «Με χρυσοκίτρινο banner», «Στα προϊόντα της στο PicWise», and «Ναι σε όλα»
("See" on the second step, not "Compare"). The picture: `docs/design/picwise_home_store_2026-11-23.html`.

Behind a switch (`data/home_store_switch.json`, `home_store_on`): off, the home page is the
one of 2026-11-12 (`reference.render_picwise_reference_surface`), byte for byte; on, this
page. It is turned on only on the owner's word, and not while a part of the specification's
section 7 is missing (`PARTS_BUILT`).

What the page is made of:

- its lists (`data/home_store.json`, `load_home_lists`): the banners, the kinds of the
  Recommended band, the six sections and their tiles, the departments;
- the month's ten as today (`trends.load_trends_panel`), drawn as tiles;
- what this process knows of its catalogue, worked out once for each catalogue and never
  while a page is drawn (`HomeFacts`, `picwise_surface.home_store_facts`): each kind's
  Recommended as its search shows it, which tiles' searches have products, the shops;
- the products and shops a search holds (`state.peek_search_catalogue_counts`).

A section whose data is not known is left out, never filled (`docs/ANTI_FAKE_TRUST_RULES.md`).
A link to a part of the specification's section 7 not built yet is not drawn (its section 6).
The search box, History, Favourites and "What is PicWise?" are the site's own, with the same
markup and scripts as on every page: only their look changes on this page's dark header.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .browser_lists import (
    BROWSER_LISTS_SCRIPT,
    BROWSER_LISTS_STYLES,
    HEAD_SCRIPT,
    header_buttons_html,
    panels_html,
)
from .fonts import FONT_PRELOAD_HTML
from .legal import SHORT_AFFILIATE_NOTICE
from .page_styles import _PAGE_STYLES
from .reference import (
    _HOME_TITLE,
    _MIC_ICON,
    _MIC_TITLE,
    _PRICE_FIRST_RECOMMENDED_LABEL,
    _SEARCH_PLACEHOLDER,
    _WHAT_IS_PICWISE,
    _at_least,
    _scanning_screen_html,
)
from .search_script import _SEARCH_SCRIPT
from .seo import (
    NOINDEX_META,
    SITE_LANGUAGE,
    declares_to_google,
    home_structured_data_html,
    icon_links_html,
    indexable_head_html,
)
from .trends import FOLDED_ROWS, MAX_TREND_ROWS, TRENDS_SCRIPT, TrendRow, TrendsPanel

_ROOT = Path(__file__).resolve().parents[2]
SWITCH_PATH = _ROOT / "data" / "home_store_switch.json"
LISTS_PATH = _ROOT / "data" / "home_store.json"
# A test's own copy of the switch or of the lists.
SWITCH_ENV = "PICWISE_HOME_STORE_SWITCH_PATH"
LISTS_ENV = "PICWISE_HOME_STORE_LISTS_PATH"
# Where the page's drawings are served from (`tools/draw_home_art.py` writes them).
ART_PATH = "/assets/home/art/"
BACKGROUND_PATH = "/assets/home/ov/"

# The parts of the specification's section 7, as task H4 builds them: "departments" (Part
# B), "offers" (Part C), "pages" (Part D, the four pages). A link to a part not named here
# is not drawn (the specification's section 6), so the page never leads to a page that
# does not answer. Each part is added here with its routes, in the same commit.
PARTS_BUILT: frozenset[str] = frozenset()
PART_ADDRESSES = {
    "how_picwise_works": "/how-picwise-works",
    "how_we_choose": "/how-we-choose",
    "our_checks": "/our-checks",
    "our_shops": "/our-shops",
    "departments": "/departments",
    "offers": "/offers",
}

# ---- the words a visitor reads (the picture the owner kept; changed only on his word) ----

STRIP_TITLE = "PicWise on your phone"
STRIP_LINE = "Add it to your home screen"
STRIP_ADD = "Add"
STRIP_CLOSE = "Close"
ALL_DEPARTMENTS = "All departments"
PROMISE_EYEBROW = "HOW PICWISE WORKS"
# The owner's own text (2026-11-24, «πρόσθεσε τα κείμενα που σου έδωσα»; before it, his
# phrase of 2026-11-23, «μπαίνεις μπερδεμένος και φεύγεις αποφασισμένος»).
PROMISE_HEADING = ("Arrive confused.", "Leave decided.")
# Under it, word for word (owner, 2026-11-24). "100+ UK Shops" while the catalogue holds
# more than 100 shops; else the count itself, so that it is never false (the
# specification, 5.3).
TRUST_SHOPS_MANY = "100+ UK Shops"
TRUST_SHOPS_COUNT = "{count} UK Shops"
TRUST_TICKS = ("30-Day Price History", "Zero Cookies & Tracking")
# Step 2 is "See", not "Compare": PicWise is never presented as price comparison (owner,
# 2026-11-12: «θα κλείσουν πολλές πόρτες»; 2026-11-23: «Ναι σε όλα»).
STEPS = (
    ("1", "Search", "Type what you need"),
    ("2", "See", "4 choices, cheapest first"),
    ("3", "Decide", "One is Recommended"),
)
OFFERS_TITLE = "Offers from the shops"
OFFERS_SUB = "In the shops' own words. Never a made-up discount."
OFFERS_ALL = "See all offers"
OFFER_ENDS = "Ends {day}"
OFFER_LINK = "See the products"
POPULAR_MORE = "Show all {count}"
POPULAR_LESS = "Show fewer"
POPULAR_NOT_SOLD = "Not in our shops yet"
BAND_EYEBROW = "RECOMMENDED"
BAND_UPDATED = "UPDATED {day}"
BAND_TITLE = "One honest pick for each kind"
BAND_LINE = "The middle price of each kind. The commission never decides it."
BAND_LINK = "How we choose the Recommended"
DEPARTMENTS_TITLE = "Browse by department"
VOWS_EYEBROW = "THE PICWISE PROMISE"
VOWS_TITLE = "What you can count on"
VOWS_FIGURE_NIGHTLY = ("Nightly", "stock and price updates")
# The owner's three points, word for word (2026-11-24): the words before the colon bold.
VOWS = (
    ("4 honest choices, zero paid rankings:", "Commissions never change the order of results or our “Recommended” pick."),
    ("Real price history:", "Check the last 30 nights at a glance. No fake discounts, no “hurry up” tricks."),
    (
        "100% Private (No Cookies):",
        "No pop-ups, no accounts. Your favourites and search history stay on your own device—we never see them.",
    ),
)
VOWS_LINK = "How PicWise works"
SHOPS_TITLE = "Some of our {count} UK shops"
SHOPS_LINK = "See all shops"
BACK_TO_TOP = "BACK TO TOP"
FOOTER_PICWISE = "PicWise"
FOOTER_HELP = "Help & legal"
FOOTER_WHERE = "United Kingdom · Prices in £"
FOOTER_META = "© 2026 PicWise. All rights reserved."
# In the footer, in the place of the "Cookies" link (owner, 2026-11-24: «αντί για Cookie
# Policy»). The cookies' page stays at its address and opens from the Privacy page.
FOOTER_NO_COOKIES = "No Cookie Policy — because we don't use any."

_THEMES = frozenset({"gold", "ink", "blue"})
_GROUNDS = frozenset({"white", "mist", "sand", "pale"})
_LAYOUTS = frozenset({"grid", "row"})
# A section with fewer tiles than this is left out (the specification, 5.8).
MIN_TILES = 2
# The Recommended band needs at least two cards (the specification, 5.7).
MIN_PICKS = 2

# ---- the switch ----

_SWITCH_CACHE: dict[str, Any] = {"key": None, "on": False}
_FORCED: list[bool | None] = [None]


def home_store_on() -> bool:
    """Whether the home page is this page: the switch's `on` is `true`, and nothing else
    counts as on (a file missing or unreadable is off). Read again only when the file
    changes; a deployment restarts the site, which reads it afresh."""
    if _FORCED[0] is not None:
        return bool(_FORCED[0])
    path = Path(str(os.environ.get(SWITCH_ENV) or "").strip() or SWITCH_PATH)
    try:
        stat = path.stat()
    except OSError:
        return False
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if _SWITCH_CACHE["key"] != key:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            on = isinstance(payload, dict) and payload.get("on") is True
        except (OSError, ValueError):
            on = False
        _SWITCH_CACHE.update(key=key, on=on)
    return bool(_SWITCH_CACHE["on"])


def set_home_store_on_for_tests(value: bool | None) -> None:
    """Turn the switch for a test (`None` goes back to the file)."""
    _FORCED[0] = value


# ---- the lists ----


@dataclass(frozen=True)
class Tile:
    name: str
    query: str
    drawing: str


@dataclass(frozen=True)
class Section:
    title: str
    arrow: str
    department: str
    layout: str
    tiles: tuple[Tile, ...]


@dataclass(frozen=True)
class Banner:
    theme: str
    eyebrow: str
    title: str
    line: str
    button: str
    part: str
    href: str
    drawings: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Department:
    slug: str
    name: str
    short: str
    drawing: str


@dataclass(frozen=True)
class Kind:
    """A kind of the Recommended band: its search's words, its name, its link's words."""

    query: str
    kind: str
    link: str
    drawing: str


@dataclass(frozen=True)
class HomeLists:
    banners: tuple[Banner, ...]
    recommended: tuple[Kind, ...]
    sections: tuple[Section, ...]
    departments: tuple[Department, ...]
    popular_drawings: dict[str, str]


_LISTS_CACHE: dict[str, Any] = {"key": None, "lists": None}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _lists_from(payload: Any) -> HomeLists:
    if not isinstance(payload, dict):
        payload = {}
    banners = []
    for item in payload.get("banners") or ():
        if not isinstance(item, dict) or _text(item.get("theme")) not in _THEMES:
            continue
        drawings = tuple(
            (_text(pair[0]), _text(pair[1]))
            for pair in item.get("drawings") or ()
            if isinstance(pair, (list, tuple)) and len(pair) == 2 and _text(pair[1]) in _GROUNDS
        )
        if len(drawings) != 3:
            continue
        banners.append(
            Banner(
                theme=_text(item.get("theme")),
                eyebrow=_text(item.get("eyebrow")),
                title=_text(item.get("title")),
                line=_text(item.get("line")),
                button=_text(item.get("button")),
                part=_text(item.get("part")),
                href=_text(item.get("href")),
                drawings=drawings,
            )
        )
    kinds = tuple(
        Kind(
            query=_text(item.get("query")),
            kind=_text(item.get("kind")),
            link=_text(item.get("link")),
            drawing=_text(item.get("drawing")),
        )
        for item in payload.get("recommended") or ()
        if isinstance(item, dict) and _text(item.get("query"))
    )
    sections = []
    for item in payload.get("sections") or ():
        if not isinstance(item, dict) or _text(item.get("layout")) not in _LAYOUTS:
            continue
        tiles = tuple(
            Tile(name=_text(tile.get("name")), query=_text(tile.get("query")), drawing=_text(tile.get("drawing")))
            for tile in item.get("tiles") or ()
            if isinstance(tile, dict) and _text(tile.get("name")) and _text(tile.get("query"))
        )
        sections.append(
            Section(
                title=_text(item.get("title")),
                arrow=_text(item.get("arrow")),
                department=_text(item.get("department")),
                layout=_text(item.get("layout")),
                tiles=tiles,
            )
        )
    departments = tuple(
        Department(
            slug=_text(item.get("slug")),
            name=_text(item.get("name")),
            short=_text(item.get("short")),
            drawing=_text(item.get("drawing")),
        )
        for item in payload.get("departments") or ()
        if isinstance(item, dict) and _text(item.get("slug")) and _text(item.get("name"))
    )
    drawings = payload.get("popular_drawings") or {}
    return HomeLists(
        banners=tuple(banners),
        recommended=kinds,
        sections=tuple(sections),
        departments=departments,
        popular_drawings={
            _text(word).lower(): _text(name) for word, name in drawings.items() if _text(word) and _text(name)
        }
        if isinstance(drawings, dict)
        else {},
    )


def load_home_lists() -> HomeLists:
    """The page's lists, read again only when their file changes; empty lists when it is
    missing or unreadable (then the sections that need them are left out)."""
    path = Path(str(os.environ.get(LISTS_ENV) or "").strip() or LISTS_PATH)
    try:
        stat = path.stat()
        key = (str(path), stat.st_mtime_ns, stat.st_size)
    except OSError:
        key = (str(path), 0, 0)
    if _LISTS_CACHE["key"] != key or _LISTS_CACHE["lists"] is None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {}
        _LISTS_CACHE.update(key=key, lists=_lists_from(payload))
    return _LISTS_CACHE["lists"]


# ---- what this process knows of its catalogue (`home_store_facts` works it out) ----


@dataclass(frozen=True)
class Pick:
    """A kind's Recommended, as its search's card shows it tonight."""

    query: str
    kind: str
    link: str
    title: str
    price: str
    shop: str
    image: str


@dataclass(frozen=True)
class OfferCard:
    """A shop's offer for the home page's row: its words as Awin gives them, never a
    price, a percentage or a saving worked out by PicWise (owner, 2026-11-19)."""

    shop: str
    offer_id: str
    title: str
    end: datetime
    # How many products shown tonight it covers; the row is ordered by it.
    products: int


@dataclass(frozen=True)
class HomeFacts:
    """What the page knows of the catalogue it was worked out for (`prepared_at`)."""

    prepared_at: datetime | None
    picks: tuple[Pick, ...] = ()
    # The words of the tiles whose search has products tonight; None while not counted,
    # and then every tile is drawn (the specification, 5.8).
    tiles_with_products: frozenset[str] | None = None
    # The shops with the most products shown, by their names as a buyer knows them.
    shops: tuple[str, ...] = ()
    shop_count: int = 0
    # The shops' offers that cover products shown tonight, one a shop (the specification, 5.5).
    offers: tuple[OfferCard, ...] = ()


# ---- pieces ----

_CHEVRON = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>'
)
_CHEVRON_DOWN = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
)
_UP = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg>'
)
# The three lines under the heading: a blue tick drawn before each, no letter.
_TRUST_TICK = (
    '<svg class="pw-hs-trust-tick" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
)
_TICK = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
)
_STAR = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
    '<path d="M12 2.6l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.5l-5.9 3.1 1.2-6.5L2.5 9.5l6.6-.9z"/></svg>'
)
_MENU = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
    'stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
)


def _search_href(query: str) -> str:
    return f"/search?q={quote(query, safe='')}"


def _department_href(slug: str) -> str:
    return f"/department/{quote(slug, safe='-')}"


def _drawing(name: str, size: int, *, lazy: bool = True) -> str:
    """A drawing of a kind, decorative: the words beside it name it."""
    if not name:
        return ""
    loading = ' loading="lazy"' if lazy else ""
    return (
        f'<img class="pw-hs-art" src="{ART_PATH}{escape(name, quote=True)}.svg" alt="" '
        f'width="{size}" height="{size}"{loading} decoding="async">'
    )


def _background(name: str, *, lazy: bool = True) -> str:
    loading = ' loading="lazy"' if lazy else ""
    return (
        f'<img class="pw-hs-ov" src="{BACKGROUND_PATH}ov_{name}.svg" alt="" width="400" height="400"'
        f'{loading} decoding="async">'
    )


def _link(href: str, label: str, *, cls: str = "pw-hs-link") -> str:
    return f'<a class="{cls}" href="{escape(href, quote=True)}">{escape(label)} ›</a>'


def _arrow(href: str, label: str) -> str:
    return f'<a class="pw-hs-arrow" href="{escape(href, quote=True)}" aria-label="{escape(label, quote=True)}">{_CHEVRON}</a>'


def _head2(title: str, title_id: str, arrow: str = "", *, sub: str = "") -> str:
    sub_html = f'<p class="pw-hs-sub">{escape(sub)}</p>' if sub else ""
    return (
        '<div class="pw-hs-head2">'
        f'<div><h2 class="pw-hs-h2" id="{title_id}">{escape(title)}</h2>{sub_html}</div>'
        f"{arrow}</div>"
    )


def _strip_html() -> str:
    """The phone strip (the specification, 5.1): drawn hidden; what it does is Part E."""
    return (
        '<div class="pw-hs-strip" id="pw-hs-strip" hidden>'
        f'<button class="pw-hs-strip-close" type="button" aria-label="{STRIP_CLOSE}">&#215;</button>'
        '<span class="pw-logo" aria-hidden="true"></span>'
        f'<span class="pw-hs-strip-text"><span class="pw-hs-strip-title">{escape(STRIP_TITLE)}</span>'
        f'<span class="pw-hs-strip-line">{escape(STRIP_LINE)}</span></span>'
        f'<button class="pw-hs-strip-add" type="button">{escape(STRIP_ADD)}</button>'
        "</div>"
    )


def search_box_html() -> str:
    """The search box: the same markup as every search page's (`reference`), whose
    scripts read its ids: suggestions, the faint completion, the voice, the loading."""
    return (
        '<section class="pw-search-wrap" aria-label="Search">'
        '<form class="pw-search-shell" action="/search" method="get" role="search">'
        '<span class="pw-search-icon" aria-hidden="true"></span>'
        '<span class="pw-input-wrap">'
        f'<input class="pw-search-input" type="search" name="q" value="" placeholder="{escape(_SEARCH_PLACEHOLDER, quote=True)}" aria-label="{escape(_SEARCH_PLACEHOLDER, quote=True)}" autocomplete="off" spellcheck="false" autocapitalize="off" enterkeyhint="search" role="combobox" aria-autocomplete="both" aria-controls="pw-suggest-list" aria-expanded="false">'
        '<span class="pw-ghost" aria-hidden="true"><span class="pw-ghost-typed" id="pw-ghost-typed"></span><span class="pw-ghost-rest" id="pw-ghost-rest"></span></span>'
        "</span>"
        f'<button class="pw-mic-button" id="pw-mic" type="button" aria-label="Search by voice" aria-pressed="false" title="{escape(_MIC_TITLE, quote=True)}" hidden>{_MIC_ICON}</button>'
        '<button class="pw-search-button" type="submit" aria-label="Search">'
        '<span class="pw-search-button-icon" aria-hidden="true"></span>'
        "</button></form>"
        '<ul class="pw-suggest" id="pw-suggest-list" role="listbox" aria-label="Suggestions" hidden></ul>'
        "</section>"
    )


def _header_html(lists: HomeLists, parts: frozenset[str]) -> str:
    nav = ""
    if "departments" in parts and lists.departments:
        nav = (
            '<nav class="pw-hs-nav" aria-label="Departments">'
            f'<a class="pw-hs-nav-all" href="{PART_ADDRESSES["departments"]}">{_MENU}{escape(ALL_DEPARTMENTS)}</a>'
            + "".join(
                f'<a href="{_department_href(item.slug)}">{escape(item.short or item.name)}</a>'
                for item in lists.departments
            )
            + "</nav>"
        )
    return (
        '<header class="pw-hs-head" id="top">'
        '<div class="pw-hs-head-in">'
        '<div class="pw-hs-head-row">'
        '<a class="pw-hs-brand" href="/" aria-label="PicWise home">'
        '<span class="pw-logo" aria-hidden="true"></span><span class="pw-hs-brand-name">picwise</span></a>'
        '<div class="pw-actions pw-hs-actions">'
        f"{header_buttons_html()}"
        '<section class="pw-info-wrap" id="pw-info-wrap"><button class="pw-topbar-control pw-info-link" id="pw-info-button" type="button" aria-label="What is PicWise?" aria-expanded="false" aria-controls="pw-tooltip"><span class="pw-info-txt">What is PicWise?</span><span class="pw-info-icon" aria-hidden="true">?</span></button><div class="pw-tooltip" id="pw-tooltip">'
        f"{escape(_WHAT_IS_PICWISE)}"
        "</div></section></div>"
        "</div>"
        f"{search_box_html()}"
        "</div>"
        f"{nav}"
        "</header>"
    )


def trust_shops_line(catalogue: tuple[int, int] | None) -> str:
    """"100+ UK Shops" while there are more than 100; the count itself at 100 or fewer;
    "" while the count is not known (the specification, 5.3)."""
    shops = int(catalogue[1] or 0) if catalogue else 0
    if shops <= 0:
        return ""
    return TRUST_SHOPS_MANY if shops > 100 else TRUST_SHOPS_COUNT.format(count=f"{shops:,}")


def _trust_ticks_html(catalogue: tuple[int, int] | None) -> str:
    lines = tuple(line for line in (trust_shops_line(catalogue), *TRUST_TICKS) if line)
    items = "".join(f'<li class="pw-hs-trust-item">{_TRUST_TICK}{escape(line)}</li>' for line in lines)
    return f'<ul class="pw-hs-trust">{items}</ul>'


def _promise_band_html(catalogue: tuple[int, int] | None = None) -> str:
    steps = "".join(
        f'<li class="pw-hs-step"><span class="pw-hs-step-n{" pw-hs-step-n-gold" if number == "3" else ""}">{number}</span>'
        f'<span class="pw-hs-step-name">{escape(name)}</span><span class="pw-hs-step-line">{escape(line)}</span></li>'
        for number, name, line in STEPS
    )
    first, second = PROMISE_HEADING
    return (
        '<section class="pw-hs-promise" aria-labelledby="pw-hs-h1">'
        f'<p class="pw-hs-eyebrow">{escape(PROMISE_EYEBROW)}</p>'
        f'<h1 class="pw-hs-h1" id="pw-hs-h1">{escape(first)}<br>{escape(second)}</h1>'
        f"{_trust_ticks_html(catalogue)}"
        f'<ol class="pw-hs-steps">{steps}</ol>'
        "</section>"
    )


def _banner_href(banner: Banner, parts: frozenset[str], *, offers_shown: bool) -> str:
    """Where a banner leads, or "" when it is not drawn: its part not built, its
    destination not decided, or, for the offers' banner, no offer to show."""
    if banner.part not in parts or not banner.href:
        return ""
    if banner.part == "offers" and not offers_shown:
        return ""
    return banner.href


def _banners_html(lists: HomeLists, parts: frozenset[str], *, offers_shown: bool) -> str:
    """The banners whose part is built (the specification, 5.4), in a row that stops on
    each; the offers' banner only while there is an offer to show (5.5)."""
    drawn = []
    for banner in lists.banners:
        href = _banner_href(banner, parts, offers_shown=offers_shown)
        if not href:
            continue
        first = not drawn
        (big, big_ground), (a, a_ground), (b, b_ground) = banner.drawings
        drawn.append(
            f'<a class="pw-hs-banner pw-hs-banner-{banner.theme}" href="{escape(href, quote=True)}">'
            f'<span class="pw-hs-banner-glow" aria-hidden="true">{_background("streak", lazy=not first)}</span>'
            '<span class="pw-hs-banner-text">'
            f'<span class="pw-hs-banner-eyebrow">{escape(banner.eyebrow)}</span>'
            f'<span class="pw-hs-banner-title">{escape(banner.title)}</span>'
            f'<span class="pw-hs-banner-line">{escape(banner.line)}</span>'
            f'<span class="pw-hs-banner-button">{escape(banner.button)}</span></span>'
            f'<span class="pw-hs-banner-big pw-hs-{big_ground}" aria-hidden="true">'
            f'{"" if big_ground == "white" else _background("soft", lazy=not first)}{_drawing(big, 150, lazy=not first)}</span>'
            f'<span class="pw-hs-banner-a pw-hs-{a_ground}" aria-hidden="true">{_drawing(a, 80, lazy=not first)}</span>'
            f'<span class="pw-hs-banner-b pw-hs-{b_ground}" aria-hidden="true">{_drawing(b, 80, lazy=not first)}</span>'
            "</a>"
        )
    if not drawn:
        return ""
    dots = (
        '<div class="pw-hs-dots pw-needs-js" aria-hidden="true">'
        + "".join(f'<span class="pw-hs-dot{" is-on" if index == 0 else ""}"></span>' for index in range(len(drawn)))
        + "</div>"
        if len(drawn) > 1
        else ""
    )
    return (
        '<section class="pw-hs-banners" aria-label="Featured">'
        f'<div class="pw-hs-banner-row" id="pw-hs-banner-row">{"".join(drawn)}</div>'
        f"{dots}</section>"
    )


def offer_href(card: OfferCard) -> str:
    """Where an offer's card leads: its products inside PicWise (owner, 2026-11-23: «Στα
    προϊόντα της στο PicWise»), the page Part C builds (the specification, 7.2)."""
    return f"{PART_ADDRESSES['offers']}/{quote(card.offer_id, safe='')}"


def _offer_end_words(end: datetime) -> str:
    year = "" if end.year == datetime.now(end.tzinfo).year else f" {end.year}"
    return OFFER_ENDS.format(day=f"{end.day} {end:%b}{year}")


def _offers_html(facts: HomeFacts | None, parts: frozenset[str]) -> str:
    """The shops' offers (the specification, 5.5): only once Part C is built, and only
    while one covers products shown tonight; one a shop, the shop's own words."""
    offers = tuple(facts.offers) if facts is not None else ()
    if "offers" not in parts or not offers:
        return ""
    cards = "".join(
        f'<a class="pw-hs-offer" href="{escape(offer_href(card), quote=True)}">'
        f'<span class="pw-hs-offer-shop">{escape(card.shop)}</span>'
        f'<span class="pw-hs-offer-title">{escape(card.title)}</span>'
        f'<span class="pw-hs-offer-end">{escape(_offer_end_words(card.end))}</span>'
        f'<span class="pw-hs-offer-link">{escape(OFFER_LINK)} \u203a</span>'
        "</a>"
        for card in offers
    )
    return (
        '<section class="pw-hs-offers" aria-labelledby="pw-hs-offers-title">'
        f'{_head2(OFFERS_TITLE, "pw-hs-offers-title", _arrow(PART_ADDRESSES["offers"], OFFERS_ALL), sub=OFFERS_SUB)}'
        f'<div class="pw-hs-scroll pw-hs-offer-row">{cards}</div>'
        "</section>"
    )


def _change_words(row: TrendRow) -> str:
    places = max(int(row.change_by or 0), 0)
    if row.change == "up" and places:
        return f"▲ {places}"
    if row.change == "down" and places:
        return f"▼ {places}"
    if row.change == "new":
        return "New"
    return ""


def _popular_html(panel: TrendsPanel | None, lists: HomeLists) -> str:
    """The month's ten as tiles (the specification, 5.6): the rules of today's panel
    (`trends.render_trends_panel`), its rows, its fold, its source; only drawn so."""
    if panel is None or not _text(panel.ranking_source):
        return ""
    rows = sorted(
        (row for row in panel.rows if _text(row.name) and int(row.rank or 0) > 0),
        key=lambda row: int(row.rank),
    )[:MAX_TREND_ROWS]
    if not rows:
        return ""
    items = []
    for row in rows:
        query = _text(row.search_query or row.name)
        drawing = lists.popular_drawings.get(query.lower(), "")
        meta_parts = []
        change = _change_words(row)
        if change:
            meta_parts.append(change)
        sold = row.offers is None or int(row.offers or 0) > 0
        if row.offers is not None and int(row.offers) > 0:
            words = f"{int(row.offers):,} {'product' if int(row.offers) == 1 else 'products'}"
            if _text(row.from_price):
                words += f" from {_text(row.from_price)}"
            meta_parts.append(words)
        elif row.offers is not None:
            meta_parts.append(POPULAR_NOT_SOLD)
        meta = f'<span class="pw-hs-pop-meta">{escape(" · ".join(meta_parts))}</span>' if meta_parts else ""
        inner = (
            f'<span class="pw-hs-pop-pic pw-hs-sand">{_background("soft")}{_drawing(drawing, 140)}'
            f'<span class="pw-hs-pop-rank">{int(row.rank)}</span></span>'
            f'<span class="pw-hs-pop-name">{escape(_text(row.name))}</span>{meta}'
        )
        if sold:
            items.append(
                f'<li class="pw-hs-pop-item"><a class="pw-hs-pop-tile" href="{_search_href(query)}">{inner}</a></li>'
            )
        else:
            # A product PicWise's shops do not sell never links to an empty search.
            items.append(f'<li class="pw-hs-pop-item"><div class="pw-hs-pop-tile pw-hs-off">{inner}</div></li>')
    country = _text(panel.country)
    if country == "United Kingdom":
        heading = "Most popular in the UK"
    elif country:
        heading = f"Most popular in {country}"
    else:
        heading = "Most popular this month"
    kicker = " · ".join(part for part in (_text(panel.period), country) if part)
    sources = [f"Ranking: {_text(panel.ranking_source)}."]
    if any(int(row.offers or 0) > 0 for row in rows) and _text(panel.offers_source):
        sources.append(f"Products and prices: {_text(panel.offers_source)}.")
    more = (
        f'<button class="pw-hs-more pw-needs-js" id="pw-tp-more" type="button" aria-expanded="false" '
        f'aria-controls="pw-tp-list" data-more="{escape(POPULAR_MORE.format(count=len(rows)), quote=True)}" '
        f'data-less="{escape(POPULAR_LESS, quote=True)}"><span>{escape(POPULAR_MORE.format(count=len(rows)))}</span>'
        f"{_CHEVRON_DOWN}</button>"
        if len(rows) > FOLDED_ROWS
        else ""
    )
    return (
        '<section class="pw-hs-pop" id="pw-trends" aria-labelledby="pw-hs-pop-title">'
        + (f'<p class="pw-hs-eyebrow">{escape(kicker)}</p>' if kicker else "")
        + f'<h2 class="pw-hs-h2" id="pw-hs-pop-title">{escape(heading)}</h2>'
        f'<ol class="pw-hs-pop-list" id="pw-tp-list">{"".join(items)}</ol>'
        f"{more}"
        f'<p class="pw-hs-source">{escape(" ".join(sources))}</p>'
        "</section>"
    )


def _updated_words(prepared_at: datetime | None) -> str:
    if prepared_at is None:
        return ""
    return BAND_UPDATED.format(day=f"{prepared_at.day} {prepared_at:%b}".upper())


def _band_html(facts: HomeFacts | None, parts: frozenset[str]) -> str:
    """The Recommended band (the specification, 5.7): each kind's Recommended as its
    search shows it tonight, a link to that search; left out under two cards."""
    picks = tuple(facts.picks) if facts is not None else ()
    if len(picks) < MIN_PICKS:
        return ""
    cards = "".join(
        f'<a class="pw-hs-pick" href="{_search_href(pick.query)}">'
        f'<span class="pw-hs-pick-pic"><img class="pw-hs-pick-img" src="{escape(pick.image, quote=True)}" '
        f'alt="" width="144" height="144" loading="lazy" decoding="async"></span>'
        f'<span class="pw-hs-pick-kind">{escape(pick.kind)}</span>'
        f'<span class="pw-hs-pick-title">{escape(pick.title)}</span>'
        f'<span class="pw-hs-pick-price">{escape(pick.price)}</span>'
        f'<span class="pw-hs-pick-shop">at {escape(pick.shop)}</span>'
        f'<span class="pw-hs-pick-chip">{escape(_PRICE_FIRST_RECOMMENDED_LABEL)}</span>'
        f'<span class="pw-hs-pick-link">{escape(pick.link)} ›</span>'
        "</a>"
        for pick in picks
    )
    updated = _updated_words(facts.prepared_at if facts is not None else None)
    eyebrow = BAND_EYEBROW + (f" · {updated}" if updated else "")
    link = (
        _link(PART_ADDRESSES["how_we_choose"], BAND_LINK, cls="pw-hs-link pw-hs-band-link")
        if "pages" in parts
        else ""
    )
    return (
        '<section class="pw-hs-band" id="pw-hs-band" aria-labelledby="pw-hs-band-title">'
        '<div class="pw-hs-band-head">'
        f'<p class="pw-hs-band-eyebrow">{_STAR}{escape(eyebrow)}</p>'
        f'<h2 class="pw-hs-band-title" id="pw-hs-band-title">{escape(BAND_TITLE)}</h2>'
        f'<p class="pw-hs-band-line">{escape(BAND_LINE)}</p>'
        "</div>"
        f'<div class="pw-hs-band-row">{cards}</div>'
        f"{link}</section>"
    )


def _departments_html(lists: HomeLists, parts: frozenset[str]) -> str:
    if "departments" not in parts or not lists.departments:
        return ""
    tiles = "".join(
        f'<a class="pw-hs-dept" href="{_department_href(item.slug)}">'
        f'<span class="pw-hs-dept-pic pw-hs-mist">{_background("soft")}{_drawing(item.drawing, 96)}</span>'
        f'<span class="pw-hs-dept-name">{escape(item.name)}</span></a>'
        for item in lists.departments
    )
    return (
        '<section class="pw-hs-depts" aria-labelledby="pw-hs-depts-title">'
        f'{_head2(DEPARTMENTS_TITLE, "pw-hs-depts-title", _arrow(PART_ADDRESSES["departments"], ALL_DEPARTMENTS))}'
        f'<div class="pw-hs-scroll">{tiles}</div>'
        "</section>"
    )


def _tiles_shown(section: Section, facts: HomeFacts | None) -> tuple[Tile, ...]:
    """The tiles whose search has products tonight; all of them while that is not
    counted (the specification, 5.8): never a link to an empty answer once it is."""
    known = facts.tiles_with_products if facts is not None else None
    if known is None:
        return section.tiles
    return tuple(tile for tile in section.tiles if tile.query in known)


def _section_html(section: Section, index: int, facts: HomeFacts | None, parts: frozenset[str]) -> str:
    tiles = _tiles_shown(section, facts)
    if len(tiles) < MIN_TILES:
        return ""
    title_id = f"pw-hs-sec-{index}"
    arrow = (
        _arrow(_department_href(section.department), section.arrow or section.title)
        if "departments" in parts and section.department
        else ""
    )
    if section.layout == "grid":
        body = "".join(
            f'<a class="pw-hs-tile" href="{_search_href(tile.query)}">'
            f'<span class="pw-hs-tile-pic pw-hs-sand">{_background("soft")}{_drawing(tile.drawing, 144)}</span>'
            f'<span class="pw-hs-tile-name">{escape(tile.name)}</span></a>'
            for tile in tiles
        )
        return (
            f'<section class="pw-hs-sec" aria-labelledby="{title_id}">'
            f"{_head2(section.title, title_id, arrow)}"
            f'<div class="pw-hs-grid">{body}</div></section>'
        )
    body = "".join(
        f'<a class="pw-hs-tile" href="{_search_href(tile.query)}">'
        f'<span class="pw-hs-tile-pic pw-hs-mist">{_background("ring")}{_drawing(tile.drawing, 104)}</span>'
        f'<span class="pw-hs-tile-name">{escape(tile.name)}</span></a>'
        for tile in tiles
    )
    return (
        f'<section class="pw-hs-sec pw-hs-sec-row" aria-labelledby="{title_id}">'
        f"{_head2(section.title, title_id, arrow)}"
        f'<div class="pw-hs-scroll">{body}</div></section>'
    )


def _vows_html(catalogue: tuple[int, int] | None, parts: frozenset[str]) -> str:
    figures = []
    if catalogue and int(catalogue[0] or 0) > 0 and int(catalogue[1] or 0) > 0:
        products, shops = int(catalogue[0]), int(catalogue[1])
        figures.append((_at_least(products), "product" if products == 1 else "products"))
        figures.append((f"{shops:,}", "UK shop" if shops == 1 else "UK shops"))
    figures.append(VOWS_FIGURE_NIGHTLY)
    figures_html = "".join(
        f'<div class="pw-hs-fig"><span class="pw-hs-fig-big">{escape(big)}</span>'
        f'<span class="pw-hs-fig-small">{escape(small)}</span></div>'
        for big, small in figures
    )
    vows = "".join(
        f'<li class="pw-hs-vow"><span class="pw-hs-tick">{_TICK}</span><span class="pw-hs-vow-text">'
        f"<strong>{escape(lead)}</strong> {escape(text)}</span></li>"
        for lead, text in VOWS
    )
    link = _link(PART_ADDRESSES["how_picwise_works"], VOWS_LINK) if "pages" in parts else ""
    return (
        '<section class="pw-hs-vows" aria-labelledby="pw-hs-vows-title">'
        '<div class="pw-hs-card">'
        f'<p class="pw-hs-eyebrow">{escape(VOWS_EYEBROW)}</p>'
        f'<h2 class="pw-hs-h2 pw-hs-card-title" id="pw-hs-vows-title">{escape(VOWS_TITLE)}</h2>'
        f'<div class="pw-hs-figures pw-hs-figures-{len(figures)}">{figures_html}</div>'
        f'<ul class="pw-hs-vow-list">{vows}</ul>'
        f"{link}</div></section>"
    )


def _shops_html(facts: HomeFacts | None, parts: frozenset[str]) -> str:
    if facts is None or not facts.shops or facts.shop_count <= 0:
        return ""
    chips = "".join(f'<li class="pw-hs-chip">{escape(name)}</li>' for name in facts.shops)
    link = _link(PART_ADDRESSES["our_shops"], SHOPS_LINK) if "pages" in parts else ""
    return (
        '<section class="pw-hs-shops" aria-labelledby="pw-hs-shops-title">'
        f'<h2 class="pw-hs-h2 pw-hs-shops-title" id="pw-hs-shops-title">{escape(SHOPS_TITLE.format(count=f"{facts.shop_count:,}"))}</h2>'
        f'<ul class="pw-hs-chips">{chips}</ul>'
        f"{link}</section>"
    )


def footer_links(parts: frozenset[str]) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    """The footer's two columns (the specification, 5.9): the four new pages only once
    Part D is built."""
    picwise: list[tuple[str, str]] = [("About PicWise", "/about")]
    if "pages" in parts:
        picwise += [
            ("How PicWise works", PART_ADDRESSES["how_picwise_works"]),
            ("How we choose the Recommended", PART_ADDRESSES["how_we_choose"]),
            ("Our checks", PART_ADDRESSES["our_checks"]),
            ("Our shops", PART_ADDRESSES["our_shops"]),
        ]
    help_links = (
        ("Contact", "/contact"),
        ("Terms", "/terms"),
        ("Privacy", "/privacy"),
        ("Affiliate disclosure", "/affiliate-disclosure"),
    )
    return ((FOOTER_PICWISE, tuple(picwise)), (FOOTER_HELP, help_links))


def _footer_html(parts: frozenset[str]) -> str:
    columns = "".join(
        '<div class="pw-hs-foot-col">'
        f'<h2 class="pw-hs-foot-h">{escape(title)}</h2>'
        + "".join(
            f'<a class="pw-hs-foot-link" href="{escape(href, quote=True)}">{escape(label)}</a>' for label, href in links
        )
        + "</div>"
        for title, links in footer_links(parts)
    )
    return (
        '<footer class="pw-hs-foot"><div class="pw-hs-foot-in">'
        f'<nav class="pw-hs-foot-cols" aria-label="PicWise public footer links">{columns}</nav>'
        '<div class="pw-hs-foot-rule"></div>'
        '<div class="pw-hs-foot-brand"><span class="pw-logo" aria-hidden="true"></span>'
        '<span class="pw-hs-foot-name">picwise</span></div>'
        f'<p class="pw-hs-foot-where">{escape(FOOTER_WHERE)}</p>'
        f'<p class="pw-hs-foot-notice">{escape(SHORT_AFFILIATE_NOTICE)}</p>'
        f'<p class="pw-hs-foot-cookies">{escape(FOOTER_NO_COOKIES)}</p>'
        f'<p class="pw-hs-foot-meta">{escape(FOOTER_META)}</p>'
        "</div></footer>"
    )


# The "What is PicWise?" button's opening and closing, as on every page (`reference`).
_INFO_SCRIPT = (
    "(function(){"
    'var infoWrap=document.getElementById("pw-info-wrap");'
    'var infoButton=document.getElementById("pw-info-button");'
    "if(!infoWrap||!infoButton){return;}"
    "var setOpen=function(isOpen){"
    'infoWrap.classList.toggle("is-open",isOpen);'
    'infoButton.setAttribute("aria-expanded",isOpen?"true":"false");'
    "};"
    "setOpen(false);"
    'infoButton.addEventListener("click",function(event){'
    "event.stopPropagation();"
    'setOpen(!infoWrap.classList.contains("is-open"));'
    "});"
    'document.addEventListener("click",function(event){'
    "if(!infoWrap.contains(event.target)){setOpen(false);}"
    "});"
    'document.addEventListener("keydown",function(event){'
    'if(event.key==="Escape"){setOpen(false);}'
    "});"
    "})();"
)

# The page's own script: the banners' dots follow the row's scroll; a Recommended card
# whose photo fails leaves the row, as a card of a search leaves its page (PROJECT_RULES.md
# 2), and the band goes with fewer than two cards. Nothing else waits for it.
HOME_STORE_SCRIPT = r"""
(function(){
"use strict";
var row=document.getElementById("pw-hs-banner-row");
if(row){
  var dots=document.querySelectorAll(".pw-hs-dot");
  var mark=function(){
    var first=row.firstElementChild;if(!first||!dots.length){return;}
    var step=first.getBoundingClientRect().width+12;
    var at=Math.max(0,Math.min(dots.length-1,Math.round(row.scrollLeft/Math.max(step,1))));
    for(var i=0;i<dots.length;i++){dots[i].classList.toggle("is-on",i===at);}
  };
  row.addEventListener("scroll",function(){window.requestAnimationFrame(mark);},{passive:true});
}
var band=document.getElementById("pw-hs-band");
if(band){
  var gone=function(img){
    var card=img.closest?img.closest(".pw-hs-pick"):null;
    if(card&&card.parentNode){card.parentNode.removeChild(card);}
    if(band.querySelectorAll(".pw-hs-pick").length<__MIN_PICKS__){band.hidden=true;}
  };
  var imgs=band.querySelectorAll("img.pw-hs-pick-img");
  for(var i=0;i<imgs.length;i++){
    if(imgs[i].complete&&imgs[i].naturalWidth===0&&imgs[i].getAttribute("src")){gone(imgs[i]);continue;}
    imgs[i].addEventListener("error",function(e){gone(e.target);});
  }
}
})();
""".replace("__MIN_PICKS__", str(MIN_PICKS))


# ---- the page's styles: a phone first; inside the site's width on a computer ----
# One family of colours (owner, 2026-11-23: «γίνεσαι παιδική χαρά»; the specification,
# 5.12). Whatever is tapped is 48 px at least and 8 px from the next; no word under 12 px.
HOME_STORE_STYLES = (
    ":root{--hs-ink:#0f2442;--hs-ink2:#1a335c;--hs-ink3:#2c4674;--hs-cream:#f8f5ef;--hs-line:#e7e0d4;"
    "--hs-muted:#566278;--hs-acc:#1a4fb7;--hs-gold:#f9bd3b;--hs-pale:#fdf0cc;--hs-sand:#efe6d6;"
    "--hs-mist:#dfe8f7;--hs-blue:#1f5fd6;}"
    ".pw-hs-body{background:var(--hs-cream);}"
    ".pw-hs{color:var(--hs-ink);}"
    ".pw-hs a:focus-visible,.pw-hs button:focus-visible{outline:2px solid var(--hs-blue);outline-offset:2px;}"
    ".pw-hs-head a:focus-visible,.pw-hs-head button:focus-visible,.pw-hs-band a:focus-visible,"
    ".pw-hs-foot a:focus-visible,.pw-hs-back:focus-visible{outline-color:#fff;}"
    # the phone strip
    ".pw-hs-strip{display:flex;align-items:center;gap:8px;padding:6px 12px 6px 0;background:#f1ede6;border-bottom:1px solid #e3dccf;}"
    ".pw-hs-strip[hidden]{display:none;}"
    ".pw-hs-strip-close{flex:0 0 auto;width:48px;height:48px;border:0;background:transparent;color:var(--hs-muted);font:inherit;font-size:22px;padding:0;cursor:pointer;}"
    ".pw-hs-strip-text{flex:1;min-width:0;display:flex;flex-direction:column;}"
    ".pw-hs-strip-title{font-size:15px;font-weight:800;color:var(--hs-ink);}"
    ".pw-hs-strip-line{font-size:13px;color:var(--hs-muted);}"
    ".pw-hs-strip-add{flex:0 0 auto;display:inline-flex;align-items:center;height:48px;padding:0 20px;border-radius:999px;border:1.5px solid var(--hs-ink);background:#fff;color:var(--hs-ink);font:inherit;font-size:14px;font-weight:700;cursor:pointer;}"
    # the header
    ".pw-hs-head{position:relative;z-index:20;background:var(--hs-ink);}"
    ".pw-hs-head-in{padding:10px 16px 0;}"
    ".pw-hs-head-row{display:flex;align-items:center;justify-content:space-between;gap:8px;}"
    ".pw-hs-brand{display:flex;align-items:center;gap:10px;min-height:48px;text-decoration:none;color:#fff;}"
    ".pw-hs-brand-name{font-size:24px;font-weight:800;letter-spacing:-.6px;text-transform:lowercase;}"
    ".pw-hs-actions{gap:8px;}"
    ".pw-hs .pw-head-btn,.pw-hs .pw-info-link{position:relative;width:48px;height:48px;padding:0;border:0;border-radius:999px;background:var(--hs-ink2);color:#fff;justify-content:center;font-size:17px;font-weight:800;}"
    ".pw-hs .pw-head-btn[aria-expanded=true],.pw-hs .pw-info-link[aria-expanded=true],.pw-hs .pw-info-link:hover{background:var(--hs-ink3);border-color:transparent;color:#fff;}"
    # The words stay the buttons' names for a screen reader; the eye sees the icon.
    ".pw-hs .pw-head-txt,.pw-hs .pw-info-txt{display:block;position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0;}"
    ".pw-hs .pw-info-icon{display:inline;}"
    ".pw-hs .pw-count{position:absolute;top:-3px;right:-3px;background:var(--hs-gold);color:var(--hs-ink);}"
    ".pw-hs .pw-search-wrap{max-width:none;margin:10px 0 12px;}"
    ".pw-hs .pw-search-shell{height:56px;padding:0 4px 0 14px;gap:8px;border:0;border-radius:16px;box-shadow:none;}"
    ".pw-hs .pw-search-shell:focus-within{box-shadow:0 0 0 3px rgba(255,255,255,.55);}"
    ".pw-hs .pw-search-icon{display:none;}"
    ".pw-hs .pw-search-input{height:48px;font-size:16px;}"
    ".pw-hs .pw-ghost{font-size:16px;}"
    ".pw-hs .pw-mic-button{width:48px;height:48px;border:0;border-radius:12px;background:#eef2f8;color:var(--hs-ink);}"
    ".pw-hs .pw-search-button{width:48px;height:48px;border-radius:12px;background:var(--hs-blue);}"
    ".pw-hs .pw-suggest-item{padding:12px 18px;}"
    ".pw-hs-nav{display:flex;gap:8px;overflow-x:auto;padding:0 12px;background:var(--hs-ink2);scrollbar-width:none;}"
    ".pw-hs-nav::-webkit-scrollbar{display:none;}"
    ".pw-hs-nav a{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;gap:6px;height:48px;min-width:48px;padding:0 8px;color:#dbe5f5;font-size:14px;font-weight:600;text-decoration:none;white-space:nowrap;}"
    ".pw-hs-nav a.pw-hs-nav-all{color:#fff;font-weight:700;}"
    # the promise
    ".pw-hs-promise{padding:18px 16px 6px;}"
    ".pw-hs-eyebrow{margin:0;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--hs-acc);}"
    ".pw-hs-h1{margin:6px 0 12px;font-size:27px;line-height:1.12;font-weight:800;letter-spacing:-.6px;color:var(--hs-ink);}"
    ".pw-hs-trust{list-style:none;margin:0 0 14px;padding:0;display:flex;flex-wrap:wrap;gap:6px 14px;}"
    ".pw-hs-trust-item{display:flex;align-items:center;gap:6px;font-size:13px;line-height:1.35;font-weight:700;color:var(--hs-ink);}"
    ".pw-hs-trust-tick{flex:0 0 auto;color:var(--hs-blue);}"
    ".pw-hs-steps{list-style:none;margin:0;padding:14px 0 0;border-top:1px solid var(--hs-line);display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}"
    ".pw-hs-step{display:flex;flex-direction:column;gap:5px;}"
    ".pw-hs-step-n{width:28px;height:28px;border-radius:999px;background:var(--hs-ink);color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;}"
    ".pw-hs-step-n-gold{background:var(--hs-gold);color:var(--hs-ink);}"
    ".pw-hs-step-name{margin-top:2px;font-size:15px;line-height:1.2;font-weight:800;color:var(--hs-ink);}"
    ".pw-hs-step-line{font-size:13px;line-height:1.35;color:var(--hs-muted);}"
    # grounds and drawings
    ".pw-hs-white{background:#fff;}.pw-hs-mist{background:var(--hs-mist);}.pw-hs-sand{background:var(--hs-sand);}.pw-hs-pale{background:var(--hs-pale);}"
    ".pw-hs-ov{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;}"
    ".pw-hs-art{position:relative;display:block;}"
    # the banners
    ".pw-hs-banners{padding:14px 0 0;}"
    ".pw-hs-banner-row{display:flex;gap:12px;overflow-x:auto;padding:0 16px 4px;scroll-snap-type:x mandatory;scroll-padding:0 16px;scrollbar-width:none;}"
    ".pw-hs-banner-row::-webkit-scrollbar{display:none;}"
    ".pw-hs-banner{position:relative;flex:0 0 auto;display:block;width:320px;height:430px;border-radius:22px;overflow:hidden;text-decoration:none;scroll-snap-align:start;}"
    ".pw-hs-banner-gold{background:var(--hs-gold);color:var(--hs-ink);}"
    ".pw-hs-banner-ink{background:var(--hs-ink);color:#fff;}"
    ".pw-hs-banner-blue{background:var(--hs-blue);color:#fff;}"
    ".pw-hs-banner-glow{position:absolute;left:0;right:0;bottom:0;height:215px;-webkit-mask-image:linear-gradient(to bottom,transparent 0%,#000 55%);mask-image:linear-gradient(to bottom,transparent 0%,#000 55%);}"
    ".pw-hs-banner-text{position:absolute;left:22px;top:22px;right:22px;display:flex;flex-direction:column;align-items:flex-start;}"
    ".pw-hs-banner-eyebrow{font-size:12px;font-weight:800;letter-spacing:.08em;}"
    ".pw-hs-banner-title{margin-top:8px;font-size:28px;line-height:1.1;font-weight:800;letter-spacing:-.5px;}"
    ".pw-hs-banner-line{margin-top:8px;font-size:15px;line-height:1.35;font-weight:500;}"
    ".pw-hs-banner-button{margin-top:12px;display:inline-flex;align-items:center;height:48px;padding:0 20px;border-radius:999px;font-size:14px;font-weight:700;background:#fff;color:var(--hs-ink);}"
    ".pw-hs-banner-gold .pw-hs-banner-button{background:var(--hs-ink);color:#fff;}"
    ".pw-hs-banner-big,.pw-hs-banner-a,.pw-hs-banner-b{position:absolute;overflow:hidden;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 22px rgba(0,0,0,.22);}"
    ".pw-hs-banner-big{left:16px;bottom:18px;width:164px;height:172px;border-radius:18px;transform:rotate(-3deg);}"
    ".pw-hs-banner-a{right:14px;bottom:110px;width:118px;height:84px;border-radius:16px;transform:rotate(3deg);}"
    ".pw-hs-banner-b{right:18px;bottom:16px;width:118px;height:84px;border-radius:16px;transform:rotate(-2deg);}"
    ".pw-hs-dots{justify-content:center;gap:6px;padding:10px 0 0;}"
    ".pw-hs-dot{width:6px;height:6px;border-radius:3px;background:#d3d0c8;transition:width .2s;}"
    ".pw-hs-dot.is-on{width:22px;background:var(--hs-ink);}"
    # headings of a section
    ".pw-hs-head2{display:flex;align-items:center;justify-content:space-between;gap:12px;}"
    ".pw-hs-h2{margin:4px 0 0;font-size:21px;line-height:1.2;font-weight:800;letter-spacing:-.3px;color:var(--hs-ink);}"
    ".pw-hs-sub{margin:3px 0 0;font-size:13px;line-height:1.35;color:var(--hs-muted);}"
    ".pw-hs-arrow{flex:0 0 auto;width:48px;height:48px;margin-right:-12px;display:flex;align-items:center;justify-content:center;color:var(--hs-ink);}"
    ".pw-hs-link{display:inline-flex;align-items:center;min-height:48px;color:var(--hs-acc);font-size:14px;font-weight:700;text-decoration:none;}"
    # the shops' offers
    ".pw-hs-offers{margin-top:14px;padding:14px 0 16px;background:#fff;}"
    ".pw-hs-offers .pw-hs-head2{padding:0 16px;}"
    ".pw-hs-offer{flex:0 0 256px;box-sizing:border-box;display:flex;flex-direction:column;gap:6px;padding:14px;border-radius:16px;background:#fff;border:1px solid var(--hs-line);text-decoration:none;color:var(--hs-ink);}"
    ".pw-hs-offer-shop{align-self:flex-start;padding:5px 10px;border-radius:999px;background:var(--hs-sand);font-size:12px;font-weight:800;}"
    ".pw-hs-offer-title{font-size:15px;line-height:1.3;font-weight:700;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}"
    ".pw-hs-offer-end{font-size:12px;color:var(--hs-muted);}"
    ".pw-hs-offer-link{margin-top:auto;padding-top:4px;font-size:13px;font-weight:700;color:var(--hs-acc);}"
    # the month's ten
    ".pw-hs-pop{margin-top:12px;padding:18px 16px;background:#fff;}"
    ".pw-hs-pop .pw-hs-h2{margin-bottom:12px;}"
    ".pw-hs-pop-list{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 12px;}"
    f".pw-js .pw-hs-pop:not(.is-open) .pw-hs-pop-item:nth-child(n+{FOLDED_ROWS + 1}){{display:none;}}"
    ".pw-hs-pop-tile{display:flex;flex-direction:column;gap:8px;text-decoration:none;color:var(--hs-ink);}"
    ".pw-hs-pop-pic{position:relative;height:171px;border-radius:16px;display:flex;align-items:center;justify-content:center;overflow:hidden;}"
    ".pw-hs-pop-rank{position:absolute;left:10px;top:10px;width:32px;height:32px;border-radius:999px;background:#fff;color:var(--hs-ink);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:800;box-shadow:0 2px 6px rgba(0,0,0,.15);}"
    ".pw-hs-pop-name{font-size:15px;line-height:1.25;font-weight:600;}"
    ".pw-hs-pop-meta{font-size:13px;line-height:1.3;color:var(--hs-muted);}"
    ".pw-hs-off .pw-hs-pop-name{color:var(--hs-muted);}"
    ".pw-hs-more{margin-top:14px;align-items:center;justify-content:center;gap:6px;width:100%;height:48px;border-radius:999px;border:1.5px solid var(--hs-ink);background:#fff;color:var(--hs-ink);font:inherit;font-size:14px;font-weight:700;cursor:pointer;}"
    ".pw-hs-more svg{transition:transform .2s;}"
    ".pw-hs-pop.is-open .pw-hs-more svg{transform:rotate(180deg);}"
    ".pw-hs-source{margin:12px 0 0;font-size:12px;line-height:1.45;color:var(--hs-muted);}"
    # the Recommended band
    ".pw-hs-band{margin-top:12px;padding:22px 0 14px;background:var(--hs-ink);}"
    ".pw-hs-band[hidden]{display:none;}"
    ".pw-hs-band-head{padding:0 16px;}"
    ".pw-hs-band-eyebrow{margin:0;display:flex;align-items:center;gap:6px;font-size:12px;font-weight:800;letter-spacing:.08em;color:var(--hs-gold);}"
    ".pw-hs-band-title{margin:6px 0 0;font-size:22px;line-height:1.2;font-weight:800;letter-spacing:-.3px;color:#fff;}"
    ".pw-hs-band-line{margin:6px 0 0;font-size:14px;line-height:1.4;color:#cdd8ea;}"
    ".pw-hs-band-row{display:flex;gap:12px;overflow-x:auto;padding:14px 16px 4px;}"
    ".pw-hs-pick{flex:0 0 168px;box-sizing:border-box;display:flex;flex-direction:column;padding:10px;border-radius:16px;background:#fff;text-decoration:none;color:var(--hs-ink);}"
    ".pw-hs-pick-pic{height:144px;border-radius:12px;background:#f4efe6;display:flex;align-items:center;justify-content:center;overflow:hidden;}"
    ".pw-hs-pick-img{width:120px;height:120px;object-fit:contain;mix-blend-mode:multiply;}"
    ".pw-hs-pick-kind{margin-top:10px;font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--hs-acc);}"
    ".pw-hs-pick-title{margin-top:4px;height:34px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;font-size:13px;line-height:1.3;font-weight:600;}"
    ".pw-hs-pick-price{margin-top:8px;font-size:20px;font-weight:800;}"
    ".pw-hs-pick-shop{margin-top:2px;font-size:12px;color:var(--hs-muted);}"
    ".pw-hs-pick-chip{margin-top:8px;padding:6px 8px;border-radius:8px;background:var(--hs-pale);color:#5c4300;font-size:12px;line-height:1.3;font-weight:600;}"
    ".pw-hs-pick-link{margin-top:10px;font-size:13px;font-weight:700;color:var(--hs-acc);}"
    ".pw-hs-band-link{margin:6px 16px 0;color:var(--hs-gold);}"
    # departments, sections
    ".pw-hs-depts{padding:20px 0 0;}"
    ".pw-hs-depts .pw-hs-head2,.pw-hs-sec-row .pw-hs-head2{padding:0 16px;}"
    ".pw-hs-scroll{display:flex;gap:12px;overflow-x:auto;padding:10px 16px 4px;}"
    ".pw-hs-dept{flex:0 0 112px;display:flex;flex-direction:column;gap:8px;text-decoration:none;color:var(--hs-ink);}"
    ".pw-hs-dept-pic{position:relative;height:112px;border-radius:18px;display:flex;align-items:center;justify-content:center;overflow:hidden;}"
    ".pw-hs-dept-name{font-size:13px;line-height:1.25;font-weight:600;text-align:center;}"
    ".pw-hs-sec{margin-top:12px;padding:14px 16px 18px;background:#fff;}"
    ".pw-hs-sec-row{padding:14px 0 18px;}"
    ".pw-hs-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 12px;margin-top:10px;}"
    ".pw-hs-tile{display:flex;flex-direction:column;gap:8px;text-decoration:none;color:var(--hs-ink);}"
    ".pw-hs-tile-pic{position:relative;height:171px;border-radius:16px;display:flex;align-items:center;justify-content:center;overflow:hidden;}"
    ".pw-hs-scroll .pw-hs-tile{flex:0 0 150px;}"
    ".pw-hs-scroll .pw-hs-tile-pic{height:150px;}"
    ".pw-hs-tile-name{font-size:15px;line-height:1.25;font-weight:600;}"
    # the promise, the shops
    ".pw-hs-vows{padding:24px 16px 0;}"
    ".pw-hs-card{padding:20px 18px 10px;border-radius:20px;background:#fff;border:1px solid var(--hs-line);}"
    ".pw-hs-card-title{margin-top:6px;font-size:22px;}"
    ".pw-hs-figures{margin-top:16px;padding:14px 0;border-top:1px solid var(--hs-line);border-bottom:1px solid var(--hs-line);display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;}"
    ".pw-hs-fig{display:flex;flex-direction:column;gap:2px;}"
    ".pw-hs-fig-big{font-size:21px;line-height:1.15;font-weight:800;letter-spacing:-.4px;color:var(--hs-ink);}"
    ".pw-hs-fig-small{font-size:12px;line-height:1.3;color:var(--hs-muted);}"
    ".pw-hs-vow-list{list-style:none;margin:16px 0 0;padding:0 0 10px;display:flex;flex-direction:column;gap:14px;}"
    ".pw-hs-vow{display:flex;align-items:flex-start;gap:10px;}"
    ".pw-hs-tick{flex:0 0 auto;width:24px;height:24px;border-radius:999px;background:var(--hs-blue);color:#fff;display:flex;align-items:center;justify-content:center;}"
    ".pw-hs-vow-text{font-size:15px;line-height:1.45;color:#33425c;}"
    ".pw-hs-vow-text strong{font-weight:800;color:var(--hs-ink);}"
    ".pw-hs-shops{padding:22px 16px 0;}"
    ".pw-hs-shops-title{margin:0 0 12px;font-size:19px;}"
    ".pw-hs-chips{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px;}"
    ".pw-hs-chip{display:inline-flex;align-items:center;height:36px;padding:0 14px;border-radius:999px;background:#fff;border:1px solid var(--hs-line);font-size:13px;font-weight:600;color:var(--hs-ink);}"
    # back to top, the footer
    ".pw-hs-back{display:flex;align-items:center;justify-content:center;gap:8px;height:52px;margin-top:18px;background:var(--hs-ink2);color:#eef2f8;font-size:13px;font-weight:700;letter-spacing:.06em;text-decoration:none;}"
    ".pw-hs-foot{background:var(--hs-ink);color:#d5deee;}"
    ".pw-hs-foot-in{padding:24px 16px 36px;}"
    ".pw-hs-foot-cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;}"
    ".pw-hs-foot-col{display:flex;flex-direction:column;gap:8px;}"
    ".pw-hs-foot-h{margin:0;font-size:14px;font-weight:800;color:#fff;}"
    ".pw-hs-foot-link{display:flex;align-items:center;min-height:48px;color:#d5deee;font-size:14px;line-height:1.3;text-decoration:none;}"
    ".pw-hs-foot-link:hover{color:#fff;text-decoration:underline;}"
    ".pw-hs-foot-rule{height:1px;margin:20px 0;background:var(--hs-ink3);}"
    ".pw-hs-foot-brand{display:flex;align-items:center;gap:10px;}"
    ".pw-hs-foot-name{font-size:20px;font-weight:800;letter-spacing:-.5px;color:#fff;}"
    ".pw-hs-foot-where{margin:10px 0 0;font-size:13px;color:#aebbd3;}"
    ".pw-hs-foot-notice{margin:14px 0 0;font-size:13px;line-height:1.55;color:#aebbd3;}"
    ".pw-hs-foot-cookies{margin:14px 0 0;font-size:14px;line-height:1.4;font-weight:700;color:#fff;}"
    ".pw-hs-foot-meta{margin:12px 0 0;font-size:12px;color:#93a3c0;}"
    "@media (prefers-reduced-motion:reduce){.pw-hs-dot,.pw-hs-more svg{transition:none;}}"
    # On a computer (the specification, 5.13): the same sections in the same order, inside
    # the site's width; no strip.
    "@media (min-width:700px){"
    ".pw-hs-strip{display:none!important;}"
    ".pw-hs-head-in{max-width:1190px;margin:0 auto;padding:12px 22px;display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:24px;}"
    ".pw-hs-head-row{display:contents;}"
    ".pw-hs-brand{grid-column:1;grid-row:1;}"
    ".pw-hs .pw-search-wrap{grid-column:2;grid-row:1;max-width:720px;width:100%;margin:0 auto;}"
    ".pw-hs-actions{grid-column:3;grid-row:1;}"
    # One row that scrolls where the names do not fit, centred where they do.
    ".pw-hs-nav{padding:0 22px;}"
    ".pw-hs-nav a:first-child{margin-left:auto;}.pw-hs-nav a:last-child{margin-right:auto;}"
    # The page's column is a flex item (`.pw-reference-viewport`): its width set, so that a
    # row that scrolls never widens it.
    ".pw-hs-main{width:100%;max-width:1190px;margin:0 auto;padding:0 22px;}"
    ".pw-hs-promise{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);column-gap:40px;align-items:end;padding:32px 0 12px;}"
    ".pw-hs-promise .pw-hs-eyebrow{grid-column:1;grid-row:1;}"
    ".pw-hs-h1{grid-column:1;grid-row:2;margin:6px 0 0;font-size:32px;}"
    ".pw-hs-trust{grid-column:1;grid-row:3;margin:12px 0 0;}"
    ".pw-hs-steps{grid-column:2;grid-row:1 / span 3;border-top:0;border-left:1px solid var(--hs-line);padding:0 0 0 32px;}"
    ".pw-hs-banners{padding-top:20px;}"
    ".pw-hs-banner-row{padding:0 0 4px;scroll-padding:0;}"
    ".pw-hs-offers,.pw-hs-pop,.pw-hs-sec{margin-top:20px;border-radius:20px;}"
    ".pw-hs-offers{padding:20px 0;}"
    ".pw-hs-offers .pw-hs-head2,.pw-hs-sec-row .pw-hs-head2,.pw-hs-depts .pw-hs-head2{padding:0 20px;}"
    ".pw-hs-offer-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));overflow:visible;padding:12px 20px 0;}"
    ".pw-hs-pop{padding:22px 20px;}"
    # Four a row, so that the fold of four (owner, 2026-11-12) is one whole row.
    ".pw-hs-pop-list{grid-template-columns:repeat(4,minmax(0,1fr));gap:18px 16px;}"
    ".pw-hs-pop-pic{height:190px;}"
    ".pw-hs-more{width:auto;min-width:240px;margin:18px auto 0;padding:0 28px;}"
    ".pw-hs-band{margin-top:20px;border-radius:22px;padding:26px 0 18px;}"
    ".pw-hs-band-head,.pw-hs-band-link{padding:0 24px;margin-left:0;margin-right:0;}"
    ".pw-hs-band-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));overflow:visible;padding:16px 24px 4px;}"
    ".pw-hs-pick{flex:none;}"
    ".pw-hs-depts{padding-top:26px;}"
    ".pw-hs-depts .pw-hs-scroll{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));overflow:visible;padding:12px 20px 0;}"
    ".pw-hs-dept{flex:none;}"
    ".pw-hs-grid{grid-template-columns:repeat(4,minmax(0,1fr));}"
    ".pw-hs-sec .pw-hs-tile-pic,.pw-hs-scroll .pw-hs-tile-pic{height:150px;}"
    ".pw-hs-sec-row .pw-hs-scroll{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));overflow:visible;padding:10px 20px 0;}"
    ".pw-hs-sec-row .pw-hs-tile{flex:none;}"
    ".pw-hs-sec{padding:18px 20px 20px;}"
    ".pw-hs-sec-row{padding:18px 0 20px;}"
    ".pw-hs-vows{padding:28px 0 0;}"
    ".pw-hs-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:48px;padding:28px 32px 18px;}"
    ".pw-hs-card>.pw-hs-eyebrow,.pw-hs-card-title,.pw-hs-figures{grid-column:1;}"
    ".pw-hs-vow-list{grid-column:2;grid-row:1 / span 3;align-self:center;margin:0;padding:0;}"
    ".pw-hs-card>.pw-hs-link{grid-column:2;}"
    ".pw-hs-shops{padding:26px 0 0;}"
    ".pw-hs-back{margin-top:28px;}"
    ".pw-hs-foot-in{max-width:1190px;margin:0 auto;padding:32px 22px 40px;display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr) minmax(0,1fr);column-gap:40px;}"
    ".pw-hs-foot-cols{display:contents;}"
    ".pw-hs-foot-col:nth-child(1){grid-column:2;grid-row:1 / span 5;}"
    ".pw-hs-foot-col:nth-child(2){grid-column:3;grid-row:1 / span 5;}"
    ".pw-hs-foot-rule{display:none;}"
    ".pw-hs-foot-brand{grid-column:1;grid-row:1;}"
    ".pw-hs-foot-where{grid-column:1;grid-row:2;}"
    ".pw-hs-foot-notice{grid-column:1;grid-row:3;max-width:520px;}"
    ".pw-hs-foot-cookies{grid-column:1;grid-row:4;}"
    ".pw-hs-foot-meta{grid-column:1;grid-row:5;}"
    "}"
    # Where there is room: the banners side by side, two sections side by side.
    "@media (min-width:1000px){"
    ".pw-hs-h1{font-size:38px;}"
    ".pw-hs-banner-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;overflow:visible;}"
    ".pw-hs-banner{width:auto;}"
    ".pw-js .pw-hs-dots{display:none!important;}"
    ".pw-hs-secs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:20px;}"
    ".pw-hs-sec .pw-hs-tile-pic,.pw-hs-scroll .pw-hs-tile-pic{height:120px;}"
    ".pw-hs-sec .pw-hs-art{width:96px;height:96px;}"
    "}"
)


def render_home_store_page(
    *,
    catalogue: tuple[int, int] | None,
    indexable: bool,
    trends: TrendsPanel | None,
    facts: HomeFacts | None = None,
    lists: HomeLists | None = None,
    parts: frozenset[str] | None = None,
) -> str:
    """The home page as a store. Its head is today's home page's: its title, its
    description, its one address when Google may index it (`indexable`), nothing more
    declared to Google (`seo.DECLARE_TO_GOOGLE`)."""
    lists = lists if lists is not None else load_home_lists()
    parts = PARTS_BUILT if parts is None else frozenset(parts)
    popular_html = _popular_html(trends, lists)
    sections_html = "".join(
        _section_html(section, index, facts, parts) for index, section in enumerate(lists.sections, start=1)
    )
    offers_html = _offers_html(facts, parts)
    main_html = (
        f"{_promise_band_html(catalogue)}"
        f"{_banners_html(lists, parts, offers_shown=bool(offers_html))}"
        f"{offers_html}"
        f"{popular_html}"
        f"{_band_html(facts, parts)}"
        f"{_departments_html(lists, parts)}"
        + (f'<div class="pw-hs-secs">{sections_html}</div>' if sections_html else "")
        + f"{_vows_html(catalogue, parts)}"
        f"{_shops_html(facts, parts)}"
        f'<a class="pw-hs-back" href="#top">{_UP}{escape(BACK_TO_TOP)}</a>'
    )
    return (
        "<!doctype html>"
        f'<html lang="{SITE_LANGUAGE}"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{'' if indexable else NOINDEX_META}"
        f"<title>{escape(_HOME_TITLE)}</title>"
        f'<meta name="description" content="{escape(_WHAT_IS_PICWISE)}">'
        f"{icon_links_html()}"
        f"{FONT_PRELOAD_HTML}"
        + (
            indexable_head_html("/", title=_HOME_TITLE, description=_WHAT_IS_PICWISE)
            + (home_structured_data_html() if declares_to_google() else "")
            if indexable
            else ""
        )
        + f"<script>{HEAD_SCRIPT}</script>"
        f"<style>{_PAGE_STYLES}{BROWSER_LISTS_STYLES}{HOME_STORE_STYLES}</style>"
        '</head><body class="pw-hs-body">'
        '<main class="pw-reference-viewport pw-hs">'
        f"{_strip_html()}"
        f"{_header_html(lists, parts)}"
        f"{panels_html()}"
        f'<div class="pw-hs-main">{main_html}</div>'
        f"{_footer_html(parts)}"
        f"<script>{_INFO_SCRIPT}</script>"
        f"{_scanning_screen_html()}"
        f"<script>{_SEARCH_SCRIPT}</script>"
        f"<script>{BROWSER_LISTS_SCRIPT}</script>"
        f"{'<script>' + TRENDS_SCRIPT + '</script>' if popular_html else ''}"
        f"<script>{HOME_STORE_SCRIPT}</script>"
        "</main>"
        "</body></html>"
    )
