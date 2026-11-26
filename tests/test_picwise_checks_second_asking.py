"""The second asking of the day (the checks' rules 23; owner, 2026-11-26: «Τα γρήγορα καταστήματα
ξαναελέγχουν ένα μέρος των προϊόντων τους και δεύτερη φορά μέσα στην ίδια μέρα. Μετράει ο πιο
πρόσφατος έλεγχος»; and the brief he gave: «Προϊόν που πέρασε την ίδια μέρα κόβεται μόνο με καθαρή
απάντηση ... Αν απλώς δεν απαντήσει, μένει ο πρώτος έλεγχος. Σταματά για τη μέρα μόλις το κατάστημα
αργήσει ή αρνηθεί αιτήματα. Ξεκινά από τα προϊόντα που βγαίνουν στις πρώτες κάρτες κάθε είδους. Έχει
δικό του διακόπτη και ανοίγει τελευταίος»; `deployment/bot/shop_checks_bot.py`).

Pinned: not before its hour; only within the most a shop is asked a day; the first cards of each
kind first; a clear answer counts in place of the first (a page read, a page not there), any other
keeps the first and stops the asking for the day, as does a slow one, without ever stopping the
shop's own night; a Shopify shop reads its catalogue again; a round started again does not ask
again what it asked, nor a shop whose asking stopped; through the bot, the latest answer is what
the night records, and the note says it; with its switch off (the repo's, until the owner's word),
nothing of it.

Every shop is fictional, on `.invalid` hosts; the fetch is a local stand-in: nothing is opened.
"""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import shop_checks_bot as bot  # noqa: E402

from picwise_checks import bot_rows as B  # noqa: E402
from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.verdicts import Row  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402

PAGE = ('<script type="application/ld+json">{"@type": "Product", "name": "Zentra Kettle %d", "sku": "ZK-%d", '
        '"offers": {"@type": "Offer", "price": "%s", "priceCurrency": "GBP", "availability": "InStock"}}</script>')
MORNING = datetime(2026, 12, 1, 5, 30, tzinfo=timezone.utc)


def _row(number: int, host: str = "alpha") -> Row:
    return Row(key=f"{host}|{number}", shop=host.title(), product_id=f"{host}-{number}",
               address=f"https://{host}.invalid/p/{number}", title=f"Zentra Kettle {number}", price=20.0 + number,
               currency="GBP")


class Shop:
    """One shop's pages. `later`: from the second asking on (the clock past `turn`), the answer for a
    product's number, as (status, price) or a status alone; `slow`: seconds a request takes then."""

    def __init__(self, *, later=None, slow: float = 0.0, turn: float = 1000.0) -> None:
        self.now = 0.0
        self.later = later or {}
        self.slow = slow
        self.turn = turn
        self.asked: Counter = Counter()

    def fetch(self, url: str, limit: int) -> bot.Answer:
        path = url.split("://", 1)[1].split("/", 1)[1]
        self.asked[path] += 1
        if path == "robots.txt" or path.startswith("products.json"):
            self.now += 1.0
            return bot.Answer(404)
        number = int(path.rsplit("/", 1)[1])
        price = f"{20 + number}.00"
        if self.now >= self.turn:
            self.now += self.slow or 1.0
            said = self.later.get(number)
            if isinstance(said, tuple):
                status, price = said
            elif said is not None:
                status = said
            else:
                status = 200
            if status != 200:
                return bot.Answer(status, "text/html", b"")
        else:
            self.now += 1.0
        return bot.Answer(200, "text/html", (PAGE % (number, number, price)).encode())

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def clock(self) -> float:
        return self.now


def _ask(shop: Shop, rows: list[Row], **second) -> bot.ShopResult:
    return bot.ask_shop(rows, fetch=shop.fetch, sleep=shop.sleep, clock=shop.clock, deadline=100_000.0, pause=3.0,
                        **second)


