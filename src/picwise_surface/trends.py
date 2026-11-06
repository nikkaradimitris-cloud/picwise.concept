"""The month's trending searches, under the home page's search box (owner, 2026-10-31).

The design is the panel in `docs/design/picwise_design_proposal_2026-10-31.html`
(owner: «φτιάξε ένα ωραίο πάνελ ... δημοφιλείς αγορές για αυτό το μήνα ... αν μπορείς
να αντλείς και αριθμό αναζητήσεων»): rank, a coloured icon per category, Google's
search interest on a five-step scale, rising, falling or new against last month,
searches a month, and what PicWise's shops ask for the product. It speaks of searches,
not sales (owner, 2026-10-31: «μπορούμε να λέμε trend αναζητήσεις και όχι πωλήσεις»).

Every figure must come from a real source, named on the panel (`docs/LANDING_PAGE_SPEC.md`,
"Trends state only what is known"; `docs/ANTI_FAKE_TRUST_RULES.md`):

- the ranking, the interest and the change: Google's search data (Google Ads Keyword
  Planner's monthly searches, or the Google Trends API's interest);
- the searches a month: Google Ads Keyword Planner, approximate;
- the offers and the lowest price: PicWise's own catalogue, counted when the panel's
  data is written, never when a page is drawn.

No source is connected yet: the owner's Google accounts do not exist (31/10). So
`load_trends_panel` returns None, its status is `not_connected`, and the home page shows
no panel at all: never invented rows, never an empty frame. The renderer is built and
tested on fictional rows so that the day a source writes real ones, the panel only has
to be given them.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from urllib.parse import quote

# The panel's source, as the dashboard enum names missing data (PROJECT_RULES §10).
TRENDS_SOURCE_STATUS = "not_connected"

MAX_TREND_ROWS = 10

# Google's search interest, on the panel's five steps. 0 or None: the source gave none,
# and the scale is not drawn.
_DEMAND_LEVELS = {5: "Very high", 4: "High", 3: "Medium", 2: "Low", 1: "Very low"}
_CHANGES = frozenset({"up", "down", "new", "flat"})

# A colour and an icon per category, matched on the category's own name. A category the
# table does not know gets the plain one: never a guessed category.
_ICON_PATHS = {
    "phone": '<rect x="7" y="2.5" width="10" height="19" rx="2.2"/><path d="M11 18.5h2"/>',
    "kitchen": '<path d="M5 10h14v3a7 7 0 0 1-14 0z"/><path d="M8 7c0-1.5 1-1.5 1-3M12 7c0-1.5 1-1.5 1-3M16 7c0-1.5 1-1.5 1-3"/>',
    "home": '<path d="M3.5 11 12 4l8.5 7"/><path d="M6 9.5V20h12V9.5"/>',
    "gaming": '<path d="M7 9h10a4 4 0 0 1 4 4v1.5a2.5 2.5 0 0 1-4.6 1.4L15 14H9l-1.4 1.9A2.5 2.5 0 0 1 3 14.5V13a4 4 0 0 1 4-4z"/><path d="M8 11.5v2M7 12.5h2"/>',
    "audio": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="4" height="6" rx="1.5"/><rect x="17" y="14" width="4" height="6" rx="1.5"/>',
    "wearable": '<rect x="7" y="6" width="10" height="12" rx="3"/><path d="M9 6V3h6v3M9 18v3h6v-3"/>',
    "computer": '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2.5 19h19"/>',
    "tv": '<rect x="3" y="5" width="18" height="12" rx="1.5"/><path d="M8 20h8"/>',
    "beauty": '<path d="M9 3h6v5H9z"/><path d="M8 8h8l-1 13H9z"/>',
    "toy": '<circle cx="12" cy="12" r="8"/><path d="M12 4v16M4 12h16"/>',
    "garden": '<path d="M12 21V11"/><path d="M12 11c0-4 3-6 7-6 0 4-3 6-7 6zM12 13c0-3-2.5-5-6-5 0 3 2.5 5 6 5z"/>',
    "sport": '<circle cx="12" cy="12" r="8"/><path d="M5 9c4 1 10 1 14 0M5 15c4-1 10-1 14 0"/>',
    "default": '<path d="M5 8h14l-1.2 11.5a1.5 1.5 0 0 1-1.5 1.5H7.7a1.5 1.5 0 0 1-1.5-1.5z"/><path d="M9 8a3 3 0 0 1 6 0"/>',
}
_CATEGORY_STYLE = (
    # (words in the category's name, icon, colour)
    (("phone", "mobile", "smartphone"), "phone", "#2f6fe4"),
    (("kitchen", "cooking", "appliance"), "kitchen", "#e07a2f"),
    (("home", "household", "cleaning", "vacuum"), "home", "#1d8a4e"),
    (("gaming", "game", "console"), "gaming", "#7b4fd6"),
    (("audio", "headphone", "speaker", "sound"), "audio", "#d6417a"),
    (("wearable", "watch", "fitness"), "wearable", "#0f9ab0"),
    (("computer", "laptop", "tablet", "pc"), "computer", "#3a5bc7"),
    (("tv", "television", "video"), "tv", "#2a7fa8"),
    (("beauty", "health", "personal care"), "beauty", "#c2477f"),
    (("toy", "baby", "kids"), "toy", "#e0a21b"),
    (("garden", "outdoor", "diy"), "garden", "#4c9a2a"),
    (("sport", "bike", "cycling"), "sport", "#c4472d"),
)
_DEFAULT_STYLE = ("default", "#6b7f9e")


@dataclass(frozen=True)
class TrendRow:
    """One product of the month, as its sources give it."""

    rank: int
    name: str
    category: str
    # Google's search interest on five steps (5 = very high); None when not given.
    demand_level: int | None = None
    # Against last month: "up", "down", "new", "flat", or "" when the source says nothing.
    change: str = ""
    change_by: int = 0
    # As the source gives it ("~550K", "10K–100K"); "" when there is no figure.
    monthly_searches: str = ""
    # PicWise's offers for it and the lowest of their prices, from its own catalogue.
    offers: int = 0
    from_price: str = ""
    # What "Compare" searches for; the name when empty.
    search_query: str = ""


@dataclass(frozen=True)
class TrendsPanel:
    """The panel's data. Each source line names where its column comes from."""

    period: str
    country: str
    rows: tuple[TrendRow, ...]
    ranking_source: str
    searches_source: str = ""
    offers_source: str = ""


