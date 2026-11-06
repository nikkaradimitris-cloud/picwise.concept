"""Code checks of the AI's answer before anything is shown (the AI layer's spec,
`docs/PICWISE_AI_LAYER_SPEC.md`, 4.3).

Nothing fake (`PROJECT_RULES.md` section 4): a sentence is shown only when every check
passes; one that fails is not shown, and the page says nothing about it.

- every product number answered is one that was sent, each once, all of them;
- a `yes` counts only when the words it gives as its proof stand, letter for letter, in
  that product's own title or description (in one run, or in pieces joined by ";", each
  standing there); otherwise it is read as `unclear`;
- the counts in the sentence are its own `yes` answers ("4 of these 30");
- every price in the sentence is the price of a product answered `yes`, and the lowest
  of them where it says "from";
- every other number is in the search, a title or the counts;
- every word with a capital letter or a digit is in the search or the products' data;
- no word of quality, testing, rating or urgency, no link or e-mail;
- English, one sentence, at most 30 words.

When no product fits, there is no sentence (owner, 2026-11-05: «ΟΤΑΝ ΔΕΝ ΒΡΙΣΚΕΙ ΚΑΤΙ ΝΑ
ΜΗΝ ΛΕΕΙ ΔΕΝ ΒΡΕΘΗΚΕ», then «ΣΩΣΤΑ»), only the words the shops use for the need, each
kept when it stands in a title of the products given, as a whole word, and is no brand,
no word of quality or price, and not the kind's own name; the page offers each as a search
only with the count the catalogue gives it (`shop_words.verified_shop_words`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from picwise_ai.complex_search import _ENGLISH_JUDGEMENTS, ComplexSearch
from picwise_ai.request import MAX_SENTENCE_WORDS, MAX_SHOP_WORDS
from picwise_providers.decision_labels import parse_price_amount

# Words a sentence may never hold, whatever the titles say (`PROJECT_RULES.md` section 4:
# no fake ratings, urgency or AI confidence; commission never ranks; the Recommended is
# the owner's rule, never the AI's).
FORBIDDEN_WORDS = frozenset(
    """
    best better greatest great top ideal perfect excellent amazing superb outstanding
    premium quality recommend recommended recommends recommendation review reviews
    reviewed rated rating ratings tested trusted popular bestseller bestselling
    favourite favorite deal deals bargain cheap hurry guaranteed guarantee certainly
    definitely
    """.split()
)
# "rated" is a word of reviews, except as a product's own rating: "rated for 20°F".
_RATING_FOLLOWERS = frozenset({"for", "to", "at", "up"})
_SHOP_WORD = re.compile(r"^[^\W_][\w'’&+./-]*(?: [^\W_][\w'’&+./-]*){0,2}$")
# Capitalised words a sentence may use that no title needs to hold.
_ALLOWED_CAPITALISED = frozenset({"picwise"})
_NUMBER_WORDS = {
    word: number
    for number, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen"
        " fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
}
_NUMBER_WORDS.update({"thirty": 30, "none": 0, "no": 0})
_CURRENCY_SYMBOLS = {"£": "GBP", "$": "USD", "€": "EUR"}

_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_LINK = re.compile(r"https?://|www\.|\w@\w|\.(?:com|co\.uk|net|org)\b", re.IGNORECASE)
_PRICE = re.compile(
    r"(?P<symbol>[£$€])\s?(?P<amount>\d[\d,]*(?:\.\d{1,2})?)"
    r"|(?P<amount2>\d[\d,]*(?:\.\d{1,2})?)\s?(?P<code>GBP|USD|EUR)\b"
)
_COUNT = re.compile(r"\b(?P<count>\w+)\s+(?:out\s+)?of\s+(?:these|the|those|all\s+)?\s*(?P<of>\w+)\b", re.IGNORECASE)
_NONE_OF = re.compile(r"\bnone\s+of\b", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_WORD = re.compile(r"[^\W_][\w'’&+.-]*", re.UNICODE)
# Where a `yes` joins pieces of its product's words: each piece is checked on its own.
_PIECES = re.compile(r"\s*(?:;|…|\.{3})\s*")


@dataclass(frozen=True)
class Checked:
    """The answer as code read it: the sentence to show ("" when withheld or when no
    product fits), the product numbers per verdict, the first check that failed ("" when
    every check passed), and, when no product fits, the shops' words that passed."""

    sentence: str
    yes: tuple[int, ...]
    no: tuple[int, ...]
    unclear: tuple[int, ...]
    failure: str
    shop_words: tuple[str, ...] = ()
    # Each counted `yes`, with the product's own words that show it.
    proof: tuple[tuple[int, str], ...] = ()
    # The `yes` answers whose words do not stand in the product: read as `unclear`.
    unproved: tuple[int, ...] = ()

    @property
    def shown(self) -> bool:
        return bool(self.sentence) and not self.failure


