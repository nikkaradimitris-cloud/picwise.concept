"""Print how the search reads every kind's searches, category by category: the first measure of the debugging.

    python3 deployment/server/print_search_reading.py [--category JW ...] [--examples 3] \
        [--json reading.json]

Owner, 2026-11-07: «...μπαταρίες 3α βγάζει μπότες δεν μπορώ να εμπιστευτώ ακόμα αυτό το
service για production σελίδα.. ζητάω μία μεγάλη γενική απασφαλμάτωση», then «Η
απασφαλμάτωση πρέπει να είναι στοχευμένη ανακατηγορία και εκτενέστερη..», and to the method
proposed (category by category; the search read, the products put in each kind, what the
visitor sees; fixed by cause; each error a test; a scoreboard per category, before and
after): «Ναι σε όλα, πάμε σε νέα συζήτηση». This is the method's first check, offline and
free, at the place a search's kind is born:
`picwise_nlu.concept_understanding.understand_product_query`, the reading every search page
takes its kind from. Nothing else is read: no catalogue, no network, no AI.

Searched, per kind of the lexicon (`picwise_nlu.product_concepts`, its 18 categories):

1. every English name, and the name in its other number ("battery" for "batteries");
2. each English name with words added as buyers add them: two brands, a size, a word
   before it, a need after it, "best" and "cheap" (`CATEGORY_WORDS`, one set per category);
3. each English name with a typing slip: a letter left out, a letter doubled, two letters
   swapped, a neighbouring key pressed, at every letter but the first of each word of four
   letters or more (the reader corrects none in a shorter word);
4. every Greek name, a one-word name in its other number where its ending says which, and
   a letter left out, doubled or two swapped (Greek where it is cheap: the site is English).

Each is read as one of: the kind; a broader or a narrower kind of it; another kind of its
category; a kind of another category (the absurd: boots for batteries); nothing. A slip or
an added word that makes another kind's whole name, read as that kind, is right; a reading
that needed a correction is marked "~".

5. the design-time packs' subcategories and product families (`picwise_taxonomy.deep_packs`,
   which the search does not read; the families without their generated tails, "compact
   bench grinder product lines ecosystems" as "compact bench grinder"), each with its
   category: read as a kind of its own category, of another one, or as nothing (a gap: a
   name a buyer may search that no kind holds). A pack filing a kind elsewhere than the
   lexicon does is read by hand, not counted as a fault;
6. every word, alone, of the lexicon's names (and in the other number), of Google's
   taxonomy and of the packs: a word spelt right, read by a correction as a kind none of
   whose names holds it, is a guess ("rubber" as router, «μπαταρία» as boots);
7. every shelf of Google's taxonomy (`concept_understanding._TAXONOMY_PATH`), by its name,
   read as a kind its aisle may not hold (`concept_understanding._aisle_may_hold`, the rule
   the catalogue reads a product's kind by).

The shops' own shelf names, and what the visitor is shown, need the server's catalogue:
the method's second and third checks, measured apart.

Printed: IN SHORT, the scoreboard per category; then each category's faults, grouped; then
every search read as a kind of another category, together. With --json, the scoreboard and
every search not read right, for the comparison after a fix. The same code reads the same
searches the same way. Always exits 0.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
for _folder in (ROOT, ROOT / "src"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from picwise_nlu.concept_understanding import (  # noqa: E402
    _TAXONOMY_PATH,
    CONNECTIVE_WORDS,
    _aisle_may_hold,
    ConceptReading,
    damerau_levenshtein,
    english_key,
    greek_key,
    greeklish_key,
    is_greek_word,
    normalize_understanding_text,
    understand_product_query,
)
from picwise_nlu.misspelling_variants import _QWERTY_NEIGHBOURS  # noqa: E402
from picwise_nlu.product_concepts import (  # noqa: E402
    _MEGA,
    broader_concepts,
    get_product_concepts,
    get_product_concepts_by_id,
)

# A category's short name ("HA") by its id, and the order the lexicon gives them.
CODE_BY_CATEGORY = {category: code for code, category in _MEGA.items()}
CATEGORY_CODES = tuple(_MEGA)

# Per category: two brands buyers in the UK type with its kinds, a size, a word put before
# the name and a need after it. Real brands, since the search must read what buyers type;
# nothing here is shown to anyone.
CATEGORY_WORDS = {
    "HA": ("Bosch", "Dyson", "8kg", "quiet", "for a small flat"),
    "KI": ("Tefal", "Ninja", "1.5 litre", "stainless steel", "for a family"),
    "FU": ("IKEA", "Philips", "120cm", "white", "for a small bedroom"),
    "PH": ("Samsung", "Apple", "128gb", "unlocked", "for the elderly"),
    "CO": ("HP", "Lenovo", "16gb", "wireless", "for students"),
    "AV": ("Sony", "JBL", "55 inch", "wireless", "for travel"),
    "CP": ("Bosch", "Castrol", "12v", "universal", "for a diesel car"),
    "TY": ("Michelin", "Continental", "17 inch", "winter", "for an suv"),
    "MO": ("Shimano", "Giant", "26 inch", "electric", "for commuting"),
    "PT": ("Makita", "DeWalt", "18v", "cordless", "for concrete"),
    "HT": ("Stanley", "Bahco", "10mm", "heavy duty", "for electricians"),
    "GA": ("Hozelock", "Flymo", "10m", "electric", "for a small garden"),
    "HE": ("Omron", "Braun", "2 pack", "digital", "for the elderly"),
    "BE": ("Philips", "Remington", "100ml", "electric", "for sensitive skin"),
    "BK": ("Chicco", "Adidas", "size 4", "kids", "for toddlers"),
    "CL": ("Nike", "Zara", "size 12", "mens", "for winter"),
    "FO": ("Clarks", "Skechers", "size 9", "womens", "for running"),
    "JW": ("Pandora", "Casio", "40mm", "silver", "for women"),
}

# How a search was built from a name, in the order they are listed.
NAME_HOWS = ("name", "number")
WORD_HOWS = ("brand", "size", "before", "need", "best", "cheap")
SLIP_HOWS = ("missing", "doubled", "swapped", "key")

RIGHT = "right"
SPELLS = "spells another kind's name"
BROADER = "a broader kind"
NARROWER = "a narrower kind"
OTHER_KIND = "another kind of the category"
OTHER_CATEGORY = "a kind of another category"
NOTHING = "nothing"
# Read right: the kind, or another kind's whole name typed (a slip or an added word made it).
RIGHT_OUTCOMES = frozenset({RIGHT, SPELLS})


@dataclass(frozen=True)
class Search:
    """One search built from a name: its text, the category and kind it was built for
    (no kind for a pack's name), its language and how it was built."""

    text: str
    category: str
    kind: str | None
    language: str
    how: str
    source: str


@dataclass(frozen=True)
class Reading:
    search: Search
    kind: str | None
    exact: bool
    outcome: str

    @property
    def right(self) -> bool:
        return self.outcome in RIGHT_OUTCOMES

    def shown(self) -> str:
        read = self.kind or "nothing"
        return f'"{self.search.text}" -> {read}{"" if self.exact or not self.kind else " ~"}'


Reader = Callable[[str], ConceptReading]


# --------------------------------------------------------------------------------------
# Grammatical number
# --------------------------------------------------------------------------------------

# Words with no other number a buyer types, or whose other number means another thing
# ("glasses" are no glass).
_NO_OTHER_NUMBER = frozenset(
    """
    clothing shelving cookware luggage jewellery jewelry footwear underwear sportswear
    workwear nightwear swimwear activewear knitwear outerwear equipment furniture software
    hardware glasses sunglasses goggles binoculars trousers jeans shorts leggings tights
    pants pyjamas pajamas scissors pliers tongs headphones earphones clothes overalls
    dungarees briefs knickers boxers lingerie hosiery bedding cutlery crockery bakeware
    tableware glassware stationery luggage aircon wifi gps ups hifi
    """.split()
)
_PLURAL_OF = {
    "shelf": "shelves", "knife": "knives", "scarf": "scarves", "foot": "feet",
    "mouse": "mice", "child": "children", "man": "men", "woman": "women", "tooth": "teeth",
    "person": "people", "lens": "lenses", "canvas": "canvases", "hoodie": "hoodies",
    "onesie": "onesies", "beanie": "beanies", "tie": "ties", "bootie": "booties",
    "nightie": "nighties", "series": "series", "chassis": "chassis", "gpu": "gpus",
    "cpu": "cpus", "psu": "psus",
}
_SINGULAR_OF = {plural: singular for singular, plural in _PLURAL_OF.items()}


def _english_word_in_other_number(word: str) -> str | None:
    lowered = word.lower()
    if not lowered.isalpha() or len(lowered) < 3 or lowered in _NO_OTHER_NUMBER:
        return None
    if lowered in _PLURAL_OF:
        return _PLURAL_OF[lowered]
    if lowered in _SINGULAR_OF:
        return _SINGULAR_OF[lowered]
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
    other = _english_word_in_other_number(words[index])
    if not other:
        return None
    return " ".join(words[:index] + [other] + words[index + 1:])


# Endings whose number is plain, as they are written with their accent: «μπαταρία»
# (feminine, -ία) and «πλυντήρια» (neuter, -ια) are told apart only by the accent.
_GREEK_NUMBER_ENDINGS = (
    ("ματα", "μα"), ("μα", "ματα"),
    ("εία", "είο"), ("είο", "εία"),
    ("ίες", "ία"), ("ία", "ίες"),
    ("ός", "οί"), ("οί", "ός"), ("ος", "οι"), ("οι", "ος"),
    ("ής", "ές"), ("ας", "ες"), ("ης", "ες"),
    ("ό", "ά"), ("ά", "ό"), ("ο", "α"), ("ι", "ια"), ("η", "ες"),
)


def greek_other_number(name: str) -> str | None:
    """A one-word Greek name in its other number, where its ending says which: «μπαταρία»,
    «μπαταρίες»; «ψυγείο», «ψυγεία»; «τηγάνι», «τηγάνια». None for a name of more words, or
    an ending of either number («πλυντήρια», «κουζίνες»)."""
    words = str(name or "").split()
    if len(words) != 1 or not is_greek_word(words[0]):
        return None
    word = words[0].lower()
    for ending, other in _GREEK_NUMBER_ENDINGS:
        if word.endswith(ending):
            return word[: -len(ending)] + other
    # A feminine noun in -α with its accent before it («σκούπα», «καφετιέρα»), not the
    # neuter plural of -ι or -ιο («τηγάνια», «πλυντήρια»).
    if word.endswith("α") and not word.endswith("ια"):
        return word[:-1] + "ες"
    return None


# --------------------------------------------------------------------------------------
# Typing slips
# --------------------------------------------------------------------------------------


def slips(name: str, *, keyboard: bool = True) -> list[tuple[str, str]]:
    """Every typing slip of the name: a letter left out, doubled, two letters swapped and,
    with `keyboard`, a neighbouring key pressed (English keyboard), at every letter but the
    first of each word of four letters or more. As (how, text), in order, repeats kept out."""
    words = normalize_understanding_text(name).split()
    found: list[tuple[str, str]] = []
    seen = {" ".join(words)}

    def add(how: str, index: int, word: str) -> None:
        text = " ".join(words[:index] + [word] + words[index + 1:])
        if text not in seen:
            seen.add(text)
            found.append((how, text))

    for index, word in enumerate(words):
        if len(word) < 4 or not word.isalpha():
            continue
        for at in range(1, len(word)):
            add("missing", index, word[:at] + word[at + 1:])
            add("doubled", index, word[:at] + word[at] + word[at:])
            if at < len(word) - 1 and word[at] != word[at + 1]:
                add("swapped", index, word[:at] + word[at + 1] + word[at] + word[at + 2:])
            if keyboard:
                for key in _QWERTY_NEIGHBOURS.get(word[at], ""):
                    add("key", index, word[:at] + key + word[at + 1:])
    return found


def with_words(name: str, code: str) -> list[tuple[str, str]]:
    """The name with the words buyers add, as (how, text): two brands, a size, a word
    before it, a need after it, "best" and "cheap"."""
    first_brand, second_brand, size, before, need = CATEGORY_WORDS[code]
    return [
        ("brand", f"{first_brand} {name}"),
        ("brand", f"{second_brand} {name}"),
        ("size", f"{name} {size}"),
        ("before", f"{before} {name}"),
        ("need", f"{name} {need}"),
        ("best", f"best {name}"),
        ("cheap", f"cheap {name}"),
    ]


# --------------------------------------------------------------------------------------
# The searches
# --------------------------------------------------------------------------------------


def kind_searches(categories: Iterable[str] | None = None) -> list[Search]:
    """Every search built from the kinds' names (1 to 4 of the module's note), per kind in
    the lexicon's order. A text built twice for one kind is searched once, as built first."""
    wanted = set(categories or CATEGORY_CODES)
    searches: list[Search] = []
    for concept in get_product_concepts():
        code = CODE_BY_CATEGORY[concept.mega_category_id]
        if code not in wanted:
            continue
        seen: set[str] = set()

        def add(text: str, language: str, how: str, source: str) -> None:
            key = normalize_understanding_text(text)
            if key and key not in seen:
                seen.add(key)
                searches.append(Search(text, code, concept.concept_id, language, how, source))

        for name in concept.english:
            add(name, "en", "name", name)
        for name in concept.english:
            other = english_other_number(name)
            if other:
                add(other, "en", "number", name)
        for name in concept.english:
            for how, text in with_words(name, code):
                add(text, "en", how, name)
        for name in concept.english:
            for how, text in slips(name, keyboard=True):
                add(text, "en", how, name)
        for name in concept.greek:
            add(name, "el", "name", name)
        for name in concept.greek:
            other = greek_other_number(name)
            if other:
                add(other, "el", "number", name)
        for name in concept.greek:
            for how, text in slips(name, keyboard=False):
                add(text, "el", how, name)
    return searches


_PACK_MODULES = (
    "home_living_appliances",
    "tech_electronics_office",
    "auto_moto_mobility",
    "tools_diy_garden_repair",
    "health_beauty_family_lifestyle",
    "fashion_footwear_jewelry_accessories",
)
# The tails the packs' product families were generated with ("... family lines taxonomy
# families", "... product lines ecosystems"): cut from the first of `_FAMILY_MARKS` after
# which every word is one of them or of `_FAMILY_TAIL_WORDS`.
_FAMILY_MARKS = frozenset(
    """
    family families line lines product products platform platforms ecosystem ecosystems
    collection collections range ranges system systems taxonomy group groups sets
    """.split()
)
_FAMILY_TAIL_WORDS = _FAMILY_MARKS | frozenset(
    """
    home setup lifecycle compatibility usage workflow routine care daily maintenance
    safety
    """.split()
)


def family_search(family: str) -> str:
    """A pack's product family as a buyer would search it: without its generated tail."""
    words = str(family or "").split()
    for index, word in enumerate(words):
        if index and word in _FAMILY_MARKS and all(rest in _FAMILY_TAIL_WORDS for rest in words[index:]):
            return " ".join(words[:index])
    return " ".join(words)


@lru_cache(maxsize=1)
def _pack_records() -> tuple[dict, ...]:
    import importlib

    records: list[dict] = []
    for name in _PACK_MODULES:
        module = importlib.import_module(f"picwise_taxonomy.deep_packs.{name}")
        records.extend(getattr(module, f"get_{name}_pack")().get("mega_categories", []))
    return tuple(records)


def pack_searches(categories: Iterable[str] | None = None) -> list[Search]:
    """The packs' subcategories as they are and their product families without their
    tails, each once per category (a family that is a subcategory too, as a subcategory)."""
    wanted = set(categories or CATEGORY_CODES)
    searches: list[Search] = []
    for record in _pack_records():
        code = CODE_BY_CATEGORY.get(str(record.get("mega_category_id") or ""))
        if code not in wanted:
            continue
        seen: set[str] = set()
        for how, names in (
            ("subcategory", record.get("subcategories") or ()),
            ("family", [family_search(name) for name in record.get("product_families") or ()]),
        ):
            for name in names:
                key = normalize_understanding_text(name)
                if key and key not in seen:
                    seen.add(key)
                    language = "el" if any(is_greek_word(word) for word in key.split()) else "en"
                    searches.append(Search(name, code, None, language, how, name))
    return searches


# --------------------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _names_of(kind: str) -> frozenset[str]:
    concept = get_product_concepts_by_id()[kind]
    return frozenset(normalize_understanding_text(name) for name in concept.english + concept.greek)


def _category_of(kind: str) -> str:
    return CODE_BY_CATEGORY[get_product_concepts_by_id()[kind].mega_category_id]


def outcome(expected: str, read: str | None, text: str) -> str:
    """What a search built for `expected` was read as."""
    if read is None:
        return NOTHING
    if read == expected:
        return RIGHT
    if normalize_understanding_text(text) in _names_of(read):
        return SPELLS
    if read in broader_concepts(expected)[1:]:
        return BROADER
    if expected in broader_concepts(read)[1:]:
        return NARROWER
    return OTHER_KIND if _category_of(read) == _category_of(expected) else OTHER_CATEGORY


def pack_outcome(code: str, read: str | None) -> str:
    """What a pack's name of category `code` was read as: its own category's kind, another
    category's, or nothing."""
    if read is None:
        return NOTHING
    return RIGHT if _category_of(read) == code else OTHER_CATEGORY


def _read_kind(reading: ConceptReading) -> tuple[str | None, bool]:
    if not reading.understood:
        return None, True
    return str(reading.concept_id), bool(reading.exact)


def read_searches(searches: Iterable[Search], reader: Reader = understand_product_query) -> list[Reading]:
    readings: list[Reading] = []
    for search in searches:
        kind, exact = _read_kind(reader(search.text))
        if search.kind is None:
            result = pack_outcome(search.category, kind)
        else:
            result = outcome(search.kind, kind, search.text)
        readings.append(Reading(search, kind, exact, result))
    return readings


@dataclass(frozen=True)
class WordGuess:
    """A word spelt right, read alone by a correction as a kind none of whose names holds
    it; `holders` are the kinds whose names do."""

    word: str
    source: str
    kind: str
    nearest: str
    holders: tuple[str, ...]

    @property
    def category(self) -> str:
        return _category_of(self.kind)

    @property
    def across(self) -> bool:
        """The guess is a kind of another category than every kind holding the word."""
        return bool(self.holders) and all(_category_of(h) != self.category for h in self.holders)


def _taxonomy_lines() -> list[str]:
    try:
        lines = _TAXONOMY_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line for line in lines if line.strip() and not line.startswith("#")]