def load_trends_panel() -> TrendsPanel | None:
    """The panel's data from its sources, or None while none is connected.

    TODO (owner's accounts, 31/10): the month's most searched products in the UK and
    their change from Google Ads Keyword Planner (monthly searches; its API needs a
    developer token with Basic access) or the Google Trends API (interest 0-100; alpha,
    by application), written once a month with the offers counted in PicWise's
    catalogue. Until then the panel is not shown.
    """
    return None


def _category_style(category: str) -> tuple[str, str]:
    name = " ".join(str(category or "").lower().split())
    for words, icon, colour in _CATEGORY_STYLE:
        if any(word in name for word in words):
            return icon, colour
    return _DEFAULT_STYLE


def _icon_html(category: str) -> str:
    icon, colour = _category_style(category)
    return (
        f'<span class="pw-tp-icon" style="--c:{colour}" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{_ICON_PATHS[icon]}</svg></span>'
    )


def _change_html(row: TrendRow) -> str:
    change = row.change if row.change in _CHANGES else ""
    if not change:
        return ""
    places = max(int(row.change_by or 0), 0)
    if change == "up" and places:
        text, label = f"&#9650; {places}", f"Up {places} {'place' if places == 1 else 'places'} on last month"
    elif change == "down" and places:
        text, label = f"&#9660; {places}", f"Down {places} {'place' if places == 1 else 'places'} on last month"
    elif change == "new":
        text, label = "NEW", "New in the top 10 this month"
    elif change == "flat":
        text, label = "=", "The same place as last month"
    else:
        return ""
    return f'<span class="pw-tp-chg pw-tp-chg-{change}" title="{label}" aria-label="{label}">{text}</span>'


