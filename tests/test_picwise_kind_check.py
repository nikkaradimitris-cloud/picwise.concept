"""Which shown products have a title that does not name their kind, for the build's note.

`src/picwise_providers/kind_check.py`. Owner, 2026-10-23: «Ναι, φτιάξ' το», to a list
the build writes every morning, so new ways of writing titles show up from every shop
without a file. Pinned here: what counts as naming a kind (a noun of its names, either
number, English or Greek), what is not counted (markers, no kind), the most suspects
first, the cheapest examples, and nothing of a link.

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
from picwise_providers.kind_check import measure_kind_titles  # noqa: E402


def _product(pid: str, title: str, price: str, shop: str = "Fixture Store One") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand="Fixturon",
        category_text="Fixture Shelf",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text=price,
        availability_text="in_stock",
        currency="GBP",
        raw={"merchant_name": shop, "title": title},
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
                "99.00 GBP | Fixture Store One | Fixturon 35mm f/1.8G Lens",
                "141.00 GBP | Fixture Lens Shop | Fixturon 50mm f/1.8 STM Lens",
                "163.00 GBP | Fixture Store One | Fixturon 24mm f/2.8 Lens",
            ],
        )

    def test_a_long_title_is_cut_and_no_link_is_written(self) -> None:
        rows = [(_product("l4", "Fixturon 85mm f/1.4 Lens " + "Extra Long Name " * 6, "500.00"), {"camera"})]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows])
        example = note["by_kind"][0]["cheapest"][0]
        title = example.split(" | ")[-1]
        self.assertEqual(len(title), 70)
        self.assertTrue(title.endswith("..."))
        self.assertNotIn("fixture.example.invalid", repr(_measure()))

    def test_at_most_twenty_five_kinds(self) -> None:
        kinds = ("kettle", "toaster", "laptop", "tablet", "monitor", "mouse", "keyboard", "printer", "camera",
                 "headphones", "speaker", "television", "fan", "heater", "iron", "blender", "juicer", "sofa",
                 "bed", "mattress", "wardrobe", "desk", "chair", "table", "lamp", "drone", "pillow", "smartwatch")
        rows = [(_product(f"x{index}", f"Fixturon Model {index}", "10.00"), {kind}) for index, kind in enumerate(kinds)]
        note = measure_kind_titles([row[0] for row in rows], [frozenset(row[1]) for row in rows])
        self.assertEqual(note["title_names_no_kind"], len(kinds))
        self.assertEqual(len(note["by_kind"]), 25)


if __name__ == "__main__":
    unittest.main()