def _words_with_holders() -> dict[str, tuple[str, set[str]]]:
    """Every word to read alone, with where it comes from and the kinds whose names hold
    it: the names' words and, in the other number, their holders' too; then Google's
    taxonomy's and the packs' words, held by none unless a name holds them."""
    words: dict[str, tuple[str, set[str]]] = {}
    for concept in get_product_concepts():
        for name in concept.english + concept.greek:
            for word in normalize_understanding_text(name).split():
                words.setdefault(word, ("a name's word", set()))[1].add(concept.concept_id)
    for concept in get_product_concepts():
        for name in concept.english + concept.greek:
            for word in name.split():
                if len(word) < 4 or normalize_understanding_text(word) in CONNECTIVE_WORDS:
                    continue
                greek = is_greek_word(word)
                other = greek_other_number(word) if greek else _english_word_in_other_number(word)
                if not other:
                    continue
                key = normalize_understanding_text(other)
                holders = words.get(normalize_understanding_text(word), ("", set()))[1]
                if key and " " not in key:
                    words.setdefault(key, ("a name's word in the other number", set()))[1].update(holders)
    for line in _taxonomy_lines():
        for word in normalize_understanding_text(line).split():
            words.setdefault(word, ("Google's taxonomy", set()))
    for record in _pack_records():
        for field_name in ("departments", "subcategories", "product_families"):
            for text in record.get(field_name) or ():
                for word in normalize_understanding_text(text).split():
                    words.setdefault(word, ("the packs", set()))
    return {word: found for word, found in words.items() if len(word) >= 4 and word.isalpha()}


