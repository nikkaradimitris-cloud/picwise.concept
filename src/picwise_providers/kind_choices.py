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

The rules that keep what it offers true (owner, 2026-10-29: «εσύ πρέπει να αποφασίσεις
ποιος είναι ο βέλτιστος τρόπος»; found on the server's catalogue the same day, run
`40911685093`), each for every kind alike and each measured on its own
(`deployment/server/print_choice_rules.py`):
- `RULE_SHOPS`: a choice by the words is named so by `MIN_SHOPS` shops or more, or its
  word is one other shops use too, before some noun of the catalogue. One shop's own
  words are no kind of the product: "robertson hoodie", "eng ring", "remount ring".
  Measured on 2026-10-30 (run `41028398470`): asking two shops for the phrase itself
  also lost one shop's "lan cable", "thermal socks", "qhd monitor";
- `RULE_PHRASES`: a word that is half of a phrase is read whole. When most of its titles
  put before it a number ("3 Piece Suit", "2 Seater Sofa") or a word the two make one
  modifier with, as they do before the nouns of other kinds too ("Slim Fit Suit", "Slim
  Fit Jeans"; "Long Sleeve Shirt", "Long Sleeve Dress"), each whole phrase of
  `MIN_GROUP` products is the choice and the half is none: "3 piece suit", "long sleeve
  shirt", not "piece suit", "sleeve shirt". A word that names the kind on its own too
  says how it is, and is no part of the phrase: "Diamond Bracelet" makes "Diamond
  Tennis Bracelet" a tennis bracelet (run `41028398470` offered "diamond tennis
  bracelet" for 6,474 tennis bracelets; run `41031539622`, reading as half of a phrase
  any word mostly after the same few words, offered one shop's lines: "britain unisex
  hoodie", "waist mini dress");
- `RULE_WHOLE_KIND`: no choice whose search keeps `KEEPS_SHARE` of the kind or more:
  "diamond ring" kept 134,488 of 141,635 rings and narrowed nothing;
- `RULE_WRITTEN`: the noun as the titles write it most, not cut to a singular the search
  does not read: "bootcut jeans", "caravan mattresses", not "bootcut jean", "caravan
  mattresse";
- `RULE_SAME_SEARCH`: no two choices a search reads the same, the same kind with the
  same words: "diamond cross pendant" and "diamond cross necklace" found the same 503;
- `RULE_SHELVES`: a shop's narrowest shelf that names one word before the kind's noun is
  a choice too, as it writes it: network cables are named "LAN", "Cat6", "Ethernet" or
  "Patch", none from 20 titles of two shops, and on the shelf "Network Cables" (71 on
  2026-10-29), the owner's own example of a cable (owner, 2026-10-28: «καλώδιο
  ίντερνετ»).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Collection, Mapping, Sequence

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
from .search_selection import (
    _CONNECTIVE_TOKENS,
    _FILTER_FIELDS,
    _KIND_MARKERS,
    _KIND_PHRASE_FIELDS,
    _PURPOSE_TOKENS,
    _carries,
    _context_allows_member,
    _filter_units,
    _kind_modifier,
    _kind_name_pattern,
    _merchant_identity,
    _product_search_fields,
)

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
# Two words make one modifier when they come before the nouns of this many kinds.
_PAIR_NOUNS = 2


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


@dataclass(frozen=True)
class _Named:
    """How one title names a kind: the word right before the noun of its name, that noun
    in the singular and as written, and the word before that word (`RULE_PHRASES`)."""

    word: str
    noun: str
    written: str
    lead: str = ""


def _could_be_word(word: str, noun: str, brand_words: Collection[str]) -> bool:
    return not (
        len(word) < 2
        or not word.replace("-", "").replace("'", "").isalpha()
        or word in _CONNECTIVE_TOKENS
        or word in _PURPOSE_TOKENS
        or any(part in brand_words for part in word.split("-"))
        or _singular(word) == noun
    )


def _possessive(word: str) -> str:
    """ "men's" for "men-s", how "Men’s" (a curly apostrophe) is read."""
    if word.endswith("-s") and word[:-2].isalpha():
        return word[:-2] + "'s"
    return word


