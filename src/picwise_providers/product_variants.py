"""One card per product: its sizes and colours are chosen at the shop.

Owner, 2026-11-19: «ένα μαγαζί πουλάει ένα ζευγάρι παπούτσια και το βγάζει σε έξι
διαφορετικά νούμερα και τέσσερα διαφορετικά χρώματα αυτό κουράζει τον επισκέπτη γιατί
βλέπει ουσιαστικά το ίδιο προϊόν ... βλέπει τα νούμερα και τα χρώματα στο κατάστημα και
όχι σε μας».

Google's format, the feed the server reads, ties a product's variants with
`item_group_id` and names each row's `color` and `size`. Two rows of one shop are one
product when they share their group (with no group, their brand) and their titles are
the same once each row's own colour and size are taken out of it. A shop whose group
holds different products (their titles differ beyond colour and size) keeps them apart.
A row that names no group, no colour and no size is no variant: rows with the very same
title are already one card (`search_selection`).
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Mapping
from urllib.parse import urlsplit

GROUP_KEYS = ("item_group_id",)
# Google's column only: Awin's own `colour` is one the prepared catalogue leaves out.
COLOUR_KEYS = ("color",)
SIZE_KEYS = ("size",)
_SHOP_KEYS = ("advertiser_id", "merchant_id", "advertiser_name", "merchant_name")
_BRAND_KEYS = ("brand", "brand_name")
_TITLE_KEYS = ("title", "product_name", "name")
# A colour or size written as several: "Black/White", "S, M", "Navy | Red".
_PARTS_RE = re.compile(r"\s*(?:/|,|;|\|)\s*")
_WORDS_RE = re.compile(r"[0-9a-z]+")


def _value(raw: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip():
            return " ".join(str(value).split())
    return ""


def _words(text: str) -> list[str]:
    return _WORDS_RE.findall(text.lower())


def _without_last(words: list[str], named: list[str]) -> tuple[list[str], bool]:
    """`words` with the last run of `named` taken out, and whether there was one."""
    width = len(named)
    for start in range(len(words) - width, -1, -1):
        if words[start:start + width] == named:
            return words[:start] + words[start + width:], True
    return words, False


def base_title(title: str, colour: str = "", size: str = "") -> str:
    """The title with the row's own colour and size taken out once each, as plain
    lower-case words: "Fluted Kettle 1.7L - Black" with colour "Black" is "fluted kettle 1
    7l". The last mention goes, so a brand that holds a colour ("Black+Decker ... Black")
    keeps its name. A value written as several ("Black/White") goes whole, else part by
    part."""
    words = _words(title)
    for value in (colour, size):
        named = _words(value)
        if not named:
            continue
        words, found = _without_last(words, named)
        if found:
            continue
        for part in _PARTS_RE.split(value):
            part_words = _words(part)
            if part_words and part_words != named:
                words, _ = _without_last(words, part_words)
    return " ".join(words)


def variant_key(raw: Mapping[str, Any], *, shop: str = "", title: str = "", brand: str = "") -> str:
    """The key the rows of one product share, sizes and colours aside; "" for a row that
    names no group, colour or size. `shop`, `title` and `brand` default to the row's own."""
    if not isinstance(raw, dict) and not isinstance(raw, Mapping):
        return ""
    group = _value(raw, GROUP_KEYS)
    colour = _value(raw, COLOUR_KEYS)
    size = _value(raw, SIZE_KEYS)
    if not (group or colour or size):
        return ""
    shop = shop or _value(raw, _SHOP_KEYS)
    title = title or _value(raw, _TITLE_KEYS)
    base = base_title(title, colour, size)
    if not shop or not base:
        return ""
    if group:
        return f"{shop}\x1fgroup:{group}\x1f{base}"
    brand = (brand or _value(raw, _BRAND_KEYS)).lower()
    return f"{shop}\x1fbrand:{brand}\x1f{base}"


# The shop's own page of a product (Google's `link`): a shop selling one product in sizes
# and colours often lists each as a row with the same page, the choice in its address
# ("/products/runner?variant=111"). The page, less its query, is where the visitor picks
# the size and colour (2026-11-19: the feed names a group, colour or size on 81, 108 and
# 94 of 1,683,586 rows, so those columns tie almost nothing).
_LINK_KEYS = ("link",)
_VARIANT_QUERY_RE = re.compile(r"(?:^|&)(?:variant|size|colou?r|sku|option)[^=&]*=", re.IGNORECASE)
# The parts of an address that pick a variant or only track a visit: left out of the page.
# The rest stay, so "product.php?id=12" and "?id=13" are two pages, not one.
_NOT_THE_PAGE_RE = re.compile(
    r"^(?:variant|size|colou?r|sku|option|attribute|utm_|ref$|source$|awc$|gclid$|fbclid$|srsltid$|"
    r"currency$|country$|lang$|aff|cid$|clickref$|campaign)",
    re.IGNORECASE,
)


