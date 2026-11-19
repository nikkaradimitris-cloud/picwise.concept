"""The shop's own price: its sale price where its feed gives one, and no price worked out.

The owner, 2026-11-19, told that the cheapest shop of one product was chosen at the shops'
own prices while each product then stood at its price after its offer: «Θα ήθελα να
αποφύγουμε τους υπολογισμούς τιμής». Told that Google's format gives a product on sale its
shop's sale price beside its usual one, which the site did not read: «Στην έκπτωση τραβά
στην τιμή της έκπτωσης». Pinned here (`docs/PICWISE_DECISION_CONTRACT.md`, "The shop's own
price"):

- the sale price read only when it is lower than the usual one, in the same currency, live
  now by its dates and not ending within 24 hours; dates that cannot be read leave the
  usual price; a row with no usual price takes a sale price live by its dates;
- a search ordering and showing each product at that price;
- the catalogue's memory: on the first night of sale prices, a product the sale price
  gives another price starts its price's history again, so no fall nobody can date is
  told; from then on a sale beginning or ending is a change like any other.

Every row is local test data: fictional brands and shops, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import gzip
import html
import io
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import price_history  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.catalogue_memory import SALE_PRICES_SINCE, remember_night  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.normalization import (  # noqa: E402
    SALE_DATES_UNREAD,
    SALE_ENDED,
    SALE_ENDING,
    SALE_NOT_BEGUN,
    SALE_NOT_LOWER,
    SALE_OTHER_CURRENCY,
    SALE_PRICE_UNREAD,
    SALE_USED,
    normalize_feed_row_to_provider_product,
    sale_price_in_force,
    sale_price_reading,
)
from picwise_providers.price_history import DOWN, SAME, UP, read_price_notes, write_price_notes  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402

NOW = datetime(2026, 11, 19, 4, 25, tzinfo=timezone.utc)
SHOP = "Fixture Shop One"
_KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"
_COLUMNS = (
    "advertiser_id", "advertiser_name", "id", "title", "description", "link", "image_link",
    "aw_deep_link", "google_product_category", "brand", "availability", "price", "sale_price",
    "sale_price_effective_date", "condition",
)


def _dates(start: datetime, end: datetime) -> str:
    return f"{start:%Y-%m-%dT%H:%M%z}/{end:%Y-%m-%dT%H:%M%z}"


def _row(pid: str, price: str, sale: str = "", dates: str = "", *, shop_id: str = "101",
         shop: str = SHOP) -> dict[str, str]:
    own = f"https://shop{shop_id}.example.invalid/products/{pid}"
    return {
        "advertiser_id": shop_id,
        "advertiser_name": shop,
        "id": pid,
        "title": f"Fixturon 1.7L Electric Kettle {pid}",
        "description": "A fictional cordless electric kettle for local tests.",
        "link": own,
        "image_link": f"https://cdn.example.invalid/{pid}.jpg",
        "aw_deep_link": f"https://track.example.invalid/cread.php?awinmid={shop_id}&ued={own}",
        "google_product_category": _KETTLES,
        "brand": "Fixturon",
        "availability": "in_stock",
        "price": price,
        "sale_price": sale,
        "sale_price_effective_date": dates,
        "condition": "new",
    }


class SalePriceTests(unittest.TestCase):
    def _sale(self, price: str, sale: str, dates: str = "") -> str:
        return sale_price_in_force({"price": price, "sale_price": sale, "sale_price_effective_date": dates}, now=NOW)

    def test_a_lower_sale_price_is_the_shop_s_price(self) -> None:
        self.assertEqual(self._sale("40.00 GBP", "29.99 GBP"), "29.99 GBP")

    def test_a_sale_price_not_lower_or_in_another_currency_is_not(self) -> None:
        self.assertEqual(self._sale("40.00 GBP", "40.00 GBP"), "")
        self.assertEqual(self._sale("40.00 GBP", "49.99 GBP"), "")
        self.assertEqual(self._sale("40.00 GBP", "29.99 EUR"), "")
        self.assertEqual(self._sale("40.00 GBP", "0.00 GBP"), "")
        self.assertEqual(self._sale("40.00 GBP", "call us"), "")

    def test_the_sale_s_dates_decide_when_it_is_the_price(self) -> None:
        live = _dates(NOW - timedelta(days=3), NOW + timedelta(days=10))
        self.assertEqual(self._sale("40.00 GBP", "29.99 GBP", live), "29.99 GBP")
        # Google's own forms: a "Z", an offset with or without its colon, seconds.
        for dates in ("2026-11-01T00:00Z/2026-12-01T00:00Z", "2026-11-01T00:00-0800/2026-12-01T00:00-0800",
                      "2026-11-01T00:00:00+01:00/2026-12-01T00:00:00+01:00", "2026-11-01T00:00Z/2026-12-01T00:00Z/"):
            with self.subTest(dates=dates):
                self.assertEqual(self._sale("40.00 GBP", "29.99 GBP", dates), "29.99 GBP")
        # Not begun, ended, or ending before the next night's reading: the usual price.
        self.assertEqual(self._sale("40.00 GBP", "29.99 GBP", _dates(NOW + timedelta(hours=2), NOW + timedelta(days=9))), "")
        self.assertEqual(self._sale("40.00 GBP", "29.99 GBP", _dates(NOW - timedelta(days=9), NOW - timedelta(hours=1))), "")
        self.assertEqual(self._sale("40.00 GBP", "29.99 GBP", _dates(NOW - timedelta(days=9), NOW + timedelta(hours=20))), "")

    def test_dates_that_cannot_be_read_leave_the_usual_price(self) -> None:
        for dates in ("soon", "2026-11-01T00:00Z", "2026-12-01T00:00Z/2026-11-01T00:00Z", "a/b"):
            with self.subTest(dates=dates):
                self.assertEqual(self._sale("40.00 GBP", "29.99 GBP", dates), "")

    def test_the_reading_names_why_a_sale_price_is_left(self) -> None:
        # Counted in the night's note: the first night read no sale price at all (19/11).
        def reading(price: str, sale: str, dates: str = "") -> str:
            return sale_price_reading({"price": price, "sale_price": sale, "sale_price_effective_date": dates}, now=NOW)

        self.assertEqual(sale_price_reading({"price": "40.00 GBP"}, now=NOW), "")
        self.assertEqual(reading("40.00 GBP", "29.99 GBP"), SALE_USED)
        self.assertEqual(reading("40.00 GBP", "free"), SALE_PRICE_UNREAD)
        self.assertEqual(reading("40.00 GBP", "40.00 GBP"), SALE_NOT_LOWER)
        self.assertEqual(reading("40.00 GBP", "29.99 EUR"), SALE_OTHER_CURRENCY)
        self.assertEqual(reading("40.00 GBP", "29.99 GBP", "soon"), SALE_DATES_UNREAD)
        self.assertEqual(reading("40.00 GBP", "29.99 GBP", _dates(NOW + timedelta(hours=2), NOW + timedelta(days=9))), SALE_NOT_BEGUN)
        self.assertEqual(reading("40.00 GBP", "29.99 GBP", _dates(NOW - timedelta(days=9), NOW - timedelta(hours=1))), SALE_ENDED)
        self.assertEqual(reading("40.00 GBP", "29.99 GBP", _dates(NOW - timedelta(days=9), NOW + timedelta(hours=20))), SALE_ENDING)

    def test_a_row_is_read_at_its_sale_price_in_its_currency(self) -> None:
        live = _dates(datetime.now(timezone.utc) - timedelta(days=1), datetime.now(timezone.utc) + timedelta(days=5))
        product = normalize_feed_row_to_provider_product(_row("s1", "24.99 GBP", "14.99 GBP", live), provider_key="awin")
        self.assertEqual((product.price_text, product.currency), ("14.99", "GBP"))
        # A sale price written without its code is in the usual price's currency.
        product = normalize_feed_row_to_provider_product(_row("s2", "24.99 GBP", "14.99"), provider_key="awin")
        self.assertEqual((product.price_text, product.currency), ("14.99", "GBP"))
        # Without a sale price, or with one ended: the usual price, as before.
        product = normalize_feed_row_to_provider_product(_row("s3", "24.99 GBP"), provider_key="awin")
        self.assertEqual((product.price_text, product.currency), ("24.99", "GBP"))
        ended = _dates(datetime.now(timezone.utc) - timedelta(days=9), datetime.now(timezone.utc) - timedelta(days=1))
        product = normalize_feed_row_to_provider_product(_row("s4", "24.99 GBP", "14.99 GBP", ended), provider_key="awin")
        self.assertEqual((product.price_text, product.currency), ("24.99", "GBP"))
        # No usual price: a sale price live by its dates.
        product = normalize_feed_row_to_provider_product(_row("s5", "", "14.99 GBP"), provider_key="awin")
        self.assertEqual((product.price_text, product.currency), ("14.99", "GBP"))

    def test_an_awin_format_row_reads_as_before(self) -> None:
        row = {"aw_product_id": "w1", "product_name": "Fixturon Kettle", "category_name": "Kettles",
               "aw_deep_link": "https://track.example.invalid/w1", "search_price": "20.00", "currency": "GBP",
               "merchant_name": "Fixture Awin Shop"}
        product = normalize_feed_row_to_provider_product(row, provider_key="awin")
        self.assertEqual((product.price_text, product.currency), ("20.00", "GBP"))


class SearchAtTheShopsPricesTests(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime.now(timezone.utc)
        folder = Path(tempfile.mkdtemp())
        self.feed = folder / "google.csv.gz"
        rows = [
            # On sale, live: £14.99, though its usual price is the dearest.
            _row("g1", "24.99 GBP", "14.99 GBP", _dates(now - timedelta(days=2), now + timedelta(days=7))),
            _row("g5", "19.99 GBP", shop_id="202", shop="Fixture Shop Two"),
            # Its sale ended: its usual £12.99.
            _row("g6", "12.99 GBP", "9.99 GBP", _dates(now - timedelta(days=9), now - timedelta(days=2)),
                 shop_id="303", shop="Fixture Shop Three"),
        ]
        with gzip.open(self.feed, "wt", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        saved = {name: os.environ.get(name) for name in ("AWIN_FEED_FILE", "AWIN_FEED_URL",
                                                         "PICWISE_PREPARED_CATALOGUE_FILE")}
        os.environ["AWIN_FEED_FILE"] = str(self.feed)
        os.environ.pop("AWIN_FEED_URL", None)
        os.environ.pop("PICWISE_PREPARED_CATALOGUE_FILE", None)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def test_each_product_is_ordered_and_shown_at_the_shop_s_price(self) -> None:
        resolution = resolve_live_search("kettle")
        cards = [
            (card.get("provider_product_id"), card.get("price_text"))
            for card in resolution.provider_feed_selected_products
        ]
        self.assertEqual(cards, [("g6", "12.99"), ("g1", "14.99"), ("g5", "19.99")])
        from api.index import app as wsgi_app

        page = b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search", "QUERY_STRING": urlencode({"q": "kettle"}),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")
        prices = [html.unescape(price) for price in re.findall(r'<p class="pw-price">(.*?)</p>', page)]
        self.assertEqual(prices, ["£12.99", "£14.99", "£19.99"])
        # Nothing is said of the usual price: a price struck through would be a saving told
        # on the shop's word alone.
        self.assertNotIn("24.99", page)
        self.assertNotIn("9.99 GBP", page)


def _product(pid: str, price: str, sale: str = "") -> ProviderProduct:
    raw = {"merchant_name": SHOP, "price": f"{price} GBP"}
    if sale:
        raw["sale_price"] = f"{sale} GBP"
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon Sofa {pid}", brand="Fixturon",
        category_text="Furniture > Sofas", product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg", price_text=sale or price,
        availability_text="in stock", currency="GBP", raw=raw,
    )


class _Nights:
    def __init__(self) -> None:
        folder = Path(tempfile.mkdtemp())
        self.memory = folder / "memory.sqlite"
        self.out = folder / price_history.PRICE_NOTES_NAME
        self.night = datetime(2026, 11, 6, 4, 23, tzinfo=timezone.utc) - timedelta(days=1)

    def run(self, products: list[ProviderProduct], nights: int = 1) -> dict:
        summary: dict = {}
        for _ in range(nights):
            self.night += timedelta(days=1)
            summary = remember_night(self.memory, products, prepared_at=self.night)
        return summary

    def before_sale_prices(self) -> None:
        """The memory as written before the shops' sale prices were read (to 19/11)."""
        with closing(sqlite3.connect(str(self.memory))) as db, db:
            db.execute("DELETE FROM meta WHERE name = ?", (SALE_PRICES_SINCE,))

    def note(self, pid: str):
        write_price_notes(self.memory, self.out, prepared_at=self.night)
        return read_price_notes(self.out).note(SHOP, pid, currency="GBP")


