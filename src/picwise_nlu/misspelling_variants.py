"""Realistic misspelling generators for Greek, greeklish and English buyer queries.

These produce the kinds of errors people actually make when typing a product search,
so the NLU can be trained and measured against them rather than against clean text:

- Greek typed without accents, which is the norm on phones
- Greek homophone vowel confusion: η, ι, υ, ει, οι all sound like "i"; ο and ω like "o";
  ε and αι like "e". Spelling them wrongly is the single most common Greek typo.
- a final σ where ς belongs, common on mobile keyboards
- greeklish under several transliteration habits, because there is no single standard:
  "πλυντήριο" is written plyntirio, plintirio, plynthrio and more
- Greek typed while the English keyboard layout is active, which turns "ψυγείο" into
  "cygeio" -- every Greek letter lands on the Latin key it shares
- English keyboard slips: a neighbouring key pressed instead of the intended one

Every generator is deterministic, so a benchmark built from them is reproducible.
"""
from __future__ import annotations

import unicodedata

_GREEK_COMBINING_MARKS = frozenset({"́", "̈", "̈́", "΅", "͂"})


def strip_greek_accents(text: str) -> str:
    """Remove tonos and dialytika, keeping the base letters and the final ς."""
    decomposed = unicodedata.normalize("NFD", str(text or ""))
    stripped = "".join(ch for ch in decomposed if ch not in _GREEK_COMBINING_MARKS)
    return unicodedata.normalize("NFC", stripped)


def has_greek_letters(text: str) -> bool:
    return any("Ͱ" <= ch <= "Ͽ" or "ἀ" <= ch <= "῿" for ch in str(text or ""))


# --------------------------------------------------------------------------------------
# Greeklish transliteration. Digraphs are handled before single letters.
# --------------------------------------------------------------------------------------

_GREEKLISH_SCHEMES: dict[str, dict[str, object]] = {
    # The habit closest to the ELOT standard: υ as y, χ as ch, η as i.
    "greeklish_standard": {
        "digraphs": {
            "ου": "ou",
            "αι": "ai",
            "ει": "ei",
            "οι": "oi",
            "αυ": "av",
            "ευ": "ev",
            "μπ": "mp",
            "ντ": "nt",
            "γκ": "gk",
            "γγ": "ng",
        },
        "letters": {
            "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i",
            "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x",
            "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y",
            "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
        },
    },
    # Written by sound: every "i" sound becomes i, χ becomes h, ει/οι collapse to i.
    "greeklish_phonetic": {
        "digraphs": {
            "ου": "ou",
            "αι": "e",
            "ει": "i",
            "οι": "i",
            "υι": "i",
            "αυ": "af",
            "ευ": "ef",
            "μπ": "mp",
            "ντ": "nt",
            "γκ": "gk",
            "γγ": "ng",
        },
        # At the start of a word these are pronounced, and so written, as b, d and g.
        "initial_digraphs": {"μπ": "b", "ντ": "d", "γκ": "g"},
        "letters": {
            "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i",
            "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "ks",
            "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "i",
            "φ": "f", "χ": "h", "ψ": "ps", "ω": "o",
        },
    },
    # Written by shape: η as h, ω as w, θ as 8, ξ as 3.
    "greeklish_visual": {
        "digraphs": {
            "ου": "ou",
            "μπ": "mp",
            "ντ": "nt",
            "γκ": "gk",
        },
        "letters": {
            "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "h",
            "θ": "8", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "3",
            "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y",
            "φ": "f", "χ": "x", "ψ": "ps", "ω": "w",
        },
    },
}

GREEKLISH_SCHEME_NAMES: tuple[str, ...] = tuple(_GREEKLISH_SCHEMES)


def transliterate_greek(text: str, scheme: str = "greeklish_standard") -> str:
    """Render Greek text in greeklish under one of the common transliteration habits."""
    table = _GREEKLISH_SCHEMES.get(scheme) or _GREEKLISH_SCHEMES["greeklish_standard"]
    digraphs: dict[str, str] = table["digraphs"]  # type: ignore[assignment]
    initial: dict[str, str] = table.get("initial_digraphs", {})  # type: ignore[assignment]
    letters: dict[str, str] = table["letters"]  # type: ignore[assignment]
    source = strip_greek_accents(str(text or "")).lower()
    output: list[str] = []
    index = 0
    while index < len(source):
        pair = source[index:index + 2]
        at_word_start = index == 0 or source[index - 1] == " "
        if len(pair) == 2 and at_word_start and pair in initial:
            output.append(initial[pair])
            index += 2
            continue
        if len(pair) == 2 and pair in digraphs:
            output.append(digraphs[pair])
            index += 2
            continue
        char = source[index]
        output.append(letters.get(char, char))
        index += 1
    return "".join(output)


# Where each Greek letter sits on a standard Greek keyboard, i.e. the Latin character
# produced when that key is pressed with the English layout active.
_GREEK_KEY_TO_LATIN = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "h",
    "θ": "u", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "j",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "w", "τ": "t", "υ": "y",
    "φ": "f", "χ": "x", "ψ": "c", "ω": "v",
}
_LATIN_KEY_TO_GREEK = {latin: greek for greek, latin in _GREEK_KEY_TO_LATIN.items() if greek != "ς"}


def greek_typed_on_english_layout(text: str) -> str:
    """What Greek text looks like when typed with the English layout still active."""
    source = strip_greek_accents(str(text or "")).lower()
    return "".join(_GREEK_KEY_TO_LATIN.get(ch, ch) for ch in source)


