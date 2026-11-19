"""One card per product, its sizes and colours chosen at the shop: the rule.

Owner, 2026-11-19: «ένα μαγαζί πουλάει ένα ζευγάρι παπούτσια και το βγάζει σε έξι
διαφορετικά νούμερα και τέσσερα διαφορετικά χρώματα αυτό κουράζει τον επισκέπτη ...
βλέπει τα νούμερα και τα χρώματα στο κατάστημα και όχι σε μας». Pinned here
(`picwise_providers.product_variants`): the title less the row's own colour and size;
the key the rows of one product share, by its group or, with none, by its brand; a group
holding different products kept apart; a row naming nothing no variant.

Every row is local test data: fictional brands and shops.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.product_variants import base_title, variant_key  # noqa: E402


class BaseTitleTests(unittest.TestCase):
    def test_the_row_s_own_colour_and_size_are_taken_out(self) -> None:
        self.assertEqual(base_title("Fluted Kettle 1.7L - Black", "Black"), "fluted kettle 1 7l")
        self.assertEqual(base_title("Fictional Runner Size 9", "", "9"), "fictional runner size")
        self.assertEqual(base_title("Fictional Runner Size 10", "", "10"), "fictional runner size")
        self.assertEqual(base_title("Hoodie Black/White M", "Black/White", "M"), "hoodie")
        self.assertEqual(base_title("Hoodie Navy and Red L", "Navy / Red", "L"), "hoodie and")

    def test_the_last_mention_goes_so_a_brand_keeps_its_name(self) -> None:
        self.assertEqual(base_title("Blackfix+Co Kettle Black", "Black"), "blackfix co kettle")
        self.assertEqual(base_title("Black+Fixture Kettle Black", "Black"), "black fixture kettle")
        self.assertEqual(base_title("Black+Fixture Kettle White", "White"), "black fixture kettle")


class VariantKeyTests(unittest.TestCase):
    def _key(self, title: str, group: str = "", colour: str = "", size: str = "", shop: str = "101",
             brand: str = "Fictional") -> str:
        return variant_key({"advertiser_id": shop, "title": title, "brand": brand, "item_group_id": group,
                            "color": colour, "size": size})

    def test_the_variants_of_one_product_share_their_key(self) -> None:
        black = self._key("Fictional Runner Black Size 8", "G1", "Black", "8")
        white = self._key("Fictional Runner White Size 9", "G1", "White", "9")
        self.assertTrue(black)
        self.assertEqual(black, white)
        # With no group, by brand and title.
        self.assertEqual(self._key("Fictional Mug Red", colour="Red"), self._key("Fictional Mug Blue", colour="Blue"))

    def test_different_products_shops_or_brands_are_kept_apart(self) -> None:
        self.assertNotEqual(self._key("Fictional Kettle Black", "G2", "Black"), self._key("Fictional Toaster Black", "G2", "Black"))
        self.assertNotEqual(self._key("Fictional Mug Red", colour="Red"), self._key("Fictional Mug Red", colour="Red", shop="102"))
        self.assertNotEqual(self._key("Fictional Mug Red", colour="Red"),
                            self._key("Fictional Mug Blue", colour="Blue", brand="Otherbrand"))
        self.assertNotEqual(self._key("Fictional Runner Black", "G1", "Black"), self._key("Fictional Runner Black", "G9", "Black"))

    def test_a_row_naming_no_group_colour_or_size_is_no_variant(self) -> None:
        self.assertEqual(self._key("Fictional Plate"), "")
        self.assertEqual(variant_key({}), "")
        self.assertEqual(variant_key(None), "")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
