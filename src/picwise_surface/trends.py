"""The month's most popular products, under the home page's search box (owner,
2026-10-31: «φτιάξε ένα ωραίο πάνελ ... δημοφιλείς αγορές για αυτό το μήνα ... αν μπορείς
να αντλείς και αριθμό αναζητήσεων»). It speaks of searches, not sales (owner, 2026-10-31:
«μπορούμε να λέμε trend αναζητήσεις και όχι πωλήσεις»).

The design of 2026-11-12, simpler than the panel of 31/10 in
`docs/design/picwise_design_proposal_2026-10-31.html` (owner: «κράτα το απλό σοβαρό και
αξιόπιστο», then «Έχεις δίκιο για αυτά»): per row its rank, its name, rising, falling or
new against last month, and how many of PicWise's products it has and from what price,
a tap away (its searches a month too, until 13/11, below). No coloured icon or category tabs, no scale of
interest, no coloured heading. "Products", not "offers": on PicWise an offer is a shop's
discount ("Offers first"). The panel folds to its first four rows, with "Show all 10"
to open it and "Show fewer" to close it again (owner, 2026-11-12: «Το πάνελ αναδιπλώνει?
Θα είναι καλύτερο να αναδιπλώνει»); without JavaScript every row shows.

The owner, 2026-11-13: «Τα 10 πιο διαδεδομένα προϊόντα», under the heading "Most popular
in the UK"; «Δεν θέλουμε να δείξουμε τον αριθμό των αναζητήσεων», so a row shows no
number of searches (the ranking still comes from them, and its source is named under the
rows); «Δεν μας ενδιαφέρει να τα έχουμε όλα», so a product PicWise's shops do not sell
keeps its row ("Not in our shops yet"). The same Google file serves a second purpose,
the owner's: the keywords of the pages given to Google, those of few searches and little
competition first (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`).

Every figure must come from a real source, named on the panel (`docs/LANDING_PAGE_SPEC.md`,
"Trends state only what is known"; `docs/ANTI_FAKE_TRUST_RULES.md`):

- the ranking and the change: Google's search data (Google Ads Keyword Planner's monthly
  searches, or the Google Trends API's interest);
- the searches a month, kept and not shown: Google Ads Keyword Planner, approximate;
- the products and the lowest price: PicWise's own catalogue, counted when the panel's
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
# The rows a folded panel shows (owner, 2026-11-12).
FOLDED_ROWS = 4

_CHANGES = frozenset({"up", "down", "new", "flat"})


@dataclass(frozen=True)
class TrendRow:
    """One product of the month, as its sources give it."""

    rank: int
    name: str
    category: str
    # Google's search interest on five steps (5 = very high); None when not given. Kept
    # as the source gives it; the panel of 2026-11-12 does not draw it.
    demand_level: int | None = None
    # Against last month: "up", "down", "new", "flat", or "" when the source says nothing.
    change: str = ""
    change_by: int = 0
    # As the source gives it ("~550K", "10K–100K"); "" when there is no figure. Kept with
    # the row, never shown (owner, 2026-11-13: «Δεν θέλουμε να δείξουμε τον αριθμό των
    # αναζητήσεων»).
    monthly_searches: str = ""
    # PicWise's products for it and the lowest of their prices, from its own catalogue.
    offers: int = 0
    from_price: str = ""
    # What a tap on the row searches for; the name when empty.
    search_query: str = ""


@dataclass(frozen=True)
class TrendsPanel:
    """The panel's data. Each source line names where its column comes from."""

    period: str
    country: str
    rows: tuple[TrendRow, ...]
    ranking_source: str
    # The source of the searches a month, which the panel no longer shows (13/11).
    searches_source: str = ""
    offers_source: str = ""


def load_trends_panel() -> TrendsPanel | None:
    """The panel's data from its sources, or None while none is connected.

    TODO (owner's accounts, 31/10): the month's most searched products in the UK and
    their change from Google Ads Keyword Planner (monthly searches; its API needs a
    developer token with Basic access) or the Google Trends API (interest 0-100; alpha,
    by application), written once a month with the products counted in PicWise's
    catalogue. Until then the panel is not shown.
    """
    return None


