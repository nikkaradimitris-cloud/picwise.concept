"""Whether the provider feed says a product is not new, and the words it said it with.

Owner decision (2026-10-10, recorded in `docs/PICWISE_DECISION_CONTRACT.md`):
refurbished, used and other non-new products are shown only when the buyer asks for
them. Both the selection gate and the card disclosure read the condition through this
module, so what is hidden by default and what a shown card admits cannot drift apart.

A product counts as non-new when the feed itself says so, in one of two places:

- **A condition column** (`condition`, `product_condition`, `item_condition`) that
  carries a word meaning not new ("Refurbished Grade A", "Used - Very Good",
  "gebraucht"). Wording this module cannot read ("A-stock", "Nuovo", "n/a", a bare
  code) is treated as **unknown**, not as non-new, and the product stays visible.
  That direction is deliberate: not understanding a word is not knowing the item is
  used, and the opposite default would empty a whole feed in silence the day a
  merchant writes its condition in wording PicWise has never seen. The cost is the
  other way round -- an unread wording that did mean "used" shows up unasked -- which
  is visible and fixable: `tools/check_awin_feed.py` lists the condition values it
  could not read, so they can be added here.
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

# Values that mean a new item. The gate never relies on this set -- a value is
# excluded only when it carries a word from the vocabulary below -- but
# `tools/check_awin_feed.py` uses it to tell an understood "new" from a wording
# PicWise cannot read and should be shown to the operator.
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

# Words in a condition column that mean the item is not new. A column is a declared
# field, so "used" and "renewed" are trusted here, unlike in marketing text. Matched
# inside the value, because feeds grade them ("Used - Very Good", "Refurbished Grade
# A"). The non-English words are the ones a European feed is likeliest to use; a
# wording not listed here is unknown, not non-new (see the module docstring).
_COLUMN_NON_NEW_PHRASES = (
    "used",
    "renewed",
    "not new",
    "like new",
    "customer return",
    "customer returned",
    "usato",
    "usata",
    "usado",
    "usada",
    "segunda mano",
    "gebraucht",
    "generaluberholt",
    "generalüberholt",
    "occasion",
    "seconde main",
    "reconditionne",
    "reconditionné",
    "ricondizionato",
    "reacondicionado",
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
# A grade with its wording, the way refurbishers title a graded item: "(Grade A1 - Like
# New)", "(Grade B - Average)". Measured on the third real feed (2026-10-16): 158
# laptops, desktops and televisions at Back to the Office, with an empty condition
# column, which price order put first in their kinds. "Grade" alone is not enough:
# "Commercial Grade TV Wall Mount" and "military grade rugged case" are new.
_GRADED_CONDITION_PATTERN = (
    r"\bgrade\s+[a-d][0-9+]?\s*[-\u2013:]\s*"
    r"(?:like new|excellent|very good|good|average|fair|acceptable|pristine|poor)\b"
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
            _GRADED_CONDITION_PATTERN,
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
    "grade",
    "σμεν",
    "σμέν",
)
# The column is a declared field, so it is read with the text vocabulary plus the
# words that are only trusted when a feed states them as the condition.
_COLUMN_NON_NEW_RE = re.compile(
    "|".join(
        [
            r"\b(?:"
            + "|".join(
                re.escape(phrase)
                for phrase in (_NON_NEW_TEXT_PHRASES + _COLUMN_NON_NEW_PHRASES)
            )
            + r")\b",
            *[rf"\b{_accent_insensitive(stem)}\w*" for stem in _GREEK_NON_NEW_STEMS],
        ]
    ),
    flags=re.IGNORECASE | re.UNICODE,
)
_PUNCTUATION_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)


# A product data sheet written into the description ("... Form factor. Clamshell.
# Refurbished. Yes. Display. ...") states the condition as a field, unlike the prose
# around it. Measured on the third real feed (2026-10-17): 22 refurbished laptops and
# desktops at Back to the Office (A2C, T1A, Circular Computing) say so only there,
# with an empty condition column. The prose is not read: 616 new UPS batteries say
# "No Refurbished or Re-used Parts", and printer inks list "PIXMA iP2600 Refurbished"
# among the printers they fit.
_DECLARED_REFURBISHED_RE = re.compile(r"\brefurbished\s*[.:]\s*yes\b", flags=re.IGNORECASE)


def stated_condition(row: Mapping[str, Any] | None) -> str:
    """The condition the feed row states, whitespace collapsed, or "".

    The condition columns first; when they are silent, a "Refurbished: Yes" field in
    the description's data sheet, as "refurbished".
    """
    if not row:
        return ""
    for key in CONDITION_KEYS:
        value = " ".join(str(row.get(key) or "").split())
        if value:
            return value
    description = str(row.get("description") or "")
    # A substring check first: this runs once per product of the feed on every search.
    if ("efurbished" in description or "EFURBISHED" in description) and (
        _DECLARED_REFURBISHED_RE.search(description)
    ):
        return "refurbished"
    return ""


def _comparable(value: str) -> str:
    collapsed = " ".join(str(value or "").lower().replace("-", " ").replace("_", " ").split())
    return " ".join(_PUNCTUATION_RE.sub(" ", collapsed).split())


def condition_value_is_non_new(condition: str) -> bool:
    """Does this condition value say the item is not new?

    Only a value carrying a word from the vocabulary does. Wording PicWise cannot read
    ("A-stock", "Nuovo", "n/a", a bare code) says nothing it can act on, and a feed
    whose whole column is written that way must keep working rather than vanish.
    """
    return bool(_COLUMN_NON_NEW_RE.search(_comparable(condition)))


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