def _word_before_noun(
    tokens: tuple[str, ...],
    spans: list,
    owners: list[int] | None,
    wholes: list[str],
    kind: str,
    brand_words: Collection[str],
) -> _Named | None:
    """The word a title puts right before the noun of this kind's name (or of a narrower
    kind's), and that noun in the singular: ("hdmi", "cable") for "Fixturon HDMI Cable
    2m", ("zip-up", "hoodie") for "Zip-Up Hoodie"; with the noun as written ("trousers")
    and the word before the word ("wide" in "Wide Leg Trousers", "3" in "3 Piece Suit").
    The word is "" when nothing that could be a choice stands there; None when the title
    does not name the kind in English."""
    for span in spans:
        if span.kind != "en" or kind not in broader_concepts(span.concept_id):
            continue
        at = span.end - 1
        noun = _singular(tokens[at])
        if owners is not None:
            # The whole written word before the one the noun stands in ("t-shirt").
            place = owners[at] - 1
            word = wholes[place] if place >= 0 else ""
            lead = wholes[place - 1] if place >= 1 else ""
        else:
            word = tokens[at - 1] if at > 0 else ""
            lead = tokens[at - 2] if at > 1 else ""
        word = _possessive(word)
        if not _could_be_word(word, noun, brand_words):
            return _Named("", noun, tokens[at])
        if not (lead.isdigit() or _could_be_word(lead, noun, brand_words)):
            lead = ""
        return _Named(word, noun, tokens[at], lead)
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
    # The kind's products, by their place in the catalogue.
    rows: list[int] = field(default_factory=list)
    # Per "word noun": the shops naming it so, the words before its word, the noun as
    # written.
    word_shops: dict[str, set] = field(default_factory=lambda: defaultdict(set))
    word_leads: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    word_written: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    # Per word, the shops whose titles put it right before a kind's noun, any kind's,
    # over the whole catalogue (`RULE_SHOPS`), shared by every kind.
    shops_of_word: Mapping[str, set] = field(default_factory=dict)
    # The pairs of words that make one modifier, over the whole catalogue: a word and the
    # one before it, together before the nouns of `_PAIR_NOUNS` kinds or more ("long
    # sleeve", "slim fit"; `RULE_PHRASES`), shared by every kind.
    compounds: frozenset = frozenset()


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
    before: dict[str, dict[int, _Named | None]] = defaultdict(dict)
    for index, product_kinds in kinds_read_of.items():
        product = products[index]
        tokens, spans, owners, wholes = _names_in(str(product.title or ""))
        brand_words = set(normalize_understanding_text(str(product.brand or "")).split())
        for kind in product_kinds:
            before[kind][index] = _word_before_noun(tokens, spans, owners, wholes, kind, brand_words)
    word_kinds: Counter = Counter()
    for kind in read:
        words = Counter(named.word for named in before[kind].values() if named and named.word)
        for word, count in words.items():
            if count >= _MIN_WORD_PRODUCTS:
                word_kinds[word] += 1
    generic = {word for word, count in word_kinds.items() if count >= GENERIC_KINDS}
    shops_of_word: dict[str, set] = defaultdict(set)
    for kind in read:
        for index, named in before[kind].items():
            if named is not None and named.word:
                shop = _merchant_identity(products[index])
                if shop:
                    shops_of_word[named.word].add(shop)
    # Each title once, whatever kinds it is read for: an office chair is a chair too.
    pairs: Counter = Counter()
    for index, product_kinds in kinds_read_of.items():
        seen = {
            (named.lead, named.word, named.noun)
            for kind in product_kinds
            if (named := before[kind][index]) is not None and named.word and named.lead
        }
        pairs.update(seen)
    pair_nouns: Counter = Counter(
        (lead, word) for (lead, word, _noun), count in pairs.items() if count >= _MIN_WORD_PRODUCTS
    )
    compounds = frozenset(pair for pair, nouns in pair_nouns.items() if nouns >= _PAIR_NOUNS)
    groups: dict[str, _KindGroups] = {}
    for kind, rows in read.items():
        group = _KindGroups(
            len(rows), Counter(), Counter(), defaultdict(Counter), Counter(), Counter(), rows,
            shops_of_word=shops_of_word, compounds=compounds,
        )
        for index in rows:
            named = before[kind][index]
            narrowest = _narrowest_kind(kinds[index])
            if named is not None:
                group.nouns[named.noun] += 1
                if named.word and named.word not in generic:
                    text = f"{named.word} {named.noun}"
                    group.words[text] += 1
                    group.word_kinds[text][narrowest] += 1
                    shop = _merchant_identity(products[index])
                    if shop:
                        group.word_shops[text].add(shop)
                    if named.lead:
                        group.word_leads[text][named.lead] += 1
                    group.word_written[text][named.written] += 1
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
    it, and how many of the kind's products that search kept when the choices were
    worked out."""

    text: str
    products: int


# How many choices a general kind offers, the largest first.
CHOICES_OFFERED = 6
# A choice by the words gives way to a narrower kind that holds this share of its
# products: "charger cable" and "usb cable" are charging cables, offered as such.
_COVERED_SHARE = 0.8

# The rules that keep the choices true (module docstring), each named so a measure can
# leave it out and see what it changes.
RULE_SHOPS = "shops"
RULE_PHRASES = "phrases"
RULE_WHOLE_KIND = "whole_kind"
RULE_WRITTEN = "written"
RULE_SAME_SEARCH = "same_search"
RULE_SHELVES = "shelves"
CHOICE_RULES = frozenset(
    {RULE_SHOPS, RULE_PHRASES, RULE_WHOLE_KIND, RULE_WRITTEN, RULE_SAME_SEARCH, RULE_SHELVES}
)
# A choice by the words is named so by this many shops, or its word is put before a
# noun by this many shops somewhere in the catalogue.
MIN_SHOPS = 2
# A word is half of a phrase when this share of its titles put before it a number ("3
# Piece Suit") or a word the two make one modifier with (`_KindGroups.compounds`).
HALF_PHRASE_SHARE = 0.75
# No choice whose search keeps this share of its kind.
KEEPS_SHARE = 0.9

# What became of each choice considered (`kind_choice_candidates`).
OFFERED = "offered"
NOT_NARROWING = "not read as narrowing the kind"
COVERED = "a narrower kind offered holds it"
FEW_SHOPS = f"one shop's own word: named so by fewer than {MIN_SHOPS} shops, and used by no other"
HALF_PHRASE = "half of a phrase"
WHOLE_KIND = f"its search keeps {KEEPS_SHARE:.0%} of the kind or more"
SAME_SEARCH = "searched as a larger choice is"
FINDS_FEW = f"its search finds fewer than {MIN_GROUP} of the kind"
BEYOND = f"beyond the {CHOICES_OFFERED} offered"


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


def _shelf_choice(shelf: str, nouns: Collection[str]) -> str:
    """A shop's narrowest shelf as a choice, as the shelf writes it, when it names one word
    before the kind's noun: "network cables" for "Network Cables"; "" for any other shelf
    ("Audio & Video Cables", "Cables", "Ceiling Light Fixtures")."""
    # "Charms & Pendants", "Coats & Jackets" are two shelves in one.
    if any(mark in shelf for mark in ("&", ",", "/", "+")) or " and " in shelf.lower():
        return ""
    words = normalize_understanding_text(shelf).split()
    if len(words) != 2 or _singular(words[1]) not in nouns:
        return ""
    word = words[0]
    if (
        len(word) < 2
        or not word.isalpha()
        or word in _CONNECTIVE_TOKENS
        or word in _PURPOSE_TOKENS
        or _singular(word) == _singular(words[1])
    ):
        return ""
    return f"{word} {words[1]}"


def _search_key(text: str) -> tuple:
    """What a search for `text` asks of the feed: its kind, the words it filters by and
    its specs, whatever their order."""
    reading = understand_product_query(text)
    filters = frozenset(term for term in reading.filters if term not in _CONNECTIVE_TOKENS)
    return (reading.concept_id, filters, frozenset(spec.token for spec in reading.specs))


@dataclass(frozen=True)
class ChoiceCandidate:
    """One choice a general kind could offer, and what became of it."""

    text: str
    # The kind's products whose titles name it so (or of the narrower kind).
    products: int
    # Of the kind's products, how many its search keeps; None when not counted.
    found: int | None
    outcome: str
    # How many shops name it so; None for a narrower kind.
    shops: int | None = None


class _KindSearch:
    """What a search for a choice keeps of one kind's products, read as the price-first
    search reads it (`search_selection._select_products_for_concept`): the products of
    the kind the choice names that carry every word it filters by, in their title, type
    and brand."""

    def __init__(self, kind: str, rows: list[int], kinds: Sequence[Collection[str]], fields_of) -> None:
        self.kind = kind
        self.rows = rows
        self.kinds = kinds
        self.fields = [fields_of(index) for index in rows]
        self.brand_words = frozenset(word for row in self.fields for word in row.get("brand", "").split())
        self.haystacks = [
            {scope: " ".join(row[name] for name in scope if row.get(name)) for scope in (_FILTER_FIELDS, _KIND_PHRASE_FIELDS)}
            for row in self.fields
        ]

    def found(self, text: str) -> int:
        reading = understand_product_query(text)
        concept = str(reading.concept_id or "")
        places = [place for place, index in enumerate(self.rows) if concept in self.kinds[index]]
        filters = tuple(term for term in reading.filters if term not in _CONNECTIVE_TOKENS)
        if not filters:
            return len(places)
        units = _filter_units(
            filters,
            reading.filter_sources,
            spec_values=frozenset(spec.token for spec in reading.specs),
            modifier=_kind_modifier(reading, self.brand_words),
            kind_names=_kind_name_pattern(concept),
        )
        return sum(1 for place in places if all(_carries(unit, self.haystacks[place]) for unit in units))


def _word_candidates(group: _KindGroups, text: str, count: int, rules: Collection[str]) -> list[tuple[str, int, str]]:
    """The choices one group of titles gives, (text, products, outcome when it is no
    choice or ""): "hdmi cable"; the phrases a half of one stands in ("3 piece suit" and
    "2 piece suit" for "piece suit"); the noun as the titles write it. A whole phrase is
    named by the shops of its half."""
    word, noun = text.rsplit(" ", 1)
    written = noun
    if RULE_WRITTEN in rules and group.word_written[text]:
        written = group.word_written[text].most_common(1)[0][0]
    if (
        RULE_SHOPS in rules
        and len(group.word_shops[text]) < MIN_SHOPS
        and len(group.shops_of_word.get(word, ())) < MIN_SHOPS
    ):
        return [(f"{word} {written}", count, FEW_SHOPS)]
    if RULE_PHRASES in rules:
        leads = group.word_leads[text]

        def fixed(lead: str) -> bool:
            # A number counts ("3 Piece"); a word the two make one modifier with before
            # other nouns too ("Slim Fit Suit", "Slim Fit Jeans"), unless it names the
            # kind on its own too, and so says how it is: "Diamond Bracelet" makes
            # "Diamond Tennis Bracelet" a tennis bracelet of diamonds.
            if lead.isdigit():
                return True
            return (lead, word) in group.compounds and group.words.get(f"{lead} {noun}", 0) < MIN_GROUP

        if sum(c for lead, c in leads.items() if fixed(lead)) >= HALF_PHRASE_SHARE * count:
            whole = [
                (f"{lead} {word} {written}", c, "") for lead, c in leads.most_common() if c >= MIN_GROUP and fixed(lead)
            ]
            return whole + [(f"{word} {written}", count, HALF_PHRASE)]
    return [(f"{word} {written}", count, "")]


def kind_choice_candidates(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    fields: Sequence[Mapping[str, str]] | None = None,
    *,
    rules: Collection[str] = CHOICE_RULES,
) -> dict[str, tuple[ChoiceCandidate, ...]]:
    """Per kind of at least `MIN_PRODUCTS` products, every choice it could offer and what
    became of it: its narrower kinds (named as the lexicon first names them), the words
    its titles name it with and its shelves, from `MIN_GROUP` products each, kept while
    the search reads them as narrowing it (`_narrows`), its own search keeps `MIN_GROUP`
    of the kind or more, and by the `rules` (module docstring); at most
    `CHOICES_OFFERED`, the largest by what that search keeps first. `fields`, when given,
    are the products' search fields, in order."""
    groups, _generic_words = _kind_groups(products, kinds)
    return choice_candidates_of(groups, products, kinds, fields, rules=rules)


