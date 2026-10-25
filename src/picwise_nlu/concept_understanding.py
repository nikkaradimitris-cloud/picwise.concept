"""Understand which product a buyer means, however they spelled it.

Buyers in Greece type product searches in Greek without accents, with the wrong vowel
for a sound (ι for η, ο for ω, ε for αι), in greeklish under whatever transliteration
habit they have, with the English keyboard layout still on, or in English with a slipped
key. This module maps all of those onto one product concept from
`picwise_nlu.product_concepts`.

How a word is recognised:

1. **By sound.** Greek and greeklish are both reduced to one phonetic key in which every
   spelling of the same sound is the same letter: η, ι, υ, ει, οι -> i; ο, ω -> o;
   ε, αι -> e; ου -> u; μπ -> b; ντ -> d; γκ -> g. "πλυντήριο", "πλιντηριο",
   "plyntirio", "plintirio" and "plhntirio" all share a key.
2. **Wrong keyboard layout.** Latin text is also read as the Greek it would be if typed
   with the Greek layout on: "cygeio" -> "ψυγειο".
3. **By edit distance.** What is left -- a missing, swapped, doubled or neighbouring
   letter -- is absorbed by a Damerau-Levenshtein distance of 1 for short words and 2
   for long ones, found with a deletion index so it costs a few dictionary lookups
   rather than a scan of the lexicon.

How a query is read:

- the longest run of words naming a concept wins, so "φούρνος μικροκυμάτων" is a
  microwave, not an oven, and "μπαταρία αυτοκινήτου" is a car battery
- when a query names several products, the product being bought is the one before
  "για/for/with/με"; among the rest, Greek names the product first ("θήκη κινητού")
  and English last ("iphone case")
- what is not the product becomes a filter: a spec ("8 κιλά" -> 8kg), a preference
  translated to the feed's language ("ασύρματο" -> wireless), or a word such as a
  brand that is kept as typed. Judgements such as "φθηνό" are recognised but are never
  filters, because no feed field can confirm them.
- words that are not retail at all (a bank, a loan, insurance) are never fuzzily
  matched onto a product: "τράπεζα" is one letter from "τραπέζι" and must not become
  a table.
- a word asking for a non-new item ("μεταχειρισμένο", "metaxirismeno", "refurbished")
  is read as a condition request, not as a filter: the feed states a condition in its
  own column, so matching the word against feed text would answer the wrong question.

Product text is annotated with the same lexicon but by exact key only, since feed text
is spelled correctly and a fuzzy match there would invent concepts.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .misspelling_variants import english_layout_text_to_greek
from .product_concepts import (
    broader_concepts,
    get_condition_request_words,
    get_product_concepts,
    get_product_concepts_by_id,
    get_qualifiers,
    spec_fields_for_mega_category,
)

# --------------------------------------------------------------------------------------
# Text normalisation and phonetic keys
# --------------------------------------------------------------------------------------

_NON_TOKEN_RE = re.compile(r"[^\w\s/.\"']+", flags=re.UNICODE)
_DOT_NOT_IN_NUMBER_RE = re.compile(r"(?<!\d)\.|\.(?!\d)")


def _strip_marks(text: str) -> str:
    if text.isascii():
        # Nothing to strip, and most feed text is ASCII: checked first, it saves
        # seconds when a large feed is read for the first time.
        return text
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    )


def strip_accents_if_needed(text: str) -> str:
    """Strip accents from text that has any; ASCII text is returned untouched."""
    return text if text.isascii() else _strip_marks(text)


def normalize_understanding_text(text: str) -> str:
    """Lowercase, strip accents, and split on everything but words, numbers and specs."""
    lowered = _strip_marks(str(text or "")).lower()
    lowered = lowered.replace("_", " ").replace("-", " ").replace("&", " ")
    lowered = _NON_TOKEN_RE.sub(" ", lowered)
    lowered = _DOT_NOT_IN_NUMBER_RE.sub(" ", lowered)
    return " ".join(lowered.split())


def _is_greek_char(ch: str) -> bool:
    return "Ͱ" <= ch <= "Ͽ" or "ἀ" <= ch <= "῿"


def is_greek_word(word: str) -> bool:
    if word.isascii():
        return False
    letters = [ch for ch in word if ch.isalpha()]
    return bool(letters) and sum(_is_greek_char(ch) for ch in letters) * 2 >= len(letters)


def _collapse_doubles(text: str) -> str:
    output: list[str] = []
    for ch in text:
        if not output or output[-1] != ch or ch.isdigit():
            output.append(ch)
    return "".join(output)


_GREEK_DIGRAPH_KEYS = (
    ("ου", "u"),
    ("ει", "i"),
    ("οι", "i"),
    ("υι", "i"),
    ("αι", "e"),
    ("αυ", "av"),
    ("ευ", "ev"),
    ("ηυ", "iv"),
    ("μπ", "b"),
    ("ντ", "d"),
    ("γκ", "g"),
    ("γγ", "g"),
)
_GREEK_LETTER_KEYS = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th",
    "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "ks", "ο": "o", "π": "p",
    "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "i", "φ": "f", "χ": "h", "ψ": "ps",
    "ω": "o",
}


@lru_cache(maxsize=65536)
def greek_key(word: str) -> str:
    """Phonetic key of a Greek word: every spelling of a sound maps to one letter."""
    source = _strip_marks(word).lower()
    output: list[str] = []
    index = 0
    while index < len(source):
        pair = source[index:index + 2]
        for digraph, key in _GREEK_DIGRAPH_KEYS:
            if pair == digraph:
                output.append(key)
                index += 2
                break
        else:
            ch = source[index]
            output.append(_GREEK_LETTER_KEYS.get(ch, ch))
            index += 1
    return _collapse_doubles("".join(output))


_LATIN_DIGRAPH_KEYS = (
    ("ou", "u"),
    ("ei", "i"),
    ("oi", "i"),
    ("yi", "i"),
    ("ai", "e"),
    ("au", "av"),
    ("af", "av"),
    ("ef", "ev"),
    ("eu", "ev"),
    ("mp", "b"),
    ("nt", "d"),
    ("gk", "g"),
    ("gg", "g"),
    ("ch", "h"),
    ("kh", "h"),
    ("th", "th"),
    ("ps", "ps"),
    ("ks", "ks"),
)
_LATIN_LETTER_KEYS = {"y": "i", "w": "o", "x": "h", "c": "k", "q": "k", "j": "i"}
_LATIN_VOWELS = frozenset("aeiouyw")


@lru_cache(maxsize=65536)
def greeklish_key(word: str) -> str:
    """Phonetic key of a greeklish word, in the same alphabet as `greek_key`."""
    source = str(word or "").lower()
    # Digits written for letters by shape, only between letters: "a8litika", "3iristiki".
    source = re.sub(r"(?<=[a-z])8|8(?=[a-z])", "th", source)
    source = re.sub(r"(?<=[a-z])3|3(?=[a-z])", "ks", source)
    output: list[str] = []
    index = 0
    while index < len(source):
        pair = source[index:index + 2]
        for digraph, key in _LATIN_DIGRAPH_KEYS:
            if pair == digraph:
                output.append(key)
                index += 2
                break
        else:
            ch = source[index]
            if ch == "h":
                # "h" is η when written by shape ("hlektriko") and χ when written by
                # sound ("rouhon"). Before a consonant or at the end it can only be η.
                following = source[index + 1:index + 2]
                output.append("i" if not following or following not in _LATIN_VOWELS else "h")
            else:
                output.append(_LATIN_LETTER_KEYS.get(ch, ch))
            index += 1
    return _collapse_doubles("".join(output))


@lru_cache(maxsize=65536)
def english_key(word: str) -> str:
    return _collapse_doubles(str(word or "").lower().replace("ph", "f"))


# --------------------------------------------------------------------------------------
# Fuzzy lookup
# --------------------------------------------------------------------------------------


def _max_distance(length: int) -> int:
    """How many typing mistakes a word of this many typed letters may carry."""
    if length <= 3:
        return 0
    if length <= 7:
        return 1
    return 2


def _indexed_distance(key_length: int) -> int:
    # Keys are shorter than the words typed (doubles collapse, digraphs merge), so a
    # key is indexed for the most mistakes any word that produces it may carry.
    if key_length >= 7:
        return 2
    if key_length >= 3:
        return 1
    return 0


def _deletes(word: str, distance: int) -> set[str]:
    results = {word}
    frontier = {word}
    for _ in range(distance):
        next_frontier: set[str] = set()
        for item in frontier:
            for index in range(len(item)):
                next_frontier.add(item[:index] + item[index + 1:])
        results |= next_frontier
        frontier = next_frontier
    return results


def damerau_levenshtein(left: str, right: str, limit: int) -> int:
    """Optimal string alignment distance, returning limit+1 as soon as it is exceeded."""
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    previous_previous: list[int] = []
    previous = list(range(len(right) + 1))
    for i, lch in enumerate(left, start=1):
        current = [i] + [0] * len(right)
        row_min = current[0]
        for j, rch in enumerate(right, start=1):
            cost = 0 if lch == rch else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if (
                i > 1
                and j > 1
                and lch == right[j - 2]
                and left[i - 2] == rch
            ):
                value = min(value, previous_previous[j - 2] + 1)
            current[j] = value
            row_min = min(row_min, value)
        if row_min > limit:
            return limit + 1
        previous_previous, previous = previous, current
    return previous[-1]


class _FuzzyIndex:
    """Deletion index: a word within distance d shares a d-deletion with the query."""

    def __init__(self, words: set[str]) -> None:
        self.words = frozenset(words)
        self._by_delete: dict[str, set[str]] = {}
        for word in words:
            for variant in _deletes(word, _indexed_distance(len(word))):
                self._by_delete.setdefault(variant, set()).add(word)

    def lookup(self, key: str, limit: int) -> dict[str, int]:
        """Lexicon words within `limit` edits of `key`, with their distance."""
        if not key:
            return {}
        found: dict[str, int] = {}
        if key in self.words:
            found[key] = 0
        if limit <= 0:
            return found
        candidates: set[str] = set()
        for variant in _deletes(key, limit):
            candidates |= self._by_delete.get(variant, set())
        for candidate in candidates:
            if candidate in found or candidate[:1] != key[:1]:
                # A first letter is almost never the mistyped one, and requiring it
                # keeps fuzzy matching from jumping between unrelated words.
                continue
            word_limit = min(limit, _indexed_distance(len(candidate)))
            distance = damerau_levenshtein(key, candidate, word_limit)
            if distance <= word_limit:
                found[candidate] = distance
        return found


# --------------------------------------------------------------------------------------
# Lexicon index
# --------------------------------------------------------------------------------------

# Words that are never product filters: the buyer's grammar, not their request.
CONNECTIVE_WORDS = frozenset(
    {
        "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "my", "of",
        "on", "or", "per", "the", "to", "with", "without",
        "για", "με", "και", "σε", "στο", "στη", "στην", "στον", "στα", "του", "της",
        "των", "το", "τα", "τη", "την", "τον", "η", "ο", "οι", "ενα", "ενας", "μια",
        "απο", "χωρις", "θελω", "ψαχνω",
        "gia", "me", "kai", "se", "sto", "sti", "stin", "tou", "tis", "ton", "to", "ta",
        "ena", "mia", "apo", "xoris", "choris", "thelo", "psaxno",
    }
)
# Connectives after which the words describe what the product is for, not the product.
# "w/" is how feed titles write "with": "Christmas Tree ... w/ LED Lights Pot Table Desk".
_PURPOSE_WORDS = frozenset(
    {"for", "with", "without", "w/", "για", "με", "χωρις", "gia", "me", "xoris", "choris"}
)

# Not retail product searches. Never fuzzily matched onto a product name.
_NON_RETAIL_WORDS = frozenset(
    {
        "δανειο", "δανεια", "τραπεζα", "τραπεζες", "ασφαλεια", "ασφαλειες",
        "ασφαλιση", "επιτοκιο", "καιρος", "καιρο", "λογιστικο", "λογισμικο",
        "loan", "loans", "bank", "banks", "insurance", "mortgage", "weather",
        "daneio", "trapeza", "asfaleia", "kairos",
    }
)

# Everyday words that are not products but are one typo away from one. They are only
# ever matched exactly, never corrected. Not exhaustive: a correction that does slip
# through is shown to the buyer ("results for ...") rather than applied silently.
_COMMON_WORDS = frozenset(
    """
    κρασι κρασια μπυρα νερο ψωμι φαγητο καφες καφε τσαι γαλα πιτσα σουβλακι μουσακα
    συνταγη συνταγες εστιατοριο ταβερνα ξενοδοχειο ξενοδοχεια ταξιδι ταξιδια διακοπες
    εισιτηρια εισιτηριο πτησεις πτηση παιδια παιδι μωρο μωρα γυναικα αντρας ανδρας
    οικογενεια φιλος φιλοι γιατρος γιατροι νοσοκομειο φαρμακειο σχολειο πανεπιστημιο
    μαθηματα μαθημα δουλεια εργασια εργασιες μισθος συνταξη εφορια ενοικιο σπιτι σπιτια
    διαμερισμα οικοπεδο καιρος ειδησεις ταινια ταινιες τραγουδι τραγουδια μουσικη
    ποδοσφαιρο μπασκετ αγωνας αγωνες κουρεμα μανικιουρ πιστωτικη χρεωστικη καρτα καρτες
    λογαριασμος λογαριασμοι ρευμα δημος δημαρχειο αστυνομια δικηγορος λογιστης
    krasi mpyra nero psomi fagito kafes paidia paidi moro douleia ergasia spiti kairos
    wine beer food pizza recipe hotel hotels flight flights ticket tickets news weather
    job jobs salary rent school doctor movie movies song songs football
    horse horses cow cows sheep goat goats bird birds house houses
    """.split()
)

# The products PicWise sells and the buyer would call their spec by a unit.
_UNIT_ALIASES = {
    "kg": ("kg", "kgs", "kilo", "kilos", "kila", "κιλα", "κιλο", "κιλων"),
    "l": ("l", "lt", "lt.", "ltr", "litre", "litres", "liter", "liters", "litra", "litro", "λιτρα", "λιτρο", "λιτρων"),
    "inch": ("inch", "inches", "\"", "''", "intses", "intsa", "ιντσες", "ιντσα", "ιντσων"),
    "mah": ("mah",),
    "ah": ("ah",),
    "wh": ("wh",),
    "w": ("w", "watt", "watts", "βατ"),
    "v": ("v", "volt", "volts", "βολτ"),
    "gb": ("gb", "giga"),
    "tb": ("tb",),
    "hz": ("hz",),
    "rpm": ("rpm", "στροφες"),
    "db": ("db",),
    "btu": ("btu",),
    "mm": ("mm",),
    "cm": ("cm", "εκ"),
    "mp": ("mp", "megapixel"),
}
_UNIT_BY_ALIAS = {alias: unit for unit, aliases in _UNIT_ALIASES.items() for alias in aliases}
# Units read only when written onto the number: "24in" is 24 inches, while the "in" of
# "2 in 1" is the word "in".
_FUSED_ONLY_UNIT_BY_ALIAS = {"in": "inch"}
_FUSED_SPEC_RE = re.compile(r"^(\d+(?:[.,]\d+)?)([a-zα-ω\"']+)$")
_NUMBER_RE = re.compile(r"^\d+(?:[.,]\d+)?$")

# Which spec field of the product rules a unit measures, by field-name fragment.
_UNIT_FIELD_HINTS = {
    "kg": ("_kg",),
    "l": ("liters", "_l"),
    "inch": ("inch", "laptop_size"),
    "mah": ("mah",),
    "ah": ("_ah",),
    "wh": ("_wh",),
    "w": ("watts", "wattage"),
    "v": ("voltage", "_v"),
    "gb": ("_gb",),
    "tb": ("storage",),
    "hz": ("_hz",),
    "rpm": ("rpm",),
    "db": ("_db",),
    "btu": ("btu",),
    "mm": ("_mm",),
    "cm": ("_cm",),
    "mp": ("camera",),
}


@dataclass(frozen=True)
class _Form:
    concept_id: str
    words: tuple[tuple[str, str], ...]  # (kind, key) per word; kind is "el" or "en"
    # A name that also reads as an ordinary word inside other products' names
    # ("cap", "ball", "screen"). Read from a query, ignored in feed text.
    weak: bool = False


def _word_identity(word: str) -> tuple[str, str]:
    if is_greek_word(word):
        return ("el", greek_key(word))
    return ("en", english_key(word))


class _Lexicon:
    def __init__(self) -> None:
        self.forms_by_first: dict[tuple[str, str], list[_Form]] = {}
        words: dict[str, set[str]] = {"el": set(), "en": set()}
        for concept in get_product_concepts():
            weak_forms = {normalize_understanding_text(form) for form in concept.weak}
            for text in concept.english + concept.greek:
                tokens = normalize_understanding_text(text).split()
                if not tokens:
                    continue
                identities = tuple(_word_identity(token) for token in tokens)
                weak = normalize_understanding_text(text) in weak_forms
                self._add(_Form(concept.concept_id, identities, weak), words)
                kinds = {kind for kind, _ in identities}
                if len(identities) > 1 and len(kinds) == 1:
                    # The same name typed without spaces: "πλυντηριορουχων".
                    joined = (identities[0][0], "".join(key for _, key in identities))
                    self._add(_Form(concept.concept_id, (joined,), weak), words)
        self.fuzzy = {kind: _FuzzyIndex(keys) for kind, keys in words.items()}
        # English names as spelled, to tell an exact word from one that only shares
        # its key once doubled letters collapse ("bots" and "boots").
        self.english_spellings = frozenset(
            token
            for concept in get_product_concepts()
            for text in concept.english + concept.greek
            for token in normalize_understanding_text(text).split()
            if not is_greek_word(token)
        )
        # Which kinds each English word belongs to, and which kinds each Greek key
        # belongs to: "patio" is a word of "patio furniture", not of «πάτοι».
        english_word_concepts: dict[str, set[str]] = {}
        greek_key_concepts: dict[str, set[str]] = {}
        for concept in get_product_concepts():
            for text in concept.english + concept.greek:
                for token in normalize_understanding_text(text).split():
                    if is_greek_word(token):
                        greek_key_concepts.setdefault(greek_key(token), set()).add(concept.concept_id)
                    else:
                        english_word_concepts.setdefault(token, set()).add(concept.concept_id)
        self.english_word_concepts = {word: frozenset(ids) for word, ids in english_word_concepts.items()}
        self.greek_key_concepts = {key: frozenset(ids) for key, ids in greek_key_concepts.items()}

        self.qualifiers: dict[str, str | None] = {}
        qualifier_keys: set[str] = set()
        for qualifier in get_qualifiers():
            for form in qualifier.greek:
                for token in [normalize_understanding_text(form)]:
                    identity = _word_identity(token) if " " not in token else ("", "")
                    if not identity[1]:
                        continue
                    self.qualifiers[identity[1]] = qualifier.english
                    qualifier_keys.add(identity[1])
        self.qualifier_fuzzy = _FuzzyIndex(qualifier_keys)
        # The feed's own language for the same preferences ("black", "wireless"), used
        # to tell a word that only describes a product from one that renames it.
        self.english_qualifier_words = frozenset(
            word
            for qualifier in get_qualifiers()
            if qualifier.english
            for word in normalize_understanding_text(qualifier.english).split()
        )

        # Words asking for a non-new item, by the same phonetic keys as everything
        # else, so "μεταχειρισμένο", "metaxirismeno" and "used" are all read. Phrases
        # ("second hand") are keyed word by word and looked up as a pair.
        condition = get_condition_request_words()
        self.condition_words: set[str] = set()
        self.condition_phrases: set[str] = set()
        for form in condition.english + condition.greek:
            keys = [_word_identity(token)[1] for token in normalize_understanding_text(form).split()]
            if not keys or not all(keys):
                continue
            if len(keys) == 1:
                self.condition_words.add(keys[0])
            else:
                self.condition_phrases.add(" ".join(keys))
        self.condition_fuzzy = _FuzzyIndex(self.condition_words)

    def _add(self, form: _Form, words: dict[str, set[str]]) -> None:
        self.forms_by_first.setdefault(form.words[0], []).append(form)
        for kind, key in form.words:
            words[kind].add(key)


@lru_cache(maxsize=1)
def _lexicon() -> _Lexicon:
    return _Lexicon()


# --------------------------------------------------------------------------------------
# Reading a query
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Span:
    start: int
    end: int
    concept_id: str
    cost: float
    kind: str
    weak: bool = False


@dataclass(frozen=True)
class SpecValue:
    token: str
    unit: str
    spec_field: str | None
    source: str


@dataclass(frozen=True)
class ConceptReading:
    """What PicWise understood from one query.

    `filters` are feed-facing words the inventory should be checked against, in the
    order the buyer gave them; `filter_sources` maps each back to what was typed so the
    page can quote the buyer's own words when a filter cannot be satisfied.
    `judgements` were understood but can never be confirmed from feed text.
    """

    query: str
    tokens: tuple[str, ...]
    concept_id: str | None = None
    mega_category_id: str | None = None
    concept_words: tuple[str, ...] = ()
    feed_terms: tuple[str, ...] = ()
    fallback_concept_id: str | None = None
    fallback_unmatched: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    filter_sources: dict[str, str] = field(default_factory=dict)
    judgements: tuple[str, ...] = ()
    # The buyer's own words asking for a non-new item ("μεταχειρισμένο", "refurbished").
    # Never a filter: no feed text can be trusted to carry them, and the feed states a
    # condition in its own column. The selection reads them as a condition request.
    condition_request: tuple[str, ...] = ()
    specs: tuple[SpecValue, ...] = ()
    other_concepts: tuple[str, ...] = ()
    non_retail: bool = False
    exact: bool = False
    spec_fields: tuple[str, ...] = ()
    # "el" when the product was named in Greek or greeklish, "en" in English.
    head_language: str = ""

    @property
    def understood(self) -> bool:
        return bool(self.concept_id) and not self.non_retail

    def to_dict(self) -> dict[str, object]:
        return {
            "concept_id": self.concept_id,
            "mega_category_id": self.mega_category_id,
            "concept_words": list(self.concept_words),
            "feed_terms": list(self.feed_terms),
            "filters": list(self.filters),
            "judgements": list(self.judgements),
            "condition_request": list(self.condition_request),
            "specs": [
                {"value": spec.token, "unit": spec.unit, "spec_field": spec.spec_field}
                for spec in self.specs
            ],
            "exact": self.exact,
            "non_retail": self.non_retail,
        }


def _token_candidates(token: str, *, fuzzy: bool = True) -> dict[tuple[str, str], float]:
    """Every lexicon word this token could be, with a cost: lower is more certain."""
    lexicon = _lexicon()
    candidates: dict[tuple[str, str], float] = {}
    limit = _max_distance(len(token)) if fuzzy else 0

    def offer(kind: str, key: str, bias: float, exact_key_cost: float = 0.0) -> None:
        if not key:
            return
        for word, distance in lexicon.fuzzy[kind].lookup(key, limit).items():
            cost = (distance or exact_key_cost) + bias
            identity = (kind, word)
            if cost < candidates.get(identity, 99.0):
                candidates[identity] = cost

    if not any(ch.isalpha() for ch in token):
        return candidates
    if is_greek_word(token):
        offer("el", greek_key(token), 0.0)
        # English words written in Greek letters: "λαπτοπ", "πρίντερ".
        offer("en", greek_key(token), 0.2)
    else:
        # Sharing a key without sharing the spelling is a correction, not a match.
        offer(
            "en",
            english_key(token),
            0.0,
            exact_key_cost=0.0 if token in lexicon.english_spellings else 0.5,
        )
        offer("el", greeklish_key(token), 0.1)
        # Greeklish letters with two habits: x is χ to most people and ξ to some
        # ("exoteriki"); h is η by shape and χ by sound.
        if "x" in token:
            offer("el", greeklish_key(token.replace("x", "ks")), 0.15)
        if "h" in token:
            offer("el", greeklish_key(token.replace("h", "x")), 0.15)
        if len(token) >= 3:
            offer("el", greek_key(english_layout_text_to_greek(token)), 0.3)
        # English before greeklish (owner's build order, step 2, 2026-10-16): a word
        # PicWise knows as English is not read as the greeklish of a Greek name of
        # another kind. "patio" was read as «πάτοι» (insoles), so "patio heater"
        # answered with insoles; "scales" as «σκάλες» (ladders). A greeklish reading
        # that names the same kind stays: "consoles" and «κονσόλες».
        own_kinds = lexicon.english_word_concepts.get(token)
        if own_kinds:
            for identity in [identity for identity in candidates if identity[0] == "el"]:
                if not lexicon.greek_key_concepts.get(identity[1], frozenset()) & own_kinds:
                    del candidates[identity]
    return candidates


def _fuzzy_span_is_safe(words: tuple[str, ...], exact_words: int) -> bool:
    """Whether a reading that needed a typo correction is trustworthy enough to act on.

    Short words sit close to many other words: "κρασί" is one letter from "κράνη",
    "παιδιά" one from "πέδιλα". A correction is accepted when another word of the same
    name was typed correctly ("pawer bank"), or when the single word is long enough
    that a one-letter slip cannot turn it into a different ordinary word.
    """
    if len(words) > 1:
        return exact_words >= 1
    # Greek has many more short everyday words one letter from a product name than
    # the English product vocabulary does, so it needs a longer word to trust.
    return len(words[0]) >= (6 if is_greek_word(words[0]) else 5)


def _find_spans(
    tokens: tuple[str, ...],
    candidates: list[dict[tuple[str, str], float]],
    *,
    safe_only: bool = True,
) -> list[_Span]:
    lexicon = _lexicon()
    spans: list[_Span] = []
    for start in range(len(tokens)):
        for identity, first_cost in candidates[start].items():
            for form in lexicon.forms_by_first.get(identity, ()):
                end = start + len(form.words)
                if end > len(tokens):
                    continue
                cost = first_cost
                exact_words = int(first_cost < 0.5)
                for offset, word in enumerate(form.words[1:], start=1):
                    word_cost = candidates[start + offset].get(word)
                    if word_cost is None:
                        break
                    cost += word_cost
                    exact_words += int(word_cost < 0.5)
                else:
                    if safe_only and cost >= 0.5 and not _fuzzy_span_is_safe(tokens[start:end], exact_words):
                        continue
                    spans.append(
                        _Span(start, end, form.concept_id, cost, identity[0], form.weak)
                    )
    return spans


def _related(left: str, right: str) -> bool:
    return left in broader_concepts(right) or right in broader_concepts(left)


def _drop_uncertain_ties(spans: list[_Span]) -> list[_Span]:
    """A misspelling equally close to two unrelated products names neither.

    "καφειερα" is two edits from both "καφετιέρα" and "κάμερα". Picking one would be a
    guess presented as understanding, so neither reading is kept for that stretch of
    text. An exact match is never a tie of this kind.
    """
    best: dict[tuple[int, int], float] = {}
    for span in spans:
        position = (span.start, span.end)
        best[position] = min(best.get(position, 99.0), span.cost)
    uncertain: set[tuple[int, int]] = set()
    for position, cost in best.items():
        if cost < 0.5:
            continue
        tied = sorted(
            {span.concept_id for span in spans if (span.start, span.end) == position and span.cost - cost < 0.5}
        )
        if any(not _related(a, b) for i, a in enumerate(tied) for b in tied[i + 1:]):
            uncertain.add(position)
    return [span for span in spans if (span.start, span.end) not in uncertain]


def _choose_spans(spans: list[_Span]) -> list[_Span]:
    chosen: list[_Span] = []
    taken: set[int] = set()
    spans = _drop_uncertain_ties(spans)
    for span in sorted(spans, key=lambda s: (-(s.end - s.start), s.cost, s.start, s.concept_id)):
        positions = set(range(span.start, span.end))
        if positions & taken:
            continue
        chosen.append(span)
        taken |= positions
    return sorted(chosen, key=lambda s: s.start)


def _pick_head(spans: list[_Span], tokens: tuple[str, ...]) -> _Span | None:
    if not spans:
        return None
    covered = {i for span in spans for i in range(span.start, span.end)}
    purpose_at = next(
        (i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS and i not in covered),
        len(tokens),
    )
    before = [span for span in spans if span.start < purpose_at] or spans
    if len(before) == 1:
        return before[0]
    # A narrower concept beats the broader one it refines: "κράνος ... ποδηλάτου".
    for span in before:
        chain = set(broader_concepts(span.concept_id)[1:])
        if any(other.concept_id in chain for other in before if other is not span):
            return span
    if all(span.kind == "en" for span in before):
        return before[-1]
    return before[0]


def _parse_specs(tokens: list[str]) -> tuple[list[tuple[int, int, str, str]], set[int]]:
    """Find specs: fused ("8kg"), spaced ("8 κιλα") and tyre sizes. Returns spans."""
    found: list[tuple[int, int, str, str]] = []
    used: set[int] = set()
    for index, token in enumerate(tokens):
        if index in used:
            continue
        fused = _FUSED_SPEC_RE.match(token)
        if fused and (
            fused.group(2) in _UNIT_BY_ALIAS or fused.group(2) in _FUSED_ONLY_UNIT_BY_ALIAS
        ):
            unit = _UNIT_BY_ALIAS.get(fused.group(2)) or _FUSED_ONLY_UNIT_BY_ALIAS[fused.group(2)]
            found.append((index, index + 1, f"{fused.group(1).replace(',', '.')}{unit}", unit))
            used.add(index)
            continue
        if _NUMBER_RE.match(token) and index + 1 < len(tokens):
            unit = _UNIT_BY_ALIAS.get(tokens[index + 1])
            if unit:
                found.append((index, index + 2, f"{token.replace(',', '.')}{unit}", unit))
                used.update({index, index + 1})
    return found, used


def _spec_field_for(unit: str, spec_fields: tuple[str, ...]) -> str | None:
    for hint in _UNIT_FIELD_HINTS.get(unit, ()):
        for name in spec_fields:
            if hint in name:
                return name
    return None


def _is_exact_qualifier(token: str) -> bool:
    key = greek_key(token) if is_greek_word(token) else greeklish_key(token)
    return key in _lexicon().qualifiers


def _qualifier_for(token: str) -> tuple[bool, str | None]:
    """Is this a known preference word, and which feed word expresses it?"""
    lexicon = _lexicon()
    key = greek_key(token) if is_greek_word(token) else greeklish_key(token)
    if key in lexicon.qualifiers:
        return True, lexicon.qualifiers[key]
    if len(key) >= 5:
        matches = lexicon.qualifier_fuzzy.lookup(key, _max_distance(len(token)))
        if matches:
            best = min(matches, key=lambda word: (matches[word], word))
            return True, lexicon.qualifiers[best]
    return False, None


@dataclass(frozen=True)
class ConditionRequest:
    """Which words of a query ask for an item that is not new, and where they are."""

    words: tuple[str, ...] = ()
    positions: frozenset[int] = frozenset()

    @property
    def wants_non_new(self) -> bool:
        return bool(self.words)


def _condition_keys_for_token(token: str) -> tuple[str, ...]:
    """The keys this typed word could be: Greek by sound, Latin as English or greeklish."""
    if is_greek_word(token):
        return (greek_key(token),)
    return tuple(dict.fromkeys((english_key(token), greeklish_key(token))))


def _token_asks_for_non_new(token: str) -> bool:
    lexicon = _lexicon()
    keys = _condition_keys_for_token(token)
    if any(key in lexicon.condition_words for key in keys):
        return True
    # Only long words are corrected, as with preference words: at four letters "used"
    # is one mistake away from ordinary words, and reading those as a request for a
    # second-hand item would hide every new product the buyer actually wanted.
    return any(
        len(key) >= 5 and lexicon.condition_fuzzy.lookup(key, _max_distance(len(token)))
        for key in keys
    )


def _pair_asks_for_non_new(first: str, second: str) -> bool:
    lexicon = _lexicon()
    return any(
        f"{left} {right}" in lexicon.condition_phrases
        for left in _condition_keys_for_token(first)
        for right in _condition_keys_for_token(second)
    )


def _read_condition_request(tokens: tuple[str, ...]) -> ConditionRequest:
    words: list[str] = []
    positions: set[int] = set()
    index = 0
    while index < len(tokens):
        if index + 1 < len(tokens) and _pair_asks_for_non_new(tokens[index], tokens[index + 1]):
            words.append(" ".join(tokens[index:index + 2]))
            positions.update({index, index + 1})
            index += 2
            continue
        if _token_asks_for_non_new(tokens[index]):
            words.append(tokens[index])
            positions.add(index)
        index += 1
    return ConditionRequest(words=tuple(dict.fromkeys(words)), positions=frozenset(positions))


@lru_cache(maxsize=4096)
def read_condition_request(query: str) -> ConditionRequest:
    """Read a query for a request for a non-new item, without reading anything else.

    The selection needs this for queries that name no known product too, where there
    is no concept reading to carry it.
    """
    return _read_condition_request(tuple(normalize_understanding_text(query).split()))


def _words_of_concept(concept_id: str) -> set[tuple[str, str]]:
    concept = get_product_concepts_by_id()[concept_id]
    words: set[tuple[str, str]] = set()
    for text in concept.english + concept.greek:
        for token in normalize_understanding_text(text).split():
            words.add(_word_identity(token))
    return words


@lru_cache(maxsize=4096)
def understand_product_query(query: str) -> ConceptReading:
    """Read which product the buyer means and what else they asked for."""
    tokens = tuple(normalize_understanding_text(query).split())
    if not tokens:
        return ConceptReading(query=str(query or ""), tokens=tokens)

    condition = _read_condition_request(tokens)
    spec_spans, spec_positions = _parse_specs(list(tokens))
    non_retail_positions = {i for i, token in enumerate(tokens) if token in _NON_RETAIL_WORDS}
    # Connectives and non-retail words are matched exactly only: they may be part of a
    # product name ("φριτέζα χωρίς λάδι", "power bank") but are never guessed at.
    candidates = [
        {}
        if i in spec_positions or i in condition.positions
        else _token_candidates(
            token,
            fuzzy=not (
                i in non_retail_positions
                or token in CONNECTIVE_WORDS
                or token in _COMMON_WORDS
                or _is_exact_qualifier(token)
            ),
        )
        for i, token in enumerate(tokens)
    ]
    spans = _choose_spans(_find_spans(tokens, candidates))
    head = _pick_head(spans, tokens)

    if head is None:
        return ConceptReading(
            query=str(query or ""),
            tokens=tokens,
            condition_request=condition.words,
            non_retail=bool(non_retail_positions),
        )

    concept = get_product_concepts_by_id()[head.concept_id]
    spec_fields = spec_fields_for_mega_category(concept.mega_category_id)
    head_positions = set(range(head.start, head.end))

    filters: list[str] = []
    sources: dict[str, str] = {}
    judgements: list[str] = []
    specs: list[SpecValue] = []
    spec_start = {start: (end, value, unit) for start, end, value, unit in spec_spans}

    index = 0
    while index < len(tokens):
        if index in head_positions or index in condition.positions:
            index += 1
            continue
        if index in spec_start:
            end, value, unit = spec_start[index]
            source = " ".join(tokens[index:end])
            specs.append(SpecValue(value, unit, _spec_field_for(unit, spec_fields), source))
            filters.append(value)
            sources[value] = source
            index = end
            continue
        token = tokens[index]
        index += 1
        if token in CONNECTIVE_WORDS or len(token) < 2 and not token.isdigit():
            continue
        is_qualifier, english = _qualifier_for(token)
        if is_qualifier:
            if english is None:
                judgements.append(token)
            else:
                for word in english.split():
                    if word not in filters:
                        filters.append(word)
                        sources[word] = token
            continue
        if token not in filters:
            filters.append(token)
            sources[token] = token

    unknown_words = [term for term in filters if sources.get(term) == term and term not in {spec.token for spec in specs}]
    if head.cost >= 0.5 and head.end - head.start == 1 and len(unknown_words) >= 2:
        # A corrected single word among several words PicWise does not know is more
        # likely an ordinary word than a misspelled product: "wedding cake topper" is
        # not a toner. Without the rest of the query making sense, do not guess.
        return ConceptReading(
            query=str(query or ""), tokens=tokens, condition_request=condition.words
        )

    fallback = concept.broader[0] if concept.broader else None
    fallback_unmatched: tuple[str, ...] = ()
    if fallback:
        broader_words = _words_of_concept(fallback)
        fallback_unmatched = tuple(
            tokens[i]
            for i in range(head.start, head.end)
            if not any(word in broader_words for word in candidates[i])
        )

    return ConceptReading(
        query=str(query or ""),
        tokens=tokens,
        concept_id=concept.concept_id,
        mega_category_id=concept.mega_category_id,
        concept_words=tokens[head.start:head.end],
        feed_terms=tuple(normalize_understanding_text(concept.primary_english).split()),
        fallback_concept_id=fallback,
        fallback_unmatched=fallback_unmatched,
        filters=tuple(filters),
        filter_sources=sources,
        judgements=tuple(judgements),
        condition_request=condition.words,
        specs=tuple(specs),
        other_concepts=tuple(span.concept_id for span in spans if span is not head),
        non_retail=bool(non_retail_positions) and not spans,
        exact=head.cost < 0.5,
        spec_fields=spec_fields,
        head_language=head.kind,
    )


def suggest_product_names(query: str, *, limit: int = 3) -> tuple[str, ...]:
    """Product names a query PicWise could not act on might have meant, to ask about.

    Used only to offer "Did you mean ...?" links when nothing was understood. A
    suggestion is a question to the buyer, never an answer, so it may use corrections
    too uncertain to act on -- a short word with a letter missing ("dsk"), or a word
    equally close to two products, in which case both are offered. Everyday and
    non-retail words are never turned into suggestions.
    """
    tokens = tuple(normalize_understanding_text(query).split())
    if not tokens or understand_product_query(query).understood:
        return tuple()
    if any(token in _NON_RETAIL_WORDS for token in tokens):
        # "car insurance" is not a misspelled car product.
        return tuple()
    lexicon = _lexicon()
    candidates: list[dict[tuple[str, str], float]] = []
    for token in tokens:
        if (
            token in CONNECTIVE_WORDS
            or token in _COMMON_WORDS
            or token in _NON_RETAIL_WORDS
            or not any(ch.isalpha() for ch in token)
        ):
            candidates.append({})
            continue
        found: dict[tuple[str, str], float] = {}
        limit_for_token = max(1, _max_distance(len(token)))
        readings = (
            [("el", greek_key(token))]
            if is_greek_word(token)
            else [("en", english_key(token)), ("el", greeklish_key(token))]
        )
        for kind, key in readings:
            for word, distance in lexicon.fuzzy[kind].lookup(key, limit_for_token).items():
                identity = (kind, word)
                found[identity] = min(found.get(identity, 99.0), float(distance))
        candidates.append(found)
    spans = sorted(
        _find_spans(tokens, candidates, safe_only=False),
        key=lambda span: (span.cost, -(span.end - span.start), span.concept_id),
    )
    by_id = get_product_concepts_by_id()
    names: list[str] = []
    for span in spans:
        concept = by_id[span.concept_id]
        name = concept.greek[0] if span.kind == "el" and concept.greek else concept.primary_english
        if name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return tuple(names)


# --------------------------------------------------------------------------------------
# Annotating product text
# --------------------------------------------------------------------------------------


def _exact_candidates(token: str) -> dict[tuple[str, str], float]:
    identity = _word_identity(token)
    lexicon = _lexicon()
    return {identity: 0.0} if identity[1] in lexicon.fuzzy[identity[0]].words else {}


def _concepts_in_text(text: str) -> list[_Span]:
    """The concepts a piece of **feed** text names, by exact key and strong names only.

    A weak name ("cap", "ball", "screen") is left out here: in feed text it is almost
    always part of something else ("Lens Cap", "Mirror Ball", "Carplay Screen"), and
    answering "καπέλο" with lens caps is the one thing PicWise must never do. A query
    still reads those names, where the buyer means the product.
    """
    return list(_read_concepts_in_text(text))


# Reading a feed reads the same text many times over: a product's title by several
# rules, and a shop's category path and product type for each of its products.
@lru_cache(maxsize=131072)
def _read_concepts_in_text(text: str) -> tuple[_Span, ...]:
    tokens = tuple(normalize_understanding_text(text).split())
    if not tokens:
        return tuple()
    candidates = [_exact_candidates(token) for token in tokens]
    spans = [span for span in _find_spans(tokens, candidates) if not span.weak]
    spans = _choose_spans(spans)
    # The product in a title is named before what it is for: "charger for iphone".
    cut = next((i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS), len(tokens))
    return tuple([span for span in spans if span.start < cut] or spans)


_BREADCRUMB_SPLIT_RE = re.compile(r"\s*(?:>|\u2192|\|)\s*")

_PLURAL_AMPERSAND_RE = re.compile(r"(\w{2,}[^s\W]s)\s*&\s*", flags=re.IGNORECASE)

# A feed row can carry several categories -- the shop's own path, the network's
# taxonomy, a short category name -- and the search joins them with this. Each is its
# own breadcrumb.
CATEGORY_FIELD_SEPARATOR = " || "


def _category_heads(category: str, title: str) -> tuple[list[str], bool]:
    """The concepts a product's categories name, and whether they say "accessory of".

    Each category field is its own breadcrumb, and the first that says anything
    decides: the shop's own "Laundry > Tumble Dryers" over the network's "Bathroom
    Accessories", which a shop's export often fills with the nearest aisle it had.
    """
    for crumb in str(category or "").split(CATEGORY_FIELD_SEPARATOR.strip()):
        heads, accessory = _breadcrumb_heads(crumb, title)
        if heads or accessory:
            return heads, accessory
    return [], False


def _breadcrumb_heads(category: str, title: str) -> tuple[list[str], bool]:
    """The concepts one breadcrumb names, and whether it says "accessory of" instead.

    A category is usually a breadcrumb, from the widest aisle to the narrowest shelf:
    "Electronics > Cables > Monitor". The **first** shelf that names a product is the
    one to trust -- these are cables, kept under the monitors -- because a later step
    says what the thing is for as often as what it is. Any shelf that says accessories
    of a product decides for the whole crumb: "Cameras > Camera Accessories" is not a
    camera. A shelf must name its product as its head ("Surveillance Cameras"), not in
    passing ("Power banks and batteries"), and a shelf holding two kinds only counts
    when the product's own title says which of them it is. So does an aisle holding a
    kind together with something PicWise has no kind for, above a narrower shelf
    ("Jewellery & Watches > Body Jewellery"): its kind counts only when the title names
    it, and otherwise the narrower shelf decides. The narrowest shelf keeps its kind:
    "Skillets & Frying Pans" are cookware, though PicWise knows no skillet.
    """
    heads: list[str] = []
    segments = [segment for segment in _BREADCRUMB_SPLIT_RE.split(str(category or "")) if segment.strip()]
    for position, segment in enumerate(segments):
        # "Garden Planters & Stands" is a shelf of two things, planters and stands, not
        # planter stands: after a plural, "&" is a list, as "and" is. After a singular
        # it shares the noun that follows: "Camera & Optic Accessories" are accessories.
        head = _head_of_text(
            _PLURAL_AMPERSAND_RE.sub(r"\1 and ", segment),
            strict_tail=True,
            accessory_words=_CLASSIFICATION_ACCESSORY_WORDS,
        )
        if head is ACCESSORY_MARKER:
            return [], True
        if heads:
            # "Car & bike > Other car accessories": a shelf of accessories under a
            # product names things for it, not the product.
            words = normalize_understanding_text(segment).split()
            if (
                words
                and words[-1] in _CLASSIFICATION_ACCESSORY_WORDS
                and not _concepts_in_text(segment)
            ):
                return [], True
            continue
        shelf = {span.concept_id for span in _concepts_in_text(segment)}
        unrelated = [
            concept
            for concept in sorted(shelf)
            if not any(other != concept and _related(concept, other) for other in shelf)
        ]
        if len(unrelated) > 1:
            # A shelf of several kinds: "Fans & Heaters". Only the product's own title
            # can say which of them this one is.
            named_by_title = {span.concept_id for span in _concepts_in_text(title)}
            confirmed = [concept for concept in unrelated if concept in named_by_title]
            if len(confirmed) == 1:
                heads.append(confirmed[0])
            continue
        if head is not None:
            # None here means the shelf names a product only in passing ("Power banks
            # and batteries" holds both, and a coin cell is not a power bank).
            if (
                position < len(segments) - 1
                and _shelf_lists_an_unknown_kind(segment)
                and head not in {span.concept_id for span in _concepts_in_text(title)}
            ):
                # "Jewellery & Watches > Body Jewellery": the aisle holds jewellery as well
                # as watches, so its piercing aftercare oil is no watch. On the server's
                # feed of every Google-format shop (owner, 2026-10-25) 167,551 of 169,271
                # products read as watches had titles naming no watch.
                continue
            heads.append(head)
    return heads, False


# A shelf's list of what it holds: "Jewellery & Watches", "Handbags, Wallets & Cases".
# Not at "/", which joins two names for one thing on a shelf ("Laptops/Notebooks").
_SHELF_LIST_SPLIT_RE = re.compile(r"\s*(?:&|,|\band\b|\bκαι\b)\s*", flags=re.IGNORECASE)


def _shelf_lists_an_unknown_kind(segment: str) -> bool:
    """Does this shelf list, besides what it names, something PicWise has no kind for?
    "Jewellery & Watches" lists jewellery; "Fans & Heaters" lists two known kinds, and
    "Tea & Coffee Makers" names one product."""
    parts = [part for part in _SHELF_LIST_SPLIT_RE.split(segment) if part.strip()]
    return len(parts) > 1 and any(
        _head_of_text(part, strict_tail=True) is None and _type_is_informative(part) for part in parts
    )


@lru_cache(maxsize=65536)
def product_text_names_concept(text: str, concept_id: str) -> bool:
    """Does this feed text name that kind of product as the product it is?

    The same reading `annotate_product_concepts` uses, for callers that have a concept
    in hand and only need to know whether a product's own words name it ("TV Show
    Theme Blanket" does not name a television).
    """
    return _head_of_text(text, strict_tail=True) == concept_id


@lru_cache(maxsize=262144)
def annotate_product_concepts(product_type: str, category: str, title: str) -> frozenset[str]:
    """Which concepts one feed product is an instance of, including broader ones.

    The feed's own product type is the authority; the category is used when there is no
    type, and the title only when neither names a concept. The title may still refine
    the type into a narrower concept of the same kind: a "Vacuum Cleaners" product
    titled "Robot Vacuum Cleaner" is also a robot vacuum.

    Strict, by the owner's rule of 2026-10-16 that "laptop" must show laptops. Price
    order puts the cheapest products first, and the cheapest products in any kind are
    its accessories and look-alikes, so a doubtful reading is a wrong card at the top
    of the page. These make a product's kind doubtful rather than guessed
    (`UNCERTAIN_MARKER`): a feed type that names no kind PicWise knows ("Temperature &
    Humidity Sensors" is not a monitor, whatever its title says), or lists one ("...
    Sensors & Monitors") while the title names none of the known ones; a title whose
    own lead names another kind than the classification ("3 Seater Sofa" filed under
    "Chairs > Chaises", a car booster seat on the "Changing Tables" shelf); and a title
    that names a kind only in passing ("Toner Collection Unit" filed under "Toner
    Cartridges", "Wall-Mounted Coat Rack: 4 Hooks, Rail & Shelf"). A lead that ends in
    an accessory noun is that accessory ("Tab 11\" Folio Case" filed under "Tablets").
    A doubtful product is still found by its words, never by its kind. Pet and camping
    products carry a context marker (`PET_MARKER`, `CAMPING_MARKER`) that the search
    reads against the buyer's words: a dog bed answers "dog bed", not "bed".
    """
    return _with_context_markers(_annotate_kinds(product_type, category, title), category, title)


def kinds_before_the_aisle_rule(product_type: str, category: str, title: str) -> frozenset[str]:
    """The kinds `annotate_product_concepts` gave before a title's kind was read against
    its aisle's departments (`_aisle_may_hold`, owner, 2026-10-25), so the build's note
    can say which products that rule made doubtful. Measured only: no search reads it."""
    return _with_context_markers(
        _annotate_kinds(product_type, category, title, aisle_rule=False), category, title
    )


def _with_context_markers(kinds: frozenset[str], category: str, title: str) -> frozenset[str]:
    if not kinds or kinds & {ACCESSORY_MARKER, UNCERTAIN_MARKER}:
        return kinds
    return kinds | _product_context_markers(category, title)


def _annotate_kinds(product_type: str, category: str, title: str, *, aisle_rule: bool = True) -> frozenset[str]:
    # What follows a spaced "+" in a type comes with the product, as in a title:
    # Pro-Camera's "... > Canon EOS R5 + EF-EOS R mount adapter" is the camera (owner's
    # file, 2026-10-23: 63 cameras were read as adapters).
    product_type = _TYPE_WITH_RE.split(str(product_type or ""), maxsplit=1)[0]
    # The whole type first: "Mobile Phone Screen & Back Protectors" are protectors, and
    # "Laptop Docks & Port Replicators" docks, which splitting at "&" would hide.
    if str(product_type or "").strip() and _head_of_text(
        product_type, accessory_words=_CLASSIFICATION_ACCESSORY_WORDS
    ) is ACCESSORY_MARKER:
        return frozenset({ACCESSORY_MARKER})
    bases: list[str] = []
    # A type whose last words name a kind is that kind -- "Mobile Phone Screen & Back
    # Protectors" -- unless it is a list of one-word kinds ("Fans & Heaters"), read
    # part by part below.
    tail, tail_size = _tail_concept_and_size(str(product_type or ""))
    if tail is not None and (tail_size > 1 or not _TYPE_LIST_SPLIT_RE.search(product_type)):
        bases.append(tail)
    # A feed type can list several kinds: "Fans & Heaters", "Cases, Covers".
    unknown_part = False
    for part in _TYPE_LIST_SPLIT_RE.split(str(product_type or "")) if not bases else ():
        head = _head_of_text(part, accessory_words=_CLASSIFICATION_ACCESSORY_WORDS)
        if head is ACCESSORY_MARKER:
            return frozenset({ACCESSORY_MARKER})
        if head is not None:
            bases.append(head)
        elif _type_is_informative(part):
            unknown_part = True
    if bases and unknown_part:
        # "Industrial Environmental Sensors & Monitors", "Power Adapters & Inverters":
        # the list also holds a kind PicWise does not know, so only a title naming one
        # of the known kinds says the product is that kind.
        named = set(_kinds_named_before_purpose(title))
        confirmed = [
            base for base in bases if any(kind == base or _related(kind, base) for kind in named)
        ]
        if len(confirmed) != 1:
            return frozenset({UNCERTAIN_MARKER})
        bases = confirmed
    if bases and all(_type_names_kind_only_before_another_product(product_type, base) for base in bases):
        # "Lenses > Canon > Canon DSLR Lenses > ...": the type names the kind only to say
        # which other product it is, so a category that says otherwise decides -- an
        # accessory shelf ("Camera Lenses"), or another kind (owner's file, 2026-10-23:
        # 43 lenses of Pro-Camera were cameras). A category naming nothing, or the same
        # kind, leaves the type its kind.
        category_heads, category_says_accessory = _category_heads(category, title)
        if category_says_accessory or (
            category_heads
            and not any(head == base or _related(head, base) for head in category_heads for base in bases)
        ):
            bases = []
    from_category = not bases
    if not bases:
        bases, category_says_accessory = _category_heads(category, title)
        if category_says_accessory:
            return frozenset({ACCESSORY_MARKER})
    title_spans = _concepts_in_text(title)
    if bases and title_spans:
        # "Smartphone USB-C" on a microphone whose title says "Microphone | Used for:
        # ... Smartphone": the type names what the product plugs into. When the title
        # names another product before any purpose word, and the category agrees with
        # the title rather than the type, the type was a compatibility label.
        # Read without the strict tail: the category agreeing with the title is the
        # corroboration that rule asks for.
        title_head = _head_of_text(title)
        if (
            title_head is not None
            and title_head is not ACCESSORY_MARKER
            and not any(_related(title_head, base) for base in bases)
            and not any(span.concept_id in bases for span in title_spans)
        ):
            category_heads, _accessory = _category_heads(category, title)
            if title_head in category_heads:
                bases = [title_head]
    if not bases:
        if _type_is_informative(product_type):
            # The type is the authority, and it names no kind PicWise knows. Reading the
            # kind off the title instead turned "Temperature & Humidity Sensors" into
            # monitors and "Computer Cooling Systems" into fans. The title is still
            # heard when the type shares a real word with what it names: "USB Flash
            # Drives" and a title saying "USB flash drive".
            lead_head = _head_of_text(_title_lead(title), first_phrase=True)
            if (
                lead_head is not None
                and lead_head is not ACCESSORY_MARKER
                and _type_supports_concept(product_type, lead_head)
                and not _type_ends_in_another_products_word(product_type, lead_head)
            ):
                return frozenset(broader_concepts(lead_head))
            return frozenset({UNCERTAIN_MARKER})
        if not title_spans:
            return frozenset()
        head = _title_fallback_head(title, category) if aisle_rule else _title_named_head(title, category)
        if head in (ACCESSORY_MARKER, UNCERTAIN_MARKER):
            return frozenset({head})
        if head is None:
            return frozenset()
        bases = [head]
    else:
        verdict = _title_lead_verdict(title, bases, trust_title=from_category, category=category)
        if verdict in (ACCESSORY_MARKER, UNCERTAIN_MARKER):
            return frozenset({verdict})
        if verdict is not None:
            bases = [verdict]
        if len(bases) > 1:
            # A shelf of several kinds ("Fans & Heaters"): the title says which.
            lead_head = _head_of_text(_title_lead(title), first_phrase=True)
            if lead_head in bases:
                bases = [lead_head]
    concepts: set[str] = set()
    for base in bases:
        concepts.update(broader_concepts(base))
    for span in title_spans:
        chain = broader_concepts(span.concept_id)
        if any(base in chain[1:] for base in bases):
            concepts.update(chain)
    if "mobile_phone" in concepts:
        # Feeds file smartphones and basic phones alike under "Mobile Phones"; the
        # title says which (`_title_says_smartphone`).
        if _title_says_smartphone(title):
            concepts.discard("mobile_phone")
            concepts.update(broader_concepts("smartphone"))
        else:
            concepts.discard("smartphone")
    return frozenset(concepts)


# The owner's rule of 2026-10-16: "smartphone" shows smartphones, and "mobile phone",
# "κινητό" or "phone" the other mobile phones -- basic, flip and big-button phones.
# Feeds file both under "Mobile Phones": the first real feed held its smartphones
# there, the third its basic phones, "Doro Leva E10 2.4\" Mobile Phone". So a phone
# is a smartphone when its title says so, or names what only a smartphone has: a
# smartphone system or 5G, 16 GB or more of storage, or a screen of 4 inches or more.
_PHONE_KINDS = frozenset({"smartphone", "mobile_phone"})
_SMARTPHONE_WORDS = frozenset({"android", "ios", "iphone", "5g"})
_STORAGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(gb|tb)\b", flags=re.IGNORECASE)
_SCREEN_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:\"|''|\u201d|inch(?:es)?\b|in\b)", flags=re.IGNORECASE)


def _title_says_smartphone(title: str) -> bool:
    text = str(title or "")
    if set(normalize_understanding_text(text).split()) & _SMARTPHONE_WORDS:
        return True
    if any(span.concept_id == "smartphone" for span in _concepts_in_text(text)):
        return True
    for value, unit in _STORAGE_RE.findall(text):
        if unit.lower() == "tb" or float(value.replace(",", ".")) >= 16:
            return True
    return any(4.0 <= float(value.replace(",", ".")) <= 8.0 for value in _SCREEN_RE.findall(text))


# Products that belong with another product rather than being it: "Washing Machine
# Accessories", "Ανταλλακτικά για πλυντήριο", "Coffee Machine Descaler". Annotating them
# as the main product would answer "πλυντήριο" with hoses and filters.
ACCESSORY_MARKER = "__accessory__"
_ACCESSORY_WORDS = frozenset(
    """
    accessories accessory parts part spare spares replacement replacements refill refills
    filter filters cover covers stand stands mount mounts holder holders strap straps
    remote descaler descalers cleaner cleaners hose hoses belt belts blade blades
    nozzle nozzles brush brushes adapter adapters kit kits pads attachment attachments
    shield shields
    αξεσουαρ ανταλλακτικα ανταλλακτικο εξαρτηματα εξαρτημα φιλτρο φιλτρα σακουλες σακουλα
    καλυμμα καλυμματα βαση βασεις τηλεχειριστηριο λουρακι καθαριστικο αφαλατικο λαστιχο
    """.split()
)


# Words that turn the product name before them into a description of something else:
# "table runner", "cable ties", "mirror ball", "ring light", "shoe restore kit". Read
# off a real feed, where each of these answered a search with the wrong kind of
# product. Only English text puts the modifier first, so only English text is read
# this way.
_MODIFIER_TAIL_WORDS = frozenset(
    """
    runner runners mat mats decor cloth cloths ties tie clip clips sleeving duct ducts
    ball balls light lights restore stopper stoppers component components
    clock clocks football tennis
    """.split()
)


# A feed's own classification names its product by the last word: "Tablet Cases" are
# cases, "UPS Batteries" batteries, "Fan Speed Controllers" controllers, "Desk
# Trays/Organizers" trays, "Printer Labels" and "Printer Drums" supplies, "Chair Back
# Supports" supports. Measured on the third real feed (2026-10-16), where each of
# these answered a search for the main product. A title cannot be read this way -- a
# phone's title lists "5000mAh battery" after the name, a console's "+ controller" --
# so these words count only in a product type or a category shelf.
_CLASSIFICATION_ACCESSORY_WORDS = _ACCESSORY_WORDS | frozenset(
    """
    case cases casing casings sleeve sleeves folio folios enclosure enclosures
    protector protectors tray trays organiser organisers organizer organizers
    drawer drawers controller controllers collector collectors ribbon ribbons
    sensor sensors cabinet cabinets cart carts trolley trolleys dock docks docking
    replicator replicators charger chargers cushion cushions shield shields
    battery batteries cartridge cartridges label labels drum drums cleaning
    upgrade upgrades support supports panel panels bracket brackets
    """.split()
)


# A product whose kind cannot be read with confidence. It is never a member of a
# concept, and is not offered to the "names the concept in its own words" fallback
# either, which would let the same doubtful text back in.
UNCERTAIN_MARKER = "__uncertain_kind__"

# Context a product's kind carries: a dog bed is a bed for a dog, a camping cot bed is
# a bed for a tent. The search answers "bed" without them and "dog bed" with them.
PET_MARKER = "__pet__"
CAMPING_MARKER = "__camping__"

_PET_WORDS = frozenset(
    normalize_understanding_text(word)
    for word in """
    pet pets dog dogs puppy puppies cat cats kitten kittens rabbit rabbits hamster
    hamsters guinea bird birds parrot parrots
    κατοικίδιο κατοικίδια σκύλος σκύλου σκύλους σκυλί σκυλιά σκυλιού κουτάβι κουτάβια
    γάτα γάτας γάτες γατάκι γατάκια κουνέλι κουνέλια χάμστερ
    """.split()
)
# The aisle words a category uses for pet products ("Animals & Pet Supplies", "Pets").
_PET_AISLE_WORDS = frozenset({"pet", "pets", "animal", "animals", "κατοικιδια"})
_CAMPING_WORDS = frozenset(
    normalize_understanding_text(word)
    for word in "camping camp campsite κάμπινγκ κατασκήνωση".split()
)

# Where a title stops naming the product and starts describing it: "Lenovo ThinkPad
# L13 13.3\" Laptop (21LB...) - Intel ..., 512GB SSD". Read past it and an English title
# names every spec as a product: the last product word of that title is "SSD". A "+"
# lists what comes in the box: "USB-C Headset +USB-C/A Adapter" is a headset. Between
# two digits it is a spec: "4+1 Burner Gas BBQ Grill".
_TITLE_LEAD_RE = re.compile(r"[(,;:]|(?<!\d)\+|\+(?!\d)|\s[-–—|]\s")
# A bar between the parts of a title, and a spaced "+" in a feed's type: what follows
# it comes with the product ("... > Canon EOS R5 + EF-EOS R mount adapter").
_TITLE_BAR_RE = re.compile(r"\s\|\s")
_TYPE_WITH_RE = re.compile(r"\s\+\s")

_UNINFORMATIVE_TYPES = frozenset(
    {
        "", "not categorized", "uncategorized", "other", "others", "general", "misc",
        "miscellaneous", "n/a", "na", "none", "default", "product", "products", "all",
    }
)


# Department words: a type made only of these ("Home", "Home & Garden") says where a
# product is sold, not what it is, and the title is heard.
_DEPARTMENT_WORDS = frozenset(
    """
    home house household garden kitchen electronics electronic computers computer
    furniture toys sports sport outdoor outdoors office clothing fashion beauty health
    baby kids pets automotive car tools diy gifts gift sale clearance new accessories
    living
    """.split()
)
# A type is a kind label -- the merchant saying what the product is -- when it ends in
# a plural ("Temperature & Humidity Sensors", "Servers") or in a noun used for a whole
# kind ("Networking Software", "Photo Paper"). A device name ("iPhone XR") is a
# compatibility label instead, and the title still says what the product is.
_KIND_LABEL_WORDS = frozenset(
    """
    software hardware equipment clothing paper furniture lighting storage bedding
    luggage jewellery jewelry footwear stationery packaging seating cookware tableware
    glassware apparel workwear sportswear nightwear underwear media film
    """.split()
)


def _type_is_informative(product_type: str) -> bool:
    words = normalize_understanding_text(product_type).split()
    if " ".join(str(product_type or "").lower().split()) in _UNINFORMATIVE_TYPES or not words:
        return False
    if all(word in _DEPARTMENT_WORDS or word == "and" for word in words):
        return False
    last = words[-1]
    return last in _KIND_LABEL_WORDS or (len(last) > 3 and last.endswith("s") and not last.endswith("ss"))


_WITH_ABBREVIATION_RE = re.compile(r"(?<![\w/])[wW]/")


def _title_lead(title: str) -> str:
    # "laptop dock/port replicator", "desk tray/organizer": a slash in a title joins
    # two names of the same thing, so it is read as a space -- except in "w/", which
    # is "with".
    text = _WITH_ABBREVIATION_RE.sub(" with ", str(title or ""))
    return _TITLE_LEAD_RE.split(text, maxsplit=1)[0].replace("/", " ")


# Words that, right after the classified kind in a title, name a different product:
# "Toner Collection Unit", "Standing Desk Converter", "Tablet Cling", "Monitor Arm".
# A model name after the kind ("iPad Air", "Galaxy A17") is not one of them, which is
# why this is a list and not every unreadable word.
_OTHER_PRODUCT_TAIL_WORDS = frozenset(
    """
    collection converter converters cling arm arms riser risers extension extensions
    extender extenders lock locks bracket brackets hub hubs splitter splitters skin
    skins decal decals sticker stickers tray trays organiser organisers organizer
    organizers drawer drawers shield shields cushion cushions protector protectors
    case cases casing sleeve sleeves folio charger chargers cable cables
    battery batteries controller controllers lamp lamps hoop hoops net nets aid aids
    rail rails companion companions guard guards
    """.split()
)


@lru_cache(maxsize=1024)
def _own_name_words(concept_id: str) -> frozenset[str]:
    concept = get_product_concepts_by_id().get(concept_id)
    if concept is None:
        return frozenset()
    names = concept.english + concept.greek + concept.weak
    return frozenset(word for name in names for word in normalize_understanding_text(name).split())


def _siblings(left: str, right: str) -> bool:
    """Two kinds of one broader kind: a laptop bag and a backpack are both bags."""
    return bool(set(broader_concepts(left)[1:]) & set(broader_concepts(right)[1:]))


@lru_cache(maxsize=4096)
def _named_as_kind_of(narrow: str, wide: str) -> bool:
    """Is one kind named as a kind of the other: a "play tent" is a tent by its name, a
    "game table" a table, an "IP phone" a phone. A title calling a play tent "Tent"
    agrees with its "Play Tents" shelf; it does not contradict it."""
    by_id = get_product_concepts_by_id()
    narrow_concept, wide_concept = by_id.get(narrow), by_id.get(wide)
    if narrow_concept is None or wide_concept is None:
        return False
    # By its main name only: a "fridge freezer" is also sold as a fridge, and a "Mini
    # Freezer" on the fridges shelf is still a freezer.
    name = normalize_understanding_text(narrow_concept.primary_english)
    return any(
        name.endswith(" " + normalize_understanding_text(wide_name))
        for wide_name in wide_concept.english
        if wide_name
    )


def _same_department(left: str, right: str) -> bool:
    by_id = get_product_concepts_by_id()
    a, b = by_id.get(left), by_id.get(right)
    return a is not None and b is not None and a.mega_category_id == b.mega_category_id


def _singular(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


# Words too general to say that a feed type and a product name mean the same thing.
_GENERIC_TYPE_WORDS = frozenset(
    """
    computer computers pc pcs electronic electronics accessory accessories home office
    digital smart portable wireless usb system systems device devices equipment unit
    units product products item items supply supplies other
    """.split()
)


def _type_supports_concept(product_type: str, concept_id: str) -> bool:
    """Does an unrecognised feed type share a real word with the kind's own names?

    "USB Flash Drives" supports a title saying "USB flash drive"; "Temperature &
    Humidity Sensors" does not support a title saying "Monitor".
    """
    type_words = {
        _singular(word)
        for word in normalize_understanding_text(product_type).split()
        if word not in _GENERIC_TYPE_WORDS
    }
    if not type_words:
        return False
    concept = get_product_concepts_by_id().get(concept_id)
    if concept is None:
        return False
    name_words = {
        _singular(word)
        for name in concept.english
        for word in normalize_understanding_text(name).split()
        if word not in _GENERIC_TYPE_WORDS
    }
    # An accessory word in common says nothing: "Equipment Cases" and a title saying
    # "Protector Case" are not phone cases.
    accessory = {_singular(word) for word in _CLASSIFICATION_ACCESSORY_WORDS}
    return bool((type_words & name_words) - accessory)


def _type_ends_in_another_products_word(product_type: str, concept_id: str) -> bool:
    """Does the type's own noun name an accessory the kind is not? "Storage Drive
    Enclosures" holds enclosures, whatever SSD their titles name first."""
    words = normalize_understanding_text(product_type).split()
    if not words or words[-1] not in _CLASSIFICATION_ACCESSORY_WORDS:
        return False
    return _singular(words[-1]) not in {_singular(word) for word in _own_name_words(concept_id)}


def _tail_concept(text: str) -> str | None:
    """The kind a classification's last words name exactly, if any: "Mobile Phone
    Cases" ends in "phone cases", a phone case, where reading from its first words
    finds a mobile phone."""
    return _tail_concept_and_size(text)[0]


def _tail_concept_and_size(text: str) -> tuple[str | None, int]:
    tokens = tuple(normalize_understanding_text(text).split())
    if any(token in _PURPOSE_WORDS for token in tokens):
        # "Accessories for Laptops", "Spare Parts for Washing Machines": what follows
        # the purpose word is what the product is for.
        return None, 0
    for size in (3, 2, 1):
        if len(tokens) < size:
            continue
        tail = tokens[-size:]
        spans = [
            span
            for span in _find_spans(tail, [_exact_candidates(token) for token in tail])
            if not span.weak and span.start == 0 and span.end == size
        ]
        if len({span.concept_id for span in spans}) == 1:
            return spans[0].concept_id, size
    return None, 0


# Kinds that are aisles as much as kinds: a toy can be a balance bike or a kids' scooter,
# garden furniture a rattan sofa set or a bistro table. A shelf of one of these holds
# products another department also sells, and the shelf decides.
_AISLE_KINDS = frozenset({"toy", "garden_furniture"})


def _title_lead_verdict(
    title: str, bases: list[str], *, trust_title: bool = False, category: str = ""
) -> str | None:
    """Does the title's own lead contradict the kind the feed classified it as?

    None when it agrees or says nothing; ACCESSORY_MARKER when the lead reads as an
    accessory, or ends in an accessory noun without naming the classified kind ("Tab
    11\" Folio Case" filed under tablets); UNCERTAIN_MARKER when it names another kind
    of the same department, or names the classified kind only to say what it is for
    ("Toner Collection Unit" filed under toner cartridges). With `trust_title` -- the
    kind came from a category shelf, where misfiling happens ("3 Seater Sofa" on the
    chairs shelf) -- a same-department kind named by the title is returned instead, and
    is the product's kind, and a kind of another department makes it doubtful unless
    the shelf is an aisle (`_AISLE_KINDS`). A product type is precise and its titles
    name the device they fit ("... Car Charger Smartphone"), so a type is never
    overruled that way.
    """
    lead = _title_lead(title)
    # Only what the title names before "with" or "for" can contradict the feed: "Rattan
    # Bistro Set ... with Wicker Chairs" is a garden set, "... with Headset" a headset.
    lead_tokens = normalize_understanding_text(lead).split()
    cut = next((i for i, token in enumerate(lead_tokens) if token in _PURPOSE_WORDS), len(lead_tokens))
    lead = " ".join(lead_tokens[:cut])
    spans = _concepts_in_text(lead)
    names_a_base = any(
        span.concept_id in bases or any(_related(span.concept_id, base) for base in bases)
        for span in spans
    )
    if not names_a_base and _lead_ends_in_accessory(title, bases):
        return ACCESSORY_MARKER
    if not spans:
        # The lead names no kind PicWise knows. A shelf's kind holds unless the lead
        # ends in another product's noun: a lens or a pair of propellers on a camera
        # shelf. A product type keeps its authority, as below.
        if (
            trust_title
            and not all(base in _AISLE_KINDS for base in bases)
            and _lead_names_another_product(title, bases, category)
        ):
            return UNCERTAIN_MARKER
        return None
    # The first product a title names is the product; English titles go on to list
    # parts and specs ("... Laptop Intel Celeron 64GB SSD").
    head = _head_of_text(lead, first_phrase=True)
    if head is ACCESSORY_MARKER:
        return ACCESSORY_MARKER
    if head is None:
        return None

    def is_base(concept_id: str) -> bool:
        return any(
            concept_id == base
            or _related(concept_id, base)
            or _siblings(concept_id, base)
            or _named_as_kind_of(base, concept_id)
            # A "Mobile Phones" type with a title saying "Smartphone": the title says
            # which phone it is, it does not contradict the type.
            or {concept_id, base} == _PHONE_KINDS
            for base in bases
        )

    # On a category shelf, a kind named inside the head's own phrase only describes it:
    # "Kids Desk Chairs" on the kids' desks shelf are chairs. A product type is read
    # the other way, because its titles put the type first and a feature after it
    # ("keyboard Mouse included").
    phrase = [spans[0]]
    for span in spans[1:]:
        if span.start != phrase[-1].end:
            break
        phrase.append(span)
    modifiers = phrase[:-1] if trust_title else []
    named_elsewhere = any(span.concept_id in bases for span in spans if span not in modifiers)
    if not is_base(head) and not named_elsewhere:
        # Another kind from the same department is a misfiled product: a sofa on the
        # chairs shelf. Another department is context, not a contradiction: a kids'
        # scooter on the toy shelf is a toy, a rattan sofa set is garden furniture.
        if any(_same_department(head, base) for base in bases):
            if trust_title:
                # The other kind's name may only describe the noun the lead ends with:
                # a "Dressing Table Stool" on the stools shelf is a stool, the shelf's
                # own product; on a shelf that does not name stools it is doubtful.
                noun = _noun_after_kind(title, [span for span in spans if span.concept_id == head])
                if noun is not None and _is_product_noun_of_another_kind(*noun, [head]):
                    shelf_holds_it = not _is_product_noun_of_another_kind(*noun, [head], category)
                    return None if shelf_holds_it else UNCERTAIN_MARKER
            return head if trust_title else UNCERTAIN_MARKER
        if trust_title and not all(base in _AISLE_KINDS for base in bases):
            # A shelf of one kind holding a product of another department is a shop's
            # misfiling, not context: a car booster seat on the "Changing Tables" shelf
            # is not a table, and PicWise cannot tell which of the two is wrong.
            return UNCERTAIN_MARKER
        return None
    tokens = tuple(normalize_understanding_text(lead).split())
    for span in spans:
        if is_base(span.concept_id) and span.end < len(tokens):
            following = tokens[span.end]
            # "Chandelier Lamp" names the same kind twice.
            if following in _OTHER_PRODUCT_TAIL_WORDS and following not in _own_name_words(span.concept_id):
                return UNCERTAIN_MARKER
            # The kind's name followed by the noun the lead ends with names that other
            # product: "Dressing Table Stool" is a stool.
            if span.concept_id not in _AISLE_KINDS and _kind_named_before_another_product(
                title, span, category
            ):
                return UNCERTAIN_MARKER
    return None


def _names_another_product_after(tokens: tuple[str, ...], end: int) -> bool:
    """Do the words right after a product name name another product?

    "Sofa Arm Tray", "Basketball Hoop": one plain word may stand between. A spec stops
    the reading -- "Smartphone 5000mAh Battery" lists the phone's battery. Only for a
    title nothing else classifies: a classified title is read word by word, because
    its second word is often the shelf ("computer cooling system Computer case Fan").
    """
    for index in (end, end + 1):
        if index >= len(tokens) or any(ch.isdigit() for ch in tokens[index]):
            return False
        if tokens[index] in _OTHER_PRODUCT_TAIL_WORDS:
            return True
    return False


def _title_fallback_head(title: str, category: str) -> str | None:
    """The kind a title names when neither its type nor its category names one
    (`_title_named_head`), unless the category is an aisle of Google's whose shelves name
    no kind of that department: "Chocolate Mice" under "Food, Beverages & Tobacco" are no
    mice, a "Circular Barbell" under "Clothing & Accessories > Jewellery & Watches" is a
    piercing, and the "Colleen Hoover" of a book under "Media > Books" no vacuum cleaner
    (owner, 2026-10-25: «προχώρα στο επόμενο λάθος»). Such a kind is doubtful: the product
    is still found by its words, never by its kind. A category that is no aisle of
    Google's leaves the title to decide, as before.
    """
    head = _title_named_head(title, category)
    if head not in (None, ACCESSORY_MARKER, UNCERTAIN_MARKER) and not _aisle_may_hold(category, head):
        return UNCERTAIN_MARKER
    return head


def _title_named_head(title: str, category: str) -> str | None:
    """The kind a title names when neither its type nor its category names one.

    The lead is read first, and read strictly: a lead that names a kind only to
    describe something else -- "Wall-Mounted Coat Rack: 4 Hooks, Rail & Shelf", "Sofa
    Arm Tray" -- makes the kind doubtful, and the rest of the title is not searched for
    a better one. A lead that names nothing lets the rest of the title speak ("Brand
    X200, Wireless Gaming Mouse"), unless the category names a kind PicWise does not
    know and shares no word with it: "Garden Sheds" and "..., Waterproof Bike Tent".
    """
    lead_tokens = normalize_understanding_text(_title_lead(title)).split()
    cut = next((i for i, token in enumerate(lead_tokens) if token in _PURPOSE_WORDS), len(lead_tokens))
    lead = " ".join(lead_tokens[:cut])
    if _concepts_in_text(lead):
        head = _head_of_text(lead, first_phrase=True, strict_tail=True)
        if head is ACCESSORY_MARKER:
            return ACCESSORY_MARKER
        if head is None:
            # Named in passing -- unless the title names the same kind plainly further
            # on: "Rattan Pendant Light Handwoven Rustic Farmhouse Ceiling Light".
            loose = _head_of_text(lead, first_phrase=True)
            if loose is None or loose is ACCESSORY_MARKER or _head_of_text(title, strict_tail=True) != loose:
                return UNCERTAIN_MARKER
            head = loose
        if _lead_names_another_product_after(title, head):
            return UNCERTAIN_MARKER
        return head
    head = _head_of_text(title, strict_tail=True)
    if head is None or head is ACCESSORY_MARKER:
        return head
    shelf = _narrowest_shelf(category)
    if shelf and _type_is_informative(shelf) and not _type_supports_concept(shelf, head):
        return UNCERTAIN_MARKER
    return head


# Google's British names for its aisles where they differ from the US file the code
# reads: the shops of the server's feed file their jewellery under "Clothing & Accessories
# > Jewellery & Watches" (owner, 2026-10-25), Google's US file under "Apparel &
# Accessories > Jewelry".
_BRITISH_AISLE_NAMES = {
    "clothing & accessories": "apparel & accessories",
    "jewellery & watches": "jewelry",
    "jewellery": "jewelry",
    "jewellery cleaning & care": "jewelry cleaning & care",
    "healthcare": "health care",
}


def _in_the_singular(text: str) -> str:
    return " ".join(_singular(word) for word in str(text or "").lower().split())


@lru_cache(maxsize=1)
def _aisle_departments() -> dict[str, frozenset[str]]:
    """Per aisle of Google's taxonomy, its top ("media") and its first two levels
    ("media > books"), the departments (`mega_category_id`) of the kinds its shelves name,
    each shelf read as it is and in the singular: the lexicon knows a "massager" but no
    "massagers", so "Electric Massagers" says nothing as it is. Empty when the taxonomy
    file is not there, and then no aisle is read."""
    try:
        lines = _TAXONOMY_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    by_id = get_product_concepts_by_id()
    departments: dict[str, set[str]] = {}
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        names = [" ".join(name.lower().split()) for name in line.split(">")]
        heads, _accessory = _category_heads(line.lower(), "")
        singular_heads, _accessory = _category_heads(" > ".join(_in_the_singular(name) for name in names), "")
        found = {by_id[head].mega_category_id for head in (*heads, *singular_heads) if head in by_id}
        for aisle in {names[0], " > ".join(names[:2])}:
            departments.setdefault(aisle, set()).update(found)
    return {aisle: frozenset(found) for aisle, found in departments.items()}


def _aisle_may_hold(category: str, concept_id: str) -> bool:
    """Does the aisle a category starts with hold, on some shelf of Google's, a kind of
    this kind's department, or of a broader kind's: a smartwatch is a watch too, so an
    aisle of watches may hold one. The first category field that is an aisle of
    Google's is read at its first two levels, or at its top when Google's shelves there
    name no kind at all ("Furniture > Furniture Sets" holds sofas the lexicon cannot
    read off its shelves); an aisle whose own name names the kind holds it ("Toys &
    Games", a toy). True when no field is an aisle of Google's."""
    by_id = get_product_concepts_by_id()
    aisles = _aisle_departments()
    if concept_id not in by_id or not aisles:
        return True
    kinds = set(broader_concepts(concept_id))
    departments = {by_id[kind].mega_category_id for kind in kinds if kind in by_id}
    for crumb in str(category or "").split(CATEGORY_FIELD_SEPARATOR.strip()):
        names = [
            _BRITISH_AISLE_NAMES.get(name, name)
            for name in (" ".join(segment.lower().split()) for segment in _BREADCRUMB_SPLIT_RE.split(crumb))
            if name
        ]
        if not names or names[0] not in aisles:
            continue
        if any(span.concept_id in kinds for name in names[:2] for span in _concepts_in_text(_in_the_singular(name))):
            return True
        two = " > ".join(names[:2])
        held = aisles.get(two) if len(names) > 1 and aisles.get(two) else aisles[names[0]]
        return bool(departments & held)
    return True


def _narrowest_shelf(category: str) -> str:
    """The last shelf of the first category field that has one."""
    for crumb in str(category or "").split(CATEGORY_FIELD_SEPARATOR.strip()):
        segments = [segment for segment in _BREADCRUMB_SPLIT_RE.split(crumb) if segment.strip()]
        if segments:
            return segments[-1]
    return ""


def _narrowest_shelves(category: str) -> str:
    """The last shelf of every category field, joined."""
    shelves = []
    for crumb in str(category or "").split(CATEGORY_FIELD_SEPARATOR.strip()):
        segments = [segment for segment in _BREADCRUMB_SPLIT_RE.split(crumb) if segment.strip()]
        if segments:
            shelves.append(segments[-1])
    return " ".join(shelves)


# The noun an English title ends its lead with is what the product is: "Lenovo Tab 11\"
# Folio Case" is a case, "Safety Bed Rail" a rail, "Sandbox Cover" a cover, "Trampoline
# Anchor Kit" anchors. Measured on the third feed, where each of these was the cheapest
# product of a kind (tablet, bed, toy) that the feed's type or shelf had given it. Read
# only when the lead does not name the classified kind itself: "Apple Watch Series 11
# ... Aluminium Case" is a watch, and a lead that names the kind is read word by word.
# Left out: "tray" (a processor's packaging), "adapter" (a multiport adapter is sold as
# a dock) and "shield" (an "eco-shield" is a screen protector).
_LEAD_ACCESSORY_NOUNS = frozenset(
    """
    cover covers case cases casing casings folio folios sleeve sleeves protector
    protectors skin skins decal decals sticker stickers stand stands mount mounts holder
    holders bracket brackets strap straps rail rails cushion cushions organiser
    organisers organizer organizers anchor anchors refill refills replacement
    replacements spare spares filter filters nozzle nozzles brush brushes attachment
    attachments companion companions guard guards accessory accessories part parts
    cleaning repair maintenance pad pads
    """.split()
)
# Words that name a group of the noun before them: "Anchor Kit", "Cleaning Kit".
_GROUP_NOUNS = frozenset("kit kits bundle bundles".split())


# The nouns that name products: the last word of every shelf in Google's product
# taxonomy ("Camera Lenses", "Safes", "Stools", "Plates", "Knee Pads"). A title whose
# lead ends in one of them names that product. On the live feed of 2026-10-22 a shelf
# gave a kind to titles that named another product in words PicWise had no kind for:
# "Canon EF 50mm f/1.8 STM Lens" and "DJI Flip Propellers (Pair)" on camera shelves, a
# "Battery Charging Safe" on a chargers shelf, a keyboard "Plate" on the keyboards shelf
# (owner, 2026-10-22: work the rule that reads the kinds).
_TAXONOMY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "taxonomy_sources" / "google" / "taxonomy.en-US.txt"
)
# Shelf words that say what a product is for, where it is sold or how it comes rather
# than what it is ("Speaker System", "Fireplace Suite", "Steam Cleaner Machine"), and
# words that end a title as a brand, a colour or a material more often than as a
# product ("Accent Chair Fabric", "Cushion in ... Cotton Linen"). A "Body" is the
# product itself, sold bare: "Canon EOS R6 Mark II Mirrorless Camera Body" is the camera
# without a lens; the word comes in only by Google's "Bath & Body" aisle (owner's file,
# 2026-10-23: 35 cameras were doubtful).
_NOT_PRODUCT_NOUNS = frozenset(
    """
    accessories accessory parts part supplies supply products product equipment gear
    care cleaning kits kit sets set items item goods clothing furniture hardware
    lighting food audio baby art games components devices device systems system
    machines machine units unit suites suite appliances appliance models model series
    range combos combo packages package extractors extractor materials essentials
    decor decorations paraphernalia manuals mixes feed hunting boxing hockey baseball
    body bodies
    apple apples orange oranges cream creams charcoal sand stone stones slate copper
    bronze brass chrome ivory natural oak walnut walnuts pine rose roses mint olive
    olives lime limes peach peaches plum plums cherry cherries navy teal coral lilac
    lavender mustard taupe khaki burgundy champagne caramel
    fabric fabrics velvet linen linens cotton wood wooden metal steel glass plastic
    rattan wicker bamboo marble ceramic acrylic wool silk polyester vinyl foam mesh
    aluminium aluminum iron leather
    """.split()
)
# Product nouns the taxonomy has no shelf for, read off the live feed: a "Rocket Club
# Subscription" on the coffee machines shelf and a "Crakl Bonfire" on a heaters one
# (the build's list of 2026-10-23) are neither.
_EXTRA_PRODUCT_NOUNS = frozenset(
    "siren sirens keycap keycaps subscription subscriptions bonfire bonfires".split()
)
# Words that close a title's lead after its noun without being the product: a colour
# ("All White"), a pair, a pack. "Dishwasher Safe" is said of a product, not a safe.
_LEAD_CLOSING_WORDS = frozenset("all pair pairs".split())
_SAFE_FOR_WORDS = frozenset(
    "dishwasher microwave oven freezer fridge child food pet baby skin eco".split()
)
# A measurement or a count closes a lead without naming anything: "250V", "45x45cm",
# "4K", "2". A model code does name the product, by its maker's name for it: a lead that
# ends "My Sweet Piano 3108RF" or "Piggy Party 5108 V5" is a keyboard called that.
_MEASUREMENT_RE = re.compile(
    r"^\d+(?:[.,]\d+)?(?:x\d+(?:[.,]\d+)?)*"
    r"(?:mm|cm|m|km|in|inch|inches|ft|w|kw|v|a|ah|mah|wh|gb|tb|mb|l|ml|kg|g|lb|lbs|oz"
    r"|hz|khz|mhz|ghz|db|pcs|pc|p|k|th|st|nd|rd)?$"
)
# Words after which a title describes its product instead of naming it, besides the
# purpose words: "Cushion in Taupe Striped Cotton Linen".
_LEAD_DESCRIPTION_WORDS = frozenset({"in"})
# Joins that make a lead a list of names for one product: "Juice Maker & Citrus Squeezer".
_LEAD_LIST_RE = re.compile(r"&|\+|\band\b", flags=re.IGNORECASE)
_LEAD_PURPOSE_RE = re.compile(r"\s(?:with|for|without|incl\.?|including|in)\s", flags=re.IGNORECASE)
# A lead cut off at the first item of a list: "4-Piece Tea, Coffee, Sugar and Bread Bin
# Canister Set" goes on to the product after the list.
_LIST_AFTER_LEAD_RE = re.compile(r"^\s*,\s*[\w'’-]+(?:\s+[\w'’-]+)?\s*(?:,|&|\band\b)", flags=re.IGNORECASE)


def _noun_forms(word: str) -> frozenset[str]:
    forms = {word}
    if word.endswith("s") and not word.endswith("ss"):
        forms.add(word[:-1])
    if word.endswith("es"):
        forms.add(word[:-2])
    if len(word) > 4 and word.endswith("ies"):
        forms.add(word[:-3] + "y")
    return frozenset(forms)


@lru_cache(maxsize=1)
def _product_nouns() -> frozenset[str]:
    """The taxonomy's product nouns; empty when the taxonomy file is not there, and then
    no title is read against them."""
    try:
        lines = _TAXONOMY_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    nouns: set[str] = set()
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        for item in re.split(r"\s*(?:&|,|\band\b)\s*", line.split(">")[-1]):
            words = normalize_understanding_text(item).split()
            if words and len(words[-1]) > 2 and words[-1].isalpha():
                nouns.update(_noun_forms(words[-1]))
    nouns.update(_EXTRA_PRODUCT_NOUNS)
    return frozenset(nouns - _NOT_PRODUCT_NOUN_FORMS)


_NOT_PRODUCT_NOUN_FORMS = frozenset(form for word in _NOT_PRODUCT_NOUNS for form in _noun_forms(word))


def _is_product_noun_of_another_kind(
    tokens: tuple[str, ...], index: int, kinds: list[str], category: str = ""
) -> bool:
    """Is the word at `index` a product noun that is none of these kinds' own words, and
    that the product's own category shelves do not name either?"""
    word = tokens[index]
    if word not in _product_nouns() or _is_descriptor_word(word):
        return False
    if index > 0 and _MEASUREMENT_RE.match(tokens[index - 1]):
        # "7-Fin", "4-Seater", "2 Slice": a count of the noun is a spec of the product.
        return False
    forms = _noun_forms(word)
    own = {form for kind in kinds for name in _own_name_words(kind) for form in _noun_forms(name)}
    if forms & own:
        return False
    # The shelf names it too ("Sunloungers" for a "Sun Lounger", "Espresso Pots" for an
    # "Espresso Pot"): the shelf holds it. Only the narrowest shelf of each path: the
    # aisles above it say where a product is sold, and "Home & Garden" holds no "Family
    # Garden Set" on a heaters shelf (the build's list of 2026-10-23).
    shelf_forms = {
        shelf_form
        for shelf_word in normalize_understanding_text(_narrowest_shelves(category)).split()
        for shelf_form in _noun_forms(shelf_word)
    }
    return not any(shelf_form.endswith(form) for shelf_form in shelf_forms for form in forms)


def _lead_noun_index(tokens: tuple[str, ...], end: int) -> int:
    """Where the lead's own noun stands: the last word before `end` that is not a
    descriptor ("Grey", "250V", "Pair"), a material or a group noun ("Kit"); -1 when
    there is none, or when the lead ends in a model code instead ("3108RF")."""
    index = end - 1
    while index >= 0:
        token = tokens[index]
        if any(ch.isdigit() for ch in token) and not _MEASUREMENT_RE.match(token):
            return -1
        if token.isdigit() and len(token) > 2:
            return -1
        if token in {"safe", "proof"} and index > 0 and tokens[index - 1] in _SAFE_FOR_WORDS:
            # "Dishwasher Safe" is said of the product before it.
            index -= 2
            continue
        if not (
            token in _GROUP_NOUNS
            or token in _LEAD_CLOSING_WORDS
            or token in _NOT_PRODUCT_NOUN_FORMS
            or _is_descriptor_word(token)
        ):
            return index
        index -= 1
    return -1


def _lead_noun_tokens(title: str) -> tuple[str, ...] | None:
    """The lead's words up to where it starts describing its product, or None when the
    lead lists several names for it ("Juice Maker & Citrus Squeezer")."""
    lead = _title_lead(title)
    if _LEAD_LIST_RE.search(_LEAD_PURPOSE_RE.split(lead, maxsplit=1)[0]):
        return None
    if _LIST_AFTER_LEAD_RE.match(str(title or "")[len(lead):]):
        return None
    tokens = tuple(normalize_understanding_text(lead).split())
    cut = next(
        (i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS or token in _LEAD_DESCRIPTION_WORDS),
        len(tokens),
    )
    return tokens[:cut]


def _lead_names_another_product(title: str, kinds: list[str], category: str = "") -> bool:
    """Does a title's lead that names no known kind end in another product's noun?

    "MonsGeek M2 Plate - POM" on the keyboards shelf is a plate, "Pine Bench All White"
    on the tables shelf a bench. A lead that ends in a model name ("Dyson V15 Detect",
    "My Sweet Piano 3108RF"), a brand or a spec says nothing, and the shelf still
    decides -- unless the part after a bar names the product: "Batteryguard L-10 HE
    VDMA 24994 Certified | Lithium-Ion Battery Charging Safe" is a safe (owner's file,
    2026-10-23: 6 safes were phone chargers).
    """
    tokens = _lead_noun_tokens(title)
    if not tokens:
        return False
    index = _lead_noun_index(tokens, len(tokens))
    if index >= 0 and tokens[index] in _product_nouns():
        return _is_product_noun_of_another_kind(tokens, index, kinds, category)
    after_bar = _TITLE_BAR_RE.split(str(title or ""), maxsplit=1)[1:]
    return bool(after_bar) and _lead_names_another_product(after_bar[0], kinds, category)


def _type_names_kind_only_before_another_product(product_type: str, kind: str) -> bool:
    """Does every part of a type that names this kind name it only before another
    product's noun? Pro-Camera's "Lenses > Canon > Canon DSLR Lenses > Canon DSLR
    Standard Prime Lenses > ..." holds lenses, which "DSLR" describes; its "Cameras >
    Canon > Canon DSLR Cameras > ..." holds cameras."""
    described = False
    for segment in _BREADCRUMB_SPLIT_RE.split(str(product_type or "")):
        spans = _concepts_in_text(segment)
        named = [span for span in spans if span.concept_id == kind or _related(span.concept_id, kind)]
        if not named:
            continue
        tokens = tuple(normalize_understanding_text(segment).split())
        index = _lead_noun_index(tokens, len(tokens))
        if (
            index < 0
            or any(span.end > index for span in named)
            or any(span.start <= index < span.end for span in spans)
            or not _is_product_noun_of_another_kind(tokens, index, [kind])
        ):
            return False
        described = True
    return described


def _noun_after_kind(title: str, spans: list[_Span]) -> tuple[tuple[str, ...], int] | None:
    """The lead's words and where its own noun stands, when that noun comes right after
    one of these names of a kind ("Dressing Table Stool"); None otherwise."""
    tokens = _lead_noun_tokens(title)
    if not tokens:
        return None
    index = _lead_noun_index(tokens, len(tokens))
    if index < 0 or not any(span.end == index for span in spans):
        return None
    if any(span.start <= index < span.end for span in _concepts_in_text(" ".join(tokens))):
        # The noun is itself a kind PicWise knows ("Fan Heater"): the names are read
        # as a run, the last one the product, as before.
        return None
    return tokens, index


def _kind_named_before_another_product(title: str, span: _Span, category: str = "") -> bool:
    """Is the kind's name followed by the noun the lead ends with, another product's?
    "Dressing Table Stool" is a stool, "Chaise Sofa Block" a block."""
    noun = _noun_after_kind(title, [span])
    return noun is not None and _is_product_noun_of_another_kind(*noun, [span.concept_id], category)


def _lead_ends_in_accessory(title: str, kinds: list[str]) -> bool:
    """Does the title's lead end in an accessory noun that is not the kind's own name?"""
    tokens = normalize_understanding_text(_title_lead(title)).split()
    cut = next((i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS), len(tokens))
    index = cut - 1
    # Past the specs and colours that close a lead: "Folio Case Grey", "Stand 2 Pack".
    while index >= 0 and tokens[index] not in _LEAD_ACCESSORY_NOUNS and _is_descriptor_word(tokens[index]):
        index -= 1
    if index >= 0 and tokens[index] in _GROUP_NOUNS:
        index -= 1
    if index < 0 or tokens[index] not in _LEAD_ACCESSORY_NOUNS:
        return False
    own = {word for kind in kinds for word in _own_name_words(kind)}
    return tokens[index] not in own


# What the word a search names must not be followed by, or end with, in a product's own
# lead when no known kind reads the product: it is then a part of that thing or goes
# with it ("Rabbit Hutch Cover", "Cat Tree Replacement Post", "Dog Crate Mat").
_UNKNOWN_KIND_OTHER_PRODUCT_WORDS = (
    _LEAD_ACCESSORY_NOUNS
    | _OTHER_PRODUCT_TAIL_WORDS
    | _ACCESSORY_WORDS
    | frozenset("mat mats liner liners pad pads".split())
)
_TYPE_ALTERNATIVES_RE = re.compile(r"\s*(?:&|,|/|\band\b)\s*", flags=re.IGNORECASE)
# A title names its product in its first words; further into a long lead, a word lists
# what the product has or goes with: "PawHut 8 Panel Dog Playpen Puppy Pen Rabbits
# Guinea Metal Crate Pet Cage Run" is a playpen. The kind's word must stand within the
# lead's first seven words, unless the lead ends with it ("... Kids Ride on Car").
_MAX_KIND_WORD_PLACE = 6


@dataclass(frozen=True)
class KindWordReading:
    """How one product's own name reads one word of a search (`read_kind_word`)."""

    # The product is the thing the word names.
    names: bool = False
    # The word is the product's own noun: the last word of its type, or the noun its
    # title's lead ends with. A word no product of a feed has as its noun names no
    # product there: "lamb" is only ever "Lamb Fleece" or "Lamb Wool".
    as_noun: bool = False
    # The word before it in the name ("coffee" in "Coffee Machine"), or "".
    modifier: str = ""


def read_kind_word(product_type: str, title: str, word_forms: tuple[str, ...]) -> KindWordReading:
    """Does this product say it is the thing one word names, for a search with no known kind?

    Part 3b of the price-first plan (2026-10-17). A search whose product the lexicon
    does not know ("dog crate", "rabbit hutch", "network switch") is answered by its own
    words, and price order puts the cheapest product carrying them first: on the third
    real feed a £14.99 hutch cover, a pet carrier "with crate" and a £1.99 "Network
    Switch Tracking" licence. So the word naming the product must be what the product
    is, read the way a known kind is read:
    - a product type says it with its last word, in its last breadcrumb, in any of the
      kinds it lists: "Network Switches" and "Crates & Kennels" do, "Network Switch
      Components" and "USB Cables" do not;
    - with no type that says anything, the title's lead must carry the word, and must
      not end in an accessory noun or put one right after the word: "PawHut Wooden
      Rabbit Hutch" is a hutch and "Cat Tree Tower" a cat tree, "Waterproof Rabbit
      Hutch Cover" is a cover.
    """
    forms = {normalize_understanding_text(form) for form in word_forms if form}
    forms.discard("")
    if not forms:
        return KindWordReading()
    last_crumb = str(product_type or "").split(">")[-1]
    type_tokens = normalize_understanding_text(last_crumb).split()
    type_says_something = bool(type_tokens) and not (
        " ".join(type_tokens) in _UNINFORMATIVE_TYPES
        or all(token in _DEPARTMENT_WORDS for token in type_tokens)
    )
    if type_says_something:
        for alternative in _TYPE_ALTERNATIVES_RE.split(last_crumb):
            tokens = normalize_understanding_text(alternative).split()
            if tokens and tokens[-1] in forms:
                return KindWordReading(
                    names=True, as_noun=True, modifier=tokens[-2] if len(tokens) > 1 else ""
                )
        return KindWordReading()
    lead_tokens = normalize_understanding_text(_title_lead(title)).split()
    cut = next((i for i, token in enumerate(lead_tokens) if token in _PURPOSE_WORDS), len(lead_tokens))
    lead_tokens = lead_tokens[:cut]
    places = [i for i, token in enumerate(lead_tokens) if token in forms]
    if not places:
        return KindWordReading()
    # The lead's own noun, past the specs and colours that close it ("Hutch Cover Grey").
    index = len(lead_tokens) - 1
    while (
        index >= 0
        and lead_tokens[index] not in forms
        and lead_tokens[index] not in _UNKNOWN_KIND_OTHER_PRODUCT_WORDS
        and _is_descriptor_word(lead_tokens[index])
    ):
        index -= 1
    if index >= 0 and lead_tokens[index] in _GROUP_NOUNS:
        index -= 1
    if index >= 0 and lead_tokens[index] in _UNKNOWN_KIND_OTHER_PRODUCT_WORDS and lead_tokens[index] not in forms:
        return KindWordReading()
    as_noun = index in places
    standing = [
        place
        for place in places
        if (as_noun or place <= _MAX_KIND_WORD_PLACE)
        and (
            place + 1 >= len(lead_tokens)
            or lead_tokens[place + 1] in forms
            or lead_tokens[place + 1] not in _UNKNOWN_KIND_OTHER_PRODUCT_WORDS
        )
    ]
    if not standing:
        return KindWordReading()
    place = standing[0]
    return KindWordReading(
        names=True,
        as_noun=as_noun,
        modifier=lead_tokens[place - 1] if place > 0 else "",
    )


def _lead_names_another_product_after(title: str, concept_id: str) -> bool:
    lead_tokens = normalize_understanding_text(_title_lead(title)).split()
    cut = next((i for i, token in enumerate(lead_tokens) if token in _PURPOSE_WORDS), len(lead_tokens))
    lead = tuple(lead_tokens[:cut])
    return any(
        span.concept_id == concept_id and _names_another_product_after(lead, span.end)
        for span in _concepts_in_text(" ".join(lead))
    )


def _kinds_named_before_purpose(title: str) -> list[str]:
    """The kinds a title names before any "for" or "with": "Power Inverter ... with
    USB Charger" names no charger as the product. "power adapter/inverter" names both."""
    text = _WITH_ABBREVIATION_RE.sub(" with ", str(title or "")).replace("/", " ")
    tokens = normalize_understanding_text(text).split()
    cut = next((i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS), len(tokens))
    return [span.concept_id for span in _concepts_in_text(text) if span.start < cut]


def _product_context_markers(category: str, title: str) -> frozenset[str]:
    markers: set[str] = set()
    category_words = set(normalize_understanding_text(category).split())
    lead = _title_lead(title)
    lead_tokens = tuple(normalize_understanding_text(lead).split())
    head = _pick_head(_concepts_in_text(lead), lead_tokens)
    before_head = lead_tokens[head.start - 1] if head is not None and head.start > 0 else ""
    if category_words & _PET_AISLE_WORDS or before_head in _PET_WORDS:
        markers.add(PET_MARKER)
    if category_words & _CAMPING_WORDS or set(lead_tokens) & _CAMPING_WORDS:
        markers.add(CAMPING_MARKER)
    return frozenset(markers)


def query_allows_context(tokens: tuple[str, ...], marker: str) -> bool:
    """Do the buyer's own words ask for products of this context?"""
    words = set(tokens)
    if marker == PET_MARKER:
        return bool(words & _PET_WORDS)
    if marker == CAMPING_MARKER:
        return bool(words & _CAMPING_WORDS)
    return True


# Words that may follow a product name in a title without changing what it is: a
# colour or other preference word, a spec, a number, a packaging or version word.
_DESCRIPTOR_TAIL_WORDS = frozenset(
    """
    color colour colours colors version edition set sets pack packs pcs piece pieces
    plus pro max mini lite uk eu us plug size type new
    """.split()
)


def _is_descriptor_word(token: str) -> bool:
    if not token or any(ch.isdigit() for ch in token):
        return True
    if token in _DESCRIPTOR_TAIL_WORDS or _is_exact_qualifier(token):
        return True
    return token in _lexicon().english_qualifier_words


def _head_of_text(
    text: str,
    *,
    first: bool = False,
    first_phrase: bool = False,
    strict_tail: bool = False,
    accessory_words: frozenset[str] | None = None,
) -> str | None:
    """The concept a piece of feed text names, or ACCESSORY_MARKER for an accessory of it.

    The accessory word's position decides: English puts the main product first and the
    accessory after it ("coffee machine filter"), while a word before it is a type
    ("filter coffee machine"). Greek is the other way round: "φίλτρο καφετιέρας" is a
    filter, "καφετιέρα φίλτρου" a coffee machine.

    Only the words before a purpose word name the product; what follows says what it is
    for or comes with. "Vacuum cleaner with filter" is a vacuum cleaner, and text that
    names a product only after a purpose word -- "filter for coffee machine",
    "accessories for laptops" -- names something for that product, an accessory.

    `accessory_words` is wider for a feed's own classification (its product type, its
    category shelves) than for a title: see `_CLASSIFICATION_ACCESSORY_WORDS`.
    """
    if accessory_words is not None and accessory_words is not _ACCESSORY_WORDS:
        # A classification names its product by its last words, and when those are a
        # known kind ("Mobile Phone Cases"), that kind is the product.
        tail = _tail_concept(text)
        if tail is not None:
            return tail
    accessory_words = _ACCESSORY_WORDS if accessory_words is None else accessory_words
    tokens = tuple(normalize_understanding_text(text).split())
    spans = _concepts_in_text(text)
    if not spans:
        return None
    if first_phrase:
        # The product a title names first, read as English reads a noun phrase: the
        # last name in the first run of names. "Fan Heater" is a heater, "Laptop Intel
        # Celeron 64GB SSD" a laptop.
        head = spans[0]
        for span in spans[1:]:
            if span.start != head.end:
                break
            head = span
    else:
        head = spans[0] if first else _pick_head(spans, tokens)
    if head is None:
        return None
    covered = {i for span in spans for i in range(span.start, span.end)}
    cut = next(
        (i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS and i not in covered),
        len(tokens),
    )
    if head.start > cut:
        return ACCESSORY_MARKER
    if head.kind == "en" and head.end < cut and tokens[head.end] in _MODIFIER_TAIL_WORDS:
        # "table runner", "cable ties": the product name describes what the thing is
        # for, it does not name it.
        return ACCESSORY_MARKER
    # An accessory word counts even when it is itself a product name ("Luggage Cover"
    # is a cover, not luggage); only the head's own words, and other names of the same
    # product, are read as part of the product.
    head_words = {
        i
        for span in spans
        if span is head or _related(span.concept_id, head.concept_id)
        for i in range(span.start, span.end)
    }
    # A word that is one of the kind's own names, weak ones included, does not make it
    # an accessory of itself: a phone "Case Cover" is a phone case.
    own_words = _own_name_words(head.concept_id)
    # "Power banks and batteries" is a shelf of two kinds, not power bank batteries:
    # an English accessory word only counts before the first "and" after the name.
    list_at = next(
        (i for i in range(head.end, cut) if tokens[i] in {"and", "και"}),
        cut,
    )
    for index, token in enumerate(tokens[:cut]):
        if index in head_words or token not in accessory_words or token in own_words:
            continue
        if token in _GROUP_NOUNS and index - 1 in head_words:
            # "Camera Kit" is the camera and what comes with it, as an "Anchor Kit" is
            # anchors; a "Cleaning Kit" stays an accessory (owner's file, 2026-10-23:
            # 13 camera kits were read as accessories).
            continue
        if head.kind == "en" and index >= list_at:
            continue
        if head.kind == "en" and index >= head.end:
            return ACCESSORY_MARKER
        if head.kind == "el" and index < head.start:
            return ACCESSORY_MARKER
    if (
        strict_tail
        and head.kind == "en"
        and head.end < cut
        and not _is_descriptor_word(tokens[head.end])
    ):
        # The text names the product in passing, with a word PicWise cannot read right
        # after it: "Truck Bed Tailgate Extender", "Power banks and batteries". On
        # that evidence the kind is a guess, and PicWise shows nothing rather than the
        # wrong kind. A colour, a spec or a packaging word still reads as the product
        # ("Smartwatch Black Dial", "Speaker 40W").
        return None
    return head.concept_id


# Words that make text a part of a product wherever they stand: "replacement coffee
# machine jug" is a jug.
_PART_WORDS = frozenset(
    """
    accessories accessory parts part spare spares replacement replacements refill refills
    αξεσουαρ ανταλλακτικα ανταλλακτικο εξαρτηματα εξαρτημα
    """.split()
)


@lru_cache(maxsize=65536)
def words_after_product_name(text: str, concept_id: str) -> str | None:
    """The words English product text puts after naming a `concept_id` product, or None.

    English puts a product's type before its name and an accessory after it: "filter
    coffee machine" and "battery lawn mower" are the products, "coffee machine filter"
    is a filter. None when the text does not name the product itself: only words before
    the first purpose word can name it ("battery for laptop" names no laptop), and an
    accessory word after the name or a part word anywhere makes it a part of one. Greek
    orders these the other way and is not read here. The words returned are normalised
    and stop at the purpose word.
    """
    tokens = tuple(normalize_understanding_text(text).split())
    if any(token in _PART_WORDS for token in tokens):
        return None
    cut = next((i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS), len(tokens))
    named = tokens[:cut]
    spans = _choose_spans(_find_spans(named, [_exact_candidates(token) for token in named]))
    for span in spans:
        if concept_id not in broader_concepts(span.concept_id):
            continue
        after = named[span.end:]
        if span.kind != "en" or any(token in _ACCESSORY_WORDS for token in after):
            return None
        return " ".join(after)
    return None


_TYPE_LIST_SPLIT_RE = re.compile(r"\s*(?:&|,|/|\band\b|\bκαι\b)\s*", flags=re.IGNORECASE)


# --------------------------------------------------------------------------------------
# Feed text normalisation for specs
# --------------------------------------------------------------------------------------

_SPACED_SPEC_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(\"|''|inches|inch|kgs|kg|litres|liters|litre|liter|ltr|lt|l\b|"
    r"mah|wh\b|ah\b|watts|watt|w\b|volts|volt|v\b|gb|tb|hz|rpm|db\b|btu|mm\b|cm\b|mp\b)",
    flags=re.IGNORECASE,
)
_CANONICAL_UNIT = {
    "\"": "inch", "''": "inch", "inches": "inch", "inch": "inch",
    "kgs": "kg", "kg": "kg",
    "litres": "l", "liters": "l", "litre": "l", "liter": "l", "ltr": "l", "lt": "l", "l": "l",
    "watts": "w", "watt": "w", "w": "w", "volts": "v", "volt": "v", "v": "v",
}


# "23.8in" in a title is inches; "2 in 1" and "2-in-1" are not, so only the fused form.
_FUSED_INCH_RE = re.compile(r"(\d+(?:[.,]\d+)?)in\b", flags=re.IGNORECASE)


def normalize_spec_text(text: str) -> str:
    """Write every "<number> <unit>" in feed text as the fused token a query produces."""

    def replace(match: re.Match[str]) -> str:
        unit = match.group(2).lower()
        return f"{match.group(1).replace(',', '.')}{_CANONICAL_UNIT.get(unit, unit)}"

    fused = _SPACED_SPEC_RE.sub(replace, str(text or ""))
    return _FUSED_INCH_RE.sub(lambda match: f"{match.group(1).replace(',', '.')}inch", fused)
