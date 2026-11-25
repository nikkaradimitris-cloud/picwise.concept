"""A pass counts for the day (the checks' rules 21; owner, 2026-11-25: «24 ώρες είναι το
σκανάρισμα και ότι προλάβει να σκανάρει.... Εάν το σύστημα κολλήσει και δεν κάνεις κανάρισμα
την επόμενη μέρα τα προϊόντα μένουν όπως έχουν πρέπει μετά την τρίτη ή την τέταρτη να
σβηστούν», then «Ναι συμφωνώ» to the rule put to him).

Pinned, with the rule of how many of a shop's products pass on:

- a shop the bot asked whole tonight (nothing stopped it, and it was asked all it had, or
  all day in a round that asked all day) shows only what passed tonight;
- while a shop's asking is not whole (the server or the bot stuck, the shop stopped
  answering), its products stay as they were up to three nights after their pass, then wait;
- a product left out on a whole night stays out on a stuck night after it;
- a round that is ours (7.1) marks no shop whole, a shop that cannot be checked is never whole,
  and a ledger written before the rule keeps the three nights until its shop's first whole night;
- the decisions name each pass's night, and the preparation, on a morning with no newer
  night, lets a pass count three nights and no more, however old the file (never "nothing
  applied", as the decisions of the three nights' rule over two nights old are);
- the bot tells a whole round from a stuck one by the hours it asked, kept across a round
  started again, never the hours it was down (the health run's lines on it are in
  `tests/test_picwise_server_health.py`).

Every row is local test data: fictional shops, `.invalid` hosts. Nothing is opened.
"""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import shop_checks_bot as bot  # noqa: E402

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.verdicts import PASSED, Row, ShopNight, Verdict  # noqa: E402
from picwise_providers import checks_applied as applied  # noqa: E402
from picwise_providers.catalogue_cap import row_key  # noqa: E402
from picwise_providers.catalogue_memory import product_key  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

NIGHT = date(2026, 12, 1)
OK = Verdict(PASSED, by="by code")
PRODUCT_PAGE = (
    '<script type="application/ld+json">{"@type": "Product", "name": "Zentra Kettle", "sku": "ZK-1", '
    '"offers": {"@type": "Offer", "price": "24.99", "priceCurrency": "GBP", "availability": "InStock"}}</script>'
)


def _rows(shop: str, count: int) -> dict[str, Row]:
    return {f"{shop}\x1f{number}": Row(key=f"{shop}\x1f{number}", shop=shop, product_id=str(number),
                                         address=f"https://{shop.lower()}.invalid/p/{number}", title=f"Thing {number}",
                                         price=10.0 + number, feed_stock="in stock")
            for number in range(count)}


def _night(ledger: L.Ledger, night: date, rows: dict[str, Row], passed, *, whole=(), checkable: bool = True) -> dict:
    """One night: the keys in `passed` pass; `whole`: the shops the bot asked whole."""
    shops = {row.shop for row in rows.values()}
    shop_night = (ShopNight(requests=10, answers=10, pages_200=10, pages_read=10) if checkable
                  else ShopNight(robots="refused", requests=1, answers=1, refused=1))
    L.record_night(ledger, night, rows, {key: L.Reading(page=OK) for key in passed},
                   {shop: shop_night for shop in shops}, shown=set(rows), complete=whole)
    return L.decisions(ledger, night, rows, shown=rows.keys(), pass_nights=L.PASS_NIGHTS_DAY)


