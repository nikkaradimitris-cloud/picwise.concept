"""Which kinds have products from too few shops, and which have none, printed.

`deployment/server/print_gaps.py`, run by `.github/workflows/server-cap.yml` on a copy of
the server's file (owner, 2026-10-31: «Ναι, κάνε τη μέτρηση», to know which shops to look
for). Pinned here: each product counts under its narrowest kind and its shop by the
merchant's name, as the nightly note counts "enough"; a kind from 3 shops is covered, one
from one or two is listed with its shops, a defined kind with no product is named under
its mega-category; an unreadable file says so; every case exits 0.

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
SCRIPT = ROOT / "deployment" / "server" / "print_gaps.py"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402


def _product(number: int, shop: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=f"Fictional product {number}",
        brand="Fictbrand",
        category_text="Home & Garden > Kitchen & Dining",
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{1 + number}.00",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop, "availability": "in stock", "ean": f"{5_000_000_000_000 + number:013d}"},
    )


# kind -> the shops selling it, each once per product.
_ROWS = {
    "kettle": ["Fictional Kitchen", "Fictional Home", "Fictional Outlet", "Fictional Kitchen"],
    "toaster": ["Fictional Kitchen", "Fictional Kitchen", "Fictional Home"],
    "ring": ["Fictional Rings"],
}


def _write(path: Path) -> None:
    products = []
    kinds = []
    for kind, shops in _ROWS.items():
        for shop in shops:
            products.append(_product(len(products), shop))
            kinds.append(frozenset({kind}))
    # A product of no kind counts for its shop only.
    products.append(_product(len(products), "Fictional Odds"))
    kinds.append(frozenset())
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 10, 31, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
        availability_context=build_feed_availability_context(tuple(products)),
        products=tuple(products),
        non_new=tuple("" for _product in products),
        kinds=tuple(kinds),
        eligible_count=len(products),
        shop_count=5,
        suggestions=(),
    )
    write_prepared_catalogue(prepared, path)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)


class PrintGapsTests(unittest.TestCase):
    def test_kinds_short_of_shops_and_kinds_with_none_are_named(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            done = _run(str(path))
        self.assertEqual(done.returncode, 0, done.stderr)
        out = done.stdout
        self.assertIn("9 products a card can show, from 5 shops; 8 of them with a kind", out)
        self.assertIn("kinds with products from at least 3 shops: 1; from two: 1; from one: 1; with none:", out)
        # The kettle is covered; the toaster and the ring are listed with their shops.
        self.assertNotIn("    kettle:", out)
        self.assertIn("    toaster: 3: Fictional Kitchen 2, Fictional Home 1", out)
        self.assertIn("    ring: 1: Fictional Rings 1", out)
        # A kind PicWise defines with no product is named under its mega-category.
        empty = out.split("the kinds with no product", 1)[1]
        self.assertIn("washing machine", empty)
        self.assertNotIn("toaster", empty)
        self.assertIn("  kitchen_cooking_household:", out)
        self.assertNotIn("shop.invalid", out)

    def test_an_unreadable_file_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            path.write_bytes(b"not a prepared catalogue")
            done = _run(str(path))
        self.assertEqual(done.returncode, 0)
        self.assertIn("no prepared catalogue could be read", done.stdout)

    def test_without_a_file_it_says_how_to_run(self) -> None:
        done = _run()
        self.assertEqual(done.returncode, 0)
        self.assertIn("usage: print_gaps.py", done.stdout)


if __name__ == "__main__":
    unittest.main()
