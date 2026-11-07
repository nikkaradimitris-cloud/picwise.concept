"""An English product name in its other number: "battery" and "batteries".

The debugging's first measure (owner, 2026-11-07: «ζητάω μία μεγάλη γενική
απασφαλμάτωση»; `deployment/server/print_search_reading.py`) found names a buyer types
in the other number than the lexicon writes them read as another kind or as nothing:
"drill bit" as a drill, "dishwasher pod" as a dishwasher, "external batteries" as AA
batteries; "boot", "sock", "sneaker", "nappy", "hair brushes" as nothing. The fix is one
rule for every name, not a list of words: each English name is read in both numbers
(`concept_understanding._Lexicon`), by this inflection.

Plain English rules, with the words that break them written out: "shelf" and "shelves",
"mouse" and "mice", "hoodie" and "hoodies"; and the words with no other number a buyer
types, or whose other number names another thing ("glasses" are no glass, "jeans" no
jean).
"""
from __future__ import annotations

# Words with no other number a buyer types, or whose other number means another thing.
NO_OTHER_NUMBER = frozenset(
    """
    clothing shelving cookware luggage jewellery jewelry footwear underwear sportswear
    workwear nightwear swimwear activewear knitwear outerwear equipment furniture software
    hardware glasses sunglasses goggles binoculars trousers jeans shorts leggings tights
    pants pyjamas pajamas scissors pliers tongs headphones earphones clothes overalls
    dungarees briefs knickers boxers lingerie hosiery bedding cutlery crockery bakeware
    tableware glassware stationery aircon wifi gps ups hifi
    """.split()
)
PLURAL_OF = {
    "shelf": "shelves", "knife": "knives", "scarf": "scarves", "foot": "feet",
    "mouse": "mice", "child": "children", "man": "men", "woman": "women", "tooth": "teeth",
    "person": "people", "lens": "lenses", "canvas": "canvases", "hoodie": "hoodies",
    "onesie": "onesies", "beanie": "beanies", "tie": "ties", "bootie": "booties",
    "nightie": "nighties", "series": "series", "chassis": "chassis", "gpu": "gpus",
    "cpu": "cpus", "psu": "psus",
}
SINGULAR_OF = {plural: singular for singular, plural in PLURAL_OF.items()}
# The same at the end of a word written as one: "bookshelf" and "bookshelves".
_COMPOUND_ENDINGS = (("shelf", "shelves"), ("knife", "knives"), ("scarf", "scarves"))


def english_word_in_other_number(word: str) -> str | None:
    """One English word in its other number, lower case; None when it has none."""
    lowered = str(word or "").lower()
    if not lowered.isalpha() or len(lowered) < 3 or lowered in NO_OTHER_NUMBER:
        return None
    if lowered in PLURAL_OF:
        return PLURAL_OF[lowered]
    if lowered in SINGULAR_OF:
        return SINGULAR_OF[lowered]
    for singular, plural in _COMPOUND_ENDINGS:
        if lowered.endswith(plural):
            return lowered[: -len(plural)] + singular
        if lowered.endswith(singular):
            return lowered[: -len(singular)] + plural
    if lowered.endswith("ies") and len(lowered) > 4:
        return lowered[:-3] + "y"
    if lowered.endswith(("sses", "shes", "ches", "xes", "zes")):
        return lowered[:-2]
    if lowered.endswith("s") and not lowered.endswith(("ss", "us", "is")):
        return lowered[:-1]
    if lowered.endswith("y") and lowered[-2] not in "aeiou":
        return lowered[:-1] + "ies"
    if lowered.endswith(("s", "sh", "ch", "x", "z")):
        return lowered + "es"
    return lowered + "s"


def english_other_number(name: str) -> str | None:
    """The name with its head word in the other number: the last word, or the word before
    "of" ("chests of drawers"). None when the word has no other number a buyer types."""
    words = str(name or "").split()
    if not words:
        return None
    index = words.index("of") - 1 if "of" in words[1:] else len(words) - 1
    other = english_word_in_other_number(words[index])
    if not other:
        return None
    return " ".join(words[:index] + [other] + words[index + 1:])