def _demand_html(level: int | None) -> str:
    if level not in _DEMAND_LEVELS:
        return ""
    steps = "".join(
        f'<i class="{"on" if step <= int(level) else ""}"></i>' for step in range(1, 6)
    )
    name = _DEMAND_LEVELS[int(level)]
    return (
        f'<span class="pw-tp-scale" role="img" aria-label="Search interest: {name}">{steps}</span>'
        f'<span class="pw-tp-level">{name}</span>'
    )


def _deal_html(row: TrendRow) -> str:
    """What PicWise's shops ask for it, or that they do not have it. A product PicWise
    has no offer for never links to an empty search."""
    if int(row.offers or 0) <= 0:
        return '<span class="pw-tp-deal pw-tp-deal-none">Not in our shops yet</span>'
    offers = int(row.offers)
    words = f"{offers:,} {'offer' if offers == 1 else 'offers'}"
    if str(row.from_price or "").strip():
        words += f" · from {escape(str(row.from_price).strip())}"
    query = str(row.search_query or row.name).strip()
    return (
        f'<a class="pw-tp-deal" href="/search?q={quote(query, safe="")}">'
        f"{words}<span>Compare &#8594;</span></a>"
    )


def _row_html(row: TrendRow) -> str:
    _icon, colour = _category_style(row.category)
    searches = str(row.monthly_searches or "").strip()
    searches_html = (
        f'<span class="pw-tp-searches">{escape(searches)} searches a month</span>' if searches else ""
    )
    return (
        f'<li class="pw-tp-row" data-category="{escape(row.category, quote=True)}">'
        f'<span class="pw-tp-rank">{int(row.rank)}</span>'
        f"{_icon_html(row.category)}"
        '<span class="pw-tp-main">'
        f'<span class="pw-tp-name">{escape(row.name)}</span>'
        f'<span class="pw-tp-sub"><span class="pw-tp-cat" style="color:{colour}">{escape(row.category)}</span>'
        f"{_demand_html(row.demand_level)}</span>"
        f"{searches_html}"
        "</span>"
        f"{_change_html(row)}"
        f"{_deal_html(row)}"
        "</li>"
    )