class SecondAskingTests(unittest.TestCase):
    def test_not_before_its_hour_within_the_most_and_the_latest_clear_answer_counts(self) -> None:
        rows = [_row(number) for number in range(1, 7)]
        shop = Shop(later={2: (200, "99.00"), 3: 404})
        result = _ask(shop, rows, second=[rows[2], rows[1], rows[0], rows[3]], second_most=3, second_at=1000.0)
        # The first asking ended long before 1,000 s: the second waited for its hour.
        self.assertEqual(result.second, {"asked": 3, "kept": 3, "stopped": ""})
        self.assertGreaterEqual(shop.now, 1000.0)
        # In the order given, three at most: 3, 2, 1 asked twice; 4, 5, 6 once.
        self.assertEqual([shop.asked[f"p/{number}"] for number in range(1, 7)], [2, 2, 2, 1, 1, 1])
        # The latest clear answer counts: product 2 at its new price, product 3's page not there.
        self.assertEqual(result.answers["alpha|2"].read.offers[0].price, 99.0)
        self.assertEqual(result.answers["alpha|3"].status, 404)
        self.assertEqual(result.stopped, "")
        # The shop's counts: each product once.
        self.assertEqual(result.night.pages_200, 5)

    def test_an_answer_that_is_not_clear_keeps_the_first_and_stops_the_asking_never_the_shops_night(self) -> None:
        rows = [_row(number) for number in range(1, 7)]
        for status in (503, 500, 403, 0):
            with self.subTest(status):
                shop = Shop(later={2: status})
                told: list[str] = []
                result = _ask(shop, rows, second=rows, second_most=6, second_at=1000.0, stop_second=told.append)
                self.assertEqual(result.second["asked"], 2)
                self.assertEqual(result.second["kept"], 1)
                self.assertTrue(result.second["stopped"].startswith("not a clear answer"), result.second)
                self.assertEqual(told, [result.second["stopped"]])
                # Product 2 keeps its first answer, read; 3 to 6 are not asked again.
                self.assertTrue(result.answers["alpha|2"].read.found)
                self.assertEqual([shop.asked[f"p/{number}"] for number in range(3, 7)], [1, 1, 1, 1])
                self.assertEqual(result.stopped, "")

    def test_asked_to_come_back_later_stops_the_asking_and_not_the_shops_night(self) -> None:
        rows = [_row(number) for number in range(1, 5)]
        shop = Shop(later={1: 429})
        result = _ask(shop, rows, second=rows, second_most=4, second_at=1000.0)
        self.assertEqual(result.second, {"asked": 1, "kept": 0, "stopped": "429: asked to come back later"})
        self.assertEqual(result.stopped, "")
        self.assertTrue(result.answers["alpha|1"].read.found)

    def test_a_slow_shop_stops_after_the_answer_that_took_too_long(self) -> None:
        rows = [_row(number) for number in range(1, 5)]
        shop = Shop(slow=bot.SECOND_SLOW_SECONDS + 1)
        result = _ask(shop, rows, second=rows, second_most=4, second_at=1000.0)
        self.assertEqual((result.second["asked"], result.second["kept"]), (1, 1))
        self.assertTrue(result.second["stopped"].startswith("slow"), result.second)

    def test_only_what_the_first_asking_read_and_never_twice_in_a_day(self) -> None:
        rows = [_row(number) for number in range(1, 5)]
        shop = Shop()
        # Product 1 asked again already tonight (a round started again); the shop's asking stopped: nothing.
        result = _ask(shop, rows, second=rows, second_most=4, second_at=1000.0, second_done={"alpha|1"})
        self.assertEqual(result.second["asked"], 3)
        self.assertEqual(shop.asked["p/1"], 1)
        stopped = Shop()
        result = _ask(stopped, rows, second=rows, second_most=4, second_at=1000.0, second_stopped=True)
        self.assertEqual(result.second, {"asked": 0, "kept": 0, "stopped": ""})
        self.assertTrue(all(count == 1 for path, count in stopped.asked.items() if path.startswith("p/")))
        # None given: no second asking, nothing said.
        self.assertEqual(_ask(Shop(), rows).second, {})

    def test_a_shopify_shop_reads_its_catalogue_again(self) -> None:
        rows = [Row(key=f"beta|{number}", shop="Beta", product_id=f"beta-{number}",
                    address=f"https://beta.invalid/products/kettle-{number}", title=f"Zentra Kettle {number}",
                    price=20.0 + number, currency="GBP", handle=f"kettle-{number}") for number in range(1, 4)]
        reads = Counter()

        def listing(price: str) -> bytes:
            return json.dumps({"products": [{"handle": f"kettle-{number}", "title": f"Zentra Kettle {number}",
                                             "variants": [{"id": number, "price": price if number == 2 else f"{20 + number}.00",
                                                           "available": True, "sku": f"ZK-{number}"}]}
                                            for number in range(1, 4)]}).encode()

        clock = {"now": 0.0}

        def fetch(url: str, limit: int) -> bot.Answer:
            clock["now"] += 1.0
            path = url.split("://", 1)[1].split("/", 1)[1]
            reads[path.split("?")[0]] += 1
            if path == "robots.txt":
                return bot.Answer(404)
            if path.startswith("products.json"):
                return bot.Answer(200, "application/json", listing("55.00" if clock["now"] > 1000 else "22.00"))
            return bot.Answer(404)

        result = bot.ask_shop(rows, fetch=fetch, sleep=lambda seconds: clock.__setitem__("now", clock["now"] + seconds),
                              clock=lambda: clock["now"], deadline=100_000.0, pause=3.0, second=rows, second_most=3,
                              second_at=1000.0)
        self.assertEqual(result.second, {"asked": 3, "kept": 3, "stopped": ""})
        self.assertEqual(reads["products.json"], 2)
        self.assertEqual(result.answers["beta|2"].read.offers[0].price, 55.0)
        self.assertTrue(result.answers["beta|2"].in_catalogue)


class SecondAskingThroughTheBotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        products = [ProviderProduct(
            provider_key="awin", provider_product_id=f"alpha-{number}", title=f"Zentra Kettle {number}", brand="Zentra",
            category_text="Home & Garden > Kitchen", product_url=f"https://alpha.invalid/p/{number}",
            image_url=f"https://alpha.invalid/i/{number}.jpg", price_text=f"{20 + number}.00",
            availability_text="in stock", currency="GBP",
            raw={"merchant_name": "Alpha", "availability": "in stock", "sku": f"ZK-{number}", "advertiser_id": "1001"})
            for number in range(1, 9)]
        prepared = PreparedCatalogue(
            prepared_at=datetime(2026, 12, 1, 4, 30, tzinfo=timezone.utc),
            feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
            availability_context=build_feed_availability_context(tuple(products)), products=tuple(products),
            non_new=("",) * len(products), kinds=(frozenset({"kettle"}),) * len(products),
            eligible_count=len(products), shop_count=1, suggestions=())
        self.catalogue = self.folder / "catalogue.json.gz"
        write_prepared_catalogue(prepared, self.catalogue)

    def _main(self, checks: Path, shop: Shop, *, on: bool) -> int:
        checks.mkdir(exist_ok=True)
        switch = self.folder / "clones.json"
        switch.write_text(json.dumps({"clones": 8, "bots": []}), encoding="utf-8")
        with mock.patch.object(bot, "second_on", return_value=on), \
                mock.patch("picwise_providers.shop_cap.shop_limits", return_value=(4, 12)):
            return bot.main(["--catalogue", str(self.catalogue), "--checks", str(checks), "--processes", "0",
                             "--shop-rule", "on", "--cache", str(self.folder / "cache")],
                            fetch=shop.fetch, sleep=shop.sleep, clock=shop.clock, now=MORNING, environ={}, switch=switch)

    def test_the_latest_answer_is_what_the_night_records_and_the_note_says_it(self) -> None:
        checks = self.folder / "on"
        shop = Shop(later={1: (200, "30.00")}, turn=bot.SECOND_AFTER_HOURS * 3600)
        self.assertEqual(self._main(checks, shop, on=True), 0)
        note = json.loads((checks / bot.NOTE_NAME).read_text())
        # Eight shown, all asked first; then, from the eighth hour, again within the twelve a day: four.
        self.assertEqual(note["second"], {"shops": 1, "asked": 4, "kept": 4, "stopped": 0})
        self.assertEqual(note["second_by_shop"], {"Alpha": [4, 4, ""]})
        ledger = L.load(checks / L.LEDGER_NAME)
        product = next(product for key, product in ledger.products.items() if key.endswith("alpha-1"))
        self.assertEqual(product.site_price, "30.00")
        # The first cards of the kind first: its middle price (the Recommended), then its cheapest.
        self.assertEqual(sorted(path for path, count in shop.asked.items() if count == 2),
                         ["p/1", "p/2", "p/3", "p/5"])

    def test_with_its_switch_off_nothing_of_it(self) -> None:
        checks = self.folder / "off"
        shop = Shop(later={1: (200, "30.00")}, turn=bot.SECOND_AFTER_HOURS * 3600)
        self.assertEqual(self._main(checks, shop, on=False), 0)
        note = json.loads((checks / bot.NOTE_NAME).read_text())
        self.assertNotIn("second", note)
        self.assertTrue(all(count == 1 for path, count in shop.asked.items() if path.startswith("p/")))

    def test_the_repos_switch_is_off_until_the_owners_word(self) -> None:
        self.assertFalse(bot.second_on())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "second.json"
            for text, on in (('{"on": true}', True), ('{"on": "true"}', False), ("{", False), ("[]", False)):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(bot.second_on(path), on, text)

    def test_the_first_cards_are_each_kinds_cheapest_four_and_its_middle_price(self) -> None:
        rows = {f"k{number}": Row(key=f"k{number}", shop="Alpha", product_id=str(number), address="", price=float(number))
                for number in range(1, 11)}
        parts = {key: "kettle" for key in rows}
        parts["k10"] = "toaster"
        self.assertEqual(B.first_cards(rows, rows, parts), {"k5": 0, "k1": 1, "k2": 2, "k3": 3, "k4": 4, "k10": 0})


if __name__ == "__main__":
    unittest.main()
