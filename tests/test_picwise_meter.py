"""The quality meter (`picwise_ai.meter`, `deployment/server/meter_service.py`;
`docs/PICWISE_KIND_ITSELF_RULES.md`, section 9; the owner's plan of 21/11, step 9).

Pinned here, with a site and a model of the test's own (no call leaves the test):

- the judge is Claude Opus 5.5, given the search's words and each card's title, shop and
  price, and nothing of the gate it measures; every verdict is checked;
- the cards are read from the site's own page as a visitor sees it: never a link or an id;
- every day the same fixed searches, and a seventh of the kinds: every kind within a week;
- a card is judged once: a day pays only for the cards it has not seen; a card whose price or
  title changed is another card;
- the day's note: the cards right of those judged, beside the day before; a fall of more
  than 3 points is flagged; the wrong cards by title and shop;
- it stops before its day's limit, and what it did not judge is counted as not judged; a
  page that fails is counted, never guessed;
- its unit runs as the AI layer, after the night's work, and writes only its own folder.

Every product is local test data: fictional brands and shops.
"""
from __future__ import annotations

import html
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import measure_after  # noqa: E402
import meter_service  # noqa: E402
from picwise_ai import meter  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402

DAY = date(2026, 11, 23)
PRINTER = [("Fixturon Inkjet Printer A4", "Fixture Shop via Awin", "£59.00"),
           ("Fixturon Pickup Roller for printers", "Fixture Shop via Awin", "£3.99"),
           ("Testline Laser Printer", "Other Shop via Awin", "£129.00")]
KETTLE = [("Fixturon Kettle 1.7L", "Fixture Shop via Awin", "£19.00"),
          ("MH22", "Other Shop via Awin", "£25.00")]
DRILL = [("Testline Cordless Drill 18V", "Other Shop via Awin", "£64.00"),
         ("Testline Drill Carry Case", "Other Shop via Awin", "£9.00")]


def _page(cards) -> str:
    """A search's page as the site draws its cards (`picwise_surface`)."""
    return "<html><body>" + "".join(
        f'<article class="pw-card pw-card-plain" data-choice-id="c{number}"><a class="pw-card-cta pw-card-cta-link" '
        f'href="/out/feed?pid=secret-{number}">Go</a><h2 title="{html.escape(title)}" class="pw-card-title">'
        f'{html.escape(title)}</h2><p class="pw-card-shop">{html.escape(shop)}</p><p class="pw-price">{html.escape(price)}</p>'
        "</article>"
        for number, (title, shop, price) in enumerate(cards, 1)
    ) + "</body></html>"


class Site:
    """The site of the test's own: each search's cards, and the addresses asked of it."""

    def __init__(self, pages: dict) -> None:
        self.pages = dict(pages)
        self.asked: list[str] = []

    def __call__(self, url: str) -> str:
        self.asked.append(url)
        search = parse_qs(urlsplit(url).query)["q"][0]
        if self.pages.get(search) is None:
            raise OSError("no answer")
        return _page(self.pages[search])


class Opus:
    """The judge of the test's own: a roller or a case is no, a title that says nothing is
    unsure, the rest yes."""

    def __init__(self, cost: float = 0.01, silent: bool = False) -> None:
        self.cost, self.silent = cost, silent
        self.requests: list[dict] = []

    def __call__(self, request: dict) -> Asked:
        self.requests.append(request)
        lines = [line for line in request["messages"][0]["content"].splitlines() if line[:1].isdigit()]
        verdicts = []
        for number, line in enumerate(lines, 1):
            said = "no" if ("Roller" in line or "Case" in line) else "unsure" if "MH22" in line else "yes"
            verdicts.append({"n": number, "is": said, "why": "a part of it" if said == "no" else "it is"})
        return Asked(None if self.silent else {"verdicts": verdicts}, "end_turn", request["model"], 800, 200, 0, 0,
                     self.cost, 0.5, "")


