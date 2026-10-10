"""Refurbished and used products appear only when the buyer asks for them.

Owner decision, 2026-10-10, recorded in `docs/PICWISE_DECISION_CONTRACT.md`:

- a product the feed calls not new is not a candidate at all for an ordinary query:
  not shown, not counted as a match, never the recommendation
- a buyer who asks ("μεταχειρισμένο", "metaxirismeno", "refurbished", "used",
  "second hand") gets those first; where the feed has fewer than four, the remaining
  slots fill with new products and the page says how many of the four are the
  condition asked for. None in the feed: the word is reported as unmatched, as any
  other filter the inventory cannot answer
- the recommended choice comes from the condition asked for whenever the four are
  mixed, and its card says that is what separated it

Everything runs end to end through `api/index.py`, the entrypoint Vercel serves, on
local fixture rows: fictional brands, `.invalid` URLs, `data_provenance=local_test_fixture`.
"""
from __future__ import annotations

import csv
import html
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
from picwise_nlu.concept_understanding import (  # noqa: E402
    read_condition_request,
    understand_product_query,
)
from picwise_nlu.product_concepts import get_product_concepts  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.product_condition import (  # noqa: E402
    _GREEK_NON_NEW_STEMS,
    _NON_NEW_TEXT_PHRASES,
    non_new_condition,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "product_type",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "stock_status",
    "merchant_name", "condition", "data_provenance",
)


def _row(pid: str, name: str, price: str, **fields: str) -> dict[str, str]:
    row = {
        "aw_product_id": pid,
        "product_name": name,
        "brand_name": name.split()[0],
        "merchant_category": "Kettles",
        "product_type": "Kettles",
        "aw_deep_link": f"https://fixture.example.invalid/out/{pid}",
        "aw_image_url": f"https://fixture.example.invalid/img/{pid}.jpg",
        "search_price": price,
        "currency": "GBP",
        "in_stock": "1",
        "stock_status": "in stock",
        "merchant_name": "Fixture Store One",
        "condition": "new",
        "data_provenance": "local_test_fixture",
    }
    row.update(fields)
    return row


def _new_kettles(count: int, *, start: int = 1, first_price: int = 14) -> list[dict[str, str]]:
    names = ("Boil", "Steam", "Mini", "Glass", "Quiet", "Travel", "Rapid")
    return [
        _row(
            f"n{index}",
            f"Testline {names[(index - 1) % len(names)]} Kettle 1.{index}L",
            f"{first_price + 5 * (index - start)}.00",
        )
        for index in range(start, start + count)
    ]


class ConditionRequestReadingTests(unittest.TestCase):
    """What the buyer typed, read before anything touches the feed."""

    def test_the_words_are_read_in_greek_greeklish_and_english(self) -> None:
        for query, expected in (
            ("μεταχειρισμένο ψυγείο", "μεταχειρισμενο"),
            ("ανακατασκευασμενο laptop", "ανακατασκευασμενο"),
            ("ανακαινισμένη τηλεόραση", "ανακαινισμενη"),
            ("metaxirismeno psigio", "metaxirismeno"),
            ("refurbished laptop", "refurbished"),
            ("kettle refurb", "refurb"),
            ("used kettle", "used"),
            ("second hand kettle", "second hand"),
            ("pre-owned laptop", "pre owned"),
        ):
            with self.subTest(query=query):
                self.assertEqual(read_condition_request(query).words, (expected,))

    def test_an_ordinary_query_asks_for_nothing(self) -> None:
        for query in ("βραστηρας", "laptop 16gb", "πλυντηριο 8 κιλα", "coffee machine"):
            with self.subTest(query=query):
                self.assertEqual(read_condition_request(query).words, ())

    def test_no_product_name_is_mistaken_for_a_condition_request(self) -> None:
        # The words are corrected for typing mistakes like every other word, so a
        # product name must never be absorbed by one: that would hide the whole feed
        # behind a condition nobody asked for.
        mistaken = [
            (concept.concept_id, form)
            for concept in get_product_concepts()
            for form in concept.english + concept.greek
            if read_condition_request(form).words
        ]
        self.assertEqual(mistaken, [])

    def test_the_word_is_not_a_filter_on_feed_text(self) -> None:
        # It names a condition the feed states in its own column. Matched against feed
        # text it would reject every correct product, or match a merchant's copy.
        reading = understand_product_query("μεταχειρισμένο ψυγείο")
        self.assertEqual(reading.concept_id, "refrigerator")
        self.assertEqual(reading.condition_request, ("μεταχειρισμενο",))
        self.assertEqual(reading.filters, ())
        self.assertNotIn("μεταχειρισμενο", reading.filters)


