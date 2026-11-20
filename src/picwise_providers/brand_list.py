"""The catalogue's brands, made each night from the feeds (the Decision Contract, "The
catalogue's brands").

The owner's series of work, agreed on 2026-11-19 at night, step 3: a list of brands from
the feeds, with the kinds each sells; taken up on 2026-11-20 («PicWise: συνέχισε το βήμα
3, τη λίστα brands, όπως γράφει το handoff»). Measured first on a copy of the server's
catalogue (`deployment/server/print_brands.py`, run `44626133872`): "samsung" and "dyson"
alone showed no product, "samsnug" nothing, "razer" was read as an electric shaver. The
owner's answers of 2026-11-20: a brand alone asks "What kind of Samsung product?" above
its products, with no Recommended until a kind is chosen («Ερώτηση + προϊόντα»); a
misspelled brand is read as the brand when only it is that close, the page saying so,
else the page asks («Διόρθωση όταν είναι σίγουρο»).

Here:
- one name for the ways a brand is written (`brand_key`), with its letters mended where a
  shop's file broke them (`mend_letters`); the feeds' placeholders are no brand;
- the list (`build_brand_list`), worked out with the prepared feed each night
  (`state.prepare_feed_catalogue`) from the products a search reads: every brand of
  `COUNTED` products or more, named as most of its products write it, with its kinds
  counted, each product under its narrowest kind, accessories and doubtful kinds aside;
- what a search asks of it (`BrandReader.read`): the brand a search names alone, with the
  brands whose names begin with it; or a word of the search read as a brand's name it is
  one slip from; or the searches to ask about when it could be several. The words of the
  brands' names are given to the reading of a search, which never corrects them
  (`concept_understanding.set_brand_names`).

The products are found by `search_selection.select_provider_products_for_brand`.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Collection

from picwise_nlu.concept_understanding import (
    ACCESSORY_MARKER,
    UNCERTAIN_MARKER,
    is_judgement_word,
    is_known_english_word,
    known_english_words,
    normalize_understanding_text,
    understand_product_query,
)
from picwise_nlu.product_concepts import broader_concepts, get_product_concepts_by_id

from .catalogue_balance import _narrowest_kind
from .contracts import ProviderProduct

# A brand counts from this many products, as the search counted brands before
# (`search_selection._catalogue_brand_names`).
COUNTED = 3
# A kind is the brand's from this many of its products.
CHOICE = 3
# A question names at most this many kinds, as a general kind's does (`kind_choices`).
ASKED = 8
# A slip is read as a brand's name of this many letters or more...
SLIP_NAME = 5
# ...from a word typed of this many letters or more ("bosh" is a slip of "bosch").
SLIP_WORD = 4
# What the feeds write where a product has no brand.
PLACEHOLDERS = (
    "generic", "unbranded", "un-branded", "unbrand", "no brand", "nobrand", "non branded", "non-branded",
    "none", "n/a", "na", "unknown", "other", "others", "oem", "does not apply", "not applicable",
    "not specified", "unspecified", "brand", "no", "null", "various", "assorted", "misc", "miscellaneous",
    "default", "own brand", "own label", "private label", "white label", "no name", "noname", "blank",
)
# Endings of a company's name, set aside when two spellings are compared ("Samsung UK",
# "Acme Ltd"), never the only word of a name.
ENDINGS = frozenset("ltd limited plc inc llc gmbh co corp uk".split())
# A brand's answer is no Recommended among several kinds (`search_selection`).
SEVERAL_KINDS = "several_kinds"

_NOT_A_LETTER = re.compile(r"[^0-9a-z]+")
# The letters a broken name shows: UTF-8 read as Windows' or Latin letters.
_BROKEN = ("Ã", "Â", "â", "Ä", "Å", "Æ", "Ð", "Ñ", "Ø")


# --------------------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------------------


def mend_letters(text: object) -> str:
    """A name whose letters a shop's file broke, mended ("PokÃ©mon" is "Pokémon",
    "Starlight Bedsâ„¢" is "Starlight Beds™"): its bytes read again as UTF-8. Any other
    name, or one that does not read so, as it is."""
    text = str(text or "")
    if text.isascii() or not any(mark in text for mark in _BROKEN):
        return text
    for encoding in ("cp1252", "latin-1"):
        try:
            mended = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if mended != text:
            return mended
    return text


def plain(text: object) -> str:
    """Lowercase, without accents or punctuation, "&", "+" and "and" left out."""
    lowered = str(text or "").lower().replace("'", "").replace("’", "")
    decomposed = unicodedata.normalize("NFKD", lowered)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(word for word in _NOT_A_LETTER.sub(" ", stripped).split() if word != "and")


def spoken(text: object) -> str:
    """A name as a buyer would type it: `plain`, its words kept apart, a leading "The" and
    an ending of a company's name set aside."""
    words = plain(text).split()
    while len(words) > 1 and words[-1] in ENDINGS:
        words.pop()
    if len(words) > 1 and words[0] == "the":
        words.pop(0)
    return " ".join(words)