def _nearest_name_word(word: str, kind: str) -> str:
    """The word of the kind's names the reader most likely took this word for, compared
    by the keys the reader compares (an English word as English and as greeklish, a Greek
    one by its sound): "pones" is taken for «πάνες», not for "nappies"."""
    concept = get_product_concepts_by_id()[kind]
    candidates: set[tuple[str, str]] = set()
    for name in concept.english + concept.greek:
        for part in normalize_understanding_text(name).split():
            candidates.add((greek_key(part) if is_greek_word(part) else english_key(part), part))
    if not candidates:
        return ""
    keys = {greek_key(word)} if is_greek_word(word) else {english_key(word), greeklish_key(word)}
    return min(
        candidates,
        key=lambda found: (min(damerau_levenshtein(key, found[0], 9) for key in keys), found[1]),
    )[1]


def word_guesses(reader: Reader = understand_product_query) -> tuple[int, list[WordGuess]]:
    """How many words were read alone, and the guesses among them (6 of the module's note)."""
    words = _words_with_holders()
    guesses: list[WordGuess] = []
    for word in sorted(words):
        source, holders = words[word]
        kind, exact = _read_kind(reader(word))
        if kind is None or exact or kind in holders:
            continue
        guesses.append(WordGuess(word, source, kind, _nearest_name_word(word, kind), tuple(sorted(holders))))
    return len(words), guesses


