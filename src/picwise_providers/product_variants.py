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

GROUP_KEYS = ("item_group_id",)
COLOUR_KEYS = ("color", "colour")
SIZE_KEYS = ("size",)
_SHOP_KEYS = ("advertiser_id", "merchant_id", "advertiser_name", "merchant_name")
_BRAND_KEYS = ("brand", "brand_name")
_TITLE_KEYS = ("title", "product_name", "name")
# A colour or size written as several: "Black/White", "S, M", "Navy | Red".
_PARTS_RE = re.compile(r"\s*(?:/|,|;|\|)\s*")
_WORDS_RE = re.compile(r"[^0-9a-z]+")


def _value(raw: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip():
            return " ".join(str(value).split())
    return ""


def _words(text: str) -> list[str]:
    return [word for word in _WORDS_RE.split(text.lower()) if word]


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