def brand_key(text: object) -> str:
    """One name for the ways a brand is written: `spoken`, the words joined. "SAMSUNG",
    "Samsung UK" and "Samsung" are "samsung"; "Black & Decker", "Black+Decker" and "Black
    and Decker" "blackdecker". A name of letters no ASCII holds keeps them, lowercased."""
    words = spoken(text).split()
    if words:
        return "".join(words)
    # Letters no ASCII holds are kept; punctuation alone ("-") is no name.
    text = str(text or "")
    return "".join(text.lower().split()) if any(char.isalnum() for char in text) else ""


_PLACEHOLDER_KEYS = frozenset(brand_key(name) for name in PLACEHOLDERS)


def is_placeholder(key: str) -> bool:
    return not key or key in _PLACEHOLDER_KEYS


def slips(a: str, b: str) -> int:
    """How many slips turn `a` into `b`: a letter more, less or other, or two side by side
    swapped (optimal string alignment); 3 stands for three or more."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 2:
        return 3
    previous2: list[int] = []
    previous = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        current = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                current[j] = min(current[j], previous2[j - 2] + 1)
        if min(current) > 2:
            return 3
        previous2, previous = previous, current
    return min(previous[len(b)], 3)


def _deletions(word: str, depth: int) -> set[str]:
    found = {word}
    edge = {word}
    for _step in range(depth):
        edge = {variant[:i] + variant[i + 1 :] for variant in edge for i in range(len(variant))}
        found |= edge
    return found


class NearIndex:
    """Words by the strings a few deleted letters leave of them, so the words a few slips
    from a name are found without comparing it with every word (symmetric deletion)."""

    def __init__(self, words: Iterable[str], depth: int) -> None:
        self.depth = depth
        self.by_variant: dict[str, list[str]] = defaultdict(list)
        for word in set(words):
            for variant in _deletions(word, depth):
                self.by_variant[variant].append(word)

    def near(self, word: str, most: int) -> dict[str, int]:
        found: dict[str, int] = {}
        for variant in _deletions(word, min(most, self.depth)):
            for other in self.by_variant.get(variant, ()):
                if other != word and other not in found:
                    distance = slips(word, other)
                    if distance <= most:
                        found[other] = distance
        return found


@lru_cache(maxsize=1)
def _known_words() -> NearIndex:
    """The words the search reads as spelt right, by what one deleted letter leaves of
    them: a word typed one slip from one of them may be a slip of it."""
    return NearIndex(known_english_words(), 1)


# --------------------------------------------------------------------------------------
# The list
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CatalogueBrand:
    """One brand of the catalogue, however its products write it."""

    key: str
    # As most of its products write it, its letters mended.
    name: str
    products: int
    # Its products' kinds, each product under its narrowest kind, the most first:
    # accessories and products of a doubtful kind or of none are not counted.
    kinds: tuple[tuple[str, int], ...] = ()


def build_brand_list(
    products: Sequence[ProviderProduct], kinds: Sequence[Collection[str]]
) -> tuple[CatalogueBrand, ...]:
    """Every brand of `COUNTED` products or more of these, the largest first (module
    docstring). `kinds` holds each product's kinds as the search reads them, in order."""
    read: dict[str, tuple[str, str]] = {}
    forms: dict[str, Counter] = defaultdict(Counter)
    counts: Counter = Counter()
    kind_counts: dict[str, Counter] = defaultdict(Counter)
    narrowest: dict[frozenset, str] = {}
    for product, product_kinds in zip(products, kinds):
        written = " ".join(str(product.brand or "").split())
        if not written:
            continue
        entry = read.get(written)
        if entry is None:
            mended = mend_letters(written)
            entry = read[written] = (brand_key(mended), mended)
        key, mended = entry
        if is_placeholder(key):
            continue
        forms[key][mended] += 1
        counts[key] += 1
        product_kinds = frozenset(product_kinds)
        if product_kinds & {ACCESSORY_MARKER, UNCERTAIN_MARKER}:
            continue
        kind = narrowest.get(product_kinds)
        if kind is None:
            kind = narrowest[product_kinds] = _narrowest_kind(product_kinds)
        if kind:
            kind_counts[key][kind] += 1
    brands = [
        CatalogueBrand(
            key=key,
            name=min(forms[key].items(), key=lambda item: (-item[1], item[0]))[0],
            products=count,
            kinds=tuple(sorted(kind_counts[key].items(), key=lambda item: (-item[1], item[0]))),
        )
        for key, count in counts.items()
        if count >= COUNTED
    ]
    brands.sort(key=lambda brand: (-brand.products, brand.key))
    return tuple(brands)


