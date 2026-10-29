"""Which words of the server's prepared catalogue are general, and their choices, printed.

`deployment/server/print_choices.py`, run by `.github/workflows/server-cap.yml` on a copy
of the server's file (owner, 2026-10-28/29: a general word answered with choices of what
it means, one logic for all of them; measured before it is built). Pinned here: each
product is read with this checkout's rules; the kinds read, and those general by the
words before their noun, by their shelves and by either, are counted; a general kind's
choices are printed as the word and its noun ("hdmi cable"), its narrower kinds and its
shelves, the largest first, with their shares; a kind that is not general is listed with
its largest groups; nothing printed is a title or a link; an unreadable file says so;
every case exits 0. Every row is local test data: fictional brands and shops, `.invalid`
addresses.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "print_choices.py"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_search_fields  # noqa: E402

CABLES = "Electronics > Electronics Accessories > Cables"
RINGS = "Apparel & Accessories > Jewelry > Rings"


def _product(number: int, title: str, category: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand="Fictbrand",
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text="9.99",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": "Fictional Store", "availability": "in stock"},
    )


def _write(path: Path) -> None:
    rows = (
        [("Fictional HDMI Cable 2m", CABLES + " > Audio & Video Cables")] * 25
        + [("Fictional Satellite Coaxial Cable 10m", CABLES + " > Audio & Video Cables")] * 20
        + [("Fictional Cat6 Ethernet Cable 5m", CABLES + " > Network Cables")] * 15
        + [("Fictional USB Charging Cable 1m", CABLES)] * 12
        + [("Fictional Diamond Engagement Ring", RINGS)] * 55
    )
    products = tuple(_product(number, title, category) for number, (title, category) in enumerate(rows))
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 10, 29, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        # Stored by older rules; the script reads every product again with this checkout's.
        kinds=tuple(frozenset() for _product in products),
        eligible_count=len(products),
        shop_count=1,
        suggestions=(),
        search_fields=tuple(_product_search_fields(product) for product in products),
    )
    write_prepared_catalogue(prepared, path)


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)


class PrintChoicesTests(unittest.TestCase):
    def test_the_general_kinds_and_their_choices(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            result = _run(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("127 products a card can show", out)
        self.assertIn(
            "kinds of at least 50 products: 2; general by the words before their noun: 1; by their shelves: 1;"
            " by either: 1",
            out,
        )
        lines = out.splitlines()
        first = next(index for index, line in enumerate(lines) if line.startswith("  cable "))
        self.assertEqual(
            lines[first], '  cable 72 [words+shelves]; the title names it as "cable" in 72 (100%)'
        )
        self.assertEqual(
            lines[first + 1].strip(),
            "words: hdmi cable 25 (35%), coaxial cable 20 (28%), ethernet cable 15 (21%), charging cable 12 (17%)",
        )
        self.assertEqual(lines[first + 2].strip(), "narrower: charging_cable 12 (17%)")
        self.assertEqual(
            lines[first + 3].strip(),
            "shelves: Audio & Video Cables 45 (62%), Network Cables 15 (21%), Cables 12 (17%)",
        )
        rest = out[out.index("the largest kinds that are not general"):]
        self.assertIn("  ring 55; words: engagement 55 (100%); shelves: Rings 55 (100%)", rest)
        self.assertIn("the words left out as saying how a product is, before the nouns of 8 kinds or more: 0", out)
        self.assertNotIn("Fictional", out)
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