def page_key(raw: Mapping[str, Any], *, shop: str = "") -> str:
    """The shop and its product page (host and path, lower case, no query) a row links to;
    "" when it links to none, or to a shop's front page."""
    if not isinstance(raw, dict) and not isinstance(raw, Mapping):
        return ""
    link = raw.get("link")
    if not link:
        return ""
    # Read by hand, not by `urlsplit`: this runs on every product of an answer.
    address, _, query = str(link).strip().split("#", 1)[0].partition("?")
    start = address.find("://")
    if start < 0:
        return ""
    rest = address[start + 3:]
    cut = rest.find("/")
    if cut <= 0:
        return ""
    host, path = rest[:cut].lower(), rest[cut:].rstrip("/").lower()
    if not path:
        return ""
    if query:
        kept = sorted(
            part for part in query.split("&") if part and not _NOT_THE_PAGE_RE.match(part.split("=", 1)[0])
        )
        if kept:
            path += "?" + "&".join(kept)
    shop = shop or _value(raw, _SHOP_KEYS)
    return f"{shop}\x1f{host}{path}"


def names_a_variant(raw: Mapping[str, Any]) -> bool:
    """Whether the row's own page address names a variant ("?variant=111", "?size=9")."""
    link = _value(raw, _LINK_KEYS) if isinstance(raw, Mapping) else ""
    if not link:
        return False
    try:
        return bool(_VARIANT_QUERY_RE.search(urlsplit(link).query))
    except ValueError:
        return False


# Words that name a size, not a product: a number ("9", "12", "100"), a number and its
# unit or letters ("2xl", "10y", "18m", "128gb"), a letter size, and the words around
# sizes. On one page they tell the variants apart, so they are not counted as a difference
# (2026-11-19: "The Bear Colour Tracksuit - GRAY / 12-18 M" and "- Pink / 3-4 Y", one
# page, differed by four words, all but the colour a size).
_SIZE_WORD_RE = re.compile(r"^(?:\d+[a-z]{0,3}|x{0,3}[sl]|x{1,3}|m|xxl|xxxl|uk|eu|us|y|yr|yrs|years?|months?|mths?)$")


def title_words(title: str) -> frozenset[str]:
    """A title's words, lower case, as `titles_close` compares them: its sizes left out."""
    return frozenset(word for word in _words(title) if not _SIZE_WORD_RE.match(word))


def words_close(first: frozenset[str], second: frozenset[str], *, most: int = 3) -> bool:
    """`titles_close` on titles already read as words (`title_words`)."""
    if not (first and second):
        return False
    apart = max(len(first - second), len(second - first))
    return apart <= most and len(first & second) > apart


def titles_close(first: str, second: str, *, most: int = 3) -> bool:
    """Whether two titles differ as a size or a colour makes them differ: sizes aside
    (`title_words`), each has at most `most` words the other lacks, and they share more
    words than either lacks ("Runner White Size 9" and "Runner Black Size 8": one each,
    three shared), while the products of a shop's list page differ by more."""
    return words_close(title_words(first), title_words(second), most=most)


# A shop listing each variant as a product of its own, each on a page of its own
# (owner, 2026-11-19: «Στην περίπτωση που δεν διαθέτει διαφορετικές παραλλαγές του
# προϊόντος σε μία καταχώρηση ... φτιάχνουμε το σύστημα με τα ομαδοποιημένα προϊόντα ...
# εκεί εμπλέκεται και το σύστημα ai»). A title is read as the product's own words and the
# words that may name a variant: a colour, a size, a number. Two products of one shop and
# brand whose own words are the same are one product when the words that differ are sizes
# or amounts with their unit ("S" and "2XL", "500GB" and "1TB", "1.5L" and "1.7L"); when a
# colour or a bare number differs ("Red Wine Glass" and "White Wine Glass", "iPhone 15"
# and "iPhone 16") the AI decides, at once and again each night (`variant_families`).
_COLOURS = frozenset(
    """black white grey gray silver gold red blue navy green pink purple yellow orange brown
    beige cream ivory khaki olive teal turquoise burgundy maroon charcoal rose champagne
    bronze copper nude tan camel mint lilac lavender coral aqua mustard plum stone sand taupe
    violet indigo magenta cyan lime peach multicolour multicolor multi clear transparent
    natural oatmeal ecru mocha espresso graphite slate gunmetal""".split()
)
_LETTER_SIZES = frozenset("xxs xs s m l xl xxl xxxl 2xl 3xl 4xl 5xl 6xl".split())
# The words that come with a size: "Size 9", "UK 9", "EU 42".
_SIZE_WORDS = frozenset("size sizes uk eu us".split())
# An amount and its unit, one word as `_words` reads it: "500gb", "7l" (of "1.7L"), "18v".
_AMOUNT_RE = re.compile(
    r"^\d+(?:gb|tb|mb|ml|l|ltr|litre|liter|w|kw|mah|v|cm|mm|m|kg|g|oz|in|inch|ft|pcs|pc|pk|pack)$"
)
_NUMBER_RE = re.compile(r"^\d+[a-z]*$")
CERTAIN = "certain"
DOUBTFUL = "doubtful"


