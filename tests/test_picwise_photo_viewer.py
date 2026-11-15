"""A card's photo opens large at a tap, with the shop's further photos (owner, 2026-11-15).

«Ο χρήστης μπορεί να έχει τη δυνατότητα η εικόνα του προϊόντος να μεγαλώνει», on every
search, and of the shop's further photos: «όποιος στέλνει επιπλέον φωτογραφίες ...
εμφανίζουμε έως 4». Pinned here:

- the further photos are read from Google's `additional_image_link`, commas between
  them, at most three beside the main photo, none twice and only web addresses;
- every card's photo can be opened (a button for a keyboard and a reader), says how many
  photos it holds when more than one, and holds the further ones hidden, loading only
  when opened;
- the page carries the viewer: it opens over the page and closes with a second tap, the
  ✕, a tap beside it, Esc, a swipe down or the back button; the heart stays the heart's;
- the home page carries none of it.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.normalization import MAX_EXTRA_IMAGES, extra_image_urls  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_surface.photo_viewer import PHOTO_VIEWER_SCRIPT, PHOTO_VIEWER_STYLES  # noqa: E402
from test_picwise_design_2026_10_31 import _call, _cards, _ean13  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "additional_image_link", "search_price", "currency", "in_stock",
    "merchant_name", "description", "data_provenance", "ean",
)


def _img(pid: str, n: int | str) -> str:
    return f"https://fixture.example.invalid/img/{pid}-{n}.jpg"


class ExtraImageTests(unittest.TestCase):
    def test_at_most_three_none_twice_only_web_addresses(self) -> None:
        main = _img("a", "main")
        raw = {"additional_image_link": ",".join([_img("a", 1), main, _img("a", 1), "not a link", _img("a", 2),
                                                  _img("a", 3), _img("a", 4)])}
        self.assertEqual(extra_image_urls(raw, main), (_img("a", 1), _img("a", 2), _img("a", 3)))
        self.assertEqual(MAX_EXTRA_IMAGES, 3)

    def test_a_comma_inside_an_address_is_kept(self) -> None:
        raw = {"additional_image_link": "https://fixture.example.invalid/img/w_400,h_400/a.jpg, " + _img("a", 2)}
        self.assertEqual(
            extra_image_urls(raw, ""), ("https://fixture.example.invalid/img/w_400,h_400/a.jpg", _img("a", 2))
        )

    def test_nothing_sent_nothing_read(self) -> None:
        self.assertEqual(extra_image_urls({}, ""), ())
        self.assertEqual(extra_image_urls(None, ""), ())
        self.assertEqual(extra_image_urls({"additional_image_link": ""}, ""), ())


class CardPhotoTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for index in range(1, 7):
                pid = f"k{index}"
                extras = ",".join(_img(pid, n) for n in range(1, 6)) if index == 1 else ""
                writer.writerow([
                    pid, f"Fixturon Kettle Model {index} 1.7L", "Fixturon", "Kettles", "Kitchen Appliances",
                    f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                    extras, f"{10 + 3 * index}.00", "GBP", "1", "Fixture Store One", fixture_description(),
                    "local_test_fixture", _ean13(f"50{index:010d}"),
                ])
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
        self.page = _call("/search", {"q": "kettle", "shown": "8"})
        self.cards = {re.search(r'data-choice-id="([^"]+)"', card).group(1): card for card in _cards(self.page)}

    def test_every_card_s_photo_opens(self) -> None:
        self.assertEqual(len(self.cards), 6)
        for card in self.cards.values():
            self.assertIn('class="pw-product-image-wrap pw-zoomable" tabindex="0" role="button"', card)
            # The heart stays inside the photo's frame, and the viewer leaves it be.
            self.assertIn('class="pw-fav', card)
        self.assertIn('target.closest(".pw-fav")', PHOTO_VIEWER_SCRIPT)

    def test_a_card_with_further_photos_holds_up_to_four(self) -> None:
        card = self.cards["k1"]
        self.assertIn('data-photos="4"', card)
        self.assertIn('aria-label="Open the 4 photos of Fixturon Kettle Model 1 1.7L"', card)
        self.assertIn('<span class="pw-zoom-count">4</span>', card)
        extras = re.search(r'<span class="pw-photo-extras" hidden>(.*?)</span>', card, re.S).group(1)
        self.assertEqual(re.findall(r'src="([^"]+)"', extras), [_img("k1", 1), _img("k1", 2), _img("k1", 3)])
        self.assertEqual(extras.count('loading="lazy"'), 3)
        self.assertIn('alt="Fixturon Kettle Model 1 1.7L, photo 2 of 4"', extras)
        # The main photo is the card's photo as before.
        self.assertIn('src="https://fixture.example.invalid/img/k1.jpg"', card)

    def test_a_card_with_one_photo_opens_it_alone(self) -> None:
        card = self.cards["k2"]
        self.assertIn('data-photos="1"', card)
        self.assertIn('aria-label="Open the photo of Fixturon Kettle Model 2 1.7L"', card)
        self.assertNotIn("pw-zoom-count", card)
        self.assertNotIn("pw-photo-extras", card)
        self.assertIn('class="pw-zoom-hint"', card)

    def test_the_page_carries_the_viewer(self) -> None:
        self.assertIn(PHOTO_VIEWER_SCRIPT.strip()[:40], self.page)
        self.assertIn(".pw-viewer{position:fixed;", self.page)
        for words in ('"Escape"', '"popstate"', "history.pushState", "history.back()", "dy>80",
                      '"ArrowRight"', '"ArrowLeft"', "close(false)", 'img.pw-photo-extra'):
            self.assertIn(words, PHOTO_VIEWER_SCRIPT)
        # Large over the page: nearly a phone's whole width, most of a wide screen.
        self.assertIn(".pw-viewer-img{display:block;width:min(100%,85vh,960px);", PHOTO_VIEWER_STYLES)
        self.assertIn(".pw-viewer-img{width:100%;}", PHOTO_VIEWER_STYLES)
        # The hint shows only where the script runs.
        self.assertIn(".pw-js .pw-zoom-hint{display:flex;}", PHOTO_VIEWER_STYLES)

    def test_the_home_page_carries_none_of_it(self) -> None:
        home = _call("/")
        self.assertNotIn("pw-viewer", home)
        self.assertNotIn("pw-zoomable", home)


if __name__ == "__main__":
    unittest.main()
