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

Product text is annotated with the same lexicon but by exact key only, since feed text
is spelled correctly and a fuzzy match there would invent concepts.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from .misspelling_variants import english_layout_text_to_greek
from .product_concepts import (
    broader_concepts,
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
_PURPOSE_WORDS = frozenset({"for", "with", "without", "για", "με", "χωρις", "gia", "me", "xoris", "choris"})

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


def _word_identity(word: str) -> tuple[str, str]:
    if is_greek_word(word):
        return ("el", greek_key(word))
    return ("en", english_key(word))


class _Lexicon:
    def __init__(self) -> None:
        self.forms_by_first: dict[tuple[str, str], list[_Form]] = {}
        words: dict[str, set[str]] = {"el": set(), "en": set()}
        for concept in get_product_concepts():
            for text in concept.english + concept.greek:
                tokens = normalize_understanding_text(text).split()
                if not tokens:
                    continue
                identities = tuple(_word_identity(token) for token in tokens)
                self._add(_Form(concept.concept_id, identities), words)
                kinds = {kind for kind, _ in identities}
                if len(identities) > 1 and len(kinds) == 1:
                    # The same name typed without spaces: "πλυντηριορουχων".
                    joined = (identities[0][0], "".join(key for _, key in identities))
                    self._add(_Form(concept.concept_id, (joined,)), words)
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
                    spans.append(_Span(start, end, form.concept_id, cost, identity[0]))
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
        if fused and fused.group(2) in _UNIT_BY_ALIAS:
            unit = _UNIT_BY_ALIAS[fused.group(2)]
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

    spec_spans, spec_positions = _parse_specs(list(tokens))
    non_retail_positions = {i for i, token in enumerate(tokens) if token in _NON_RETAIL_WORDS}
    # Connectives and non-retail words are matched exactly only: they may be part of a
    # product name ("φριτέζα χωρίς λάδι", "power bank") but are never guessed at.
    candidates = [
        {}
        if i in spec_positions
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
        if index in head_positions:
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
        return ConceptReading(query=str(query or ""), tokens=tokens)

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
    tokens = tuple(normalize_understanding_text(text).split())
    if not tokens:
        return []
    candidates = [_exact_candidates(token) for token in tokens]
    spans = _choose_spans(_find_spans(tokens, candidates))
    # The product in a title is named before what it is for: "charger for iphone".
    cut = next((i for i, token in enumerate(tokens) if token in _PURPOSE_WORDS), len(tokens))
    return [span for span in spans if span.start < cut] or spans


@lru_cache(maxsize=262144)
def annotate_product_concepts(product_type: str, category: str, title: str) -> frozenset[str]:
    """Which concepts one feed product is an instance of, including broader ones.

    The feed's own product type is the authority; the category is used when there is no
    type, and the title only when neither names a concept. The title may still refine
    the type into a narrower concept of the same kind: a "Vacuum Cleaners" product
    titled "Robot Vacuum Cleaner" is also a robot vacuum.
    """
    bases: list[str] = []
    for text in (product_type, category):
        # A feed type can list several kinds: "Fans & Heaters", "Cases, Covers".
        for part in _TYPE_LIST_SPLIT_RE.split(str(text or "")):
            head = _head_of_text(part)
            if head is ACCESSORY_MARKER:
                return frozenset({ACCESSORY_MARKER})
            if head is not None:
                bases.append(head)
        if bases:
            break
    title_spans = _concepts_in_text(title)
    if not bases:
        if not title_spans:
            return frozenset()
        head = _head_of_text(title, first=True)
        if head is ACCESSORY_MARKER or head is None:
            return frozenset({ACCESSORY_MARKER}) if head is ACCESSORY_MARKER else frozenset()
        bases = [head]
    concepts: set[str] = set()
    for base in bases:
        concepts.update(broader_concepts(base))
    for span in title_spans:
        chain = broader_concepts(span.concept_id)
        if any(base in chain[1:] for base in bases):
            concepts.update(chain)
    return frozenset(concepts)


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
    αξεσουαρ ανταλλακτικα ανταλλακτικο εξαρτηματα εξαρτημα φιλτρο φιλτρα σακουλες σακουλα
    καλυμμα καλυμματα βαση βασεις τηλεχειριστηριο λουρακι καθαριστικο αφαλατικο λαστιχο
    """.split()
)


def _head_of_text(text: str, *, first: bool = False) -> str | None:
    """The concept a piece of feed text names, or ACCESSORY_MARKER for an accessory of it.

    The accessory word's position decides: English puts the main product first and the
    accessory after it ("coffee machine filter"), while a word before it is a type
    ("filter coffee machine"). Greek is the other way round: "φίλτρο καφετιέρας" is a
    filter, "καφετιέρα φίλτρου" a coffee machine.
    """
    tokens = tuple(normalize_understanding_text(text).split())
    spans = _concepts_in_text(text)
    if not spans:
        return None
    head = spans[0] if first else _pick_head(spans, tokens)
    if head is None:
        return None
    covered = {i for span in spans for i in range(span.start, span.end)}
    for index, token in enumerate(tokens):
        if index in covered or token not in _ACCESSORY_WORDS:
            continue
        if head.kind == "en" and index >= head.end:
            return ACCESSORY_MARKER
        if head.kind == "el" and index < head.start:
            return ACCESSORY_MARKER
    return head.concept_id


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


def normalize_spec_text(text: str) -> str:
    """Write every "<number> <unit>" in feed text as the fused token a query produces."""

    def replace(match: re.Match[str]) -> str:
        unit = match.group(2).lower()
        return f"{match.group(1).replace(',', '.')}{_CANONICAL_UNIT.get(unit, unit)}"

    return _SPACED_SPEC_RE.sub(replace, str(text or ""))