@dataclass(frozen=True)
class ShelfReading:
    shelf: str
    path: str
    kind: str
    exact: bool

    @property
    def category(self) -> str:
        return _category_of(self.kind)


def shelf_readings(reader: Reader = understand_product_query) -> tuple[int, list[ShelfReading]]:
    """How many of Google's shelves were read, and those read as a kind their aisle may
    not hold (7 of the module's note)."""
    lines = _taxonomy_lines()
    found: list[ShelfReading] = []
    for line in lines:
        shelf = line.split(">")[-1].strip()
        kind, exact = _read_kind(reader(shelf))
        if kind is not None and not _aisle_may_hold(line, kind):
            found.append(ShelfReading(shelf, line, kind, exact))
    return len(lines), found


# --------------------------------------------------------------------------------------
# The scoreboard
# --------------------------------------------------------------------------------------


def _part(reading: Reading) -> str:
    """Which column of the scoreboard a reading counts in."""
    search = reading.search
    if search.kind is None:
        return "packs"
    if search.language == "el":
        return "greek"
    if search.how in NAME_HOWS:
        return "names"
    if search.how in WORD_HOWS:
        return "with words"
    return "slips"


PARTS = ("names", "with words", "slips", "greek", "packs")


def scoreboard(
    readings: Iterable[Reading],
    guesses: Iterable[WordGuess] = (),
    shelves: Iterable[ShelfReading] = (),
    categories: Iterable[str] | None = None,
) -> dict[str, dict[str, object]]:
    """Per category: the kinds; per part, the searches and how they were read; the words
    guessed into its kinds; Google's shelves read as its kinds on an aisle that may not
    hold them."""
    wanted = list(categories or CATEGORY_CODES)
    board: dict[str, dict[str, object]] = {}
    for code in wanted:
        kinds = [c for c in get_product_concepts() if CODE_BY_CATEGORY[c.mega_category_id] == code]
        board[code] = {
            "category": _MEGA[code],
            "kinds": len(kinds),
            "narrower kinds": sum(1 for c in kinds if c.broader),
            **{part: Counter() for part in PARTS},
            "words guessed": 0,
            "words guessed across": 0,
            "shelves": 0,
        }
    for reading in readings:
        row = board.get(reading.search.category)
        if row is not None:
            row[_part(reading)][reading.outcome] += 1
    for guess in guesses:
        row = board.get(guess.category)
        if row is not None:
            row["words guessed"] += 1
            row["words guessed across"] += int(guess.across)
    for shelf in shelves:
        row = board.get(shelf.category)
        if row is not None:
            row["shelves"] += 1
    return board