def _withheld(failure: str, yes=(), no=(), unclear=(), proof=(), unproved=()) -> Checked:
    return Checked(
        sentence="", yes=tuple(yes), no=tuple(no), unclear=tuple(unclear), failure=failure,
        proof=tuple(proof), unproved=tuple(unproved),
    )


def _plain(text: str) -> str:
    """Text as a proof is matched against it: one case, one kind of quote and dash, one space."""
    text = str(text or "").lower()
    for old, new in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("\u00a0", " ")):
        text = text.replace(old, new)
    return " ".join(text.split())


def _proved(words: Any, candidate) -> str:
    """The words a `yes` gives, when they stand in the product's own title or description:
    in one run, or in pieces joined by ";" or an ellipsis, each piece standing there
    (the third measure: "TSA Carry-On Compliant; Keep your devices charged all day")."""
    text = _plain(f"{candidate.title} {candidate.description}")
    pieces = [piece.strip(" .,;:'\"…") for piece in _PIECES.split(_plain(words))]
    pieces = [piece for piece in pieces if piece]
    if not pieces or any(len(piece) < 3 or piece not in text for piece in pieces):
        return ""
    return "; ".join(pieces)


def _as_int(token: str) -> int | None:
    text = str(token or "").strip().lower()
    if text.isdigit():
        return int(text)
    return _NUMBER_WORDS.get(text)


def _number_key(text: str) -> str:
    value = text.replace(",", ".")
    try:
        number = float(value)
    except ValueError:
        return text
    return str(int(number)) if number == int(number) else f"{number:g}"


def _price_of(candidate_price: str) -> tuple[str, float] | None:
    amount = parse_price_amount(candidate_price)
    if amount is None:
        return None
    currency = ""
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in candidate_price or code in candidate_price.upper():
            currency = code
            break
    return currency, round(amount, 2)


def check_answer(answer: Any, complex_search: ComplexSearch, *, stop_reason: str) -> Checked:
    """Read the AI's answer against the products it was given; see the module's docstring."""
    if stop_reason != "end_turn":
        return _withheld(f"the answer stopped early ({stop_reason or 'no reason'})")
    if not isinstance(answer, dict) or not isinstance(answer.get("verdicts"), list):
        return _withheld("the answer is not in the agreed shape")
    count = len(complex_search.candidates)
    by_number = {candidate.number: candidate for candidate in complex_search.candidates}
    seen: dict[int, str] = {}
    proofs: dict[int, str] = {}
    for verdict in answer["verdicts"]:
        if not isinstance(verdict, dict):
            return _withheld("a verdict is not in the agreed shape")
        number, fits = verdict.get("n"), verdict.get("fits")
        if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= count:
            return _withheld(f"a product number that was not sent ({number!r})")
        if fits not in ("yes", "no", "unclear"):
            return _withheld(f"a verdict that is not yes, no or unclear ({fits!r})")
        if number in seen:
            return _withheld(f"product {number} answered twice")
        if fits == "yes":
            proof = _proved(verdict.get("words"), by_number[number])
            if proof:
                proofs[number] = proof
            else:
                fits = "unproved"
        seen[number] = fits
    yes = tuple(sorted(number for number, fits in seen.items() if fits == "yes"))
    no = tuple(sorted(number for number, fits in seen.items() if fits == "no"))
    unproved = tuple(sorted(number for number, fits in seen.items() if fits == "unproved"))
    unclear = tuple(sorted(number for number, fits in seen.items() if fits in ("unclear", "unproved")))
    proof = tuple((number, proofs[number]) for number in yes)
    if len(seen) != count:
        return _withheld(f"{count - len(seen)} of the {count} products not answered", yes, no, unclear, proof, unproved)

    if not yes:
        # No sentence when nothing fits: the shops' words for the need, those that pass.
        words = shop_words_that_pass(answer.get("shop_words"), complex_search)
        return Checked(sentence="", yes=yes, no=no, unclear=unclear, failure="", shop_words=words,
                       unproved=unproved)
    sentence = " ".join(str(answer.get("sentence") or "").split())
    failure = _sentence_failure(sentence, complex_search, yes)
    if failure:
        return _withheld(failure, yes, no, unclear, proof, unproved)
    return Checked(sentence=sentence, yes=yes, no=no, unclear=unclear, failure="", proof=proof, unproved=unproved)


def shop_words_that_pass(words: Any, complex_search: ComplexSearch) -> tuple[str, ...]:
    """The words the AI gave for the need, each kept only when it stands as a whole word
    or phrase in a title of the products it was given, is at most three words, and is
    no brand of them, no word of quality, price or judgement, and not the kind's name."""
    if not isinstance(words, list):
        return ()
    titles = [candidate.title for candidate in complex_search.candidates]
    brands = {candidate.brand.lower() for candidate in complex_search.candidates if candidate.brand}
    kind = complex_search.kind_name.lower()
    kept: list[str] = []
    for word in words:
        phrase = " ".join(str(word or "").split())
        lowered = phrase.lower()
        if not phrase or len(phrase) > 40 or not _SHOP_WORD.match(phrase) or _GREEK.search(phrase):
            continue
        parts = set(re.split(r"[\s-]+", lowered))
        if parts & (FORBIDDEN_WORDS | _ENGLISH_JUDGEMENTS) or lowered in brands or lowered in (kind, f"{kind}s"):
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
        if not any(pattern.search(title) for title in titles):
            continue
        if lowered not in {k.lower() for k in kept}:
            kept.append(phrase)
        if len(kept) == MAX_SHOP_WORDS:
            break
    return tuple(kept)


