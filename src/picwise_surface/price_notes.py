"""A card's price note under its price: a chip, and a tap opening its last 30 nights.

The design the owner agreed to on 2026-11-13 («Συμφωνώ με το σχεδιασμό», to the pictures
of that day), on every card, not only the Recommended's: a green ▼ when the price fell
("£40 since 6 Dec"), a red ▲ when it rose (for a buyer a fall is good news, so green,
the stock market's colours the other way round), a grey "Same price for 12 nights";
nothing when there is nothing true to tell yet. A tap on the chip opens, under it, the
price as the shop listed it each night of the last 30, now, lowest and highest. The
rule behind each chip is `picwise_providers.price_history`'s.

Plain HTML (`<details>`), so the chip opens without JavaScript, and the history is in
the page as text. Where any card of a page has a note, every card keeps the chip's line
on a wide screen, so the cards of a row stay as tall as each other and their lines meet;
on a phone, a card a row, an empty line is not kept.
"""
from __future__ import annotations

from datetime import date
from html import escape

from picwise_providers.price_history import DOWN, SAME, UP, PriceNote, PriceRun

_SIGNS = {"GBP": "£", "EUR": "€", "USD": "$"}

_CHART_WIDTH = 260
_CHART_HEIGHT = 56
_CHART_PAD = 5


def _money(pence: int, currency: str, *, whole: bool = False) -> str:
    """£40, £39.99, or "40.00 SEK" for a currency without a sign here."""
    amount = f"{pence // 100:,}" if whole and pence % 100 == 0 else f"{pence / 100:,.2f}"
    sign = _SIGNS.get(str(currency or "").upper())
    return f"{sign}{amount}" if sign else f"{amount} {currency}".strip()


def _day(day: date, night: date) -> str:
    return f"{day.day} {day:%b}" + ("" if day.year == night.year else f" {day.year}")


def _days(start: date, end: date, night: date) -> str:
    """"23 Nov", "14–23 Nov", "28 Nov – 3 Dec"."""
    if start == end:
        return _day(end, night)
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}–{_day(end, night)}"
    return f"{_day(start, night)} – {_day(end, night)}"


def _chart_svg(runs: tuple[PriceRun, ...], night: date, flat: bool) -> str:
    """The price night by night as a step line, one slot a night; a night the shop did
    not list the product breaks the line."""
    if not runs:
        return ""
    first = runs[0].start
    span = (night - first).days + 1
    slot = (_CHART_WIDTH - 2 * _CHART_PAD) / span
    prices = [run.pence for run in runs]
    low, high = min(prices), max(prices)

    def x_left(day: date) -> float:
        return _CHART_PAD + (day - first).days * slot

    def y(pence: int) -> float:
        if flat or high == low:
            return _CHART_HEIGHT / 2
        return _CHART_PAD + (high - pence) * (_CHART_HEIGHT - 2 * _CHART_PAD) / (high - low)

    path: list[str] = []
    for index, run in enumerate(runs):
        left, right, level = x_left(run.start), x_left(run.end) + slot, y(run.pence)
        before = runs[index - 1] if index else None
        if before is not None and (run.start - before.end).days == 1:
            path.append(f"L{left:.1f},{level:.1f}")
        else:
            path.append(f"M{left:.1f},{level:.1f}")
        path.append(f"L{right:.1f},{level:.1f}")
    last = runs[-1]
    return (
        f'<svg class="pw-ph-chart" viewBox="0 0 {_CHART_WIDTH} {_CHART_HEIGHT}" role="img" '
        f'aria-label="The price each night">'
        f'<path d="{" ".join(path)}" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>'
        f'<circle cx="{x_left(last.end) + slot - 1:.1f}" cy="{y(last.pence):.1f}" r="3.5" fill="currentColor"/>'
        "</svg>"
    )


def _extreme(runs: tuple[PriceRun, ...], pence: int, night: date) -> str:
    """When a lowest or highest price was the shop's, unless it is today's."""
    for run in reversed(runs):
        if run.pence == pence:
            return "" if run.end == night else f' <span>({_days(run.start, run.end, night)})</span>'
    return ""


def _facts_html(note: PriceNote, price: str) -> str:
    if note.kind == SAME:
        return (
            f'<p class="pw-ph-f"><b>{escape(price)}</b> on each of the last {note.nights} '
            f'{"night" if note.nights == 1 else "nights"} it was listed.</p>'
        )
    prices = [run.pence for run in note.runs]
    low, high = min(prices), max(prices)
    if low == high:
        return f'<p class="pw-ph-f">Now <b>{escape(price)}</b></p>'
    return (
        f'<p class="pw-ph-f">Now <b>{escape(price)}</b> &middot; '
        f"Lowest <b>{escape(_money(low, note.currency))}</b>{_extreme(note.runs, low, note.night)} &middot; "
        f"Highest <b>{escape(_money(high, note.currency))}</b>{_extreme(note.runs, high, note.night)}</p>"
    )


