"""Whether a feed product can be found in a product database, and by what key.

Owner decision, 2026-10-12: PicWise was being built on the wrong source. An affiliate
feed is an **offer** source -- price, availability, the buy link -- not a **product**
source. Specifications and ratings come from a product database and a rating source.

That makes one question decide whether a shop is usable at all: can its products be
looked up? Every product database is keyed by a GTIN or by a brand plus the
manufacturer's part code, so a product carrying neither can never be enriched, and can
never be ranked on anything but its price.

These tests pin that a filled identifier column is not an identifier. The first real
feed has one merchant writing product names into `upc` ("Atletico Madrid Bambo Classic
Hat") and SKU codes into `isbn`, and counting those as keys would report a shop as
usable when nothing about its products can be found.

Values here are local test data, in the shapes the real feed used.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.product_identity import (  # noqa: E402
    gtin_is_valid,
    read_product_identity,
)


class GtinTests(unittest.TestCase):
    def test_a_real_gtin_is_accepted(self) -> None:
        # EAN-13 and UPC-12 from the real feed's own rows.
        for value in ("5412810295623", "5412810295753", "725712278195"):
            with self.subTest(value=value):
                self.assertTrue(gtin_is_valid(value))

    def test_a_wrong_check_digit_is_not_a_gtin(self) -> None:
        # The check digit is the whole point: it separates a GTIN from any other number
        # a merchant put in the column.
        self.assertFalse(gtin_is_valid("5412810295624"))

    def test_the_wrong_length_is_not_a_gtin(self) -> None:
        for value in ("123", "12345678901", "123456789012345"):
            with self.subTest(value=value):
                self.assertFalse(gtin_is_valid(value))

    def test_text_in_an_identifier_column_is_not_a_gtin(self) -> None:
        # Both of these are real shapes from the feed's `upc` and `isbn` columns.
        for value in ("Atletico Madrid Bambo Classic Hat", "atm-2093-1110", "", None):
            with self.subTest(value=value):
                self.assertFalse(gtin_is_valid(value))

    def test_all_zeroes_is_not_a_gtin(self) -> None:
        # Passes the check digit arithmetic and identifies nothing.
        self.assertFalse(gtin_is_valid("0000000000000"))

    def test_separators_are_ignored(self) -> None:
        self.assertTrue(gtin_is_valid("5-412810-295623"))


class IdentityTests(unittest.TestCase):
    def test_a_gtin_is_the_strongest_key(self) -> None:
        identity = read_product_identity(
            {"ean": "5412810295623", "mpn": "A-CAB141631"}, brand="Nedis"
        )
        self.assertTrue(identity.matchable)
        self.assertEqual(identity.key, "gtin:5412810295623")

    def test_a_brand_with_a_part_code_is_a_key(self) -> None:
        identity = read_product_identity({"mpn": "A-CAB141631"}, brand="Nedis")
        self.assertTrue(identity.matchable)
        self.assertEqual(identity.key, "brand:nedis/part:a-cab141631")

    def test_a_part_code_without_a_brand_is_not_a_key(self) -> None:
        # A part code is not unique across manufacturers, so alone it finds nothing.
        identity = read_product_identity({"mpn": "A-CAB141631"})
        self.assertFalse(identity.matchable)
        self.assertEqual(identity.key, "")

    def test_a_colour_in_a_model_column_is_not_a_part_code(self) -> None:
        for value in ("Black", "Olive", "Matte"):
            with self.subTest(value=value):
                self.assertFalse(read_product_identity({"mpn": value}, brand="Nedis").matchable)

    def test_a_title_in_a_part_code_column_is_not_a_part_code(self) -> None:
        identity = read_product_identity(
            {"mpn": "Nedis Balanced Audio Cable 2x XLR 3-Pin Male"}, brand="Nedis"
        )
        self.assertFalse(identity.matchable)

    def test_a_shop_that_sends_nothing_is_not_matchable(self) -> None:
        # Geekbuying's 877 rows: a title and a price, no identifier of any kind.
        self.assertFalse(read_product_identity({}).matchable)
        self.assertFalse(read_product_identity({"product_name": "Xiaomi TV S Pro 55"}).matchable)

    def test_the_brand_column_is_read_when_no_brand_is_passed(self) -> None:
        identity = read_product_identity({"brand_name": "Nedis", "mpn": "A-CAB141631"})
        self.assertEqual(identity.brand, "Nedis")
        self.assertTrue(identity.matchable)

    def test_a_junk_gtin_falls_through_to_the_part_code(self) -> None:
        # The merchant with product names in `upc` still has a usable `mpn`.
        identity = read_product_identity(
            {"upc": "Atletico Madrid Bambo Classic Hat", "mpn": "FI-2071-1358"},
            brand="Fan Ink",
        )
        self.assertEqual(identity.gtin, "")
        self.assertTrue(identity.matchable)
        self.assertEqual(identity.key, "brand:fan ink/part:fi-2071-1358")

    def test_the_same_product_from_two_shops_has_the_same_key(self) -> None:
        # Which is the point: a product database answers once for both offers.
        one = read_product_identity({"ean": "5412810295623"}, brand="Nedis")
        two = read_product_identity({"product_GTIN": "5412810295623"}, brand="NEDIS")
        self.assertEqual(one.key, two.key)


if __name__ == "__main__":
    unittest.main()
