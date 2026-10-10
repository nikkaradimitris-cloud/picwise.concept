"""Whether the provider feed says a product is not new, and the words it said it with.

Owner decision (2026-10-10, recorded in `docs/PICWISE_DECISION_CONTRACT.md`):
refurbished, used and other non-new products are shown only when the buyer asks for
them. Both the selection gate and the card disclosure read the condition through this
module, so what is hidden by default and what a shown card admits cannot drift apart.

A product counts as non-new when the feed itself says so, in one of two places:

- **A condition column** (`condition`, `product_condition`, `item_condition`) whose
  value is not a "new" value. A value that carries no information ("n/a", "unknown",
  "-", a bare number) is read as unknown, not as non-new: a sloppy column must not
  empty a whole feed. Any other wording is taken at face value, including wordings
  this module has no vocabulary for ("usato", "grade b"), because a feed that bothered
  to write something other than "new" there is saying something.
- **The product's own text** (title, product type, category), where many merchants put
  it instead ("Refurbished Dell Latitude", "Open Box"). Only words that can mean
  nothing else count here. "used" and "renewed" are deliberately not among them:
  marketing text uses them for other things ("used by professionals", "renewed
  formula"), while a condition column does not.

Nothing here judges a product. It reports what the feed stated, in the feed's words.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

# The columns a feed states an item's condition in, in the order they are trusted.
CONDITION_KEYS = ("condition", "product_condition", "item_condition")

# Values that mean a new item.
NEW_CONDITION_VALUES = frozenset(
    {
        "new",
        "brand new",
        "new with tags",
        "new with box",
        "new in box",
        "new other",
    }
)

# Values that state nothing: an empty column filled with a placeholder. Reading these
# as non-new would hide every product of a feed whose condition column is unpopulated.
_NO_INFORMATION_VALUES = frozenset(
    {
        "",
        "-",
        "--",
        "n a",
        "na",
        "none",
        "null",
        "nil",
        "unknown",
        "unspecified",
        "not specified",
        "not applicable",
        "not available",
    }
)

# Words in a product's own text that can only mean a non-new item. Kept narrow on
# purpose: this text is marketing copy, not a declared field.
_NON_NEW_TEXT_PHRASES = (
    "refurbished",
    "refurb",
    "refurbs",
    "reconditioned",
    "pre owned",
    "preowned",
    "second hand",
    "secondhand",
    "open box",
    "openbox",
    "ex display",
    "ex demo",
)
# Greek says it with an ending on a stem, and every ending says the same thing
# ("μεταχειρισμένο", "μεταχειρισμένα", "μεταχειρισμένος"), so the stem is matched and
# the whole word the feed wrote is reported back.
_GREEK_NON_NEW_STEMS = ("μεταχειρισμεν", "ανακατασκευασμεν", "ανακαινισμεν")
_GREEK_ACCENTS = {
    "α": "αά", "ε": "εέ", "η": "ηή", "ι": "ιίϊΐ", "ο": "οό", "υ": "υύϋΰ", "ω": "ωώ",
}


def _accent_insensitive(stem: str) -> str:
    """The stem with every vowel allowed to carry its accent, as feed text writes it."""
    return "".join(
        f"[{_GREEK_ACCENTS[ch]}]" if ch in _GREEK_ACCENTS else re.escape(ch) for ch in stem
    )


# One pattern, not one per word: this runs once per product of the feed on every
# search, and PROJECT_RULES section 9 leaves no room for a scan per vocabulary entry.
_NON_NEW_TEXT_RE = re.compile(
    "|".join(
        [
            r"\b(?:" + "|".join(re.escape(phrase) for phrase in _NON_NEW_TEXT_PHRASES) + r")\b",
            *[rf"\b{_accent_insensitive(stem)}\w*" for stem in _GREEK_NON_NEW_STEMS],
        ]
    ),
    flags=re.IGNORECASE | re.UNICODE,
)
# A cheap pre-filter in front of that alternation, which costs ten times a substring
# check on the same text. Every hint is a fragment of a pattern above -- "σμεν" and
# "σμέν" cover the one syllable of the Greek stems that can carry an accent -- so
# nothing the pattern matches can fail the filter. `test_picwise_condition_request`
# pins that over the vocabulary itself: a hint missing for a phrase would silently
# show a used product to a buyer who never asked for one.
_NON_NEW_TEXT_HINTS = (
    "refurb",
    "recondition",
    "owned",
    "hand",
    "box",
    "ex di",
    "ex de",
    "σμεν",
    "σμέν",
)
_PUNCTUATION_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)


def stated_condition(row: Mapping[str, Any] | None) -> str:
    """The condition the feed row states, whitespace collapsed, or ""."""
    if not row:
        return ""
    for key in CONDITION_KEYS:
        value = " ".join(str(row.get(key) or "").split())
        if value:
            return value
    return ""


def _comparable(value: str) -> str:
    collapsed = " ".join(str(value or "").lower().replace("-", " ").replace("_", " ").split())
    return " ".join(_PUNCTUATION_RE.sub(" ", collapsed).split())


def condition_value_is_non_new(condition: str) -> bool:
    """Does this condition value say the item is not new?

    A value that is a "new" value, carries no information, or is a bare number (a feed
    code PicWise cannot read) says nothing about wear, so it is not read as non-new.
    """
    comparable = _comparable(condition)
    if comparable in _NO_INFORMATION_VALUES or comparable in NEW_CONDITION_VALUES:
        return False
    return not comparable.replace(" ", "").isdigit()


def non_new_words_in_text(text: str) -> str:
    """The non-new words a product's own text carries, as the feed wrote them, or ""."""
    haystack = str(text or "")
    if not haystack:
        return ""
    lowered = haystack.lower()
    if not any(hint in lowered for hint in _NON_NEW_TEXT_HINTS):
        return ""
    match = _NON_NEW_TEXT_RE.search(haystack)
    # Quote the feed's own words ("Refurbished", "μεταχειρισμένος"), not the pattern.
    return " ".join(match.group(0).split()) if match else ""


def non_new_condition(*, condition: str = "", text: str = "") -> str:
    """What the feed said to call this item not new, or "" when it did not say so.

    The condition column wins when it states anything readable; the product's own text
    is read only when the column is silent.
    """
    stated = " ".join(str(condition or "").split())
    if stated:
        return stated if condition_value_is_non_new(stated) else ""
    return non_new_words_in_text(text)


def product_text_for_condition(parts: Iterable[Any]) -> str:
    """The product text the condition words are looked for in."""
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())