class Rule21APassCountsForTheDayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger, self.rows = L.Ledger(), _rows("Alpha", 3)
        self.keys = list(self.rows)
        _night(self.ledger, NIGHT, self.rows, self.keys, whole={"Alpha"})
        self.ledger.shops["Alpha"].round_over = NIGHT.isoformat()

    def test_a_shop_asked_whole_shows_only_what_passed_tonight(self) -> None:
        # The bot reached two of the three tonight, asking all day: the third waits at once.
        made = _night(self.ledger, NIGHT + timedelta(days=1), self.rows, self.keys[:2], whole={"Alpha"})
        self.assertEqual(made["wait"], {self.keys[2]: L.NOT_PASSED_TODAY})
        self.assertEqual(L.NOT_PASSED_TODAY, applied.A_DAY)
        self.assertEqual(self.ledger.shops["Alpha"].complete_on, (NIGHT + timedelta(days=1)).isoformat())

    def test_while_its_shop_is_not_asked_whole_a_product_stays_up_to_three_nights_then_waits(self) -> None:
        for later in (1, 2):
            self.assertEqual(_night(self.ledger, NIGHT + timedelta(days=later), self.rows, ())["wait"], {}, later)
        made = _night(self.ledger, NIGHT + timedelta(days=3), self.rows, ())
        self.assertEqual(made["wait"], {key: L.NOT_PASSED_IN_THREE for key in self.keys})
        # Back the night it passes, as ever.
        self.assertEqual(_night(self.ledger, NIGHT + timedelta(days=4), self.rows, self.keys, whole={"Alpha"})["wait"], {})

    def test_one_left_out_on_a_whole_night_stays_out_on_a_stuck_night_after(self) -> None:
        _night(self.ledger, NIGHT + timedelta(days=1), self.rows, self.keys[:2], whole={"Alpha"})
        made = _night(self.ledger, NIGHT + timedelta(days=2), self.rows, ())
        # The two passed on the whole night stay as they were; the third, left out that night, waits.
        self.assertEqual(made["wait"], {self.keys[2]: L.NOT_PASSED_TODAY})

    def test_a_round_that_is_ours_marks_no_shop_whole(self) -> None:
        tonight = NIGHT + timedelta(days=1)
        quiet = {f"Quiet {number}": ShopNight(requests=1) for number in range(5)}
        night = L.record_night(self.ledger, tonight, self.rows, {}, {**quiet, "Alpha": ShopNight(requests=1)},
                               shown=set(self.rows), complete={"Alpha"})
        self.assertTrue(night.note.get("ours"))
        self.assertEqual(self.ledger.shops["Alpha"].complete_on, NIGHT.isoformat())
        made = L.decisions(self.ledger, tonight, self.rows, shown=self.rows.keys(), pass_nights=L.PASS_NIGHTS_DAY)
        self.assertEqual(made["wait"], {})

    def test_a_shop_that_cannot_be_checked_tonight_is_never_whole(self) -> None:
        made = _night(self.ledger, NIGHT + timedelta(days=1), self.rows, (), whole={"Alpha"}, checkable=False)
        self.assertEqual(self.ledger.shops["Alpha"].complete_on, NIGHT.isoformat())
        self.assertEqual(made["wait"], {})

    def test_a_ledger_written_before_the_rule_keeps_three_nights_until_a_whole_night(self) -> None:
        self.ledger.shops["Alpha"].complete_on = ""
        for later in (1, 2):
            made = L.decisions(self.ledger, NIGHT + timedelta(days=later), self.rows, shown=self.rows.keys(),
                               pass_nights=L.PASS_NIGHTS_DAY)
            self.assertEqual(made["wait"], {}, later)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / L.LEDGER_NAME
            L.save(self.ledger, path)
            payload = json.loads(gzip.open(path, "rt", encoding="utf-8").read())
            for shop in payload["shops"].values():
                shop.pop("complete_on", None)
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(payload, handle)
            self.assertEqual(L.load(path).shops["Alpha"].complete_on, "")

    def test_the_decisions_name_each_passs_night(self) -> None:
        tonight = NIGHT + timedelta(days=1)
        made = _night(self.ledger, tonight, self.rows, self.keys[:1])
        # Not whole tonight: the two not asked stay on their pass of the night before.
        self.assertEqual(made["passed_on"], {NIGHT.isoformat(): sorted(self.keys[1:]),
                                             tonight.isoformat(): self.keys[:1]})
        # Not named without the day's rule.
        self.assertNotIn("passed_on", L.decisions(self.ledger, tonight, self.rows, shown=self.rows.keys(),
                                                  pass_nights=L.PASS_NIGHTS_SCANNED))

    def test_a_candidate_enters_on_tonights_pass_and_is_named_with_it(self) -> None:
        extra = _rows("Beta", 1)
        key = next(iter(extra))
        every = {**self.rows, **extra}
        tonight = NIGHT + timedelta(days=1)
        L.record_night(self.ledger, tonight, every, {key: L.Reading(page=OK), **{k: L.Reading(page=OK) for k in self.keys}},
                       {"Alpha": ShopNight(requests=10, answers=10, pages_200=10, pages_read=10),
                        "Beta": ShopNight(requests=2, answers=2, pages_200=1, pages_read=1)},
                       shown=set(self.rows), complete={"Alpha", "Beta"})
        made = L.decisions(self.ledger, tonight, every, shown=self.rows.keys(), candidates=[key],
                           pass_nights=L.PASS_NIGHTS_DAY)
        self.assertEqual(made["enter"], [key])
        self.assertIn(key, made["passed_on"][tonight.isoformat()])


