"""A look at a few shops' links (`deployment/server/look_shop_links.py`; owner, 2026-11-24:
PCHUB.UK's buy buttons do not lead to the shop, «βγάζεις σφάλμα 503 αν θυμάμαι καλά»).

Pinned here: links are read as text, by kind and by their parameters' names; an HTML code
left in a link breaks a parameter's name and is counted; Awin's product number is checked
against the row's id; a shop's own pages are asked only as robots.txt allows, never an Awin
link, and the output carries no address and no link.

Every row is local test data: fictional brands, `.invalid` hosts. Nothing leaves the
machine: the answers are the test's own.
"""
from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_spec = importlib.util.spec_from_file_location("look_shop_links", ROOT / "deployment" / "server" / "look_shop_links.py")
links = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = links
_spec.loader.exec_module(links)

import shop_catalogue_test as look  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402


def _product(pid: str, shop: str, link: str, own: str, title: str = "Fixturon Monitor 22\"") -> ProviderProduct:
    raw = {"merchant_name": shop, "merchant_id": "77", "merchant_deep_link": own}
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=title, brand="Fixturon", category_text="Monitors",
        product_url=link, image_url=f"https://img.example.invalid/{pid}.jpg", price_text="99.99",
        availability_text="in stock", currency="GBP", raw=raw,
    )


class LookShopLinksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            _product("101", "Fixture Hub", "https://www.awin1.com/pclick.php?p=101&a=9&m=77",
                     "https://shop.example.invalid/monitor-22.html"),
            _product("102", "Fixture Hub", "https://www.awin1.com/pclick.php?p=102&amp;a=9&amp;m=77",
                     "https://shop.example.invalid/monitor-24.html?x=1&amp;y=2", title="Fixturon 24&quot;"),
            _product("103", "Fixture Hub", "https://www.awin1.com/pclick.php?p=999&a=9&m=77",
                     "https://shop.example.invalid/monitor-27.html"),
        ]

    def test_links_counted_by_kind_parameters_codes_and_ids(self) -> None:
        tally = links.look_at(self.products)["Fixture Hub"]
        self.assertEqual(tally["products"], 3)
        self.assertEqual(tally["link: Awin pclick.php"], 3)
        self.assertEqual(tally["params: p,a,m"], 2)
        self.assertEqual(tally["params: p,amp;a,amp;m"], 1)
        self.assertEqual(tally["HTML code in the button's link"], 1)
        self.assertEqual(tally["HTML code in the shop's own address"], 1)
        self.assertEqual(tally["HTML code in the title"], 1)
        self.assertEqual(tally["Awin's product number = the row's id"], 2)
        self.assertEqual(tally["Awin's product number != the row's id"], 1)
        self.assertEqual(tally["Awin's advertiser = the row's"], 3)

    def test_pages_asked_as_robots_allows_never_awin_and_no_address_printed(self) -> None:
        asked: list[str] = []

        def fetch(url: str, limit: int = 0) -> look.Answer:
            asked.append(url)
            if url.endswith("/robots.txt"):
                return look.Answer(404)
            return look.Answer(503 if "&amp;" in url else 200, "text/html", b"<html></html>")

        prepared = SimpleNamespace(prepared_at=datetime(2026, 11, 24, tzinfo=timezone.utc), products=self.products)
        out = io.StringIO()
        with redirect_stdout(out):
            code = links.main(["--shop", "Fixture Hub", "--ask", "Fixture Hub", "--pages", "3"],
                              prepared=prepared, fetch=lambda url, limit=0: fetch(url, limit),
                              sleep=lambda seconds: None)
        self.assertEqual(code, 0)
        self.assertFalse(any("awin1.com" in url for url in asked))
        self.assertIn("as written: 503", out.getvalue())
        self.assertIn("codes read: 200", out.getvalue())
        self.assertNotIn("monitor-2", out.getvalue())
        self.assertNotIn("awin1.com", out.getvalue())


if __name__ == "__main__":
    unittest.main()
