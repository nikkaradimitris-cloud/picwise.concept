"""The AI layer for complex searches (`docs/PICWISE_AI_LAYER_SPEC.md`, part (c)).

Owner, 2026-11-05: «συμφωνώ με την αρχιτεκτονική και την εγκατάσταση Haiku», then «ΝΑΙ»
to building it first, measured first on about 150 searches. Pinned here, with the API
faked (no test reaches the network):

- the AI is asked only when a search for a kind is answered with products and the page
  says "PicWise could not match" some of its words; never for the buyer's judgements
  ("best", «φθηνό»), a condition, a search whose kind was not understood, or an answer
  found by its words; a narrower kind that fell back is said to be the broader one;
- it reads at most 30 products, in the page's order, with their prices as the page shows
  them, and never a link;
- the request: Claude Haiku 5.5, effort low, the answer's shape enforced (JSON schema);
- the code's checks withhold a sentence whose counts, prices, numbers or names are not
  the answer's own, that holds a forbidden word, a link, Greek, more than one sentence or
  more than 30 words, or an answer that stopped early or skipped a product;
- when no product fits, no sentence (owner, 2026-11-05: «ΟΤΑΝ ΔΕΝ ΒΡΙΣΚΕΙ ΚΑΤΙ ΝΑ ΜΗΝ ΛΕΕΙ
  ΔΕΝ ΒΡΕΘΗΚΕ», then «ΣΩΣΤΑ»): the shops' words for the need, kept only when they stand
  in a title given and are no brand, judgement or the kind's name, then offered only when
  their own search finds products of a kind, with that count;
- each product's own description read too, cleaned and cut;
- the call's cost from the tokens counted, and any failure an answer with nothing shown;
- the measure (`deployment/server/measure_ai.py`) on a small prepared catalogue, without
  the AI, and its list of searches;
- the SDK is imported nowhere but `picwise_ai.client.make_client`, and the understanding
  (`picwise_nlu`) never imports the AI layer.

Every brand and shop is fictional.
"""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MEASURE = ROOT / "deployment" / "server" / "measure_ai.py"
SEARCHES = ROOT / "deployment" / "server" / "ai_measure_searches.txt"
for path in (HERE, ROOT, ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
# This module reads Greek and greeklish, closed on the site (owner, 2026-11-07: «Ναι σε
# όλα, κλείσε και τα δύο»); the switch is on for its tests (`greek_search_switch`).
from greek_search_switch import setUpModule, tearDownModule  # noqa: E402,F401

from picwise_ai.checks import FORBIDDEN_WORDS, check_answer, shop_words_that_pass  # noqa: E402
from picwise_ai.client import Asked, ask, cost_usd  # noqa: E402
from picwise_ai.complex_search import (  # noqa: E402
    MAX_CANDIDATES,
    clean_description,
    complex_search_of,
    description_of,
    why_not_asked,
)
from picwise_ai.request import EFFORT, MODEL, SCHEMA, SYSTEM_PROMPT, request_kwargs, user_message  # noqa: E402
from picwise_ai.shop_words import button_search, verified_shop_words  # noqa: E402

WASHERS = [
    ("Fixturon WM1045 10kg 1400rpm Washing Machine", "Fixturon", "279.00", "Fictional Appliances"),
    ("Testline Series 6 9kg Quiet Washing Machine", "Testline", "549.00", "Fictional Electricals"),
    ("Fixturon EcoWash 9kg Washing Machine White", "Fixturon", "429.99", "Fictional Appliances"),
]


def _rows(items=WASHERS) -> list[dict]:
    return [
        {
            "provider_product_id": f"row-{number}",
            "title": title,
            "brand": brand,
            "price_text": price,
            "currency": "GBP",
            "merchant_name": shop,
            "product_url": f"https://shop.invalid/p/{number}",
        }
        for number, (title, brand, price, shop) in enumerate(items, start=1)
    ]


def _resolution(concept="washing_machine", unmatched=("quiet",), rows=None, total=None, reasons=()):
    rows = _rows() if rows is None else rows
    return types.SimpleNamespace(
        understood_concept_id=concept,
        understood_concept_name=concept.replace("_", " ") if concept else None,
        provider_feed_unmatched_query_terms=tuple(unmatched),
        provider_feed_selected_products=tuple(rows[:4]),
        provider_feed_more_products=tuple(rows[4:]),
        provider_feed_total_count=len(rows) if total is None else total,
        reason_codes=tuple(reasons),
    )


def _quiet():
    return complex_search_of("quiet washing machine", _resolution())


# The words of each product's own title that show it is quiet, as a `yes` must give them.
PROOF = {1: "1400rpm", 2: "Quiet Washing Machine", 3: "EcoWash"}


def _answer(sentence, verdicts=("unclear", "yes", "unclear"), shop_words=(), words=None):
    words = PROOF if words is None else words
    return {
        "verdicts": [
            {"n": n, "fits": fits, "words": words.get(n, "") if fits == "yes" else ""}
            for n, fits in enumerate(verdicts, start=1)
        ],
        "sentence": sentence,
        "shop_words": list(shop_words),
    }


GOOD = "1 of these 3 washing machines say quiet in their titles, from 549.00 GBP."


class WhenTheAIIsAsked(unittest.TestCase):
    def test_words_no_product_of_the_kind_carries(self) -> None:
        found = _quiet()
        self.assertIsNotNone(found)
        self.assertEqual(found.words, ("quiet",))
        self.assertEqual(found.kind_name, "washing machine")
        self.assertFalse(found.fell_back)
        self.assertEqual(found.total, 3)
        self.assertEqual(why_not_asked("quiet washing machine", _resolution()), "")

    def test_never_the_buyers_judgement_nor_a_condition(self) -> None:
        for search, unmatched in (
            ("best washing machine", ("best",)),
            ("cheap good washing machine", ("cheap", "good")),
            ("φθηνό πλυντήριο", ("φθηνο",)),
            ("refurbished washing machine", ("refurbished",)),
        ):
            with self.subTest(search=search):
                resolution = _resolution(unmatched=unmatched)
                self.assertIsNone(complex_search_of(search, resolution))
                self.assertEqual(why_not_asked(search, resolution), "only judgements or a condition not matched")

    def test_a_judgement_beside_a_need_leaves_the_need(self) -> None:
        found = complex_search_of("best quiet washing machine", _resolution(unmatched=("best", "quiet")))
        self.assertEqual(found.words, ("quiet",))

    def test_not_asked_without_a_kind_products_or_unmatched_words(self) -> None:
        cases = (
            (_resolution(concept=None), "no kind understood"),
            (_resolution(rows=[]), "no products"),
            (_resolution(unmatched=()), "every word matched"),
            (_resolution(reasons=("provider_feed_selection_product_named_by_words",)), "answered by its words"),
        )
        for resolution, why in cases:
            with self.subTest(why=why):
                self.assertIsNone(complex_search_of("quiet washing machine", resolution))
                self.assertEqual(why_not_asked("quiet washing machine", resolution), why)

    def test_a_narrower_kind_answered_with_the_broader_one(self) -> None:
        found = complex_search_of("motorcycle helmet", _resolution(concept="moto_helmet", unmatched=("motorcycle",)))
        self.assertTrue(found.fell_back)
        self.assertEqual(found.kind_name, "helmet")
        self.assertEqual(found.words, ("motorcycle",))

    def test_at_most_thirty_products_in_the_pages_order_with_the_pages_prices(self) -> None:
        many = [(f"Fixturon Model {n} 8kg Washing Machine", "Fixturon", f"{200 + n}.00", "Fictional Appliances")
                for n in range(1, 41)]
        found = complex_search_of("quiet washing machine", _resolution(rows=_rows(many)))
        self.assertEqual(len(found.candidates), MAX_CANDIDATES)
        self.assertEqual([c.number for c in found.candidates], list(range(1, 31)))
        self.assertEqual(found.candidates[0].title, "Fixturon Model 1 8kg Washing Machine")
        self.assertEqual(found.candidates[0].price_text, "201.00 GBP")
        self.assertEqual(found.candidates[0].shop, "Fictional Appliances")


class TheRequest(unittest.TestCase):
    def test_the_model_the_effort_and_the_answers_shape(self) -> None:
        request = request_kwargs(_quiet())
        self.assertEqual(request["model"], "claude-haiku-5-5")
        self.assertEqual(MODEL, "claude-haiku-5-5")
        self.assertEqual(request["output_config"]["effort"], EFFORT)
        self.assertEqual(EFFORT, "low")
        self.assertEqual(request["output_config"]["format"], {"type": "json_schema", "schema": SCHEMA})
        self.assertEqual(SCHEMA["required"], ["verdicts", "sentence", "shop_words"])
        self.assertEqual(SCHEMA["properties"]["verdicts"]["items"]["required"], ["n", "fits", "words"])
        self.assertEqual(request["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertNotIn("temperature", request)

    def test_the_products_with_their_numbers_and_never_a_link(self) -> None:
        text = user_message(_quiet())
        self.assertIn("Search, as typed: quiet washing machine", text)
        self.assertIn("Words PicWise could not check: quiet", text)
        self.assertIn("Kind of product shown: washing machine", text)
        self.assertIn("2. Testline Series 6 9kg Quiet Washing Machine | brand Testline | 549.00 GBP | shop Fictional"
                      " Electricals", text)
        self.assertNotIn("http", text)
        self.assertNotIn("shop.invalid", text)

    def test_a_broader_kind_is_named_as_such(self) -> None:
        found = complex_search_of("motorcycle helmet", _resolution(concept="moto_helmet", unmatched=("motorcycle",)))
        self.assertIn("Kind of product shown: helmet (a broader kind than the one asked for)", user_message(found))

    def test_the_rules_the_third_measure_called_for(self) -> None:
        # The third measure (2026-11-06, run 42192705450), read by hand: a manual razor
        # counted among electric shavers, "suitable for all skin types" as for dry skin,
        # backpacks "1 - 2 Years" as for school although their age was stated, and
        # sentences such as "14 of these 30 boots say Winter Snow Boots". The request
        # states each rule plainly.
        prompt = " ".join(SYSTEM_PROMPT.split())
        self.assertIn("A product that is not the kind shown at all is \"no\", whatever it says", prompt)
        self.assertIn("is \"no\", whatever its description says (\"Kids Backpack - 1 - 2 Years\" is not \"for"
                      " school\", even when its description speaks of school)", prompt)
        self.assertIn("(\"suitable for all skin types\", \"for all ages\") do not say that it fits the need"
                      " asked for: \"unclear\"", prompt)
        self.assertIn("the kind in the plural", prompt)
        self.assertIn("never a title's words pasted in", prompt)
        self.assertIn("\"This <kind> says ...\" when only one product was given", prompt)


class TheChecks(unittest.TestCase):
    def test_a_true_sentence_is_shown(self) -> None:
        checked = check_answer(_answer(GOOD), _quiet(), stop_reason="end_turn")
        self.assertTrue(checked.shown)
        self.assertEqual(checked.sentence, GOOD)
        self.assertEqual((checked.yes, checked.no, checked.unclear), ((2,), (), (1, 3)))
        self.assertEqual(checked.proof, ((2, "quiet washing machine"),))
        self.assertEqual(checked.unproved, ())

    def test_a_yes_counts_only_with_its_words_in_the_product(self) -> None:
        # The words given are not the product's: the yes is read as unclear, and the
        # sentence that counted it is withheld.
        checked = check_answer(_answer(GOOD, words={2: "Whisper quiet drum"}), _quiet(), stop_reason="end_turn")
        self.assertFalse(checked.shown)
        self.assertEqual((checked.yes, checked.unproved, checked.unclear), ((), (2,), (1, 2, 3)))
        # No words at all: the same.
        self.assertEqual(check_answer(_answer(GOOD, words={}), _quiet(), stop_reason="end_turn").unproved, (2,))
        # Case, spaces and curly quotes do not matter; the description counts as much as
        # the title.
        found = complex_search_of("quiet washing machine", _resolution(),
                                  descriptions={"row-2": "Inverter motor, low noise: 49 dB."})
        checked = check_answer(_answer(GOOD, words={2: "LOW  NOISE: 49 dB"}), found, stop_reason="end_turn")
        self.assertTrue(checked.shown, checked.failure)
        self.assertEqual(checked.proof, ((2, "low noise: 49 db"),))

    def test_a_yes_may_give_its_words_in_pieces(self) -> None:
        # The third measure: all six unproved answers joined two pieces of their
        # product's words with ";". Each piece is checked on its own, letter for letter.
        found = complex_search_of("quiet washing machine", _resolution(),
                                  descriptions={"row-2": "Inverter motor, low noise: 49 dB. Runs at night."})
        for words in ("low noise: 49 dB; Runs at night", "low noise: 49 dB … runs at night",
                      "Low noise: 49 dB...runs at night."):
            checked = check_answer(_answer(GOOD, words={2: words}), found, stop_reason="end_turn")
            self.assertTrue(checked.shown, (words, checked.failure))
            self.assertEqual(checked.proof, ((2, "low noise: 49 db; runs at night"),))
        # One piece not in the product, or too short to show anything: the yes is
        # unproved and the sentence that counted it withheld.
        for words in ("low noise: 49 dB; whisper quiet", "low noise: 49 dB; dB", ";;"):
            checked = check_answer(_answer(GOOD, words={2: words}), found, stop_reason="end_turn")
            self.assertFalse(checked.shown, words)
            self.assertEqual(checked.unproved, (2,), words)

    def test_one_fitting_product_among_many_may_be_this_one(self) -> None:
        checked = check_answer(_answer("This washing machine says quiet in its title, at 549.00 GBP."), _quiet(),
                               stop_reason="end_turn")
        self.assertTrue(checked.shown, checked.failure)

    def test_numbers_and_names_from_a_description(self) -> None:
        found = complex_search_of("quiet washing machine", _resolution(),
                                  descriptions={"row-2": "Quiet Mark approved, 47 dB at night."})
        checked = check_answer(
            _answer("1 of these 3 washing machines say Quiet Mark, 47 dB, from 549.00 GBP."), found,
            stop_reason="end_turn",
        )
        self.assertTrue(checked.shown, checked.failure)

    def test_no_sentence_when_none_fits(self) -> None:
        checked = check_answer(
            _answer("None of these 3 washing machines say quiet in their titles.", ("unclear",) * 3),
            _quiet(), stop_reason="end_turn",
        )
        self.assertFalse(checked.shown)
        self.assertEqual((checked.sentence, checked.failure, checked.shop_words), ("", "", ()))

    def test_the_shops_words_when_none_fits(self) -> None:
        checked = check_answer(
            _answer("", ("unclear",) * 3, shop_words=("EcoWash", "Fixturon", "best", "washing machine",
                                                   "compact", "10kg 1400rpm", "1400rpm")),
            _quiet(), stop_reason="end_turn",
        )
        # A brand, a judgement, the kind's name and a word in no title are dropped; three
        # at most.
        self.assertEqual(checked.shop_words, ("EcoWash", "10kg 1400rpm", "1400rpm"))
        self.assertEqual(checked.sentence, "")

    def test_the_shops_words_never_from_a_product_answered_no(self) -> None:
        # The fourth measure: "Skinguard" came from "Gillette Skinguard Razor", a manual
        # razor the AI itself answered `no` among electric shavers; its button would have
        # shown that razor. A word standing only in such a title is dropped.
        checked = check_answer(
            _answer("", ("no", "unclear", "unclear"), shop_words=("1400rpm", "EcoWash")),
            _quiet(), stop_reason="end_turn",
        )
        self.assertEqual(checked.shop_words, ("EcoWash",))
        self.assertEqual(checked.no, (1,))
        # The same words, no product answered `no`: both stand.
        checked = check_answer(
            _answer("", ("unclear",) * 3, shop_words=("1400rpm", "EcoWash")), _quiet(), stop_reason="end_turn",
        )
        self.assertEqual(checked.shop_words, ("1400rpm", "EcoWash"))

    def test_the_shops_words_only_when_none_fits(self) -> None:
        checked = check_answer(_answer(GOOD, shop_words=("EcoWash",)), _quiet(), stop_reason="end_turn")
        self.assertTrue(checked.shown)
        self.assertEqual(checked.shop_words, ())
        self.assertEqual(shop_words_that_pass("EcoWash", _quiet()), ())

    def test_a_rating_of_the_product_is_no_review(self) -> None:
        rated = "1 of these 3 washing machines say quiet, rated for 10kg loads, from 549.00 GBP."
        self.assertTrue(check_answer(_answer(rated), _quiet(), stop_reason="end_turn").shown)
        reviewed = "1 of these 3 washing machines say quiet, rated highly, from 549.00 GBP."
        self.assertIn("rated", check_answer(_answer(reviewed), _quiet(), stop_reason="end_turn").failure)

    def test_one_product_is_this_one(self) -> None:
        one = complex_search_of("quiet washing machine", _resolution(rows=_rows(WASHERS[1:2])))
        checked = check_answer(
            _answer("This washing machine says quiet in its title, at 549.00 GBP.", ("yes",),
                    words={1: "Quiet Washing Machine"}), one,
            stop_reason="end_turn",
        )
        self.assertTrue(checked.shown, checked.failure)

    def test_a_price_with_its_symbol(self) -> None:
        checked = check_answer(_answer(GOOD.replace("549.00 GBP", "£549.00")), _quiet(), stop_reason="end_turn")
        self.assertTrue(checked.shown, checked.failure)

    def test_withheld(self) -> None:
        cases = {
            "2 of these 3 washing machines say quiet in their titles, from 549.00 GBP.": "a count that is not its own",
            "1 of these 7 washing machines say quiet in their titles, from 549.00 GBP.": "a count of products that was not sent",
            "1 of these 3 washing machines say quiet in their titles, from 279.00 GBP.": "a price not of a product answered yes",
            "1 of these 3 washing machines say quiet, from 549.00 USD.": "a price not of a product answered yes",
            "1 of these 3 washing machines is the best quiet one, from 549.00 GBP.": "a forbidden word: best",
            "1 of these 3 washing machines is a best-selling quiet one, from 549.00 GBP.": "a forbidden word: best",
            "1 of these 3 washing machines, a Miele, says quiet, from 549.00 GBP.": "a name not in the search",
            "1 of these 3 washing machines say quiet at 47 dB, from 549.00 GBP.": "a number not in the search",
            "1 από τα 3 πλυντήρια είναι αθόρυβο, από 549.00 GBP.": "a sentence not in English",
            "1 of these 3 washing machines say quiet. Buy it soon, from 549.00 GBP.": "more than one sentence",
            "Is 1 of these 3 washing machines quiet?": "a question or an exclamation",
            "1 of these 3 washing machines say quiet, see www.shop.invalid, from 549.00 GBP.": "a link or an e-mail",
            "Their titles say quiet for one washing machine, from 549.00 GBP.": "does not say how many fit",
            "None of these 3 washing machines say quiet.": "a count that is not its own yes answers (1)",
            "None of their titles say quiet.": "'none' while 1 were answered yes",
            " ".join(["word"] * 31): "a sentence of 31 words",
            "": "no sentence",
        }
        for sentence, failure in cases.items():
            with self.subTest(sentence=sentence):
                checked = check_answer(_answer(sentence), _quiet(), stop_reason="end_turn")
                self.assertFalse(checked.shown)
                self.assertEqual(checked.sentence, "")
                self.assertIn(failure, checked.failure)

    def test_withheld_for_the_verdicts_or_the_stop(self) -> None:
        found = _quiet()
        cases = (
            (_answer(GOOD, ("unclear", "yes")), "end_turn", "1 of the 3 products not answered"),
            ({"verdicts": [{"n": 4, "fits": "yes", "words": ""}], "sentence": GOOD}, "end_turn",
             "a product number that was not sent"),
            ({"verdicts": [{"n": 1, "fits": "yes", "words": "1400rpm"}, {"n": 1, "fits": "no", "words": ""}],
              "sentence": GOOD}, "end_turn", "answered twice"),
            ({"verdicts": [{"n": 1, "fits": "maybe"}], "sentence": GOOD}, "end_turn", "not yes, no or unclear"),
            ({"sentence": GOOD}, "end_turn", "not in the agreed shape"),
            (None, "refusal", "stopped early (refusal)"),
            (_answer(GOOD), "max_tokens", "stopped early (max_tokens)"),
        )
        for answer, stop, failure in cases:
            with self.subTest(failure=failure):
                checked = check_answer(answer, found, stop_reason=stop)
                self.assertFalse(checked.shown)
                self.assertIn(failure, checked.failure)

    def test_the_forbidden_words(self) -> None:
        for word in ("best", "recommended", "quality", "cheap", "deal", "rated", "tested", "perfect"):
            self.assertIn(word, FORBIDDEN_WORDS)


class TheDescriptions(unittest.TestCase):
    def test_cleaned_and_cut(self) -> None:
        text = "<p>Low&nbsp;noise <b>49 dB</b> spin,\n\n quiet  wash.</p>"
        self.assertEqual(clean_description(text), "Low noise 49 dB spin, quiet wash.")
        long = " ".join(["word"] * 200)
        cut = clean_description(long)
        self.assertLessEqual(len(cut), 402)
        self.assertTrue(cut.endswith(" …"))

    def test_read_from_the_feeds_own_columns(self) -> None:
        product = types.SimpleNamespace(raw={"description": "", "product_short_description": "Ages 6-10."})
        self.assertEqual(description_of(product), "Ages 6-10.")
        self.assertEqual(description_of(types.SimpleNamespace(raw={})), "")

    def test_given_to_the_ai_under_each_product(self) -> None:
        found = complex_search_of(
            "quiet washing machine", _resolution(),
            descriptions={"row-3": "<p>Low noise 49 dB spin</p>"},
        )
        self.assertEqual(found.candidates[2].description, "Low noise 49 dB spin")
        self.assertEqual(found.candidates[0].description, "")
        self.assertIn("3. Fixturon EcoWash 9kg Washing Machine White | brand Fixturon | 429.99 GBP | shop Fictional"
                      " Appliances\n   description: Low noise 49 dB spin", user_message(found))


class TheShopsWordsAsSearches(unittest.TestCase):
    def test_kept_only_with_the_catalogues_own_count(self) -> None:
        answers = {
            "EcoWash washing machine": _resolution(unmatched=(), total=12),
            "Fixturon washing machine": _resolution(unmatched=(), rows=[], total=0),
            "1400rpm washing machine": _resolution(unmatched=("1400rpm",)),
            "Steam washing machine": _resolution(unmatched=(), reasons=("provider_feed_selection_product_named_by_words",)),
        }
        asked = []

        def resolve(search, shown):
            asked.append((search, shown))
            return answers[search]

        kept = verified_shop_words(("EcoWash", "Fixturon", "1400rpm", "Steam"), _quiet(), resolve)
        self.assertEqual([(word.word, word.search, word.count) for word in kept],
                         [("EcoWash", "EcoWash washing machine", 12)])
        self.assertEqual(asked[0], ("EcoWash washing machine", 4))
        self.assertEqual(button_search("  compact  ", _quiet()), "compact washing machine")


class _FakeMessages:
    def __init__(self, response=None, error=None) -> None:
        self.response, self.error, self.requests = response, error, []

    def create(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response


def _client(response=None, error=None):
    return types.SimpleNamespace(messages=_FakeMessages(response, error))


def _response(text, stop="end_turn", usage=None):
    return {
        "model": "claude-haiku-5-5",
        "stop_reason": stop,
        "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": text}],
        "usage": usage or {"input_tokens": 1800, "output_tokens": 400},
    }


class TheCall(unittest.TestCase):
    def test_an_answer_its_tokens_and_its_cost(self) -> None:
        client = _client(_response('{"verdicts": [], "sentence": "x"}'))
        asked = ask(request_kwargs(_quiet()), client=client)
        self.assertEqual(asked.answer, {"verdicts": [], "sentence": "x"})
        self.assertEqual((asked.stop_reason, asked.model, asked.error), ("end_turn", "claude-haiku-5-5", ""))
        self.assertEqual((asked.input_tokens, asked.output_tokens), (1800, 400))
        # $0.10 a million read, $0.50 a million written.
        self.assertAlmostEqual(asked.cost_usd, 0.00038)
        self.assertEqual(client.messages.requests[0]["model"], "claude-haiku-5-5")

    def test_the_cache_is_priced_as_such(self) -> None:
        usage = {"input_tokens": 1000, "output_tokens": 0, "cache_creation_input_tokens": 1000,
                 "cache_read_input_tokens": 1000}
        self.assertAlmostEqual(cost_usd("claude-haiku-5-5", usage), (100 + 125 + 10) / 1_000_000)

    def test_any_failure_is_an_answer_with_nothing_to_show(self) -> None:
        class Overloaded(Exception):
            status_code = 529

        cases = (
            (_client(error=Overloaded("busy")), "Overloaded (HTTP 529)", ""),
            (_client(_response("not json")), "an answer that is not JSON", "end_turn"),
            (_client(_response("[1, 2]")), "an answer that is not a JSON object", "end_turn"),
            (_client(_response("", stop="refusal")), "", "refusal"),
        )
        for client, error, stop in cases:
            with self.subTest(error=error or stop):
                asked = ask(request_kwargs(_quiet()), client=client)
                self.assertIsNone(asked.answer)
                self.assertEqual(asked.error, error)
                self.assertEqual(asked.stop_reason, stop)
                self.assertFalse(check_answer(asked.answer, _quiet(), stop_reason=asked.stop_reason).shown)


class TheMeasure(unittest.TestCase):
    def test_its_list_of_searches(self) -> None:
        from measure_ai import TAGS, read_searches

        searches = read_searches(SEARCHES)
        self.assertGreaterEqual(len(searches), 150)
        tags = {tag for tag, _search in searches}
        self.assertEqual(tags, set(TAGS))
        self.assertTrue(any(any("Ͱ" <= char <= "Ͽ" for char in search) for _tag, search in searches))
        self.assertEqual(len({search for _tag, search in searches}), len(searches))

    def test_a_line_without_its_tag_is_refused(self) -> None:
        from measure_ai import read_searches

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "searches.txt"
            path.write_text("# a comment\nwords | quiet washing machine\nquiet fridge\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_searches(path)

    def test_one_search_asked_with_the_ai_faked(self) -> None:
        from measure_ai import measure_one

        def resolve(search, shown):
            self.assertEqual(shown, 32)
            return _resolution()

        def fake_ask(request, client):
            return Asked(_answer(GOOD), "end_turn", "claude-haiku-5-5", 1800, 400, 0, 0, 0.00038, 1.2, "")

        measured = measure_one("words", "quiet washing machine", resolve=resolve, ask=fake_ask, client=object(),
                               dry_run=False)
        self.assertTrue(measured.asked)
        self.assertEqual(measured.sentence, GOOD)
        self.assertEqual((measured.yes, measured.no, measured.unclear), (1, 0, 2))
        self.assertIn("    yes      2. Testline Series 6 9kg Quiet Washing Machine | 549.00 GBP | Fictional Electricals",
                      measured.lines)
        self.assertIn("               its words: quiet washing machine", measured.lines)

    def test_the_shops_words_when_nothing_fits(self) -> None:
        from measure_ai import measure_one

        def resolve(search, shown):
            if search == "EcoWash washing machine":
                return _resolution(unmatched=(), total=7)
            return _resolution()

        def fake_ask(request, client):
            answer = _answer("", ("unclear",) * 3, shop_words=("EcoWash", "Testline"))
            return Asked(answer, "end_turn", "claude-haiku-5-5", 1800, 400, 0, 0, 0.00038, 1.2, "")

        measured = measure_one("words", "quiet washing machine", resolve=resolve, ask=fake_ask, client=object(),
                               dry_run=False)
        self.assertEqual(measured.sentence, "")
        self.assertEqual(measured.failure, "")
        # "Testline" is a brand of the products: never offered.
        self.assertEqual(measured.buttons, ("EcoWash (7)",))
        self.assertEqual(measured.proposed, ("EcoWash", "Testline"))

    def test_a_dry_run_asks_nothing(self) -> None:
        from measure_ai import measure_one

        def never(request, client):
            raise AssertionError("the AI was asked in a dry run")

        measured = measure_one("words", "quiet washing machine", resolve=lambda search, shown: _resolution(),
                               ask=never, client=None, dry_run=True)
        self.assertFalse(measured.asked)
        self.assertEqual(measured.words, ("quiet",))


def _write_catalogue(path: Path) -> None:
    from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct
    from picwise_providers.offer_health import build_feed_availability_context
    from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue
    from picwise_providers.search_selection import _product_search_fields

    shelf = "Home & Garden > Household Appliances > Laundry Appliances > Washers & Dryers"
    rows = [(f"Fixturon Model {n} 8kg 1400rpm Washing Machine White", 199.0 + 20 * n) for n in range(1, 9)]
    products = tuple(
        ProviderProduct(
            provider_key="awin",
            provider_product_id=f"row-{number}",
            title=title,
            brand="Fixturon",
            category_text=shelf,
            product_url=f"https://shop.invalid/p/{number}",
            image_url=f"https://shop.invalid/i/{number}.jpg",
            price_text=f"{price:.2f}",
            availability_text="in stock",
            currency="GBP",
            raw={"merchant_name": "Fictional Appliances", "in_stock": "1", "description": fixture_description()},
        )
        for number, (title, price) in enumerate(rows, start=1)
    )
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 11, 5, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(
            status="provider_feed_ready", provider_key="awin", product_count=len(products), eligible_count=len(products)
        ),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        kinds=tuple(frozenset({"washing_machine"}) for _product in products),
        eligible_count=len(products),
        shop_count=1,
        suggestions=(),
        search_fields=tuple(_product_search_fields(product) for product in products),
    )
    write_prepared_catalogue(prepared, path)


class TheMeasureOnACatalogue(unittest.TestCase):
    def test_the_copy_end_to_end_without_the_ai(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            catalogue = Path(folder) / "catalogue.json.gz"
            searches = Path(folder) / "searches.txt"
            _write_catalogue(catalogue)
            searches.write_text(
                "words | washing machine for a narrow utility room\n"
                "plain | washing machine\n"
                "judgement | best washing machine\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(MEASURE), str(catalogue), str(searches), "--dry-run"],
                capture_output=True, text=True, check=False, timeout=900,
                env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("8 products", out)
        self.assertIn("3 searches; the AI: not asked (a dry run)", out)
        self.assertIn("[1] words | washing machine for a narrow utility room", out)
        self.assertIn("read as washing machine; 8 products, 8 read; asked about: narrow, utility, room", out)
        self.assertIn("characters of products, 8 with a description", out)
        self.assertIn("[2] plain | washing machine\n    not asked: every word matched", out)
        # "best" is set aside, as the words that judge or shop are (owner, 2026-11-07;
        # `tests/test_picwise_reading_rules_by_cause.py`): not asked, every word matched.
        self.assertIn("[3] judgement | best washing machine\n    not asked: every word matched", out)
        self.assertIn("words: 1 searches, 1 complex for the engine (expected: complex)", out)
        self.assertIn("plain: 1 searches, 0 complex for the engine (expected: not complex)", out)
        self.assertNotIn("shop.invalid", out)


class TheLayersBoundaries(unittest.TestCase):
    def _imports(self, path: Path) -> list[tuple[str, int]]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found += [(alias.name, node.col_offset) for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append((node.module, node.col_offset))
        return found

    def test_the_sdk_only_inside_make_client(self) -> None:
        for path in sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "deployment").rglob("*.py")) + [ROOT / "api" / "index.py"]:
            for module, column in self._imports(path):
                if module.split(".")[0] != "anthropic":
                    continue
                with self.subTest(path=str(path.relative_to(ROOT))):
                    self.assertEqual(path, ROOT / "src" / "picwise_ai" / "client.py")
                    self.assertGreater(column, 0, "imported at the top of the module")

    def test_the_understanding_never_imports_the_ai_layer(self) -> None:
        for path in sorted((ROOT / "src" / "picwise_nlu").rglob("*.py")):
            for module, _column in self._imports(path):
                with self.subTest(path=str(path.relative_to(ROOT)), module=module):
                    self.assertNotEqual(module.split(".")[0], "picwise_ai")


if __name__ == "__main__":
    unittest.main()
