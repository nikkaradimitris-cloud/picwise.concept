"""What a card says of its product's variants at the shop.

Owner, 2026-11-19, shown a drawing of the card: (1) a shop whose page holds the variants,
«δείχνουμε τις διαφορετικές παραλλαγές στην ίδια κάρτα»; (2) a shop listing each variant
as a product of its own, grouped, «πάλι δείχνουμε μία κάρτα». Earlier the same day:
«εμείς βάζουμε μία καταχώρηση και λέμε συμπεριλαμβάνονται χρώματα … μεγέθη …
χωρητικότητα στο κατάστημα».

From the titles of one shop's listings of one product (the card's first), the words that
tell them apart, by kind: colours, sizes, capacities, power, and other options (a print,
a finish, a pack). Only what reads as a variant is said. A title that differs in more
than one thing of a kind, or whose difference reads as nothing a buyer picks
("Funny Housewarming Gifts"), leaves the card without the line: no line is better than
words that are not the variants.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from .product_variants import _COLOURS, _LETTER_SIZES

COLOURS = "colours"
SIZES = "sizes"
CAPACITIES = "capacities"
POWER = "power"
OPTIONS = "options"
# The order the card names them in, and how many it names.
KINDS = (COLOURS, OPTIONS, SIZES, CAPACITIES, POWER)
KINDS_SHOWN = 2
# The titles read for one card at most: a page of a shop can hold hundreds of rows.
TITLES_READ = 200

# Where a title passes from one part to the next: "Satin Sleep Mask - Snake Print - Sleep
# Mask Only", "Runner | Black / 9", "Henna Mehendi (Pack of 2)".
_PART_END_RE = re.compile(r"\s+[-–—|/]\s+|,\s+|\s*[()]\s*")
_UNITS = (
    r"ml|l|ltr|litres?|liters?|g|gms?|kg|oz|gb|tb|mb|mah|ah|w|kw|v|cm|mm|m|in|inch(?:es)?|ft"
    r"|pcs|pc|pk|packs?|pairs?|pieces?|seater|seats?|person|people"
)
# A part's words: an amount with its unit as one ("70 ml", "128GB", "2 Seater"), else a
# word or a number ("2XL", "AW420K", "33\"", "0.5").
_TOKEN_RE = re.compile(
    rf"\d+(?:[.,]\d+)?\s?(?:{_UNITS})(?![^\W_])"
    r"|[^\W_]+(?:[.,]\d+)*(?:['’][^\W_]+)?(?:\"|”|″)?",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(rf"^(\d+(?:[.,]\d+)?)({_UNITS})$", re.IGNORECASE)
_CAPACITY_UNITS = {"mb": 0.001, "gb": 1.0, "tb": 1000.0, "mah": 1.0, "ah": 1000.0}
_POWER_UNITS = {"w": 1.0, "kw": 1000.0, "v": 1.0}
_PACK_UNITS = re.compile(r"^(?:pcs|pc|pk|packs?|pairs?|pieces?)$")
_COLOUR_MODIFIERS = frozenset(
    "light dark pale bright deep matte matt metallic neon hot baby royal sky off jet dusty washed mid midnight "
    "and gloss glossy".split()
)
_SIZE_NAMES = frozenset(
    "size sizes uk eu us y yr yrs year years month months mth mths small medium large extra regular petite tall "
    "single double king queen super emperor cot one waist leg chest neck inside".split()
)
_PAPER_SIZE_RE = re.compile(r"^a[0-6]$")
# The words a size follows: "Size 9", "UK 10".
_SIZE_LEAD = frozenset("size uk eu us".split())
_LETTER_ORDER = {
    size: rank
    for rank, names in enumerate(
        ("xxs", "xs", "s", "m", "l", "xl", "xxl 2xl", "xxxl 3xl", "4xl", "5xl", "6xl")
    )
    for size in names.split()
}


def _key(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _tokens(text: str) -> list[re.Match[str]]:
    return list(_TOKEN_RE.finditer(text))


def _parts(title: str) -> list[str]:
    parts = (part.strip(" -\u2013\u2014|/,") for part in _PART_END_RE.split(title) if part)
    return [part for part in parts if part]


def _part_key(part: str) -> str:
    return " ".join(_key(token.group(0)) for token in _tokens(part))


def kind_of(value: str) -> str:
    """The kind of variant a value names: colours, sizes, capacities, power or options."""
    words = [_key(token.group(0)) for token in _tokens(value)]
    if not words:
        return ""
    if any(word in _COLOURS for word in words) and all(
        word in _COLOURS or word in _COLOUR_MODIFIERS for word in words
    ):
        return COLOURS
    if len(words) == 1:
        amount = _AMOUNT_RE.match(words[0])
        if amount:
            unit = amount.group(2).lower()
            if unit in _CAPACITY_UNITS:
                return CAPACITIES
            if unit in _POWER_UNITS:
                return POWER
            if _PACK_UNITS.match(unit):
                return OPTIONS
            return SIZES
    if all(
        word in _LETTER_SIZES
        or word in _SIZE_NAMES
        or _PAPER_SIZE_RE.match(word)
        or re.match(r"^\d+(?:[.,]\d+)?(?:\"|”|″)?$", word)
        or (_AMOUNT_RE.match(word) and not _PACK_UNITS.match(_AMOUNT_RE.match(word).group(2).lower())
            and _AMOUNT_RE.match(word).group(2).lower() not in _CAPACITY_UNITS
            and _AMOUNT_RE.match(word).group(2).lower() not in _POWER_UNITS)
        for word in words
    ):
        return SIZES
    return OPTIONS


def _shown(value: str) -> str:
    """A value as the card writes it: one space, and "GRAY" as "Gray" (a size stays "XL")."""
    text = " ".join(value.split())
    if text.isupper() and sum(char.isalpha() for char in text) > 3:
        return " ".join(
            word if word.lower() in _LETTER_SIZES or any(char.isdigit() for char in word) else word.capitalize()
            for word in text.split()
        )
    return text


def _number(value: str) -> float | None:
    found = re.search(r"\d+(?:[.,]\d+)?", value)
    return float(found.group(0).replace(",", ".")) if found else None


def _size_order(value: str, place: int) -> tuple[int, float, int]:
    words = [_key(token.group(0)) for token in _tokens(value)]
    if words and words[0] in _LETTER_ORDER:
        return (0, float(_LETTER_ORDER[words[0]]), place)
    number = _number(value)
    if number is not None:
        return (1, number, place)
    return (2, 0.0, place)


def _scaled_order(value: str, units: dict[str, float], place: int) -> tuple[float, int]:
    amount = _AMOUNT_RE.match(_key(value))
    if not amount:
        return (float("inf"), place)
    return (float(amount.group(1).replace(",", ".")) * units.get(amount.group(2).lower(), 1.0), place)


def _title_values(
    parts: list[str], keys: list[str], part_count: dict[str, int], common_tokens: set[str], titles: int
) -> dict[str, list[str]] | None:
    """One title's variants by kind, or None when they do not read as one variant."""
    values: dict[str, list[tuple[str, int]]] = {}
    for index, (part, key) in enumerate(zip(parts, keys)):
        if not key or part_count.get(key, 0) == titles:
            continue
        tokens = _tokens(part)
        if index > 0 and len(tokens) <= 3:
            # A part of its own after the name: "- Snake Print -", "- Grey Oak", "- S".
            kind = kind_of(part)
            if kind:
                values.setdefault(kind, []).append((part, part_count.get(key, 0)))
            continue
        # The name, or a long part: the runs of its words the other titles lack.
        runs: list[list[re.Match[str]]] = []
        run: list[re.Match[str]] = []
        before: re.Match[str] | None = None
        for token in tokens:
            if _key(token.group(0)) in common_tokens:
                if run:
                    runs.append(run)
                    run = []
            elif _AMOUNT_RE.match(_key(token.group(0))):
                # An amount is a value of its own: "650 W" of "650 W 24-pin".
                if run:
                    runs.append(run)
                runs.append([token])
                run = []
            else:
                if not run and before is not None and _key(before.group(0)) in _SIZE_LEAD:
                    run.append(before)  # "Size 9", "UK 10": the size with its word
                run.append(token)
            before = token
        if run:
            runs.append(run)
        for found in runs:
            value = part[found[0].start():found[-1].end()]
            kind = kind_of(value)
            # Only a colour, a size, a capacity or a power read inside a name: other words
            # there ("Funny", a model's number) name no variant.
            if kind in (COLOURS, CAPACITIES, POWER) or (
                kind == SIZES and not all(word.isdigit() for word in value.split())
            ):
                values.setdefault(kind, []).append((value, 1))
    # The same value twice in one title ("Black ... Coat - L-XL / Black", "33\" Waist -
    # ... / 33\" Waist") is one: the longest of those one holds the other.
    for kind, found in list(values.items()):
        kept: list[tuple[str, int]] = []
        for value, count in sorted(found, key=lambda item: -len(_key(item[0]))):
            if not any(_key(value) in _key(other) for other, _count in kept):
                kept.append((value, count))
        values[kind] = sorted(kept, key=lambda item: found.index(item))
    picked = values.get(COLOURS, []) + values.get(OPTIONS, [])
    if len(picked) > 1:
        # A description several titles share ("- Sleep Mask Only") is not the variant.
        values[OPTIONS] = [(value, count) for value, count in values.get(OPTIONS, []) if count == 1]
        picked = values.get(COLOURS, []) + values[OPTIONS]
    if len(picked) > 1 or any(len(found) > 1 for found in values.values()):
        # Two colours or two sizes in one title: not one variant a buyer picks.
        return None
    return {kind: [value for value, _count in found] for kind, found in values.items() if found}