def render_trends_panel(panel: TrendsPanel | None) -> str:
    """The panel's HTML, or "" when there is nothing real to show.

    A panel needs rows and the name of the source that ranks them; without either it is
    not drawn. Rows are shown in rank order, ten at most. A column a source did not
    give (the demand, the change, the searches) is left out of its row, never filled.
    """
    if panel is None or not str(panel.ranking_source or "").strip():
        return ""
    rows = sorted(
        (row for row in panel.rows if str(row.name or "").strip() and int(row.rank or 0) > 0),
        key=lambda row: int(row.rank),
    )[:MAX_TREND_ROWS]
    if not rows:
        return ""
    categories: list[str] = []
    for row in rows:
        if row.category and row.category not in categories:
            categories.append(row.category)
    tabs = "".join(
        f'<button class="pw-tp-tab" type="button" data-category="{escape(name, quote=True)}" '
        f'style="--c:{_category_style(name)[1]}" aria-pressed="false">{escape(name)}</button>'
        for name in categories
    )
    sources = [f"Ranking and interest: {escape(panel.ranking_source.strip())}."]
    if any(str(row.monthly_searches or "").strip() for row in rows) and panel.searches_source.strip():
        sources.append(f"Searches: {escape(panel.searches_source.strip())}.")
    if any(int(row.offers or 0) > 0 for row in rows) and panel.offers_source.strip():
        sources.append(f"Offers and prices: {escape(panel.offers_source.strip())}.")
    kicker = " · ".join(part for part in (panel.period.strip(), panel.country.strip()) if part)
    country = panel.country.strip()
    heading = "Trending searches in the UK this month" if country == "United Kingdom" else "Trending searches this month"
    has_change = any(row.change in _CHANGES for row in rows)
    legend = (
        '<div class="pw-tp-legend" aria-hidden="true">'
        '<span><span class="pw-tp-chg pw-tp-chg-up">&#9650;</span>rising</span>'
        '<span><span class="pw-tp-chg pw-tp-chg-down">&#9660;</span>falling</span>'
        '<span><span class="pw-tp-chg pw-tp-chg-new">NEW</span>new in the top 10</span>'
        "</div>"
        if has_change
        else ""
    )
    return (
        '<section class="pw-tp" id="pw-trends" aria-labelledby="pw-tp-title">'
        '<div class="pw-tp-head"><div>'
        f'<p class="pw-tp-kicker">{escape(kicker)}</p>'
        f'<h2 class="pw-tp-title" id="pw-tp-title">{heading}</h2>'
        '<p class="pw-tp-intro">The products people search for most on Google this month, how '
        "that is changing, and what PicWise's shops ask for them.</p>"
        f"</div>{legend}</div>"
        f'<div class="pw-tp-tabs pw-needs-js" role="group" aria-label="Show a category">'
        '<button class="pw-tp-tab on" type="button" data-category="" aria-pressed="true">All</button>'
        f"{tabs}</div>"
        f'<ol class="pw-tp-list">{"".join(_row_html(row) for row in rows)}</ol>'
        f'<p class="pw-tp-source">{" ".join(sources)}</p>'
        "</section>"
    )


# The category tabs: plain JavaScript that only hides rows; without it every row shows.
TRENDS_SCRIPT = r"""
(function(){
"use strict";
var panel=document.getElementById("pw-trends");
if(!panel){return;}
var tabs=panel.querySelectorAll(".pw-tp-tab");
var rows=panel.querySelectorAll(".pw-tp-row");
Array.prototype.forEach.call(tabs,function(tab){
  tab.addEventListener("click",function(){
    var wanted=tab.getAttribute("data-category")||"";
    Array.prototype.forEach.call(tabs,function(other){
      var on=other===tab;
      other.classList.toggle("on",on);
      other.setAttribute("aria-pressed",on?"true":"false");
    });
    Array.prototype.forEach.call(rows,function(row){
      row.hidden=!!wanted&&row.getAttribute("data-category")!==wanted;
    });
  });
});
})();
"""


