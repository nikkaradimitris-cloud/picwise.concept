"""The read-only check of the live site's photos and offers (`.github/scripts/live_photos.py`).

The owner, 2026-11-01: «έχω παρατηρήσει ότι και σε άλλα προϊόντα η εικόνα είναι χαλασμένη».
Pinned here: the check reads the cards as the site draws them, fetches a photo where a
browser on an https page would, tells a picture from a page by its first bytes, and counts
each photo once per shop and per host. Every shop and product is fictional.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.product_offers import set_offers_document  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from test_picwise_offers_first import KETTLES, _COLUMNS, _ean13, _offer, _shop  # noqa: E402

_SPEC = importlib.util.spec_from_file_location("live_photos", ROOT / ".github" / "scripts" / "live_photos.py")
live_photos = importlib.util.module_from_spec(_SPEC)
sys.modules["live_photos"] = live_photos
_SPEC.loader.exec_module(live_photos)


class LivePageCardsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.get("AWIN_FEED_FILE")
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for index, (pid, title, price, shop, shop_id) in enumerate(KETTLES, start=1):
                writer.writerow([pid, title, title.split()[0], "Kettles", "Kitchen Appliances",
                                 f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                                 price, "GBP", "1", shop, shop_id, fixture_description(), "local_test_fixture",
                                 _ean13(f"50{index:010d}")])
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def tearDown(self) -> None:
        set_offers_document(None)
        if self._previous is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = self._previous
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def test_the_cards_of_a_page_as_the_site_draws_them(self) -> None:
        set_offers_document({"shops": {"1003": _shop("Fixture Store Three", [
            _offer(7, "10% off kettles", code="KETTLE10"),
        ], joined=True)}})
        page = b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search", "QUERY_STRING": urlencode({"q": "kettle"}),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")
        cards = live_photos.page_cards("kettle", page)
        self.assertEqual(len(cards), 4)
        first = cards[0]
        self.assertTrue(first.recommended)
        self.assertEqual((first.role, first.price, first.shop), ("On offer", "£28.00", "Fixture Store Three"))
        self.assertIn("10% off kettles", first.offer)
        self.assertEqual(first.image, "https://fixture.example.invalid/img/k6.jpg")
        self.assertEqual([card.recommended for card in cards[1:]], [False, False, False])
        self.assertEqual(cards[3].role, "Lowest price")
        self.assertEqual(cards[3].offer, "")


class PhotoRulesTests(unittest.TestCase):
    def test_a_photo_given_as_http_is_fetched_over_https(self) -> None:
        self.assertEqual(live_photos.browser_address("http://img.example.invalid/a.jpg"), "https://img.example.invalid/a.jpg")
        self.assertEqual(live_photos.browser_address("HTTP://img.example.invalid/a.jpg"), "https://img.example.invalid/a.jpg")
        self.assertEqual(live_photos.browser_address("https://img.example.invalid/a.jpg"), "https://img.example.invalid/a.jpg")

    def test_a_picture_is_told_from_a_page_by_its_first_bytes(self) -> None:
        self.assertEqual(live_photos.image_kind(b"\xff\xd8\xff\xe0rest"), "jpeg")
        self.assertEqual(live_photos.image_kind(b"\x89PNG\r\n\x1a\nrest"), "png")
        self.assertEqual(live_photos.image_kind(b"GIF89arest"), "gif")
        self.assertEqual(live_photos.image_kind(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "webp")
        self.assertEqual(live_photos.image_kind(b"\x00\x00\x00\x1cftypavif"), "avif")
        self.assertEqual(live_photos.image_kind(b'<svg xmlns="http://www.w3.org/2000/svg">'), "svg")
        self.assertEqual(live_photos.image_kind(b"<!doctype html><html>Hotlinking not allowed"), "")
        self.assertEqual(live_photos.image_kind(b""), "")

    def test_each_photo_is_counted_once_per_shop_and_host(self) -> None:
        def card(shop: str, image: str) -> live_photos.Card:
            return live_photos.Card("q", False, "", "£1.00", shop, "A product", "", image)

        good = live_photos.Photo("https://a.example.invalid/1.jpg", ok=True)
        good.cards += [card("Fixture Store One", good.url), card("Fixture Store One", good.url)]
        refused = live_photos.Photo("https://b.example.invalid/2.jpg", ok=False, why="HTTP 403", without_referer="")
        refused.cards.append(card("Fixture Store One", refused.url))
        dead = live_photos.Photo("http://b.example.invalid/3.jpg", ok=False, why="HTTP 404", without_referer="HTTP 404")
        dead.cards.append(card("Fixture Store Two", dead.url))
        lines = live_photos.summary({photo.url: photo for photo in (good, refused, dead)})
        text = "\n".join(lines)
        self.assertIn("Fixture Store One", text)
        one = next(line for line in lines if line.strip().startswith("Fixture Store One"))
        self.assertIn("1 of   2 load", one)
        self.assertIn("HTTP 403 x1", one)
        self.assertIn("loads without a Referer x1", one)
        host_b = next(line for line in lines if line.strip().startswith("b.example.invalid"))
        self.assertIn("0 of   2 load", host_b)
        self.assertIn("== examples of photos that fail (of 2)", text)


if __name__ == "__main__":
    unittest.main()
