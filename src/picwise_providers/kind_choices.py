"""The choices a search for a general word offers: "What kind of cable?".

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
catalogue (`deployment/server/print_choices.py`, `measure_kind_choices`): 81 of the 116
kinds of 50 or more products were general.

What a search offers (`build_kind_choices`; owner, 2026-10-29: «Ναι προχώρα, βάλ' το στο
search»): a general kind's narrower kinds and the words its titles name it with, each a
search that narrows it as the understanding reads it, the largest first. Worked out
each night with the prepared feed (`state.prepare_feed_catalogue`), shown above the
results of a search naming only the kind (`picwise_surface.reference`) and offered in
the search box's suggestions.
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
    understand_product_query,
)
from picwise_nlu.product_concepts import broader_concepts, get_product_concepts_by_id

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


@dataclass
class _KindGroups:
    products: int
    nouns: Counter
    # "word noun" -> products, and the narrowest kinds of those products.
    words: Counter
    word_kinds: dict[str, Counter]
    narrower: Counter
    shelves: Counter


def _kind_groups(
    products: Sequence[ProviderProduct], kinds: Sequence[Collection[str]]
) -> tuple[dict[str, _KindGroups], tuple[tuple[str, int], ...]]:
    """Every kind of at least `MIN_PRODUCTS` products, grouped (module docstring), and
    the words left out as saying how a product is, with how many kinds each came before.
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
    groups: dict[str, _KindGroups] = {}
    for kind, rows in read.items():
        group = _KindGroups(len(rows), Counter(), Counter(), defaultdict(Counter), Counter(), Counter())
        for index in rows:
            named = before[kind][index]
            narrowest = _narrowest_kind(kinds[index])
            if named is not None:
                group.nouns[named[1]] += 1
                if named[0] and named[0] not in generic:
                    text = f"{named[0]} {named[1]}"
                    group.words[text] += 1
                    group.word_kinds[text][narrowest] += 1
            if narrowest and narrowest != kind:
                group.narrower[narrowest] += 1
            shelf = narrowest_shelf(products[index])
            if shelf:
                group.shelves[shelf] += 1
        groups[kind] = group
    generic_words = tuple(
        sorted(((word, word_kinds[word]) for word in generic), key=lambda item: (-item[1], item[0]))
    )
    return groups, generic_words


def measure_kind_choices(
    products: Sequence[ProviderProduct], kinds: Sequence[Collection[str]]
) -> ChoicesMeasure:
    """Every kind of at least `MIN_PRODUCTS` products, grouped (module docstring)."""
    groups, generic_words = _kind_groups(products, kinds)
    measured = [
        KindChoices(
            kind=kind,
            products=group.products,
            noun=group.nouns.most_common(1)[0][0] if group.nouns else "",
            named=sum(group.nouns.values()),
            words=_choices(group.words),
            narrower=_choices(group.narrower),
            shelves=_choices(group.shelves),
        )
        for kind, group in groups.items()
    ]
    measured.sort(key=lambda entry: (-entry.products, entry.kind))
    return ChoicesMeasure(kinds=tuple(measured), generic_words=generic_words)


@dataclass(frozen=True)
class KindChoice:
    """One choice a search for a general kind offers: the words of a search that narrows
    it, and how many of the kind's products had them when the choices were worked out."""

    text: str
    products: int


# How many choices a general kind offers, the largest first.
CHOICES_OFFERED = 6
# A choice by the words gives way to a narrower kind that holds this share of its
# products: "charger cable" and "usb cable" are charging cables, offered as such.
_COVERED_SHARE = 0.8


def _narrows(text: str, kind: str) -> bool:
    """Does a search for `text` answer a narrower part of `kind`: a narrower kind, or the
    kind with a word to filter by? On the server's catalogue of 2026-10-29 "pendant
    light" read as every lamp (one of the lamp's own names), and "funny shirt" as an
    oven; neither is offered for what it would not answer."""
    reading = understand_product_query(text)
    if not reading.understood or reading.concept_id is None:
        return False
    if reading.concept_id != kind:
        return kind in broader_concepts(reading.concept_id)
    return bool(reading.filters)


def build_kind_choices(
    products: Sequence[ProviderProduct], kinds: Sequence[Collection[str]]
) -> dict[str, tuple[KindChoice, ...]]:
    """The choices each general kind offers, for the products a search can show: its
    narrower kinds (named as the lexicon first names them) and the words its titles name
    it with, from `MIN_GROUP` products each, the largest first, at most
    `CHOICES_OFFERED`; only those the search reads as narrowing it (`_narrows`). A kind
    is general, and listed, with `MIN_CHOICES` of them."""
    groups, _generic_words = _kind_groups(products, kinds)
    by_id = get_product_concepts_by_id()
    offered: dict[str, tuple[KindChoice, ...]] = {}
    for kind, group in groups.items():
        narrower = {name: count for name, count in group.narrower.items() if count >= MIN_GROUP}
        candidates: dict[str, int] = {}
        for narrower_kind, count in narrower.items():
            concept = by_id.get(narrower_kind)
            name = concept.primary_english if concept is not None else ""
            if name:
                candidates[name] = max(candidates.get(name, 0), count)
        for text, count in group.words.items():
            if count < MIN_GROUP:
                continue
            inside = group.word_kinds[text]
            if any(name in narrower and held >= _COVERED_SHARE * count for name, held in inside.items()):
                continue
            candidates[text] = max(candidates.get(text, 0), count)
        kept: list[KindChoice] = []
        for text, count in sorted(candidates.items(), key=lambda item: (-item[1], item[0])):
            if len(kept) >= CHOICES_OFFERED:
                break
            if _narrows(text, kind):
                kept.append(KindChoice(text=text, products=count))
        if len(kept) >= MIN_CHOICES:
            offered[kind] = tuple(kept)
    return offered