def _share(counter: Counter, outcomes: frozenset[str] = RIGHT_OUTCOMES) -> str:
    total = sum(counter.values())
    if not total:
        return "-"
    right = sum(count for result, count in counter.items() if result in outcomes)
    return f"{right:,}/{total:,} ({100 * right / total:.1f}%)"


def _faults(counter: Counter) -> str:
    parts = [
        f"{counter[result]:,} {label}"
        for result, label in (
            (OTHER_CATEGORY, "another category"),
            (OTHER_KIND, "another kind"),
            (BROADER, "broader"),
            (NARROWER, "narrower"),
            (NOTHING, "nothing"),
        )
        if counter[result]
    ]
    return ", ".join(parts) or "none"


def scoreboard_lines(board: dict[str, dict[str, object]]) -> list[str]:
    lines: list[str] = []
    totals: dict[str, Counter] = {part: Counter() for part in PARTS}
    guessed = across = shelves = 0
    for code, row in board.items():
        absurd = sum(row[part][OTHER_CATEGORY] for part in PARTS[:4])
        lines.append(
            f"{code} {row['category']}: {row['kinds']} kinds ({row['narrower kinds']} narrower);"
            f" {absurd:,} of its searches read as a kind of another category"
        )
        for part in PARTS[:4]:
            counter = row[part]
            totals[part].update(counter)
            if sum(counter.values()):
                lines.append(f"    {part:<10} right {_share(counter)}; faults: {_faults(counter)}")
        packs = row["packs"]
        totals["packs"].update(packs)
        if sum(packs.values()):
            lines.append(
                f"    {'packs':<10} {packs[RIGHT]:,} its own kinds, {packs[OTHER_CATEGORY]:,} another category's,"
                f" {packs[NOTHING]:,} nothing (of {sum(packs.values()):,})"
            )
        guessed += int(row["words guessed"])
        across += int(row["words guessed across"])
        shelves += int(row["shelves"])
        lines.append(
            f"    {'guesses':<10} {row['words guessed']} words spelt right read as its kinds by a correction"
            f" ({row['words guessed across']} of another category's words); {row['shelves']} of Google's"
            " shelves read as its kinds on an aisle that may not hold them"
        )
    lines.append("ALL")
    for part in PARTS[:4]:
        lines.append(f"    {part:<10} right {_share(totals[part])}; faults: {_faults(totals[part])}")
    packs = totals["packs"]
    lines.append(
        f"    {'packs':<10} {packs[RIGHT]:,} their own kinds, {packs[OTHER_CATEGORY]:,} another category's,"
        f" {packs[NOTHING]:,} nothing (of {sum(packs.values()):,})"
    )
    lines.append(f"    {'guesses':<10} {guessed} words ({across} across categories); {shelves} shelves")
    return lines


