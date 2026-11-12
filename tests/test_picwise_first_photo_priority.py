"""The first card's photo is asked for first (docs/PICWISE_AUDIT_FIXES.md, section 4, A.1).

A card is seen only once its photo has loaded (PROJECT_RULES.md section 2), so the first
card of a page waits on its photo. `fetchpriority="high"` asks the browser for that photo
before the page's others. Pinned here: one photo of a page carries it, the first card's,
on a page of four, on a page "More" drew with eight and on the one product's own layout;
the first row's photos still load at once and the others as the page is scrolled to
them, each decoded apart from the page.

Every row is written with fictional brands and `.invalid` URLs, served through
api/index.py, the deployed entry point (the rows and helpers of the design's tests).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_picwise_design_2026_10_31 as design  # noqa: E402

_IMAGE = re.compile(r'<img class="pw-product-image" [^>]+>')


def _images(page: str) -> list[str]:
    """Each card's photo, in the order of the cards."""
    images = []
    for card in design._cards(page):
        found = _IMAGE.search(card)
        if found is None:
            raise AssertionError("a card without its photo")
        images.append(found.group(0))
    return images


class FirstPhotoPriorityTests(design._FeedMixin, unittest.TestCase):
    def test_on_a_page_of_four_only_the_first_cards_photo_is_asked_for_first(self) -> None:
        self._serve(design._kettles())
        page = design._call("/search", {"q": "kettle"})
        images = _images(page)
        self.assertEqual(len(images), 4)
        self.assertIn('fetchpriority="high"', images[0])
        for image in images[1:]:
            self.assertNotIn("fetchpriority", image)
        self.assertEqual(page.count("fetchpriority"), 1)

    def test_a_page_more_drew_still_marks_only_the_first_card(self) -> None:
        self._serve(design._kettles())
        page = design._call("/search", {"q": "kettle", "shown": "8"})
        images = _images(page)
        self.assertEqual(len(images), 8)
        self.assertIn('fetchpriority="high"', images[0])
        self.assertEqual(page.count("fetchpriority"), 1)

    def test_the_first_row_loads_at_once_and_the_rest_as_scrolled_to(self) -> None:
        self._serve(design._kettles())
        images = _images(design._call("/search", {"q": "kettle", "shown": "8"}))
        for image in images[:4]:
            self.assertIn('loading="eager"', image)
        for image in images[4:]:
            self.assertIn('loading="lazy"', image)
        for image in images:
            self.assertIn('decoding="async"', image)
            self.assertIn('width="400" height="400"', image)

    def test_the_one_products_own_layout_asks_for_its_photo_first(self) -> None:
        self._serve(design._kettles()[:1])
        page = design._call("/search", {"q": "kettle"})
        images = _images(page)
        self.assertEqual(len(images), 1)
        self.assertIn('fetchpriority="high"', images[0])
        self.assertEqual(page.count("fetchpriority"), 1)


if __name__ == "__main__":
    unittest.main()
