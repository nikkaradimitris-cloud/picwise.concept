"""The store's pages other than the home page (`docs/PICWISE_HOME_STORE_SPEC.md`, section 7;
task H4): built behind the home page's switch (`home_store.home_store_on`), each drawn only
once it is in `home_store.PARTS_BUILT`.

The owner decided them on 2026-11-24 («Ναι σε όλα»), to the pictures on his canvas, which
`tools/draw_store_pages.py` draws again: their words and look are this module's reference.

- Part B, the departments (7.1): `/departments`, all of them in four groups; and
  `/department/<name>`, a department's kinds, their Recommended, every kind as a row. A
  department of one kind has no page: it leads to that kind's search.

Every page is kept out of Google (`noindex`): nothing of the store is declared (section 2).
What a page knows of the catalogue is worked out once a night (`home_store_facts`), never
while it is drawn; what is not known yet is left out, never filled.
"""
from __future__ import annotations

from html import escape
from typing import Any

from . import home_store as hs
from .home_store_facts import DepartmentsFacts, KindFacts, current_kind_facts
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
    "@media (min-width:700px){"
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


def store_page(path: str, *, parts: frozenset[str] | None = None) -> str | None:
    """The page of the store at `path`, or None: not one of its pages, or its part not
    built (`home_store.PARTS_BUILT`)."""
    parts = hs.PARTS_BUILT if parts is None else frozenset(parts)
    if "departments" in parts:
        if path == hs.PART_ADDRESSES["departments"]:
            return render_departments_page(parts=parts)
        prefix = "/department/"
        if path.startswith(prefix) and path.count("/") == 2:
            return render_department_page(path[len(prefix):], parts=parts)
    return None