# --------------------------------------------------------------------------------------
# The faults, printed
# --------------------------------------------------------------------------------------


def _grouped(readings: list[Reading], examples: int) -> list[str]:
    """Faults grouped by the kind built for, what it was read as and how it was read."""
    groups: dict[tuple[str, str, str], list[Reading]] = defaultdict(list)
    for reading in readings:
        groups[(str(reading.search.kind), reading.kind or "nothing", reading.outcome)].append(reading)
    lines = []
    for (kind, read, result), members in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        shown = "; ".join(f'"{m.search.text}"{"" if m.exact or not m.kind else " ~"}' for m in members[:examples])
        lines.append(f"      {kind} -> {read} ({result}): {len(members)}, e.g. {shown}")
    return lines


def category_lines(
    code: str,
    readings: list[Reading],
    guesses: list[WordGuess],
    shelves: list[ShelfReading],
    examples: int,
) -> list[str]:
    mine = [r for r in readings if r.search.category == code]
    lines = [f"== {code} {_MEGA[code]}"]

    def section(title: str, faults: list[Reading], *, every: bool = False) -> None:
        if not faults:
            return
        lines.append(f"  {title}: {len(faults):,}")
        if every:
            for reading in faults:
                lines.append(f"      {reading.search.kind}: {reading.shown()} ({reading.outcome}; {reading.search.how})")
        else:
            lines.extend(_grouped(faults, examples))

    english = [r for r in mine if r.search.kind and r.search.language == "en"]
    greek = [r for r in mine if r.search.kind and r.search.language == "el"]
    section(
        "English names, as written or in the other number, not read right",
        [r for r in english if r.search.how in NAME_HOWS and not r.right],
        every=True,
    )
    for how in WORD_HOWS:
        section(
            f'English names with words added ({how}), not read right',
            [r for r in english if r.search.how == how and not r.right],
        )
    section(
        "English slips read as another kind",
        [r for r in english if r.search.how in SLIP_HOWS and not r.right and r.outcome != NOTHING],
    )
    unread = [r for r in english if r.search.how in SLIP_HOWS and r.outcome == NOTHING]
    if unread:
        per_kind = Counter(r.search.kind for r in unread)
        total = Counter(r.search.kind for r in english if r.search.how in SLIP_HOWS)
        lines.append(f"  English slips read as nothing: {len(unread):,}, per kind (of its slips):")
        lines.append(
            "      "
            + "; ".join(f"{kind} {count}/{total[kind]}" for kind, count in sorted(per_kind.items(), key=lambda i: (-i[1], i[0])))
        )
    section(
        "Greek names, as written or in the other number, not read right",
        [r for r in greek if r.search.how in NAME_HOWS and not r.right],
        every=True,
    )
    section(
        "Greek slips read as another kind",
        [r for r in greek if r.search.how in SLIP_HOWS and not r.right and r.outcome != NOTHING],
    )
    packs = [r for r in mine if r.search.kind is None]
    across = [r for r in packs if r.outcome == OTHER_CATEGORY]
    if across:
        lines.append(f"  The packs' names read as another category's kind (read by hand): {len(across)}")
        for reading in across:
            lines.append(
                f"      {reading.search.how}: {reading.shown()} ({_category_of(str(reading.kind))})"
            )
    gaps = [r for r in packs if r.outcome == NOTHING]
    if gaps:
        lines.append(f"  The packs' names read as nothing (gaps, or no product's name): {len(gaps)}")
        lines.append("      " + "; ".join(f'"{r.search.text}"' for r in gaps))
    mine_guesses = [g for g in guesses if g.category == code]
    if mine_guesses:
        lines.append(f"  Words spelt right read as its kinds by a correction: {len(mine_guesses)}")
        for guess in mine_guesses:
            held = f"; its kinds: {', '.join(guess.holders)}" if guess.holders else ""
            mark = " ACROSS" if guess.across else ""
            lines.append(f'      "{guess.word}" -> {guess.kind} (as "{guess.nearest}"; {guess.source}{held}){mark}')
    mine_shelves = [s for s in shelves if s.category == code]
    if mine_shelves:
        lines.append(f"  Google's shelves read as its kinds on an aisle that may not hold them: {len(mine_shelves)}")
        for shelf in mine_shelves:
            lines.append(f'      "{shelf.shelf}" -> {shelf.kind}{"" if shelf.exact else " ~"} ({shelf.path})')
    if len(lines) == 1:
        lines.append("  no fault")
    return lines


