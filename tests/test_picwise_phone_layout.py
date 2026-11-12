"""The search page on a phone (the audit, 2026-11-10; owner, the same day: «Ζητώ διόρθωση και
βελτίωση ... στη ορατότητα σε κινητές συσκευές»).

The audit rendered the live site's pages at 360x640 and 390x664: with two cards a row no
"View" button was on the first screen, the four cards were 2.5 screens long, words were
10 to 13 px, "Mid-priced for this catego" was cut, and the buttons were 36 to 40 px.
Rendered again with these styles, the Recommended and its button are on the first
screen at both sizes. Pinned here, in the styles a phone is given (`@media
(max-width:699px)`), since a test has no browser:

- one product a row, its photo beside its words, the price with the button beside it;
- a product alone keeps its own layout;
- no word under 12 px;
- whatever is tapped is at least 44 px: the search's buttons, the header's, the card's
  button, "More", the footer's links, a kind's choice;
- the computer's layout is as it was.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_surface.browser_lists import BROWSER_LISTS_STYLES  # noqa: E402
from picwise_surface.legal import _base_styles  # noqa: E402
from picwise_surface.reference import _PAGE_STYLES  # noqa: E402

_PHONE = "@media (max-width:699px){"
_LIST_CARD = '.pw-grid:not([data-layout="single"])'


def _phone(styles: str, opening: str = _PHONE) -> str:
    """The rules a phone is given: the last block of the styles."""
    assert styles.count(opening) == 1 and styles.endswith("}")
    return styles.split(opening, 1)[1][:-1]


def _rule(block: str, selector: str) -> str:
    """The declarations of one selector's rule in a block of styles."""
    found = re.search(r"(?:^|\})" + re.escape(selector) + r"\{([^}]*)\}", block)
    assert found, selector
    return found.group(1)


class PhoneLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = _phone(_PAGE_STYLES)
        self.lists = _phone(BROWSER_LISTS_STYLES)

    def test_one_product_a_row_with_its_photo_beside_its_words(self) -> None:
        self.assertIn("grid-template-columns:minmax(0,1fr);", _rule(self.page, ".pw-grid,.pw-grid[data-card-count]"))
        card = _rule(self.page, f"{_LIST_CARD} .pw-card")
        self.assertIn("display:grid;", card)
        self.assertIn("grid-template-columns:96px minmax(0,1fr);", card)
        self.assertIn("grid-column:1;", _rule(self.page, f"{_LIST_CARD} .pw-product-image-wrap"))
        # The card's words are placed one by one beside and under the photo.
        self.assertEqual(_rule(self.page, f"{_LIST_CARD} .pw-card-body"), "display:contents;")
        self.assertIn("grid-column:2;", _rule(self.page, f"{_LIST_CARD} .pw-card-body>*"))

    def test_the_price_with_the_button_beside_it_under_the_limitation(self) -> None:
        note = _rule(self.page, f"{_LIST_CARD} .pw-card-body>.pw-card-note")
        price = _rule(self.page, f"{_LIST_CARD} .pw-card-body>.pw-price")
        button = _rule(self.page, f"{_LIST_CARD} .pw-card-body>.pw-card-cta")
        for rule in (note, price, button):
            self.assertIn("grid-column:1 / -1;", rule)
        self.assertIn("grid-row:19;", note)
        self.assertIn("grid-row:20;", price)
        self.assertIn("grid-row:20;", button)
        self.assertIn("justify-self:end;", button)

    def test_a_product_alone_keeps_its_own_layout(self) -> None:
        # Every rule that lays the list's card out leaves a product alone as it was.
        for selector in re.findall(r"(?:^|\})([^{}]*\.pw-card-body[^{}]*)\{", self.page):
            self.assertTrue(selector.startswith(_LIST_CARD), selector)
        self.assertIn('.pw-grid[data-layout="single"] .pw-card{grid-template-columns:1fr;', _PAGE_STYLES)

    def test_no_word_under_12_px(self) -> None:
        for name, block in (("page", self.page), ("lists", self.lists)):
            sizes = [float(size) for size in re.findall(r"font-size:([\d.]+)px", block)]
            self.assertTrue(sizes, name)
            self.assertGreaterEqual(min(sizes), 12.0, name)
        # The words the audit measured under 12 px on a phone, each given its size here.
        self.assertIn("font-size:12px;", _rule(self.page, ".pw-rec-badge,.pw-role-label"))
        self.assertIn("font-size:12px;", _rule(self.page, ".pw-card-note"))
        self.assertIn("font-size:15px;", _rule(self.page, ".pw-card-title"))

    def test_the_recommendation_is_said_whole(self) -> None:
        self.assertIn("white-space:normal;", _rule(self.page, ".pw-role-label"))
        role = _rule(self.page, ".pw-role")
        self.assertIn("height:auto;", role)
        self.assertIn("overflow:visible;", role)
        self.assertIn("white-space:normal;", _rule(self.page, ".pw-card-shop"))

    def test_whatever_is_tapped_is_at_least_44_px(self) -> None:
        for selector in (".pw-mic-button", ".pw-search-button", ".pw-info-link"):
            rule = _rule(self.page, selector)
            self.assertIn("width:44px;", rule, selector)
            self.assertIn("height:44px;", rule, selector)
        self.assertIn("min-height:44px;", _rule(self.page, ".pw-card-cta"))
        self.assertIn("min-height:44px;", _rule(self.page, ".pw-footer-link"))
        self.assertIn("height:44px;", _rule(self.page, ".pw-kind-choice"))
        self.assertIn("height:48px;", _rule(self.page, ".pw-more-button"))
        head = _rule(self.lists, ".pw-head-btn")
        self.assertIn("width:44px;", head)
        self.assertIn("height:44px;", head)
        # The heart keeps its look and takes the taps around it; so does "Did you mean".
        self.assertIn("top:-5px;", _rule(self.lists, ".pw-fav::after"))
        self.assertIn("top:-13px;", _rule(self.page, ".pw-reference-disclaimer a::after"))
        legal = _phone(_base_styles(), "@media (max-width:760px){")
        self.assertIn("min-height:44px;", _rule(legal, ".pw-footer-link"))

    def test_the_computers_layout_is_as_it_was(self) -> None:
        wide = _PAGE_STYLES.split(_PHONE, 1)[0]
        self.assertIn(".pw-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;", wide)
        self.assertIn(".pw-card{position:relative;display:flex;flex-direction:column;", wide)
        self.assertIn(".pw-card-body{display:flex;flex-direction:column;flex:1;min-width:0;}", wide)
        self.assertNotIn("display:contents", wide)


if __name__ == "__main__":
    unittest.main()
