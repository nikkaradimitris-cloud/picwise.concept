"""The checks' eight bots (the checks' rules 23; owner, 2026-11-26: «8 bot αντί για 4, 2 σε κάθε
πυρήνα. Κάθε bot είναι ξεχωριστό πρόγραμμα», «κάθε κατάστημα παίρνει σταθερό κωδικό ... και
πηγαίνει πάντα στο ίδιο bot»; `picwise_checks.bot_rows`, `deployment/bot/shop_checks_bot.py`).

Pinned: a shop's bot by a code of its number at Awin, its name only when its rows give none, and
the same whatever its products; the switch read strictly (how many bots, which are on); with some
bots on, the bot alone asks only the other bots' shops, waits for the day's end and records the
night from its day and theirs, and decides what it decides asking every shop alone; with every bot
on, it asks nothing; a bot started again goes on from what it kept and counts its starts; the
catalogue read in a process of its own hands back the same rows as read on the bot's own; the
night's note names each asker's day.

Every shop is fictional, on `.invalid` hosts; the fetch is a local stand-in: nothing is opened.
"""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import shop_checks_bot as bot  # noqa: E402

from picwise_checks import bot_rows as B  # noqa: E402
from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.rows import row_from_record, row_of, row_record  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402

PAGE = ('<script type="application/ld+json">{"@type": "Product", "name": "Zentra Kettle %d", "sku": "ZK-%d", '
        '"offers": {"@type": "Offer", "price": "%s", "priceCurrency": "GBP", "availability": "InStock"}}</script>')
SHOPS = {"Alpha Kettles": "1001", "Beta Kettles": "1002", "Gamma Kettles": "1003", "Delta Kettles": "1004",
         "Epsilon Kettles": "1005", "Zeta Kettles": "", "Eta Kettles": "1007", "Theta Kettles": "1008"}
MORNING = datetime(2026, 12, 1, 5, 30, tzinfo=timezone.utc)
AFTER = datetime(2026, 12, 2, 3, 7, tzinfo=timezone.utc)
NIGHT = "2026-12-02"


def _product(shop: str, number: int) -> ProviderProduct:
    host = shop.split()[0].lower()
    raw = {"merchant_name": shop, "availability": "in stock", "sku": f"ZK-{number}"}
    if SHOPS.get(shop):
        raw["advertiser_id"] = SHOPS[shop]
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"{host}-{number}", title=f"Zentra Kettle {number}", brand="Zentra",
        category_text="Home & Garden > Kitchen", product_url=f"https://{host}.invalid/p/{number}",
        image_url=f"https://{host}.invalid/i/{number}.jpg", price_text=f"{20 + number}.00", availability_text="in stock",
        currency="GBP", raw=raw)


class Site:
    """Every shop's pages: robots.txt not there, each product's page read."""

    def __init__(self) -> None:
        self.now = 0.0
        self.asked: Counter = Counter()

    def fetch(self, url: str, limit: int) -> bot.Answer:
        self.now += 1.0
        host, path = url.split("://", 1)[1].split("/", 1)
        self.asked[host.split(".")[0]] += 1
        if path == "robots.txt" or path.startswith("products.json"):
            return bot.Answer(404)
        number = int(path.rsplit("/", 1)[1])
        return bot.Answer(200, "text/html", (PAGE % (number, number, f"{20 + number}.00")).encode())

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def clock(self) -> float:
        return self.now


