"""What a cap of 15% a category would keep of the server's prepared catalogue, printed.

`deployment/server/print_cap.py`, run by `.github/workflows/server-cap.yml` on a copy of
the server's file (owner, 2026-10-27: measure first). Pinned here: a prepared file
written by this code is read and measured (the categories over the cap, the largest
after it, the kinds inside, the shops, the clean signs), a file written by other code is
measured too, an unreadable one says so, and every case exits 0; the next night, the
pool kept as its starting point, keeps the same pool on the same products (owner,
2026-10-30: the cap chooses the pool Google may be given from).

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "print_cap.py"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402


def _product(number: int, category: str, shop: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=f"Fictional product {number}",
        brand="Fictbrand",
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{1 + number}.00",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop, "availability": "in stock", "ean": f"{5_000_000_000_000 + number:013d}"},
    )


def _write(path: Path) -> None:
    products = [_product(number, "Apparel & Accessories > Jewelry > Rings", "Fictional Rings") for number in range(300)]
    number = 1_000
    for decor in range(10):
        for _ in range(20):
            products.append(_product(number, f"Home & Garden > Decor {decor} > Vases", "Fictional Home"))
            number += 1
    kinds = tuple(frozenset({"ring"}) if index < 300 else frozenset() for index in range(len(products)))
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 10, 27, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
        availability_context=build_feed_availability_context(tuple(products)),
        products=tuple(products),
        non_new=tuple("" for _product in products),
        kinds=kinds,
        eligible_count=len(products),
        shop_count=2,
        suggestions=(),
    )
    write_prepared_catalogue(prepared, path)


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)


class PrintCapTests(unittest.TestCase):
    def test_a_prepared_file_is_measured(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            result = _run(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("500 products a card can show, in 11 categories", out)
        self.assertIn("a cap of 15% a category: at most", out)
        self.assertIn("categories over the cap:", out)
        self.assertIn("apparel & accessories > jewelry", out)
        self.assertIn("inside apparel & accessories > jewelry, by kind", out)
        self.assertIn("ring", out)
        self.assertIn("Fictional Rings", out)
        self.assertIn("with all of an identity, an image", out)
        # The next night, the pool its starting point, keeps the same pool (owner,
        # 2026-10-30: the cap chooses the pool Google may be given from).
        self.assertRegex(
            out,
            r"the next night, the pool kept as its starting point, on the same products: ([\d,]+) kept, \1 of them the same",
        )
        self.assertNotIn("shop.invalid", out)

    def test_a_file_written_by_other_code_is_measured_too(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            payload = json.loads(gzip.decompress(path.read_bytes()))
            payload["code"] = "written-by-other-code"
            path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
            result = _run(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("categories over the cap:", result.stdout)

    def test_an_unreadable_file_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            path.write_bytes(b"not a prepared file")
            result = _run(path)
        self.assertEqual(result.returncode, 0)
        self.assertIn("no prepared catalogue could be read", result.stdout)


if __name__ == "__main__":
    unittest.main()