def _sentence_failure(sentence: str, complex_search: ComplexSearch, yes: tuple[int, ...]) -> str:
    if not sentence:
        return "no sentence"
    words = sentence.split()
    if len(words) > MAX_SENTENCE_WORDS:
        return f"a sentence of {len(words)} words"
    if _GREEK.search(sentence):
        return "a sentence not in English"
    if "!" in sentence or "?" in sentence:
        return "a question or an exclamation"
    if re.search(r"\.\s+[A-Z]", sentence):
        return "more than one sentence"
    if _LINK.search(sentence):
        return "a link or an e-mail"
    bare = [word.strip(".,;:'’\"()").lower().replace("’", "'") for word in words]
    lowered = {part for word in bare for part in word.split("-")}
    if "rated" in lowered and all(
        index + 1 < len(bare) and bare[index + 1] in _RATING_FOLLOWERS
        for index, word in enumerate(bare) if word == "rated"
    ):
        lowered.discard("rated")
    forbidden = sorted(lowered & FORBIDDEN_WORDS)
    if forbidden:
        return "a forbidden word: " + ", ".join(forbidden)

    by_number = {candidate.number: candidate for candidate in complex_search.candidates}
    yes_prices = [price for price in (_price_of(by_number[number].price_text) for number in yes) if price]

    # Prices: each one a product answered "yes"; "from" the lowest of them.
    rest = sentence
    for match in _PRICE.finditer(sentence):
        amount = parse_price_amount(match.group("amount") or match.group("amount2") or "")
        if amount is None:
            return f"a price that cannot be read: {match.group(0)}"
        currency = _CURRENCY_SYMBOLS.get(match.group("symbol") or "", match.group("code") or "")
        amount = round(amount, 2)
        if not any(amount == value and currency in ("", code) for code, value in yes_prices):
            return f"a price not of a product answered yes: {match.group(0)}"
        before = sentence[max(0, match.start() - 6):match.start()].lower()
        if "from" in before and amount != min(value for _code, value in yes_prices):
            return f"a 'from' price that is not the lowest of those answered yes: {match.group(0)}"
        rest = rest.replace(match.group(0), " ", 1)

    # Counts: "4 of these 30" is its own yes answers of the products sent.
    totals = {len(complex_search.candidates), complex_search.total}
    stated = False
    for match in _COUNT.finditer(rest):
        number, of = _as_int(match.group("count")), _as_int(match.group("of"))
        if number is None or of is None:
            continue
        if of not in totals:
            return f"a count of products that was not sent: {match.group(0)}"
        if number != len(yes):
            return f"a count that is not its own yes answers ({len(yes)}): {match.group(0)}"
        stated = True
        rest = rest.replace(match.group(0), " ", 1)
    if _NONE_OF.search(rest):
        if yes:
            return f"'none' while {len(yes)} were answered yes"
        stated = True
    if len(yes) == 1 and not stated and rest.lstrip().lower().startswith("this "):
        stated = True  # one product fits: "This kettle says ..."
    if yes and not stated:
        return "the sentence does not say how many fit"

    # Other numbers and named things: only from the search and the products' own data.
    sources = " ".join(
        [complex_search.search, complex_search.kind_name, *complex_search.words]
        + [f"{c.title} {c.brand} {c.shop} {c.description}" for c in complex_search.candidates]
    )
    known_numbers = {_number_key(text) for text in _NUMBER.findall(sources)}
    known_numbers |= {str(len(yes)), *(str(total) for total in totals)}
    for text in _NUMBER.findall(rest):
        if _number_key(text) not in known_numbers:
            return f"a number not in the search or the products: {text}"
    known_words = {word.lower().strip(".,;:'’\"()") for word in _WORD.findall(sources)}
    for index, word in enumerate(_WORD.findall(rest)):
        bare = word.strip(".,;:'’\"()-")
        if not bare:
            continue
        # Digits are read by the numbers above; a capital names a brand, a model or a
        # place, except at the head of the sentence.
        if not bare[0].isupper() or (index == 0 and rest.lstrip().startswith(word)):
            continue
        if bare.lower() in _ALLOWED_CAPITALISED or bare.lower() in known_words:
            continue
        if bare.lower().rstrip("s") in known_words or f"{bare.lower()}s" in known_words:
            continue
        return f"a name not in the search or the products: {bare}"
    return ""
