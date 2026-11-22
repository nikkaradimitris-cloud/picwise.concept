"""The checks' ledger: one night into it by the rules' order, what the preparation reads,
and the order of asking (`picwise_checks.ledger`; `docs/PICWISE_CHECKS_RULES.md`).

Pinned by section: a failure cut that night and asked again on its schedule (5, 8.1);
back within 7 nights keeping its place (8.2); the brakes holding new failures of a shop,
of a kind, of the whole night, and twice running stopping the cutting (7.2 to 7.4); a
round ours recording nothing (7.1); a shop's 3 days (5.6.2); Awin's word and its stop
(5.6.3), its Proposed part and a feed over 7 days old (5.6.4) only on the owner's yes; the
first round, after which a product never asked waits and is not cut (9.3); what may enter (9.4); the
page's price and stock only where the reader is proven (5.3, 5.2, 7.5); the order of
asking (10); the ledger written and read whole (11).

Every row is local test data: fictional shops, `.invalid` hosts. Nothing is opened.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.verdicts import FAILED, GONE, NO_ANSWER, NOT_CHECKED, PASSED, REFUSED  # noqa: E402
from picwise_checks.verdicts import Row, ShopNight, Verdict  # noqa: E402

NIGHT = date(2026, 12, 1)
OK = Verdict(PASSED, by="by code")


def _rows(shop: str, count: int, *, price: float = 10.0, start: int = 0) -> dict[str, Row]:
    rows = {}
    for number in range(start, start + count):
        key = f"{shop}\x1f{number}"
        rows[key] = Row(key=key, shop=shop, product_id=str(number), address=f"https://{shop.lower()}.invalid/p/{number}",
                        title=f"Thing {number}", price=price + number, feed_stock="in stock")
    return rows


def _answered(rows: dict[str, Row]) -> dict[str, ShopNight]:
    shops: dict[str, int] = {}
    for row in rows.values():
        shops[row.shop] = shops.get(row.shop, 0) + 1
    return {shop: ShopNight(requests=count, answers=count, pages_200=count, pages_read=count)
            for shop, count in shops.items()}


# A catalogue of 2,000 products shown and not asked, so that a few cuts are not a tenth of
# the site (the whole night's brake, 7.4, which its own test meets without it).
FILLER = _rows("Filler", 2000)


def _night(ledger, night, rows, verdicts, *, shown=None, shops=None, filler=True, **kwargs):
    readings = {key: (L.Reading(page=verdict) if isinstance(verdict, Verdict) else verdict)
                for key, verdict in verdicts.items()}
    every_row = {**FILLER, **rows} if filler else rows
    every_shown = set(rows if shown is None else shown) | (set(FILLER) if filler else set())
    return L.record_night(ledger, night, every_row, readings, shops if shops is not None else _answered(rows),
                          shown=every_shown, **kwargs)


class Rules5And8FailuresAndComingBackTests(unittest.TestCase):
    def test_a_failure_is_cut_that_night_and_a_pass_is_shown(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 2)
        keys = list(rows)
        result = _night(ledger, NIGHT, rows, {keys[0]: OK, keys[1]: Verdict(FAILED, GONE)})
        self.assertEqual(result.note["cut_tonight"], 1)
        self.assertEqual(ledger.products[keys[1]].cut_on, NIGHT.isoformat())
        made = L.decisions(ledger, NIGHT, rows, shown=rows.keys())
        self.assertEqual(made["cut"], {keys[1]: GONE})

    def test_8_1_asked_again_on_its_schedule(self) -> None:
        self.assertEqual(L.due_after(NO_ANSWER, 1, NIGHT), NIGHT + timedelta(days=1))
        self.assertEqual(L.due_after(NO_ANSWER, 3, NIGHT), NIGHT + timedelta(days=1))
        self.assertEqual(L.due_after(NO_ANSWER, 4, NIGHT), NIGHT + timedelta(days=7))
        self.assertEqual(L.due_after(GONE, 1, NIGHT), NIGHT + timedelta(days=7))
        self.assertEqual(L.due_after(GONE, 2, NIGHT), NIGHT + timedelta(days=30))

    def test_8_2_back_within_seven_nights_keeps_its_place(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        key = next(iter(rows))
        _night(ledger, NIGHT, rows, {key: Verdict(FAILED, NO_ANSWER)})
        back = _night(ledger, NIGHT + timedelta(days=3), rows, {key: OK})
        self.assertEqual(back.came_back, [key])
        self.assertEqual((ledger.products[key].state, ledger.products[key].cut_on), (PASSED, ""))
        late = L.Ledger()
        _night(late, NIGHT, rows, {key: Verdict(FAILED, NO_ANSWER)})
        self.assertEqual(_night(late, NIGHT + timedelta(days=8), rows, {key: OK}).came_back, [])

    def test_not_checked_changes_nothing(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        key = next(iter(rows))
        _night(ledger, NIGHT, rows, {key: OK})
        _night(ledger, NIGHT + timedelta(days=1), rows, {key: Verdict(NOT_CHECKED, REFUSED)})
        self.assertEqual((ledger.products[key].state, ledger.products[key].passed_on), (PASSED, NIGHT.isoformat()))

    def test_7_5_a_price_far_apart_fails_the_product_where_the_reader_is_proven(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 21, price=20.0)
        keys = list(rows)
        # Twenty readings the same as the feed: the shop's reader is proven.
        _night(ledger, NIGHT, rows, {key: L.Reading(page=OK, site_price=rows[key].price, tie="code")
                                     for key in keys[:20]})
        _night(ledger, NIGHT + timedelta(days=1), rows, {keys[20]: L.Reading(page=OK, site_price=9.0, tie="code")})
        self.assertEqual((ledger.products[keys[20]].state, ledger.products[keys[20]].reason), (FAILED, "price far apart"))

    def test_7_5_a_price_far_apart_cuts_nothing_where_the_reader_is_not_proven(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1, price=20.0)
        key = next(iter(rows))
        _night(ledger, NIGHT, rows, {key: L.Reading(page=OK, site_price=9.0, tie="code")})
        self.assertEqual(ledger.products[key].state, PASSED)
        self.assertEqual(ledger.products[key].site_price, "9.00")


class Rules7BrakesTests(unittest.TestCase):
    def _shop_of_forty(self):
        ledger, rows = L.Ledger(), _rows("Alpha", 40)
        _night(ledger, NIGHT, rows, {key: OK for key in rows})
        return ledger, rows, list(rows)

    def test_7_2_a_shops_new_failures_are_held_then_cut_when_they_fail_again(self) -> None:
        ledger, rows, keys = self._shop_of_forty()
        second = NIGHT + timedelta(days=1)
        result = _night(ledger, second, rows, {key: (Verdict(FAILED, NO_ANSWER) if i < 11 else OK)
                                               for i, key in enumerate(keys)})
        self.assertEqual(result.note["held"], {"shop": 11})
        self.assertEqual(result.note["cut_tonight"], 0)
        self.assertEqual(L.decisions(ledger, second, rows, shown=rows.keys())["cut"], {})
        third = second + timedelta(days=1)
        order = L.asking_order(ledger, third, rows, shown=rows.keys())["Alpha"]
        self.assertEqual(order[:11], sorted(keys[:11]))
        again = _night(ledger, third, rows, {key: Verdict(FAILED, NO_ANSWER) for key in keys[:11]})
        self.assertEqual(again.note["cut_tonight"], 11)

    def test_7_2_a_shop_with_fewer_than_twenty_passes_is_held_for_the_owner(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 20)
        keys = list(rows)
        _night(ledger, NIGHT, rows, {key: (Verdict(FAILED, GONE) if i < 6 else OK) for i, key in enumerate(keys)})
        self.assertTrue(ledger.shops["Alpha"].owner_hold)
        self.assertEqual({ledger.products[key].held for key in keys[:6]}, {L.BY_OWNER})
        second = NIGHT + timedelta(days=1)
        _night(ledger, second, rows, {key: Verdict(FAILED, GONE) for key in keys[:6]})
        self.assertEqual({ledger.products[key].state for key in keys[:6]}, {L.HELD})
        third = second + timedelta(days=1)
        _night(ledger, third, rows, {key: Verdict(FAILED, GONE) for key in keys[:6]}, owner_cut_shops=["Alpha"])
        self.assertEqual({ledger.products[key].state for key in keys[:6]}, {FAILED})
        self.assertEqual(len(L.decisions(ledger, third, rows, shown=rows.keys())["cut"]), 6)

    def test_7_3_a_kinds_new_cuts_over_a_quarter_are_held(self) -> None:
        ledger, rows = L.Ledger(), {}
        for number in range(8):
            rows.update(_rows(f"Shop{number}", 5))
        parts = {key: "kettle" for key in rows}
        _night(ledger, NIGHT, rows, {key: OK for key in rows}, parts=parts)
        failing = [key for key in rows if key.endswith(("\x1f0", "\x1f1"))]
        result = _night(ledger, NIGHT + timedelta(days=1), rows, {key: Verdict(FAILED, GONE) for key in failing},
                        parts=parts)
        self.assertEqual(result.note["held"], {"kind": 16})
        self.assertEqual(result.note["cut_tonight"], 0)

    def test_7_4_a_night_that_would_cut_over_a_tenth_is_held_and_twice_running_stops(self) -> None:
        ledger, rows = L.Ledger(), {}
        for number in range(10):
            rows.update(_rows(f"Shop{number}", 5))
        _night(ledger, NIGHT, rows, {key: OK for key in rows}, filler=False)
        failing = [key for key in rows if key.endswith("\x1f0")]
        failing.append(next(key for key in rows if key.endswith("\x1f1")))
        first = _night(ledger, NIGHT + timedelta(days=1), rows, {key: Verdict(FAILED, GONE) for key in failing},
                       filler=False)
        self.assertTrue(first.note["night_brake"])
        self.assertEqual(first.note["held"], {"night": 11})
        second = _night(ledger, NIGHT + timedelta(days=2), rows, {key: Verdict(FAILED, GONE) for key in failing},
                        filler=False)
        self.assertTrue(second.note["stopped"])
        self.assertEqual(second.note["cut_tonight"], 0)

    def test_7_1_a_round_most_shops_did_not_answer_records_nothing(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 3)
        # Two of three shops gave no answer at all (timeouts): fewer than half answered.
        shops = {"Alpha": ShopNight(requests=3), "Beta": ShopNight(requests=2),
                 "Gamma": ShopNight(requests=5, answers=5, pages_200=5, pages_read=5)}
        result = _night(ledger, NIGHT, rows, {key: Verdict(FAILED, GONE) for key in rows}, shops=shops)
        self.assertTrue(result.note["ours"])
        self.assertEqual(ledger.products, {})


class Rules56ShopsTests(unittest.TestCase):
    def test_5_6_2_out_on_day_four_back_when_read_afresh_after_seven(self) -> None:
        # Owner, 2026-11-22: «Σε 3 μέρες» (the 14 days of 21/11 were too many).
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        blocked = {"Alpha": ShopNight(requests=5, answers=5, refused=5)}
        other = {"Beta": ShopNight(requests=1, answers=1, pages_200=1, pages_read=1)}
        for day in range(3):
            _night(ledger, NIGHT + timedelta(days=day), rows, {}, shops={**blocked, **other})
        self.assertEqual((ledger.shops["Alpha"].days, ledger.shops["Alpha"].out), (3, ""))
        _night(ledger, NIGHT + timedelta(days=3), rows, {}, shops={**blocked, **other})
        self.assertEqual(ledger.shops["Alpha"].out, "cannot be checked: refuses the bot")
        made = L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys())
        self.assertEqual(made["shops_out"], {"Alpha": "cannot be checked: refuses the bot"})
        read = {"Alpha": ShopNight(requests=1, answers=1, pages_200=1, pages_read=1), **other}
        _night(ledger, NIGHT + timedelta(days=4), rows, {}, shops=read)
        self.assertEqual((ledger.shops["Alpha"].out, ledger.shops["Alpha"].days), ("", 4))
        _night(ledger, NIGHT + timedelta(days=5), rows, {}, shops={**blocked, **other})
        self.assertEqual((ledger.shops["Alpha"].days, ledger.shops["Alpha"].out), (5, "cannot be checked: refuses the bot"))
        for day in range(6, 13):
            _night(ledger, NIGHT + timedelta(days=day), rows, {}, shops=read)
        self.assertEqual(ledger.shops["Alpha"].days, 0)

    def test_5_6_3_awin_rejected_out_many_at_once_waits(self) -> None:
        ledger, rows = L.Ledger(), {}
        for shop in ("A", "B", "C", "D", "E"):
            rows.update(_rows(shop, 100))
        verdicts = {key: OK for key in rows}
        awin = {"A": ("rejected", ""), "B": ("joined", ""), "C": ("notjoined", ""), "D": ("pending", ""),
                "E": ("joined", "")}
        result = _night(ledger, NIGHT, rows, verdicts, awin=awin, filler=False)
        # One shop of 100 products of 500 shown: over 5%, so it waits for the owner.
        self.assertTrue(result.note["awin"]["waits"])
        self.assertEqual(ledger.shops["A"].out, "")
        self.assertEqual({name: shop.out for name, shop in ledger.shops.items() if shop.out}, {})

    def test_5_6_3_a_small_rejection_puts_the_shop_out_and_joining_brings_it_back(self) -> None:
        ledger, rows = L.Ledger(), _rows("Big", 1000)
        rows.update(_rows("Small", 10))
        awin = {"Big": ("joined", ""), "Small": ("rejected", "")}
        _night(ledger, NIGHT, rows, {}, awin=awin, filler=False)
        self.assertEqual(ledger.shops["Small"].out, "Awin: rejected")
        _night(ledger, NIGHT + timedelta(days=1), rows, {}, awin={**awin, "Small": ("joined", "")}, filler=False)
        self.assertEqual(ledger.shops["Small"].out, "")

    def test_5_6_3_a_name_written_otherwise_is_matched_and_one_not_held_is_not_judged(self) -> None:
        ledger, rows = L.Ledger(), _rows("Big", 1000)
        rows.update(_rows("Shopping Ads: Google & Bing", 5))
        rows.update(_rows("MONÉ UK", 5))
        awin = {"Big": ("joined", ""), "Shopping Ads: Google &amp; Bing": ("rejected", ""), "Other": ("joined", "")}
        result = _night(ledger, NIGHT, rows, {}, awin=awin, filler=False)
        self.assertEqual(ledger.shops["Shopping Ads: Google & Bing"].out, "Awin: rejected")
        self.assertEqual(ledger.shops.get("MONÉ UK", L.Shop()).out, "")
        self.assertEqual(result.note["awin"]["names_not_matched"], ["MONÉ UK"])

    def test_5_6_3_the_owners_word_lets_a_large_reading_through(self) -> None:
        ledger, rows = L.Ledger(), _rows("Big", 100)
        rows.update(_rows("Other", 100))
        result = _night(ledger, NIGHT, rows, {}, awin={"Big": ("rejected", ""), "Other": ("joined", "")}, filler=False)
        self.assertTrue(result.note["awin"]["waits"])
        self.assertEqual(ledger.shops["Big"].out, "")
        _night(ledger, NIGHT, rows, {}, awin={"Big": ("rejected", ""), "Other": ("joined", "")}, owner_awin_word=True,
               filler=False)
        self.assertEqual(ledger.shops["Big"].out, "Awin: rejected")

    def test_5_6_3_suspended_closed_or_offline_is_out_only_on_the_owners_yes(self) -> None:
        # Proposed (13.2), his yes still to come on 22/11: until it, only a rejection puts a shop out.
        rows = _rows("Big", 1000)
        for shop in ("Closed", "Paused", "Offline", "Refused"):
            rows.update(_rows(shop, 3))
        awin = {"Big": ("joined", ""), "Closed": (None, ""), "Paused": ("suspended", ""), "Offline": ("joined", "offline"),
                "Refused": ("rejected", "")}
        ledger = L.Ledger()
        result = _night(ledger, NIGHT, rows, {}, awin=awin, filler=False)
        self.assertEqual({name: shop.out for name, shop in ledger.shops.items() if shop.out}, {"Refused": "Awin: rejected"})
        self.assertEqual(result.note["awin"]["would_be_out_if_proposed"],
                         [["Closed", "Awin: in no list", 3], ["Offline", "Awin: offline", 3], ["Paused", "Awin: suspended", 3]])
        with_yes = L.Ledger()
        _night(with_yes, NIGHT, rows, {}, awin=awin, awin_closed_out=True, owner_awin_word=True, filler=False)
        self.assertEqual({name: shop.out for name, shop in with_yes.shops.items() if shop.out},
                         {"Closed": "Awin: in no list", "Offline": "Awin: offline", "Paused": "Awin: suspended",
                          "Refused": "Awin: rejected"})
        # His yes taken back: the shops it had put out are in again the next night.
        _night(with_yes, NIGHT + timedelta(days=1), rows, {}, awin=awin, filler=False)
        self.assertEqual({name: shop.out for name, shop in with_yes.shops.items() if shop.out}, {"Refused": "Awin: rejected"})

    def test_5_6_4_an_old_feed_needs_a_fresh_reading_once_the_first_round_is_over(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 2)
        keys = list(rows)
        _night(ledger, NIGHT, rows, {keys[0]: L.Reading(page=OK, site_price=10.0, tie="code"), keys[1]: OK},
               feeds={"Alpha": NIGHT - timedelta(days=10)})
        self.assertTrue(ledger.shops["Alpha"].round_over)
        made = L.decisions(ledger, NIGHT + timedelta(days=2), rows, shown=rows.keys(), old_feed_rule=True)
        self.assertEqual(made["wait"], {keys[1]: "old feed, no fresh reading"})
        self.assertEqual(made["cut"], {})
        later = L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys(), old_feed_rule=True)
        self.assertEqual(set(later["wait"]), set(keys))
        # Proposed (13.2), the owner's yes still to come on 22/11: without it the rule changes nothing.
        without = L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys())
        self.assertEqual((without["wait"], without["cut"]), ({}, {}))

    def test_5_6_4_a_fresh_reading_of_stock_counts_beside_an_older_one_of_price(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        key = next(iter(rows))
        old_feed = {"Alpha": NIGHT - timedelta(days=10)}
        _night(ledger, NIGHT, rows, {key: L.Reading(page=OK, site_price=10.0, tie="code", stock="in stock")}, feeds=old_feed)
        _night(ledger, NIGHT + timedelta(days=3), rows, {key: L.Reading(page=OK, stock="in stock")}, feeds=old_feed)
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=4), rows, shown=rows.keys(), old_feed_rule=True)["wait"], {})
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=6), rows, shown=rows.keys(), old_feed_rule=True)["wait"],
                         {key: "old feed, no fresh reading"})

    def test_5_6_4_of_an_old_feed_only_a_candidate_with_a_fresh_reading_enters(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 2)
        keys = list(rows)
        _night(ledger, NIGHT, rows, {keys[0]: L.Reading(page=OK, site_price=10.0, tie="code"), keys[1]: OK},
               shown=(), feeds={"Alpha": NIGHT - timedelta(days=10)})
        self.assertEqual(L.decisions(ledger, NIGHT, rows, shown=(), candidates=keys, old_feed_rule=True)["enter"], [keys[0]])
        self.assertEqual(L.decisions(ledger, NIGHT, rows, shown=(), candidates=keys)["enter"], keys)


class Rules9WhatTheCapReadsTests(unittest.TestCase):
    def test_9_3_the_first_round_is_over_when_all_are_decided_or_after_three_days(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 3)
        keys = list(rows)
        _night(ledger, NIGHT, rows, {keys[0]: OK})
        self.assertEqual(ledger.shops["Alpha"].round_over, "")
        self.assertEqual(L.decisions(ledger, NIGHT, rows, shown=rows.keys())["cut"], {})
        _night(ledger, NIGHT + timedelta(days=2), rows, {keys[1]: OK})
        self.assertEqual(ledger.shops["Alpha"].round_over, "")
        _night(ledger, NIGHT + timedelta(days=3), rows, {})
        self.assertEqual(ledger.shops["Alpha"].round_over, (NIGHT + timedelta(days=3)).isoformat())
        made = L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys())
        # No check of it failed: it is not cut, it waits at the cap's gate until asked (9.3, 9.4).
        self.assertEqual(made["wait"], {keys[2]: "never checked"})
        self.assertEqual(made["cut"], {})

    def test_9_3_a_shop_whose_products_were_refused_keeps_its_three_days(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 4)
        refused = {key: Verdict(NOT_CHECKED, REFUSED) for key in rows}
        _night(ledger, NIGHT, rows, refused)
        self.assertEqual(ledger.shops["Alpha"].round_over, "")
        self.assertEqual(L.decisions(ledger, NIGHT, rows, shown=rows.keys())["wait"], {})
        _night(ledger, NIGHT + timedelta(days=3), rows, refused)
        made = L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys())
        self.assertEqual((set(made["wait"]), set(made["wait"].values())), (set(rows), {"never checked"}))

    def test_9_3_not_passed_in_thirty_nights(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        key = next(iter(rows))
        _night(ledger, NIGHT, rows, {key: OK})
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=29), rows, shown=rows.keys())["wait"], {})
        late = L.decisions(ledger, NIGHT + timedelta(days=30), rows, shown=rows.keys())
        self.assertEqual((late["wait"], late["cut"]), ({key: "not passed in 30 nights"}, {}))
        # Named a candidate by the cap, it may enter again only once it has passed afresh.
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=31), rows, shown=(), candidates=[key])["enter"], [])
        _night(ledger, NIGHT + timedelta(days=31), rows, {key: OK}, shown=())
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=31), rows, shown=(), candidates=[key])["enter"], [key])

    def test_9_4_only_a_candidate_that_passed_may_enter(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 3)
        keys = list(rows)
        _night(ledger, NIGHT, rows, {keys[0]: OK, keys[1]: Verdict(FAILED, GONE)}, shown=())
        made = L.decisions(ledger, NIGHT, rows, shown=(), candidates=keys)
        self.assertEqual(made["enter"], [keys[0]])
        self.assertEqual(made["cut"], {keys[1]: GONE})


class Rules53And52ProvenReaderTests(unittest.TestCase):
    def _night_of_prices(self, same: int, *, reader_pages: bool = False):
        ledger, rows = L.Ledger(), _rows("Alpha", 20)
        readings = {}
        for index, key in enumerate(rows):
            feed = rows[key].price
            readings[key] = L.Reading(page=OK, site_price=feed if index < same else round(feed * 1.09, 2), tie="code",
                                      stock="in stock" if index < same else "sold out")
        shops = {"Alpha": ShopNight(requests=20, answers=20, pages_200=20, pages_read=20)} if reader_pages else \
            {"Alpha": ShopNight(catalogue_read=True)}
        _night(ledger, NIGHT, rows, readings, shops=shops)
        return ledger, rows

    def test_the_pages_price_where_seven_in_ten_agree(self) -> None:
        ledger, rows = self._night_of_prices(14)
        made = L.decisions(ledger, NIGHT, rows, shown=rows.keys())
        self.assertEqual(len(made["prices"]), 6)

    def test_no_price_changes_where_the_reader_is_not_proven(self) -> None:
        ledger, rows = self._night_of_prices(13)
        self.assertEqual(L.decisions(ledger, NIGHT, rows, shown=rows.keys())["prices"], {})

    def test_a_reading_of_an_older_feed_price_is_old(self) -> None:
        ledger, rows = self._night_of_prices(14)
        changed = {key: Row(**{**row.__dict__, "price": (row.price or 0) + 1}) for key, row in rows.items()}
        self.assertEqual(L.decisions(ledger, NIGHT, changed, shown=rows.keys())["prices"], {})

    def test_5_2_a_page_readers_stock_only_where_proven(self) -> None:
        ledger, rows = self._night_of_prices(14, reader_pages=True)
        made = L.decisions(ledger, NIGHT, rows, shown=rows.keys())
        self.assertEqual(set(state for state, _on in made["stock"].values()), {"in stock", "sold out"})
        self.assertEqual(len(made["stock"]), 20)
        shopify, rows = self._night_of_prices(14)
        self.assertEqual(L.decisions(shopify, NIGHT, rows, shown=rows.keys())["stock"], {})


class Rules10OrderOfAskingTests(unittest.TestCase):
    def test_the_tiers(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 30)
        keys = list(rows)
        _night(ledger, NIGHT, rows, {keys[0]: Verdict(FAILED, NO_ANSWER), keys[1]: OK, keys[2]: OK})
        tonight = NIGHT + timedelta(days=1)
        changed = dict(rows)
        changed[keys[2]] = Row(**{**rows[keys[2]].__dict__, "price": 99.0})
        candidate = Row(key="Alpha\x1fnew", shop="Alpha", product_id="new", address="https://alpha.invalid/p/new")
        changed[candidate.key] = candidate
        order = L.asking_order(ledger, tonight, changed, shown=rows.keys(), candidates=[candidate.key])["Alpha"]
        self.assertEqual(order[:3], [keys[0], keys[2], candidate.key])
        never = order[3:3 + 25]
        self.assertEqual(never[0], keys[3])
        self.assertEqual(order[-1], keys[1])
        self.assertEqual(len(order), 31)

    def test_a_failed_product_not_due_is_not_asked(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        key = next(iter(rows))
        _night(ledger, NIGHT, rows, {key: Verdict(FAILED, GONE)})
        self.assertEqual(L.asking_order(ledger, NIGHT + timedelta(days=1), rows, shown=()), {})
        self.assertEqual(L.asking_order(ledger, NIGHT + timedelta(days=7), rows, shown=())["Alpha"], [key])


class Rules11TheLedgerTests(unittest.TestCase):
    def test_written_and_read_whole(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 3)
        keys = list(rows)
        _night(ledger, NIGHT, rows, {keys[0]: OK, keys[1]: Verdict(FAILED, GONE),
                                     keys[2]: L.Reading(page=OK, site_price=12.0, tie="code")})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / L.LEDGER_NAME
            L.save(ledger, path)
            again = L.load(path)
        self.assertEqual(again.products, ledger.products)
        self.assertEqual(again.shops, ledger.shops)
        self.assertEqual(again.nights, ledger.nights)
        self.assertEqual(L.load(Path("/nonexistent/ledger.json.gz")).products, {})


if __name__ == "__main__":
    unittest.main()
