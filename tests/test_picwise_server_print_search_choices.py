"""What a buyer would see for each general word, searched on a copy of the server's catalogue.

`deployment/server/print_search_choices.py`, run by `.github/workflows/server-cap.yml`
(owner, 2026-10-29: «Ναι προχώρα, βάλ' το στο search», measured before any deployment).
Pinned here: the file is prepared again with this checkout's rules, kinds stored by older
rules notwithstanding; each general kind's search is printed with how many products it
finds, its first card and the choices it asks; each choice is searched and said to find
products of the kind; "chair", which the vocabulary's older "too broad" answered with no
product until 2026-10-29, shows its chairs and asks like any other kind (the measure
says so when that list answers instead); the Greek name asks the same; the box's
suggestions hold the choices; nothing printed is a link; an unreadable file says so;
every case exits 0.
Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "deployment" / "server" / "print_search_choices.py"
for path in (HERE, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_search_fields  # noqa: E402

CABLES = "Electronics > Electronics Accessories > Cables"
KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"
DINING_CHAIRS = "Furniture > Chairs > Kitchen & Dining Room Chairs"
OFFICE_CHAIRS = "Furniture > Office Furniture > Office Chairs"


def _product(number: int, title: str, category: str, price: float) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand="Fixturon",
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{price:.2f}",
        availability_text="in stock",
        currency="GBP",
        raw={
            "merchant_name": "Fictional Store One" if number % 2 else "Fictional Store Two",
            "in_stock": "1",
            "description": fixture_description(),
        },
    )


def _write(path: Path) -> None:
    products = []
    for title, category, count, base in (
        ("Fixturon HDMI Cable {n}m", CABLES, 30, 3.0),
        ("Fixturon Coaxial Cable {n}m", CABLES, 25, 2.0),
        ("Fixturon Speaker Cable {n}m", CABLES, 22, 4.0),
        ("Fixturon Electric Kettle {n}", KETTLES, 55, 20.0),
        ("Fixturon Velvet Dining Chair {n}", DINING_CHAIRS, 10, 40.0),
        ("Fixturon Oak Dining Chair {n}", DINING_CHAIRS, 10, 50.0),
        ("Fixturon Grey Dining Chair {n}", DINING_CHAIRS, 10, 60.0),
        ("Fixturon Ergonomic Office Chair {n}", OFFICE_CHAIRS, 25, 70.0),
    ):
        for step in range(count):
            products.append(_product(len(products) + 1, title.format(n=step + 1), category, base + step))
    products = tuple(products)
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 10, 29, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(
            status="provider_feed_ready", provider_key="awin", product_count=len(products), eligible_count=len(products)
        ),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        # Stored by older rules; the script reads every product again with this checkout's.
        kinds=tuple(frozenset() for _product in products),
        eligible_count=len(products),
        shop_count=2,
        suggestions=(),
        search_fields=tuple(_product_search_fields(product) for product in products),
    )
    write_prepared_catalogue(prepared, path)


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False, timeout=600
    )


class PrintSearchChoicesTests(unittest.TestCase):
    def test_each_general_kind_as_the_buyer_would_see_it(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            result = _run(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("187 products a card can show, 187 of them new", out)
        self.assertIn("2 general kinds ask which one is meant", out)
        self.assertRegex(out, r"  cable: 77 products, the first card \d+\.\d\d GBP 'Fixturon [A-Za-z]+ Cable \d+m'")
        self.assertIn("      What kind of cable? hdmi cable, coaxial cable, speaker cable", out)
        self.assertIn(
            "      each found: hdmi cable 30 (yes); coaxial cable 25 (yes); speaker cable 22 (yes)", out
        )
        self.assertIn("  the Greek καλώδιο: 77 products; asks: hdmi cable, coaxial cable, speaker cable", out)
        # "chair" has five of the vocabulary's suggestions, which once answered it alone.
        self.assertIn("  chair: 55 products, the first card 40.00 GBP 'Fixturon Velvet Dining Chair 1'", out)
        self.assertIn("      What kind of chair? dining chair, office chair", out)
        self.assertIn("      each found: dining chair 30 (yes); office chair 25 (yes)", out)
        self.assertNotIn("  chair: no products", out)
        self.assertIn("  the Greek καρέκλα: 55 products; asks: dining chair, office chair", out)
        # Every kind's own name that list once answered alone, what it finds now.
        self.assertRegex(out, r"the kinds' own names the vocabulary's \"too broad\" list once answered alone: \d+")
        self.assertIn("  chair: 55 products; asks: dining chair, office chair\n", out)
        self.assertIn("  jacket: 0 products; asks: nothing (the list answers, no product)", out)
        self.assertRegex(out, r"the search box: \d+ suggestions, 5 of them choices")
        self.assertNotIn("kettle:", out)
        self.assertNotIn("shop.invalid", out)

    def test_an_unreadable_file_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            path.write_bytes(b"not a prepared file")
            result = _run(path)
        self.assertEqual(result.returncode, 0)
        self.assertIn("no prepared catalogue could be read", result.stdout)


if __name__ == "__main__":
    unittest.main()