# A number after a size word is a size ("Size 9", "UK 10"), kept as "~9".
_SIZED_NUMBER = "~"
_DECIMAL_RE = re.compile(r"(\d)[.,](\d)")


def _variant_word(word: str) -> str:
    """"size" for a size or an amount with its unit, "other" for a colour or a number that
    may name a model, "" for one of the product's own words."""
    if word.startswith(_SIZED_NUMBER) or word in _LETTER_SIZES or word in _SIZE_WORDS or _AMOUNT_RE.match(word):
        return "size"
    if word in _COLOURS or _NUMBER_RE.match(word):
        return "other"
    return ""


@lru_cache(maxsize=262144)
def title_parts(title: str) -> tuple[str, frozenset[str]]:
    """A title's own words (the words that name no variant, in order, once each) and the
    words that may name a variant. "1.7L" is read as one amount ("17l")."""
    own: list[str] = []
    variant: set[str] = set()
    previous = ""
    for word in _words(_DECIMAL_RE.sub(r"\1\2", str(title or ""))):
        if previous in _SIZE_WORDS and word.isdigit():
            variant.add(_SIZED_NUMBER + word)
        elif _variant_word(word):
            variant.add(word)
        elif word not in own:
            own.append(word)
        previous = word
    return " ".join(own), frozenset(variant)


def family_key(*, shop: str, brand: str, title: str) -> str:
    """The key the products of one shop and brand with the same own words share; "" when a
    title has fewer than two words of its own, too few to tell a product."""
    own, _variant = title_parts(title)
    if not shop or len(own.split()) < 2:
        return ""
    return f"{shop}\x1f{brand.strip().lower()}\x1f{own}"


# Where a shop's title passes from the product's name to its variant: "Satin Sleep Mask -
# Snake Print - Sleep Mask Only", "Mug | Personalised", "Runner, Black".
_HEAD_END_RE = re.compile(r"\s[-\u2013\u2014|]\s|,\s")


def head_key(*, shop: str, brand: str, title: str) -> str:
    """The family key of a title's head, its words before the first " - ", " | " or ", ",
    when the head has two words of its own at least; else the whole title's
    (`family_key`). One shop's prints, designs and finishes of a product, named in words
    no list of colours holds ("- Snake Print -", "- Cheetah Print -"), share it, so that
    the AI is asked whether they are one product."""
    head = _HEAD_END_RE.split(title, maxsplit=1)[0]
    if head != title:
        key = family_key(shop=shop, brand=brand, title=head)
        if key:
            return key
    return family_key(shop=shop, brand=brand, title=title)


def sizes_apart_key(*, shop: str, brand: str, title: str) -> str:
    """The key the products of one family key share when only sizes or amounts tell them
    apart: their colours and numbers are part of it, so two products with the same one
    are `CERTAIN` one product ("" when the title has no family key)."""
    key = family_key(shop=shop, brand=brand, title=title)
    if not key:
        return ""
    others = sorted(word for word in title_parts(title)[1] if _variant_word(word) == "other")
    return f"{key}\x1f{' '.join(others)}"


def variant_difference(first: str, second: str) -> str:
    """How two titles of one family key differ: "" not at all, `CERTAIN` by sizes or amounts
    only, `DOUBTFUL` by a colour or a number."""
    apart = title_parts(first)[1] ^ title_parts(second)[1]
    if not apart:
        return ""
    if all(_variant_word(word) == "size" for word in apart):
        return CERTAIN
    return DOUBTFUL
