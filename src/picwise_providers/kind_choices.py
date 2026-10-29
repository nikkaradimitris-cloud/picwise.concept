"""The choices a search for a general word could offer: measured, nothing shown changes.

Owner, 2026-10-28: «Το search όταν του βάζεις καλώδιο πρέπει να συμπληρώνει προτάσεις τι
καλώδιο ζητάει: καλώδιο τηλεόρασης, καλώδιο φόρτισης, καλώδιο ίντερνετ ... το ίδιο με όλες
αυτές τις γενικές λέξεις»; 2026-10-29: «η ίδια λογική ένας προγραμματισμός για όλες αυτές
τις αναζητήσεις ... δεν θέλω να διορθώνουμε ένα-ένα λέξη κλειδί». So no word is named
here: every kind with products is read the same way, from the catalogue itself, and its
products are grouped three ways:

- by the words their titles name it with: the word right before the noun of the kind's
  name and that noun, as written ("HDMI Cable" gives "hdmi cable", "Sofa Bed" under sofas
  "sofa bed", "Diamond Engagement Ring" "engagement ring"), a hyphenated word kept whole
  ("Zip-Up Hoodie" gives "zip-up hoodie"); in English;
- by the narrower kind they are: a charging cable is a cable;
- by the shop's narrowest shelf: "Audio & Video Cables".

A word that comes before the nouns of many kinds says how a product is, not which kind
of it: "gaming", "knitted". Which words do is read from the catalogue too, each night: a
word before the nouns of at least `GENERIC_KINDS` kinds is no choice for any of them.
Numbers, specs and the product's own brand never are.

A group is a choice from `MIN_GROUP` products, however large the kind: on the server's
catalogue of 2026-10-29 one shop's fabric extension leads were 81% of all cables, and a
share would have left "cable" without its HDMI, coaxial and charging cables. A kind is
general with `MIN_CHOICES` choices of one way. Measured first on a copy of the server's
catalogue (`deployment/server/print_choices.py`): which kinds are general, and what each
would offer, before anything is built into the search.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Collection, Sequence

from picwise_nlu.concept_understanding import (
    ACCESSORY_MARKER,
    CATEGORY_FIELD_SEPARATOR,
    UNCERTAIN_MARKER,
    _choose_spans,
    _exact_candidates,
    _find_spans,
    _singular,
    normalize_understanding_text,
)
from picwise_nlu.product_concepts import broader_concepts

from .catalogue_balance import _narrowest_kind
from .contracts import ProviderProduct
from .search_selection import _CONNECTIVE_TOKENS, _KIND_MARKERS, _PURPOSE_TOKENS, _context_allows_member

# A kind is read for choices from this many products.
MIN_PRODUCTS = 50
# A group is a choice from this many products.
MIN_GROUP = 20
# A kind is general with this many choices of one way.
MIN_CHOICES = 2
# A word before the nouns of this many kinds says how a product is, not which kind.
GENERIC_KINDS = 8
# A word counts before a kind's noun from this many of its products.
_MIN_WORD_PRODUCTS = 3
# How many choices of each way a kind keeps, the largest first.
_KEPT = 12


@dataclass(frozen=True)
class KindChoices:
    """One kind's products, grouped the three ways (module docstring)."""

    kind: str
    products: int
    # The noun the titles name the kind by, most often, in the singular ("cable").
    noun: str
    # How many of its products' titles name it in English.
    named: int
    # The choices of each way, (name, products), the most first: the words the titles name
    # it with ("hdmi cable"), generic words left out; its narrower kinds; its shelves.
    words: tuple[tuple[str, int], ...]
    narrower: tuple[tuple[str, int], ...]
    shelves: tuple[tuple[str, int], ...]

    @property
    def general_by_words(self) -> bool:
        return len(self.words) >= MIN_CHOICES

    @property
    def general_by_shelves(self) -> bool:
        return len(self.shelves) >= MIN_CHOICES

    @property
    def general(self) -> bool:
        return self.general_by_words or self.general_by_shelves


@dataclass(frozen=True)
class ChoicesMeasure:
    kinds: tuple[KindChoices, ...]
    # The words left out as saying how a product is: (word, kinds it comes before).
    generic_words: tuple[tuple[str, int], ...]


def _names_in(title: str) -> tuple[tuple[str, ...], list, list[int] | None, list[str]]:
    """A title's words, the kinds' names in it, weak ones too ("Wedding Ring": the
    product's kind is already known, so a weak name only says where its noun stands), and
    for each word the whole word it is written in, hyphens kept ("zip-up" for "zip" and
    "up" of "Zip-Up Hoodie"); None for those when the two readings do not line up."""
    tokens = tuple(normalize_understanding_text(title).split())
    spans = _choose_spans(_find_spans(tokens, [_exact_candidates(token) for token in tokens]))
    owners: list[int] = []
    wholes: list[str] = []
    parts_read: list[str] = []
    for written in str(title or "").split():
        parts = normalize_understanding_text(written).split()
        if parts:
            owners.extend([len(wholes)] * len(parts))
            wholes.append("-".join(parts))
            parts_read.extend(parts)
    return tokens, spans, (owners if tuple(parts_read) == tokens else None), wholes