# --------------------------------------------------------------------------------------
# What a search asks of it
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BrandAnswer:
    """The brands a search names alone, read as one: "bosch" is Bosch and Bosch
    Professional."""

    # As the page names them: "Samsung", "Bosch".
    name: str
    keys: tuple[str, ...]
    products: int
    # Their kinds together, the most first (`CatalogueBrand.kinds`).
    kinds: tuple[tuple[str, int], ...]

    @property
    def search_name(self) -> str:
        """The name as a search for it is typed: "samsung"."""
        return " ".join(self.name.lower().split())

    @property
    def own_kinds(self) -> tuple[tuple[str, int], ...]:
        """The kinds that are the brand's: of `CHOICE` of its products or more."""
        return tuple(item for item in self.kinds if item[1] >= CHOICE)

    def choices(self) -> tuple[str, ...]:
        """The searches a question for it offers, the largest kind first, `ASKED` at most:
        the brand with the kind's name, each read back as that kind or a narrower one
        ("samsung tv", "samsung monitor"); none for a brand of fewer than two kinds."""
        if len(self.own_kinds) < 2:
            return ()
        by_id = get_product_concepts_by_id()
        texts: list[str] = []
        for kind, _count in self.own_kinds:
            concept = by_id.get(kind)
            if concept is None or not concept.primary_english:
                continue
            text = f"{self.search_name} {concept.primary_english}"
            reading = understand_product_query(text)
            if not reading.understood or not reading.concept_id:
                continue
            if reading.concept_id != kind and kind not in broader_concepts(reading.concept_id):
                continue
            if text not in texts:
                texts.append(text)
            if len(texts) >= ASKED:
                break
        return tuple(texts)


@dataclass(frozen=True)
class BrandSearch:
    """What the brands make of one search: a brand alone; or the search with a word read
    as a brand's name, and that brand's name; or searches to ask about; or nothing."""

    alone: BrandAnswer | None = None
    corrected: str = ""
    corrected_to: str = ""
    suggestions: tuple[str, ...] = ()


def _leading_words(name: str, count: int) -> str:
    """The first `count` words of a name as it is written, punctuation between them kept,
    a leading "The" left out: the first two of "Black & Decker Pro" are "Black & Decker",
    the first of "The North Face" "North"."""
    written = name.split()
    if len(written) > 1 and plain(written[0]) == "the":
        written = written[1:]
    kept: list[str] = []
    found = 0
    for word in written:
        if found >= count:
            break
        kept.append(word)
        found += len(plain(word).split())
    return " ".join(kept).strip(" &+-,.") or name


def _says_how(word: str) -> bool:
    """Does the word say how a product is, or how much of it ("white", "small", "pack")?
    Such a search names no brand alone (the Decision Contract, "The catalogue's brands",
    point 3)."""
    from .search_selection import _DESCRIBING_WORDS, _MEASURE_WORDS

    return word in _DESCRIBING_WORDS or word in _MEASURE_WORDS


