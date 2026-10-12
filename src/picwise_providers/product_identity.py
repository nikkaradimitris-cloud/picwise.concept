"""Whether a feed product can be found in a product database, and by what key.

Owner decision (2026-10-12): PicWise was being built on the wrong source. An affiliate
feed is an **offer** source -- price, availability, the buy link -- not a **product**
source. The facts a decision needs (specifications, and a rating) come from a product
database and a rating source, and the feed supplies what only a merchant can.

That makes one question decide whether a feed is usable at all: **can its products be
found in a product database?** Every such database -- Icecat and the rest -- is keyed
by a GTIN (EAN/UPC/JAN) or by a brand plus the manufacturer's part code. A product
carrying neither cannot be looked up, cannot be enriched, and therefore cannot be
ranked on anything but its price, however good the rest of its row is.

A filled identifier column is not an identifier. In the first real feed one merchant
writes product names into `upc` ("Atletico Madrid Bambo Classic Hat") and SKU codes
into `isbn`, so a column is trusted here only when its value survives a check:

- a **GTIN** must be 8, 12, 13 or 14 digits and its check digit must agree, which is
  what a GTIN is for;
- a **part code** must look like a code rather than a sentence, so a title dropped into
  `mpn` is not mistaken for a manufacturer reference, and it is only usable together
  with a brand, because a part code alone is not unique across manufacturers.

Measured on the first real feed (11,573 products, 2026-10-12): 59% carry a valid GTIN,
63% a brand with a part code, and 65% at least one of the two -- but the split by shop
is almost total. Boxed2me, Aperturee, Tooled Up, Plusshop and Bazta are at 99-100%,
while TV Cables (1,745 products), Geekbuying (877), AmberPromos and Printerval are at
**0%**: they send no identifier of any kind. So Geekbuying's televisions, TV boxes and
vacuum cleaners cannot be rescued by a product database either -- there is no key to
look them up with.

Nothing here judges a product. It reports whether the feed said enough for the product
to be known.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

# The columns a GTIN may arrive in, in the order they are trusted. `upc` and `isbn`
# are included because merchants do use them, and excluded in practice by the check
# digit when what they hold is not a GTIN.
GTIN_KEYS = ("ean", "product_GTIN", "gtin", "upc", "isbn")
# The columns a manufacturer's part code may arrive in.
PART_CODE_KEYS = ("mpn", "model_number", "product_model", "manufacturer_part_number")
BRAND_KEYS = ("brand_name", "brand", "manufacturer")

_NON_DIGITS = re.compile(r"\D")
# A part code is a reference, not a sentence. Four or more spaces means prose.
_MAX_PART_CODE_WORDS = 4
_MIN_PART_CODE_CHARS = 3
_MAX_PART_CODE_CHARS = 40


@dataclass(frozen=True)
class ProductIdentity:
    """The keys a product database could be asked for this product with."""

    gtin: str = ""
    brand: str = ""
    part_code: str = ""

    @property
    def matchable(self) -> bool:
        """Can this product be looked up in a product database at all?"""
        return bool(self.gtin or (self.brand and self.part_code))

    @property
    def key(self) -> str:
        """The strongest key available, or "". A GTIN identifies one product globally."""
        if self.gtin:
            return f"gtin:{self.gtin}"
        if self.brand and self.part_code:
            return f"brand:{self.brand.lower()}/part:{self.part_code.lower()}"
        return ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gtin": self.gtin,
            "brand": self.brand,
            "part_code": self.part_code,
            "matchable": self.matchable,
            "key": self.key,
        }


def gtin_is_valid(value: Any) -> bool:
    """A GTIN-8/12/13/14 whose check digit agrees.

    The check digit is the whole point of a GTIN: it is what separates a real one from
    a SKU, a price or a product name that a merchant put in the same column.
    """
    digits = _NON_DIGITS.sub("", str(value or ""))
    if len(digits) not in (8, 12, 13, 14):
        return False
    if not digits.strip("0"):
        return False
    body, check = digits[:-1], int(digits[-1])
    total = 0
    for index, char in enumerate(reversed(body)):
        total += int(char) * (3 if index % 2 == 0 else 1)
    return (10 - total % 10) % 10 == check


def _looks_like_a_part_code(value: str) -> bool:
    text = " ".join(str(value or "").split())
    if not _MIN_PART_CODE_CHARS <= len(text) <= _MAX_PART_CODE_CHARS:
        return False
    if len(text.split()) > _MAX_PART_CODE_WORDS:
        return False
    # A reference carries at least one digit or one run of capitals; a plain word does
    # not, and "Black" in a model column is a colour, not a model.
    return bool(re.search(r"\d", text)) or bool(re.search(r"[A-Z]{2,}", text))


def read_product_identity(
    row: Mapping[str, Any] | None,
    *,
    brand: str = "",
) -> ProductIdentity:
    """The product-database keys this feed row carries, after checking each one."""
    raw = row if isinstance(row, Mapping) else {}
    gtin = ""
    for key in GTIN_KEYS:
        value = raw.get(key)
        if gtin_is_valid(value):
            gtin = _NON_DIGITS.sub("", str(value))
            break
    part_code = ""
    for key in PART_CODE_KEYS:
        value = " ".join(str(raw.get(key) or "").split())
        if _looks_like_a_part_code(value):
            part_code = value
            break
    name = " ".join(str(brand or "").split())
    if not name:
        for key in BRAND_KEYS:
            name = " ".join(str(raw.get(key) or "").split())
            if name:
                break
    return ProductIdentity(gtin=gtin, brand=name, part_code=part_code)