def _word_before_noun(
    tokens: tuple[str, ...],
    spans: list,
    owners: list[int] | None,
    wholes: list[str],
    kind: str,
    brand_words: Collection[str],
) -> tuple[str, str] | None:
    """The word a title puts right before the noun of this kind's name (or of a narrower
    kind's), and that noun in the singular: ("hdmi", "cable") for "Fixturon HDMI Cable
    2m", ("zip-up", "hoodie") for "Zip-Up Hoodie". ("", noun) when nothing that could be a
    choice stands there; None when the title does not name the kind in English."""
    for span in spans:
        if span.kind != "en" or kind not in broader_concepts(span.concept_id):
            continue
        at = span.end - 1
        noun = _singular(tokens[at])
        if owners is not None:
            # The whole written word before the one the noun stands in ("t-shirt").
            word = wholes[owners[at] - 1] if owners[at] > 0 else ""
        else:
            word = tokens[at - 1] if at > 0 else ""
        if (
            len(word) < 2
            or not word.replace("-", "").isalpha()
            or word in _CONNECTIVE_TOKENS
            or word in _PURPOSE_TOKENS
            or any(part in brand_words for part in word.split("-"))
            or _singular(word) == noun
        ):
            word = ""
        return word, noun
    return None


def narrowest_shelf(product: ProviderProduct) -> str:
    """The last level of the product's first category path, as the shop wrote it."""
    first = str(product.category_text or "").split(CATEGORY_FIELD_SEPARATOR.strip())[0]
    levels = [level.strip() for level in first.split(">") if level.strip()]
    return levels[-1] if levels else ""


def _choices(counts: Counter) -> tuple[tuple[str, int], ...]:
    return tuple(
        (name, count)
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= MIN_GROUP
    )[:_KEPT]


def measure_kind_choices(
    products: Sequence[ProviderProduct], kinds: Sequence[Collection[str]]
) -> ChoicesMeasure:
    """Every kind of at least `MIN_PRODUCTS` products, grouped (module docstring).
    `kinds` holds each product's kinds, as the search reads them; a kind counts the
    products a search for it would list (`_context_allows_member`: a dog bed is no bed)."""
    members: dict[str, list[int]] = defaultdict(list)
    for index, product_kinds in enumerate(kinds):
        if set(product_kinds) & {ACCESSORY_MARKER, UNCERTAIN_MARKER}:
            continue
        concepts = frozenset(product_kinds)
        for kind in concepts - _KIND_MARKERS:
            if _context_allows_member(concepts, kind, tuple(kind.split("_"))):
                members[kind].append(index)
    read = {kind: rows for kind, rows in members.items() if len(rows) >= MIN_PRODUCTS}
    kinds_read_of: dict[int, list[str]] = defaultdict(list)
    for kind, rows in read.items():
        for index in rows:
            kinds_read_of[index].append(kind)
    # Each title is read once, for every kind of it that is read.
    before: dict[str, dict[int, tuple[str, str] | None]] = defaultdict(dict)
    for index, product_kinds in kinds_read_of.items():
        product = products[index]
        tokens, spans, owners, wholes = _names_in(str(product.title or ""))
        brand_words = set(normalize_understanding_text(str(product.brand or "")).split())
        for kind in product_kinds:
            before[kind][index] = _word_before_noun(tokens, spans, owners, wholes, kind, brand_words)
    word_kinds: Counter = Counter()
    for kind in read:
        words = Counter(named[0] for named in before[kind].values() if named and named[0])
        for word, count in words.items():
            if count >= _MIN_WORD_PRODUCTS:
                word_kinds[word] += 1
    generic = {word for word, count in word_kinds.items() if count >= GENERIC_KINDS}
    measured = []
    for kind, rows in read.items():
        nouns: Counter = Counter()
        words: Counter = Counter()
        narrower: Counter = Counter()
        shelves: Counter = Counter()
        for index in rows:
            named = before[kind][index]
            if named is not None:
                nouns[named[1]] += 1
                if named[0] and named[0] not in generic:
                    words[f"{named[0]} {named[1]}"] += 1
            narrowest = _narrowest_kind(kinds[index])
            if narrowest and narrowest != kind:
                narrower[narrowest] += 1
            shelf = narrowest_shelf(products[index])
            if shelf:
                shelves[shelf] += 1
        measured.append(
            KindChoices(
                kind=kind,
                products=len(rows),
                noun=nouns.most_common(1)[0][0] if nouns else "",
                named=sum(nouns.values()),
                words=_choices(words),
                narrower=_choices(narrower),
                shelves=_choices(shelves),
            )
        )
    measured.sort(key=lambda entry: (-entry.products, entry.kind))
    return ChoicesMeasure(
        kinds=tuple(measured),
        generic_words=tuple(sorted(((word, word_kinds[word]) for word in generic), key=lambda item: (-item[1], item[0]))),
    )
