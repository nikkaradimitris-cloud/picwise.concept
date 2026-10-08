"""Which kind of product a feed row is, read around "for" and "with".

Only the words before a purpose word name the product. A shop category such as
"Accessories for Laptops" used to be read as laptops, so a laptop sleeve was shown as one
of the four laptops; a title such as "Robot Vacuum Cleaner with HEPA Filter" used to be
read as an accessory because of a word that only lists what comes in the box, so a real
robot vacuum was never shown. Found while closing audit finding F3
(docs/picwise_mission_truth_audit_2026-10-08.md).

Served through api/index.py, the deployed entry point. All rows are local test data:
fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
    "data_provenance",
)


class ProductKindReadingTests(unittest.TestCase):
    def _serve(self, rows: list[tuple[str, str, str, str]]) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for pid, title, kind, price in rows:
                writer.writerow(
                    [pid, title, title.split()[0], kind, kind,
                     f"https://fixture.example.invalid/out/{pid}",
                     f"https://fixture.example.invalid/img/{pid}.jpg", price, "GBP", "1",
                     "Fixture Store One", "local_test_fixture"]
                )
        previous = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if previous is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = previous
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def _shown(self, query: str) -> tuple[list[str], str]:
        def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
            return None

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": urlencode({"q": query}),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        ).decode("utf-8")
        cards = re.findall(r'<article class="pw-card[^"]*" data-choice-id="([^"]+)"', body)
        return cards, body

    def test_an_accessory_category_for_a_product_is_never_that_product(self) -> None:
        self._serve(
            [
                ("l1", "Fixturon Vantage 14 Laptop", "Laptops", "699.00"),
                ("l2", "Testline Air 13 Laptop", "Laptops", "899.00"),
                ("l3", "Sampleworks Pro 16 Laptop", "Laptops", "1199.00"),
                ("s1", "Fixturon Neoprene Sleeve 15.6", "Accessories for Laptops", "19.00"),
            ]
        )
        for query in ("laptop", "λάπτοπ"):
            with self.subTest(query=query):
                shown, body = self._shown(query)
                # Three laptops cannot make four, and the sleeve does not make up the
                # number: the page says so instead.
                self.assertNotIn("s1", shown)
                self.assertEqual(shown, [])
                self.assertIn("has no four products it can show for it", body)

    def test_what_comes_with_a_product_does_not_hide_it(self) -> None:
        self._serve(
            [
                # No product type and a category naming no kind: the title decides.
                ("r1", "Fixturon Robot Vacuum Cleaner with HEPA Filter", "Home", "199.00"),
                ("r2", "Testline Robot Vacuum Cleaner S5", "Robot Vacuums", "249.00"),
                ("r3", "Sampleworks Robot Vacuum Cleaner X", "Robot Vacuums", "299.00"),
                ("r4", "Fixturon Robot Vacuum Cleaner Mini", "Robot Vacuums", "349.00"),
            ]
        )
        for query in ("robot vacuum", "σκούπα ρομπότ"):
            with self.subTest(query=query):
                shown, _body = self._shown(query)
                self.assertEqual(sorted(shown), ["r1", "r2", "r3", "r4"])


if __name__ == "__main__":
    unittest.main()
