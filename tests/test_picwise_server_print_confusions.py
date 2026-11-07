"""Which products confuse the search, measured on a copy of the server's catalogue (owner, 2026-11-04).

`deployment/server/print_confusions.py`, run by `.github/workflows/server-confusions.yml`
(owner: «Θέλω να μάθω ποια προϊόντα δημιουργούν μπέρδεμα στην αναζήτηση.. όπως τα tablets...
Banks...», and «Ναι, προχώρα με τον έλεγχο»). Pinned here, on a catalogue whose stored kinds
read every title naming "tablets" as a tablet, as the deployed rules did:

- where each kind comes from: the pills' kind from their title alone, on an aisle that may
  not hold a tablet (Health & Beauty, by the shelf's name); a tablet on a shop's shelf Google
  has no name for, not known; the real tablets on "Tablet Computers" by their title too,
  on an aisle that may hold them;
- what this checkout's rule takes away (the pills) and what it leaves (every real tablet);
- a kind read from a shelf on an aisle that may not hold it, which the rule does not read;
- the words: "tablet" with its aisles, "bank" with its power banks and piggy banks;
- every search, on the copy with both sets of kinds: "tablet" with eleven suspects as
  deployed and none with this checkout's rules, the unchecked tablet listed; "banks" asking
  which is meant;
- each part on its own (one job a part on GitHub's runner, each with its own log);
- the live site: its cards matched to the copy by their product id, its suspects found;
- an unreadable file says so; nothing printed is a link; every case exits 0.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "deployment" / "server" / "print_confusions.py"
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_search_fields  # noqa: E402

TABLETS = "Electronics > Computers > Tablet Computers"
PILLS = (
    ("Vitamins & Supplements", "Fixturon Milk Thistle Extract Tablets 4000mg High Strength"),
    ("Vitamins & Supplements", "Fixturon Chromium Picolinate Daily Tablets"),
    ("Vitamins & Supplements", "Fixturon Coconut Oil Biotin Tablets"),
    ("Vitamins & Supplements", "Fixturon Vitamin D3 1000IU 365 Tablets"),
    ("Vitamins & Supplements", "Fixturon Magnesium Citrate Tablets 120"),
    ("Vitamins & Supplements", "Fixturon Iron Gentle Tablets 90"),
    ("Mouthwash", "Testline Natural Mouthwash Tablets"),
    ("Mouthwash", "Testline Mint Mouthwash Tablets"),
    ("Toothpaste", "Testline Toothpaste Tablets Charcoal"),
    ("Toothpaste", "Testline Toothpaste Tablets Mint"),
    ("Fish Food", "Testline FunTips Tablets 20"),
)


def _product(number: int, title: str, category: str, price: float, shop: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand=title.split()[0],
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{price:.2f}",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop, "in_stock": "1", "description": fixture_description()},
    )


def _rows() -> list[tuple[str, str, float, str, frozenset[str]]]:
    """(title, category, price, shop, the kinds the deployed rules stored)."""
    tablet = frozenset({"tablet"})
    rows = [
        (f"Fixturon Tab {n} Android Tablet 128GB", TABLETS, 120.0 + 10 * n, "Fictional Store One", tablet)
        for n in range(1, 6)
    ]
    rows += [(title, shelf, 3.0 + 0.5 * n, "Fictional Pharmacy", tablet) for n, (shelf, title) in enumerate(PILLS)]
    # A tablet on a shop's own shelf that Google has no name for: its aisle is not known.
    rows.append(("Testline Pad 11 Tablet 256GB", "Gadgets Galore", 199.0, "Fictional Store Two", tablet))
    # A kind from a deeper shelf of Google's path, on an aisle that may not hold it.
    rows.append(("Fixturon Wireless Mouse Silent", "Health & Beauty > Personal Care > Mouse", 9.0, "Fictional Store Two",
                 frozenset({"mouse"})))
    rows += [
        (f"Fixturon Wireless Optical Mouse {n}", "Electronics > Electronics Accessories > Computer Components > Input Devices > Mice & Trackballs",
         12.0 + n, "Fictional Store One", frozenset({"mouse"}))
        for n in range(1, 5)
    ]
    rows += [
        (f"Fixturon Power Bank 20000mAh {n}", "Electronics > Electronics Accessories > Power > Power Banks", 15.0 + n,
         "Fictional Store One", frozenset({"power_bank"}))
        for n in range(1, 4)
    ]
    rows += [
        ("Testline Ceramic Piggy Bank Pink", "Money Boxes", 6.0, "Fictional Gifts", frozenset()),
        ("Testline Unicorn Money Bank", "Money Boxes", 7.0, "Fictional Gifts", frozenset()),
    ]
    return rows


def _write(path: Path) -> None:
    rows = _rows()
    products = tuple(_product(number, *row[:4]) for number, row in enumerate(rows, start=1))
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 11, 4, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(
            status="provider_feed_ready", provider_key="awin", product_count=len(products), eligible_count=len(products)
        ),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        kinds=tuple(row[4] for row in rows),
        eligible_count=len(products),
        shop_count=4,
        suggestions=(),
        search_fields=tuple(_product_search_fields(product) for product in products),
    )
    write_prepared_catalogue(prepared, path)


def _run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments, "--kinds", "3"],
        capture_output=True, text=True, check=False, timeout=900,
    )


class _Quiet(WSGIRequestHandler):
    def log_message(self, *args) -> None:  # noqa: D401 - the test's output stays clean
        pass


class PrintConfusionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        cls.path = Path(cls.folder.name) / "catalogue.json.gz"
        _write(cls.path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.folder.cleanup()

    def test_the_copy_end_to_end(self) -> None:
        result = _run(str(self.path))
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("the prepared catalogue of 2026-11-04T04:21:00+00:00: 27 products a card can show", out)
        self.assertIn("12 read otherwise", out)
        self.assertIn("the part: all", out)
        # 1: the pills' kind from their title alone, on an aisle that may not hold a tablet;
        # the real tablets' too, since the reader cannot read "Tablet Computers": their title
        # decides, on an aisle that may hold a tablet.
        # The mouse filed under Health & Beauty: its shelf's kind gives way to its title's,
        # under the same rule (owner, 2026-11-05: «Εντάξει, προχώρα με το βήμα 2»).
        self.assertIn("with the rules deployed (the kinds the server stored): 25 products of a kind; the type or the"
                      " shelf named one 3 (the title may have corrected it); from the title alone, neither naming"
                      " one, 22: on an aisle that may hold the kind 9, on one that may not 12, the aisle not known 1",
                      out)
        self.assertIn("with this checkout's rules (the main kind only): 13 products of a kind; the type or the shelf"
                      " named one 3 (the title may have corrected it); from the title alone, neither naming one, 10:"
                      " on an aisle that may hold the kind 9, on one that may not 0, the aisle not known 1; of no"
                      " kind: doubtful 12", out)
        # 2: per kind, by the aisle's verdict and the shop's shelf, with the cheapest.
        self.assertIn("  tablet: 17 products (6 with this checkout's rules); from the title alone 17: may hold 5,"
                      " may not 11, not known 1", out)
        self.assertIn("      may not: vitamins & supplements (health & beauty) 6, mouthwash (health & beauty) 2,"
                      " toothpaste (health & beauty) 2, fish food (animals & pet supplies) 1", out)
        self.assertIn("      not known: gadgets galore 1", out)
        self.assertIn("      holds: tablet computers 5", out)
        self.assertIn("      e.g. may not:       3.00 GBP | Fictional Pharmacy | Fixturon Milk Thistle Extract Tablets"
                      " 4000mg High Strength | vitamins & supplements", out)
        self.assertIn("      e.g. not known:     199.00 GBP | Fictional Store Two | Testline Pad 11 Tablet 256GB |"
                      " gadgets galore", out)
        # 3: what the rule takes away: the pills and the mouse filed under Health & Beauty,
        # and no real tablet.
        self.assertIn("12 products lose their kind or change it, in 2 kinds; 0 gain one", out)
        self.assertIn("  mouse: 1 -> (doubtful) 1 | shelves: mouse (health & beauty) 1", out)
        self.assertIn("  tablet: 11 -> (doubtful) 11 | shelves: vitamins & supplements (health & beauty) 6", out)
        self.assertNotIn("Android Tablet", out.split("== 3.")[1].split("== 4.")[0])
        # 4: a kind from a shelf on an aisle that may not hold it: none left, the rule reads
        # a shelf's kind too since 2026-11-05.
        self.assertIn("== 4. Products whose type or shelf named a kind", out)
        self.assertIn("\n0 products in 0 kinds\n", out)
        # 5: the words, the owner's first, and in short.
        self.assertIn("  tablet (dishwasher_tablets, tablet): 17 titles; read as its kind 17 -> 6; of those on an aisle"
                      " that may not hold it 11 -> 0, from the title alone where no aisle is known 1 -> 1", out)
        self.assertIn("  bank (power_bank): 5 titles; read as its kind 3 -> 3", out)
        self.assertIn("e.g. not its kind ((no kind)), animals & pet supplies / ar...:       6.00 GBP | Fictional Gifts"
                      " | Testline Ceramic Piggy Bank Pink | money boxes", out)
        self.assertIn("      e.g. as mouse on another aisle:       9.00 GBP | Fictional Store Two | Fixturon Wireless"
                      " Mouse Silent", out)
        self.assertIn("  tablet: of 17 -> 6 read as its kind, another aisle 11 -> 0, no aisle known 1 -> 1", out)
        self.assertIn("  this checkout's rule changes the kind of 12 products of 27", out)
        # 6: the searches on the copy, with both sets of kinds.
        tablet_line = next(line for line in out.splitlines() if line.startswith("  tablet: deployed"))
        self.assertEqual(
            tablet_line,
            "  tablet: deployed: 17 (tablet) S 11/12 (4 in the first 4) U 0 | this checkout: 6 (tablet) S 0/6"
            " (0 in the first 4) U 1",
        )
        self.assertRegex(out, r"      deployed #1 S +3\.00 GBP \| Fictional Pharmacy \| Fixturon Milk Thistle .*"
                              r"\| on an aisle that may not hold tablet: health & beauty \(by the shelf's name\)")
        self.assertRegex(out, r"      this checkout #6 U +199\.00 GBP \| Fictional Store Two \| Testline Pad 11 Tablet 256GB")
        # "banks" asks which is meant, from its products' families; "pad" finds by its words.
        self.assertIn("  banks: deployed: 0 products, no card (which do you mean: power banks, money banks, piggy banks;", out)
        self.assertIn("  pad: deployed: 1 products, by their words, of the kinds tablet 1", out)
        # In short.
        # The searches by a product's own name: as deployed, the pills are tablets; with this
        # checkout's rules, "vitamin tablets" finds the vitamin by its words, and "kids
        # tablet", whose word no product carries, lists the tablets.
        self.assertIn("  deployed: 7 of 8 searches of a kind: electrolyte tablets 11, kids tablet 11, tablet 11,"
                      " tablets 11, vitamin tablets 11, mouse 1, sugar mice 1", out)
        self.assertIn("  this checkout: 0 of 7 searches of a kind: \n", out)
        self.assertIn("  vitamin tablets: deployed: 17 (tablet) S 11/12 (4 in the first 4) U 0 | this checkout: 1"
                      " products, by their words, of the kinds (doubtful) 1", out)
        self.assertNotIn("shop.invalid", out)
        self.assertNotIn("== 7.", out)

    def test_each_part_on_its_own(self) -> None:
        kinds = _run(str(self.path), "--part", "kinds").stdout
        self.assertIn("== 5. The words", kinds)
        self.assertIn("== In short (the kinds)", kinds)
        self.assertNotIn("searching", kinds)
        searches = _run(str(self.path), "--part", "searches").stdout
        self.assertNotIn("== 1.", searches)
        self.assertIn("== 6. Every kind's search", searches)
        self.assertIn("== In short (the searches on the copy)", searches)
        # Without a site, the live part reads nothing.
        live = _run(str(self.path), "--part", "live").stdout
        # The owner's words, the searches by a product's own name, and the first kinds'.
        self.assertIn("searching 45 words on the copy\n", live)
        self.assertNotIn("== 6.", live)
        self.assertNotIn("== 7.", live)

    def test_the_live_site_matched_to_the_copy(self) -> None:
        # The site, as the server serves it from the same file with the rules deployed:
        # here, this checkout's app answering from the file's stored kinds.
        environment = dict(os.environ)
        try:
            os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(self.path)
            os.environ["PICWISE_PREPARED_MAX_AGE_HOURS"] = "100000"
            for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "PICWISE_PURCHASABILITY_CACHE_FILE"):
                os.environ.pop(name, None)
            from api.index import app as wsgi_app
            from picwise_providers import state

            state._PREPARED_STATE.clear()
            server = make_server("127.0.0.1", 0, wsgi_app, handler_class=_Quiet)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = _run(str(self.path), "--part", "live", "--site", f"http://127.0.0.1:{server.server_port}")
            finally:
                server.shutdown()
                server.server_close()
                state._PREPARED_STATE.clear()
        finally:
            os.environ.clear()
            os.environ.update(environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("== 7. The same searches on the live site", out)
        self.assertIn("  tablet: 12 of 17, 12 cards, 12 of them the copy's, the same in order; S 11", out)
        self.assertRegex(out, r"      live #1 S +3\.00 GBP \| Fictional Pharmacy \| Fixturon Milk Thistle")
        self.assertIn("  mouse: 5 of 5, 5 cards, 5 of them the copy's, the same in order; S 1", out)
        # The owner's words, the searches by a product's own name and the first kinds': the
        # site answers from the stored kinds, where the pills are still tablets.
        self.assertRegex(out, r"  45 pages read; 45 show the copy's cards, card for card")
        self.assertIn("  7 of 45 pages read (45 the copy's cards, card for card): electrolyte tablets 11, kids tablet 11,"
                      " tablet 11, tablets 11, vitamin tablets 11, mouse 1, sugar mice 1", out)
        self.assertNotIn("== 6.", out)

    def test_an_unreadable_file_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            path.write_bytes(b"not a prepared file")
            result = _run(str(path))
        self.assertEqual(result.returncode, 0)
        self.assertIn("no prepared catalogue could be read", result.stdout)

    def test_no_file_named_says_how(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False, timeout=120)
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: print_confusions.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
