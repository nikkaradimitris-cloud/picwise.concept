"""The shops' own words for a kind, learned by review (the owner, 12/11: «να μαθαίνει νέες
λέξεις από τα καταστήματα», then «Ναι, προχώρα με όλα»).

A shop writes its own type on each product (its feed's `product_type`, or its own
catalogue's, which the shops' catalogue bot brings). PicWise reads a kind from that type
with its lexicon (`picwise_nlu.product_concepts`); a type the lexicon cannot read leaves
the product with no kind, found by its words only. Each night the note lists the types
of the products kept with no kind, the most first, with their shops and two titles
(`catalogue_balance`, `words_to_learn`; the server's report prints them).

A type is learned here only after review, and only when it plainly names a kind PicWise
already has, for the shop it was seen in or, written with no shop, for every shop. It is
never learned by itself: a word read wrongly fills a kind with wrong cards, and the
owner's bar is 98% right. A type naming a kind PicWise does not have is a proposal for
the lexicon, measured before it is added.

The table: (shop, type), both as written, compared without case and extra spaces; the
shop "" for every shop.
"""
from __future__ import annotations

from typing import Any, Mapping

from .normalization import extract_merchant_name

LEARNED_TYPES: dict[tuple[str, str], str] = {
    # Finediam's own type for its rings, from its catalogue (672 products named no kind on
    # 12/11). "ring" alone is a weak name in the lexicon, never classifying a feed row by
    # itself ("key ring", "O-ring"), so the type said nothing; in this jewellery shop's
    # catalogue it names a ring.
    ("Finediam", "Diamond Ring"): "ring",
}


def _key(text: str) -> str:
    return " ".join(str(text or "").split()).casefold()


_LEARNED = {(_key(shop), _key(product_type)): kind for (shop, product_type), kind in LEARNED_TYPES.items()}


def learned_kind(raw: Mapping[str, Any] | None, product_type: str) -> str:
    """The kind a reviewed shop type names, for this row's shop, or ""."""
    if not product_type or not _LEARNED:
        return ""
    wanted = _key(product_type)
    shop = _key(extract_merchant_name(raw if isinstance(raw, Mapping) else {}))
    return _LEARNED.get((shop, wanted)) or _LEARNED.get(("", wanted)) or ""