class AssignmentTests(unittest.TestCase):
    def test_a_shops_bot_is_by_its_number_at_awin_else_by_its_name(self) -> None:
        # The same number under another name: the same bot; no number: by name, as from 25/11.
        self.assertEqual(B.clone_of("Alpha Kettles", 8, "1001"), B.clone_of("Alpha Kettles Ltd (renamed)", 8, "1001"))
        self.assertEqual(B.clone_of("Zeta Kettles", 8), B.clone_of("  zeta   KETTLES ", 8))
        self.assertEqual(B.clone_of("Zeta Kettles", 4), bot.clone_of("Zeta Kettles", 4))
        # Over many shops, each bot has about an eighth of them.
        spread = Counter(B.clone_of(f"Shop {number}", 8, str(4000 + number)) for number in range(800))
        self.assertEqual(sorted(spread), list(range(1, 9)))
        self.assertTrue(all(70 <= count <= 130 for count in spread.values()), spread)

    def test_a_shops_number_is_the_one_most_of_its_rows_give_and_its_bot_holds_whatever_its_products(self) -> None:
        rows = [row_of(_product("Alpha Kettles", number)) for number in range(1, 6)]
        self.assertEqual({row.advertiser for row in rows}, {"1001"})
        self.assertEqual(B.shop_advertisers(rows), {"Alpha Kettles": "1001"})
        fewer = B.assignment(rows[:1], 8)
        self.assertEqual(B.assignment(rows, 8), fewer)
        # A row written before the number was kept reads with none; a row names its number again.
        record = row_record(rows[0])
        self.assertEqual(row_from_record(record), rows[0])
        self.assertEqual(row_from_record(record[:14]).advertiser, "")
        odd = [rows[0], rows[1].__class__(**{**rows[1].__dict__, "advertiser": "9"})]
        self.assertEqual(B.shop_advertisers(odd + [rows[2]]), {"Alpha Kettles": "1001"})
        self.assertEqual(B.shop_advertisers(odd), {"Alpha Kettles": "1001"})  # tied: the smallest
        self.assertEqual(B.shop_advertisers([row_of(_product("Zeta Kettles", 1))]), {"Zeta Kettles": ""})

    def test_the_switch_is_read_strictly(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "checks_clones.json"
            self.assertEqual(B.clones_switch(path), B.Clones(8, frozenset()))
            for words, clones, bots in (({"clones": 8, "bots": []}, 8, set()),
                                        ({"clones": 8, "bots": [1, 2]}, 8, {1, 2}),
                                        ({"clones": 8, "bots": [0, 2, 9, "3", True]}, 8, {2}),
                                        ({"clones": "8", "bots": [1]}, 8, {1}),
                                        ({"clones": 2, "bots": [1, 2]}, 2, {1, 2}),
                                        ({"on": True}, 8, set())):
                path.write_text(json.dumps(words), encoding="utf-8")
                switch = B.clones_switch(path)
                self.assertEqual((switch.clones, set(switch.bots)), (clones, bots), words)
            self.assertTrue(B.Clones(2, frozenset({1, 2})).all_on)
            self.assertFalse(B.Clones(8, frozenset()).all_on)
            self.assertEqual(B.Clones(4, frozenset({1})).rest, {2, 3, 4})

    def test_the_repos_switch_has_all_eight_bots_on_by_the_owners_word(self) -> None:
        # 27/11, «2 συμφωνώ με αυτά»: all eight at once (the rules 23.9).
        switch = B.clones_switch()
        self.assertEqual((switch.clones, switch.bots), (8, frozenset(range(1, 9))))
        self.assertTrue(switch.all_on)


class EightBotsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        products = [_product(shop, number) for shop in SHOPS for number in range(1, 4)]
        prepared = PreparedCatalogue(
            prepared_at=datetime(2026, 12, 1, 4, 30, tzinfo=timezone.utc),
            feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(products)),
            availability_context=build_feed_availability_context(tuple(products)), products=tuple(products),
            non_new=("",) * len(products), kinds=(frozenset({"kettle"}),) * len(products),
            eligible_count=len(products), shop_count=len(SHOPS), suggestions=())
        self.catalogue = self.folder / "catalogue.json.gz"
        write_prepared_catalogue(prepared, self.catalogue)
        self.rows = [row_of(product) for product in products]

    def _switch(self, clones: int, bots) -> Path:
        path = self.folder / f"switch-{clones}-{'-'.join(map(str, bots)) or 'none'}.json"
        path.write_text(json.dumps({"clones": clones, "bots": sorted(bots)}), encoding="utf-8")
        return path

    def _main(self, checks: Path, site: Site, *extra: str, now: datetime = MORNING, switch: Path | None = None,
              processes: str = "0") -> int:
        checks.mkdir(exist_ok=True)
        return bot.main(["--catalogue", str(self.catalogue), "--checks", str(checks), "--processes", processes,
                         "--shop-rule", "on", "--cache", str(self.folder / "cache"), *extra],
                        fetch=site.fetch, sleep=site.sleep, clock=site.clock, now=now, environ={},
                        switch=switch or self._switch(8, ()))

    @staticmethod
    def _decisions(checks: Path) -> dict:
        with gzip.open(checks / L.DECISIONS_NAME, "rt", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _states(checks: Path) -> dict:
        ledger = L.load(checks / L.LEDGER_NAME)
        return {key: (product.state, product.reason, product.passed_on) for key, product in ledger.products.items()}

    def test_some_bots_on_the_bot_alone_asks_the_others_and_records_what_it_records_alone(self) -> None:
        alone = self.folder / "alone"
        self.assertEqual(self._main(alone, Site()), 0)
        bot_of = B.assignment(self.rows, 2)
        mixed = self.folder / "mixed"
        switch = self._switch(2, (1,))
        first = Site()
        self.assertEqual(self._main(mixed, first, "--clone", "1", switch=switch), 0)
        self.assertEqual(set(first.asked), {shop.split()[0].lower() for shop, number in bot_of.items() if number == 1})
        self.assertFalse((mixed / L.DECISIONS_NAME).exists())
        rest = Site()
        said: list[str] = []
        import builtins

        printed = builtins.print
        builtins.print = lambda *args, **kwargs: said.append(" ".join(str(arg) for arg in args))
        try:
            self.assertEqual(self._main(mixed, rest, switch=switch), 0)
        finally:
            builtins.print = printed
        # Only the shops of the bot not switched on; and it waited for the day's end before it read
        # bot 1's day (it never records a night a bot of its own is still asking).
        self.assertEqual(set(rest.asked), {shop.split()[0].lower() for shop, number in bot_of.items() if number == 2})
        self.assertGreater(rest.now, (datetime(2026, 12, 2, 3, 5, tzinfo=timezone.utc) - MORNING).total_seconds() - 60)
        self.assertTrue(any("bots of their own: 1 of 2" in line for line in said), said)
        self.assertEqual(self._decisions(mixed), self._decisions(alone))
        self.assertEqual(self._states(mixed), self._states(alone))
        note = json.loads((mixed / bot.NOTE_NAME).read_text())
        self.assertEqual(note["asked_by_shop"], json.loads((alone / bot.NOTE_NAME).read_text())["asked_by_shop"])
        self.assertEqual([entry["bot"] for entry in note["shop_rule"]["bots"]], [0, 1])
        self.assertTrue(note["shop_rule"]["whole_round"])
        self.assertEqual(sorted(path.name for path in mixed.glob("tonight-*")), [])
        self.assertEqual(sorted(path.name for path in mixed.glob("clone-*")), [])

    def test_eight_bots_and_the_recording_decide_what_the_bot_alone_decides(self) -> None:
        alone = self.folder / "alone"
        self.assertEqual(self._main(alone, Site()), 0)
        cloned = self.folder / "cloned"
        switch = self._switch(8, range(1, 9))
        bot_of = B.assignment(self.rows, 8)
        for number in range(1, 9):
            site = Site()
            self.assertEqual(self._main(cloned, site, "--clone", str(number), switch=switch), 0)
            self.assertEqual(set(site.asked), {shop.split()[0].lower() for shop, n in bot_of.items() if n == number})
            # Bot K starts reading (K - 1) * 75 seconds after it starts.
            self.assertGreaterEqual(site.now, bot.STAGGER_SECONDS * (number - 1))
        # Every bot on: the bot alone asks nothing.
        idle = Site()
        self.assertEqual(self._main(self.folder / "idle", idle, switch=switch), 0)
        self.assertEqual(idle.asked, Counter())
        self.assertEqual(self._main(cloned, Site(), "--record", "8", "--wait-minutes", "0", now=AFTER, switch=switch), 0)
        self.assertEqual(self._decisions(cloned), self._decisions(alone))
        self.assertEqual(self._states(cloned), self._states(alone))
        note = json.loads((cloned / bot.NOTE_NAME).read_text())
        self.assertEqual(note["shop_rule"]["clones"], 8)
        self.assertEqual([entry["bot"] for entry in note["shop_rule"]["bots"]], list(range(1, 9)))
        self.assertEqual(sum(entry["shops"] for entry in note["shop_rule"]["bots"]), len(SHOPS))

    def test_a_bot_started_again_goes_on_from_what_it_kept_and_counts_its_starts(self) -> None:
        cloned = self.folder / "cloned"
        switch = self._switch(2, (1, 2))
        bot_of = B.assignment(self.rows, 2)
        mine = sum(3 for number in bot_of.values() if number == 1)
        # Stopped after a few minutes (its memory's limit, a deployment): its answers kept.
        first = Site()
        self.assertEqual(self._main(cloned, first, "--clone", "1", "--minutes", "0.1", switch=switch), 0)
        kept = bot.Tonight(cloned / bot.TONIGHT.format(night=bot.clone_name(NIGHT, (1, 2)))).load()
        self.assertTrue(0 < len(kept) < mine, kept)
        (cloned / bot.CLONE_DAY.format(name=bot.clone_name(NIGHT, (1, 2)))).unlink()
        again = Site()
        self.assertEqual(self._main(cloned, again, "--clone", "1", now=MORNING + timedelta(minutes=5), switch=switch), 0)
        # Asked only what it had not: each of its shops' robots.txt and catalogue's first page, and the
        # rest of its products.
        shops = sum(1 for number in bot_of.values() if number == 1)
        self.assertEqual(sum(again.asked.values()), 2 * shops + mine - len(kept))
        day = json.loads((cloned / bot.CLONE_DAY.format(name=bot.clone_name(NIGHT, (1, 2)))).read_text())
        self.assertEqual((day["bot"], day["starts"]), (1, 2))

    def test_the_catalogue_read_in_a_process_of_its_own_is_the_same(self) -> None:
        candidates = self.folder / "checks" / L.CANDIDATES_NAME
        here = B.read_bot_rows(self.catalogue, candidates, order=True, clones=8, chosen=(3,))
        said: list[str] = []
        apart = B.read_apart(self.catalogue, candidates, order=True, clones=8, chosen=(3,), say=said.append)
        self.assertEqual(apart.read, "apart", said)
        self.assertGreater(apart.read_peak_mb, 0)
        self.assertEqual((apart.rows, apart.shown, apart.parts, apart.orders, apart.dearer, apart.candidates,
                          apart.bot_of, apart.counts),
                         (here.rows, here.shown, here.parts, here.orders, here.dearer, here.candidates,
                          here.bot_of, here.counts))
        self.assertEqual({row.shop for row in here.rows.values()},
                         {shop for shop, number in B.assignment(self.rows, 8).items() if number == 3})
        # Every shop when none is chosen; the counts are the whole night's either way.
        whole = B.read_bot_rows(self.catalogue, candidates, clones=8)
        self.assertEqual(len(whole.rows), len(self.rows))
        self.assertEqual(whole.counts, here.counts)

    def test_the_table_per_bot(self) -> None:
        rows = {row.key: row for row in self.rows}
        bot_of = B.assignment(rows.values(), 8)
        table = B.table(rows, set(rows), [], bot_of, 8)
        self.assertEqual([entry["bot"] for entry in table], list(range(1, 9)))
        self.assertEqual(sum(entry["shops"] for entry in table), len(SHOPS))
        self.assertEqual(sum(entry["shown"] for entry in table), len(rows))
        self.assertEqual(sum(entry["by_name"] for entry in table), 1)  # Zeta Kettles names no number


class LedgerLetGoTests(unittest.TestCase):
    """The checks' rules 23 (owner, 2026-11-26: «να σβήνονται τα προϊόντα που λείπουν από το feed πάνω
    από 7 μέρες, και κάθε bot να φορτώνει μόνο τα δικά του καταστήματα»)."""

    def test_a_product_not_given_for_over_seven_nights_is_let_go_and_a_line_of_it_kept(self) -> None:
        from datetime import date

        ledger = L.Ledger(products={"a": L.Product(shop="Alpha", state="passed"),
                                    "b": L.Product(shop="Alpha", state="failed", reason="gone"),
                                    "c": L.Product(shop="Beta", state="passed")})
        first = date(2026, 12, 1)
        # The first night the ledger holds no night seen: nothing is let go.
        self.assertEqual(L.forget_unseen(ledger, first, {"a", "c"})["let_go"], 0)
        self.assertEqual(set(ledger.seen), {"a", "b", "c"})
        for day in range(1, 8):
            done = L.forget_unseen(ledger, first + timedelta(days=day), {"a"})
            self.assertEqual(done["let_go"], 0, day)
        # Over seven nights not given: let go, the short line kept.
        done = L.forget_unseen(ledger, first + timedelta(days=8), {"a"})
        self.assertEqual((done["let_go"], done["let_go_by_state"]), (2, {"failed": 1, "passed": 1}))
        self.assertEqual(set(ledger.products), {"a"})
        self.assertEqual(ledger.gone["b"], ["2026-12-09", "failed", "gone"])
        self.assertEqual(set(ledger.seen), {"a"})
        # Given again: out of the lines of those let go (it is asked as a new product).
        L.forget_unseen(ledger, first + timedelta(days=9), {"a", "b"})
        self.assertNotIn("b", ledger.gone)
        self.assertIn("c", ledger.gone)
        # The lines go after thirty nights.
        L.forget_unseen(ledger, first + timedelta(days=40), {"a"})
        self.assertEqual(ledger.gone, {})

    def test_the_ledger_keeps_them_and_a_bot_loads_only_its_shops(self) -> None:
        from datetime import date

        folder = Path(tempfile.mkdtemp())
        ledger = L.Ledger(products={"a": L.Product(shop="Alpha", state="passed"),
                                    "c": L.Product(shop="Beta", state="passed")},
                          shops={"Alpha": L.Shop(reader="page"), "Beta": L.Shop(reader="shopify")},
                          nights=[{"night": "2026-12-01"}])
        L.forget_unseen(ledger, date(2026, 12, 1), {"a"})
        ledger.gone["z"] = ["2026-12-01", "failed", "gone"]
        L.save(ledger, folder / L.LEDGER_NAME)
        back = L.load(folder / L.LEDGER_NAME)
        self.assertEqual((back.seen, back.gone, set(back.products)), (ledger.seen, ledger.gone, {"a", "c"}))
        mine = L.load(folder / L.LEDGER_NAME, shops={"Beta"})
        self.assertEqual((set(mine.products), set(mine.shops), mine.seen, mine.gone), ({"c"}, {"Beta"}, {}, {}))
        self.assertEqual(mine.nights, [{"night": "2026-12-01"}])
        # A ledger written before 26/11 (no nights seen, no lines) reads with none.
        with gzip.open(folder / "old.json.gz", "wt", encoding="utf-8") as handle:
            json.dump({"format": L.FORMAT, "version": L.VERSION, "products": {"a": ["Alpha", "passed"]},
                       "shops": {}, "nights": []}, handle)
        old = L.load(folder / "old.json.gz")
        self.assertEqual((old.seen, old.gone, old.products["a"].state), ({}, {}, "passed"))

    def test_a_bot_of_its_own_reads_its_shops_part_of_the_ledger_with_the_catalogue(self) -> None:
        tests = EightBotsTests("test_the_table_per_bot")
        tests.setUp()
        rows = {row.key: row for row in tests.rows}
        ledger = L.Ledger(products={key: L.Product(shop=row.shop, state="passed") for key, row in rows.items()},
                          shops={row.shop: L.Shop() for row in rows.values()})
        checks = tests.folder / "checks"
        checks.mkdir()
        L.save(ledger, checks / L.LEDGER_NAME)
        found = B.read_bot_rows(tests.catalogue, checks / L.CANDIDATES_NAME, clones=8, chosen=(3,),
                                ledger=checks / L.LEDGER_NAME)
        mine = {shop for shop, number in B.assignment(rows.values(), 8).items() if number == 3}
        self.assertEqual({product.shop for product in found.ledger.products.values()}, mine)
        self.assertEqual(set(found.ledger.shops), mine)
        everything = B.read_bot_rows(tests.catalogue, checks / L.CANDIDATES_NAME, ledger=checks / L.LEDGER_NAME)
        self.assertEqual(len(everything.ledger.products), len(rows))


if __name__ == "__main__":
    unittest.main()
