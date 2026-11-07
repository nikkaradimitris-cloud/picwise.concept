"""What the AI layer's answer adds to a search page (`docs/PICWISE_AI_LAYER_SPEC.md`,
4.4 and 4.5; the Decision Contract, "The products that fit a complex search first").

The owner, 2026-11-06: «...τα προϊόντα που υποδεικνύει πρέπει να έχουν λεκτική αναφορά
αλλά και οπτική σημείωση καθώς πρέπει να κατατάσσονται και πρώτα», then «Ναι, συμφωνώ με
όλα, προχώρα» to the order, the time and the mark proposed:

- above the products, the AI's sentence, checked by code, and under it "Checked against
  the shops' own words", naming no AI («δεν θέλουμε να αποδομείται ο τρόπος που
  δουλεύουμε»);
- on each product that fits, a ✓ and its own words that show it, in quotes;
- when no product fits, the shops' own words for the need, each a search of its own with
  the count the catalogue gives it;
- the page never waits: while the answer is not there, an empty place and a small script
  that asks the site for it (`/assist-status`) and, once it is there, reads the same page
  again, which the site then draws from the stored answer, and puts its results in place.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from html import escape
from urllib.parse import quote

ASSIST_NOTE = "Checked against the shops' own words"
ASSIST_WORDS_LABEL = "In the shops' own words:"
# How long the page asks for the answer: the fourth measure's took 11.1 s at most, and
# the service may be answering others.
ASSIST_WAIT_SECONDS = 20


@dataclass(frozen=True)
class AssistView:
    """The AI layer's part of one search page: its checked sentence and the fitting
    products' own words by product id; or the shops' words as (word, search, count); or,
    while the answer is awaited, the key the page asks about."""

    sentence: str = ""
    fit_words: Mapping[str, str] = field(default_factory=dict)
    buttons: tuple[tuple[str, str, int], ...] = ()
    pending_key: str = ""


def fit_line_html(words: str) -> str:
    """A fitting product's mark: a ✓ and its own words, in quotes. Every card of a page
    with such products holds the line, empty where a product has none, so that each row
    of cards keeps one height."""
    if not words:
        return '<p class="pw-card-fit"></p>'
    return (
        '<p class="pw-card-fit"><span class="pw-fit-mark" aria-hidden="true">&#10003;</span> '
        f'<span class="pw-fit-words">“{escape(words)}”</span></p>'
    )


def assist_block_html(view: AssistView) -> str:
    """The place above the products: the sentence, the shops' words, or, awaited, empty."""
    if view.sentence:
        return (
            '<section class="pw-assist" id="pw-assist">'
            '<p class="pw-assist-sentence"><span class="pw-fit-mark" aria-hidden="true">&#10003;</span> '
            f"{escape(view.sentence)}</p>"
            f'<p class="pw-assist-note">{escape(ASSIST_NOTE)}</p>'
            "</section>"
        )
    if view.buttons:
        links = " ".join(
            f'<a class="pw-assist-word" href="/search?q={quote(search, safe="")}">{escape(word)} '
            f'<span class="pw-assist-count">({count:,})</span></a>'
            for word, search, count in view.buttons
        )
        return (
            '<section class="pw-assist" id="pw-assist">'
            f'<p class="pw-assist-words"><span class="pw-assist-label">{escape(ASSIST_WORDS_LABEL)}</span> {links}</p>'
            "</section>"
        )
    if view.pending_key:
        return (
            f'<section class="pw-assist" id="pw-assist" data-assist-key="{escape(view.pending_key, quote=True)}" '
            'hidden></section>'
        )
    return ""


# Asks `/assist-status` once a second; when the answer is there, reads the same page again
# with `assist=1` (drawn from the stored answer, with no new job and no second impression)
# and puts its results, `#pw-results`, in place of these. Nothing else: an answer that is
# not there, or a page that cannot be read, leaves the page as it is.
ASSIST_SCRIPT = (
    "(function(){"
    'var box=document.getElementById("pw-assist");'
    "if(!box||!window.fetch||!window.DOMParser||!window.URL){return;}"
    'var key=box.getAttribute("data-assist-key");'
    "if(!key){return;}"
    f"var tries=0,most={ASSIST_WAIT_SECONDS};"
    "function swap(){"
    'var url=new URL(window.location.href);url.searchParams.set("assist","1");'
    'fetch(url.toString(),{credentials:"same-origin"}).then(function(r){return r.ok?r.text():"";})'
    ".then(function(text){if(!text){return;}"
    'var doc=new DOMParser().parseFromString(text,"text/html");'
    'var fresh=doc.getElementById("pw-results"),here=document.getElementById("pw-results");'
    'var answer=fresh&&fresh.querySelector("#pw-assist");'
    'if(!here||!answer||answer.hasAttribute("data-assist-key")){return;}'
    "here.parentNode.replaceChild(document.importNode(fresh,true),here);"
    'try{document.dispatchEvent(new Event("pw-cards"));}catch(e){}'
    "}).catch(function(){});}"
    "function ask(){tries++;"
    'fetch("/assist-status?k="+encodeURIComponent(key),{credentials:"same-origin"})'
    ".then(function(r){return r.ok?r.json():null;})"
    '.then(function(state){if(state&&state.state==="ready"){swap();return;}'
    'if(state&&state.state==="pending"&&tries<most){setTimeout(ask,1000);}})'
    ".catch(function(){if(tries<most){setTimeout(ask,1000);}});}"
    "setTimeout(ask,1000);"
    "})();"
)

ASSIST_STYLES = (
    ".pw-results{display:contents;}"
    ".pw-assist{margin:10px 0 12px;padding:10px 14px;border:1px solid #cfe6dc;border-radius:12px;background:#f3faf6;}"
    ".pw-assist-sentence{margin:0;font-size:14.5px;line-height:1.45;color:var(--ink);font-weight:600;}"
    ".pw-assist-note{margin:4px 0 0;font-size:12px;color:var(--muted);}"
    ".pw-assist-words{margin:0;font-size:14px;line-height:2;color:var(--ink);}"
    ".pw-assist-label{margin-right:6px;color:var(--muted);}"
    ".pw-assist-word{display:inline-block;margin:0 6px 0 0;padding:2px 10px;border:1px solid #b9d9cb;border-radius:999px;"
    "background:#fff;color:#0b5d43;text-decoration:none;font-weight:600;}"
    ".pw-assist-word:hover{background:#e7f5ee;}"
    ".pw-assist-count{color:var(--muted);font-weight:500;}"
    ".pw-fit-mark{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;"
    "border-radius:50%;background:#12805c;color:#fff;font-size:10.5px;line-height:1;vertical-align:1px;}"
    ".pw-card-fit{margin:6px 0 0;font-size:12.5px;line-height:1.35;color:#0b5d43;font-weight:600;"
    "display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;height:2.7em;}"
    '.pw-grid[data-layout="single"] .pw-card-fit{height:auto;}'
)
