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

from picwise_providers.product_variants import (  # noqa: E402
    CERTAIN,
    DOUBTFUL,
    base_title,
    family_key,
    page_key,
    sizes_apart_key,
    title_parts,
    titles_close,
    variant_difference,
    variant_key,
)


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


class PageKeyTests(unittest.TestCase):
    def _page(self, link: str, shop: str = "Fixture Shoes") -> str:
        return page_key({"merchant_name": shop, "link": link})

    def test_a_variant_s_choice_and_a_visit_s_tracking_are_not_the_page(self) -> None:
        page = self._page("https://shoes.example.invalid/products/runner")
        self.assertTrue(page)
        for link in (
            "https://Shoes.example.invalid/products/Runner/?variant=111",
            "https://shoes.example.invalid/products/runner?size=9&colour=Black#reviews",
            "https://shoes.example.invalid/products/runner?attribute_pa_size=9&utm_source=awin&awc=1",
        ):
            with self.subTest(link=link):
                self.assertEqual(self._page(link), page)

    def test_a_product_named_in_the_address_is_its_own_page(self) -> None:
        self.assertNotEqual(self._page("https://shop.example.invalid/product.php?id=12"),
                            self._page("https://shop.example.invalid/product.php?id=13"))
        self.assertNotEqual(self._page("https://shop.example.invalid/index.php?route=product/product&product_id=50"),
                            self._page("https://shop.example.invalid/index.php?route=product/product&product_id=51"))

    def test_a_front_page_another_shop_or_no_link_is_no_shared_page(self) -> None:
        self.assertEqual(self._page("https://shop.example.invalid/"), "")
        self.assertEqual(self._page("https://shop.example.invalid"), "")
        self.assertEqual(page_key({"merchant_name": "Fixture Shoes"}), "")
        self.assertNotEqual(self._page("https://shoes.example.invalid/products/runner"),
                            self._page("https://shoes.example.invalid/products/runner", shop="Fixture Other"))

    def test_titles_close_as_a_size_or_colour_makes_them(self) -> None:
        self.assertTrue(titles_close("Fixturon Runner Black Size 8", "Fixturon Runner White Size 9"))
        self.assertTrue(titles_close("1.7L Fast-Boil Cordless Beige Electric Kettle",
                                     "1.7L Fast-Boil Cordless Black Electric Kettle"))
        self.assertFalse(titles_close("Fixturon Runner Black Size 8", "Fixturon Garden Hose Reel With Wall Bracket"))
        # Sizes are not counted as a difference: a colour and an age range, one page.
        self.assertTrue(titles_close("Fixturon Bear Tracksuit 100% Cotton - GRAY / 12-18 M",
                                     "Fixturon Bear Tracksuit 100% Cotton - Pink / 3-4 Y"))
        self.assertTrue(titles_close("Fixturon Tracksuit - 2XL", "Fixturon Tracksuit - S"))
        self.assertFalse(titles_close("", "Fixturon Runner"))


class OwnWordsTests(unittest.TestCase):
    """A shop listing each variant as a product of its own (owner, 2026-11-19, rule 2)."""

    def test_a_title_is_its_own_words_and_the_words_that_may_name_a_variant(self) -> None:
        self.assertEqual(title_parts("Fixturon Runner Black Size 9"), ("fixturon runner", frozenset({"black", "size", "~9"})))
        self.assertEqual(title_parts("Fixturon Kettle 1.7L"), ("fixturon kettle", frozenset({"17l"})))

    def test_sizes_and_amounts_apart_are_certain_colours_and_numbers_doubtful(self) -> None:
        for first, second in (
            ("Fixturon Tracksuit - S", "Fixturon Tracksuit - 2XL"),
            ("Fixturon 870 EVO 500GB SSD", "Fixturon 870 EVO 1TB SSD"),
            ("Fixturon Kettle 1.7L", "Fixturon Kettle 2L"),
            ("Fixturon Runner Size 8", "Fixturon Runner UK 9"),
        ):
            with self.subTest(first=first):
                self.assertEqual(variant_difference(first, second), CERTAIN)
        for first, second in (
            ("Fixturon Red Wine Glass", "Fixturon White Wine Glass"),
            ("Fixturon Phone 15 128GB", "Fixturon Phone 16 128GB"),
            ("Fixturon 870 EVO 1TB SSD", "Fixturon 990 EVO 1TB SSD"),
        ):
            with self.subTest(first=first):
                self.assertEqual(variant_difference(first, second), DOUBTFUL)
        self.assertEqual(variant_difference("Fixturon Mug", "Fixturon Mug"), "")

    def test_the_keys_of_one_shop_and_brand(self) -> None:
        self.assertEqual(family_key(shop="s", brand="Fixturon", title="Phone 15"), "")  # one word of its own
        self.assertTrue(family_key(shop="s", brand="Fixturon", title="Fixturon Runner Black"))
        self.assertEqual(
            family_key(shop="s", brand="Fixturon", title="Fixturon Runner Black"),
            family_key(shop="s", brand="Fixturon", title="Fixturon Runner White Size 9"),
        )
        self.assertNotEqual(
            family_key(shop="s", brand="Fixturon", title="Fixturon Runner Black"),
            family_key(shop="t", brand="Fixturon", title="Fixturon Runner Black"),
        )
        # Sizes apart: one key; a colour apart: two.
        self.assertEqual(
            sizes_apart_key(shop="s", brand="Fixturon", title="Fixturon Runner Black Size 8"),
            sizes_apart_key(shop="s", brand="Fixturon", title="Fixturon Runner Black UK 9"),
        )
        self.assertNotEqual(
            sizes_apart_key(shop="s", brand="Fixturon", title="Fixturon Runner Black Size 8"),
            sizes_apart_key(shop="s", brand="Fixturon", title="Fixturon Runner White Size 8"),
        )

class HeadKeyTests(unittest.TestCase):
    def test_the_head_is_the_name_before_the_variant(self) -> None:
        from picwise_providers.product_variants import family_key, head_key

        def key(title: str) -> str:
            return head_key(shop="fixture shop", brand="", title=title)

        self.assertEqual(key("Satin Sleep Mask - Snake Print - Sleep Mask Only"), key("Satin Sleep Mask - Black"))
        self.assertEqual(key("Fixturon Runner | Cheetah"), key("Fixturon Runner, Leopard"))
        self.assertNotEqual(key("Satin Sleep Mask - Black"), key("Cloud Padded Satin Sleep Mask - Black"))
        # Without a head of two own words, the whole title's key.
        self.assertEqual(key("Fixturon Runner Black"), family_key(shop="fixture shop", brand="", title="Fixturon Runner Black"))
        self.assertEqual(key("Platinum - Lola's Leads Cable"),
                         family_key(shop="fixture shop", brand="", title="Platinum - Lola's Leads Cable"))
        # A hyphen inside a word or a range is not where a name ends.
        self.assertEqual(key("Fixturon T-Shirt Black"), family_key(shop="fixture shop", brand="", title="Fixturon T-Shirt Black"))
        self.assertEqual(head_key(shop="", brand="", title="Satin Sleep Mask - Black"), "")



if __name__ == "__main__":
    unittest.main()
