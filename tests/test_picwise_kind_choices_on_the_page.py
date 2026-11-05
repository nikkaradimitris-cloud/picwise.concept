"""A search naming only a general kind asks which one is meant, above its results.

Owner, 2026-10-28: «Το search όταν του βάζεις καλώδιο πρέπει να συμπληρώνει προτάσεις τι
καλώδιο ζητάει: καλώδιο τηλεόρασης, καλώδιο φόρτισης, καλώδιο ίντερνετ ... το ίδιο με όλες
αυτές τις γενικές λέξεις»; 2026-10-29: one logic for all of them, «Ναι προχώρα, βάλ' το στο
search», after the measure on the server's catalogue (runs 40868599997, 40869626869).

Pinned here, through the deployed entry point (`api/index.py`) on a feed file: the page
for "cable" (and «καλώδιο») shows its cheapest cables and above them "What kind of
cable?" with the searches that narrow it, the largest first, each a link to its search,
which finds those cables, and the vocabulary's older "This search is too broad" does not
ask too; "chair", a word with many of the vocabulary's suggestions, shows the feed's
chairs and asks the same way, where it once showed only that list and no product, which
stays for a broad word the feed has nothing for ("jacket" here); "shorts", which the
index sets near "short", shows its shorts too and for a word read as a
kind only by correcting it ("chain", read as chair); a search that already narrows
("hdmi cable") asks nothing,
and nor does one for a kind with one group only; the box's list offers the choices, so
typing "cable" lists them after it; the prepared feed carries the choices, read back as
written. Every row is local test data: fictional brands, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.kind_choices import KindChoice  # noqa: E402
from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure, write_prepared_catalogue  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache, prepare_feed_catalogue  # noqa: E402

CABLES = "Electronics > Electronics Accessories > Cables"
KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"
DINING_CHAIRS = "Furniture > Chairs > Kitchen & Dining Room Chairs"
OFFICE_CHAIRS = "Furniture > Office Furniture > Office Chairs"
SHORTS = "Apparel & Accessories > Clothing > Shorts"
HEADER = [
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock",
    "merchant_name", "description", "data_provenance",
]


def _rows() -> list[list[str]]:
    rows = []
    number = 0
    for title, category, count, base in (
        ("Fixturon HDMI Cable {n}m", CABLES, 30, 3.0),
        ("Fixturon Coaxial Cable {n}m", CABLES, 25, 2.0),
        ("Fixturon Speaker Cable {n}m", CABLES, 22, 4.0),
        ("Fixturon Electric Kettle {n}", KETTLES, 55, 20.0),
        ("Fixturon Velvet Dining Chair {n}", DINING_CHAIRS, 10, 40.0),
        ("Fixturon Oak Dining Chair {n}", DINING_CHAIRS, 10, 50.0),
        ("Fixturon Grey Dining Chair {n}", DINING_CHAIRS, 10, 60.0),
        ("Fixturon Ergonomic Office Chair {n}", OFFICE_CHAIRS, 25, 70.0),
        ("Fixturon Beach Shorts {n}", SHORTS, 30, 12.0),
        ("Fixturon Cargo Shorts {n}", SHORTS, 25, 16.0),
    ):
        for step in range(count):
            number += 1
            rows.append(
                [f"p{number}", title.format(n=step + 1), "Fixturon", "", category,
                 f"https://fixture.example.invalid/out/p{number}",
                 f"https://fixture.example.invalid/img/p{number}.jpg", f"{base + step:.2f}", "GBP", "1",
                 "Fixture Store One" if number % 2 else "Fixture Store Two", fixture_description(),
                 "local_test_fixture"]
            )
    return rows


class KindChoicesOnThePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="")
        with handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER)
            writer.writerows(_rows())
        cls.feed = handle.name
        cls.previous = {key: os.environ.pop(key, None) for key in ("AWIN_FEED_FILE", "AWIN_FEED_URL")}
        os.environ["AWIN_FEED_FILE"] = cls.feed
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.pop("AWIN_FEED_FILE", None)
        for key, value in cls.previous.items():
            if value is not None:
                os.environ[key] = value
        os.unlink(cls.feed)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def _get(self, path: str, query: str = "") -> str:
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": path,
                    "QUERY_STRING": query,
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        )
        self.assertEqual(captured["status"], "200 OK")
        return body.decode("utf-8")

    def test_a_general_kind_asks_which_one_above_its_results(self) -> None:
        page = self._get("/search", "q=cable")
        self.assertIn('<nav class="pw-kind-choices" aria-label="What kind of cable?">', page)
        self.assertIn('<span class="pw-kind-choices-ask">What kind of cable?</span>', page)
        start = page.index('<nav class="pw-kind-choices"')
        choices = page[start:page.index("</nav>", start)]
        # The largest first, each a link to the search that narrows it.
        self.assertLess(choices.index("hdmi cable"), choices.index("coaxial cable"))
        self.assertLess(choices.index("coaxial cable"), choices.index("speaker cable"))
        self.assertIn('href="/search?q=hdmi%20cable"', choices)
        # Above the results: the question comes before the first card.
        self.assertLess(start, page.index('<section class="pw-grid"'))
        # The cheapest cables are still the answer.
        self.assertIn("Fixturon Coaxial Cable 1m", page)
        # One question: the vocabulary's older list ("usb cable", "lightning cable",
        # which this catalogue does not have) does not ask too.
        self.assertNotIn("This search is too broad", page)
        self.assertNotIn("lightning cable", page)

    def test_a_word_of_many_suggestions_shows_its_kind_and_asks(self) -> None:
        # "chair" has five of the vocabulary's suggestions ("baby feeding chair", "shower
        # chair" ...): once shown alone, with no product, as "This search is too broad".
        page = self._get("/search", "q=chair")
        self.assertIn("Fixturon Velvet Dining Chair 1", page)
        self.assertIn('<span class="pw-kind-choices-ask">What kind of chair?</span>', page)
        start = page.index('<nav class="pw-kind-choices"')
        choices = page[start:page.index("</nav>", start)]
        self.assertIn('href="/search?q=dining%20chair"', choices)
        self.assertIn('href="/search?q=office%20chair"', choices)
        self.assertNotIn("This search is too broad", page)
        self.assertNotIn("shower chair", page)

    def test_a_word_the_index_sets_near_another_shows_its_kind(self) -> None:
        # The index sets "shorts" near "short"; it is the kind's own name, exactly.
        page = self._get("/search", "q=shorts")
        self.assertIn("Fixturon Beach Shorts 1", page)
        self.assertNotIn("This search is too broad", page)

    def test_a_broad_word_with_nothing_to_show_keeps_the_older_list(self) -> None:
        page = self._get("/search", "q=jacket")
        self.assertIn("This search is too broad. Try:", page)
        self.assertNotIn('<nav class="pw-kind-choices"', page)

    def test_a_word_read_as_a_kind_only_by_correcting_it_shows_none_of_it(self) -> None:
        # "chain" reads as "chair" only as a misspelling: no chair is its answer.
        page = self._get("/search", "q=chain")
        self.assertNotIn("Fixturon Velvet Dining Chair", page)
        self.assertNotIn('<nav class="pw-kind-choices"', page)

    def test_the_greek_word_asks_the_same(self) -> None:
        page = self._get("/search", "q=%CE%BA%CE%B1%CE%BB%CF%8E%CE%B4%CE%B9%CE%BF")
        self.assertIn("What kind of cable?", page)

    def test_each_choice_finds_what_it_names(self) -> None:
        page = self._get("/search", "q=hdmi+cable")
        self.assertIn("Fixturon HDMI Cable 1m", page)
        self.assertNotIn("Fixturon Coaxial Cable", page)
        # A search that already says which asks nothing.
        self.assertNotIn('<nav class="pw-kind-choices"', page)

    def test_a_kind_of_one_group_asks_nothing(self) -> None:
        page = self._get("/search", "q=kettle")
        self.assertIn("Fixturon Electric Kettle 1", page)
        self.assertNotIn('<nav class="pw-kind-choices"', page)

    def test_the_box_offers_the_choices(self) -> None:
        suggestions = json.loads(self._get("/suggest.json"))["suggestions"]
        for text in ("hdmi cable", "coaxial cable", "speaker cable"):
            self.assertIn(text, suggestions)
        # Typing "cable" lists, after the names starting with it, those it ends.
        self.assertIn("cable", suggestions)
        self.assertEqual(len(suggestions), len(set(suggestions)))

    def test_the_prepared_feed_carries_the_choices(self) -> None:
        prepared = prepare_feed_catalogue(now=datetime(2026, 10, 29, 4, 21, tzinfo=timezone.utc))
        self.assertIsNotNone(prepared)
        self.assertEqual(
            prepared.choices["cable"],
            (KindChoice("hdmi cable", 30), KindChoice("coaxial cable", 25), KindChoice("speaker cable", 22)),
        )
        self.assertNotIn("kettle", prepared.choices)
        self.assertIn("hdmi cable", [suggestion.text for suggestion in prepared.suggestions])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            write_prepared_catalogue(prepared, path)
            read = read_prepared_catalogue_to_measure(path)
        self.assertEqual(read.choices, prepared.choices)


if __name__ == "__main__":
    unittest.main()
