"""The AI layer on the search page, end to end through the deployed entry point
(`docs/PICWISE_AI_LAYER_SPEC.md`, 4.4 and 4.5; the Decision Contract, "The products that
fit a complex search first"), with the service's answers written by hand: no test calls
the API.

Owner, 2026-11-06: «...τα προϊόντα που υποδεικνύει πρέπει να έχουν λεκτική αναφορά αλλά
και οπτική σημείωση καθώς πρέπει να κατατάσσονται και πρώτα», then «Ναι, συμφωνώ με όλα,
προχώρα» to the order, the time and the mark. Pinned here:

- a complex search with no answer stored: the page as before, an empty place with its key
  and the script, and one draft written, never twice, never by the script's own reading;
  the draft becomes a job for the service only when the script asks, so a visitor whose
  browser runs no script, as most bots, costs nothing;
- with a shown answer: the products that fit first, each with a ✓ and its own words (an
  empty line on the others), the Recommended among them, "Mid-priced of those that fit",
  the sentence and "Checked against the shops' own words", the page saying the order;
- with the shops' words: the script told to read again once the catalogue has counted
  them, then the words as searches with their counts;
- the script's own question (`/assist-status`) and a key from a URL naming no other file;
- a search that is not complex, or a server without the layer, draws the page as before.

Every product is fictional; the feed rows are served as the price-first tests serve them.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_ai import store  # noqa: E402
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402
from picwise_surface.assist import ASSIST_NOTE, ASSIST_SCRIPT  # noqa: E402
from test_picwise_price_first import _PageMixin  # noqa: E402

PRICES = [20, 30, 40, 50, 60, 70, 80, 90, 100]
SEARCH = "quiet kettle"


def _get(path: str, params: dict[str, str]) -> tuple[str, dict[str, str], str]:
    seen: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        seen["status"], seen["headers"] = status, dict(headers)

    body = b"".join(
        wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": path, "QUERY_STRING": urlencode(params),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            start_response,
        )
    ).decode("utf-8")
    return str(seen["status"]), dict(seen["headers"]), body


class _AssistMixin(_PageMixin):
    def setUp(self) -> None:
        self._serve(self._kettles(PRICES))
        self.directory = Path(tempfile.mkdtemp())
        # The deployment makes `jobs/` only when the service has its key.
        (self.directory / "jobs").mkdir()
        previous = os.environ.get(store.ASSIST_DIR_ENV)
        os.environ[store.ASSIST_DIR_ENV] = str(self.directory)
        self.addCleanup(
            lambda: os.environ.__setitem__(store.ASSIST_DIR_ENV, previous)
            if previous is not None else os.environ.pop(store.ASSIST_DIR_ENV, None)
        )

    def _key(self, search: str = SEARCH) -> str:
        signature = resolve_live_search(search).provider_feed_candidates_signature
        return store.job_key(search, signature)

    def _jobs(self) -> list[Path]:
        return sorted((self.directory / "jobs").glob("*.json")) if (self.directory / "jobs").is_dir() else []

    def _drafts(self) -> list[Path]:
        return sorted((self.directory / "drafts").glob("*.json")) if (self.directory / "drafts").is_dir() else []

    def _search_page(self, search: str = SEARCH, **params: str) -> str:
        return _get("/search", {"q": search, **params})[2]

    @staticmethod
    def _fits(page: str) -> list[str]:
        return [
            html.unescape(match) for match in re.findall(r'<p class="pw-card-fit">(.*?)</p>', page, flags=re.S)
        ]


class WaitingForTheAnswerTests(_AssistMixin, unittest.TestCase):
    def test_a_draft_once_an_empty_place_and_a_job_only_when_the_script_asks(self) -> None:
        key = self._key()
        page = self._search_page()
        self.assertIn("PicWise could not match: quiet", page)
        self.assertEqual([card["id"] for card in self._cards(page)], ["k5", "k1", "k2", "k3"])
        self.assertIn(f'<section class="pw-assist" id="pw-assist" data-assist-key="{key}" hidden></section>', page)
        self.assertIn(ASSIST_SCRIPT, page)
        self.assertIn('<div class="pw-results" id="pw-results">', page)
        self.assertNotIn('class="pw-card-fit"', page)
        # A visitor whose browser runs no script leaves a draft, and asks nothing.
        drafts = self._drafts()
        self.assertEqual([path.stem for path in drafts], [key])
        self.assertEqual(self._jobs(), [])
        first = drafts[0].read_text(encoding="utf-8")
        self._search_page()
        self.assertEqual(drafts[0].read_text(encoding="utf-8"), first)
        self.assertNotIn("http", first)
        # The page's script asks: the draft becomes the service's job.
        self.assertEqual(json.loads(_get("/assist-status", {"k": key})[2]), {"state": "pending"})
        self.assertEqual(self._drafts(), [])
        jobs = self._jobs()
        self.assertEqual([path.stem for path in jobs], [key])
        _key, signature, _written, job = store.read_job(jobs[0])
        self.assertEqual((job.search, job.words, job.kind_name, job.total), (SEARCH, ("quiet",), "kettle", 9))
        self.assertEqual([candidate.product_id for candidate in job.candidates],
                         ["k5", "k1", "k2", "k3", "k4", "k6", "k7", "k8", "k9"])
        self.assertTrue(all(candidate.description for candidate in job.candidates))
        self.assertEqual(json.loads(_get("/assist-status", {"k": key})[2]), {"state": "pending"})
        # While the job waits, no draft; read again by the script, nothing written at all.
        self._search_page()
        self.assertEqual(self._drafts(), [])
        jobs[0].unlink()
        self._search_page(assist="1")
        self.assertEqual((self._jobs(), self._drafts()), ([], []))
        # "More" holds what it held before.
        self.assertEqual(len(self._cards(self._search_page(shown="8"))), 8)

    def test_the_scripts_question(self) -> None:
        key = self._key()
        status, headers, body = _get("/assist-status", {"k": key})
        self.assertEqual((status, json.loads(body)), ("200 OK", {"state": "none"}))
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertIn("noindex", " ".join(headers.values()))
        self._search_page()
        self.assertEqual(json.loads(_get("/assist-status", {"k": key})[2]), {"state": "pending"})
        self.assertTrue(store.job_pending(self.directory, key))
        store.write_result(self.directory, key, {"status": "withheld"})
        self.assertEqual(json.loads(_get("/assist-status", {"k": key})[2]), {"state": "none"})
        for bad in ("../results/" + key, "x" * 32, ""):
            self.assertEqual(json.loads(_get("/assist-status", {"k": bad})[2]), {"state": "none"})


class ShownAnswerTests(_AssistMixin, unittest.TestCase):
    SENTENCE = "3 of these 9 kettles say they are quiet, from 30.00 GBP."

    def setUp(self) -> None:
        super().setUp()
        self.key = self._key()
        store.write_result(self.directory, self.key, {
            "status": "shown",
            "sentence": self.SENTENCE,
            "kind_name": "kettle",
            "fitting": [{"product_id": "k2", "words": "Quiet Boil"}, {"product_id": "k7", "words": "Whisper-quiet 45 dB"},
                        {"product_id": "k9", "words": "Low noise"}],
        })

    def test_the_fitting_first_marked_with_their_own_recommended(self) -> None:
        page = self._search_page()
        cards = self._cards(page)
        self.assertEqual([card["id"] for card in cards], ["k7", "k2", "k9", "k1"])
        self.assertTrue(cards[0]["recommended"])
        self.assertEqual(cards[0]["role"], "Mid-priced of those that fit")
        self.assertEqual(self._fits(page)[:3], [
            '<span class="pw-fit-mark" aria-hidden="true">✓</span> <span class="pw-fit-words">“Whisper-quiet 45 dB”</span>',
            '<span class="pw-fit-mark" aria-hidden="true">✓</span> <span class="pw-fit-words">“Quiet Boil”</span>',
            '<span class="pw-fit-mark" aria-hidden="true">✓</span> <span class="pw-fit-words">“Low noise”</span>',
        ])
        self.assertEqual(self._fits(page)[3], "")
        self.assertIn(html.escape(self.SENTENCE), page)
        self.assertIn(f'<p class="pw-assist-note">{html.escape(ASSIST_NOTE)}</p>', page)
        self.assertNotIn("AI", re.search(r'<section class="pw-assist".*?</section>', page, flags=re.S).group(0))
        self.assertIn("Results for: quiet kettle, those that fit first, then cheapest first", page)
        # The order is said by the heading alone (owner, 2026-11-12, «Β»).
        self.assertNotIn("Products whose own words show they fit your search come first", page)
        self.assertIn("The Recommended is mid-priced of those that fit.", page)
        self.assertNotIn("data-assist-key", page)
        self.assertNotIn(ASSIST_SCRIPT, page)
        self.assertEqual(self._jobs(), [])
        self.assertEqual(json.loads(_get("/assist-status", {"k": self.key})[2]), {"state": "ready"})
        # "More" goes on in that order, and the script's reading is the same page.
        self.assertEqual([card["id"] for card in self._cards(self._search_page(shown="8"))],
                         ["k7", "k2", "k9", "k1", "k3", "k4", "k5", "k6"])
        self.assertEqual(self._cards(self._search_page(assist="1")), cards)

    def test_an_answer_for_other_products_or_too_old_changes_nothing(self) -> None:
        self._serve(self._kettles(PRICES[:-1] + [101]))
        page = self._search_page()
        self.assertEqual([card["id"] for card in self._cards(page)], ["k5", "k1", "k2", "k3"])
        self.assertNotIn(html.escape(self.SENTENCE), page)
        self.assertIn("data-assist-key", page)


class ShopWordsTests(_AssistMixin, unittest.TestCase):
    def test_the_shops_words_counted_once_then_offered_as_searches(self) -> None:
        key = self._key()
        store.write_result(self.directory, key, {"status": "buttons", "kind_name": "kettle",
                                                 "shop_words": ["1.7L", "Steamless"]})
        page = self._search_page()
        self.assertIn(f'data-assist-key="{key}"', page)
        self.assertEqual(json.loads(_get("/assist-status", {"k": key})[2]), {"state": "ready"})
        self.assertEqual(store.read_served(self.directory, key),
                         [{"word": "1.7L", "search": "1.7L kettle", "count": 9}])
        page = self._search_page()
        self.assertIn('<a class="pw-assist-word" href="/search?q=1.7L%20kettle">1.7L '
                      '<span class="pw-assist-count">(9)</span></a>', page)
        self.assertEqual([card["id"] for card in self._cards(page)], ["k5", "k1", "k2", "k3"])
        self.assertNotIn("Steamless", page)


class AsBeforeTests(_AssistMixin, unittest.TestCase):
    def test_a_search_that_is_not_complex_is_drawn_as_before(self) -> None:
        with_layer = self._search_page("kettle")
        os.environ.pop(store.ASSIST_DIR_ENV)
        self.assertEqual(self._search_page("kettle"), with_layer)
        self.assertEqual((self._jobs(), self._drafts()), ([], []))

    def test_a_server_without_the_layer_writes_no_job(self) -> None:
        os.environ.pop(store.ASSIST_DIR_ENV)
        page = self._search_page()
        self.assertNotIn("pw-assist", page)
        self.assertNotIn('id="pw-results"', page)
        self.assertEqual(self._jobs(), [])
        self.assertEqual(json.loads(_get("/assist-status", {"k": "a" * 32})[2]), {"state": "none"})

    def test_a_server_whose_service_has_no_key_writes_no_job(self) -> None:
        # The deployment leaves `jobs/` out when GitHub holds no key.
        (self.directory / "jobs").rmdir()
        page = self._search_page()
        self.assertNotIn("pw-assist", page)
        self.assertFalse((self.directory / "jobs").exists())
        self.assertEqual(self._drafts(), [])


if __name__ == "__main__":
    unittest.main()