class TheJudge(unittest.TestCase):
    def test_it_is_opus_given_what_a_visitor_sees(self) -> None:
        cards = [{"title": title, "shop": shop, "price": price} for title, shop, price in PRINTER]
        request = meter.request_kwargs("printer", cards)
        self.assertEqual((request["model"], request["output_config"]["effort"]), ("claude-opus-5-5", meter.EFFORT))
        self.assertEqual(request["system"][0]["text"], meter.SYSTEM_PROMPT)
        self.assertEqual(request["messages"][0]["content"].splitlines(), [
            "The buyer's search: printer", "", "Results (3):",
            "1. Fixturon Inkjet Printer A4 | shop: Fixture Shop via Awin | price: £59.00",
            "2. Fixturon Pickup Roller for printers | shop: Fixture Shop via Awin | price: £3.99",
            "3. Testline Laser Printer | shop: Other Shop via Awin | price: £129.00",
        ])
        self.assertEqual(request["output_config"]["format"]["schema"], meter.SCHEMA)

    def test_it_reads_no_part_of_the_gate_it_measures(self) -> None:
        for module in (ROOT / "src" / "picwise_ai" / "meter.py", ROOT / "deployment" / "server" / "meter_service.py"):
            imports = [line.strip() for line in module.read_text(encoding="utf-8").splitlines()
                       if line.strip().startswith(("import ", "from "))]
            for line in imports:
                self.assertNotIn("itself", line, module.name)
                self.assertNotIn("kind_lines", line, module.name)
                self.assertNotIn("ai_shelves", line, module.name)
        # The gate's model is not the judge.
        from picwise_ai import itself

        self.assertNotIn(meter.MODEL, (itself.MODEL, itself.SECOND_MODEL))

    def test_the_instructions_are_pinned(self) -> None:
        # Changed on purpose only, with `meter_service.VERSION`: the days before are then
        # not read beside the days after.
        self.assertEqual((meter_service.VERSION, meter.prompt_fingerprint()), (1, "6fdca035d31a"))

    def test_every_verdict_is_checked(self) -> None:
        answer = {"verdicts": [{"n": 1, "is": "yes", "why": "a printer"}, {"n": 2, "is": "no", "why": "x" * 200},
                               {"n": 3, "is": "maybe", "why": ""}, {"n": 9, "is": "yes", "why": ""},
                               {"n": True, "is": "yes", "why": ""}, "not a verdict"]}
        found = meter.checked_verdicts(answer, 3)
        self.assertEqual(sorted(found), [1, 2])
        self.assertEqual(found[1], ("yes", "a printer"))
        self.assertLessEqual(len(found[2][1]), meter.WHY_CHARS)
        twice = {"verdicts": [{"n": 1, "is": "yes", "why": ""}, {"n": 1, "is": "no", "why": ""}, {"n": 2, "is": "no", "why": ""}]}
        self.assertEqual(sorted(meter.checked_verdicts(twice, 2)), [2])
        for broken in (None, {}, {"verdicts": "yes"}, []):
            self.assertEqual(meter.checked_verdicts(broken, 3), {})

    def test_a_verdict_is_kept_by_the_search_and_what_the_card_shows(self) -> None:
        card = {"title": "Fixturon Kettle 1.7L", "shop": "Fixture Shop via Awin", "price": "£19.00"}
        key = meter.card_key("kettle", card)
        self.assertEqual(key, meter.card_key("  Kettle ", {**card, "title": "Fixturon  Kettle 1.7L", "image": "x"}))
        for other in (meter.card_key("electric kettle", card), meter.card_key("kettle", {**card, "price": "£18.00"}),
                      meter.card_key("kettle", {**card, "shop": "Other Shop"}), meter.card_key("kettle", {**card, "title": "Kettle"})):
            self.assertNotEqual(key, other)


