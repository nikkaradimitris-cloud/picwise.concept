"""The checks' bot in clones (the checks' rules 22; owner, 2026-11-25: «οι πρώτες 500.000 κωδικοί
σκανάρονται από 4 κλωνοποιημένα συστήματα για να τελειώνει πιο γρήγορα ... μην αγνοείς τους 4
κλώνους»; `deployment/bot/shop_checks_bot.py`).

Pinned: each shop is asked by one clone only, always the same, chosen by a code of its name;
a clone asks only its shops and keeps its day (what each shop gave) for the night's recording,
recording nothing itself; the recording, after the round, records the night once from every
clone's day, and decides what the bot alone decides from the same answers; a clone that kept
no day counts as stopped (its answers so far count, none of its shops asked whole, so their
products stay as they were, the checks' rules 21).

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

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import shop_checks_bot as bot  # noqa: E402

from picwise_checks import ledger as L  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402

PAGE = ('<script type="application/ld+json">{"@type": "Product", "name": "Zentra Kettle %d", "sku": "ZK-%d", '
        '"offers": {"@type": "Offer", "price": "%s", "priceCurrency": "GBP", "availability": "InStock"}}</script>')
SHOPS = ("Alpha Kettles", "Beta Kettles", "Gamma Kettles", "Delta Kettles", "Epsilon Kettles", "Zeta Kettles")
MORNING = datetime(2026, 12, 1, 5, 30, tzinfo=timezone.utc)
AFTER = datetime(2026, 12, 2, 3, 7, tzinfo=timezone.utc)


def _product(shop: str, number: int) -> ProviderProduct:
    host = shop.split()[0].lower()
    return ProviderProduct(
        provider_key="awin", provider_product_id=f"{host}-{number}", title=f"Zentra Kettle {number}", brand="Zentra",
        category_text="Home & Garden > Kitchen", product_url=f"https://{host}.invalid/p/{number}",
        image_url=f"https://{host}.invalid/i/{number}.jpg", price_text=f"{20 + number}.00", availability_text="in stock",
        currency="GBP", raw={"merchant_name": shop, "availability": "in stock", "sku": f"ZK-{number}"})


class Site:
    """Every shop's pages: robots.txt not there, each product's page read; Gamma Kettles says
    to come back later at its second product (a 429 ends its night)."""

    def __init__(self) -> None:
        self.now = 0.0
        self.asked: Counter = Counter()

    def fetch(self, url: str, limit: int) -> bot.Answer:
        self.now += 1.0
        host, path = url.split("://", 1)[1].split("/", 1)
        self.asked[host] += 1
        if path == "robots.txt" or path.startswith("products.json"):
            return bot.Answer(404)
        number = int(path.rsplit("/", 1)[1])
        if host.startswith("gamma") and number == 2:
            return bot.Answer(429)
        return bot.Answer(200, "text/html", (PAGE % (number, number, f"{20 + number}.00")).encode())

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def clock(self) -> float:
        return self.now


class ClonesTests(unittest.TestCase):
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

    def _main(self, checks: Path, site: Site, *extra: str, now: datetime = MORNING) -> int:
        checks.mkdir(exist_ok=True)
        # The bot alone asks every shop: no bot of its own on, whatever the repository's switch says
        # (all eight on from 27/11).
        switch = self.folder / "checks_clones.json"
        switch.write_text('{"clones": 2, "bots": []}\n', encoding="utf-8")
        return bot.main(["--catalogue", str(self.catalogue), "--checks", str(checks), "--processes", "0",
                         "--shop-rule", "on", "--cache", str(self.folder / "cache"), *extra],
                        fetch=site.fetch, sleep=site.sleep, clock=site.clock, now=now, environ={}, switch=switch)

    @staticmethod
    def _decisions(checks: Path) -> dict:
        with gzip.open(checks / L.DECISIONS_NAME, "rt", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _states(checks: Path) -> dict:
        ledger = L.load(checks / L.LEDGER_NAME)
        return {key: (product.state, product.reason, product.passed_on) for key, product in ledger.products.items()}

    def test_each_shop_is_asked_by_one_clone_always_the_same(self) -> None:
        for clones in (1, 2, 4):
            chosen = {shop: bot.clone_of(shop, clones) for shop in SHOPS}
            self.assertTrue(set(chosen.values()) <= set(range(1, clones + 1)), clones)
            self.assertEqual(chosen, {shop: bot.clone_of(f"  {shop} ", clones) for shop in SHOPS})
        # Over many shops, each clone has about a quarter of them.
        spread = Counter(bot.clone_of(f"Shop {number} Ltd", 4) for number in range(800))
        self.assertEqual(sorted(spread), [1, 2, 3, 4])
        self.assertTrue(all(150 <= count <= 250 for count in spread.values()), spread)

    def test_the_clones_and_the_recording_decide_what_the_bot_alone_decides(self) -> None:
        alone = self.folder / "alone"
        self.assertEqual(self._main(alone, Site()), 0)
        cloned = self.folder / "cloned"
        sites = [Site(), Site()]
        for number, site in enumerate(sites, start=1):
            self.assertEqual(self._main(cloned, site, "--clone", f"{number}/2"), 0)
            # A clone records nothing; it keeps its day for the recording.
            self.assertFalse((cloned / L.DECISIONS_NAME).exists())
            self.assertTrue((cloned / bot.CLONE_DAY.format(name=bot.clone_name("2026-12-02", (number, 2)))).exists())
        # Each shop asked by its own clone only.
        for number, site in enumerate(sites, start=1):
            self.assertEqual({host.split(".")[0] for host in site.asked},
                             {shop.split()[0].lower() for shop in SHOPS if bot.clone_of(shop, 2) == number})
        self.assertEqual(self._main(cloned, Site(), "--record", "2", "--wait-minutes", "0", now=AFTER), 0)
        self.assertEqual(self._decisions(cloned), self._decisions(alone))
        self.assertEqual(self._states(cloned), self._states(alone))
        note = json.loads((cloned / bot.NOTE_NAME).read_text())
        self.assertEqual(note["shop_rule"]["clones"], 2)
        self.assertEqual(note["asked_by_shop"], json.loads((alone / bot.NOTE_NAME).read_text())["asked_by_shop"])
        self.assertEqual(note["asked_by_shop"]["Gamma Kettles"][2], "429: asked to come back later")
        # The night's files are gone once recorded; the night is not recorded twice.
        self.assertEqual(sorted(path.name for path in cloned.glob("tonight-*")), [])
        self.assertEqual(sorted(path.name for path in cloned.glob("clone-*")), [])
        self.assertEqual(self._main(cloned, Site(), "--record", "2", "--wait-minutes", "0", now=AFTER), 0)

    def test_a_clone_that_kept_no_day_counts_as_stopped(self) -> None:
        cloned = self.folder / "cloned"
        self._main(cloned, Site(), "--clone", "1/2")
        # Clone 2 asked part of its day and stopped before keeping it.
        second = Site()
        self._main(cloned, second, "--clone", "2/2")
        (cloned / bot.CLONE_DAY.format(name=bot.clone_name("2026-12-02", (2, 2)))).unlink()
        said: list[str] = []
        import builtins

        printed = builtins.print
        builtins.print = lambda *args, **kwargs: said.append(" ".join(str(arg) for arg in args))
        try:
            self.assertEqual(self._main(cloned, Site(), "--record", "2", "--wait-minutes", "0", now=AFTER), 0)
        finally:
            builtins.print = printed
        self.assertTrue(any("clone 2 of 2 kept no day" in line for line in said), said)
        note = json.loads((cloned / bot.NOTE_NAME).read_text())
        stopped = {shop for shop, (_asked, _answered, why) in note["asked_by_shop"].items() if why == "error: the clone did not finish"}
        self.assertEqual(stopped, {shop for shop in SHOPS if bot.clone_of(shop, 2) == 2})
        # None of them asked whole: their products stay as they were (21).
        self.assertTrue(stopped <= set(note["shop_rule"]["not_whole"]))

    def test_a_clone_argument_that_is_not_k_of_n_asks_nothing(self) -> None:
        for text in ("0/4", "5/4", "two", "1-4"):
            self.assertEqual(self._main(self.folder / "bad", Site(), "--clone", text), 2, text)


if __name__ == "__main__":
    unittest.main()