class Rule21ThePreparationOnAMorningWithNoNewerNightTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()
        self.addCleanup(applied.reset_for_tests)

    def _product(self, number: int) -> ProviderProduct:
        return ProviderProduct(
            provider_key="awin", provider_product_id=f"row-{number}", title=f"Zentra Kettle {number}", brand="Zentra",
            category_text="Home & Garden > Kitchen", product_url=f"https://alpha.invalid/p/{number}",
            image_url=f"https://alpha.invalid/i/{number}.jpg", price_text="20.99", availability_text="in stock",
            currency="GBP", raw={"merchant_name": "Alpha", "availability": "in stock"})

    def _decisions(self, keys: list[str], candidate: str) -> dict:
        return {"format": applied.DECISIONS_FORMAT, "version": 1, "night": NIGHT.isoformat(), "shops_out": {},
                "cut": {}, "wait": {}, "enter": [candidate], "prices": {}, "stock": {}, "returning": [],
                "passed": list(keys),
                "passed_on": {(NIGHT - timedelta(days=1)).isoformat(): [keys[0]], NIGHT.isoformat(): [keys[1], candidate]}}

    def test_a_pass_counts_three_nights_and_no_more_however_old_the_file(self) -> None:
        products = [self._product(1), self._product(2), self._product(3)]
        keys = [product_key(product) for product in products]
        document = self._decisions(keys[:2], keys[2])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decisions.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(document, handle)
            # The night's own morning: as decided.
            self.assertEqual(applied.load_decisions(path, today=NIGHT), (document, "read"))
            # The morning after: the pass of the night before the decisions is two nights old, still shown.
            read, status = applied.load_decisions(path, today=NIGHT + timedelta(days=1))
            self.assertEqual((read["wait"], read["enter"]), ({}, [keys[2]]))
            self.assertIn("a pass over 2 nights old waits", status)
            # Two mornings after: the first is three nights old and waits; the rest stand.
            read, _status = applied.load_decisions(path, today=NIGHT + timedelta(days=2))
            self.assertEqual((read["wait"], read["enter"], read["passed"]),
                             ({keys[0]: applied.THREE_NIGHTS}, [keys[2]], [keys[1]]))
            # Ten mornings after: read, never "too old", every pass waits and nothing enters.
            read, _status = applied.load_decisions(path, today=NIGHT + timedelta(days=10))
            self.assertEqual((sorted(read["wait"]), read["enter"]), (sorted(keys), []))
        applied.apply_checks(products, decisions=read, switch=True, today=NIGHT + timedelta(days=10), scanned=True)
        self.assertEqual(applied.unchecked_row_keys(products, row_key), frozenset(row_key(item) for item in products))
        self.assertFalse(applied.may_enter(products[2]))

    def test_decisions_without_the_nights_of_passes_over_two_nights_old_are_still_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decisions.json.gz"
            document = {"format": applied.DECISIONS_FORMAT, "night": NIGHT.isoformat(), "wait": {}}
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(document, handle)
            self.assertIsNone(applied.load_decisions(path, today=NIGHT + timedelta(days=3))[0])

    def test_the_days_waits_only_with_the_switch_on(self) -> None:
        product = self._product(1)
        key = product_key(product)
        decisions = {"format": applied.DECISIONS_FORMAT, "night": NIGHT.isoformat(), "wait": {key: applied.A_DAY}}
        applied.apply_checks([product], decisions=decisions, switch=True, today=NIGHT, scanned=True)
        self.assertEqual(applied.unchecked_row_keys([product], row_key), frozenset({row_key(product)}))
        applied.apply_checks([product], decisions=decisions, switch=True, today=NIGHT, scanned=False)
        self.assertEqual(applied.unchecked_row_keys([product], row_key), frozenset())
        self.assertEqual(applied.last_checks_note()["three_nights_left_aside"], 1)
        self.assertEqual(applied.PASS_GRACE_NIGHTS, L.PASS_NIGHTS_SCANNED)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Rule21TheBotTellsAWholeRoundTests(unittest.TestCase):
    def test_the_hours_asked_are_kept_across_a_round_started_again_never_the_hours_down(self) -> None:
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / bot.TONIGHT_TIME.format(night="2026-12-01")
            first = bot.RoundTime(path, clock)
            clock.now = 10 * 3600.0
            first.keep()
            # Down for six hours; started again, it goes on from the ten it had asked.
            clock.now = 16 * 3600.0
            second = bot.RoundTime(path, clock)
            self.assertEqual(second.before, 10 * 3600.0)
            clock.now = 25 * 3600.0
            self.assertEqual(second.seconds(), 19 * 3600.0)
            second.keep(now=True)
            self.assertEqual(json.loads(path.read_text())["seconds"], 19 * 3600.0)
            # Forgotten with the night's answers.
            bot.Tonight(Path(folder) / bot.TONIGHT.format(night="2026-12-01")).forget()
            self.assertFalse(path.exists())
        # A look keeps it in memory only.
        self.assertEqual(bot.RoundTime(None, clock).before, 0.0)

    def test_kept_every_few_minutes_not_at_every_answer(self) -> None:
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "time.json"
            time = bot.RoundTime(path, clock)
            clock.now = 60.0
            time.keep()
            self.assertFalse(path.exists())
            clock.now = bot.TIME_KEPT_EVERY + 1.0
            time.keep()
            self.assertTrue(path.exists())

    def test_a_shop_asked_whole(self) -> None:
        answered = bot.ShopResult(ShopNight(requests=3, answers=3), {"a": bot.PageAnswer(status=200),
                                                                      "b": bot.PageAnswer(status=200)})
        # Asked every product of its order: whole, whatever the round.
        self.assertTrue(bot.asked_whole(answered, 2, whole_round=False, late=0.0))
        # Not every one: whole only in a round that asked all day, from its start.
        self.assertFalse(bot.asked_whole(answered, 5, whole_round=False, late=0.0))
        self.assertTrue(bot.asked_whole(answered, 5, whole_round=True, late=0.0))
        self.assertFalse(bot.asked_whole(answered, 5, whole_round=True, late=2 * 3600.0))
        # Stopped by the shop (a 429) or an error, or asked nothing at all: never whole.
        stopped = bot.ShopResult(answered.night, answered.answers, "429: asked to come back later")
        self.assertFalse(bot.asked_whole(stopped, 2, whole_round=True, late=0.0))
        self.assertFalse(bot.asked_whole(bot.ShopResult(ShopNight(requests=1, answers=0)), 5, whole_round=True, late=0.0))

    def _run(self, *, hours_before: float) -> tuple:
        rows = {f"Kettles\x1f{n}": Row(key=f"Kettles\x1f{n}", shop="Kettles", product_id=str(n),
                                       address=f"https://kettles.invalid/p/{n}", title="Zentra Kettle", price=24.99,
                                       skus=frozenset({"ZK-1"})) for n in range(1, 4)}
        page = PRODUCT_PAGE.encode()
        now = {"t": 0.0}

        def fetch(url: str, limit: int) -> bot.Answer:
            now["t"] += 1.0
            path = url.split(".invalid", 1)[1]
            return bot.Answer(404) if path == "/robots.txt" else bot.Answer(200, "text/html", page)

        def sleep(seconds: float) -> None:
            now["t"] += seconds

        def clock() -> float:
            return now["t"]

        ledger = L.Ledger()
        ledger.shops["Kettles"] = L.Shop(round_over="2026-11-28", complete_on="2026-11-30")
        for key in rows:
            ledger.products[key] = L.Product(shop="Kettles", state=PASSED, asked="2026-11-30", passed_on="2026-11-30")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "time.json"
            path.write_text(json.dumps({"seconds": hours_before * 3600.0}))
            # The deadline falls after the first product: the other two are not asked tonight.
            night, made = bot.run(rows, shown=set(rows), parts={}, shared_ids=set(), candidates=[], ledger=ledger,
                                  night=NIGHT, fetch=fetch, sleep=sleep, clock=clock, deadline=6.0, workers=1,
                                  pause=3.0, awin=None, feeds={}, owner_cut_shops=[], owner_awin_word=False,
                                  say=lambda _line: None, scanned=True, round_time=bot.RoundTime(path, clock))
        return night, made, ledger, sorted(rows)

    def test_a_round_that_asked_all_day_lets_the_products_not_reached_wait(self) -> None:
        night, made, ledger, keys = self._run(hours_before=21.0)
        rule = night.note["shop_rule"]
        self.assertEqual((rule["pass_nights"], rule["whole_round"], rule["asked_whole"]), (L.PASS_NIGHTS_DAY, True, 1))
        self.assertEqual(ledger.shops["Kettles"].complete_on, NIGHT.isoformat())
        self.assertEqual(made["wait"], {key: L.NOT_PASSED_TODAY for key in keys[1:]})
        lines: list[str] = []
        bot.print_night(night.note, made, ledger, lines.append)
        self.assertIn("a pass counts for the day it was made, 3 nights while its shop is not asked whole "
                      "(the round asked 21.0 hours, all day; 1 shops asked whole)", "\n".join(lines))

    def test_a_round_stuck_for_hours_keeps_them_as_they_were(self) -> None:
        night, made, ledger, _keys = self._run(hours_before=8.0)
        rule = night.note["shop_rule"]
        self.assertEqual((rule["whole_round"], rule["asked_whole"], rule["not_whole"]), (False, 0, ["Kettles"]))
        self.assertEqual(ledger.shops["Kettles"].complete_on, "2026-11-30")
        self.assertEqual(made["wait"], {})


if __name__ == "__main__":
    unittest.main()