def english_layout_text_to_greek(text: str) -> str:
    """Undo `greek_typed_on_english_layout`: map Latin key characters back to Greek.

    A word-final "w" or "s" becomes ς, since that is the key ς lives on and σ never
    ends a Greek word.
    """
    words = []
    for word in str(text or "").lower().split():
        letters = [_LATIN_KEY_TO_GREEK.get(ch, ch) for ch in word]
        if word and word[-1] in {"w", "s"}:
            letters[-1] = "ς"
        words.append("".join(letters))
    return " ".join(words)


# --------------------------------------------------------------------------------------
# Greek spelling errors
# --------------------------------------------------------------------------------------

# The misspelling people actually make for each sound: ι where η belongs, ε for αι...
# Digraphs are listed first so they are found before their single letters.
_SOUND_SUBSTITUTES: tuple[dict[str, str], ...] = (
    {"ει": "ι", "οι": "ι", "υι": "ι", "η": "ι", "ι": "η", "υ": "ι"},
    {"ω": "ο", "ο": "ω"},
    {"αι": "ε", "ε": "αι"},
)


# Two-letter vowels read as one sound. A single letter inside one of them is part of a
# different sound, so misspelling it would not be a homophone error: changing the ο of
# "ου" gives "ωυ", which nobody types for the "ou" sound.
_VOWEL_DIGRAPHS = ("ει", "οι", "υι", "ου", "αι", "αυ", "ευ")


def _inside_other_digraph(text: str, index: int, sound: str) -> bool:
    for digraph in _VOWEL_DIGRAPHS:
        if digraph == sound:
            continue
        for offset in (0, 1):
            start = index - offset
            if start >= 0 and text.startswith(digraph, start) and start <= index < start + 2:
                return True
    return False


def _replace_first_sound(text: str, substitutes: dict[str, str]) -> str:
    sounds = sorted(substitutes, key=len, reverse=True)
    for index in range(len(text)):
        for sound in sounds:
            if not text.startswith(sound, index):
                continue
            if len(sound) == 1 and _inside_other_digraph(text, index, sound):
                continue
            return text[:index] + substitutes[sound] + text[index + len(sound):]
    return text


def greek_vowel_confusion_variants(text: str) -> list[str]:
    """Homophone misspellings: the same sound written with a different Greek vowel."""
    base = strip_greek_accents(text).lower()
    variants: list[str] = []
    for substitutes in _SOUND_SUBSTITUTES:
        candidate = _replace_first_sound(base, substitutes)
        if candidate != base and candidate not in variants:
            variants.append(candidate)
    return variants


def greek_final_sigma_error(text: str) -> str:
    """Write a word-final ς as σ, as happens on some mobile keyboards."""
    words = strip_greek_accents(text).lower().split()
    changed = [word[:-1] + "σ" if word.endswith("ς") else word for word in words]
    return " ".join(changed)


def _longest_word_index(words: list[str]) -> int:
    return max(range(len(words)), key=lambda i: (len(words[i]), -i)) if words else -1


def missing_letter(text: str) -> str:
    """Drop one interior letter from the longest word."""
    words = str(text or "").split()
    index = _longest_word_index(words)
    if index < 0 or len(words[index]) < 5:
        return ""
    word = words[index]
    position = len(word) // 2
    words[index] = word[:position] + word[position + 1:]
    return " ".join(words)


def swapped_letters(text: str) -> str:
    """Transpose two adjacent interior letters of the longest word."""
    words = str(text or "").split()
    index = _longest_word_index(words)
    if index < 0 or len(words[index]) < 4:
        return ""
    word = list(words[index])
    position = max(1, len(word) // 2 - 1)
    if word[position] == word[position + 1]:
        return ""
    word[position], word[position + 1] = word[position + 1], word[position]
    words[index] = "".join(word)
    return " ".join(words)


def doubled_letter(text: str) -> str:
    """Type one letter of the longest word twice."""
    words = str(text or "").split()
    index = _longest_word_index(words)
    if index < 0 or len(words[index]) < 4:
        return ""
    word = words[index]
    position = len(word) // 2
    words[index] = word[:position] + word[position] + word[position:]
    return " ".join(words)


def joined_words(text: str) -> str:
    """Forget the space between words."""
    words = str(text or "").split()
    if len(words) < 2:
        return ""
    return "".join(words)


# --------------------------------------------------------------------------------------
# English keyboard slips
# --------------------------------------------------------------------------------------

_QWERTY_NEIGHBOURS = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij",
    "i": "uok", "o": "ipl", "p": "ol", "a": "qsz", "s": "adw", "d": "sfe", "f": "dgr",
    "g": "fht", "h": "gjy", "j": "hku", "k": "jli", "l": "ko", "z": "xa", "x": "zcs",
    "c": "xvd", "v": "cbf", "b": "vng", "n": "bmh", "m": "nj",
}


def english_keyboard_slip(text: str) -> str:
    """Press a neighbouring QWERTY key for one interior letter of the longest word."""
    words = str(text or "").split()
    index = _longest_word_index(words)
    if index < 0 or len(words[index]) < 4:
        return ""
    word = words[index]
    for position in range(len(word) // 2, len(word) - 1):
        neighbours = _QWERTY_NEIGHBOURS.get(word[position])
        if neighbours:
            words[index] = word[:position] + neighbours[0] + word[position + 1:]
            return " ".join(words)
    return ""
