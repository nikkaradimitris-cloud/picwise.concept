"""The prices at the ends of the server's prepared catalogue, printed.

`deployment/server/print_prices.py`, run by `.github/workflows/server-cap.yml` on a copy
of the server's file (owner, 2026-10-27: 99 pence may be poor or a piece of a pack, about
100,000 is too much; «Κάνε τη μέτρηση»). Pinned here: the bands (under 1 and 2, 10,000
and 50,000 and over) with their categories, shops and cheapest or dearest titles; the
cheap titles naming a pack; the products priced far outside their kind's usual prices
(the check for wrong kinds the owner said yes to), a shelf naming a kind joining it; no
trim of each kind's ends; an unreadable file says so; nothing printed holds a link;
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

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "print_prices.py"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402

RINGS = "Apparel & Accessories > Jewelry > Rings"


def _product(number: int, title: str, price: float, category: str = RINGS, shop: str = "Fictional Rings") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand="Fictbrand",
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{price:.2f}",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop, "availability": "in stock"},
    )


def _write(path: Path) -> None:
    products = [_product(number, f"Fictional Silver Ring {number}", 20.0 + number) for number in range(300)]
    products += [
        _product(1_001, "Fictional Earring Backs Pack of 10", 0.50, shop="Fictional Bits"),
        _product(1_002, "Fictional Toe Ring", 0.99),
        _product(1_003, "Fictional Midi Ring", 1.50),
        _product(1_004, "Fictional Diamond Ring", 12_000.00, shop="Fictional Diamonds"),
        _product(1_005, "Fictional Diamond Ring Eternity", 60_000.00, shop="Fictional Diamonds"),
    ]
    number = 2_000
    for decor in range(10):
        for _ in range(20):
            products.append(_product(number, f"Fictional Vase {number}", 15.0, f"Home & Garden > Decor {decor} > Vases", "Fictional Home"))
            number += 1
    kinds = tuple(frozenset({"ring"}) if "Ring" in product.title else frozenset() for product in products)
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 10, 27, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
        availability_context=build_feed_availability_context(tuple(products)),
        products=tuple(products),
        non_new=tuple("" for _product in products),
        kinds=kinds,
        eligible_count=len(products),
        shop_count=4,
        suggestions=(),
    )
    write_prepared_catalogue(prepared, path)


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)


class PrintPricesTests(unittest.TestCase):
    def test_the_ends_and_the_far_ones_are_printed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            result = _run(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("prices of the 505 products a card can show", out)
        self.assertIn("GBP 505", out)
        self.assertIn("under 1.00: 2 (0.40%)", out)
        self.assertIn("1.00 to under 2.00: 1", out)
        self.assertIn("10,000 and over: 2", out)
        self.assertIn("50,000 and over: 1", out)
        self.assertIn("== under 1.00: 2", out)
        self.assertIn("their title names a pack, a set or a number of pieces: 1", out)
        self.assertIn("0.50 GBP | Fictional Bits | Fictional Earring Backs Pack of 10", out)
        self.assertIn("the dearest 2:", out)
        self.assertIn("60,000.00 GBP | Fictional Diamonds | Fictional Diamond Ring Eternity", out)
        # Far outside the usual prices of rings: the toe and midi rings, the two diamond
        # rings, and the earring backs, which sit on the shelf of rings and so join "ring":
        # the kind of product the check is there to find.
        self.assertIn("priced far outside the usual prices of their kind (or shelf): 5, in 1 of the 11", out)
        self.assertIn("of     305 (usual", out)
        self.assertIn("0.50 GBP | ring (middle 169.00) | Fictional Bits | Fictional Earring Backs Pack of 10", out)
        self.assertNotIn("Fictional Silver Ring 150", out)
        # The trim of each kind's ends was dropped (owner, 2026-10-27).
        self.assertNotIn("cheapest 2%", out)
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
