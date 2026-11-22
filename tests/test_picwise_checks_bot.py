"""The checks' bot asks each shop as the rules say, and only fetches
(`deployment/bot/shop_checks_bot.py`; `docs/PICWISE_CHECKS_RULES.md`, section 4).

Pinned: only the shop's own address, its robots.txt first (a refusal, a disallow, a
crawl-delay over 60 s each end the shop's night); one request at a time, at least 3 s
apart; a Shopify shop read by its catalogue and a product missing from a catalogue read
whole asked at its `.js`; any other shop by each product's page; a product that did not
answer asked once more at the end of the round; a 429 ends the shop's night; a challenge
page is a refusal; nothing asked past the deadline; a row on another site not asked; and
a night run end to end into the ledger and the decisions.

Every shop is fictional, on `.invalid` hosts; the fetch is a local stand-in: nothing is
opened.
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import shop_checks_bot as bot  # noqa: E402

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.verdicts import FAILED, GONE, NO_ANSWER, NOT_CHECKED, PASSED, Row  # noqa: E402

PRODUCT_PAGE = (
    '<script type="application/ld+json">{"@type": "Product", "name": "Zentra Kettle", "sku": "ZK-1", '
    '"offers": {"@type": "Offer", "price": "%s", "priceCurrency": "GBP", "availability": "InStock"}}</script>'
)


class Shop:
    """A fictional shop: answers by path; records what was asked and the clock."""

    def __init__(self, answers: dict, *, clock_step: float = 0.0) -> None:
        self.answers = answers
        self.asked: list[str] = []
        self.now = 0.0
        self.sleeps: list[float] = []
        self.step = clock_step

    def fetch(self, url: str, limit: int) -> bot.Answer:
        path = url.split(".invalid", 1)[1]
        self.asked.append(path)
        self.now += self.step
        answer = self.answers.get(path, bot.Answer(404))
        if isinstance(answer, list):
            return answer.pop(0) if len(answer) > 1 else answer[0]
        return answer

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def clock(self) -> float:
        return self.now


def _row(number: int, *, host: str = "kettles.invalid", path: str | None = None, price: float = 24.99,
         handle: str = "") -> Row:
    address = f"https://{host}{path or f'/p/{number}'}"
    return Row(key=f"Kettles\x1f{number}", shop="Kettles", product_id=str(number), address=address,
               title="Zentra Kettle", price=price, skus=frozenset({"ZK-1"}), handle=handle)


def _ask(shop: Shop, rows: list[Row], *, deadline: float = 10_000.0) -> bot.ShopResult:
    return bot.ask_shop(rows, fetch=shop.fetch, sleep=shop.sleep, clock=shop.clock, deadline=deadline)


class Rules4HowAShopIsAskedTests(unittest.TestCase):
    def test_a_product_page_read_and_three_seconds_between_requests(self) -> None:
        shop = Shop({"/robots.txt": bot.Answer(404), "/products.json?limit=250&page=1": bot.Answer(404),
                     "/p/1": bot.Answer(200, "text/html", (PRODUCT_PAGE % "24.99").encode(),
                                        final_url="https://kettles.invalid/p/1"),
                     "/p/2": bot.Answer(404)})
        result = _ask(shop, [_row(1), _row(2)])
        self.assertEqual(shop.asked, ["/robots.txt", "/products.json?limit=250&page=1", "/p/1", "/p/2"])
        self.assertTrue(all(seconds >= 3.0 for seconds in shop.sleeps))
        self.assertEqual(len(shop.sleeps), 3)
        self.assertTrue(result.answers["Kettles\x1f1"].read.found)
        readings = bot.judge({row.key: row for row in (_row(1), _row(2))}, result)
        self.assertEqual(readings["Kettles\x1f1"].page.state, PASSED)
        self.assertEqual(readings["Kettles\x1f1"].site_price, 24.99)
        self.assertEqual(readings["Kettles\x1f2"].page.reason, GONE)

    def test_robots_refused_disallowed_or_too_slow_end_the_shops_night(self) -> None:
        refused = _ask(Shop({"/robots.txt": bot.Answer(403)}), [_row(1)])
        self.assertEqual((refused.night.robots, refused.night.refused), ("refused", 1))
        shop = Shop({"/robots.txt": bot.Answer(200, "text/plain", b"User-agent: *\nDisallow: /p/\n")})
        disallowed = _ask(shop, [_row(1)])
        self.assertEqual(disallowed.night.robots, "disallowed")
        self.assertEqual(shop.asked, ["/robots.txt"])
        slow = _ask(Shop({"/robots.txt": bot.Answer(200, "text/plain", b"User-agent: *\nCrawl-delay: 61\n")}), [_row(1)])
        self.assertEqual(slow.night.crawl_delay, 61.0)
        self.assertEqual(slow.answers, {})

    def test_an_awin_address_alone_is_no_address_of_its_own(self) -> None:
        result = _ask(Shop({}), [_row(1, host="www.awin1.invalid")])
        self.assertFalse(result.night.own_address)

    def test_a_shopify_catalogue_read_whole_and_a_missing_product_asked_at_its_js(self) -> None:
        catalogue = {"products": [{"handle": "zentra-kettle", "title": "Zentra Kettle",
                                   "variants": [{"id": 111, "sku": "ZK-1", "price": "24.99", "available": True}]}]}
        shop = Shop({"/robots.txt": bot.Answer(404),
                     "/products.json?limit=250&page=1": bot.Answer(200, "application/json", json.dumps(catalogue).encode()),
                     "/products/old-kettle.js": bot.Answer(404)})
        rows = [_row(1, path="/products/zentra-kettle", handle="zentra-kettle"),
                _row(2, path="/products/old-kettle", handle="old-kettle")]
        result = _ask(shop, rows)
        self.assertTrue(result.night.catalogue_read)
        # No `.js` of that name: asked at its own address before it is called gone (rules 5.1).
        self.assertEqual(shop.asked, ["/robots.txt", "/products.json?limit=250&page=1", "/products/old-kettle.js",
                                      "/products/old-kettle"])
        self.assertEqual(result.night.requests, 4)
        readings = bot.judge({row.key: row for row in rows}, result)
        self.assertEqual(readings["Kettles\x1f1"].page.state, PASSED)
        self.assertEqual(readings["Kettles\x1f1"].site_price, 24.99)
        self.assertEqual(readings["Kettles\x1f2"].page.reason, GONE)

    def test_a_shopify_product_the_shop_renamed_is_found_at_its_own_address_not_called_gone(self) -> None:
        # The feed still names the old address: the shop's site sends a visitor on to the new
        # one, while the old name's `.js` answers 404. The same product, by its code: passed.
        catalogue = {"products": [{"handle": "zentra-kettle-2", "title": "Zentra Kettle",
                                   "variants": [{"id": 111, "sku": "ZK-1", "price": "24.99", "available": True}]}]}
        page = (PRODUCT_PAGE % "24.99").encode()
        shop = Shop({"/robots.txt": bot.Answer(404),
                     "/products.json?limit=250&page=1": bot.Answer(200, "application/json", json.dumps(catalogue).encode()),
                     "/products/zentra-kettle.js": bot.Answer(404),
                     "/products/zentra-kettle": bot.Answer(200, "text/html", page,
                                                           final_url="https://kettles.invalid/products/zentra-kettle-2"),
                     "/products/other.js": bot.Answer(404),
                     "/products/other": bot.Answer(200, "text/html", b"<html><title>Kettles</title></html>",
                                                   final_url="https://kettles.invalid/")})
        rows = [_row(1, path="/products/zentra-kettle", handle="zentra-kettle"),
                _row(2, path="/products/other", handle="other")]
        result = _ask(shop, rows)
        readings = bot.judge({row.key: row for row in rows}, result)
        self.assertEqual((readings["Kettles\x1f1"].page.state, readings["Kettles\x1f1"].page.by), (PASSED, "by code"))
        # Sent to the home page instead: moved, a failure as before.
        self.assertEqual((readings["Kettles\x1f2"].page.state, readings["Kettles\x1f2"].page.reason), (FAILED, "moved"))

    def test_no_answer_is_asked_once_more_at_the_end(self) -> None:
        page = bot.Answer(200, "text/html", (PRODUCT_PAGE % "24.99").encode(), final_url="https://kettles.invalid/p/1")
        shop = Shop({"/robots.txt": bot.Answer(404), "/p/1": [bot.Answer(error="timeout"), page],
                     "/p/2": [bot.Answer(503), bot.Answer(503)]})
        result = _ask(shop, [_row(1), _row(2)])
        self.assertEqual(shop.asked.count("/p/1"), 2)
        readings = bot.judge({row.key: row for row in (_row(1), _row(2))}, result)
        self.assertEqual(readings["Kettles\x1f1"].page.state, PASSED)
        self.assertEqual(readings["Kettles\x1f2"].page.reason, NO_ANSWER)

    def test_a_429_ends_the_shops_night_and_a_challenge_is_a_refusal(self) -> None:
        shop = Shop({"/robots.txt": bot.Answer(404), "/p/1": bot.Answer(429), "/p/2": bot.Answer(200)})
        result = _ask(shop, [_row(1), _row(2)])
        self.assertNotIn("/p/2", shop.asked)
        self.assertIn("429", result.stopped)
        challenge = bot.Answer(503, "text/html", b"<html><title>Just a moment...</title>_cf_chl_opt</html>")
        refused = _ask(Shop({"/robots.txt": bot.Answer(404), "/p/1": challenge}), [_row(1)])
        self.assertEqual(refused.night.refused, 1)
        readings = bot.judge({"Kettles\x1f1": _row(1)}, refused)
        self.assertEqual(readings["Kettles\x1f1"].page.state, NOT_CHECKED)

    def test_a_product_page_with_a_recaptcha_box_or_cloudflares_script_is_no_challenge(self) -> None:
        page = (PRODUCT_PAGE % "24.99") + ('<script src="/cdn-cgi/challenge-platform/h/b/scripts/jsd/main.js"></script>'
                                           '<div class="g-recaptcha" data-sitekey="x"></div>' + "x" * 120_000)
        shop = Shop({"/robots.txt": bot.Answer(404), "/p/1": bot.Answer(200, "text/html", page.encode(),
                                                                         final_url="https://kettles.invalid/p/1")})
        result = _ask(shop, [_row(1)])
        self.assertFalse(result.answers["Kettles\x1f1"].challenge)
        self.assertEqual(result.night.refused, 0)
        self.assertEqual(bot.judge({"Kettles\x1f1": _row(1)}, result)["Kettles\x1f1"].page.state, PASSED)
        # A 404 page is never a challenge, whatever it writes.
        self.assertFalse(bot.is_challenge(bot.Answer(404, "text/html", b"<title>Just a moment</title>")))
        self.assertTrue(bot.is_challenge(bot.Answer(403, "text/html", b"<title>Just a moment...</title>")))
        # A wall that makes a browser work or wait first: a challenge, never got around.
        anubis = b'<title>Making sure you&#39;re not a bot!</title><script id="anubis_challenge">{}</script>'
        moment = b"<title>One moment, please...</title><p>Please wait while your request is being verified...</p>"
        self.assertTrue(bot.is_challenge(bot.Answer(200, "text/html", anubis + b" " * 6_000)))
        self.assertTrue(bot.is_challenge(bot.Answer(200, "text/html", moment + b" " * 12_000)))

    def test_nothing_is_asked_past_the_deadline(self) -> None:
        shop = Shop({"/robots.txt": bot.Answer(404)}, clock_step=10.0)
        result = _ask(shop, [_row(number) for number in range(10)], deadline=40.0)
        self.assertLess(len(result.answers), 10)
        self.assertTrue(all(answer for answer in result.answers))

    def test_a_row_on_another_site_is_not_asked(self) -> None:
        shop = Shop({"/robots.txt": bot.Answer(404)})
        rows = [_row(1), _row(2), _row(3, host="elsewhere.invalid")]
        result = _ask(shop, rows)
        self.assertTrue(result.answers["Kettles\x1f3"].elsewhere)
        self.assertEqual(shop.asked.count("/p/3"), 0)


class AllDayRoundTests(unittest.TestCase):
    """Owner, 2026-11-22: «Ναι, όλη μέρα»: a round from 05:30 to 03:05 UTC, kept as it goes."""

    def test_the_quiet_hours_and_the_nights_date(self) -> None:
        from datetime import datetime, timezone

        def at(hour: int, minute: int = 0, day: int = 22):
            return datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc)

        self.assertTrue(bot.quiet(at(3, 5), bot.UNTIL, bot.QUIET_UNTIL))
        self.assertTrue(bot.quiet(at(4, 17), bot.UNTIL, bot.QUIET_UNTIL))
        self.assertFalse(bot.quiet(at(5, 30), bot.UNTIL, bot.QUIET_UNTIL))
        self.assertFalse(bot.quiet(at(3, 4), bot.UNTIL, bot.QUIET_UNTIL))
        self.assertEqual(bot._deadline(at(5, 30), bot.UNTIL), at(3, 5, day=23))
        self.assertEqual(bot._deadline(at(22), bot.UNTIL), at(3, 5, day=23))
        self.assertEqual(bot._deadline(at(1), bot.UNTIL), at(3, 5))

    def test_answers_kept_as_they_come_and_a_round_started_again_goes_on(self) -> None:
        import tempfile

        page = bot.Answer(200, "text/html", (PRODUCT_PAGE % "24.99").encode(), final_url="https://kettles.invalid/p/1")
        with tempfile.TemporaryDirectory() as folder:
            tonight = bot.Tonight(Path(folder) / bot.TONIGHT.format(night="2026-11-23"))
            first = Shop({"/robots.txt": bot.Answer(404), "/p/1": page, "/p/2": bot.Answer(404)})
            _ask_kept = bot.ask_shop([_row(1), _row(2)], fetch=first.fetch, sleep=first.sleep, clock=first.clock,
                                     deadline=10_000.0, done={}, keep=tonight.keep)
            kept = tonight.load()
            self.assertEqual(set(kept), {"Kettles\x1f1", "Kettles\x1f2"})
            self.assertEqual(kept["Kettles\x1f1"].read.offers[0].price, 24.99)
            self.assertEqual(kept["Kettles\x1f2"].status, 404)
            again = Shop({"/robots.txt": bot.Answer(404), "/p/3": bot.Answer(410)})
            result = bot.ask_shop([_row(1), _row(2), _row(3)], fetch=again.fetch, sleep=again.sleep,
                                  clock=again.clock, deadline=10_000.0, done=kept, keep=tonight.keep)
            self.assertNotIn("/p/1", again.asked)
            self.assertNotIn("/p/2", again.asked)
            self.assertEqual(set(result.answers), {"Kettles\x1f1", "Kettles\x1f2", "Kettles\x1f3"})
            self.assertEqual(result.night.pages_read, 1)
            self.assertEqual(len(tonight.load()), 3)
            tonight.forget()
            self.assertEqual(tonight.load(), {})


class ANightEndToEndTests(unittest.TestCase):
    def test_a_night_into_the_ledger_and_the_decisions(self) -> None:
        rows = {row.key: row for row in (_row(1), _row(2), _row(3, price=10.0))}
        filler = {f"Filler\x1f{n}": Row(key=f"Filler\x1f{n}", shop="Filler", product_id=f"f{n}",
                                        address=f"https://filler.invalid/p/{n}") for n in range(200)}
        everything = {**rows, **filler}
        page = (PRODUCT_PAGE % "24.99").encode()
        answers = {"/robots.txt": bot.Answer(404), "/p/1": bot.Answer(200, "text/html", page),
                   "/p/2": bot.Answer(410), "/p/3": bot.Answer(200, "text/html", (PRODUCT_PAGE % "3.00").encode())}
        shop = Shop(answers)
        ledger = L.Ledger()
        night, made = bot.run(everything, shown=set(everything), parts={}, shared_ids=set(), candidates=[],
                              ledger=ledger, night=date(2026, 12, 1), fetch=shop.fetch, sleep=shop.sleep,
                              clock=shop.clock, deadline=1e9, workers=1, pause=3.0, awin=None, feeds={},
                              owner_cut_shops=[], owner_awin_word=False, say=lambda _line: None)
        # The price far apart cuts nothing: the shop's reader is not proven (three readings).
        self.assertEqual(made["cut"], {"Kettles\x1f2": GONE})
        self.assertEqual(ledger.products["Kettles\x1f1"].state, PASSED)
        self.assertEqual((ledger.products["Kettles\x1f3"].state, ledger.products["Kettles\x1f3"].site_price),
                         (PASSED, "3.00"))
        lines: list[str] = []
        bot.print_night(night.note, made, ledger, lines.append)
        # A look also says each shop's pace: its robots.txt, its catalogue asked for, 3 products; 3 s apart.
        self.assertEqual(night.note["seconds_by_shop"]["Kettles"], [12.0, None])
        bot.print_look(night.note, ledger, lines.append)
        printed = "\n".join(lines)
        self.assertIn("products cut 1", printed)
        self.assertIn("Kettles: 5 requests in 12 s, 2.4 s a request", printed)
        # And the shops' own stock words behind its readings (rules 5.2), counted.
        self.assertEqual(night.note["stock_words_by_shop"]["Kettles"], {"in stock: instock": 2})
        self.assertNotIn(".invalid", printed)
        self.assertNotIn("\x1f", printed)


class TheOldFeedRuleCountedWhileItWaitsTests(unittest.TestCase):
    def test_what_the_rule_would_not_show_is_counted_and_nothing_changes(self) -> None:
        # Rules 5.6.4, Proposed: a feed over 7 days old; a product of it with no reading of its
        # shop's site of the last 3 nights. Off until the owner's yes: counted for him only.
        rows = {f"Filler\x1f{n}": Row(key=f"Filler\x1f{n}", shop="Filler", product_id=f"f{n}",
                                      address=f"https://filler.invalid/q/{n}") for n in range(200)}
        rows.update({row.key: row for row in (_row(1), _row(2))})
        priced = (PRODUCT_PAGE % "24.99").encode()
        shop = Shop({"/robots.txt": bot.Answer(404), "/p/1": bot.Answer(200, "text/html", priced),
                     "/p/2": bot.Answer(200, "text/html", priced)})
        ledger = L.Ledger()
        arguments = dict(shown=set(rows), parts={}, shared_ids=set(), candidates=[], ledger=ledger, fetch=shop.fetch,
                         sleep=shop.sleep, clock=shop.clock, deadline=1e9, workers=1, pause=3.0, awin=None,
                         feeds={"Kettles": date(2026, 11, 1)}, owner_cut_shops=[], owner_awin_word=False,
                         say=lambda _line: None)
        first, made = bot.run(rows, night=date(2026, 12, 1), **arguments)
        self.assertTrue(ledger.shops["Kettles"].round_over)
        self.assertEqual((made["wait"], first.note["old_feed_would_wait"]["products"]), ({}, 0))
        # Four nights on its pages name the product but neither a price nor its stock: no reading.
        bare = b'<script type="application/ld+json">{"@type": "Product", "name": "Zentra Kettle", "sku": "ZK-1"}</script>'
        shop.answers.update({"/p/1": bot.Answer(200, "text/html", bare), "/p/2": bot.Answer(200, "text/html", bare)})
        later, made = bot.run(rows, night=date(2026, 12, 5), **arguments)
        self.assertEqual([ledger.products[key].state for key in ("Kettles\x1f1", "Kettles\x1f2")], [PASSED, PASSED])
        self.assertEqual(made["wait"], {})
        self.assertEqual(later.note["old_feed_would_wait"], {"products": 2, "shops": 1, "most": [["Kettles", 2]]})
        lines: list[str] = []
        bot.print_night(later.note, made, ledger, lines.append)
        self.assertIn("the Proposed rule of a feed over 7 days old (waits for the owner's yes) would not show 2 products "
                      "of 1 shops: Kettles 2", lines)
        # With his yes they wait, and the count is no longer made.
        with_yes, made = bot.run(rows, night=date(2026, 12, 6), old_feed_rule=True, **arguments)
        self.assertEqual(set(made["wait"].values()), {"old feed, no fresh reading"})
        self.assertNotIn("old_feed_would_wait", with_yes.note)


class OwnersYesTests(unittest.TestCase):
    def test_the_two_proposed_rules_are_off_until_the_owners_yes(self) -> None:
        # Rules 13.2: a feed over 7 days old (5.6.4) and a shop suspended, closed or offline at
        # Awin (5.6.3) wait for his yes (asked 21/11 to be reminded of them); the repo's file says no.
        self.assertEqual(bot.owner_yes(), {"old_feed_rule": False, "awin_closed_out": False})
        self.assertEqual(bot.owner_yes(ROOT / "data" / "none.json"), {"old_feed_rule": False, "awin_closed_out": False})

    def test_his_yes_is_read_from_the_file_and_only_true_is_yes(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "words.json"
            path.write_text(json.dumps({"old_feed_rule": True, "awin_closed_out": "yes"}), encoding="utf-8")
            self.assertEqual(bot.owner_yes(path), {"old_feed_rule": True, "awin_closed_out": False})

    def test_without_his_yes_a_suspended_shop_stays_and_is_named(self) -> None:
        rows = {f"Filler\x1f{n}": Row(key=f"Filler\x1f{n}", shop="Filler", product_id=f"f{n}",
                                      address=f"https://filler.invalid/p/{n}") for n in range(200)}
        rows.update({row.key: row for row in (_row(1),)})
        shop = Shop({"/robots.txt": bot.Answer(404)})
        arguments = dict(shown=set(rows), parts={}, shared_ids=set(), candidates=[], night=date(2026, 12, 1),
                         fetch=shop.fetch, sleep=shop.sleep, clock=shop.clock, deadline=1e9, workers=1, pause=3.0,
                         awin={"Kettles": ("suspended", ""), "Filler": ("joined", "")}, feeds={}, owner_cut_shops=[],
                         owner_awin_word=False, say=lambda _line: None)
        ledger = L.Ledger()
        night, made = bot.run(rows, ledger=ledger, **arguments)
        self.assertEqual(made["shops_out"], {})
        lines: list[str] = []
        bot.print_night(night.note, made, ledger, lines.append)
        self.assertIn("Awin: not out, the Proposed rule waits for the owner's yes: Kettles (suspended, 1 products)",
                      "\n".join(lines))
        with_yes = L.Ledger()
        _night, made = bot.run(rows, ledger=with_yes, awin_closed_out=True, **arguments)
        self.assertEqual(made["shops_out"], {"Kettles": "Awin: suspended"})


class RowsTests(unittest.TestCase):
    def test_a_row_of_the_second_link_takes_its_own_address(self) -> None:
        from picwise_providers.contracts import ProviderProduct

        product = ProviderProduct(
            provider_key="awin", provider_product_id="123", title="Zentra Kettle", brand="Zentra", category_text="",
            product_url="https://www.awin1.com/pclick.php?p=1&a=2&m=7", image_url="https://img.invalid/k.jpg",
            price_text="24.99", availability_text="in stock", currency="GBP",
            raw={"merchant_name": "Kettles", "merchant_deep_link": "https://kettles.invalid/products/zk?variant=9",
                 "ean": "5012345678900", "mpn": "ZK1", "merchant_product_id": "ZK-1"},
        )
        row = bot.row_of(product)
        self.assertEqual(row.address, "https://kettles.invalid/products/zk?variant=9")
        self.assertEqual((row.handle, row.variant), ("zk", "9"))
        self.assertEqual((row.gtin, row.mpn, row.price, row.feed_stock), ("05012345678900", "ZK1", 24.99, "in stock"))
        self.assertIn("ZK-1", row.skus)
        self.assertEqual(bot.row_from_record(bot.row_record(row)), row)


if __name__ == "__main__":
    unittest.main()