def _change_html(row: TrendRow) -> str:
    """Rising, falling or new against last month; nothing for a row in the same place,
    nor when the source says nothing."""
    change = row.change if row.change in _CHANGES else ""
    places = max(int(row.change_by or 0), 0)
    if change == "up" and places:
        text, label = f"&#9650; {places}", f"Up {places} {'place' if places == 1 else 'places'} on last month"
    elif change == "down" and places:
        text, label = f"&#9660; {places}", f"Down {places} {'place' if places == 1 else 'places'} on last month"
    elif change == "new":
        text, label = "New", "New in the top 10 this month"
    else:
        return ""
    return f'<span class="pw-tp-chg pw-tp-chg-{change}" title="{label}" aria-label="{label}">{text}</span>'


def _row_html(row: TrendRow) -> str:
    """One row: a link to the search when PicWise's shops have the product, its words
    alone when they do not. A column a source did not give is left out, never filled."""
    products = max(int(row.offers or 0), 0)
    parts = []
    if products:
        words = f"{products:,} {'product' if products == 1 else 'products'}"
        price = str(row.from_price or "").strip()
        if price:
            words += f" from <b>{escape(price)}</b>"
        parts.append(f'<span class="pw-tp-deal">{words}</span>')
    else:
        parts.append('<span class="pw-tp-deal pw-tp-deal-none">Not in our shops yet</span>')
    inner = (
        f'<span class="pw-tp-rank">{int(row.rank)}</span>'
        '<span class="pw-tp-main">'
        f'<span class="pw-tp-name-line"><span class="pw-tp-name">{escape(row.name)}</span>'
        f"{_change_html(row)}</span>"
        f'<span class="pw-tp-meta">{" · ".join(parts)}</span>'
        "</span>"
    )
    if not products:
        # A product PicWise has none of never links to an empty search.
        return f'<li class="pw-tp-item"><div class="pw-tp-row pw-tp-row-off">{inner}</div></li>'
    query = str(row.search_query or row.name).strip()
    return (
        f'<li class="pw-tp-item"><a class="pw-tp-row" href="/search?q={quote(query, safe="")}">'
        f'{inner}<span class="pw-tp-go" aria-hidden="true">&#8250;</span></a></li>'
    )


def render_trends_panel(panel: TrendsPanel | None) -> str:
    """The panel's HTML, or "" when there is nothing real to show.

    A panel needs rows and the name of the source that ranks them; without either it is
    not drawn. Rows are shown in rank order, ten at most, folded to the first
    `FOLDED_ROWS` where there are more. Each source the rows use is named under them.
    """
    if panel is None or not str(panel.ranking_source or "").strip():
        return ""
    rows = sorted(
        (row for row in panel.rows if str(row.name or "").strip() and int(row.rank or 0) > 0),
        key=lambda row: int(row.rank),
    )[:MAX_TREND_ROWS]
    if not rows:
        return ""
    sources = [f"Ranking: {escape(panel.ranking_source.strip())}."]
    if any(int(row.offers or 0) > 0 for row in rows) and panel.offers_source.strip():
        sources.append(f"Products and prices: {escape(panel.offers_source.strip())}.")
    country = panel.country.strip()
    if country == "United Kingdom":
        heading = "Most popular in the UK"
    elif country:
        heading = f"Most popular in {escape(country)}"
    else:
        heading = "Most popular this month"
    period = panel.period.strip()
    period_html = f'<span class="pw-tp-period">{escape(period)}</span>' if period else ""
    more_html = (
        '<button class="pw-tp-more pw-needs-js" id="pw-tp-more" type="button" aria-expanded="false" '
        f'aria-controls="pw-tp-list" data-more="Show all {len(rows)}" data-less="Show fewer">'
        f"<span>Show all {len(rows)}</span>"
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
        "</button>"
        if len(rows) > FOLDED_ROWS
        else ""
    )
    return (
        '<section class="pw-tp" id="pw-trends" aria-labelledby="pw-tp-title">'
        f'<div class="pw-tp-head"><h2 class="pw-tp-title" id="pw-tp-title">{heading}</h2>{period_html}</div>'
        f'<ol class="pw-tp-list" id="pw-tp-list">{"".join(_row_html(row) for row in rows)}</ol>'
        f"{more_html}"
        f'<p class="pw-tp-source">{" ".join(sources)}</p>'
        "</section>"
    )


# The fold. Folded from the first paint wherever JavaScript runs (the page's head marks
# it, `browser_lists.HEAD_SCRIPT`); the button opens and closes it. Without JavaScript
# every row shows and the button does not.
TRENDS_SCRIPT = r"""
(function(){
"use strict";
var panel=document.getElementById("pw-trends");
var more=document.getElementById("pw-tp-more");
if(!panel||!more){return;}
var words=more.querySelector("span");
more.addEventListener("click",function(){
  var open=!panel.classList.contains("is-open");
  panel.classList.toggle("is-open",open);
  more.setAttribute("aria-expanded",open?"true":"false");
  words.textContent=more.getAttribute(open?"data-less":"data-more");
});
})();
"""