class PriceHistoryTests(unittest.TestCase):
    def test_on_the_first_night_of_sale_prices_a_product_on_sale_starts_its_history_again(self) -> None:
        nights = _Nights()
        nights.run([_product("a", "40.00", sale="30.00"), _product("b", "40.00")], 8)
        # Written before sale prices: both were remembered at their usual £40.
        with closing(sqlite3.connect(str(nights.memory))) as db, db:
            db.execute("UPDATE products SET price_pence = 4000")
            db.execute("UPDATE prices SET price_pence = 4000")
        nights.before_sale_prices()
        summary = nights.run([_product("a", "40.00", sale="30.00"), _product("b", "35.00")])
        self.assertEqual((summary["on_sale_tonight"], summary["history_restarted_tonight"]), (1, 1))
        # a: the shop may have asked £30 all along; no fall is told, its history starts tonight.
        note = nights.note("a")
        self.assertEqual((note.kind, note.nights, note.change_pence), (SAME, 1, 0))
        # b: a price the shop changed, told as before.
        note = nights.note("b")
        self.assertEqual((note.kind, note.change_pence), (DOWN, 500))
        # A second preparation of that night starts nothing again.
        later = nights.night.replace(hour=6, minute=40)
        summary = remember_night(nights.memory, [_product("a", "40.00", sale="30.00"), _product("b", "35.00")],
                                 prepared_at=later)
        self.assertEqual(summary["history_restarted_tonight"], 0)
        self.assertEqual(nights.note("a").kind, SAME)

    def test_the_night_s_note_counts_the_sale_prices_given_and_why_each_is_left(self) -> None:
        nights = _Nights()
        ended = _product("e", "40.00", sale="30.00")
        ended.raw["sale_price_effective_date"] = "2026-10-01T00:00Z/2026-10-31T23:59Z"
        not_lower = _product("n", "40.00")
        not_lower.raw["sale_price"] = "40.00 GBP"
        summary = nights.run([_product("a", "40.00", sale="30.00"), ended, not_lower, _product("b", "35.00")])
        self.assertEqual(
            summary["sale_prices"],
            {
                "given": 3,
                "readings": {SALE_ENDED: 1, SALE_NOT_LOWER: 1, SALE_USED: 1},
                "shops": [{"shop": SHOP, "given": 3, "used": 1}],
            },
        )
        self.assertEqual(summary["on_sale_tonight"], 1)
        import contextlib
        import importlib.util

        spec = importlib.util.spec_from_file_location("print_shops", ROOT / "deployment" / "server" / "print_shops.py")
        print_shops = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(print_shops)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_shops.print_memory({"memory": summary})
        report = out.getvalue()
        self.assertIn("  sale prices: 3 of tonight's products give one: ended 1, not lower 1, used 1", report)
        self.assertIn(f"  shops giving the most: {SHOP} 3 (1 used)", report)

    def test_from_then_on_a_sale_beginning_or_ending_is_a_change(self) -> None:
        nights = _Nights()
        nights.run([_product("c", "40.00")], 8)
        summary = nights.run([_product("c", "40.00", sale="30.00")])
        self.assertEqual(summary["history_restarted_tonight"], 0)
        note = nights.note("c")
        self.assertEqual((note.kind, note.change_pence, note.since), (DOWN, 1000, nights.night.date()))
        nights.run([_product("c", "40.00", sale="30.00")], 7)
        nights.run([_product("c", "40.00")])
        note = nights.note("c")
        self.assertEqual((note.kind, note.change_pence), (UP, 1000))


if __name__ == "__main__":
    unittest.main()