def absurd_lines(readings: list[Reading], guesses: list[WordGuess]) -> list[str]:
    """Every search built for a kind and read as a kind of another category, by the
    category it was built for; then every word of a name read alone as a kind of another
    category than its own kinds': the boots for batteries."""
    lines = []
    for code in CATEGORY_CODES:
        mine = [
            r for r in readings
            if r.search.category == code and r.search.kind and r.outcome == OTHER_CATEGORY
        ]
        if not mine:
            continue
        lines.append(f"  {code}: {len(mine):,}")
        for reading in mine:
            lines.append(
                f"      {reading.search.kind}: {reading.shown()} ({_category_of(str(reading.kind))};"
                f" {reading.search.language} {reading.search.how})"
            )
    across = [g for g in guesses if g.across]
    if across:
        lines.append(f"  Words of the names, alone: {len(across)}")
        for guess in across:
            held = ", ".join(f"{h} ({_category_of(h)})" for h in guess.holders)
            lines.append(f'      "{guess.word}" -> {guess.kind} ({guess.category}; as "{guess.nearest}"), its kinds: {held}')
    return lines or ["  none"]


def _fault_record(reading: Reading) -> dict[str, object]:
    search = reading.search
    return {
        "text": search.text,
        "category": search.category,
        "kind": search.kind,
        "language": search.language,
        "how": search.how,
        "source": search.source,
        "read": reading.kind,
        "exact": reading.exact,
        "outcome": reading.outcome,
    }