class FeedConditionReadingTests(unittest.TestCase):
    """What the feed said, read the one way both the gate and the cards read it."""

    def test_a_stated_condition_other_than_new_is_non_new(self) -> None:
        for value in ("refurbished", "Refurbished", "used", "Pre-Owned", "open box",
                      "like new", "grade b", "usato", "μεταχειρισμένο"):
            with self.subTest(value=value):
                self.assertEqual(non_new_condition(condition=value), value)

    def test_new_values_are_new(self) -> None:
        for value in ("new", "New", "Brand New", "new with tags", "NEW_WITH_BOX"):
            with self.subTest(value=value):
                self.assertEqual(non_new_condition(condition=value), "")

    def test_a_column_that_states_nothing_hides_no_product(self) -> None:
        # An unpopulated condition column must not empty a feed: PicWise does not know
        # these items are used, so it does not treat them as used.
        for value in ("", "n/a", "N/A", "-", "--", "unknown", "not specified", "0", "1"):
            with self.subTest(value=value):
                self.assertEqual(non_new_condition(condition=value), "")

    def test_the_product_text_is_read_when_the_column_is_silent(self) -> None:
        for text, expected in (
            ("Fixturon Refurbished Aero Kettle", "Refurbished"),
            ("Open Box Testline Kettle", "Open Box"),
            ("Sampleworks Kettle (reconditioned)", "reconditioned"),
            ("Βραστήρας μεταχειρισμένος", "μεταχειρισμένος"),
            ("Ψυγείο ανακατασκευασμένο (Grade A)", "ανακατασκευασμένο"),
        ):
            with self.subTest(text=text):
                self.assertEqual(non_new_condition(text=text), expected)

    def test_marketing_copy_words_do_not_make_a_product_used(self) -> None:
        # Free text uses "used" and "renewed" for other things; a condition column
        # does not. Only the column is trusted with those two.
        for text in (
            "Fixturon Kettle used by professionals",
            "Testline Kettle with renewed formula",
            "Sampleworks New Kettle",
        ):
            with self.subTest(text=text):
                self.assertEqual(non_new_condition(text=text), "")
        self.assertEqual(non_new_condition(condition="used", text="Fixturon Kettle"), "used")

    def test_every_word_of_the_vocabulary_survives_the_cheap_pre_filter(self) -> None:
        # The text scan is guarded by a substring pre-filter for speed. A word added to
        # the vocabulary without its hint would stop being read at all, and a used
        # product would reach a buyer who did not ask for one.
        for phrase in _NON_NEW_TEXT_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    non_new_condition(text=f"Fixturon {phrase} Aero Kettle 1.7L").lower(),
                    phrase,
                )
        for stem in _GREEK_NON_NEW_STEMS:
            for word in (f"{stem}ο", f"{stem[:-3]}μένο"):
                with self.subTest(word=word):
                    self.assertEqual(non_new_condition(text=f"Βραστήρας {word}"), word)

    def test_the_column_wins_over_the_product_text(self) -> None:
        self.assertEqual(
            non_new_condition(condition="new", text="Fixturon Refurbished Kettle"), ""
        )


