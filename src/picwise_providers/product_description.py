"""Whether the feed sent a description worth showing, and the text it sent.

Owner rule (2026-10-12): every product PicWise shows must always carry availability,
a price, an image **and a sufficient description** -- the last one partly so the
published pages are not thin content. Availability, price and image were already
required for a card (`offer_health.evaluate_product_eligibility`); the description is
what this module adds, and both the gate and the feed audit tool read it from here so
what is required and what is reported cannot drift apart.

"Sufficient" is a length of real text, nothing more: this module never judges how good
a description is, only that the merchant sent one. Three things are deliberate.

- **HTML is stripped before measuring.** Feeds send `<p>` and `<br>` wrappers, and a
  product described by `<div class="a"><br/></div>` has no description at all.
- **A description identical to the title does not count.** Some merchants fill the
  column by repeating the product name, which adds nothing for a reader or for a
  search engine, and counting it would let exactly the thin page the rule exists to
  prevent through the gate.
- **The longest of the description columns is taken**, not the first: a feed may leave
  `description` empty and write the real text in `product_short_description`.

Measured on the first real feed (11,573 products, 2026-10-12): the rule costs 13% of
the feed, and the cost is not spread over kinds but over shops. Two merchants send no
descriptions at all -- Geekbuying (877 products) and Xiaomi RO (66) -- and every other
shop fills them on 88% to 100% of its rows. Those two shops carry whole kinds that
therefore stop appearing: televisions, TV boxes, vacuum cleaners, robot vacuums and
treadmills entirely, and all but a handful of watches, smartwatches and projectors.
That is the rule working as asked, not a defect, and it is recorded here because the
next person to read a search that returns nothing for "television" needs to find the
reason in one place.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

# The columns a feed describes a product in. The longest text among them is used.
DESCRIPTION_KEYS = ("description", "product_short_description", "specifications")

# How much real text counts as a description. Chosen on the measurement above rather
# than from taste: the feed holds 91% of its products at 40 characters, 89% at 80, 87%
# at 120, 79% at 200 and 61% at 300, so anything from 40 to 120 costs about the same
# and 120 is roughly the shortest text that reads as a sentence about a product rather
# than a label. One number, one place, so the owner can move it with one word.
DESCRIPTION_MIN_CHARS = 120

_TAG_RE = re.compile(r"<[^>]*>")
_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")


def _visible_text(value: Any) -> str:
    """The text a reader would see: tags removed, entities blanked, spaces collapsed."""
    text = str(value or "")
    if not text:
        return ""
    if "<" in text:
        text = _TAG_RE.sub(" ", text)
    if "&" in text:
        # An entity stands for one character, so it is replaced by one, not dropped:
        # "&amp;" is a word's worth of markup but a single "&" to a reader.
        text = _ENTITY_RE.sub(" ", text)
    return " ".join(text.split())


def _comparable(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def product_description_text(row: Mapping[str, Any] | None, *, title: str = "") -> str:
    """The description the feed sent for this product, as a reader would see it.

    "" when the feed sent none, sent only markup, or only repeated the title.
    """
    if not row:
        return ""
    best = ""
    for key in DESCRIPTION_KEYS:
        text = _visible_text(row.get(key))
        if len(text) > len(best):
            best = text
    if not best:
        return ""
    if _comparable(best) == _comparable(title):
        return ""
    return best


def has_sufficient_description(row: Mapping[str, Any] | None, *, title: str = "") -> bool:
    """Did the feed send enough description for this product to be shown?"""
    return len(product_description_text(row, title=title)) >= DESCRIPTION_MIN_CHARS