def _board_record(board: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        code: {key: (dict(value) if isinstance(value, Counter) else value) for key, value in row.items()}
        for code, row in board.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--category", action="append", choices=CATEGORY_CODES, help="read these categories only")
    parser.add_argument("--examples", type=int, default=3, help="examples per group of faults")
    parser.add_argument("--json", help="write the scoreboard and every fault here")
    args = parser.parse_args(argv)
    categories = tuple(args.category or CATEGORY_CODES)
    whole = set(categories) == set(CATEGORY_CODES)

    started = time.time()
    searches = kind_searches(categories) + pack_searches(categories)
    readings = read_searches(searches)
    read_words, guesses = word_guesses()
    read_shelves, shelves = shelf_readings()
    if not whole:
        guesses = [g for g in guesses if g.category in categories or any(_category_of(h) in categories for h in g.holders)]
        shelves = [s for s in shelves if s.category in categories]
    board = scoreboard(readings, guesses, shelves, categories)
    took = time.time() - started

    kinds = len({r.search.kind for r in readings if r.search.kind})
    print("PicWise: how the search reads every kind's searches (the debugging's first measure)")
    print(
        f"Read: {len(searches):,} searches built for {kinds} kinds of {len(categories)} categories"
        f" and from the packs, {read_words:,} words alone, {read_shelves:,} of Google's shelves;"
        f" {took:.0f} s. Right: the kind, or another kind's whole name typed; ~ a correction."
    )
    print()
    print("IN SHORT, per category")
    for line in scoreboard_lines(board):
        print(line)
    print()
    print("Every search read as a kind of another category, and every word guessed across categories")
    for line in absurd_lines(readings, guesses):
        print(line)
    for code in categories:
        print()
        for line in category_lines(code, readings, guesses, shelves, max(1, args.examples)):
            print(line)

    if args.json:
        record = {
            "categories": list(categories),
            "searches": len(searches),
            "scoreboard": _board_record(board),
            "faults": [_fault_record(r) for r in readings if not r.right],
            "word guesses": [
                {"word": g.word, "source": g.source, "read": g.kind, "as": g.nearest, "kinds": list(g.holders)}
                for g in guesses
            ],
            "shelves": [{"shelf": s.shelf, "path": s.path, "read": s.kind, "exact": s.exact} for s in shelves],
        }
        Path(args.json).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print()
        print(f"Written: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
