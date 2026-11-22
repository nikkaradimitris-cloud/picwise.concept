"""Task 6's look before its rules (`deployment/server/look_itself.py`): what the question
"is it the kind itself" would be asked about, counted on a copy of the server's catalogue.

Pinned here, on a prepared catalogue of the test's own (nothing is asked of any AI and
nothing leaves the machine): a question is one (question key, kind), a product's sizes and
numbers sharing the key; a product with no kind is counted apart; a search is answered as
the site answers it, with the kinds the prepared file carries, its first cards and its
Recommended; each card says the way it came; the notes are cut into files a later step says
as GitHub's notes, each escaped as GitHub asks; nothing printed is a link or an id.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import look_itself  # noqa: E402
import say_notes  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_concepts, _product_search_fields  # noqa: E402

KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"
LAPTOPS = "Electronics > Computers > Laptops"
DRILLS = "Hardware > Tools > Drills"


def _product(number: int, title: str, category: str, price: float) -> ProviderProduct:
    raw = {"merchant_name": "Fictional Store One", "in_stock": "1", "description": fixture_description(),
           "gtin": f"50000000{number:05d}"}
    if category:
        raw["google_product_category"] = category
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"row-{number}", title=title, brand="Fixturon", category_text=category,
        product_url=f"https://shop.invalid/p/{number}", image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{price:.2f}", availability_text="in stock", currency="GBP", raw=raw,
    )


def _write(path: Path) -> PreparedCatalogue:
    products = []
    for title, category, count, base in (
        ("Fixturon Electric Kettle {n}", KETTLES, 12, 20.0),
        ("Fixturon Book {n} Laptop 8GB", LAPTOPS, 8, 300.0),
        ("Fixturon Laptop Sleeve Case {n}", LAPTOPS, 3, 9.0),
        ("Fixturon Cordless Drill {n} 18V", DRILLS, 9, 60.0),
        # Read as drills by their shelf, and the cheapest: what the question is for.
        ("Fixturon Pilot Drill {n} for hole saws", DRILLS, 4, 3.0),
        ("Sampleworks Garden Gnome Statue {n}", "Home & Garden > Decor", 5, 15.0),
    ):
        for step in range(count):
            products.append(_product(len(products) + 1, title.format(n=step + 1), category, base + step))
    products = tuple(products)
    fields = tuple(_product_search_fields(product) for product in products)
    prepared = PreparedCatalogue(
        prepared_at=datetime.now(timezone.utc),
        feed_status=ProviderFeedStatus(
            status="provider_feed_ready", provider_key="awin", product_count=len(products), eligible_count=len(products)
        ),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        kinds=tuple(_product_concepts(product, product_fields) for product, product_fields in zip(products, fields)),
        eligible_count=len(products),
        shop_count=1,
        suggestions=(),
        search_fields=fields,
    )
    write_prepared_catalogue(prepared, path)
    return prepared


class LookItselfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        cls.catalogue = Path(cls.folder.name) / "catalogue.json.gz"
        _write(cls.catalogue)
        cls.notes = Path(cls.folder.name) / "notes"
        out = io.StringIO()
        with redirect_stdout(out):
            cls.status = look_itself.main([str(cls.catalogue), "--notes", str(cls.notes), "--no-searches"])
        cls.printed = out.getvalue()
        # The copy stays the site's catalogue of this process for the searches below.
        from picwise_providers import state

        cls.prepared = state._PREPARED_STATE["prepared"]
        cls.index = {str(product.provider_product_id): place for place, product in enumerate(cls.prepared.products)}

    @classmethod
    def tearDownClass(cls) -> None:
        from picwise_providers import state

        state._PREPARED_STATE.clear()
        state.remember_product_kinds({})
        cls.folder.cleanup()

    def test_it_ends_well_and_prints_no_link_or_id(self) -> None:
        self.assertEqual(self.status, 0)
        self.assertNotIn("http", self.printed)
        self.assertNotIn("row-", self.printed)
        self.assertNotIn("failed", self.printed)

    def test_a_question_is_a_key_and_a_kind(self) -> None:
        # 33 products with a kind (12 kettles, 8 laptops, 13 read as drills); the products
        # of one title but for its number share a key: one question for the kettles, one for
        # the laptops, two for the drills (the drills and the pilot drills).
        self.assertIn("products 41; with a kind 33", self.printed)
        self.assertIn("questions, one a (key, kind): 4 in 3 kinds", self.printed)
        self.assertIn("(no kind) 5", self.printed)
        self.assertIn("__accessory__ 3", self.printed)

    def test_the_way_a_card_came(self) -> None:
        self.assertEqual(look_itself.way_of(frozenset({"drill"}), "drill"), "kind")
        self.assertEqual(look_itself.way_of(frozenset(), "drill"), "words")
        self.assertEqual(look_itself.way_of(frozenset({"__uncertain_kind__"}), "drill"), "doubtful")
        self.assertEqual(look_itself.way_of(frozenset({"__accessory__"}), "drill"), "accessory")
        self.assertEqual(look_itself.way_of(frozenset({"kettle"}), "drill"), "other kind")

    def test_the_narrowest_kind_of_a_product(self) -> None:
        self.assertEqual(look_itself.narrowest(frozenset({"robot_vacuum", "vacuum_cleaner"})), frozenset({"robot_vacuum"}))
        self.assertEqual(look_itself.narrowest(frozenset({"kettle"})), frozenset({"kettle"}))

    def test_a_search_is_answered_as_the_site_answers_it(self) -> None:
        found = look_itself.searched("drill", 24)
        self.assertEqual(found["kind"], "drill")
        self.assertEqual(found["total"], 13)
        self.assertEqual(len(found["cards"]), 13)
        titles = [self.prepared.products[self.index[product_id]].title for product_id in found["cards"]]
        # The Recommended first, then the cheapest: the pilot drills, read as drills.
        self.assertEqual(found["cards"][0], found["recommended"])
        self.assertIn("Cordless Drill", titles[0])
        self.assertTrue(all("Pilot Drill" in title for title in titles[1:5]))

    def test_the_searches_of_the_measure_after_say_each_card(self) -> None:
        with redirect_stdout(io.StringIO()):
            lines = look_itself.searches_report(self.prepared, self.index)
        text = "\n".join(lines)
        self.assertIn('"drill" (drill, 13 products):', text)
        self.assertIn("3.00 | Fixturon Pilot Drill 1 for hole saws | Fictional Store… | kind | -", text)
        self.assertIn('"boots" (boots, 0 products):', text)
        self.assertIn("the way each card came: kind", lines[-1])

    def test_the_notes_are_files_a_step_says(self) -> None:
        files = sorted(self.notes.glob("*.txt"))
        self.assertEqual([path.name for path in files], ["01.txt", "02.txt", "03.txt", "04.txt"])
        self.assertTrue(files[0].read_text(encoding="utf-8").startswith("look: the catalogue\n"))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(say_notes.main([str(self.notes), "1", "2"]), 0)
        said = out.getvalue().splitlines()
        self.assertEqual(len(said), 2)
        self.assertTrue(said[0].startswith("::notice title=look  the catalogue::prepared at "))
        self.assertIn("%0A", said[1])
        self.assertNotIn("\r", said[1])

    def test_a_long_note_is_cut(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            notes = look_itself.Notes(Path(folder))
            with redirect_stdout(io.StringIO()):
                notes.say("long", ["x" * 3000 for _ in range(5)])
            files = sorted(Path(folder).glob("*.txt"))
            self.assertEqual(len(files), 3)
            self.assertTrue(files[0].read_text(encoding="utf-8").startswith("long (1 of 3)\n"))
            self.assertTrue(all(len(path.read_text(encoding="utf-8")) <= look_itself.NOTE_CHARS + 40 for path in files))

    def test_a_note_is_escaped_as_github_asks(self) -> None:
        self.assertEqual(say_notes.command("a: b, c", "50% of\nit"), "::notice title=a  b  c::50%25 of%0Ait")


if __name__ == "__main__":
    unittest.main()