TRENDS_STYLES = (
    ".pw-tp{max-width:980px;margin:28px auto 0;text-align:left;background:var(--card);border:1px solid var(--line);border-radius:20px;overflow:hidden;box-shadow:0 14px 34px rgba(16,40,80,.10);}"
    ".pw-tp-head{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:20px 22px 14px;background:linear-gradient(120deg,#0f2f73 0%,#2f6fe4 60%,#5b8ff0 100%);color:#fff;}"
    ".pw-tp-kicker{margin:0;font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.85;font-weight:700;}"
    ".pw-tp-title{margin:4px 0 6px;font-size:24px;letter-spacing:-.02em;color:#fff;}"
    ".pw-tp-intro{margin:0;max-width:560px;font-size:14px;line-height:1.5;opacity:.92;}"
    ".pw-tp-legend{display:flex;flex-direction:column;gap:6px;font-size:12px;opacity:.95;align-self:center;}"
    ".pw-tp-legend .pw-tp-chg{margin:0 4px 0 0;}"
    ".pw-tp-tabs{display:flex;gap:8px;flex-wrap:wrap;padding:14px 22px 4px;}"
    ".pw-tp-tab{padding:6px 12px;border-radius:999px;border:1px solid var(--line);font:inherit;font-size:13px;color:var(--ink-2);background:#fff;cursor:pointer;}"
    ".pw-tp-tab:not(.on){border-left:4px solid var(--c,var(--line));}"
    ".pw-tp-tab.on{background:var(--ink);color:#fff;border-color:var(--ink);}"
    ".pw-tp-list{list-style:none;margin:0;padding:10px 14px 4px;display:grid;grid-template-columns:1fr 1fr;column-gap:14px;}"
    ".pw-tp-row{display:grid;grid-template-columns:34px 44px minmax(0,1fr) auto;grid-template-areas:'rank icon main chg' 'rank icon deal deal';align-items:center;gap:4px 10px;padding:12px 8px;border-bottom:1px solid #eef2f8;}"
    ".pw-tp-row[hidden]{display:none;}"
    ".pw-tp-rank{grid-area:rank;font-size:22px;font-weight:800;color:#c3cfe2;text-align:center;}"
    ".pw-tp-row:nth-child(-n+3) .pw-tp-rank{color:var(--blue-2);}"
    ".pw-tp-icon{grid-area:icon;width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;color:var(--c);background:#f2f5fa;background:color-mix(in srgb,var(--c) 13%,#fff);}"
    ".pw-tp-icon svg{width:24px;height:24px;}"
    ".pw-tp-main{grid-area:main;min-width:0;display:flex;flex-direction:column;gap:3px;}"
    ".pw-tp-name{font-weight:700;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
    ".pw-tp-sub{display:flex;align-items:center;gap:8px;font-size:12px;}"
    ".pw-tp-cat{font-weight:700;}"
    ".pw-tp-scale{display:inline-flex;gap:3px;}"
    ".pw-tp-scale i{display:block;width:16px;height:7px;border-radius:3px;background:#e3e9f3;}"
    ".pw-tp-scale i.on{background:var(--blue-2);}"
    ".pw-tp-level{color:var(--muted);}"
    ".pw-tp-searches{font-size:12px;color:var(--muted);}"
    ".pw-tp-chg{grid-area:chg;font-size:11px;font-weight:800;padding:3px 7px;border-radius:999px;white-space:nowrap;}"
    ".pw-tp-chg-up{background:#e7f6ed;color:#1d8a4e;}.pw-tp-chg-down{background:#fdecec;color:#c23b3b;}"
    ".pw-tp-chg-new{background:#fff3d6;color:#a56a00;}.pw-tp-chg-flat{background:#eef2f8;color:#6b7f9e;}"
    ".pw-tp-deal{grid-area:deal;display:flex;justify-content:space-between;align-items:center;margin-top:4px;padding:7px 10px;border-radius:10px;background:#f2f6fe;color:var(--ink);font-size:13px;font-weight:650;text-decoration:none;}"
    ".pw-tp-deal span{color:var(--blue-2);}"
    ".pw-tp-deal-none{background:#f6f7f9;color:#8a96a8;font-weight:500;}"
    ".pw-tp-source{margin:0;padding:12px 22px 18px;font-size:12px;color:var(--muted);line-height:1.5;}"
    "@media (max-width:860px){.pw-tp-list{grid-template-columns:1fr;}}"
    "@media (max-width:520px){.pw-tp-title{font-size:21px;}.pw-tp-legend{flex-direction:row;flex-wrap:wrap;gap:10px;}.pw-tp-list{padding:6px 8px 4px;}.pw-tp-row{grid-template-columns:22px 36px minmax(0,1fr) auto;gap:4px 8px;padding:12px 2px;}.pw-tp-rank{font-size:17px;}.pw-tp-icon{width:36px;height:36px;border-radius:10px;}.pw-tp-icon svg{width:20px;height:20px;}.pw-tp-level{display:none;}.pw-tp-scale i{width:12px;height:6px;}.pw-tp-deal{font-size:12px;padding:7px 9px;}}"
)