class BrandReader:
    """The list as a search reads it (module docstring)."""

    def __init__(self, brands: Iterable[CatalogueBrand]) -> None:
        self.brands = {brand.key: brand for brand in brands}
        self._spoken = {key: spoken(brand.name) for key, brand in self.brands.items()}
        by_first: dict[str, list[str]] = defaultdict(list)
        for key, name in self._spoken.items():
            if name:
                by_first[name.split()[0]].append(key)
        self._by_first = dict(by_first)
        self.single_words = frozenset(name for name in self._spoken.values() if name and " " not in name)
        self.several_words = tuple(
            tuple(name.split()) for name in self._spoken.values() if name and " " in name
        )
        self._words_of_several = frozenset(word for name in self.several_words for word in name)
        self._near: NearIndex | None = None

    def __len__(self) -> int:
        return len(self.brands)

    def _near_names(self) -> NearIndex:
        if self._near is None:
            self._near = NearIndex((key for key in self.brands if len(key) >= SLIP_NAME), 1)
        return self._near

    def read(self, query: str) -> BrandSearch:
        """What the brands make of a search (the Decision Contract, "The catalogue's
        brands", points 3 and 4)."""
        if not self.brands:
            return BrandSearch()
        words = [word for word in normalize_understanding_text(query).split() if not is_judgement_word(word)]
        if not words:
            return BrandSearch()
        alone = self.alone(words, query)
        if alone is not None:
            return BrandSearch(alone=alone)
        return self._slips(words, query)

    def alone(self, words: list[str], query: str) -> BrandAnswer | None:
        """The brands a search's words name alone: a brand's whole name, with the brands
        whose names begin with it; or, a name of no brand made of no word the search knows,
        the brands whose names begin with it ("karcher" for Karcher Pro). None when the
        search names a kind and nothing else, or is one word that says how a product is
        ("white", "strong"), or its words begin names only and one of them says how a
        product is."""
        text = spoken(" ".join(words))
        if not text:
            return None
        exact = self.brands.get(brand_key(text))
        family = [
            key
            for key in self._by_first.get(text.split()[0], ())
            if self._spoken[key].startswith(text + " ")
        ]
        if exact is not None and len(words) == 1 and _says_how(words[0]):
            return None
        if exact is None and (
            not family
            or len(brand_key(text)) < SLIP_WORD
            or any(is_known_english_word(word) or _says_how(word) for word in text.split())
        ):
            return None
        reading = understand_product_query(query)
        if reading.understood and not reading.filters and not reading.specs:
            # "rugs", "lego": the kind's own name.
            return None
        members = ([exact] if exact is not None else []) + [
            self.brands[key] for key in family if exact is None or key != exact.key
        ]
        kinds: Counter = Counter()
        for brand in members:
            kinds.update(dict(brand.kinds))
        if exact is not None:
            name = exact.name
        else:
            largest = max(members, key=lambda brand: (brand.products, brand.key))
            name = _leading_words(largest.name, len(text.split()))
        return BrandAnswer(
            name=name,
            keys=tuple(brand.key for brand in members),
            products=sum(brand.products for brand in members),
            kinds=tuple(sorted(kinds.items(), key=lambda item: (-item[1], item[0]))),
        )

    def _close(self, word: str) -> list[CatalogueBrand]:
        """The brands of one word whose name is one slip from `word`, the largest first."""
        found = [
            self.brands[key]
            for key in self._near_names().near(word, 1)
            if " " not in self._spoken[key]
        ]
        return sorted(found, key=lambda brand: (-brand.products, brand.key))

    def _slips(self, words: list[str], query: str) -> BrandSearch:
        """A word of the search, or its whole text, read as a brand's name it is one slip
        from, when only that name and no word the search knows is that close; else the
        searches to ask about (the Decision Contract, "The catalogue's brands", point 4)."""
        reading = understand_product_query(query)
        # A brand's whole name of several words, one slip off: "bosch profesional".
        whole = brand_key(" ".join(words))
        if len(words) > 1 and len(whole) >= 2 * SLIP_NAME and not reading.understood:
            near = [
                self.brands[key]
                for key in self._near_names().near(whole, 1)
                if " " in self._spoken[key]
            ]
            if len(near) == 1:
                brand = near[0]
                return BrandSearch(corrected=" ".join(brand.name.lower().split()), corrected_to=brand.name)
        corrected = list(words)
        corrected_to = ""
        suggestions: list[str] = []
        for place, word in enumerate(words):
            if (
                len(word) < SLIP_WORD
                or not word.isalpha()
                or word in self.single_words
                or word in self._words_of_several
                or is_known_english_word(word)
            ):
                continue
            close = self._close(word)
            if not close:
                continue
            # Another brand, a word the search knows, or a kind the reading would correct
            # it into ("torres" read as tyres) as close: a question, never a guess.
            ambiguous = (
                len(close) > 1
                or bool(_known_words().near(word, 1))
                or understand_product_query(word).understood
            )
            if not ambiguous and not corrected_to:
                corrected[place] = " ".join(close[0].name.lower().split())
                corrected_to = close[0].name
                continue
            for brand in close[:3]:
                asked = list(words)
                asked[place] = " ".join(brand.name.lower().split())
                suggestions.append(" ".join(asked))
        if corrected_to:
            return BrandSearch(corrected=" ".join(corrected), corrected_to=corrected_to)
        return BrandSearch(suggestions=tuple(dict.fromkeys(suggestions))[:3])

    def reading_names(self) -> tuple[frozenset[str], tuple[tuple[str, ...], ...]]:
        """The names a search's reading never corrects (`concept_understanding.set_brand_names`):
        those of one word, and those of several as their words."""
        return self.single_words, self.several_words