class DeployedSurfaceConditionTests(unittest.TestCase):
    """End to end through api/index.py, the entrypoint Vercel serves."""

    def _serve(self, rows: list[dict[str, str]]) -> None:
        directory = tempfile.mkdtemp()
        path = Path(directory) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
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

    def _page(self, query: str) -> str:
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status

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
        )
        self.assertEqual(captured["status"], "200 OK")
        return body.decode("utf-8")

    def _cards(self, query: str) -> list[dict[str, object]]:
        body = self._page(query)
        cards: list[dict[str, object]] = []
        for match in re.finditer(
            r'<article class="pw-card([^"]*)" data-choice-id="([^"]+)">(.*?)</article>', body, re.S
        ):
            classes, choice_id, inner = match.groups()
            text = html.unescape(re.sub(r"<[^>]+>", " ", inner))
            cards.append(
                {
                    "choice_id": choice_id,
                    "recommended": "recommended" in classes,
                    "text": " ".join(text.split()),
                }
            )
        return cards

    def _text(self, query: str) -> str:
        return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", self._page(query))).split())

    def _shown(self, query: str) -> list[str]:
        return [str(card["choice_id"]) for card in self._cards(query)]

    def test_a_refurbished_product_is_not_one_of_the_four_by_default(self) -> None:
        # It is also the cheapest, which is what used to carry it into the four and
        # make it the recommendation.
        self._serve(
            [
                _row("r1", "Fixturon Aero Kettle 1.7L", "9.00", condition="refurbished"),
                _row("u1", "Fixturon Mini Kettle 0.8L", "11.00", condition="used"),
                *_new_kettles(4),
            ]
        )
        shown = self._shown("kettle")
        self.assertEqual(len(shown), 4)
        self.assertNotIn("r1", shown)
        self.assertNotIn("u1", shown)
        self.assertEqual(sorted(shown), ["n1", "n2", "n3", "n4"])

    def test_a_non_new_product_is_not_counted_as_one_of_the_four_either(self) -> None:
        # Three new kettles and two non-new ones are not five choices: PicWise owes
        # four it may actually show, so it shows none and says so.
        self._serve(
            [
                _row("r1", "Fixturon Aero Kettle 1.7L", "9.00", condition="refurbished"),
                _row("u1", "Fixturon Mini Kettle 0.8L", "11.00", condition="Used"),
                *_new_kettles(3),
            ]
        )
        self.assertEqual(self._cards("kettle"), [])

    def test_the_four_are_the_condition_asked_for_when_the_feed_has_four(self) -> None:
        self._serve(
            [
                _row("r1", "Fixturon Aero Kettle 1.7L", "9.00", condition="refurbished"),
                _row("r2", "Fixturon Mini Kettle 0.8L", "19.00", condition="refurbished"),
                _row("r3", "Sampleworks Steam Kettle 1.7L", "29.00", condition="used"),
                _row("r4", "Sampleworks Quiet Kettle 1.5L", "39.00", condition="Pre-Owned"),
                *_new_kettles(4),
            ]
        )
        for query in ("refurbished kettle", "μεταχειρισμενος βραστηρας", "metaxirismenos vrastiras"):
            with self.subTest(query=query):
                self.assertEqual(sorted(self._shown(query)), ["r1", "r2", "r3", "r4"])
                self.assertNotIn("Only some of the four match", self._text(query))

    def test_too_few_of_the_condition_asked_for_fill_up_with_new_ones_and_say_so(self) -> None:
        # Owner decision, 2026-10-10: fill the remaining slots rather than leave the
        # buyer with nothing, and state how many of the four are what they asked for.
        self._serve(
            [
                _row("r1", "Fixturon Aero Kettle 1.7L", "9.00", condition="refurbished"),
                _row("r2", "Fixturon Mini Kettle 0.8L", "11.00", condition="used"),
                *_new_kettles(4),
            ]
        )
        cards = self._cards("μεταχειρισμενος βραστηρας")
        shown = [str(card["choice_id"]) for card in cards]
        self.assertEqual(len(shown), 4)
        self.assertIn("r1", shown)
        self.assertIn("r2", shown)
        # The ones asked for come first, so the buyer reads the answer to their
        # question before the fill-ins.
        self.assertEqual(shown[:2], ["r1", "r2"])
        page = self._text("μεταχειρισμενος βραστηρας")
        self.assertIn("Only some of the four match: μεταχειρισμενος (2 of 4)", page)
        self.assertNotIn("could not match", page)
        # Every non-new card still admits its condition.
        by_id = {str(card["choice_id"]): str(card["text"]) for card in cards}
        self.assertIn("not new", by_id["r1"])
        self.assertIn("not new", by_id["r2"])
        self.assertNotIn("not new", by_id[shown[2]])

    def test_the_recommendation_comes_from_the_condition_asked_for(self) -> None:
        # The dearest refurbished one against three cheaper new ones: price must not
        # move the recommendation back onto a condition the buyer did not ask for.
        self._serve(
            [
                _row("r1", "Fixturon Aero Kettle 1.7L", "99.00", condition="refurbished"),
                *_new_kettles(4),
            ]
        )
        cards = self._cards("refurbished kettle")
        recommended = [card for card in cards if card["recommended"]]
        self.assertEqual(len(recommended), 1)
        self.assertEqual(recommended[0]["choice_id"], "r1")
        self.assertIn("in the condition you asked for", str(recommended[0]["text"]))
        self.assertIn("Only some of the four match: refurbished (1 of 4)", self._text("refurbished kettle"))

    def test_a_condition_the_feed_cannot_answer_is_reported_unmatched(self) -> None:
        self._serve(_new_kettles(4))
        page = self._text("ανακατασκευασμενος βραστηρας")
        self.assertIn("PicWise could not match: ανακατασκευασμενος", page)
        self.assertEqual(sorted(self._shown("ανακατασκευασμενος βραστηρας")), ["n1", "n2", "n3", "n4"])

    def test_the_condition_is_read_from_the_title_when_the_column_is_silent(self) -> None:
        self._serve(
            [
                _row("t1", "Fixturon Refurbished Aero Kettle 1.7L", "9.00", condition=""),
                *_new_kettles(4),
            ]
        )
        self.assertNotIn("t1", self._shown("kettle"))
        self.assertIn("t1", self._shown("refurbished kettle"))

    def test_an_unreadable_condition_column_hides_nothing(self) -> None:
        self._serve(
            [
                _row("j1", "Testline Boil Kettle 1.5L", "14.00", condition="n/a"),
                _row("j2", "Testline Steam Kettle 1.6L", "19.00", condition="-"),
                _row("j3", "Testline Mini Kettle 1.7L", "24.00", condition="unknown"),
                _row("j4", "Testline Glass Kettle 1.8L", "29.00", condition="1"),
            ]
        )
        self.assertEqual(sorted(self._shown("kettle")), ["j1", "j2", "j3", "j4"])

    def test_the_condition_word_does_not_filter_the_feed_text(self) -> None:
        # "refurbished" appears in no title here. Read as a word to match, it would
        # leave nothing to show; read as a condition, it still answers with four.
        self._serve(
            [
                _row("r1", "Fixturon Aero Kettle 1.7L", "9.00", condition="refurbished"),
                *_new_kettles(4),
            ]
        )
        self.assertEqual(len(self._shown("refurbished kettle")), 4)

    def test_a_query_that_names_no_known_product_honours_the_condition_too(self) -> None:
        # The token path: no concept is understood for "widget", so the gate has to
        # work without a concept reading.
        self._serve(
            [
                _row("w1", "Fixturon Aero Widget Pro", "9.00", condition="refurbished",
                     merchant_category="Widgets", product_type="Widgets"),
                *[
                    _row(f"w{index}", f"Testline Widget Model {index}", f"{10 + index}.00",
                         merchant_category="Widgets", product_type="Widgets")
                    for index in range(2, 6)
                ],
            ]
        )
        self.assertNotIn("w1", self._shown("widget"))
        self.assertIn("w1", self._shown("refurbished widget"))

    def test_one_product_offered_new_and_refurbished_fills_one_slot_only(self) -> None:
        # Same GTIN, two conditions. The four are products, not offers, so the
        # refurbished offer must not take a second slot once it has taken the first.
        self._serve(
            [
                _row("d1", "Fixturon Aero Kettle 1.7L", "9.00", condition="refurbished"),
                _row("d2", "Fixturon Aero Kettle 1.7L", "19.00"),
                *_new_kettles(3, start=2, first_price=24),
            ]
        )
        shown = self._shown("refurbished kettle")
        self.assertEqual(len(shown), 4)
        self.assertIn("d1", shown)
        self.assertNotIn("d2", shown)


if __name__ == "__main__":
    unittest.main()
