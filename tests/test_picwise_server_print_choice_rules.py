"""What each rule of the choices for a general word changes, on a copy of the server's catalogue.

`deployment/server/print_choice_rules.py`, run by `.github/workflows/server-cap.yml`
(owner, 2026-10-29: «εσύ πρέπει να αποφασίσεις ποιος είναι ο βέλτιστος τρόπος», each rule
measured before any deployment). Pinned here: the file is read again with this
checkout's rules, kinds stored by older rules notwithstanding; the choices are worked
out with every rule and without each, and each rule's line says what it leaves out and
lets in ("robertson suit" of one shop, "piece suit" for "3 piece suit" and "2 piece
suit", "denim jeans" keeping all the jeans, "bootcut jean" for "bootcut jeans"); every
general kind's choices are printed with what each one's search keeps and why the
others were left out; nothing printed is a link; an unreadable file says so; every case
exits 0. Every row is local test data: fictional brands and shops, `.invalid` addresses.
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
SCRIPT = ROOT / "deployment" / "server" / "print_choice_rules.py"
for path in (HERE, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_search_fields  # noqa: E402

SUITS = "Apparel & Accessories > Clothing > Suits"
JEANS = "Apparel & Accessories > Clothing > Pants > Jeans"


def _product(number: int, title: str, category: str, shop: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand="Fixturon",
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{20 + number % 50:.2f}",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop, "in_stock": "1", "description": fixture_description()},
    )


def _write(path: Path) -> None:
    products = []
    for title, category, count in (
        ("Fixturon 3 Piece Suit {n}", SUITS, 30),
        ("Fixturon 2 Piece Suit {n}", SUITS, 25),
        ("Fixturon Tweed Suit {n}", SUITS, 25),
        ("Fixturon Robertson Suit {n}", SUITS, 22),
        ("Fixturon Denim Bootcut Jeans {n}", JEANS, 30),
        ("Fixturon Denim Embroidered Jeans {n}", JEANS, 25),
        ("Fixturon Denim Jeans {n}", JEANS, 25),
    ):
        for step in range(count):
            number = len(products) + 1
            one_shop = title.startswith("Fixturon Robertson")
            shop = "Fictional Store One" if one_shop or number % 2 else "Fictional Store Two"
            products.append(_product(number, title.format(n=step + 1), category, shop))
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


class PrintChoiceRulesTests(unittest.TestCase):
    def test_what_each_rule_changes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            result = _run(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("182 new products a search reads", out)
        self.assertIn("every rule: 2 kinds ask which one is meant, 5 choices", out)
        self.assertIn("the rule 'shops' leaves out 1 choices and lets in 0", out)
        self.assertIn("    suit: robertson suit 22 (1 shop)", out)
        self.assertIn("the rule 'phrases' leaves out 1 choices and lets in 2", out)
        self.assertIn("    suit: piece suit 55 (half of a phrase)", out)
        self.assertIn("    suit: 3 piece suit 30", out)
        self.assertIn("the rule 'whole_kind' leaves out 1 choices and lets in 0", out)
        # "denim" comes before "jeans" in every jeans title, one word between at most.
        self.assertIn("    jeans: denim jeans 25 (its search keeps 80)", out)
        # Without the rule the jeans asked nothing: "bootcut jean" is no search it reads.
        self.assertIn("the rule 'written' leaves out 0 choices and lets in 2", out)
        self.assertIn("    jeans: bootcut jeans 30", out)
        self.assertIn("  suit 102: 3 piece suit 30/30; 2 piece suit 25/25; tweed suit 25/25", out)
        self.assertIn("  jeans 80: bootcut jeans 30/30; embroidered jeans 25/25", out)
        self.assertIn("      left out: piece suit 55 (half of a phrase); robertson suit 22 (1 shop)", out)
        self.assertIn("      left out: denim jeans 25 (its search keeps 80)", out)
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
