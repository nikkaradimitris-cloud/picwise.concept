"""A card's price note under its price (`picwise_surface.price_notes`; the owner,
2026-11-13: «Συμφωνώ με το σχεδιασμό», to the pictures of that day).

Pinned here:

- a fall is a green ▼ with its amount and since when, a rise a red ▲, a price kept 7
  nights or more a grey "Same price for N nights"; a screen reader hears "Price down";
- the chip opens (plain `<details>`, no script) the last nights as the shop listed
  them: a chart, now, lowest and highest with their nights, a gap said when there is one;
- every card of an answer is looked up, not only the Recommended's, by the shop as its
  feed row names it and the product's id; where any card has a note, the others keep
  its line; where none has, nothing is added to any card;
- no note is shown beside a catalogue another preparation wrote, and nothing on the home
  page.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import re
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import test_picwise_design_2026_10_31 as design  # noqa: E402
from picwise_providers.price_history import DOWN, SAME, UP, PriceNote, PriceNotes, PriceRun  # noqa: E402
from picwise_surface import reference  # noqa: E402
from picwise_surface.price_notes import PRICE_NOTE_STYLES, price_note_html  # noqa: E402

NIGHT = date(2026, 12, 13)


def _down() -> PriceNote:
    return PriceNote(
        kind=DOWN, night=NIGHT, currency="GBP", change_pence=4000, since=date(2026, 12, 6),
        runs=(
            PriceRun(date(2026, 11, 14), date(2026, 11, 23), 10, 124900, "GBP"),
            PriceRun(date(2026, 11, 24), date(2026, 12, 5), 12, 123800, "GBP"),
            PriceRun(date(2026, 12, 6), NIGHT, 8, 119800, "GBP"),
        ),
    )


def _text(fragment: str) -> str:
    return design._text(fragment)


def _chart_path(html: str) -> str:
    return re.search(r'<svg class="pw-ph-chart".*?<path d="([^"]+)"', html, re.S).group(1)


class ChipTests(unittest.TestCase):
    def test_a_fall_is_green_with_its_amount_and_since_when(self) -> None:
        html = price_note_html(_down(), shop="Fixture Store One", price="£1,198.00")
        self.assertIn('<details class="pw-ph pw-ph-down">', html)
        summary = re.search(r"<summary.*?</summary>", html, re.S).group(0)
        self.assertEqual(_text(summary), "▼ Price down £40 since 6 Dec")
        self.assertIn('<span class="pw-ph-a" aria-hidden="true">&#9660;</span>', summary)
        self.assertIn(".pw-ph-down .pw-ph-chip{color:#15803d;", PRICE_NOTE_STYLES)

    def test_it_opens_the_nights_now_lowest_and_highest(self) -> None:
        html = price_note_html(_down(), shop="Fixture Store One", price="£1,198.00")
        pop = _text(re.search(r'<div class="pw-ph-pop">.*</div>', html, re.S).group(0))
        self.assertIn("Price at Fixture Store One, last 30 nights", pop)
        self.assertIn("Now £1,198.00 · Lowest £1,198.00 · Highest £1,249.00 (14–23 Nov)", pop)
        self.assertIn("As the shop listed it, checked every night.", pop)
        self.assertNotIn("A gap is", pop)
        self.assertIn('<svg class="pw-ph-chart"', html)
        # One step line: three levels, joined (no night missing).
        path = _chart_path(html)
        self.assertEqual(path.count("M"), 1)

    def test_a_rise_is_red(self) -> None:
        note = PriceNote(
            kind=UP, night=NIGHT, currency="GBP", change_pence=600, since=date(2026, 12, 9),
            runs=(PriceRun(date(2026, 11, 14), date(2026, 12, 8), 25, 11999, "GBP"),
                  PriceRun(date(2026, 12, 9), NIGHT, 5, 12599, "GBP")),
        )
        html = price_note_html(note, shop="Fixture Store Two", price="£125.99")
        self.assertIn('class="pw-ph pw-ph-up"', html)
        self.assertEqual(_text(re.search(r"<summary.*?</summary>", html, re.S).group(0)), "▲ Price up £6 since 9 Dec")
        self.assertIn(".pw-ph-up .pw-ph-chip{color:#b42318;", PRICE_NOTE_STYLES)
        self.assertIn("Lowest £119.99 (14 Nov – 8 Dec) · Highest £125.99", _text(html))

    def test_the_same_price_is_grey_and_says_for_how_many_nights(self) -> None:
        note = PriceNote(kind=SAME, night=NIGHT, currency="GBP", nights=12,
                         runs=(PriceRun(date(2026, 12, 2), NIGHT, 12, 0, "GBP"),))
        html = price_note_html(note, shop="Fixture Store One", price="£54.99")
        self.assertIn('class="pw-ph pw-ph-same"', html)
        self.assertEqual(_text(re.search(r"<summary.*?</summary>", html, re.S).group(0)), "= Same price for 12 nights")
        self.assertIn("£54.99 on each of the last 12 nights it was listed.", _text(html))
        self.assertIn("Price at Fixture Store One, last 12 nights", _text(html))

    def test_a_gap_is_said_and_breaks_the_line(self) -> None:
        note = PriceNote(
            kind=DOWN, night=NIGHT, currency="GBP", change_pence=1000, since=date(2026, 12, 10),
            runs=(PriceRun(date(2026, 11, 30), date(2026, 12, 6), 7, 10000, "GBP"),
                  PriceRun(date(2026, 12, 10), NIGHT, 4, 9000, "GBP")),
        )
        html = price_note_html(note, shop="", price="£90.00")
        self.assertIn("A gap is a night the shop did not list it.", _text(html))
        self.assertIn("Price at the shop, last 14 nights", _text(html))
        self.assertEqual(_chart_path(html).count("M"), 2)

    def test_no_note_is_nothing_or_the_line_kept(self) -> None:
        self.assertEqual(price_note_html(None, shop="x", price="£1"), "")
        self.assertEqual(
            price_note_html(None, shop="x", price="£1", slot=True),
            '<div class="pw-ph pw-ph-empty" aria-hidden="true"></div>',
        )
        # The kept line is a wide screen's only: a phone shows a card a row.
        self.assertIn("@media (max-width:699px){", PRICE_NOTE_STYLES)
        self.assertIn(".pw-ph-empty{display:none;}", PRICE_NOTE_STYLES.split("@media (max-width:699px){", 1)[1])

    def test_words_from_the_feed_are_escaped(self) -> None:
        html = price_note_html(_down(), shop='Shop <b>"One"</b>', price="£1,198.00")
        self.assertNotIn("<b>\"One\"</b>", html)
        self.assertIn("Shop &lt;b&gt;&quot;One&quot;&lt;/b&gt;", html)


class CardsTests(design._FeedMixin, unittest.TestCase):
    """An answer's cards, the notes looked up as the site does."""

    def _page(self, notes: PriceNotes | None) -> list[str]:
        self._serve(design._kettles())
        with mock.patch.object(reference, "_price_notes", return_value=notes):
            self.page = design._call("/search", {"q": "kettle"})
        return design._cards(self.page)

    def test_every_card_is_looked_up_by_its_shop_and_id(self) -> None:
        from datetime import datetime, timezone

        notes = PriceNotes(
            datetime(2026, 12, 13, 4, 20, tzinfo=timezone.utc), NIGHT,
            {"Fixture Store Two\x1fk1": 9, "Fixture Store One\x1fk3": ["d", 250, 2, "GBP", [[20, 3, 2150], [2, 0, 1900]]]},
        )
        cards = self._page(notes)
        by_id = {re.search(r'data-choice-id="([^"]+)"', card).group(1): card for card in cards}
        self.assertIn("Same price", _text(by_id["k1"]))
        self.assertIn("▼ Price down £2.50 since 11 Dec", _text(by_id["k3"]))
        # Not the Recommended's alone: the others keep the chip's line.
        for pid, card in by_id.items():
            if pid not in ("k1", "k3"):
                self.assertIn('<div class="pw-ph pw-ph-empty" aria-hidden="true"></div>', card)
        self.assertIn(".pw-ph-chip{", self.page)

    def test_with_no_note_nothing_is_added(self) -> None:
        for card in self._page(None):
            self.assertNotIn("pw-ph", card)
        empty = PriceNotes(design_now(), NIGHT, {})
        for card in self._page(empty):
            self.assertNotIn("pw-ph", card)

    def test_the_home_page_has_no_price_note_styles(self) -> None:
        self.assertNotIn(".pw-ph-chip{", design._call("/"))


class SamePreparationTests(unittest.TestCase):
    def test_the_cards_ask_for_the_notes_of_the_catalogue_they_read(self) -> None:
        stamp = design_now()
        with mock.patch("picwise_providers.state.loaded_prepared_at", return_value=stamp), mock.patch(
            "picwise_providers.price_history.notes_for_catalogue", return_value="notes"
        ) as asked:
            self.assertEqual(reference._price_notes(), "notes")
        asked.assert_called_once_with(stamp)


def design_now():
    from datetime import datetime, timezone

    return datetime(2026, 12, 13, 4, 20, tzinfo=timezone.utc)


if __name__ == "__main__":
    unittest.main()