TRENDS_STYLES = (
    ".pw-tp{max-width:860px;margin:44px auto 0;text-align:left;background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;}"
    ".pw-tp-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:18px 22px 12px;border-bottom:1px solid var(--line);}"
    ".pw-tp-title{margin:0;font-size:18px;letter-spacing:-.01em;color:var(--ink);}"
    ".pw-tp-period{font-size:13px;color:var(--muted);white-space:nowrap;}"
    # Two columns read row by row, so opening the panel only adds rows under the four.
    ".pw-tp-list{list-style:none;margin:0;padding:4px 10px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:20px;}"
    ".pw-tp-item{min-width:0;}"
    f".pw-js .pw-tp:not(.is-open) .pw-tp-item:nth-child(n+{FOLDED_ROWS + 1}){{display:none;}}"
    ".pw-tp-row{display:grid;grid-template-columns:30px minmax(0,1fr) 14px;align-items:center;gap:10px;padding:12px 8px;border-top:1px solid #eef1f5;border-radius:8px;color:inherit;text-decoration:none;}"
    ".pw-tp-item:nth-child(-n+2) .pw-tp-row{border-top:0;}"
    "a.pw-tp-row:hover{background:#f4f7fc;}"
    "a.pw-tp-row:focus-visible{outline:2px solid var(--blue-2);outline-offset:-2px;}"
    ".pw-tp-rank{font-size:15px;font-weight:700;color:var(--muted);text-align:center;font-variant-numeric:tabular-nums;}"
    ".pw-tp-main{display:flex;flex-direction:column;gap:2px;min-width:0;}"
    ".pw-tp-name-line{display:flex;align-items:center;gap:8px;min-width:0;}"
    ".pw-tp-name{font-size:15px;font-weight:650;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
    ".pw-tp-row-off .pw-tp-name{color:var(--ink-2);}"
    ".pw-tp-meta{font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
    ".pw-tp-deal b{color:var(--ink);font-weight:650;}"
    ".pw-tp-deal-none{color:#8a97a8;}"
    ".pw-tp-chg{flex:0 0 auto;font-size:12px;font-weight:700;white-space:nowrap;font-variant-numeric:tabular-nums;}"
    ".pw-tp-chg-up{color:#15803d;}"
    ".pw-tp-chg-down{color:#94a3b8;}"
    ".pw-tp-chg-new{color:var(--blue-2);border:1px solid #c9d8f5;border-radius:999px;padding:1px 7px;font-size:11px;}"
    ".pw-tp-go{font-size:20px;line-height:1;color:#a3b1c4;}"
    ".pw-tp-more{align-items:center;justify-content:center;gap:6px;width:100%;min-height:46px;margin:0;border:0;border-top:1px solid var(--line);background:#fff;color:var(--blue-2);font:inherit;font-size:14px;font-weight:650;cursor:pointer;}"
    ".pw-tp-more:hover{background:#f4f7fc;}"
    ".pw-tp-more:focus-visible{outline:2px solid var(--blue-2);outline-offset:-2px;}"
    ".pw-tp-more svg{width:16px;height:16px;transition:transform .2s;}"
    ".pw-tp.is-open .pw-tp-more svg{transform:rotate(180deg);}"
    ".pw-tp-source{margin:0;padding:12px 22px 16px;border-top:1px solid var(--line);font-size:12px;line-height:1.5;color:var(--muted);}"
    "@media (prefers-reduced-motion:reduce){.pw-tp-more svg{transition:none;}}"
    "@media (max-width:699px){"
    ".pw-tp{margin-top:28px;border-radius:14px;}"
    ".pw-tp-head{padding:14px 14px 10px;}"
    ".pw-tp-title{font-size:17px;}"
    ".pw-tp-list{grid-template-columns:minmax(0,1fr);padding:2px 6px;}"
    ".pw-tp-item:nth-child(2) .pw-tp-row{border-top:1px solid #eef1f5;}"
    ".pw-tp-row{grid-template-columns:24px minmax(0,1fr) 12px;gap:8px;padding:11px 6px;min-height:56px;}"
    ".pw-tp-more{min-height:48px;}"
    ".pw-tp-source{padding:10px 14px 14px;}"
    "}"
)
