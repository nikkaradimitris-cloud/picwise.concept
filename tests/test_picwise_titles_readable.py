"""Titles read as a buyer reads them (owner, 2026-11-24: «Ναι φτιάξε και τη μικρή διόρθωση»).

Some shops' feeds carry their titles HTML-encoded ("Monitor 22&quot;"), and the page escapes
the title again, so the card read "22&quot;" (PCHUB.UK 1,564 and GamingKit 1,577 titles of the
catalogue of 24/11). Pinned here: the codes are read once (twice for a text encoded twice);
an id worked out from the title does not move; the card shows 22", escaped once.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.normalization import normalize_feed_row_to_provider_product, readable_title  # noqa: E402
from test_picwise_design_2026_10_31 import _FeedMixin, _call, _cards, _ean13, _text  # noqa: E402


class ReadableTitleTests(unittest.TestCase):
    def test_html_codes_are_read_once(self) -> None:
        self.assertEqual(readable_title("Fixturon Monitor 22&quot; Black &amp; Silver"),
                         'Fixturon Monitor 22" Black & Silver')
        self.assertEqual(readable_title("Fixturon &amp;quot;Pro&amp;quot;"), 'Fixturon "Pro"')
        self.assertEqual(readable_title("Fixturon&nbsp; Kettle &#8211; 1.7L"), "Fixturon Kettle – 1.7L")
        self.assertEqual(readable_title('Fixturon Monitor 22" Black & Silver'), 'Fixturon Monitor 22" Black & Silver')

    def test_a_row_s_title_is_readable_and_an_id_from_the_title_does_not_move(self) -> None:
        row = {"product_name": "Fixturon Monitor 22&quot;",
               "aw_deep_link": "https://fixture.example.invalid/out/m1"}
        product = normalize_feed_row_to_provider_product(row, provider_key="awin")
        self.assertEqual(product.title, 'Fixturon Monitor 22"')
        same_url_written_plainly = normalize_feed_row_to_provider_product(
            {**row, "product_name": 'Fixturon Monitor 22"'}, provider_key="awin")
        # The id is worked out from the title as the feed wrote it, as it was before.
        self.assertNotEqual(product.provider_product_id, same_url_written_plainly.provider_product_id)
        self.assertEqual(product.raw["product_name"], "Fixturon Monitor 22&quot;")


class CardTitleTests(_FeedMixin, unittest.TestCase):
    def test_the_card_shows_the_title_escaped_once(self) -> None:
        self._serve([
            {"pid": f"k{index}", "title": f"Fixturon Kettle Model {index} &quot;Classic&quot; 1.7L",
             "price": f"{price:.2f}", "ean": _ean13(f"61{index:010d}")}
            for index, price in enumerate((19.0, 24.0, 29.0, 34.0, 39.0), start=1)
        ])
        page = _call("/search", {"q": "kettle"})
        cards = _cards(page)
        self.assertTrue(cards)
        self.assertNotIn("&amp;quot;", page)
        titles = [_text(re.search(r'class="pw-card-title"[^>]*>(.*?)</', card, re.S).group(1)) for card in cards]
        self.assertTrue(all('"' in title and "&quot;" not in title for title in titles), titles)


if __name__ == "__main__":
    unittest.main()