def price_note_html(note: PriceNote | None, *, shop: str, price: str, slot: bool = False) -> str:
    """The chip under a card's price and what it opens; with no note, an empty line where
    another card of the page has one (`slot`), else nothing."""
    if note is None:
        return '<div class="pw-ph pw-ph-empty" aria-hidden="true"></div>' if slot else ""
    if note.kind in (DOWN, UP):
        arrow, words = ("&#9660;", "Price down") if note.kind == DOWN else ("&#9650;", "Price up")
        when = f"since {_day(note.since, note.night)}" if note.since else ""
        chip = (
            f'<span class="pw-ph-a" aria-hidden="true">{arrow}</span>'
            f'<span class="pw-ph-sr">{words} </span>{escape(_money(note.change_pence, note.currency, whole=True))}'
            f' <span class="pw-ph-w">{escape(when)}</span>'
        )
        span = (note.night - note.runs[0].start).days + 1 if note.runs else 0
    elif note.kind == SAME:
        chip = (
            '<span class="pw-ph-a" aria-hidden="true">=</span>Same price '
            f'<span class="pw-ph-w">for {note.nights} {"night" if note.nights == 1 else "nights"}</span>'
        )
        span = note.nights
    else:
        return '<div class="pw-ph pw-ph-empty" aria-hidden="true"></div>' if slot else ""
    shop_words = f"at {escape(shop)}" if str(shop or "").strip() else "at the shop"
    gaps = any((later.start - earlier.end).days > 1 for earlier, later in zip(note.runs, note.runs[1:]))
    return (
        f'<details class="pw-ph pw-ph-{note.kind}">'
        f'<summary class="pw-ph-chip">{chip}'
        '<svg class="pw-ph-v" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
        "</summary>"
        '<div class="pw-ph-pop">'
        f'<p class="pw-ph-h">Price {shop_words}, last {span} {"night" if span == 1 else "nights"}</p>'
        f"{_chart_svg(note.runs, note.night, flat=note.kind == SAME)}"
        f"{_facts_html(note, price)}"
        + ('<p class="pw-ph-n">A gap is a night the shop did not list it.</p>' if gaps else "")
        + '<p class="pw-ph-n">As the shop listed it, checked every night.</p>'
        "</div>"
        "</details>"
    )


PRICE_NOTE_STYLES = (
    ".pw-ph{position:relative;margin:6px 0 0;}"
    # The chip's line is 22px high (its words' line and its padding), and so is the line
    # a card without a chip keeps, so that the lines under them meet.
    ".pw-ph-empty{height:22px;}"
    ".pw-ph-chip{display:flex;width:-moz-fit-content;width:fit-content;align-items:center;gap:5px;height:22px;padding:0 9px;border-radius:999px;"
    "font-size:12.5px;line-height:1;font-weight:700;cursor:pointer;list-style:none;-webkit-user-select:none;user-select:none;}"
    ".pw-ph-chip::-webkit-details-marker{display:none;}"
    ".pw-ph-chip:focus-visible{outline:2px solid var(--blue-2);outline-offset:2px;}"
    ".pw-ph-w{font-weight:500;}"
    ".pw-ph-sr{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0;}"
    ".pw-ph-v{width:13px;height:13px;transition:transform .2s;}"
    ".pw-ph[open] .pw-ph-v{transform:rotate(180deg);}"
    ".pw-ph-down .pw-ph-chip{color:#15803d;background:#e8f6ed;}"
    ".pw-ph-up .pw-ph-chip{color:#b42318;background:#fdecea;}"
    ".pw-ph-same .pw-ph-chip{color:#5b6b82;background:#eef2f7;}"
    ".pw-ph-pop{position:absolute;left:0;right:0;top:calc(100% + 6px);z-index:6;background:#fff;"
    "border:1px solid var(--line);border-radius:12px;box-shadow:0 14px 30px rgba(16,40,80,.18);padding:10px 12px;}"
    ".pw-ph-down .pw-ph-pop{color:#15803d;}.pw-ph-up .pw-ph-pop{color:#b42318;}.pw-ph-same .pw-ph-pop{color:#7b8ba3;}"
    ".pw-ph-h{margin:0 0 6px;font-size:12px;font-weight:700;color:var(--ink);}"
    ".pw-ph-chart{display:block;width:100%;height:auto;background:#f6f8fb;border-radius:6px;}"
    ".pw-ph-f{margin:6px 0 0;font-size:12px;line-height:1.45;color:var(--ink-2);}"
    ".pw-ph-f b{color:var(--ink);}"
    ".pw-ph-f span,.pw-ph-n{color:var(--muted);}"
    ".pw-ph-n{margin:2px 0 0;font-size:11.5px;line-height:1.4;}"
    "@media (prefers-reduced-motion:reduce){.pw-ph-v{transition:none;}}"
    "@media (max-width:699px){"
    ".pw-grid:not([data-layout=\"single\"]) .pw-card-body>.pw-ph{grid-column:1 / -1;grid-row:21;margin-top:8px;}"
    ".pw-ph-empty{display:none;}"
    ".pw-ph-pop{position:static;margin-top:8px;box-shadow:none;}"
    ".pw-ph-chip{height:32px;font-size:13px;}"
    "}"
)
