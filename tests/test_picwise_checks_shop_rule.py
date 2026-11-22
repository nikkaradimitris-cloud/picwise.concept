"""The rule of how many of a shop's products pass, on the checks' side (the checks' rules 19;
owner, 2026-11-22): a pass counts for three nights (19.3.1, `picwise_checks.ledger`); the bot
asks a shop's shown products again first, in the order of 19.4, new ones in the time left, and
at most the first 20,000 of a shop (19.3.2, 19.3.3); the passed products named for a shop over
the most (19.4 f); the preparation leaves the waits of three nights aside with the switch off
(19.7.2, `picwise_providers.checks_applied`); the pages read on processes of their own (19.5,
`deployment/bot/shop_checks_bot.Readers`). The nights walked through both sides are in
`tests/test_picwise_checks_walk.py`.

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
from picwise_checks.verdicts import FAILED, GONE, PASSED, Row, ShopNight, Verdict  # noqa: E402
from picwise_providers import checks_applied as applied  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

NIGHT = date(2026, 12, 1)
OK = Verdict(PASSED, by="by code")
PRODUCT_PAGE = (
    '<script type="application/ld+json">{"@type": "Product", "name": "Zentra Kettle", "sku": "ZK-1", '
    '"offers": {"@type": "Offer", "price": "%s", "priceCurrency": "GBP", "availability": "InStock"}}</script>'
)


def _rows(shop: str, count: int, *, start: int = 0) -> dict[str, Row]:
    return {f"{shop}\x1f{number}": Row(key=f"{shop}\x1f{number}", shop=shop, product_id=str(number),
                                         address=f"https://{shop.lower()}.invalid/p/{number}", title=f"Thing {number}",
                                         price=10.0 + number, feed_stock="in stock")
            for number in range(start, start + count)}


def _record(ledger: L.Ledger, night: date, rows: dict[str, Row], verdicts: dict[str, Verdict]) -> None:
    shops = {row.shop for row in rows.values()}
    L.record_night(ledger, night, rows, {key: L.Reading(page=verdict) for key, verdict in verdicts.items()},
                   {shop: ShopNight(requests=10, answers=10, pages_200=10, pages_read=10) for shop in shops},
                   shown=set(rows))


class Rule1931APassCountsForThreeNightsTests(unittest.TestCase):
    def test_shown_the_night_it_passed_and_the_two_after_then_it_waits(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        key = next(iter(rows))
        _record(ledger, NIGHT, rows, {key: OK})
        ledger.shops["Alpha"].round_over = NIGHT.isoformat()
        for later in (0, 1, 2):
            made = L.decisions(ledger, NIGHT + timedelta(days=later), rows, shown=rows.keys(), pass_nights=3)
            self.assertEqual(made["wait"], {}, later)
        made = L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys(), pass_nights=3)
        self.assertEqual((made["wait"], made["cut"]), ({key: L.NOT_PASSED_IN_THREE}, {}))
        self.assertEqual(L.NOT_PASSED_IN_THREE, applied.THREE_NIGHTS)
        # Thirty nights stays its own reason; without the rule, thirty nights as before (9.1).
        late = L.decisions(ledger, NIGHT + timedelta(days=30), rows, shown=rows.keys(), pass_nights=3)
        self.assertEqual(late["wait"], {key: L.NOT_PASSED_IN_THIRTY})
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys())["wait"], {})

    def test_a_candidate_whose_pass_is_over_three_nights_old_does_not_enter(self) -> None:
        ledger, rows = L.Ledger(), _rows("Alpha", 1)
        key = next(iter(rows))
        _record(ledger, NIGHT, rows, {key: OK})
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=2), rows, shown=(), candidates=[key],
                                     pass_nights=3)["enter"], [key])
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=(), candidates=[key],
                                     pass_nights=3)["enter"], [])


class Rule194fThePassedOfAShopOverTheMostTests(unittest.TestCase):
    def test_named_only_for_a_shop_that_shows_more_than_the_most(self) -> None:
        ledger = L.Ledger()
        big, small = _rows("Big", 5), _rows("Small", 2)
        rows = {**big, **small}
        keys = list(big)
        _record(ledger, NIGHT, rows, {keys[0]: OK, keys[1]: OK, keys[2]: Verdict(FAILED, GONE),
                                      next(iter(small)): OK})
        made = L.decisions(ledger, NIGHT, rows, shown=rows.keys(), pass_nights=3, passed_over=3)
        self.assertEqual(made["passed"], sorted(keys[:2]))
        self.assertNotIn("passed", L.decisions(ledger, NIGHT, rows, shown=rows.keys()))


class Rules1932And1933TheOrderOfAskingTests(unittest.TestCase):
    def _ledger(self):
        ledger, rows = L.Ledger(), _rows("Alpha", 8)
        keys = list(rows)
        _record(ledger, NIGHT, rows, {keys[0]: Verdict(FAILED, GONE), keys[1]: OK, keys[2]: OK, keys[3]: OK})
        return ledger, rows, keys

    def test_the_shown_again_first_in_the_order_given_then_candidates_then_the_never_asked(self) -> None:
        ledger, rows, keys = self._ledger()
        tonight = NIGHT + timedelta(days=7)
        candidates = {key: row for key, row in _rows("Alpha", 2, start=100).items()}
        every = {**rows, **candidates}
        named = list(reversed(candidates))
        order = L.asking_order(ledger, tonight, every, shown=rows.keys(), candidates=named, scanned=True,
                               shown_order={"Alpha": [keys[3], keys[1], keys[2]]})["Alpha"]
        # The failed one due; the shown asked before in the order of 19.4; the candidates in the
        # order named; then the shown never asked, the cheapest first.
        self.assertEqual(order, [keys[0], keys[3], keys[1], keys[2], *named, *keys[4:]])
        # Without the rule, as before: candidates, the never asked, then the shown asked before.
        before = L.asking_order(ledger, tonight, every, shown=rows.keys(), candidates=named)["Alpha"]
        self.assertEqual(before[1:3], sorted(named))
        self.assertEqual(before[-3:], [keys[1], keys[2], keys[3]])

    def test_at_most_the_first_of_a_shop_past_the_failed_due(self) -> None:
        ledger, rows, keys = self._ledger()
        order = L.asking_order(ledger, NIGHT + timedelta(days=7), rows, shown=rows.keys(), scanned=True,
                               shown_order={"Alpha": keys[1:4]}, limit=4)["Alpha"]
        self.assertEqual(order, [keys[0], keys[1], keys[2], keys[3], keys[4]])


class Rule1972TheSwitchOffBringsThemBackTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()
        self.addCleanup(applied.reset_for_tests)

    def _product(self) -> ProviderProduct:
        return ProviderProduct(
            provider_key="awin", provider_product_id="row-1", title="Zentra Kettle", brand="Zentra",
            category_text="Home & Garden > Kitchen", product_url="https://alpha.invalid/p/1",
            image_url="https://alpha.invalid/i/1.jpg", price_text="20.99", availability_text="in stock", currency="GBP",
            raw={"merchant_name": "Alpha", "availability": "in stock"},
        )

    def _decisions(self, key: str) -> dict:
        return {"format": applied.DECISIONS_FORMAT, "night": NIGHT.isoformat(), "wait": {key: applied.THREE_NIGHTS},
                "passed": [key]}

    def test_the_waits_of_three_nights_only_with_the_switch_on(self) -> None:
        from picwise_providers.catalogue_cap import row_key
        from picwise_providers.catalogue_memory import product_key

        product = self._product()
        key = product_key(product)
        applied.apply_checks([product], decisions=self._decisions(key), switch=True, today=NIGHT, scanned=True)
        self.assertEqual(applied.unchecked_row_keys([product], row_key), frozenset({row_key(product)}))
        self.assertTrue(applied.passed(product))
        applied.apply_checks([product], decisions=self._decisions(key), switch=True, today=NIGHT, scanned=False)
        self.assertEqual(applied.unchecked_row_keys([product], row_key), frozenset())
        self.assertEqual(applied.last_checks_note()["three_nights_left_aside"], 1)

    def test_passed_is_false_while_the_gate_is_off(self) -> None:
        self.assertFalse(applied.passed(self._product()))


class Rule1932TheOrderReadFromThePreparedCatalogueTests(unittest.TestCase):
    def test_per_shop_its_keys_in_the_order_of_19_4_a_cheaper_shops_last(self) -> None:
        import tempfile
        from datetime import datetime, timezone

        from picwise_checks.rows import row_of
        from picwise_providers.contracts import ProviderFeedStatus
        from picwise_providers.offer_health import build_feed_availability_context
        from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue

        def product(number: int, shop: str, price: float, ean: str = "") -> ProviderProduct:
            raw = {"merchant_name": shop, "availability": "in stock", **({"ean": ean} if ean else {})}
            return ProviderProduct(
                provider_key="awin", provider_product_id=f"{shop}-{number}", title=f"Zentra Kettle {number}",
                brand="Zentra", category_text="Home & Garden > Kitchen", product_url=f"https://{shop}.invalid/p/{number}",
                image_url=f"https://{shop}.invalid/i/{number}.jpg", price_text=f"{price:.2f}", availability_text="in stock",
                currency="GBP", raw=raw)

        shared = "5012345678900"
        products = [product(1, "big", 60.0, shared), product(2, "big", 20.0), product(3, "big", 25.0),
                    product(1, "small", 30.0, shared)]
        prepared = PreparedCatalogue(
            prepared_at=datetime(2026, 11, 24, 4, 30, tzinfo=timezone.utc),
            feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
            availability_context=build_feed_availability_context(tuple(products)), products=tuple(products),
            non_new=("",) * len(products), kinds=(frozenset({"kettle"}),) * len(products), eligible_count=len(products),
            shop_count=2, suggestions=())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            write_prepared_catalogue(prepared, path)
            rows, _parts, _ids, orders = bot.rows_from_catalogue(path, order=True)
            self.assertEqual(bot.rows_from_catalogue(path)[3], {})
        keys = [row_of(item).key for item in products]
        self.assertEqual(set(rows), set(keys))
        self.assertEqual(sorted(orders["big"]), sorted(keys[:3]))
        self.assertEqual(orders["big"][-1], keys[0])
        self.assertEqual(orders["small"], [keys[3]])


class TheShopsRuleInThePreparationTests(unittest.TestCase):
    def test_a_failure_keeps_every_product_and_is_said(self) -> None:
        import importlib.util
        import tempfile
        from unittest import mock

        from picwise_providers import shop_cap
        from picwise_providers.offer_health import build_feed_availability_context

        spec = importlib.util.spec_from_file_location("prepare_catalogue_shop_rule", ROOT / "tools" / "prepare_catalogue.py")
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        products = [ProviderProduct(
            provider_key="awin", provider_product_id=f"row-{number}", title=f"Zentra Kettle {number}", brand="Zentra",
            category_text="Home & Garden > Kitchen", product_url=f"https://alpha.invalid/p/{number}",
            image_url=f"https://alpha.invalid/i/{number}.jpg", price_text=f"{20 + number}.99", availability_text="in stock",
            currency="GBP", raw={"merchant_name": "Alpha", "availability": "in stock"}) for number in range(5)]
        context = build_feed_availability_context(tuple(products))
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(shop_cap, "shop_cap_on", return_value=True), \
                mock.patch.object(shop_cap, "cap_shops", side_effect=KeyError("x")):
            capping = tool._Cap(Path(folder) / "catalogue.json.gz")
            keep = capping(products, [frozenset({"kettle"})] * 5, context)
            self.assertEqual(list(keep), [True] * 5)
            self.assertIn("KeyError", capping.shops_error)
            self.assertFalse(tool._shop_cap(capping)["applied"])
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(shop_cap, "shop_cap_on", return_value=True), \
                mock.patch.object(shop_cap, "SHOP_LIMIT", 3):
            capping = tool._Cap(Path(folder) / "catalogue.json.gz")
            keep = capping(products, [frozenset({"kettle"})] * 5, context)
            self.assertEqual(sum(keep), 3)
            note = tool._shop_cap(capping)
            self.assertEqual((note["applied"], note["capped_shops"], note["cut"]), (True, 1, 2))


class Rule195ThePagesReadOnProcessesOfTheirOwnTests(unittest.TestCase):
    def test_a_page_read_on_processes_is_read_as_on_the_bots_own(self) -> None:
        said: list[str] = []
        readers = bot.Readers.start(2, said.append)
        self.addCleanup(readers.close)
        if not readers.processes:
            self.skipTest("this machine starts no processes: " + "; ".join(said))
        page = bot.Answer(200, "text/html; charset=utf-8", (PRODUCT_PAGE % "24.99").encode())
        self.assertEqual(readers.page(page), bot.Readers().page(page))
        self.assertEqual(readers.page(page).offers[0].price, 24.99)
        self.assertEqual(readers.page(bot.Answer(404)), bot.Readers().page(bot.Answer(404)))
        catalogue = b'{"products": [{"handle": "Zentra-Kettle", "variants": [{"id": 1, "price": "24.99", "available": true}]}]}'
        size, found = readers.catalogue_page(bot.Answer(200, "application/json", catalogue))
        self.assertEqual((size, [handle for handle, _read in found]), (1, ["zentra-kettle"]))
        self.assertIsNone(readers.catalogue_page(bot.Answer(200, "text/html", b"<html></html>")))
        self.assertIn("2 processes", said[-1])

    def test_a_shops_night_through_processes_is_the_same(self) -> None:
        readers = bot.Readers.start(2, lambda _line: None)
        self.addCleanup(readers.close)
        answers = {"/robots.txt": bot.Answer(404), "/products.json?limit=250&page=1": bot.Answer(404),
                   "/p/1": bot.Answer(200, "text/html", (PRODUCT_PAGE % "24.99").encode(),
                                      final_url="https://kettles.invalid/p/1")}
        rows = [Row(key="Kettles\x1f1", shop="Kettles", product_id="1", address="https://kettles.invalid/p/1",
                    title="Zentra Kettle", price=24.99, skus=frozenset({"ZK-1"}))]

        def night(with_readers):
            return bot.ask_shop(rows, fetch=lambda url, _limit: answers.get(url.split(".invalid", 1)[1], bot.Answer(404)),
                                sleep=lambda _seconds: None, clock=lambda: 0.0, deadline=10.0, readers=with_readers)

        self.assertEqual(night(readers).answers, night(None).answers)

    def test_no_processes_reads_on_the_bots_own(self) -> None:
        readers = bot.Readers.start(0, lambda _line: None)
        self.assertEqual(readers.processes, 0)


if __name__ == "__main__":
    unittest.main()