def variant_values(titles: Sequence[str]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """The variants one shop's titles of one product name, by kind (`KINDS`), each kind
    with two values at least, `KINDS_SHOWN` kinds at most; the first title is the card's,
    and its colour or option is named first. Empty when the titles do not read as
    variants."""
    titles = [" ".join(str(title or "").split()) for title in list(titles)[:TITLES_READ]]
    titles = list(dict.fromkeys(title for title in titles if title))
    if len(titles) < 2:
        return ()
    parts_of = [_parts(title) for title in titles]
    part_keys = [[_part_key(part) for part in parts] for parts in parts_of]
    # How many titles hold each part, and the words every title holds.
    part_count: dict[str, int] = {}
    for keys in part_keys:
        for key in set(keys):
            part_count[key] = part_count.get(key, 0) + 1
    common_tokens = set.intersection(*({_key(token.group(0)) for token in _tokens(title)} for title in titles))
    read: list[dict[str, list[str]]] = []
    for parts, keys in zip(parts_of, part_keys):
        of_title = _title_values(parts, keys, part_count, common_tokens, len(titles))
        if of_title is None:
            return ()
        read.append(of_title)
    # Colours beside prints and finishes are one choice at the shop.
    merge = any(OPTIONS in of_title for of_title in read) and any(COLOURS in of_title for of_title in read)
    found: dict[str, list[str]] = {}
    for of_title in read:  # in the titles' order: the card's first
        for kind in KINDS:
            for value in of_title.get(kind, ()):
                found.setdefault(OPTIONS if merge and kind == COLOURS else kind, []).append(value)
    kinds: list[tuple[str, tuple[str, ...]]] = []
    for kind in KINDS:
        distinct: dict[str, str] = {}
        for value in found.get(kind) or ():
            distinct.setdefault(_key(value), _shown(value))
        if len(distinct) < 2:
            continue
        ordered = list(distinct.values())
        if kind == SIZES and all(re.match(r"(?i)^sizes?\s+\S", value) for value in ordered):
            # "Size 7, Size 8" under "Sizes at the shop" reads "7, 8".
            ordered = [re.sub(r"(?i)^sizes?\s+", "", value) for value in ordered]
        place = {value: index for index, value in enumerate(ordered)}
        if kind == SIZES:
            ordered.sort(key=lambda value: _size_order(value, place[value]))
        elif kind == CAPACITIES:
            ordered.sort(key=lambda value: _scaled_order(value, _CAPACITY_UNITS, place[value]))
        elif kind == POWER:
            ordered.sort(key=lambda value: _scaled_order(value, _POWER_UNITS, place[value]))
        kinds.append((kind, tuple(ordered)))
    return tuple(kinds[:KINDS_SHOWN])
