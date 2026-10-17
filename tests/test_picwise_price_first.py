"""Price first: the owner's plan of 2026-10-15, settled on 2026-10-16.

`docs/picwise_price_first_plan_2026-10-15.md`. In the owner's words: «εμφανίζουμε πρώτα
αυτά με τη φθηνότερη τιμή και πάντα με σκληρό κριτήριο τη διαθεσιμότητα». What is
pinned here:

- the answer is every product of the kind asked for that carries the search's filters,
  cheapest first, each product once, from the cheapest shop that has it;
- the first page is one Recommended and then the three cheapest; "More" opens the next
  four cheapest, as often as asked, and nothing it opens is recommended;
- the Recommended is the middle product by price over the whole answer, leaving out
  extreme top prices, and carries an EAN/GTIN; with no product carrying one there is
  none;
- fewer than four are shown as they are, "2 of 2";
- the cards say "Recommended" with "Mid-priced for this category", and "Lowest price",
  or "Lowest price of N shops" when one product is sold by several.

Every row is written with fictional brands, and the page tests are served through
api/index.py, the deployed entry point, with `.invalid` URLs.
"""
from __future__ import annotations

import csv
import html
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.product_condition import (  # noqa: E402
    non_new_condition,
    stated_condition,
)
from picwise_providers.product_identity import same_product_key  # noqa: E402
from picwise_providers.search_selection import (  # noqa: E402
    _median_recommendation,
    _price_first_products,
    product_non_new_condition,
    provider_product_to_backend_dict,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_search.live_search_resolver import (  # noqa: E402
    MAX_SHOWN_PRODUCTS,
    parse_shown_count,
)


def _ean(number: int) -> str:
    """A valid EAN-13: twelve digits and the check digit that agrees with them."""
    body = str(number).zfill(12)
    total = sum(int(char) * (3 if index % 2 else 1) for index, char in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _offer(
    pid: str,
    price: float,
    *,
    gtin: str = "",
    mpn: str = "",
    model: str = "",
    brand: str = "Fixturon",
    shop: str = "Fixture Store One",
    title: str = "",
    currency: str = "GBP",
) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title or f"{brand} Kettle {pid}",
        brand=brand,
        category_text="Kettles",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=f"{price:.2f}",
        availability_text="in stock",
        currency=currency,
        raw={
            "ean": gtin,
            "mpn": mpn,
            "model_number": model,
            "brand_name": brand,
            "merchant_name": shop,
        },
    )


def _prices(entries) -> list[float]:
    return [entry.price for entry in entries]


class SameProductTests(unittest.TestCase):
    """Rule 5: the same product in several shops is shown once, from the cheapest."""

    def test_one_gtin_in_two_shops_is_one_product_at_the_cheaper_price(self) -> None:
        code = _ean(500000000001)
        ordered = _price_first_products(
            [
                _offer("a1", 30.0, gtin=code, shop="Fixture Store One"),
                _offer("a2", 25.0, gtin=code, shop="Fixture Store Two"),
                _offer("b1", 40.0, gtin=_ean(500000000002)),
            ]
        )
        self.assertEqual([entry.product.provider_product_id for entry in ordered], ["a2", "b1"])
        self.assertEqual(ordered[0].shops, 2)
        self.assertEqual(ordered[1].shops, 1)

    def test_upc_and_ean_forms_of_one_code_agree(self) -> None:
        upc = "036000291452"
        self.assertEqual(same_product_key({"ean": upc}), same_product_key({"ean": "0" + upc}))

    def test_brand_and_part_number_join_but_a_model_name_does_not(self) -> None:
        ordered = _price_first_products(
            [
                _offer("m1", 99.0, mpn="FX-2200-W", shop="Fixture Store One"),
                _offer("m2", 89.0, mpn="FX-2200-W", shop="Fixture Store Two"),
                # A model column can name a range: 128 GB and 256 GB of one phone.
                _offer("n1", 199.0, model="Nova A17", shop="Fixture Store One"),
                _offer("n2", 249.0, model="Nova A17", shop="Fixture Store Two"),
            ]
        )
        self.assertEqual(
            [entry.product.provider_product_id for entry in ordered], ["m2", "n1", "n2"]
        )
        self.assertEqual(ordered[0].shops, 2)

    def test_without_either_code_two_offers_are_never_joined(self) -> None:
        ordered = _price_first_products(
            [
                _offer("x1", 20.0, title="Fixturon Kettle White", shop="Fixture Store One"),
                _offer("x2", 22.0, title="Fixturon Kettle White", shop="Fixture Store Two"),
            ]
        )
        self.assertEqual(len(ordered), 2)

    def test_an_invalid_check_digit_is_not_a_code(self) -> None:
        self.assertEqual(same_product_key({"ean": "5000000000013"}), "")

    def test_one_currency_per_answer(self) -> None:
        ordered = _price_first_products(
            [
                _offer("g1", 20.0),
                _offer("g2", 30.0),
                _offer("e1", 10.0, currency="EUR"),
            ]
        )
        self.assertEqual([entry.product.currency for entry in ordered], ["GBP", "GBP"])


class RecommendedTests(unittest.TestCase):
    """Rule 7: the middle product by price, with an EAN/GTIN, over the whole answer."""

    def _answer(self, prices, *, codes=None):
        codes = codes if codes is not None else [True] * len(prices)
        return _price_first_products(
            [
                _offer(f"p{index}", price, gtin=_ean(500000000100 + index) if code else "")
                for index, (price, code) in enumerate(zip(prices, codes))
            ]
        )

    def _recommended_price(self, prices, *, codes=None):
        ordered = self._answer(prices, codes=codes)
        index, status = _median_recommendation(ordered)
        return (ordered[index].price if index is not None else None), status

    def test_the_middle_of_45_is_the_23rd(self) -> None:
        prices = [float(10 + step) for step in range(45)]
        self.assertEqual(self._recommended_price(prices), (32.0, "recommended"))

    def test_the_owners_example_recommends_150(self) -> None:
        # «£100, £150, £200 ... recommend £150»
        self.assertEqual(self._recommended_price([100.0, 150.0, 200.0]), (150.0, "recommended"))

    def test_an_extreme_top_price_does_not_count_but_stays_listed(self) -> None:
        # The owner's example: £1,000 is five times £200 and does not count.
        ordered = self._answer([100.0, 150.0, 200.0, 1000.0])
        index, status = _median_recommendation(ordered)
        self.assertEqual((ordered[index].price, status), (150.0, "recommended"))
        self.assertEqual(_prices(ordered)[-1], 1000.0)

    def test_extreme_prices_are_left_out_one_after_another(self) -> None:
        # £1,000 is at least twice £400, and then £400 at least twice £140.
        self.assertEqual(
            self._recommended_price([100.0, 120.0, 140.0, 400.0, 1000.0]),
            (120.0, "recommended"),
        )

    def test_a_price_under_twice_the_next_counts(self) -> None:
        self.assertEqual(
            self._recommended_price([100.0, 120.0, 140.0, 279.0, 300.0]),
            (140.0, "recommended"),
        )

    def test_of_an_even_number_the_cheaper_middle_one(self) -> None:
        self.assertEqual(
            self._recommended_price([100.0, 150.0, 200.0, 250.0]), (150.0, "recommended")
        )

    def test_without_a_code_the_nearest_with_one_and_the_cheaper_on_a_tie(self) -> None:
        self.assertEqual(
            self._recommended_price(
                [100.0, 140.0, 150.0, 160.0, 200.0], codes=[True, True, False, True, True]
            ),
            (140.0, "recommended"),
        )
        self.assertEqual(
            self._recommended_price(
                [100.0, 130.0, 150.0, 160.0, 200.0], codes=[True, True, False, True, True]
            ),
            (160.0, "recommended"),
        )

    def test_the_cheapest_or_the_dearest_is_never_called_mid_priced(self) -> None:
        # The nearest product with a code may be an end of a short list.
        self.assertEqual(
            self._recommended_price([100.0, 150.0, 200.0], codes=[True, False, True]),
            (None, "no_product_code"),
        )
        self.assertEqual(
            self._recommended_price([100.0, 100.0, 100.0]), (None, "too_few_products")
        )

    def test_an_extreme_price_is_never_the_recommended(self) -> None:
        self.assertEqual(
            self._recommended_price([100.0, 150.0, 200.0, 1000.0], codes=[False, False, False, True]),
            (None, "no_product_code"),
        )

    def test_no_code_on_any_product_means_no_recommended(self) -> None:
        self.assertEqual(
            self._recommended_price([100.0, 150.0, 200.0], codes=[False, False, False]),
            (None, "no_product_code"),
        )

    def test_two_products_have_no_middle(self) -> None:
        self.assertEqual(self._recommended_price([100.0, 150.0]), (None, "too_few_products"))


class GradedConditionTests(unittest.TestCase):
    """Graded titles are refurbished: price order put them first among laptops."""

    def test_a_grade_with_its_wording_is_not_new(self) -> None:
        for title in (
            'Fixturon Book 14" Windows 11 - White (Grade B - Average)',
            "Testline Elite 14 - Silver (Grade A - Good)",
            "Sampleworks AIO 27 (Grade A1 - Like New)",
        ):
            with self.subTest(title=title):
                self.assertTrue(non_new_condition(text=title))

    def test_grade_as_a_quality_word_is_new(self) -> None:
        for title in (
            "Fixturon Heavy Duty Commercial Grade TV Wall Mount - Fixed",
            "Testline Tab 11 military grade drop protection rugged case",
            "Sampleworks Medical Grade Shower Seat",
        ):
            with self.subTest(title=title):
                self.assertEqual(non_new_condition(text=title), "")


class DeclaredConditionTests(unittest.TestCase):
    """A data sheet in the description that says "Refurbished. Yes." is a declared field.

    Measured on the third real feed (2026-10-17): 22 refurbished laptops and desktops
    say so only there, and the search "lenovo thinkpad 16gb ram" would have opened with
    one of them as new. The prose around it is not read: 616 new UPS batteries say "No
    Refurbished or Re-used Parts".
    """

    def test_the_declared_field_says_refurbished(self) -> None:
        for description in (
            "Design. Product type. Laptop. Form factor. Clamshell. Refurbished. Yes. Display.",
            "Product colour: Black. Refurbished: Yes. Weight: 1.4 kg",
        ):
            with self.subTest(description=description):
                self.assertEqual(stated_condition({"description": description}), "refurbished")

    def test_prose_and_a_no_say_nothing(self) -> None:
        for description in (
            "Design. Product colour. Black. Refurbished. No. Colour name. Black.",
            "No Refurbished or Re-used Parts. Extensive Inventory Available.",
            "The highest quality refurbished laptops in the world.",
            "Compatibility. PIXMA iP2600, PIXMA iP2600 Refurbished, PIXMA iP6210D.",
        ):
            with self.subTest(description=description):
                self.assertEqual(stated_condition({"description": description}), "")

    def test_the_condition_column_still_wins(self) -> None:
        row = {"condition": "new", "description": "Refurbished. Yes."}
        self.assertEqual(stated_condition(row), "new")

    def test_the_gate_and_the_card_agree(self) -> None:
        product = _offer("r1", 300.0, gtin=_ean(700000000001))
        product.raw["description"] = "Form factor. Clamshell. Refurbished. Yes. Display."
        self.assertEqual(product_non_new_condition(product), "refurbished")
        card = provider_product_to_backend_dict(product)
        self.assertEqual(non_new_condition(text="", condition=card["condition"]), "refurbished")


class ShownCountTests(unittest.TestCase):
    def test_the_shown_parameter_is_a_bounded_whole_number(self) -> None:
        self.assertEqual(parse_shown_count(""), 0)
        self.assertEqual(parse_shown_count("abc"), 0)
        self.assertEqual(parse_shown_count("-8"), 0)
        self.assertEqual(parse_shown_count("8"), 8)
        self.assertEqual(parse_shown_count("0008"), 8)
        self.assertEqual(parse_shown_count("100000"), MAX_SHOWN_PRODUCTS)

    def test_a_hand_typed_shown_never_breaks_the_page(self) -> None:
        # "²" passes str.isdigit() and breaks int(); Python refuses to read a number
        # of more than 4,300 digits. Both reach the page from a typed address.
        self.assertEqual(parse_shown_count("²"), 0)
        self.assertEqual(parse_shown_count("٣"), 0)
        self.assertEqual(parse_shown_count("9" * 5000), MAX_SHOWN_PRODUCTS)
        self.assertEqual(parse_shown_count("0" * 5000 + "8"), 8)


_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
    "description", "data_provenance", "ean", "mpn",
)


