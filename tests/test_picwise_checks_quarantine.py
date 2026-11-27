"""The quarantine of the shops that cannot be checked (the checks' rules 23.10; owner, 2026-11-27:
«Τα καταστήματα που είναι προβληματικά μπαίνουν σε καραντίνα η καραντίνα έχει δύο τύπους αυτά που
δεν τα ελέγχονται γιατί έχουν κάποιο τεχνικό θέμα και αυτά που δεν επιτρέπουν τα bot», then
«συμφωνώ με αυτά»).

Pinned:

- the two kinds by why: the shops that do not let the bot in (they refuse it, robots.txt forbids or
  refuses, a crawl-delay over 60 s) and those with a technical matter (no address of their own,
  pages not read, nothing that could be asked);
- a shop the round had time for that answered nothing, nor said to come back, cannot be checked: a
  day of its technical quarantine, out on its day 4 as every shop that cannot be checked;
- a shop out of the quarantine of the shops that do not let the bot in is asked again once a week,
  nothing of it asked on the other nights; a technical one, each night as before; either is back
  the first night it can be checked;
- the night's note names every shop in quarantine, those not asked tonight too, with its kind;
- the bot tells why a shop's asking was not whole: the shop said to come back, it answered nothing,
  the round had not the time, an error (the health run's stable day reads it:
  `tests/test_picwise_server_health.py`).

Every row is local test data: fictional shops, `.invalid` hosts. Nothing is opened.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import shop_checks_bot as bot  # noqa: E402

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.verdicts import (  # noqa: E402
    BOTS_NOT_ALLOWED, NOTHING_ASKED, TECHNICAL, Row, ShopNight, quarantine_kind,
)

NIGHT = date(2026, 12, 1)
REFUSES = ShopNight(requests=20, answers=20, refused=20)
FINE = ShopNight(requests=10, answers=10, pages_200=10, pages_read=10)
# A robots.txt that sends elsewhere: one request, one answer, nothing asked after it.
NOTHING = ShopNight(requests=1, answers=1)


def _rows(shop: str, count: int) -> dict[str, Row]:
    return {f"{shop}\x1f{number}": Row(key=f"{shop}\x1f{number}", shop=shop, product_id=str(number),
                                         address=f"https://{shop.lower()}.invalid/p/{number}", title=f"Thing {number}",
                                         price=10.0 + number, feed_stock="in stock")
            for number in range(count)}


def _night(ledger: L.Ledger, night: date, shop_nights: dict[str, ShopNight], *, nothing_asked=()) -> L.Night:
    rows = {}
    for name in shop_nights:
        rows.update(_rows(name, 2))
    # A round of one shop only would be ours (7.1): another shop that answers keeps it the shops'.
    others = {f"Other {number}": FINE for number in range(6)}
    for name in others:
        rows.update(_rows(name, 2))
    return L.record_night(ledger, night, rows, {}, {**shop_nights, **others}, shown=set(rows),
                          nothing_asked=nothing_asked)


class KindsTests(unittest.TestCase):
    def test_the_two_kinds_by_why(self) -> None:
        for why in ("refuses the bot", "robots.txt refused", "robots.txt disallows its product pages",
                    "crawl-delay over 60 s"):
            self.assertEqual(quarantine_kind(why), BOTS_NOT_ALLOWED, why)
        for why in ("no address of its own", "its pages are not read", NOTHING_ASKED, ""):
            self.assertEqual(quarantine_kind(why), TECHNICAL, why)


class LedgerTests(unittest.TestCase):
    def test_a_shop_that_answered_nothing_is_in_technical_quarantine_and_out_on_day_4(self) -> None:
        ledger = L.Ledger()
        for day in range(4):
            note = _night(ledger, NIGHT + timedelta(days=day), {"Quiet": NOTHING}, nothing_asked={"Quiet"}).note
        self.assertEqual(note["cannot_be_checked"]["Quiet"], [NOTHING_ASKED, 4, TECHNICAL])
        self.assertEqual(ledger.shops["Quiet"].out, f"cannot be checked: {NOTHING_ASKED}")
        self.assertEqual(ledger.shops["Quiet"].out_on, (NIGHT + timedelta(days=3)).isoformat())
        self.assertEqual(note["quarantine"]["Quiet"], [NOTHING_ASKED, 4, TECHNICAL, True, ""])
        # The same night without the bot's word: it could be checked, as before.
        ledger = L.Ledger()
        note = _night(ledger, NIGHT, {"Quiet": NOTHING}).note
        self.assertNotIn("Quiet", note["cannot_be_checked"])
        self.assertNotIn("Quiet", note["quarantine"])

    def test_a_shop_that_does_not_let_the_bot_in_rests_but_on_its_weeks_night(self) -> None:
        ledger = L.Ledger()
        for day in range(4):
            _night(ledger, NIGHT + timedelta(days=day), {"Walled": REFUSES})
        went = NIGHT + timedelta(days=3)
        shop = ledger.shops["Walled"]
        self.assertTrue(shop.out.startswith("cannot be checked"))
        self.assertEqual(shop.out_on, went.isoformat())
        rows = _rows("Walled", 3)
        for later in range(1, 7):
            self.assertTrue(L.resting(shop, went + timedelta(days=later)), later)
            self.assertEqual(L.asking_order(ledger, went + timedelta(days=later), rows, shown=()), {}, later)
        self.assertFalse(L.resting(shop, went + timedelta(days=7)))
        order = L.asking_order(ledger, went + timedelta(days=7), rows, shown=())
        self.assertEqual(len(order["Walled"]), 3)
        # Not asked on a resting night, it stays in quarantine, named with the night it is asked again.
        note = _night(ledger, went + timedelta(days=2), {}).note
        self.assertEqual(note["quarantine"]["Walled"],
                         ["refuses the bot", 4, BOTS_NOT_ALLOWED, True, (went + timedelta(days=7)).isoformat()])
        # Asked on its week's night and it lets the bot in: back.
        _night(ledger, went + timedelta(days=7), {"Walled": FINE})
        self.assertEqual((shop.out, shop.out_on), ("", ""))
        self.assertFalse(L.resting(shop, went + timedelta(days=8)))

    def test_a_technical_shop_out_is_asked_each_night(self) -> None:
        ledger = L.Ledger()
        for day in range(4):
            _night(ledger, NIGHT + timedelta(days=day), {"Quiet": NOTHING}, nothing_asked={"Quiet"})
        rows = _rows("Quiet", 3)
        for later in range(4, 11):
            self.assertFalse(L.resting(ledger.shops["Quiet"], NIGHT + timedelta(days=later)))
            self.assertIn("Quiet", L.asking_order(ledger, NIGHT + timedelta(days=later), rows, shown=()))

    def test_a_shop_out_before_the_quarantine_is_asked_and_its_night_kept(self) -> None:
        ledger = L.Ledger()
        ledger.shops["Walled"] = L.Shop(days=6, why="refuses the bot", out="cannot be checked: refuses the bot")
        self.assertFalse(L.resting(ledger.shops["Walled"], NIGHT))
        self.assertIn("Walled", L.asking_order(ledger, NIGHT, _rows("Walled", 2), shown=()))
        _night(ledger, NIGHT, {"Walled": REFUSES})
        self.assertEqual(ledger.shops["Walled"].out_on, NIGHT.isoformat())
        self.assertTrue(L.resting(ledger.shops["Walled"], NIGHT + timedelta(days=1)))


class NotWholeTests(unittest.TestCase):
    def _result(self, answers: int, stopped: str = "") -> bot.ShopResult:
        return bot.ShopResult(FINE, {str(number): None for number in range(answers)}, stopped)

    def test_why_a_shops_asking_was_not_whole(self) -> None:
        late = 600.0
        self.assertEqual(bot.not_whole_why(self._result(5, "429: asked to come back later"), 9, whole_round=True,
                                           late=late), bot.NOT_WHOLE_SAID_LATER)
        self.assertEqual(bot.not_whole_why(self._result(5, "error: boom"), 9, whole_round=True, late=late),
                         bot.NOT_WHOLE_ERROR)
        self.assertEqual(bot.not_whole_why(self._result(0), 9, whole_round=True, late=late), NOTHING_ASKED)
        # Nothing answered, but the round had not the time for it: ours.
        self.assertEqual(bot.not_whole_why(self._result(0), 9, whole_round=False, late=late), bot.NOT_WHOLE_NO_TIME)
        self.assertEqual(bot.not_whole_why(self._result(0), 9, whole_round=True, late=2 * 3600.0),
                         bot.NOT_WHOLE_NO_TIME)
        self.assertEqual(bot.not_whole_why(self._result(5), 9, whole_round=False, late=late), bot.NOT_WHOLE_NO_TIME)
        self.assertEqual(set(bot.NOT_WHOLE_THE_SHOPS), {bot.NOT_WHOLE_SAID_LATER, NOTHING_ASKED})

    def test_a_rounds_shops_not_whole_and_why(self) -> None:
        results = {"Quiet": self._result(0), "Busy": self._result(3, "429: asked to come back later"),
                   "Done": self._result(4)}
        asked = bot.Round(results=results, ordered={"Quiet": 4, "Busy": 9, "Done": 4}, seconds={}, late={},
                          threads=1, processes=0, hours=21.0)
        self.assertEqual(asked.complete(), {"Done"})
        self.assertEqual(asked.not_whole(), {"Quiet": NOTHING_ASKED, "Busy": bot.NOT_WHOLE_SAID_LATER})

    def test_the_reports_reasons_match_the_bots(self) -> None:
        import print_health

        self.assertEqual(set(print_health.NOT_WHOLE_THE_SHOPS), set(bot.NOT_WHOLE_THE_SHOPS))
        self.assertEqual((print_health.QUARANTINE_BOTS, print_health.QUARANTINE_TECHNICAL), (BOTS_NOT_ALLOWED, TECHNICAL))


if __name__ == "__main__":
    unittest.main()