def choice_candidates_of(
    groups: Mapping[str, _KindGroups],
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    fields: Sequence[Mapping[str, str]] | None = None,
    *,
    rules: Collection[str] = CHOICE_RULES,
) -> dict[str, tuple[ChoiceCandidate, ...]]:
    """`kind_choice_candidates` from groups already made (`_kind_groups`), so a measure
    can weigh each rule without reading every title again."""
    by_id = get_product_concepts_by_id()

    def fields_of(index: int) -> Mapping[str, str]:
        return fields[index] if fields is not None else _product_search_fields(products[index])

    considered: dict[str, tuple[ChoiceCandidate, ...]] = {}
    for kind, group in groups.items():
        narrower = {name: count for name, count in group.narrower.items() if count >= MIN_GROUP}
        candidates: dict[str, tuple[int, str, int | None]] = {}

        def consider(text: str, count: int, outcome: str, shops: int | None) -> None:
            # One entry a text: a choice still open over one already ruled out, then the
            # larger count.
            current = candidates.get(text)
            if current is None or (bool(current[1]), -current[0]) > (bool(outcome), -count):
                candidates[text] = (count, outcome, shops)

        for narrower_kind, count in narrower.items():
            concept = by_id.get(narrower_kind)
            name = concept.primary_english if concept is not None else ""
            if name:
                consider(name, count, "", None)
        for text, count in group.words.items():
            if count < MIN_GROUP:
                continue
            shops = len(group.word_shops[text])
            inside = group.word_kinds[text]
            if any(name in narrower and held >= _COVERED_SHARE * count for name, held in inside.items()):
                consider(text, count, COVERED, shops)
                continue
            for phrase, products_named, outcome in _word_candidates(group, text, count, rules):
                consider(phrase, products_named, outcome, shops)
        if RULE_SHELVES in rules:
            for shelf, count in group.shelves.items():
                text = _shelf_choice(shelf, group.nouns)
                if text and count >= MIN_GROUP:
                    consider(text, count, "", None)
        search: _KindSearch | None = None
        # What each choice's own search keeps of the kind, for those still open; the
        # largest of those, by what the buyer would find, are offered.
        judged: list[list] = []
        for text, (count, outcome, shops) in candidates.items():
            found = None
            if not outcome and not _narrows(text, kind):
                outcome = NOT_NARROWING
            if not outcome:
                if search is None:
                    search = _KindSearch(kind, group.rows, kinds, fields_of)
                found = search.found(text)
                if found < MIN_GROUP:
                    # A shelf's words may be in no field the search reads ("End Tables"
                    # on 800 products, the search finding 7).
                    outcome = FINDS_FEW
                elif RULE_WHOLE_KIND in rules and found >= KEEPS_SHARE * group.products:
                    outcome = WHOLE_KIND
            judged.append([text, count, found, outcome, shops])
        judged.sort(key=lambda row: (bool(row[3]), -(row[2] or 0), -row[1], row[0]))
        offered = 0
        searches: set[tuple] = set()
        for row in judged:
            if row[3]:
                continue
            if RULE_SAME_SEARCH in rules:
                # "diamond cross pendant" and "diamond cross necklace" are one search: a
                # necklace with "diamond" and "cross".
                same = _search_key(row[0])
                if same in searches:
                    row[3] = SAME_SEARCH
                    continue
                searches.add(same)
            if offered >= CHOICES_OFFERED:
                row[3] = BEYOND
                continue
            row[3] = OFFERED
            offered += 1
        considered[kind] = tuple(
            ChoiceCandidate(text=text, products=count, found=found, outcome=outcome, shops=shops)
            for text, count, found, outcome, shops in judged
        )
    return considered


def build_kind_choices(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    fields: Sequence[Mapping[str, str]] | None = None,
    *,
    rules: Collection[str] = CHOICE_RULES,
) -> dict[str, tuple[KindChoice, ...]]:
    """The choices each general kind offers, for the products a search can show
    (`kind_choice_candidates`): a kind is general, and listed, with `MIN_CHOICES` of
    them."""
    offered: dict[str, tuple[KindChoice, ...]] = {}
    for kind, rows in kind_choice_candidates(products, kinds, fields, rules=rules).items():
        kept = tuple(
            KindChoice(text=row.text, products=row.found or row.products) for row in rows if row.outcome == OFFERED
        )
        if len(kept) >= MIN_CHOICES:
            offered[kind] = kept
    return offered
