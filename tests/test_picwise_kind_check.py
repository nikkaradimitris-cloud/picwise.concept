"""Which shown products have a title that does not name their kind, for the build's note.

`src/picwise_providers/kind_check.py`. Owner, 2026-10-23: «Ναι, φτιάξ' το», to a list
the build writes every morning, so new ways of writing titles show up from every shop
without a file. Pinned here: what counts as naming a kind (a noun of its names, either
number, English or Greek, a word joined by a slash, a narrower kind's noun), what is not
counted (markers, no kind), the most suspects first, the cheapest examples with their
narrowest shelf, and nothing of a link. Owner, 2026-10-25, with every Google-format shop
on the server: also the products whose title names their kind while neither their
product type nor their shelf does ("Colleen Hoover" books answering "vacuum cleaner",
"Chocolate Mice" answering "mouse"); pinned too. And for each kind listed, the shelves
its suspects most often sit on, whole as the kind reader saw them ("jewellery & watches
> body jewellery", where the cheapest example shows only "Body Jewellery"); and the
products a title's kind on another department's aisle made doubtful, read as before.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.kind_check import measure_kind_titles, measure_title_alone  # noqa: E402


def _product(
    pid: str,
    title: str,
    price: str,
    shop: str = "Fixture Store One",
    category: str = "Fixture Shelf",
    product_type: str = "",
) -> ProviderProduct:
    raw = {"merchant_name": shop, "title": title}
    if product_type:
        raw["product_type"] = product_type
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand="Fixturon",
        category_text=category,
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in_stock",
        currency="GBP",
        raw=raw,
    )


_ROWS = (
    (_product("c1", "Fixturon Z50 Mirrorless Camera", "799.00"), {"camera"}),
    (_product("l1", "Fixturon 50mm f/1.8 STM Lens", "141.00", shop="Fixture Lens Shop"), {"camera"}),
    (_product("l2", "Fixturon 24mm f/2.8 Lens", "163.00"), {"camera"}),
    (_product("l3", "Fixturon 35mm f/1.8G Lens", "99.00"), {"camera"}),
    (_product("l4", "Fixturon 85mm f/1.4 Lens " + "Extra Long Name " * 6, "500.00"), {"camera"}),
    (_product("v1", "Fixturon S8 Robot Vacuum", "399.00"), {"robot_vacuum", "vacuum_cleaner"}),
    (_product("s1", "Fixturon Mesh Seat", "89.00"), {"office_chair", "chair"}),
    (_product("g1", "Φορτιστής κινητού Fixturon 20W", "12.00"), {"phone_charger"}),
    (_product("k1", "Fixturon Kettles Twin Pack", "30.00"), {"kettle"}),
    (_product("a1", "Fixturon Lens Cap", "5.00"), {"__accessory__"}),
    (_product("u1", "Fixturon Thing", "6.00"), {"__uncertain_kind__"}),
    (_product("n1", "Fixturon Unknown Gadget", "7.00"), set()),
    (_product("p1", "Fixturon Orthopaedic Dog Bed", "45.00"), {"bed", "__pet__"}),
)


def _measure() -> dict:
    return measure_kind_titles([row[0] for row in _ROWS], [frozenset(row[1]) for row in _ROWS])


class KindTitleCheckTests(unittest.TestCase):
    def test_what_names_a_kind_and_what_is_counted(self) -> None:
        note = _measure()
        # Markers and products without a kind are not counted; the pet bed counts as a bed.
        self.assertEqual(note["products"], 10)
        # The four lenses and the seat name none of their kinds.
        self.assertEqual(note["title_names_no_kind"], 5)
        by_kind = {entry["kind"]: entry for entry in note["by_kind"]}
        # A Greek name, a plural, and each kind of a narrower one, name their kinds.
        for kind in ("phone_charger", "kettle", "robot_vacuum", "vacuum_cleaner", "bed"):
            self.assertNotIn(kind, by_kind)
        self.assertEqual((by_kind["camera"]["products"], by_kind["camera"]["title_without_kind"]), (5, 4))
        self.assertEqual(by_kind["chair"]["title_without_kind"], 1)
        self.assertEqual(by_kind["office_chair"]["title_without_kind"], 1)

    def test_the_most_suspects_first_and_the_cheapest_of_each(self) -> None:
        note = _measure()
        self.assertEqual([entry["kind"] for entry in note["by_kind"]], ["camera", "chair", "office_chair"])
        self.assertEqual(
            note["by_kind"][0]["cheapest"],
            [
                "99.00 GBP | Fixture Store One | Fixturon 35mm f/1.8G Lens | Fixture Shelf",
                "141.00 GBP | Fixture Lens Shop | Fixturon 50mm f/1.8 STM Lens | Fixture Shelf",
                "163.00 GBP | Fixture Store One | Fixturon 24mm f/2.8 Lens | Fixture Shelf",
            ],
        )

    def test_a_long_title_is_cut_and_no_link_is_written(self) -> None:
        rows = [(_product("l4", "Fixturon 85mm f/1.4 Lens " + "Extra Long Name " * 6, "500.00"), {"camera"})]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows])
        example = note["by_kind"][0]["cheapest"][0]
        title = example.split(" | ")[2]
        self.assertEqual(len(title), 70)
        self.assertTrue(title.endswith("..."))
        self.assertNotIn("fixture.example.invalid", repr(_measure()))

    def test_a_slash_a_narrower_kind_and_the_shelf_shown(self) -> None:
        rows = [
            # Words joined by a slash are two words.
            (_product("h1", "Fixturon AUD9 headphones/headset Wireless", "36.99"), {"headphones"}),
            # A narrower kind's noun names the broader kind too.
            (_product("b1", "Fixturon Oak Bookcase", "120.00"), {"bookcase", "shelving"}),
            # The shelf a suspect sits on is its category's narrowest.
            (
                _product(
                    "m1", "Fixturon Noodle Mats - 40x60cm / Black", "6.99",
                    category="Home & Garden > Bathroom Accessories > Bath Mats & Rugs",
                ),
                {"rug"},
            ),
        ]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows])
        self.assertEqual((note["products"], note["title_names_no_kind"]), (3, 1))
        self.assertEqual(
            note["by_kind"],
            [
                {
                    "kind": "rug",
                    "products": 1,
                    "title_without_kind": 1,
                    "cheapest": ["6.99 GBP | Fixture Store One | Fixturon Noodle Mats - 40x60cm / Black | Bath Mats & Rugs"],
                    "shelves": [{"shelf": "Home & Garden > Bathroom Accessories > Bath Mats & Rugs", "products": 1}],
                }
            ],
        )

    def test_at_most_twenty_five_kinds(self) -> None:
        kinds = ("kettle", "toaster", "laptop", "tablet", "monitor", "mouse", "keyboard", "printer", "camera",
                 "headphones", "speaker", "television", "fan", "heater", "iron", "blender", "juicer", "sofa",
                 "bed", "mattress", "wardrobe", "desk", "chair", "table", "lamp", "drone", "pillow", "smartwatch")
        rows = [(_product(f"x{index}", f"Fixturon Model {index}", "10.00"), {kind}) for index, kind in enumerate(kinds)]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows])
        self.assertEqual(note["title_names_no_kind"], len(kinds))
        self.assertEqual(len(note["by_kind"]), 25)

    def test_a_title_naming_the_kind_its_type_and_shelf_do_not(self) -> None:
        rows = [
            # The shelf names nothing PicWise knows, and the title names the kind's word
            # for something else.
            (_product("h1", "Fixturon Hoover 6 Book Collection Set", "8.99", category="Media > Books"),
             {"vacuum_cleaner"}),
            (_product("h2", "Fixturon Hoover Paperback", "2.99", category="Media > Books"), {"vacuum_cleaner"}),
            (_product("m1", "Fixturon Chocolate Mice 225g", "3.75", category="Food Items > Candy & Chocolate"),
             {"mouse"}),
            # A suspect, not a mistake: a broad shelf names no kettle and holds kettles.
            (_product("k1", "Fixturon Electric Kettle", "19.99", category="Home > Kitchen Appliances"),
             {"kettle"}),
            # The shelf, or the product type, names the kind: not listed.
            (_product("k2", "Fixturon Glass Kettle", "24.99", category="Small Appliances > Kettles"), {"kettle"}),
            (_product("k3", "Fixturon Steel Kettle", "29.99", product_type="Kitchen > Kettles"), {"kettle"}),
            (_product("v1", "Fixturon S8 Robot Vacuum", "399.00", category="Floor Care > Vacuums"),
             {"robot_vacuum", "vacuum_cleaner"}),
            # A title naming no kind is the other list's.
            (_product("s1", "Fixturon Mesh Seat", "89.00"), {"office_chair", "chair"}),
        ]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows])
        self.assertEqual(note["only_title_names_kind"], 4)
        self.assertEqual(
            note["by_kind_only_title"],
            [
                {
                    "kind": "vacuum_cleaner",
                    "products": 3,
                    "only_title_names_it": 2,
                    "cheapest": [
                        "2.99 GBP | Fixture Store One | Fixturon Hoover Paperback | Books",
                        "8.99 GBP | Fixture Store One | Fixturon Hoover 6 Book Collection Set | Books",
                    ],
                    "shelves": [{"shelf": "Media > Books", "products": 2}],
                },
                {
                    "kind": "kettle",
                    "products": 3,
                    "only_title_names_it": 1,
                    "cheapest": ["19.99 GBP | Fixture Store One | Fixturon Electric Kettle | Kitchen Appliances"],
                    "shelves": [{"shelf": "Home > Kitchen Appliances", "products": 1}],
                },
                {
                    "kind": "mouse",
                    "products": 1,
                    "only_title_names_it": 1,
                    "cheapest": [
                        "3.75 GBP | Fixture Store One | Fixturon Chocolate Mice 225g | Candy & Chocolate"
                    ],
                    "shelves": [{"shelf": "Food Items > Candy & Chocolate", "products": 1}],
                },
            ],
        )
        # The first list is unchanged by the second.
        self.assertEqual(note["title_names_no_kind"], 1)
        self.assertEqual([entry["kind"] for entry in note["by_kind"]], ["chair", "office_chair"])

    def test_the_whole_shelf_the_kind_reader_saw_and_the_most_frequent_first(self) -> None:
        rows = [
            (_product("w1", "Jojoba Healing Oil Roll-On", "3.49", category="Body Jewellery"), {"watch"}),
            (_product("w2", "316L Ear Expander - 3mm", "4.99", category="Body Jewellery"), {"watch"}),
            (_product("w3", "Fixturon Heart Pendant", "49.00", category="Pendants"), {"watch"}),
            (_product("w4", "Fixturon F-91W Classic Watch", "15.00", category="Watches"), {"watch"}),
        ]
        fields = [
            {"category": "jewellery & watches > body jewellery"},
            {"category": "jewellery & watches > body jewellery"},
            {"category": "jewellery & watches > pendants"},
            {"category": "jewellery & watches > watches"},
        ]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows], fields)
        (watch,) = note["by_kind"]
        self.assertEqual((watch["products"], watch["title_without_kind"]), (4, 3))
        self.assertEqual(
            watch["shelves"],
            [
                {"shelf": "jewellery & watches > body jewellery", "products": 2},
                {"shelf": "jewellery & watches > pendants", "products": 1},
            ],
        )
        # The cheapest still name the narrowest shelf of the product's own category.
        self.assertEqual(watch["cheapest"][0], "3.49 GBP | Fixture Store One | Jojoba Healing Oil Roll-On | Body Jewellery")

    def test_the_products_their_aisle_made_doubtful(self) -> None:
        sweets = "food, beverages & tobacco > food items > sweets & chocolate"
        rows = [
            # Doubtful by its aisle: read as a mouse before the rule.
            (_product("d1", "Fixturon Chocolate Mice - 225g Sweet Pouch", "3.75"), {"__uncertain_kind__"}, sweets),
            (_product("d2", "Fixturon Pink Mice - 100g", "1.49"), {"__uncertain_kind__"}, sweets),
            # Doubtful for another reason: its type names no kind PicWise knows.
            (_product("d3", "Fixturon Thing", "2.00", product_type="Temperature & Humidity Sensors"),
             {"__uncertain_kind__"}, ""),
            (_product("m1", "Fixturon M100 Wireless Mouse", "9.99"), {"mouse"}, "electronics > computer accessories"),
        ]
        fields = [{"category": row[2]} for row in rows]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows], fields)
        self.assertEqual(note["doubted_by_aisle"], 2)
        self.assertEqual(
            note["by_kind_doubted_by_aisle"],
            [
                {
                    "kind": "mouse",
                    "products": 1,
                    "doubted_by_its_aisle": 2,
                    "cheapest": [
                        "1.49 GBP | Fixture Store One | Fixturon Pink Mice - 100g | Fixture Shelf",
                        "3.75 GBP | Fixture Store One | Fixturon Chocolate Mice - 225g Sweet Pouch | Fixture Shelf",
                    ],
                    "shelves": [{"shelf": sweets, "products": 2}],
                }
            ],
        )
        # Without the search fields, not measured.
        self.assertIsNone(measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows])[
            "doubted_by_aisle"
        ])


class TitleAloneTests(unittest.TestCase):
    """Owner, 2026-10-25, «Ναι»: how often a title alone gives the kind its shelf gives,
    before any row without a category is shown by its title."""

    def test_the_title_alone_against_the_shelf(self) -> None:
        rows = [
            # The title names the shelf's kind.
            _product("k1", "Fixturon Glass Electric Kettle 1.7L", "24.99", category="Kettles"),
            # The title names another kind: a mouse on a kettles shelf.
            _product("k2", "Fixturon Wireless Optical Mouse", "9.99", category="Kettles"),
            _product("k3", "Fixturon Gaming Mouse", "14.99", shop="Fixture Store Two", category="Kettles"),
            # The title names an accessory, or nothing.
            _product("k4", "Fixturon Kettle Descaler Tablets", "4.99", category="Kettles"),
            _product("k5", "Fixturon Rapid Boil 1.7L", "19.99", shop="Fixture Store Two", category="Kettles"),
            # The shelf names no kind: not counted.
            _product("x1", "Fixturon Glass Electric Kettle", "24.99", category="Gift Ideas"),
        ]
        note = measure_title_alone(rows, [{"category": row.category_text.lower()} for row in rows])
        self.assertEqual(
            {key: note[key] for key in ("products", "agrees", "differs", "accessory", "doubtful", "none")},
            {"products": 5, "agrees": 1, "differs": 2, "accessory": 1, "doubtful": 0, "none": 1},
        )
        self.assertEqual(
            note["by_shop"],
            [
                {"shop": "Fixture Store One", "products": 3, "agrees": 1, "differs": 1, "accessory": 1,
                 "doubtful": 0, "none": 0, "title_gives_none": 1, "description_gives": 0,
                 "description_agrees": 0},
                {"shop": "Fixture Store Two", "products": 2, "agrees": 0, "differs": 1, "accessory": 0,
                 "doubtful": 0, "none": 1, "title_gives_none": 1, "description_gives": 0,
                 "description_agrees": 0},
            ],
        )
        self.assertEqual(
            note["differs_by_pair"],
            [
                {
                    "shelf_kind": "kettle",
                    "title_kind": "mouse",
                    "products": 2,
                    "cheapest": [
                        "9.99 GBP | Fixture Store One | Fixturon Wireless Optical Mouse | Kettles",
                        "14.99 GBP | Fixture Store Two | Fixturon Gaming Mouse | Kettles",
                    ],
                }
            ],
        )

    def test_where_the_title_gives_none_the_descriptions_first_sentence(self) -> None:
        def with_description(pid: str, title: str, description: str) -> ProviderProduct:
            product = _product(pid, title, "19.99", category="Kettles")
            product.raw["description"] = description
            return product

        rows = [
            with_description("k1", "Fixturon Rapid Boil 1.7L", "<p>This glass electric kettle boils fast.</p> More."),
            with_description("k2", "Fixturon Rapid Boil 2L", "A wireless optical mouse for the desk. More text."),
            with_description("k3", "Fixturon Rapid Boil 3L", ""),
        ]
        note = measure_title_alone(rows)
        self.assertEqual(
            {key: note[key] for key in ("title_gives_none", "description_gives", "description_agrees")},
            {"title_gives_none": 3, "description_gives": 2, "description_agrees": 1},
        )

    def test_a_broader_or_narrower_kind_agrees(self) -> None:
        rows = [_product("v1", "Fixturon S8 Robot Vacuum Cleaner", "199.00", category="Vacuums")]
        note = measure_title_alone(rows)
        self.assertEqual((note["products"], note["agrees"], note["differs"]), (1, 1, 0))


if __name__ == "__main__":
    unittest.main()
