"""A shop's name as a buyer knows it, on its card and the card's button (owner, 2026-11-13,
to the list of what waited in the design: «Τι περιμένεις?»).

Awin gives a shop's name as its affiliate programme is called: the button read "View at
Geepas Partner Program". Only the words that name a programme come off, never a word of the
shop's own name, and nothing is added:

- "Geepas Partner Program" reads "Geepas"; "Watch Enclave Affiliate Programme" "Watch
  Enclave"; "MONÉ UK Affiliate Programme" "MONÉ UK"; "Atenai London Affiliation
  Marketing" "Atenai London";
- "Affiliates - Spoiled Brat" reads "Spoiled Brat";
- "MonsterPiercing -Quality Piercing Jewellery", a strapline after a dash written against
  it, reads "MonsterPiercing";
- "Greenera (UK)" reads "Greenera", "SafeFort (UK)" "SafeFort".

A name these would leave empty is kept as Awin gives it. Of the 75 shops of 12/11 these
were the eight; "Shopping Ads: Google & Bing" names no shop and is kept as it is, for the
owner to ask Awin about.
"""
from __future__ import annotations

import re

_PROGRAMME_PREFIX = re.compile(r"^(?:affiliates?|affiliate\s+program(?:me)?)\s*[-–:]\s*", re.IGNORECASE)
_PROGRAMME_SUFFIX = re.compile(
    r"\s+(?:partner|affiliate|affiliates|affiliation)\s+(?:program|programme|marketing)\s*$",
    re.IGNORECASE,
)
# A strapline after a dash written against it ("MonsterPiercing -Quality ..."); a dash
# with a space on both sides may be part of a name, and is kept.
_STRAPLINE = re.compile(r"\s+-(?=\S).*$")
_COUNTRY_IN_BRACKETS = re.compile(r"\s*\((?:uk|gb)\)\s*$", re.IGNORECASE)


def shop_display_name(name: str) -> str:
    """The shop's name without the words of its affiliate programme (see above)."""
    original = " ".join(str(name or "").split()).strip()
    shown = _PROGRAMME_PREFIX.sub("", original)
    shown = _PROGRAMME_SUFFIX.sub("", shown)
    shown = _STRAPLINE.sub("", shown)
    shown = _COUNTRY_IN_BRACKETS.sub("", shown).strip()
    return shown or original