class PriceFirstPageTests(unittest.TestCase):
    """The deployed page, end to end."""

    def _serve(self, rows: list[dict[str, str]]) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for row in rows:
                pid = row["pid"]
                title = row["title"]
                writer.writerow(
                    [pid, title, title.split()[0], row.get("type", "Kettles"),
                     row.get("category", "Kitchen Appliances"),
                     f"https://fixture.example.invalid/out/{pid}",
                     f"https://fixture.example.invalid/img/{pid}.jpg", row["price"], "GBP",
                     "1", row.get("shop", "Fixture Store One"), fixture_description(),
                     "local_test_fixture", row.get("ean", ""), row.get("mpn", "")]
                )
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if previous is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = previous
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def _page(self, query: str, shown: int = 0) -> str:
        def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
            return None

        params = {"q": query}
        if shown:
            params["shown"] = str(shown)
        return b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": urlencode(params),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        ).decode("utf-8")

    @staticmethod
    def _cards(page: str) -> list[dict[str, str]]:
        cards = []
        for recommended, card_id, body in re.findall(
            r'<article class="pw-card( pw-card-recommended)?" data-choice-id="([^"]+)">(.*?)</article>',
            page,
            flags=re.S,
        ):
            role = re.search(r'class="pw-role-label">(.*?)</p>', body)
            place = re.search(r'class="pw-card-description">(.*?)</p>', body)
            href = re.search(r'href="(/out/feed[^"]+)"', body)
            cards.append(
                {
                    "id": card_id,
                    "recommended": bool(recommended),
                    "role": html.unescape(role.group(1)) if role else "",
                    "place": html.unescape(place.group(1)) if place else "",
                    "rec": "rec=1" in html.unescape(href.group(1)) if href else False,
                    "badge": "pw-rec-badge" in body,
                }
            )
        return cards

    @staticmethod
    def _counter(page: str) -> str:
        match = re.search(r'class="pw-counter">(.*?)</p>', page)
        return match.group(1) if match else ""

    @staticmethod
    def _more_link(page: str) -> str:
        match = re.search(r'class="pw-more-button" href="([^"]+)"', page)
        return html.unescape(match.group(1)) if match else ""

    def _kettles(self, prices, *, codes=True, shop="Fixture Store One"):
        return [
            {
                "pid": f"k{index + 1}",
                "title": f"Fixturon Electric Kettle {index + 1} 1.7L",
                "price": f"{price:.2f}",
                "ean": _ean(500000001000 + index) if codes else "",
                "shop": shop,
            }
            for index, price in enumerate(prices)
        ]

    def test_the_recommended_comes_first_and_then_the_three_cheapest(self) -> None:
        # Nine kettles at £20 to £100: the middle one is the fifth, £60.
        self._serve(self._kettles([20, 30, 40, 50, 60, 70, 80, 90, 100]))
        page = self._page("kettle")
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k5", "k1", "k2", "k3"])
        self.assertTrue(cards[0]["recommended"] and cards[0]["badge"] and cards[0]["rec"])
        self.assertEqual(cards[0]["role"], "Mid-priced for this category")
        self.assertEqual(cards[0]["place"], "5th cheapest of 9")
        self.assertEqual([card["role"] for card in cards[1:]], ["Lowest price"] * 3)
        self.assertEqual(cards[1]["place"], "Cheapest of 9")
        self.assertFalse(any(card["recommended"] or card["rec"] for card in cards[1:]))
        self.assertEqual(self._counter(page), "4 of 9")
        self.assertIn("shown=8", self._more_link(page))
        self.assertIn("Results for: kettle, cheapest first", page)
        self.assertIn("The Recommended is mid-priced for this category.", page)

    def test_more_opens_the_next_four_cheapest_until_the_list_ends(self) -> None:
        self._serve(self._kettles([20, 30, 40, 50, 60, 70, 80, 90, 100]))
        page = self._page("kettle", shown=8)
        cards = self._cards(page)
        self.assertEqual(
            [card["id"] for card in cards], ["k5", "k1", "k2", "k3", "k4", "k6", "k7", "k8"]
        )
        # Nothing "More" opens is recommended or labelled as the lowest price.
        self.assertFalse(any(card["recommended"] or card["rec"] for card in cards[4:]))
        self.assertEqual([card["role"] for card in cards[4:]], [""] * 4)
        self.assertEqual(self._counter(page), "8 of 9")
        self.assertIn("shown=12", self._more_link(page))
        last = self._page("kettle", shown=12)
        self.assertEqual(len(self._cards(last)), 9)
        self.assertEqual(self._counter(last), "9 of 9")
        self.assertEqual(self._more_link(last), "")

    def test_no_product_appears_twice_however_far_more_is_pressed(self) -> None:
        # Replaces the second four of 2026-10-12, which only the kinds with no best
        # had, once (owner, 2026-10-15: "More" on every search, as often as asked).
        self._serve(self._kettles([float(20 + 5 * step) for step in range(14)]))
        for shown in (4, 8, 12, 16):
            with self.subTest(shown=shown):
                page = self._page("kettle", shown=shown)
                ids = [card["id"] for card in self._cards(page)]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(len(ids), min(shown, 14))
                self.assertEqual(sum(1 for card in self._cards(page) if card["recommended"]), 1)
                self.assertEqual(self._counter(page), f"{min(shown, 14)} of 14")

    def test_fewer_than_four_are_shown_as_they_are(self) -> None:
        self._serve(self._kettles([25, 35]))
        page = self._page("kettle")
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k1", "k2"])
        self.assertFalse(any(card["recommended"] for card in cards))
        self.assertEqual(self._counter(page), "2 of 2")
        self.assertEqual(self._more_link(page), "")
        self.assertIn("No Recommended here: these products have no middle price to pick.", page)
        # Of two, the middle price is the cheaper one's (owner, 2026-10-17).
        self.assertEqual([card["role"] for card in cards], ["Lowest price", ""])

    def test_without_a_recommended_lowest_price_goes_up_to_the_middle_price(self) -> None:
        # Owner, 2026-10-17, on three standing desks that all said "Lowest price": as
        # with a Recommended, only up to the middle price. The £630.99 one is extreme
        # (at least twice the next) and does not count, so the middle of the other two
        # is the cheaper one.
        self._serve(self._kettles([137.99, 255.99, 630.99]))
        page = self._page("kettle")
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k1", "k2", "k3"])
        self.assertFalse(any(card["recommended"] for card in cards))
        self.assertEqual([card["role"] for card in cards], ["Lowest price", "", ""])

    def test_three_have_a_middle_and_a_dearer_card_is_not_the_lowest_price(self) -> None:
        self._serve(self._kettles([100, 150, 200]))
        cards = self._cards(self._page("kettle"))
        self.assertEqual([card["id"] for card in cards], ["k2", "k1", "k3"])
        self.assertEqual(
            [card["role"] for card in cards],
            ["Mid-priced for this category", "Lowest price", ""],
        )

    def test_no_barcode_on_any_product_means_the_four_cheapest_and_no_recommended(self) -> None:
        self._serve(self._kettles([60, 20, 50, 30, 40, 70], codes=False))
        page = self._page("kettle")
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k2", "k4", "k5", "k3"])
        self.assertFalse(any(card["recommended"] or card["badge"] for card in cards))
        # "Lowest price" up to the middle price (owner, 2026-10-17): of six, the third
        # cheapest, £40. The £50 kettle on the page claims no price label.
        self.assertEqual(
            [card["role"] for card in cards], ["Lowest price"] * 3 + [""]
        )
        self.assertIn("No Recommended here", page)
        self.assertEqual(self._counter(page), "4 of 6")

    def test_one_product_in_two_shops_is_one_card_at_the_cheaper_price(self) -> None:
        rows = self._kettles([20, 30, 40, 50, 60])
        rows.append(
            {
                "pid": "k1b",
                "title": "Fixturon Electric Kettle 1 1.7L",
                "price": "18.00",
                "ean": rows[0]["ean"],
                "shop": "Fixture Store Two",
            }
        )
        self._serve(rows)
        page = self._page("kettle")
        cards = self._cards(page)
        ids = [card["id"] for card in cards]
        self.assertIn("k1b", ids)
        self.assertNotIn("k1", ids)
        self.assertEqual(
            next(card["role"] for card in cards if card["id"] == "k1b"),
            "Lowest price of 2 shops",
        )
        self.assertEqual(self._counter(page), "4 of 5")

    def test_the_search_words_decide_what_is_in_the_answer(self) -> None:
        rows = [
            {"pid": "s1", "title": "Fixturon 3 Seater Sofa - Grey", "price": "300.00",
             "type": "Sofas", "category": "Living Room Furniture"},
            {"pid": "s2", "title": "Testline 3-Seater Fabric Sofa, Grey", "price": "250.00",
             "type": "Sofas", "category": "Living Room Furniture"},
            {"pid": "s3", "title": "Sampleworks 2 Seater Sofa - Grey", "price": "150.00",
             "type": "Sofas", "category": "Living Room Furniture"},
            {"pid": "s4", "title": "Fixturon 3 Seater Sofa - Blue", "price": "200.00",
             "type": "Sofas", "category": "Living Room Furniture"},
        ]
        self._serve(rows)
        page = self._page("3 seater sofa grey")
        self.assertEqual(sorted(card["id"] for card in self._cards(page)), ["s1", "s2"])
        self.assertEqual(self._counter(page), "2 of 2")

    def test_a_word_no_product_carries_is_dropped_and_named(self) -> None:
        self._serve(self._kettles([20, 30, 40, 50]))
        page = self._page("kettle purple")
        self.assertEqual(len(self._cards(page)), 4)
        self.assertIn("PicWise could not match: purple", page)

    def test_a_word_is_matched_whole(self) -> None:
        rows = [
            {"pid": "g1", "title": "Fixturon Rattan Garden Furniture Set, 4 Seater",
             "price": "300.00", "type": "Garden Furniture Sets", "category": "Garden"},
            {"pid": "g2", "title": "Testline Rattan Garden Settee Bench",
             "price": "150.00", "type": "Garden Furniture", "category": "Garden"},
        ]
        self._serve(rows)
        page = self._page("rattan garden furniture set")
        self.assertEqual([card["id"] for card in self._cards(page)], ["g1"])

    def test_a_word_only_the_description_carries_does_not_count(self) -> None:
        # The description is the merchant's marketing text: a table lamp described as
        # lighting "the floor" is not a floor lamp. Price order would put it first.
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for pid, title, price, detail in (
                ("f1", "Fixturon Arc Floor Lamp 170cm", "49.00", ""),
                ("t1", "Testline Bedside Table Lamp", "19.00", "Lights the floor around the bed."),
            ):
                writer.writerow(
                    [pid, title, "Fixturon", "Lamps", "Lighting",
                     f"https://fixture.example.invalid/out/{pid}",
                     f"https://fixture.example.invalid/img/{pid}.jpg", price, "GBP", "1",
                     "Fixture Store One", fixture_description(detail), "local_test_fixture", "", ""]
                )
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if previous is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = previous
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)
        self.assertEqual([card["id"] for card in self._cards(self._page("floor lamp"))], ["f1"])

    def test_a_spec_one_product_carries_is_kept_when_another_word_fails(self) -> None:
        rows = self._kettles([20, 30, 40, 50])
        rows[2]["title"] = "Fixturon Electric Kettle 3 1.5L"
        rows[3]["title"] = "Fixturon Electric Kettle 4 1.5L"
        rows[0]["title"] = "Fixturon Electric Kettle 1 1.2L"
        self._serve(rows)
        # Only k2 is 1.7L, and no kettle is purple: the 1.7L one is the answer.
        page = self._page("kettle 1.7l purple")
        self.assertEqual([card["id"] for card in self._cards(page)], ["k2"])
        self.assertIn("PicWise could not match: purple", page)

    def test_a_dropped_word_every_product_shown_carries_is_not_reported(self) -> None:
        rows = self._kettles([20, 30, 40, 50])
        rows[0]["title"] = "Fixturon Electric Kettle 1 1.2L"
        rows[1]["title"] = "Fixturon Retro Electric Kettle 2 1.7L"
        rows[2]["title"] = "Fixturon Electric Kettle 3 1.5L"
        rows[3]["title"] = "Fixturon Electric Kettle 4 1.5L"
        self._serve(rows)
        # No kettle is purple, so not every word can be kept; one kettle is "retro",
        # too few to keep the word for. The answer is the one 1.7L kettle, and it is
        # retro: "Only some match: retro (1 of 1)" would be false.
        page = self._page("kettle 1.7l purple retro")
        self.assertEqual([card["id"] for card in self._cards(page)], ["k2"])
        self.assertIn("PicWise could not match: purple", page)
        self.assertNotIn("Only some match", page)
        unmatched = re.search(r"PicWise could not match: ([^<]*)", page)
        self.assertNotIn("retro", unmatched.group(1) if unmatched else "")

    def test_a_word_one_product_happens_to_carry_is_not_the_answer(self) -> None:
        rows = [
            {"pid": f"w{index}", "title": f"Fixturon Webcam {index} 1080p", "price": f"{20 + index}.00",
             "type": "Webcams", "category": "Computer Accessories"}
            for index in range(1, 5)
        ] + [
            {"pid": "z1", "title": "Testline 4K Webcam with 5x Digital Zoom", "price": "60.00",
             "type": "Webcams", "category": "Computer Accessories"},
        ]
        self._serve(rows)
        page = self._page("web cam for zoom calls")
        self.assertEqual(len(self._cards(page)), 4)
        self.assertEqual(self._counter(page), "4 of 5")
        # Said as it is: one webcam carries "zoom", none carries "calls".
        self.assertIn("Only some match: zoom (1 of 5)", page)
        self.assertIn("PicWise could not match: calls", page)

    def test_graded_laptops_are_shown_only_when_asked_for(self) -> None:
        rows = [
            {"pid": f"n{index}", "title": f"Fixturon Book {index} 14\" Laptop 8GB",
             "price": f"{300 + index * 50}.00", "type": "Laptops", "category": "Computers"}
            for index in range(1, 5)
        ] + [
            {"pid": "r1", "title": "Testline Elite 14 Laptop - Silver (Grade A - Good)",
             "price": "149.00", "type": "Laptops", "category": "Computers"},
        ]
        self._serve(rows)
        self.assertNotIn("r1", [card["id"] for card in self._cards(self._page("laptop"))])
        self.assertEqual(
            [card["id"] for card in self._cards(self._page("refurbished laptop"))], ["r1"]
        )


if __name__ == "__main__":
    unittest.main()
