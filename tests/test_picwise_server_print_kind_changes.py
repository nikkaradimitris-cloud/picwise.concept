"""The products of the server's prepared catalogue this checkout reads as another kind, printed.

`deployment/server/print_kind_changes.py`, run by `.github/workflows/server-cap.yml` on a
copy of the server's file (owner, 2026-10-27: «Διόρθω τους κανόνες και άντε να δούμε πού
θα καταλήξουμε τελικά»). Pinned here: each product is read again with this checkout's
rules and set against the kind stored with it; the changes are counted from kind to
kind, the most first, with their shops, their titles' commonest words and cheapest
titles; a product that keeps its narrowest kind and only gains a broader one (a
charging cable, now a cable too) is no change; the kinds whose counts change are
listed; the check of far prices is made again with the kinds read so; an unreadable
file says so; nothing printed holds a link; every case exits 0.

Every row is local test data: fictional brands and shops, `.invalid` addresses; the kinds
stored are those the rules before 2026-10-27 gave such titles.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "print_kind_changes.py"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_search_fields  # noqa: E402

CABLES = "Electronics > Electronics Accessories > Cables"


def _product(number: int, title: str, price: float, shop: str, *, category: str = "", product_type: str = "") -> ProviderProduct:
    raw = {"merchant_name": shop, "availability": "in stock"}
    if product_type:
        raw["product_type"] = product_type
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
        raw=raw,
    )


def _write(path: Path) -> None:
    rows = [
        (_product(1, "Fictional Locking Earring Backs - Gold", 11.49, "Fictional Jewels", product_type="Earrings"), {"earrings"}),
        (_product(2, "Fictional Silicone Earring Backs", 4.99, "Fictional Jewels", product_type="Earrings"), {"earrings"}),
        (_product(3, "Fictional Diamond Stud Earrings", 499.00, "Fictional Jewels", product_type="Earrings"), {"earrings"}),
        (_product(4, "Fictional Satellite Aerial Coaxial Cable 10m", 1.99, "Fictional Store", category=CABLES), {"charging_cable"}),
        (_product(5, "Fictional HDMI Cable 2m", 3.49, "Fictional Store", category=CABLES), {"charging_cable"}),
        (_product(6, "Fictional Speaker Cable 20m", 8.99, "Fictional Store", category=CABLES), {"charging_cable"}),
        (_product(7, "Fictional USB C to USB C Cable 2m", 6.99, "Fictional Store", category=CABLES), {"charging_cable"}),
        (_product(8, "Fictional Sauna Stones 20kg", 39.00, "Fictional Saunas", product_type="Sauna Stones"), {"sauna"}),
        (_product(9, "Fictional Barrel Sauna 4 Person", 4_999.00, "Fictional Saunas", product_type="Outdoor Sauna"), {"sauna"}),
        (_product(10, "Fictional Glass & Mirror 6x4 Photo Frame", 7.99, "Fictional Store"), {"mirror"}),
        (_product(11, "Fictional Round Wall Mirror with Wooden Frame", 49.00, "Fictional Store"), {"mirror"}),
    ]
    # Dear charging cables of another shop: the cheap cables were far from their prices.
    rows += [
        (_product(100 + step, f"Fictional Type 2 EV Charging Cable 7kW {step}m", 150.0 + step, "Fictional EV", category=CABLES), {"charging_cable"})
        for step in range(25)
    ]
    products = tuple(product for product, _kinds in rows)
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 10, 28, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        kinds=tuple(frozenset(kinds) for _product, kinds in rows),
        eligible_count=len(products),
        shop_count=4,
        suggestions=(),
        search_fields=tuple(_product_search_fields(product) for product in products),
    )
    write_prepared_catalogue(prepared, path)


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)


class PrintKindChangesTests(unittest.TestCase):
    def test_the_changes_are_counted_from_kind_to_kind(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            result = _run(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("36 products a card can show", out)
        # Two earring backs, three plain cables, the sauna stones and the photo frame;
        # the USB-C and EV cables keep their kind and gain "cable".
        self.assertIn("7 are read as another kind (19.44%); 26 keep their kind and gain or lose a broader one", out)
        lines = out.splitlines()
        first = next(index for index, line in enumerate(lines) if "->" in line and "charging_cable" in line)
        self.assertRegex(lines[first], r"^\s+3  charging_cable -> cable$")
        self.assertIn("shops: Fictional Store 3", lines[first + 1])
        self.assertEqual(
            lines[first + 2].strip(), "words: cable 3, fictional 3, aerial 1, coaxial 1, hdmi 1, satellite 1, speaker 1"
        )
        self.assertIn("1.99 GBP | Fictional Store | Fictional Satellite Aerial Coaxial Cable 10m", lines[first + 3])
        self.assertRegex(out, r"\n\s+2  earrings -> \(accessory\)\n")
        self.assertIn("4.99 GBP | Fictional Jewels | Fictional Silicone Earring Backs", out)
        self.assertRegex(out, r"\n\s+1  sauna -> \(accessory\)\n")
        self.assertRegex(out, r"\n\s+1  mirror -> photo_frame\n")
        self.assertIn("the kinds whose counts change, the most first: 7", out)
        self.assertRegex(out, r"\n\s+29 ->\s+26  charging_cable\n")
        self.assertRegex(out, r"\n\s+0 ->\s+3  cable\n")
        self.assertRegex(out, r"\n\s+0 ->\s+3  \(accessory\)\n")
        # Where it ends: of the cheap cables only the USB-C one is still a charging
        # cable, and still far from the EV cables' prices.
        far = out[out.index("the check of far prices again"):]
        self.assertIn("when it has 10 or more: 1, in 1 of the 1 with at least 20", far)
        self.assertIn("of      26 (usual", far)
        self.assertRegex(far, r"6\.99 GBP \| charging_cable \(middle [\d,.]+\) \| Fictional Store \| Fictional USB C to USB C Cable 2m")
        self.assertNotIn("Coaxial", far)
        self.assertNotIn("Diamond Stud", out)
        self.assertNotIn("Barrel Sauna", out)
        self.assertNotIn("Wooden Frame", out)
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
