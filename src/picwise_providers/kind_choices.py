"""The choices a search for a general word could offer: measured, nothing shown changes.

Owner, 2026-10-28: «Το search όταν του βάζεις καλώδιο πρέπει να συμπληρώνει προτάσεις τι
καλώδιο ζητάει: καλώδιο τηλεόρασης, καλώδιο φόρτισης, καλώδιο ίντερνετ ... το ίδιο με όλες
αυτές τις γενικές λέξεις»; 2026-10-29: «η ίδια λογική ένας προγραμματισμός για όλες αυτές
τις αναζητήσεις ... δεν θέλω να διορθώνουμε ένα-ένα λέξη κλειδί». So no word is named
here: every kind with products is read the same way, from the catalogue itself, and its
products are grouped three ways:

- by the word their titles put right before the noun that names the kind: "HDMI Cable"
  and "Aerial Coaxial Cable" give "hdmi" and "coaxial", "Diamond Engagement Ring" gives
  "engagement" (the noun is the last word of the kind's name in the title, in English);
- by the narrower kind they are: a charging cable is a cable;
- by the shop's narrowest shelf: "Audio & Video Cables".

A word that comes before the nouns of many kinds says how a product is, not which kind
of it: "black", "gold", "wireless", "usb" ("usb cable", "usb fan", "usb hub"). Which
words do is read from the catalogue too, each night: a word before the nouns of at least
`GENERIC_KINDS` kinds is no choice for any of them. Numbers, specs and the product's own
brand never are.

A kind is general when at least `MIN_CHOICES` of its groups of one way each hold at least
`MIN_SHARE` of its products and `MIN_GROUP` products. Measured first on a copy of the
server's catalogue (`deployment/server/print_choices.py`): which kinds are general, and
what each would offer, before anything is built into the search.
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
# A group is a choice when it holds this share of its kind's products, and this many.
MIN_SHARE = 0.05
MIN_GROUP = 10
# A kind is general with this many such groups of one way.
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
    # (the word before the noun, products), the most first; generic words left out.
    words: tuple[tuple[str, int], ...]
    # (narrower kind, products) and (narrowest shelf, products), the most first.
    narrower: tuple[tuple[str, int], ...]
    shelves: tuple[tuple[str, int], ...]
    general_by_words: bool
    general_by_shelves: bool

    @property
    def general(self) -> bool:
        return self.general_by_words or self.general_by_shelves


@dataclass(frozen=True)
class ChoicesMeasure:
    kinds: tuple[KindChoices, ...]
    # The words left out as saying how a product is: (word, kinds it comes before).
    generic_words: tuple[tuple[str, int], ...]


def _names_in(title: str) -> tuple[tuple[str, ...], list]:
    """A title's words and the kinds' names in it, weak ones too ("Wedding Ring"): the
    product's kind is already known, so a weak name only says where its noun stands."""
    tokens = tuple(normalize_understanding_text(title).split())
    return tokens, _choose_spans(_find_spans(tokens, [_exact_candidates(token) for token in tokens]))


def _word_before_noun(
    tokens: tuple[str, ...], spans: list, kind: str, brand_words: Collection[str]
) -> tuple[str, str] | None:
    """The word a title puts right before the noun of this kind's name (or of a narrower
    kind's), and that noun in the singular: ("hdmi", "cable") for "Fixturon HDMI Cable
    2m". ("", noun) when nothing that could be a choice stands there; None when the title
    does not name the kind in English."""
    for span in spans:
        if span.kind != "en" or kind not in broader_concepts(span.concept_id):
            continue
        noun = _singular(tokens[span.end - 1])
        word = tokens[span.end - 2] if span.end >= 2 else ""
        if (
            len(word) < 2
            or not word.isalpha()
            or word in _CONNECTIVE_TOKENS
            or word in _PURPOSE_TOKENS
            or word in brand_words
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


def _choices(counts: Counter, total: int) -> tuple[tuple[tuple[str, int], ...], bool]:
    ordered = tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:_KEPT])
    large = [count for _name, count in ordered if count >= max(MIN_GROUP, MIN_SHARE * total)]
    return ordered, len(large) >= MIN_CHOICES


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
        tokens, spans = _names_in(str(product.title or ""))
        brand_words = set(normalize_understanding_text(str(product.brand or "")).split())
        for kind in product_kinds:
            before[kind][index] = _word_before_noun(tokens, spans, kind, brand_words)
    word_kinds: Counter = Counter()
    for kind in read:
        words = Counter(named[0] for named in before[kind].values() if named and named[0])
        for word, count in words.items():
            if count >= _MIN_WORD_PRODUCTS:
                word_kinds[word] += 1
    generic = {word for word, count in word_kinds.items() if count >= GENERIC_KINDS}
    measured = []
    for kind, rows in read.items():
        total = len(rows)
        nouns: Counter = Counter()
        words: Counter = Counter()
        narrower: Counter = Counter()
        shelves: Counter = Counter()
        for index in rows:
            named = before[kind][index]
            if named is not None:
                nouns[named[1]] += 1
                if named[0] and named[0] not in generic:
                    words[named[0]] += 1
            narrowest = _narrowest_kind(kinds[index])
            if narrowest and narrowest != kind:
                narrower[narrowest] += 1
            shelf = narrowest_shelf(products[index])
            if shelf:
                shelves[shelf] += 1
        word_choices, by_words = _choices(words, total)
        shelf_choices, by_shelves = _choices(shelves, total)
        measured.append(
            KindChoices(
                kind=kind,
                products=total,
                noun=nouns.most_common(1)[0][0] if nouns else "",
                named=sum(nouns.values()),
                words=word_choices,
                narrower=tuple(sorted(narrower.items(), key=lambda item: (-item[1], item[0]))[:_KEPT]),
                shelves=shelf_choices,
                general_by_words=by_words,
                general_by_shelves=by_shelves,
            )
        )
    measured.sort(key=lambda entry: (-entry.products, entry.kind))
    return ChoicesMeasure(
        kinds=tuple(measured),
        generic_words=tuple(sorted(((word, word_kinds[word]) for word in generic), key=lambda item: (-item[1], item[0]))),
    )
