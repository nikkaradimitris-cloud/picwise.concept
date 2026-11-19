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
from typing import Any, Mapping
from urllib.parse import urlsplit

GROUP_KEYS = ("item_group_id",)
COLOUR_KEYS = ("color", "colour")
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
    if not isinstance(raw, Mapping):
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
    if not isinstance(raw, Mapping):
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


def title_words(title: str) -> frozenset[str]:
    """A title's words, lower case, as `titles_close` compares them."""
    return frozenset(_words(title))


def words_close(first: frozenset[str], second: frozenset[str], *, most: int = 3) -> bool:
    """`titles_close` on titles already read as words (`title_words`)."""
    return bool(first and second) and len(first - second) <= most and len(second - first) <= most


def titles_close(first: str, second: str, *, most: int = 3) -> bool:
    """Whether two titles differ as a size or a colour makes them differ: each has at most
    `most` words the other lacks ("Runner White Size 9" and "Runner Black Size 8": two
    each), while the products of a shop's list page differ by more."""
    return words_close(title_words(first), title_words(second), most=most)