class TheSitesOwnPage(unittest.TestCase):
    def test_the_cards_as_a_visitor_sees_them(self) -> None:
        from picwise_app import PicwiseLocalApp
        from picwise_providers.awin_adapter import clear_awin_feed_parse_cache
        from picwise_providers.state import clear_provider_feed_pipeline_cache
        from picwise_search import search_warmup

        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("AWIN_FEED_", "PICWISE_PREPARED", "PICWISE_SHOP_CATALOGUES"))}
        env["AWIN_FEED_FILE"] = str(ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv")
        with mock.patch.dict(os.environ, env, clear=True):
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()
            self.addCleanup(clear_awin_feed_parse_cache)
            self.addCleanup(clear_provider_feed_pipeline_cache)
            self.addCleanup(search_warmup._reset_search_warmup_for_tests)
            page = PicwiseLocalApp().picwise_reference_html("laptop", shown=meter.CARDS)
        cards = meter_service.read_cards(page, meter.CARDS)
        # The fixture's six laptops: more than the first page's four choices.
        self.assertEqual(len(cards), 6)
        for card in cards:
            self.assertEqual(sorted(card), ["price", "shop", "title"])
            self.assertIn("Laptop", card["title"])
            self.assertTrue(card["price"].startswith("£"), card)
            self.assertIn("via Awin", card["shop"])
            self.assertNotIn("http", " ".join(card.values()))
        self.assertEqual(len(meter_service.read_cards(page, 4)), 4)
        self.assertEqual(meter_service.read_cards("<html>no cards</html>", 12), [])


class TheDaysKinds(unittest.TestCase):
    def test_every_kind_within_a_week_by_its_first_name(self) -> None:
        from picwise_nlu.product_concepts import get_product_concepts

        named = {concept.concept_id: concept.english[0] for concept in get_product_concepts() if concept.english}
        week = [meter_service.kinds_of_the_day(DAY + timedelta(days=n)) for n in range(7)]
        seen = [kind for day in week for kind, _name in day]
        self.assertEqual(sorted(seen), sorted(named))
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(dict(pair for day in week for pair in day), named)
        self.assertLessEqual(max(map(len, week)) - min(map(len, week)), 1)
        self.assertEqual(meter_service.kinds_of_the_day(DAY), meter_service.kinds_of_the_day(DAY + timedelta(days=7)))


class ADay(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)
        for patch in (mock.patch.object(measure_after, "SEARCHES", ("printer", "kettle")),
                      mock.patch.object(meter_service, "kinds_of_the_day", lambda day: [("drill", "drill"), ("kettle", "kettle")])):
            patch.start()
            self.addCleanup(patch.stop)
        self.site = Site({"printer": PRINTER, "kettle": KETTLE, "drill": DRILL})

    def _run(self, judge, day: date = DAY, **options) -> dict:
        with redirect_stdout(io.StringIO()) as said:
            note = meter_service.run(self.directory, get=self.site, ask_fn=judge, day=day, sleep=lambda seconds: None,
                                     workers=1, **options)
        self.said = said.getvalue()
        return note

    def test_the_pages_are_asked_as_pages_and_the_cards_judged(self) -> None:
        judge = Opus()
        note = self._run(judge)
        # Each search's page once (the kettle is a fixed search and one of the day's kinds).
        self.assertEqual(self.site.asked, [f"{meter_service.SITE}/search?q={name}&shown=12" for name in ("printer", "kettle", "drill")])
        self.assertEqual(len(judge.requests), 3)
        self.assertEqual(note["searches"], {"searches": 2, "pages_failed": 0, "with_no_card": 0, "cards": 5, "yes": 3, "no": 1,
                                            "unsure": 1, "not_judged": 0, "share": 0.75})
        self.assertEqual((note["kinds"]["of_the_day"], note["kinds"]["cards"], note["kinds"]["yes"], note["kinds"]["no"]), (2, 4, 2, 1))
        self.assertEqual((note["day"], note["judged_today"], note["calls"], note["cost_usd"], note["stopped"], note["before"]),
                         ("2026-11-23", 7, 3, 0.03, "", None))
        self.assertEqual(note["wrong"], [
            {"part": "search", "q": "printer", "title": "Fixturon Pickup Roller for printers", "shop": "Fixture Shop via Awin",
             "price": "£3.99", "why": "a part of it"},
            {"part": "kind", "q": "drill", "title": "Testline Drill Carry Case", "shop": "Other Shop via Awin", "price": "£9.00",
             "why": "a part of it"},
        ])
        self.assertEqual(json.loads((self.directory / meter_service.NOTE_NAME).read_text(encoding="utf-8")), note)
        self.assertIn("quality on 2026-11-23, the 40 searches: 3 of 4 cards right (75.0%); 1 cannot be told, 0 not judged, "
                      "0 pages failed; no day before", self.said)
        self.assertIn('quality, wrong for "printer": Fixturon Pickup Roller for printers (Fixture Shop via Awin, £3.99): a part of it',
                      self.said)
        # Never a link or an id: not in what the judge reads, not in what is kept or said.
        kept = (self.directory / meter_service.NOTE_NAME).read_text(encoding="utf-8") + self.said \
            + json.dumps(judge.requests) + json.dumps(meter_service.read_verdicts(self.directory / meter_service.VERDICTS_NAME))
        for word in ("secret-", "/out/", "pid="):
            self.assertNotIn(word, kept)

    def test_a_card_is_judged_once(self) -> None:
        self._run(Opus())
        judge = Opus()
        note = self._run(judge, DAY + timedelta(days=1))
        self.assertEqual((judge.requests, note["judged_today"], note["cost_usd"]), ([], 0, 0.0))
        self.assertEqual((note["searches"]["share"], note["before"], note["fell_points"], note["fell"]),
                         (0.75, {"day": "2026-11-23", "share": 0.75}, 0.0, False))
        # A price changes: that card is another card, and only it is judged.
        self.site.pages["kettle"] = [KETTLE[0][:2] + ("£18.00",), KETTLE[1]]
        note = self._run(judge, DAY + timedelta(days=2))
        self.assertEqual(len(judge.requests), 1)
        self.assertEqual(judge.requests[0]["messages"][0]["content"].splitlines()[2:],
                         ["Results (1):", "1. Fixturon Kettle 1.7L | shop: Fixture Shop via Awin | price: £18.00"])
        self.assertEqual(note["judged_today"], 1)
        days = meter_service.read_days(self.directory / meter_service.DAYS_NAME)
        self.assertEqual([entry["day"] for entry in days], ["2026-11-23", "2026-11-24", "2026-11-25"])
        self.assertEqual(note["kinds_week"]["days"], 3)

    def test_a_fall_of_more_than_three_points_is_flagged(self) -> None:
        self._run(Opus())
        # A roller takes a printer's place among the first cards.
        self.site.pages["printer"] = [PRINTER[1], ("Fixturon Feed Roller Kit", "Fixture Shop via Awin", "£4.50"), PRINTER[2]]
        note = self._run(Opus(), DAY + timedelta(days=1))
        self.assertEqual((note["searches"]["share"], note["before"]["share"], note["fell_points"], note["fell"]), (0.5, 0.75, 25.0, True))
        # The day run again counts the same day once, against the day before.
        again = self._run(Opus(), DAY + timedelta(days=1))
        self.assertEqual((again["before"]["day"], again["fell"]), ("2026-11-23", True))
        self.assertEqual(len(meter_service.read_days(self.directory / meter_service.DAYS_NAME)), 2)

    def test_it_stops_before_its_days_limit(self) -> None:
        judge = Opus(cost=0.04)
        note = self._run(judge, budget=0.06)
        self.assertEqual((len(judge.requests), note["stopped"]), (1, "its limit of $0.06"))
        self.assertEqual((note["searches"]["cards"], note["searches"]["not_judged"]), (5, 2))
        self.assertIn("stopped at its limit of $0.06", self.said)
        # The next day judges what was left, with the day's own limit.
        rest = Opus(cost=0.01)
        note = self._run(rest, DAY + timedelta(days=1))
        self.assertEqual((len(rest.requests), note["searches"]["not_judged"], note["stopped"]), (2, 0, ""))

    def test_a_page_that_fails_is_counted_never_guessed(self) -> None:
        self.site.pages["printer"] = None
        self.site.pages["drill"] = []
        note = self._run(Opus())
        self.assertEqual((note["searches"]["pages_failed"], note["searches"]["cards"], note["searches"]["share"]), (1, 2, 1.0))
        self.assertEqual((note["kinds"]["with_no_card"], note["kinds"]["pages_failed"]), (1, 0))

    def test_a_call_with_no_answer_leaves_its_cards_not_judged(self) -> None:
        note = self._run(Opus(silent=True))
        self.assertEqual((note["failed_calls"], note["judged_today"], note["searches"]["not_judged"], note["searches"]["share"]),
                         (3, 0, 5, None))
        self.assertIn("none judged", self.said)

    def test_verdicts_kept_under_other_instructions_are_not_counted(self) -> None:
        self._run(Opus())
        judge = Opus()
        with mock.patch.object(meter_service, "VERSION", 2):
            note = self._run(judge, DAY + timedelta(days=1))
        self.assertEqual((len(judge.requests), note["judged_today"], note["version"]), (3, 7, f"2.{meter.prompt_fingerprint()}"))

    def test_a_verdict_no_page_shows_any_more_is_dropped_in_time(self) -> None:
        self._run(Opus())
        self.site.pages["drill"] = [DRILL[0]]
        self._run(Opus(), DAY + timedelta(days=meter_service.KEPT_DAYS))
        kept = meter_service.read_verdicts(self.directory / meter_service.VERDICTS_NAME)
        self.assertEqual(len(kept), 7)
        self._run(Opus(), DAY + timedelta(days=meter_service.KEPT_DAYS + 1))
        kept = meter_service.read_verdicts(self.directory / meter_service.VERDICTS_NAME)
        self.assertEqual(len(kept), 6)
        self.assertNotIn("Testline Drill Carry Case", {entry["title"] for entry in kept.values()})

    def test_with_no_judge_the_cards_are_counted_against_what_is_kept(self) -> None:
        note = self._run(None)
        self.assertEqual((note["asked"], note["judged_today"], note["searches"]["not_judged"]), (False, 0, 5))
        self.assertIn("the AI not asked", self.said)

    def test_without_the_key_nothing_is_judged(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False), redirect_stdout(io.StringIO()) as said:
            os.environ.pop("ANTHROPIC_API_KEY", None)
            self.assertEqual(meter_service.main(["--dir", str(self.directory)]), 0)
        self.assertIn("no key", said.getvalue())
        self.assertFalse((self.directory / meter_service.NOTE_NAME).exists())

    def test_the_fixed_searches_are_the_measure_afters_forty(self) -> None:
        import importlib

        self.assertEqual(len(importlib.reload(measure_after).SEARCHES), 40)
        self.assertEqual((meter.CARDS, meter_service.BUDGET_USD, meter_service.FALL_POINTS), (12, 2.0, 3.0))


class TheUnit(unittest.TestCase):
    def test_it_runs_as_the_ai_layer_after_the_nights_work_and_writes_its_own_folder(self) -> None:
        server = ROOT / "deployment" / "server"
        unit = (server / "picwise-meter.service").read_text(encoding="utf-8")
        self.assertIn("User=picwise-assist", unit)
        self.assertIn("EnvironmentFile=-/etc/picwise/assist.env", unit)
        self.assertIn("picwise-prepare.service picwise-itself.service", unit)
        self.assertEqual([line for line in unit.splitlines() if line.startswith("ReadWritePaths=")],
                         ["ReadWritePaths=/srv/picwise/assist/meter"])
        self.assertIn('meter_service.py" --dir /srv/picwise/assist/meter', unit)
        self.assertIn("OnCalendar=*-*-* 06:20:00 UTC", (server / "picwise-meter.timer").read_text(encoding="utf-8"))
        deploy = (server / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn('install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/meter"', deploy)
        self.assertIn("systemctl enable --now picwise-meter.timer", deploy)
        self.assertEqual(deploy.count("picwise-meter.service picwise-meter.timer"), 2)
        self.assertIn("picwise-itself.timer picwise-meter.timer > /dev/null", deploy)
        health = (server / "print_health.py").read_text(encoding="utf-8")
        self.assertIn('METER_NOTE = Path("/srv/picwise/assist/meter/day.json")', health)
        self.assertEqual(meter_service.NOTE_NAME, "day.json")
        # The site is asked on the server itself, at the address its service listens on.
        self.assertIn("--bind 127.0.0.1:8016", (server / "picwise-web.service").read_text(encoding="utf-8"))
        self.assertEqual(meter_service.SITE, "http://127.0.0.1:8016")


if __name__ == "__main__":
    unittest.main()
